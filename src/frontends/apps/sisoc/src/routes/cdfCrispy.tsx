/* eslint-disable react-refresh/only-export-components -- shared CDF form pieces: the field renderer and its payload validators. */
import type { ReactNode } from "react";
import { messagesValid, record, text, type CdfMessage } from "./cdfFrame";

/**
 * `{{ form|crispy }}` (crispy-bootstrap5, inline errors) of the CDF forms: the label with its
 * asterisk, the control and the `invalid-feedback` block, from the field payload the API projects.
 */
export type Choice = { value: string; label: string };
export type CrispyFieldData = {
  name: string; label: string; required: boolean; widget: string; help_text: string; value: string | boolean;
  attrs: Record<string, string>; choices?: Choice[]; disabled?: boolean;
};
export type FieldError = { message: string; code: string };
export type FormErrors = { errors: Record<string, FieldError[]>; non_field_errors: string[] };

export const fieldValid = (f: unknown): f is CrispyFieldData => record(f) && text(f.name) && text(f.label) && typeof f.required === "boolean" &&
  text(f.widget) && text(f.help_text) && (text(f.value) || typeof f.value === "boolean") && record(f.attrs) && Object.values(f.attrs).every(text) &&
  (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label))));

export const errorsValid = (v: Record<string, unknown>): boolean => record(v.errors) &&
  Object.values(v.errors).every((list) => Array.isArray(list) && list.every((e) => record(e) && text(e.message) && text(e.code))) &&
  Array.isArray(v.non_field_errors) && v.non_field_errors.every(text);

export { messagesValid, type CdfMessage };

const INPUT_CLASS: Record<string, string> = { text: "textinput", email: "emailinput", number: "numberinput", date: "dateinput", url: "urlinput" };

export function CrispyField({ field, errors }: { field: CrispyFieldData; errors: FieldError[] }) {
  const id = `id_${field.name}`;
  const invalid = errors.length ? " is-invalid" : "";
  const described = [field.help_text && `${id}_helptext`, errors.length && `${id}_error`].filter(Boolean).join(" ");
  const common = {
    name: field.name, id, required: field.required || undefined, disabled: field.disabled || undefined,
    "aria-invalid": errors.length ? ("true" as const) : undefined, "aria-describedby": described || undefined,
  };
  let control: ReactNode;
  if (field.widget === "select") {
    control = (
      <select {...common} className={`select form-select${invalid}`} defaultValue={String(field.value)}>
        {(field.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
    );
  } else {
    control = <input type={field.widget} {...common} {...field.attrs} className={`form-control ${INPUT_CLASS[field.widget] ?? "textinput"}${invalid}`} defaultValue={String(field.value)} />;
  }
  return <FieldFrame id={id} label={field.label} required={field.required} helpText={field.help_text} errors={errors}>{control}</FieldFrame>;
}

/** The crispy wrapper of one field: label with asterisk, the control, the inline errors and the help text. */
export function FieldFrame({ id, label, required, helpText, errors, children }: {
  id: string; label: string; required: boolean; helpText: string; errors: FieldError[]; children: ReactNode;
}) {
  return (
    <div id={`div_${id}`} className="mb-3">
      <label htmlFor={id} className={`form-label${required ? " requiredField" : ""}`}>
        {label}{required && <span className="asteriskField">*</span>}
      </label>
      {children}
      {errors.length > 0 && (
        <div id={`${id}_error`} className="invalid-feedback">
          {errors.map((e, i) => <span key={i} id={`error_${i + 1}_${id}`}><strong>{e.message}</strong></span>)}
        </div>
      )}
      {helpText && <div id={`${id}_helptext`} className="form-text">{helpText}</div>}
    </div>
  );
}

/** crispy's `errors.html`: the non-field errors drawn at the top of the form. */
export function CrispyFormErrors({ messages }: { messages: string[] }) {
  if (!messages.length) return null;
  return <div className="alert alert-block alert-danger"><ul className="m-0">{messages.map((m, i) => <li key={i}>{m}</li>)}</ul></div>;
}
