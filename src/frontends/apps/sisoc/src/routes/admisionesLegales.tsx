/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { Fragment, useEffect, useState, type ReactNode } from "react";
import { Pagination } from "./listControls";
import { NativeModal, NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * AD03.03 legal detail (`admisiones_legales_detalle.html`, `/comedores/admisiones/legales/ver/<pk>`)
 * and the review of the complementary report (`revisar_informe_complementario.html`). Data comes from
 * `/api/web/comedores/admisiones/legales/<pk>/`, which runs the native view; every button, modal and
 * form is drawn as the template does and posts to the endpoint of its action, which runs the native
 * `LegalesService` handler (messages verbatim). A rejected form answers 400 with the bound form and
 * the modal stays open with its errors, like the native re-render.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Choice = { value: string; label: string };
type Field = {
  name: string; label: string; kind: "text" | "select" | "textarea" | "date" | "number" | "checkbox" | "file"; required: boolean;
  value: string | boolean; help_text: string; errors: string[]; id: string; attrs: Record<string, string | boolean>; choices?: Choice[];
};
type FormPayload = { fields: Field[]; non_field_errors: string[] };
type Boton = { key: string; texto: string; modal: string | null; clase: string; url: string | null };
type Providencia = { pdf: string | null; docx: string | null; numero_gde_pv: string | null } | null;
type Final = { pdf: string | null; docx: string | null; numero_if: string | null };
type Page = { is_paginated: boolean; number: number; count: number; has_rows: boolean; previous: number | null; next: number | null; range: (number | "…")[]; param: string; query_without_page: string };
const FORM_KEYS = ["rectificar", "numero_expediente", "primera_providencia", "segunda_providencia", "gde_pv_primera", "gde_pv_segunda", "intervencion_juridicos", "if_proyecto_convenio", "convenio", "reinicio_expediente", "solicitar_complementario"] as const;
type FormKey = (typeof FORM_KEYS)[number];
export type LegalData = {
  id: number;
  titulo: { num_expediente: string; archivada: boolean; rechazo: string; estado: string };
  urls: { lista: string; pagina: string };
  botones: Boton[];
  expediente: {
    estado: string; numero: string; proyecto: Final | null; primera_providencia: Providencia; segunda_providencia: Providencia;
    intervencion: { label: string; rechazo: string | null } | null; dictamen: string | null;
    disposicion: { numero: string; archivo: string | null } | null; convenio: { numero: string; archivo: string | null } | null;
  };
  admision: {
    tipo: string; tipo_convenio: string; estado: string; fecha: string; vencimiento_mandatos: string; num_expediente: string; informe_pdf: string | null;
    complementarios: { fecha: string; estado: string; pdf: string | null }[]; complementario_final: Final | null;
  };
  comedor: { id: number; nombre: string; url: string; tipo: string; programa: string; organizacion: string; ubicacion: string; calle: string };
  es_judicializado: boolean; tipo_admision: string;
  documentos: { id: number; nombre: string; archivo_url: string | null }[];
  historial_estados: { headers: { title: string; width: string | null }[]; rows: string[][]; page: Page };
  forms: Record<FormKey, FormPayload>;
  messages: Message[];
};
type Result = { messages: Message[]; estado_legales: string | null; botones: Boton[] };
export type RevisionData = {
  id: number; comedor: string; urls: { legal: string };
  informe: { estado: string; creado_por: string; fecha: string; campos: { campo: string; value: string }[] } | null; messages: Message[];
};

const API = "web/comedores/admisiones/legales/";
const LEVELS = ["success", "error", "warning", "info"];
const KINDS = ["text", "select", "textarea", "date", "number", "checkbox", "file"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const list = (v: unknown, ok: (x: unknown) => boolean) => Array.isArray(v) && v.every(ok);
const strings = (v: unknown, keys: string[]) => record(v) && keys.every((k) => text(v[k]));
const nullableText = (v: unknown) => v === null || text(v);
const fileUrl = (v: unknown) => v === null || internal(v) || (text(v) && /^https?:\/\//.test(v));
const messagesOk = (v: unknown) => list(v, (m) => strings(m, ["message"]) && LEVELS.includes((m as Message).level));
const fieldOk = (f: unknown) => strings(f, ["name", "label", "id", "help_text"]) && KINDS.includes((f as Field).kind) && typeof (f as Field).required === "boolean" && list((f as Field).errors, text) && record((f as Field).attrs);
const formOk = (f: unknown) => record(f) && list(f.fields, fieldOk) && list(f.non_field_errors, text);
const providenciaOk = (p: unknown) => p === null || (record(p) && fileUrl(p.pdf) && fileUrl(p.docx) && nullableText(p.numero_gde_pv));
const finalOk = (p: unknown) => p === null || (record(p) && fileUrl(p.pdf) && fileUrl(p.docx) && nullableText(p.numero_if));

export function legalValid(v: unknown): v is LegalData {
  if (!record(v) || !record(v.titulo) || !record(v.urls) || !record(v.expediente) || !record(v.admision) || !record(v.comedor) || !record(v.historial_estados) || !record(v.forms)) return false;
  const e = v.expediente, a = v.admision, h = v.historial_estados, p = h.page;
  if (!record(p)) return false;
  return int(v.id) && strings(v.titulo, ["num_expediente", "rechazo", "estado"]) && typeof v.titulo.archivada === "boolean" && internal(v.urls.lista) && internal(v.urls.pagina) &&
    list(v.botones, (b) => strings(b, ["key", "texto", "clase"]) && (b as Boton).modal !== undefined && nullableText((b as Boton).modal) && nullableText((b as Boton).url)) &&
    strings(e, ["estado", "numero"]) && finalOk(e.proyecto) && providenciaOk(e.primera_providencia) && providenciaOk(e.segunda_providencia) &&
    (e.intervencion === null || (record(e.intervencion) && text(e.intervencion.label) && nullableText(e.intervencion.rechazo))) && nullableText(e.dictamen) &&
    (e.disposicion === null || (record(e.disposicion) && text(e.disposicion.numero) && fileUrl(e.disposicion.archivo))) &&
    (e.convenio === null || (record(e.convenio) && text(e.convenio.numero) && fileUrl(e.convenio.archivo))) &&
    strings(a, ["tipo", "tipo_convenio", "estado", "fecha", "vencimiento_mandatos", "num_expediente"]) && fileUrl(a.informe_pdf) && finalOk(a.complementario_final) &&
    list(a.complementarios, (c) => strings(c, ["fecha", "estado"]) && fileUrl((c as Record<string, unknown>).pdf)) &&
    int(v.comedor.id) && strings(v.comedor, ["nombre", "tipo", "programa", "organizacion", "ubicacion", "calle"]) && internal(v.comedor.url) &&
    typeof v.es_judicializado === "boolean" && text(v.tipo_admision) &&
    list(v.documentos, (d) => record(d) && int(d.id) && text(d.nombre) && (d.archivo_url === null || text(d.archivo_url))) &&
    list(h.headers, (x) => record(x) && text(x.title) && nullableText(x.width)) && list(h.rows, (r) => list(r, text)) &&
    typeof p.is_paginated === "boolean" && typeof p.has_rows === "boolean" && int(p.number) && int(p.count) && (p.previous === null || int(p.previous)) && (p.next === null || int(p.next)) &&
    list(p.range, (n) => n === "…" || int(n)) && text(p.param) && text(p.query_without_page) &&
    FORM_KEYS.every((k) => formOk((v.forms as Record<string, unknown>)[k])) && messagesOk(v.messages);
}

export function revisionValid(v: unknown): v is RevisionData {
  if (!record(v) || !record(v.urls)) return false;
  return int(v.id) && text(v.comedor) && internal(v.urls.legal) && messagesOk(v.messages) &&
    (v.informe === null || (record(v.informe) && strings(v.informe, ["estado", "creado_por", "fecha"]) && list(v.informe.campos, (c) => strings(c, ["campo", "value"]))));
}

/** The CSS the template links (`numeroExpedienteModal.css`). */
const EXPEDIENTE_CSS = `
.modal-dialog.modal-expediente-amplio {
  width: min(70vw, 1000px);
  max-width: min(70vw, 1000px);
}

.modal-expediente-amplio .expediente-estructurado-grid {
  display: grid;
  grid-template-columns:
    minmax(110px, 0.8fr)
    minmax(170px, 1.1fr)
    minmax(210px, 1.5fr)
    minmax(140px, 1fr);
  gap: 1rem;
  align-items: end;
  margin: 0;
}

.modal-expediente-amplio .expediente-estructurado-grid > div {
  width: auto;
  max-width: none;
  padding: 0;
}

.modal-expediente-amplio .expediente-estructurado-grid .form-control {
  width: 100%;
  min-width: 0;
}

.modal-expediente-amplio .expediente-estructurado-grid .input-group .form-control {
  width: 1%;
  flex: 1 1 auto;
}

.modal-expediente-amplio .expediente-estructurado-grid .input-group {
  display: flex !important;
  flex-flow: row nowrap !important;
  align-items: stretch;
  width: 100%;
}

.modal-expediente-amplio .expediente-estructurado-grid .input-group-text {
  display: flex !important;
  flex: 0 0 auto;
  align-items: center;
  white-space: nowrap;
}

@media (max-width: 767.98px) {
  .modal-dialog.modal-expediente-amplio {
    width: auto;
    max-width: calc(100vw - 1rem);
    margin: 0.5rem;
  }

  .modal-expediente-amplio .expediente-estructurado-grid {
    grid-template-columns: 1fr;
  }
}
`;

const ATTR_NAMES: Record<string, string> = { class: "className", maxlength: "maxLength", minlength: "minLength", inputmode: "inputMode", autocomplete: "autoComplete" };
const NUMERIC = ["maxLength", "minLength", "cols", "rows"];
/** The HTML attributes of a native widget as React props (`class` and `value` are decided by the caller). */
function attrProps(attrs: Record<string, string | boolean>, skip: string[] = []) {
  const props: Record<string, unknown> = {};
  for (const [name, value] of Object.entries(attrs)) {
    const key = ATTR_NAMES[name] ?? name;
    if (skip.includes(key)) continue;
    props[key] = NUMERIC.includes(key) ? Number(value) : value;
  }
  return props;
}

/** crispy-bootstrap5 `as_crispy_field`. */
function Crispy({ f, value, onChange, onFile, required }: { f: Field; value: string; onChange: (v: string) => void; onFile?: (file: File | null) => void; required?: boolean }) {
  const invalid = f.errors.length > 0;
  const base = f.kind === "select" ? "select form-select" : f.kind === "textarea" ? "textarea form-control" : f.kind === "file" ? "form-control" : "textinput form-control";
  const props: Record<string, unknown> = { name: f.name, id: f.id, ...attrProps(f.attrs, ["className", "required"]) };
  const isRequired = required ?? f.required;
  if (isRequired) props.required = true;
  props.className = `${base}${invalid ? " is-invalid" : ""}`;
  if (invalid) { props["aria-invalid"] = "true"; props["aria-describedby"] = `${f.id}_error`; }
  let input: ReactNode;
  if (f.kind === "select") input = <select {...props} value={value} onChange={(e) => onChange(e.target.value)}>{(f.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}</select>;
  else if (f.kind === "textarea") input = <textarea {...props} value={value} onChange={(e) => onChange(e.target.value)} />;
  else if (f.kind === "file") input = <div><input {...props} type="file" onChange={(e) => onFile?.(e.target.files?.[0] ?? null)} /></div>;
  else input = <input {...props} type="text" value={value} onChange={(e) => onChange(e.target.value)} />;
  return <div id={`div_${f.id}`} className="mb-3">
    {f.label !== "" && <label htmlFor={f.id} className={`form-label${isRequired ? " requiredField" : ""}`}>{f.label}{isRequired && <span className="asteriskField">*</span>}</label>}
    {input}
    {invalid && <div id={`${f.id}_error`} className="invalid-feedback">{f.errors.map((e, i) => <p key={i} id={`error_${i + 1}_${f.id}`}><strong>{e}</strong></p>)}</div>}
    {f.help_text !== "" && <div id={`hint_${f.id}`} className="form-text">{f.help_text}</div>}
  </div>;
}

/** `{{ form.<campo> }}`: the bare widget of the structured numbers. */
function Bare({ f, value, onChange }: { f: Field; value: string; onChange: (v: string) => void }) {
  const { class: widgetClass, ...rest } = f.attrs;
  return <input type="text" name={f.name} id={f.id} {...attrProps(rest)} className={String(widgetClass ?? "")} value={value} onChange={(e) => onChange(e.target.value)} />;
}

/** `{{ form.<campo>.errors }}`. */
const ErrorList = ({ errors }: { errors: string[] }) => (errors.length ? <ul className="errorlist">{errors.map((e, i) => <li key={i}>{e}</li>)}</ul> : null);
const NonField = ({ errors }: { errors: string[] }) => (errors.length ? <div className="alert alert-danger mt-3 mb-0"><ul className="errorlist nonfield">{errors.map((e, i) => <li key={i}>{e}</li>)}</ul></div> : null);

type Ctx = { form: FormPayload; values: Record<string, string>; set: (name: string, value: string) => void; field: (name: string) => Field; file: (f: File | null) => void };

/** `partials/numero_expediente_estructurado.html` and `partials/numero_pv_estructurado.html`. */
function Estructurado({ ctx, prefix }: { ctx: Ctx; prefix: "expediente" | "pv" }) {
  const parts: [string, string, string | null, string][] = prefix === "expediente"
    ? [["expediente_anio", "Año", "EX-", "col-12 col-md-2"], ["expediente_numero", "Número", null, "col-12 col-md-3"], ["expediente_reparticion", "Repartición", "APN-", "col-12 col-md-4"], ["expediente_organismo", "Organismo", "#", "col-12 col-md-3"]]
    : [["pv_anio", "Año", "PV-", "col-12 col-md-3"], ["pv_numero", "Número", null, "col-12 col-md-3"], ["pv_reparticion", "Repartición", "APN-", "col-12 col-md-3"], ["pv_organismo", "Organismo", "#", "col-12 col-md-3"]];
  return <>
    <div className={prefix === "expediente" ? "row g-3 expediente-estructurado-grid" : "row g-3"}>
      {parts.map(([name, title, addon, col]) => {
        const f = ctx.field(name);
        const input = <Bare f={f} value={ctx.values[name] ?? ""} onChange={(v) => ctx.set(name, v)} />;
        return <div key={name} className={col}>
          <label className="form-label" htmlFor={f.id}>{title}</label>
          {addon ? <div className="input-group"><span className="input-group-text">{addon}</span>{input}</div> : input}
          <ErrorList errors={f.errors} />
        </div>;
      })}
    </div>
    <NonField errors={ctx.form.non_field_errors} />
  </>;
}

type Action = { run: (accion: string, values: Record<string, string>, file: File | null) => Promise<FormPayload | null> };
type ModalSpec = {
  id: string; title: string; accion: string; formKey?: FormKey; size?: string; header?: string;
  submit: { id: string; name: string; className: string; label: string };
  body: (ctx: Ctx) => ReactNode;
};

/** One native modal with its form: the HTML validation runs on submit and a 400 leaves it open with the bound form. */
function ActionModal({ spec, data, action, close }: { spec: ModalSpec; data: LegalData; action: Action; close: () => void }) {
  const [form, setForm] = useState<FormPayload>(spec.formKey ? data.forms[spec.formKey] : { fields: [], non_field_errors: [] });
  const initial = (f: FormPayload) => Object.fromEntries(f.fields.filter((x) => x.kind !== "file").map((x) => [x.name, typeof x.value === "string" ? x.value : ""]));
  const [values, setValues] = useState<Record<string, string>>(() => initial(form));
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    const rejected = await action.run(spec.accion, values, file);
    setBusy(false);
    if (rejected) { setForm(rejected); setValues(initial(rejected)); }
  };
  const ctx: Ctx = {
    form, values, set: (name, value) => setValues((current) => ({ ...current, [name]: value })),
    field: (name) => form.fields.find((x) => x.name === name) as Field, file: setFile,
  };
  return (
    <NativeModal id={spec.id} title={spec.title} close={close} busy={busy} size={spec.size ?? " modal-dialog-centered"} controls="button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled])">
      <div className="modal-content">
        <form method="POST" action="" onSubmit={(e) => void submit(e)}>
          <div className="modal-header">
            <h5 className="modal-title">{spec.header ?? spec.title}</h5>
            <button type="button" className="btn-close" aria-label="Close" onClick={close} />
          </div>
          {spec.body(ctx)}
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>{" "}
            <button type="submit" id={spec.submit.id} name={spec.submit.name} className={spec.submit.className} disabled={busy}>{spec.submit.label}</button>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}

const crispy = (ctx: Ctx, name: string, required?: boolean) => <Crispy f={ctx.field(name)} value={ctx.values[name] ?? ""} onChange={(v) => ctx.set(name, v)} onFile={ctx.file} required={required} />;
const readonly = (label: string, value: string) => <div className="mb-3"><label className="form-label">{label}</label><input type="text" className="form-control" value={value} readOnly /></div>;

function IntervencionBody({ ctx }: { ctx: Ctx }) {
  const rechazado = ctx.values.intervencion_juridicos === "rechazado";
  const dictamen = rechazado && ctx.values.rechazo_juridicos_motivo === "dictamen";
  return <div className="modal-body mb-2">
    {crispy(ctx, "intervencion_juridicos")}
    <div id="motivoRechazoField" style={{ display: rechazado ? "block" : "none" }}>{crispy(ctx, "rechazo_juridicos_motivo", rechazado)}</div>
    <div id="motivoDictamenField" style={{ display: dictamen ? "block" : "none" }}>{crispy(ctx, "dictamen_motivo", dictamen)}</div>
  </div>;
}

function specs(data: LegalData): Record<string, ModalSpec> {
  const primaryBtn = (id: string, name: string, label: string, className = "btn btn-primary") => ({ id, name, className, label });
  return {
    modalIntervencionJuridicos: {
      id: "modalIntervencionJuridicos", title: "Expediente:", accion: "intervencion-juridicos", formKey: "intervencion_juridicos",
      submit: primaryBtn("IntervencionJuridicosId", "BtnIntervencionJuridicos", "Confirmar"), body: (ctx) => <IntervencionBody ctx={ctx} />,
    },
    modalRectificar: {
      id: "modalRectificar", title: "Enviar a Rectificar", accion: "rectificar", formKey: "rectificar", size: " modal-dialog-centered modal-lg",
      submit: primaryBtn("btnObservaciones_id", "btnObservaciones", "Enviar", "btn btn-warning"),
      body: (ctx) => {
        const f = ctx.field("observaciones");
        const { class: widgetClass, ...rest } = f.attrs;
        return <div className="modal-body"><div className="mb-3">
          <label htmlFor={f.id}>{f.label}:</label>{" "}
          <textarea name={f.name} id={f.id} {...attrProps(rest)} className={String(widgetClass)} value={ctx.values.observaciones ?? ""} onChange={(e) => ctx.set("observaciones", e.target.value)} />
          {f.errors.length > 0 && <div className="text-danger"><ErrorList errors={f.errors} /></div>}
        </div></div>;
      },
    },
    modalPrimeraProvidencia: {
      id: "modalPrimeraProvidencia", title: "Generar Primera Providencia", accion: "primera-providencia", formKey: "primera_providencia",
      submit: primaryBtn("btnPrimeraProvidencia_id", "btnPrimeraProvidencia", "Generar"),
      body: (ctx) => <div className="modal-body">
        {readonly("Número de Providencia", "Primera Providencia")}
        {readonly("Tipo de Admisión", data.tipo_admision === "" ? "Sin información" : data.tipo_admision)}
        {crispy(ctx, "cantidad_espacios")}
        {readonly("¿Es Judicializado?", data.es_judicializado ? "Sí" : "No")}
        {data.es_judicializado && <>{crispy(ctx, "caratula_causa")}{crispy(ctx, "juzgado")}{crispy(ctx, "memo")}</>}
      </div>,
    },
    modalSegundaProvidencia: {
      id: "modalSegundaProvidencia", title: "Generar Segunda Providencia", accion: "segunda-providencia", formKey: "segunda_providencia", size: " modal-dialog-centered modal-lg",
      submit: primaryBtn("btnSegundaProvidencia_id", "btnSegundaProvidencia", "Generar"),
      body: (ctx) => <div className="modal-body">
        {readonly("Número de Providencia", "Segunda Providencia")}
        <label className="form-label">Número de PV de la Primera Providencia</label>
        <Estructurado ctx={ctx} prefix="pv" />
      </div>,
    },
    modalFormConvenio: {
      id: "modalFormConvenio", title: "Formulario Proyecto de Convenio", accion: "proyecto-convenio",
      submit: primaryBtn("btnProyectoConvenio_id", "btnProyectoConvenio", "Aceptar"),
      body: () => <div className="modal-body">Generará los archivos del Formulario Proyecto de Convenio.</div>,
    },
    modalReinicioExpediente: {
      id: "modalReinicioExpediente", title: "Reinicio de Expediente", accion: "reinicio-expediente", formKey: "reinicio_expediente",
      submit: primaryBtn("btnReinicioExpedienteID", "btnReinicioExpediente", "Aceptar", "btn btn-danger"),
      body: (ctx) => <div className="modal-body"><h6 className="mb-3 fw-bold">Esta seguro que desea Reiniciar el Expediente y enviar a Archivo?</h6>{crispy(ctx, "observaciones_reinicio_expediente")}</div>,
    },
    modalSolicitarInformeComplementario: {
      id: "modalSolicitarInformeComplementario", title: "Solicitar Informe Técnico Complementario", accion: "solicitar-complementario", formKey: "solicitar_complementario",
      submit: primaryBtn("btnInformeComplementarioID", "btnInformeComplementario", "Aceptar"),
      body: (ctx) => <div className="modal-body">{crispy(ctx, "observaciones_informe_tecnico_complementario")}</div>,
    },
    modalConvenio: {
      id: "modalConvenio", title: "Convenio", accion: "convenio", formKey: "convenio",
      submit: primaryBtn("btnConvenioID", "btnConvenio", "Guardar"),
      body: (ctx) => <div className="modal-body">{crispy(ctx, "numero_convenio")}{crispy(ctx, "archivo_convenio")}</div>,
    },
    modalLegalesNumIF: {
      id: "modalLegalesNumIF", title: "Agrege el número de expediente", accion: "numero-expediente", formKey: "numero_expediente", size: " modal-dialog-centered modal-expediente-amplio",
      submit: primaryBtn("btnLegalesNumIF_id", "btnLegalesNumIF", "Guardar"),
      body: (ctx) => <div className="modal-body">
        <Estructurado ctx={ctx} prefix="expediente" />
        <small className="text-muted">Legales puede rectificar el dato; el cambio se aplicará a las etapas siguientes.</small>
      </div>,
    },
    modalConvenioNumIF: {
      id: "modalConvenioNumIF", title: "Agrege el número IF de Proyecto de Convenio", accion: "if-proyecto-convenio", formKey: "if_proyecto_convenio",
      submit: primaryBtn("btnConvenioNumIF_id", "btnConvenioNumIF", "Guardar"),
      body: (ctx) => <div className="modal-body">{crispy(ctx, "numero_if")}</div>,
    },
    modalGDEPVPrimera: {
      id: "modalGDEPVPrimera", title: "Cargar número de GDE PV", accion: "gde-pv-primera", formKey: "gde_pv_primera", size: " modal-dialog-centered modal-lg",
      submit: primaryBtn("btnGDEPVPrimera_id", "btnGDEPVPrimera", "Guardar"),
      body: (ctx) => <div className="modal-body"><Estructurado ctx={ctx} prefix="pv" /></div>,
    },
    modalGDEPVSegunda: {
      id: "modalGDEPVSegunda", title: "Cargar número de GDE Segunda PV", accion: "gde-pv-segunda", formKey: "gde_pv_segunda", size: " modal-dialog-centered modal-lg",
      submit: primaryBtn("btnGDEPVSegunda_id", "btnGDEPVSegunda", "Guardar"),
      body: (ctx) => <div className="modal-body"><Estructurado ctx={ctx} prefix="pv" /></div>,
    },
  };
}

/** The modal `IF Informe Técnico Complementario`: a bare input the native handler reads. */
function IfComplementarioModal({ action, close }: { action: Action; close: () => void }) {
  const [numero, setNumero] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <NativeModal id="modalIFInformeComplementario" title="IF Informe Técnico Complementario" close={close} busy={busy} size=" modal-dialog-centered" controls="button:not([disabled]),input:not([disabled])">
      <div className="modal-content">
        <form method="POST" action="" onSubmit={(e) => { e.preventDefault(); setBusy(true); void action.run("if-complementario", { numero_if_complementario: numero }, null).then(() => setBusy(false)); }}>
          <div className="modal-header">
            <h5 className="modal-title">IF Informe Técnico Complementario</h5>
            <button type="button" className="btn-close" aria-label="Close" onClick={close} />
          </div>
          <div className="modal-body">
            <div className="form-group">
              <label htmlFor="numero_if_complementario">Número IF:</label>{" "}
              <input type="text" className="form-control" name="numero_if_complementario" id="numero_if_complementario" required value={numero} onChange={(e) => setNumero(e.target.value)} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>{" "}
            <button type="submit" className="btn btn-success" name="btnIFInformeComplementario" id="btnIFInformeComplementario_id" disabled={busy}>Guardar</button>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}

const pdfIcon = (cls = "h5 mx-2") => <i className={`bi bi-filetype-pdf text-info ${cls} text-bold`} />;
const docxIcon = (cls = "h5 mx-2") => <i className={`bi bi-filetype-docx text-info ${cls} text-bold`} />;

function Documento({ item }: { item: Providencia | Final | null }) {
  return <>{item?.pdf && <><a href={item.pdf} target="_blank" rel="noopener">{pdfIcon()}</a>{" "}</>}{item?.docx && <><a href={item.docx} download>{docxIcon()}</a>{" "}</>}</>;
}

function Entry({ children }: { children: ReactNode }) {
  return <li className="nav-item"><div className="comment-text">{children}</div></li>;
}

function Providencias({ p, label }: { p: Providencia; label: string }) {
  return <Entry>
    {label}:{" "}
    {p ? <>
      <Documento item={p} />
      {p.numero_gde_pv ? <><br />{p.numero_gde_pv}{" "}<i className="bi bi-check-circle-fill text-success" /></> : <i className="bi bi-exclamation-circle-fill text-warning" />}
    </> : <i className="bi bi-x-circle-fill text-danger" />}
  </Entry>;
}

function ExpedienteCard({ data }: { data: LegalData }) {
  const e = data.expediente;
  return (
    <div className="col-4"><div className="card card-primary card-outline h-100">
      <div className="card-header"><h2 className="card-title fw-bold fs-3">Expediente</h2></div>
      <div className="card-body card-comments"><ul className="nav nav-pills flex-column">
        <Entry>Estado expediente:{" "}<span className="fw-bold">{e.estado}</span></Entry>
        <Entry>Número de expediente:{" "}<span className="fw-bold">{e.numero}</span></Entry>
        <Entry>
          Formulario Proyecto de Convenio:{" "}
          {e.proyecto ? <>
            <Documento item={e.proyecto} />
            {e.proyecto.numero_if ? <><br />{e.proyecto.numero_if}{" "}<i className="bi bi-check-circle-fill text-success" /></> : <i className="bi bi-exclamation-circle-fill text-warning" />}
          </> : <i className="bi bi-x-circle-fill text-danger" />}
        </Entry>
        <Providencias p={e.primera_providencia} label="Primera Providencia" />
        <Providencias p={e.segunda_providencia} label="Segunda Providencia" />
        <Entry>
          Intervención Juridicos:{" "}
          {e.intervencion ? <>
            <span className="fw-bold">{e.intervencion.label}</span>{" "}
            {e.intervencion.rechazo !== null && <>- <span className="fw-bold">{e.intervencion.rechazo}</span>{" "}</>}
            <i className="bi bi-check-circle-fill text-success" />
          </> : <i className="bi bi-x-circle-fill text-danger" />}
        </Entry>
        {e.dictamen !== null ? <Entry>Motivo Dictamen:{" "}<span className="fw-bold">{e.dictamen}</span></Entry> : <>
          {e.disposicion && <Entry>
            Disposición:{" "}
            {e.disposicion.archivo && <><a href={e.disposicion.archivo} target="_blank" rel="noopener"><i className="bi bi-file-earmark-check text-info h5 mx-2 text-bold" /></a>{" "}</>}
            <span className="fw-bold">{e.disposicion.numero}</span>{" "}<i className="bi bi-check-circle-fill text-success" />
          </Entry>}
          <Entry>
            Convenio:{" "}
            {e.convenio ? <>
              <a href={e.convenio.archivo ?? undefined} target="_blank" rel="noopener"><i className="bi bi-file-earmark-check text-info h5 mx-2 text-bold" /></a>{" "}
              <span className="fw-bold">{e.convenio.numero}</span>{" "}<i className="bi bi-check-circle-fill text-success" />
            </> : <i className="bi bi-x-circle-fill text-danger" />}
          </Entry>
        </>}
      </ul></div>
    </div></div>
  );
}

function AdmisionCard({ data }: { data: LegalData }) {
  const a = data.admision;
  return (
    <div className="col-4"><div className="card card-primary card-outline h-100">
      <div className="card-header"><h2 className="card-title fw-bold fs-3">Admisión</h2></div>
      <div className="card-body card-comments"><ul className="nav nav-pills flex-column">
        <Entry>Tipo:{" "}<span className="fw-bold">{a.tipo}</span></Entry>
        <Entry>Tipo Convenio:{" "}<span className="fw-bold">{a.tipo_convenio}</span></Entry>
        <Entry>Estado:{" "}<span className="fw-bold">{a.estado}</span></Entry>
        <Entry>Fecha:{" "}<span className="fw-bold">{a.fecha}</span></Entry>
        <Entry>Fecha de vencimiento de mandatos:{" "}<span className="fw-bold">{a.vencimiento_mandatos}</span></Entry>
        <Entry>Número de Expediente:{" "}<span className="fw-bold">{a.num_expediente}</span></Entry>
        {a.informe_pdf && <Entry>Informe Técnico:{" "}<a href={a.informe_pdf} target="_blank" rel="noopener">{pdfIcon("h4 ms-3")}</a></Entry>}
        {a.complementarios.length > 0 && <Entry>
          Informes Complementarios:{" "}
          {a.complementarios.map((c, n) => <Fragment key={n}>
            {c.pdf ? <span className="fw-bold"><a href={c.pdf} target="_blank" rel="noopener">{pdfIcon("h4 ms-3")}{c.fecha} ({c.estado})</a></span> : <span className="fw-bold">{c.fecha} - {c.estado}</span>}
            <br />
          </Fragment>)}
        </Entry>}
        {a.complementario_final && <Entry>
          Informe Técnico Complementario Final:{" "}
          {a.complementario_final.pdf && <><a href={a.complementario_final.pdf} target="_blank" rel="noopener">{pdfIcon("h4 ms-3")}</a>{" "}</>}
          {a.complementario_final.docx && <><a href={a.complementario_final.docx} target="_blank" rel="noopener">{docxIcon("h4 ms-3")}</a>{" "}</>}
          {a.complementario_final.numero_if && <><br />IF: {a.complementario_final.numero_if}</>}
        </Entry>}
      </ul></div>
    </div></div>
  );
}

function ComedorCard({ data }: { data: LegalData }) {
  const c = data.comedor;
  return (
    <div className="col-4"><div className="card card-primary card-outline">
      <div className="card-header"><h2 className="card-title fw-bold fs-3">Comedor</h2></div>
      <div className="card-body card-comments p-3"><ul className="nav nav-pills flex-column">
        <Entry>Nombre:{" "}<a href={c.url}><span className="fw-bold">{c.nombre}</span></a></Entry>
        <Entry>Tipo Comedor:{" "}<span className="fw-bold">{c.tipo}</span></Entry>
        <Entry>Programa:{" "}<span className="fw-bold">{c.programa}</span></Entry>
        <Entry>Organización:{" "}<span className="fw-bold">{c.organizacion}</span></Entry>
        <Entry>Provincia:{" "}<span className="fw-bold">{c.ubicacion}</span></Entry>
        <Entry>Calle:{" "}<span className="fw-bold">{c.calle}</span></Entry>
      </ul></div>
    </div></div>
  );
}

/** `components/data_table.html` (custom cells, no actions) with its pagination. */
function Historial({ data }: { data: LegalData }) {
  const h = data.historial_estados, p = h.page;
  return (
    <div className="col-12 mt-3"><div className="card">
      <div className="card-header"><h2 className="card-title fw-bold fs-3">Historial de estados</h2></div>
      <div className="card-body p-0">
        <div className="row mt-5 max-width-100"><div className="col-12"><div className="card"><div className="card-body">
          <div className="table-responsive-lg">
            <table className="table table-bordered table-striped projects ">
              <thead><tr>{h.headers.map((x) => <th key={x.title} style={x.width ? { width: x.width } : undefined}>{x.title}</th>)}</tr></thead>
              <tbody>
                {h.rows.length ? h.rows.map((row, r) => <tr key={r}>{row.map((c, i) => <td key={i}>{c}</td>)}</tr>)
                  : <tr><td colSpan={h.headers.length} className="text-center text-muted py-4">No hay cambios de estado registrados</td></tr>}
              </tbody>
            </table>
          </div>
          <Pagination paginated={p.is_paginated} number={p.number} previous={p.previous} next={p.next} range={p.range}
            href={(n) => `?${p.query_without_page}${p.param}=${n}`} count={p.has_rows ? p.count : null} />
        </div></div></div></div>
      </div>
    </div></div>
  );
}

function Documentacion({ data }: { data: LegalData }) {
  return (
    <div className="col-12"><div className="card">
      <div className="card-header"><h2 className="card-title fw-bold fs-3">Documentación</h2></div>
      <div className="card-body card-comments p-0 pb-1"><div className="container mt-2 table-responsive">
        <table className="table table-striped table-bordered table-hover table-sm" id="tablaDocumentos">
          <thead><tr><th>Documento</th><th>Archivo</th></tr></thead>
          <tbody>
            {data.documentos.map((d) => <tr key={d.id} id={`fila-${d.id}`}>
              <td className="ps-3">{d.nombre}</td>
              <td><a href={d.archivo_url ?? "None"} target="_blank" rel="noopener" className="btn btn-primary btn-sm">Ver Archivo</a></td>
            </tr>)}
          </tbody>
        </table>
      </div></div>
    </div></div>
  );
}

/** The `titulo-pagina` block. */
export function LegalHeading({ data }: { data: LegalData }): ReactNode {
  const t = data.titulo;
  return <>{t.num_expediente} -{" "}{t.archivada ? <span className="fs-5 bg-danger text-white">Rechazado: {t.rechazo} / Enviado a Archivo</span> : t.estado}</>;
}

export function LegalBreadcrumb({ data }: { data: LegalData }) {
  return <ol className="breadcrumb float-sm-right">
    <div className="breadcrumb-item"><a href={data.urls.lista}>Expedientes</a></div>
    <div className="breadcrumb-item active">{data.titulo.num_expediente}</div>
  </ol>;
}

type Outcome = { status: number; data: unknown };

/** The native request of a modal: form-encoded, or multipart when it carries the agreement file. */
async function postAction(endpoint: string, values: Record<string, string>, file: File | null): Promise<Outcome> {
  let body: URLSearchParams | FormData;
  if (file) {
    body = new FormData();
    Object.entries(values).forEach(([k, v]) => (body as FormData).append(k, v));
    body.append("archivo_convenio", file);
  } else {
    body = new URLSearchParams(values);
  }
  const { data, status } = await webClient.post(endpoint, body, { validateStatus: () => true });
  return { status, data };
}

const resultOk = (v: unknown): v is Result => record(v) && messagesOk(v.messages) && Array.isArray(v.botones);

export function LegalContent({ initial }: { initial: LegalData }) {
  const [data, setData] = useState(initial);
  const [open, setOpen] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const endpoint = `${API}${initial.id}/`;
  const reread = async (messages: Message[]) => {
    try {
      const { data: fresh } = await webClient.get(endpoint, { validateStatus: () => true });
      if (legalValid(fresh)) setData({ ...fresh, messages: [...messages, ...fresh.messages] });
    } catch { /* the page keeps its last data */ }
    setTick((n) => n + 1);
  };
  const action: Action = {
    run: async (accion, values, file) => {
      let outcome: Outcome;
      try { outcome = await postAction(`${endpoint}acciones/${accion}/`, values, file); } catch { outcome = { status: 0, data: null }; }
      if (outcome.status === 400 && record(outcome.data) && formOk(outcome.data)) {
        resetAfterRejectedPost();
        return outcome.data as unknown as FormPayload;
      }
      setOpen(null);
      await reread(resultOk(outcome.data) && (outcome.status === 200 || outcome.status === 409) ? outcome.data.messages : []);
      return null;
    },
  };
  // The native page reloads after the POST: the view starts at the top with the focus at the start of the document.
  useEffect(() => { if (tick > 0) resetAfterRejectedPost(); }, [tick]);
  const modals = specs(data);
  return (
    <>
      <style>{EXPEDIENTE_CSS}</style>
      <NativeToasts key={tick} messages={data.messages} />
      <div className="row justify-content-between d-print-none mx-1 mb-3">
        <div className="col-auto">
          {data.botones.map((b) => (b.url
            ? <Fragment key={b.key}><a href={b.url} className={`btn ${b.clase} mr-1`}>{b.texto}</a>{" "}</Fragment>
            : <Fragment key={b.key}><button type="button" className={`btn ${b.clase} mr-1`} data-bs-toggle="modal" data-bs-target={`#${b.modal}`} onClick={() => setOpen(b.modal)}>{b.texto}</button>{" "}</Fragment>))}
        </div>
      </div>
      <div className="row mb-3"><ExpedienteCard data={data} /><AdmisionCard data={data} /><ComedorCard data={data} /></div>
      <div className="row"><Documentacion data={data} /><Historial data={data} /></div>
      {open && modals[open] && <ActionModal key={open} spec={modals[open]} data={data} action={action} close={() => setOpen(null)} />}
      {open === "modalIFInformeComplementario" && <IfComplementarioModal action={action} close={() => setOpen(null)} />}
    </>
  );
}

function LegalPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/${window.location.search}`, legalValid);
  return renderMain(state, "Cargando expediente…", (data) => ({
    title: `Expediente: ${data.titulo.num_expediente}`,
    heading: <LegalHeading data={data} />,
    breadcrumb: <LegalBreadcrumb data={data} />,
    content: <LegalContent initial={data} />,
  }));
}

/** `revisar_informe_complementario.html`. */
export function RevisionContent({ data }: { data: RevisionData }) {
  const [accion, setAccion] = useState("");
  const [observaciones, setObservaciones] = useState("");
  const [busy, setBusy] = useState(false);
  const i = data.informe;
  if (!i) {
    return <div className="container mt-4"><div className="alert alert-warning"><i className="fas fa-exclamation-triangle" />{" "}No se encontró un informe complementario pendiente de revisión.</div></div>;
  }
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      await webClient.post(`${API}${data.id}/complementario/revision/`, new URLSearchParams({ accion_complementario: accion, observaciones_complementario: observaciones }), { validateStatus: () => true });
    } finally {
      // The native view redirects to the legal detail, which shows the flash message.
      window.location.assign(data.urls.legal);
    }
  };
  return (
    <div className="container mt-4">
      <div className="row">
        <div className="col-md-6"><div className="card">
          <div className="card-header"><h5>Cambios Realizados por el Técnico</h5><small className="text-muted">Fecha: {i.fecha}</small></div>
          <div className="card-body">
            {i.campos.length ? <div className="list-group">{i.campos.map((c, n) => <div key={n} className="list-group-item">
              <div className="d-flex w-100 justify-content-between"><h6 className="mb-1">{c.campo}</h6></div>
              <p className="mb-1"><strong>Nuevo valor:</strong> {c.value}</p>
            </div>)}</div> : <p className="text-muted">No se realizaron cambios específicos.</p>}
          </div>
        </div></div>
        <div className="col-md-6"><div className="card">
          <div className="card-header"><h5>Información del Informe</h5></div>
          <div className="card-body">
            <p><strong>Estado:</strong> {i.estado}</p>
            <p><strong>Creado por:</strong> {i.creado_por}</p>
            <p><strong>Fecha:</strong> {i.fecha}</p>
            <div className="alert alert-info"><small><i className="bi bi-info-circle" /> Al validar, se actualizará el informe técnico original y se generarán los PDF/DOCX finales.</small></div>
          </div>
        </div></div>
      </div>
      <div className="card mt-4">
        <div className="card-header"><h5>Decisión sobre el Informe Complementario</h5></div>
        <div className="card-body">
          <form method="post" onSubmit={(e) => void submit(e)}>
            <div className="form-group">
              <label>Seleccione una acción:</label>
              <div className="form-check">
                <input className="form-check-input" type="radio" name="accion_complementario" id="validar" value="validar" required checked={accion === "validar"}
                  onChange={() => { setAccion("validar"); setObservaciones(""); }} />{" "}
                <label className="form-check-label" htmlFor="validar"><i className="fas fa-check text-success" /> Validar - Continuar con el proceso</label>
              </div>
              <div className="form-check">
                <input className="form-check-input" type="radio" name="accion_complementario" id="rectificar" value="rectificar" required checked={accion === "rectificar"}
                  onChange={() => setAccion("rectificar")} />{" "}
                <label className="form-check-label" htmlFor="rectificar"><i className="fas fa-times text-danger" /> Rectificar - Solicitar nuevos cambios</label>
              </div>
            </div>
            <div className="form-group" id="observaciones-group" style={{ display: accion === "rectificar" ? "block" : "none" }}>
              <label htmlFor="observaciones_complementario">Observaciones para el técnico:</label>{" "}
              <textarea className="form-control" name="observaciones_complementario" id="observaciones_complementario" rows={4} required={accion === "rectificar"}
                placeholder="Escriba las observaciones que el técnico debe atender..." value={observaciones} onChange={(e) => setObservaciones(e.target.value)} />
            </div>
            <div className="form-group mt-3">
              <button type="submit" name="btnRevisarInformeComplementario" className="btn btn-primary" disabled={busy}><i className="fas fa-save" /> Guardar</button>{" "}
              <a href={data.urls.legal} className="btn btn-secondary">Cancelar</a>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function RevisionPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/complementario/revision/`, revisionValid);
  return renderMain(state, "Cargando informe…", (data) => ({
    title: `Revisar Informe Complementario: ${data.comedor}`,
    heading: `Revisar Informe Complementario: ${data.comedor}`,
    breadcrumb: null,
    content: <><NativeToasts messages={data.messages} /><RevisionContent data={data} /></>,
  }));
}

type Params = { page: "ver"; id: string } | { page: "revision"; id: string };
// Native GET pages of `admisiones/urls/web_urls.py`; neither URL ends with a slash.
const VER = /^\/comedores\/admisiones\/legales\/ver\/([0-9]+)$/;
const REVISION = /^\/comedores\/admisiones\/legales\/revisar-complementario\/([0-9]+)$/;

export const admisionesLegalesRoute: RouteDefinition<Params> = {
  name: "comedores-admisiones-legales",
  match(pathname) {
    const v = pathname.match(VER);
    if (v) return { page: "ver", id: v[1] };
    const r = pathname.match(REVISION);
    return r ? { page: "revision", id: r[1] } : null;
  },
  render(params) {
    return params.page === "ver" ? <LegalPage key={`ver/${params.id}`} id={params.id} /> : <RevisionPage key={`revision/${params.id}`} id={params.id} />;
  },
};
