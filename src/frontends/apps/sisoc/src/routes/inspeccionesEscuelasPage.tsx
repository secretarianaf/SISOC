import { useCallback, useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import ClaroFrame, { type ClaroLayout } from "./ClaroFrame";
import InspSelect2, { type InspOption } from "./InspSelect2";
import EscuelaForm from "./inspeccionesEscuelaForm";
import {
  apiPath, apiUrlValid, client, escuelaFormValid, internal, layoutValid, messagesValid, optionValid, postEscuela, provinciasValid,
  tabsValid, totalesValid, type EscuelaFormData, type Totales,
} from "./inspeccionesEscuelasApi";
import { escuelasNavigation } from "./inspeccionesEscuelasNavigation";
import { useBootstrapModal } from "./inspeccionesModal";
import { submitForm, useScreen, type Loaded } from "./inspeccionesScreen";
import InspToasts, { type InspMessage } from "./inspeccionesToasts";

/**
 * Escuelas tab of the Inspecciones panel (`inspecciones/escuelas.html`, IN05)
 * and the school form as a page (`escuela_form_page.html`). Data comes from the
 * vertical's G1 web API; filters stay a native GET form (`panel.js` rules), the
 * import stays the native multipart form, and the school form opens in the
 * `#insp-modal-form` modal as in `panel.js` (load, post, «otra», reload).
 */
type Row = {
  id: number; cueanexo: string; nombre: string; provincia: string;
  localidad: { vinculada: boolean; texto: string; distrito: string; aviso: string };
  domicilio: string; cp: string; telefono: string; mail: string; mail_invalido: boolean; form_url: string;
};
export type Page = {
  number: number; count: number; start_index: number; end_index: number; has_other_pages: boolean;
  previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string;
};
export type EscuelasData = {
  layout: ClaroLayout; tabs: { id: string; label: string; url: string }[]; totales: Totales;
  filters: { q: string; provincia: string; localidad: InspOption | null };
  options: { provincias: { id: number; nombre: string }[]; localidades_url: string };
  a_revisar: { activo: boolean; contador: number; url: string };
  results: Row[]; page: Page; urls: { nueva: string; importar: string }; editar_url: string | null; messages: InspMessage[];
};

const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object";
const text = (v: unknown): v is string => typeof v === "string";
const PANEL = "/inspecciones/";
const accepted = (status: number) => (status >= 200 && status < 300) || status === 403;

function rowValid(r: unknown): r is Row {
  return record(r) && Number.isSafeInteger(r.id) && ["cueanexo", "nombre", "provincia", "domicilio", "cp", "telefono", "mail"].every((k) => text(r[k])) &&
    typeof r.mail_invalido === "boolean" && apiUrlValid(r.form_url) && record(r.localidad) && typeof r.localidad.vinculada === "boolean" &&
    ["texto", "distrito", "aviso"].every((k) => text((r.localidad as Record<string, unknown>)[k]));
}
function escuelasValid(v: unknown): v is EscuelasData {
  if (!record(v) || !record(v.filters) || !record(v.options) || !record(v.a_revisar) || !record(v.page) || !record(v.urls)) return false;
  const p = v.page;
  return layoutValid(v.layout) && tabsValid(v.tabs) && totalesValid(v.totales) &&
    text(v.filters.q) && text(v.filters.provincia) && (v.filters.localidad === null || optionValid(v.filters.localidad)) &&
    provinciasValid(v.options.provincias) && apiUrlValid(v.options.localidades_url) &&
    typeof v.a_revisar.activo === "boolean" && Number.isSafeInteger(v.a_revisar.contador) && text(v.a_revisar.url) && v.a_revisar.url.startsWith("?") &&
    Array.isArray(v.results) && v.results.every(rowValid) &&
    ["number", "count", "start_index", "end_index"].every((k) => Number.isSafeInteger(p[k])) && typeof p.has_other_pages === "boolean" &&
    Array.isArray(p.range) && text(p.query_without_page) &&
    apiUrlValid(v.urls.nueva) && internal(v.urls.importar) && (v.editar_url === null || apiUrlValid(v.editar_url)) && messagesValid(v.messages);
}

function Encabezado({ totales, tabs }: { totales: Totales; tabs: EscuelasData["tabs"] }) {
  return (
    <>
      <h1 className="insp-titulo">Inspecciones escolares</h1>
      <div className="insp-totales">
        <div className="insp-kpi"><div className="insp-kpi-titulo">Escuelas en el catálogo</div><div className="insp-kpi-valor">{totales.escuelas}</div></div>
        <div className={`insp-kpi${totales.escuelas_a_revisar ? " insp-kpi-alerta" : ""}`}><div className="insp-kpi-titulo">Escuelas con datos a revisar</div><div className="insp-kpi-valor">{totales.escuelas_a_revisar}</div></div>
        <div className="insp-kpi"><div className="insp-kpi-titulo">Asignaciones de hoy ({totales.jornada})</div><div className="insp-kpi-valor">{totales.asignaciones_hoy}</div></div>
        <div className="insp-kpi"><div className="insp-kpi-titulo">Actas cerradas hoy</div><div className="insp-kpi-valor">{totales.actas_hoy}</div></div>
      </div>
      <ul className="nav insp-tabs border-bottom mb-3" aria-label="Secciones">
        {tabs.map((tab) => (
          <li key={tab.id} className="nav-item">
            <a className={`nav-link${tab.id === "escuelas" ? " active" : ""}`} href={tab.url} aria-current={tab.id === "escuelas" ? "page" : undefined}>{tab.label}</a>
          </li>
        ))}
      </ul>
    </>
  );
}

function Filters({ data, openForm, openImport }: { data: EscuelasData; openForm: (url: string) => void; openImport: (trigger: HTMLButtonElement) => void }) {
  const form = useRef<HTMLFormElement>(null);
  const { filters, options, a_revisar: chip } = data;
  const [clear, setClear] = useState(0);
  const [localidadDisabled, setLocalidadDisabled] = useState(!filters.provincia);
  // `panel.js`: a [data-insp-auto-submit] change submits the filters.
  useEffect(() => {
    const element = form.current;
    if (!element) return undefined;
    const change = (event: Event) => {
      if ((event.target as HTMLElement).hasAttribute?.("data-insp-auto-submit")) submitForm(element);
    };
    // `data-insp-limpia` is bound on the province itself, so it runs before the form's
    // auto-submit: the locality is emptied (and disabled without a province) in the DOM first.
    const provincia = element.querySelector<HTMLSelectElement>("#filtro-provincia");
    const limpia = () => {
      const localidad = element.querySelector<HTMLSelectElement>("#filtro-localidad");
      if (localidad) { localidad.value = ""; localidad.disabled = !provincia?.value; }
      setClear((n) => n + 1);
      setLocalidadDisabled(!provincia?.value);
    };
    provincia?.addEventListener("change", limpia);
    element.addEventListener("change", change);
    return () => { provincia?.removeEventListener("change", limpia); element.removeEventListener("change", change); };
  }, []);
  const search = useCallback((term: string, signal: AbortSignal) => {
    const provincia = form.current?.querySelector<HTMLSelectElement>("#filtro-provincia")?.value ?? "";
    const url = `${apiPath(options.localidades_url)}?q=${encodeURIComponent(term)}&provincia=${encodeURIComponent(provincia)}`;
    return client.get(url, { signal }).then(({ data: body }: { data: unknown }) => body);
  }, [options.localidades_url]);
  const selected = options.provincias.some((p) => String(p.id) === filters.provincia) ? filters.provincia : "";
  return (
    <form ref={form} method="get" action={PANEL} className="insp-filtros" role="search">
      <label className="insp-busqueda">
        <span className="visually-hidden">Buscar</span>
        <i className="fas fa-search" aria-hidden="true" />
        <input id="filtro-q" className="form-control" type="search" name="q" defaultValue={filters.q} placeholder="Nombre, Cueanexo o domicilio" />
      </label>
      <label className="visually-hidden" htmlFor="filtro-provincia">Provincia</label>
      <select id="filtro-provincia" className="form-select" name="provincia" data-insp-auto-submit="" data-insp-limpia="#filtro-localidad" defaultValue={selected}>
        <option value="">Todas las provincias</option>
        {options.provincias.map((p) => <option key={p.id} value={String(p.id)}>{p.nombre}</option>)}
      </select>
      <label className="visually-hidden" htmlFor="filtro-localidad">Localidad</label>
      <InspSelect2 id="filtro-localidad" name="localidad" placeholder={filters.provincia ? "Todas las localidades" : "Elegí provincia"} minimum={0}
        initial={filters.localidad} search={search} disabled={localidadDisabled} clearSignal={clear} />
      {chip.activo && <input type="hidden" name="a_revisar" value="1" />}
      <a className={`insp-chip${chip.activo ? " activo" : ""}`} href={chip.url}>
        <span className="insp-punto" aria-hidden="true" />
        {` A revisar · ${chip.contador} `}
      </a>
      <span className="insp-espacio" />
      <button type="button" className="btn btn-outline-primary" onClick={(event) => openImport(event.currentTarget)}>
        <i className="fas fa-upload" aria-hidden="true" />Importar Excel/CSV
      </button>
      <button type="button" className="btn btn-primary" onClick={() => openForm(data.urls.nueva)}>
        <i className="fas fa-plus" aria-hidden="true" />Nueva escuela
      </button>
    </form>
  );
}

function EscuelaRow({ row, openForm }: { row: Row; openForm: (url: string) => void }) {
  const l = row.localidad;
  return (
    <tr>
      <td className="insp-mono">{row.cueanexo}</td>
      <td>{row.nombre}</td>
      <td>{row.provincia}</td>
      <td>
        {l.vinculada ? <>{l.texto}{l.distrito && <>{" "}<span className="insp-detalle">{l.distrito}</span></>}</>
          : <><span className="text-muted">{l.texto}</span>{l.aviso && <>{" "}<span className="insp-badge insp-badge-alerta">{l.aviso}</span></>}</>}
      </td>
      <td>{row.domicilio}</td>
      <td>{row.cp}</td>
      <td>{row.telefono}</td>
      <td className="insp-mail">
        {row.mail_invalido ? <><span className="text-muted">{row.mail}</span>{" "}<span className="insp-badge insp-badge-alerta">mail inválido</span></> : row.mail}
      </td>
      <td className="text-end">
        <button type="button" className="insp-boton-icono" aria-label={`Editar ${row.nombre}`} onClick={() => openForm(row.form_url)}>
          <i className="fas fa-pen" aria-hidden="true" />
        </button>
      </td>
    </tr>
  );
}

export function Pagination({ page }: { page: Page }) {
  if (!page.has_other_pages) return null;
  const href = (n: number) => `?${page.query_without_page}page=${n}`;
  return (
    <nav className="insp-paginacion" aria-label="Páginas">
      {page.previous !== null ? <a className="insp-pagina" href={href(page.previous)} aria-label="Página anterior">‹</a>
        : <span className="insp-pagina deshabilitada" aria-hidden="true">‹</span>}
      {page.range.map((n, index) => n === "…" ? <span key={`gap-${index}`} className="insp-pagina-puntos" aria-hidden="true">…</span>
        : n === page.number ? <span key={n} className="insp-pagina activa" aria-current="page">{n}</span>
          : <a key={n} className="insp-pagina" href={href(n)}>{n}</a>)}
      {page.next !== null ? <a className="insp-pagina" href={href(page.next)} aria-label="Página siguiente">›</a>
        : <span className="insp-pagina deshabilitada" aria-hidden="true">›</span>}
    </nav>
  );
}

export function InspModal({ id, labelledBy, dialogClass, modalRef, close, children }: {
  id: string; labelledBy: string; dialogClass: string; modalRef: RefObject<HTMLDivElement | null>; close: () => void; children: ReactNode;
}) {
  return (
    <>
      <div className="modal fade show" id={id} tabIndex={-1} aria-labelledby={labelledBy} aria-modal="true" role="dialog" ref={modalRef}
        style={{ display: "block" }} onClick={(event) => { if (event.target === event.currentTarget) close(); }}>
        <div className={dialogClass}>{children}</div>
      </div>
      <div className="modal-backdrop fade show" />
    </>
  );
}

const PASOS = (
  <ol className="insp-pasos" aria-label="Pasos">
    <li className="actual" aria-current="step"><span className="insp-paso-num">1</span>{" Archivo "}</li>
    <li className="insp-paso-linea" aria-hidden="true" />
    <li className=""><span className="insp-paso-num">2</span>{" Revisión "}</li>
    <li className="insp-paso-linea" aria-hidden="true" />
    <li className=""><span className="insp-paso-num">3</span>{" Resultado "}</li>
  </ol>
);

const ESCUELAS_HELP = (
  <p className="small text-muted">
            {"Columnas del padrón oficial: "}<strong>Jurisdicción</strong>{", "}<strong>Localidad</strong>{", "}
            <strong>Cueanexo</strong>{" y "}<strong>Nombre</strong>
            {" (obligatorias), Domicilio, C. P., Teléfono y Mail. Del Excel se lee sólo la primera hoja y el encabezado puede estar después de filas de título. El Cueanexo lleva 9 dígitos: dejá la columna como texto para conservar los ceros iniciales. Una escuela que ya está en el catálogo se actualiza; nada se borra. Antes de guardar vas a ver qué se importa y qué queda a revisar."}
  </p>
);

/** `partials/modal_importar.html` for escuelas: the native multipart POST (IN01). */
export function ImportModal({ action, trigger, close, title = "Importar escuelas", tipo = "escuelas", help = ESCUELAS_HELP }: {
  action: string; trigger: HTMLElement; close: () => void; title?: string; tipo?: string; help?: ReactNode;
}) {
  const modal = useRef<HTMLDivElement>(null);
  const [processing, setProcessing] = useState(false);
  useBootstrapModal(modal, close, trigger);
  return (
    <InspModal id="insp-modal-importar" labelledBy="insp-modal-importar-titulo" dialogClass="modal-dialog modal-lg" modalRef={modal} close={close}>
      <form className="modal-content" method="post" encType="multipart/form-data" action={action} data-insp-procesando="Leyendo el archivo… puede tardar unos segundos."
        onSubmit={() => setProcessing(true)}>
        <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
        <div className="modal-header">
          <h2 className="modal-title h5" id="insp-modal-importar-titulo">{title}</h2>
          <button type="button" className="btn-close" aria-label="Cerrar" onClick={close} />
        </div>
        <div className="modal-body">
          {PASOS}
          {help}
          <label className="form-label" htmlFor={`id_archivo_${tipo}`}>Archivo Excel (.xlsx) o CSV</label>
          <input id={`id_archivo_${tipo}`} className="form-control" type="file" name="archivo" accept=".xlsx,.csv" required />
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-link" onClick={close}>Cancelar</button>
          <button type="submit" className="btn btn-primary" disabled={processing}>Revisar el archivo</button>
        </div>
        {processing && <div className="small text-muted mt-2 px-3 pb-2" role="status">Leyendo el archivo… puede tardar unos segundos.</div>}
      </form>
    </InspModal>
  );
}

type FormState = { url: string; data: EscuelaFormData | null; success: string; revision: number; pending: boolean; uncertain: boolean };

/** `#insp-modal-form`: «Cargando…», then the form; a confirmed save reloads the page. */
function FormModal({ url, close, onForbidden, onLoad }: { url: string; close: () => void; onForbidden: (data: unknown) => void; onLoad: boolean }) {
  const modal = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<FormState>({ url, data: null, success: "", revision: 0, pending: false, uncertain: false });
  useBootstrapModal(modal, close, null, onLoad);
  const load = useCallback((target: string, success: string) => {
    client.get(apiPath(target), { headers: { "X-Requested-With": "XMLHttpRequest" }, validateStatus: accepted }).then(({ data, status }: { data: unknown; status: number }) => {
      if (status === 403) { onForbidden(data); return; }
      if (escuelaFormValid(data)) setState((s) => ({ ...s, url: target, data, success, revision: s.revision + 1, pending: false }));
      else setState((s) => ({ ...s, uncertain: true }));
    }).catch(() => setState((s) => ({ ...s, uncertain: true })));
  }, [onForbidden]);
  useEffect(() => { load(url, ""); }, [load, url]);
  const parent = useCallback(() => modal.current, []);
  const submit = async (body: URLSearchParams) => {
    setState((s) => ({ ...s, pending: true }));
    const outcome = await postEscuela(state.url, body, true);
    if (outcome.kind === "json") {
      if (outcome.otra) load(state.url.split("?")[0], outcome.mensaje); else escuelasNavigation.reload();
    } else if (outcome.kind === "invalid") setState((s) => ({ ...s, data: outcome.data, success: "", revision: s.revision + 1, pending: false }));
    else if (outcome.kind === "forbidden") onForbidden(outcome.data);
    else setState((s) => ({ ...s, uncertain: true }));
  };
  return (
    <InspModal id="insp-modal-form" labelledBy="insp-modal-form-titulo" dialogClass="modal-dialog modal-lg modal-dialog-scrollable" modalRef={modal} close={close}>
      <div className="modal-content" data-insp-modal-contenido="">
        {state.uncertain ? <div className="modal-body" role="alert">No se pudo confirmar el resultado. <a href={PANEL}>Volver al panel</a></div>
          : state.data ? <EscuelaForm key={state.revision} data={state.data} action={state.url} modal={{ parent, close }} success={state.success} pending={state.pending} onSubmit={(body) => void submit(body)} autoFocus />
            : <div className="modal-body text-center text-muted py-5">Cargando…</div>}
      </div>
    </InspModal>
  );
}

function Panel({ data, onForbidden }: { data: EscuelasData; onForbidden: (data: unknown) => void }) {
  const [formUrl, setFormUrl] = useState<string | null>(data.editar_url);
  // `data-insp-abrir-modal`: opened by `panel.js` on load, before AdminLTE finishes.
  const [onLoad, setOnLoad] = useState(data.editar_url !== null);
  const [importTrigger, setImportTrigger] = useState<HTMLElement | null>(null);
  const closeForm = useCallback(() => { setFormUrl(null); setOnLoad(false); }, []);
  const closeImport = useCallback(() => setImportTrigger(null), []);
  return (
    <>
      <Encabezado totales={data.totales} tabs={data.tabs} />
      <section className="insp-seccion">
        <div className="insp-seccion-barra"><Filters data={data} openForm={setFormUrl} openImport={setImportTrigger} /></div>
        {data.results.length ? (
          <div className="table-responsive">
            <table className="table insp-tabla">
              <thead>
                <tr>
                  {["Cueanexo", "Nombre", "Provincia", "Localidad", "Domicilio", "C. P.", "Teléfono", "Mail"].map((h) => <th key={h} scope="col">{h}</th>)}
                  <th scope="col"><span className="visually-hidden">Acciones</span></th>
                </tr>
              </thead>
              <tbody>{data.results.map((row) => <EscuelaRow key={row.id} row={row} openForm={setFormUrl} />)}</tbody>
            </table>
          </div>
        ) : (
          <div className="insp-vacio">
            <i className="fas fa-school" aria-hidden="true" />
            {" "}<strong>No hay escuelas</strong>
            {" "}No hay escuelas que coincidan con la búsqueda o los filtros.
          </div>
        )}
        {data.page.count > 0 && (
          <div className="insp-seccion-pie">
            <span>Mostrando {data.page.start_index}–{data.page.end_index} de {data.page.count}</span>
            {" "}<Pagination page={data.page} />
          </div>
        )}
      </section>
      {importTrigger && <ImportModal action={data.urls.importar} trigger={importTrigger} close={closeImport} />}
      {formUrl && <FormModal url={formUrl} close={closeForm} onForbidden={onForbidden} onLoad={onLoad} />}
      <InspToasts messages={data.messages} />
    </>
  );
}

/** `escuela_form_page.html`: the same form inside `.insp-dialogo`, posted as a page. */
function FormPage({ data, endpoint, onForbidden }: { data: EscuelaFormData; endpoint: string; onForbidden: (data: unknown) => void }) {
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
    const outcome = await postEscuela(endpoint, body, false);
    if (outcome.kind === "redirect") { escuelasNavigation.assign(outcome.to); return; }
    if (outcome.kind === "invalid") setCurrent((s) => ({ data: outcome.data, revision: s.revision + 1, pending: false, uncertain: false }));
    else if (outcome.kind === "forbidden") onForbidden(outcome.data);
    else setCurrent((s) => ({ ...s, pending: false, uncertain: true }));
  };
  return (
    <>
      <Encabezado totales={current.data.totales} tabs={current.data.tabs} />
      <div className="insp-dialogo">
        <EscuelaForm key={current.revision} data={current.data} action={endpoint} modal={null} success="" pending={current.pending} onSubmit={(body) => void submit(body)} autoFocus={false} />
        {current.uncertain && <p role="alert">No se pudo confirmar el resultado. <a href={PANEL}>Volver al panel</a></p>}
      </div>
      <InspToasts messages={current.data.messages} />
    </>
  );
}

