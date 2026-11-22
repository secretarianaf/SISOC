/* eslint-disable react-refresh/only-export-components -- the form screens export their validators and navigation seam for the unit tests. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "../webAccess";
import InsumosAccessError from "../InsumosAccessError";
import DuplasSelect2, { type Choice } from "./duplasSelect2";
import { API, LIST_PATH, client, integer, messagesValid, record, renderDuplas, text, useDuplasResource, type Message } from "./duplasShared";

/**
 * `dupla_form.html` (create and edit share it, title «Editar Equipo técnico»)
 * and `dupla_confirm_delete.html` (`delete_confirm.html` with the cascade
 * preview). POSTs go to the web API, which runs the native view's `post()`;
 * a confirmed redirect is a full-page navigation, like the native 302.
 */
type FieldName = "nombre" | "estado" | "tecnico" | "abogado";
type Field = { label: string; required: boolean; help_text: string; value: string | string[]; max_length?: number; choices?: Choice[] };
type Errors = Record<string, { message: string; code: string }[]>;
export type DuplaFormData = {
  title: string;
  fields: Record<FieldName, Field>;
  errors: Errors;
  coordinador: string | null;
  urls: { cancel: string };
  messages: Message[];
};
type Preview = { total_afectados: number; total_baja_logica: number; total_borrado_fisico: number; desglose_por_modelo: { modelo: string; cantidad: number; modo: string; ejemplos: string[] }[] };
export type DuplaDeleteData = {
  id: number; object_name: string; title: string; confirm_text: string; cancel_text: string;
  cascade_preview: Preview | null; urls: { cancel: string }; messages: Message[];
};

const NAMES: FieldName[] = ["nombre", "estado", "tecnico", "abogado"];
const choicesValid = (v: unknown) => Array.isArray(v) && v.every((c) => record(c) && text(c.value) && text(c.label));
const errorsValid = (v: unknown): v is Errors => record(v) &&
  Object.values(v).every((list) => Array.isArray(list) && list.every((e) => record(e) && text(e.message)));

export function formValid(v: unknown): v is DuplaFormData {
  if (!record(v) || !record(v.fields) || !record(v.urls)) return false;
  const f = v.fields as Record<string, unknown>;
  return text(v.title) && NAMES.every((n) => {
    const x = f[n];
    return record(x) && text(x.label) && typeof x.required === "boolean" && text(x.help_text) &&
      (n === "tecnico" ? Array.isArray(x.value) && x.value.every(text) : text(x.value)) &&
      (n === "nombre" ? integer(x.max_length) : choicesValid(x.choices));
  }) && errorsValid(v.errors) && (v.coordinador === null || text(v.coordinador)) &&
    safeInternalPath(v.urls.cancel) !== null && messagesValid(v.messages);
}

export function deleteValid(v: unknown): v is DuplaDeleteData {
  if (!record(v) || !record(v.urls)) return false;
  const p = v.cascade_preview;
  return integer(v.id) && ["object_name", "title", "confirm_text", "cancel_text"].every((k) => text(v[k])) &&
    (p === null || (record(p) && ["total_afectados", "total_baja_logica", "total_borrado_fisico"].every((k) => integer(p[k] ?? 0)) &&
      Array.isArray(p.desglose_por_modelo) && p.desglose_por_modelo.every((d) => record(d) && text(d.modelo) && integer(d.cantidad) && text(d.modo) &&
        Array.isArray(d.ejemplos) && d.ejemplos.every(text)))) &&
    safeInternalPath(v.urls.cancel) !== null && messagesValid(v.messages);
}

/** Full-page navigation after a confirmed POST; replaceable in tests. */
export const duplasFormNavigation = { assign: (to: string) => window.location.assign(to) };
const accepted = (status: number) => (status >= 200 && status < 300) || status === 403 || status === 400;

type Outcome = { kind: "redirect"; to: string } | { kind: "invalid"; data: unknown } | { kind: "forbidden"; data: unknown } | { kind: "uncertain" };

/** POST once; an unconfirmed outcome is reported, never resubmitted. */
async function postOnce(endpoint: string, body: URLSearchParams): Promise<Outcome> {
  try {
    const { data, status } = await client.post(endpoint, body, { validateStatus: accepted });
    if (status === 403) return { kind: "forbidden", data };
    if (status === 400) return { kind: "invalid", data };
    if (record(data) && data.ok === true && text(data.redirect) && safeInternalPath(data.redirect) === data.redirect && data.redirect.startsWith(LIST_PATH)) {
      return { kind: "redirect", to: data.redirect };
    }
  } catch {
    // Network error or timeout after sending: the result is unknown.
  }
  return { kind: "uncertain" };
}

function CsrfInput() {
  return <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;
}

function Uncertain() {
  return <p role="alert">No se pudo confirmar el resultado. <a href={LIST_PATH}>Volver al listado</a></p>;
}

function FieldErrors({ id, errors }: { id: string; errors: Errors[string] | undefined }) {
  if (!errors?.length) return null;
  return <div id={`${id}_error`} className="invalid-feedback">{errors.map((e, i) => <p key={i} id={`error_${i + 1}_${id}`}><strong>{e.message}</strong></p>)}</div>;
}

