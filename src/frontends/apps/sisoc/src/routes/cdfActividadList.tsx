/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { useRef, useState, type FormEvent } from "react";
import { renderWithNativeToasts } from "./cdfActividades";
import { client, csrfToken, internal, messagesValid, navigation, record, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import { resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDF-B: `centros/actividadcentro_list.html` (unpaged list with the local `listSort.js` sort; the
 * view puts no title, buttons or breadcrumb items in the context, so those elements are empty, as
 * today) and `centros/actividad_form.html` (catalog: category and name). The API runs the native
 * views; a valid catalog POST follows the native redirect (no message is queued). A POST is never
 * retried.
 */
const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";

type Header = { title: string; sortable: boolean; sort_key: string };
type Fila = {
  id: number; centro: string; actividad: string; dias: string[]; dias_vacio: string; horariosdesde: string; horarioshasta: string;
  estado_display: string; urls: { detail: string };
};
export type ActividadListData = { headers: Header[]; results: Fila[]; messages: CdfMessage[] };

const filaValid = (f: unknown): f is Fila => record(f) && typeof f.id === "number" && ["centro", "actividad", "dias_vacio", "horariosdesde", "horarioshasta", "estado_display"].every((k) => text(f[k])) &&
  Array.isArray(f.dias) && f.dias.every(text) && record(f.urls) && internal(f.urls.detail);

export function listValid(v: unknown): v is ActividadListData {
  return record(v) && Array.isArray(v.headers) && v.headers.every((h) => record(h) && text(h.title) && typeof h.sortable === "boolean" && text(h.sort_key)) &&
    Array.isArray(v.results) && v.results.every(filaValid) && messagesValid(v.messages);
}

/** `listSort.js`: the value of the `data-<column>` attribute each cell carries. */
const sortValue = (f: Fila, column: string) => ({
  centro: f.centro, actividad: f.actividad, dias: f.dias.join(", "), horariosdesde: f.horariosdesde, horarioshasta: f.horarioshasta, estado: f.estado_display,
} as Record<string, string>)[column] ?? "";

function parseDateForSort(value: string): number | null {
  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(value.trim());
  if (!match) return null;
  const [day, month, year] = [Number(match[1]), Number(match[2]), Number(match[3])];
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day ? parsed.getTime() : null;
}
function compare(a: string, b: string): number {
  const ad = parseDateForSort(a), bd = parseDateForSort(b);
  if (ad !== null && bd !== null) return ad - bd;
  const an = parseFloat(a), bn = parseFloat(b);
  if (!Number.isNaN(an) && !Number.isNaN(bn) && a !== "" && b !== "") return an - bn;
  const plain = (s: string) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  return plain(a).localeCompare(plain(b), "es", { sensitivity: "base" });
}

export function ActividadListContent({ data }: { data: ActividadListData }) {
  const [rows, setRows] = useState(data.results);
  const [sort, setSort] = useState<{ column: string | null; direction: "asc" | "desc" | null }>({ column: null, direction: null });
  // `listSort.js` edits classList: a header sorted once keeps `sort-icon` before its state class.
  const [touched, setTouched] = useState<string[]>([]);

  function sortBy(column: string) {
    const direction = sort.column === column ? (sort.direction === "asc" ? "desc" : sort.direction === "desc" ? null : "asc") : "asc";
    setSort({ column: direction ? column : null, direction });
    setTouched((current) => (current.includes(column) ? current : [...current, column]));
    if (!direction) return;
    setRows((current) => [...current].sort((a, b) => {
      const value = compare(sortValue(a, column), sortValue(b, column));
      return direction === "asc" ? value : -value;
    }));
  }

  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/cdf.css" />
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <h2 className="text-center display-4 mb-4" />
      <div className="row mt-3" />
      <div className="row mt-4 cdf-page">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <div className="table-responsive">
                <table className="table table-bordered table-striped projects">
                  <thead>
                    <tr>
                      {data.headers.map((h) => (h.sortable ? (
                        <th key={h.sort_key} className={`sortable ${sort.column === h.sort_key ? `sort-${sort.direction}` : ""}`} data-column={h.sort_key} onClick={() => sortBy(h.sort_key)}>
                          {h.title}{" "}
                          <i className={sort.column === h.sort_key ? `fas sort-icon fa-sort-${sort.direction === "asc" ? "up" : "down"}`
                            : touched.includes(h.sort_key) ? "fas sort-icon fa-sort" : "fas fa-sort sort-icon"} />
                        </th>
                      ) : <th key={h.title}>{h.title}</th>))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.length ? rows.map((f) => (
                      <tr key={f.id}>
                        <td data-centro={f.centro}>{f.centro}</td>
                        <td data-actividad={f.actividad}><a href={f.urls.detail} className="text-decoration-none">{f.actividad}</a></td>
                        <td data-dias={f.dias.join(", ")}>{f.dias.length ? f.dias.join(" , ") : f.dias_vacio}</td>
                        <td data-horariosdesde={f.horariosdesde}>{f.horariosdesde}</td>
                        <td data-horarioshasta={f.horarioshasta}>{f.horarioshasta}</td>
                        <td data-estado={f.estado_display}><span className="badge badge-info">{f.estado_display}</span></td>
                      </tr>
                    )) : (
                      <tr><td colSpan={data.headers.length} className="text-center">No hay actividades registradas.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function ActividadList() {
  const state = useCdfPage(`web/cdf/actividades/${window.location.search}`, listValid);
  return renderWithNativeToasts(state, (data) => ({
    title: "Actividades",
    breadcrumb: <ol className="breadcrumb float-sm-right" />,
    content: <ActividadListContent data={data} />,
  }));
}

// --- Catalog (`centros/actividad_form.html`) ---------------------------------

type Choice = { value: string; label: string };
type CatalogField = {
  name: string; label: string; required: boolean; widget: string; value: string; attrs: Record<string, string>; choices?: Choice[];
  html: Record<string, string>;
};
export type CatalogoData = {
  fields: CatalogField[]; errors: Record<string, { message: string; code: string }[]>; non_field_errors: string[];
  urls: { cancel: string }; messages: CdfMessage[];
};

const catalogFieldValid = (f: unknown): f is CatalogField => record(f) && text(f.name) && text(f.label) && typeof f.required === "boolean" && text(f.widget) && text(f.value) &&
  record(f.attrs) && Object.values(f.attrs).every(text) && record(f.html) && Object.values(f.html).every(text) &&
  (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label))));

export function catalogoValid(v: unknown): v is CatalogoData {
  return record(v) && Array.isArray(v.fields) && v.fields.every(catalogFieldValid) && record(v.errors) &&
    Object.values(v.errors).every((l) => Array.isArray(l) && l.every((e) => record(e) && text(e.message) && text(e.code))) &&
    Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && record(v.urls) && internal(v.urls.cancel) && messagesValid(v.messages);
}

const ErrorList = ({ messages, nonfield = false }: { messages: string[]; nonfield?: boolean }) => (messages.length
  ? <ul className={`errorlist${nonfield ? " nonfield" : ""}`}>{messages.map((m, i) => <li key={i}>{m}</li>)}</ul> : null);

export function CatalogoContent({ data }: { data: CatalogoData }) {
  const [form, setForm] = useState(data);
  const [phase, setPhase] = useState<"idle" | "sending" | "uncertain">("idle");
  const sending = useRef(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current) return;
    sending.current = true;
    setPhase("sending");
    try {
      const { data: body, status } = await client.post("web/cdf/actividades/nueva/", new FormData(event.currentTarget), { validateStatus: (s: number) => s === 200 || s === 400 });
      if (status === 200 && record(body) && internal(body.url)) { navigation.assign(body.url); return; }
      if (status === 400 && catalogoValid(body)) { setForm(body); sending.current = false; setPhase("idle"); resetAfterRejectedPost(); return; }
      setPhase("uncertain");
    } catch {
      setPhase("uncertain");
    }
    sending.current = false;
  }

  return (
    <div className="container-fluid no-gutters">
      <div className="card bg-dark text-white mb-4">
        <div className="card-header bg-secondary">Nueva Actividad</div>
        <div className="card-body">
          {phase === "uncertain" && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
          <form method="post" key={JSON.stringify(form.errors) + form.non_field_errors.join()} onSubmit={(e) => void submit(e)}>
            <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
            <ErrorList messages={form.non_field_errors} nonfield />
            {form.fields.map((f) => (
              <div className="mb-3" key={f.name}>
                <label className="form-label text-white">{f.label}</label>
                {f.widget === "select" ? (
                  <select name={f.name} id={`id_${f.name}`} className={f.html.class} required={f.required || undefined} defaultValue={f.value}>
                    {(f.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                ) : (
                  <input type={f.widget} name={f.name} id={`id_${f.name}`} className={f.html.class} placeholder={f.html.placeholder} {...f.attrs}
                    required={f.required || undefined} defaultValue={f.value} />
                )}
                <ErrorList messages={(form.errors[f.name] ?? []).map((e) => e.message)} />
              </div>
            ))}
            <button type="submit" className="btn btn-outline-success" disabled={phase === "sending" || undefined}>Guardar</button>{" "}
            <a href={form.urls.cancel} className="btn btn-outline-secondary">Cancelar</a>
          </form>
        </div>
      </div>
    </div>
  );
}

function Catalogo() {
  const state = useCdfPage("web/cdf/actividades/nueva/", catalogoValid);
  return renderWithNativeToasts(state, (data) => ({ title: "Nueva Actividad", breadcrumb: null, content: <CatalogoContent data={data} /> }));
}

// Native URLs of the CDF activity list and the activity catalog form (CDF-B).
export const cdfActividadListRoute: RouteDefinition<{ catalogo: boolean }> = {
  name: "cdf-actividad-lista",
  match: (pathname) => {
    if (pathname === "/centrodefamilia/actividades/") return { catalogo: false };
    return pathname === "/centrodefamilia/actividades/nueva/" ? { catalogo: true } : null;
  },
  render: ({ catalogo }) => (catalogo ? <Catalogo /> : <ActividadList />),
};
