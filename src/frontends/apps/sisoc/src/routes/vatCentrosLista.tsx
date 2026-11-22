/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validator and content are exported for the tests. */
import { useLayoutEffect, useRef, useState } from "react";
import { Filters, Pagination, filtersConfigValid, type Favorites, type FiltersConfig } from "./listControls";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { bool, compareForSort, integer, listUrlsValid, messagesValid, type Message } from "./vatShared";
import { CsrfInput, useForbidden } from "./vatFormShared";
import { UncertainNotice, usePostDelete, vatBreadcrumb } from "./vatCentrosListaShared";
import { TourHelp } from "./vatTour";
import type { RouteDefinition } from "./types";

/**
 * V06.01 centros: `vat/centros/centro_list.html` (the search bar in filters mode, the table with the sortable headers,
 * the inline delete form and `pagination.html` over a paginator without a count). Data comes from
 * `/api/web/vat/centros-lista/`, which runs `CentroListView`; the delete confirmation is `vatCentrosBaja.tsx`.
 */
type Row = { id: number; nombre: string; calle: string; telefono: string; celular: string; activo: boolean; detail_url: string; update_url: string; delete_url: string };
type Paging = { is_paginated: boolean; number: number; previous: number | null; next: number | null; range: (number | "…")[]; query_prefix: string };
export type CentrosListData = {
  filters_config: FiltersConfig; favorites: Favorites; results: Row[]; page: Paging; can_add: boolean; permisos: { eliminar: boolean };
  urls: { list: string; create: string }; messages: Message[];
};

const API = "web/vat/centros-lista/";
export const DELETE_CONFIRM = "¿Estás seguro de que deseas eliminar este centro? Esta acción no se puede deshacer.";

const rowValid = (r: unknown) => record(r) && integer(r.id) && ["nombre", "calle", "telefono", "celular"].every((k) => text(r[k])) && bool(r.activo) &&
  internal(r.detail_url) && internal(r.update_url) && internal(r.delete_url);

export function centrosListValid(v: unknown): v is CentrosListData {
  if (!record(v) || !record(v.favorites) || !record(v.page) || !record(v.permisos)) return false;
  const f = v.favorites, p = v.page;
  return filtersConfigValid(v.filters_config) && text(f.section) && internal(f.url) && internal(f.detail_url_template) &&
    Array.isArray(v.results) && v.results.every(rowValid) &&
    bool(p.is_paginated) && integer(p.number) && (p.previous === null || integer(p.previous)) && (p.next === null || integer(p.next)) &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || integer(n)) && text(p.query_prefix) &&
    bool(v.can_add) && bool(v.permisos.eliminar) && listUrlsValid(v.urls) && messagesValid(v.messages);
}

type SortKey = "nombre" | "calle" | "telefono" | "activo";
const HEADERS: { title: string; key: SortKey }[] = [
  { title: "Nombre", key: "nombre" }, { title: "Dirección", key: "calle" }, { title: "Teléfono", key: "telefono" }, { title: "Estado", key: "activo" },
];
/** The `data-*` value each header sorts by (`listSort.js`). */
const sortValue = (row: Row, key: SortKey) => (key === "activo" ? (row.activo ? "Activo" : "Inactivo") : row[key]);

/** `poncho_scroll_tablas.js` on the card body, which holds the table directly. */
function useScrollHint(revision: string) {
  const ref = useRef<HTMLDivElement>(null);
  const [className, setClassName] = useState("poncho-scroll");
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return undefined;
    const update = () => {
      const overflow = element.scrollWidth - element.clientWidth > 2;
      const left = overflow && element.scrollLeft > 2;
      const right = overflow && element.scrollLeft + element.clientWidth < element.scrollWidth - 2;
      setClassName(`poncho-scroll${left ? " poncho-scroll--izq" : ""}${right ? " poncho-scroll--der" : ""}`);
    };
    update();
    element.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => { element.removeEventListener("scroll", update); window.removeEventListener("resize", update); };
  }, [revision]);
  return { ref, className };
}

/** The inline `<form method="post">` of a row, guarded by the native `confirm()`. */
function DeleteForm({ row, forbidden }: { row: Row; forbidden: (d: unknown) => void }) {
  const { uncertain, submit } = usePostDelete(`${API}${row.id}/eliminar/`, forbidden, DELETE_CONFIRM);
  return <form method="post" action={row.delete_url} style={{ display: "inline" }} onSubmit={submit}>
    <CsrfInput />
    <UncertainNotice show={uncertain} />
    <button type="submit" className="btn btn-eliminar" title="Eliminar centro" data-confirm-click={DELETE_CONFIRM}>
      <i className="fas fa-trash-alt" />{" "}Eliminar
    </button>
  </form>;
}