export function Screen<T extends { layout: ClaroLayout }>({ state, children, noun = "escuelas", title = "Inspecciones escolares" }: { state: Loaded<T>; children: (data: T) => ReactNode; noun?: string; title?: string }) {
  if (state.status === "loading") return <main role="status">Cargando {noun}…</main>;
  if (state.status === "error") return <main role="alert">No se pudieron cargar las {noun}.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  return (
    <ClaroFrame title={title} user={state.session.user} layout={state.data.layout} navigation={state.session.navigation} footerLabel={state.session.footer_version_label}>
      {children(state.data)}
    </ClaroFrame>
  );
}

export function EscuelasPanelPage() {
  const { state, forbidden } = useScreen(`web/inspecciones/escuelas/${window.location.search}`, escuelasValid);
  return <Screen state={state}>{(data) => <Panel data={data} onForbidden={forbidden} />}</Screen>;
}

export function EscuelaFormPage({ pk }: { pk: number | null }) {
  const endpoint = pk === null ? "/api/web/inspecciones/escuelas/nueva/" : `/api/web/inspecciones/escuelas/${pk}/editar/`;
  const { state, forbidden } = useScreen(apiPath(endpoint), escuelaFormValid);
  return <Screen state={state}>{(data) => <FormPage data={data} endpoint={endpoint} onForbidden={forbidden} />}</Screen>;
}
