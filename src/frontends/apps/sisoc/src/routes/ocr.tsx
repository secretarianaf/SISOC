/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { InsumosToastList } from "../InsumosToast";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * OCR01.01 upload (`ocr/ocr_upload.html`) and OCR01.02 batch detail
 * (`ocr/ocr_job_detail.html`). Data comes from `/api/web/ocr/`, which reuses the
 * native form and `create_ocr_job`; the text download stays the native GET.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Option = { name: string; label: string; help_text: string; initial: boolean };
type Recent = { id: number; requested_at: string; status: string; processed_documents: number; total_documents: number; detail_url: string };
export type UploadData = { max_file_size_mb: number; allowed_extensions: string[]; options: Option[]; recent_jobs: Recent[]; messages: Message[] };
type Doc = {
  id: number; original_filename: string; status: string; page_count: number | null; file_size_label: string; extracted_text: string;
  error_message: string; processed_at: string; download_url: string | null;
};
export type JobData = {
  id: number; requested_at: string; status: string; total_documents: number; processed_documents: number; failed_documents: number;
  last_error_message: string; options: { preprocess: boolean; pdf_text_layer: boolean; auto_orient: boolean }; documents: Doc[];
  upload_url: string; messages: Message[];
};

const UPLOAD = "/ocr/";
const API = "web/ocr/";
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const bool = (v: unknown): v is boolean => typeof v === "boolean";
const messagesValid = (v: unknown) => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && ["success", "error", "warning", "info"].includes(m.level as string));

export function uploadValid(v: unknown): v is UploadData {
  return record(v) && integer(v.max_file_size_mb) && Array.isArray(v.allowed_extensions) && v.allowed_extensions.every(text) &&
    Array.isArray(v.options) && v.options.every((o) => record(o) && text(o.name) && text(o.label) && text(o.help_text) && bool(o.initial)) &&
    Array.isArray(v.recent_jobs) && v.recent_jobs.every((j) => record(j) && integer(j.id) && text(j.requested_at) && text(j.status) &&
      integer(j.processed_documents) && integer(j.total_documents) && internal(j.detail_url)) && messagesValid(v.messages);
}

export function jobValid(v: unknown): v is JobData {
  return record(v) && integer(v.id) && text(v.requested_at) && text(v.status) && integer(v.total_documents) && integer(v.processed_documents) &&
    integer(v.failed_documents) && text(v.last_error_message) && record(v.options) && bool(v.options.preprocess) && bool(v.options.pdf_text_layer) &&
    bool(v.options.auto_orient) && internal(v.upload_url) && messagesValid(v.messages) &&
    Array.isArray(v.documents) && v.documents.every((d) => record(d) && integer(d.id) && text(d.original_filename) && text(d.status) &&
      (d.page_count === null || integer(d.page_count)) && text(d.file_size_label) && text(d.extracted_text) && text(d.error_message) &&
      text(d.processed_at) && (d.download_url === null || internal(d.download_url)));
}

const STATUS: Record<string, [string, string]> = {
  completed: ["Completado", "success"], completed_with_errors: ["Completado con errores", "warning"], failed: ["Fallido", "danger"], processing: ["Procesando", "warning"],
};
const DOC_STATUS: Record<string, [string, string]> = {
  completed: ["Completado", "success"], no_text: ["Sin texto", "warning"], failed: ["Error", "danger"], processing: ["Procesando", "warning"],
};
function Badge({ map, status }: { map: Record<string, [string, string]>; status: string }) {
  const [label, tone] = map[status] ?? ["Pendiente", "secondary"];
  return <span className={`badge badge-${tone}`}>{label}</span>;
}

const MODEL_ERROR = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";

