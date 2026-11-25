/* eslint-disable react-refresh/only-export-components -- route module: the validator and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { sameOriginTarget } from "./cdiObservaciones";
import { Alerts, Errors, FieldLabel, toasts, UNCERTAIN, type Message } from "./comedorColaboradores";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CO03.02 comedor activities: `actividad_espacio_pwa_form.html` (create and edit). Data and POSTs go through
 * `/api/web/comedores/actividades-espacio/`, which runs the native views (scoped PNUD comedor,
 * `ActividadEspacioPWAWebForm`, the shared PWA service). Several schedules are several stored activities: the
 * rows travel as the repeated `schedule_*` fields the native form reads. The category filter and the add and
 * remove row buttons do what the template's script does. A confirmed redirect is a full-page navigation.
 */
type Field = { label: string; required: boolean; value: string; errors: string[] };
type Row = { values: { dia_actividad: string; hora_inicio: string; hora_fin: string }; errors: Record<string, string> };
export type ActividadData = {
  comedor: { id: number; nombre: string; url: string };
  edit_mode: boolean;
  fields: {
    categoria: Field & { options: { value: string; label: string }[] };
    catalogo_actividad: Field;
    vigencia_actividad_meses: Field & { min: string | null };
    responsable_actividad: Field & { max_length: number | null };
  };
  non_field_errors: string[];
  activity_options: { id: number; categoria: string; actividad: string }[];
  days: { id: number; nombre: string }[];
  rows: Row[];
  messages: Message[];
  urls: { comedor: string; volver: string };
};

const API = "web/comedores/actividades-espacio/comedor/";
const fieldValid = (f: unknown): boolean => record(f) && text(f.label) && typeof f.required === "boolean" && text(f.value) && Array.isArray(f.errors) && f.errors.every(text);

export function dataValid(v: unknown): v is ActividadData {
  if (!record(v) || !record(v.comedor) || !record(v.fields) || !record(v.urls)) return false;
  const f = v.fields;
  return Number.isSafeInteger(v.comedor.id) && text(v.comedor.nombre) && internal(v.comedor.url) && typeof v.edit_mode === "boolean" &&
    fieldValid(f.categoria) && record(f.categoria) && Array.isArray(f.categoria.options) && f.categoria.options.every((o) => record(o) && text(o.value) && text(o.label)) &&
    fieldValid(f.catalogo_actividad) && fieldValid(f.vigencia_actividad_meses) && record(f.vigencia_actividad_meses) && (f.vigencia_actividad_meses.min === null || text(f.vigencia_actividad_meses.min)) &&
    fieldValid(f.responsable_actividad) && record(f.responsable_actividad) && (f.responsable_actividad.max_length === null || Number.isSafeInteger(f.responsable_actividad.max_length)) &&
    Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) &&
    Array.isArray(v.activity_options) && v.activity_options.every((o) => record(o) && Number.isSafeInteger(o.id) && text(o.categoria) && text(o.actividad)) &&
    Array.isArray(v.days) && v.days.every((d) => record(d) && Number.isSafeInteger(d.id) && text(d.nombre)) &&
    Array.isArray(v.rows) && v.rows.length > 0 && v.rows.every((r) => record(r) && record(r.values) && ["dia_actividad", "hora_inicio", "hora_fin"].every((k) => text((r.values as Record<string, unknown>)[k])) && record(r.errors) && Object.values(r.errors).every(text)) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && text(m.tags)) && internal(v.urls.comedor) && internal(v.urls.volver);
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const actividadesNavigation = { assign: (to: string) => window.location.assign(to) };

