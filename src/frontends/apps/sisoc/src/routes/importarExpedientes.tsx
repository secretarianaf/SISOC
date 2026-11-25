/* eslint-disable react-refresh/only-export-components -- route module: validators and the navigation seam are exported for the tests. */
import { useCallback, useEffect, useRef, useState, type FormEvent, type MouseEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { Filters, Pagination, filtersConfigValid, type Favorites, type FiltersConfig } from "./listControls";
import { accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * EX02: `importarexpediente_list.html`, `importarexpediente_detail.html`, `upload.html` and
 * `importarexpediente_acreditacion_upload.html`. The API under `/api/web/comedores/importarexpedientes/` runs the native
 * views; the import, the validation and the physical delete are the native synchronous code. Messages queued by a native redirect are
 * shown by the destination list; a rejection that stays on the form comes back in the body. A POST is never retried.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Page = { is_paginated: boolean; number: number; num_pages: number; count: number; previous: number | null; next: number | null; range: (number | string)[]; query_without_page: string };
type Row = {
  id: number; numero_expediente_pago: string; archivo: string; periodo_pago: string; periodo_orden: string; usuario: string; fecha_subida: string;
  count_exitos: string; count_errores: string; importacion_completada: string; detail_url: string; download_url: string;
};
export type ListData = { filters_config: FiltersConfig; favorites: Favorites; urls: { list: string; upload: string }; results: Row[]; page: Page; messages: Message[] };
type ErrorRow = { id: number; batch_id: number; fila: string; mensaje: string; archivo: string; detail_url: string };
export type DetailData = {
  batch: { id: number; label: string; importacion_completada: boolean }; counts: { validos: number; errores: number; con_acreditacion: number };
  can_update_acreditacion: boolean; urls: { list: string; ajax: string }; query: string; results: ErrorRow[]; page: Page; messages: Message[];
};
type Field = { name: string; label: string; type: "file" | "select" | "checkbox"; required: boolean; accept: string; choices?: { value: string; label: string }[]; value?: string | boolean };
export type UploadData = { fields: Field[]; list_url: string; messages: Message[] };
export type DatesData = { batch: { id: number; label: string }; fields: Field[]; list_url: string; messages: Message[] };

const API = "web/comedores/importarexpedientes/";
const LIST = "/importarexpedientes/listar";
const LEVELS = ["success", "error", "warning", "info"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const messagesValid = (v: unknown): v is Message[] => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
const pageValid = (v: unknown): v is Page => record(v) && typeof v.is_paginated === "boolean" && int(v.number) && int(v.num_pages) && int(v.count) &&
  (v.previous === null || int(v.previous)) && (v.next === null || int(v.next)) && text(v.query_without_page) &&
  Array.isArray(v.range) && v.range.every((n) => int(n) || text(n));
const fieldValid = (f: unknown): f is Field => record(f) && text(f.name) && text(f.label) && ["file", "select", "checkbox"].includes(f.type as string) &&
  typeof f.required === "boolean" && text(f.accept) && (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && text(c.value) && text(c.label))));

export function listValid(v: unknown): v is ListData {
  return record(v) && filtersConfigValid(v.filters_config) && record(v.favorites) && text(v.favorites.section) && internal(v.favorites.url) &&
    internal(v.favorites.detail_url_template) && record(v.urls) && internal(v.urls.list) && internal(v.urls.upload) && pageValid(v.page) && messagesValid(v.messages) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && int(r.id) && internal(r.detail_url) && internal(r.download_url) &&
      ["numero_expediente_pago", "archivo", "periodo_pago", "periodo_orden", "usuario", "fecha_subida", "count_exitos", "count_errores", "importacion_completada"].every((k) => text(r[k])));
}
export function detailValid(v: unknown): v is DetailData {
  return record(v) && record(v.batch) && int(v.batch.id) && text(v.batch.label) && typeof v.batch.importacion_completada === "boolean" &&
    record(v.counts) && int(v.counts.validos) && int(v.counts.errores) && int(v.counts.con_acreditacion) && typeof v.can_update_acreditacion === "boolean" &&
    record(v.urls) && internal(v.urls.list) && internal(v.urls.ajax) && text(v.query) && pageValid(v.page) && messagesValid(v.messages) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && int(r.id) && int(r.batch_id) && text(r.fila) && text(r.mensaje) && text(r.archivo) && internal(r.detail_url));
}
export function uploadValid(v: unknown): v is UploadData {
  return record(v) && Array.isArray(v.fields) && v.fields.every(fieldValid) && internal(v.list_url) && messagesValid(v.messages);
}
export function datesValid(v: unknown): v is DatesData {
  return record(v) && record(v.batch) && int(v.batch.id) && text(v.batch.label) && Array.isArray(v.fields) && v.fields.every(fieldValid) && internal(v.list_url) && messagesValid(v.messages);
}

