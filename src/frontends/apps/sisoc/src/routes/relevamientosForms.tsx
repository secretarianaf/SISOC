/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useState, type FormEvent, type ReactNode } from "react";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { Tree, arr, bool, csrf, integer, messagesValid, nodeValid, path, useCardCollapse, type TreeNode } from "./relevamientos";
import { UNCERTAIN, postApi, relevamientosNavigation, restartFromTop, setFlash, useToasts, type Message } from "./relevamientosApi";
import { CSS } from "./relevamientosShared";
import type { RouteDefinition } from "./types";

/**
 * R03.02 `seguimiento_form.html` and R02.02 `acta_complementaria_form.html`.
 * The API projects the native editors (`SeguimientoEditor`,
 * `ActaComplementariaEditor`): every field arrives as its real widget markup
 * with its bound errors, and the POST carries the native names (`seg-*`,
 * `<bloque>-*`, `acta-*`, `prestaciones-*`). A 400 re-renders the page with the
 * errors; a lost answer is never resent.
 */
export type Field = { name: string; label: string; id: string; hidden: boolean; help_text: string; errors: string[]; nodes: TreeNode[] };
type Form = { fields: Field[]; non_field_errors: string[] };
type Formset = { management: Field[]; forms: { hidden: Field[]; fields: Field[] }[]; non_form_errors: string[] };
export type SeguimientoFormData = {
  seguimiento: { id: number; tipo_display: string; numero_orden: number }; relevamiento: { id: number; fecha_visita: string }; comedor: { id: number; nombre: string };
  root: Form; bloques: { key: string; label: string; existe: boolean; form: Form }[]; prestaciones: Formset;
  urls: { comedores: string; comedor: string; relevamiento: string; detalle: string }; messages: Message[];
};
export type ActaFormData = {
  acta_id: number | null; comedor: { id: number; nombre: string }; form: Form; prestaciones: Formset;
  urls: { comedores: string; comedor: string; listado: string }; messages: Message[];
};

const API = "web/comedores/relevamientos/";
const fieldValid = (f: unknown) => record(f) && text(f.name) && text(f.label) && text(f.id) && bool(f.hidden) && text(f.help_text) && arr(f.errors, text) && arr(f.nodes, nodeValid);
const formValid = (f: unknown) => record(f) && arr(f.fields, fieldValid) && arr(f.non_field_errors, text);
const formsetValid = (f: unknown) => record(f) && arr(f.management, fieldValid) && arr(f.forms, (r) => record(r) && arr(r.hidden, fieldValid) && arr(r.fields, fieldValid)) && arr(f.non_form_errors, text);

export function seguimientoFormValid(v: unknown): v is SeguimientoFormData {
  if (!record(v) || !record(v.seguimiento) || !record(v.relevamiento) || !record(v.comedor) || !record(v.urls)) return false;
  const urls = v.urls;
  return integer(v.seguimiento.id) && text(v.seguimiento.tipo_display) && integer(v.seguimiento.numero_orden) && integer(v.relevamiento.id) && text(v.relevamiento.fecha_visita) &&
    integer(v.comedor.id) && text(v.comedor.nombre) && formValid(v.root) &&
    arr(v.bloques, (b) => record(b) && text(b.key) && text(b.label) && bool(b.existe) && formValid(b.form)) && formsetValid(v.prestaciones) &&
    ["comedores", "comedor", "relevamiento", "detalle"].every((k) => internal(urls[k])) && messagesValid(v.messages);
}

export function actaFormValid(v: unknown): v is ActaFormData {
  if (!record(v) || !record(v.comedor) || !record(v.urls)) return false;
  const urls = v.urls;
  return (v.acta_id === null || integer(v.acta_id)) && integer(v.comedor.id) && text(v.comedor.nombre) && formValid(v.form) && formsetValid(v.prestaciones) &&
    ["comedores", "comedor", "listado"].every((k) => internal(urls[k])) && messagesValid(v.messages);
}

