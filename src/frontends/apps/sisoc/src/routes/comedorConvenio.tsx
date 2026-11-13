/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useEffect, useRef, useState, type FocusEvent, type FormEvent } from "react";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CO07.03 `comedor_convenio_pnud_form.html`: the PNUD / Abordaje Comunitario convenio data. The page
 * reads and saves through `/api/web/comedores/comedores/<id>/convenio-pnud/`, which runs the native
 * `ComedorDatosConvenioPnudUpdateView` (scope, applicability, variant form, Decimal montos and the
 * preservation of historical cents). React lays out what the server projected: the variant flags choose the
 * native template blocks, the fields the form removed are neither shown nor posted.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type ConvenioField = {
  name: string; label: string; type: string; required: boolean; help: string; value: string; monto: boolean; errors: string[];
  attrs: Record<string, string>;
};
export type ConvenioForm = {
  comedor_id: number;
  prefill: Record<(typeof PREFILL)[number][0], string>;
  territoriales: { territorial: string; codigo: string }[];
  es_linea_secos: boolean; es_linea_tradicional: boolean;
  fields: ConvenioField[]; non_field_errors: string[]; urls: { ficha: string };
};
export type ConvenioPayload = { form: ConvenioForm; messages: Message[] };

const PREFILL = [
  ["organizacion_solicitante", "Organización solicitante"], ["codigo_proyecto", "Código del proyecto"], ["estado_general", "Estado general"],
  ["subestado", "Subestado"], ["nombre_espacio", "Nombre del espacio comunitario"], ["id_externo", "ID externo"],
  ["domicilio_completo", "Domicilio completo del espacio"],
] as const;
const DIAS = [["lunes", "Lunes"], ["martes", "Martes"], ["miercoles", "Miércoles"], ["jueves", "Jueves"], ["viernes", "Viernes"], ["sabado", "Sábado"], ["domingo", "Domingo"]] as const;
const COMIDAS = [["desayuno", "Desayuno"], ["almuerzo", "Almuerzo"], ["merienda", "Merienda"], ["merienda_reforzada", "Merienda Reforzada"], ["cena", "Cena"]] as const;
const DIARIAS = COMIDAS.map(([comida]) => `prestaciones_financiadas_diarias_${comida}`);
const LEVELS = ["success", "error", "warning", "info"];
const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";

const fieldValid = (f: unknown): f is ConvenioField => record(f) && text(f.name) && text(f.label) && text(f.type) && typeof f.required === "boolean" && text(f.help) &&
  text(f.value) && typeof f.monto === "boolean" && Array.isArray(f.errors) && f.errors.every(text) && record(f.attrs) && Object.values(f.attrs).every(text);

export function convenioValid(v: unknown): v is ConvenioForm {
  return record(v) && typeof v.comedor_id === "number" && record(v.prefill) && PREFILL.every(([key]) => text((v.prefill as Record<string, unknown>)[key])) &&
    Array.isArray(v.territoriales) && v.territoriales.every((t) => record(t) && text(t.territorial) && text(t.codigo)) &&
    typeof v.es_linea_secos === "boolean" && typeof v.es_linea_tradicional === "boolean" && Array.isArray(v.fields) && v.fields.every(fieldValid) &&
    Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && record(v.urls) && internal(v.urls.ficha);
}

