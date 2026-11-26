/* eslint-disable react-refresh/only-export-components -- the list screens export their validator and navigation seam for the unit tests. */
import { useState } from "react";
import { InsumosToastList } from "../InsumosToast";
import { ColumnModal, Filters, Pagination, ServerSortHeader, filtersConfigValid, type Columns, type Favorites, type FiltersConfig } from "./listControls";
import { Breadcrumb, internal, record, text } from "./MainFrame";

/**
 * AD03.01 technical and legal admision lists (`admisiones_tecnicos_list.html`,
 * `admisiones_legales_list.html`): `search_bar.html` in filters mode without the
 * add button, `data_table.html` with custom cells and actions, the server
 * ordering header of «Nombre», column preferences and `pagination.html`. Data
 * comes from `/api/web/comedores/admisiones/{tecnicos,legales}/`, which runs the
 * native views; the «Rectificar»/«Archivado» badge is data, not markup.
 */
type Header = { title: string; sort_url: string | null; sort_direction: "asc" | "desc" | null };
type Cell = { content: string; data_attr: string | null; data_value: string | null; link_url: string | null; link_class: string | null; link_title: string | null };
type Action = { label: string; badge: string | null; url: string; type: string };
type Row = { cells: Cell[]; actions: Action[] };
type Page = { is_paginated: boolean; number: number; count: number; has_rows: boolean; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type Crumb = { text: string; url: string | null; active: boolean };
export type ListData = {
  title: string; breadcrumb: Crumb[]; filters_config: FiltersConfig; favorites: Favorites; urls: { list: string; reset: string };
  columns: Columns; headers: Header[]; results: Row[]; page: Page; messages: Message[];
};

const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const LEVELS = ["success", "error", "warning", "info"];
const nullable = (v: unknown) => v === null || text(v);

export function listValid(v: unknown): v is ListData {
  if (!record(v) || !record(v.filters_config) || !record(v.favorites) || !record(v.urls) || !record(v.columns) || !record(v.page)) return false;
  const c = v.columns, p = v.page, u = v.urls;
  return text(v.title) && filtersConfigValid(v.filters_config) &&
    Array.isArray(v.breadcrumb) && v.breadcrumb.every((b) => record(b) && text(b.text) && nullable(b.url) && typeof b.active === "boolean") &&
    text(v.favorites.section) && internal(v.favorites.url) && internal(v.favorites.detail_url_template) &&
    internal(u.list) && internal(u.reset) &&
    text(c.list_key) && internal(c.endpoint) && text(c.modal_id) && text(c.script_id) &&
    Array.isArray(c.available) && c.available.every((x) => record(x) && text(x.key) && text(x.title) && typeof x.active === "boolean" && typeof x.required === "boolean") &&
    Array.isArray(v.headers) && v.headers.every((h) => record(h) && text(h.title) && nullable(h.sort_url)) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && Array.isArray(r.cells) &&
      r.cells.every((x) => record(x) && text(x.content) && (x.link_url === null || internal(x.link_url))) &&
      Array.isArray(r.actions) && r.actions.every((a) => record(a) && text(a.label) && nullable(a.badge) && internal(a.url) && text(a.type))) &&
    typeof p.is_paginated === "boolean" && typeof p.has_rows === "boolean" && int(p.number) && int(p.count) &&
    (p.previous === null || int(p.previous)) && (p.next === null || int(p.next)) &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || int(n)) && text(p.query_without_page) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Full-page navigation (reload); replaceable in tests. */
export const admisionesListNavigation = { reload: () => window.location.reload() };

function Table({ data, empty }: { data: ListData; empty: string }) {
  const [configOpen, setConfigOpen] = useState(false);
  return (
    <div className="row mt-5 max-width-100"><div className="col-12"><div className="card"><div className="card-body">
      <div className="d-flex justify-content-start mb-2">
        <button type="button" className="btn btn-outline-warning btn-sm" data-bs-toggle="modal" data-bs-target={`#${data.columns.modal_id}`}
          onClick={() => setConfigOpen(true)}>Configurar columnas</button>
      </div>
      {configOpen && <ColumnModal columns={data.columns} close={() => setConfigOpen(false)} reload={() => admisionesListNavigation.reload()} />}
      <div className="table-responsive-lg">
        <table className="table table-bordered table-striped projects ">
          <thead><tr>
            {data.headers.map((h, i) => <th key={i}>{h.sort_url ? <ServerSortHeader title={h.title} url={h.sort_url} direction={h.sort_direction} /> : h.title}</th>)}
            <th style={{ width: "15%" }} className="notexport">Acciones</th>
          </tr></thead>
          <tbody>
            {data.results.length ? data.results.map((row, r) => <tr key={r}>
              {row.cells.map((cell, i) => <td key={i} {...(cell.data_attr ? { [`data-${cell.data_attr}`]: cell.data_value || cell.content } : {})}>
                {cell.link_url ? <a href={cell.link_url} {...(cell.link_class ? { className: cell.link_class } : {})} {...(cell.link_title ? { title: cell.link_title } : {})}>{cell.content}</a> : cell.content}
              </td>)}
              <td className="project-actions text-right">
                {row.actions.length > 0 && <div className="action-buttons flex-wrap flex-lg-nowrap" role="group">
                  {row.actions.map((a) => <a key={a.label} href={a.url} className={`btn btn-${a.type} ${a.badge ? "position-relative" : ""}`} title={a.label}>
                    <i className="fas fa-eye" />{" "}{a.label}
                    {a.badge && <span className="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger">{a.badge}</span>}
                  </a>)}
                </div>}
              </td>
            </tr>) : <tr><td colSpan={data.headers.length + 1} className="text-center text-muted py-4">{empty}</td></tr>}
          </tbody>
        </table>
      </div>
      <Pagination paginated={data.page.is_paginated} number={data.page.number} previous={data.page.previous} next={data.page.next} range={data.page.range}
        href={(n) => `?${data.page.query_without_page}page=${n}`} count={data.page.has_rows ? data.page.count : null} />
    </div></div></div></div>
  );
}

export function ListCrumbs({ items }: { items: Crumb[] }) {
  return <Breadcrumb items={items.map((c) => ({ text: c.text, url: c.active ? null : c.url }))} />;
}

export function AdmisionesListContent({ data, empty }: { data: ListData; empty: string }) {
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
      <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
      <InsumosToastList messages={data.messages} />
      <h2 className="text-center mb-4 poncho-titulo">{data.title}</h2>
      <Filters config={data.filters_config} action={data.urls.list} favorites={data.favorites} />
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={data.urls.reset} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
        </div>
      </div>
      <Table data={data} empty={empty} />
    </>
  );
}
