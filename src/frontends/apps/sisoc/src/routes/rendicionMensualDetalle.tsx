/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validator and navigation seam are exported for the tests. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { InsumosToastList } from "../InsumosToast";
import { internal, record, text, useMainResource, type MainState } from "./MainFrame";
import SisocShell from "./SisocShell";
import { HITOS_STYLESHEET } from "./userImport";
import type { RouteDefinition } from "./types";

/**
 * RM01.01 detail of a monthly rendición (`rendicioncuentasmensual_detail.html`):
 * header and data card, process actions, audit card, the documentation table with
 * the per-document review and the missing-document requests
 * (`rendicioncuentasmensual_detail.js`) and the asynchronous PDF button
 * (`rendicioncuentasmensual_pdf_descarga.js`). Data comes from
 * `/api/web/comedores/rendicioncuentasmensual/<pk>/`, which runs the native view.
 * Every write is the native POST of the detail URL, sent exactly as the native
 * page sends it (form POST with redirect, or `X-Requested-With` AJAX); the PDF and
 * the documents stay native downloads.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Archivo = {
  id: number; nombre: string; estado: string; badge: string; estado_text: string; observaciones: string;
  fecha: string; visualizado: boolean; visualizacion_title: string; ver_url: string;
};
type ArchivoConHistorial = Archivo & { subsanaciones: Archivo[] };
type Categoria = {
  codigo: string; label: string; required: boolean; historial_plano: boolean;
  solicitud_faltante: { observaciones: string } | null; archivos: ArchivoConHistorial[];
};
type Resumen = { id: number; actual: boolean; titulo: string; documentos: { categoria: string; nombre: string; estado_text: string; ver_url: string }[] };
const CAPABILITIES = [
  "puede_revisar_documentos", "puede_solicitar_faltantes", "puede_revision_territorial", "puede_revision_auditoria", "puede_auditoria",
  "puede_regularizacion", "puede_editar_datos", "puede_gestionar_auditoria", "mostrar_acciones_proceso", "mostrar_documentacion_auditoria",
  "puede_descargar_pdf",
] as const;
type Capabilities = Record<(typeof CAPABILITIES)[number], boolean>;
export type RendicionDetalleData = {
  rendicion: {
    id: number; numero: string; nombre: string; proyecto: string; organizacion: string; convenio: string; linea_programatica: string;
    mes_anio: string; periodo: string; fecha_creacion: string; ultima_modificacion: string; comedores_relacionados: string[];
    usuario_creador: string; usuario_ultima_modificacion: string; observaciones: string; etapa_proceso: string; subestado_proceso: string;
    estado_proceso_display: string; validada: string; genera_acta: boolean; genera_acta_text: string; resultado_auditoria: string;
    acta_auditoria_url: string | null; documento_regularizacion_url: string | null;
  };
  capabilities: Capabilities;
  documentacion: Categoria[];
  resumenes: Resumen[];
  urls: { volver: string; update: string; auditoria: string; pdf_solicitar: string; pdf_estado: string };
  messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const nullableText = (v: unknown) => v === null || text(v);
const archivoValid = (a: unknown): a is Archivo => record(a) && integer(a.id) && ["nombre", "estado", "badge", "estado_text", "observaciones", "fecha", "visualizacion_title"].every((k) => text(a[k])) &&
  typeof a.visualizado === "boolean" && internal(a.ver_url);

export function detalleValid(v: unknown): v is RendicionDetalleData {
  if (!record(v) || !record(v.rendicion) || !record(v.capabilities) || !record(v.urls)) return false;
  const r = v.rendicion, u = v.urls;
  return integer(r.id) &&
    ["numero", "nombre", "proyecto", "organizacion", "convenio", "linea_programatica", "mes_anio", "periodo", "fecha_creacion", "ultima_modificacion", "usuario_creador",
      "usuario_ultima_modificacion", "observaciones", "etapa_proceso", "subestado_proceso", "estado_proceso_display", "validada", "genera_acta_text", "resultado_auditoria"].every((k) => text(r[k])) &&
    Array.isArray(r.comedores_relacionados) && r.comedores_relacionados.every(text) && typeof r.genera_acta === "boolean" &&
    nullableText(r.acta_auditoria_url) && nullableText(r.documento_regularizacion_url) &&
    CAPABILITIES.every((k) => typeof (v.capabilities as Record<string, unknown>)[k] === "boolean") &&
    Array.isArray(v.documentacion) && v.documentacion.every((c) => record(c) && text(c.codigo) && text(c.label) && typeof c.required === "boolean" && typeof c.historial_plano === "boolean" &&
      (c.solicitud_faltante === null || (record(c.solicitud_faltante) && text(c.solicitud_faltante.observaciones))) &&
      Array.isArray(c.archivos) && c.archivos.every((a) => archivoValid(a) && Array.isArray((a as Record<string, unknown>).subsanaciones) && ((a as Record<string, unknown>).subsanaciones as unknown[]).every(archivoValid))) &&
    Array.isArray(v.resumenes) && v.resumenes.every((s) => record(s) && integer(s.id) && typeof s.actual === "boolean" && text(s.titulo) && Array.isArray(s.documentos) &&
      s.documentos.every((d) => record(d) && text(d.categoria) && text(d.nombre) && text(d.estado_text) && internal(d.ver_url))) &&
    ["volver", "update", "auditoria", "pdf_solicitar", "pdf_estado"].every((k) => internal(u[k])) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Full-page navigation (reload after saving a review, PDF download); replaceable in tests. */