export function payloadValid(v: unknown): v is ConvenioPayload {
  return record(v) && convenioValid(v.form) && Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

const redirectOf = (v: unknown) => (record(v) && internal(v.redirect) ? v.redirect : null);

/** Full-page navigation after the POST (and for the native "not applicable" redirect); replaceable in tests. */
export const comedorConvenioNavigation = { assign: (to: string) => window.location.assign(to) };

/** `convenio_pnud.js`: a monto field gets its thousands separators on blur when it is a well-formed integer. */
export const formatMonto = (value: string) => {
  const v = value.trim();
  return /^-?(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)$/.test(v) ? v.replace(/\./g, "").replace(/\B(?=(\d{3})+(?!\d))/g, ".") : value;
};

type Values = Record<string, string>;
const valuesOf = (form: ConvenioForm): Values => Object.fromEntries(form.fields.map((f) => [f.name, f.value]));

/** `{{ form.x|as_crispy_field }}`: label with the asterisk, widget, errors and hint. */
function Campo({ f, values, set }: { f: ConvenioField; values: Values; set: (name: string, v: string) => void }) {
  const id = `id_${f.name}`;
  const invalid = f.errors.length > 0;
  const { maxlength, minlength, min, max, step, inputmode } = f.attrs;
  const describedBy = [f.help ? `hint_${id}` : "", invalid ? `error_1_${id}` : ""].filter(Boolean).join(" ") || undefined;
  return (
    <div id={`div_${id}`} className="mb-3">
      <label htmlFor={id} className={`form-label${f.required ? " requiredField" : ""}`}>{f.label}{f.required && <span className="asteriskField">*</span>}</label>
      <input type={f.type} name={f.name} id={id} className={`${f.type === "number" ? "numberinput" : "textinput"} form-control${invalid ? " is-invalid" : ""}`}
        value={values[f.name] ?? ""} required={f.required || undefined} maxLength={maxlength ? Number(maxlength) : undefined} minLength={minlength ? Number(minlength) : undefined}
        min={min} max={max} step={step} inputMode={inputmode as "numeric" | undefined} data-monto-entero={f.monto ? "true" : undefined} aria-describedby={describedBy}
        onChange={(e) => set(f.name, e.target.value)} onBlur={f.monto ? (e: FocusEvent<HTMLInputElement>) => set(f.name, formatMonto(e.target.value)) : undefined} />
      {f.errors.map((e, i) => <p key={e} id={`error_${i + 1}_${id}`} className="invalid-feedback"><strong>{e}</strong></p>)}
      {f.help && <div id={`hint_${id}`} className="form-text">{f.help}</div>}
    </div>
  );
}

/** A bare `{{ form.x }}{{ form.x.errors }}` cell of the weekly matrix. */
function Celda({ f, values, set }: { f: ConvenioField | undefined; values: Values; set: (name: string, v: string) => void }) {
  if (!f) return <td />;
  return (
    <td>
      <input type="number" name={f.name} id={`id_${f.name}`} className="form-control form-control-sm" min={f.attrs.min} required={f.required || undefined} value={values[f.name] ?? ""}
        onChange={(e) => set(f.name, e.target.value)} />
      {f.errors.length > 0 && <ul className="errorlist">{f.errors.map((e) => <li key={e}>{e}</li>)}</ul>}
    </td>
  );
}

function ConvenioContent({ form: inicial, messages }: { form: ConvenioForm; messages: Message[] }) {
  const [form, setForm] = useState(inicial);
  const [values, setValues] = useState<Values>(() => valuesOf(inicial));
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState("");
  const busy = useRef(false);
  const by = new Map(form.fields.map((f) => [f.name, f]));
  const set = (name: string, v: string) => setValues((cur) => ({ ...cur, [name]: v }));
  const { es_linea_secos: secos, es_linea_tradicional: tradicional } = form;
  const resto = !secos && !tradicional;
  const campo = (name: string) => { const f = by.get(name); return f ? <Campo f={f} values={values} set={set} /> : null; };
  const col = (name: string) => <div className="col-md-6">{campo(name)}</div>;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    // Only the controls the native template renders for this variant are posted.
    const body = new URLSearchParams();
    for (const f of form.fields) body.set(f.name, values[f.name] ?? "");
    let message = UNCERTAIN;
    try {
      const { data, status } = await webClient.post(`web/comedores/comedores/${form.comedor_id}/convenio-pnud/`, body, { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403 });
      if (status === 400 && record(data) && convenioValid(data.form)) {
        setForm(data.form); setValues(valuesOf(data.form));
        busy.current = false; setPending(false); resetAfterRejectedPost();
        return;
      }
      const to = status < 300 ? redirectOf(data) : null;
      if (to) { comedorConvenioNavigation.assign(to); return; }
      if (status === 403 && record(data) && text(data.detail)) message = data.detail;
    } catch {
      // Network error or timeout after sending: the result is unknown, nothing is retried.
    }
    busy.current = false; setPending(false); setUncertain(message);
  }

  return (
    <>
      <NativeToasts messages={messages} />
      <div className="card">
        <div className="card-header d-flex justify-content-between align-items-center">
          <h5 className="mb-0">Cargar datos del Convenio</h5>
        </div>
        <div className="card-body">
          <div className="mb-3">
            {PREFILL.map(([key, label]) => <p key={key} className="mb-1"><strong>{label}:</strong> {form.prefill[key]}</p>)}
          </div>
          <form method="post" onSubmit={submit}>
            {form.territoriales.length > 0 && <>
              <p className="fw-bold mb-1">Territoriales Asignados</p>
              <ul className="list-unstyled">
                {form.territoriales.map((t, i) => <li key={i}>{t.territorial} — Código de Proyecto: {t.codigo}</li>)}
              </ul>
            </>}
            <div className="row">
              {col("monto_total_conveniado")}
              {resto && col("personas_declaradas_siph")}
              {col("nro_convenio")}
              {col("monto_convenio_prestaciones_alimentarias")}
              {col("monto_convenio_siph")}
              {resto && col("prestaciones_financiadas_mensuales")}
              {tradicional && DIARIAS.map((name) => <div key={name} className="col-md-6">{campo(name)}</div>)}
              <div className="col-12">
                <div className="row">
                  {col("personas_conveniadas")}
                  {tradicional && col("personas_declaradas_siph")}
                </div>
                {!tradicional && (
                  <div className="row">
                    {col("cantidad_modulos")}
                    {secos && col("personas_declaradas_siph")}
                  </div>
                )}
              </div>
              {!secos && (
                <div className="col-12 mt-3">
                  <h6 className="fw-bold">Prestaciones por convenio</h6>
                  <div className="table-responsive">
                    <table className="table table-sm table-bordered align-middle">
                      <thead>
                        <tr>
                          <th>Día</th>
                          {COMIDAS.filter(([comida]) => tradicional || comida !== "merienda_reforzada").map(([comida, label]) => <th key={comida}>{label}</th>)}
                        </tr>
                      </thead>
                      <tbody>
                        {DIAS.map(([dia, label]) => (
                          <tr key={dia}>
                            <th>{label}</th>
                            {COMIDAS.filter(([comida]) => tradicional || comida !== "merienda_reforzada").map(([comida]) => (
                              <Celda key={comida} f={by.get(`aprobadas_${comida}_${dia}`)} values={values} set={set} />
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
            <button type="submit" className="btn btn-primary" disabled={pending || !!uncertain}>Guardar</button>
            {uncertain && <p role="alert" className="mb-0 mt-2">{uncertain}</p>}
          </form>
        </div>
      </div>
    </>
  );
}

function Leaving({ to }: { to: string }) {
  useEffect(() => { comedorConvenioNavigation.assign(to); }, [to]);
  return <main role="status">Cargando…</main>;
}

function ConvenioPage({ id }: { id: string }) {
  const endpoint = `web/comedores/comedores/${id}/convenio-pnud/`;
  const [state] = useMainResource(endpoint, payloadOrRedirect);
  // The native "only PNUD or Abordaje Comunitario" refusal: its message waits on the ficha.
  if (state.status === "ready" && redirectOf(state.data)) return <Leaving to={redirectOf(state.data) as string} />;
  return renderMain(state, "Cargando convenio…", (data) => {
    const { form, messages } = data as ConvenioPayload;
    return {
      title: "Datos del Convenio",
      heading: "Datos del Convenio",
      breadcrumb: <></>,
      content: <ConvenioContent key={endpoint} form={form} messages={messages} />,
    };
  });
}

function payloadOrRedirect(v: unknown): v is ConvenioPayload | { redirect: string } {
  return payloadValid(v) || (record(v) && Object.keys(v).length === 1 && redirectOf(v) !== null);
}

export const comedorConvenioRoute: RouteDefinition<{ id: string }> = {
  name: "comedores-convenio-pnud",
  match(pathname) {
    const m = pathname.match(/^\/comedores\/([0-9]+)\/convenio-pnud\/$/);
    return m ? { id: m[1] } : null;
  },
  render(params) {
    return <ConvenioPage key={params.id} id={params.id} />;
  },
};
