/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { useEffect, useRef, useState, type FormEvent } from "react";
import { renderWithNativeToasts } from "./cdfActividades";
import { CrispyFormErrors, FieldFrame, errorsValid, type Choice, type FieldError, type FormErrors } from "./cdfCrispy";
import { client, csrfToken, integer, internal, messagesValid, navigation, record, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import DatacalleSelect2 from "./datacalleSelect2";
import { resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDF-B: `centros/actividadcentro_form.html` (create and edit; `form_card` with the crispy
 * `ActividadCentroForm`, `centro_familia_categoria.js`, the global Select2 of `custom.js` and the
 * flatpickr 24 h time pickers). The view puts no title, cancel URL or breadcrumb items in the
 * context, so the card has no title and no cancel button, as today. The API runs the native
 * view; a saved form follows the native redirect to the centre ficha, where the queued message
 * shows once. A POST is never retried.
 */
const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";

type Field = {
  name: string; label: string; required: boolean; disabled: boolean; widget: string; help_text: string;
  value: string | string[]; attrs: Record<string, string>; choices?: Choice[]; html: Record<string, string>;
};
export type ActividadFormData = FormErrors & {
  centro: { id: number; nombre: string; tipo: string }; fields: Field[]; messages: CdfMessage[];
};

const fieldValid = (f: unknown): f is Field => record(f) && text(f.name) && text(f.label) && typeof f.required === "boolean" && typeof f.disabled === "boolean" &&
  text(f.widget) && text(f.help_text) && (text(f.value) || (Array.isArray(f.value) && f.value.every(text))) && record(f.attrs) && Object.values(f.attrs).every(text) &&
  record(f.html) && Object.values(f.html).every(text) &&
  (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label))));

export function formValid(v: unknown): v is ActividadFormData {
  return record(v) && record(v.centro) && integer(v.centro.id) && text(v.centro.nombre) && text(v.centro.tipo) && Array.isArray(v.fields) && v.fields.every(fieldValid) &&
    errorsValid(v) && messagesValid(v.messages);
}

/** `centro_familia_categoria.js` asks `/ajax/actividades/` (`[{id, nombre}]`); replaceable in tests. */
const ACTIVIDADES_URL = "/ajax/actividades/";
export const actividadesLoader = {
  load: (url: string): Promise<unknown> => fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } }).then((r) => r.json()),
};

/** The flatpickr plugin the native page loads from jsDelivr; replaceable in tests. */
type Picker = { destroy: () => void };
type Flatpickr = (element: Element, options: Record<string, unknown>) => Picker;
const FLATPICKR_CSS = "https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css";
const FLATPICKR_JS = "https://cdn.jsdelivr.net/npm/flatpickr";
const PICKER_OPTIONS = { enableTime: true, noCalendar: true, dateFormat: "H:i", time_24hr: true };
let pickerScript: Promise<Flatpickr | null> | null = null;
export const timePicker = {
  load: (): Promise<Flatpickr | null> => {
    pickerScript ??= new Promise((resolve) => {
      const win = window as unknown as { flatpickr?: Flatpickr };
      if (win.flatpickr) { resolve(win.flatpickr); return; }
      const element = document.createElement("script");
      element.src = FLATPICKR_JS;
      element.onload = () => resolve(win.flatpickr ?? null);
      element.onerror = () => { pickerScript = null; resolve(null); };
      document.head.appendChild(element);
    });
    return pickerScript;
  },
};

function TimeInput({ field, errors }: { field: Field; errors: FieldError[] }) {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    let active = true;
    let picker: Picker | undefined;
    void timePicker.load().then((flatpickr) => {
      if (active && flatpickr && ref.current) picker = flatpickr(ref.current, PICKER_OPTIONS);
    });
    return () => { active = false; picker?.destroy(); };
  }, []);
  const id = `id_${field.name}`;
  return (
    <input ref={ref} type="text" name={field.name} id={id} className={`${field.html.class ?? ""} textinput${errors.length ? " is-invalid" : ""}`}
      placeholder={field.html.placeholder} required={field.required || undefined} defaultValue={String(field.value)}
      aria-invalid={errors.length ? "true" : undefined} aria-describedby={errors.length ? `${id}_error` : undefined} />
  );
}

const ICONS: Record<string, string> = { success: "fa-check-circle", error: "fa-exclamation-triangle", warning: "fa-exclamation-circle", info: "fa-info-circle" };

/** `components/alert_message.html` with `show_django_messages`. */
function Alerta({ message, level }: CdfMessage) {
  const [open, setOpen] = useState(true);
  if (!open) return null;
  return (
    <div className={`alert alert-${level} alert-dismissible fade show`} role="alert">
      <i className={`fas ${ICONS[level]} me-2`} />
      {message}
      <button type="button" className="btn-close" aria-label="Close" onClick={() => setOpen(false)} />
    </div>
  );
}

