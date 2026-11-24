/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import type { ReactNode } from "react";
import { accepted, internal, postForm, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { PARAMETRIA_FORM_CSS } from "./vatParametriaFormStyles";
import { Control, CsrfInput, fieldValid, Select2Links, UNCERTAIN, useForbidden, useWriteForm, type Field } from "./vatFormShared";
import { messagesValid, type Message } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V01.02 forms: `voucher_form.html` (asignar), `voucher_asignacion_masiva.html` and `parametria_form.html`.
 * Fields, widget attributes, errors and the masivo result come from `/api/web/vat/vouchers/`, which runs the
 * native views; the POST persists through their `form_valid` / `post`.
 */
export type Resultado = { creados: string[]; ya_tenia: string[]; no_encontrados: string[]; errores: string[] };
export type VoucherFormData = { fields: Field[]; urls: { list: string }; messages: Message[]; titulo?: string; resultado?: Resultado | null };

const API = "web/vat/vouchers/";
const strings = (v: unknown) => Array.isArray(v) && v.every((x) => typeof x === "string");
const resultadoValid = (r: unknown) => r === undefined || r === null || (record(r) && ["creados", "ya_tenia", "no_encontrados", "errores"].every((k) => strings(r[k])));

const formValid = (count: number) => (v: unknown): v is VoucherFormData => record(v) && Array.isArray(v.fields) && v.fields.length === count && v.fields.every(fieldValid) &&
  record(v.urls) && internal(v.urls.list) && messagesValid(v.messages) && (v.titulo === undefined || text(v.titulo)) && resultadoValid(v.resultado);
export const asignarValid = formValid(4);
export const masivoValid = formValid(4);
export const parametriaValid = formValid(9);

/** The native masivo page re-renders (status 200) with the bound form and the result: both outcomes replace the form. */
const sendMasivo: typeof postForm = async (endpoint, body) => {
  try {
    const { data, status } = await webClient.post(endpoint, body, { validateStatus: accepted });
    if (status === 403) return { kind: "forbidden" as const, data };
    return { kind: "invalid" as const, data };
  } catch (error: unknown) {
    const response = (error as { response?: { status?: number; data?: unknown } }).response;
    if (response?.status === 400) return { kind: "invalid" as const, data: response.data };
    return { kind: "uncertain" as const };
  }
};

const Errors = ({ f }: { f: Field }) => (f.errors.length ? <div className="text-danger small mt-1">{f.errors.join(", ")}</div> : null);

/** `{% for field in form %}` of the two generic form templates. */
function GenericFields({ fields, state, set, help }: { fields: Field[]; state: Record<string, string | boolean>; set: (n: string, v: string | boolean) => void; help: boolean }) {
  return <>{fields.map((f) => <div key={f.name} className="mb-3">
    <label className="form-label fw-semibold">{f.label}</label>{" "}
    <Control f={f} state={state} set={set} />
    {f.errors.length > 0 && <>{" "}<Errors f={f} /></>}
    {help && f.help_text && <>{" "}<div className="text-muted small mt-1">{f.help_text}</div></>}
  </div>)}</>;
}

function GenericPage({ initial, endpoint, forbidden, valid, masivo }: {
  initial: VoucherFormData; endpoint: string; forbidden: (d: unknown) => void; valid: (v: unknown) => v is VoucherFormData; masivo: boolean;
}) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid, send: masivo ? sendMasivo : postForm });
  const r = data.resultado;
  const stat = (tone: string, n: number, label: string) => <div className="col-6">
    <div className={`p-2 rounded bg-${tone} bg-opacity-10 border border-${tone}-subtle text-center`}>
      <div className={`fw-bold text-${tone} fs-4`}>{n}</div>
      <div className="small text-muted">{label}</div>
    </div>
  </div>;
  const list = (items: string[], tone: string, label: string) => items.length > 0 && <details className="mb-2">
    <summary className={`text-${tone} fw-semibold small`}>{label} ({items.length})</summary>
    <div className="mt-1 small text-muted">{items.join(", ")}</div>
  </details>;
  const card = <div className="card">
    <div className="card-header"><h3 className="card-title"><i className={`bi ${masivo ? "bi-people" : "bi-ticket-perforated"} me-2`} />{masivo ? "Asignación masiva de vouchers" : data.titulo}</h3></div>
    <div className="card-body">
      {masivo && <p className="text-muted small mb-3">Ingresá los DNIs separados por coma, espacio o salto de línea (máx. 500). Se creará un voucher por cada ciudadano encontrado que no tenga ya uno activo en el programa seleccionado.</p>}
      <form method="post" onSubmit={(e) => void submit(e)}>
        <CsrfInput />
        {uncertain && <p role="alert">{UNCERTAIN}</p>}
        <GenericFields fields={data.fields} state={state} set={set} help={!masivo} />
        <div className={`d-flex gap-2${masivo ? "" : " mt-3"}`}>
          <button type="submit" className="btn btn-primary">{masivo ? <><i className="bi bi-check-all me-1" />Procesar</> : <><i className="bi bi-check-lg me-1" />Asignar</>}</button>{" "}
          <a href={data.urls.list} className="btn btn-outline-secondary">Cancelar</a>
        </div>
      </form>
    </div>
  </div>;
  return <>
    <NativeToasts messages={data.messages} />
    <Select2Links />
    <link rel="stylesheet" href="/static/custom/css/cardsDetail.css" />
    {masivo ? <div className="row">
      <div className="col-md-6">{card}</div>
      {r && <div className="col-md-6"><div className="card">
        <div className="card-header"><h3 className="card-title"><i className="bi bi-clipboard-check me-2" />Resultado</h3></div>
        <div className="card-body">
          <div className="row g-2 mb-3">
            {stat("success", r.creados.length, "Asignados")}{stat("warning", r.ya_tenia.length, "Ya tenían")}
            {stat("secondary", r.no_encontrados.length, "No encontrados")}{stat("danger", r.errores.length, "Errores")}
          </div>
          {list(r.creados, "success", "Asignados")}
          {list(r.ya_tenia, "warning", "Ya tenían voucher activo")}
          {list(r.no_encontrados, "secondary", "DNIs no encontrados")}
          {list(r.errores, "danger", "Errores al procesar")}
          <a href="/vat/vouchers/" className="btn btn-sm btn-outline-primary mt-2"><i className="bi bi-list me-1" />Ver todos los vouchers</a>
        </div>
      </div></div>}
    </div> : <div className="row justify-content-center"><div className="col-md-7">{card}</div></div>}
  </>;
}

