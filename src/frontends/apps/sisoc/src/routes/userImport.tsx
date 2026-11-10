/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { crearCliente, leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { InsumosToastList } from "../InsumosToast";
import type { RequiredPasswordPresentation } from "../RequiredPasswordChange";
import { userJobsFrame } from "../identityFrames";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "../webAccess";
import type { RouteDefinition } from "./types";

// Shared by the user-job units (import U05, bulk credentials U04): session GET,
// prerequisite/permission 403, and the legacy presentation frame.
export type JobMessage = { message: string; level: "success" | "error" | "warning" | "info" };
export type FieldErrors = Record<string, { message: string; code: string }[]>;
export type LoadState<T> = { status: "loading" | "error" } | { status: "forbidden"; prerequisite: WebPrerequisite | null } | { status: "ready"; data: T };
export type JobField = { name: string; label: string; help_text: string; required: boolean; accept?: string };

export const client = crearCliente("/api");
/** Full-page navigation after a confirmed POST; replaceable in tests. */
export const navigation = { assign: (to: string) => window.location.assign(to) };
export const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object";
export const accepted = (status: number) => (status >= 200 && status < 300) || status === 403;
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v) && v >= 0;

export function presentationValid(v: unknown): v is RequiredPasswordPresentation {
  if (!record(v) || !record(v.user) || typeof v.footer_version_label !== "string" || !Array.isArray(v.legacy_frame_navigation)) return false;
  const node = (n: unknown): boolean => record(n) && typeof n.id === "string" && typeof n.label === "string" && (n.href === null || safeInternalPath(n.href) !== null) && Array.isArray(n.children) && n.children.every(node);
  return ["username", "display_name", "avatar_initial", "role_label"].every(k => typeof (v.user as Record<string, unknown>)[k] === "string") && v.legacy_frame_navigation.every(node);
}
export const messagesValid = (v: unknown): v is JobMessage[] => Array.isArray(v) && v.every(m => record(m) && typeof m.message === "string" && ["success", "error", "warning", "info"].includes(m.level as string));
export const errorsValid = (v: unknown): v is FieldErrors => record(v) && Object.values(v).every(entries => Array.isArray(entries) && entries.every(e => record(e) && typeof e.message === "string"));
export const fieldsValid = (v: unknown): v is JobField[] => Array.isArray(v) && v.every(f => record(f) && typeof f.name === "string" && typeof f.label === "string" && typeof f.help_text === "string" && typeof f.required === "boolean");
export const countsValid = (v: Record<string, unknown>, keys: string[]) => keys.every(k => integer(v[k]));

/** One GET per mount; the status is read on demand only, never polled or retried. */
export function useWebResource<T>(endpoint: string, valid: (v: unknown) => v is T) {
  const [state, setState] = useState<LoadState<T>>({ status: "loading" });
  useEffect(() => {
    let active = true; const controller = new AbortController();
    client.get(endpoint, { signal: controller.signal, validateStatus: accepted }).then(({ data, status }: { data: unknown; status?: number }) => {
      if (!active) return;
      if (status === 403) setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(data) });
      else setState(valid(data) ? { status: "ready", data } : { status: "error" });
    }).catch(() => { if (active) setState({ status: "error" }); });
    return () => { active = false; controller.abort(); };
  }, [endpoint, valid]);
  return [state, setState] as const;
}

export function renderLoad<T extends { presentation: RequiredPasswordPresentation }>(state: LoadState<T>, loading: string, render: (data: T) => { content: ReactNode; title: string; breadcrumb: ReactNode }) {
  if (state.status === "loading") return <main role="status">{loading}</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar el lote.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  if (state.status !== "ready") return null;
  const { content, title, breadcrumb } = render(state.data);
  return userJobsFrame(content, state.data.presentation, title, breadcrumb);
}

/** POST once; an unconfirmed outcome is reported, never resubmitted. */
export async function postOnce(endpoint: string, body: FormData | URLSearchParams, expected: string) {
  try {
    const { data, status } = await client.post(endpoint, body, { validateStatus: accepted });
    if (status === 403) return { kind: "forbidden" as const, data };
    if (record(data) && data.ok === true && typeof data.redirect === "string" && data.redirect === safeInternalPath(data.redirect) && data.redirect.startsWith(expected)) return { kind: "redirect" as const, to: data.redirect };
    return { kind: "uncertain" as const };
  } catch (error: unknown) {
    const response = (error as { response?: { status?: number; data?: unknown } }).response;
    if (response?.status === 400) return { kind: "invalid" as const, data: response.data };
    return { kind: "uncertain" as const };
  }
}