function Label({ id, field }: { id: string; field: Field }) {
  return <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>{field.label}{field.required && <span className="asteriskField">*</span>}</label>;
}

type Values = { nombre: string; estado: string; tecnico: string[]; abogado: string };
const valuesOf = (data: DuplaFormData): Values => ({
  nombre: data.fields.nombre.value as string, estado: data.fields.estado.value as string,
  tecnico: data.fields.tecnico.value as string[], abogado: data.fields.abogado.value as string,
});

function SelectField({ name, field, value, errors, onChange, extraClass }: { name: "estado" | "abogado"; field: Field; value: string; errors: Errors; onChange: (v: string) => void; extraClass: string }) {
  const id = `id_${name}`, invalid = !!errors[name]?.length;
  return (
    <div id={`div_${id}`} className="mb-3">
      <Label id={id} field={field} />
      <select name={name} className={`${extraClass}select form-select${invalid ? " is-invalid" : ""}`} required={field.required} id={id} value={value}
        aria-invalid={invalid ? "true" : undefined} aria-describedby={invalid ? `${id}_error` : undefined} onChange={(e) => onChange(e.target.value)}>
        {(field.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
      <FieldErrors id={id} errors={errors[name]} />
    </div>
  );
}

function Card({ icon, title, children }: { icon: string; title: string; children: ReactNode }) {
  return (
    <div className="card card-custom mb-3 shadow-sm">
      <div className="card-header card-header-custom"><h5 className="mb-0"><i className={`fas ${icon}`} />{title}</h5></div>
      <div className="card-body">{children}</div>
    </div>
  );
}

export function DuplaFormContent({ initial, endpoint, onForbidden }: { initial: DuplaFormData; endpoint: string; onForbidden: (data: unknown) => void }) {
  const [data, setData] = useState(initial);
  const [values, setValues] = useState(() => valuesOf(initial));
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  // An invalid response is a native re-render: the widgets start again.
  const [revision, setRevision] = useState(0);
  const busy = useRef(false);
  const active = useRef(true);
  useEffect(() => () => { active.current = false; }, []);
  const set = <K extends keyof Values>(key: K, value: Values[K]) => setValues((current) => ({ ...current, [key]: value }));
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    const body = new URLSearchParams({ nombre: values.nombre, estado: values.estado, abogado: values.abogado });
    values.tecnico.forEach((id) => body.append("tecnico", id));
    const outcome = await postOnce(endpoint, body);
    if (!active.current) return;
    if (outcome.kind === "redirect") { duplasFormNavigation.assign(outcome.to); return; }
    if (outcome.kind === "forbidden") onForbidden(outcome.data);
    else if (outcome.kind === "invalid" && formValid(outcome.data)) {
      setData(outcome.data); setValues(valuesOf(outcome.data)); setRevision((r) => r + 1);
      window.scrollTo?.({ top: 0, left: 0, behavior: "instant" });
      busy.current = false;
    } else setUncertain(true);
    setPending(false);
  }
  const f = data.fields, e = data.errors;
  const nombreInvalid = !!e.nombre?.length, tecnicoInvalid = !!e.tecnico?.length;
  return (
    <>
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css" />
      <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
      <link rel="stylesheet" href="/static/custom/css/hitos.css" />
      <link rel="stylesheet" href="/static/custom/css/duplasSelect2.min.css" />
      <link rel="stylesheet" href="/static/custom/css/user_form.css" />
      <InsumosToastList key={`messages-${revision}`} messages={data.messages} />
      <div className="container mt-4">
        <h2>{data.title}</h2>
        <form key={revision} method="post" onSubmit={submit}>
          <CsrfInput />
          {uncertain && <Uncertain />}
          <Card icon="fa-id-card" title="Datos del Equipo Técnico">
            <div id="div_id_nombre" className="mb-3">
              <Label id="id_nombre" field={f.nombre} />
              <input type="text" name="nombre" maxLength={f.nombre.max_length} className={`textinput form-control${nombreInvalid ? " is-invalid" : ""}`} required id="id_nombre"
                aria-invalid={nombreInvalid ? "true" : undefined} aria-describedby={nombreInvalid ? "id_nombre_error" : undefined}
                value={values.nombre} disabled={pending || uncertain} onChange={(ev) => set("nombre", ev.target.value)} />
              <FieldErrors id="id_nombre" errors={e.nombre} />
            </div>
            <SelectField name="estado" field={f.estado} value={values.estado} errors={e} onChange={(v) => set("estado", v)} extraClass="" />
          </Card>
          <Card icon="fa-users" title="Miembros del Equipo Técnico">
            <div id="div_id_tecnico" className="mb-3">
              <Label id="id_tecnico" field={f.tecnico} />
              <DuplasSelect2 id="id_tecnico" name="tecnico" placeholder="Selecciona técnicos" choices={f.tecnico.choices ?? []} value={values.tecnico}
                onChange={(v) => set("tecnico", v)} invalid={tecnicoInvalid} describedBy={`id_tecnico_helptext${tecnicoInvalid ? " id_tecnico_error" : ""}`} />
              <FieldErrors id="id_tecnico" errors={e.tecnico} />
              {f.tecnico.help_text && <div id="id_tecnico_helptext" className="form-text">{f.tecnico.help_text}</div>}
            </div>
            <SelectField name="abogado" field={f.abogado} value={values.abogado} errors={e} onChange={(v) => set("abogado", v)} extraClass="form-control " />
          </Card>
          <Card icon="fa-user-tie" title="Coordinador del Equipo Técnico">
            <div className="alert alert-info mb-0" role="alert">
              <strong>Coordinador de Equipo Técnico:</strong>
              {" "}{data.coordinador ?? <span className="badge badge-warning">Sin asignar</span>}
              {" "}<br />
              {" "}<small className="text-muted">El coordinador se asigna desde módulo de configuración de Usuarios</small>
            </div>
          </Card>
          <div className="row">
            <div className="col-md-12">
              <div className="form-group mb-0 mt-3 d-flex justify-content-between">
                <a href={data.urls.cancel} className="btn btn-secondary mb-3">Cancelar</a>
                <div>
                  <button type="submit" className="btn btn-primary mb-3" disabled={pending || uncertain}><i className="fas fa-save me-1" /> Guardar</button>
                </div>
              </div>
            </div>
          </div>
        </form>
      </div>
    </>
  );
}

export function DuplaDeleteContent({ data, endpoint, onForbidden }: { data: DuplaDeleteData; endpoint: string; onForbidden: (data: unknown) => void }) {
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setPending(true);
    const outcome = await postOnce(endpoint, new URLSearchParams());
    if (outcome.kind === "redirect") { duplasFormNavigation.assign(outcome.to); return; }
    if (outcome.kind === "forbidden") onForbidden(outcome.data); else setUncertain(true);
    setPending(false);
  }
  const p = data.cascade_preview;
  return (
    <>
      <InsumosToastList messages={data.messages} />
      <div className="error-page mt-5 px-3">
        <div className="error-content">
          <h3><i className="fas fa-exclamation-triangle text-danger px-2" />{" "}{data.title}</h3>
          <p>
            ¿Estás seguro que deseas realizar una baja lógica en cascada del registro
            {" "}<span className="font-weight-bold">{data.object_name}</span>?
          </p>
          {p && (
            <>
              <div className="alert alert-info">
                <div><strong>Total de registros afectados:</strong>{" "}{p.total_afectados}</div>
                {!!p.total_baja_logica && <div>Bajas lógicas: {p.total_baja_logica}</div>}
                {!!p.total_borrado_fisico && <div>Borrados físicos técnicos: {p.total_borrado_fisico}</div>}
              </div>
              <div className="table-responsive mb-3">
                <table className="table table-sm table-striped mb-0">
                  <thead><tr><th>Modelo</th><th>Cantidad</th><th>Acción</th><th>Ejemplos</th></tr></thead>
                  <tbody>
                    {p.desglose_por_modelo.map((item, index) => (
                      <tr key={index}>
                        <td>{item.modelo}</td>
                        <td>{item.cantidad}</td>
                        <td>{item.modo === "baja_logica" ? "Baja lógica" : "Borrado físico técnico"}</td>
                        <td>{item.ejemplos.length ? item.ejemplos.join(", ") : "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          <div className="text-left">
            <form method="post" action="" onSubmit={submit}>
              <CsrfInput />
              {uncertain && <Uncertain />}
              <button type="submit" className="btn btn-danger btn-sm" disabled={pending || uncertain}>{data.confirm_text}</button>
              {" "}<a href={data.urls.cancel} className="btn btn-secondary btn-sm">{data.cancel_text}</a>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}

function useForbidden() {
  const [forbidden, setForbidden] = useState<{ prerequisite: WebPrerequisite | null } | null>(null);
  return [forbidden, (data: unknown) => setForbidden({ prerequisite: prerequisiteFromForbidden(data) })] as const;
}

export function DuplaFormPage({ id }: { id?: string }) {
  const endpoint = id ? `${API}${id}/editar/` : `${API}crear/`;
  const state = useDuplasResource(endpoint, formValid);
  const [forbidden, onForbidden] = useForbidden();
  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;
  return renderDuplas(state, (data) => ({
    title: data.title, heading: "", breadcrumb: null,
    content: <DuplaFormContent initial={data} endpoint={endpoint} onForbidden={onForbidden} />,
  }));
}

export function DuplaDeletePage({ id }: { id: string }) {
  const endpoint = `${API}${id}/eliminar/`;
  const state = useDuplasResource(endpoint, deleteValid);
  const [forbidden, onForbidden] = useForbidden();
  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;
  return renderDuplas(state, (data) => ({
    title: "Borrar Equipo técnico", heading: "", breadcrumb: null,
    content: <DuplaDeleteContent data={data} endpoint={endpoint} onForbidden={onForbidden} />,
  }));
}
