/* eslint-disable react-refresh/only-export-components -- route module: the validator and the navigation seam are exported for the tests. */
import { Fragment, useRef, useState, type FormEvent } from "react";
import { sameOriginTarget } from "./cdiObservaciones";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CO03.01 comedor collaborators: `colaborador_form.html` (create with the citizen search and edit).
 * Data and POSTs go through `/api/web/comedores/colaboradores/`, which runs the native views
 * (scoped comedor, "linea secos" veto, local-then-RENAPER search, `ColaboradorEspacioService`).
 * The search is the native GET form (a page load); a confirmed redirect is a full-page navigation
 * like the native 302. A collaborator is not an access user: nothing here creates one.
 */
export type Message = { message: string; tags: string };
export type FieldError = { message: string; code: string };
type Choice = { value: string; label: string };
type Scalar = { label: string; required: boolean; html_required: boolean; value: string; max_length: number | null };
export type ColaboradorData = {
  comedor: { id: number; nombre: string; url: string };
  edit_mode: boolean;
  query: string;
  preview: Record<string, string> | null;
  source: "edicion" | "sisoc" | "renaper" | null;
  existing: boolean;
  not_found: boolean;
  hidden: { name: "ciudadano_id" | "dni"; value: string };
  form: {
    fields: {
      genero: Scalar & { choices: Choice[] };
      codigo_telefono: Scalar;
      numero_telefono: Scalar;
      fecha_alta: Scalar;
      fecha_baja: Scalar;
      actividades: { label: string; required: boolean; choices: (Choice & { checked: boolean })[] };
    };
    errors: Record<string, FieldError[]>;
  } | null;
  messages: Message[];
  urls: { comedor: string };
};

const API = "web/comedores/colaboradores/comedor/";
const PREVIEW_LABELS: [string, string][] = [
  ["apellido", "Apellido"], ["nombre", "Nombre"], ["dni", "DNI"], ["prefijo_cuil", "Prefijo CUIL"], ["cuil_cuit", "CUIT/CUIL"],
  ["sufijo_cuil", "Sufijo CUIL"], ["sexo", "Sexo"], ["fecha_nacimiento", "Fecha de nacimiento"], ["edad", "Edad"],
];
const SCALARS = ["genero", "codigo_telefono", "numero_telefono", "fecha_alta", "fecha_baja"] as const;
const choiceValid = (c: unknown): c is Choice => record(c) && text(c.value) && text(c.label);
const scalarValid = (f: unknown): boolean => record(f) && text(f.label) && typeof f.required === "boolean" && typeof f.html_required === "boolean" && text(f.value) &&
  (f.max_length === null || Number.isSafeInteger(f.max_length));

