/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CM01: `comunicados/mailing_form.html` and `comunicados/mailing_job_detail.html`. The API under
 * `/api/web/comedores/comunicados/mailing/` runs the native views (403 unless admin, 404 for a missing batch): the upload only
 * queues a `pending` batch for the existing worker (nothing is sent here) and «Reanudar» runs the native resume. A rejected upload
 * comes back as 400 with the bound form. «Descargar plantilla» stays the native GET submit and «Actualizar estado» a plain link.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Field = { name: string; label: string; help_text: string; required: boolean; type: "text" | "textarea" | "file" | "files"; accept: string; value: string; errors: string[] };
type Recent = {
  id: number; requested_at: string; status: string; asunto_corto: string; last_successful_mail: string; last_successful_row: number | null;
  last_error_message: string; detail_url: string;
};
export type FormData_ = { form_title: string; fields: Field[]; template_download_url: string; gestion_url: string; recent_jobs: Recent[]; messages: Message[] };
type Last = { mail: string; fila: number | null };
export type JobData = {
  job: {
    id: number; original_filename: string; requested_at: string; status: string; asunto: string; cuerpo: string; resume_count: number;
    total_rows: number; processed_rows: number; sent_rows: number; rejected_rows: number; last_successful: Last; last_attempted: Last;
    last_error_message: string; last_error_at: string | null; attachments: { nombre_original: string; url: string }[];
  };
  rows: { fila: number; status: string; mail_destino: string; attempts: number; mensaje: string }[];
  page: { number: number; num_pages: number; previous: number | null; next: number | null };
  is_resume_available: boolean; resume_url: string; refresh_url: string; upload_url: string; gestion_url: string; messages: Message[];
};

