/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen, validator and navigation seam live here with the route. */
import { useRef, useState } from "react";
import { useLegacyScrollHints } from "../useLegacyScrollHints";
import { safeInternalPath } from "../webAccess";
import { Breadcrumb, crumbsValid, internal, messagesValid, record, renderCdi, text, useCdiPage, type CdiMessage, type Crumb } from "./cdiFrame";
import { ColumnModal, Filters, filtersConfigValid, Pagination, type Columns, type Favorites, type FiltersConfig } from "./listControls";
import type { RouteDefinition } from "./types";
import { useModalTabTrap } from "./nativeParity";

/**
 * CDI09.01 centres list (`centrodeinfancia/centrodeinfancia_list.html` +
 * `partials/rows.html`): `search_bar.html` in filters mode, the table with
 * column preferences (`column_config.js`) and local sorting (`listSort.js`),
 * `pagination.html` (exact pages of 10, "Volver"/"Continuar"), the CSV button
 * (`export_helper.js`) and the children PDF modal. Row cells come computed from
 * the backend; the CSV and the PDF stay native downloads.
 */
type Cell = { text: string; sort: string; url: string | null };
type Row = { id: number; cells: Cell[]; urls: { detail: string; edit: string; delete: string } };
type Page = { is_paginated: boolean; number: number; previous: number | null; next: number | null; range: (number | string)[]; count: number | null; query_prefix: string };
export type CentrosData = {
  breadcrumb: Crumb[];
  filters_config: FiltersConfig;
  favorites: Favorites;
  columns: Columns;
  headers: { key: string; title: string }[];
  results: Row[];
  page: Page;
  can_export: boolean;
  nomina_ninos: { provincias: { id: number; nombre: string }[]; url: string } | null;
  urls: { list: string; add: string; export: string };
  messages: CdiMessage[];
};

const integer = (v: unknown): v is number => Number.isSafeInteger(v);

export function centrosValid(v: unknown): v is CentrosData {
  if (!record(v) || !record(v.favorites) || !record(v.columns) || !record(v.page) || !record(v.urls)) return false;
  const f = v.favorites, c = v.columns, p = v.page, u = v.urls, n = v.nomina_ninos;
  return crumbsValid(v.breadcrumb) && filtersConfigValid(v.filters_config) &&
    text(f.section) && internal(f.url) && internal(f.detail_url_template) &&
    text(c.list_key) && internal(c.endpoint) && text(c.modal_id) && text(c.script_id) &&
    Array.isArray(c.available) && c.available.every((x) => record(x) && text(x.key) && text(x.title) && typeof x.active === "boolean" && typeof x.required === "boolean") &&
    Array.isArray(c.active) && c.active.every(text) && Array.isArray(c.defaults) && c.defaults.every(text) &&
    Array.isArray(v.headers) && v.headers.every((h) => record(h) && text(h.key) && text(h.title)) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && integer(r.id) && Array.isArray(r.cells) &&
      r.cells.every((x) => record(x) && text(x.text) && text(x.sort) && (x.url === null || internal(x.url))) &&
      record(r.urls) && internal(r.urls.detail) && internal(r.urls.edit) && internal(r.urls.delete)) &&
    typeof p.is_paginated === "boolean" && integer(p.number) && (p.previous === null || integer(p.previous)) && (p.next === null || integer(p.next)) &&
    Array.isArray(p.range) && p.range.every((x) => integer(x) || x === "...") && (p.count === null || integer(p.count)) && text(p.query_prefix) &&
    typeof v.can_export === "boolean" &&
    (n === null || (record(n) && internal(n.url) && Array.isArray(n.provincias) && n.provincias.every((x) => record(x) && integer(x.id) && text(x.nombre)))) &&
    internal(u.list) && internal(u.add) && internal(u.export) && messagesValid(v.messages);
}

/** Full-page navigation (CSV export, column reload); replaceable in tests. */
export const centrosNavigation = {
  assign: (to: string) => window.location.assign(to),
  reload: () => window.location.reload(),
};

/** `export_helper.js`: the current query plus the active local sort (`sort`/`direction`). */
function exportUrl(base: string) {
  const params = new URLSearchParams(window.location.search);
  const sorted = document.querySelector("th.sortable.sort-asc, th.sortable.sort-desc");
  const column = sorted?.getAttribute("data-column");
  if (sorted && column) {
    params.set("sort", column);
    params.set("direction", sorted.classList.contains("sort-asc") ? "asc" : "desc");
  }
  const url = new URL(base, window.location.href);
  params.forEach((value, key) => url.searchParams.set(key, value));
  return `${url.pathname}${url.search}`;
}

// --- Sorting (`listSort.js`): data value first, cell text when both are empty ---

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

function sortValues(a: Cell | undefined, b: Cell | undefined): [string, string] {
  const av = a?.sort ?? "", bv = b?.sort ?? "";
  return av === "" && bv === "" ? [a?.text.trim() ?? "", b?.text.trim() ?? ""] : [av, bv];
}

type Sort = { column: string | null; direction: "asc" | "desc" | null };

