/* eslint-disable react-refresh/only-export-components -- the module exports its validators and the legajo section next to the route. */
import { Fragment, useState, type FormEvent } from "react";
import { InsumosToastList } from "../InsumosToast";
import { CrispyField, FLASH_KEY, FlashToasts, freshPage, organizacionesNavigation, type Field, type Message } from "./organizacionesForm";
import { accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * O01 `convenio_proyecto_form.html` (alta/edición de los Datos de Convenio de
 * un proyecto) and the "Datos de Convenio" summary of the legajo
 * (`legajo/convenios.html`). The API runs the native `ConvenioProyectoView`;
 * amounts travel as text and React only adds up cents for the on-screen hint,
 * exactly as the native script does.
 */
type Resumen = { suma: string; total: string; diferencia: string; coincide: boolean };
export type ConvenioData = {
  project: { id: number; code: string };
  organization: { id: number; name: string; cuit: string; region: string; subzone: string };
  line: string; is_tradicional: boolean; exists: boolean;
  form: { fields: Field[]; components: string[]; non_field_errors: string[] };
  summary: Resumen | null; urls: { cancel: string }; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const FAILED: Message = { message: "No se pudo guardar el convenio. Recargá la página para ver el estado actual.", level: "error" };

export function convenioValid(v: unknown): v is ConvenioData {
  return record(v) && record(v.project) && record(v.organization) && text(v.line) && record(v.form) && Array.isArray(v.form.fields) &&
    v.form.fields.every((f) => record(f) && text(f.name) && text(f.label) && Array.isArray(f.errors)) && Array.isArray(v.form.components) &&
    record(v.urls) && internal(v.urls.cancel) && Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

const STYLE = `
.convenio-linea-secos { --convenio-color: #5CC8B5; }
.convenio-linea-tradicional { --convenio-color: #8FB8F5; }
.convenio-card { border: 2px solid var(--convenio-color); border-radius: 12px; overflow: hidden; }
.convenio-franja { background: var(--convenio-color); color: #1B2340; padding: 12px 20px; display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 16px; }
.convenio-franja-eyebrow { font-size: 13px; text-transform: uppercase; letter-spacing: .08em; font-weight: 600; }
.convenio-franja-linea { font-size: 20px; font-weight: 700; }
.convenio-codigo { display: inline-block; background: #0d6efd; color: #fff; padding: 4px 12px; border-radius: 999px; font-size: 13px; font-weight: 600; }
.convenio-dato { display: flex; justify-content: space-between; gap: 12px; padding: 7px 0; border-bottom: 1px solid rgba(255, 255, 255, .08); }
.convenio-dato strong { opacity: .75; font-weight: 500; }
.convenio-subtitulo { color: #E7BA61; font-size: 15px; font-weight: 600; margin: 8px 0 12px; }
.convenio-resumen td, .convenio-resumen th { font-variant-numeric: tabular-nums; }
.convenio-aviso { background: #4A3A12; border: 1px solid #F2C14E; color: #FFE7A8; border-radius: 8px; padding: 12px 14px; display: flex; gap: 10px; align-items: flex-start; }
.convenio-ok { color: #7ee2a0; font-size: 14px; }
.convenio-nota { font-size: 13px; opacity: .75; }`;

/** The native script's `formato`: whole pesos with dots, cents only when present. */
export function formatCents(cents: number): string {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  const whole = Math.floor(abs / 100).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const rest = abs % 100;
  return `${sign}$${whole}${rest ? "," + String(rest).padStart(2, "0") : ""}`;
}

const toCents = (raw: unknown): number => {
  if (raw === "" || raw === null || raw === undefined) return 0;
  const n = Number(raw);
  return Number.isNaN(n) ? 0 : Math.round(n * 100);
};

function MontoField({ f, value, set }: { f: Field; value: unknown; set: (v: string) => void }) {
  const attrs = f.attrs;
  return (
    <div className="mb-3">
      <label className={`form-label${f.required ? " requiredField" : ""}`} htmlFor={`id_${f.name}`}>
        {f.label}{f.required && <>{" "}<span className="asteriskField">*</span></>}
      </label>
      <div className="input-group">
        <span className="input-group-text">$</span>
        <input type="number" name={f.name} id={`id_${f.name}`} className="form-control" required={f.required} value={String(value ?? "")}
          step={attrs.step} min={attrs.min} inputMode={attrs.inputmode as "decimal" | undefined} onChange={(e) => set(e.target.value)} />
      </div>
      {f.errors.map((e) => <div key={e} className="text-danger small mt-1">{e}</div>)}
    </div>
  );
}

function ConvenioContent({ initial, messages }: { initial: ConvenioData; messages: Message[] }) {
  const [form, setForm] = useState(initial.form);
  const [values, setValues] = useState<Record<string, unknown>>(() => Object.fromEntries(initial.form.fields.map((f) => [f.name, f.value])));
  const [touched, setTouched] = useState(false);
  const [toasts, setToasts] = useState<Message[]>(messages);
  const [pending, setPending] = useState(false);
  const fields = Object.fromEntries(form.fields.map((f) => [f.name, f]));
  const set = (name: string, v: unknown) => { setTouched(true); setValues((cur) => ({ ...cur, [name]: v })); };
  const { project, organization } = initial;

  const total = toCents(values.monto_total);
  const sum = form.components.reduce((acc, name) => acc + toCents(values[name]), 0);
  const complete = values.monto_total !== "" && values.monto_total != null;
  const live = touched
    ? { suma: formatCents(sum), total: formatCents(total), diferencia: formatCents(total - sum), showAviso: complete && sum !== total, showOk: complete && sum === total }
    : { suma: initial.summary?.suma || "$0", total: initial.summary?.total || "$0", diferencia: initial.summary?.diferencia || "$0",
        showAviso: !!initial.summary && !initial.summary.coincide, showOk: !!initial.summary && initial.summary.coincide };

  async function submit(event: FormEvent) {
    event.preventDefault();
    const body = new URLSearchParams();
    for (const f of form.fields) body.set(f.name, values[f.name] == null ? "" : String(values[f.name]));
    setPending(true);
    try {
      const { data, status } = await webClient.post(`web/comedores/organizaciones/proyectos/${project.id}/convenio/`, body,
        { validateStatus: (s: number) => accepted(s) || s === 400 || s === 409 });
      if ((status === 200 || status === 409) && record(data) && internal(data.redirect)) {
        if (Array.isArray(data.messages) && data.messages.length) { try { window.sessionStorage.setItem(FLASH_KEY, JSON.stringify(data.messages)); } catch { /* the message is optional */ } }
        organizacionesNavigation.assign(data.redirect);
        return;
      }
      if (status === 400 && convenioValid({ ...(data as object), messages: [] })) {
        const bound = (data as ConvenioData).form;
        setForm(bound);
        setValues(Object.fromEntries(bound.fields.map((f) => [f.name, f.value])));
        freshPage();
        return;
      }
      setToasts([FAILED]);
    } catch {
      setToasts([FAILED]);
    } finally { setPending(false); }
  }

  const amount = (name: string) => fields[name] && <div className="col-md-6"><MontoField f={fields[name]} value={values[name]} set={(v) => set(name, v)} /></div>;
  const crispy = (name: string) => fields[name] && <div className="col-md-6"><CrispyField f={fields[name]} values={values} set={set} /></div>;
  return (
    <>
      <style>{STYLE}</style>
      <InsumosToastList messages={toasts} />
      <div className={`card convenio-card ${initial.is_tradicional ? "convenio-linea-tradicional" : "convenio-linea-secos"}`}>
        <div className="convenio-franja">
          <span className="convenio-franja-eyebrow">Abordaje Comunitario</span>
          <span className="convenio-franja-linea">{initial.line}</span>
        </div>
        <div className="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
          <h5 className="mb-0">{initial.exists ? "Editar datos del Convenio" : "Cargar datos del Convenio"}</h5>
          <span className="convenio-codigo">{project.code}</span>
        </div>
        <div className="card-body">
          <div className="row mb-4">
            <div className="col-md-6">
              <div className="convenio-dato"><strong>Organización:</strong><span>{organization.name}</span></div>
              <div className="convenio-dato"><strong>CUIT:</strong><span>{organization.cuit}</span></div>
              <div className="convenio-dato"><strong>Código del proyecto:</strong><span>{project.code}</span></div>
            </div>
            <div className="col-md-6">
              <div className="convenio-dato"><strong>Línea:</strong><span>{initial.line}</span></div>
              <div className="convenio-dato"><strong>Región:</strong><span>{organization.region}</span></div>
              <div className="convenio-dato"><strong>Subzona:</strong><span>{organization.subzone}</span></div>
            </div>
          </div>
          <form method="post" id="convenioProyectoForm" noValidate onSubmit={submit}>
            {form.non_field_errors.length > 0 && <ul className="errorlist nonfield">{form.non_field_errors.map((e) => <li key={e}>{e}</li>)}</ul>}
            <h6 className="convenio-subtitulo">Datos generales</h6>
            <div className="row">{crispy("numero")}{crispy("fecha")}{crispy("meses")}{amount("monto_total")}</div>
            <h6 className="convenio-subtitulo">Componentes del convenio</h6>
            <div className="row">{form.components.map((name) => <Fragment key={name}>{amount(name)}</Fragment>)}</div>
            {!initial.is_tradicional && <p className="convenio-nota mb-3">Imprevistos no aplica: es solo para Línea Tradicional.</p>}
            <div className="table-responsive">
              <table className="table table-sm convenio-resumen mb-2">
                <tbody>
                  <tr><th>Suma de componentes</th><td className="text-end" id="convenio-suma">{live.suma}</td></tr>
                  <tr><th>Monto total del convenio</th><td className="text-end" id="convenio-total">{live.total}</td></tr>
                  <tr><th>Diferencia</th><td className="text-end" id="convenio-diferencia">{live.diferencia}</td></tr>
                </tbody>
              </table>
            </div>
            <div id="convenio-suma-aviso" className={`convenio-aviso${live.showAviso ? "" : " d-none"}`} role="status">
              <i className="fas fa-exclamation-triangle mt-1" aria-hidden="true" />
              <span><strong>La suma de componentes no coincide con el monto total del convenio.</strong> Revisá los montos cargados. Se puede guardar igual.</span>
            </div>
            <p id="convenio-suma-ok" className={`convenio-ok mb-0${live.showOk ? "" : " d-none"}`}>
              <i className="fas fa-check mr-1" aria-hidden="true" /> La suma de componentes coincide con el monto total del convenio.
            </p>
            <div className="mt-4">
              <button type="submit" className="btn btn-primary" disabled={pending}>Guardar</button>
              {" "}
              <a href={initial.urls.cancel} className="btn btn-secondary ml-2">Cancelar</a>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}

export default function OrganizacionConvenio({ id }: { id: number }) {
  const [state] = useMainResource(`web/comedores/organizaciones/proyectos/${id}/convenio/`, convenioValid);
  return renderMain(state, "Cargando convenio…", (data) => ({
    title: "Datos del Convenio",
    heading: "Datos del Convenio",
    breadcrumb: <></>,
    content: (
      <>
        <FlashToasts messages={data.messages} />
        <ConvenioContent initial={data} messages={[]} />
      </>
    ),
  }));
}

// --- legajo section (`legajo/convenios.html`) -------------------------------------------

type Fila = {
  project: { id: number; code: string };
  convenio: { number: string; date: string; months: number; total: string; components: { label: string; amount: string }[]; imprevistos: string } | null;
  summary: Resumen | null; url: string;
};
export type ConveniosSection = { kind: "convenios"; program: string; color: string; is_tradicional: boolean; can_manage: boolean; rows: Fila[] };

export const conveniosSectionValid = (v: unknown): v is ConveniosSection =>
  record(v) && v.kind === "convenios" && text(v.program) && text(v.color) && Array.isArray(v.rows) &&
  v.rows.every((r) => record(r) && record(r.project) && internal(r.url) && (r.convenio === null || record(r.convenio)));

export function ConveniosSection({ section }: { section: ConveniosSection }) {
  return (
    <div className={`tabla-legajo card-programa card-${section.color}`}>
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-1">
        <h5 className="mb-0">Datos de Convenio · {section.program}</h5>
        <span className="chip-legajo">Solo proyectos de esta línea</span>
      </div>
      <p className="nota-legajo mb-3">Un convenio por cada proyecto de la línea.</p>
      {section.rows.map(({ project, convenio, summary, url }) => (
        <details className="convenio-paquete" key={project.id}>
          <summary>
            <span className="badge rounded-pill bg-primary px-3 py-2">{project.code}</span>
            {convenio ? (
              <>
                <span className="ms-2">Convenio {convenio.number}</span>
                {summary?.coincide ? <span className="badge-status vigente ms-auto">Cargado</span> : <span className="badge-status por-vencer ms-auto">Revisar montos</span>}
              </>
            ) : <span className="badge badge-pendiente ms-auto">Sin cargar</span>}
          </summary>
          <div className="convenio-cuerpo">
            {convenio && summary ? (
              <>
                <div className="convenio-generales">
                  <div><span className="etiqueta">N° de convenio</span><strong>{convenio.number}</strong></div>
                  <div><span className="etiqueta">Fecha</span><strong>{convenio.date}</strong></div>
                  <div><span className="etiqueta">Meses</span><strong>{convenio.months}</strong></div>
                  <div><span className="etiqueta">Monto total</span><strong>{convenio.total}</strong></div>
                </div>
                <h6 className="titulo-dorado mt-3 mb-1">Componentes del convenio</h6>
                <table className="table table-sm mb-0">
                  <thead><tr><th>Componente</th><th className="text-end">Monto</th></tr></thead>
                  <tbody>
                    {convenio.components.map((c) => <tr key={c.label}><td>{c.label}</td><td className="text-end">{c.amount}</td></tr>)}
                    {section.is_tradicional && <tr><td>Imprevistos</td><td className="text-end">{convenio.imprevistos}</td></tr>}
                  </tbody>
                  <tfoot><tr><th>Suma de componentes</th><th className="text-end">{summary.suma}</th></tr></tfoot>
                </table>
                {summary.coincide ? <p className="texto-ok mt-2 mb-0">✔ La suma de componentes coincide con el monto total del convenio.</p> : (
                  <div className="aviso-legajo mt-2" role="status">
                    <strong>La suma de componentes no coincide con el monto total del convenio.</strong>
                    {" "}Suma: {summary.suma} · Monto total: {summary.total} · Diferencia: {summary.diferencia}.
                  </div>
                )}
                {!section.is_tradicional && <p className="nota-legajo mt-2 mb-0">Imprevistos no aplica: es solo para Línea Tradicional.</p>}
              </>
            ) : <p className="texto-vacio mb-0">El proyecto todavía no tiene convenio cargado.</p>}
            {section.can_manage && <a href={url} className="btn btn-success btn-sm mt-3">{convenio ? "Editar convenio" : "Cargar convenio"}</a>}
          </div>
        </details>
      ))}
      {section.rows.length === 0 && <p className="texto-vacio mb-0">No hay proyectos en esta línea.</p>}
    </div>
  );
}

// Native URL (trailing slash, as `urls.py` declares it).
export const organizacionConvenioRoute: RouteDefinition<{ id: number }> = {
  name: "comedores-organizaciones-convenio",
  match(pathname) {
    const found = /^\/organizaciones\/proyectos\/([1-9]\d{0,14})\/convenio\/$/.exec(pathname);
    return found ? { id: Number(found[1]) } : null;
  },
  render: ({ id }) => <OrganizacionConvenio id={id} />,
};
