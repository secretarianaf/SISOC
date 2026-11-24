/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validator is exported for the tests. */
import { useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { internal, record, renderMain, text, useMainResource, webClient, accepted } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import { messagesValid, vatNavigation, type Message } from "./vatShared";
import { Control, CsrfInput, fieldValid, initialValues, Select2Links, UNCERTAIN, useForbidden, type Field, type FormValues } from "./vatFormShared";
import { WIZARD_CSS, WIZARD_INFO_CSS } from "./vatComisionWizardStyles";
import { TourHelpInline } from "./vatTourInline";
import type { RouteDefinition } from "./types";

/**
 * V04.02 course commission wizard: `comision_curso_wizard/_base.html`, `step1_info.html`, `step2_horarios.html`,
 * `_horario_block.html` and `step3_confirmacion.html` (`vat_comision_curso_wizard`, three steps). The native `SessionWizardView`
 * runs behind `/api/web/vat/comisiones-asistente/cursos/<id>/`: the GET restarts it and returns the first step, every POST goes to
 * its session storage (validate, next, back, confirm) and answers with the context of the step that follows (400 with the
 * errors when the step is rejected, `{ok, redirect}` when the commission is created).
 *
 * Kept native behaviors: Enter in step 2 triggers the first submit button (the back button); the back button drops the unsaved
 * edits of the step; the waiting-list capacity is hidden (and cleared) unless the waiting list is on; the horario blocks are
 * added from the template, the last visible block is cleared instead of removed and the weekly total is computed on the client.
 */
type Step = "info" | "horarios" | "confirmacion";
type Horario = { fields: Field[] };
export type WizardData = {
  step: Step; steps: Step[]; management: { name: string; value: string }; estado_label: string;
  curso: { nombre: string; plan: string; codigo: string }; urls: { cancel: string }; messages: Message[];
  fields?: Field[]; non_field_errors?: string[];
  formset?: { prefix: string; management: { name: string; value: string }[]; forms: Horario[]; empty: Horario; non_form_errors: string[] };
  resumen?: { ubicacion: string; periodo: string; cupo: string; horarios: { dia: string; horas: string; duracion: string; estado: string }[]; total: string };
};

const STEPS: Step[] = ["info", "horarios", "confirmacion"];
const horarioValid = (h: unknown) => record(h) && Array.isArray(h.fields) && h.fields.every(fieldValid);
const textList = (v: unknown) => Array.isArray(v) && v.every(text);

export const wizardValid = (v: unknown): v is WizardData => {
  if (!record(v) || !STEPS.includes(v.step as Step) || !Array.isArray(v.steps) || v.steps.join() !== STEPS.join()) return false;
  if (!record(v.management) || !text(v.management.name) || v.management.value !== v.step || !text(v.estado_label)) return false;
  if (!record(v.curso) || !text(v.curso.nombre) || !text(v.curso.plan) || !text(v.curso.codigo)) return false;
  if (!record(v.urls) || !internal(v.urls.cancel) || !messagesValid(v.messages)) return false;
  if (v.step === "info") return Array.isArray(v.fields) && v.fields.every(fieldValid) && textList(v.non_field_errors);
  if (v.step === "horarios") {
    const f = v.formset;
    return record(f) && text(f.prefix) && Array.isArray(f.management) && f.management.every((m) => record(m) && text(m.name) && text(m.value)) &&
      Array.isArray(f.forms) && f.forms.every(horarioValid) && horarioValid(f.empty) && textList(f.non_form_errors);
  }
  const r = v.resumen;
  return record(r) && text(r.ubicacion) && text(r.periodo) && text(r.cupo) && text(r.total) && Array.isArray(r.horarios) &&
    r.horarios.every((h) => record(h) && text(h.dia) && text(h.horas) && text(h.duracion) && text(h.estado));
};

const API = (cursoId: string) => `web/vat/comisiones-asistente/cursos/${cursoId}/`;

type Outcome = { kind: "redirect"; url: string } | { kind: "step"; data: WizardData } | { kind: "forbidden"; data: unknown } | { kind: "uncertain" };

/** POST of a step: 200 and 400 both carry the step to show next (the native view renders the same page either way). */
async function postStep(endpoint: string, body: URLSearchParams): Promise<Outcome> {
  try {
    const { data, status } = await webClient.post(endpoint, body, { validateStatus: accepted });
    if (status === 403) return { kind: "forbidden", data };
    if (record(data) && data.ok === true && internal(data.redirect)) return { kind: "redirect", url: data.redirect };
    return wizardValid(data) ? { kind: "step", data } : { kind: "uncertain" };
  } catch (error: unknown) {
    const response = (error as { response?: { status?: number; data?: unknown } }).response;
    return response?.status === 400 && wizardValid(response.data) ? { kind: "step", data: response.data } : { kind: "uncertain" };
  }
}

const fieldBody = (body: URLSearchParams, f: Field, v: string | boolean | undefined) => {
  if (f.attrs.type === "checkbox") { if (v === true) body.append(f.name, "on"); } else body.append(f.name, String(v ?? ""));
};
const errorList = (errors: string[], kind: string): ReactNode => errors.length > 0 && <div className="text-danger"><ul className={`errorlist ${kind}`}>{errors.map((e) => <li key={e}>{e}</li>)}</ul></div>;
const fieldError = (f: Field): ReactNode => f.errors.length > 0 && <div className="text-danger">{f.errors[0]}</div>;
const required = <span className="text-danger">*</span>;

type StepProps = { data: WizardData; busy: boolean; send: (body: URLSearchParams) => void };

function InfoStep({ data, send }: StepProps) {
  const by = Object.fromEntries(data.fields!.map((f) => [f.name.replace(/^info-/, ""), f])) as Record<string, Field>;
  const [accept, cupoEspera] = [by.acepta_lista_espera.name, by.cupo_lista_espera.name];
  // The native script hides the waiting-list capacity and clears it as soon as the waiting list is off (also on load).
  const [state, setState] = useState<FormValues>(() => {
    const values = initialValues(data.fields!);
    return values[accept] === true ? values : { ...values, [cupoEspera]: "" };
  });
  const set = (name: string, value: string | boolean) => setState((s) => ({ ...s, [name]: value, ...(name === accept && value !== true ? { [cupoEspera]: "" } : {}) }));
  const acepta = state[accept] === true;
  const field = (name: string, label: string, mandatory: boolean) => {
    const f = by[name];
    return <div className="sisoc-wizard-field">
      <label className="sisoc-wizard-label" htmlFor={f.id}>{label}{mandatory && required}</label>
      <Control f={f} state={state} set={set} />
      {fieldError(f)}
    </div>;
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const body = new URLSearchParams({ [data.management.name]: data.management.value });
    for (const f of data.fields!) fieldBody(body, f, state[f.name]);
    send(body);
  };
  return <form method="post" id="sisoc-wizard-form" noValidate onSubmit={submit}>
    <CsrfInput />
    <input type="hidden" name={data.management.name} value={data.management.value} id={`id_${data.management.name}`} />
    <div className="sisoc-wizard-card">
      <div className="sisoc-wizard-card-header"><i className="fas fa-info-circle" />{" "}<span>Información básica</span></div>
      <div className="sisoc-wizard-card-body">
        <p className="sisoc-wizard-intro">Complete los datos generales de la comisión. Todos los campos marcados con <strong>*</strong> son obligatorios.</p>
        <div className="sisoc-wizard-row sisoc-wizard-row--info-grid">
          <div className="sisoc-wizard-field">
            <label className="sisoc-wizard-label" htmlFor="curso-display">Curso{required}</label>
            <input id="curso-display" type="text" className="form-control sisoc-wizard-input" value={data.curso.nombre} readOnly />
          </div>
          {field("ubicacion", "Ubicación", true)}
        </div>
        <div className="sisoc-wizard-row sisoc-wizard-row--metrics-grid">
          {field("cupo_total", "Cupo total", true)}{field("estado", "Estado", true)}
          {field("fecha_inicio", "Fecha de inicio", true)}{field("fecha_fin", "Fecha de finalización", true)}
        </div>
        <div className="sisoc-wizard-row">
          <div className="sisoc-wizard-field">
            <label className="sisoc-wizard-label" htmlFor={by.acepta_lista_espera.id}>Lista de espera</label>
            <div className="sisoc-wizard-check-row">
              <Control f={by.acepta_lista_espera} state={state} set={set} />{" "}
              <label className="sisoc-wizard-check-text" htmlFor={by.acepta_lista_espera.id}>Acepta lista de espera</label>
            </div>
            {fieldError(by.acepta_lista_espera)}
          </div>
          <div className="sisoc-wizard-field" id="wizard-cupo-espera-wrapper" hidden={!acepta}>
            <label className="sisoc-wizard-label" htmlFor={by.cupo_lista_espera.id}>Cantidad que acepta la lista de espera</label>
            <Control f={by.cupo_lista_espera} state={state} set={set} />
            {fieldError(by.cupo_lista_espera)}
          </div>
        </div>
        <div className="sisoc-wizard-field">
          <label className="sisoc-wizard-label" htmlFor={by.observaciones.id}>Observaciones</label>
          <Control f={by.observaciones} state={state} set={set} />
          {fieldError(by.observaciones)}
        </div>
        {errorList(data.non_field_errors!, "nonfield")}
      </div>
    </div>
    <style>{WIZARD_INFO_CSS}</style>
    <div className="sisoc-wizard-footer-row">
      <div className="sisoc-wizard-footer-left">
        <div className="sisoc-wizard-validations">
          <h4><i className="fas fa-exclamation-circle" />{" "}Códigos de validación</h4>
          <ul>
            <li>La fecha de inicio debe ser igual o posterior a hoy</li>
            <li>La fecha de finalización debe ser posterior a la fecha de inicio</li>
            <li>El cupo debe estar entre 5 y 100 estudiantes</li>
          </ul>
        </div>
      </div>
      <div className="sisoc-wizard-footer-right" />
    </div>
    <div className="sisoc-wizard-buttons">
      <a href={data.urls.cancel} className="sisoc-wizard-btn sisoc-wizard-btn--light">Cancelar</a>
      <button type="submit" className="sisoc-wizard-btn sisoc-wizard-btn--primary">Avanzar al paso siguiente <i className="fas fa-arrow-right" /></button>
    </div>
  </form>;
}

type Block = { index: number; hidden: boolean; fields: Field[]; values: FormValues };
const minutes = (value: string) => {
  const parts = value.split(":");
  const h = parseInt(parts[0], 10), m = parseInt(parts[1] ?? "", 10);
  return parts.length < 2 || Number.isNaN(h) || Number.isNaN(m) ? null : h * 60 + m;
};
const nameOf = (f: Field) => f.name.replace(/^.*-/, "");
const renamed = (h: Horario, index: number): Field[] => h.fields.map((f) => ({ ...f, name: f.name.replace("__prefix__", String(index)), id: f.id.replace("__prefix__", String(index)) }));

function HorariosStep({ data, send }: StepProps) {
  const formset = data.formset!;
  const [blocks, setBlocks] = useState<Block[]>(() => formset.forms.map((h, index) => ({ index, hidden: false, fields: h.fields, values: initialValues(h.fields) })));
  const set = (index: number) => (name: string, value: string | boolean) => setBlocks((all) => all.map((b) => (b.index === index ? { ...b, values: { ...b.values, [name]: value } } : b)));
  const visible = blocks.filter((b) => !b.hidden);
  const total = visible.reduce((sum, b) => {
    const v = (name: string) => minutes(String(b.values[b.fields.find((f) => nameOf(f) === name)!.name] ?? ""));
    const [from, to] = [v("hora_desde"), v("hora_hasta")];
    return from !== null && to !== null && to > from ? sum + to - from : sum;
  }, 0);
  const hours = Math.floor(total / 60), mins = total % 60;
  const [value, unit] = total >= 60 ? [mins ? `${hours} h ${mins}` : String(hours), mins ? "min" : hours === 1 ? "Hora" : "Horas"] : [String(total), "Min"];
  const add = () => setBlocks((all) => {
    const index = all.length;
    const fields = renamed(formset.empty, index);
    return [...all, { index, hidden: false, fields, values: initialValues(fields) }];
  });
  const remove = (index: number) => setBlocks((all) => {
    const alone = all.filter((b) => !b.hidden).length <= 1;
    return all.map((b) => {
      if (b.index !== index) return b;
      if (!alone) return { ...b, hidden: true, values: { ...b.values, [b.fields.find((f) => nameOf(f) === "DELETE")!.name]: true } };
      // The last visible block is cleared (every input but DELETE).
      return { ...b, values: Object.fromEntries(Object.entries(b.values).map(([k, v]) => [k, k.endsWith("-DELETE") ? v : typeof v === "boolean" ? false : ""])) };
    });
  });
  const body = (extra: Record<string, string>) => new URLSearchParams({ [data.management.name]: data.management.value, ...extra });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const out = body({});
    const management = Object.fromEntries(formset.management.map((m) => [m.name, m.value]));
    for (const [name, v] of Object.entries(management)) out.append(name, name.endsWith("TOTAL_FORMS") ? String(blocks.length) : v);
    for (const b of blocks) for (const f of b.fields) fieldBody(out, f, b.values[f.name]);
    send(out);
  };
  const back = (event: { preventDefault: () => void }) => { event.preventDefault(); send(body({ wizard_goto_step: "info" })); };
  const block = (b: Block) => {
    const idx = visible.indexOf(b);
    const f = Object.fromEntries(b.fields.map((x) => [nameOf(x), x])) as Record<string, Field>;
    const ctl = (name: string) => <Control f={f[name]} state={b.values} set={set(b.index)} />;
    const group = (name: string, label: string) => <div className="sisoc-wizard-field" style={{ marginBottom: 0 }}>
      <label className="sisoc-wizard-label" htmlFor={f[name].id}>{label}</label>{ctl(name)}{fieldError(f[name])}
    </div>;
    return <fieldset key={b.index} className="sisoc-wizard-horario" data-horario-index={b.index} {...(b.hidden ? { "data-deleted": "1", style: { display: "none" } } : {})}>
      <legend className="sisoc-wizard-horario-title">Horario {b.hidden ? b.index + 1 : idx + 1}</legend>
      <div className="sisoc-wizard-horario-grid">
        {group("dia_semana", "Día de la semana")}{group("hora_desde", "Hora inicio")}{group("hora_hasta", "Hora finalización")}
        <button type="button" className="sisoc-wizard-btn sisoc-wizard-btn--icon-danger" data-action="remove-horario" title="Eliminar horario" onClick={() => remove(b.index)}><i className="fas fa-trash" /></button>
      </div>
      <div className="sisoc-wizard-horario-estado">
        <label className="sisoc-wizard-label" htmlFor={f.vigente.id}>Estado</label>{ctl("vigente")}
      </div>
      <div style={{ display: "none" }}>{ctl("DELETE")}</div>
    </fieldset>;
  };
  return <form method="post" id="sisoc-wizard-form" noValidate onSubmit={submit}>
    <CsrfInput />
    <input type="hidden" name={data.management.name} value={data.management.value} id={`id_${data.management.name}`} />
    <div className="sisoc-wizard-card">
      <div className="sisoc-wizard-card-header"><i className="fas fa-clock" />{" "}<span>Horarios de clase</span></div>
      <div className="sisoc-wizard-card-body">
        <p className="sisoc-wizard-intro">Defina los días y horarios en que se dictará la comisión. Debe agregar al menos 1 horario y el total semanal debe ser mínimo 2 horas.</p>
        {formset.management.map((m) => <input key={m.name} type="hidden" name={m.name} value={m.name.endsWith("TOTAL_FORMS") ? blocks.length : m.value} id={`id_${m.name}`} readOnly />)}
        {errorList(formset.non_form_errors, "nonform")}
        <div id="sisoc-wizard-horarios" data-horarios-prefix={formset.prefix}>{blocks.map(block)}</div>
        <div className="sisoc-wizard-add-horario-row">
          <button type="button" className="sisoc-wizard-btn sisoc-wizard-btn--add" data-action="add-horario" onClick={add}><i className="fas fa-plus" />{" "}Agregar horario</button>
        </div>
      </div>
    </div>
    <div className="sisoc-wizard-footer-row">
      <div className="sisoc-wizard-footer-left">
        <div className={`sisoc-wizard-total${total >= 120 ? " is-ok" : ""}`} data-total-semanal>
          <h4>Total semanal</h4>
          <div className="value"><span data-total-value>{value}</span>{" "}<span data-total-unit>{unit}</span></div>
          <div className="note">• Mínimo requerido 2 hs semanales</div>
        </div>
      </div>
      <div className="sisoc-wizard-footer-right">
        <div className="sisoc-wizard-validations">
          <h4><i className="fas fa-exclamation-circle" />{" "}Códigos de validación</h4>
          <ul>
            <li>Al menos 1 horario definido (obligatorio)</li>
            <li>Duración de cada clase: entre 45 minutos y 4 horas</li>
            <li>Total semanal mínimo: 2 horas</li>
            <li>No puede haber 2 horarios el mismo día</li>
          </ul>
        </div>
      </div>
    </div>
    <div className="sisoc-wizard-buttons">
      <button type="submit" name="wizard_goto_step" value="info" className="sisoc-wizard-btn sisoc-wizard-btn--light" formNoValidate onClick={back}><i className="fas fa-arrow-left" />{" "}Volver al paso anterior</button>
      <button type="submit" className="sisoc-wizard-btn sisoc-wizard-btn--primary">Avanzar al paso siguiente <i className="fas fa-arrow-right" /></button>
    </div>
  </form>;
}