/** Full-page navigation after a native redirect; replaceable in tests. */
export const importarExpedientesNavigation = { assign: (to: string) => window.location.assign(to) };

const Migas = ({ actual }: { actual: string }) => (
  <ol className="breadcrumb float-sm-right">
    <li className="breadcrumb-item"><a href={LIST}>Importar Expedientes</a></li>
    <li className="breadcrumb-item active">{actual}</li>
  </ol>
);

// --- `listSort.js`: client sort of the visible page --------------------------

function parseDateForSort(value: string): number | null {
  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(value.trim());
  if (!match) return null;
  const [day, month, year] = [Number(match[1]), Number(match[2]), Number(match[3])];
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day ? parsed.getTime() : null;
}
const plain = (s: string) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

/** `cells`: the text of each cell; `attr`: the `data-<column>` value of the first cell that carries it (empty here but for the period). */
function sortRows<T>(rows: T[], columns: string[], column: string, direction: "asc" | "desc", cells: (r: T) => string[], attr: (r: T, column: string) => string): T[] {
  const index = columns.indexOf(column);
  return [...rows].sort((a, b) => {
    let av = attr(a, column), bv = attr(b, column);
    if (av === "" && bv === "") { av = cells(a)[index]?.trim() ?? ""; bv = cells(b)[index]?.trim() ?? ""; }
    let an = parseDateForSort(av), bn = parseDateForSort(bv), numeric = an !== null && bn !== null;
    if (!numeric) {
      an = parseFloat(av); bn = parseFloat(bv);
      numeric = !Number.isNaN(an) && !Number.isNaN(bn) && av !== "" && bv !== "";
    }
    const order = numeric ? (an as number) - (bn as number) : plain(av).localeCompare(plain(bv), "es", { sensitivity: "base" });
    return direction === "asc" ? order : -order;
  });
}

function useSort<T>(rows: T[], columns: string[], cells: (r: T) => string[], attr: (r: T, c: string) => string) {
  type View = { source: T[]; shown: T[]; column: string | null; direction: "asc" | "desc" | null };
  const [stored, setStored] = useState<View>({ source: rows, shown: rows, column: null, direction: null });
  const [touched, setTouched] = useState<string[]>([]);
  // A new page of rows (a search) starts unsorted, like the replaced tbody.
  const view: View = stored.source === rows ? stored : { source: rows, shown: rows, column: null, direction: null };
  const sortBy = (column: string) => {
    const direction = view.column === column ? (view.direction === "asc" ? "desc" : view.direction === "desc" ? null : "asc") : "asc";
    setTouched((current) => (current.includes(column) ? current : [...current, column]));
    setStored({ source: rows, shown: direction ? sortRows(view.shown, columns, column, direction, cells, attr) : view.shown, column: direction ? column : null, direction });
  };
  const header = (column: string, index: number, title: string) => {
    const active = view.column === column;
    const icon = active ? `fas sort-icon fa-sort-${view.direction === "asc" ? "up" : "down"}`
      : touched.includes(column) ? "fas sort-icon fa-sort" : "fas fa-sort sort-icon";
    return <th key={index} className={`sortable${active && view.direction ? ` sort-${view.direction}` : ""}`} data-column={column} onClick={() => sortBy(column)}>
      {title}
      <i className={icon} />
    </th>;
  };
  return { shown: view.shown, header };
}

