/* eslint-disable react-refresh/only-export-components -- the unit surface is this module: types, validation, cards and modals of the ficha lower block. */
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { NativeModal, NativeToasts } from "./nativeParity";
import { accepted, internal, record, text, webClient } from "./MainFrame";
import { guardarRechazo } from "./comedorFichaRechazo";
import { useBodyLock } from "./comedorFichaModal";

/**
 * CO07.01 ficha, the «Nómina» card and the «Intervenciones / Observaciones» tabs card of
 * `comedor_detail.html`: the `nomina`, `intervenciones` and `observaciones` keys of the ficha API.
 * The two creation modals post (multipart / form) to the web APIs of the native create views, whose
 * `{ok, redirect}` answer ends in the same full-page navigation to the ficha as the native 302.
 * A rejected post ends where the native one does: the create page (`modal.formulario`) with the posted
 * values and the errors (see `comedorFichaRechazo`). The import form of the nómina card stays a native
 * form POST (`nomina_importar`).
 */
type Cell = { texto?: string; insignia?: string; acciones?: { url: string; clase: string; nueva_ventana: boolean; label: string }[] };
type Pager = { param: string; anterior: number | null; siguiente: number | null; paginas: ({ ellipsis: true } | { numero: number; activa: boolean })[] } | null;
type Tabla = { encabezados: string[]; filas: Cell[][]; paginacion: Pager; resultados: number };
type Select = { id: string; label: string; required: boolean; options: { value: string; label: string }[] };
type Basic = { id: string; label: string; required: boolean };
export type Nomina = {
  ver: string | null; pendiente: boolean; importar: string | null; directa: boolean;
  cifras: { asistentes: string; hombres: string; mujeres: string; menores: string; espera: string; bajas: string };
};
export type Intervenciones = Tabla & {
  convenios: { id: number; texto: string; cerrada: boolean; seleccionada: boolean }[];
  modal: {
    crear: string; formulario: string; subestados: string; next: string; admision_id: number | null; fecha: Basic; tipo_intervencion: Select; subintervencion: Select;
    destinatario: Select; forma_contacto: Select; observaciones: Basic; tiene_documentacion: { id: string; label: string }; documentacion: { id: string; label: string };
  };
};
export type Observaciones = Tabla & { modal: { crear: string; formulario: string; next: string; campo: Basic & { rows: number; placeholder: string } } };
export type Relaciones = { nomina: Nomina; intervenciones: Intervenciones; observaciones: Observaciones };

const strs = (v: unknown, keys: string[]) => record(v) && keys.every((k) => typeof v[k] === "string");
const tablaValid = (v: unknown) => record(v) && Array.isArray(v.encabezados) && v.encabezados.every(text) && Array.isArray(v.filas) &&
  v.filas.every((f) => Array.isArray(f) && f.every((c) => record(c) && (c.acciones === undefined || (Array.isArray(c.acciones) && c.acciones.every((a) => record(a) && internal(a.url) && text(a.label)))))) &&
  Number.isSafeInteger(v.resultados) && (v.paginacion === null || (record(v.paginacion) && text(v.paginacion.param) && Array.isArray(v.paginacion.paginas)));

export function relacionesValid(v: Record<string, unknown>): boolean {
  const n = v.nomina, i = v.intervenciones, o = v.observaciones;
  return record(n) && (n.ver === null || internal(n.ver)) && (n.importar === null || internal(n.importar)) && typeof n.pendiente === "boolean" && typeof n.directa === "boolean" &&
    strs(n.cifras, ["asistentes", "hombres", "mujeres", "menores", "espera", "bajas"]) &&
    tablaValid(i) && Array.isArray((i as Record<string, unknown>).convenios) && record((i as Record<string, unknown>).modal) && internal(((i as Record<string, unknown>).modal as Record<string, unknown>).crear) && internal(((i as Record<string, unknown>).modal as Record<string, unknown>).formulario) &&
    tablaValid(o) && record((o as Record<string, unknown>).modal) && internal(((o as Record<string, unknown>).modal as Record<string, unknown>).crear) && internal(((o as Record<string, unknown>).modal as Record<string, unknown>).formulario);
}

