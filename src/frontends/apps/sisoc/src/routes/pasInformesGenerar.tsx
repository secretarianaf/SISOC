/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { Fragment, useEffect, useRef, useState, type FormEvent, type MouseEvent, type ReactNode } from "react";
import { prerequisiteFromForbidden } from "../webAccess";
import { Breadcrumb, breadcrumbValid, record, renderMain, text, useMainResource, webClient, type Breadcrumbs } from "./MainFrame";
import { PAS_API, integer, list, shape } from "./pasFrame";
import type { RouteDefinition } from "./types";

/**
 * PAS04.02: request of a new report on the native URL `pas/informes/generar`
 * (`pas/informe_form.html` + `pas_informe.js`). The choices come from
 * `/api/web/pas/informes/opciones/`, the preview from `previsualizar/` and
 * «Realizar informe» posts to `generar/`, which creates the report and answers
 * its CSV in the same response (the screen saves it as the browser would).
 * The screen never retries: each POST creates a record.
 */
type Choice = { id: number; nombre: string };
type Aviso = { id: number; texto: string };
export type InformeOptions = { breadcrumb: Breadcrumbs; estados: Choice[]; avisos: Aviso[]; provincias: Choice[]; municipios: Choice[] };
type Preview = { modo: string; total: number; limit: number; columns: { key: string; label: string }[]; rows: Record<string, unknown>[] };
type Errors = Record<string, string[]>;

const choice = (v: unknown): v is Choice => shape(v, { id: integer, nombre: text });
export const optionsValid = (v: unknown): v is InformeOptions => shape(v, {
  breadcrumb: breadcrumbValid, estados: list(choice), provincias: list(choice), municipios: list(choice),
  avisos: list((a: unknown): a is Aviso => shape(a, { id: integer, texto: text })),
});
const previewValid = (v: unknown): v is Preview => shape(v, {
  modo: text, total: integer, limit: integer,
  columns: list((c: unknown): c is object => shape(c, { key: text, label: text })),
  rows: list((r: unknown): r is Record<string, unknown> => record(r)),
});
const errorsValid = (v: unknown): v is Errors => record(v) && Object.values(v).every((e) => Array.isArray(e) && e.every(text));

const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";
const PREVIEW_FAILED = "No se pudo previsualizar el informe.";
const FIELDS = [
  "fecha_creacion_desde", "fecha_creacion_hasta", "fecha_cambio_desde", "fecha_cambio_hasta", "estado_anterior", "estado_nuevo",
  "estado_actual", "aviso_cambio", "aviso_actual", "provincia", "municipio", "dni", "id_persona", "usuario_cambio",
] as const;
type Name = (typeof FIELDS)[number];
type Values = Record<Name, string>;
const EMPTY = Object.fromEntries(FIELDS.map((f) => [f, ""])) as Values;

const body = (values: Values) => new URLSearchParams(FIELDS.map((f) => [f, values[f]]));
const isBuffer = (data: unknown): data is ArrayBuffer => Object.prototype.toString.call(data) === "[object ArrayBuffer]";
const decode = (data: unknown): unknown => {
  try {
    return isBuffer(data) ? JSON.parse(new TextDecoder().decode(data)) : data;
  } catch {
    return null;
  }
};
const errorsOf = (data: unknown) => (record(data) && data.ok === false && errorsValid(data.errors) ? data.errors : null);

/** `renderErrors`: `field: message` lines, in the order the server sent them. */
const lines = (errors: Errors) => Object.entries(errors).flatMap(([field, messages]) => messages.map((m) => `${field}: ${m}`));

type Outcome = { kind: "done" } | { kind: "invalid"; errors: Errors } | { kind: "forbidden"; data: unknown } | { kind: "uncertain" };

