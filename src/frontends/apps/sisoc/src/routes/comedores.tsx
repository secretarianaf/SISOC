/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { useState } from "react";
import { InsumosToastList } from "../InsumosToast";
import { ColumnModal, Filters, Pagination, type Columns, type Favorites, type FiltersConfig } from "./listControls";
import { Breadcrumb, internal, record, renderMain, text, useMainResource, type Breadcrumbs } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * CO07.01 comedor list (`/comedores/listar`): `comedor_list.html` with the
 * search bar in filters mode (export button by role, add button), the
 * `comedor_table.html` card (column preferences, client-side `listSort.js`
 * ordering of «Nombre» and «Validación», row actions) and `pagination.html`
 * over the NoCount paginator (no result total). Data comes from
 * `/api/web/comedores/comedores/`, which runs the native `ComedorListView`.
 * The CSV is the native GET with the current query; create, edit and delete
 * stay native pages.
 */
type Cell =
  | { key: "ubicacion"; lines: string[] }
  | { key: "validacion"; value: string; date: string | null }
  | { key: string; text: string };
type Row = { id: number; nombre: string; cells: Cell[]; urls: { detalle: string; editar: string; eliminar: string } };
type Header = { key: string; title: string; sortable: boolean };
type Page = { is_paginated: boolean; number: number; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type ComedoresListData = {
  breadcrumb: Breadcrumbs; filters_config: FiltersConfig; favorites: Favorites;
  urls: { list: string; reset: string; add: string; export: string }; can_export: boolean; columns: Columns;
  headers: Header[]; results: Row[]; page: Page; messages: Message[];
};

const API = "web/comedores/comedores/";
const LEVELS = ["success", "error", "warning", "info"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);

export function listValid(v: unknown): v is ComedoresListData {
  if (!record(v) || !record(v.filters_config) || !record(v.favorites) || !record(v.urls) || !record(v.columns) || !record(v.page)) return false;
  const f = v.filters_config, c = v.columns, p = v.page, u = v.urls;
  return Array.isArray(v.breadcrumb) && v.breadcrumb.every((b) => record(b) && text(b.text) && (b.url === null || internal(b.url))) &&
    Array.isArray(f.fields) && f.fields.length > 0 && f.fields.every((x) => record(x) && text(x.name) && text(x.label) && text(x.type)) &&
    text(v.favorites.section) && internal(v.favorites.url) && internal(v.favorites.detail_url_template) &&
    ["list", "reset", "add", "export"].every((k) => internal(u[k])) && typeof v.can_export === "boolean" &&
    text(c.list_key) && internal(c.endpoint) && text(c.modal_id) && text(c.script_id) &&
    Array.isArray(c.available) && c.available.every((x) => record(x) && text(x.key) && text(x.title) && typeof x.active === "boolean" && typeof x.required === "boolean") &&
    Array.isArray(v.headers) && v.headers.every((h) => record(h) && text(h.key) && text(h.title) && typeof h.sortable === "boolean") &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && int(r.id) && text(r.nombre) && record(r.urls) && ["detalle", "editar", "eliminar"].every((k) => internal((r.urls as Record<string, unknown>)[k])) &&
      Array.isArray(r.cells) && r.cells.every((x) => record(x) && text(x.key))) &&
    typeof p.is_paginated === "boolean" && int(p.number) && (p.previous === null || int(p.previous)) && (p.next === null || int(p.next)) &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || int(n)) && text(p.query_without_page) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Full-page navigation (export, reload); replaceable in tests. */
export const comedoresNavigation = {
  assign: (to: string) => window.location.assign(to),
  reload: () => window.location.reload(),
};

// `listSort.js`: ascending, descending, then back to the page order.
type Sort = { column: string; direction: "asc" | "desc" } | null;
const PRIORITY: Record<string, number> = { Validado: 3, Pendiente: 2, "No Validado": 1 };
const fold = (s: string) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

function sortValue(row: Row, column: string): string {
  if (column === "nombre") return row.nombre;
  const cell = row.cells.find((c) => c.key === column);
  return cell && "value" in cell ? cell.value : "";
}

export function sortRows(rows: Row[], sort: Sort): Row[] {
  if (!sort) return rows;
  const sign = sort.direction === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const x = sortValue(a, sort.column), y = sortValue(b, sort.column);
    if (sort.column === "validacion") return sign * ((PRIORITY[x] ?? 0) - (PRIORITY[y] ?? 0));
    return sign * fold(x).localeCompare(fold(y), "es", { sensitivity: "base" });
  });
}

function nextSort(current: Sort, column: string): Sort {
  if (!current || current.column !== column) return { column, direction: "asc" };
  return current.direction === "asc" ? { column, direction: "desc" } : null;
}

