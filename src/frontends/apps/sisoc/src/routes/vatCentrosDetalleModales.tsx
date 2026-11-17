/* eslint-disable react-refresh/only-export-components -- the module exports the modal pieces together with their validators and the replaceable browser calls. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { postForm, record, text } from "./MainFrame";
import { NativeModal } from "./nativeParity";
import Select2 from "./select2";
import { CsrfInput, Control, fieldValid, initialValues, type Field, type FormValues } from "./vatFormShared";
import { vatGeography } from "./vatUbicacionesForm";

/**
 * The Bootstrap modals of `vat/centros/centro_detail.html` (contacto, ubicación) and of the courses panel (curso, comisión de
 * curso): the form the native page prints with `form.as_p` (or its own markup), the `setupModalForm` submit (HTML validation,
 * `Guardando...`, per-field `invalid-feedback` and an `alert` on a rejected save) and the page reload after a saved record.
 * Fields, choices and errors come from the native ModelForms through the web API; the POST persists through their `form_valid`.
 */
export const GENERIC_ERROR = "Error al guardar. Intente nuevamente.";
export const MODAL_CONTROLS = "button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled])";

/** The browser calls of the native script (`location.reload()`, `alert()`); replaceable in tests. */
export const centroAcciones = {
  reload: () => window.location.reload(),
  alert: (message: string) => window.alert(message),
};

export const fieldsValid = (v: unknown): v is Field[] => Array.isArray(v) && v.every(fieldValid);
export const formDataValid = (v: unknown): v is { fields: Field[] } => record(v) && fieldsValid(v.fields);
export const planesValid = (v: unknown): v is Plan[] => Array.isArray(v) && v.every((p) => record(p) && typeof p.id === "number" && text(p.etiqueta) && text(p.normativa));
export type Plan = { id: number; etiqueta: string; normativa: string };

const isSelect2 = (f: Field) => (f.attrs.class ?? "").split(" ").includes("select2");
const isMultiple = (f: Field) => f.attrs.multiple !== undefined;
const isDisabled = (f: Field) => f.attrs.disabled !== undefined;
const asList = (value: string | boolean) => (typeof value === "string" ? value.split(",").filter(Boolean) : []);

/** `FormData(form)`: the enabled controls only; a checkbox sends `on`, a multiple select one entry per option. */
export function bodyOf(fields: Field[], state: FormValues) {
  const body = new URLSearchParams();
  for (const f of fields) {
    if (isDisabled(f)) continue;
    const value = state[f.name];
    if (f.attrs.type === "checkbox") { if (value === true) body.append(f.name, "on"); continue; }
    if (isMultiple(f)) { asList(value).forEach((v) => body.append(f.name, v)); continue; }
    body.append(f.name, String(value ?? ""));
  }
  return body;
}

/** `renderFormErrors`: the errors of a rejected save by field name. */
export const errorsOf = (fields: Field[]) => Object.fromEntries(fields.filter((f) => f.errors.length > 0).map((f) => [f.name, f.errors.join(" ")]));

export type ModalForm = ReturnType<typeof useModalForm>;

/** State, validation and POST of a modal form (`setupModalForm`). `onSaved` runs after a saved record (the modal hides first). */
export function useModalForm({ fields, endpoint, rejection, onSaved, extra }: {
  fields: Field[]; endpoint: string; rejection: string; onSaved: () => void; extra?: (state: FormValues) => FormValues;
}) {
  const [state, setState] = useState<FormValues>(() => initialValues(fields));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const set = (name: string, value: string | boolean) => setState((s) => ({ ...s, [name]: value }));
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setErrors({});
    if (!form.checkValidity()) { form.reportValidity(); return; }
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    const result = await postForm(endpoint, bodyOf(fields, extra ? extra(state) : state));
    if (result.kind === "redirect") { onSaved(); return; }
    busyRef.current = false;
    setBusy(false);
    if (result.kind === "invalid" && formDataValid(result.data)) { setErrors(errorsOf(result.data.fields)); centroAcciones.alert(rejection); } else centroAcciones.alert(GENERIC_ERROR);
  }
  return { state, set, errors, busy, submit };
}

/** The submit button as `setupModalForm` leaves it while saving. */
export function SubmitButton({ busy, className, id, children }: { busy: boolean; className: string; id?: string; children: ReactNode }) {
  return <button type="submit" className={className} id={id} disabled={busy}>{busy ? <><i className="fas fa-spinner fa-spin me-1" />Guardando...</> : children}</button>;
}