/** `{{ errors }}`: Django's `<ul class="errorlist">`. */
const ErrorList = ({ errors, nonfield = false }: { errors: string[]; nonfield?: boolean }) => (
  <ul className={`errorlist${nonfield ? " nonfield" : ""}`}>{errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
);

/** `{{ field }}` with its label, help text and errors, in the markup of the native loops. */
function FieldBox({ field, cls }: { field: Field; cls: string }) {
  return (
    <div className={cls}>
      <label htmlFor={field.id} className="form-label">{field.label}</label>
      <Tree nodes={field.nodes} />
      {field.help_text && <small className="form-text text-muted">{field.help_text}</small>}
      {field.errors.map((e, i) => <div className="text-danger small" key={i}>{e}</div>)}
    </div>
  );
}

function Prestaciones({ formset, head, title, tail }: { formset: Formset; head: string[]; title: string; tail: ReactNode }) {
  return (
    <div className="card mb-3" id="bloque-prestaciones">
      <div className="card-header"><h3 className="card-title font-weight-bold mr-3 pt-1">{title}</h3></div>
      <div className="card-body p-0">
        {formset.management.map((f) => <Tree key={f.name} nodes={f.nodes} />)}
        {formset.non_form_errors.length > 0 && <div className="alert alert-danger m-3"><ErrorList errors={formset.non_form_errors} nonfield /></div>}
        <div className="table-responsive">
          <table className="table table-striped mb-0">
            <thead><tr>{head.map((h) => <th key={h}>{h}</th>)}</tr></thead>
            <tbody>
              {formset.forms.map((row, i) => (
                <tr key={i}>
                  {row.hidden.map((f) => <Tree key={f.name} nodes={f.nodes} />)}
                  {row.fields.map((f) => <td key={f.name}><Tree nodes={f.nodes} />{f.errors.map((e, j) => <div className="text-danger small" key={j}>{e}</div>)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {tail}
      </div>
    </div>
  );
}

const PRESTACIONES_HELP = <p className="text-muted small m-3 mb-2">La última fila vacía permite agregar una prestación. Guarde y vuelva a editar para agregar más.</p>;

type Saver<T> = { data: T; version: number; pending: boolean; uncertain: boolean; submit: (event: FormEvent<HTMLFormElement>) => void };

/** The POST of a native form: ok flashes and goes on, a 400 re-renders the bound form, a lost answer is never resent. */
function useFormSave<T>(initial: T, endpoint: string, push: (m: Message) => void): Saver<T> {
  const [state, setState] = useState({ data: initial, version: 0 });
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    const result = await postApi(endpoint, new URLSearchParams(new FormData(event.currentTarget) as unknown as Record<string, string>));
    if (result.kind === "ok") {
      setFlash([{ message: result.message, level: "success" }]);
      relevamientosNavigation.assign(result.redirect);
      return;
    }
    if (result.kind === "invalid") {
      setState((s) => ({ data: { ...s.data, ...(result.body as Partial<T>) }, version: s.version + 1 }));
      push({ message: String(result.body.detail), level: "error" });
      window.setTimeout(restartFromTop, 0);
    } else if (result.kind === "error") push({ message: result.message, level: "error" });
    else setUncertain(true);
    setPending(false);
  }
  return { data: state.data, version: state.version, pending, uncertain, submit };
}

const Uncertain = () => (
  <div role="alert" className="alert alert-warning">{UNCERTAIN}{" "}
    <button type="button" className="btn btn-link p-0 align-baseline" onClick={() => relevamientosNavigation.assign(window.location.pathname)}>Recargar</button></div>
);

const Footer = ({ cancel, saver }: { cancel: string; saver: { pending: boolean; uncertain: boolean } }) => (
  <>
    {saver.uncertain && <Uncertain />}
    <div className="d-flex justify-content-end gap-2 mb-4">
      <a href={path(cancel)} className="btn btn-secondary">Cancelar</a>
      <button type="submit" className="btn btn-primary" disabled={saver.pending || saver.uncertain}>Guardar</button>
    </div>
  </>
);

// --- Seguimiento -------------------------------------------------------------

export function SeguimientoFormContent({ initial }: { initial: SeguimientoFormData }) {
  useCardCollapse();
  const { toasts, push } = useToasts(initial.messages);
  const { seguimiento: s } = initial;
  const saver = useFormSave(initial, `${API}${initial.comedor.id}/relevamiento/${initial.relevamiento.id}/seguimientos/${s.id}/editar/`, push);
  const data = saver.data;
  return <>
    {toasts}
    {CSS}
    <form method="post" noValidate key={saver.version} onSubmit={saver.submit}>
      {csrf()}
      {data.root.non_field_errors.length > 0 && <div className="alert alert-danger"><ErrorList errors={data.root.non_field_errors} nonfield /></div>}
      <div className="card mb-3">
        <div className="card-header"><h3 className="card-title font-weight-bold mr-3 pt-1">Datos de la instancia</h3></div>
        <div className="card-body"><div className="row">{data.root.fields.map((f) => <FieldBox key={f.name} field={f} cls="col-md-6 mb-3" />)}</div></div>
      </div>
      {data.bloques.map((b) => (
        <div className="card mb-3" id={`bloque-${b.key}`} key={b.key}>
          <div className="card-header d-flex align-items-center">
            <h3 className="card-title font-weight-bold mr-3 pt-1 mb-0">{b.label}</h3>
            {!b.existe && <>{" "}<span className="badge bg-secondary ml-2" title="Se crea solo si se completa algún campo">Sin cargar</span></>}
            <div className="card-tools ml-auto"><button type="button" className="btn btn-tool" data-card-widget="collapse"><i className="fas fa-minus" /></button></div>
          </div>
          <div className="card-body">
            {b.form.non_field_errors.length > 0 && <div className="alert alert-danger"><ErrorList errors={b.form.non_field_errors} nonfield /></div>}
            <div className="row">{b.form.fields.map((f) => <FieldBox key={f.name} field={f} cls="col-md-4 col-sm-6 mb-3" />)}</div>
          </div>
        </div>
      ))}
      <Prestaciones formset={data.prestaciones} title="Prestaciones" tail={PRESTACIONES_HELP}
        head={["Días", "Tipo", "AP presencial", "AP vianda", "AP total", "DE presencial", "DE vianda", "Eliminar"]} />
      <Footer cancel={data.urls.detalle} saver={saver} />
    </form>
  </>;
}

function SeguimientoFormPage({ comedor, relevamiento, id }: { comedor: string; relevamiento: string; id: string }) {
  const [state] = useMainResource(`${API}${comedor}/relevamiento/${relevamiento}/seguimientos/${id}/editar/`, seguimientoFormValid);
  return renderMain(state, "Cargando seguimiento…", (data) => {
    const s = data.seguimiento;
    const tipo = s.tipo_display.toLowerCase();
    return {
      title: `Editar ${tipo} - Comedor: ${data.comedor.nombre}`,
      heading: <>{data.comedor.nombre}{" "}<span className="ml-2 h5">| Editar {tipo} #{s.numero_orden}</span></> as unknown as string,
      breadcrumb: <>
        <div className="breadcrumb-item"><a href={path(data.urls.comedores)}>Comedores</a></div>
        <div className="breadcrumb-item"><a href={path(data.urls.comedor)}>{data.comedor.nombre}</a></div>
        <div className="breadcrumb-item"><a href={path(data.urls.relevamiento)}>Acompañamiento Territorial {data.relevamiento.fecha_visita}</a></div>
        <div className="breadcrumb-item"><a href={path(data.urls.detalle)}>{s.tipo_display}</a></div>
        <div className="breadcrumb-item active">Editar</div>
      </>,
      content: <SeguimientoFormContent initial={data} />,
    };
  });
}

// --- Acta ----------------------------------------------------------------------

export function ActaFormContent({ initial }: { initial: ActaFormData }) {
  const { toasts, push } = useToasts(initial.messages);
  const endpoint = `${API}${initial.comedor.id}/actas/${initial.acta_id === null ? "crear" : `${initial.acta_id}/editar`}/`;
  const saver = useFormSave(initial, endpoint, push);
  const data = saver.data;
  return <>
    {toasts}
    {CSS}
    <form method="post" noValidate key={saver.version} onSubmit={saver.submit}>
      {csrf()}
      <div className="card mb-3">
        <div className="card-header"><h3 className="card-title font-weight-bold mr-3 pt-1">Datos del acta</h3></div>
        <div className="card-body">
          <p className="text-muted">Registra, fuera del ciclo de visitas, un cambio en la prestación del comedor.</p>
          {data.form.non_field_errors.length > 0 && <div className="alert alert-danger"><ErrorList errors={data.form.non_field_errors} nonfield /></div>}
          <div className="row">{data.form.fields.map((f) => <FieldBox key={f.name} field={f} cls={`${f.name === "acta-observaciones" ? "col-12" : "col-md-6"} mb-3`} />)}</div>
        </div>
      </div>
      <Prestaciones formset={data.prestaciones} title="Prestaciones (día × tipo)" tail={PRESTACIONES_HELP} head={["Días", "Tipo", "Cantidad actual", "Cantidad en espera", "Eliminar"]} />
      <Footer cancel={data.urls.listado} saver={saver} />
    </form>
  </>;
}

function ActaFormPage({ comedor, id }: { comedor: string; id?: string }) {
  const [state] = useMainResource(`${API}${comedor}/actas/${id ? `${id}/editar` : "crear"}/`, actaFormValid);
  return renderMain(state, "Cargando acta…", (data) => {
    const prefijo = id ? "Editar" : "Nueva";
    return {
      title: `${prefijo} acta complementaria - Comedor: ${data.comedor.nombre}`,
      heading: <>{data.comedor.nombre}{" "}<span className="ml-2 h5">| {prefijo} acta complementaria extraordinaria</span></> as unknown as string,
      breadcrumb: <>
        <div className="breadcrumb-item"><a href={path(data.urls.comedores)}>Comedores</a></div>
        <div className="breadcrumb-item"><a href={path(data.urls.comedor)}>{data.comedor.nombre}</a></div>
        <div className="breadcrumb-item"><a href={path(data.urls.listado)}>Acompañamiento Territorial</a></div>
        <div className="breadcrumb-item active">Acta complementaria</div>
      </>,
      content: <ActaFormContent initial={data} />,
    };
  });
}

type Params = { comedor: string; relevamiento?: string; id?: string; acta?: boolean };
const SEGUIMIENTO = /^\/comedores\/([0-9]+)\/relevamiento\/([0-9]+)\/seguimiento\/([0-9]+)\/editar$/;
const ACTA_NUEVA = /^\/comedores\/([0-9]+)\/acta-complementaria\/crear$/;
const ACTA_EDITAR = /^\/comedores\/([0-9]+)\/acta-complementaria\/([0-9]+)\/editar$/;

export const relevamientosFormsRoute: RouteDefinition<Params> = {
  name: "comedores-relevamientos-formularios",
  match(pathname) {
    const s = SEGUIMIENTO.exec(pathname);
    if (s) return { comedor: s[1], relevamiento: s[2], id: s[3] };
    const n = ACTA_NUEVA.exec(pathname);
    if (n) return { comedor: n[1], acta: true };
    const e = ACTA_EDITAR.exec(pathname);
    return e ? { comedor: e[1], id: e[2], acta: true } : null;
  },
  render({ comedor, relevamiento, id, acta }) {
    return acta ? <ActaFormPage comedor={comedor} id={id} /> : <SeguimientoFormPage comedor={comedor} relevamiento={relevamiento!} id={id!} />;
  },
};
