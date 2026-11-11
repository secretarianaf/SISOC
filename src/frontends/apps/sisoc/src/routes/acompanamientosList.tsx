/* eslint-disable react-refresh/only-export-components -- the list screen exports its validator and navigation seam for the unit tests. */
import { useState } from "react";
import { InsumosToastList } from "../InsumosToast";
import { ColumnModal, Filters, Pagination, ServerSortHeader, type Columns, type Favorites, type FiltersConfig } from "./listControls";
import { internal, record, text } from "./MainFrame";

/**
 * `lista_comedores.html`: `search_bar.html` in filters mode without the add
 * button (`advanced_filters.js`, choice fields included), `data_table.html`
 * with custom cells and actions, the server ordering header of «Nombre»,
 * column preferences (`column_config.js`) and the integrated
 * `pagination.html`. The CSV button is the native GET with the current query.
 *
 * Filters, column modal, ordering header and pagination come from
 * `routes/listControls.tsx`, shared with Duplas and CDF.
 */
type Header = { title: string; sort_url: string | null; sort_direction: "asc" | "desc" | null };
type Cell = { content: string; data_attr: string | null; data_value: string | null };
type Action = { label: string; url: string; type: string };
type Row = { cells: Cell[]; actions: Action[] };
type Page = { is_paginated: boolean; number: number; count: number; has_rows: boolean; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type AcompanamientosListData = {
  filters_config: FiltersConfig; favorites: Favorites;
  urls: { list: string; reset: string; export: string }; can_export: boolean; columns: Columns;
  headers: Header[]; results: Row[]; page: Page; messages: Message[];
};

const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const LEVELS = ["success", "error", "warning", "info"];

export function listValid(v: unknown): v is AcompanamientosListData {
  if (!record(v) || !record(v.filters_config) || !record(v.favorites) || !record(v.urls) || !record(v.columns) || !record(v.page)) return false;
  const f = v.filters_config, c = v.columns, p = v.page, u = v.urls;
  return Array.isArray(f.fields) && f.fields.length > 0 && f.fields.every((x) => record(x) && text(x.name) && text(x.label) && text(x.type)) &&
    text(v.favorites.section) && internal(v.favorites.url) && internal(v.favorites.detail_url_template) &&
    ["list", "reset", "export"].every((k) => internal(u[k])) && typeof v.can_export === "boolean" &&
    text(c.list_key) && internal(c.endpoint) && text(c.modal_id) && text(c.script_id) &&
    Array.isArray(c.available) && c.available.every((x) => record(x) && text(x.key) && text(x.title) && typeof x.active === "boolean" && typeof x.required === "boolean") &&
    Array.isArray(v.headers) && v.headers.every((h) => record(h) && text(h.title) && (h.sort_url === null || text(h.sort_url))) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && Array.isArray(r.cells) && r.cells.every((x) => record(x) && text(x.content)) &&
      Array.isArray(r.actions) && r.actions.every((a) => record(a) && text(a.label) && internal(a.url) && text(a.type))) &&
    typeof p.is_paginated === "boolean" && typeof p.has_rows === "boolean" && int(p.number) && int(p.count) &&
    (p.previous === null || int(p.previous)) && (p.next === null || int(p.next)) &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || int(n)) && text(p.query_without_page) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Full-page navigation (export, reload); replaceable in tests. */
export const acompanamientosNavigation = {
  assign: (to: string) => window.location.assign(to),
  reload: () => window.location.reload(),
};

// --- Table (`data_table.html` with custom cells) and `pagination.html` -------

function Table({ data }: { data: AcompanamientosListData }) {
  const [configOpen, setConfigOpen] = useState(false);
  return (
    <div className="row mt-5 max-width-100"><div className="col-12"><div className="card"><div className="card-body">
      <div className="d-flex justify-content-start mb-2">
        <button type="button" className="btn btn-outline-warning btn-sm" data-bs-toggle="modal" data-bs-target={`#${data.columns.modal_id}`}
          onClick={() => setConfigOpen(true)}>Configurar columnas</button>
      </div>
      {configOpen && <ColumnModal columns={data.columns} close={() => setConfigOpen(false)} reload={() => acompanamientosNavigation.reload()} />}
      <div className="table-responsive-lg">
        <table className="table table-bordered table-striped projects ">
          <thead><tr>
            {data.headers.map((h, i) => <th key={i}>{h.sort_url ? <ServerSortHeader title={h.title} url={h.sort_url} direction={h.sort_direction} /> : h.title}</th>)}
            <th style={{ width: "15%" }} className="notexport">Acciones</th>
          </tr></thead>
          <tbody>
            {data.results.length ? data.results.map((row, r) => <tr key={r}>
              {row.cells.map((cell, i) => <td key={i} {...(cell.data_attr ? { [`data-${cell.data_attr}`]: cell.data_value || cell.content } : {})}>{cell.content}</td>)}
              <td className="project-actions text-right">
                {row.actions.length > 0 && <div className="action-buttons flex-wrap flex-lg-nowrap" role="group">
                  {row.actions.map((a) => <a key={a.label} href={a.url} className={`btn btn-${a.type} `} title={a.label}>{a.label}</a>)}
                </div>}
              </td>
            </tr>) : <tr><td colSpan={data.headers.length + 1} className="text-center text-muted py-4">No se encontraron comedores.</td></tr>}
          </tbody>
        </table>
      </div>
      <Pagination paginated={data.page.is_paginated} number={data.page.number} previous={data.page.previous} next={data.page.next} range={data.page.range}
        href={(n) => `?${data.page.query_without_page}page=${n}`} count={data.page.has_rows ? data.page.count : null} />
    </div></div></div></div>
  );
}

function exportCsv(base: string) {
  // `export_helper.js`: the native GET with the current query.
  const url = new URL(base, window.location.href);
  if (url.origin !== window.location.origin) return;
  new URLSearchParams(window.location.search).forEach((value, key) => url.searchParams.set(key, value));
  acompanamientosNavigation.assign(`${url.pathname}${url.search}`);
}

export function AcompanamientosListContent({ data }: { data: AcompanamientosListData }) {
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
      <h2 className="text-center mb-4 poncho-titulo">Comedores en Acompañamiento</h2>
      <Filters config={data.filters_config} action={data.urls.list} favorites={data.favorites} />
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={data.urls.reset} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
        </div>
      </div>
      <Table data={data} />
    </>
  );
}
