/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { sameOriginTarget } from "./cdiObservaciones";
import { bajaValid, BajaContent, type BajaData } from "./comedorIntervencionesBaja";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * RM01.02 monthly rendición forms: `rendicioncuentasmensual_form.html` (create, with the
 * `rendicioncuentasmensual_form.js` rows of attached files), `rendicioncuentasmensual_datos_form.html`
 * (edit the general data) and `rendicioncuentasmensual_confirm_delete.html` (the shared
 * `delete_confirm.html`). Data and POSTs go through `/api/web/comedores/rendicioncuentasmensual/`, which
 * runs the native views; a confirmed redirect is a full-page navigation like the native 302.
 * Create options and validation come from the bound Django form.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Choice = { value: string; label: string };
type FieldError = { message: string; code: string };
type Campo = { name: string; label: string; required: boolean; value: string; choices?: Choice[]; maxlength?: number; rows?: number };
type FormBase = { errors: Record<string, FieldError[]>; non_field_errors: string[]; messages: Message[] };
export type RendicionNuevaData = FormBase & {
  comedor_id: number; titulo: string; urls: { listado: string };
  campos: Record<"mes" | "anio" | "linea_programatica" | "estado" | "observaciones" | "nombre" | "archivo", Campo>;
};
export type RendicionEditarData = FormBase & {
  id: number; numero: string; urls: { detalle: string };
  campos: Record<"convenio" | "numero_rendicion" | "periodo_inicio" | "periodo_fin" | "nombre", Campo>;
};
export type RendicionBajaData = BajaData;

const API = "web/comedores/rendicioncuentasmensual/";
const LEVELS = ["success", "error", "warning", "info"];
const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const campoValid = (v: unknown): v is Campo => record(v) && text(v.name) && text(v.label) && typeof v.required === "boolean" && text(v.value) &&
  (v.choices === undefined || (Array.isArray(v.choices) && v.choices.every((c) => record(c) && text(c.value) && text(c.label)))) &&
  (v.maxlength === undefined || integer(v.maxlength)) && (v.rows === undefined || integer(v.rows));
const camposValid = (v: unknown, names: string[]) => record(v) && names.every((n) => campoValid(v[n]) && (v[n] as Campo).name === n);
const baseValid = (v: Record<string, unknown>) => record(v.errors) &&
  Object.values(v.errors).every((list) => Array.isArray(list) && list.every((e) => record(e) && text(e.message) && text(e.code))) &&
  Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) &&
  Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));

export function nuevaValid(v: unknown): v is RendicionNuevaData {
  return record(v) && baseValid(v) && integer(v.comedor_id) && text(v.titulo) && record(v.urls) && internal(v.urls.listado) &&
    camposValid(v.campos, ["mes", "anio", "linea_programatica", "estado", "observaciones", "nombre", "archivo"]);
}

export function editarValid(v: unknown): v is RendicionEditarData {
  return record(v) && baseValid(v) && integer(v.id) && text(v.numero) && record(v.urls) && internal(v.urls.detalle) &&
    camposValid(v.campos, ["convenio", "numero_rendicion", "periodo_inicio", "periodo_fin", "nombre"]);
}

