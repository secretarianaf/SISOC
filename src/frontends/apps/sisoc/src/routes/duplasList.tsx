/* eslint-disable react-refresh/only-export-components -- the list screen exports its validator and navigation seam for the unit tests. */
import { useCallback, useEffect, useRef, useState } from "react";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { useLegacyScrollHints } from "../useLegacyScrollHints";
import { safeInternalPath } from "../webAccess";
import { API, integer, messagesValid, record, renderDuplas, text, useDuplasResource, type Message } from "./duplasShared";

/**
 * `dupla_list.html`: `search_bar.html` in filters mode (`advanced_filters.js`),
 * `data_table.html` with column preferences (`column_config.js`) and client
 * sorting (`listSort.js`), `pagination.html` and the CSV button
 * (`export_helper.js`, native GET).
 */
type FilterField = { name: string; label: string; type: string; input?: { step?: string; min?: string; max?: string } };
type FiltersConfig = { fields: FilterField[]; defaultOperators?: Record<string, string>; defaultField?: string };
type Column = { key: string; title: string; active: boolean; required: boolean; default: boolean };
type Columns = { list_key: string; endpoint: string; modal_id: string; script_id: string; available: Column[]; active: string[]; defaults: string[] };
type Header = { title: string; sortable: boolean; sort_key: string };
type Action = { label: string; url: string; type: string; icon: string };
type Row = { id: number; cells: string[]; actions: Action[] };
type Page = { is_paginated: boolean; number: number; count: number; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };
export type DuplasListData = {
  breadcrumb: { text: string; url: string | null }[];
  filters_config: FiltersConfig;
  favorites: { section: string; url: string; detail_url_template: string };
  urls: { list: string; reset: string; add: string; export: string };
  can_export: boolean;
  columns: Columns;
  headers: Header[];
  results: Row[];
  page: Page;
  messages: Message[];
};

const internal = (v: unknown) => safeInternalPath(v) !== null;

export function listValid(v: unknown): v is DuplasListData {
  if (!record(v) || !record(v.filters_config) || !record(v.favorites) || !record(v.urls) || !record(v.columns) || !record(v.page)) return false;
  const f = v.filters_config, c = v.columns, p = v.page, u = v.urls;
  return Array.isArray(v.breadcrumb) && v.breadcrumb.every((b) => record(b) && text(b.text) && (b.url === null || internal(b.url))) &&
    Array.isArray(f.fields) && f.fields.length > 0 && f.fields.every((x) => record(x) && text(x.name) && text(x.label) && text(x.type)) &&
    text(v.favorites.section) && internal(v.favorites.url) && internal(v.favorites.detail_url_template) &&
    ["list", "reset", "add", "export"].every((k) => internal(u[k])) && typeof v.can_export === "boolean" &&
    text(c.list_key) && internal(c.endpoint) && text(c.modal_id) && text(c.script_id) &&
    Array.isArray(c.available) && c.available.every((x) => record(x) && text(x.key) && text(x.title) && typeof x.active === "boolean" && typeof x.required === "boolean") &&
    Array.isArray(c.active) && c.active.every(text) && Array.isArray(c.defaults) && c.defaults.every(text) &&
    Array.isArray(v.headers) && v.headers.every((h) => record(h) && text(h.title) && typeof h.sortable === "boolean" && text(h.sort_key)) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && integer(r.id) && Array.isArray(r.cells) && r.cells.every(text) &&
      Array.isArray(r.actions) && r.actions.every((a) => record(a) && text(a.label) && internal(a.url) && text(a.type) && text(a.icon))) &&
    typeof p.is_paginated === "boolean" && ["number", "count"].every((k) => integer(p[k])) &&
    (p.previous === null || integer(p.previous)) && (p.next === null || integer(p.next)) &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || integer(n)) && text(p.query_without_page) && messagesValid(v.messages);
}

/** Full-page navigation (export, reload); replaceable in tests. */
export const duplasNavigation = {
  assign: (to: string) => window.location.assign(to),
  reload: () => window.location.reload(),
};

// --- Filters (`advanced_filters.js`) ---------------------------------------