function CentrosTable({ data, forbidden }: { data: CentrosListData; forbidden: (d: unknown) => void }) {
  const [rows, setRows] = useState(data.results);
  const [sort, setSort] = useState<{ key: SortKey | null; direction: "asc" | "desc" | null }>({ key: null, direction: null });
  // `listSort.js` edits classList: a header sorted once keeps `sort-icon` before its state class.
  const [touched, setTouched] = useState<string[]>([]);
  const { ref, className } = useScrollHint(String(rows.length));
  const { page } = data;
  function sortBy(key: SortKey) {
    const direction = sort.key === key ? (sort.direction === "asc" ? "desc" : sort.direction === "desc" ? null : "asc") : "asc";
    setSort({ key: direction ? key : null, direction });
    setTouched((current) => (current.includes(key) ? current : [...current, key]));
    if (!direction) return;
    setRows((current) => [...current].sort((a, b) => {
      const value = compareForSort(sortValue(a, key), sortValue(b, key));
      return direction === "asc" ? value : -value;
    }));
  }
  return <div className="row mt-5 max-width-100"><div className="col-12"><div className="card">
    <div ref={ref} className={`card-body ${className}`}>
      <table className="table table-bordered table-striped projects">
        <thead><tr>
          {HEADERS.map((h) => (
            <th key={h.key} className={`sortable ${sort.key === h.key ? `sort-${sort.direction}` : ""}`.trimEnd()} data-column={h.key} onClick={() => sortBy(h.key)}>
              {h.title}{" "}
              <i className={sort.key === h.key ? `fas sort-icon fa-sort-${sort.direction === "asc" ? "up" : "down"}`
                : touched.includes(h.key) ? "fas sort-icon fa-sort" : "fas fa-sort sort-icon"} />
            </th>
          ))}
          <th>Acciones</th>
        </tr></thead>
        <tbody id="centros-table-body">
          {rows.length ? rows.map((row) => <tr key={row.id}>
            <td data-nombre={row.nombre}><a href={row.detail_url} className="font-weight-bold link-handler" title="Ver detalles">{row.nombre}</a></td>
            <td data-calle={row.calle}>{row.calle}</td>
            <td data-telefono={row.telefono}>{row.telefono} / {row.celular}</td>
            <td data-activo={row.activo ? "Activo" : "Inactivo"}>
              {row.activo ? <span className="badge badge-success">Activo</span> : <span className="badge badge-danger">Inactivo</span>}
            </td>
            <td><div className="action-buttons" role="group">
              <a href={row.detail_url} className="btn btn-primary" title="Ver detalle del centro"><i className="fas fa-eye" />{" "}Ver</a>{" "}
              <a href={row.update_url} className="btn btn-editar" title="Editar centro"><i className="fas fa-edit" />{" "}Editar</a>
              {data.permisos.eliminar && <>{" "}<DeleteForm row={row} forbidden={forbidden} /></>}
            </div></td>
          </tr>) : <tr><td colSpan={5} className="text-center">No se encontraron centros.</td></tr>}
        </tbody>
      </table>
      <div id="pagination-container">
        <Pagination paginated={page.is_paginated} number={page.number} previous={page.previous} next={page.next} range={page.range}
          href={(n) => `?${page.query_prefix}page=${n}`} count={null} />
      </div>
    </div>
  </div></div></div>;
}

export function CentrosListContent({ data, forbidden }: { data: CentrosListData; forbidden: (d: unknown) => void }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
    <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
    <h2 className="text-center mb-4 poncho-titulo">Buscar Centros de Formación Profesional</h2>
    <Filters config={data.filters_config} action={data.urls.list} favorites={data.favorites} />
    <div className="row mt-3"><div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
      <a href={data.urls.list} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
      {data.can_add && <a href={data.urls.create} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />Agregar CFP</a>}
    </div></div>
    <CentrosTable data={data} forbidden={forbidden} />
    <TourHelp section="centros_list" />
  </>;
}

function ListPage() {
  const [state, setState] = useMainResource(`${API}${window.location.search}`, centrosListValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando centros…", (data) => ({
    title: "INET - Centros",
    breadcrumb: vatBreadcrumb([{ text: "INET", url: data.urls.list }, { text: "Listar", url: null }]),
    content: <CentrosListContent data={data} forbidden={forbidden} />,
  }));
}

// Native URL of `VAT/urls.py`; `<id>/eliminar/` is `vatCentrosBaja.tsx`.
export const vatCentrosListaRoute: RouteDefinition<Record<string, never>> = {
  name: "vat-centros-lista",
  match: (pathname) => (pathname === "/vat/centros/" ? {} : null),
  render: () => <ListPage />,
};
