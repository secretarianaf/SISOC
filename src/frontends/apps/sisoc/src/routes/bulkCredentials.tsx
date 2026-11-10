/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { Fragment, useRef, useState, type FormEvent } from "react";
import { InsumosToastList } from "../InsumosToast";
import type { RequiredPasswordPresentation } from "../RequiredPasswordChange";
import { prerequisiteFromForbidden, safeInternalPath } from "../webAccess";
import type { RouteDefinition } from "./types";
import {
  HITOS_STYLESHEET, countsValid, errorsValid, jobWidgets, jobsBreadcrumb, messagesValid, navigation, pageValid, postOnce,
  presentationValid, record, renderLoad, restartKeyboardFromTop, useWebResource,
  type FieldErrors, type JobField, type JobMessage, type JobPage,
} from "./userImport";

// U04: same transport, frame and widgets as the user-import unit (U05).
const { CsrfInput, FileField, Pagination, ResumeButton } = jobWidgets;

type JobStatus = "pending" | "processing" | "completed" | "failed";
type Choice = { value: string; label: string };
type SelectField = JobField & { choices: Choice[] };
type SendTypeOption = { key: string; label: string; description: string; required_columns: string[] };
type RecentJob = { id: number; requested_at: string; status: JobStatus; send_type: string; last_successful_username: string; last_successful_row: number | null; last_error_message: string; detail_url: string };
type FormPayload = { form_title: string; fields: [SelectField, JobField]; values: { tipo_envio: string }; errors: FieldErrors; template_download_url: string; send_type_options: SendTypeOption[]; recent_jobs: RecentJob[]; messages: JobMessage[]; presentation: RequiredPasswordPresentation };
type Row = { id: number; fila: number; usuario: string; status: "sent" | "failed"; mail_destino: string; attempts: number; mensaje: string };
type Job = { id: number; original_filename: string; requested_at: string; status: JobStatus; send_type: string; resume_count: number; total_rows: number; processed_rows: number; sent_rows: number; rejected_rows: number; last_successful_username: string; last_successful_row: number | null; last_attempted_username: string; last_attempted_row: number | null; last_error_message: string; last_error_at: string };
type Detail = { job: Job; rows: Row[]; page: JobPage; is_resume_available: boolean; upload_url: string; messages: JobMessage[]; presentation: RequiredPasswordPresentation };

const text = (v: unknown) => typeof v === "string";
const optionalRow = (v: unknown) => v === null || (typeof v === "number" && Number.isSafeInteger(v) && v >= 0);
const strings = (v: Record<string, unknown>, keys: string[]) => keys.every(k => text(v[k]));
const internal = (v: unknown) => typeof v === "string" && safeInternalPath(v) !== null;

function formValid(v: unknown): v is FormPayload {
  if (!record(v) || !presentationValid(v.presentation) || !Array.isArray(v.fields) || v.fields.length !== 2) return false;
  const [tipo, archivo] = v.fields as unknown[];
  const field = (f: unknown, name: string) => record(f) && f.name === name && text(f.label) && text(f.help_text) && typeof f.required === "boolean";
  return field(tipo, "tipo_envio") && Array.isArray((tipo as Record<string, unknown>).choices) && ((tipo as Record<string, unknown>).choices as unknown[]).every(c => record(c) && text(c.value) && text(c.label))
    && field(archivo, "archivo") && text(v.form_title) && record(v.values) && text(v.values.tipo_envio) && errorsValid(v.errors) && internal(v.template_download_url) && messagesValid(v.messages)
    && Array.isArray(v.send_type_options) && v.send_type_options.every(o => record(o) && strings(o, ["key", "label", "description"]) && Array.isArray(o.required_columns) && o.required_columns.every(text))
    && Array.isArray(v.recent_jobs) && v.recent_jobs.every(j => record(j) && countsValid(j, ["id"]) && strings(j, ["requested_at", "status", "send_type", "last_successful_username", "last_error_message"]) && optionalRow(j.last_successful_row) && internal(j.detail_url));
}

