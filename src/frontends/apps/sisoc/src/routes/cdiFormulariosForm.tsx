/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen, helpers and validators live here with the route. */
import { Fragment, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "../webAccess";
import { client, internal, messagesValid, navigation, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import { bindFormularioForm } from "./cdiFormulariosForm.behavior";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDI03 institutional form create and edit (`centrodeinfancia/formulario_cdi_form.html`):
 * the section cards, the per-day schedule card, and the three fixed formsets (room
 * distribution with live totals, unmet demand and institutional articulation). The
 * fields are the server-rendered `as_crispy_field` markup of the native form and the
 * formset cells the native widgets, so labels, widgets and error feedback come from
 * `FormularioCDIForm` and its formsets; the layout, the management forms, the key
 * widgets and the submit are drawn here and the inline script of the template runs as
 * `cdiFormulariosForm.behavior.ts`. Saving goes to `/api/web/cdi/`, which runs the
 * native view; a saved form returns to its detail page where the queued message shows.
 * A POST is sent once and never retried.
 */
type Oculto = { name: string; id: string; value: string };
type Celda = { html: string; errors: string[] };
type FormsetData = { management: Oculto[]; non_form_errors: string[]; rows: { hidden: Oculto[]; label: string; cells: Celda[] }[] };
type Campo = { name: string; col_class: string; html: string };
export type FormularioFormData = {
  is_edit: boolean;
  centro: { id: number; nombre: string; codigo: string; listado_url: string; cancelar_url: string };
  has_errors: boolean;
  non_field_errors: string[];
  sections: { title: string; rows: Campo[][] }[];
  horarios: { dia: string; etiqueta: string; apertura: string; cierre: string }[];
  formsets: { salas: FormsetData; demanda: FormsetData; articulacion: FormsetData };
  urls: { departamentos: string; municipios: string; localidades: string };
  messages: CdiMessage[];
};

const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text);
const ocultosValid = (v: unknown): v is Oculto[] => Array.isArray(v) && v.every((o) => record(o) && text(o.name) && text(o.id) && text(o.value));
const formsetValid = (width: number) => (f: unknown): f is FormsetData => record(f) && ocultosValid(f.management) && strings(f.non_form_errors) && Array.isArray(f.rows) &&
  f.rows.every((r) => record(r) && ocultosValid(r.hidden) && text(r.label) && Array.isArray(r.cells) && r.cells.length === width &&
    r.cells.every((c) => record(c) && text(c.html) && strings(c.errors)));

export function formValid(v: unknown): v is FormularioFormData {
  if (!record(v) || !record(v.centro) || !record(v.formsets) || !record(v.urls)) return false;
  const c = v.centro;
  return typeof v.is_edit === "boolean" && Number.isSafeInteger(c.id) && text(c.nombre) && text(c.codigo) && internal(c.listado_url) && internal(c.cancelar_url) &&
    typeof v.has_errors === "boolean" && strings(v.non_field_errors) && messagesValid(v.messages) &&
    Array.isArray(v.sections) && v.sections.every((s) => record(s) && text(s.title) && Array.isArray(s.rows) &&
      s.rows.every((r) => Array.isArray(r) && r.every((f) => record(f) && text(f.name) && text(f.col_class) && text(f.html)))) &&
    Array.isArray(v.horarios) && v.horarios.every((h) => record(h) && text(h.dia) && text(h.etiqueta) && text(h.apertura) && text(h.cierre)) &&
    formsetValid(4)(v.formsets.salas) && formsetValid(1)(v.formsets.demanda) && formsetValid(1)(v.formsets.articulacion) &&
    ["departamentos", "municipios", "localidades"].every((k) => internal((v.urls as Record<string, unknown>)[k]));
}

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
const Errors = ({ list }: { list: string[] }) => <ul className="errorlist nonfield">{list.map((e, i) => <li key={i}>{e}</li>)}</ul>;
const cellHtml = (c: Celda) => c.html + c.errors.map((e) => `<div class="invalid-feedback d-block">${esc(e)}</div>`).join("");

function Hidden({ items }: { items: Oculto[] }) {
  return <>{items.map((o) => <input key={o.name} type="hidden" name={o.name} id={o.id} defaultValue={o.value} />)}</>;
}

function Card({ title, id, children }: { title: string; id?: string; children: ReactNode }) {
  return (
    <div className="card mb-3" id={id}>
      <div className="card-header"><strong>{title}</strong></div>
      <div className="card-body">{children}</div>
    </div>
  );
}

function Horarios({ data }: { data: FormularioFormData }) {
  return (
    <Card title="Horarios de funcionamiento por día" id="horarios-funcionamiento-card">
      {data.horarios.map((h) => (
        <div key={h.dia} className="row align-items-start mb-3 formulario-horario-row d-none" data-dia={h.dia}>
          <div className="col-md-4"><label className="form-label fw-semibold">{h.etiqueta}</label></div>
          <div className="col-md-4" dangerouslySetInnerHTML={{ __html: h.apertura }} />
          <div className="col-md-4" dangerouslySetInnerHTML={{ __html: h.cierre }} />
        </div>
      ))}
    </Card>
  );
}

function Formset({ title, data, heads, children }: { title: string; data: FormsetData; heads: string[]; children?: ReactNode }) {
  return (
    <Card title={title}>
      <Hidden items={data.management} />
      {data.non_form_errors.length > 0 && <div className="alert alert-danger"><Errors list={data.non_form_errors} /></div>}
      <div className="table-responsive">
        <table className="table table-bordered align-middle">
          <thead><tr>{heads.map((h) => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>
            {data.rows.map((row, n) => (
              <tr key={n}>
                <td><Hidden items={row.hidden} />{row.label}</td>
                {row.cells.map((c, i) => <td key={i} dangerouslySetInnerHTML={{ __html: cellHtml(c) }} />)}
                {heads.length === 6 && <td className="room-staff-ratio">-</td>}
              </tr>
            ))}
            {children}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

type PostResult = { kind: "redirect"; to: string } | { kind: "invalid"; data: unknown } | { kind: "forbidden"; data: unknown } | { kind: "rejected"; detail: string | null } | { kind: "uncertain" };

/** POST once, URL-encoded like the native form; an unconfirmed outcome is reported, never resubmitted. */
async function postOnce(endpoint: string, body: URLSearchParams): Promise<PostResult> {
  try {
    const { data, status } = await client.post(endpoint, body, { validateStatus: () => true });
    if (status === 400) return { kind: "invalid", data };
    if (status === 403 && record(data) && "state" in data) return { kind: "forbidden", data };
    if (status === 403 || status === 404) return { kind: "rejected", detail: record(data) && text(data.detail) ? data.detail : null };
    if (status >= 200 && status < 300 && record(data) && data.ok === true && internal(data.redirect)) return { kind: "redirect", to: data.redirect as string };
    return { kind: "uncertain" };
  } catch {
    return { kind: "uncertain" };
  }
}

const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";

export function FormularioFormContent({ data: initial, endpoint }: { data: FormularioFormData; endpoint: string }) {
  const [data, setData] = useState(initial);
  const [version, setVersion] = useState(0);
  const [toasts, setToasts] = useState<CdiMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [forbidden, setForbidden] = useState<{ prerequisite: WebPrerequisite | null } | null>(null);
  const sending = useRef(false);
  const { departamentos, municipios, localidades } = data.urls;

  useEffect(() => bindFormularioForm({ departamentos, municipios, localidades }), [version, departamentos, municipios, localidades]);

  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;

  async function submit(target: HTMLFormElement) {
    if (sending.current) return;
    sending.current = true;
    setPending(true);
    const body = new URLSearchParams();
    new FormData(target).forEach((value, key) => { if (typeof value === "string") body.append(key, value); });
    const result = await postOnce(endpoint, body);
    if (result.kind === "redirect") { navigation.assign(result.to); return; }
    if (result.kind === "invalid" && formValid(result.data)) {
      setData(result.data);
      setToasts(result.data.messages);
      setVersion((v) => v + 1);
      setUncertain(false);
      resetAfterRejectedPost();
    } else if (result.kind === "forbidden") setForbidden({ prerequisite: prerequisiteFromForbidden(result.data) });
    else if (result.kind === "rejected") window.alert(result.detail ?? "No se pudo completar la acción.");
    else setUncertain(true);
    sending.current = false;
    setPending(false);
  }

  const { centro, formsets } = data;
  // The native script moves the schedule card right after the row of the days field.
  const hasDays = data.sections.some((s) => s.rows.some((r) => r.some((f) => f.name === "dias_funcionamiento")));
  return (
    <>
      {toasts.length > 0 && <NativeToasts messages={toasts} />}
      <div className="container-fluid">
        <div className="d-flex justify-content-between mb-3">
          <a href={safeInternalPath(centro.listado_url) ?? "/"} className="btn btn-outline-secondary">Ver formularios</a>
        </div>
        <div className="card mb-3">
          <div className="card-body">
            <h3 className="mb-1">{centro.nombre}</h3>
            <p className="text-muted mb-0">Formulario vinculado al centro #{centro.id} ({centro.codigo})</p>
          </div>
        </div>
        <form method="post" noValidate key={version} onSubmit={(e: FormEvent<HTMLFormElement>) => { e.preventDefault(); void submit(e.currentTarget); }}>
          {data.has_errors && (
            <div className="alert alert-danger">
              No se pudo guardar el formulario. Revisá los campos marcados.
              {data.non_field_errors.length > 0 && <div className="mt-2"><Errors list={data.non_field_errors} /></div>}
            </div>
          )}
          {data.sections.map((section, n) => (
            <Card key={n} title={section.title}>
              {section.rows.map((row, k) => (
                <Fragment key={k}>
                  <div className="row">
                    {row.map((f) => <div key={f.name} className={`${f.col_class} mb-3 form-field-wrapper`} data-field-name={f.name} dangerouslySetInnerHTML={{ __html: f.html }} />)}
                  </div>
                  {row.some((f) => f.name === "dias_funcionamiento") && <Horarios data={data} />}
                </Fragment>
              ))}
            </Card>
          ))}
          {!hasDays && <Horarios data={data} />}
          <Formset title="Organización de Salas: ¿Cómo se distribuyen los niños y niñas en las salas dentro del CDI? Complete la siguiente tabla consignando para cada grupo existente, la cantidad de salas, la superficie exclusiva en m², la cantidad de niñas y niños que concurren y la cantidad de personal de sala disponible."
            data={formsets.salas} heads={["Grupo etario", "Cantidad de Salas (A)", "Superficie m2", "Niñas y niños", "Cantidad de Personal de Sala (B)", "Cantidad de personal por sala (B/A)"]}>
            <tr className="table-secondary fw-semibold">
              <td>Totales</td><td id="room-total-count">0</td><td id="room-total-area">0</td><td id="room-total-children">0</td><td id="room-total-staff">0</td><td id="room-total-ratio">-</td>
            </tr>
          </Formset>
          <Formset title="Demanda insatisfecha por sala" data={formsets.demanda} heads={["Grupo etario", "Lista de espera"]} />
          <Formset title="Articulaciones institucionales" data={formsets.articulacion} heads={["Institucion", "Frecuencia"]} />
          {uncertain && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
          <div className="d-flex gap-2 justify-content-end mb-4">
            <button className="btn btn-primary" type="submit" disabled={pending || undefined}>Guardar</button>
            <a href={safeInternalPath(centro.cancelar_url) ?? "/"} className="btn btn-secondary">Cancelar</a>
          </div>
        </form>
      </div>
    </>
  );
}

function FormularioFormPage({ centro, id }: { centro: string; id?: string }) {
  const base = `web/cdi/centros/${centro}/formularios/`;
  const endpoint = id ? `${base}${id}/editar/` : `${base}crear/`;
  const [state] = useCdiPage(endpoint, formValid);
  return renderCdi(state, (data) => {
    const title = `${data.is_edit ? "Editar" : "Nuevo"} Formulario CDI`;
    return { title, heading: title, content: <FormularioFormContent data={data} endpoint={endpoint} /> };
  });
}

const OWN = /^\/centrodeinfancia\/([1-9]\d*)\/formularios\/(?:crear|([1-9]\d*)\/editar)\/$/;

// Native URLs of the CDI institutional form create and edit (CDI03); same trailing slash.
export const cdiFormularioFormRoute: RouteDefinition<{ centro: string; id?: string }> = {
  name: "cdi-formulario-form",
  match: (pathname) => {
    const own = OWN.exec(pathname);
    return own ? { centro: own[1], id: own[2] } : null;
  },
  render: ({ centro, id }) => <FormularioFormPage centro={centro} id={id} />,
};
