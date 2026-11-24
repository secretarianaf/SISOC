/* eslint-disable react-refresh/only-export-components -- the list screen exports its validator and navigation seam for the unit tests. */
import { useState } from "react";
import { FlashToasts } from "./organizacionesForm";
import { useLegacyScrollHints } from "../useLegacyScrollHints";
import { safeInternalPath } from "../webAccess";
import { Filters, Pagination, filtersConfigValid, type Favorites, type FiltersConfig } from "./listControls";
import { Breadcrumb, breadcrumbValid, internal, record, renderMain, text, useMainResource, type Breadcrumbs } from "./MainFrame";

/**
 * O05.01 `organizacion_list.html`: `search_bar.html` in filters mode
 * (`advanced_filters.js`) with «Agregar» and «Exportar búsqueda», the rows of
 * `organizaciones/partials/organizacion_rows.html` with client sorting
 * (`listSort.js` over the `data-*` values) and `pagination.html` («Volver» /
 * «Continuar», no result count: `NoCountPaginator`). Data comes from
 * `/api/web/comedores/organizaciones/listado/`, which runs the native view and
 * renders the native rows include. The CSV stays the native
 * `/organizaciones/exportar` GET (`export_helper.js`).
 */
type Cell = { text: string; sort: string | null };
type Action = { label: string; url: string; class: string; title: string; icon: string | null };
type Row = { id: number; cells: Cell[]; detail_url: string; actions: Action[] };
type Page = { is_paginated: boolean; number: number; previous: number | null; next: number | null; range: (number | "…")[]; query_prefix: string };
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type OrganizacionesListData = {
  breadcrumb: Breadcrumbs;
  filters_config: FiltersConfig;
  favorites: Favorites;
  urls: { list: string; reset: string; add: string; export: string };
  can_add: boolean;
  can_export: boolean;
  results: Row[];
  empty: string | null;
  page: Page;
  messages: Message[];
};

const API = "web/comedores/organizaciones/listado/";
const LEVELS = ["success", "error", "warning", "info"];
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const nullable = (v: unknown) => v === null || text(v);

export function listValid(v: unknown): v is OrganizacionesListData {
  if (!record(v) || !record(v.favorites) || !record(v.urls) || !record(v.page)) return false;
  const p = v.page, u = v.urls;
  return breadcrumbValid(v.breadcrumb) && filtersConfigValid(v.filters_config) &&
    text(v.favorites.section) && internal(v.favorites.url) && internal(v.favorites.detail_url_template) &&
    ["list", "reset", "add", "export"].every((k) => internal(u[k])) &&
    typeof v.can_add === "boolean" && typeof v.can_export === "boolean" && nullable(v.empty) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && integer(r.id) && internal(r.detail_url) &&
      Array.isArray(r.cells) && r.cells.length === 7 && r.cells.every((c) => record(c) && text(c.text) && nullable(c.sort)) &&
      Array.isArray(r.actions) && r.actions.every((a) => record(a) && text(a.label) && internal(a.url) && text(a.class) && text(a.title) && nullable(a.icon))) &&
    typeof p.is_paginated === "boolean" && integer(p.number) &&
    (p.previous === null || integer(p.previous)) && (p.next === null || integer(p.next)) &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || integer(n)) && text(p.query_prefix) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Full-page navigation (CSV download); replaceable in tests. */
export const organizacionesNavigation = {
  assign: (to: string) => window.location.assign(to),
};

// --- Table (`organizacion_list.html` + `listSort.js`) -----------------------

const COLUMNS = [
  ["cuit", "CUIT"], ["nombre", "Nombre"], ["comedores", "Comedores"], ["tipo_entidad", "Tipo de entidad"],
  ["subtipo_entidad", "Subtipo de entidad"], ["telefono", "Teléfono"], ["email", "Email"],
] as const;
type Sort = { column: string | null; direction: "asc" | "desc" | null };

function parseDateForSort(value: string): number | null {
  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(value.trim());
  if (!match) return null;
  const [day, month, year] = [Number(match[1]), Number(match[2]), Number(match[3])];
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day ? parsed.getTime() : null;
}

/** `sortTable`: the `data-<column>` values; the cell text only when both are empty. */
function compare(a: Cell, b: Cell): number {
  let av = a.sort ?? "", bv = b.sort ?? "";
  if (av === "" && bv === "") { av = a.text.trim(); bv = b.text.trim(); }
  const ad = parseDateForSort(av), bd = parseDateForSort(bv);
  if (ad !== null && bd !== null) return ad - bd;
  const an = parseFloat(av), bn = parseFloat(bv);
  if (!Number.isNaN(an) && !Number.isNaN(bn) && av !== "" && bv !== "") return an - bn;
  const plain = (s: string) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  return plain(av).localeCompare(plain(bv), "es", { sensitivity: "base" });
}

