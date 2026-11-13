/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators live with the screen. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import type { RequiredPasswordPresentation } from "../RequiredPasswordChange";
import { safeInternalPath } from "../webAccess";
import DatacalleSelect2 from "./datacalleSelect2";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import Select2 from "./select2";
import { errorsValid, messagesValid, navigation, postOnce, presentationValid, record, type FieldErrors, type JobMessage } from "./userImport";

/**
 * `user/user_form.html` (core cards): personal data, access, DataCalle, Inspecciones escolares,
 * groups, territorial scope and access administration. The server decides which cards exist, which
 * fields are disabled and every error; the browser only draws the native markup, repeats the
 * visibility rules of `user_mobile_access.js`/`usuarioprovincial.js` and posts the enabled
 * controls. A rejected post re-renders the form with the bound values.
 */
type Value = string | boolean | string[];
type Choice = { value: string; label: string };
export type UsuarioField = {
  name: string;
  kind: "text" | "email" | "password" | "boolean" | "radio" | "select" | "multiselect" | "hidden";
  label: string;
  required: boolean;
  disabled: boolean;
  help_text: string;
  max_length: number | null;
  value: Value;
  choices?: Choice[];
};
type Section = { key: string; fields: UsuarioField[] };
type Scope = { provincia_id: string | number | null; municipio_id?: string | number | null; localidad_id?: string | number | null };
export type UsuarioFormData = {
  mode: "create" | "edit";
  title: string;
  object: { id: number; username: string } | null;
  sections: Section[];
  identity_present: string[];
  errors: FieldErrors;
  comedores: { sections: string[]; runtime_required: boolean };
  territorial: { initial: Scope[]; municipios_url: string; localidades_url: string };
  urls: { cancel: string };
  submit_text: string;
  credential: { temporary_password: string } | null;
  messages: JobMessage[];
  presentation: RequiredPasswordPresentation;
};

const KINDS = ["text", "email", "password", "boolean", "radio", "select", "multiselect", "hidden"];
const fieldValid = (f: unknown) => record(f) && typeof f.name === "string" && KINDS.includes(f.kind as string) && typeof f.label === "string" &&
  typeof f.required === "boolean" && typeof f.disabled === "boolean" && typeof f.help_text === "string" &&
  (f.max_length === null || typeof f.max_length === "number") &&
  (typeof f.value === "string" || typeof f.value === "boolean" || (Array.isArray(f.value) && f.value.every((v) => typeof v === "string"))) &&
  (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && typeof c.value === "string" && typeof c.label === "string")));

export function usuarioFormValid(v: unknown): v is UsuarioFormData {
  return record(v) && presentationValid(v.presentation) && (v.mode === "create" || v.mode === "edit") && typeof v.title === "string" &&
    typeof v.submit_text === "string" && Array.isArray(v.sections) &&
    v.sections.every((s) => record(s) && typeof s.key === "string" && Array.isArray(s.fields) && s.fields.every(fieldValid)) &&
    Array.isArray(v.identity_present) && v.identity_present.every((n) => typeof n === "string") && errorsValid(v.errors) &&
    record(v.comedores) && Array.isArray(v.comedores.sections) && record(v.territorial) && Array.isArray(v.territorial.initial) &&
    typeof v.territorial.municipios_url === "string" && typeof v.territorial.localidades_url === "string" &&
    record(v.urls) && safeInternalPath(v.urls.cancel) !== null && messagesValid(v.messages) &&
    (v.credential === null || (record(v.credential) && typeof v.credential.temporary_password === "string"));
}

const CARDS: Record<string, { id?: string; icon: string; title: string }> = {
  personal: { icon: "fas fa-user mr-4", title: "Datos Personales" },
  access: { icon: "fas fa-key mr-3", title: "Datos de Acceso" },
  datacalle: { id: "relevador-calle-card", icon: "fas fa-street-view mr-3", title: "Acceso SISOC - Mobile DataCalle" },
  inspecciones: { id: "inspecciones-escolares-card", icon: "fas fa-school mr-3", title: "Inspecciones escolares" },
  permissions: { id: "backoffice-permisos-card", icon: "fas fa-shield-alt mr-3", title: "Permisos y Roles" },
  territorial: { id: "backoffice-config-card", icon: "fas fa-map mr-3", title: "Alcance territorial" },
  delegation: { id: "backoffice-admin-card", icon: "fas fa-user-shield mr-3", title: "Administración de accesos" },
};
const INPUT_CLASS = { text: "textinput", email: "emailinput", password: "passwordinput" } as const;