/** A native re-render is a page load: the next Tab starts again at the top of the document. */
export function restartKeyboardFromTop() {
  const body = document.body; const had = body.hasAttribute("tabindex");
  if (!had) body.setAttribute("tabindex", "-1");
  body.focus({ preventScroll: true });
  if (!had) body.removeAttribute("tabindex");
}

function CsrfInput() {
  return <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;
}

function FileField({ field, errors, disabled, inputKey }: { field: JobField; errors: FieldErrors; disabled: boolean; inputKey: number }) {
  const id = `id_${field.name}`; const invalid = !!errors[field.name]?.length;
  const input = <input key={inputKey} type="file" name={field.name} className={`form-control${invalid ? " is-invalid" : ""}`} accept={field.accept} id={id} required={field.required} disabled={disabled} aria-invalid={invalid ? "true" : undefined} aria-describedby={`${id}_helptext${invalid ? ` ${id}_error` : ""}`} />;
  return <div className="mb-3"><div id={`div_${id}`} className="mb-3">
    <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>{field.label}{field.required && <span className="asteriskField">*</span>}</label>
    <div className={invalid ? "is-invalid" : undefined}>
      {input}
      {invalid && <div id={`${id}_error`} className="invalid-feedback">{errors[field.name].map((e, i) => <p id={`error_${i + 1}_${id}`} key={i}><strong>{e.message}</strong></p>)}</div>}
      <div id={`${id}_helptext`} className="form-text">{field.help_text}</div>
    </div>
  </div></div>;
}

function CheckField({ field, checked, onChange, disabled }: { field: JobField; checked: boolean; onChange: (value: boolean) => void; disabled: boolean }) {
  const id = `id_${field.name}`;
  return <div className="mb-3"><div className="mb-3"><div id={`div_${id}`} className="form-check">
    <input type="checkbox" name={field.name} className="checkboxinput form-check-input" aria-describedby={`${id}_helptext`} id={id} checked={checked} disabled={disabled} onChange={e => onChange(e.target.checked)} />
    {" "}<label htmlFor={id} className="form-check-label">{field.label}</label>
    <div id={`${id}_helptext`} className="form-text">{field.help_text}</div>
  </div></div></div>;
}

function Pagination({ page, query }: { page: JobPage; query: (page: number) => string }) {
  if (page.num_pages <= 1) return null;
  return <nav aria-label="Paginacion de filas" className="mt-3"><ul className="pagination mb-0">
    {page.previous !== null && <li className="page-item"><a className="page-link" href={query(page.previous)}>Anterior</a></li>}
    <li className="page-item active"><span className="page-link">{`Pagina ${page.number} de ${page.num_pages}`}</span></li>
    {page.next !== null && <li className="page-item"><a className="page-link" href={query(page.next)}>Siguiente</a></li>}
  </ul></nav>;
}

function ResumeButton({ endpoint, expected, onForbidden }: { endpoint: string; expected: string; onForbidden: (data: unknown) => void }) {
  const [pending, setPending] = useState(false); const [uncertain, setUncertain] = useState(false); const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy.current) return;
    busy.current = true; setPending(true);
    const result = await postOnce(endpoint, new URLSearchParams(), expected);
    if (result.kind === "redirect") navigation.assign(result.to);
    else if (result.kind === "forbidden") onForbidden(result.data);
    else { setUncertain(true); setPending(false); }
  }
  return <form method="post" onSubmit={submit}><CsrfInput /><button type="submit" className="btn btn-warning" disabled={pending || uncertain}>Reanudar</button>{uncertain && <p role="alert" className="mb-0">No se pudo confirmar el resultado. Use Actualizar estado.</p>}</form>;
}

