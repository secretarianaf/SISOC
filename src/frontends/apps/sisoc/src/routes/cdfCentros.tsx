/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { Fragment, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Filters, filtersConfigValid, type Favorites, type FiltersConfig } from "./cdfFilters";
import {
  client, csrfToken, integer, internal, messagesValid, navigation, nullableText, record, renderCdf, text, useCdfPage,
  type CdfMessage,
} from "./cdfFrame";
import type { RouteDefinition } from "./types";

/**
 * CDF04.01 (contract #2805): `centros/centro_list.html` (NoCount list) and
 * `centros/centro_detail.html` (ficha) on their native URLs. Data comes
 * projected from the native views; the credentials panel (CR1) is its own
 * private request and is never stored outside this component.
 */
const API = "web/cdf/centros/";
const DELETE_CONFIRM = "¿Estás seguro de que deseas eliminar este centro? Esta acción no se puede deshacer.";
const MAPS_PREFIX = "https://maps.google.com/maps?q=";

// --- List -------------------------------------------------------------------

type Fila = {
  id: number; nombre: string; tipo: string; tipo_display: string; calle: string; telefono: string; celular: string; activo: boolean;
  urls: { detail: string; edit: string; delete: string };
};
export type CdfNoCountPage<T> = {
  count: number | null; page: number; page_size: number; pages: number | null; has_next: boolean; has_previous: boolean;
  page_range: (number | "...")[]; filters: { busqueda: string; filters: string }; results: T[];
};
export type CentrosListData = CdfNoCountPage<Fila> & {
  is_paginated: boolean; query_prefix: string; filters_config: FiltersConfig; favorites: Favorites;
  can_add: boolean; can_delete: boolean;
  urls: { list: string; add: string; actividad_create: string; informecabal: string };
  messages: CdfMessage[];
};

const filaValid = (f: unknown): f is Fila => record(f) && integer(f.id) && ["nombre", "tipo", "tipo_display", "calle", "telefono", "celular"].every((k) => text(f[k])) &&
  typeof f.activo === "boolean" && record(f.urls) && ["detail", "edit", "delete"].every((k) => internal((f.urls as Record<string, unknown>)[k]));

export function listValid(v: unknown): v is CentrosListData {
  if (!record(v) || !record(v.filters) || !record(v.favorites) || !record(v.urls)) return false;
  const u = v.urls, fav = v.favorites;
  return (v.count === null || integer(v.count)) && (v.pages === null || integer(v.pages)) && integer(v.page) && integer(v.page_size) &&
    typeof v.has_next === "boolean" && typeof v.has_previous === "boolean" && typeof v.is_paginated === "boolean" &&
    Array.isArray(v.page_range) && v.page_range.every((n) => n === "..." || integer(n)) &&
    text(v.filters.busqueda) && text(v.filters.filters) && text(v.query_prefix) &&
    Array.isArray(v.results) && v.results.every(filaValid) && filtersConfigValid(v.filters_config) &&
    text(fav.section) && internal(fav.url) && internal(fav.detail_url_template) &&
    typeof v.can_add === "boolean" && typeof v.can_delete === "boolean" &&
    ["list", "add", "actividad_create", "informecabal"].every((k) => internal(u[k])) && messagesValid(v.messages);
}

/** `listSort.js`: three-state local sort of the visible rows by their `data-*` value. */
type SortKey = "nombre" | "tipo" | "calle" | "telefono" | "activo";
const HEADERS: { title: string; key: SortKey }[] = [
  { title: "Nombre", key: "nombre" }, { title: "Tipo", key: "tipo" }, { title: "Dirección", key: "calle" },
  { title: "Teléfono", key: "telefono" }, { title: "Estado", key: "activo" },
];
const sortValue = (fila: Fila, key: SortKey) => (key === "tipo" ? fila.tipo_display : key === "activo" ? (fila.activo ? "Activo" : "Inactivo") : fila[key]);

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

/** `poncho_scroll_tablas.js` on the table card body. */
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