const asErrors = (list: string[]) => list.map((message) => ({ message, code: "" }));
const ERROR_STATUSES = (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403;
type RowState = Row["values"] & { key: number; errors: Record<string, string> };

function ActividadForm({ data, endpoint, rejected }: { data: ActividadData; endpoint: string; rejected: (d: ActividadData) => void }) {
  const { fields } = data;
  const [categoria, setCategoria] = useState(fields.categoria.value);
  // The template script rebuilds the select from the server-rendered selection and keeps it only inside the category.
  const [catalogo, setCatalogo] = useState(() => (data.activity_options.some((o) => o.categoria === fields.categoria.value && String(o.id) === fields.catalogo_actividad.value) ? fields.catalogo_actividad.value : ""));
  const [vigencia, setVigencia] = useState(fields.vigencia_actividad_meses.value);
  const [responsable, setResponsable] = useState(fields.responsable_actividad.value);
  const next = useRef(data.rows.length);
  const [rows, setRows] = useState<RowState[]>(() => data.rows.map((r, key) => ({ ...r.values, errors: r.errors, key })));
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState("");
  const busy = useRef(false);
  const options = data.activity_options.filter((o) => o.categoria === categoria);
  const patchRow = (key: number, patch: Partial<Row["values"]>) => setRows((all) => all.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  const aria = (errors: string[], id: string) => (errors.length ? { "aria-invalid": "true" as const, "aria-describedby": `${id}_error` } : {});
  const cls = (errors: string[], base: string) => `${base}${errors.length ? " is-invalid" : ""}`;
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    const body = new URLSearchParams();
    body.append("categoria", categoria);
    body.append("catalogo_actividad", catalogo);
    body.append("vigencia_actividad_meses", vigencia);
    for (const row of rows) body.append("schedule_dia_actividad", row.dia_actividad);
    for (const row of rows) body.append("schedule_hora_inicio", row.hora_inicio);
    for (const row of rows) body.append("schedule_hora_fin", row.hora_fin);
    body.append("responsable_actividad", responsable);
    let message = UNCERTAIN;
    try {
      const { data: response, status } = await webClient.post(endpoint, body, { validateStatus: ERROR_STATUSES });
      if (status === 400 && dataValid(response)) { rejected(response); resetAfterRejectedPost(); return; }
      const to = status < 300 && record(response) && response.ok === true ? sameOriginTarget(response.redirect) : null;
      if (to) { actividadesNavigation.assign(to); return; }
      if (status === 403 && record(response) && text(response.detail)) message = response.detail;
    } catch {
      // Network error or timeout after sending: the result is unknown.
    }
    busy.current = false; setPending(false); setUncertain(message);
  }
  const f = fields;
  return <div className="card">
    <div className="card-header font-weight-bold">{data.comedor.nombre}</div>
    <form method="post" noValidate onSubmit={(event) => void submit(event)}>
      <div className="card-body">
        {data.non_field_errors.length > 0 && <div className="alert alert-danger"><ul className="errorlist nonfield">{data.non_field_errors.map((e, i) => <li key={i}>{e}</li>)}</ul></div>}
        <div className="row">
          <div className="col-md-4">
            <div id="div_id_categoria" className="mb-3">
              <FieldLabel id="id_categoria" field={f.categoria} />{" "}
              <select name="categoria" className={cls(f.categoria.errors, "form-control select form-select")} required id="id_categoria" value={categoria}
                onChange={(e) => { setCategoria(e.target.value); setCatalogo(""); }} {...aria(f.categoria.errors, "id_categoria")}>
                {f.categoria.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>{" "}
              <Errors id="id_categoria" errors={asErrors(f.categoria.errors)} />
            </div>
          </div>
          <div className="col-md-4">
            <div id="div_id_catalogo_actividad" className="mb-3">
              <FieldLabel id="id_catalogo_actividad" field={f.catalogo_actividad} />{" "}
              <select name="catalogo_actividad" className={cls(f.catalogo_actividad.errors, "form-control select form-select")} required id="id_catalogo_actividad" value={catalogo}
                disabled={!categoria} onChange={(e) => setCatalogo(e.target.value)} {...aria(f.catalogo_actividad.errors, "id_catalogo_actividad")}>
                <option value="">Seleccionar</option>
                {options.map((o) => <option key={o.id} value={String(o.id)}>{o.actividad}</option>)}
              </select>{" "}
              <Errors id="id_catalogo_actividad" errors={asErrors(f.catalogo_actividad.errors)} />
            </div>
          </div>
          <div className="col-md-4">
            <div id="div_id_vigencia_actividad_meses" className="mb-3">
              <FieldLabel id="id_vigencia_actividad_meses" field={f.vigencia_actividad_meses} />{" "}
              <input type="number" name="vigencia_actividad_meses" className={cls(f.vigencia_actividad_meses.errors, "form-control numberinput")} min={f.vigencia_actividad_meses.min ?? undefined}
                id="id_vigencia_actividad_meses" value={vigencia} onChange={(e) => setVigencia(e.target.value)} {...aria(f.vigencia_actividad_meses.errors, "id_vigencia_actividad_meses")} />{" "}
              <Errors id="id_vigencia_actividad_meses" errors={asErrors(f.vigencia_actividad_meses.errors)} />
            </div>
          </div>
        </div>
        <div className="mb-3">
          <div className="d-flex justify-content-between align-items-center mb-2">
            <label className="font-weight-bold mb-0">Dias y horarios</label>
            <button type="button" className="btn btn-outline-primary btn-sm" id="add-schedule-row"
              onClick={() => setRows((all) => [...all, { dia_actividad: "", hora_inicio: "", hora_fin: "", errors: {}, key: next.current++ }])}>
              <i className="fas fa-plus" aria-hidden="true" /> Agregar horario
            </button>
          </div>
          <div id="schedule-rows">
            {rows.map((row) => {
              const errors = row.errors;
              return <div key={row.key} className="schedule-row border rounded p-3 mb-2">
                <div className="row align-items-start">
                  <div className="col-md-4">
                    <label className="form-label">Dia</label>{" "}
                    <select name="schedule_dia_actividad" className="form-control" value={row.dia_actividad} onChange={(e) => patchRow(row.key, { dia_actividad: e.target.value })}>
                      <option value="">Seleccionar</option>
                      {data.days.map((day) => <option key={day.id} value={String(day.id)}>{day.nombre}</option>)}
                    </select>
                    {errors.dia_actividad && <div className="invalid-feedback d-block">{errors.dia_actividad}</div>}
                  </div>
                  <div className="col-md-3">
                    <label className="form-label">Hora inicio</label>{" "}
                    <input type="time" name="schedule_hora_inicio" className="form-control" value={row.hora_inicio} onChange={(e) => patchRow(row.key, { hora_inicio: e.target.value })} />
                    {errors.hora_inicio && <div className="invalid-feedback d-block">{errors.hora_inicio}</div>}
                  </div>
                  <div className="col-md-3">
                    <label className="form-label">Hora fin</label>{" "}
                    <input type="time" name="schedule_hora_fin" className="form-control" value={row.hora_fin} onChange={(e) => patchRow(row.key, { hora_fin: e.target.value })} />
                    {errors.hora_fin && <div className="invalid-feedback d-block">{errors.hora_fin}</div>}
                  </div>
                  <div className="col-md-2 pt-md-4 mt-2 mt-md-0 text-md-right">
                    <button type="button" className="btn btn-outline-danger btn-sm remove-schedule-row" disabled={rows.length <= 1}
                      onClick={() => setRows((all) => all.filter((r) => r.key !== row.key))}>
                      <i className="fas fa-trash" aria-hidden="true" /> Quitar
                    </button>
                  </div>
                </div>
              </div>;
            })}
          </div>
        </div>
        <div className="row">
          <div className="col-md-12">
            <div id="div_id_responsable_actividad" className="mb-3">
              <FieldLabel id="id_responsable_actividad" field={f.responsable_actividad} />{" "}
              <input type="text" name="responsable_actividad" className={cls(f.responsable_actividad.errors, "form-control textinput")} maxLength={f.responsable_actividad.max_length ?? undefined}
                id="id_responsable_actividad" value={responsable} onChange={(e) => setResponsable(e.target.value)} {...aria(f.responsable_actividad.errors, "id_responsable_actividad")} />{" "}
              <Errors id="id_responsable_actividad" errors={asErrors(f.responsable_actividad.errors)} />
            </div>
          </div>
        </div>
        {uncertain && <p role="alert" className="mb-0">{uncertain}</p>}
      </div>
      <div className="card-footer d-flex justify-content-between">
        <a href={data.urls.volver} className="btn btn-outline-secondary">Volver</a>{" "}
        <button type="submit" className="btn btn-primary" disabled={pending || !!uncertain}>{data.edit_mode ? "Actualizar actividad" : "Guardar actividad"}</button>
      </div>
    </form>
  </div>;
}

function Content({ initial, endpoint }: { initial: ActividadData; endpoint: string }) {
  const [state, setState] = useState({ data: initial, revision: 0 });
  const { data, revision } = state;
  return <div className="container">
    <h2 className="text-center display-4 mb-4">{data.edit_mode ? "Editar actividad del espacio" : "Agregar actividad del espacio"}</h2>
    <Alerts key={revision} messages={data.messages} />
    <NativeToasts key={`t${revision}`} messages={toasts(data.messages)} />
    <ActividadForm key={revision} data={data} endpoint={endpoint} rejected={(response) => setState((s) => ({ data: response, revision: s.revision + 1 }))} />
  </div>;
}

function Page({ endpoint }: { endpoint: string }) {
  const [state] = useMainResource(endpoint, dataValid);
  return renderMain(state, "Cargando actividad…", (data) => {
    const label = data.edit_mode ? "Editar actividad" : "Agregar actividad";
    return {
      title: label,
      heading: "",
      breadcrumb: <ol className="breadcrumb float-sm-right">
        <li className="breadcrumb-item"><a href={data.urls.comedor}>Comedor</a></li>
        <li className="breadcrumb-item active">{label}</li>
      </ol>,
      content: <Content initial={data} endpoint={endpoint} />,
    };
  });
}

type Params = { page: "create"; comedor: string } | { page: "edit"; comedor: string; pk: string };

// Native URLs of `comedores/urls.py`, with their trailing slashes.
const CREATE = /^\/comedores\/(\d+)\/actividades\/crear\/$/;
const EDIT = /^\/comedores\/(\d+)\/actividades\/(\d+)\/editar\/$/;

export const comedorActividadesRoute: RouteDefinition<Params> = {
  name: "comedores-actividades",
  match(pathname) {
    const create = CREATE.exec(pathname);
    if (create) return { page: "create", comedor: create[1] };
    const edit = EDIT.exec(pathname);
    return edit ? { page: "edit", comedor: edit[1], pk: edit[2] } : null;
  },
  render(params) {
    if (params.page === "create") return <Page key={`c${params.comedor}`} endpoint={`${API}${params.comedor}/crear/`} />;
    return <Page key={`e${params.pk}`} endpoint={`${API}${params.comedor}/${params.pk}/editar/`} />;
  },
};
