/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent, type MouseEvent, type ReactNode } from "react";
import { sameOriginTarget } from "./cdiObservaciones";
import { bajaValid, BajaContent, type BajaData } from "./comedorIntervencionesBaja";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import { useCardCollapse } from "./relevamientos";
import type { RouteDefinition } from "./types";

/**
 * CO06 comedor observations: `observacion_form.html` (create and edit), `observacion_detail.html`
 * and `observacion_confirm_delete.html` (the shared `delete_confirm.html`). Data and POSTs go through
 * `/api/web/comedores/observaciones/`, which runs the native views (user scope, server-side author and
 * date, soft delete); a confirmed redirect is a full-page navigation like the native 302.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Comedor = { id: number; nombre: string; url: string };
type FieldError = { message: string; code: string };
export type ObservacionFormData = {
  comedor: Comedor; observacion_id: number | null; urls: { comedores: string; observacion: string | null };
  field: { name: "observacion"; label: string; required: boolean; rows: number; placeholder: string };
  value: string; errors: Record<string, FieldError[]>; messages: Message[];
};
export type ObservacionDetailData = {
  id: number; comedor: Comedor; observador: string; fecha: string; observacion: string;
  urls: { comedores: string; editar: string; eliminar: string }; messages: Message[];
};
export type ObservacionBajaData = BajaData & { comedor: Comedor; urls: { comedores: string } };

const API = "web/comedores/observaciones/";
const LEVELS = ["success", "error", "warning", "info"];
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const messagesValid = (v: unknown) => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
const comedorValid = (v: unknown): v is Comedor => record(v) && integer(v.id) && text(v.nombre) && internal(v.url);

export function formValid(v: unknown): v is ObservacionFormData {
  if (!record(v) || !record(v.field) || !record(v.errors) || !record(v.urls)) return false;
  const f = v.field;
  return comedorValid(v.comedor) && (v.observacion_id === null || integer(v.observacion_id)) && internal(v.urls.comedores) &&
    (v.urls.observacion === null || internal(v.urls.observacion)) && f.name === "observacion" && text(f.label) && typeof f.required === "boolean" &&
    integer(f.rows) && text(f.placeholder) && text(v.value) && messagesValid(v.messages) &&
    Object.values(v.errors).every((list) => Array.isArray(list) && list.every((e) => record(e) && text(e.message)));
}

export function detailValid(v: unknown): v is ObservacionDetailData {
  return record(v) && integer(v.id) && comedorValid(v.comedor) && text(v.observador) && text(v.fecha) && text(v.observacion) && record(v.urls) &&
    internal(v.urls.comedores) && internal(v.urls.editar) && internal(v.urls.eliminar) && messagesValid(v.messages);
}

export function bajaObservacionValid(v: unknown): v is ObservacionBajaData {
  return bajaValid(v) && comedorValid((v as Record<string, unknown>).comedor) && record((v as Record<string, unknown>).urls) &&
    internal(((v as Record<string, unknown>).urls as Record<string, unknown>).comedores);
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const observacionesNavigation = { assign: (to: string) => window.location.assign(to) };

const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";

/** `<div class="breadcrumb-item">` blocks sit directly in the `ol` of these templates. */
const crumb = (children: ReactNode, active = false) => <div className={`breadcrumb-item${active ? " active" : ""}`}>{children}</div>;