function CentrosTable({ data }: { data: CentrosListData }) {
  const [rows, setRows] = useState(data.results);
  const [sort, setSort] = useState<{ key: SortKey | null; direction: "asc" | "desc" | null }>({ key: null, direction: null });
  const { ref: scrollRef, className: scrollClass } = useScrollHint(String(rows.length));
  function sortBy(key: SortKey) {
    const direction = sort.key === key ? (sort.direction === "asc" ? "desc" : sort.direction === "desc" ? null : "asc") : "asc";
    setSort({ key: direction ? key : null, direction });
    if (!direction) return;
    setRows((current) => [...current].sort((a, b) => {
      const value = compare(sortValue(a, key), sortValue(b, key));
      return direction === "asc" ? value : -value;
    }));
  }
  return (
    <div className="row mt-5 max-width-100 cdf-page">
      <div className="col-12">
        <div className="card">
          <div ref={scrollRef} className={`card-body ${scrollClass}`}>
            <table className="table table-bordered table-striped projects">
              <thead>
                <tr>
                  {HEADERS.map((h) => (
                    <th key={h.key} className={`sortable ${sort.key === h.key ? `sort-${sort.direction}` : ""}`} data-column={h.key} onClick={() => sortBy(h.key)}>
                      {h.title}{" "}
                      <i className={sort.key === h.key ? `fas sort-icon fa-sort-${sort.direction === "asc" ? "up" : "down"}` : "fas fa-sort sort-icon"} />
                    </th>
                  ))}
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody id="centros-table-body">
                {rows.length ? rows.map((fila) => (
                  <tr key={fila.id}>
                    <td data-nombre={fila.nombre}>
                      <a href={fila.urls.detail} className="font-weight-bold link-handler" title="Ver detalles">{fila.nombre}</a>
                    </td>
                    <td data-tipo={fila.tipo_display}>{fila.tipo_display}</td>
                    <td data-calle={fila.calle}>{fila.calle}</td>
                    <td data-telefono={fila.telefono}>{fila.telefono} / {fila.celular}</td>
                    <td data-activo={fila.activo ? "Activo" : "Inactivo"}>
                      {fila.activo ? <span className="badge badge-success">Activo</span> : <span className="badge badge-danger">Inactivo</span>}
                    </td>
                    <td>
                      <div className="action-buttons" role="group">
                        <a href={fila.urls.detail} className="btn btn-primary" title="Ver detalle del centro">
                          <i className="fas fa-eye" />{" "}Ver
                        </a>{" "}
                        <a href={fila.urls.edit} className="btn btn-editar" title="Editar centro">
                          <i className="fas fa-edit" />{" "}Editar
                        </a>
                        {data.can_delete && <>{" "}
                          <form method="post" action={fila.urls.delete} style={{ display: "inline" }}>
                            <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
                            <button type="submit" className="btn btn-eliminar" title="Eliminar centro" data-confirm-click={DELETE_CONFIRM}
                              onClick={(e) => { if (!navigation.confirm(DELETE_CONFIRM)) e.preventDefault(); }}>
                              <i className="fas fa-trash-alt" />{" "}Eliminar
                            </button>
                          </form>
                        </>}
                      </div>
                    </td>
                  </tr>
                )) : (
                  <tr><td colSpan={6} className="text-center">No se encontraron centros.</td></tr>
                )}
              </tbody>
            </table>
            <div id="pagination-container">
              <div className="mt-2">
                {data.is_paginated && <ListPagination data={data} />}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** `components/pagination.html` with the NoCount range ("Volver"/"Continuar", no total). */
function ListPagination({ data }: { data: CentrosListData }) {
  const href = (n: number) => `?${data.query_prefix}page=${n}`;
  return (
    <ul className="pagination">
      <li className={`page-item${data.has_previous ? "" : " disabled"}`}>
        <a href={data.has_previous ? href(data.page - 1) : "#"} className="page-link">Volver</a>
      </li>
      {data.page_range.map((n, index) => (n === "..." ? (
        <li key={`gap-${index}`} className="page-item disabled"><a href="#" className="page-link">...</a></li>
      ) : (
        <li key={n} className={`page-item ${data.page === n ? "active" : ""}`}><a href={href(n)} className="page-link">{n}</a></li>
      )))}
      <li className={`page-item${data.has_next ? "" : " disabled"}`}>
        <a href={data.has_next ? href(data.page + 1) : "#"} className="page-link">Continuar</a>
      </li>
    </ul>
  );
}

export function CentrosListContent({ data }: { data: CentrosListData }) {
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/cdf.css" />
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
      <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
      <h2 className="text-center mb-4 poncho-titulo">Buscar Centro</h2>
      <Filters config={data.filters_config} action={data.urls.list} favorites={data.favorites} />
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={data.urls.list} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
          <a href={data.urls.add} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />Agregar</a>
          {data.can_add && <>
            <a href={data.urls.actividad_create} className="btn btn-primary btn-lg text-white text-nowrap">Agregar Actividad</a>
            <a href={data.urls.informecabal} className="btn btn-info btn-lg text-white text-nowrap" id="btn-cabal">Procesar Informe Cabal</a>
          </>}
        </div>
      </div>
      <CentrosTable data={data} />
    </>
  );
}

function CentrosList() {
  const state = useCdfPage(`${API}${window.location.search}`, listValid);
  return renderCdf(state, (data) => ({
    title: "Centros de Familia",
    breadcrumb: (
      <ol className="breadcrumb float-sm-right">
        <li className="breadcrumb-item"><a href={data.urls.list}>Centro de Familia</a></li>
        <li className="breadcrumb-item active">Listar</li>
      </ol>
    ),
    content: <CentrosListContent data={data} />,
  }));
}

// --- Detail -----------------------------------------------------------------

type Paginada<T> = { number: number; pages: number; page_range: number[]; previous: number | null; next: number | null; results: T[] };
type ActCurso = { id: number; actividad: string; categoria: string; dias: string[]; horariosdesde: string; horarioshasta: string; estado_display: string; detalle_url: string };
type ActOtra = { id: number; centro: string; actividad: string; categoria: string; estado_display: string; cantidad_personas: string; dias: string[]; horariosdesde: string; horarioshasta: string; precio: string | null };
const CENTRO_TEXTS = ["correo", "sitio_web", "link_redes", "telefono", "celular", "calle", "domicilio_actividad", "nombre_referente",
  "apellido_referente", "telefono_referente", "correo_referente", "numero", "localidad", "provincia", "municipio", "organizacion_asociada"] as const;
type Centro = { id: number; nombre: string; tipo: string; tipo_display: string; activo: boolean; codigo: string } & Record<(typeof CENTRO_TEXTS)[number], string | null>;
export type CentroDetailData = {
  centro: Centro;
  mapa: string | null;
  acciones: { editar_url: string; agregar_actividad_url: string; agregar_adherido_url: string | null; generar_usuario_url: string | null };
  metricas: {
    categorias: number; actividades: number; inscriptos: number; hombres: number; mujeres: number; mixtas: number; interacciones: number;
    centros_faro: null; total_recaudado: string | null; asistentes: { total: number; hombres: number; mujeres: number; espera: number };
  };
  actividades_curso: Paginada<ActCurso>;
  actividades_otras: Paginada<ActOtra>;
  search: { actividades_curso: string; actividades: string; todas_activa: boolean };
  links: { curso_prefix: string; todas_suffix: string };
  cabal: { ultimo: { fecha_subida: string; usuario: string } | null; archivos: { id: number; nombre_original: string; fecha_subida: string; url: string }[] };
  adheridos: never[];
  observaciones: never[];
  puede_ver_usuarios: boolean;
  urls: { usuarios: string };
  messages: CdfMessage[];
};

const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text);
function paginadaValid<T>(v: unknown, item: (x: unknown) => x is T): v is Paginada<T> {
  return record(v) && integer(v.number) && integer(v.pages) && Array.isArray(v.page_range) && v.page_range.every(integer) &&
    (v.previous === null || integer(v.previous)) && (v.next === null || integer(v.next)) && Array.isArray(v.results) && v.results.every(item);
}
const cursoValid = (a: unknown): a is ActCurso => record(a) && integer(a.id) && ["actividad", "categoria", "horariosdesde", "horarioshasta", "estado_display"].every((k) => text(a[k])) &&
  strings(a.dias) && internal(a.detalle_url);
