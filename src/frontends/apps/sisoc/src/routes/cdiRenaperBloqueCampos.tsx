/* eslint-disable react-refresh/only-export-components -- shared module: the field component plus the field projection helpers. */
import type { ChangeEvent, ReactNode } from "react";
import { record, text } from "./cdiFrame";
import { lockProps, type RenaperBloqueApi } from "./cdiRenaperBloque";

/**
 * Crispy (Bootstrap 5) field of the CDI forms: the markup `{{ form.x|as_crispy_field }}` renders,
 * driven by the field projection of `centrodeinfancia.web_api_formularios.campo_web`.
 */
export type Choice = { value: string; label: string };
export type FieldError = { message: string; code: string };
export type CampoWeb = {
  name: string; label: string; required: boolean; disabled: boolean; widget: string; help_text: string; value: string;
  attrs: Record<string, string>; renaper: boolean; errors: FieldError[]; choices: Choice[] | null;
};

export const campoValid = (f: unknown): f is CampoWeb => record(f) && text(f.name) && text(f.label) && typeof f.required === "boolean" &&
  typeof f.disabled === "boolean" && text(f.widget) && text(f.help_text) && text(f.value) && record(f.attrs) &&
  Object.values(f.attrs).every(text) && typeof f.renaper === "boolean" &&
  Array.isArray(f.errors) && f.errors.every((e) => record(e) && text(e.message) && text(e.code)) &&
  (f.choices === null || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label))));

const INPUT_CLASS: Record<string, string> = { text: "textinput", email: "emailinput", number: "numberinput", url: "urlinput", tel: "textinput" };

export function describedBy(field: CampoWeb): string | undefined {
  const ids = [field.help_text ? `id_${field.name}_helptext` : "", field.errors.length ? `id_${field.name}_error` : ""].filter(Boolean);
  return ids.length ? ids.join(" ") : undefined;
}

export function Label({ field, children }: { field: CampoWeb; children?: ReactNode }) {
  return (
    <label htmlFor={`id_${field.name}`} className={`form-label${field.required ? " requiredField" : ""}`}>
      {children ?? field.label}{field.required && <span className="asteriskField">*</span>}
    </label>
  );
}

/** Errors (`invalid-feedback` with a paragraph each) then the help text, in the crispy order. */
export function Feedback({ field }: { field: CampoWeb }) {
  return (
    <>
      {field.errors.length > 0 && (
        <div id={`id_${field.name}_error`} className="invalid-feedback">
          {field.errors.map((e, i) => <p key={i} id={`error_${i + 1}_id_${field.name}`}><strong>{e.message}</strong></p>)}
        </div>
      )}
      {field.help_text && <div id={`id_${field.name}_helptext`} className="form-text">{field.help_text}</div>}
    </>
  );
}

/** `div_id_<name>` wrapper with label, control and feedback; the control comes from the caller or the default input. */
export function CampoCrispy({ field, value, onChange, block, children }: {
  field: CampoWeb;
  value: string;
  onChange: (value: string) => void;
  /** The RENAPER block that governs the field, when it does (lock state, DNI Enter key). */
  block?: { api: RenaperBloqueApi; dni?: boolean };
  children?: ReactNode;
}) {
  const id = `id_${field.name}`;
  const lock = block?.api.lock(field.name);
  const invalid = field.errors.length > 0 ? " is-invalid" : "";
  const isSelect = field.widget === "select";
  const attrs = field.attrs;
  const common = {
    id, name: field.name, required: field.required || undefined, "aria-invalid": invalid ? ("true" as const) : undefined,
    "aria-describedby": describedBy(field),
  };
  // A server-disabled field that is not RENAPER-managed (e.g. a derived value) stays disabled.
  const staticDisabled = field.disabled && !field.renaper;
  const control = children ?? (
    <input type={field.widget} {...attrs} {...common} className={`form-control ${INPUT_CLASS[field.widget] ?? "textinput"}${invalid}`}
      value={value} disabled={staticDisabled || undefined} {...lockProps(lock, isSelect)}
      onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
      onKeyDown={block?.dni ? block.api.onDniKeyDown : undefined} />
  );
  return (
    <div id={`div_${id}`} className="mb-3">
      <Label field={field} />
      {control}
      <Feedback field={field} />
    </div>
  );
}

/** A grid column that the RENAPER block can hide, as the native script hides `.row > [class*='col-']`. */
export function Col({ className, hidden, children }: { className: string; hidden?: boolean; children: ReactNode }) {
  return <div className={className} hidden={hidden}>{children}</div>;
}
