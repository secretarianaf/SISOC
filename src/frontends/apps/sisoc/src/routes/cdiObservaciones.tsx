/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { useRef, useState, type FormEvent, type MouseEvent } from "react";
import { leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "../webAccess";
import { client, internal, messagesValid, navigation, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import type { RouteDefinition } from "./types";

/**
 * CDI07 observation screens (`centrodeinfancia/observacion_*.html`): create,
 * detail, edit and soft-delete confirmation. The native views stay the
 * authority through `/api/web/cdi/`; a confirmed POST navigates to the native
 * redirect (detail, safe `next` or the centre page with its message).
 */
type Centro = { id: number; nombre: string; url: string };
type FieldError = { message: string; code: string };
type FormData_ = {
  centro: Centro;
  field: { name: "observacion"; label: string; required: boolean; rows: number; placeholder: string };
  value: string;
  errors: Record<string, FieldError[]>;
  messages: CdiMessage[];
};
type Detail = { id: number; centro: Centro; observador: string; fecha: string; observacion: string; urls: { editar: string; eliminar: string }; messages: CdiMessage[] };
type PreviewItem = { modelo: string; cantidad: number; modo: string; ejemplos: string[] };
type Confirm = {
  id: number; centro: Centro; object_name: string; confirm_text: string; cancel_text: string; cancel_url: string; messages: CdiMessage[];
  cascade_preview: { total_afectados: number; total_baja_logica: number; total_borrado_fisico: number; desglose_por_modelo: PreviewItem[] } | null;
};
type Params = { mode: "create"; centro: string } | { mode: "detail" | "edit" | "delete"; id: string };

const count = (v: unknown) => Number.isSafeInteger(v) && (v as number) >= 0;
const centroValid = (v: unknown): v is Centro => record(v) && Number.isSafeInteger(v.id) && text(v.nombre) && internal(v.url);
function formValid(v: unknown): v is FormData_ {
  if (!record(v) || !record(v.field) || !record(v.errors)) return false;
  const f = v.field;
  return centroValid(v.centro) && f.name === "observacion" && text(f.label) && typeof f.required === "boolean" && count(f.rows) && text(f.placeholder) &&
    text(v.value) && messagesValid(v.messages) &&
    Object.values(v.errors).every((list) => Array.isArray(list) && list.every((e) => record(e) && text(e.message)));
}
function detailValid(v: unknown): v is Detail {
  return record(v) && Number.isSafeInteger(v.id) && centroValid(v.centro) && text(v.observador) && text(v.fecha) && text(v.observacion) &&
    record(v.urls) && internal(v.urls.editar) && internal(v.urls.eliminar) && messagesValid(v.messages);
}
function confirmValid(v: unknown): v is Confirm {
  if (!record(v) || !Number.isSafeInteger(v.id) || !centroValid(v.centro) || !messagesValid(v.messages)) return false;
  const p = v.cascade_preview;
  const previewOk = p === null || (record(p) && count(p.total_afectados) && count(p.total_baja_logica) && count(p.total_borrado_fisico) &&
    Array.isArray(p.desglose_por_modelo) && p.desglose_por_modelo.every((i) => record(i) && text(i.modelo) && count(i.cantidad) && text(i.modo) && Array.isArray(i.ejemplos) && i.ejemplos.every(text)));
  return previewOk && text(v.object_name) && text(v.confirm_text) && text(v.cancel_text) && internal(v.cancel_url);
}

/** The native redirect target, only when it stays on this origin (`safe_redirect` may return an absolute URL). */
export function sameOriginTarget(value: unknown): string | null {
  if (typeof value !== "string") return null;
  if (value.startsWith("/")) return safeInternalPath(value);
  try {
    const url = new URL(value);
    return url.origin === window.location.origin ? safeInternalPath(`${url.pathname}${url.search}${url.hash}`) : null;
  } catch {
    return null;
  }
}

type PostResult = { kind: "redirect"; to: string } | { kind: "invalid"; data: unknown } | { kind: "forbidden"; data: unknown } | { kind: "uncertain" };

/** POST once, URL-encoded like the native form; an unconfirmed outcome is reported, never resubmitted. */
async function postOnce(endpoint: string, body: URLSearchParams): Promise<PostResult> {
  try {
    const { data, status } = await client.post(endpoint, body, { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403 });
    if (status === 400) return { kind: "invalid", data };
    if (status === 403) return { kind: "forbidden", data };
    const to = record(data) && data.ok === true ? sameOriginTarget(data.redirect) : null;
    return to ? { kind: "redirect", to } : { kind: "uncertain" };
  } catch {
    return { kind: "uncertain" };
  }
}

function useSubmit(endpoint: string) {
  const busy = useRef(false);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [forbidden, setForbidden] = useState<{ prerequisite: WebPrerequisite | null } | null>(null);
  async function send(body: URLSearchParams, onInvalid?: (data: unknown) => void) {
    if (busy.current) return;
    busy.current = true; setPending(true);
    const result = await postOnce(endpoint, body);
    if (result.kind === "redirect") { navigation.assign(result.to); return; }
    if (result.kind === "forbidden") setForbidden({ prerequisite: prerequisiteFromForbidden(result.data) });
    else if (result.kind === "invalid" && onInvalid) onInvalid(result.data);
    else setUncertain(true);
    busy.current = false; setPending(false);
  }
  return { send, pending, uncertain, forbidden };
}

function CsrfInput() {
  return <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;
}

const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";

function historyBack(event: MouseEvent) {
  event.preventDefault();
  window.history.back();
}

function ObservacionForm({ data, endpoint }: { data: FormData_; endpoint: string }) {
  const [value, setValue] = useState(data.value);
  const [errors, setErrors] = useState(data.errors);
  const { send, pending, uncertain, forbidden } = useSubmit(endpoint);
  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;
  const field = data.field;
  const fieldErrors = errors[field.name] ?? [];
  const invalid = fieldErrors.length > 0;
  const id = `id_${field.name}`;
  function submit(event: FormEvent) {
    event.preventDefault();
    send(new URLSearchParams({ observacion: value }), (body) => {
      if (formValid(body)) { setErrors(body.errors); setValue(body.value); } else setErrors({});
    });
  }
  return (
    <div className="row">
      <div className="col-12">
        <div className="card card-primary card-outline">
          <div className="card-header mb-3">
            <h3 className="card-title">
              Agregar observación al centro: <a href={data.centro.url}>{data.centro.nombre}</a>
            </h3>
          </div>
          <div className="card-body">
            <div className="form-row justify-content-center">
              <form method="post" className="w-100" onSubmit={submit}>
                <CsrfInput />
                <div id={`div_${id}`} className="mb-3">
                  <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>
                    {field.label}{field.required && <span className="asteriskField">*</span>}
                  </label>
                  <textarea name={field.name} cols={40} rows={field.rows} className={`form-control textarea${invalid ? " is-invalid" : ""}`}
                    placeholder={field.placeholder} required={field.required} aria-invalid={invalid ? "true" : undefined}
                    aria-describedby={invalid ? `${id}_error` : undefined} id={id} value={value} disabled={pending}
                    onChange={(event) => setValue(event.target.value)} />
                  {invalid && (
                    <div id={`${id}_error`} className="invalid-feedback">
                      {fieldErrors.map((error, index) => <p key={index} id={`error_${index + 1}_${id}`}><strong>{error.message}</strong></p>)}
                    </div>
                  )}
                </div>
                <button className="btn btn-primary mx-1" type="submit" disabled={pending || uncertain}>Confirmar</button>
                {" "}<a href="#" data-history-back="true" className="btn btn-secondary" onClick={historyBack}>Cancelar</a>
                {uncertain && <p role="alert" className="mb-0">{UNCERTAIN}</p>}
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailContent({ data }: { data: Detail }) {
  return <>
    <div className="row justify-content-sm-start justify-content-between d-print-none mx-1 mb-2">
      <a href={data.urls.editar} className="btn btn-primary mr-1">Editar</a>
      {" "}<a href={data.urls.eliminar} className="btn btn-danger">Eliminar</a>
    </div>
    <div className="card">
      <div className="card-header">
        <h3 className="card-title font-weight-bold mr-3 pt-1">Información</h3>
      </div>
      <div className="card-body">
        <p className="mb-2"><strong>Centro:</strong>{" "}<a href={data.centro.url}>{data.centro.nombre}</a></p>
        <p className="mb-2"><strong>Observador:</strong> {data.observador}</p>
        <p className="mb-2"><strong>Fecha y hora:</strong> {data.fecha}</p>
        <p className="mb-0"><strong>Observación:</strong> {data.observacion}</p>
      </div>
    </div>
  </>;
}

function ConfirmContent({ data, endpoint }: { data: Confirm; endpoint: string }) {
  const { send, pending, uncertain, forbidden } = useSubmit(endpoint);
  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;
  const preview = data.cascade_preview;
  function submit(event: FormEvent) {
    event.preventDefault();
    send(new URLSearchParams());
  }
  return (
    <div className="error-page mt-5 px-3">
      <div className="error-content">
        <h3><i className="fas fa-exclamation-triangle text-danger px-2" />{" "}Atención!</h3>
        <p>
          ¿Estás seguro que deseas realizar una baja lógica en cascada del registro
          {" "}<span className="font-weight-bold">{data.object_name}</span>?
        </p>
        {preview && <>
          <div className="alert alert-info">
            <div><strong>Total de registros afectados:</strong>{" "}{preview.total_afectados}</div>
            {preview.total_baja_logica > 0 && <div>Bajas lógicas: {preview.total_baja_logica}</div>}
            {preview.total_borrado_fisico > 0 && <div>Borrados físicos técnicos: {preview.total_borrado_fisico}</div>}
          </div>
          <div className="table-responsive mb-3">
            <table className="table table-sm table-striped mb-0">
              <thead><tr><th>Modelo</th><th>Cantidad</th><th>Acción</th><th>Ejemplos</th></tr></thead>
              <tbody>
                {preview.desglose_por_modelo.map((item, index) => (
                  <tr key={index}>
                    <td>{item.modelo}</td>
                    <td>{item.cantidad}</td>
                    <td>{item.modo === "baja_logica" ? "Baja lógica" : "Borrado físico técnico"}</td>
                    <td>{item.ejemplos.length ? item.ejemplos.join(", ") : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>}
        <div className="text-left">
          <form method="post" action="" onSubmit={submit}>
            <CsrfInput />
            <button type="submit" className="btn btn-danger btn-sm" disabled={pending || uncertain}>{data.confirm_text}</button>
            {" "}<a href={data.cancel_url} className="btn btn-secondary btn-sm">{data.cancel_text}</a>
            {uncertain && <p role="alert" className="mb-0">{UNCERTAIN}</p>}
          </form>
        </div>
      </div>
    </div>
  );
}

const FORM_TITLE = "Observación - Centro de Desarrollo Infantil";

function FormPage({ endpoint }: { endpoint: string }) {
  const [state] = useCdiPage(endpoint, formValid);
  return renderCdi(state, (data) => ({ title: FORM_TITLE, heading: "Observación", content: <ObservacionForm data={data} endpoint={endpoint} /> }));
}

function DetailPage({ endpoint }: { endpoint: string }) {
  const [state] = useCdiPage(endpoint, detailValid);
  return renderCdi(state, (data) => ({ title: `Observación - ${data.centro.nombre}`, heading: `Observación ${data.id}`, content: <DetailContent data={data} /> }));
}

function ConfirmPage({ endpoint }: { endpoint: string }) {
  const [state] = useCdiPage(endpoint, confirmValid);
  return renderCdi(state, (data) => ({ title: `Observación - ${data.centro.nombre}`, heading: "", content: <ConfirmContent data={data} endpoint={endpoint} /> }));
}

function ObservacionPage({ params }: { params: Params }) {
  if (params.mode === "create") {
    // The native form posts to its own URL, so `next` travels in the query string.
    return <FormPage endpoint={`web/cdi/centros/${params.centro}/observaciones/crear/${window.location.search}`} />;
  }
  const base = `web/cdi/observaciones/${params.id}/`;
  if (params.mode === "detail") return <DetailPage endpoint={base} />;
  if (params.mode === "edit") return <FormPage endpoint={`${base}editar/`} />;
  return <ConfirmPage endpoint={`${base}eliminar/`} />;
}

const CREATE = /^\/centrodeinfancia\/(\d+)\/observacion\/crear\/$/;
const OWN = /^\/centrodeinfancia\/observacion\/(\d+)\/(?:(editar|eliminar)\/)?$/;

// Native URLs of the CDI observation screens (CDI07); same trailing slashes.
export const cdiObservacionesRoute: RouteDefinition<Params> = {
  name: "cdi-observaciones",
  match: (pathname) => {
    const create = CREATE.exec(pathname);
    if (create) return { mode: "create", centro: create[1] };
    const own = OWN.exec(pathname);
    if (!own) return null;
    return { mode: own[2] === "editar" ? "edit" : own[2] === "eliminar" ? "delete" : "detail", id: own[1] };
  },
  render: (params) => <ObservacionPage params={params} />,
};