type Values = Record<string, Value>;
type Api = {
  values: Values;
  errors: FieldErrors;
  busy: boolean;
  set: (name: string, value: Value) => void;
};

const text = (value: Value | undefined) => (typeof value === "string" ? value : "");
const list = (value: Value | undefined) => (Array.isArray(value) ? value : []);

function Errors({ name, errors, block = false }: { name: string; errors: FieldErrors; block?: boolean }) {
  return <>{(errors[name] ?? []).map((e, i) => <p id={`error_${i + 1}_id_${name}`} className={`invalid-feedback${block ? " d-block" : ""}`} style={block ? { paddingLeft: "1.5rem" } : undefined} key={i}><strong>{e.message}</strong></p>)}</>;
}
const Help = ({ spec }: { spec: UsuarioField }) => (spec.help_text ? <div id={`id_${spec.name}_helptext`} className="form-text">{spec.help_text}</div> : null);
const describedBy = (spec: UsuarioField) => (spec.help_text ? `id_${spec.name}_helptext` : undefined);

function Control({ spec, api, extra }: { spec: UsuarioField; api: Api; extra?: ReactNode }) {
  const { values, errors, busy, set } = api;
  const id = `id_${spec.name}`;
  const invalid = (errors[spec.name] ?? []).length > 0;
  const disabled = spec.disabled || busy;
  if (spec.kind === "boolean") {
    return (
      <div className="mb-3">
        <div id={`div_${id}`} className="form-check">
          <input type="checkbox" name={spec.name} className={`checkboxinput form-check-input${invalid ? " is-invalid" : ""}`} aria-describedby={describedBy(spec)} id={id}
            checked={values[spec.name] === true} disabled={disabled} onChange={(e) => set(spec.name, e.target.checked)} />{" "}
          <label htmlFor={id} className="form-check-label">{spec.label}</label>
          <Errors name={spec.name} errors={errors} />
          <Help spec={spec} />
        </div>
      </div>
    );
  }
  if (spec.kind === "radio") {
    return (
      <div id={`div_${id}`} className="mb-3">
        <fieldset aria-describedby={describedBy(spec)}>
          <legend className={`form-label${spec.required ? " requiredField" : ""} fs-6`}>{spec.label}{spec.required && <span className="asteriskField">*</span>}</legend>
          <div>
            {(spec.choices ?? []).map((choice, i) => (
              <div className="form-check" key={choice.value}>
                <input type="radio" className={`form-check-input${invalid ? " is-invalid" : ""}`} name={spec.name} value={choice.value} id={`${id}_${i}`} required={spec.required}
                  checked={values[spec.name] === choice.value} disabled={disabled} onChange={() => set(spec.name, choice.value)} />{" "}
                <label htmlFor={`${id}_${i}`} className="form-check-label">{choice.label}</label>
              </div>
            ))}
          </div>
          <Errors name={spec.name} errors={errors} block />
          <Help spec={spec} />
        </fieldset>
      </div>
    );
  }
  const multiple = spec.kind === "multiselect";
  const label = <label htmlFor={id} className={`form-label${spec.required ? " requiredField" : ""}`}>{spec.label}{spec.required && <span className="asteriskField">*</span>}</label>;
  let control: ReactNode;
  if (spec.kind === "select" || multiple) {
    control = <DatacalleSelect2 id={id} name={spec.name} multiple={multiple} className={`select2${multiple ? " selectmultiple" : ""} form-select`} choices={spec.choices ?? []}
      value={multiple ? list(values[spec.name]) : [text(values[spec.name])]} onChange={(v) => set(spec.name, multiple ? v : (v[0] ?? ""))}
      disabled={disabled} required={spec.required} invalid={invalid} describedBy={describedBy(spec)} />;
  } else {
    const kind = spec.kind === "email" || spec.kind === "password" ? spec.kind : "text";
    control = <input type={kind === "password" && extra === "visible" ? "text" : kind} name={spec.name} id={id} maxLength={spec.max_length ?? undefined}
      className={`${INPUT_CLASS[kind]} form-control${invalid ? " is-invalid" : ""}`} required={spec.required} aria-describedby={describedBy(spec)}
      value={text(values[spec.name])} disabled={disabled} autoComplete="off" onChange={(e) => set(spec.name, e.target.value)} />;
  }
  return <div id={`div_${id}`} className="mb-3">{label}{control}<Errors name={spec.name} errors={errors} /><Help spec={spec} /></div>;
}

