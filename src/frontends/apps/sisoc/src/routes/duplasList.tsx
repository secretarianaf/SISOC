/* eslint-disable react-refresh/only-export-components -- the list screen exports its validator and navigation seam for the unit tests. */
import { useState } from "react";
import { InsumosToastList } from "../InsumosToast";
import { useLegacyScrollHints } from "../useLegacyScrollHints";
import { safeInternalPath } from "../webAccess";
import { ColumnModal, Filters, Pagination, type Columns, type Favorites, type FiltersConfig } from "./listControls";
import { API, integer, messagesValid, record, renderDuplas, text, useDuplasResource, type Message } from "./duplasShared";

/**
 * `dupla_list.html`: `search_bar.html` in filters mode (`advanced_filters.js`),
 * `data_table.html` with column preferences (`column_config.js`) and client
 * sorting (`listSort.js`), `pagination.html` and the CSV button
 * (`export_helper.js`, native GET). Filters, column modal and pagination come
 * from `routes/listControls.tsx`.
 */
type Header = { title: string; sortable: boolean; sort_key: string };
type Action = { label: string; url: string; type: string; icon: string };
type Row = { id: number; cells: string[]; actions: Action[] };
type Page = { is_paginated: boolean; number: number; count: number; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };
export type DuplasListData = {
  breadcrumb: { text: string; url: string | null }[];
  filters_config: FiltersConfig;
  favorites: Favorites;
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
            {configOpen && <ColumnModal columns={data.columns} close={() => setConfigOpen(false)} reload={() => duplasNavigation.reload()} />}
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
      <Filters config={data.filters_config} action={data.urls.list} favorites={data.favorites} />
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={data.urls.reset} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
          <a href={data.urls.add} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />Agregar</a>
        </div>
      </div>
      <div className="container mt-4">
        <Table data={data} />
        {/* An empty `page_obj` is falsy in the template: no count line. */}
        <Pagination paginated={data.page.is_paginated} number={data.page.number} previous={data.page.previous} next={data.page.next} range={data.page.range}
          href={(n) => `?${data.page.query_without_page}page=${n}`} prevText="Anterior" nextText="Siguiente" count={data.page.count > 0 ? data.page.count : null} />
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
