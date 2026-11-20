/* eslint-disable react-refresh/only-export-components -- the form screen, its validator and its replaceable lookup live together. */
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { client, csrfToken, integer, internal, messagesValid, navigation, record, renderCdf, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import DatacalleSelect2, { type Choice } from "./datacalleSelect2";

/**
 * DC01.02: `datacalle/relevamiento_form.html` (create and edit). Crispy
 * Bootstrap 5 fields, its inline script (the phase shows the place field that
 * applies and validates it on submit; the province reloads municipalities,
 * localities, devices and team) and Select2. Saving runs the native form through
 * `/api/web/dispositivos/datacalle/`; 201/200 go to the native ficha (no message,
 * as native), 400 renders the bound form. A POST is never retried.
 */
const API = "web/dispositivos/datacalle/relevamientos/";
const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";
const AREA_REQUIRED = "Indicá el área operativa del espacio público.";
const DISPOSITIVO_REQUIRED = "Elegí el dispositivo de alojamiento.";

type Field = {
  name: string; label: string; required: boolean; disabled: boolean; widget: string; help_text: string;
  value: string | string[] | boolean; attrs: Record<string, string>; choices?: Choice[];
};
type FieldError = { message: string; code: string };
export type RelevamientoFormData = {
  titulo: string; fields: Field[]; errors: Record<string, FieldError[]>; non_field_errors: string[]; can_add_dispositivo: boolean;
  urls: { cancel: string; add_dispositivo: string; municipios: string; localidades: string; dispositivos: string; relevadores: string };
  messages: CdfMessage[];
};

const choicesValid = (v: unknown) => Array.isArray(v) && v.every((c) => record(c) && text(c.value) && text(c.label));
const fieldValid = (f: unknown): f is Field => record(f) && text(f.name) && text(f.label) && typeof f.required === "boolean" &&
  typeof f.disabled === "boolean" && text(f.widget) && text(f.help_text) &&
  (text(f.value) || typeof f.value === "boolean" || (Array.isArray(f.value) && f.value.every(text))) &&
  record(f.attrs) && Object.values(f.attrs).every(text) && (f.choices === undefined || choicesValid(f.choices));

export function formValid(v: unknown): v is RelevamientoFormData {
  if (!record(v) || !record(v.urls) || !record(v.errors)) return false;
  return text(v.titulo) && Array.isArray(v.fields) && v.fields.every(fieldValid) &&
    Object.values(v.errors).every((list) => Array.isArray(list) && list.every((e) => record(e) && text(e.message) && text(e.code))) &&
    Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && typeof v.can_add_dispositivo === "boolean" &&
    ["cancel", "add_dispositivo", "municipios", "localidades", "dispositivos", "relevadores"].every((k) => internal((v.urls as Record<string, unknown>)[k])) &&
    messagesValid(v.messages);
}

type Row = { id: number; nombre: string };
/** The template's `fetch(url + '?' + params)`, same session; replaceable in tests. */
export const lookups = {
  load: (url: string): Promise<unknown> => fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } }).then((r) => r.json()),
};
const rowsValid = (v: unknown): v is Row[] => Array.isArray(v) && v.every((r) => record(r) && integer(r.id) && text(r.nombre));

const CASCADE = ["municipio", "localidades", "dispositivo", "equipo"] as const;
type Cascade = (typeof CASCADE)[number];

function Help({ id, text: help }: { id: string; text: string }) {
  return help ? <div id={`${id}_helptext`} className="form-text">{help}</div> : null;
}

function Errors({ id, errors }: { id: string; errors: FieldError[] }) {
  return errors.length ? (
    <div id={`${id}_error`} className="invalid-feedback">
      {errors.map((e, i) => <p key={i} id={`error_${i + 1}_${id}`}><strong>{e.message}</strong></p>)}
    </div>
  ) : null;
}

const describedBy = (field: Field, id: string, errors: FieldError[]) =>
  [field.help_text && `${id}_helptext`, errors.length && `${id}_error`].filter(Boolean).join(" ") || undefined;

