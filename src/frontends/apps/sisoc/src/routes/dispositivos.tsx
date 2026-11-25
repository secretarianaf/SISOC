/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { Fragment, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useLegacyScrollHints } from "../useLegacyScrollHints";
import { Filters, filtersConfigValid, type Favorites, type FiltersConfig } from "./cdfFilters";
import { favoritesValid, SearchActions } from "./dispositivosShared";
import { Mapa } from "./dispositivosMapa";
import { integer, internal, messagesValid, nullableText, record, renderCdf, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import { Breadcrumb, breadcrumbValid, type Breadcrumbs } from "./MainFrame";
import { DETALLE_CSS } from "./dispositivosDetalleCss";
import type { RouteDefinition } from "./types";

/**
 * DS02.01 (contract DS01-DS02, #2785): `dispositivos_list.html` and
 * `dispositivos_detail.html` on their native URLs. Data comes projected from
 * the native views through `/api/web/dispositivos/` (G1 v1).
 */
const API = "web/dispositivos/";


// --- List -------------------------------------------------------------------

type Fila = {
  id: number; nombre_institucion: string; tipo_dispositivo_display: string; provincia: string; municipio: string;
  urls: { detail: string; edit: string; delete: string };
};
export type DispositivosListData = {
  count: number; page: number; page_size: number; pages: number; filters: { busqueda: string; filters: string };
  results: Fila[]; is_paginated: boolean; has_next: boolean; has_previous: boolean; page_range: (number | "…" | "...")[]; query_prefix: string;
  titulo: string; filters_config: FiltersConfig; favorites: Favorites; add_url: string | null; map_url: string | null;
  urls: { list: string; reset: string }; can_change: boolean; can_delete: boolean; messages: CdfMessage[];
};

const filaValid = (f: unknown): f is Fila => record(f) && integer(f.id) &&
  ["nombre_institucion", "tipo_dispositivo_display", "provincia", "municipio"].every((k) => text(f[k])) &&
  record(f.urls) && ["detail", "edit", "delete"].every((k) => internal((f.urls as Record<string, unknown>)[k]));

export function listValid(v: unknown): v is DispositivosListData {
  if (!record(v) || !record(v.filters) || !record(v.urls)) return false;
  return ["count", "page", "page_size", "pages"].every((k) => integer(v[k])) && text(v.filters.busqueda) && text(v.filters.filters) &&
    Array.isArray(v.results) && v.results.every(filaValid) && typeof v.is_paginated === "boolean" &&
    typeof v.has_next === "boolean" && typeof v.has_previous === "boolean" &&
    Array.isArray(v.page_range) && v.page_range.every((n) => n === "…" || n === "..." || integer(n)) && text(v.query_prefix) &&
    text(v.titulo) && filtersConfigValid(v.filters_config) && favoritesValid(v.favorites) &&
    (v.add_url === null || internal(v.add_url)) && (v.map_url === null || internal(v.map_url)) &&
    internal(v.urls.list) && internal(v.urls.reset) && typeof v.can_change === "boolean" && typeof v.can_delete === "boolean" &&
    messagesValid(v.messages);
}

/** `components/pagination.html` with `page_obj|compact_page_range` and the results line. */
function ListPagination({ data }: { data: DispositivosListData }) {
  const href = (n: number) => `?${data.query_prefix}page=${n}`;
  return (
    <div className="mt-2">
      {data.is_paginated && (
        <ul className="pagination">
          <li className={`page-item${data.has_previous ? "" : " disabled"}`}>
            <a href={data.has_previous ? href(data.page - 1) : "#"} className="page-link">Volver</a>
          </li>
          {data.page_range.map((n, i) => (n === "…" || n === "..." ? (
            <li key={`gap-${i}`} className="page-item disabled"><a href="#" className="page-link">...</a></li>
          ) : (
            <li key={n} className={`page-item ${data.page === n ? "active" : ""}`}><a href={href(n)} className="page-link">{n}</a></li>
          )))}
          <li className={`page-item${data.has_next ? "" : " disabled"}`}>
            <a href={data.has_next ? href(data.page + 1) : "#"} className="page-link">Continuar</a>
          </li>
        </ul>
      )}
      {data.results.length > 0 && <p className="text-center text-muted mb-0 mt-1">Se encontraron {data.count} resultados</p>}
    </div>
  );
}

export const mapLink = (mapUrl: string, id: number) => `${mapUrl}${mapUrl.includes("?") ? "&" : "?"}dispositivo=${id}`;

export function DispositivosListContent({ data }: { data: DispositivosListData }) {
  const { cardRef, tableRef, classes } = useLegacyScrollHints(String(data.results.length));
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <div className="list-container">
        <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
        <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
        <h2 className="text-center mb-4 poncho-titulo">{data.titulo}</h2>
        <Filters config={data.filters_config} action={data.urls.list} favorites={data.favorites} />
        <SearchActions mapUrl={data.map_url} mapText="Mapa de dispositivos" resetUrl={data.urls.reset} addUrl={data.add_url} addText="Agregar dispositivo" />
        <div className="row mt-5">
          <div className="col-12">
            <div className="card comedor-table-card">
              <div ref={cardRef} className={`card-body ${classes.card}`}>
                <div ref={tableRef} className={`table-responsive-lg ${classes.table}`}>
                  <table className="table table-comedor-moderno">
                    <thead>
                      <tr><th>Institución</th><th>Tipo</th><th>Provincia</th><th>Municipio</th><th>Acciones</th></tr>
                    </thead>
                    <tbody>
                      {data.results.length ? data.results.map((fila) => (
                        <tr key={fila.id}>
                          <td>{fila.nombre_institucion}</td>
                          <td>{fila.tipo_dispositivo_display}</td>
                          <td>{fila.provincia}</td>
                          <td>{fila.municipio}</td>
                          <td>
                            <div className="comedor-actions">
                              {data.map_url && (
                                <a href={mapLink(data.map_url, fila.id)} className="btn btn-ver" title="Ver ubicación en el mapa">
                                  <i className="fas fa-map-marker-alt" aria-hidden="true" />{" "}Ver en mapa{" "}
                                </a>
                              )}
                              <a href={fila.urls.detail} className="btn btn-ver" title="Ver detalles"><i className="fas fa-eye" />{" "}Ver detalle{" "}</a>
                              {data.can_change && <a href={fila.urls.edit} className="btn btn-editar" title="Editar"><i className="fas fa-edit" />{" "}Editar{" "}</a>}
                              {data.can_delete && <a href={fila.urls.delete} className="btn btn-eliminar" title="Eliminar"><i className="fas fa-trash-alt" />{" "}Eliminar{" "}</a>}
                            </div>
                          </td>
                        </tr>
                      )) : (
                        <tr>
                          <td colSpan={5}>
                            <div className="no-data-message">
                              <h3>No se encontraron dispositivos</h3>
                              <p>No hay dispositivos que coincidan con los criterios de búsqueda.</p>
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
        <ListPagination data={data} />
      </div>
    </>
  );
}

function DispositivosList() {
  const state = useCdfPage(`${API}listado/${window.location.search}`, listValid);
  return renderCdf(state, (data) => ({ title: "Dispositivos", breadcrumb: null, content: <DispositivosListContent data={data} /> }));
}

// --- Detail -----------------------------------------------------------------

type Archivo = { name: string; url: string };
type Item =
  | { label: string; kind: "text"; wide: boolean; value: string }
  | { label: string; kind: "list"; wide: boolean; value: string[] }
  | { label: string; kind: "file"; wide: boolean; value: Archivo | null };
type Seccion = { titulo: string; icono: string; items: Item[] };
export type DispositivoDetailData = {
  id: number; nombre_institucion: string;
  meta: { tipo: string | null; provincia: string | null; municipio: string | null; actualizado: string | null };
  can_change: boolean; edit_url: string; breadcrumb: Breadcrumbs; show_map: boolean; mapa_query: string | null;
  detalle_secciones: Seccion[]; messages: CdfMessage[];
};

const itemValid = (i: unknown): i is Item => record(i) && text(i.label) && typeof i.wide === "boolean" && (
  (i.kind === "text" && text(i.value)) ||
  (i.kind === "list" && Array.isArray(i.value) && i.value.every(text)) ||
  (i.kind === "file" && (i.value === null || (record(i.value) && text(i.value.name) && text(i.value.url)))));

export function detailValid(v: unknown): v is DispositivoDetailData {
  if (!record(v) || !record(v.meta)) return false;
  const m = v.meta;
  return integer(v.id) && text(v.nombre_institucion) && ["tipo", "provincia", "municipio", "actualizado"].every((k) => nullableText(m[k])) &&
    typeof v.can_change === "boolean" && internal(v.edit_url) && breadcrumbValid(v.breadcrumb) && typeof v.show_map === "boolean" &&
    nullableText(v.mapa_query) && Array.isArray(v.detalle_secciones) &&
    v.detalle_secciones.every((s) => record(s) && text(s.titulo) && text(s.icono) && Array.isArray(s.items) && s.items.every(itemValid)) &&
    messagesValid(v.messages);
}

const HEADER_CLASSES = ["informacion", "funcionamiento", "ubicacion", "responsables", "trabajadores", "nomina", "formularios", "prestaciones", "relevamientos"];
const CLOSED_WIDTH = 60;

function Items({ items }: { items: Item[] }) {
  const files = items.filter((i): i is Extract<Item, { kind: "file" }> => i.kind === "file" && i.value !== null);
  // Native quirk: the template opens the "Archivos adjuntos" block on `forloop.first` of
  // *all* items, so the divider, label and grid only appear when the first item is a file.
  const wrapped = items[0]?.kind === "file" && items[0].value !== null;
  const cards = files.map((item, i) => {
    const file = item.value as Archivo;
    const pdf = file.name.slice(-4).toLowerCase() === ".pdf";
    // The template's indentation leaves a space before each inline card.
    return (
      <Fragment key={i}>{" "}
        <a href={file.url} target="_blank" rel="noopener" className="doc-card-ro" title={item.label}>
          <i className={`doc-card-icon fas ${pdf ? "fa-file-pdf pdf" : "fa-file-image img"}`} />
          <span className="doc-card-name">{file.name}</span>
          <i className="fas fa-external-link-alt" style={{ fontSize: "10px", opacity: 0.5 }} />
        </a>
      </Fragment>
    );
  });
  return (
    <>
      <div className="row">
        {items.filter((i) => i.kind !== "file").map((item, index) => (
          <div key={index} className={item.wide ? "col-md-12" : item.kind === "list" ? "col-md-6" : "col-md-4"}>
            <div className="detail-item-label">{item.label}</div>
            {item.kind === "list" ? (item.value.length ? (
              <div className="chip-list">{item.value.map((chip, i) => <span key={i} className="chip">{chip}</span>)}</div>
            ) : <div className="detail-item-value empty">—</div>) : (
              <div className={`detail-item-value ${item.value === "-" ? "empty" : ""}`}>{item.value === "-" ? "—" : item.value as string}</div>
            )}
          </div>
        ))}
      </div>
      {files.length > 0 && (wrapped ? <>
        <div className="docs-section-divider" />
        <div className="docs-section-label"><i className="fas fa-paperclip mr-1" />Archivos adjuntos</div>
        <div className="doc-cards-grid">{cards}</div>
      </> : cards)}
    </>
  );
}

/** The horizontal accordion of `dispositivos_detail.html` (its inline script). */
function Accordion({ secciones }: { secciones: Seccion[] }) {
  const [open, setOpen] = useState(0);
  const [mobile, setMobile] = useState(() => window.innerWidth <= 768);
  const [loading, setLoading] = useState(true);
  const accordion = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const resize = () => setMobile(window.innerWidth <= 768);
    window.addEventListener("resize", resize);
    const timer = window.setTimeout(() => setLoading(false), 250);
    return () => { window.removeEventListener("resize", resize); window.clearTimeout(timer); };
  }, []);
  useLayoutEffect(() => {
    if (accordion.current) accordion.current.style.height = mobile ? "auto" : "400px";
  }, [mobile]);
  const openWidth = `calc(100% - ${(secciones.length - 1) * CLOSED_WIDTH}px)`;
  return (
    <div className={`accordion-shell${loading && secciones.length ? " is-loading" : ""}`}>
      <div className="accordion-loader" aria-live="polite" aria-busy="true">
        <div className="d-flex align-items-center gap-2">
          <div className="spinner-border text-warning" role="status"><span className="visually-hidden">Cargando...</span></div>
          <span className="fw-semibold">Cargando información...</span>
        </div>
      </div>
      <div ref={accordion} className="accordion-horizontal border rounded shadow shadow-sm mb-3">
        {secciones.map((seccion, index) => (
          <div key={index} className={`accordion-panel${open === index ? " open" : ""}`}
            style={mobile ? { width: "100%", height: "auto" } : { width: open === index ? openWidth : `${CLOSED_WIDTH}px`, height: "100%" }}>
            <button type="button" className={`accordion-header h5 accordion-header--${HEADER_CLASSES[index % HEADER_CLASSES.length]}`}
              aria-controls={`dispositivo-accordion-panel-${index + 1}`} aria-expanded={open === index ? "true" : "false"}
              onClick={() => setOpen(index)}>
              {seccion.titulo}
            </button>
            <div className="accordion-content" id={`dispositivo-accordion-panel-${index + 1}`} role="region">
              <div className="mb-3 d-flex align-items-center gap-2">
                <i className={seccion.icono} />
                <h4 className="mb-0">{seccion.titulo}</h4>
              </div>
              <Items items={seccion.items} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Meta({ meta }: { meta: DispositivoDetailData["meta"] }) {
  return (
    <div className="detail-page-meta">
      {meta.tipo !== null && <span>{meta.tipo}</span>}
      {meta.provincia !== null && <>{" "}· <span>{meta.provincia}</span></>}
      {meta.municipio !== null && <>{" "}· <span>{meta.municipio}</span></>}
      {meta.actualizado !== null && <>{" "}· Actualizado el {meta.actualizado}</>}
    </div>
  );
}

export function DispositivoDetailContent({ data }: { data: DispositivoDetailData }) {
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/comedor_detail.css" />
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/dispositivoFormModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/nuevo_comedor.css" />
      <style>{DETALLE_CSS}</style>
      {data.show_map && (
        <section className="card mb-3" aria-label="Ubicación en el mapa">
          <div className="card-body">
            <h3 className="h5">Ubicación en el mapa</h3>
            <iframe id="dispositivo-mapa" title="Ubicación del dispositivo" width="100%" height="320" loading="lazy" allowFullScreen
              src={`https://www.google.com/maps?q=${data.mapa_query || "Argentina"}&output=embed`} />
          </div>
        </section>
      )}
      <div className="detail-page-header">
        <div>
          <h1 className="detail-page-title">{data.nombre_institucion}</h1>
          <Meta meta={data.meta} />
        </div>
        <div className="d-flex gap-2 flex-shrink-0 flex-wrap">
          {data.can_change && <a href={data.edit_url} className="btn btn-warning btn-sm"><i className="fas fa-pencil-alt mr-1" /> Editar{" "}</a>}
        </div>
      </div>
      <Accordion secciones={data.detalle_secciones} />
      {data.detalle_secciones.map((seccion, index) => (
        <div key={index} className="section-card" style={{ marginBottom: "16px" }}>
          <div className="section-header" style={{ cursor: "default" }}>
            <div className="section-header-left">
              <div className="section-icon"><i className={seccion.icono} /></div>
              <div className="section-title-group"><h3 className="section-title">{seccion.titulo}</h3></div>
            </div>
          </div>
          <div className="section-body-detail"><Items items={seccion.items} /></div>
        </div>
      ))}
    </>
  );
}

function DispositivoDetail({ id }: { id: string }) {
  const state = useCdfPage(`${API}${id}/`, detailValid);
  return renderCdf(state, (data) => ({
    title: data.nombre_institucion,
    heading: "Dispositivos",
    breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <DispositivoDetailContent data={data} />,
  }));
}

// --- Route ------------------------------------------------------------------

type DispositivosParams = { id?: string; mapa?: boolean };

// Native URLs of the Dispositivos list, legajo (DS02.01) and map (DS01.01); same trailing slash.
export const dispositivosRoute: RouteDefinition<DispositivosParams> = {
  name: "dispositivos",
  match: (pathname) => {
    if (pathname === "/dispositivos/") return {};
    if (pathname === "/dispositivos/mapa/") return { mapa: true };
    const detail = /^\/dispositivos\/([1-9]\d*)\/$/.exec(pathname);
    return detail ? { id: detail[1] } : null;
  },
  render: ({ id, mapa }) => (mapa ? <Mapa /> : id ? <DispositivoDetail id={id} /> : <DispositivosList />),
};