function UploadForm({ data }: { data: UploadData }) {
  const [files, setFiles] = useState<File[]>([]);
  const [checked, setChecked] = useState<Record<string, boolean>>(Object.fromEntries(data.options.map((o) => [o.name, o.initial])));
  const [errors, setErrors] = useState<string[]>([]);
  const [sending, setSending] = useState(false);
  const busy = useRef(false);

  async function send(event: FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true;
    setSending(true);
    const body = new FormData();
    files.forEach((f) => body.append("archivos", f));
    data.options.forEach((o) => { if (checked[o.name]) body.append(o.name, "on"); });
    try {
      const { data: reply, status } = await webClient.post(`${API}lotes/`, body, { validateStatus: () => true });
      if (status === 201 && record(reply) && internal(reply.detail_url)) {
        window.location.assign(reply.detail_url);
        return;
      }
      if (status === 400 && record(reply) && record(reply.errors)) {
        setErrors(Object.values(reply.errors).flatMap((m) => (Array.isArray(m) ? m.filter(text) : [])));
      } else setErrors([MODEL_ERROR]);
    } catch {
      setErrors([MODEL_ERROR]);
    }
    busy.current = false;
    setSending(false);
  }

  return <>
    {errors.length > 0 && <div className="alert alert-danger" role="alert">{errors.map((m, i) => <div key={i}>{m}</div>)}</div>}
  <form method="post" encType="multipart/form-data" noValidate onSubmit={(e) => void send(e)}>
    <div className="mb-3">
      <label htmlFor="id_archivos" className="form-label fw-bold">Archivos</label>
      <input type="file" name="archivos" id="id_archivos" multiple accept=".jpg,.jpeg,.png,.pdf" className={`form-control ${errors.length ? "is-invalid" : ""}`}
        onChange={(e) => setFiles([...(e.target.files ?? [])])} />
      <div className="form-text text-muted">{files.length === 0 ? "Puede seleccionar varios archivos a la vez." : files.length === 1 ? "1 archivo seleccionado" : `${files.length} archivos seleccionados`}</div>
    </div>
    <div className="mb-3">
      <label className="form-label fw-bold">Opciones de calidad</label>
      <p className="form-text text-muted mt-0">Activadas por defecto (mejor calidad). Desactivar una opción puede <strong>degradar</strong> el resultado del OCR.</p>
      {data.options.map((o) => <div key={o.name} className="form-check form-switch mb-2">
        <input type="checkbox" name={o.name} id={`id_${o.name}`} className="form-check-input" role="switch" checked={checked[o.name]}
          onChange={(e) => setChecked((c) => ({ ...c, [o.name]: e.target.checked }))} />{" "}
        <label className="form-check-label" htmlFor={`id_${o.name}`}>{o.label}</label>
        <div className="form-text text-muted">{o.help_text}</div>
      </div>)}
    </div>
    <div className="d-flex flex-wrap gap-2">
      <button type="submit" className="btn btn-success" disabled={sending}>Procesar archivos</button>
      <a href="/" className="btn btn-secondary">Volver</a>
    </div>
  </form></>;
}

function Recents({ jobs }: { jobs: Recent[] }) {
  if (!jobs.length) return <><hr className="my-4" /><div className="alert alert-light border mb-0">Todavía no hay lotes OCR creados.</div></>;
  return <>
    <hr className="my-4" />
    <h4 className="mb-3">Últimos lotes</h4>
    <div className="table-responsive">
      <table className="table table-bordered table-hover align-middle mb-0">
        <thead><tr><th scope="col">Lote</th><th scope="col">Fecha</th><th scope="col">Estado</th><th scope="col">Archivos</th><th scope="col">Detalle</th></tr></thead>
        <tbody>{jobs.map((j) => <tr key={j.id}>
          <td>#{j.id}</td><td>{j.requested_at}</td><td><Badge map={STATUS} status={j.status} /></td>
          <td>{j.processed_documents}/{j.total_documents}</td>
          <td><a href={j.detail_url} className="btn btn-sm btn-outline-primary">Ver detalle</a></td>
        </tr>)}</tbody>
      </table>
    </div>
  </>;
}

