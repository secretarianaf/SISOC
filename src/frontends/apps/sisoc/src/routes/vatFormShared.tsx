/* eslint-disable react-refresh/only-export-components -- shared VAT form pieces: components plus the validators and hooks that go with them. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { prerequisiteFromForbidden } from "../webAccess";
import { postForm, record, text, type MainState } from "./MainFrame";
import { resetAfterRejectedPost } from "./nativeParity";
import Select2, { type RemoteSource } from "./select2";
import { bool, vatNavigation } from "./vatShared";

/**
 * Pieces the VAT form pages share: a field as the native ModelForm widget renders it (the API
 * projects tag, attributes, value, choices and errors), the control that draws it, the POST of the
 * form with its redirect/invalid/forbidden outcomes, and the `*_confirm_delete.html` card.
 */
export type Field = {
  name: string; id: string; label: string; tag: "input" | "select" | "textarea" | "radio"; attrs: Record<string, string>;
  value: string | boolean; choices: { value: string; label: string; id?: string }[]; errors: string[]; help_text?: string;
};
export type FormValues = Record<string, string | boolean>;

export const UNCERTAIN = "No se pudo confirmar el resultado. Actualice la página antes de volver a intentar.";
export const ICON = { color: "#1f3a93" };

export const fieldValid = (f: unknown) => record(f) && text(f.name) && text(f.id) && text(f.label) && ["input", "select", "textarea", "radio"].includes(f.tag as string) &&
  record(f.attrs) && Object.values(f.attrs).every(text) && (text(f.value) || bool(f.value)) &&
  Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label)) &&
  Array.isArray(f.errors) && f.errors.every(text) && (f.help_text === undefined || typeof f.help_text === "string");

const isSelect2 = (f: Field) => (f.attrs.class ?? "").split(" ").includes("select2");

/** `data-ajax--*` of a remote widget (`BusquedaRemotaFormMixin`, #2889): its choices are only the chosen value. */
export const remoteSource = (f: Field): RemoteSource | undefined => (f.attrs["data-ajax--url"] ? {
  url: f.attrs["data-ajax--url"],
  delay: Number(f.attrs["data-ajax--delay"] ?? 0) || 0,
  minimumInputLength: Number(f.attrs["data-minimum-input-length"] ?? 0) || 0,
} : undefined);

/** Widget attributes as Django prints them; `class`, `required` and the `data-*` of the widget are kept. */
function widgetProps(f: Field) {
  const { class: className, required, rows, cols, ...rest } = f.attrs;
  return { className, required: required !== undefined ? true : undefined, ...(rows ? { rows: Number(rows) } : {}), ...(cols ? { cols: Number(cols) } : {}), ...rest };
}

export function Control({ f, state, set }: { f: Field; state: FormValues; set: (name: string, value: string | boolean) => void }) {
  if (f.tag === "select" && !isSelect2(f)) {
    return <select name={f.name} id={f.id} className={f.attrs.class} required={f.attrs.required !== undefined ? true : undefined} value={String(state[f.name] ?? "")} onChange={(e) => set(f.name, e.target.value)}>
      {f.choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
    </select>;
  }
  if (f.tag === "select") {
    return <Select2 id={f.id} name={f.name} choices={f.choices} value={[String(state[f.name] ?? "")]} onChange={(v) => set(f.name, v[0] ?? "")}
      placeholder={f.attrs["data-placeholder"] ?? f.choices.find((c) => c.value === "")?.label}
      selectClassName={f.attrs.class ?? ""} selectProps={{ required: f.attrs.required !== undefined ? true : undefined, "data-width": f.attrs["data-width"] }}
      hideEmptyChoice noResults="No results found" clearTrigger="mousedown" focusMarker="container" termHandling="reset" enterOnSelected="toggle" outsideClick="dropdown"
      remote={remoteSource(f)} />;
  }
  if (f.tag === "radio") {
    return <>{f.choices.map((c) => <label key={c.value} className="vp-radio-option d-flex align-items-start gap-2 mb-0" htmlFor={c.id}>
      <input type="radio" name={f.name} id={c.id} value={c.value} checked={state[f.name] === c.value} onChange={() => set(f.name, c.value)} />
      <span>{c.label}</span>
    </label>)}</>;
  }
  const props = widgetProps(f);
  if (f.tag === "textarea") return <textarea name={f.name} id={f.id} {...props} value={String(state[f.name] ?? "")} onChange={(e) => set(f.name, e.target.value)} />;
  if (f.attrs.type === "checkbox") return <input type="checkbox" name={f.name} id={f.id} {...props} checked={state[f.name] === true} onChange={(e) => set(f.name, e.target.checked)} />;
  return <input name={f.name} id={f.id} {...props} value={String(state[f.name] ?? "")} onChange={(e) => set(f.name, e.target.value)} />;
}

/** A plain select with no matching option shows (and submits) its first one, as the browser does. */
export function initialValues(fields: Field[]): FormValues {
  return Object.fromEntries(fields.map((f) => {
    const plainSelect = f.tag === "select" && !isSelect2(f);
    if (f.tag === "radio") return [f.name, f.choices.some((c) => c.value === f.value) ? f.value : ""];
    return [f.name, plainSelect && !f.choices.some((c) => c.value === f.value) ? f.choices[0]?.value ?? "" : f.value];
  }));
}

export const Err = ({ f }: { f: Field }) => (f.errors.length ? <div className="text-danger small mt-1">{f.errors[0]}</div> : null);

export function useForbidden<T>(setState: (s: MainState<T>) => void) {
  return (d: unknown) => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(d) });
}