const otraValid = (a: unknown): a is ActOtra => record(a) && integer(a.id) && ["centro", "actividad", "categoria", "estado_display", "cantidad_personas", "horariosdesde", "horarioshasta"].every((k) => text(a[k])) &&
  strings(a.dias) && nullableText(a.precio);

export function detailValid(v: unknown): v is CentroDetailData {
  if (!record(v) || !record(v.centro) || !record(v.acciones) || !record(v.metricas) || !record(v.search) || !record(v.links) || !record(v.cabal) || !record(v.urls)) return false;
  const c = v.centro, a = v.acciones, m = v.metricas, cab = v.cabal;
  return integer(c.id) && ["nombre", "tipo", "tipo_display", "codigo"].every((k) => text(c[k])) && typeof c.activo === "boolean" &&
    CENTRO_TEXTS.every((k) => nullableText(c[k])) &&
    (v.mapa === null || (text(v.mapa) && v.mapa.startsWith(MAPS_PREFIX))) &&
    internal(a.editar_url) && internal(a.agregar_actividad_url) && (a.agregar_adherido_url === null || internal(a.agregar_adherido_url)) &&
    (a.generar_usuario_url === null || internal(a.generar_usuario_url)) &&
    ["categorias", "actividades", "inscriptos", "hombres", "mujeres", "mixtas", "interacciones"].every((k) => integer(m[k])) &&
    m.centros_faro === null && nullableText(m.total_recaudado) && record(m.asistentes) &&
    ["total", "hombres", "mujeres", "espera"].every((k) => integer((m.asistentes as Record<string, unknown>)[k])) &&
    paginadaValid(v.actividades_curso, cursoValid) && paginadaValid(v.actividades_otras, otraValid) &&
    text(v.search.actividades_curso) && text(v.search.actividades) && typeof v.search.todas_activa === "boolean" &&
    text(v.links.curso_prefix) && v.links.curso_prefix.startsWith("?") && text(v.links.todas_suffix) && v.links.todas_suffix.startsWith("&") &&
    (cab.ultimo === null || (record(cab.ultimo) && text(cab.ultimo.fecha_subida) && text(cab.ultimo.usuario))) &&
    Array.isArray(cab.archivos) && cab.archivos.every((x) => record(x) && integer(x.id) && text(x.nombre_original) && text(x.fecha_subida) && internal(x.url)) &&
    Array.isArray(v.adheridos) && v.adheridos.length === 0 && Array.isArray(v.observaciones) && v.observaciones.length === 0 &&
    typeof v.puede_ver_usuarios === "boolean" && internal(v.urls.usuarios) && messagesValid(v.messages);
}