export const rendicionDetalleNavigation = {
  assign: (to: string) => window.location.assign(to),
  reload: () => window.location.reload(),
};

const csrf = () => <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;
// The native script sends `X-Requested-With` only; the token travels in the form body.
const AJAX = { "X-Requested-With": "XMLHttpRequest" };

type Feedback = { message: string; kind: "success" | "error" } | null;

/** `setSubmitterLoading`: the button is disabled and its idle label swaps for the spinner. */
function Submit({ loading, className, children }: { loading: boolean; className: string; children: ReactNode }) {
  return (
    <button type="submit" className={className} disabled={loading}>
      <span className={`js-submit-idle${loading ? " d-none" : ""}`}>{children}</span>
      <span className={`spinner-border spinner-border-sm js-submit-spinner${loading ? "" : " d-none"}`} role="status" aria-hidden="true" />
    </button>
  );
}

async function ajaxPost(body: FormData, failure: string) {
  const response = await fetch(window.location.href, { method: "POST", headers: AJAX, body, credentials: "same-origin" });
  let data: Record<string, unknown> = {};
  try {
    const parsed: unknown = await response.json();
    if (record(parsed)) data = parsed;
  } catch {
    data = {};
  }
  if (!response.ok) throw new Error(text(data.message) && data.message ? data.message : failure);
  return data;
}

// --- Process actions --------------------------------------------------------------

function ProcessForm({ action, className, label, button, extra }: { action: string; className?: string; label: string; button: string; extra?: ReactNode }) {
  return (
    <form method="post" className={className} encType={extra ? "multipart/form-data" : undefined}>
      {csrf()}
      <input type="hidden" name="accion_proceso" value={action} />
      {extra}
      <button className={button}>{label}</button>
    </form>
  );
}

function ProcessActions({ data }: { data: RendicionDetalleData }) {
  const { rendicion: r, capabilities: c, urls } = data;
  const etapa = r.etapa_proceso, sub = r.subestado_proceso;
  const iniciable = sub === "pendiente" || sub === "subsanado";
  return (
    <div className="card mb-4">
      <div className="card-body">
        <h5>Acciones del proceso</h5>
        <div className="d-flex flex-wrap gap-2">
          {c.puede_revision_territorial && etapa === "revision_documentacion" && (iniciable
            ? <ProcessForm action="iniciar_revision_territorial" label="Iniciar revisión territorial" button="btn btn-primary" />
            : sub === "en_curso" && <ProcessForm action="finalizar_revision_territorial" label="Finalizar revisión territorial" button="btn btn-success" />)}
          {c.puede_revision_auditoria && etapa === "revision_auditoria" && (iniciable
            ? <ProcessForm action="iniciar_revision_auditoria" label="Iniciar revisión para carga" button="btn btn-primary" />
            : sub === "en_curso" && <ProcessForm action="finalizar_revision_auditoria" label="Finalizar revisión para Carga" button="btn btn-success" />)}
          {c.puede_gestionar_auditoria && <a className="btn btn-primary" href={urls.auditoria}>Gestionar Auditoría</a>}
        </div>
        {c.puede_regularizacion && etapa === "auditoria" && sub === "finalizada_con_observaciones" && (
          <ProcessForm action="iniciar_regularizacion" className="mt-3" label="Iniciar regularización" button="btn btn-primary" />
        )}
        {c.puede_regularizacion && etapa === "regularizacion" && sub === "en_curso" && (
          <ProcessForm action="finalizar_regularizacion" className="mt-3" label="Finalizar regularización" button="btn btn-success" extra={
            <div id="div_id_documento_regularizacion" className="mb-3">
              <label htmlFor="id_documento_regularizacion" className="form-label">Acta Complementaria</label>
              <div><input type="file" name="documento_regularizacion" className="form-control" id="id_documento_regularizacion" /></div>
            </div>} />
        )}
      </div>
    </div>
  );
}