/** `<link>`s of the select2 theme the native form pages load. */
export const Select2Links = () => <>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css" />
  <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
</>;

export const CsrfInput = () => <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;

/**
 * State and POST of a form page. The body carries only the fields the native template renders
 * (`data.fields`); a rejected POST shows the bound form like the native reload.
 */
export function useWriteForm<D extends { fields: Field[] }>({ initial, endpoint, forbidden, valid, send = postForm }: {
  initial: D; endpoint: string; forbidden: (d: unknown) => void; valid: (v: unknown) => v is D; send?: typeof postForm;
}) {
  const [data, setData] = useState(initial);
  const [state, setState] = useState<FormValues>(() => initialValues(initial.fields));
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  const set = (name: string, value: string | boolean) => setState((s) => ({ ...s, [name]: value }));
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true;
    const body = new URLSearchParams();
    for (const f of data.fields) {
      const v = state[f.name];
      if (f.attrs.type === "checkbox") { if (v === true) body.append(f.name, "on"); } else body.append(f.name, String(v));
    }
    const result = await send(endpoint, body);
    busy.current = false;
    if (result.kind === "redirect") vatNavigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else if (result.kind === "invalid" && valid(result.data)) {
      setData(result.data);
      setState(initialValues(result.data.fields));
      resetAfterRejectedPost();
    } else setUncertain(true);
  }
  return { data, state, set, uncertain, submit };
}

/** `*_confirm_delete.html`: the card with the record summary and the POST that deletes it. */
export function ConfirmDelete({ title, subtitle, cancel, endpoint, forbidden }: {
  title: string; subtitle: string; cancel: string; endpoint: string; forbidden: (d: unknown) => void;
}) {
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true;
    const result = await postForm(endpoint, new URLSearchParams());
    busy.current = false;
    if (result.kind === "redirect") vatNavigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else setUncertain(true);
  }
  return <>
    <div className="container-fluid py-4"><div className="row"><div className="col-lg-6 offset-lg-3 col-md-8 offset-md-2">
      <div className="card border-danger border-2 shadow-sm"><div className="card-body p-5 text-center">
        <div className="mb-4"><i className="bi bi-exclamation-triangle" style={{ fontSize: "4rem", color: "#dc3545" }} /></div>
        <h2 className="h4 mb-2 fw-bold">¿Estás seguro?</h2>
        <p className="text-muted mb-4">Esta acción no se puede deshacer</p>
        <div className="alert alert-light border mb-4" style={{ background: "#f8f9fa" }}>
          <strong className="d-block mb-1">{title}</strong>
          <small className="text-muted d-block">{subtitle}</small>
        </div>
        <div className="alert alert-warning mb-4" role="alert">
          <i className="bi bi-exclamation-circle me-2" />{" "}<strong>Advertencia:</strong> Al eliminar este registro se perderá toda su información.
        </div>
        <form method="post" className="mt-4" onSubmit={(e) => void submit(e)}>
          <CsrfInput />
          {uncertain && <p role="alert">{UNCERTAIN}</p>}
          <div className="d-grid gap-2">
            <button type="submit" className="btn btn-danger btn-lg"><i className="bi bi-trash me-2" />Sí, eliminar definitivamente</button>
            <a href={cancel} className="btn btn-outline-secondary btn-lg"><i className="bi bi-x-lg me-2" />Cancelar</a>
          </div>
        </form>
        <p className="small text-muted mt-4 mb-0">Si cometiste un error, puedes cancelar y volver al detalle.</p>
      </div></div>
    </div></div></div>
    <style>{".fw-bold { font-weight: 700 !important; } .border-danger { border-color: #dc3545 !important; }"}</style>
  </>;
}

export const FORM_CSS = `
    .form-control, .form-select { border: 1px solid #e0e0e0; border-radius: 0.5rem; padding: 0.75rem 1rem; }
    .form-control:focus, .form-select:focus { border-color: #1f3a93; box-shadow: 0 0 0 0.2rem rgba(31, 58, 147, 0.15); }
    .input-group-text { border: 1px solid #e0e0e0 !important; }
    .fw-600 { font-weight: 600 !important; }
    `;
