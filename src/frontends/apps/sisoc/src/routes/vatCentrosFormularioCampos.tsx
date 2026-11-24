/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module family; its validators are exported for the tests. */
import { useState, type ReactNode, type RefObject } from "react";
import { record, text } from "./MainFrame";
import Select2, { type Choice } from "./select2";
import { bool } from "./vatShared";
import { fieldValid, type Field } from "./vatFormShared";

/**
 * Pieces of `vat/centros/centro_create_form.html`: a field as `{{ form.x|as_crispy_field }}` draws it (label with its asterisk,
 * the control, the `invalid-feedback` block and the help text), the referente/revisor search with chips of
 * `centro_create_form.js`, and one contact of the formset.
 */
export type Campo = Field & { disabled: boolean; required: boolean };
export type Usuario = { id: string; username: string; label: string };
export type UsuariosData = { label: string; choices: Choice[]; selected: string[]; options: Usuario[]; errors: string[] };
export type ContactoData = { hidden: { name: string; value: string }[]; fields: Campo[]; errors: { field: string; messages: string[] }[] };

export const campoValid = (f: unknown): f is Campo => fieldValid(f) && bool((f as Campo).disabled) && bool((f as Campo).required);
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text);
export const usuariosValid = (v: unknown): v is UsuariosData => record(v) && text(v.label) && strings(v.errors) && strings(v.selected) &&
  Array.isArray(v.choices) && v.choices.every((c) => record(c) && text(c.value) && text(c.label)) &&
  Array.isArray(v.options) && v.options.every((o) => record(o) && text(o.id) && text(o.username) && text(o.label));
export const contactoValid = (v: unknown): v is ContactoData => record(v) &&
  Array.isArray(v.hidden) && v.hidden.every((h) => record(h) && text(h.name) && text(h.value)) &&
  Array.isArray(v.fields) && v.fields.every(campoValid) &&
  Array.isArray(v.errors) && v.errors.every((e) => record(e) && text(e.field) && strings(e.messages));

const INPUT_CLASS: Record<string, string> = { text: "textinput", email: "emailinput", url: "urlinput", number: "numberinput" };
const DOM_ATTRS: Record<string, string> = { maxlength: "maxLength", inputmode: "inputMode", minlength: "minLength", autocomplete: "autoComplete" };

/** Widget attributes as the browser sees them; `class`, `required`, `type` and the inline `oninput` are handled apart. */
function domAttrs(attrs: Record<string, string>) {
  const rest: Record<string, string> = {};
  for (const [key, value] of Object.entries(attrs)) {
    if (["class", "required", "type", "oninput", "disabled", "data-width", "data-placeholder"].includes(key)) continue;
    rest[DOM_ATTRS[key] ?? key] = value;
  }
  return rest;
}

export const isSelect2 = (f: Campo) => (f.attrs.class ?? "").split(" ").includes("select2");