function detailValid(v: unknown): v is Detail {
  if (!record(v) || !presentationValid(v.presentation) || !record(v.job) || !Array.isArray(v.rows) || !pageValid(v.page) || !messagesValid(v.messages)) return false;
  const j = v.job;
  return countsValid(j, ["id", "resume_count", "total_rows", "processed_rows", "sent_rows", "rejected_rows"]) && strings(j, ["original_filename", "requested_at", "status", "send_type", "last_successful_username", "last_attempted_username", "last_error_message", "last_error_at"])
    && optionalRow(j.last_successful_row) && optionalRow(j.last_attempted_row) && typeof v.is_resume_available === "boolean" && internal(v.upload_url)
    && v.rows.every(r => record(r) && countsValid(r, ["id", "fila", "attempts"]) && strings(r, ["usuario", "status", "mail_destino", "mensaje"]));
}

function StatusBadge({ status }: { status: string }) {
  if (status === "completed") return <span className="badge badge-success">Completado</span>;
  if (status === "failed") return <span className="badge badge-danger">Fallido</span>;
  if (status === "processing") return <span className="badge badge-warning">Procesando</span>;
  return <span className="badge badge-secondary">Pendiente</span>;
}

function SelectInput({ field, value, onChange, disabled }: { field: SelectField; value: string; onChange: (value: string) => void; disabled: boolean }) {
  const id = `id_${field.name}`;
  return <div className="mb-3"><div id={`div_${id}`} className="mb-3">
    <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>{field.label}{field.required && <span className="asteriskField">*</span>}</label>
    <select name={field.name} className="form-control select form-select" aria-describedby={`${id}_helptext`} id={id} value={value} disabled={disabled} onChange={e => onChange(e.target.value)}>
      {field.choices.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
    </select>
    <div id={`${id}_helptext`} className="form-text">{field.help_text}</div>
  </div></div>;
}

const FORM_ENDPOINT = "web/users/bulk-credentials/";

function BulkForm() {
  const [state, setState] = useWebResource(FORM_ENDPOINT, formValid);
  return renderLoad(state, "Cargando credenciales masivas…", data => ({
    title: "Credenciales masivas",
    breadcrumb: jobsBreadcrumb(<li className="breadcrumb-item active">Credenciales masivas</li>),
    content: <BulkFormContent data={data} forbidden={d => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(d) })} />,
  }));
}

