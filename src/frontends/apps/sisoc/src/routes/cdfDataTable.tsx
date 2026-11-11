/* eslint-disable react-refresh/only-export-components -- shared list pieces of the CDF route modules. */
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { useLegacyScrollHints } from "../useLegacyScrollHints";
import { safeInternalPath } from "../webAccess";
import { Filters, filtersConfigValid, type Favorites, type FiltersConfig } from "./cdfFilters";
import { integer, internal, messagesValid, record, text, type CdfMessage } from "./cdfFrame";

/**
 * `search_bar.html` (filters mode) + `data_table.html` with column preferences
 * (`column_config_modal.html`, `column_config.js`), local sort (`listSort.js`)
 * and `pagination.html` for the CDF beneficiaries and responsables lists. The
 * exact envelope carries `count`; the NoCount one has `count: null` and shows
 * no total. Every link is a native GET.
 */
type Column = { key: string; title: string; active: boolean; required: boolean; default: boolean };
type Columns = { list_key: string; endpoint: string; modal_id: string; script_id: string; available: Column[]; active: string[]; defaults: string[] };
type Header = { title: string; width: string; sortable: boolean; sort_key: string };
type Row = { id: number; cells: string[]; url: string };
export type CdfListData = {
  breadcrumb: { text: string; url: string | null }[];
  filters_config: FiltersConfig; favorites: Favorites; columns: Columns; headers: Header[]; results: Row[];
  count: number | null; page: number; page_size: number; pages: number | null; has_next: boolean; has_previous: boolean;
  page_range: (number | "...")[]; is_paginated: boolean; query_without_page: string; filters: { filters: string };
  messages: CdfMessage[];
};

export function cdfListValid(v: unknown): v is CdfListData {
  if (!record(v) || !record(v.columns) || !record(v.favorites) || !record(v.filters)) return false;
  const c = v.columns, fav = v.favorites;
  return Array.isArray(v.breadcrumb) && v.breadcrumb.every((b) => record(b) && text(b.text) && (b.url === null || internal(b.url))) &&
    filtersConfigValid(v.filters_config) && text(fav.section) && internal(fav.url) && internal(fav.detail_url_template) &&
    text(c.list_key) && internal(c.endpoint) && text(c.modal_id) && text(c.script_id) &&
    Array.isArray(c.available) && c.available.every((x) => record(x) && text(x.key) && text(x.title) && typeof x.active === "boolean" && typeof x.required === "boolean") &&
    Array.isArray(c.active) && c.active.every(text) && Array.isArray(c.defaults) && c.defaults.every(text) &&
    Array.isArray(v.headers) && v.headers.every((h) => record(h) && text(h.title) && text(h.width) && typeof h.sortable === "boolean" && text(h.sort_key)) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && integer(r.id) && Array.isArray(r.cells) && r.cells.every(text) && internal(r.url)) &&
    (v.count === null || integer(v.count)) && (v.pages === null || integer(v.pages)) && integer(v.page) && integer(v.page_size) &&
    typeof v.has_next === "boolean" && typeof v.has_previous === "boolean" && typeof v.is_paginated === "boolean" &&
    Array.isArray(v.page_range) && v.page_range.every((n) => n === "..." || integer(n)) && text(v.query_without_page) &&
    text(v.filters.filters) && messagesValid(v.messages);
}

/** Full-page navigation (export, reload); replaceable in tests. */
export const listNavigation = {
  assign: (to: string) => window.location.assign(to),
  reload: () => window.location.reload(),
};