const API = "web/comedores/comunicados/mailing/";
const LEVELS = ["success", "error", "warning", "info"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const nullableInt = (v: unknown) => v === null || int(v);
const messagesValid = (v: unknown): v is Message[] => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
const fieldValid = (f: unknown): f is Field => record(f) && text(f.name) && text(f.label) && text(f.help_text) && typeof f.required === "boolean" &&
  ["text", "textarea", "file", "files"].includes(f.type as string) && text(f.accept) && text(f.value) && Array.isArray(f.errors) && f.errors.every(text);

export function formValid(v: unknown): v is FormData_ {
  return record(v) && text(v.form_title) && Array.isArray(v.fields) && v.fields.length === 4 && v.fields.every(fieldValid) && internal(v.template_download_url) &&
    internal(v.gestion_url) && messagesValid(v.messages) &&
    Array.isArray(v.recent_jobs) && v.recent_jobs.every((j) => record(j) && int(j.id) && text(j.requested_at) && text(j.status) && text(j.asunto_corto) &&
      text(j.last_successful_mail) && nullableInt(j.last_successful_row) && text(j.last_error_message) && internal(j.detail_url));
}
const lastValid = (l: unknown) => record(l) && text(l.mail) && nullableInt(l.fila);
export function jobValid(v: unknown): v is JobData {
  if (!record(v) || !record(v.job) || !record(v.page) || !Array.isArray(v.rows)) return false;
  const j = v.job, p = v.page;
  return int(j.id) && text(j.original_filename) && text(j.requested_at) && text(j.status) && text(j.asunto) && text(j.cuerpo) && int(j.resume_count) &&
    int(j.total_rows) && int(j.processed_rows) && int(j.sent_rows) && int(j.rejected_rows) && lastValid(j.last_successful) && lastValid(j.last_attempted) &&
    text(j.last_error_message) && (j.last_error_at === null || text(j.last_error_at)) &&
    Array.isArray(j.attachments) && j.attachments.every((a) => record(a) && text(a.nombre_original) && text(a.url)) &&
    v.rows.every((r) => record(r) && int(r.fila) && text(r.status) && text(r.mail_destino) && int(r.attempts) && text(r.mensaje)) &&
    int(p.number) && int(p.num_pages) && nullableInt(p.previous) && nullableInt(p.next) && typeof v.is_resume_available === "boolean" &&
    internal(v.resume_url) && internal(v.refresh_url) && internal(v.upload_url) && internal(v.gestion_url) && messagesValid(v.messages);
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const comunicadosMailingNavigation = { assign: (to: string) => window.location.assign(to) };

const UNCERTAIN_UPLOAD = "No se pudo confirmar el resultado. Revise los últimos lotes antes de volver a cargar el archivo.";
const UNCERTAIN_RESUME = "No se pudo confirmar el resultado. Use Actualizar estado.";

const Migas = ({ gestion, mailing, actual }: { gestion: string; mailing: string | null; actual: string }) => (
  <ol className="breadcrumb float-sm-right">
    <li className="breadcrumb-item">Gestión</li>
    <li className="breadcrumb-item"><a href={gestion}>Comunicados</a></li>
    {mailing && <li className="breadcrumb-item"><a href={mailing}>Mailing masivo</a></li>}
    <li className="breadcrumb-item active">{actual}</li>
  </ol>
);

const BADGES: Record<string, [string, string]> = {
  completed: ["badge-success", "Completado"], failed: ["badge-danger", "Fallido"], processing: ["badge-warning", "Procesando"],
};
function Badge({ estado }: { estado: string }) {
  const [clase, etiqueta] = BADGES[estado] ?? ["badge-secondary", "Pendiente"];
  return <span className={`badge ${clase}`}>{etiqueta}</span>;
}

/** One `as_crispy_field` (Bootstrap 5) block with its help text and errors. */
function CrispyField({ field, fileKey }: { field: Field; fileKey: number }) {
  const id = `id_${field.name}`;
  const invalid = field.errors.length > 0;
  const describedby = `${id}_helptext${invalid ? ` ${id}_error` : ""}`;
  const aria = { ...(invalid ? { "aria-invalid": true as const } : {}), "aria-describedby": describedby };
  const errors = invalid && (
    <div id={`${id}_error`} className="invalid-feedback">{field.errors.map((e, i) => <p key={i} id={`error_${i + 1}_${id}`}><strong>{e}</strong></p>)}</div>
  );
  const help = <div id={`${id}_helptext`} className="form-text">{field.help_text}</div>;
  const label = (
    <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>{field.label}{field.required && <span className="asteriskField">*</span>}</label>
  );
  let control;
  if (field.type === "text") {
    control = <>
      <input type="text" name={field.name} defaultValue={field.value} className={`form-control textinput${invalid ? " is-invalid" : ""}`} maxLength={255} required {...aria} id={id} />
      {errors}{help}
    </>;
  } else if (field.type === "textarea") {
    control = <>
      <textarea name={field.name} cols={40} rows={10} defaultValue={field.value} className={`form-control textarea${invalid ? " is-invalid" : ""}`} required {...aria} id={id} />
      {errors}{help}
    </>;
  } else {
    control = (
      <div className={invalid ? "is-invalid" : undefined}>
        <input key={fileKey} type="file" name={field.name} className={`form-control form-control${invalid ? " is-invalid" : ""}`} accept={field.accept || undefined}
          multiple={field.type === "files" || undefined} id={id} required={field.required || undefined} {...aria} />
        {errors}{help}
      </div>
    );
  }
  return <div className="mb-3"><div id={`div_${id}`} className="mb-3">{label}{" "}{control}</div></div>;
}

function UploadForm({ initial }: { initial: FormData_ }) {
  const [data, setData] = useState(initial);
  const [revision, setRevision] = useState(0);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    // "Descargar plantilla" is a native GET submit (formaction/formmethod): the browser follows it.
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    if (submitter && submitter.formMethod === "get") return;
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setPending(true); setError("");
    try {
      const { data: body, status } = await webClient.post(API, new FormData(event.currentTarget), { validateStatus: (s: number) => accepted(s) || s === 400 });
      if (status === 400 && formValid(body)) { setData(body); setRevision((n) => n + 1); resetAfterRejectedPost(); }
      else if (record(body) && body.ok === true && internal(body.redirect)) { comunicadosMailingNavigation.assign(body.redirect); return; }
      else setError(status === 403 && record(body) && text(body.detail) ? body.detail : UNCERTAIN_UPLOAD);
    } catch { setError(UNCERTAIN_UPLOAD); }
    busy.current = false; setPending(false);
  }
  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="row justify-content-center">
        <div className="col-12 col-lg-8">
          <div className="card shadow-sm">
            <div className="card-header"><h3 className="mb-0">{data.form_title}</h3></div>
            <div className="card-body">
              <p className="text-muted">
                Descargue la plantilla, complete la columna <code>mail</code> con las direcciones de destino
                y luego cargue el archivo <code>.xlsx</code>. El sistema validará
                el archivo y creará un lote. Los correos se enviarán de forma asíncrona.
              </p>
              <form key={revision} method="post" encType="multipart/form-data" noValidate onSubmit={(e) => void submit(e)}>
                <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
                {data.fields.map((f) => <CrispyField key={f.name} field={f} fileKey={revision} />)}
                {error && <p role="alert" className="text-danger">{error}</p>}
                <div className="d-flex flex-wrap gap-2">
                  <button type="submit" className="btn btn-outline-primary" formAction={data.template_download_url} formMethod="get" formNoValidate>Descargar plantilla</button>
                  <button type="submit" className="btn btn-success" disabled={pending}>Crear lote de mailing</button>
                  <a href={data.gestion_url} className="btn btn-secondary">Volver</a>
                </div>
              </form>
              <hr className="my-4" />
              {data.recent_jobs.length > 0 ? (
                <>
                  <h4 className="mb-3">Últimos lotes de mailing</h4>
                  <div className="table-responsive">
                    <table className="table table-bordered table-hover align-middle mb-0">
                      <thead>
                        <tr>{["Lote", "Fecha", "Estado", "Asunto", "Último mail enviado", "Error", "Detalle"].map((t) => <th key={t} scope="col">{t}</th>)}</tr>
                      </thead>
                      <tbody>
                        {data.recent_jobs.map((j) => (
                          <tr key={j.id}>
                            <td>#{j.id}</td>
                            <td>{j.requested_at}</td>
                            <td><Badge estado={j.status} /></td>
                            <td>{j.asunto_corto}</td>
                            <td>
                              {j.last_successful_mail ? <>{j.last_successful_mail}{j.last_successful_row ? <small className="text-muted d-block">Fila {j.last_successful_row}</small> : null}</> : "-"}
                            </td>
                            <td>{j.last_error_message || "-"}</td>
                            <td><a href={j.detail_url} className="btn btn-sm btn-outline-primary">Ver detalle</a></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : <div className="alert alert-light border mb-0">Todavía no hay lotes creados para mailing masivo.</div>}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function FormPage() {
  const [state] = useMainResource(API, formValid);
  return renderMain(state, "Cargando mailing…", (data) => ({
    title: "Mailing masivo", heading: "Mailing masivo",
    breadcrumb: <Migas gestion={data.gestion_url} mailing={null} actual="Mailing masivo" />,
    content: <UploadForm initial={data} />,
  }));
}

function Reanudar({ data }: { data: JobData }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setPending(true); setError("");
    try {
      const { data: body, status } = await webClient.post(`${API}jobs/${data.job.id}/resume/`, new URLSearchParams(), { validateStatus: accepted });
      if (record(body) && body.ok === true && internal(body.redirect)) { comunicadosMailingNavigation.assign(body.redirect); return; }
      setError(status === 403 && record(body) && text(body.detail) ? body.detail : UNCERTAIN_RESUME);
    } catch { setError(UNCERTAIN_RESUME); }
    busy.current = false; setPending(false);
  }
  return (
    <>
      <form method="post" action={data.resume_url} onSubmit={(e) => void submit(e)}>
        <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
        <button type="submit" className="btn btn-warning" disabled={pending}>Reanudar</button>
      </form>
      {error && <p role="alert" className="text-danger">{error}</p>}
    </>
  );
}

function Counter({ title, value }: { title: string; value: number }) {
  return (
    <div className="col-sm-6 col-xl-3">
      <div className="border rounded p-3 h-100">
        <div className="text-muted small">{title}</div>
        <div className="h4 mb-0">{value}</div>
      </div>
    </div>
  );
}

function LastMail({ title, last, empty }: { title: string; last: Last; empty: string }) {
  return (
    <div className="col-md-6">
      <div className="alert alert-light border mb-0 h-100">
        <div className="font-weight-bold mb-2">{title}</div>
        {last.mail ? <><div>{last.mail}</div><small className="text-muted">Fila {last.fila ?? "-"}</small></> : <div className="text-muted">{empty}</div>}
      </div>
    </div>
  );
}

export function JobContent({ data }: { data: JobData }) {
  const { job, page } = data;
  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="row justify-content-center">
        <div className="col-12 col-xl-10">
          <div className="card shadow-sm mb-4">
            <div className="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
              <div>
                <h3 className="mb-0">Lote #{job.id}</h3>
                <small className="text-muted">{job.original_filename} | {job.requested_at}</small>
              </div>
              <div className="d-flex flex-wrap gap-2">
                <a href={data.refresh_url} className="btn btn-outline-primary">Actualizar estado</a>
                {data.is_resume_available && <Reanudar data={data} />}
              </div>
            </div>
            <div className="card-body">
              <div className="mb-4">
                <Badge estado={job.status} />{" "}
                <span className="ml-2 text-muted">Asunto: <strong>{job.asunto}</strong>{" "}</span>{" "}
                <span className="ml-2 text-muted">Reanudaciones: <strong>{job.resume_count}</strong>{" "}</span>
              </div>
              <div className="row g-3 mb-4">
                <Counter title="Filas totales" value={job.total_rows} />
                <Counter title="Filas procesadas" value={job.processed_rows} />
                <Counter title="Enviadas" value={job.sent_rows} />
                <Counter title="Rechazadas" value={job.rejected_rows} />
              </div>
              <div className="row g-3 mb-4">
                <LastMail title="Último mail enviado correctamente" last={job.last_successful} empty="Todavía no hay envíos exitosos." />
                <LastMail title="Último mail intentado" last={job.last_attempted} empty="Todavía no se intentó ninguna fila." />
              </div>
              <div className="card mb-4">
                <div className="card-header">Cuerpo del mensaje</div>
                <div className="card-body"><pre style={{ whiteSpace: "pre-wrap" }}>{job.cuerpo}</pre></div>
              </div>
              {job.attachments.length > 0 && (
                <div className="card mb-4">
                  <div className="card-header">Archivos adjuntos</div>
                  <div className="card-body">
                    <ul className="list-unstyled mb-0">
                      {job.attachments.map((a, i) => (
                        <li key={i}><i className="fas fa-paperclip me-1 text-muted" />{" "}<a href={a.url} target="_blank">{a.nombre_original}</a></li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
              {job.last_error_message ? (
                <div className="alert alert-danger">
                  <div className="font-weight-bold">Causa del error</div>
                  <div>{job.last_error_message}</div>
                  {job.last_error_at && <small className="d-block mt-2">Registrado el {job.last_error_at}</small>}
                </div>
              ) : (job.status === "processing" || job.status === "pending") && (
                <div className="alert alert-info">
                  El lote está en curso fuera de la request web. Use{" "}
                  <strong>Actualizar estado</strong> para refrescar el detalle.
                </div>
              )}
              <div className="table-responsive">
                <table className="table table-bordered table-hover align-middle mb-0">
                  <thead>
                    <tr>{["Fila", "Estado", "Mail destino", "Intentos", "Detalle"].map((t) => <th key={t} scope="col">{t}</th>)}</tr>
                  </thead>
                  <tbody>
                    {data.rows.length ? data.rows.map((r) => (
                      <tr key={r.fila}>
                        <td>{r.fila}</td>
                        <td>{r.status === "sent" ? <span className="badge badge-success">Enviado</span> : <span className="badge badge-danger">Fallido</span>}</td>
                        <td>{r.mail_destino}</td>
                        <td>{r.attempts}</td>
                        <td>{r.mensaje}</td>
                      </tr>
                    )) : <tr><td colSpan={5} className="text-center text-muted py-4">Aún no hay filas procesadas para este lote.</td></tr>}
                  </tbody>
                </table>
              </div>
              {page.num_pages > 1 && (
                <nav aria-label="Paginación de filas" className="mt-3">
                  <ul className="pagination mb-0">
                    {page.previous !== null && <li className="page-item"><a className="page-link" href={`?page=${page.previous}`}>Anterior</a></li>}
                    <li className="page-item active"><span className="page-link">Página {page.number} de {page.num_pages}</span></li>
                    {page.next !== null && <li className="page-item"><a className="page-link" href={`?page=${page.next}`}>Siguiente</a></li>}
                  </ul>
                </nav>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function JobPage({ pk }: { pk: string }) {
  const [state] = useMainResource(`${API}jobs/${pk}/${window.location.search}`, jobValid);
  return renderMain(state, "Cargando lote…", (data) => ({
    title: "Detalle de lote de mailing", heading: "Detalle de lote de mailing",
    breadcrumb: <Migas gestion={data.gestion_url} mailing={data.upload_url} actual={`Lote #${data.job.id}`} />,
    content: <JobContent data={data} />,
  }));
}

export const comunicadosMailingRoute: RouteDefinition<{ pk: string | null }> = {
  name: "comedores-comunicados-mailing",
  match(pathname) {
    if (pathname === "/comunicados/mailing/") return { pk: null };
    const found = /^\/comunicados\/mailing\/lotes\/([0-9]+)\/$/.exec(pathname);
    return found ? { pk: found[1] } : null;
  },
  render({ pk }) {
    return pk === null ? <FormPage key="form" /> : <JobPage key={`job:${pk}`} pk={pk} />;
  },
};