function UploadPage() {
  const [state] = useMainResource(`${API}carga/`, uploadValid);
  return renderMain(state, "Cargando…", (data) => ({
    title: "OCR", heading: "OCR",
    breadcrumb: <ol className="breadcrumb float-sm-right"><li className="breadcrumb-item">Administración</li><li className="breadcrumb-item active">OCR</li></ol>,
    content: <div className="row justify-content-center"><div className="col-12 col-lg-8"><div className="card shadow-sm">
      <InsumosToastList messages={data.messages} />
      <div className="card-header"><h3 className="mb-0">Extracción de texto (OCR)</h3></div>
      <div className="card-body">
        <p className="text-muted">Cargue uno o varios archivos para extraer su texto automáticamente. El procesamiento se ejecuta en segundo plano. Puede consultar el resultado desde la pantalla de detalle del lote.</p>
        <div className="alert alert-light border">
          <div className="font-weight-bold mb-2">Formatos admitidos</div>
          <ul className="mb-0 pl-3">
            <li><strong>Imágenes:</strong> JPG, JPEG, PNG</li>
            <li><strong>Documentos:</strong> PDF (incluye multipágina y escaneos)</li>
          </ul>
        </div>
        <div className="alert alert-info">
          <div className="font-weight-bold mb-2">Consideraciones</div>
          <ul className="mb-0 pl-3">
            <li>El texto se extrae en idioma español por defecto.</li>
            <li>Los archivos se eliminan del servidor una vez procesados.</li>
            <li>Si una imagen está en blanco o es ilegible, se informará sin error.</li>
            <li>Tamaño máximo por archivo: {data.max_file_size_mb} MB.</li>
          </ul>
        </div>
        <UploadForm data={data} />
        <Recents jobs={data.recent_jobs} />
      </div>
    </div></div></div>,
  }));
}

function DocText({ doc }: { doc: Doc }) {
  const [open, setOpen] = useState(false);
  return <div>
    <pre id={`texto-doc-${doc.id}`} className="ocr-text-preview mb-2"
      style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: "0.875rem", maxHeight: open ? "none" : "200px", overflowY: "auto", background: "var(--bs-body-bg)", border: "1px solid var(--bs-border-color)", borderRadius: "4px", padding: "0.75rem" }}>{doc.extracted_text}</pre>
    <button type="button" className="btn btn-sm btn-link p-0 text-muted" onClick={() => setOpen(!open)}>{open ? "Colapsar texto" : "Ver texto completo"}</button>
  </div>;
}

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => window.alert("No se pudo copiar el texto. Selecciónelo manualmente."));
  }
  return <button type="button" className="btn btn-sm btn-outline-secondary" title="Copiar texto extraído" disabled={copied} onClick={copy}>{copied ? "¡Copiado!" : "Copiar"}</button>;
}

function DocCard({ doc }: { doc: Doc }) {
  const hasText = doc.status === "completed" && !!doc.extracted_text;
  return <div className="card mb-3 border">
    <div className="card-header d-flex flex-wrap justify-content-between align-items-center gap-2 py-2">
      <div className="d-flex align-items-center gap-2 flex-wrap">
        <strong className="text-break">{doc.original_filename}</strong>{" "}
        <Badge map={DOC_STATUS} status={doc.status} />
        {!!doc.page_count && <span className="text-muted small">{doc.page_count} página{doc.page_count === 1 ? "" : "s"}</span>}
        {doc.file_size_label && <span className="text-muted small">{doc.file_size_label}</span>}
      </div>
      {hasText && <div className="d-flex gap-2">
        <CopyButton value={doc.extracted_text} />
        {doc.download_url && <a href={doc.download_url} className="btn btn-sm btn-outline-primary" title="Descargar como .txt">Descargar .txt</a>}
      </div>}
    </div>
    <div className="card-body py-2">
      {hasText ? <DocText doc={doc} />
        : doc.status === "no_text" ? <p className="text-muted mb-0"><em>No se pudo extraer texto legible del archivo.</em>{doc.error_message && <span className="d-block small">{doc.error_message}</span>}</p>
        : doc.status === "failed" ? <div className="alert alert-danger mb-0 py-2"><strong>Error:</strong> {doc.error_message || "Error desconocido al procesar el archivo."}</div>
        : doc.status === "pending" || doc.status === "processing" ? <p className="text-muted mb-0"><em>Esperando procesamiento...</em></p> : null}
      {doc.processed_at && <small className="text-muted d-block mt-1">Procesado: {doc.processed_at}</small>}
    </div>
  </div>;
}