// --- List --------------------------------------------------------------------

const LIST_COLUMNS = ["numero_expediente_pago", "nombre", "periodo_pago", "cuit", "telefono", "email", "email", "email"];
const LIST_TITLES = ["Nº Expediente de Pago", "Archivo", "Periodo", "Usuario", "Fecha de Subida", "Válidos", "Errores", "Importacion Completada"];
const listCells = (r: Row) => [r.numero_expediente_pago, r.archivo, r.periodo_pago, r.usuario, r.fecha_subida, r.count_exitos, r.count_errores, r.importacion_completada];

export function ListContent({ data }: { data: ListData }) {
  const { shown, header } = useSort(data.results, LIST_COLUMNS, listCells, (r, c) => (c === "periodo_pago" ? r.periodo_orden : ""));
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
      <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
      <NativeToasts messages={data.messages} />
      <h2 className="text-center mb-4 poncho-titulo">Buscar Expedientes de Pago</h2>
      <Filters config={data.filters_config} action={data.urls.list} favorites={data.favorites} />
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={LIST} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
        </div>
      </div>
      <div className="row mt-4 max-width-100">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <table className="table table-bordered table-striped projects">
                <thead>
                  <tr>
                    {LIST_COLUMNS.map((c, i) => header(c, i, LIST_TITLES[i]))}
                    <th style={{ width: "15%" }} className="notexport">Acciones</th>
                  </tr>
                </thead>
                <tbody id="importarexpedientes-tbody">
                  {shown.length ? shown.map((r) => (
                    <tr key={r.id}>
                      <td>{r.numero_expediente_pago}</td>
                      <td><a href={r.detail_url} className="font-weight-bold link-handler" title="Ver detalles">{r.archivo}</a></td>
                      <td data-periodo={r.periodo_orden}>{r.periodo_pago}</td>
                      <td>{r.usuario}</td>
                      <td>{r.fecha_subida}</td>
                      <td>{r.count_exitos}</td>
                      <td>{r.count_errores}</td>
                      <td>{r.importacion_completada}</td>
                      <td className="project-actions text-right">
                        <div className="action-buttons" role="group">
                          <a href={r.detail_url} className="btn btn-primary link-handler" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
                          <a href={r.download_url} className="btn btn-secondary" title="Descargar archivo adjunto"><i className="fas fa-download" />{" "}Descargar</a>
                        </div>
                      </td>
                    </tr>
                  )) : <tr><td colSpan={9} className="text-center text-muted py-4">No hay expedientes disponibles.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      <div id="pagination-container">
        <Pagination paginated={data.page.is_paginated} number={data.page.number} previous={data.page.previous} next={data.page.next} range={data.page.range}
          href={(n) => `?${data.page.query_without_page}page=${n}`} count={shown.length ? data.page.count : null} />
      </div>
    </>
  );
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, listValid);
  return renderMain(state, "Cargando lotes…", (data) => ({
    title: "Importar Expedientes", breadcrumb: <Migas actual="Listar" />, content: <ListContent data={data} />,
    appHeader: (
      <div className="row g-2 align-items-center">
        <div className="col-12 col-lg d-flex flex-wrap justify-content-start justify-content-lg-end gap-2 align-items-center">
          <a href={data.urls.upload} className="btn btn-md btn-primary" title="Importar Nuevo Archivo"><i className="fas fa-upload me-1" />Importar Nuevo Archivo</a>
        </div>
      </div>
    ),
  }));
}

// --- Detail ------------------------------------------------------------------

const UNCERTAIN = "No se pudo confirmar el resultado. Revise el listado de lotes antes de volver a intentar.";
const DETAIL_COLUMNS = ["nombre", "telefono", "email"];