const dash = (v: string | null) => v || "—";
const capfirst = (v: string) => (v ? v[0].toUpperCase() + v.slice(1) : v);
const ANCHOR = "#actividades-curso-container";

function Info({ icon, label, children }: { icon: string; label: string; children: ReactNode }) {
  return (
    <div className="cdf-info-item">
      <i className={`fas ${icon}`} />
      <div>
        <div className="cdf-info-label">{label}</div>
        <div className="cdf-info-value">{children}</div>
      </div>
    </div>
  );
}

function Metric({ tone, value, label, sub }: { tone: string; value: ReactNode; label: string; sub?: string }) {
  return (
    <article className={`cdf-metric cdf-metric--${tone}`}>
      <strong className="cdf-metric-value">{value}</strong>
      <span className="cdf-metric-label">{label}</span>
      {sub !== undefined && <span className="cdf-metric-sub">{sub}</span>}
    </article>
  );
}

/** The per-tab pagination of the ficha: every page number, disabled ends inert. */
function TabPagination({ page, href }: { page: { number: number; page_range: number[]; previous: number | null; next: number | null } | null; href: (n: number) => string }) {
  const end = (label: string, target: number | null) => (
    <li className={`page-item ${target === null ? "disabled" : ""}`}>
      {target === null
        ? <a className="page-link disabled" href="#" tabIndex={-1} aria-disabled="true">{label}</a>
        : <a className="page-link" href={href(target)}>{label}</a>}
    </li>
  );
  return (
    <div className="cdf-card-foot">
      <ul className="pagination justify-content-center mb-0">
        {end("Anterior", page?.previous ?? null)}
        {page?.page_range.map((n) => (
          <li key={n} className={`page-item ${page.number === n ? "active" : ""}`}><a className="page-link" href={href(n)}>{n}</a></li>
        ))}
        {end("Siguiente", page?.next ?? null)}
      </ul>
    </div>
  );
}

function searchTo(param: "search_actividades" | "search_actividades_curso", value: string) {
  // `centrodefamilia.js`: every input reloads the page with the parameter set.
  const url = new URL(window.location.href);
  url.searchParams.set(param, value);
  url.searchParams.delete(param === "search_actividades" ? "page_act" : "page");
  navigation.assign(url.toString());
}

function Tabs({ tabs, active, onSelect }: { tabs: { id: string; pane: string; label: string }[]; active: string; onSelect: (id: string) => void }) {
  return (
    <ul className="nav cdf-tabs" role="tablist">
      {tabs.map((tab) => (
        <li key={tab.id} className="nav-item" role="presentation">
          <button className={`nav-link ${active === tab.id ? "active" : ""}`} id={tab.id} data-bs-toggle="tab" data-bs-target={`#${tab.pane}`} type="button"
            role="tab" aria-controls={tab.pane} aria-selected={active === tab.id} tabIndex={active === tab.id ? undefined : -1} onClick={() => onSelect(tab.id)}>
            {tab.label}
          </button>
        </li>
      ))}
    </ul>
  );
}