function ObservacionForm({ data, endpoint }: { data: ObservacionFormData; endpoint: string }) {
  const [state, setState] = useState({ data, revision: 0 });
  const [value, setValue] = useState(data.value);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState("");
  const busy = useRef(false);
  const current = state.data;
  const field = current.field;
  const errors = current.errors[field.name] ?? [];
  const invalid = errors.length > 0;
  const id = `id_${field.name}`;
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    let message = UNCERTAIN;
    try {
      const { data: response, status } = await webClient.post(endpoint, new URLSearchParams({ observacion: value }), { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403 });
      if (status === 400 && formValid(response)) {
        setState((s) => ({ data: response, revision: s.revision + 1 })); setValue(response.value);
        busy.current = false; setPending(false); resetAfterRejectedPost();
        return;
      }
      const to = status < 300 && record(response) && response.ok === true ? sameOriginTarget(response.redirect) : null;
      if (to) { observacionesNavigation.assign(to); return; }
      if (status === 403 && record(response) && text(response.detail)) message = response.detail;
    } catch {
      // Network error or timeout after sending: the result is unknown.
    }
    busy.current = false; setPending(false); setUncertain(message);
  }
  const back = (event: MouseEvent) => { event.preventDefault(); window.history.back(); };
  return <>
    <NativeToasts messages={current.messages} />
    <div className="row">
      <div className="col-12">
        <div className="card card-primary card-outline">
          <div className="bs-stepper">
            <div className="card-header mb-3">
              <h3 className="card-title">Agregar observacion al comedor: <a href={current.comedor.url}>{current.comedor.nombre}</a></h3>
            </div>
            <div className="card-body">
              <div className="form-row justify-content-center">
                <form method="post" className="w-100" onSubmit={submit}>
                  <div id={`div_${id}`} className="mb-3">
                    <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>
                      {field.label}{field.required && <span className="asteriskField">*</span>}
                    </label>
                    <textarea name={field.name} cols={40} rows={field.rows} className={`form-control textarea${invalid ? " is-invalid" : ""}`} placeholder={field.placeholder}
                      required={field.required} aria-invalid={invalid ? "true" : undefined} aria-describedby={invalid ? `${id}_error` : undefined} id={id} value={value}
                      onChange={(event) => setValue(event.target.value)} />
                    {invalid && (
                      <div id={`${id}_error`} className="invalid-feedback">
                        {errors.map((error, index) => <p key={index} id={`error_${index + 1}_${id}`}><strong>{error.message}</strong></p>)}
                      </div>
                    )}
                  </div>
                  <button className="btn btn-primary mx-1" type="submit" disabled={pending || !!uncertain}>Confirmar</button>
                  {" "}<a className="btn btn-secondary print mr-1 d-none d-sm-inline" onClick={() => window.print()}>Imprimir</a>
                  {" "}<a href="#" data-history-back="true" className="btn btn-secondary" onClick={back}>Cancelar</a>
                  {uncertain && <p role="alert" className="mb-0">{uncertain}</p>}
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </>;
}

function FormPage({ endpoint }: { endpoint: string }) {
  const [state] = useMainResource(endpoint, formValid);
  return renderMain(state, "Cargando observación…", (data) => ({
    title: `Observacion - Espacio Comunitario: ${data.comedor.nombre}`,
    heading: "Observacion",
    breadcrumb: <ol className="breadcrumb float-sm-right px-3">
      <li className="breadcrumb-item"><a href={data.urls.comedores}>Espacios Comunitarios</a></li>
      <li className="breadcrumb-item"><a href={data.comedor.url}>{data.comedor.nombre}</a></li>
      {data.urls.observacion
        ? <><li className="breadcrumb-item"><a href={data.urls.observacion}>{data.observacion_id}</a></li><li className="breadcrumb-item active">Editar</li></>
        : <li className="breadcrumb-item active">Agregar</li>}
    </ol>,
    content: <ObservacionForm key={endpoint} data={data} endpoint={endpoint} />,
  }));
}

