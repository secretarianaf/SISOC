/* eslint-disable react-refresh/only-export-components -- route module: the validator and the navigation seam are exported for the tests. */
import { useState } from "react";
import { useLegacyScrollHints } from "../useLegacyScrollHints";
import { safeInternalPath } from "../webAccess";
import { Filters, filtersConfigValid, Pagination, type Favorites, type FiltersConfig } from "./listControls";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * `ciudadanos/ciudadano_list.html` (`/ciudadanos/listar`) with `components/search_bar.html` in filters mode.
 * GET `/api/web/ciudadanos/listar/` runs `CiudadanosListView` (403 without `ciudadanos.view_ciudadano`) and returns what the
 * template prints. The search bar is the shared `Filters` (a native GET), the identity form is its own native GET, the table
 * sorts locally like `listSort.js` and the CSV button keeps `export_helper.js` (the current query plus the active sort, as a
 * full-page navigation to the native download). The page of 25 has no total, as the `NoCountPaginator` page has none.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Cell = { text: string; sort: string };
type Row = { id: number; cells: Cell[]; tipo_registro: string; requiere_revision: boolean; ver_url: string };
type Choice = { label: string; value: string; options: { value: string; label: string }[] };
type Button = { label: string; url: string; class: string; title: string };
export type ListadoData = {
  filters_config: FiltersConfig;
  favorites: Favorites;
  filtros: { q: string; tipo_registro: Choice; estado_revision: Choice; filters: string };
  results: Row[];
  page: { is_paginated: boolean; number: number; previous: number | null; next: number | null; range: (number | string)[]; query_prefix: string };
  can_export: boolean;
  additional_buttons: Button[];
  urls: { list: string; add: string; export: string };
  messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const integer = (v: unknown): v is number => Number.isSafeInteger(v);
const pageNumber = (v: unknown) => v === null || integer(v);
const choiceValid = (v: unknown): v is Choice => record(v) && text(v.label) && text(v.value) && Array.isArray(v.options) &&
  v.options.every((o) => record(o) && text(o.value) && text(o.label));

export function listadoValid(v: unknown): v is ListadoData {
  if (!record(v) || !record(v.favorites) || !record(v.filtros) || !record(v.page) || !record(v.urls) || !Array.isArray(v.results)) return false;
  const f = v.favorites, q = v.filtros, p = v.page, u = v.urls;
  return filtersConfigValid(v.filters_config) && text(f.section) && internal(f.url) && internal(f.detail_url_template) &&
    text(q.q) && choiceValid(q.tipo_registro) && choiceValid(q.estado_revision) && text(q.filters) &&
    v.results.every((r) => record(r) && integer(r.id) && text(r.tipo_registro) && typeof r.requiere_revision === "boolean" && internal(r.ver_url) &&
      Array.isArray(r.cells) && r.cells.length === HEADERS.length && r.cells.every((c) => record(c) && text(c.text) && text(c.sort))) &&
    typeof p.is_paginated === "boolean" && integer(p.number) && pageNumber(p.previous) && pageNumber(p.next) &&
    Array.isArray(p.range) && p.range.every((n) => integer(n) || n === "...") && text(p.query_prefix) &&
    typeof v.can_export === "boolean" &&
    Array.isArray(v.additional_buttons) && v.additional_buttons.every((b) => record(b) && text(b.label) && internal(b.url) && text(b.class) && text(b.title)) &&
    internal(u.list) && internal(u.add) && internal(u.export) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Replaceable in tests: the CSV download is a full-page navigation, like `export_helper.js`. */
export const ciudadanoListadoNavigation = { assign: (to: string) => window.location.assign(to) };

const HEADERS = [
  { key: "apellido", title: "Apellido" }, { key: "nombre", title: "Nombre" }, { key: "documento", title: "Documento" },
  { key: "sexo", title: "Sexo" }, { key: "provincia", title: "Provincia" },
];
/** `data-enabled-values` of `#estado-revision-group`: the identity types that allow filtering the review. */
const REVISION_TIPOS = ["", "SIN_DNI", "DNI_NO_VALIDADO_RENAPER"];

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

function Identidad({ row }: { row: Row }) {
  return (
    <td>
      {row.tipo_registro === "SIN_DNI" ? <span className="badge bg-warning text-dark" title="Sin DNI">Sin DNI</span>
        : row.tipo_registro === "DNI_NO_VALIDADO_RENAPER" ? <span className="badge bg-danger" title="DNI no validado por RENAPER">RENAPER no validado</span>
        : <span className="badge bg-success" title="Estándar">Estándar</span>}
      {row.requiere_revision && (
        <>
          {" "}
          <span className="badge bg-secondary ms-1" title="Requiere revisión manual"><i className="fas fa-exclamation-triangle" />{" "}Revisión</span>
        </>
      )}
    </td>
  );
}

function IdentityForm({ data }: { data: ListadoData }) {
  const { filtros } = data;
  const [tipo, setTipo] = useState(filtros.tipo_registro.value);
  const [estado, setEstado] = useState(filtros.estado_revision.value);
  const visible = REVISION_TIPOS.includes(tipo);
  const select = (name: string, choice: Choice, value: string, change: (v: string) => void, disabled = false) => (
    <select name={name} id={`id_${name}`} value={value} disabled={disabled} onChange={(e) => change(e.target.value)}>
      {choice.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
  return (
    <form method="get" className="row g-2 align-items-end mb-4" id="province-filter-form">
      <div className="col-12 col-lg-4">
        <label htmlFor="id_tipo_registro">{filtros.tipo_registro.label}</label>{" "}
        {select("tipo_registro", filtros.tipo_registro, tipo, setTipo)}
      </div>
      <div className={`col-12 col-lg-4${visible ? "" : " invisible"}`} id="estado-revision-group" data-enabled-values={`,${REVISION_TIPOS.slice(1).join(",")}`}>
        <label htmlFor="id_estado_revision">{filtros.estado_revision.label}</label>{" "}
        {select("estado_revision", filtros.estado_revision, estado, setEstado, !visible)}
      </div>
      <input type="hidden" name="q" id="province-hidden-q" value={filtros.q} readOnly />
      <input type="hidden" name="filters_mode" value="ui" readOnly />
      <input type="hidden" name="filters" value={filtros.filters} readOnly />
      <div className="col-12 col-lg-4">
        <button type="submit" className="btn btn-outline-secondary w-100">Aplicar</button>
      </div>
    </form>
  );
}

function Table({ data }: { data: ListadoData }) {
  const [rows, setRows] = useState(data.results);
  const [sort, setSort] = useState<Sort>({ column: null, direction: null });
  // `listSort.js` edits classList: a header sorted once keeps `sort-icon` before its state class.
  const [touched, setTouched] = useState<string[]>([]);
  const { cardRef, tableRef, classes } = useLegacyScrollHints(null);
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
        <div className="card">
          <div className="card-header">
            <h3 className="card-title mb-0">Listado de ciudadanos</h3>
          </div>
          <div ref={cardRef} className={`card-body ${classes.card}`}>
            <IdentityForm data={data} />
            <div ref={tableRef} className={`table-responsive ${classes.table}`}>
              <table className="table table-bordered table-striped projects mb-0">
                <thead>
                  <tr>
                    {HEADERS.map((header, index) => (
                      <th key={header.key} className={`sortable${sort.column === header.key ? ` sort-${sort.direction}` : ""}`} data-column={header.key}
                        onClick={() => sortBy(header.key, index)}>
                        {header.title}{" "}
                        <i className={sort.column === header.key ? `fas sort-icon fa-sort-${sort.direction === "asc" ? "up" : "down"}`
                          : touched.includes(header.key) ? "fas sort-icon fa-sort" : "fas fa-sort sort-icon"} />
                      </th>
                    ))}
                    <th>Estado identidad</th>
                    <th style={{ width: "15%" }} className="text-center">Acciones</th>
                  </tr>
                </thead>
                <tbody id="ciudadanos-table-body">
                  {rows.length ? rows.map((row) => (
                    <tr key={row.id}>
                      {row.cells.map((cell, index) => <td key={HEADERS[index].key}>{cell.text}</td>)}
                      <Identidad row={row} />
                      <td className="text-center">
                        <a href={safeInternalPath(row.ver_url) ?? "/"} className="btn btn-primary" title="Ver detalle del ciudadano"><i className="fas fa-eye" />{" "}Ver</a>
                      </td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan={7} className="text-center">No se encontraron ciudadanos.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div id="pagination-container" className="mt-3">
              {data.page.is_paginated && (
                <Pagination paginated number={data.page.number} previous={data.page.previous} next={data.page.next} range={data.page.range}
                  count={null} href={(n) => `?${data.page.query_prefix}page=${n}`} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ListadoContent({ data }: { data: ListadoData }) {
  const { filtros } = data;
  return (
    <>
      <NativeToasts messages={data.messages} />
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
      <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
      <div className="poncho-topbar">
        {data.can_export && (
          <button type="button" className="poncho-export btn-export-csv" data-url={data.urls.export} title="Descargar listado actual en CSV"
            onClick={() => ciudadanoListadoNavigation.assign(exportUrl(data.urls.export))}>
            <i className="fas fa-file-excel" aria-hidden="true" />Exportar búsqueda
          </button>
        )}
      </div>
      <h2 className="text-center mb-4 poncho-titulo">Buscar ciudadano</h2>
      <Filters config={data.filters_config} action={data.urls.list} favorites={data.favorites} />
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={data.urls.list} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
          <a href={data.urls.add} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />Nuevo ciudadano</a>
          {data.additional_buttons.map((button) => (
            <a key={button.url} href={button.url} className={button.class} title={button.title}>{button.label}</a>
          ))}
        </div>
      </div>
      <input type="hidden" name="q" id="hidden-q-input" form="filters-form" value={filtros.q} readOnly />
      <input type="hidden" name="filters_mode" form="filters-form" value="ui" readOnly />
      <input type="hidden" name="tipo_registro" form="filters-form" value={filtros.tipo_registro.value} readOnly />
      <input type="hidden" name="estado_revision" form="filters-form" value={filtros.estado_revision.value} readOnly />
      <Table data={data} />
    </>
  );
}

function ListadoPage() {
  const [state] = useMainResource(`web/ciudadanos/listar/${window.location.search}`, listadoValid);
  // The native template defines the page title and heading with the same text.
  return renderMain(state, "Cargando ciudadanos…", (data) => ({
    title: "Historia Social Digital", heading: "Historia Social Digital", breadcrumb: null, content: <ListadoContent data={data} />,
  }));
}

// Native URL of the ciudadanos list; no trailing slash, like the Django route.
export const ciudadanoListadoRoute: RouteDefinition<Record<string, never>> = {
  name: "ciudadano-listado",
  match: (pathname) => (pathname === "/ciudadanos/listar" ? {} : null),
  render: () => <ListadoPage />,
};