export function dataValid(v: unknown): v is ColaboradorData {
  if (!record(v) || !record(v.comedor) || !record(v.hidden) || !record(v.urls) || !Array.isArray(v.messages)) return false;
  const base = Number.isSafeInteger(v.comedor.id) && text(v.comedor.nombre) && internal(v.comedor.url) && typeof v.edit_mode === "boolean" && text(v.query) &&
    (v.preview === null || (record(v.preview) && PREVIEW_LABELS.every(([k]) => text((v.preview as Record<string, unknown>)[k])))) &&
    (v.source === null || ["edicion", "sisoc", "renaper"].includes(v.source as string)) && typeof v.existing === "boolean" && typeof v.not_found === "boolean" &&
    (v.hidden.name === "ciudadano_id" || v.hidden.name === "dni") && text(v.hidden.value) && internal(v.urls.comedor) &&
    v.messages.every((m) => record(m) && text(m.message) && text(m.tags));
  if (!base) return false;
  if (v.form === null) return true;
  if (!record(v.form) || !record(v.form.fields) || !record(v.form.errors)) return false;
  const fields = v.form.fields;
  const actividades = fields.actividades;
  return SCALARS.every((name) => scalarValid(fields[name])) && record(fields.genero) && Array.isArray(fields.genero.choices) && fields.genero.choices.every(choiceValid) &&
    record(actividades) && text(actividades.label) && typeof actividades.required === "boolean" && Array.isArray(actividades.choices) &&
    actividades.choices.every((c) => choiceValid(c) && typeof (c as Record<string, unknown>).checked === "boolean") &&
    Object.values(v.form.errors).every((list) => Array.isArray(list) && list.every((e) => record(e) && text(e.message)));
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const colaboradoresNavigation = { assign: (to: string) => window.location.assign(to) };

export const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";
const ERROR_STATUSES = (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403;

type Form = NonNullable<ColaboradorData["form"]>;
type Values = { genero: string; codigo_telefono: string; numero_telefono: string; fecha_alta: string; fecha_baja: string; actividades: string[] };
const initialValues = (form: Form): Values => ({
  genero: form.fields.genero.value, codigo_telefono: form.fields.codigo_telefono.value, numero_telefono: form.fields.numero_telefono.value,
  fecha_alta: form.fields.fecha_alta.value, fecha_baja: form.fields.fecha_baja.value,
  actividades: form.fields.actividades.choices.filter((c) => c.checked).map((c) => c.value),
});

/** crispy-bootstrap5 field errors block (`field_errors_block.html`). */
export function Errors({ id, errors }: { id: string; errors: FieldError[] }) {
  if (errors.length === 0) return null;
  return <div id={`${id}_error`} className="invalid-feedback">
    {errors.map((error, index) => <p key={index} id={`error_${index + 1}_${id}`}><strong>{error.message}</strong></p>)}
  </div>;
}

export function FieldLabel({ id, field }: { id: string; field: { label: string; required: boolean } }) {
  return <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>
    {field.label}{field.required && <span className="asteriskField">*</span>}
  </label>;
}

function ColaboradorForm({ data, form, endpoint, rejected }: { data: ColaboradorData; form: Form; endpoint: string; rejected: (data: ColaboradorData) => void }) {
  const [values, setValues] = useState(() => initialValues(form));
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState("");
  const busy = useRef(false);
  const { fields, errors } = form;
  const set = (patch: Partial<Values>) => setValues((v) => ({ ...v, ...patch }));
  const aria = (name: string) => (errors[name]?.length ? { "aria-invalid": "true" as const, "aria-describedby": `id_${name}_error` } : {});
  const cls = (name: string, base: string) => `${base}${errors[name]?.length ? " is-invalid" : ""}`;
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    const body = new URLSearchParams();
    body.append(data.hidden.name, data.hidden.value);
    for (const name of SCALARS) body.append(name, values[name]);
    for (const value of values.actividades) body.append("actividades", value);
    let message = UNCERTAIN;
    try {
      const { data: response, status } = await webClient.post(endpoint, body, { validateStatus: ERROR_STATUSES });
      if (status === 400 && dataValid(response)) {
        // The native page reloaded: the parent remounts this form with the bound values and the messages.
        rejected(response); resetAfterRejectedPost();
        return;
      }
      const to = status < 300 && record(response) && response.ok === true ? sameOriginTarget(response.redirect) : null;
      if (to) { colaboradoresNavigation.assign(to); return; }
      if (status === 403 && record(response) && text(response.detail)) message = response.detail;
    } catch {
      // Network error or timeout after sending: the result is unknown.
    }
    busy.current = false; setPending(false); setUncertain(message);
  }
  const genero = fields.genero;
  return <>
    <div className="card mb-3">
      <div className="card-header font-weight-bold">Datos del colaborador</div>
      <div className="card-body">
        <form method="post" noValidate onSubmit={(event) => void submit(event)}>
          <input type="hidden" name={data.hidden.name} value={data.hidden.value} />
          <div id="div_id_genero" className="mb-3">
            <FieldLabel id="id_genero" field={genero} />{" "}
            <select name="genero" className={cls("genero", "form-select")} id="id_genero" required={genero.html_required || undefined} value={values.genero}
              onChange={(e) => set({ genero: e.target.value })} {...aria("genero")}>
              {genero.choices.map((c) => <Fragment key={c.value}><option value={c.value}>{c.label}</option>{" "}</Fragment>)}
            </select>{" "}
            <Errors id="id_genero" errors={errors.genero ?? []} />
          </div>
          {(["codigo_telefono", "numero_telefono"] as const).map((name) => (
            <div key={name} id={`div_id_${name}`} className="mb-3">
              <FieldLabel id={`id_${name}`} field={fields[name]} />{" "}
              <input type="text" name={name} className={cls(name, "form-control textinput")} maxLength={fields[name].max_length ?? undefined} id={`id_${name}`}
                required={fields[name].html_required || undefined} value={values[name]} onChange={(e) => set({ [name]: e.target.value })} {...aria(name)} />{" "}
              <Errors id={`id_${name}`} errors={errors[name] ?? []} />
            </div>
          ))}
          {(["fecha_alta", "fecha_baja"] as const).map((name) => (
            <div key={name} id={`div_id_${name}`} className="mb-3">
              <FieldLabel id={`id_${name}`} field={fields[name]} />{" "}
              <input type="date" name={name} className={cls(name, "form-control dateinput")} id={`id_${name}`} required={fields[name].html_required || undefined}
                value={values[name]} onChange={(e) => set({ [name]: e.target.value })} {...aria(name)} />{" "}
              <Errors id={`id_${name}`} errors={errors[name] ?? []} />
            </div>
          ))}
          <div id="div_id_actividades" className="mb-3">
            <fieldset aria-describedby={errors.actividades?.length ? "id_actividades_error" : undefined}>
              <legend className={`form-label${fields.actividades.required ? " requiredField" : ""} fs-6`}>
                {fields.actividades.label}{fields.actividades.required && <span className="asteriskField">*</span>}
              </legend>{" "}
              <div>
                {fields.actividades.choices.map((choice, index, all) => {
                  const id = `id_actividades_${index}`;
                  const invalid = !!errors.actividades?.length;
                  return <div key={choice.value} className="form-check">
                    <input type="checkbox" className={`form-check-input${invalid ? " is-invalid" : ""}`} name="actividades" value={choice.value} id={id}
                      checked={values.actividades.includes(choice.value)} aria-invalid={invalid ? "true" : undefined}
                      onChange={(e) => set({ actividades: e.target.checked ? [...values.actividades, choice.value] : values.actividades.filter((v) => v !== choice.value) })} />{" "}
                    <label htmlFor={id} className="form-check-label">{choice.label}</label>
                    {index === all.length - 1 && <>{" "}<Errors id="id_actividades" errors={errors.actividades ?? []} /></>}
                  </div>;
                })}
              </div>
            </fieldset>
          </div>
          <button type="submit" className="btn btn-primary" disabled={pending || !!uncertain}>
            {pending
              ? <><span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" /> Guardando…</>
              : data.edit_mode ? "Guardar cambios" : "Guardar colaborador"}
          </button>
          {uncertain && <p role="alert" className="mb-0 mt-2">{uncertain}</p>}
        </form>
      </div>
    </div>
  </>;
}

const LEVELS = ["success", "error", "warning", "info"] as const;
/** The base template also shows every flash message as a toastr toast at the end of `<body>`. */
export const toasts = (messages: Message[]) => messages.map((m) => ({ message: m.message, level: LEVELS.find((l) => l === m.tags) ?? "info" }));

/** `{% for message in messages %}` of the template: dismissible Bootstrap alerts inside the container. */
export function Alerts({ messages }: { messages: Message[] }) {
  const [closed, setClosed] = useState<number[]>([]);
  return <>{messages.map((m, index) => closed.includes(index) ? null : (
    <div key={index} className={`alert alert-${m.tags} alert-dismissible fade show`} role="alert">
      {m.message}{" "}
      <button type="button" className="btn-close" aria-label="Cerrar" onClick={() => setClosed((c) => [...c, index])} />
    </div>
  ))}</>;
}

function Content({ initial, endpoint }: { initial: ColaboradorData; endpoint: string }) {
  const [state, setState] = useState({ data: initial, revision: 0 });
  const { data, revision } = state;
  const title = data.edit_mode ? "Editar colaborador del espacio" : "Agregar colaborador del espacio";
  const header = data.source === "edicion" ? "Ciudadano asociado" : data.source === "sisoc" ? "Ciudadano encontrado en SISOC" : "Datos obtenidos desde RENAPER";
  return <>
    <div className="container">
      <h2 className="text-center display-4 mb-4">{title}</h2>
      <Alerts key={revision} messages={data.messages} />
      <NativeToasts key={`t${revision}`} messages={toasts(data.messages)} />
      {!data.edit_mode && (
        <div className="card mb-3">
          <div className="card-header font-weight-bold">Buscar ciudadano por DNI</div>
          <div className="card-body">
            <form key={revision} method="get" className="form-inline">
              <div className="form-group mr-2">
                <label htmlFor="busqueda-dni" className="sr-only">DNI</label>{" "}
                <input type="text" className="form-control" name="query" id="busqueda-dni" placeholder="Ingrese DNI (mín. 7 dígitos)" defaultValue={data.query} />
              </div>{" "}
              <button className="btn btn-secondary mt-3" type="submit">Buscar</button>
            </form>
          </div>
        </div>
      )}
      {data.preview ? <>
        <div className="card mb-3">
          <div className="card-header font-weight-bold">{header}</div>
          <div className="card-body">
            <div className="row">
              {PREVIEW_LABELS.map(([key, label]) => (
                <div key={key} className="col-md-4 mb-2"><strong>{label}:</strong> {data.preview![key]}</div>
              ))}
            </div>
          </div>
        </div>
        {data.existing
          ? <div className="alert alert-warning">La persona ya se encuentra registrada como colaborador de este espacio.</div>
          : data.form && <ColaboradorForm key={revision} data={data} form={data.form} endpoint={endpoint.split("?")[0]} rejected={(response) => setState((s) => ({ data: response, revision: s.revision + 1 }))} />}
      </> : data.not_found && <div className="alert alert-info">No se encontraron datos para el DNI ingresado.</div>}
    </div>
  </>;
}

function Page({ endpoint }: { endpoint: string }) {
  const [state] = useMainResource(endpoint, dataValid);
  return renderMain(state, "Cargando colaborador…", (data) => {
    const label = data.edit_mode ? "Editar colaborador" : "Agregar colaborador";
    return {
      title: label,
      heading: "",
      breadcrumb: <ol className="breadcrumb float-sm-right">
        <li className="breadcrumb-item"><a href={data.urls.comedor}>Comedor</a></li>
        <li className="breadcrumb-item active">{label}</li>
      </ol>,
      content: <Content initial={data} endpoint={endpoint} />,
    };
  });
}

type Params = { page: "create"; comedor: string } | { page: "edit"; comedor: string; pk: string };

// Native URLs of `comedores/urls.py`, with their trailing slashes.
const CREATE = /^\/comedores\/(\d+)\/colaboradores\/crear\/$/;
const EDIT = /^\/comedores\/(\d+)\/colaboradores\/(\d+)\/editar\/$/;

export const comedorColaboradoresRoute: RouteDefinition<Params> = {
  name: "comedores-colaboradores",
  match(pathname) {
    const create = CREATE.exec(pathname);
    if (create) return { page: "create", comedor: create[1] };
    const edit = EDIT.exec(pathname);
    return edit ? { page: "edit", comedor: edit[1], pk: edit[2] } : null;
  },
  render(params) {
    // The native search is a GET form: `query`/`ciudadano_id` travel in the query string.
    if (params.page === "create") return <Page key={`c${params.comedor}${window.location.search}`} endpoint={`${API}${params.comedor}/crear/${window.location.search}`} />;
    return <Page key={`e${params.pk}`} endpoint={`${API}${params.comedor}/${params.pk}/editar/`} />;
  },
};