type FilterRow = { key: number; field: string; value: string };
type Prefill = { field?: unknown; value?: unknown };

function inputType(field: FilterField | undefined) {
  return field?.type === "number" ? "number" : field?.type === "date" ? "date" : "text";
}

function initialRows(config: FiltersConfig, names: Set<string>): FilterRow[] {
  const blank = (key: number): FilterRow => ({ key, field: config.defaultField && names.has(config.defaultField) ? config.defaultField : "", value: "" });
  try {
    const raw = new URLSearchParams(window.location.search).get("filters");
    if (!raw) return [blank(0)];
    const parsed: unknown = JSON.parse(raw);
    if (!record(parsed) || !Array.isArray(parsed.items) || !parsed.items.length) return [blank(0)];
    return parsed.items.map((item: Prefill, index: number) => (record(item) && text(item.field) && names.has(item.field)
      ? { key: index, field: item.field, value: item.value === undefined ? "" : String(item.value) }
      : blank(index)));
  } catch {
    return [blank(0)];
  }
}

function Filters({ data }: { data: DuplasListData }) {
  const config = data.filters_config;
  const fields = config.fields.filter((f) => f.name && f.label);
  const byName = new Map(fields.map((f) => [f.name, f]));
  const defaults: Record<string, string> = { text: "contains", number: "eq", date: "eq", boolean: "eq", choice: "eq", ...config.defaultOperators };
  const [rows, setRows] = useState(() => initialRows(config, new Set(byName.keys())));
  const next = useRef(rows.length);
  const hidden = useRef<HTMLInputElement>(null);
  const update = (key: number, change: Partial<FilterRow>) => setRows((current) => current.map((r) => (r.key === key ? { ...r, ...change } : r)));
  function submit() {
    // The native submit handler only serializes; the browser then sends the GET form.
    const items = rows.flatMap((row) => {
      const field = row.field || fields[0].name;
      const definition = byName.get(field);
      const value = row.value.trim();
      return definition && value !== "" ? [{ field, op: defaults[definition.type] ?? "contains", value }] : [];
    });
    if (hidden.current) hidden.current.value = JSON.stringify({ logic: "AND", items });
  }
  return (
    <form method="GET" action={data.urls.list} id="filters-form" className="ms-0 ms-lg-5" data-config-id="filters-config-json"
      data-seccion-filtros-favoritos={data.favorites.section} data-url-filtros-favoritos={data.favorites.url}
      data-plantilla-url-filtro-favorito={data.favorites.detail_url_template} onSubmit={submit}>
      <div id="poncho-filters-rows" className="poncho-rows">
        {rows.map((row, index) => {
          const definition = byName.get(row.field) ?? fields[0];
          return (
            <div key={row.key} className="poncho-search poncho-search--row">
              <select className="poncho-search__field" data-rol="campo" aria-label="Buscar por" value={row.field}
                onChange={(e) => update(row.key, { field: e.target.value, value: "" })}>
                <option value="">Buscar por</option>
                {fields.map((f) => <option key={f.name} value={f.name}>{f.label}</option>)}
              </select>
              <div className="poncho-search__box">
                <input type={inputType(definition)} className="poncho-search__input" data-rol="valor" autoComplete="off" aria-label="Valor a buscar"
                  placeholder={`Buscar por filtro ${index + 1}`} value={row.value} step={definition.type === "number" ? definition.input?.step ?? "1" : undefined}
                  min={definition.input?.min} max={definition.input?.max} onChange={(e) => update(row.key, { value: e.target.value })} />
                <select className="poncho-search__input poncho-search__input--select" data-rol="valor-select" aria-label="Valor a buscar" hidden style={{ display: "none" }} />
                <button type="submit" className="poncho-search__go" aria-label="Buscar"><i className="fas fa-search" aria-hidden="true" /></button>
              </div>
              <div className="poncho-row-actions">
                <button type="button" className="poncho-addfilter" data-rol="agregar"
                  onClick={() => setRows((current) => [...current, { key: next.current++, field: config.defaultField && byName.has(config.defaultField) ? config.defaultField : "", value: "" }])}>
                  <i className="fas fa-plus" aria-hidden="true" /><span>Filtro</span>
                </button>
                <button type="button" className="poncho-removefilter" data-rol="quitar" hidden={index === 0} style={{ display: index > 0 ? "" : "none" }}
                  onClick={() => setRows((current) => current.filter((r) => r.key !== row.key))}>
                  <i className="fas fa-minus" aria-hidden="true" /><span>Filtro</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
      <input ref={hidden} type="hidden" name="filters" id="filters-input" />
    </form>
  );
}

// --- Table (`data_table.html` + `listSort.js`) ------------------------------

type Sort = { column: string | null; direction: "asc" | "desc" | null };

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

function Table({ data }: { data: DuplasListData }) {
  const [rows, setRows] = useState(data.results);
  const [sort, setSort] = useState<Sort>({ column: null, direction: null });
  // `listSort.js` edits classList: a header sorted once keeps `sort-icon` before its state class.
  const [touched, setTouched] = useState<string[]>([]);
  const [configOpen, setConfigOpen] = useState(false);
  const { cardRef, tableRef, classes } = useLegacyScrollHints(JSON.stringify(data.columns.active));
  function sortBy(column: string, index: number) {
    const direction = sort.column === column ? (sort.direction === "asc" ? "desc" : sort.direction === "desc" ? null : "asc") : "asc";
    setSort({ column: direction ? column : null, direction });
    setTouched((current) => (current.includes(column) ? current : [...current, column]));
    // The source keeps the last row order when the third click clears the sort.
    if (!direction) return;
    setRows((current) => [...current].sort((a, b) => {
      const value = compare(a.cells[index]?.trim() ?? "", b.cells[index]?.trim() ?? "");
      return direction === "asc" ? value : -value;
    }));
  }
  const columns = data.headers.length + 1;
  return (
    <div className="row mt-5 max-width-100">
      <div className="col-12">
        <div className="card">
          <div ref={cardRef} className={`card-body ${classes.card}`}>
            <div className="d-flex justify-content-start mb-2">
              <button type="button" className="btn btn-outline-warning btn-sm" data-bs-toggle="modal" data-bs-target={`#${data.columns.modal_id}`}
                onClick={() => setConfigOpen(true)}>Configurar columnas</button>
            </div>
            {configOpen && <ColumnModal columns={data.columns} close={() => setConfigOpen(false)} />}
            <div ref={tableRef} className={`table-responsive-lg ${classes.table}`}>
              <table className="table table-bordered table-striped projects ">
                <thead>
                  <tr>
                    {data.headers.map((header, index) => (header.sortable ? (
                      <th key={header.sort_key} className={`sortable${sort.column === header.sort_key ? ` sort-${sort.direction}` : ""}`} data-column={header.sort_key}
                        onClick={() => sortBy(header.sort_key, index)}>
                        {header.title}{" "}
                        <i className={sort.column === header.sort_key ? `fas sort-icon fa-sort-${sort.direction === "asc" ? "up" : "down"}`
                          : touched.includes(header.sort_key) ? "fas sort-icon fa-sort" : "fas fa-sort sort-icon"} />
                      </th>
                    ) : <th key={`${index}:${header.title}`}>{header.title}</th>))}
                    <th style={{ width: "20%" }} className="notexport">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.length ? rows.map((row) => (
                    <tr key={row.id}>
                      {row.cells.map((cell, index) => <td key={index}>{cell}</td>)}
                      <td className="project-actions text-right">
                        <div className="action-buttons flex-wrap flex-lg-nowrap" role="group">
                          {row.actions.map((action) => (
                            <a key={action.label} href={safeInternalPath(action.url) ?? "/"} className={`btn btn-${action.type} `} title={action.label}>
                              <i className={`fas fa-${action.icon}`} />{" "}{action.label}
                            </a>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )) : (
                    <tr><td colSpan={columns} className="text-center text-muted py-4">No hay equipos técnicos disponibles.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Column preferences (`column_config_modal.html` + `column_config.js`) ---

function ColumnModal({ columns, close }: { columns: Columns; close: () => void }) {
  const [order, setOrder] = useState(columns.available.map((c) => c.key));
  const [selected, setSelected] = useState(() => columns.available.filter((c) => c.active).map((c) => c.key));
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const modal = useRef<HTMLDivElement>(null);
  const busy = useRef(false);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const before = document.body.style.overflow;
    document.body.classList.add("modal-open");
    document.body.style.overflow = "hidden";
    modal.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy.current) close();
      if (e.key !== "Tab") return;
      const controls = Array.from(modal.current?.querySelectorAll<HTMLElement>("button:not([disabled]),input:not([disabled])") ?? []);
      const first = controls[0], last = controls.at(-1);
      if (e.shiftKey && (document.activeElement === first || document.activeElement === modal.current)) { e.preventDefault(); last?.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      document.body.classList.remove("modal-open");
      document.body.style.overflow = before;
      previous?.focus();
    };
  }, [close]);
  const save = useCallback(async (reset: boolean) => {
    if (busy.current) return;
    const values = order.filter((k) => selected.includes(k));
    setError("");
    if (!reset && !values.length) { setError("Debe haber al menos una columna visible."); return; }
    const fallback = reset ? "No se pudo restablecer la configuracion." : "No se pudo guardar la configuracion.";
    busy.current = true; setPending(true);
    try {
      const response = await fetch(columns.endpoint, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": leerCookie("csrftoken") ?? "", "X-Requested-With": "XMLHttpRequest" },
        body: JSON.stringify(reset ? { list_key: columns.list_key, reset: true } : { list_key: columns.list_key, columns: values }),
      });
      const result: unknown = await response.json().catch(() => null);
      if (!response.ok) throw new Error(record(result) && text(result.error) ? result.error : fallback);
      duplasNavigation.reload();
    } catch (e: unknown) {
      setError(e instanceof Error && e.message ? e.message : fallback);
      setPending(false); busy.current = false;
    }
  }, [columns, order, selected]);
  const move = (key: string, offset: number) => setOrder((current) => {
    const i = current.indexOf(key), j = i + offset;
    if (j < 0 || j >= current.length) return current;
    const nextOrder = [...current]; [nextOrder[i], nextOrder[j]] = [nextOrder[j], nextOrder[i]];
    return nextOrder;
  });
  const titleId = `${columns.modal_id}-title`;
  return (
    <>
      <div className="modal-backdrop fade show" />
      <div ref={modal} className="modal fade show d-block" id={columns.modal_id} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby={titleId}
        data-column-config="true" data-config-id={columns.script_id} onClick={(e) => { if (e.target === e.currentTarget && !pending) close(); }}>
        <div className="modal-dialog modal-dialog-centered modal-lg">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title" id={titleId}>Columnas visibles</h5>
              <button type="button" className="btn-close" aria-label="Cerrar" disabled={pending} onClick={close} />
            </div>
            <div className="modal-body">
              <p className="text-muted mb-3">Seleccioná qué columnas mostrar y ordenalas con las flechas.</p>
              <div className="list-group column-config-list">
                {order.map((key) => {
                  const column = columns.available.find((c) => c.key === key);
                  if (!column) return null;
                  const id = `${columns.modal_id}-${key}`;
                  return (
                    <div key={key} className="list-group-item d-flex flex-wrap align-items-center justify-content-between gap-2" data-column-key={key}>
                      <div className="form-check">
                        <input className="form-check-input column-config-checkbox" type="checkbox" id={id} checked={selected.includes(key)} disabled={pending || column.required}
                          onChange={(e) => setSelected((current) => (e.target.checked ? [...current, key] : current.filter((k) => k !== key)))} />
                        {" "}<label className="form-check-label" htmlFor={id}>{column.title}</label>
                        {column.required && <>{" "}<span className="badge bg-secondary ms-2">Obligatoria</span></>}
                      </div>
                      <div className="btn-group btn-group-sm" role="group">
                        <button type="button" className="btn btn-light column-move-up" title="Mover arriba" disabled={pending} onClick={() => move(key, -1)}><i className="fas fa-arrow-up" /></button>
                        <button type="button" className="btn btn-light column-move-down" title="Mover abajo" disabled={pending} onClick={() => move(key, 1)}><i className="fas fa-arrow-down" /></button>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className={`alert alert-danger mt-3 column-config-error${error ? "" : " d-none"}`}>{error}</div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline-secondary column-config-reset" disabled={pending} onClick={() => void save(true)}>Restablecer</button>
              <button type="button" className="btn btn-primary column-config-save" disabled={pending} onClick={() => void save(false)}>Guardar</button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// --- Pagination (`pagination.html`) -----------------------------------------

function Pagination({ page }: { page: Page }) {
  const href = (n: number) => `?${page.query_without_page}page=${n}`;
  return (
    <div className="mt-2">
      {page.is_paginated && (
        <ul className="pagination">
          <li className={`page-item${page.previous === null ? " disabled" : ""}`}>
            <a href={page.previous === null ? "#" : href(page.previous)} className="page-link">Anterior</a>
          </li>
          {page.range.map((n, index) => (n === "…" ? (
            <li key={`gap-${index}`} className="page-item disabled"><a href="#" className="page-link">...</a></li>
          ) : (
            <li key={n} className={`page-item ${page.number === n ? "active" : ""}`}><a href={href(n)} className="page-link">{n}</a></li>
          )))}
          <li className={`page-item${page.next === null ? " disabled" : ""}`}>
            <a href={page.next === null ? "#" : href(page.next)} className="page-link">Siguiente</a>
          </li>
        </ul>
      )}
      {/* An empty `page_obj` is falsy in the template: no count line. */}
      {page.count > 0 && <p className="text-center text-muted mb-0 mt-1">Se encontraron {page.count} resultados</p>}
    </div>
  );
}

function exportCsv(base: string) {
  const params = new URLSearchParams(window.location.search);
  const sorted = document.querySelector("th.sortable.sort-asc, th.sortable.sort-desc");
  const column = sorted?.getAttribute("data-column");
  if (sorted && column) {
    params.set("sort", column);
    params.set("direction", sorted.classList.contains("sort-asc") ? "asc" : "desc");
  }
  const url = new URL(base, window.location.href);
  if (url.origin !== window.location.origin) return;
  params.forEach((value, key) => url.searchParams.set(key, value));
  duplasNavigation.assign(`${url.pathname}${url.search}`);
}

export function DuplasListContent({ data }: { data: DuplasListData }) {
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
      <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
      <InsumosToastList messages={data.messages} />
      <div className="poncho-topbar">
        {data.can_export && (
          <button type="button" className="poncho-export btn-export-csv" data-url={data.urls.export} title="Descargar listado actual en CSV"
            onClick={() => exportCsv(data.urls.export)}>
            <i className="fas fa-file-excel" aria-hidden="true" />Exportar búsqueda
          </button>
        )}
      </div>
      <h2 className="text-center mb-4 poncho-titulo">Buscar Equipo Técnico</h2>
      <Filters data={data} />
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={data.urls.reset} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
          <a href={data.urls.add} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />Agregar</a>
        </div>
      </div>
      <div className="container mt-4">
        <Table data={data} />
        <Pagination page={data.page} />
      </div>
    </>
  );
}

export function Breadcrumb({ items }: { items: DuplasListData["breadcrumb"] }) {
  return (
    <ol className="breadcrumb float-sm-right">
      {items.map((item, index) => (
        <li key={`${index}:${item.text}`} className={`breadcrumb-item ${item.url === null ? "active" : ""}`}>
          {item.url !== null ? <a href={safeInternalPath(item.url) ?? "/"}>{item.text}</a> : item.text}
        </li>
      ))}
    </ol>
  );
}

export default function DuplasList() {
  const state = useDuplasResource(`${API}${window.location.search}`, listValid);
  return renderDuplas(state, (data) => ({
    title: "Listado de Equipos técnicos",
    heading: "Equipo técnico",
    breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <DuplasListContent data={data} />,
  }));
}
