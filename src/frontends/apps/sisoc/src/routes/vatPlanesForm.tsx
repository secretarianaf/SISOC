/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useState } from "react";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { CrispyCampo, campoValid, type Campo } from "./vatCentrosFormularioCampos";
import { CsrfInput, Select2Links, UNCERTAIN, useForbidden, useWriteForm } from "./vatFormShared";
import { bool, messagesValid, type Message } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V07.02 curricular plan form: `vat/catalogo/planversioncurricular_form.html` (alta y edición). Fields, widget attributes, locked
 * fields of the provincial role and errors come from `/api/web/vat/catalogos/planes-curriculares/`, which runs the native
 * `PlanVersionCurricularForm` and views; the POST persists through their `form_valid` (message and reference title included).
 */
export type PlanFormData = {
  editing: boolean; fields: Campo[]; non_field_errors: string[]; normativa_actual: string; page: { page_title: string; submit_text: string };
  urls: { list: string; cancel: string }; messages: Message[];
};

const API = "web/vat/catalogos/planes-curriculares/";
const NAMES = ["nombre", "sector", "subsector", "modalidad_cursada", "normativa_tipo", "normativa_numero", "normativa_anio", "horas_reloj", "nivel_requerido", "nivel_certifica", "activo"];
// The columns of the native template (`col-md-*`); `provincia` is drawn only when creating.
const COLS: Record<string, string> = {
  provincia: "col-md-12", nombre: "col-md-12", sector: "col-md-4", subsector: "col-md-4", modalidad_cursada: "col-md-4", normativa_tipo: "col-md-4",
  normativa_numero: "col-md-4", normativa_anio: "col-md-4", horas_reloj: "col-md-2", nivel_requerido: "col-md-3", nivel_certifica: "col-md-3", activo: "col-md-3",
};

export const planFormValid = (v: unknown): v is PlanFormData => record(v) && bool(v.editing) && Array.isArray(v.fields) && v.fields.every(campoValid) &&
  [...(v.fields as Campo[]).map((f) => f.name)].sort().join() === [...(v.editing ? NAMES : ["provincia", ...NAMES])].sort().join() &&
  Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && text(v.normativa_actual) &&
  record(v.page) && text(v.page.page_title) && text(v.page.submit_text) && record(v.urls) && internal(v.urls.list) && internal(v.urls.cancel) && messagesValid(v.messages);

const ICONS: Record<string, string> = { success: "fas fa-check-circle", error: "fas fa-exclamation-triangle", warning: "fas fa-exclamation-circle", info: "fas fa-info-circle" };

/** `components/alert_message.html` with `show_django_messages=True`: dismissible alerts above the page. */
function FlashAlerts({ messages }: { messages: Message[] }) {
  const [closed, setClosed] = useState<number[]>([]);
  return <>{messages.map((m, n) => (closed.includes(n) ? null : (
    <div key={n} className={`alert alert-${m.level} alert-dismissible fade show`} role="alert">
      <i className={`${ICONS[m.level]} me-2`} />{m.message}
      <button type="button" className="btn-close" aria-label="Close" onClick={() => setClosed((c) => [...c, n])} />
    </div>
  )))}</>;
}

