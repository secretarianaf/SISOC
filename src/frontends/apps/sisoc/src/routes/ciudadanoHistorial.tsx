/* eslint-disable react-refresh/only-export-components -- route module: the validator is exported for the tests. */
import { Breadcrumb, internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * Instance history (the "Historial" action of the Ciudadano 360 ficha): `audittrail/log_list.html` in its
 * `is_instance_view` mode. GET `/api/web/auditoria/<app_label>/<model_name>/<object_pk>/` (+ the page query) runs
 * `AuditLogInstanceView` (403 without `auditlog.view_logentry`, 404 for a page out of range) and returns what the
 * template prints. Filters, pagination and the CSV/JSON export are plain GETs of the page itself, as in the native
 * page, so the form has no script. Values arrive formatted; only "No cargado" is marked as emphasised. Like the native `items|slice:":2"` (which does not
 * cut a `dict_items`), every change of a row is listed and the "+ N más" counter follows.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Valor = { empty: boolean; text: string };
type Campo = {
  name: string; label: string; hidden: boolean; widget: string; value: string; attrs: Record<string, string>;
  choices?: { value: string; label: string }[];
};
type Fila = {
  id: number; fecha_texto: string; actor_texto: string; actor_fallback: boolean; evento_texto: string; evento_clase: string;
  continuacion: boolean; masiva: boolean; masiva_inicio: boolean; masiva_cantidad: number; masiva_origen: string; con_diffs: boolean;
  cambios: { campo: string; old: Valor; new: Valor }[]; cambios_total: number; detalle_url: string;
};
export type HistorialData = {
  title: string; inicio_url: string; fields: Campo[]; field_errors: { label: string; message: string }[]; non_field_errors: string[];
  has_errors: boolean; puede_exportar: boolean; filtros_activos: { label: string; value: string }[]; filas: Fila[];
  paginacion: { is_paginated: boolean; number: number; num_pages: number; previous: boolean; next: boolean; querystring: string };
  messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const flag = (v: unknown) => typeof v === "boolean";
const count = (v: unknown) => Number.isSafeInteger(v);
const valor = (v: unknown) => record(v) && flag(v.empty) && text(v.text);
const campoValid = (c: unknown) => record(c) && text(c.name) && text(c.label) && flag(c.hidden) && text(c.widget) && text(c.value) &&
  record(c.attrs) && Object.values(c.attrs).every(text) &&
  (c.choices === undefined || (Array.isArray(c.choices) && c.choices.every((o) => record(o) && text(o.value) && text(o.label))));
const filaValid = (f: unknown) => record(f) && count(f.id) && text(f.fecha_texto) && text(f.actor_texto) && flag(f.actor_fallback) && text(f.evento_texto) &&
  text(f.evento_clase) && flag(f.continuacion) && flag(f.masiva) && flag(f.masiva_inicio) && count(f.masiva_cantidad) && text(f.masiva_origen) && flag(f.con_diffs) &&
  Array.isArray(f.cambios) && f.cambios.every((c) => record(c) && text(c.campo) && valor(c.old) && valor(c.new)) && count(f.cambios_total) && internal(f.detalle_url);

export function historialValid(v: unknown): v is HistorialData {
  if (!record(v) || !record(v.paginacion)) return false;
  const p = v.paginacion;
  return text(v.title) && internal(v.inicio_url) && Array.isArray(v.fields) && v.fields.every(campoValid) &&
    Array.isArray(v.field_errors) && v.field_errors.every((e) => record(e) && text(e.label) && text(e.message)) &&
    Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && flag(v.has_errors) && flag(v.puede_exportar) &&
    Array.isArray(v.filtros_activos) && v.filtros_activos.every((f) => record(f) && text(f.label) && text(f.value)) &&
    Array.isArray(v.filas) && v.filas.every(filaValid) &&
    flag(p.is_paginated) && count(p.number) && count(p.num_pages) && flag(p.previous) && flag(p.next) && text(p.querystring) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

function Control({ c }: { c: Campo }) {
  const common = { name: c.name, id: `id_${c.name}`, className: "form-control", defaultValue: c.value };
  if (c.widget === "select") return <select {...common}>{(c.choices ?? []).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>;
  return <input type={c.widget} {...common} placeholder={c.attrs.placeholder} maxLength={c.attrs.maxlength ? Number(c.attrs.maxlength) : undefined} max={c.attrs.max} />;
}

const AYUDA: Record<string, string> = {
  keyword: "Busca texto dentro de los diffs del evento.",
  field_name: "Filtra por nombre de campo auditado.",
  batch_key: "Agrupa o localiza un lote específico.",
};
const COLUMNAS: Record<string, string> = { keyword: "col-md-6", field_name: "col-md-3", batch_key: "col-md-3" };

function Valor({ v }: { v: Valor }) {
  return v.empty ? <em>No cargado</em> : <>{v.text}</>;
}

function FilaEvento({ f }: { f: Fila }) {
  return (
    <tr className={f.continuacion ? "table-light" : undefined}>
      <td>{f.fecha_texto}</td>
      <td><div className={f.actor_fallback ? "text-muted" : ""}>{f.actor_texto}</div></td>
      <td>
        <span className={`badge ${f.evento_clase}`}>{f.evento_texto}</span>
        {f.masiva && (f.masiva_inicio ? (
          <>{" "}<span className="badge bg-dark ms-1">Acción masiva x{f.masiva_cantidad}</span>
            <small className="text-muted d-block mt-1">Agrupado por {f.masiva_origen}</small></>
        ) : <>{" "}<span className="badge bg-light text-dark border ms-1">Mismo lote</span></>)}
        {!f.con_diffs && <>{" "}<span className="badge bg-warning text-dark ms-1">Sin diffs</span></>}
      </td>
      <td>
        {f.con_diffs ? (
          <>
            {f.cambios.map((c) => <div key={c.campo}><strong>{c.campo}</strong>: <Valor v={c.old} /> → <Valor v={c.new} /></div>)}
            {f.cambios_total > 2 && <div className="text-muted">+ {f.cambios_total - 2} más</div>}
          </>
        ) : <span className="text-muted">Sin diffs registrados</span>}
      </td>
      <td className="text-end"><a href={f.detalle_url} className="btn btn-sm btn-outline-secondary">Ver</a></td>
    </tr>
  );
}

export function HistorialContent({ data }: { data: HistorialData }) {
  const p = data.paginacion;
  const enlace = (page: number) => `?page=${page}${p.querystring ? `&${p.querystring}` : ""}`;
  return (
    <>
      <NativeToasts messages={data.messages} />
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-header"><h3 className="card-title">Filtros</h3></div>
            <div className="card-body">
              <form method="get" className="row g-3">
                {data.fields.filter((c) => !c.hidden).map((c) => (
                  <div className={COLUMNAS[c.name] ?? "col-md-3"} key={c.name}>
                    <label htmlFor={`id_${c.name}`}>{c.label}:</label>{" "}
                    <Control c={c} />
                    {AYUDA[c.name] && <small className="form-text text-muted">{AYUDA[c.name]}</small>}
                  </div>
                ))}
                {data.fields.filter((c) => c.hidden).map((c) => <input key={c.name} type="hidden" name={c.name} defaultValue={c.value} id={`id_${c.name}`} />)}
                <div className="col-md-6 align-self-end">
                  <button type="submit" className="btn btn-primary" aria-label="Aplicar filtros de auditoría">Aplicar</button>{" "}
                  <a href="." className="btn btn-outline-secondary ms-2">Limpiar</a>{" "}
                  {data.puede_exportar && <>
                    <button type="submit" name="export" value="csv" className="btn btn-outline-success ms-2">Exportar CSV</button>{" "}
                    <button type="submit" name="export" value="json" className="btn btn-outline-success ms-2">Exportar JSON</button>
                  </>}
                </div>
              </form>
              {data.has_errors && (
                <div className="alert alert-warning mt-3 mb-0">
                  {data.field_errors.map((e, i) => <div key={`f${i}`}>{e.label}: {e.message}</div>)}
                  {data.non_field_errors.map((e, i) => <div key={`n${i}`}>{e}</div>)}
                </div>
              )}
              {data.filtros_activos.length > 0 && (
                <div className="mt-3" aria-label="Resumen de filtros activos">
                  <span className="small text-muted me-2">Filtros activos:</span>{" "}
                  {data.filtros_activos.map((f) => <span key={f.label}><span className="badge bg-light text-dark border me-1 mb-1">{f.label}: {f.value}</span>{" "}</span>)}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-header"><h3 className="card-title">Eventos</h3></div>
            <div className="card-body table-responsive p-0">
              <table className="table table-hover table-striped">
                <thead><tr><th>Fecha</th><th>Usuario</th><th>Evento</th><th>Cambios</th><th /></tr></thead>
                <tbody>
                  {data.filas.length > 0 ? data.filas.map((f) => <FilaEvento key={f.id} f={f} />) : (
                    <tr><td colSpan={5} className="text-center py-4">
                      <div className="fw-semibold">No hay eventos para los filtros seleccionados.</div>
                      <div className="small text-muted mt-1">Ajustá los filtros o usá “Limpiar” para volver al listado completo.</div>
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
            {p.is_paginated && (
              <div className="card-footer clearfix">
                <ul className="pagination pagination-sm m-0 float-end">
                  {p.previous && <>
                    <li className="page-item"><a className="page-link" href={enlace(1)}>«</a></li>
                    <li className="page-item"><a className="page-link" href={enlace(p.number - 1)}>‹</a></li>
                  </>}
                  <li className="page-item disabled"><span className="page-link">Página {p.number} de {p.num_pages}</span></li>
                  {p.next && <>
                    <li className="page-item"><a className="page-link" href={enlace(p.number + 1)}>›</a></li>
                    <li className="page-item"><a className="page-link" href={enlace(p.num_pages)}>»</a></li>
                  </>}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

function HistorialPage({ app, model, pk }: { app: string; model: string; pk: string }) {
  const [state] = useMainResource(`web/auditoria/${app}/${model}/${pk}/${window.location.search}`, historialValid);
  return renderMain(state, "Cargando historial…", (data) => ({
    title: "Auditoría", activePath: "/auditoria/",
    heading: data.title,
    breadcrumb: <Breadcrumb items={[{ text: "Inicio", url: data.inicio_url }, { text: "Auditoría", url: null }]} />,
    content: <HistorialContent data={data} />,
  }));
}

const HISTORIAL = /^\/auditoria\/([a-z_]+)\/([a-z_]+)\/([^/]+)\/$/;

export const ciudadanoHistorialRoute: RouteDefinition<{ app: string; model: string; pk: string }> = {
  name: "auditoria-historial-instancia",
  match(pathname) {
    const found = HISTORIAL.exec(pathname);
    return found ? { app: found[1], model: found[2], pk: found[3] } : null;
  },
  render({ app, model, pk }) {
    return <HistorialPage app={app} model={model} pk={pk} />;
  },
};