export function ActividadFormContent({ data, endpoint }: { data: ActividadFormData; endpoint: string }) {
  const [form, setForm] = useState(data);
  const [phase, setPhase] = useState<"idle" | "sending" | "uncertain">("idle");
  const byName = new Map(form.fields.map((f) => [f.name, f]));
  const [actividades, setActividades] = useState<Choice[]>(byName.get("actividad")?.choices ?? []);
  const [multi, setMulti] = useState<Record<string, string[]>>(() => ({
    sexoact: (byName.get("sexoact")?.value as string[]) ?? [], dias: (byName.get("dias")?.value as string[]) ?? [],
  }));
  const sending = useRef(false);

  function onCategoria(value: string) {
    setActividades([{ value: "", label: "Cargando..." }]);
    void actividadesLoader.load(`${ACTIVIDADES_URL}?categoria_id=${value}`).then((rows) => {
      if (!Array.isArray(rows)) return;
      setActividades([{ value: "", label: "Seleccione una actividad" },
        ...rows.filter((r): r is { id: number; nombre: string } => record(r) && integer(r.id) && text(r.nombre)).map((r) => ({ value: String(r.id), label: r.nombre }))]);
    });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current) return;
    sending.current = true;
    setPhase("sending");
    try {
      const { data: body, status } = await client.post(endpoint, new FormData(event.currentTarget), { validateStatus: (s: number) => s === 200 || s === 400 });
      if (status === 200 && record(body) && internal(body.url)) { navigation.assign(body.url); return; }
      if (status === 400 && formValid(body)) {
        const next = new Map(body.fields.map((f) => [f.name, f]));
        setForm(body);
        setActividades(next.get("actividad")?.choices ?? []);
        setMulti({ sexoact: (next.get("sexoact")?.value as string[]) ?? [], dias: (next.get("dias")?.value as string[]) ?? [] });
        sending.current = false;
        setPhase("idle");
        resetAfterRejectedPost();
        return;
      }
      setPhase("uncertain");
    } catch {
      setPhase("uncertain");
    }
    sending.current = false;
  }

  return (
    <>
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css" />
      <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
      <link rel="stylesheet" href="/static/custom/css/duplasSelect2.min.css" />
      <link rel="stylesheet" href={FLATPICKR_CSS} />
      {form.messages.map((m, i) => <Alerta key={i} {...m} />)}
      <div className="container">
        <div className="card card-body shadow">
          {phase === "uncertain" && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
          <form method="post" action="" encType="multipart/form-data" key={JSON.stringify(form.errors) + form.non_field_errors.join()} onSubmit={(e) => void submit(e)}>
            <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
            <CrispyFormErrors messages={form.non_field_errors} />
            {form.fields.map((f) => {
              const errors = form.errors[f.name] ?? [];
              const id = `id_${f.name}`;
              const invalid = errors.length ? " is-invalid" : "";
              if (f.widget === "hidden") return <input key={f.name} type="hidden" name={f.name} id={id} defaultValue={String(f.value)} />;
              let control;
              if (f.widget === "selectmultiple") {
                control = (
                  <DatacalleSelect2 id={id} name={f.name} className={`${f.html.class ?? ""} selectmultiple form-select`} multiple choices={f.choices ?? []}
                    value={multi[f.name] ?? []} onChange={(v) => setMulti((m) => ({ ...m, [f.name]: v }))} invalid={errors.length > 0}
                    describedBy={errors.length ? `${id}_error` : undefined} />
                );
              } else if (f.widget === "select") {
                const options = f.name === "actividad" ? actividades : f.choices ?? [];
                control = (
                  <select name={f.name} id={id} className={`${f.html.class ? `${f.html.class} ` : ""}select form-select${invalid}`} required={f.required || undefined}
                    defaultValue={String(f.value)} key={f.name === "actividad" ? options.map((o) => o.value).join(",") : f.name}
                    onChange={f.name === "categoria" ? (e) => onCategoria(e.target.value) : undefined}>
                    {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                );
              } else if (f.html.class?.includes("timepicker")) {
                control = <TimeInput field={f} errors={errors} />;
              } else {
                control = (
                  <input type={f.widget} name={f.name} id={id} {...f.attrs} className={`${f.html.class ?? ""} numberinput${invalid}`} required={f.required || undefined}
                    defaultValue={String(f.value)} />
                );
              }
              return <FieldFrame key={f.name} id={id} label={f.label} required={f.required} helpText={f.help_text} errors={errors}>{control}</FieldFrame>;
            })}
            <div className="text-center mt-4">
              <button type="submit" className="btn btn-primary" disabled={phase === "sending" || undefined}>Guardar</button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}

function ActividadForm({ centro, id }: { centro?: string; id?: string }) {
  const api = id ? `web/cdf/actividades/${id}/editar/` : `web/cdf/centros/${centro}/actividades/nueva/`;
  const state = useCdfPage(api, formValid);
  return renderWithNativeToasts(state, (data) => ({
    title: "Nueva Actividad",
    breadcrumb: <ol className="breadcrumb float-sm-right" />,
    content: <ActividadFormContent data={data} endpoint={api} />,
  }));
}

type Params = { centro?: string; id?: string };

// Native URLs of the CDF centre activity create and edit form (CDF-B).
export const cdfActividadFormRoute: RouteDefinition<Params> = {
  name: "cdf-actividad-form",
  match: (pathname) => {
    const crear = /^\/centrodefamilia\/centros\/([1-9]\d*)\/actividades\/nueva\/$/.exec(pathname);
    if (crear) return { centro: crear[1] };
    const editar = /^\/centrodefamilia\/centros\/actividades\/([1-9]\d*)\/editar\/$/.exec(pathname);
    return editar ? { id: editar[1] } : null;
  },
  render: ({ centro, id }) => <ActividadForm centro={centro} id={id} />,
};