async function generate(values: Values): Promise<Outcome> {
  try {
    const response = await webClient.post(`${PAS_API}informes/generar/`, body(values), { responseType: "arraybuffer", validateStatus: () => true });
    if (response.status === 403) return { kind: "forbidden", data: decode(response.data) };
    if (response.status === 400) {
      const errors = errorsOf(decode(response.data));
      return errors ? { kind: "invalid", errors } : { kind: "uncertain" };
    }
    if (response.status !== 200 || !isBuffer(response.data)) return { kind: "uncertain" };
    const headers = response.headers as Record<string, string | undefined>;
    const name = /filename="([^"]+)"/.exec(headers["content-disposition"] ?? "")?.[1] ?? `pas-inf-${headers["x-pas-informe-id"] ?? "nuevo"}.csv`;
    const url = URL.createObjectURL(new Blob([response.data], { type: headers["content-type"] ?? "" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    return { kind: "done" };
  } catch {
    return { kind: "uncertain" };
  }
}

type PreviewOutcome = { kind: "ready"; preview: Preview } | { kind: "errors"; errors: Errors };

async function previewOf(values: Values): Promise<PreviewOutcome> {
  try {
    const response = await webClient.post(`${PAS_API}informes/previsualizar/`, body(values), { validateStatus: () => true });
    if (response.status === 200 && record(response.data) && response.data.ok === true && previewValid(response.data)) return { kind: "ready", preview: response.data };
    const errors = response.status === 400 ? errorsOf(response.data) : null;
    if (errors) return { kind: "errors", errors };
  } catch {
    // The native script reports every failure the same way.
  }
  return { kind: "errors", errors: { preview: [PREVIEW_FAILED] } };
}

function Section({ icon, title, subtitle, children }: { icon: string; title: string; subtitle: string; children: ReactNode }) {
  return <div className="section-card">
    <div className="section-header"><div className="section-header-left">
      <div className="section-icon"><i className={`fas ${icon}`} /></div>
      <div className="section-title-group"><h3 className="section-title">{title}</h3><p className="section-subtitle">{subtitle}</p></div>
    </div></div>
    <div className="section-body collapse show">{children}</div>
  </div>;
}

type FieldProps = { name: Name; label: string; values: Values; errors: Errors; set: (name: Name, value: string) => void };

function Errs({ id, messages }: { id: string; messages: string[] | undefined }) {
  if (!messages?.length) return null;
  return <div id={`${id}_error`} className="invalid-feedback d-block">
    {messages.map((m, i) => <p key={i} id={`error_${i + 1}_${id}`} className="mb-0"><strong>{m}</strong></p>)}
  </div>;
}

function Input({ name, label, type, klass, values, errors, set, placeholder }: FieldProps & { type: string; klass: string; placeholder?: string }) {
  const id = `id_${name}`, invalid = !!errors[name]?.length;
  return <div id={`div_${id}`} className="mb-3">
    <label htmlFor={id} className="form-label">{label}</label>{" "}
    <input type={type} name={name} id={id} className={`${klass} form-control${invalid ? " is-invalid" : ""}`} placeholder={placeholder}
      value={values[name]} aria-invalid={invalid ? "true" : undefined} aria-describedby={invalid ? `${id}_error` : undefined}
      onChange={(e) => set(name, e.target.value)} />
    <Errs id={id} messages={errors[name]} />
  </div>;
}

function Select({ name, label, empty, items, values, errors, set }: FieldProps & { empty: string; items: { value: string; label: string }[] }) {
  const id = `id_${name}`, invalid = !!errors[name]?.length;
  return <div id={`div_${id}`} className="mb-3">
    <label htmlFor={id} className="form-label">{label}</label>{" "}
    <select name={name} id={id} className={`form-select pas-select2 select form-select${invalid ? " is-invalid" : ""}`} value={values[name]}
      aria-invalid={invalid ? "true" : undefined} aria-describedby={invalid ? `${id}_error` : undefined} onChange={(e) => set(name, e.target.value)}>
      <option value="">{empty}</option>
      {items.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
    </select>
    <Errs id={id} messages={errors[name]} />
  </div>;
}

function PreviewCard({ preview, messages }: { preview: Preview | null; messages: string[] }) {
  return <div className="section-card pas-preview-card mt-4" id="pasInformePreview">
    <div className="section-header"><div className="section-header-left">
      <div className="section-icon"><i className="fas fa-table" /></div>
      <div className="section-title-group">
        <h3 className="section-title">Previsualizacion del CSV</h3>
        <p className="section-subtitle" id="pasInformePreviewMeta">{preview ? `${preview.total} filas encontradas. Se muestran hasta ${preview.limit}. Modo: ${preview.modo}.` : ""}</p>
      </div>
    </div></div>
    <div className="section-body collapse show">
      {messages.length > 0 && <div className="alert alert-danger" id="pasInformePreviewErrors" role="alert">
        {messages.map((m, i) => <Fragment key={i}>{i > 0 && <br />}{m}</Fragment>)}
      </div>}
      <div className="table-responsive">
        <table className="table table-sm table-bordered table-striped mb-0 pas-preview-table">
          <thead id="pasInformePreviewHead">{preview && <tr>{preview.columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr>}</thead>
          <tbody id="pasInformePreviewBody">
            {preview && (preview.rows.length
              ? preview.rows.map((row, i) => <tr key={i}>{preview.columns.map((c) => <td key={c.key}>{String(row[c.key] ?? "")}</td>)}</tr>)
              : <tr><td colSpan={preview.columns.length} className="text-center text-muted py-3">Sin resultados para los filtros aplicados.</td></tr>)}
          </tbody>
        </table>
      </div>
    </div>
  </div>;
}

function historyBack(event: MouseEvent) {
  event.preventDefault();
  window.history.back();
}

function RequestForm({ options, onForbidden }: { options: InformeOptions; onForbidden: (data: unknown) => void }) {
  const [values, setValues] = useState<Values>(EMPTY);
  const [errors, setErrors] = useState<Errors>({});
  const [municipios, setMunicipios] = useState<{ reset: boolean; items: Choice[] }>({ reset: false, items: options.municipios });
  const [preview, setPreview] = useState<{ shown: boolean; data: Preview | null; messages: string[] }>({ shown: false, data: null, messages: [] });
  const [previewing, setPreviewing] = useState(false);
  const [sending, setSending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  const latest = useRef(0);
  useEffect(() => () => { latest.current = -1; }, []);

  function set(name: Name, value: string) {
    setValues((v) => ({ ...v, [name]: value }));
    if (name !== "provincia") return;
    // `pas_informe.js`: the municipio list is reset and reloaded for the chosen province.
    const ticket = ++latest.current;
    setValues((v) => ({ ...v, municipio: "" }));
    setMunicipios({ reset: true, items: [] });
    if (!value) return;
    webClient.get(`${PAS_API}informes/opciones/`, { params: { provincia: value } }).then((response) => {
      if (latest.current === ticket && optionsValid(response.data)) setMunicipios({ reset: true, items: response.data.municipios });
    }).catch(() => undefined);
  }
  async function showPreview() {
    if (busy.current) return;
    busy.current = true;
    setPreviewing(true);
    const outcome = await previewOf(values);
    busy.current = false;
    setPreviewing(false);
    if (outcome.kind === "ready") setPreview({ shown: true, data: outcome.preview, messages: [] });
    else setPreview((p) => ({ shown: true, data: p.data, messages: lines(outcome.errors) }));
  }
  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true;
    setSending(true);
    setUncertain(false);
    const outcome = await generate(values);
    busy.current = false;
    setSending(false);
    if (outcome.kind === "invalid") setErrors(outcome.errors);
    else if (outcome.kind === "forbidden") onForbidden(outcome.data);
    else if (outcome.kind === "done") setErrors({});
    else setUncertain(true);
  }

  const common = { values, errors, set };
  const named = (items: Choice[]) => items.map((i) => ({ value: String(i.id), label: i.nombre }));
  const estados = named(options.estados);
  const avisos = options.avisos.map((a) => ({ value: String(a.id), label: a.texto }));
  const municipioItems = named(municipios.items);
  return <>
    <div className="d-flex justify-content-between mb-3">
      <a href="#" data-history-back="true" className="btn btn-secondary" onClick={historyBack}>Cancelar</a>
    </div>
    <div className="row comedor-form"><div className="col-12">
      <form method="post" id="pasInformeForm" className="w-100" onSubmit={(e) => void send(e)}>
        {errors.__all__ && <div className="alert alert-danger">{errors.__all__.join(" ")}</div>}
        {uncertain && <div className="alert alert-danger" role="alert">{UNCERTAIN} <a href="/pas/informes">Ver informes</a></div>}
        <Section icon="fa-calendar-alt" title="Rangos temporales" subtitle="Acote por alta del registro o por cambios de estado.">
          <div className="form-group row">
            <div className="col-md-3"><Input {...common} name="fecha_creacion_desde" label="Fecha creación desde" type="date" klass="dateinput" /></div>
            <div className="col-md-3"><Input {...common} name="fecha_creacion_hasta" label="Fecha creación hasta" type="date" klass="dateinput" /></div>
            <div className="col-md-3"><Input {...common} name="fecha_cambio_desde" label="Fecha de cambios desde" type="date" klass="dateinput" /></div>
            <div className="col-md-3"><Input {...common} name="fecha_cambio_hasta" label="Fecha de cambios hasta" type="date" klass="dateinput" /></div>
          </div>
        </Section>
        <Section icon="fa-exchange-alt" title="Estado y motivos" subtitle="Ejemplo: cambios de Baja a Activo dentro de un periodo.">
          <div className="form-group row">
            <div className="col-md-4"><Select {...common} name="estado_anterior" label="Estado anterior" empty="Todos" items={estados} /></div>
            <div className="col-md-4"><Select {...common} name="estado_nuevo" label="Estado resultante" empty="Todos" items={estados} /></div>
            <div className="col-md-4"><Select {...common} name="estado_actual" label="Estado actual" empty="Todos" items={estados} /></div>
          </div>
          <div className="form-group row">
            <div className="col-md-6"><Select {...common} name="aviso_cambio" label="Aviso del cambio" empty="Todos" items={avisos} /></div>
            <div className="col-md-6"><Select {...common} name="aviso_actual" label="Aviso actual" empty="Todos" items={avisos} /></div>
          </div>
        </Section>
        <Section icon="fa-filter" title="Filtros sugeridos" subtitle="Ubicacion, identificadores y usuario responsable del cambio.">
          <div className="form-group row">
            <div className="col-md-3"><Select {...common} name="provincia" label="Provincia" empty="Todas" items={named(options.provincias)} /></div>
            <div className="col-md-3"><Select {...common} name="municipio" label="Municipio" empty={municipios.reset ? "---------" : "Todos"} items={municipioItems} /></div>
            <div className="col-md-3"><Input {...common} name="dni" label="DNI" type="number" klass="numberinput" /></div>
            <div className="col-md-3"><Input {...common} name="id_persona" label="IdPersona" type="number" klass="numberinput" /></div>
          </div>
          <div className="form-group row">
            <div className="col-md-6"><Input {...common} name="usuario_cambio" label="Usuario que modificó" type="text" klass="textinput" placeholder="Usuario, nombre o apellido" /></div>
          </div>
        </Section>
        <div className="sticky-actions">
          <a href="/pas/informes" className="btn btn-secondary"><i className="fas fa-arrow-left mr-1" /> Volver</a>{" "}
          <button className="btn btn-primary" type="button" id="pasInformePreviewBtn" disabled={previewing || sending} onClick={() => void showPreview()}>
            {previewing ? <><i className="fas fa-spinner fa-spin mr-1" /> Previsualizando</> : <><i className="fas fa-eye mr-1" /> Previsualizar</>}
          </button>{" "}
          <button className="btn btn-success" type="submit" disabled={sending || previewing}><i className="fas fa-download mr-1" /> Realizar informe</button>
        </div>
      </form>
      {preview.shown && <PreviewCard preview={preview.data} messages={preview.messages} />}
    </div></div>
  </>;
}

function GenerarPage() {
  const [state, setState] = useMainResource(`${PAS_API}informes/opciones/`, optionsValid);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: "Generar informe PAS", breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <>
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      <RequestForm options={data} onForbidden={(body) => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(body) })} />
    </>,
  }));
}

export const pasInformesGenerarRoute: RouteDefinition<{ page: "generar" }> = {
  name: "pas-informes-generar",
  match: (pathname) => (pathname === "/pas/informes/generar" ? { page: "generar" } : null),
  render: () => <GenerarPage />,
};