/** Full-page navigation after a created record (the native 302); replaceable in tests. */
export const relacionesNavigation = { assign: (to: string) => window.location.assign(to) };
const apiPath = (url: string) => url.replace(/^\/api\//, "");

// --- Nómina card ------------------------------------------------------------------------------

const BOXES: [keyof Nomina["cifras"], string, string, string][] = [
  ["asistentes", "amarillo", "bi-people-fill", "Asistentes"], ["hombres", "celeste", "bi-person-standing", "Hombres"], ["mujeres", "rosa", "bi-person-standing-dress", "Mujeres"],
  ["menores", "verde", "bi-person-arms-up", "Menores de edad"], ["espera", "rojo", "bi-list-check", "Lista de espera"], ["bajas", "gris", "bi-person-dash-fill", "Dados de baja"],
];

export function NominaCard({ data }: { data: Nomina }) {
  return (
    <div className="col-12 col-lg-3">
      <div className="card bg-card">
        <div className="card-header py-1 d-flex align-items-center justify-content-between">
          <h4 className="fw-bold my-1">Nómina</h4>
          {data.ver && <a href={data.ver} className="btn btn-success btn-sm ms-auto"><i className="bi bi-people-fill me-1" />Ver nómina</a>}
        </div>
        <div className="card-body">
          {data.pendiente && <div className="alert alert-warning py-1 px-2 mb-2 small"><i className="bi bi-exclamation-triangle me-1" />{" "}Nómina pendiente de presentación.</div>}
          {data.importar ? (
            <form method="post" action={data.importar} className="mb-2">
              <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
              <button type="submit" className="btn btn-sm btn-outline-light w-100" title="Importar nómina del convenio anterior"><i className="bi bi-clipboard-plus me-1" />Importar del convenio anterior</button>
            </form>
          ) : data.directa && <div className="alert alert-info py-1 px-2 mb-2 small"><i className="bi bi-info-circle me-1" />{" "}Este comedor usa nómina directa y no depende de admisiones.</div>}
          {BOXES.map(([key, color, icon, label]) => (
            <div className="col-12" key={key}>
              <div className={`d-flex align-items-center bg-${color} px-3 py-2 rounded-3 mb-2`}>
                <div className={`d-flex align-items-center justify-content-center bg-${color}-75 text-white rounded-circle mx-2 me-3 comedor-icon-60`}><i className={`bi ${icon} fs-1`} /></div>
                <div><div className="fw-bold fs-2 mb-0 py-0 text-white">{data.cifras[key]}</div><p className="mb-0 text-white fw-bold">{label}</p></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// --- data_table.html + pagination.html ----------------------------------------------------------

function pageHref(param: string, page: number) {
  const rest = new URLSearchParams();
  new URLSearchParams(window.location.search).forEach((value, key) => { if (key !== param && key !== "busqueda") rest.append(key, value); });
  const base = rest.toString();
  return `?${base ? `${base}&` : ""}${param}=${page}`;
}

function Pager({ pager, resultados, vacia }: { pager: Pager; resultados: number; vacia: boolean }) {
  return (
    <div className="mt-2">
      {pager && (
        <ul className="pagination">
          <li className={`page-item${pager.anterior ? "" : " disabled"}`}><a href={pager.anterior ? pageHref(pager.param, pager.anterior) : "#"} className="page-link">Volver</a></li>
          {pager.paginas.map((p, i) => ("ellipsis" in p
            ? <li key={`e${i}`} className="page-item disabled"><a href="#" className="page-link">...</a></li>
            : <li key={p.numero} className={`page-item ${p.activa ? "active" : ""}`}><a href={pageHref(pager.param, p.numero)} className="page-link">{p.numero}</a></li>))}
          <li className={`page-item${pager.siguiente ? "" : " disabled"}`}><a href={pager.siguiente ? pageHref(pager.param, pager.siguiente) : "#"} className="page-link">Continuar</a></li>
        </ul>
      )}
      {/* An empty `Page` is falsy for the template `{% if page_obj %}`: no count under an empty table. */}
      {!vacia && <p className="text-center text-muted mb-0 mt-1">Se encontraron {resultados} resultados</p>}
    </div>
  );
}

function CellContent({ c }: { c: Cell }) {
  if (c.acciones) {
    return <>{c.acciones.map((a, i) => (
      <span key={a.url}>{i > 0 && " "}<a href={a.url} className={a.clase} {...(a.nueva_ventana ? { target: "_blank", rel: "noopener" } : {})}>{a.label}</a></span>
    ))}</>;
  }
  if (c.insignia) return <span className={`badge ${c.insignia}`}>{c.texto}</span>;
  return <>{c.texto}</>;
}

function Tabla({ t, empty, tableClass }: { t: Tabla; empty: string; tableClass: string }) {
  return (
    <div className="row mt-5 max-width-100">
      <div className="col-12">
        <div className="card">
          <div className="card-body">
            <div className="table-responsive-lg">
              <table className={`table table-bordered table-striped projects ${tableClass}`}>
                <thead><tr>{t.encabezados.map((h) => <th key={h}>{h}</th>)}</tr></thead>
                <tbody>
                  {t.filas.length ? t.filas.map((fila, i) => <tr key={i}>{fila.map((c, j) => <td key={j}><CellContent c={c} /></td>)}</tr>)
                    : <tr><td colSpan={t.encabezados.length} className="text-center text-muted py-4">{empty}</td></tr>}
                </tbody>
              </table>
            </div>
            <Pager pager={t.paginacion} resultados={t.resultados} vacia={t.filas.length === 0} />
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Modals ---------------------------------------------------------------------------------------

// Hidden inputs (csrf, next) are never focusable: as the first control they would break the Tab wrap.
const MODAL_CONTROLS = "button:not([disabled]),input:not([disabled]):not([type=hidden]),select:not([disabled]),textarea:not([disabled])";
const FAILED = (what: string) => ({ message: `No se pudo guardar ${what}. Revisá los datos e intentá de nuevo.`, level: "error" as const });
const BLANK_SUB = { value: "", label: "Seleccione una opción" };

async function enviar(url: string, formulario: string, form: HTMLFormElement): Promise<"redirigido" | "rechazado" | "incierto"> {
  try {
    const { data, status } = await webClient.post(apiPath(url), new FormData(form), { validateStatus: (code: number) => accepted(code) || code === 400 });
    if (status === 200 && record(data) && data.ok === true && internal(data.redirect)) { relacionesNavigation.assign(data.redirect); return "redirigido"; }
    // The native rejection re-renders the create form: hand its payload to the create page.
    if (status === 400 && record(data) && guardarRechazo(apiPath(url), data)) { relacionesNavigation.assign(formulario); return "redirigido"; }
    return status === 400 || status === 403 ? "rechazado" : "incierto";
  } catch { return "incierto"; }
}

function SelectInput({ f, name, options }: { f: Select; name: string; options: { value: string; label: string }[] }) {
  return <select className="form-control" name={name} id={f.id} required={f.required || undefined}>{options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>;
}

function IntervencionModal({ m, close }: { m: Intervenciones["modal"]; close: () => void }) {
  useBodyLock();
  const [busy, setBusy] = useState(false);
  const [toasts, setToasts] = useState<{ message: string; level: "error" }[]>([]);
  const [fechaError, setFechaError] = useState("");
  const [archivo, setArchivo] = useState(false);
  const [subs, setSubs] = useState([BLANK_SUB]);
  const inFlight = useRef(false);

  function loadSubs(tipo: string) {
    setSubs([BLANK_SUB]);
    if (!tipo) return;
    webClient.get(apiPath(m.subestados), { params: { id: tipo } }).then(({ data }: { data: unknown }) => {
      if (!Array.isArray(data)) return;
      setSubs([BLANK_SUB, ...data.filter((r) => record(r) && Number.isSafeInteger(r.id) && text(r.text)).map((r) => ({ value: String(r.id), label: String(r.text) }))]);
    }).catch(() => undefined);
  }
  function validarFecha(input: HTMLInputElement) {
    if (!input.value) { setFechaError(""); return true; }
    const year = new Date(input.value).getFullYear();
    if (year < 2000 || year > 2100) { setFechaError("El año de la fecha debe estar entre 2000 y 2100."); return false; }
    setFechaError(""); return true;
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const fecha = form.querySelector<HTMLInputElement>(`#${m.fecha.id}`);
    if ((fecha && !validarFecha(fecha)) || inFlight.current) return;
    inFlight.current = true; setBusy(true); setToasts([]);
    const resultado = await enviar(m.crear, m.formulario, form);
    if (resultado !== "redirigido") { setToasts([FAILED("la intervención")]); inFlight.current = false; setBusy(false); }
  }
  return (
    <>
      {toasts.length > 0 && <NativeToasts messages={toasts} />}
      <NativeModal id="modalIntervencion" title="Nueva intervención" close={close} busy={busy} size=" modal-lg modal-dialog-centered" controls={MODAL_CONTROLS}>
        <div className="modal-content">
          <form method="POST" action="" encType="multipart/form-data" id="intervencionModalForm" onSubmit={(e) => void submit(e)}>
            <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
            <input type="hidden" name="next" value={m.next} />
            {m.admision_id !== null && <input type="hidden" name="admision_id" value={m.admision_id} />}
            <div className="modal-header">
              <h5 className="modal-title" id="modalIntervencionLabel">Nueva intervención</h5>
              <button type="button" className="btn-close" aria-label="Close" onClick={close} disabled={busy} />
            </div>
            <div className="modal-body">
              <div className="row g-3">
                <div className="col-md-6">
                  <label htmlFor={m.fecha.id} className="form-label">{m.fecha.label}</label>
                  <input type="date" className={`form-control${fechaError ? " is-invalid" : ""}`} name="fecha" required={m.fecha.required || undefined} id={m.fecha.id}
                    onChange={(e) => validarFecha(e.currentTarget)} onBlur={(e) => validarFecha(e.currentTarget)} />
                  <div id="fecha-error-intervencion" className={`invalid-feedback${fechaError ? "" : " d-none"}`}>{fechaError}</div>
                </div>
                <div className="col-md-6">
                  <label htmlFor={m.tipo_intervencion.id} className="form-label">{m.tipo_intervencion.label}</label>
                  <select className="form-control" name="tipo_intervencion" id={m.tipo_intervencion.id} required={m.tipo_intervencion.required || undefined} defaultValue="" onChange={(e) => loadSubs(e.currentTarget.value)}>
                    {m.tipo_intervencion.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
                <div className="col-md-6">
                  <label htmlFor={m.subintervencion.id} className="form-label">{m.subintervencion.label}</label>
                  <SelectInput f={m.subintervencion} name="subintervencion" options={subs} />
                </div>
                <div className="col-md-6">
                  <label htmlFor={m.destinatario.id} className="form-label">{m.destinatario.label}</label>
                  <SelectInput f={m.destinatario} name="destinatario" options={m.destinatario.options} />
                </div>
                <div className="col-md-6">
                  <label htmlFor={m.forma_contacto.id} className="form-label">{m.forma_contacto.label}</label>
                  <SelectInput f={m.forma_contacto} name="forma_contacto" options={m.forma_contacto.options} />
                </div>
                <div className="col-12">
                  <label htmlFor={m.observaciones.id} className="form-label">{m.observaciones.label}</label>
                  <textarea name="observaciones" cols={40} rows={4} className="form-control" id={m.observaciones.id} required={m.observaciones.required || undefined} />
                </div>
                <div className="col-12">
                  <div className="form-check">
                    <input type="checkbox" name="tiene_documentacion" id={m.tiene_documentacion.id} onChange={(e) => setArchivo(e.currentTarget.checked)} />{" "}
                    <label className="form-check-label" htmlFor={m.tiene_documentacion.id}>{m.tiene_documentacion.label}</label>
                  </div>
                </div>
                <div className={`col-12${archivo ? "" : " d-none"}`} id="documentacion-field-modal">
                  <label htmlFor={m.documentacion.id} className="form-label">{m.documentacion.label}</label>
                  <input type="file" name="documentacion" className="form-control" id={m.documentacion.id} />
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={close} disabled={busy}>Cancelar</button>{" "}
              <button type="submit" className="btn btn-primary" disabled={busy}>Guardar intervención</button>
            </div>
          </form>
        </div>
      </NativeModal>
    </>
  );
}

function ObservacionModal({ m, close }: { m: Observaciones["modal"]; close: () => void }) {
  useBodyLock();
  const [busy, setBusy] = useState(false);
  const [toasts, setToasts] = useState<{ message: string; level: "error" }[]>([]);
  const inFlight = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setToasts([]);
    const resultado = await enviar(m.crear, m.formulario, event.currentTarget);
    if (resultado !== "redirigido") { setToasts([FAILED("la observación")]); inFlight.current = false; setBusy(false); }
  }
  const c = m.campo;
  return (
    <>
      {toasts.length > 0 && <NativeToasts messages={toasts} />}
      <NativeModal id="modalObservacion" title="Nueva observación" close={close} busy={busy} size=" modal-dialog-centered" controls={MODAL_CONTROLS}>
        <div className="modal-content">
          <form method="POST" action="" id="observacionModalForm" onSubmit={(e) => void submit(e)}>
            <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
            <input type="hidden" name="next" value={m.next} />
            <div className="modal-header">
              <h5 className="modal-title" id="modalObservacionLabel">Nueva observación</h5>
              <button type="button" className="btn-close" aria-label="Close" onClick={close} disabled={busy} />
            </div>
            <div className="modal-body">
              <div className="mb-3">
                <label htmlFor={c.id} className="form-label">{c.label}</label>
                <textarea name="observacion" cols={40} rows={c.rows} className="form-control" placeholder={c.placeholder} required={c.required || undefined} id={c.id} />
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={close} disabled={busy}>Cancelar</button>{" "}
              <button type="submit" className="btn btn-primary" disabled={busy}>Guardar observación</button>
            </div>
          </form>
        </div>
      </NativeModal>
    </>
  );
}

// --- Tabs card ----------------------------------------------------------------------------------

export type RelacionesModal = "intervencion" | "observacion" | null;

export function IntervencionesObservaciones({ i, o, onModal }: { i: Intervenciones; o: Observaciones; onModal: (m: RelacionesModal) => void }) {
  const [tab, setTab] = useState<"intervenciones" | "observaciones">("intervenciones");
  const setModal = onModal;
  const nav = (id: "intervenciones" | "observaciones", label: string): ReactNode => (
    <li className="nav-item" role="presentation">
      <button className={`nav-link${tab === id ? " active" : ""} fs-6`} id={`${id}-tab`} type="button" role="tab" aria-controls={`${id}-pane`} aria-selected={tab === id} onClick={() => setTab(id)}>{label}</button>
    </li>
  );
  return (
    <>
      <div className="row mb-3 mt-5">
        <div className="col-12 tabs-comedor-wrap">
          <ul className="nav nav-tabs tabs-comedor ms-2 mb-0" id="intervencionesObservacionesTabs" role="tablist">
            {nav("intervenciones", "Intervenciones")}
            {nav("observaciones", "Observaciones")}
          </ul>
          <div className="card bg-card">
            <div className="card-body pt-0">
              <div className="tab-content" id="intervencionesObservacionesContent">
                <div className={`tab-pane fade${tab === "intervenciones" ? " show active" : ""}`} id="intervenciones-pane" role="tabpanel" aria-labelledby="intervenciones-tab">
                  <div className="d-flex align-items-center gap-2 mb-3 flex-wrap">
                    {i.convenios.length > 0 && (
                      <>
                        <span className="fw-bold text-muted small"><i className="fas fa-file-contract me-1" />Convenio:</span>
                        {i.convenios.map((c) => (
                          <a key={c.id} href={`?admision_id=${c.id}#intervenciones-tab`} className={`btn btn-sm ${c.seleccionada ? "btn-primary" : "btn-outline-secondary"}`}>
                            {c.texto}{c.cerrada && <>{" "}<span className="badge bg-secondary ms-1">Cerrada</span></>}
                          </a>
                        ))}
                      </>
                    )}
                    <button type="button" className="btn btn-sm btn-primary ms-auto" onClick={() => setModal("intervencion")}>Agregar intervención</button>
                  </div>
                  <Tabla t={i} empty="Aún no se han registrado intervenciones." tableClass="table-sm table-compact" />
                </div>
                <div className={`tab-pane fade${tab === "observaciones" ? " show active" : ""}`} id="observaciones-pane" role="tabpanel" aria-labelledby="observaciones-tab">
                  <div className="d-flex justify-content-end mb-2">
                    <button type="button" className="btn btn-sm btn-primary" onClick={() => setModal("observacion")}>Agregar observación</button>
                  </div>
                  <Tabla t={o} empty="Sin observaciones registradas." tableClass="table-sm table-compact" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

/** The modals sit where the template declares them: after the cards, before the admission and validation modals. */
export function RelacionesModales({ i, o, modal, close }: { i: Intervenciones; o: Observaciones; modal: RelacionesModal; close: () => void }) {
  return (
    <>
      {modal === "intervencion" && <IntervencionModal m={i.modal} close={close} />}
      {modal === "observacion" && <ObservacionModal m={o.modal} close={close} />}
    </>
  );
}