function ConfirmStep({ data, send }: StepProps) {
  const r = data.resumen!;
  const body = (extra: Record<string, string>) => new URLSearchParams({ [data.management.name]: data.management.value, ...extra });
  const column = (cell: (h: (typeof r.horarios)[number]) => ReactNode) => <div className="sisoc-wizard-horarios-list">{r.horarios.map((h, i) => <div key={i} className="sisoc-wizard-horarios-item">{cell(h)}</div>)}</div>;
  const summary = (icon: string, title: string, cells: [string, string][]) => <div className="sisoc-wizard-summary-card">
    <div className="sisoc-wizard-summary-header"><i className={icon} />{" "}<span>{title}</span></div>
    <div className="sisoc-wizard-summary-body">
      {cells.map(([label, value]) => <div className="sisoc-wizard-summary-cell" key={label}><span className="label">{label}</span>{" "}<span className="value">{value}</span></div>)}
    </div>
  </div>;
  return <form method="post" id="sisoc-wizard-form" noValidate onSubmit={(e) => { e.preventDefault(); send(body({})); }}>
    <CsrfInput />
    <input type="hidden" name={data.management.name} value={data.management.value} id={`id_${data.management.name}`} />
    <div className="sisoc-wizard-card">
      <div className="sisoc-wizard-card-header"><i className="fas fa-check-circle" />{" "}<span>Confirmación final</span></div>
      <div className="sisoc-wizard-card-body">
        <p className="sisoc-wizard-intro">Revise todos los datos antes de guardar. Una vez confirmado, la comisión quedará registrada en el sistema.</p>
      </div>
    </div>
    {summary("fas fa-graduation-cap", "Curso - Nuevo", [["Nombre del curso", data.curso.nombre], ["Plan curricular", data.curso.plan], ["Código", data.curso.codigo]])}
    {summary("fas fa-book", "Comisión", [["Ubicación", r.ubicacion], ["Período", r.periodo], ["Cupo", r.cupo]])}
    <div className="sisoc-wizard-summary-card">
      <div className="sisoc-wizard-summary-header"><i className="fas fa-clock" />{" "}<span>Horarios</span></div>
      <div className="sisoc-wizard-summary-body sisoc-wizard-summary-body--horarios">
        {column((h) => <><div className="sisoc-wizard-horarios-day">{h.dia}</div><div className="sisoc-wizard-horarios-time">{h.horas}</div></>)}
        {column((h) => <><div className="sisoc-wizard-horarios-meta-label">Duración</div><div className="sisoc-wizard-horarios-meta-value">{h.duracion}</div></>)}
        {column((h) => <><div className="sisoc-wizard-horarios-meta-label">Estado</div><div className="sisoc-wizard-horarios-meta-value">{h.estado}</div></>)}
        <div className="sisoc-wizard-summary-total sisoc-wizard-summary-total--horarios"><span className="label">Duración total semanal</span>{" "}<span className="value">{r.total}</span></div>
      </div>
    </div>
    <div className="sisoc-wizard-footer-row"><div className="sisoc-wizard-footer-left" /><div className="sisoc-wizard-footer-right" /></div>
    <div className="sisoc-wizard-buttons">
      <button type="submit" name="wizard_goto_step" value="horarios" className="sisoc-wizard-btn sisoc-wizard-btn--light" formNoValidate
        onClick={(e) => { e.preventDefault(); send(body({ wizard_goto_step: "horarios" })); }}><i className="fas fa-arrow-left" />{" "}Volver al paso anterior</button>
      <button type="submit" className="sisoc-wizard-btn sisoc-wizard-btn--success"><i className="fas fa-check-circle" />{" "}Confirmar y crear comisión</button>
    </div>
  </form>;
}