function PlanForm({ initial, endpoint, forbidden }: { initial: PlanFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: planFormValid });
  const byName = Object.fromEntries(data.fields.map((f) => [f.name, f])) as Record<string, Campo>;
  const campo = (name: string) => <CrispyCampo key={name} f={byName[name]} id={byName[name].id} name={name} col={COLS[name]} value={String(state[name] ?? "")} onChange={(v) => set(name, v)} />;
  const activo = byName.activo;
  return <>
    <NativeToasts messages={data.messages} />
    <Select2Links />
    <link rel="stylesheet" href="/static/custom/css/vat_design.css" />
    <FlashAlerts messages={data.messages} />
    <div className="vat-ui vp-shell">
      <div className="vp-hero">
        <h1><i className="fas fa-clipboard-list me-2" />{data.page.page_title}</h1>
        <p>
          Definí el nombre del plan y su estructura académica con sector, subsector, modalidad, normativa estructurada y condiciones de certificación.
        </p>
      </div>
      <form method="post" noValidate onSubmit={(e) => void submit(e)}>
        <CsrfInput />
        {uncertain && <p role="alert">{UNCERTAIN}</p>}
        {data.non_field_errors.length > 0 && <div className="alert alert-danger"><ul className="errorlist nonfield">{data.non_field_errors.map((e, n) => <li key={n}>{e}</li>)}</ul></div>}
        <div className="card vp-panel">
          <div className="vp-panel-header"><div>
            <h3 className="card-title"><i className="fas fa-sitemap me-2" />1. Clasificación Académica</h3>
            <div className="small">Definí el nombre, sector, subsector y modalidad de cursado del plan.</div>
          </div></div>
          <div className="vp-section"><div className="row">
            {byName.provincia && campo("provincia")}
            {campo("nombre")}
            {campo("sector")}
            {campo("subsector")}
            {campo("modalidad_cursada")}
          </div></div>
        </div>
        <div className="card vp-panel">
          <div className="vp-panel-header"><div>
            <h3 className="card-title"><i className="fas fa-book me-2" />2. Datos del Plan</h3>
            <div className="small">Completá normativa estructurada, carga horaria y configuración de certificación.</div>
          </div></div>
          <div className="vp-section">
            <div className="mb-3">
              <label className="form-label mb-1">Normativa</label>
              <div className="small text-muted">Solo se edita el formato estructurado con tipo, número y año.</div>
            </div>
            {data.normativa_actual && <div className="alert alert-secondary mb-3">
              <strong>Normativa libre cargada en base:</strong>{" "}
              {data.normativa_actual}
            </div>}
            <div className="row">
              {campo("normativa_tipo")}
              {campo("normativa_numero")}
              {campo("normativa_anio")}
              {campo("horas_reloj")}
              {campo("nivel_requerido")}
              {campo("nivel_certifica")}
              <ActivoCampo f={activo} checked={state.activo === true} onChange={(v) => set("activo", v)} />
            </div>
          </div>
          <div className="vp-actions">
            <a href={data.urls.cancel} className="btn btn-secondary"><i className="fas fa-times me-1" />Cancelar</a>{" "}
            <button type="submit" className="btn btn-primary"><i className="fas fa-save me-1" />{data.page.submit_text}</button>
          </div>
        </div>
      </form>
    </div>
  </>;
}

/** `{{ form.activo|as_crispy_field }}` (crispy-bootstrap5 checkbox); the INET provincial role gets it hidden and locked. */
function ActivoCampo({ f, checked, onChange }: { f: Campo; checked: boolean; onChange: (v: boolean) => void }) {
  if (f.attrs.type === "hidden") return <div className={`${COLS.activo} vp-field`}><input type="hidden" name={f.name} id={f.id} value={f.value === true ? "on" : ""} disabled={f.disabled || undefined} readOnly /></div>;
  const invalid = f.errors.length > 0;
  return <div className={`${COLS.activo} vp-field`}><div id={`div_${f.id}`} className="mb-3 form-check">
    <input type="checkbox" name={f.name} id={f.id} className={`form-check-input checkboxinput${invalid ? " is-invalid" : ""}`} checked={checked} disabled={f.disabled || undefined}
      onChange={(e) => onChange(e.target.checked)} />{" "}
    <label htmlFor={f.id} className="form-check-label">{f.label}</label>
    {invalid && <div id={`${f.id}_error`} className="invalid-feedback">{f.errors.map((e, n) => <p key={n} id={`error_${n + 1}_${f.id}`}><strong>{e}</strong></p>)}</div>}
  </div></div>;
}

function FormPage({ id }: { id?: string }) {
  const endpoint = id ? `${API}${id}/editar/` : `${API}nuevo/`;
  const [state, setState] = useMainResource(endpoint, planFormValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: data.page.page_title, heading: data.page.page_title, breadcrumb: null,
    content: <PlanForm initial={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { id?: string };

// Native URLs of `VAT/urls.py`: `nuevo/` and `<id>/editar/`.
const PATH = /^\/vat\/catalogos\/planes-curriculares\/(?:nuevo|([0-9]+)\/editar)\/$/;

export const vatPlanesFormRoute: RouteDefinition<Params> = {
  name: "vat-planes-form",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { id: m[1] } : null;
  },
  render({ id }) {
    return <FormPage key={id ?? "nuevo"} id={id} />;
  },
};