export type JobPage = { number: number; num_pages: number; previous: number | null; next: number | null };
export const pageValid = (v: unknown): v is JobPage => record(v) && integer(v.number) && integer(v.num_pages) && (v.previous === null || integer(v.previous)) && (v.next === null || integer(v.next));
/** The native base layout loads hitos.css on every page; it styles the card-header titles. */
export const HITOS_STYLESHEET = <link rel="stylesheet" href="/static/custom/css/hitos.css" />;
export const jobsBreadcrumb = (items: ReactNode) => <ol className="breadcrumb float-sm-right"><li className="breadcrumb-item">Administracion</li><li className="breadcrumb-item"><a href="/usuarios/">Usuarios</a></li>{items}</ol>;

type ImportStatus = "pending" | "processing" | "completed" | "completed_with_errors" | "failed";
type RecentJob = { id: number; requested_at: string; status: ImportStatus; created_rows: number; skipped_rows: number; failed_rows: number; detail_url: string };
type FormData_ = { fields: JobField[]; initial: { enviar_credenciales: boolean; es_pwa: boolean }; errors: FieldErrors; template_download_url: string; recent_jobs: RecentJob[]; messages: JobMessage[]; presentation: RequiredPasswordPresentation };
type Row = { id: number; fila: number; nombre: string; apellido: string; email: string; status: "pending" | "created" | "skipped" | "failed"; attempts: number; mensaje: string };
type Job = { id: number; original_filename: string; requested_at: string; status: ImportStatus; send_credentials: boolean; resume_count: number; total_rows: number; processed_rows: number; created_rows: number; skipped_rows: number; failed_rows: number; last_error_message: string; last_error_at: string };
type Detail = { job: Job; rows: Row[]; page: JobPage; status_filter: string; is_resume_available: boolean; csv_url: string | null; upload_url: string; messages: JobMessage[]; presentation: RequiredPasswordPresentation };
const FIELD_NAMES = ["archivo", "enviar_credenciales", "es_pwa"];

function formValid(v: unknown): v is FormData_ {
  return record(v) && presentationValid(v.presentation) && fieldsValid(v.fields) && v.fields.map(f => f.name).join() === FIELD_NAMES.join() && record(v.initial) && typeof v.initial.enviar_credenciales === "boolean" && typeof v.initial.es_pwa === "boolean" && errorsValid(v.errors) && typeof v.template_download_url === "string" && safeInternalPath(v.template_download_url) !== null && messagesValid(v.messages) && Array.isArray(v.recent_jobs) && v.recent_jobs.every(j => record(j) && countsValid(j, ["id", "created_rows", "skipped_rows", "failed_rows"]) && typeof j.requested_at === "string" && typeof j.status === "string" && typeof j.detail_url === "string" && safeInternalPath(j.detail_url) !== null);
}
function detailValid(v: unknown): v is Detail {
  if (!record(v) || !presentationValid(v.presentation) || !record(v.job) || !Array.isArray(v.rows) || !pageValid(v.page) || !messagesValid(v.messages)) return false;
  const j = v.job;
  return countsValid(j, ["id", "resume_count", "total_rows", "processed_rows", "created_rows", "skipped_rows", "failed_rows"]) && ["original_filename", "requested_at", "status", "last_error_message", "last_error_at"].every(k => typeof j[k] === "string") && typeof j.send_credentials === "boolean" && typeof v.status_filter === "string" && typeof v.is_resume_available === "boolean" && (v.csv_url === null || (typeof v.csv_url === "string" && safeInternalPath(v.csv_url) !== null)) && typeof v.upload_url === "string" && v.rows.every(r => record(r) && countsValid(r, ["id", "fila", "attempts"]) && ["nombre", "apellido", "email", "status", "mensaje"].every(k => typeof r[k] === "string"));
}

function ImportStatusBadge({ status }: { status: string }) {
  if (status === "completed") return <span className="badge badge-success">Completado</span>;
  if (status === "completed_with_errors") return <span className="badge badge-warning">Completado con errores</span>;
  if (status === "failed") return <span className="badge badge-danger">Fallido</span>;
  if (status === "processing") return <span className="badge badge-warning">Procesando</span>;
  return <span className="badge badge-secondary">Pendiente</span>;
}
function RowBadge({ status }: { status: string }) {
  if (status === "created") return <span className="badge badge-success">Creado</span>;
  if (status === "skipped") return <span className="badge badge-secondary">Omitido</span>;
  if (status === "failed") return <span className="badge badge-danger">Fallido</span>;
  return <span className="badge badge-light">Pendiente</span>;
}

const FORM_ENDPOINT = "web/users/import/";