function section(icon: string, title: string, intro: string, body: ReactNode) {
  return <div className="vp-section">
    <div className="vp-section-title"><span className="vp-badge"><i className={icon} /></span>{" "}{title}</div>
    <div className="vp-section-text">{intro}</div>
    {body}
  </div>;
}

function ParametriaPage({ initial, endpoint, forbidden }: { initial: VoucherFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: parametriaValid });
  const f = Object.fromEntries(data.fields.map((x) => [x.name, x])) as Record<string, Field>;
  const req = <>{" "}<span className="text-danger">*</span></>;
  const lbl = (x: Field, star: boolean) => <label htmlFor={x.id}>{x.label}{star && req}</label>;
  const err = (x: Field) => x.errors.length > 0 && <div className="text-danger small mt-1">{x.errors.join(", ")}</div>;
  const toggle = (x: Field, last: boolean) => <div className={`vp-toggle-card${last ? "" : " mb-3"}`}>
    <div className="form-check mb-0">
      <Control f={x} state={state} set={set} />{" "}
      <label className="form-check-label fw-semibold" htmlFor={x.id}>{x.label}</label>
    </div>
    {x.help_text && <div className="vp-help">{x.help_text}</div>}
    {err(x)}
  </div>;
  return <>
    <NativeToasts messages={data.messages} />
    <Select2Links />
    <link rel="stylesheet" href="/static/custom/css/cardsDetail.css" />
    <style>{PARAMETRIA_FORM_CSS}</style>
    <div className="vp-shell">
      <div className="vp-hero">
        <h1><i className="bi bi-sliders me-2" />{data.titulo}</h1>
        <p>Configurá cómo se asignan, vencen y renuevan los créditos de voucher para un programa. El objetivo es que la parametría quede legible y fácil de mantener.</p>
      </div>
      <div className="row g-4 align-items-start">
        <div className="col-lg-8"><div className="card vp-panel">
          <div className="vp-panel-header">
            <h3 className="card-title mb-1">Configuración general</h3>
            <div className="text-muted small vp-panel-subtitle">Definí la identidad de la parametría y las reglas operativas del voucher.</div>
          </div>
          <form method="post" onSubmit={(e) => void submit(e)}>
            <CsrfInput />
            {uncertain && <p role="alert">{UNCERTAIN}</p>}
            {section("bi bi-card-text", "Identificación", "Primero asociá la parametría al programa correcto y asignale un nombre claro para reconocerla después.",
              <div className="row g-3">
                <div className="col-md-6 vp-field">{lbl(f.programa, true)}<Control f={f.programa} state={state} set={set} />{err(f.programa)}</div>
                <div className="col-md-6 vp-field">{lbl(f.nombre, true)}<Control f={f.nombre} state={state} set={set} />{err(f.nombre)}</div>
                <div className="col-12 vp-field">{lbl(f.descripcion, false)}<Control f={f.descripcion} state={state} set={set} />{err(f.descripcion)}
                  <div className="vp-help">Usá este campo para aclarar alcance, público objetivo o criterios especiales.</div></div>
              </div>)}
            {section("bi bi-ticket-perforated", "Créditos y vigencia", "Definí cuántos créditos recibe cada ciudadano y hasta cuándo serán válidos.",
              <div className="row g-3">
                <div className="col-md-6 vp-field">{lbl(f.cantidad_inicial, true)}<Control f={f.cantidad_inicial} state={state} set={set} />{err(f.cantidad_inicial)}</div>
                <div className="col-md-6 vp-field">{lbl(f.fecha_vencimiento, true)}<Control f={f.fecha_vencimiento} state={state} set={set} />{err(f.fecha_vencimiento)}</div>
              </div>)}
            {section("bi bi-arrow-repeat", "Renovación automática", "Configurá si el sistema debe renovar créditos todos los meses y de qué forma hacerlo.",
              <>
                {toggle(f.renovacion_mensual, false)}
                <div className="row g-3">
                  <div className="col-md-6 vp-field">{lbl(f.cantidad_renovacion, false)}<Control f={f.cantidad_renovacion} state={state} set={set} />{err(f.cantidad_renovacion)}
                    {f.cantidad_renovacion.help_text && <div className="vp-help">{f.cantidad_renovacion.help_text}</div>}</div>
                  <div className="col-md-6 vp-field"><label className="d-block">{f.renovacion_tipo.label}</label>
                    <div className="vp-radio-group mt-2"><Control f={f.renovacion_tipo} state={state} set={set} /></div>
                    {err(f.renovacion_tipo)}</div>
                </div>
              </>)}
            {section("bi bi-shield-check", "Reglas de uso", "Determiná restricciones funcionales para las inscripciones que dependen de esta parametría.", toggle(f.inscripcion_unica_activa, true))}
            <div className="vp-actions">
              <a href={data.urls.list} className="btn btn-outline-secondary">Cancelar</a>{" "}
              <button type="submit" className="btn btn-primary px-4"><i className="bi bi-check-lg me-1" />Guardar parametría</button>
            </div>
          </form>
        </div></div>
        <div className="col-lg-4">
          <div className="card vp-sidecard mb-3"><div className="card-body">
            <h5><i className="bi bi-lightbulb me-2" />Sugerencia de orden</h5>
            <ol className="vp-checklist">
              <li>Elegí el programa y un nombre entendible.</li>
              <li>Definí créditos iniciales y fecha de vencimiento.</li>
              <li>Recién después configurá renovación mensual.</li>
              <li>Activá inscripción única solo si el programa lo requiere.</li>
            </ol>
          </div></div>
          <div className="card vp-sidecard"><div className="card-body">
            <h5><i className="bi bi-exclamation-circle me-2" />Impacto funcional</h5>
            <ul className="vp-checklist">
              <li>La fecha de vencimiento debe ser posterior a hoy.</li>
              <li>Si no completás créditos de renovación, se reutiliza la cantidad inicial.</li>
              <li>El tipo de renovación define si se acumula saldo o se reinicia.</li>
            </ul>
          </div></div>
        </div>
      </div>
    </div>
  </>;
}

