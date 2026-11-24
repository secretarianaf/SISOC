/* eslint-disable react-refresh/only-export-components -- shared module of the destinatario form: controls, data types and validators. */
import type { ReactNode } from "react";
import { internal, messagesValid, record, text, type CdiMessage } from "./cdiFrame";
import { bloqueValid, lockProps, type BloqueConfig, type RenaperBloqueApi } from "./cdiRenaperBloque";
import { campoValid, CampoCrispy, describedBy, type CampoWeb } from "./cdiRenaperBloqueCampos";

/**
 * Data of the CDI destinatario create/edit page (`centrodeinfancia.web_api_destinatario`) and the
 * controls that draw it: the markup `{{ form.x|as_crispy_field }}` renders (Bootstrap 5).
 */
export type Campo = CampoWeb & { checked?: boolean };
export type Opcion = { id: string; value: string; label: string; checked: boolean };
export type Multiple = { label: string; required: boolean; errors: string[]; options: Opcion[] };
export type Ciudadano = { id: number; apellido: string; nombre: string; documento: string };
export type Busqueda = {
  query: string; ciudadanos: Ciudadano[]; no_resultados: boolean; renaper_precarga: boolean; renaper_prefill_token: string | null;
};
export type Centro = {
  id: number; nombre: string; url: string; nombre_visible: string; codigo_cdi: string; provincia: string;
  departamento: string; municipio: string; localidad: string;
};
export type DestinatarioData = {
  is_edit: boolean; centro: Centro; search: Busqueda | null; mostrar_formulario: boolean; selected: Ciudadano | null;
  renaper_prefill_token: string | null; non_field_errors: string[]; fields: Campo[]; multiples: Record<string, Multiple>;
  renaper: { nino: BloqueConfig | null; responsable_legal_1: BloqueConfig; responsable_legal_2: BloqueConfig };
  urls: { cancelar: string; departamentos: string; municipios: string; localidades: string }; messages: CdiMessage[];
  /** Client only: bumped after a rejected POST so the form restarts from the server state. */
  seq?: number;
};

const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text);
const ciudadanoValid = (c: unknown): c is Ciudadano => record(c) && Number.isSafeInteger(c.id) && text(c.apellido) && text(c.nombre) && text(c.documento);
const busquedaValid = (b: unknown): b is Busqueda => record(b) && text(b.query) && Array.isArray(b.ciudadanos) && b.ciudadanos.every(ciudadanoValid) &&
  typeof b.no_resultados === "boolean" && typeof b.renaper_prefill_token !== "undefined" && typeof b.renaper_precarga === "boolean" &&
  (b.renaper_prefill_token === null || text(b.renaper_prefill_token));
const multipleValid = (g: unknown): g is Multiple => record(g) && text(g.label) && typeof g.required === "boolean" && strings(g.errors) && Array.isArray(g.options) &&
  g.options.every((o) => record(o) && text(o.id) && text(o.value) && text(o.label) && typeof o.checked === "boolean");
const centroValid = (c: unknown): c is Centro => record(c) && Number.isSafeInteger(c.id) && internal(c.url) &&
  ["nombre", "nombre_visible", "codigo_cdi", "provincia", "departamento", "municipio", "localidad"].every((k) => text(c[k]));

export function destinatarioValid(v: unknown): v is DestinatarioData {
  if (!record(v) || !record(v.renaper) || !record(v.urls) || !record(v.multiples)) return false;
  const r = v.renaper;
  return typeof v.is_edit === "boolean" && centroValid(v.centro) && (v.search === null || busquedaValid(v.search)) &&
    typeof v.mostrar_formulario === "boolean" && (v.selected === null || ciudadanoValid(v.selected)) &&
    (v.renaper_prefill_token === null || text(v.renaper_prefill_token)) && strings(v.non_field_errors) &&
    Array.isArray(v.fields) && v.fields.every((f) => campoValid(f) && (!("checked" in (f as object)) || typeof (f as Campo).checked === "boolean")) &&
    Object.values(v.multiples).every(multipleValid) && (r.nino === null || bloqueValid(r.nino)) && bloqueValid(r.responsable_legal_1) &&
    bloqueValid(r.responsable_legal_2) && ["cancelar", "departamentos", "municipios", "localidades"].every((k) => internal((v.urls as Record<string, unknown>)[k])) &&
    messagesValid(v.messages);
}

const DOM_ATTRS: Record<string, string> = { readonly: "readOnly", tabindex: "tabIndex", maxlength: "maxLength", minlength: "minLength", inputmode: "inputMode" };
/** Django emits lower-case HTML attribute names; React wants the DOM property names. */
export function domAttrs(attrs: Record<string, string>): Record<string, string | boolean> {
  return Object.fromEntries(Object.entries(attrs).map(([k, v]) => [DOM_ATTRS[k] ?? k, k === "readonly" ? true : v]));
}