const pane = (id: string, active: string, labelledBy: string, children: ReactNode) => (
  <div className={`tab-pane fade${active === labelledBy ? " show active" : ""}`} id={id} role="tabpanel" aria-labelledby={labelledBy}>{children}</div>
);

type Acceso = { username: string; nombre_completo: string | null; email: string | null; activo: boolean; contrasena_temporal: string | null };
const accesoValid = (a: unknown): a is Acceso => record(a) && text(a.username) && nullableText(a.nombre_completo) && nullableText(a.email) &&
  typeof a.activo === "boolean" && nullableText(a.contrasena_temporal);

/** CR1 panel: one private GET, kept only in this component's memory. */
function UsuariosPanel({ endpoint }: { endpoint: string }) {
  const [state, setState] = useState<{ status: "loading" | "error" } | { status: "ready"; rows: Acceso[] }>({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    client.get(endpoint.replace(/^\/api\//, ""), { signal: controller.signal })
      .then(({ data }: { data: unknown }) => {
        if (controller.signal.aborted) return;
        setState(record(data) && Array.isArray(data.results) && data.results.every(accesoValid) ? { status: "ready", rows: data.results } : { status: "error" });
      })
      .catch(() => { if (!controller.signal.aborted) setState({ status: "error" }); });
    return () => controller.abort();
  }, [endpoint]);
  return (
    <>
      <hr className="mt-4 mb-3" />
      <div className="mb-2">
        <strong>Usuarios del centro</strong>
        <br />
        <small className="text-muted">
          Credenciales visibles solo para el referente del centro y administradores.
          La contraseña temporal se oculta automáticamente cuando el usuario la cambia.
        </small>
      </div>
      <div className="cdf-tbl-scroll">
        <table className="cdf-table">
          <thead>
            <tr><th>Usuario</th><th>Nombre</th><th>Email</th><th>Estado</th><th>Contraseña temporal</th></tr>
          </thead>
          <tbody>
            {state.status === "ready" && state.rows.map((acceso) => (
              <tr key={acceso.username}>
                <td><code>{acceso.username}</code></td>
                <td>{acceso.nombre_completo ?? "-"}</td>
                <td>{acceso.email ?? "-"}</td>
                <td>{acceso.activo ? <span className="cdf-pill cdf-pill--success">Activo</span> : <span className="cdf-pill cdf-pill--muted">Baja</span>}</td>
                <td>{acceso.contrasena_temporal ? <code>{acceso.contrasena_temporal}</code> : <span className="cdf-td-muted">Ya cambiada</span>}</td>
              </tr>
            ))}
            {state.status === "ready" && !state.rows.length && (
              <tr><td colSpan={5} className="text-center cdf-td-muted py-3">No hay usuarios generados para este centro.</td></tr>
            )}
            {state.status === "error" && (
              <tr><td colSpan={5} className="text-center cdf-td-muted py-3">No se pudieron cargar los usuarios del centro.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

function ActividadModal({ ac, close }: { ac: ActOtra; close: () => void }) {
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const body = document.body;
    body.classList.add("modal-open");
    dialog.current?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") close(); };
    document.addEventListener("keydown", onKey);
    return () => { body.classList.remove("modal-open"); document.removeEventListener("keydown", onKey); };
  }, [close]);
  return (
    <>
      <div ref={dialog} className="modal fade show" id={`modalAct${ac.id}`} tabIndex={-1} aria-labelledby={`modalActLabel${ac.id}`} aria-modal="true" role="dialog"
        style={{ display: "block" }} onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
        <div className="modal-dialog modal-dialog-scrollable modal-lg">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title" id={`modalActLabel${ac.id}`}>{ac.actividad} – {ac.centro}</h5>
              <button type="button" className="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Cerrar" onClick={close} />
            </div>
            <div className="modal-body">
              <dl className="row mb-0">
                <dt className="col-5">Cupo Total</dt>
                <dd className="col-7">{ac.cantidad_personas}</dd>
                <dt className="col-5">Días</dt>
                <dd className="col-7">
                  {ac.dias.length ? ac.dias.map((d, i) => <Fragment key={i}>{i > 0 && " "}<span className="cdf-pill cdf-pill--muted">{d}</span></Fragment>)
                    : <span className="text-muted">No especificado</span>}
                </dd>
                <dt className="col-5">Horario desde</dt>
                <dd className="col-7">{ac.horariosdesde}</dd>
                <dt className="col-5">Horario hasta</dt>
                <dd className="col-7">{ac.horarioshasta}</dd>
                <dt className="col-5">Precio</dt>
                <dd className="col-7">{ac.precio ? `$${ac.precio}` : <span className="text-muted">Gratuita</span>}</dd>
                <dt className="col-5">Estado</dt>
                <dd className="col-7">{ac.estado_display}</dd>
              </dl>
            </div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop fade show" />
    </>
  );
}

export function CentroDetailContent({ data }: { data: CentroDetailData }) {
  const { centro, acciones, metricas } = data;
  const [actTab, setActTab] = useState(data.search.todas_activa ? "tab-act-todas" : "tab-act-curso");
  const [redTab, setRedTab] = useState(centro.tipo === "faro" ? "tab-adheridos" : "tab-cabal");
  const [modal, setModal] = useState<number | null>(null);
  const abierta = data.actividades_otras.results.find((ac) => ac.id === modal);
  const curso = data.actividades_curso, otras = data.actividades_otras;
  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      <link href="https://fonts.googleapis.com/css2?family=Lora:wght@600;700&display=swap" rel="stylesheet" />
      <link rel="stylesheet" href="/static/custom/css/cdf.css" />
      <div className="cdf-page">
        <div className="cdf-hero">
          <div className="cdf-hero-block">
            <h1>
              {capfirst(centro.nombre)}{" "}
              <span className={`cdf-pill ${centro.tipo === "faro" ? "cdf-pill--gold" : "cdf-pill--teal"}`}>{centro.tipo_display}</span>{" "}
              {centro.activo ? <span className="cdf-pill cdf-pill--success">Activo</span> : <span className="cdf-pill cdf-pill--danger">Inactivo</span>}
            </h1>
            <p className="cdf-hero-sub">
              <span><i className="fas fa-barcode" />{centro.codigo}</span>{" "}
              <span><i className="fas fa-map-marker-alt" />{dash(centro.localidad)}, {dash(centro.provincia)}</span>
            </p>
          </div>
          <div className="cdf-hero-side">
            <a href={acciones.editar_url} className="cdf-btn"><i className="fas fa-pen" />Editar</a>{" "}
            <a href={acciones.agregar_actividad_url} className="cdf-btn cdf-btn--primary"><i className="fas fa-plus" />Agregar Actividad</a>
            {acciones.agregar_adherido_url && <>{" "}<a href={acciones.agregar_adherido_url} className="cdf-btn"><i className="fas fa-network-wired" />Agregar Adherido</a></>}
            {acciones.generar_usuario_url && <>{" "}<a href={acciones.generar_usuario_url} className="cdf-btn cdf-btn--gold"><i className="fas fa-user-plus" />Generar usuario</a></>}
          </div>
        </div>
        <div className="cdf-metric-grid">
          {centro.tipo === "faro" && <Metric tone="gold" value="" label="Centros Adheridos" />}
          {centro.tipo === "adherido" && <Metric tone="gold" value={`$${metricas.total_recaudado ?? ""}`} label="Monto Recaudado" />}
          <Metric tone="navy" value={metricas.categorias} label="Categorías" />
          <Metric tone="green" value={metricas.actividades} label="Actividades" />
          <Metric tone="green" value={metricas.inscriptos} label="Inscriptos" />
          <Metric tone="gold" value={metricas.asistentes.total} label="Asistentes" sub={`${metricas.asistentes.hombres} hombres · ${metricas.asistentes.mujeres} mujeres`} />
          <Metric tone="red" value={metricas.asistentes.espera} label="Lista de espera" />
        </div>
        <div className="row gx-4">
          <div className="col-lg-7 d-flex">
            <div className="cdf-card w-100">
              <div className="cdf-card-head"><i className="fas fa-circle-info" /><span>Información del centro</span></div>
              <div className="cdf-card-body">
                <div className="cdf-info-grid">
                  <Info icon="fa-layer-group" label="Tipo">{centro.tipo_display}</Info>
                  <Info icon="fa-barcode" label="Código">{centro.codigo}</Info>
                  <Info icon="fa-envelope" label="Correo electrónico">{dash(centro.correo)}</Info>
                  <Info icon="fa-globe" label="Sitio web">{dash(centro.sitio_web)}</Info>
                  <Info icon="fa-share-alt" label="Redes sociales">{dash(centro.link_redes)}</Info>
                  <Info icon="fa-building" label="Organización">{dash(centro.organizacion_asociada)}</Info>
                  <Info icon="fa-phone" label="Teléfono">{dash(centro.telefono)}</Info>
                  <Info icon="fa-mobile-alt" label="Celular">{dash(centro.celular)}</Info>
                  <Info icon="fa-file-invoice" label="Último informe CABAL">
                    {data.cabal.ultimo
                      ? <>{data.cabal.ultimo.fecha_subida}{" "}<span className="cdf-td-muted">({data.cabal.ultimo.usuario})</span></>
                      : "Sin informes vinculados"}
                  </Info>
                </div>
              </div>
            </div>
          </div>
          <div className="col-lg-5 d-flex">
            <div className="cdf-card w-100">
              <div className="cdf-card-head"><i className="fas fa-map-marker-alt" /><span>Ubicación</span></div>
              <div className="cdf-card-body">
                <div className="cdf-map mb-3" id="mapa-iframe">
                  {data.mapa ? <iframe src={data.mapa} title="Mapa del centro" allowFullScreen /> : <span>Sin mapa disponible</span>}
                </div>
                <div className="cdf-info-grid">
                  <Info icon="fa-road" label="Calle">{dash(centro.calle)} {centro.numero ?? ""}</Info>
                  <Info icon="fa-map-pin" label="Domicilio de actividades">{dash(centro.domicilio_actividad)}</Info>
                  <Info icon="fa-city" label="Municipio">{dash(centro.municipio)}</Info>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div id="actividades-curso-container" className="cdf-card">
          <div className="cdf-card-head"><i className="fas fa-person-running" /><span>Actividades</span></div>
          <Tabs active={actTab} onSelect={setActTab} tabs={[
            { id: "tab-act-curso", pane: "pane-act-curso", label: "En curso" },
            { id: "tab-act-todas", pane: "pane-act-todas", label: "Todas las actividades" },
          ]} />
          <div className="tab-content">
            {pane("pane-act-curso", actTab, "tab-act-curso", <>
              <div className="cdf-card-body pb-2 d-flex justify-content-end">
                <input id="searchCurso" defaultValue={data.search.actividades_curso} className="cdf-search" placeholder="Buscar actividad…"
                  onInput={(e) => searchTo("search_actividades_curso", e.currentTarget.value)} />
              </div>
              <div className="cdf-tbl-scroll">
                <table className="cdf-table">
                  <thead><tr><th>Actividad</th><th>Categoría</th><th>Días</th><th>Horario</th><th>Estado</th></tr></thead>
                  <tbody>
                    {curso.results.length ? curso.results.map((act) => (
                      <tr key={act.id}>
                        <td><a href={act.detalle_url}>{act.actividad}</a></td>
                        <td>{act.categoria}</td>
                        <td>{act.dias.length ? act.dias.join(" , ") : "—"}</td>
                        <td>{act.horariosdesde} - {act.horarioshasta}</td>
                        <td><span className="cdf-pill cdf-pill--teal">{act.estado_display}</span></td>
                      </tr>
                    )) : <tr><td colSpan={5} className="text-center cdf-td-muted py-3">No hay actividades en curso.</td></tr>}
                  </tbody>
                </table>
              </div>
              <TabPagination page={curso} href={(n) => `${data.links.curso_prefix}${n}${ANCHOR}`} />
            </>)}
            {pane("pane-act-todas", actTab, "tab-act-todas", <>
              <div className="cdf-card-body pb-2 d-flex justify-content-end">
                <input id="searchActividades" defaultValue={data.search.actividades} className="cdf-search" placeholder="Buscar actividad…"
                  onInput={(e) => searchTo("search_actividades", e.currentTarget.value)} />
              </div>
              <div className="cdf-tbl-scroll">
                <table id="tablaActividades" className="cdf-table">
                  <thead><tr><th>Centro</th><th>Actividad</th><th>Categoría</th><th>Estado</th><th className="text-end">Acción</th></tr></thead>
                  <tbody>
                    {otras.results.length ? otras.results.map((ac) => (
                      <tr key={ac.id}>
                        <td>{ac.centro}</td>
                        <td>{ac.actividad}</td>
                        <td>{ac.categoria}</td>
                        <td><span className="cdf-pill cdf-pill--teal">{ac.estado_display}</span></td>
                        <td className="text-end">
                          <button className="cdf-btn" data-bs-toggle="modal" data-bs-target={`#modalAct${ac.id}`} onClick={() => setModal(ac.id)}>Detalles</button>
                        </td>
                      </tr>
                    )) : <tr><td colSpan={5} className="text-center cdf-td-muted py-3">No hay actividades.</td></tr>}
                  </tbody>
                </table>
              </div>
              <TabPagination page={otras} href={(n) => `?page_act=${n}${data.links.todas_suffix}${ANCHOR}`} />
            </>)}
          </div>
        </div>
        <div className="row gx-4">
          <div className="col-lg-7 d-flex">
            <div className="cdf-card w-100">
              <div className="cdf-card-head"><i className="fas fa-user-tie" /><span>Referente</span></div>
              <div className="cdf-card-body">
                <div className="cdf-info-grid">
                  <Info icon="fa-user" label="Responsable">{centro.nombre_referente ?? ""} {centro.apellido_referente ?? ""}</Info>
                  <Info icon="fa-phone" label="Teléfono">{dash(centro.telefono_referente)}</Info>
                  <Info icon="fa-envelope" label="Correo">{dash(centro.correo_referente)}</Info>
                </div>
                {data.puede_ver_usuarios && <UsuariosPanel endpoint={data.urls.usuarios} />}
              </div>
            </div>
          </div>
          <div className="col-lg-5 d-flex">
            <div className="cdf-card w-100">
              <div className="cdf-card-head"><i className="fas fa-comment-dots" /><span>Observaciones</span></div>
              <div className="cdf-card-body">
                <div className="cdf-empty">
                  <i className="fas fa-comment-dots" />
                  <p className="cdf-empty-t">Sin observaciones</p>
                  <p className="cdf-empty-s">No hay observaciones registradas para este centro.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="cdf-card">
          <div className="cdf-card-head"><i className="fas fa-folder-open" /><span>Gestión del centro</span></div>
          <Tabs active={redTab} onSelect={setRedTab} tabs={[
            ...(centro.tipo === "faro" ? [{ id: "tab-adheridos", pane: "pane-adheridos", label: "Centros adheridos" }] : []),
            { id: "tab-cabal", pane: "pane-cabal", label: "Informes CABAL" },
          ]} />
          <div className="tab-content">
            {centro.tipo === "faro" && pane("pane-adheridos", redTab, "tab-adheridos", <>
              <div className="cdf-card-body pb-2 d-flex justify-content-end">
                <input id="filterCentros" className="cdf-search" placeholder="Buscar centro…" />
              </div>
              <div className="cdf-tbl-scroll">
                <table id="tablaCentros" className="cdf-table">
                  <thead><tr><th>Nombre</th><th>Tipo</th><th>Activo</th></tr></thead>
                  <tbody><tr><td colSpan={3} className="text-center cdf-td-muted py-3">No hay centros adheridos.</td></tr></tbody>
                </table>
              </div>
              <TabPagination page={null} href={(n) => `?page=${n}`} />
            </>)}
            {pane("pane-cabal", redTab, "tab-cabal", (
              <div id="expedientes-container">
                <div className="cdf-tbl-scroll">
                  <table className="cdf-table">
                    <thead><tr><th>Archivo</th><th>Fecha de carga</th><th className="text-end">Acción</th></tr></thead>
                    <tbody>
                      {data.cabal.archivos.length ? data.cabal.archivos.map((a) => (
                        <tr key={a.id}>
                          <td><a href={a.url}>{a.nombre_original}</a></td>
                          <td>{a.fecha_subida}</td>
                          <td className="text-end"><a href={a.url} className="cdf-btn">Ver registros</a></td>
                        </tr>
                      )) : <tr><td colSpan={3} className="text-center cdf-td-muted py-3">No hay informes CABAL con registros vinculados a este centro.</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </div>
        {abierta && <ActividadModal ac={abierta} close={() => setModal(null)} />}
      </div>
    </>
  );
}

function CentroDetail({ id }: { id: string }) {
  const state = useCdfPage(`${API}${id}/${window.location.search}`, detailValid);
  return renderCdf(state, (data) => ({
    title: data.centro.nombre,
    breadcrumb: <ol className="breadcrumb float-sm-right" />,
    content: <CentroDetailContent data={data} />,
  }));
}

// --- Route ------------------------------------------------------------------

type CentrosParams = { id?: string };

// Native URLs of the CDF centre list and detail (CDF04.01); same trailing slash.
export const cdfCentrosRoute: RouteDefinition<CentrosParams> = {
  name: "cdf-centros",
  match: (pathname) => {
    if (pathname === "/centrodefamilia/centros/") return {};
    const detail = /^\/centrodefamilia\/centros\/([1-9]\d*)\/$/.exec(pathname);
    return detail ? { id: detail[1] } : null;
  },
  render: ({ id }) => (id ? <CentroDetail id={id} /> : <CentrosList />),
};