/** `{{ form.x|as_crispy_field }}` (crispy-bootstrap5) inside its `col-md-*` cell. */
export function CrispyCampo({ f, id, name, col, value, onChange, choices }: {
  f: Campo; id: string; name: string; col: string; value: string; onChange: (v: string) => void; choices?: Choice[];
}) {
  const invalid = f.errors.length > 0;
  const type = f.attrs.type ?? "text";
  const cls = f.attrs.class ?? "form-control";
  const required = f.attrs.required !== undefined ? true : undefined;
  const described = [f.help_text && `${id}_helptext`, invalid && `${id}_error`].filter(Boolean).join(" ") || undefined;
  const common = { "aria-describedby": described, "aria-invalid": invalid ? ("true" as const) : undefined };
  const options = choices ?? f.choices;
  let control: ReactNode;
  if (type === "hidden") {
    return <div className={`${col} vp-field`}><input type="hidden" name={name} id={id} value={value} disabled={f.disabled || undefined} readOnly /></div>;
  }
  if (f.tag === "select" && isSelect2(f)) {
    control = <Select2 id={id} name={name} choices={options} value={[value]} onChange={(v) => onChange(v[0] ?? "")} disabled={f.disabled}
      placeholder={f.attrs["data-placeholder"]} selectClassName={`${cls} form-select`} invalid={invalid}
      selectProps={{ required, "data-width": f.attrs["data-width"], "data-placeholder": f.attrs["data-placeholder"], "aria-describedby": described }}
      hideEmptyChoice noResults="No results found" clearTrigger="mousedown" focusMarker="container" termHandling="reset" enterOnSelected="toggle" outsideClick="dropdown" />;
  } else if (f.tag === "select") {
    control = <select name={name} id={id} className={`${cls} select form-select${invalid ? " is-invalid" : ""}`} required={required} disabled={f.disabled || undefined}
      value={value} onChange={(e) => onChange(e.target.value)} {...common}>
      {options.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
    </select>;
  } else {
    // The native contact `documento` strips whatever is not a digit on `oninput`.
    const digits = f.attrs.oninput !== undefined;
    control = <input type={type} name={name} id={id} className={`${cls} ${INPUT_CLASS[type] ?? "textinput"}${invalid ? " is-invalid" : ""}`} required={required}
      disabled={f.disabled || undefined} {...domAttrs(f.attrs)} {...common} value={value} onChange={(e) => onChange(digits ? e.target.value.replace(/\D/g, "") : e.target.value)} />;
  }
  return (
    <div className={`${col} vp-field`}>
      <div id={`div_${id}`} className="mb-3">
        <label htmlFor={id} className={`form-label${f.required ? " requiredField" : ""}`}>
          {f.label}{f.required && <span className="asteriskField">*</span>}
        </label>
        {control}
        {invalid && <div id={`${id}_error`} className="invalid-feedback">
          {f.errors.map((e, i) => <p key={i} id={`error_${i + 1}_${id}`}><strong>{e}</strong></p>)}
        </div>}
        {f.help_text && <div id={`${id}_helptext`} className="form-text">{f.help_text}</div>}
      </div>
    </div>
  );
}

const normal = (s: string) => s.trim().toLowerCase();

/**
 * The referente/revisor typeahead: the search box lists up to eight users that match and are not chosen yet, a chosen one is a
 * chip with a remove button, and the hidden `<select multiple>` owns the posted values. The results close 150 ms after the box
 * loses focus, like the native script.
 */
export function UsuariosBusqueda({ nombre, data, selected, onChange, inputRef, empty, placeholder, children }: {
  nombre: "referentes" | "revisores"; data: UsuariosData; selected: string[]; onChange: (v: string[]) => void;
  inputRef: RefObject<HTMLInputElement | null>; empty: string; placeholder: string; children?: ReactNode;
}) {
  const [term, setTerm] = useState("");
  const [open, setOpen] = useState(false);
  const matches = normal(term) ? data.options.filter((o) => (o.username.toLowerCase().includes(normal(term)) || o.label.toLowerCase().includes(normal(term))) &&
    !selected.includes(o.id)).slice(0, 8) : [];
  // The chips follow the order of the options of the hidden select.
  const chips = data.choices.filter((c) => selected.includes(c.value)).map((c) => data.options.find((o) => o.id === c.value)).filter((o): o is Usuario => !!o);
  const choose = (user: Usuario) => {
    onChange([...selected, user.id]);
    setTerm("");
    inputRef.current?.setCustomValidity("");
    setOpen(false);
  };
  const label = nombre === "referentes"
    ? <label htmlFor={`id_${nombre}_search`} className="requiredField">{data.label}<span className="asteriskField">*</span></label>
    : <label htmlFor={`id_${nombre}_search`}>{data.label}</label>;
  return (
    <div className="col-md-6 vp-field">
      <div id={`div_id_${nombre}`} className="form-group">
        {label}
        <div className="referente-search-wrapper">
          <input type="search" id={`id_${nombre}_search`} ref={inputRef} className={`form-control${data.errors.length ? " is-invalid" : ""}`}
            placeholder={placeholder} autoComplete="off" value={term}
            onChange={(e) => { setTerm(e.target.value); e.target.setCustomValidity(""); setOpen(!!e.target.value.trim()); }}
            onFocus={() => { if (term.trim()) setOpen(true); }} onBlur={() => { window.setTimeout(() => setOpen(false), 150); }} />
          <div id={`${nombre}-search-results`} className="referente-search-results" hidden={!open}>
            {open && (matches.length
              ? matches.map((o) => <button key={o.id} type="button" className="referente-search-option" data-user-id={o.id} onClick={() => choose(o)}>{o.label}</button>)
              : <div className="referente-search-empty">{empty}</div>)}
          </div>
        </div>
        <div id={`${nombre}-selected-items`} className="referente-selected-items">
          {chips.map((o) => <span key={o.id} className="referente-selected-chip">{o.label}
            <button type="button" className="referente-chip-remove" aria-label="Quitar" data-user-id={o.id} onClick={() => onChange(selected.filter((s) => s !== o.id))}>&times;</button>
          </span>)}
        </div>
        <select name={nombre} className="referente-hidden-select" tabIndex={-1} id={`id_${nombre}`} multiple value={selected} onChange={() => undefined}>
          {data.choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        {children}
        {data.errors.map((e, i) => <span key={i} className="referente-search-error">{e}</span>)}
      </div>
    </div>
  );
}