/** `{{ field|as_crispy_field }}` (crispy-bootstrap5) around one control. */
function Crispy({ field, errors, control, asterisk = false, inline }: { field: Field; errors: FieldError[]; control: ReactNode; asterisk?: boolean; inline?: string }) {
  const id = `id_${field.name}`;
  return (
    <div id={`div_${id}`} className="mb-3">
      <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>
        {field.label}{field.required && <span className="asteriskField">*</span>}
        {/* The script appends its asterisk after the label's trailing whitespace. */}
        {asterisk && !field.required && <>{" "}<span className="asteriskField">*</span></>}
      </label>
      {control}
      <Errors id={id} errors={errors} />
      <Help id={id} text={field.help_text} />
      {inline && <div className="invalid-feedback d-block dc-error-inline">{inline}</div>}
    </div>
  );
}

function FormFields({ data, endpoint, onInvalid }: { data: RelevamientoFormData; endpoint: string; onInvalid: (body: RelevamientoFormData) => void }) {
  const fields = new Map(data.fields.map((f) => [f.name, f]));
  const list = (name: string) => {
    const v = fields.get(name)?.value;
    return Array.isArray(v) ? v : typeof v === "string" && v !== "" ? [v] : [];
  };
  const [values, setValues] = useState<Record<string, string[]>>(() =>
    Object.fromEntries(data.fields.filter((f) => f.choices !== undefined).map((f) => [f.name, list(f.name)])));
  const [options, setOptions] = useState<Record<Cascade, Choice[]>>(() =>
    Object.fromEntries(CASCADE.map((n) => [n, fields.get(n)?.choices ?? []])) as Record<Cascade, Choice[]>);
  const [inline, setInline] = useState<{ area_operativa?: string; dispositivo?: string }>({});
  const [state, setState] = useState<"idle" | "sending" | "uncertain">("idle");
  const area = useRef<HTMLInputElement>(null);
  const fase = values.fase?.[0] ?? "";
  const publico = fase === "espacio_publico";
  const alojamiento = fase === "dispositivo_alojamiento";
  const set = (name: string, value: string[]) => setValues((v) => ({ ...v, [name]: value }));

  async function cargar(url: string, param: string, value: string, name: Cascade, emptyLabel: string | null) {
    const base = (label: string | null) => (label === null ? [] : [{ value: "", label }]);
    set(name, []);
    if (!value) { setOptions((o) => ({ ...o, [name]: base(emptyLabel) })); return; }
    setOptions((o) => ({ ...o, [name]: base("Cargando...") }));
    let rows: Choice[] = [];
    try {
      const body = await lookups.load(`${url}?${new URLSearchParams({ [param]: value })}`);
      rows = rowsValid(body) ? body.map((r) => ({ value: String(r.id), label: r.nombre })) : [];
    } catch {
      rows = [];
    }
    setOptions((o) => ({ ...o, [name]: [...base(emptyLabel), ...rows] }));
  }
  function onProvincia(value: string) {
    void cargar(data.urls.municipios, "provincia_id", value, "municipio", "Seleccionar municipio...");
    set("localidades", []);
    setOptions((o) => ({ ...o, localidades: [] }));
    void cargar(data.urls.dispositivos, "provincia_id", value, "dispositivo", "Seleccionar dispositivo...");
    void cargar(data.urls.relevadores, "provincia_id", value, "equipo", null);
  }
  function onFase(value: string) {
    if (value !== "espacio_publico") setInline((i) => ({ ...i, area_operativa: undefined }));
    if (value !== "dispositivo_alojamiento") setInline((i) => ({ ...i, dispositivo: undefined }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state !== "idle") return;
    // The template's submit check (QA-0009): the form is `novalidate`.
    if (publico && !(area.current?.value ?? "").trim()) {
      setInline((i) => ({ ...i, area_operativa: AREA_REQUIRED }));
      area.current?.focus();
      return;
    }
    if (alojamiento && !(values.dispositivo?.[0] ?? "")) {
      setInline((i) => ({ ...i, dispositivo: DISPOSITIVO_REQUIRED }));
      return;
    }
    setState("sending");
    try {
      const { data: body, status } = await client.post(endpoint, new FormData(event.currentTarget), { validateStatus: (s: number) => s === 200 || s === 201 || s === 400 });
      if ((status === 200 || status === 201) && record(body) && internal(body.url)) { navigation.assign(body.url); return; }
      if (status === 400 && formValid(body)) { onInvalid(body); return; }
      setState("uncertain");
    } catch {
      setState("uncertain");
    }
  }

  const errorsOf = (name: string) => data.errors[name] ?? [];
  const select = (name: string, onPick?: (value: string) => void) => {
    const field = fields.get(name)!;
    const errors = errorsOf(name);
    const multiple = field.widget === "selectmultiple";
    const choices = (CASCADE as readonly string[]).includes(name) ? options[name as Cascade] : field.choices ?? [];
    return (
      <DatacalleSelect2 id={`id_${name}`} name={name} className={multiple ? "select2 selectmultiple form-select" : "select2 form-select"}
        multiple={multiple} choices={choices} value={values[name] ?? []} disabled={field.disabled} required={field.required}
        invalid={errors.length > 0 || (name === "dispositivo" && !!inline.dispositivo)} describedBy={describedBy(field, `id_${name}`, errors)}
        onChange={(v) => {
          set(name, v);
          if (name === "dispositivo") setInline((i) => ({ ...i, dispositivo: undefined }));
          onPick?.(v[0] ?? "");
        }} />
    );
  };
  const crispySelect = (name: string, onPick?: (value: string) => void, extra: { asterisk?: boolean; inline?: string } = {}) => {
    const field = fields.get(name)!;
    return <Crispy field={field} errors={errorsOf(name)} control={select(name, onPick)} {...extra} />;
  };
  const input = (name: string, type: "text" | "date", extra: { asterisk?: boolean; inline?: string; required?: boolean } = {}) => {
    const field = fields.get(name)!;
    const errors = errorsOf(name);
    const id = `id_${name}`;
    const invalid = errors.length > 0 || !!extra.inline;
    return (
      <Crispy field={field} errors={errors} asterisk={extra.asterisk} inline={extra.inline} control={
        <input ref={name === "area_operativa" ? area : undefined} type={type} name={name} defaultValue={String(field.value)} maxLength={field.attrs.maxlength ? Number(field.attrs.maxlength) : undefined}
          className={`${type === "date" ? "dateinput" : "textinput"} form-control${invalid ? " is-invalid" : ""}`}
          required={field.required || extra.required || undefined} aria-invalid={errors.length ? "true" : undefined}
          aria-describedby={describedBy(field, id, errors)} id={id}
          onInput={name === "area_operativa" ? () => setInline((i) => ({ ...i, area_operativa: undefined })) : undefined} />
      } />
    );
  };
  const papel = fields.get("modalidad_papel")!;
  const observaciones = fields.get("observaciones")!;

  return (
    <form method="post" noValidate onSubmit={submit}>
      <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
      {state === "uncertain" && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
      {data.non_field_errors.length > 0 && <ul className="errorlist nonfield">{data.non_field_errors.map((m, i) => <li key={i}>{m}</li>)}</ul>}
      <Seccion icon="fa-tag" titulo="Identificación">
        <div className="row"><div className="col-12">{input("denominacion", "text")}</div></div>
      </Seccion>
      <Seccion icon="fa-map-marked-alt" titulo="Dónde se releva" ayuda="La fase define si el lugar es un área del espacio público o un dispositivo de alojamiento.">
        <div className="row">
          <div className="col-md-4">{crispySelect("provincia", onProvincia)}</div>
          <div className="col-md-4">{crispySelect("municipio", (v) => void cargar(data.urls.localidades, "municipio_id", v, "localidades", null))}</div>
          <div className="col-md-4">{crispySelect("localidades")}</div>
          <div className="col-md-4">{crispySelect("fase", onFase)}</div>
          <div className="col-md-8" id="campo-area-operativa" style={publico ? undefined : { display: "none" }}>
            {input("area_operativa", "text", { asterisk: publico, inline: inline.area_operativa, required: publico })}
          </div>
          <div className="col-md-8" id="campo-dispositivo" style={alojamiento ? undefined : { display: "none" }}>
            {crispySelect("dispositivo", undefined, { asterisk: alojamiento, inline: inline.dispositivo })}
            {data.can_add_dispositivo && (
              <p className="dc-form-seccion__ayuda mb-3">
                {" "}¿No está en la lista?{" "}
                <a href={data.urls.add_dispositivo} target="_blank" rel="noopener">Dar de alta un dispositivo</a>{" "}
                y volvé a elegir la provincia para recargarlo.{" "}
              </p>
            )}
          </div>
        </div>
      </Seccion>
      <Seccion icon="fa-calendar-alt" titulo="Cuándo" ayuda="Puede durar un día o varios.">
        <div className="row align-items-center">
          <div className="col-md-4">{input("fecha_inicio", "date")}</div>
          <div className="col-md-4">{input("fecha_fin", "date")}</div>
          <div className="col-md-4">
            <div className="mb-3">
              <div id="div_id_modalidad_papel" className="form-check">
                <input type="checkbox" name="modalidad_papel" className={`checkboxinput form-check-input${errorsOf("modalidad_papel").length ? " is-invalid" : ""}`}
                  aria-describedby={describedBy(papel, "id_modalidad_papel", errorsOf("modalidad_papel"))} id="id_modalidad_papel" defaultChecked={papel.value === true} />{" "}
                <label htmlFor="id_modalidad_papel" className="form-check-label"> {papel.label} </label>{" "}
                <Errors id="id_modalidad_papel" errors={errorsOf("modalidad_papel")} />
                <Help id="id_modalidad_papel" text={papel.help_text} />
              </div>
            </div>
          </div>
        </div>
      </Seccion>
      <Seccion icon="fa-users" titulo="Equipo" ayuda="Sólo los entrevistadores elegidos ven el operativo en la app.">
        <div className="row">
          <div className="col-12">{crispySelect("equipo")}</div>
          <div className="col-12">
            <Crispy field={observaciones} errors={errorsOf("observaciones")} control={
              <textarea name="observaciones" cols={Number(observaciones.attrs.cols ?? 40)} rows={Number(observaciones.attrs.rows ?? 3)}
                className={`textarea form-control${errorsOf("observaciones").length ? " is-invalid" : ""}`} id="id_observaciones"
                aria-describedby={describedBy(observaciones, "id_observaciones", errorsOf("observaciones"))} defaultValue={String(observaciones.value)} />
            } />
          </div>
        </div>
      </Seccion>
      <div className="dc-form-acciones">
        <button type="submit" className="btn btn-primary" disabled={state !== "idle" || undefined}><i className="fas fa-save mr-1" /> Guardar{" "}</button>{" "}
        <a href={data.urls.cancel} className="btn btn-secondary">Cancelar</a>
      </div>
    </form>
  );
}

function Seccion({ icon, titulo, ayuda, children }: { icon: string; titulo: string; ayuda?: string; children: ReactNode }) {
  return (
    <div className="dc-form-seccion">
      <div className="dc-form-seccion__header">
        <h2 className="dc-form-seccion__titulo"><i className={`fas ${icon}`} />{titulo}</h2>
        {ayuda && <>{" "}<span className="dc-form-seccion__ayuda">{ayuda}</span></>}
      </div>{" "}
      <div className="dc-form-seccion__body">{children}</div>
    </div>
  );
}

/** The native 400 is a new page: top of the document, nothing focused. */
function freshPage() {
  const body = document.body;
  body.setAttribute("tabindex", "-1");
  body.focus({ preventScroll: true });
  body.removeAttribute("tabindex");
  window.scrollTo(0, 0);
}

export function RelevamientoFormContent({ data, endpoint }: { data: RelevamientoFormData; endpoint: string }) {
  // A 400 replaces the whole form with the bound one, as the native re-render does.
  const [form, setForm] = useState({ data, version: 0 });
  return (
    <>
      {/* `includes/base.html` loads both for every native page; the shell does not. */}
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css" />
      <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
      <link rel="stylesheet" href="/static/custom/css/datacalle.css" />
      <div className="dc-header">
        <div>
          <h1 className="dc-header__title">{form.data.titulo}</h1>
          <div className="dc-header__meta">
            <span><i className="fas fa-mobile-alt" />El operativo le llega como tarea a los entrevistadores del equipo</span>
          </div>
        </div>
      </div>
      <FormFields key={form.version} data={form.data} endpoint={endpoint} onInvalid={(body) => { setForm((f) => ({ data: body, version: f.version + 1 })); freshPage(); }} />
    </>
  );
}

export function RelevamientoForm({ id }: { id?: string }) {
  const state = useCdfPage(id ? `${API}${id}/formulario/` : `${API}formulario/`, formValid);
  return renderCdf(state, (data) => ({
    title: data.titulo,
    breadcrumb: null,
    content: <RelevamientoFormContent data={data} endpoint={id ? `${API}${id}/editar/` : `${API}crear/`} />,
  }));
}
