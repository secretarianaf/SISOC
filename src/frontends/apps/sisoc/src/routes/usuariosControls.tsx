/* eslint-disable react-refresh/only-export-components -- shared card controls: components plus their small helpers. */
import type { ReactNode } from "react";
import DatacalleSelect2 from "./datacalleSelect2";
import type { FieldErrors } from "./userImport";

/** Field specs and the native crispy controls shared by the user form cards. */
export type Value = string | boolean | string[];
export type Choice = { value: string; label: string; organizacion_id?: string; organizacion_nombre?: string };
export type Section = { key: string; fields: UsuarioField[] };
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

const INPUT_CLASS = { text: "textinput", email: "emailinput", password: "passwordinput" } as const;

export type Values = Record<string, Value>;
export type Api = {
  values: Values;
  errors: FieldErrors;
  busy: boolean;
  set: (name: string, value: Value) => void;
};

export const text = (value: Value | undefined) => (typeof value === "string" ? value : "");
export const list = (value: Value | undefined) => (Array.isArray(value) ? value : []);

export function Errors({ name, errors, block = false }: { name: string; errors: FieldErrors; block?: boolean }) {
  return <>{(errors[name] ?? []).map((e, i) => <p id={`error_${i + 1}_id_${name}`} className={`invalid-feedback${block ? " d-block" : ""}`} style={block ? { paddingLeft: "1.5rem" } : undefined} key={i}><strong>{e.message}</strong></p>)}</>;
}
export const Help = ({ spec }: { spec: UsuarioField }) => (spec.help_text ? <div id={`id_${spec.name}_helptext`} className="form-text">{spec.help_text}</div> : null);
const describedBy = (spec: UsuarioField) => (spec.help_text ? `id_${spec.name}_helptext` : undefined);

export function Control({ spec, api, extra }: { spec: UsuarioField; api: Api; extra?: ReactNode }) {
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
    control = <DatacalleSelect2 id={id} name={spec.name} multiple={multiple} className={`select2${multiple ? (spec.name === "comedores_pwa" ? " comedorpwaselectmultiple" : " selectmultiple") : ""} form-select`} choices={spec.choices ?? []}
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