function Table({ data }: { data: OrganizacionesListData }) {
  const [rows, setRows] = useState(data.results);
  const [sort, setSort] = useState<Sort>({ column: null, direction: null });
  // `listSort.js` edits classList: a header sorted once keeps `sort-icon` before its state class.
  const [touched, setTouched] = useState<string[]>([]);
  // The rows hang from the card body: it is the scroll container of `poncho_scroll_tablas.js`.
  const { cardRef, tableRef, classes } = useLegacyScrollHints(String(data.results.length));
  const bodyRef = (element: HTMLDivElement | null) => { cardRef.current = element; tableRef.current = element; };
  function sortBy(column: string, index: number) {
    const direction = sort.column === column ? (sort.direction === "asc" ? "desc" : sort.direction === "desc" ? null : "asc") : "asc";
    setSort({ column: direction ? column : null, direction });
    setTouched((current) => (current.includes(column) ? current : [...current, column]));
    // The source keeps the last row order when the third click clears the sort.
    if (!direction) return;
    setRows((current) => [...current].sort((a, b) => {
      const value = compare(a.cells[index], b.cells[index]);
      return direction === "asc" ? value : -value;
    }));
  }
  return (
    <div className="row mt-5 max-width-100">
      <div className="col-12">
        <div className="card">
          <div ref={bodyRef} className={`card-body ${classes.card}`}>
            <table className="table table-bordered table-striped projects">
              <thead>
                <tr>
                  {COLUMNS.map(([key, title], index) => (
                    <th key={key} className={`sortable${sort.column === key ? ` sort-${sort.direction}` : ""}`} data-column={key} onClick={() => sortBy(key, index)}>
                      {title}{" "}
                      <i className={sort.column === key ? `fas sort-icon fa-sort-${sort.direction === "asc" ? "up" : "down"}`
                        : touched.includes(key) ? "fas sort-icon fa-sort" : "fas fa-sort sort-icon"} />
                    </th>
                  ))}
                  <th style={{ width: "20%" }} className="notexport">Acciones</th>
                </tr>
              </thead>
              <tbody id="organizaciones-tbody">
                {rows.length ? rows.map((row) => (
                  <tr key={row.id}>
                    {row.cells.map((cell, index) => (
                      <td key={COLUMNS[index][0]} {...{ [`data-${COLUMNS[index][0]}`]: cell.sort ?? undefined }}>
                        {index === 1 ? <a href={safeInternalPath(row.detail_url) ?? "/"} className="font-weight-bold link-handler" title="Ver detalles">{cell.text}</a> : cell.text}
                      </td>
                    ))}
                    <td className="project-actions text-right">
                      <div className="action-buttons" role="group">
                        {row.actions.map((action) => (
                          <a key={action.label} href={safeInternalPath(action.url) ?? "/"} className={action.class} title={action.title}>
                            {action.icon && <i className={action.icon} />}{" "}{action.label}
                          </a>
                        ))}
                      </div>
                    </td>
                  </tr>
                )) : (
                  <tr><td colSpan={8} className="text-center text-muted py-4">{data.empty}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

/** `export_helper.js`: the native CSV URL with the current query and the client sort. */
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
  organizacionesNavigation.assign(`${url.pathname}${url.search}`);
}

export function OrganizacionesListContent({ data }: { data: OrganizacionesListData }) {
  return (
    <>
      <FlashToasts messages={data.messages} />
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
      <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
      <div className="poncho-topbar">
        {data.can_export && (
          <button type="button" className="poncho-export btn-export-csv" data-url={data.urls.export} title="Descargar listado actual en CSV"
            onClick={() => exportCsv(data.urls.export)}>
            <i className="fas fa-file-excel" aria-hidden="true" />Exportar búsqueda
          </button>
        )}
      </div>
      <h2 className="text-center mb-4 poncho-titulo">Buscar Organización</h2>
      {/* The native form posts to "" (this page): same GET target. */}
      <Filters config={data.filters_config} action={data.urls.list} favorites={data.favorites} />
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={data.urls.reset} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
          {data.can_add && <a href={data.urls.add} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />Agregar</a>}
        </div>
      </div>
      <Table data={data} />
      <div id="pagination-container">
        <Pagination paginated={data.page.is_paginated} number={data.page.number} previous={data.page.previous} next={data.page.next} range={data.page.range}
          href={(n) => `?${data.page.query_prefix}page=${n}`} count={null} />
      </div>
    </>
  );
}

export default function OrganizacionesList() {
  const [state] = useMainResource(`${API}${window.location.search}`, listValid);
  return renderMain(state, "Cargando organizaciones…", (data) => ({
    title: "Organizaciones",
    breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <OrganizacionesListContent data={data} />,
  }));
}