function ImportForm() {
  const [state, setState] = useWebResource(FORM_ENDPOINT, formValid);
  return renderLoad(state, "Cargando gestor masivo…", data => ({
    title: "Gestor masivo de usuarios",
    breadcrumb: jobsBreadcrumb(<li className="breadcrumb-item active">Gestor masivo</li>),
    content: <ImportFormContent data={data} forbidden={d => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(d) })} />,
  }));
}

function ImportFormContent({ data, forbidden }: { data: FormData_; forbidden: (data: unknown) => void }) {
  const [errors, setErrors] = useState(data.errors); const [values, setValues] = useState(data.initial);
  const [pending, setPending] = useState(false); const [uncertain, setUncertain] = useState(false); const [revision, setRevision] = useState(0);
  const busy = useRef(false); const form = useRef<HTMLFormElement>(null);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    const body = new FormData(); const file = (form.current?.elements.namedItem("archivo") as HTMLInputElement | null)?.files?.[0];
    if (file) body.append("archivo", file);
    if (values.enviar_credenciales) body.append("enviar_credenciales", "on");
    if (values.es_pwa) body.append("es_pwa", "on");
    const result = await postOnce(FORM_ENDPOINT, body, "/usuarios/importar/lotes/");
    if (result.kind === "redirect") { navigation.assign(result.to); return; }
    if (result.kind === "forbidden") { forbidden(result.data); return; }
    if (result.kind === "invalid" && formValid(result.data) && Object.keys(result.data.errors).length) {
      // The native page re-renders the bound form: the file input starts empty.
      setErrors(result.data.errors); setValues(result.data.initial); setRevision(r => r + 1); busy.current = false;
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
      restartKeyboardFromTop();
    } else setUncertain(true);
    setPending(false);
  }
  const disabled = pending || uncertain;
  const [archivo, enviar, pwa] = data.fields;
  return <>
    {HITOS_STYLESHEET}
    <InsumosToastList messages={data.messages} />
    <div className="row justify-content-center"><div className="col-12 col-lg-8"><div className="card shadow-sm">
      <div className="card-header"><h3 className="mb-0">Gestor masivo de usuarios</h3></div>
      <div className="card-body">
        <p className="text-muted">Cargue un archivo <code>.xlsx</code> con los usuarios a crear. El sistema validara el archivo, creara los usuarios en background y podra seguir el estado desde el detalle del lote. Si un usuario ya existe (mismo correo), la fila se omite sin error.</p>
        <div className="alert alert-light border">
          <div className="font-weight-bold mb-2">Formato del archivo</div>
          <p className="mb-2">Descargue la plantilla y complete una fila por usuario. Las columnas requeridas son:</p>
          <ul className="mb-2 pl-3">
            <li><code>Username</code> — opcional. Si se completa, se usa tal cual; si se deja en blanco, se genera automaticamente a partir del nombre y apellido.</li>
            <li><code>Nombre</code> — nombre del usuario</li>
            <li><code>Apellido</code> — apellido del usuario</li>
            <li><code>Correo</code> — email (se usara como identificador unico)</li>
            <li><code>Permisos</code> — nombres de grupos y/o codenames de permisos PWA delegables, separados por <code>;</code>. Cada valor se busca primero como nombre de grupo; si no existe, se busca como permiso PWA que usted pueda delegar. Aplica igual con o sin &quot;Usuarios de la PWA&quot; marcado.{" "}<br />{" "}<small className="text-muted">Ej: <code>Comedores Ver;Comedores Listar;manage_nomina_pwa</code></small></li>
            <li><code>Accion grupos</code> — opcional (si se deja en blanco se usa <code>agregar</code>). Define que hacer con los grupos y permisos de la columna <code>Permisos</code> cuando la fila actualiza un usuario existente:{" "}<ul className="mb-0">
              <li><code>agregar</code>: suma los grupos/permisos indicados a los que ya tiene.</li>
              <li><code>quitar</code>: remueve los indicados, conserva el resto.</li>
              <li><code>reemplazar</code>: deja exactamente los indicados (salvo los que usted no pueda delegar, que se preservan).</li>
            </ul></li>
            <li><code>Provincias</code> — nombres de provincias separados por <code>;</code> (no aplica a usuarios PWA){" "}<br />{" "}<small className="text-muted">Ej: <code>CABA;BUENOS AIRES</code></small></li>
            <li><code>Rol</code> — descripcion textual del rol (ej: <code>TERRITORIAL</code>, no aplica a usuarios PWA)</li>
            <li><code>Organizaciones</code> — IDs de organizaciones separados por <code>;</code> (solo para usuarios PWA). El usuario opera con todos los comedores de esas organizaciones.{" "}<br />{" "}<small className="text-muted">Ej: <code>3;7</code></small></li>
            <li><code>Comedores</code> — IDs de comedores separados por <code>;</code> (solo para usuarios PWA). Permite asignar comedores puntuales ademas o en lugar de organizaciones.{" "}<br />{" "}<small className="text-muted">Ej: <code>101;205</code></small></li>
          </ul>
          <p className="mb-0 text-muted small">Los nombres de grupos y provincias, y los IDs de organizaciones y comedores, deben coincidir exactamente con los registros del sistema. Una fila invalida detiene el lote y puede reanudarse desde esa fila.</p>
        </div>
        <form ref={form} method="post" encType="multipart/form-data" noValidate onSubmit={submit}>
          <CsrfInput />
          {uncertain && <p role="alert">No se pudo confirmar el resultado. Revise los ultimos lotes antes de volver a cargar el archivo.</p>}
          <FileField field={archivo} errors={errors} disabled={disabled} inputKey={revision} />
          <CheckField field={enviar} checked={values.enviar_credenciales} disabled={disabled} onChange={v => setValues(c => ({ ...c, enviar_credenciales: v }))} />
          <CheckField field={pwa} checked={values.es_pwa} disabled={disabled} onChange={v => setValues(c => ({ ...c, es_pwa: v }))} />
          <div className="d-flex flex-wrap gap-2">
            <a href={data.template_download_url} className="btn btn-outline-primary">Descargar plantilla</a>
            <button type="submit" className="btn btn-success" disabled={disabled}>Crear lote</button>
            <a href="/usuarios/" className="btn btn-secondary">Volver</a>
          </div>
        </form>
        <hr className="my-4" />
        {data.recent_jobs.length ? <>
          <h4 className="mb-3">Ultimos lotes</h4>
          <div className="table-responsive"><table className="table table-bordered table-hover align-middle mb-0">
            <thead><tr><th scope="col">Lote</th><th scope="col">Fecha</th><th scope="col">Estado</th><th scope="col">Creados</th><th scope="col">Omitidos</th><th scope="col">Fallidos</th><th scope="col">Detalle</th></tr></thead>
            <tbody>{data.recent_jobs.map(job => <tr key={job.id}><td>{`#${job.id}`}</td><td>{job.requested_at}</td><td> <ImportStatusBadge status={job.status} /> </td><td>{job.created_rows}</td><td>{job.skipped_rows}</td><td>{job.failed_rows}</td><td> <a href={job.detail_url} className="btn btn-sm btn-outline-primary">Ver detalle</a> </td></tr>)}</tbody>
          </table></div>
        </> : <div className="alert alert-light border mb-0">Todavia no hay lotes de importacion creados.</div>}
      </div>
    </div></div></div>
  </>;
}