export function Breadcrumb({ items }: { items: CdfListData["breadcrumb"] }) {
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

/** `search_bar.html` in filters mode: optional export button, title, filters and actions. */
export function SearchBar({ data, title, reset, add, exportButton }: {
  data: CdfListData; title: string; reset: string; add?: { url: string; text: string }; exportButton?: ReactNode;
}) {
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
      <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
      {exportButton !== undefined && <div className="poncho-topbar">{exportButton}</div>}
      <h2 className="text-center mb-4 poncho-titulo">{title}</h2>
      <Filters config={data.filters_config} action={reset} favorites={data.favorites} />
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={reset} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
          {add && <a href={add.url} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />{add.text}</a>}
        </div>
      </div>
    </>
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

export function DataTable({ data, empty }: { data: CdfListData; empty: string }) {
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
    if (!direction) return;
    setRows((current) => [...current].sort((a, b) => {
      const value = compare(a.cells[index]?.trim() ?? "", b.cells[index]?.trim() ?? "");
      return direction === "asc" ? value : -value;
    }));
  }
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
                      <th key={header.sort_key} style={header.width ? { width: header.width } : undefined}
                        className={`sortable ${sort.column === header.sort_key ? `sort-${sort.direction}` : ""}`} data-column={header.sort_key}
                        onClick={() => sortBy(header.sort_key, index)}>
                        {header.title}{" "}
                        <i className={sort.column === header.sort_key ? `fas sort-icon fa-sort-${sort.direction === "asc" ? "up" : "down"}`
                          : touched.includes(header.sort_key) ? "fas sort-icon fa-sort" : "fas fa-sort sort-icon"} />
                      </th>
                    ) : <th key={`${index}:${header.title}`} style={header.width ? { width: header.width } : undefined}>{header.title}</th>))}
                    <th style={{ width: "15%" }} className="notexport">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.length ? rows.map((row) => (
                    <tr key={row.id}>
                      {row.cells.map((cell, index) => <td key={index}>{cell}</td>)}
                      <td className="project-actions text-right">
                        <div className="action-buttons flex-wrap flex-lg-nowrap" role="group">
                          <a href={safeInternalPath(row.url) ?? "/"} className="btn btn-info btn-sm" title="Ver"><i className="fas fa-eye" />{" "}Ver</a>
                        </div>
                      </td>
                    </tr>
                  )) : (
                    <tr><td colSpan={data.headers.length + 1} className="text-center text-muted py-4">{empty}</td></tr>
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
      listNavigation.reload();
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

// --- Pagination (`pagination.html`, «Anterior»/«Siguiente») ------------------

export function Pagination({ data }: { data: CdfListData }) {
  const href = (n: number) => `?${data.query_without_page}page=${n}`;
  return (
    <div className="mt-2">
      {data.is_paginated && (
        <ul className="pagination">
          <li className={`page-item${data.has_previous ? "" : " disabled"}`}>
            <a href={data.has_previous ? href(data.page - 1) : "#"} className="page-link">Anterior</a>
          </li>
          {data.page_range.map((n, index) => (n === "..." ? (
            <li key={`gap-${index}`} className="page-item disabled"><a href="#" className="page-link">...</a></li>
          ) : (
            <li key={n} className={`page-item ${data.page === n ? "active" : ""}`}><a href={href(n)} className="page-link">{n}</a></li>
          )))}
          <li className={`page-item${data.has_next ? "" : " disabled"}`}>
            <a href={data.has_next ? href(data.page + 1) : "#"} className="page-link">Siguiente</a>
          </li>
        </ul>
      )}
      {data.count !== null && data.results.length > 0 && <p className="text-center text-muted mb-0 mt-1">Se encontraron {data.count} resultados</p>}
    </div>
  );
}

// --- Detail pieces (`cdf.css` cards of the CDF03 details) ------------------

export function DetailHead() {
  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      <link href="https://fonts.googleapis.com/css2?family=Lora:wght@600;700&display=swap" rel="stylesheet" />
      <link rel="stylesheet" href="/static/custom/css/cdf.css" />
    </>
  );
}

export function Dl({ rows, dt = "col-sm-4", dd = "col-sm-8" }: { rows: [string, ReactNode][]; dt?: string; dd?: string }) {
  return (
    <dl className="row mb-0">
      {rows.map(([label, value]) => [
        <dt key={`t-${label}`} className={dt}>{label}</dt>,
        <dd key={`d-${label}`} className={dd}>{value}</dd>,
      ])}
    </dl>
  );
}

export function Card({ icon, title, tools, children, half = true }: { icon: string; title: string; tools?: ReactNode; children: ReactNode; half?: boolean }) {
  const card = (
    <div className={`cdf-card${half ? " w-100" : ""}`}>
      <div className="cdf-card-head">
        <i className={`fas ${icon}`} />
        <span>{title}</span>
        {tools}
      </div>
      <div className="cdf-card-body">{children}</div>
    </div>
  );
  return half ? <div className="col-md-6 d-flex">{card}</div> : card;
}
