/* eslint-disable react-refresh/only-export-components -- route module: the validator and the navigation seam are exported for the tests. */
import { useEffect, useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { sameOriginTarget } from "./cdiObservaciones";
import { record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import Select2, { type Choice } from "./select2";

/**
 * CO02 intervention form: `intervencion_form.html` (create and edit share it, title
 * «Agregar Intervención»). The two-step wizard, the date check and the dynamic subtypes
 * reproduce the template script. Data and POSTs go through `/api/web/comedores/intervenciones/`,
 * which runs the native views; a confirmed redirect is a full-page navigation like the native 302.
 * Native quirks kept: a bound or edited type reloads the subtype list and drops its selection, the
 * edit date arrives as `dd/mm/yyyy` (a `type=date` input shows it empty) and the page draws no errors.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Field = { id: string; label: string; required: boolean; invalid: boolean };
type SelectField = Field & { options: Choice[]; value: string };
export type IntervencionFormData = {
  comedor: { id: number; nombre: string; url: string };
  admision_id: number | null;
  fields: {
    tipo_intervencion: SelectField; subintervencion: SelectField; destinatario: SelectField; forma_contacto: SelectField;
    fecha: Field & { value: string; hidden_initial: string };
    observaciones: Field & { value: string };
    tiene_documentacion: Field & { value: boolean };
    documentacion: { id: string; label: string };
  };
  messages: Message[];
};

const API = "web/comedores/intervenciones/";
const LEVELS = ["success", "error", "warning", "info"];
const bool = (v: unknown): v is boolean => typeof v === "boolean";
const field = (v: unknown): v is Field => record(v) && text(v.id) && text(v.label) && bool(v.required) && bool(v.invalid);
const extra = (v: unknown, key: string, check: (x: unknown) => boolean) => field(v) && check((v as Record<string, unknown>)[key]);
const selectField = (v: unknown): v is SelectField => extra(v, "value", text) &&
  extra(v, "options", (o) => Array.isArray(o) && o.every((c: unknown) => record(c) && text(c.value) && text(c.label)));

export function formValid(v: unknown): v is IntervencionFormData {
  if (!record(v) || !record(v.comedor) || !record(v.fields)) return false;
  const f = v.fields;
  return Number.isSafeInteger(v.comedor.id) && text(v.comedor.nombre) && text(v.comedor.url) &&
    (v.admision_id === null || Number.isSafeInteger(v.admision_id)) &&
    [f.tipo_intervencion, f.subintervencion, f.destinatario, f.forma_contacto].every(selectField) &&
    extra(f.fecha, "value", text) && extra(f.fecha, "hidden_initial", text) &&
    extra(f.observaciones, "value", text) && extra(f.tiene_documentacion, "value", bool) &&
    record(f.documentacion) && text(f.documentacion.id) && text(f.documentacion.label) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const intervencionFormNavigation = { assign: (to: string) => window.location.assign(to) };

const UNCERTAIN = "No se pudo confirmar el resultado. Revise las intervenciones del comedor antes de volver a intentar.";
const BLANK_SUB: Choice = { value: "", label: "Seleccione una opción" };
const aria = (f: Field) => (f.invalid ? { "aria-invalid": "true" as const, "aria-describedby": `${f.id}_error` } : {});

function Label({ f }: { f: Field }) {
  return <label htmlFor={f.id}>{f.label}{f.required && <>{" "}<span className="text-danger">*</span></>}</label>;
}

function PlainSelect({ name, f, invalid }: { name: string; f: SelectField; invalid: boolean }) {
  return (
    <select name={name} className={`form-control${invalid ? " is-invalid" : ""}`} required={f.required || undefined} id={f.id} defaultValue={f.value} {...aria(f)}>
      {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

function Wizard({ initial, endpoint }: { initial: IntervencionFormData; endpoint: string }) {
  const [data, setData] = useState(initial);
  const [revision, setRevision] = useState(0);
  return <Steps key={revision} data={data} endpoint={endpoint}
    onRejected={(next) => { setData(next); setRevision((r) => r + 1); resetAfterRejectedPost(); }} />;
}

function Steps({ data, endpoint, onRejected }: { data: IntervencionFormData; endpoint: string; onRejected: (data: IntervencionFormData) => void }) {
  const busy = useRef(false);
  const [uncertain, setUncertain] = useState("");
  const f = data.fields;
  const [step, setStep] = useState(1);
  const [tipo, setTipo] = useState(f.tipo_intervencion.value);
  // The template script reloads the subtype list when the page opens with a type already chosen.
  const [subOptions, setSubOptions] = useState<Choice[]>(f.tipo_intervencion.value ? [BLANK_SUB] : f.subintervencion.options);
  const [sub, setSub] = useState(f.tipo_intervencion.value ? "" : f.subintervencion.value);
  const [invalidSelects, setInvalidSelects] = useState({ tipo: false, destinatario: false });
  const [fechaError, setFechaError] = useState("");
  const [fileVisible, setFileVisible] = useState(false);
  const form = useRef<HTMLFormElement>(null);

  function fetchSubtypes(id: string) {
    webClient.get(`${API}subestados/`, { params: { id } })
      .then(({ data: rows }: { data: unknown }) => {
        if (!Array.isArray(rows)) return;
        const valid = rows.filter((r) => record(r) && Number.isSafeInteger(r.id) && text(r.text)) as { id: number; text: string }[];
        setSubOptions([BLANK_SUB, ...valid.map((r) => ({ value: String(r.id), label: r.text }))]);
      })
      .catch((error: unknown) => console.error("Error al cargar subintervenciones:", error));
  }
  function loadSubtypes(id: string) {
    setSub("");
    setSubOptions([BLANK_SUB]);
    if (id) fetchSubtypes(id);
  }
  useEffect(() => { if (f.tipo_intervencion.value) fetchSubtypes(f.tipo_intervencion.value); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function validateDate(input: HTMLInputElement) {
    if (!input.value) { setFechaError(""); return true; }
    const year = new Date(input.value).getFullYear();
    if (year < 2000) { setFechaError("El año de la fecha debe ser mayor o igual a 2000."); return false; }
    if (year > 2100) { setFechaError("El año de la fecha debe ser menor o igual a 2100."); return false; }
    setFechaError("");
    return true;
  }

  function next() {
    const destinatario = form.current?.querySelector<HTMLSelectElement>("#id_destinatario");
    const missing = { tipo: tipo === "", destinatario: (destinatario?.value ?? "") === "" };
    if (!missing.tipo && !missing.destinatario) {
      setStep(2);
    } else setInvalidSelects(missing);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fecha = event.currentTarget.querySelector<HTMLInputElement>("#id_fecha");
    if (fecha && !validateDate(fecha)) return;
    if (busy.current || uncertain) return;
    busy.current = true;
    const body = new FormData(event.currentTarget);
    try {
      const { data: response, status } = await webClient.post(endpoint, body, { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403 });
      if (status === 403) { setUncertain(record(response) && text(response.detail) ? response.detail : UNCERTAIN); busy.current = false; return; }
      if (status === 400 && formValid(response)) { busy.current = false; onRejected(response); return; }
      const to = status < 300 && record(response) && response.ok === true ? sameOriginTarget(response.redirect) : null;
      if (to) { intervencionFormNavigation.assign(to); return; }
    } catch {
      // Network error or timeout after sending: the result is unknown.
    }
    busy.current = false;
    setUncertain(UNCERTAIN);
  }

  const pasos = step === 1 ? { n: "1", width: "50%" } : { n: "2", width: "100%" };
  return (
    <>
      <NativeToasts messages={data.messages} />
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css" />
      <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/intervencionForm.css" />
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
        <div>
          <h3 className="mb-1">Nueva Intervención</h3>
          <p className="text-muted mb-0">Complete los datos de la intervención en 2 pasos</p>
        </div>
      </div>
      <div className="progress-indicator">
        <div className="progress-header">
          <h4 className="progress-title"><i className="fas fa-clipboard-check mr-2" />{" "}Progreso del Formulario</h4>
          <span className="progress-stats"><span id="current-step">{pasos.n}</span>/<span id="total-steps">2</span> pasos</span>
        </div>
        <div className="progress-bar-container"><div className="progress-bar-fill" id="progressBarFill" style={{ width: pasos.width }} /></div>
      </div>
      <div className="row">
        <div className="col-12">
          <form ref={form} method="post" id="intervencionForm" encType="multipart/form-data" noValidate onSubmit={submit}>
            <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
            {data.admision_id !== null && <input type="hidden" name="admision_id" value={data.admision_id} />}
            <div id="step-1" className={`step-container${step === 1 ? "" : " d-none"}`}>
              <div className="section-card">
                <div className="section-header active">
                  <div className="section-header-left">
                    <div className="section-icon"><i className="fas fa-clipboard-list" /></div>
                    <div className="section-title-group">
                      <h3 className="section-title">Paso 1 - Datos Iniciales</h3>
                      <p className="section-subtitle">Tipo de intervención y destinatario</p>
                    </div>
                  </div>
                </div>
                <div className="section-body show">
                  <div className="row">
                    <div className="col-md-6">
                      <div className="form-group">
                        <Label f={f.tipo_intervencion} />
                        <Select2 id={f.tipo_intervencion.id} name="tipo_intervencion" choices={f.tipo_intervencion.options} value={[tipo]}
                          onChange={(v) => { const id = v[0] ?? ""; setTipo(id); loadSubtypes(id); }} placeholder="Seleccione un tipo de intervención"
                          selectClassName="form-control" selectProps={{ required: f.tipo_intervencion.required || undefined, ...aria(f.tipo_intervencion) }}
                          invalid={invalidSelects.tipo} noResults="No hay resultados" hideEmptyChoice clearTrigger="mousedown" />
                      </div>
                    </div>
                    <div className="col-md-6">
                      <div className="form-group">
                        <Label f={f.subintervencion} />
                        <Select2 id={f.subintervencion.id} name="subintervencion" choices={subOptions} value={[sub]} onChange={(v) => setSub(v[0] ?? "")}
                          placeholder="Seleccione una subintervención" selectClassName="form-control" selectProps={aria(f.subintervencion)}
                          noResults="No hay resultados" hideEmptyChoice clearTrigger="mousedown" />
                      </div>
                    </div>
                  </div>
                  <div className="row">
                    <div className="col-12">
                      <div className="form-group">
                        <Label f={f.destinatario} />
                        <PlainSelect name="destinatario" f={f.destinatario} invalid={invalidSelects.destinatario} />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="sticky-actions" style={{ justifyContent: "flex-end" }}>
                <div>
                  <button type="button" id="next-step" className="btn btn-primary" onClick={next}><i className="fas fa-arrow-right mr-1" />{" "}Siguiente</button>
                </div>
              </div>
            </div>
            <div id="step-2" className={`step-container${step === 2 ? "" : " d-none"}`}>
              <div className="section-card">
                <div className="section-header active">
                  <div className="section-header-left">
                    <div className="section-icon"><i className="fas fa-calendar-alt" /></div>
                    <div className="section-title-group">
                      <h3 className="section-title">Paso 2 - Datos de Contacto</h3>
                      <p className="section-subtitle">Fecha, forma de contacto y observaciones</p>
                    </div>
                  </div>
                </div>
                <div className="section-body show">
                  <div className="row">
                    <div className="col-md-6">
                      <div className="form-group">
                        <Label f={f.fecha} />
                        <input type="date" name="fecha" defaultValue={f.fecha.value} className={`form-control${fechaError ? " is-invalid" : ""}`} required={f.fecha.required || undefined}
                          min="2000-01-01" max="2100-12-31" id={f.fecha.id} {...aria(f.fecha)}
                          onChange={(e) => validateDate(e.currentTarget)} onBlur={(e) => validateDate(e.currentTarget)} />
                        <input type="hidden" name="initial-fecha" defaultValue={f.fecha.hidden_initial} id={`initial-${f.fecha.id}`}
                          aria-describedby={f.fecha.invalid ? `${f.fecha.id}_error` : undefined} />
                        <div id="fecha-error" className="invalid-feedback" style={{ display: fechaError ? "block" : "none" }}>{fechaError}</div>
                      </div>
                    </div>
                    <div className="col-md-6">
                      <div className="form-group">
                        <Label f={f.forma_contacto} />
                        <PlainSelect name="forma_contacto" f={f.forma_contacto} invalid={false} />
                      </div>
                    </div>
                  </div>
                  <div className="row">
                    <div className="col-12">
                      <div className="form-group">
                        <Label f={f.observaciones} />
                        <textarea name="observaciones" cols={40} rows={4} className="form-control" id={f.observaciones.id} defaultValue={f.observaciones.value} {...aria(f.observaciones)} />
                      </div>
                    </div>
                  </div>
                  <div className="row">
                    <div className="col-12">
                      <div className="form-group mb-3">
                        <div className="custom-control custom-checkbox" style={{ paddingLeft: "1.5rem" }}>
                          <input type="checkbox" name="tiene_documentacion" id={f.tiene_documentacion.id} defaultChecked={f.tiene_documentacion.value}
                            onChange={(e) => setFileVisible(e.currentTarget.checked)} />{" "}
                          <label className="custom-control-label" htmlFor={f.tiene_documentacion.id} style={{ cursor: "pointer", userSelect: "none" }}>
                            {f.tiene_documentacion.label}
                          </label>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className={`row${fileVisible ? "" : " d-none"}`} id="documentacion-field">
                    <div className="col-12">
                      <div className="form-group">
                        <label htmlFor={f.documentacion.id}>{f.documentacion.label}</label>
                        <input type="file" name="documentacion" className="form-control" id={f.documentacion.id} />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="sticky-actions">
                <div>
                  <button type="button" id="prev-step" className="btn btn-secondary" onClick={() => setStep(1)}><i className="fas fa-arrow-left mr-1" />{" "}Anterior</button>
                </div>
                <div>
                  <button type="submit" className="btn btn-success"><i className="fas fa-save mr-1" />{" "}Guardar Intervención</button>
                </div>
              </div>
              {uncertain && <p role="alert" className="text-danger mb-0">{uncertain}</p>}
            </div>
          </form>
        </div>
      </div>
    </>
  );
}

export function IntervencionFormPage({ endpoint }: { endpoint: string }) {
  const [state] = useMainResource(endpoint, formValid);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: "Agregar Intervención",
    breadcrumb: null,
    content: <Wizard initial={data} endpoint={endpoint} />,
  }));
}