function NominaNinosModal({ config, close }: { config: NonNullable<CentrosData["nomina_ninos"]>; close: () => void }) {
  const modal = useRef<HTMLDivElement>(null);
  useModalTabTrap(modal, close, { controls: "button:not([disabled]),select:not([disabled])" });
  return (
    <>
      <div className="modal-backdrop fade show" />
      <div ref={modal} className="modal fade show d-block" id="nomina-ninos-provincia-modal" tabIndex={-1} role="dialog" aria-modal="true"
        aria-labelledby="nomina-ninos-provincia-modal-label" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
        <div className="modal-dialog modal-dialog-centered">
          <div className="modal-content">
            <form method="get" action={config.url}>
              <div className="modal-header">
                <h5 className="modal-title" id="nomina-ninos-provincia-modal-label">Descargar nómina de niños</h5>
                <button type="button" className="btn-close" aria-label="Cerrar" onClick={close} />
              </div>
              <div className="modal-body">
                <label className="form-label" htmlFor="nomina-ninos-provincia">Provincia</label>
                <select className="form-select" id="nomina-ninos-provincia" name="provincia" required defaultValue="">
                  <option value="">Seleccionar provincia</option>
                  {config.provincias.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                </select>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline-secondary" onClick={close}>Cancelar</button>
                <button type="submit" className="btn btn-primary">Descargar</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}

function Table({ data }: { data: CentrosData }) {
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
      const [x, y] = sortValues(a.cells[index], b.cells[index]);
      const value = compare(x, y);
      return direction === "asc" ? value : -value;
    }));
  }
  return (
    <div className="row mt-5 max-width-100">
      <div className="col-12">
        <div className="card comedor-table-card">
          <div ref={cardRef} className={`card-body ${classes.card}`}>
            <div className="d-flex justify-content-start mb-2">
              <button type="button" className="btn btn-outline-warning btn-sm" data-bs-toggle="modal" data-bs-target={`#${data.columns.modal_id}`}
                onClick={() => setConfigOpen(true)}>Configurar columnas</button>
            </div>
            {configOpen && <ColumnModal columns={data.columns} close={() => setConfigOpen(false)} reload={() => centrosNavigation.reload()} />}
            <div ref={tableRef} className={`table-responsive-lg ${classes.table}`}>
              <table className="table table-comedor-moderno">
                <thead>
                  <tr>
                    {data.headers.map((header, index) => (
                      <th key={header.key} className={`sortable${sort.column === header.key ? ` sort-${sort.direction}` : ""}`} data-column={header.key}
                        onClick={() => sortBy(header.key, index)}>
                        {header.title}{" "}
                        <i className={sort.column === header.key ? `fas sort-icon fa-sort-${sort.direction === "asc" ? "up" : "down"}`
                          : touched.includes(header.key) ? "fas sort-icon fa-sort" : "fas fa-sort sort-icon"} />
                      </th>
                    ))}
                    <th className="notexport">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.length ? rows.map((row) => (
                    <tr key={row.id}>
                      {row.cells.map((cell, index) => (
                        <td key={data.headers[index]?.key ?? index}>
                          {cell.url ? <a href={safeInternalPath(cell.url) ?? "/"}>{cell.text}</a> : cell.text}
                        </td>
                      ))}
                      <td>
                        <div className="comedor-actions">
                          <a href={safeInternalPath(row.urls.detail) ?? "/"} className="btn btn-ver" title="Ver detalles"><i className="fas fa-eye" />{" "}Ver</a>
                          <a href={safeInternalPath(row.urls.edit) ?? "/"} className="btn btn-editar" title="Editar centro"><i className="fas fa-edit" />{" "}Editar</a>
                          <a href={safeInternalPath(row.urls.delete) ?? "/"} className="btn btn-eliminar" title="Eliminar centro"><i className="fas fa-trash-alt" />{" "}Eliminar</a>
                        </div>
                      </td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan={data.headers.length + 1}>
                        <div className="no-comedores-message">
                          <h3>No se encontraron centros de desarrollo infantil</h3>
                          <p>No hay centros que coincidan con los criterios de búsqueda.</p>
                        </div>
                      </td>
                    </tr>
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

export function CentrosContent({ data }: { data: CentrosData }) {
  const [nominaOpen, setNominaOpen] = useState(false);
  const { page } = data;
  return (
    <div className="comedor-list-container">
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
      <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
      <div className="poncho-topbar">
        {data.can_export && (
          <button type="button" className="poncho-export btn-export-csv" data-url={data.urls.export} title="Descargar listado actual en CSV"
            onClick={() => centrosNavigation.assign(exportUrl(data.urls.export))}>
            <i className="fas fa-file-excel" aria-hidden="true" />Exportar búsqueda
          </button>
        )}
      </div>
      <h2 className="text-center mb-4 poncho-titulo">Buscar Centro de Desarrollo Infantil</h2>
      <Filters config={data.filters_config} action={data.urls.list} favorites={data.favorites} />
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={data.urls.list} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
          <a href={data.urls.add} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />Nuevo Centro</a>
          {data.nomina_ninos && (
            <button type="button" className="poncho-btn poncho-btn--descarga" data-bs-toggle="modal" data-bs-target="#nomina-ninos-provincia-modal"
              onClick={() => setNominaOpen(true)}>Descargar nómina de niños</button>
          )}
        </div>
      </div>
      {nominaOpen && data.nomina_ninos && <NominaNinosModal config={data.nomina_ninos} close={() => setNominaOpen(false)} />}
      <Table data={data} />
      <Pagination paginated={page.is_paginated} number={page.number} previous={page.previous} next={page.next} range={page.range}
        count={page.count} href={(n) => `?${page.query_prefix}page=${n}`} prevText="Volver" nextText="Continuar" />
    </div>
  );
}

function CentrosPage() {
  const [state] = useCdiPage(`web/cdi/centros/${window.location.search}`, centrosValid);
  return renderCdi(state, (data) => ({
    title: "Centros de Desarrollo Infantil",
    heading: "",
    breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <CentrosContent data={data} />,
  }));
}

// Native URL of the CDI centres list (CDI09.01); no trailing slash, like the Django route.
export const cdiCentrosRoute: RouteDefinition<Record<string, never>> = {
  name: "cdi-centros",
  match: (pathname) => (pathname === "/centrodeinfancia/listar" ? {} : null),
  render: () => <CentrosPage />,
};