function BulkFormContent({ data, forbidden }: { data: FormPayload; forbidden: (data: unknown) => void }) {
  const [errors, setErrors] = useState(data.errors); const [sendType, setSendType] = useState(data.values.tipo_envio);
  const [pending, setPending] = useState(false); const [uncertain, setUncertain] = useState(false); const [revision, setRevision] = useState(0);
  const busy = useRef(false); const form = useRef<HTMLFormElement>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    // "Descargar plantilla" keeps the native GET form submission (formaction/formmethod).
    const submitter = (event.nativeEvent as SubmitEvent).submitter;
    if (submitter?.getAttribute("formmethod") === "get") return;
    event.preventDefault(); if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    const body = new FormData(); body.append("tipo_envio", sendType);
    const file = (form.current?.elements.namedItem("archivo") as HTMLInputElement | null)?.files?.[0];
    if (file) body.append("archivo", file);
    const result = await postOnce(FORM_ENDPOINT, body, "/usuarios/credenciales-masivas/lotes/");
    if (result.kind === "redirect") { navigation.assign(result.to); return; }
    if (result.kind === "forbidden") { forbidden(result.data); return; }
    if (result.kind === "invalid" && formValid(result.data) && Object.keys(result.data.errors).length) {
      // The native page re-renders the bound form: the file input starts empty.
      setErrors(result.data.errors); setSendType(result.data.values.tipo_envio); setRevision(r => r + 1); busy.current = false;
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
      restartKeyboardFromTop();
    } else setUncertain(true);
    setPending(false);
  }
  const disabled = pending || uncertain;
  const [tipo, archivo] = data.fields;
  return <>
    {HITOS_STYLESHEET}
    <InsumosToastList messages={data.messages} />
    <div className="row justify-content-center"><div className="col-12 col-lg-8"><div className="card shadow-sm">
      <div className="card-header"><h3 className="mb-0">{data.form_title}</h3></div>
      <div className="card-body">
        <p className="text-muted">Seleccione el tipo de envio, descargue la plantilla correspondiente y luego cargue una planilla <code>.xlsx</code>. El sistema validara el archivo y creara un lote persistido. El correo se enviara al mail informado en la planilla y no se actualizaran mails ni passwords. El procesamiento se ejecuta fuera de la request web para evitar cortes por timeout y permitir reanudar desde la fila fallida.</p>
        <div className="alert alert-light border">
          <div className="font-weight-bold mb-2">Tipos disponibles</div>
          <ul className="mb-0 pl-3">
            {data.send_type_options.map(option => <li key={option.key}>
              <strong>{option.label}</strong>{`: ${option.description} Encabezados: `}
              {option.required_columns.map((column, index) => <Fragment key={column}><code>{column}</code>{index < option.required_columns.length - 1 && " , "}</Fragment>)}
            </li>)}
          </ul>
        </div>
        <div className="alert alert-info">
          <div className="font-weight-bold mb-2">Reglas de envio</div>
          <ul className="mb-0 pl-3">
            <li><code>usuario</code> es la llave de busqueda y nunca se modifica.</li>
            <li><code>mail</code> es el destino preferido del correo. Puede no coincidir con el mail guardado del usuario.</li>
            <li>Si <code>mail</code> esta vacio, se usa el mail cargado en el usuario.</li>
            <li>Si ambos mails faltan o el mail resultante es invalido, la fila falla con causa explicita.</li>
            <li>No se actualiza el mail ni la password del usuario desde esta planilla.</li>
            <li>La password enviada es la contrasena temporal vigente visible del usuario.</li>
          </ul>
        </div>
        <form ref={form} method="post" encType="multipart/form-data" noValidate onSubmit={submit}>
          <CsrfInput />
          {uncertain && <p role="alert">No se pudo confirmar el resultado. Revise los ultimos lotes antes de volver a cargar el archivo.</p>}
          <SelectInput field={tipo} value={sendType} onChange={setSendType} disabled={disabled} />
          <FileField field={archivo} errors={errors} disabled={disabled} inputKey={revision} />
          <div className="d-flex flex-wrap gap-2">
            <button type="submit" className="btn btn-outline-primary" formAction={data.template_download_url} formMethod="get" formNoValidate>Descargar plantilla</button>
            <button type="submit" className="btn btn-success" disabled={disabled}>Crear lote</button>
            <a href="/usuarios/" className="btn btn-secondary">Volver</a>
          </div>
        </form>
        <hr className="my-4" />
        {data.recent_jobs.length ? <>
          <h4 className="mb-3">Ultimos lotes</h4>
          <div className="table-responsive"><table className="table table-bordered table-hover align-middle mb-0">
            <thead><tr><th scope="col">Lote</th><th scope="col">Fecha</th><th scope="col">Estado</th><th scope="col">Tipo</th><th scope="col">Ultimo usuario enviado</th><th scope="col">Error</th><th scope="col">Detalle</th></tr></thead>
            <tbody>{data.recent_jobs.map(job => <tr key={job.id}>
              <td>{`#${job.id}`}</td><td>{job.requested_at}</td><td> <StatusBadge status={job.status} /> </td><td>{job.send_type}</td>
              <td>{job.last_successful_username ? <>{`${job.last_successful_username} `}{job.last_successful_row ? <small className="text-muted d-block">{`Fila ${job.last_successful_row}`}</small> : null}</> : "-"}</td>
              <td>{job.last_error_message || "-"}</td>
              <td> <a href={job.detail_url} className="btn btn-sm btn-outline-primary">Ver detalle</a> </td>
            </tr>)}</tbody>
          </table></div>
        </> : <div className="alert alert-light border mb-0">Todavia no hay lotes creados para credenciales masivas.</div>}
      </div>
    </div></div></div>
  </>;
}

function BulkJob({ id }: { id: string }) {
  const [state, setState] = useWebResource(`web/users/bulk-credentials/jobs/${id}/${window.location.search}`, detailValid);
  return renderLoad(state, "Cargando lote…", data => ({
    title: "Detalle de lote de credenciales",
    backHref: "/usuarios/credenciales-masivas/", // native volver_url: reverse("usuarios_credenciales_masivas")
    breadcrumb: jobsBreadcrumb(<><li className="breadcrumb-item"><a href={data.upload_url}>Credenciales masivas</a></li><li className="breadcrumb-item active">{`Lote #${data.job.id}`}</li></>),
    content: <BulkJobContent data={data} forbidden={d => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(d) })} />,
  }));
}