function DetailContent({ data }: { data: ObservacionDetailData }) {
  useCardCollapse();
  return <>
    <NativeToasts messages={data.messages} />
    <div className="row justify-content-sm-start justify-content-between d-print-none mx-1 mb-2">
      <a href={data.urls.editar} className="btn btn-primary mr-1">Editar</a>
      {" "}<a href="#" className="btn btn-secondary print mr-1 d-none d-sm-inline" onClick={(e) => { e.preventDefault(); window.print(); }}>Imprimir</a>
      {" "}<a href={data.urls.eliminar} className="btn btn-danger">Eliminar</a>
    </div>
    <div className="card">
      <div className="card-header">
        <h3 className="card-title font-weight-bold mr-3 pt-1">Información</h3>
        <div className="card-tools"><button type="button" className="btn btn-tool" data-card-widget="collapse"><i className="fas fa-minus" /></button></div>
      </div>
      <div className="card-body card-comments p-0 pb-1">
        <div className="nav nav-pills row my-3">
          <div className="nav-item col-6 d-flex justify-content-center">
            <div className="comment-text comment-text d-flex flex-column align-items-center">Usuario observador<span className="username">{data.observador}</span></div>
          </div>
          <div className="nav-item col-6 d-flex justify-content-center">
            <div className="comment-text comment-text d-flex flex-column align-items-center">Fecha y hora de observacion<span className="username">{data.fecha}</span></div>
          </div>
        </div>
        <div className="nav nav-pills row my-3">
          <div className="nav-item col-12 d-flex justify-content-center">
            <div className="comment-text comment-text d-flex flex-column align-items-center">Observacion<span className="username">{data.observacion}</span></div>
          </div>
        </div>
      </div>
    </div>
  </>;
}

function DetailPage({ pk }: { pk: string }) {
  const [state] = useMainResource(`${API}${pk}/`, detailValid);
  return renderMain(state, "Cargando observación…", (data) => ({
    title: `Observacion - Espacio Comunitario: ${data.comedor.nombre}`,
    heading: `Observacion ${data.id} - Comedor: ${data.comedor.nombre}`,
    breadcrumb: <ol className="breadcrumb float-sm-right">
      {crumb(<a href={data.urls.comedores}>Espacios Comunitarios</a>)}
      {crumb(<a href={data.comedor.url}>{data.comedor.nombre}</a>)}
      {crumb(<>Observacion {data.id}</>, true)}
    </ol>,
    content: <DetailContent data={data} />,
  }));
}

function BajaPage({ pk }: { pk: string }) {
  const endpoint = `${API}${pk}/eliminar/`;
  const [state] = useMainResource(endpoint, bajaObservacionValid);
  return renderMain(state, "Cargando observación…", (data) => ({
    title: `Espacio Comunitario - ${data.comedor.nombre}`,
    breadcrumb: <ol className="breadcrumb float-sm-right">
      {crumb(<a href={data.urls.comedores}>Espacios Comunitarios</a>)}
      {crumb(<a href={data.comedor.url}>{data.comedor.nombre}</a>)}
      {crumb(<a href={data.cancel_url}>Observacion - {data.id}</a>, true)}
      {crumb("Eliminar")}
    </ol>,
    content: <BajaContent data={data} endpoint={endpoint} />,
  }));
}

type Params = { page: "create"; comedor: string } | { page: "detail" | "edit" | "delete"; pk: string };

// Native URLs of `comedores/urls.py`: none ends in a slash.
const CREATE = /^\/comedores\/(\d+)\/observacion\/crear$/;
const OWN = /^\/comedores\/observacion\/(\d+)(?:\/(editar|eliminar))?$/;

export const comedorObservacionesRoute: RouteDefinition<Params> = {
  name: "comedores-observaciones",
  match(pathname) {
    const create = CREATE.exec(pathname);
    if (create) return { page: "create", comedor: create[1] };
    const own = OWN.exec(pathname);
    if (!own) return null;
    return { page: own[2] === "editar" ? "edit" : own[2] === "eliminar" ? "delete" : "detail", pk: own[1] };
  },
  render(params) {
    // The native form posts to its own URL, so `next` travels in the query string.
    if (params.page === "create") return <FormPage key={params.comedor} endpoint={`${API}comedor/${params.comedor}/crear/${window.location.search}`} />;
    if (params.page === "edit") return <FormPage key={params.pk} endpoint={`${API}${params.pk}/editar/`} />;
    return params.page === "detail" ? <DetailPage key={params.pk} pk={params.pk} /> : <BajaPage key={params.pk} pk={params.pk} />;
  },
};