type Params = { mode: "asignar" | "masivo" | "parametria" };

const TITLES = { asignar: "Asignar Voucher", masivo: "Asignación Masiva de Vouchers", parametria: "" };

function FormPage({ mode }: Params) {
  const endpoint = { asignar: `${API}asignar/`, masivo: `${API}asignar-masivo/`, parametria: `${API}parametrias/nueva/` }[mode];
  const valid = { asignar: asignarValid, masivo: masivoValid, parametria: parametriaValid }[mode];
  const [state, setState] = useMainResource(`${endpoint}${mode === "asignar" ? window.location.search : ""}`, valid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: mode === "parametria" ? data.titulo! : TITLES[mode], heading: mode === "masivo" ? "Asignación Masiva" : data.titulo ?? "", breadcrumb: null,
    content: mode === "parametria" ? <ParametriaPage initial={data} endpoint={endpoint} forbidden={forbidden} />
      : <GenericPage initial={data} endpoint={endpoint} forbidden={forbidden} valid={valid} masivo={mode === "masivo"} />,
  }));
}

// Native URLs of `VAT/urls.py` (`parametrias/nueva/` is matched before `parametrias/<id>/`, which is not mine).
const PATH = /^\/vat\/vouchers\/(asignar|asignar-masivo|parametrias\/nueva)\/$/;

export const vatVouchersFormRoute: RouteDefinition<Params> = {
  name: "vat-vouchers-form",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    return { mode: m[1] === "asignar" ? "asignar" : m[1] === "asignar-masivo" ? "masivo" : "parametria" };
  },
  render: ({ mode }) => <FormPage key={mode} mode={mode} />,
};