function Credential({ credential }: { credential: UsuarioFormData["credential"] }) {
  if (!credential) return null;
  return (
    <div className="alert alert-warning" role="alert">
      <strong>Contraseña temporal vigente:</strong>{" "}
      <span className="ml-2">{credential.temporary_password}</span>
      <div className="small mt-2">Se mostrará aquí hasta que el usuario cambie su contraseña.</div>
    </div>
  );
}

function PasswordField({ spec, api }: { spec: UsuarioField; api: Api }) {
  const [visible, setVisible] = useState(false);
  return (
    <>
      <div id="password-field-wrapper">
        <Control spec={spec} api={api} extra={visible ? "visible" : undefined} />
        <button type="button" id="toggle-password" className="btn btn-sm btn-link p-0 mb-2" aria-pressed={visible} aria-label={visible ? "Ocultar la contraseña" : "Mostrar la contraseña"} onClick={() => setVisible(!visible)}>
          <i className={`fas ${visible ? "fa-eye-slash" : "fa-eye"}`} aria-hidden="true" />{" "}
          <span id="toggle-password-texto">{visible ? "Ocultar contraseña" : "Ver contraseña"}</span>
        </button>
      </div>
    </>
  );
}

type Option = { id: string | number; nombre: string };
type Row = { key: number; provincia: string; municipio: string; localidad: string; municipios: Option[] | null; localidades: Option[] | null };
export const territorialTransport = {
  async options(url: string, key: string, id: string): Promise<Option[]> {
    const target = new URL(url, window.location.origin);
    target.searchParams.set(key, id);
    const response = await fetch(target.toString(), { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" });
    return response.ok ? ((await response.json()) as Option[]) : [];
  },
};
const asId = (v: string | number | null | undefined) => (v === null || v === undefined ? "" : String(v));
const choicesOf = (options: Option[] | null, placeholder: string): Choice[] => [{ value: "", label: placeholder }, ...(options ?? []).map((o) => ({ value: String(o.id), label: o.nombre }))];

function ScopeRows({ rows, setRows, provinces, data, busy }: { rows: Row[]; setRows: (update: (rows: Row[]) => Row[]) => void; provinces: Choice[]; data: UsuarioFormData; busy: boolean }) {
  const patch = (key: number, change: Partial<Row>) => setRows((current) => current.map((r) => (r.key === key ? { ...r, ...change } : r)));
  async function province(row: Row, value: string) {
    patch(row.key, { provincia: value, municipio: "", localidad: "", municipios: null, localidades: null });
    if (value) patch(row.key, { municipios: await territorialTransport.options(data.territorial.municipios_url, "provincia_id", value) });
  }
  async function municipality(row: Row, value: string) {
    patch(row.key, { municipio: value, localidad: "", localidades: null });
    if (value) patch(row.key, { localidades: await territorialTransport.options(data.territorial.localidades_url, "municipio_id", value) });
  }
  return (
    <tbody id="territorial-scopes-list">
      {rows.map((row) => (
        <tr key={row.key}>
          <td><Select2 id={`scope-${row.key}-provincia`} name="" choices={[{ value: "", label: "Seleccione provincia" }, ...provinces]} value={[row.provincia]} onChange={(v) => void province(row, v[0] ?? "")} selectClassName="form-control form-control-sm" selectProps={{ "aria-label": "Provincia" }} noResults="No results found" disabled={busy} /></td>
          <td><Select2 id={`scope-${row.key}-municipio`} name="" choices={choicesOf(row.municipios, row.provincia ? "Todos los municipios" : "Seleccione provincia primero")} value={[row.municipio]} onChange={(v) => void municipality(row, v[0] ?? "")} selectClassName="form-control form-control-sm" selectProps={{ "aria-label": "Municipio" }} noResults="No results found" disabled={busy || !row.municipios?.length} /></td>
          <td><Select2 id={`scope-${row.key}-localidad`} name="" choices={choicesOf(row.localidades, row.municipio ? "Todas las localidades" : "Seleccione municipio primero")} value={[row.localidad]} onChange={(v) => patch(row.key, { localidad: v[0] ?? "" })} selectClassName="form-control form-control-sm" selectProps={{ "aria-label": "Localidad" }} noResults="No results found" disabled={busy || !row.localidades?.length} /></td>
          <td className="text-right">
            <button type="button" className="btn btn-outline-danger btn-sm" disabled={busy} onClick={() => setRows((current) => current.filter((r) => r.key !== row.key))}>
              <i className="fas fa-trash" aria-hidden="true" />{" "}<span className="sr-only">Quitar alcance</span>
            </button>
          </td>
        </tr>
      ))}
    </tbody>
  );
}

const serialize = (rows: Row[]) => JSON.stringify(rows.map((r) => ({ provincia_id: r.provincia || null, municipio_id: r.municipio || null, localidad_id: r.localidad || null })));
let rowKey = 0;
const blank = (scope: Scope): Row => ({ key: ++rowKey, provincia: asId(scope.provincia_id), municipio: asId(scope.municipio_id), localidad: asId(scope.localidad_id), municipios: null, localidades: null });

function initialValues(data: UsuarioFormData): Values {
  const values: Values = {};
  data.sections.forEach((s) => s.fields.forEach((f) => { values[f.name] = f.value; }));
  return values;
}

export function UsuarioFormContent({ data: initial, endpoint, onForbidden }: { data: UsuarioFormData; endpoint: string; onForbidden: (data: unknown) => void }) {
  const [data, setData] = useState(initial);
  const [values, setValues] = useState<Values>(() => initialValues(initial));
  const [errors, setErrors] = useState<FieldErrors>(initial.errors);
  const [rows, setRows] = useState<Row[]>(() => initial.territorial.initial.map(blank));
  const [revision, setRevision] = useState(0);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const fields = data.sections.flatMap((s) => s.fields);
  const provinces = (fields.find((f) => f.name === "provincia")?.choices ?? []).filter((c) => c.value !== "");
  // The native script loads each row's options on start; the same here, once per initial row.
  useEffect(() => {
    let active = true;
    initial.territorial.initial.forEach((scope, index) => {
      void (async () => {
        if (!scope.provincia_id) return;
        const municipios = await territorialTransport.options(initial.territorial.municipios_url, "provincia_id", asId(scope.provincia_id));
        const localidades = scope.municipio_id ? await territorialTransport.options(initial.territorial.localidades_url, "municipio_id", asId(scope.municipio_id)) : null;
        if (active) setRows((current) => current.map((r, i) => (i === index && r.municipios === null ? { ...r, municipios, localidades } : r)));
      })();
    });
    return () => { active = false; };
  }, [initial]);
  const api: Api = { values, errors, busy: pending || uncertain, set: (name, value) => setValues((current) => ({ ...current, [name]: value })) };
  const provincial = values.es_usuario_provincial === true;
  const detail = (name: string, flag: string) => ({ id: name, style: values[flag] === true ? undefined : { display: "none" } });

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    const body = new URLSearchParams();
    fields.filter((f) => !f.disabled).forEach((f) => {
      const value = f.name === "territorial_scopes" ? (provincial ? serialize(rows) : "[]") : values[f.name];
      if (Array.isArray(value)) value.forEach((v) => body.append(f.name, v));
      else if (typeof value === "boolean") { if (value) body.append(f.name, "on"); }
      else if (value !== undefined && !(f.kind === "radio" && value === "")) body.append(f.name, value);
    });
    data.identity_present.forEach((name) => body.append("_identity_present", name));
    const result = await postOnce(endpoint, body, "/usuarios/");
    if (!mounted.current) return;
    if (result.kind === "redirect") { navigation.assign(result.to); return; }
    busy.current = false;
    if (result.kind === "forbidden") onForbidden(result.data);
    else if (result.kind === "invalid" && usuarioFormValid(result.data) && Object.keys(result.data.errors).length) {
      const next = result.data;
      setData(next); setValues(initialValues(next)); setErrors(next.errors); setRows(next.territorial.initial.map(blank)); setRevision((n) => n + 1); setPending(false);
      resetAfterRejectedPost();
    } else { setUncertain(true); setPending(false); }
  }

  const render = (section: Section) => {
    const card = CARDS[section.key];
    const by = (name: string) => section.fields.find((f) => f.name === name)!;
    const field = (name: string) => <Control spec={by(name)} api={api} />;
    let body: ReactNode;
    if (section.key === "personal") {
      body = <><div className="row"><div className="col-md-6">{field("first_name")}</div><div className="col-md-6">{field("last_name")}</div></div><div className="row"><div className="col-md-6">{field("dni")}</div><div className="col-md-6">{field("cuil")}</div></div>{field("tipo_usuario")}</>;
    } else if (section.key === "access") {
      body = <><Credential credential={data.credential} />{field("username")}{field("email")}<PasswordField spec={by("password")} api={api} /></>;
    } else if (section.key === "datacalle") {
      body = <><div id="relevador-calle-toggle-wrapper">{field("es_relevador_calle")}</div><div {...detail("relevador-calle-detalle-wrapper", "es_relevador_calle")}>{field("datacalle_rol")}{field("provincias_datacalle")}</div></>;
    } else if (section.key === "inspecciones") {
      body = <><div id="inspecciones-escolares-toggle-wrapper">{field("es_inspector_escolar")}</div><div {...detail("inspecciones-escolares-detalle-wrapper", "es_inspector_escolar")}>{field("inspecciones_rol")}</div></>;
    } else if (section.key === "permissions") {
      body = <>{field("groups")}{field("rol")}</>;
    } else if (section.key === "territorial") {
      body = (
        <>
          {field("es_usuario_provincial")}
          <div className="d-none" id="legacy-provincia-field">{field("provincia")}</div>
          <input type="hidden" name="territorial_scopes" id="id_territorial_scopes" value={provincial ? serialize(rows) : "[]"} readOnly />
          <div id="territorial-scopes-panel" className="mb-3" style={provincial ? undefined : { display: "none" }}>
            <label className="form-label d-block">Alcances territoriales</label>
            {(errors.territorial_scopes ?? []).length > 0 && <div className="invalid-feedback d-block mb-2">{errors.territorial_scopes.map((e) => e.message).join(" ")}</div>}
            <div className="table-responsive">
              <table className="table table-sm align-middle mb-2">
                <thead><tr><th scope="col">Provincia</th><th scope="col">Municipio</th><th scope="col">Localidad</th><th scope="col" className="text-right">Acción</th></tr></thead>
                <ScopeRows rows={rows} setRows={setRows} provinces={provinces} data={data} busy={pending || uncertain} />
              </table>
            </div>
            <button type="button" className="btn btn-outline-primary btn-sm" id="add-territorial-scope" disabled={pending || uncertain} onClick={() => setRows((current) => [...current, blank({ provincia_id: null })])}><i className="fas fa-plus mr-1" />Agregar alcance</button>
          </div>
        </>
      );
    } else {
      body = <>{section.fields.map((f) => <Control key={f.name} spec={f} api={api} />)}</>;
    }
    return (
      <div className="card card-custom mb-3 shadow-sm" id={card?.id} key={section.key}>
        <div className="card-header card-header-custom"><h5 className="mb-0"><i className={card?.icon} />{card?.title}</h5></div>
        <div className="card-body">{body}</div>
      </div>
    );
  };

  return (
    <>
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css" />
      <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
      <link rel="stylesheet" href="/static/custom/css/user_form.css" />
      <NativeToasts messages={data.messages} />
      <div className="row">
        <div className="col">
          <form key={revision} className="needs-validation" noValidate method="POST" autoComplete="off" onSubmit={submit}>
            <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
            {data.sections.map(render)}
            <div className="row">
              <div className="col-md-12">
                <div className="form-group mb-0 mt-3 d-flex justify-content-between">
                  <a href={safeInternalPath(data.urls.cancel) ?? "/usuarios/"} className="btn btn-secondary mb-3">Cancelar</a>
                  <div><button type="submit" className="btn btn-primary mb-3" disabled={pending || uncertain}><i className="fas fa-save me-1" /> {data.submit_text}</button></div>
                </div>
              </div>
            </div>
            {uncertain && <p role="alert">No se pudo confirmar el resultado. Revise el listado antes de reintentar.</p>}
          </form>
        </div>
      </div>
    </>
  );
}