function Td({ cell, row }: { cell: Cell; row: Row }) {
  if (cell.key === "nombre") {
    return <td data-nombre={row.nombre}><a href={row.urls.detalle} className="link-handler" title={`Ver detalles de ${row.nombre}`}>{row.nombre}</a></td>;
  }
  if ("lines" in cell) {
    return <td><div className="ubicacion-info">{cell.lines.map((line, i) => <div key={i} className="ubicacion-item">{line}</div>)}</div></td>;
  }
  if ("value" in cell) {
    const kind = cell.value === "Validado" ? { cls: "validado", icon: "fa-check-circle", label: "Validado" }
      : cell.value === "No Validado" ? { cls: "no-validado", icon: "fa-times-circle", label: "No Validado" } : { cls: "pendiente", icon: "fa-clock", label: "Pendiente" };
    return <td data-validacion={cell.value}>
      <span className={`badge-validacion ${kind.cls}`}><i className={`fas ${kind.icon}`} />{" "}{kind.label}</span>
      {cell.date && kind.cls !== "pendiente" && <>{" "}<small className="fecha-validacion">{cell.date}</small></>}
    </td>;
  }
  return <td>{cell.text}</td>;
}

function Table({ data }: { data: ComedoresListData }) {
  const [configOpen, setConfigOpen] = useState(false);
  const [sort, setSort] = useState<Sort>(null);
  const rows = sortRows(data.results, sort);
  return (
    <div className="row mt-5 max-width-100"><div className="col-12"><div className="card comedor-table-card"><div className="card-body">
      <div className="d-flex justify-content-start mb-2">
        <button type="button" className="btn btn-outline-warning btn-sm" data-bs-toggle="modal" data-bs-target={`#${data.columns.modal_id}`}
          onClick={() => setConfigOpen(true)}>Configurar columnas</button>
      </div>
      {configOpen && <ColumnModal columns={data.columns} close={() => setConfigOpen(false)} reload={() => comedoresNavigation.reload()} />}
      <div className="table-responsive-lg">
        <table className="table table-comedor-moderno">
          <thead><tr>
            {data.headers.map((h) => {
              if (!h.sortable) return <th key={h.key}>{h.title}</th>;
              const state = sort?.column === h.key ? sort.direction : null;
              const icon = state === "asc" ? "fa-sort-up" : state === "desc" ? "fa-sort-down" : "fa-sort";
              return <th key={h.key} className={`sortable${state ? ` sort-${state}` : ""}`} data-column={h.key} onClick={() => setSort(nextSort(sort, h.key))}>
                {h.title}{" "}<i className={`fas ${icon} sort-icon`} />
              </th>;
            })}
            <th className="notexport">Acciones</th>
          </tr></thead>
          <tbody>
            {rows.length ? rows.map((row) => <tr key={row.id}>
              {row.cells.map((cell) => <Td key={cell.key} cell={cell} row={row} />)}
              <td><div className="comedor-actions">
                <a href={row.urls.detalle} className="btn btn-ver link-handler" title="Ver detalles"><i className="fas fa-eye" />{" "}Ver</a>{" "}
                <a href={row.urls.editar} className="btn btn-editar link-handler" title="Editar comedor"><i className="fas fa-edit" />{" "}Editar</a>{" "}
                <a href={row.urls.eliminar} className="btn btn-eliminar link-handler" title="Eliminar comedor"><i className="fas fa-trash-alt" />{" "}Eliminar</a>
              </div></td>
            </tr>) : <tr><td colSpan={data.headers.length + 1}><div className="no-comedores-message">
              <h3>No se encontraron comedores</h3><p>No hay comedores que coincidan con los criterios de búsqueda.</p>
            </div></td></tr>}
          </tbody>
        </table>
      </div>
    </div></div></div></div>
  );
}

function exportCsv(base: string) {
  // `export_helper.js`: the native GET with the current query.
  const url = new URL(base, window.location.href);
  if (url.origin !== window.location.origin) return;
  new URLSearchParams(window.location.search).forEach((value, key) => url.searchParams.set(key, value));
  comedoresNavigation.assign(`${url.pathname}${url.search}`);
}

export function ComedoresListContent({ data }: { data: ComedoresListData }) {
  return (
    <div className="comedor-list-container">
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
      <h2 className="text-center mb-4 poncho-titulo">Buscar Espacio Comunitario</h2>
      <Filters config={data.filters_config} action={data.urls.list} favorites={data.favorites} />
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={data.urls.reset} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
          <a href={data.urls.add} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />Agregar</a>
        </div>
      </div>
      <Table data={data} />
      <Pagination paginated={data.page.is_paginated} number={data.page.number} previous={data.page.previous} next={data.page.next} range={data.page.range}
        href={(n) => `?${data.page.query_without_page}page=${n}`} count={null} />
    </div>
  );
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, listValid);
  return renderMain(state, "Cargando comedores…", (data) => ({
    title: "Espacios Comunitarios", breadcrumb: <Breadcrumb items={data.breadcrumb} />, content: <ComedoresListContent data={data} />,
  }));
}

// Native GET page `comedores/listar` (no trailing slash).
export const comedoresRoute: RouteDefinition<{ page: "list" }> = {
  name: "comedores-listado",
  match(pathname) {
    return pathname === "/comedores/listar" ? { page: "list" } : null;
  },
  render() {
    return <ListPage />;
  },
};
