import { useCallback, useEffect, useRef, useState } from "react";
import AsignacionForm from "./inspeccionesAsignacionForm";
import InspSelect2 from "./InspSelect2";
import {
  asignacionFormValid, asignacionesValid, postAsignacion, quitarAsignacion,
  type AsignacionFormData, type AsignacionesData, type Row, type Tab,
} from "./inspeccionesAsignacionesApi";
import { apiPath, client } from "./inspeccionesEscuelasApi";
import { ImportModal, InspModal, Pagination, Screen } from "./inspeccionesEscuelasPage";
import { submitForm, useScreen } from "./inspeccionesScreen";
import { escuelasNavigation } from "./inspeccionesEscuelasNavigation";
import { useBootstrapModal } from "./inspeccionesModal";
import InspToasts from "./inspeccionesToasts";

/**
 * Asignaciones tab of the Inspecciones panel (`inspecciones/asignaciones.html`,
 * IN02) and the assignment form as a page (`asignacion_form_page.html`). Data
 * comes from the vertical's G1 web API: the day totals are the server's, never
 * derived from the rows of the page. Filters stay a native GET form
 * (`panel.js` rules), the import stays the native multipart form, the form
 * opens in the `#insp-modal-form` modal (load, post, «otra», reload) and
 * «Quitar» asks for confirmation, posts once and returns to the day.
 */
const PANEL = "/inspecciones/asignaciones/";

function Encabezado({ tabs }: { tabs: Tab[] }) {
  return (
    <>
      <h1 className="insp-titulo">Inspecciones escolares</h1>
      <ul className="nav insp-tabs border-bottom mb-3" aria-label="Secciones">
        {tabs.map((tab) => (
          <li key={tab.id} className="nav-item">
            <a className={`nav-link${tab.id === "asignaciones" ? " active" : ""}`} href={tab.url} aria-current={tab.id === "asignaciones" ? "page" : undefined}>{tab.label}</a>
          </li>
        ))}
      </ul>
    </>
  );
}

function Kpis({ totales }: { totales: AsignacionesData["totales"] }) {
  return (
    <div className="insp-totales">
      <div className="insp-kpi"><div className="insp-kpi-titulo">Asignaciones de la jornada</div><div className="insp-kpi-valor">{totales.total}</div></div>
      <div className="insp-kpi insp-kpi-ambar"><div className="insp-kpi-titulo">Pendientes</div><div className="insp-kpi-valor">{totales.pendiente}</div></div>
      <div className="insp-kpi insp-kpi-celeste"><div className="insp-kpi-titulo">En curso (borrador)</div><div className="insp-kpi-valor">{totales.en_curso}</div></div>
      <div className="insp-kpi insp-kpi-teal"><div className="insp-kpi-titulo" title="Sin actas anuladas ni de prueba">Finalizadas</div><div className="insp-kpi-valor">{totales.finalizada}</div></div>
    </div>
  );
}

const searchUrl = (url: string, term: string) => `${apiPath(url)}${url.includes("?") ? "&" : "?"}q=${encodeURIComponent(term)}`;