function BulkJobContent({ data, forbidden }: { data: Detail; forbidden: (data: unknown) => void }) {
  const { job } = data; const detailUrl = `/usuarios/credenciales-masivas/lotes/${job.id}/`;
  const counter = (label: string, value: number) => <div className="col-sm-6 col-xl-3"><div className="border rounded p-3 h-100"><div className="text-muted small">{label}</div><div className="h4 mb-0">{value}</div></div></div>;
  const last = (title: string, username: string, row: number | null, empty: string) => <div className="col-md-6"><div className="alert alert-light border mb-0 h-100">
    <div className="font-weight-bold mb-2">{title}</div>
    {username ? <><div>{username}</div><small className="text-muted">{`Fila ${row || "-"}`}</small></> : <div className="text-muted">{empty}</div>}
  </div></div>;
  return <>
    {HITOS_STYLESHEET}
    <InsumosToastList messages={data.messages} />
    <div className="row justify-content-center"><div className="col-12 col-xl-10"><div className="card shadow-sm mb-4">
      <div className="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div><h3 className="mb-0">{`Lote #${job.id}`}</h3><small className="text-muted">{`${job.original_filename} | ${job.requested_at}`}</small></div>
        <div className="d-flex flex-wrap gap-2">
          <a href={detailUrl} className="btn btn-outline-primary">Actualizar estado</a>
          {data.is_resume_available && <ResumeButton endpoint={`web/users/bulk-credentials/jobs/${job.id}/resume/`} expected={detailUrl} onForbidden={forbidden} />}
        </div>
      </div>
      <div className="card-body">
        <div className="mb-4">
          <StatusBadge status={job.status} />{" "}
          <span className="ml-2 text-muted">Tipo: <strong>{job.send_type}</strong></span>{" "}
          <span className="ml-2 text-muted">Reanudaciones: <strong>{job.resume_count}</strong></span>
        </div>
        <div className="row g-3 mb-4">
          {counter("Filas totales", job.total_rows)}
          {counter("Filas procesadas", job.processed_rows)}
          {counter("Enviadas", job.sent_rows)}
          {counter("Rechazadas", job.rejected_rows)}
        </div>
        <div className="row g-3 mb-4">
          {last("Ultimo usuario enviado correctamente", job.last_successful_username, job.last_successful_row, "Todavia no hay envios exitosos.")}
          {last("Ultimo usuario intentado", job.last_attempted_username, job.last_attempted_row, "Todavia no se intento ninguna fila.")}
        </div>
        {job.last_error_message ? <div className="alert alert-danger"><div className="font-weight-bold">Causa del error</div><div>{job.last_error_message}</div>{job.last_error_at && <small className="d-block mt-2">{`Registrado el ${job.last_error_at}`}</small>}</div>
          : (job.status === "processing" || job.status === "pending") && <div className="alert alert-info">{"El lote esta en curso fuera de la request web. Use "}<strong>Actualizar estado</strong> para refrescar el detalle.</div>}
        <div className="table-responsive"><table className="table table-bordered table-hover align-middle mb-0">
          <thead><tr><th scope="col">Fila</th><th scope="col">Usuario</th><th scope="col">Estado</th><th scope="col">Mail destino</th><th scope="col">Intentos</th><th scope="col">Detalle</th></tr></thead>
          <tbody>{data.rows.length ? data.rows.map(row => <tr key={row.id}><td>{row.fila}</td><td>{row.usuario || "-"}</td><td> {row.status === "sent" ? <span className="badge badge-success">Enviada</span> : <span className="badge badge-danger">Fallida</span>} </td><td>{row.mail_destino || "-"}</td><td>{row.attempts}</td><td>{row.mensaje || "-"}</td></tr>)
            : <tr><td colSpan={6} className="text-center text-muted py-4">Aun no hay filas procesadas para este lote.</td></tr>}</tbody>
        </table></div>
        <Pagination page={data.page} query={page => `?page=${page}`} />
      </div>
    </div></div></div>
  </>;
}

type BulkParams = { mode: "form" } | { mode: "job"; id: string };

export const bulkCredentialsRoute: RouteDefinition<BulkParams> = {
  name: "bulk-credentials",
  match(pathname) {
    if (pathname === "/usuarios/credenciales-masivas/") return { mode: "form" };
    const job = pathname.match(/^\/usuarios\/credenciales-masivas\/lotes\/([0-9]+)\/$/);
    return job ? { mode: "job", id: job[1] } : null;
  },
  render: params => params.mode === "form" ? <BulkForm /> : <BulkJob key={params.id} id={params.id} />,
};