// --- Audit card ---------------------------------------------------------------------

function AuditCard({ data }: { data: RendicionDetalleData }) {
  const r = data.rendicion;
  return (
    <div className="card mb-4">
      <div className="card-body">
        <h5>Auditoría</h5>
        <div className="row gy-3">
          <div className="col-md-4"><small className="text-muted d-block">Validada</small><strong>{r.validada}</strong></div>
          <div className="col-md-4"><small className="text-muted d-block">¿Se genera acta de auditoría?</small><strong>{r.genera_acta_text}</strong></div>
          {r.genera_acta && (
            <>
              <div className="col-md-4"><small className="text-muted d-block">Resultado de la Auditoría</small><strong>{r.resultado_auditoria}</strong></div>
              {r.acta_auditoria_url && <div className="col-md-6"><a href={r.acta_auditoria_url} target="_blank" rel="noopener">Acta de Auditoría</a></div>}
              {r.documento_regularizacion_url && <div className="col-md-6"><a href={r.documento_regularizacion_url} target="_blank" rel="noopener">Acta Complementaria</a></div>}
            </>
          )}
        </div>
        {data.capabilities.mostrar_documentacion_auditoria && (
          <>
            <h6 className="mt-4">Documentación de las rendiciones incluidas</h6>
            {data.resumenes.map((s) => (
              <details key={s.id} className="border rounded p-3 mb-3 js-resumen-rendicion" data-rendicion={s.id} data-actual={s.actual ? "true" : "false"}>
                <summary>{s.titulo}</summary>
                <div className="table-responsive mt-3">
                  <table className="table table-comedor-moderno">
                    <thead><tr><th>Categoría</th><th>Documento</th><th>Estado</th></tr></thead>
                    <tbody>
                      {s.documentos.map((d, i) => (
                        <tr key={i}>
                          <td>{d.categoria}</td>
                          <td><a href={d.ver_url} target="_blank" rel="noopener">{d.nombre}</a></td>
                          <td>{d.estado_text}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

// --- PDF button (`rendicioncuentasmensual_pdf_descarga.js`) ---------------------------

const PDF_INTERVAL_MS = 3000;
const PDF_MAX_POLLS = (15 * 60 * 1000) / PDF_INTERVAL_MS;

function PdfAction({ urls }: { urls: RendicionDetalleData["urls"] }) {
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null);
  const polls = useRef(0);
  const timer = useRef<number | null>(null);
  useEffect(() => () => { if (timer.current !== null) window.clearTimeout(timer.current); }, []);

  async function read(response: Response) {
    let data: Record<string, unknown> = {};
    try {
      const parsed: unknown = await response.json();
      if (record(parsed)) data = parsed;
    } catch {
      data = {};
    }
    if (!response.ok) throw new Error(text(data.mensaje) && data.mensaje ? data.mensaje : "No se pudo generar el PDF.");
    return data;
  }
  function process(data: Record<string, unknown>) {
    if (data.estado === "listo" && text(data.url_descarga) && data.url_descarga) {
      setGenerating(false);
      setMessage({ text: "PDF listo. La descarga comienza en unos segundos.", error: false });
      rendicionDetalleNavigation.assign(data.url_descarga);
      return;
    }
    if (data.estado === "pendiente" || data.estado === "procesando") {
      if (polls.current++ > PDF_MAX_POLLS) throw new Error("La generación del PDF tardó demasiado. Intentá nuevamente.");
      setMessage({ text: "Generando el PDF. Puede tardar unos minutos.", error: false });
      timer.current = window.setTimeout(poll, PDF_INTERVAL_MS);
      return;
    }
    throw new Error(text(data.mensaje) && data.mensaje ? data.mensaje : "No se pudo generar el PDF.");
  }
  function fail(error: unknown) {
    setGenerating(false);
    setMessage({ text: error instanceof Error ? error.message : "No se pudo generar el PDF.", error: true });
  }
  function poll() {
    fetch(urls.pdf_estado, { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" }).then(read).then(process).catch(fail);
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    polls.current = 0;
    setGenerating(true);
    setMessage({ text: "", error: false });
    fetch(urls.pdf_solicitar, { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" }, body: new FormData(event.currentTarget), credentials: "same-origin" })
      .then(read).then(process).catch(fail);
  }
  return (
    <form className="d-inline js-pdf-descarga-form" method="post" action={urls.pdf_solicitar} data-estado-url={urls.pdf_estado} onSubmit={submit}>
      {csrf()}
      <button type="submit" className="btn btn-sm btn-success" disabled={generating}>
        <span className={`js-submit-idle${generating ? " d-none" : ""}`}><i className="fas fa-file-pdf" /> Generar descarga</span>
        <span className={`js-submit-spinner${generating ? "" : " d-none"}`}>
          <span className="spinner-border spinner-border-sm" aria-hidden="true" />{" "}
          Generando PDF…
        </span>
      </button>
      <div className={`small mt-1 js-pdf-descarga-mensaje${message ? (message.error ? " text-danger" : " text-muted") : ""}`} role="status" aria-live="polite">{message?.text ?? ""}</div>
    </form>
  );
}

// --- Documentation table ----------------------------------------------------------------

type Draft = { estado: string; observaciones: string };

function MissingRequest({ categoria, onDone }: { categoria: Categoria; onDone: (message: Feedback, observaciones: string | null) => void }) {
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = new FormData();
    body.set("csrfmiddlewaretoken", leerCookie("csrftoken") ?? "");
    body.set("solicitar_categoria", categoria.codigo);
    body.set("observaciones_faltante", value);
    setLoading(true);
    try {
      const data = await ajaxPost(body, "No se pudo registrar la solicitud.");
      const solicitud = record(data.solicitud) && text(data.solicitud.observaciones) ? data.solicitud.observaciones : "";
      setValue("");
      onDone({ message: text(data.message) ? data.message : "", kind: "success" }, solicitud);
    } catch (error: unknown) {
      onDone({ message: error instanceof Error ? error.message : "No se pudo registrar la solicitud.", kind: "error" }, null);
    } finally {
      setLoading(false);
    }
  }
  return (
    <form method="post" className="d-flex flex-wrap gap-2 align-items-center js-solicitud-faltante-form" data-categoria={categoria.codigo} onSubmit={submit}>
      {csrf()}
      <input type="hidden" name="solicitar_categoria" value={categoria.codigo} />
      <input type="text" name="observaciones_faltante" className="form-control form-control-sm" required placeholder="Observaciones" aria-label="Observaciones para documento faltante"
        value={value} onChange={(e) => setValue(e.target.value)} />
      <Submit loading={loading} className="btn btn-sm btn-outline-danger">Solicitar documento faltante</Submit>
    </form>
  );
}

function ViewCell({ archivo }: { archivo: Archivo }) {
  return (
    <td>
      <div className="comedor-actions">
        <a href={archivo.ver_url} className="btn btn-ver" target="_blank" title="Ver archivo" data-refresh-visualizacion="true">
          <i className="fas fa-eye" />{" "}
          Ver
        </a>{" "}
        {archivo.visualizado
          ? <span className="badge bg-success" title={archivo.visualizacion_title}>Visualizado</span>
          : <span className="badge bg-secondary">Sin visualizar</span>}
      </div>
    </td>
  );
}

/** Row of a historical document (`subsanaciones_historial`); the plain variant is the one of `comprobantes`/`otros`. */
function HistoryRow({ archivo, plain }: { archivo: Archivo; plain: boolean }) {
  return (
    <>
      <tr className={`documento-detail-row${plain ? " historial-documento-row" : ""}`}>
        <td>{archivo.nombre}</td>
        <td id={`estado-cell-${archivo.id}`}>
          {plain ? <span className="historial-documento-estado">{archivo.estado_text}</span> : <span className={`badge-validacion ${archivo.badge}`}>{archivo.estado_text}</span>}
        </td>
        <td id={`revision-cell-${archivo.id}`}>
          {plain && archivo.observaciones
            ? <span className="historial-documento-estado"><strong>Obs:</strong> {archivo.observaciones}</span>
            : <span className="text-muted">-</span>}
        </td>
        <td>{archivo.fecha}</td>
        <ViewCell archivo={archivo} />
      </tr>
      {!plain && archivo.observaciones && (
        <tr id={`observaciones-row-${archivo.id}`} className="documento-detail-row">
          <td colSpan={5} className="text-start pt-0 pb-1 ps-4">
            <div className="ps-3" id={`observaciones-display-${archivo.id}`}><strong>Observaciones:</strong> {archivo.observaciones}</div>
          </td>
        </tr>
      )}
    </>
  );
}

function DocumentRows({ archivo, review, onFeedback }: { archivo: ArchivoConHistorial; review: boolean; onFeedback: (f: Feedback) => void }) {
  const [draft, setDraft] = useState<Draft>(() => {
    const estado = archivo.estado === "validado" || archivo.estado === "subsanar" ? archivo.estado : "";
    // `actualizarFilaRevision` runs on load and clears the text of a state that is not «A subsanar».
    return { estado, observaciones: estado === "subsanar" ? archivo.observaciones : "" };
  });
  const [loading, setLoading] = useState<"inline" | "obs" | null>(null);
  const subsanar = draft.estado === "subsanar";
  const previa = !!archivo.observaciones;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLElement | null;
    const body = new FormData();
    body.set("csrfmiddlewaretoken", leerCookie("csrftoken") ?? "");
    body.set("documento_id", String(archivo.id));
    body.set("estado", draft.estado);
    body.set("observaciones", draft.observaciones.trim());
    setLoading(submitter?.id.startsWith("guardar-revision-observaciones") ? "obs" : "inline");
    try {
      await ajaxPost(body, "No se pudo actualizar el documento.");
      rendicionDetalleNavigation.reload();
    } catch (error: unknown) {
      onFeedback({ message: error instanceof Error ? error.message : "No se pudo actualizar el documento.", kind: "error" });
    } finally {
      setLoading(null);
    }
  }
  const detail = previa || review;
  return (
    <>
      <tr className={detail ? "documento-row-with-details" : ""}>
        <td>{archivo.nombre}</td>
        <td id={`estado-cell-${archivo.id}`}><span className={`badge-validacion ${archivo.badge}`}>{archivo.estado_text}</span></td>
        <td id={`revision-cell-${archivo.id}`}>
          {review ? (
            <>
              <form id={`revision-documento-${archivo.id}`} method="post" onSubmit={submit}>
                {csrf()}
                <input type="hidden" name="documento_id" value={archivo.id} />
              </form>
              <div className="d-flex align-items-center gap-2">
                <select name="estado" form={`revision-documento-${archivo.id}`} className="form-select form-select-sm js-documento-estado" data-documento-id={archivo.id} required
                  value={draft.estado} onChange={(e) => setDraft({ estado: e.target.value, observaciones: e.target.value === "subsanar" ? draft.observaciones : "" })}>
                  <option value="">Seleccionar accion</option>
                  <option value="validado">Validar</option>
                  <option value="subsanar">A subsanar</option>
                </select>
                <button type="submit" form={`revision-documento-${archivo.id}`} id={`guardar-revision-inline-${archivo.id}`}
                  className={`btn btn-success btn-sm js-guardar-revision-inline${draft.estado === "validado" ? "" : " d-none"}`} data-documento-id={archivo.id}
                  title="Guardar revision" aria-label="Guardar revision" disabled={loading === "inline"}>
                  <span className={`js-submit-idle${loading === "inline" ? " d-none" : ""}`}><i className="fas fa-check" /></span>
                  <span className={`spinner-border spinner-border-sm js-submit-spinner${loading === "inline" ? "" : " d-none"}`} role="status" aria-hidden="true" />
                </button>
              </div>
            </>
          ) : <span className="text-muted">-</span>}
        </td>
        <td>{archivo.fecha}</td>
        <ViewCell archivo={archivo} />
      </tr>
      {detail && (
        <tr id={`observaciones-row-${archivo.id}`} className={`documento-detail-row${review && !subsanar && !previa ? " d-none" : ""}`}>
          <td colSpan={5} className="text-start pt-0 pb-1">
            {review ? (
              <>
                {previa && <div className="ps-3" id={`observaciones-display-${archivo.id}`}><strong>Observaciones:</strong> {archivo.observaciones}</div>}
                <div className={`d-flex align-items-start gap-2${subsanar ? "" : " d-none"}`}>
                  <textarea id={`observaciones-${archivo.id}`} name="observaciones" form={`revision-documento-${archivo.id}`}
                    className="documento-observaciones-input form-control form-control-sm js-observaciones-input" data-documento-id={archivo.id} rows={2}
                    placeholder="Observaciones para subsanacion" required={subsanar} value={draft.observaciones}
                    onChange={(e) => setDraft({ ...draft, observaciones: e.target.value })} />
                  <button type="submit" form={`revision-documento-${archivo.id}`} id={`guardar-revision-observaciones-${archivo.id}`}
                    className={`btn btn-success btn-sm js-guardar-revision-observaciones${subsanar ? "" : " d-none"}`} data-documento-id={archivo.id}
                    title="Guardar revision" aria-label="Guardar revision" disabled={loading === "obs"}>
                    <span className={`js-submit-idle${loading === "obs" ? " d-none" : ""}`}><i className="fas fa-check" /></span>
                    <span className={`spinner-border spinner-border-sm js-submit-spinner${loading === "obs" ? "" : " d-none"}`} role="status" aria-hidden="true" />
                  </button>
                </div>
              </>
            ) : <div className="ps-3" id={`observaciones-display-${archivo.id}`}><strong>Observaciones:</strong> {archivo.observaciones}</div>}
          </td>
        </tr>
      )}
    </>
  );
}

function CategoryRows({ categoria, data, onFeedback }: { categoria: Categoria; data: RendicionDetalleData; onFeedback: (f: Feedback) => void }) {
  const [solicitud, setSolicitud] = useState(categoria.solicitud_faltante);
  const review = data.capabilities.puede_revisar_documentos;
  const n = categoria.archivos.length;
  return (
    <>
      <tr className="categoria-documentos-header">
        <td colSpan={5}>
          <div className="d-flex flex-wrap align-items-center justify-content-between gap-2">
            <div className="d-flex flex-wrap align-items-center gap-2">
              <span className="categoria-documentos-titulo">{categoria.label}</span>
              {categoria.required ? <span className="badge bg-warning text-dark">Obligatorio</span> : <span className="badge bg-secondary">Opcional</span>}
            </div>
            <span className="categoria-documentos-meta">{n} archivo{n === 1 ? "" : "s"}</span>
            <span id={`solicitud-faltante-badge-${categoria.codigo}`} className={`badge bg-danger${solicitud ? "" : " d-none"}`}>Documento faltante solicitado</span>
            {data.capabilities.puede_solicitar_faltantes && (
              <MissingRequest categoria={categoria} onDone={(feedback, observaciones) => {
                if (feedback) onFeedback(feedback);
                if (observaciones !== null) setSolicitud({ observaciones });
              }} />
            )}
          </div>
        </td>
      </tr>
      <tr id={`solicitud-faltante-row-${categoria.codigo}`} className={`documento-detail-row${solicitud ? "" : " d-none"}`}>
        <td colSpan={5} className="text-start pt-0 pb-2">
          <div className="ps-3" id={`solicitud-faltante-observacion-${categoria.codigo}`}><strong>Observaciones:</strong> {solicitud?.observaciones ?? ""}</div>
        </td>
      </tr>
      {n > 0 ? (
        <>
          {categoria.archivos.map((a) => <DocumentRows key={a.id} archivo={a} review={review} onFeedback={onFeedback} />)}
          {categoria.archivos.flatMap((a) => a.subsanaciones.map((s) => <HistoryRow key={s.id} archivo={s} plain={categoria.historial_plano} />))}
        </>
      ) : <tr><td colSpan={5}>No hay archivos cargados en esta categoria.</td></tr>}
    </>
  );
}

function Documentation({ data }: { data: RendicionDetalleData }) {
  const [feedback, setFeedback] = useState<Feedback>(null);
  return (
    <div className="card comedor-table-card">
      <div className="card-body">
        <div className="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3">
          <div>
            <h5 className="mb-1">Documentacion asociada</h5>
            <small className="text-muted">
              Cada documento presentado puede validarse o enviarse a subsanacion de forma independiente.
              {data.capabilities.puede_revisar_documentos && " Podés cambiar las selecciones guardadas hasta presionar Finalizar Revisión."}
            </small>
          </div>
        </div>
        <div id="revision-feedback" className={feedback ? `alert mb-3 ${feedback.kind === "error" ? "alert-danger" : "alert-success"}` : "d-none alert mb-3"} role="alert">{feedback?.message ?? ""}</div>
        <div className="table-responsive-lg">
          <table className="table table-comedor-moderno">
            <thead><tr><th>Archivo</th><th>Estado</th><th>Revision</th><th>Fecha</th><th>Acciones</th></tr></thead>
            <tbody>
              {data.documentacion.map((c) => <CategoryRows key={c.codigo} categoria={c} data={data} onFeedback={setFeedback} />)}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/** Reload on coming back from the document viewer (`data-refresh-visualizacion`), unless a review is being edited. */
function useRefreshOnReturn() {
  useEffect(() => {
    let opened = false, left = false;
    const click = (event: MouseEvent) => {
      if (event.target instanceof Element && event.target.closest("a[data-refresh-visualizacion]")) { opened = true; left = false; }
    };
    const unsaved = () => Array.from(document.querySelectorAll<HTMLTextAreaElement>('textarea[name="observaciones"]')).some((t) => t.value.trim() !== "") ||
      Array.from(document.querySelectorAll<HTMLSelectElement>(".js-documento-estado")).some((s) => s.value !== "");
    const leave = () => { if (opened) left = true; };
    const back = () => {
      if (document.visibilityState === "hidden") { leave(); return; }
      if (!left || unsaved()) return;
      opened = false; left = false;
      rendicionDetalleNavigation.reload();
    };
    document.addEventListener("click", click);
    window.addEventListener("blur", leave);
    window.addEventListener("focus", back);
    document.addEventListener("visibilitychange", back);
    return () => {
      document.removeEventListener("click", click);
      window.removeEventListener("blur", leave);
      window.removeEventListener("focus", back);
      document.removeEventListener("visibilitychange", back);
    };
  }, []);
}

export function RendicionDetalleContent({ data }: { data: RendicionDetalleData }) {
  const { rendicion: r, capabilities: c, urls } = data;
  useRefreshOnReturn();
  const badge = r.subestado_proceso === "finalizada" ? "validado" : r.subestado_proceso === "pendiente_correcciones" ? "no-validado" : "pendiente";
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/rendicioncuentasmensual_detail.css" />
      <InsumosToastList messages={data.messages} />
      <div className="comedor-list-container">
        <div className="card mb-4">
          <div className="card-body">
            <div className="d-flex justify-content-between align-items-start flex-wrap gap-3">
              <div>
                <div className="d-flex align-items-center flex-wrap gap-2 mb-2">
                  <h2 className="mb-0 fw-bold">Rendicion {r.numero}</h2>
                  <div className="d-flex flex-wrap gap-2" id="rendicion-estado-badge-container">
                    <span className={`badge-validacion ${badge}`} id="rendicion-estado-badge">{r.estado_proceso_display}</span>
                  </div>
                </div>
              </div>
              <div className="d-flex align-items-center gap-2 flex-wrap">
                {c.puede_editar_datos && <a href={urls.update} className="btn btn-sm btn-warning">Editar Datos de Rendición</a>}
                <div id="rendicion-download-action">{c.puede_descargar_pdf && <PdfAction urls={urls} />}</div>
              </div>
            </div>
            <div className="row mt-4 gy-3">
              <Datum cols="col-12 col-md-6 col-xl-3" label="Nombre de rendición" value={r.nombre} />
              <Datum cols="col-12 col-md-6 col-xl-3" label="Proyecto" value={r.proyecto} />
              <Datum cols="col-12 col-md-6 col-xl-3" label="Organizacion" value={r.organizacion} />
              <Datum cols="col-12 col-md-6 col-xl-3" label="Convenio" value={r.convenio} />
              <Datum cols="col-12 col-md-6 col-xl-3" label="Linea Programatica" value={r.linea_programatica} />
              <Datum cols="col-12 col-md-6 col-xl-3" label="Mes / Ano" value={r.mes_anio} />
              <Datum cols="col-12 col-md-6 col-xl-6" label="Periodo" value={r.periodo} />
              <Datum cols="col-12 col-md-6 col-xl-3" label="Fecha de creacion" value={r.fecha_creacion} />
              <Datum cols="col-12 col-md-6 col-xl-3" label="Ultima modificacion" value={r.ultima_modificacion} />
              <div className="col-12 col-xl-6">
                <small className="text-muted d-block">Comedores relacionados con el proyecto</small>
                {r.comedores_relacionados.length > 0
                  ? <div className="d-flex flex-wrap gap-2 mt-1">{r.comedores_relacionados.map((n, i) => <span key={i} className="badge bg-light text-dark border">{n}</span>)}</div>
                  : <strong>Sin comedores relacionados</strong>}
              </div>
              <Datum cols="col-12 col-md-6 col-xl-3" label="Usuario creador" value={r.usuario_creador} />
              <Datum cols="col-12 col-md-6 col-xl-3" label="Usuario ultima modificacion" value={r.usuario_ultima_modificacion} />
              {r.observaciones && <Datum cols="col-12" label="Observaciones" value={r.observaciones} />}
            </div>
          </div>
        </div>
        {r.subestado_proceso === "pendiente_correcciones" && <div className="alert alert-warning">La rendición tiene documentación pendiente de correcciones.</div>}
        {c.mostrar_acciones_proceso && <ProcessActions data={data} />}
        {(r.etapa_proceso === "auditoria" || r.etapa_proceso === "regularizacion") && <AuditCard data={data} />}
        <Documentation data={data} />
      </div>
    </>
  );
}

function Datum({ cols, label, value }: { cols: string; label: string; value: string }) {
  return <div className={cols}><small className="text-muted d-block">{label}</small><strong>{value}</strong></div>;
}

function AppLoaded() {
  useEffect(() => {
    document.body.classList.add("app-loaded");
    return () => document.body.classList.remove("app-loaded");
  }, []);
  return null;
}

function renderDetalle(state: MainState<RendicionDetalleData>): ReactNode {
  if (state.status === "loading") return <main role="status">Cargando rendición…</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar la página.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  const { data, session } = state;
  // Native `{% block breadcrumb %}`: the link carries its own `title`.
  const breadcrumb = (
    <ol className="breadcrumb float-sm-right">
      <li className="breadcrumb-item"><a href={data.urls.volver} title="Ver listado de rendiciones">Rendiciones</a></li>
      <li className="breadcrumb-item active">Detalle</li>
    </ol>
  );
  return (
    <>
      <SisocShell context={session} content={<>{HITOS_STYLESHEET}<RendicionDetalleContent data={data} /></>} pageTitle="Detalle de Rendicion de Cuenta" heading="" breadcrumb={breadcrumb}
        previewLinks={false} backHref={data.urls.volver} />
      <AppLoaded />
    </>
  );
}

function DetallePage({ pk }: { pk: string }) {
  const [state] = useMainResource(`web/comedores/rendicioncuentasmensual/${pk}/`, detalleValid);
  return <>{renderDetalle(state)}</>;
}

// Native URL of `rendicioncuentasmensual/urls.py` under the runtime's
// `rendicioncuentasmensual/` include (the prefix is repeated on purpose).
const DETALLE = /^\/rendicioncuentasmensual\/rendicioncuentasmensual\/detalle\/([0-9]+)\/$/;

export const rendicionMensualDetalleRoute: RouteDefinition<{ pk: string }> = {
  name: "comedores-rendicion-mensual-detalle",
  match(pathname) {
    const found = DETALLE.exec(pathname);
    return found ? { pk: found[1] } : null;
  },
  render(params) {
    return <DetallePage pk={params.pk} />;
  },
};