function Filters({ data, openForm, openImport }: { data: AsignacionesData; openForm: (url: string) => void; openImport: (trigger: HTMLButtonElement) => void }) {
  const form = useRef<HTMLFormElement>(null);
  const { filters, options, day } = data;
  // `panel.js`: a [data-insp-auto-submit] change submits the filters.
  useEffect(() => {
    const element = form.current;
    if (!element) return undefined;
    const change = (event: Event) => {
      if ((event.target as HTMLElement).hasAttribute?.("data-insp-auto-submit")) submitForm(element);
    };
    element.addEventListener("change", change);
    return () => element.removeEventListener("change", change);
  }, []);
  const searchInspector = useCallback((term: string, signal: AbortSignal) =>
    client.get(searchUrl(options.inspectores_url, term), { signal }).then(({ data: body }: { data: unknown }) => body), [options.inspectores_url]);
  const searchEscuela = useCallback((term: string, signal: AbortSignal) =>
    client.get(searchUrl(options.escuelas_url, term), { signal }).then(({ data: body }: { data: unknown }) => body), [options.escuelas_url]);
  const provincia = options.provincias.some((p) => String(p.id) === filters.provincia) ? filters.provincia : "";
  const choice = (list: { value: string }[], value: string) => (list.some((c) => c.value === value) ? value : "");
  return (
    <form ref={form} method="get" action={PANEL} className="insp-filtros">
      <div className="insp-jornada" role="group" aria-label="Jornada">
        <a className="btn btn-outline-secondary insp-boton-dia" href={day.anterior} aria-label="Día anterior">‹</a>
        <label className="visually-hidden" htmlFor="filtro-fecha">Jornada</label>
        <input id="filtro-fecha" className="form-control" type="date" name="fecha" defaultValue={filters.fecha} data-insp-auto-submit="" />
        <a className="btn btn-outline-secondary insp-boton-dia" href={day.siguiente} aria-label="Día siguiente">›</a>
        <a className={`btn btn-outline-secondary${day.es_hoy ? " disabled" : ""}`} href={day.hoy}>Hoy</a>
      </div>
      <label className="visually-hidden" htmlFor="filtro-inspector">Inspector</label>
      <InspSelect2 id="filtro-inspector" name="inspector" placeholder="Todos los inspectores" minimum={3} initial={filters.inspector} search={searchInspector} />
      <label className="visually-hidden" htmlFor="filtro-escuela">Buscar por escuela</label>
      <InspSelect2 id="filtro-escuela" name="escuela" placeholder="Buscar por escuela" minimum={3} initial={filters.escuela} search={searchEscuela} />
      <label className="visually-hidden" htmlFor="filtro-provincia">Provincia</label>
      <select id="filtro-provincia" className="form-select" name="provincia" data-insp-auto-submit="" defaultValue={provincia}>
        <option value="">Todas las provincias</option>
        {options.provincias.map((p) => <option key={p.id} value={String(p.id)}>{p.nombre}</option>)}
      </select>
      <label className="visually-hidden" htmlFor="filtro-estado">Estado</label>
      <select id="filtro-estado" className="form-select" name="estado" data-insp-auto-submit="" defaultValue={choice(options.estados, filters.estado)}>
        {options.estados.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
      <label className="visually-hidden" htmlFor="filtro-estado-acta">Estado del acta</label>
      <select id="filtro-estado-acta" className="form-select" name="estado_acta" data-insp-auto-submit="" defaultValue={choice(options.estados_acta, filters.estado_acta)}>
        {options.estados_acta.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
      <span className="insp-espacio" />
      <button type="button" className="btn btn-outline-primary" onClick={(event) => openImport(event.currentTarget)}>
        <i className="fas fa-upload" aria-hidden="true" />Importar Excel/CSV
      </button>
      <button type="button" className="btn btn-primary" onClick={() => openForm(data.urls.nueva)}>
        <i className="fas fa-plus" aria-hidden="true" />Nueva asignación
      </button>
    </form>
  );
}

function RemoveButton({ row, onForbidden }: { row: Row; onForbidden: (data: unknown) => void }) {
  const [state, setState] = useState<"idle" | "pending" | "uncertain">("idle");
  const name = row.inspector.nombre;
  // `data-insp-confirmar`: `window.confirm` before sending; cancel sends nothing.
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (state === "pending") return;
    if (!window.confirm(`¿Quitar la asignación de ${row.escuela.nombre} a ${name}?`)) return;
    setState("pending");
    const outcome = await quitarAsignacion(row.quitar_url);
    if (outcome.kind === "redirect") escuelasNavigation.assign(outcome.to);
    else if (outcome.kind === "forbidden") onForbidden(outcome.data);
    else setState("uncertain");
  };
  return (
    <form method="post" onSubmit={(event) => void submit(event)}>
      <button type="submit" className="insp-boton-icono insp-boton-quitar" aria-label={`Quitar asignación de ${row.escuela.nombre}`} disabled={state === "pending"}>
        <i className="fas fa-trash-alt" aria-hidden="true" />
      </button>
      {state === "uncertain" && <div className="small text-danger" role="alert">No se pudo confirmar el resultado. <a href={PANEL}>Volver a las asignaciones</a></div>}
    </form>
  );
}

function AsignacionRow({ row, onForbidden }: { row: Row; onForbidden: (data: unknown) => void }) {
  const badge = row.estado === "finalizada" ? "insp-badge-ok" : row.estado === "en_curso" ? "insp-badge-info" : "insp-badge-alerta";
  return (
    <tr>
      <td>
        <div className="insp-persona">
          <span className="insp-avatar" aria-hidden="true">{row.iniciales}</span>
          <div>{row.inspector.nombre}{" "}<span className="insp-detalle insp-mono">{row.inspector.usuario}</span></div>
        </div>
      </td>
      <td>{row.escuela.nombre}{" "}<span className="insp-detalle insp-mono">{row.escuela.cueanexo}</span></td>
      <td>{row.escuela.localidad}{row.escuela.provincia ? ` · ${row.escuela.provincia}` : ""}</td>
      <td><span className={`insp-badge ${badge}`}><i aria-hidden="true" />{row.estado_display}</span></td>
      <td>
        {row.actas.length ? row.actas.map((acta) => (
          <div key={acta.numero}>
            <a href={acta.url}>{acta.numero}</a>
            {acta.anulada && <>{" "}<span className="insp-badge insp-badge-error">Anulada</span></>}
            {acta.prueba && <>{" "}<span className="insp-badge insp-badge-neutro">Prueba</span></>}
          </div>
        )) : "—"}
      </td>
      <td className="text-end">
        {row.se_puede_quitar ? <RemoveButton row={row} onForbidden={onForbidden} />
          : <span className="insp-boton-icono deshabilitado" title="No se puede quitar: ya tiene acta">–<span className="visually-hidden">No se puede quitar: ya tiene acta</span></span>}
      </td>
    </tr>
  );
}

const IMPORT_HELP = (
  <p className="small text-muted">
    {"Columnas: "}<strong>fecha</strong>{" (AAAA-MM-DD o DD/MM/AAAA), "}<strong>cueanexo</strong>{" e "}<strong>inspector</strong>
    {" (usuario, DNI o mail). El inspector tiene que tener la sección Inspecciones escolares con rol Inspector. Una asignación repetida no se duplica; si la escuela ya tiene otro inspector ese día, se asigna igual y cuenta como otra visita."}
  </p>
);

type FormState = { url: string; data: AsignacionFormData | null; success: string; revision: number; pending: boolean; uncertain: boolean };
const accepted = (status: number) => (status >= 200 && status < 300) || status === 403;

/** `#insp-modal-form`: «Cargando…», then the form; a confirmed save reloads the page. */
function FormModal({ url, close, onForbidden }: { url: string; close: () => void; onForbidden: (data: unknown) => void }) {
  const modal = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<FormState>({ url, data: null, success: "", revision: 0, pending: false, uncertain: false });
  useBootstrapModal(modal, close, null);
  const load = useCallback((target: string, success: string) => {
    client.get(apiPath(target), { headers: { "X-Requested-With": "XMLHttpRequest" }, validateStatus: accepted }).then(({ data, status }: { data: unknown; status: number }) => {
      if (status === 403) { onForbidden(data); return; }
      if (asignacionFormValid(data)) setState((s) => ({ ...s, url: target, data, success, revision: s.revision + 1, pending: false }));
      else setState((s) => ({ ...s, uncertain: true }));
    }).catch(() => setState((s) => ({ ...s, uncertain: true })));
  }, [onForbidden]);
  useEffect(() => { load(url, ""); }, [load, url]);
  const parent = useCallback(() => modal.current, []);
  const submit = async (body: URLSearchParams) => {
    setState((s) => ({ ...s, pending: true }));
    const outcome = await postAsignacion(state.url.split("?")[0], body, true);
    if (outcome.kind === "json") {
      if (outcome.otra) {
        // `panel.js` otraConFecha: the next form keeps the day that was just saved.
        const fecha = body.get("fecha");
        load(state.url.split("?")[0] + (fecha ? `?fecha=${encodeURIComponent(fecha)}` : ""), outcome.mensaje);
      } else escuelasNavigation.reload();
    } else if (outcome.kind === "invalid") setState((s) => ({ ...s, data: outcome.data, success: "", revision: s.revision + 1, pending: false }));
    else if (outcome.kind === "forbidden") onForbidden(outcome.data);
    else setState((s) => ({ ...s, uncertain: true }));
  };
  return (
    <InspModal id="insp-modal-form" labelledBy="insp-modal-form-titulo" dialogClass="modal-dialog modal-lg modal-dialog-scrollable" modalRef={modal} close={close}>
      <div className="modal-content" data-insp-modal-contenido="">
        {state.uncertain ? <div className="modal-body" role="alert">No se pudo confirmar el resultado. <a href={PANEL}>Volver a las asignaciones</a></div>
          : state.data ? <AsignacionForm key={state.revision} data={state.data} action={state.url.split("?")[0]} modal={{ parent, close }} success={state.success} pending={state.pending} onSubmit={(body) => void submit(body)} autoFocus />
            : <div className="modal-body text-center text-muted py-5">Cargando…</div>}
      </div>
    </InspModal>
  );
}

function Panel({ data, onForbidden }: { data: AsignacionesData; onForbidden: (data: unknown) => void }) {
  const [formUrl, setFormUrl] = useState<string | null>(null);
  const [importTrigger, setImportTrigger] = useState<HTMLElement | null>(null);
  const closeForm = useCallback(() => setFormUrl(null), []);
  const closeImport = useCallback(() => setImportTrigger(null), []);
  return (
    <>
      <Encabezado tabs={data.tabs} />
      <Kpis totales={data.totales} />
      <section className="insp-seccion">
        <div className="insp-seccion-barra"><Filters data={data} openForm={setFormUrl} openImport={setImportTrigger} /></div>
        {data.results.length ? (
          <div className="table-responsive">
            <table className="table insp-tabla">
              <thead>
                <tr>
                  {["Inspector", "Escuela", "Localidad · Provincia", "Estado", "Acta"].map((h) => <th key={h} scope="col">{h}</th>)}
                  <th scope="col"><span className="visually-hidden">Acciones</span></th>
                </tr>
              </thead>
              <tbody>{data.results.map((row) => <AsignacionRow key={row.id} row={row} onForbidden={onForbidden} />)}</tbody>
            </table>
          </div>
        ) : (
          <div className="insp-vacio">
            <i className="fas fa-calendar-day" aria-hidden="true" />
            {" "}<strong>No hay asignaciones</strong>
            {" "}No hay asignaciones para esta jornada con los filtros elegidos.
          </div>
        )}
        {data.page.count > 0 && (
          <div className="insp-seccion-pie">
            <span>Mostrando {data.page.start_index}–{data.page.end_index} de {data.page.count} · {data.totales.inspectores} inspectores</span>
            {" "}<Pagination page={data.page} />
          </div>
        )}
      </section>
      {importTrigger && <ImportModal action={data.urls.importar} trigger={importTrigger} close={closeImport} title="Importar asignaciones" tipo="asignaciones" help={IMPORT_HELP} />}
      {formUrl && <FormModal url={formUrl} close={closeForm} onForbidden={onForbidden} />}
      <InspToasts messages={data.messages} />
    </>
  );
}

/** `asignacion_form_page.html`: the same form inside `.insp-dialogo`, posted as a page. */
function FormPage({ data, endpoint, onForbidden }: { data: AsignacionFormData; endpoint: string; onForbidden: (data: unknown) => void }) {
  const [current, setCurrent] = useState({ data, revision: 0, pending: false, uncertain: false });
  // The native invalid POST renders a new page: back to the top, focus at the document start.
  useEffect(() => {
    if (!current.revision) return;
    window.scrollTo(0, 0);
    const body = document.body;
    body.tabIndex = -1;
    body.focus({ preventScroll: true });
    body.removeAttribute("tabindex");
  }, [current.revision]);
  const submit = async (body: URLSearchParams) => {
    setCurrent((s) => ({ ...s, pending: true }));
    const outcome = await postAsignacion(endpoint, body, false);
    if (outcome.kind === "redirect") { escuelasNavigation.assign(outcome.to); return; }
    if (outcome.kind === "invalid") setCurrent((s) => ({ data: outcome.data, revision: s.revision + 1, pending: false, uncertain: false }));
    else if (outcome.kind === "forbidden") onForbidden(outcome.data);
    else setCurrent((s) => ({ ...s, pending: false, uncertain: true }));
  };
  return (
    <>
      <Encabezado tabs={current.data.tabs} />
      <div className="insp-dialogo">
        <AsignacionForm key={current.revision} data={current.data} action={endpoint} modal={null} success="" pending={current.pending} onSubmit={(body) => void submit(body)} autoFocus={false} />
        {current.uncertain && <p role="alert">No se pudo confirmar el resultado. <a href={PANEL}>Volver a las asignaciones</a></p>}
      </div>
      <InspToasts messages={current.data.messages} />
    </>
  );
}

export function AsignacionesPanelPage() {
  const { state, forbidden } = useScreen(`web/inspecciones/asignaciones/${window.location.search}`, asignacionesValid);
  return <Screen state={state} noun="asignaciones">{(data) => <Panel data={data} onForbidden={forbidden} />}</Screen>;
}

export function AsignacionFormPage() {
  const endpoint = "/api/web/inspecciones/asignaciones/nueva/";
  const { state, forbidden } = useScreen(`${apiPath(endpoint)}${window.location.search}`, asignacionFormValid);
  return <Screen state={state} noun="asignaciones">{(data) => <FormPage data={data} endpoint={endpoint} onForbidden={forbidden} />}</Screen>;
}