/** The two native `data-confirm-click` forms: confirm, post once, follow the native redirect. */
function ActionButton({ endpoint, confirm, className, icon, label, title, busy, setBusy, setError }: {
  endpoint: string; confirm: string; className: string; icon: string; label: string; title: string; busy: boolean; setBusy: (b: boolean) => void; setError: (e: string) => void;
}) {
  const lock = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (lock.current || !window.confirm(confirm)) return;
    lock.current = true; setBusy(true); setError("");
    try {
      const { data, status } = await webClient.post(endpoint, new URLSearchParams(), { validateStatus: (s: number) => accepted(s) || [400, 409, 500].includes(s) });
      if (record(data) && internal(data.redirect) && [200, 400, 409, 500].includes(status)) { importarExpedientesNavigation.assign(data.redirect); return; }
      setError(status === 403 && record(data) && text(data.detail) ? data.detail : UNCERTAIN);
    } catch { setError(UNCERTAIN); }
    lock.current = false; setBusy(false);
  }
  return (
    <form method="post" action="" className="d-inline" onSubmit={(e) => void submit(e)}>
      <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
      <button type="submit" className={className} title={title} disabled={busy}><i className={`${icon} me-1`} />{label}</button>
    </form>
  );
}

function DetailHeader({ data, setError }: { data: DetailData; setError: (e: string) => void }) {
  const [busy, setBusy] = useState(false);
  const id = data.batch.id;
  return (
    <div className="row g-2 align-items-center">
      <div className="col-12 col-lg d-flex flex-wrap justify-content-start justify-content-lg-end gap-2 align-items-center">
        <ActionButton endpoint={`${API}${id}/importar/`} confirm="¿Confirmar importación del lote?" className="btn btn-md btn-primary" icon="fas fa-upload" label="Completar Importación" title="Importar datos" busy={busy} setBusy={setBusy} setError={setError} />
        {" "}
        {data.can_update_acreditacion && <><a href={`/importarexpedientes/${id}/fechas-acreditacion/`} className="btn btn-md btn-primary" title="Actualizar fechas de acreditación"><i className="fas fa-calendar-check me-1" />Actualizar fechas de acreditación</a>{" "}</>}
        <ActionButton endpoint={`${API}${id}/borrar-datos/`} confirm="¿Confirmar borrado de datos importados del lote?" className="btn btn-md btn-danger" icon="fas fa-trash" label="Eliminar Archivo" title="Borrar datos" busy={busy} setBusy={setBusy} setError={setError} />
      </div>
    </div>
  );
}

function Counter({ color, title, value, strong }: { color: string; title: string; value: number; strong?: string }) {
  return (
    <div className="card mb-0" style={{ borderLeft: `4px solid ${color}` }}>
      <div className="card-body py-2 px-3">
        <small className="text-muted d-block">{title}</small>
        <span className={`fw-semibold fs-4${strong ? ` ${strong}` : ""}`}>{value}</span>
      </div>
    </div>
  );
}