/** `modal fade vat-ui-modal`: the shared `NativeModal` plus the class the native markup adds to the modal. */
export function useModalClass(id: string, className: string) {
  useEffect(() => { document.getElementById(id)?.classList.add(className); }, [id, className]);
}

/** A control as the native widget draws it, with the select2 states the modal forms need (`disabled`, `multiple`, `is-invalid`). */
export function ModalControl({ f, state, set, invalid, choices, disabled, dropdownParent, placeholderOnly = false, plainSelect = false }: {
  f: Field; state: FormValues; set: (name: string, value: string | boolean) => void; invalid?: boolean;
  choices?: Field["choices"]; disabled?: boolean; dropdownParent?: HTMLElement | null;
  /** The select2 box shows its placeholder while the form state keeps the value (the native `select.value = x` without `change.select2`). */
  placeholderOnly?: boolean;
  /** A `select.select2` the native script never initialised: it draws as the browser's plain select. */
  plainSelect?: boolean;
}) {
  // `select.value = x` without `change.select2`: the hidden select holds the value while the box shows its placeholder.
  const real = String(state[f.name] ?? "");
  useEffect(() => {
    const el = placeholderOnly ? (document.getElementById(f.id) as HTMLSelectElement | null) : null;
    if (el) el.value = real;
  });
  if (f.tag === "select" && plainSelect) {
    return <select name={f.name} id={f.id} className={`${f.attrs.class ?? ""}${invalid ? " is-invalid" : ""}`.trim()} required={f.attrs.required !== undefined ? true : undefined}
      value={String(state[f.name] ?? "")} onChange={(e) => set(f.name, e.target.value)}>
      {(choices ?? f.choices).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
    </select>;
  }
  if (f.tag === "select" && isSelect2(f)) {
    const multiple = isMultiple(f);
    const options = choices ?? f.choices;
    return <Select2 id={f.id} name={f.name} choices={options} value={placeholderOnly ? [""] : multiple ? asList(state[f.name]) : [String(state[f.name] ?? "")]}
      onChange={(v) => set(f.name, multiple ? v.join(",") : v[0] ?? "")} multiple={multiple} disabled={disabled ?? isDisabled(f)} invalid={invalid}
      placeholder={f.attrs["data-placeholder"] ?? (multiple ? undefined : options.find((c) => c.value === "")?.label)} dropdownParent={dropdownParent}
      selectClassName={f.attrs.class ?? ""} selectProps={{ required: f.attrs.required !== undefined && !placeholderOnly ? true : undefined, "data-width": f.attrs["data-width"] }}
      hideEmptyChoice noResults="No results found" clearTrigger="mousedown" focusMarker="container" termHandling="reset" enterOnSelected="toggle" outsideClick="dropdown" />;
  }
  // The inline `oninput` of the digits-only widgets runs as a filter on the value, as the browser would run it.
  const { oninput, ...attrs } = f.attrs;
  const patched: Field = { ...f, attrs: { ...attrs, class: `${f.attrs.class ?? ""}${invalid ? " is-invalid" : ""}`.trim() } };
  const filtered = (name: string, value: string | boolean) => set(name, oninput?.includes("\\D") && typeof value === "string" ? value.replace(/\D/g, "") : value);
  return <Control f={patched} state={state} set={filtered} />;
}

/** `label_tag`: Django adds the suffix unless the label already ends in punctuation. */
export const labelOf = (f: Field) => (/[:?.!]$/.test(f.label) ? f.label : `${f.label}:`);

/** One `form.as_p` paragraph with the `invalid-feedback` a rejected save adds after the control. */
export function AsPField({ f, state, set, error, choices, disabled, dropdownParent }: {
  f: Field; state: FormValues; set: (name: string, value: string | boolean) => void; error?: string;
  choices?: Field["choices"]; disabled?: boolean; dropdownParent?: HTMLElement | null;
}) {
  const withDescription: Field = f.help_text ? { ...f, attrs: { ...f.attrs, "aria-describedby": `${f.id}_helptext` } } : f;
  return (
    <p>
      <label htmlFor={f.id}>{labelOf(f)}</label>{" "}
      <ModalControl f={withDescription} state={state} set={set} invalid={error !== undefined} choices={choices} disabled={disabled} dropdownParent={dropdownParent} />
      {error !== undefined && <div className="invalid-feedback d-block">{error}</div>}
      {f.help_text ? <>{" "}<span className="helptext" id={`${f.id}_helptext`}>{f.help_text}</span></> : null}
    </p>
  );
}

type Choice = Field["choices"][number];
const EMPTY: Choice = { value: "", label: "" };

/** `setupUbicacionDepartamentoCascade`: the localidades of the chosen departamento by AJAX, kept when the saved one is among them. */
export function useLocalidades(localidadesUrl: string | null, fields: Field[], form: ModalForm) {
  const [choices, setChoices] = useState<Choice[]>(fields.find((f) => f.name === "localidad")?.choices ?? []);
  const [disabled, setDisabled] = useState(false);
  const ticket = useRef(0);
  const current = useRef(form.state);
  useEffect(() => { current.current = form.state; });
  async function cargar(municipio: string, conservar: boolean) {
    const previo = conservar ? String(current.current.localidad ?? "") : "";
    if (!municipio) { setChoices([EMPTY]); setDisabled(true); form.set("localidad", ""); return; }
    const mine = ++ticket.current;
    setDisabled(true);
    setChoices([{ value: "", label: "Cargando..." }]);
    form.set("localidad", "");
    let rows: unknown;
    try { rows = await vatGeography.load(`${localidadesUrl}?municipio_id=${encodeURIComponent(municipio)}`); } catch { rows = null; }
    if (mine !== ticket.current) return;
    if (!Array.isArray(rows) || !rows.every((r) => record(r) && typeof r.id === "number" && text(r.nombre))) { setChoices([EMPTY]); return; }
    const listed = rows as { id: number; nombre: string }[];
    setChoices([EMPTY, ...listed.map((l) => ({ value: String(l.id), label: l.nombre }))]);
    setDisabled(false);
    if (listed.some((l) => String(l.id) === previo)) form.set("localidad", previo);
  }
  // `shown.bs.modal`: a lone departamento is chosen by itself and its localidades are fetched, keeping the saved one.
  useEffect(() => {
    if (!localidadesUrl) return;
    const departamento = fields.find((f) => f.name === "departamento");
    let municipio = String(form.state.departamento ?? "");
    if (!municipio && departamento) {
      const opciones = departamento.choices.filter((o) => o.value);
      if (opciones.length === 1) { municipio = opciones[0].value; form.set("departamento", municipio); }
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- the `shown.bs.modal` handler of the native page.
    void cargar(municipio, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const onDepartamento = (value: string) => { form.set("departamento", value); void cargar(value, false); };
  return { choices: localidadesUrl ? choices : undefined, disabled: localidadesUrl ? disabled : undefined, onDepartamento };
}

export type AsPModalProps = {
  id: string; formId: string; title: string; fields: Field[]; endpoint: string; rejection: string; close: () => void; localidades?: string | null;
};

/** `#modalContacto` and `#modalUbicacion`: the title, the `form.as_p` body and the Cancelar/Guardar footer. */
export function AsPModal({ id, formId, title, fields, endpoint, rejection, close, localidades = null }: AsPModalProps) {
  const form = useModalForm({ fields, endpoint, rejection, onSaved: () => { close(); centroAcciones.reload(); } });
  const cascade = useLocalidades(localidades, fields, form);
  useModalClass(id, "vat-ui-modal");
  const set = (name: string, value: string | boolean) => (name === "departamento" && localidades ? cascade.onDepartamento(String(value)) : form.set(name, value));
  return (
    <NativeModal id={id} title={title} close={close} busy={form.busy} size=" modal-lg" controls={MODAL_CONTROLS}>
      <div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title" id={`${id}Label`}>{title}</h5>
          <button type="button" className="btn-close" aria-label="Close" onClick={close} />
        </div>
        <form id={formId} method="post" onSubmit={(e) => void form.submit(e)}>
          <CsrfInput />
          <div className="modal-body">
            {fields.map((f) => (
              <AsPField key={f.name} f={f} state={form.state} set={set} error={form.errors[f.name]}
                choices={f.name === "localidad" ? cascade.choices : undefined} disabled={f.name === "localidad" ? cascade.disabled : undefined} />
            ))}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
            <SubmitButton busy={form.busy} className="btn btn-primary">Guardar</SubmitButton>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}