function Switch({ label, on }: { label: string; on: boolean }) {
  return <><span className={`badge ${on ? "badge-success" : "badge-secondary"}`}>{label}: {on ? "ON" : "OFF"}</span>{" "}</>;
}

function JobPage({ pk }: { pk: string }) {
  const [state] = useMainResource(`${API}lotes/${pk}/`, jobValid);
  return renderMain(state, "Cargando…", (job) => ({
    title: "Detalle de lote OCR", heading: "Detalle de lote OCR",
    breadcrumb: <ol className="breadcrumb float-sm-right">
      <li className="breadcrumb-item">Administración</li>
      <li className="breadcrumb-item"><a href={job.upload_url}>OCR</a></li>
      <li className="breadcrumb-item active">Lote #{job.id}</li>
    </ol>,
    content: <div className="row justify-content-center"><div className="col-12 col-xl-10"><div className="card shadow-sm mb-4">
      <InsumosToastList messages={job.messages} />
      <div className="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div><h3 className="mb-0">Lote OCR #{job.id}</h3><small className="text-muted">{job.requested_at}</small></div>
        <div className="d-flex flex-wrap gap-2"><a href={`/ocr/${job.id}/`} className="btn btn-outline-primary" onClick={(e) => { e.preventDefault(); window.location.reload(); }}>Actualizar estado</a></div>
      </div>
      <div className="card-body">
        <div className="mb-4"><Badge map={STATUS} status={job.status} /></div>
        <div className="row g-3 mb-4">
          {([["Archivos totales", job.total_documents, false], ["Procesados", job.processed_documents, false], ["Con error", job.failed_documents, job.failed_documents > 0]] as const).map(([label, n, red]) =>
            <div key={label} className="col-sm-4"><div className="border rounded p-3 h-100"><div className="text-muted small">{label}</div><div className={`h4 mb-0 ${red ? "text-danger" : ""}`}>{n}</div></div></div>)}
        </div>
        <div className="mb-4">
          <div className="text-muted small mb-1">Opciones de calidad del lote</div>
          <Switch label="Preprocesado" on={job.options.preprocess} />
          <Switch label="Capa de texto PDF" on={job.options.pdf_text_layer} />
          <Switch label="Auto-orientación" on={job.options.auto_orient} />
        </div>
        {job.last_error_message && <div className="alert alert-danger mb-4"><strong>Error del lote:</strong> {job.last_error_message}</div>}
        {job.documents.length ? <><h5 className="mb-3">Resultados por archivo</h5>{job.documents.map((d) => <DocCard key={d.id} doc={d} />)}</>
          : <div className="alert alert-light border">Todavía no hay documentos en este lote.</div>}
      </div>
    </div></div></div>,
  }));
}

export const ocrRoute: RouteDefinition<{ pk: string | null }> = {
  name: "ocr",
  match: (pathname) => {
    if (pathname === UPLOAD) return { pk: null };
    const m = /^\/ocr\/([0-9]+)\/$/.exec(pathname);
    return m ? { pk: m[1] } : null;
  },
  render: ({ pk }) => (pk ? <JobPage pk={pk} /> : <UploadPage />),
};