const FILTERS: [string, string, string][] = [["", "Todos", "btn-primary"], ["created", "Creados", "btn-success"], ["skipped", "Omitidos", "btn-secondary"], ["failed", "Fallidos", "btn-danger"], ["pending", "Pendientes", "btn-warning"]];

function ImportJob({ id }: { id: string }) {
  const [state, setState] = useWebResource(`web/users/import/jobs/${id}/${window.location.search}`, detailValid);
  return renderLoad(state, "Cargando lote…", data => ({
    title: "Detalle de lote de importacion",
    breadcrumb: jobsBreadcrumb(<><li className="breadcrumb-item"><a href={data.upload_url}>Gestor masivo</a></li><li className="breadcrumb-item active">{`Lote #${data.job.id}`}</li></>),
    content: <ImportJobContent data={data} forbidden={d => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(d) })} />,
  }));
}

function ImportJobContent({ data, forbidden }: { data: Detail; forbidden: (data: unknown) => void }) {
  const { job } = data; const detailUrl = `/usuarios/importar/lotes/${job.id}/`;
  const query = (page: number) => `?${data.status_filter ? `estado=${encodeURIComponent(data.status_filter)}&` : ""}page=${page}`;
  const counter = (label: string, value: number, box = "", number = "") => <div className="col-sm-6 col-xl-3"><div className={`border rounded p-3 h-100${box}`}><div className="text-muted small">{label}</div><div className={`h4 mb-0${number}`}>{value}</div></div></div>;
  return <>
    {HITOS_STYLESHEET}
    <InsumosToastList messages={data.messages} />
    <div className="row justify-content-center"><div className="col-12 col-xl-10"><div className="card shadow-sm mb-4">
      <div className="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div><h3 className="mb-0">{`Lote #${job.id}`}</h3><small className="text-muted">{`${job.original_filename} | ${job.requested_at}`}</small></div>
        <div className="d-flex flex-wrap gap-2">
          <a href={detailUrl} className="btn btn-outline-primary">Actualizar estado</a>
          {data.csv_url && <a href={data.csv_url} className="btn btn-outline-success">Descargar CSV</a>}
          {data.is_resume_available && <ResumeButton endpoint={`web/users/import/jobs/${job.id}/resume/`} expected={detailUrl} onForbidden={forbidden} />}
        </div>
      </div>
      <div className="card-body">
        <div className="mb-4">
          <ImportStatusBadge status={job.status} />{" "}
          <span className="ml-2 text-muted">Credenciales por email: <strong>{`${job.send_credentials ? "Si" : "No"} `}</strong></span>{" "}
          <span className="ml-2 text-muted">Reanudaciones: <strong>{job.resume_count}</strong></span>
        </div>
        <div className="row g-3 mb-4">
          {counter("Filas totales", job.total_rows)}
          {counter("Procesadas", job.processed_rows)}
          {counter("Creados", job.created_rows, " border-success", " text-success")}
          {counter("Omitidos", job.skipped_rows, "", " text-secondary")}
          {counter("Fallidos", job.failed_rows, " border-danger", " text-danger")}
        </div>
        {job.last_error_message ? <div className="alert alert-danger"><div className="font-weight-bold">Causa del error</div><div>{job.last_error_message}</div>{job.last_error_at && <small className="d-block mt-2">{`Registrado el ${job.last_error_at}`}</small>}</div>
          : (job.status === "processing" || job.status === "pending") && <div className="alert alert-info">{"El lote esta en curso fuera de la request web. Use "}<strong>Actualizar estado</strong> para refrescar el detalle.</div>}
        <div className="d-flex flex-wrap gap-2 mb-3">
          {FILTERS.map(([value, label, active]) => <a key={label} href={value ? `?estado=${value}` : "?"} className={`btn btn-sm ${data.status_filter === value || (!value && !data.status_filter) ? active : "btn-outline-secondary"}`}>{label}</a>)}
        </div>
        <div className="table-responsive"><table className="table table-bordered table-hover align-middle mb-0">
          <thead><tr><th scope="col">Fila</th><th scope="col">Nombre</th><th scope="col">Email</th><th scope="col">Estado</th><th scope="col">Intentos</th><th scope="col">Detalle</th></tr></thead>
          <tbody>{data.rows.length ? data.rows.map(row => <tr key={row.id}><td>{row.fila}</td><td>{`${row.nombre} ${row.apellido}`}</td><td>{row.email || "-"}</td><td> <RowBadge status={row.status} /> </td><td>{row.attempts}</td><td>{row.mensaje || "-"}</td></tr>)
            : <tr><td colSpan={6} className="text-center text-muted py-4">Aun no hay filas procesadas para este lote.</td></tr>}</tbody>
        </table></div>
        <Pagination page={data.page} query={query} />
      </div>
    </div></div></div>
  </>;
}

/** Widgets shared with the bulk-credentials unit (kept off the module's component exports). */
export const jobWidgets = { CsrfInput, FileField, Pagination, ResumeButton };

type UserImportParams = { mode: "form" } | { mode: "job"; id: string };

export const userImportRoute: RouteDefinition<UserImportParams> = {
  name: "user-import",
  match(pathname) {
    if (pathname === "/usuarios/importar/") return { mode: "form" };
    const job = pathname.match(/^\/usuarios\/importar\/lotes\/([0-9]+)\/$/);
    return job ? { mode: "job", id: job[1] } : null;
  },
  render: params => params.mode === "form" ? <ImportForm /> : <ImportJob key={params.id} id={params.id} />,
};