function Stepper({ current }: { current: Step }) {
  const done = (step: Step) => STEPS.indexOf(step) < STEPS.indexOf(current);
  const item = (step: Step, n: number, label: string, help: string) => <li key={step} className={`sisoc-wizard-step ${current === step ? " is-current" : done(step) ? " is-done" : ""}`}>
    <div className="sisoc-wizard-step-bubble">{done(step) ? <i className="fas fa-check" /> : n}</div>
    <div className="sisoc-wizard-step-label">{label}</div>
    <div className="sisoc-wizard-step-help">{help}</div>
  </li>;
  return <ol className="sisoc-wizard-stepper" aria-label="Pasos del wizard">
    {item("info", 1, "Información básica", "Datos generales de la comisión")}
    {item("horarios", 2, "Horarios", "Días y horarios de clase")}
    {item("confirmacion", 3, "Confirmación", "Revisión final")}
  </ol>;
}

function WizardBody({ initial, endpoint, forbidden }: { initial: WizardData; endpoint: string; forbidden: (d: unknown) => void }) {
  const [data, setData] = useState(initial);
  const [turn, setTurn] = useState(0);
  const [uncertain, setUncertain] = useState(false);
  const [busy, setBusy] = useState(false);
  const working = useRef(false);
  const send = useMemo(() => async (body: URLSearchParams) => {
    if (working.current) return;
    working.current = true;
    setBusy(true);
    const result = await postStep(endpoint, body);
    working.current = false;
    setBusy(false);
    if (result.kind === "redirect") vatNavigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else if (result.kind === "step") { setData(result.data); setTurn((t) => t + 1); setUncertain(false); resetAfterRejectedPost(); } else setUncertain(true);
  }, [endpoint, forbidden]);
  const key = `${data.step}:${turn}`;
  const props = { data, busy, send };
  return <>
    <NativeToasts messages={data.messages} />
    <Select2Links />
    <div className="sisoc-wizard">
      <div className="sisoc-wizard-topbar">
        <a href={data.urls.cancel} className="sisoc-wizard-delete"><i className="fas fa-times" />{" "}<span>Cancelar</span></a>
      </div>
      <div className="sisoc-wizard-header">
        <h1 className="sisoc-wizard-title">Nueva Comisión de curso</h1>
        <span className="sisoc-wizard-status">{data.estado_label}</span>
      </div>
      <Stepper current={data.step} />
      {uncertain && <p role="alert">{UNCERTAIN}</p>}
      {data.step === "info" ? <InfoStep key={key} {...props} /> : data.step === "horarios" ? <HorariosStep key={key} {...props} /> : <ConfirmStep key={key} {...props} />}
    </div>
    <style>{WIZARD_CSS}</style>
    <TourHelpInline section="curso_wizard" />
  </>;
}

function WizardPage({ cursoId }: { cursoId: string }) {
  const endpoint = API(cursoId);
  const [state, setState] = useMainResource(endpoint, wizardValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando asistente…", (data) => ({
    title: "", breadcrumb: null,
    content: <WizardBody initial={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

// Native URL of `VAT/urls.py` (`vat_comision_curso_wizard`).
const PATH = /^\/vat\/cursos\/([0-9]+)\/comision\/nueva\/$/;

export const vatComisionWizardRoute: RouteDefinition<{ cursoId: string }> = {
  name: "vat-comision-wizard",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { cursoId: m[1] } : null;
  },
  render({ cursoId }) {
    return <WizardPage key={cursoId} cursoId={cursoId} />;
  },
};