export function DetailContent({ initial, error }: { initial: DetailData; error: string }) {
  const [data, setData] = useState(initial);
  const [consulta, setConsulta] = useState(initial.query);
  const [termino, setTermino] = useState(initial.query);
  const [cargando, setCargando] = useState(false);
  const [fallo, setFallo] = useState(false);
  const [consultada, setConsultada] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const control = useRef<AbortController>(undefined);
  const buscar = useCallback((query: string, page = 1) => {
    setTermino(query); setConsultada(true);
    control.current?.abort();
    const controller = new AbortController();
    control.current = controller;
    setCargando(true);
    const params = new URLSearchParams({ busqueda: query });
    if (page > 1) params.set("page", String(page));
    webClient.get(`${API}${initial.batch.id}/?${params}`, { signal: controller.signal, validateStatus: accepted }).then(({ data: body, status }: { data: unknown; status?: number }) => {
      if (controller.signal.aborted) return;
      if (status !== 200 || !detailValid(body)) throw new Error("invalid");
      setData((current) => ({ ...current, results: body.results, page: body.page }));
      setFallo(false); setCargando(false);
    }).catch(() => { if (!controller.signal.aborted) { setFallo(true); setCargando(false); } });
  }, [initial.batch.id]);
  useEffect(() => {
    // Native script: an initial value runs the search once on load.
    const start = initial.query.trim() ? setTimeout(() => buscar(initial.query.trim()), 0) : undefined;
    return () => { clearTimeout(start); clearTimeout(timer.current); control.current?.abort(); };
  }, [initial.query, buscar]);
  const cells = useCallback((r: ErrorRow) => [r.archivo, r.fila, r.mensaje], []);
  const none = useCallback(() => "", []);
  const { shown, header } = useSort(data.results, DETAIL_COLUMNS, cells, none);
  const onPagination = (e: MouseEvent<HTMLDivElement>) => {
    const link = (e.target as HTMLElement).closest<HTMLAnchorElement>('a[href*="page="]');
    if (!link) return;
    e.preventDefault();
    buscar(termino, Number(new URL(link.href).searchParams.get("page")) || 1);
  };
  const page = data.page;
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/cardsDetail.css" />
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
      <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
      <NativeToasts messages={[...data.messages, ...(error ? [{ message: error, level: "error" as const }] : [])]} />
      <div className="d-flex flex-wrap gap-3 mb-4">
        <Counter color="#198754" title="Registros Válidos" value={data.counts.validos} strong="text-success" />
        <Counter color="#dc3545" title="Registros con Errores" value={data.counts.errores} strong="text-danger" />
        <Counter color="#6f42c1" title="Con Acreditación" value={data.counts.con_acreditacion} />
      </div>
      <h2 className="text-center mb-4 poncho-titulo">Buscar Errores</h2>
      <div className="poncho-search poncho-search--solo">
        <div className="poncho-search__box">
          <input type="search" id="ajax-search-input" className="poncho-search__input" placeholder="Buscar por Fila" title="Ingresar una Fila." autoComplete="off" aria-label="Ingresar una Fila."
            value={consulta}
            onChange={(e) => { const v = e.target.value; setConsulta(v); clearTimeout(timer.current); timer.current = setTimeout(() => buscar(v.trim()), 300); }}
            onKeyDown={(e) => { if (e.key === "Escape") { clearTimeout(timer.current); setConsulta(""); buscar(""); } }} />
          <button type="button" id="ajax-search-go" className="poncho-search__go" aria-label="Buscar" onClick={() => { clearTimeout(timer.current); buscar(consulta.trim()); }}>
            <i className="fas fa-search" aria-hidden="true" />
          </button>
        </div>
      </div>
      <div className="poncho-search__meta"><span id="ajax-results-count">{consultada && termino.trim() ? `${data.page.count} resultado(s) encontrado(s)` : ""}</span></div>
      <div id="ajax-loading-indicator" className="text-center py-3" style={{ display: cargando ? "block" : "none" }}>
        <div className="spinner-border" role="status"><span className="sr-only">Cargando...</span></div>
      </div>
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={initial.urls.list} className="poncho-btn poncho-btn--neutro">Resetear</a>
        </div>
      </div>
      <div className="row mt-4 max-width-100">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <table className="table table-bordered table-striped projects">
                <thead><tr>{DETAIL_COLUMNS.map((c, i) => header(c, i, ["Archivo", "Fila", "Error"][i]))}</tr></thead>
                <tbody id="importarexpedientes-tbody" style={{ opacity: cargando ? 0.5 : 1 }}>
                  {fallo ? <tr><td colSpan={3} className="text-center text-danger py-4">Error al cargar los datos. Intente nuevamente.</td></tr>
                    : shown.length ? shown.map((r) => (
                      <tr key={r.id}>
                        <td><a href={r.detail_url} className="font-weight-bold link-handler" title="Ver detalles">{r.archivo}</a></td>
                        <td>{r.fila}</td>
                        <td>
                          <div className="alert alert-danger py-1 px-2 mb-0 d-inline-flex align-items-center" role="alert">
                            <i className="fas fa-exclamation-circle mr-2" aria-hidden="true" />
                            <span>{r.mensaje}</span>
                          </div>
                        </td>
                      </tr>
                    )) : <tr><td colSpan={5} className="text-center text-muted py-4">No hay errores registrados para este archivo.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      <div id="pagination-container" onClick={onPagination}>
        <Pagination paginated={page.is_paginated} number={page.number} previous={page.previous} next={page.next} range={page.range} count={shown.length ? page.count : null}
          href={(n) => `?${termino ? `busqueda=${encodeURIComponent(termino)}&` : ""}${page.query_without_page}page=${n}`} />
      </div>
    </>
  );
}

function DetailPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/${window.location.search}`, detailValid);
  const [error, setError] = useState("");
  return renderMain(state, "Cargando lote…", (data) => ({
    title: "Importar Expedientes - Detalle", breadcrumb: <Migas actual="Detalle" />, content: <DetailContent initial={data} error={error} />,
    appHeader: <DetailHeader data={data} setError={setError} />,
  }));
}

// --- Upload and accreditation dates (crispy markup) ----------------------------

/** `upload.html` icons the alert; `importarexpediente_acreditacion_upload.html` prints the text only (and its error class is `alert-error`). */
function Alerts({ messages, close, icons }: { messages: Message[]; close: (i: number) => void; icons: boolean }) {
  if (!messages.length) return null;
  return (
    <div className="mb-3">
      {messages.map((m, i) => {
        const error = icons && m.level === "error";
        const tag = icons && error ? "danger" : m.level;
        return (
          <div key={i} className={`alert alert-${tag} alert-dismissible fade show${error ? " d-flex align-items-center" : ""}`} role="alert">
            {icons ? <><i className={`fas ${error ? "fa-exclamation-circle" : "fa-info-circle"} mr-2`} aria-hidden="true" /><span>{m.message}</span></> : <>{m.message}{" "}</>}
            <button type="button" className="btn-close" aria-label="Close" onClick={() => close(i)} />
          </div>
        );
      })}
    </div>
  );
}

function CrispyFields({ fields, fileKey }: { fields: Field[]; fileKey: number }) {
  return (
    <>
      {fields.map((f) => {
        const id = `id_${f.name}`;
        if (f.type === "checkbox") {
          return <div key={f.name} className="mb-3"><div id={`div_${id}`} className="form-check">
            <input type="checkbox" name={f.name} className="checkboxinput form-check-input" id={id} defaultChecked={f.value === true} />{" "}
            <label htmlFor={id} className="form-check-label">{f.label}</label>
          </div></div>;
        }
        const label = <label htmlFor={id} className="form-label requiredField">{f.label}<span className="asteriskField">*</span></label>;
        return <div key={f.name} id={`div_${id}`} className="mb-3">
          {label}{" "}
          {f.type === "file"
            ? <div><input key={fileKey} type="file" name={f.name} className="form-control" accept={f.accept} id={id} required />{" "}</div>
            : <><select name={f.name} className="select form-select" id={id} defaultValue={String(f.value ?? "")}>
              {(f.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>{" "}</>}
        </div>;
      })}
    </>
  );
}

/** `busyLabel` marks the upload page: its rejected POST is a redirect (alerts and toast); the dates page re-renders (alerts above its notice); both also raise the layout toast. */
function UploadForm({ fields, endpoint, initial, busyLabel, submit, notice }: { fields: Field[]; endpoint: string; initial: Message[]; busyLabel?: boolean; submit: ReactNode; notice?: ReactNode }) {
  const [messages, setMessages] = useState(initial);
  const [fileKey, setFileKey] = useState(0);
  const [pending, setPending] = useState(false);
  const busy = useRef(false);
  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setPending(true);
    try {
      const { data, status } = await webClient.post(endpoint, new FormData(event.currentTarget), { validateStatus: (s: number) => accepted(s) || [400, 409, 415].includes(s) });
      if (record(data) && data.ok === true && internal(data.redirect)) { importarExpedientesNavigation.assign(data.redirect); return; }
      if ([400, 409].includes(status) && record(data) && messagesValid(data.messages)) {
        setMessages(data.messages); setFileKey((k) => k + 1); resetAfterRejectedPost();
      } else setMessages([{ level: "error", message: status === 403 && record(data) && text(data.detail) ? data.detail : UNCERTAIN }]);
    } catch { setMessages([{ level: "error", message: UNCERTAIN }]); }
    busy.current = false; setPending(false);
  }
  return (
    <>
      <NativeToasts messages={messages} />
      <Alerts messages={messages} icons={Boolean(busyLabel)} close={(i) => setMessages((m) => m.filter((_, j) => j !== i))} />
      {notice}
      <form id={busyLabel ? "csv-upload-form" : undefined} method="post" encType="multipart/form-data" onSubmit={(e) => void send(e)}>
        <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
        <CrispyFields fields={fields} fileKey={fileKey} />
        {busyLabel ? <button id="csv-upload-btn" className={`btn btn-primary${pending ? " disabled" : ""}`} type="submit" disabled={pending}>
          {pending ? <><span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" /> Procesando…</> : "Importar"}
        </button> : <button className="btn btn-primary" type="submit" disabled={pending}>{submit}</button>}
      </form>
    </>
  );
}

function UploadPage() {
  const [state] = useMainResource(`${API}subir/`, uploadValid);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: "Importar Expedientes desde CSV o XLSX", breadcrumb: <Migas actual="Importar Archivo" />,
    content: (
      <div className="container-fluid"><div className="card">
        <div className="card-header"><h3 className="card-title">Importar Expedientes desde CSV o XLSX</h3></div>
        <div className="card-body"><UploadForm fields={data.fields} endpoint={`${API}subir/`} initial={data.messages} busyLabel submit={null} /></div>
      </div></div>
    ),
  }));
}

function DatesPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/fechas-acreditacion/`, datesValid);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: "Actualizar fechas de acreditación", breadcrumb: <Migas actual="Fechas de acreditación" />,
    content: (
      <div className="container-fluid"><div className="card">
        <div className="card-header"><h3 className="card-title">Actualizar fechas de acreditación</h3></div>
        <div className="card-body">
          <UploadForm fields={data.fields} endpoint={`${API}${id}/fechas-acreditacion/`} initial={data.messages}
            notice={
            <div className="alert alert-info">
            El archivo debe ser CSV o XLSX y contener las columnas <strong>ID</strong> y{" "}
            <strong>Fecha de Acreditación</strong>. La fecha debe cargarse con
            formato <strong>DD/MM/AAAA</strong>. Todas las filas deben informar la
            misma fecha; solo se actualizarán los expedientes de los comedores
            informados en el archivo.
          </div>
            }
            submit={<><i className="fas fa-calendar-check me-1" />Actualizar fechas</>} />
        </div>
      </div></div>
    ),
  }));
}

type Params = { kind: "list" | "detail" | "upload" | "dates"; id: string };
const DETAIL = /^\/importarexpedientes\/([0-9]+)\/(fechas-acreditacion\/)?$/;

export const importarExpedientesRoute: RouteDefinition<Params> = {
  name: "comedores-importar-expedientes",
  match(pathname) {
    if (pathname === LIST) return { kind: "list", id: "" };
    if (pathname === "/importarexpedientes/upload") return { kind: "upload", id: "" };
    const found = DETAIL.exec(pathname);
    return found ? { kind: found[2] ? "dates" : "detail", id: found[1] } : null;
  },
  render({ kind, id }) {
    if (kind === "list") return <ListPage key="list" />;
    if (kind === "upload") return <UploadPage key="upload" />;
    if (kind === "dates") return <DatesPage key={`dates:${id}`} id={id} />;
    return <DetailPage key={`detail:${id}`} id={id} />;
  },
};