const INPUT_CLASS: Record<string, string> = { text: "textinput", email: "emailinput", number: "numberinput", url: "urlinput", tel: "textinput", date: "dateinput" };

type ControlProps = {
  field: Campo; value: string; onChange: (value: string) => void; block?: RenaperBloqueApi; dni?: boolean;
  readOnly?: boolean; required?: boolean; small?: boolean; after?: ReactNode;
};

/** The control of one field: input, select or textarea, with the lock state of its RENAPER block. */
export function Control({ field, value, onChange, block, dni, readOnly, required, small }: ControlProps) {
  const lock = block?.lock(field.name);
  const invalid = field.errors.length > 0 ? " is-invalid" : "";
  const staticDisabled = field.disabled && !field.renaper;
  const common = {
    id: `id_${field.name}`, name: field.name, required: required ?? (field.required || undefined),
    "aria-invalid": invalid ? ("true" as const) : undefined, "aria-describedby": describedBy(field),
  };
  const attrs = domAttrs(field.attrs);
  const sm = small ? "-sm" : "";
  if (field.widget === "select") {
    return (
      <select {...attrs} {...common} className={`form-select${small ? " form-select-sm" : ""}${invalid}`} value={value} disabled={staticDisabled || undefined}
        {...lockProps(lock, true)} onChange={(e) => onChange(e.target.value)}>
        {(field.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
    );
  }
  if (field.widget === "textarea") {
    return <textarea {...attrs} {...common} className={`form-control textarea${invalid}`} value={value} onChange={(e) => onChange(e.target.value)} />;
  }
  const locked = lockProps(lock, false) as { readOnly?: boolean };
  return (
    <input type={field.widget} {...attrs} {...common} className={`form-control${sm ? " form-control-sm" : ` ${INPUT_CLASS[field.widget] ?? "textinput"}`}${invalid}`}
      value={value} disabled={staticDisabled || undefined} {...lockProps(lock, false)} readOnly={readOnly || locked.readOnly || (attrs.readOnly as boolean | undefined)}
      onChange={(e) => onChange(e.target.value)} onKeyDown={dni ? block?.onDniKeyDown : undefined} />
  );
}

/** `div_id_<name>` with label, control and feedback (the crispy field). */
export function Crispy(props: ControlProps) {
  const { field, value, onChange, block, dni, after } = props;
  return (
    <CampoCrispy field={field} value={value} onChange={onChange} block={block ? { api: block, dni } : undefined}>
      <><Control {...props} />{after}</>
    </CampoCrispy>
  );
}

/** A crispy check box (`form-check`). */
export function Casilla({ field, checked, onChange }: { field: Campo; checked: boolean; onChange: (checked: boolean) => void }) {
  const id = `id_${field.name}`;
  return (
    <div className="mb-3">
      <div id={`div_${id}`} className="form-check">
        <input type="checkbox" id={id} name={field.name} className="form-check-input checkboxinput" checked={checked}
          {...(domAttrs(field.attrs) as Record<string, string>)} onChange={(e) => onChange(e.target.checked)} />{" "}
        <label htmlFor={id} className="form-check-label">{field.label}</label>
      </div>
    </div>
  );
}

/** A group of check boxes (`CheckboxSelectMultiple`): fieldset, legend, options, errors. */
export function Checks({ name, grupo, selected, onToggle }: { name: string; grupo: Multiple; selected: string[]; onToggle: (value: string) => void }) {
  const invalid = grupo.errors.length > 0;
  return (
    <div id={`div_id_${name}`} className="mb-3">
      <fieldset aria-describedby={invalid ? `id_${name}_error` : undefined}>
        <legend className={`form-label${grupo.required ? " requiredField" : ""} fs-6`}>
          {grupo.label}{grupo.required && <span className="asteriskField">*</span>}
        </legend>
        <div>
          {grupo.options.map((o, index) => (
            <div key={o.id} className="form-check">
              <input type="checkbox" className={`form-check-input${invalid ? " is-invalid" : ""}`} name={name} value={o.value} id={o.id} checked={selected.includes(o.value)}
                aria-invalid={invalid ? "true" : undefined} onChange={() => onToggle(o.value)} />{" "}
              <label htmlFor={o.id} className="form-check-label">{o.label}</label>
              {invalid && index === grupo.options.length - 1 && (
                <div id={`id_${name}_error`} className="invalid-feedback">
                  {grupo.errors.map((e, i) => <p key={i} id={`error_${i + 1}_id_${name}`}><strong>{e}</strong></p>)}
                </div>
              )}
            </div>
          ))}
        </div>
      </fieldset>
    </div>
  );
}