export function bajaRendicionValid(v: unknown): v is RendicionBajaData {
  return bajaValid(v);
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const rendicionFormNavigation = { assign: (to: string) => window.location.assign(to) };

type Kind = "select" | "text" | "number" | "date" | "textarea" | "file";
const CLASSES: Record<Kind, string> = {
  select: "form-control select form-select", text: "form-control textinput", number: "form-control numberinput", date: "dateinput form-control",
  textarea: "form-control textarea", file: "form-control form-control",
};

/** The crispy wrapper of one field (`as_crispy_field`): label with asterisk, control and inline errors. */
function Field({ campo, kind, errors, classes, bare }: { campo: Campo; kind: Kind; errors: FieldError[]; classes?: string; bare?: boolean }) {
  const id = `id_${campo.name}`;
  const invalid = errors.length > 0;
  const common = {
    name: campo.name, id, className: `${classes ?? CLASSES[kind]}${invalid ? " is-invalid" : ""}`, required: campo.required || undefined,
    "aria-invalid": invalid ? ("true" as const) : undefined, "aria-describedby": invalid ? `${id}_error` : undefined,
  };
  let control: ReactNode;
  if (kind === "select") {
    control = <select {...common} defaultValue={campo.value}>{(campo.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}</select>;
  } else if (kind === "textarea") {
    control = <textarea {...common} cols={40} rows={campo.rows} defaultValue={campo.value} />;
  } else if (kind === "file") {
    control = <div><input type="file" {...common} /></div>;
  } else {
    control = <input type={kind} {...common} maxLength={campo.maxlength} defaultValue={campo.value} />;
  }
  return (
    <div id={`div_${id}`} className="mb-3">
      <label htmlFor={id} className={`form-label${campo.required ? " requiredField" : ""}`}>
        {campo.label}{campo.required && <span className="asteriskField">*</span>}
      </label>
      {control}
      {invalid && !bare && (
        <div id={`${id}_error`} className="invalid-feedback">
          {errors.map((e, i) => <p key={i} id={`error_${i + 1}_${id}`}><strong>{e.message}</strong></p>)}
        </div>
      )}
    </div>
  );
}

const csrf = () => <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;

type Outcome<T> = { kind: "rejected"; data: T } | { kind: "uncertain"; message: string } | { kind: "redirected" };

/** One POST; a 400 with a valid payload is the rejected form, a confirmed redirect navigates. */
async function send<T>(endpoint: string, body: FormData | URLSearchParams, valid: (v: unknown) => v is T): Promise<Outcome<T>> {
  let message = UNCERTAIN;
  try {
    const { data, status } = await webClient.post(endpoint, body, { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403 });
    if (status === 400 && valid(data)) return { kind: "rejected", data };
    const to = status < 300 && record(data) && data.ok === true ? sameOriginTarget(data.redirect) : null;
    if (to) { rendicionFormNavigation.assign(to); return { kind: "redirected" }; }
    if (status === 403 && record(data) && text(data.detail)) message = data.detail;
  } catch {
    // Network error or timeout after sending: the result is unknown.
  }
  return { kind: "uncertain", message };
}

/** Shared submit state: one request at a time, and a failed one blocks the form until reload. */
function useSubmit<T>(valid: (v: unknown) => v is T, initial: T, build: (form: HTMLFormElement) => FormData | URLSearchParams, endpoint: string, onRejected?: () => void) {
  const [state, setState] = useState({ data: initial, revision: 0 });
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState("");
  const busy = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    const outcome = await send(endpoint, build(event.currentTarget), valid);
    if (outcome.kind === "redirected") return;
    busy.current = false; setPending(false);
    if (outcome.kind === "rejected") {
      setState((s) => ({ data: outcome.data, revision: s.revision + 1 }));
      onRejected?.();
      resetAfterRejectedPost();
    } else setUncertain(outcome.message);
  }
  return { ...state, pending, uncertain, submit };
}

const Alert = ({ message }: { message: string }) => message ? <p role="alert" className="mb-0">{message}</p> : null;

// --- Create ----------------------------------------------------------------------

function NuevaForm({ data, endpoint }: { data: RendicionNuevaData; endpoint: string }) {
  // Each row has its own key, so clearing a row (or the whole list) remounts its inputs empty.
  const [rows, setRows] = useState({ keys: [0], next: 1 });
  const form = useSubmit(nuevaValid, data, (element) => new FormData(element), endpoint, () => setRows((s) => ({ keys: [s.next], next: s.next + 1 })));
  const { campos, errors, non_field_errors: general } = form.data;
  const errorsOf = (name: string) => errors[name] ?? [];
  // `rendicioncuentasmensual_form.js`: add clones the last row empty; remove drops the last, or clears the only one.
  const add = () => setRows((s) => ({ keys: [...s.keys, s.next], next: s.next + 1 }));
  const remove = () => setRows((s) => (s.keys.length > 1 ? { ...s, keys: s.keys.slice(0, -1) } : { keys: [s.next], next: s.next + 1 }));
  return <>
    <NativeToasts messages={form.data.messages} />
    <div className="container mt-4">
      <h2 className="mb-4">{form.data.titulo} Seguimiento mensual</h2>
      <form method="post" encType="multipart/form-data" onSubmit={form.submit} key={form.revision}>
        {csrf()}
        {general.length > 0 && <ul role="alert" className="errorlist nonfield">{general.map((m, i) => <li key={i}>{m}</li>)}</ul>}
        <div className="row">
          <div className="col-md-6">
            <div className="card">
              <div className="card-header bg-primary text-white"><h5>Datos asociados</h5></div>
              <div className="card-body">
                <Field campo={campos.mes} kind="select" errors={errorsOf("mes")} />
                <Field campo={campos.anio} kind="number" errors={errorsOf("anio")} />
                <Field campo={campos.linea_programatica} kind="select" errors={errorsOf("linea_programatica")} />
                <Field campo={campos.estado} kind="select" errors={errorsOf("estado")} />
                <Field campo={campos.observaciones} kind="textarea" errors={errorsOf("observaciones")} />
              </div>
            </div>
          </div>
          <div className="col-md-6">
            <div className="card">
              <div className="card-header bg-secondary text-white"><h5>Documentación Adjunta</h5></div>
              <div className="card-body" id="documentacion-container">
                {rows.keys.map((key) => (
                  <div key={key} className="documentacion-item d-flex align-items-center">
                    <div className="flex-grow-1">
                      <Field campo={campos.nombre} kind="text" errors={errorsOf("nombre")} />
                      <Field campo={campos.archivo} kind="file" errors={errorsOf("archivo")} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="card-footer text-end d-flex justify-content-between">
                <button type="button" className="btn btn-primary" id="add-documentacion" onClick={add}>Agregar Archivo</button>
                <button type="button" className="btn btn-danger btn-sm" id="remove-documentacion" onClick={remove}>Eliminar Archivo</button>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-4 text-center">
          <button type="submit" className="btn btn-success" disabled={form.pending || !!form.uncertain}>Guardar</button>
          {" "}<a href={form.data.urls.listado} className="btn btn-secondary">Cancelar</a>
          <Alert message={form.uncertain} />
        </div>
      </form>
    </div>
  </>;
}

function NuevaPage({ comedor }: { comedor: string }) {
  const endpoint = `${API}nuevo/${comedor}/`;
  const [state] = useMainResource(endpoint, nuevaValid);
  return renderMain(state, "Cargando rendición…", (data) => ({
    title: "Detalle de Rendición de Cuenta",
    breadcrumb: <ol className="breadcrumb float-sm-right">
      <li className="breadcrumb-item"><a href={data.urls.listado} title="Ver listado de rendiciones">Rendiciones de Cuenta</a></li>
      <li className="breadcrumb-item active">{data.titulo} Rendición</li>
    </ol>,
    content: <NuevaForm key={endpoint} data={data} endpoint={endpoint} />,
  }));
}

// --- Edit ------------------------------------------------------------------------

function EditarForm({ data, endpoint }: { data: RendicionEditarData; endpoint: string }) {
  const form = useSubmit(editarValid, data, (element) => new URLSearchParams(Array.from(new FormData(element), ([k, v]) => [k, String(v)])), endpoint);
  const { campos, errors, non_field_errors: general } = form.data;
  const errorsOf = (name: string) => errors[name] ?? [];
  return <>
    <NativeToasts messages={form.data.messages} />
    <div className="container mt-4">
      <div className="card">
        <div className="card-header bg-primary text-white"><h5 className="mb-0">Editar datos de rendición</h5></div>
        <div className="card-body">
          <p className="text-muted small">
            Los datos vienen precargados. Lo que dejes igual conserva su valor;
            no hace falta completar de nuevo los campos que no cambian.
          </p>
          <form method="post" onSubmit={form.submit} key={form.revision}>
            {csrf()}
            {general.length > 0 && <ul className="errorlist nonfield">{general.map((m, i) => <li key={i}>{m}</li>)}</ul>}
            <Field campo={campos.convenio} kind="select" errors={errorsOf("convenio")} classes="select form-select" />
            <Field campo={campos.numero_rendicion} kind="select" errors={errorsOf("numero_rendicion")} classes="select form-select" />
            <Field campo={campos.periodo_inicio} kind="date" errors={errorsOf("periodo_inicio")} />
            <Field campo={campos.periodo_fin} kind="date" errors={errorsOf("periodo_fin")} />
            <Field campo={campos.nombre} kind="text" errors={errorsOf("nombre")} classes="textinput form-control" />
            <div className="mt-4 text-center">
              <button type="submit" className="btn btn-success" disabled={form.pending || !!form.uncertain}>Guardar</button>
              {" "}<a href={form.data.urls.detalle} className="btn btn-secondary">Cancelar</a>
              <Alert message={form.uncertain} />
            </div>
          </form>
        </div>
      </div>
    </div>
  </>;
}

function EditarPage({ pk }: { pk: string }) {
  const endpoint = `${API}editar/${pk}/`;
  const [state] = useMainResource(endpoint, editarValid);
  return renderMain(state, "Cargando rendición…", (data) => ({
    title: "Editar datos de rendición",
    breadcrumb: <ol className="breadcrumb float-sm-right">
      <li className="breadcrumb-item"><a href={data.urls.detalle} title="Volver al detalle de la rendición">Rendición {data.numero}</a></li>
      <li className="breadcrumb-item active">Editar datos</li>
    </ol>,
    content: <EditarForm key={endpoint} data={data} endpoint={endpoint} />,
  }));
}

// --- Delete ----------------------------------------------------------------------

function BajaPage({ pk }: { pk: string }) {
  const endpoint = `${API}eliminar/${pk}/`;
  const [state] = useMainResource(endpoint, bajaRendicionValid);
  return renderMain(state, "Cargando rendición…", (data) => ({
    title: "Acciones",
    breadcrumb: <ol className="breadcrumb float-sm-right">
      {/* The template has `href=""` (this very page) and, in the second item, an attribute that does not exist: an empty link. */}
      <li className="breadcrumb-item"><a href={`${window.location.pathname}${window.location.search}`} title="Ver listado de admisiones">Seguimiento mensual</a></li>
      <li className="breadcrumb-item "><a href={data.cancel_url} title="Ver ciudadano" /></li>
      <li className="breadcrumb-item active">Eliminar</li>
    </ol>,
    content: <BajaContent data={data} endpoint={endpoint} />,
  }));
}

type Params = { page: "nuevo" | "editar" | "eliminar"; id: string };

// Native URLs of `rendicioncuentasmensual/urls.py` under the runtime's `rendicioncuentasmensual/` include
// (the prefix is repeated on purpose).
const OWN = /^\/rendicioncuentasmensual\/rendicioncuentasmensual\/(nuevo|editar|eliminar)\/([0-9]+)\/$/;

export const rendicionMensualFormRoute: RouteDefinition<Params> = {
  name: "comedores-rendicion-mensual-form",
  match(pathname) {
    const found = OWN.exec(pathname);
    return found ? { page: found[1] as Params["page"], id: found[2] } : null;
  },
  render(params) {
    if (params.page === "nuevo") return <NuevaPage key={`n${params.id}`} comedor={params.id} />;
    return params.page === "editar" ? <EditarPage key={`e${params.id}`} pk={params.id} /> : <BajaPage key={`b${params.id}`} pk={params.id} />;
  },
};
