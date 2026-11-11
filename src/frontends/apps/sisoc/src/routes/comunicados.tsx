/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { Fragment } from "react";
import { InsumosToastList } from "../InsumosToast";
import { safeInternalPath } from "../webAccess";
import { Pagination } from "./listControls";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * CM03.01 published comunicados: `comunicado_list.html` (`search_bar.html` in
 * simple mode, the cards and `pagination.html`) and the reader variant of
 * `comunicado_detail.html`. Data comes from `/api/web/comedores/comunicados/`,
 * which runs the native views; dates and the card summary arrive formatted.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Card = { id: number; titulo: string; cuerpo_resumen: string; destacado: boolean; fecha_publicacion: string; creador: string; adjuntos_count: number; detail_url: string };
type Page = { is_paginated: boolean; number: number; num_pages: number; count: number; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };
export type ComunicadoListData = { results: Card[]; page: Page; filtro_titulo: string; can_manage: boolean; gestion_url: string | null; messages: Message[] };
type Adjunto = { id: number; nombre_original: string; url: string };
export type ComunicadoDetailData = {
  id: number; titulo: string; cuerpo: string; estado: string; estado_label: string; destacado: boolean;
  fecha_publicacion: string; fecha_vencimiento: string; esta_vencido: boolean; creador: string; adjuntos: Adjunto[];
  can_manage: boolean; permisos: { editar: boolean; publicar: boolean; archivar: boolean; eliminar: boolean }; messages: Message[];
};

const API = "web/comedores/comunicados/";
const LIST = "/comunicados/";
const LEVELS = ["success", "error", "warning", "info"];
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const bool = (v: unknown): v is boolean => typeof v === "boolean";
const messagesValid = (v: unknown) => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));

export function listValid(v: unknown): v is ComunicadoListData {
  if (!record(v) || !record(v.page)) return false;
  const p = v.page;
  return Array.isArray(v.results) && v.results.every((c) => record(c) && integer(c.id) && text(c.titulo) && text(c.cuerpo_resumen) && bool(c.destacado) &&
      text(c.fecha_publicacion) && text(c.creador) && integer(c.adjuntos_count) && internal(c.detail_url)) &&
    bool(p.is_paginated) && integer(p.number) && integer(p.num_pages) && integer(p.count) &&
    (p.previous === null || integer(p.previous)) && (p.next === null || integer(p.next)) &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || integer(n)) && text(p.query_without_page) &&
    text(v.filtro_titulo) && bool(v.can_manage) && (v.gestion_url === null || internal(v.gestion_url)) && messagesValid(v.messages);
}

export function detailValid(v: unknown): v is ComunicadoDetailData {
  if (!record(v) || !record(v.permisos)) return false;
  const p = v.permisos;
  return integer(v.id) && text(v.titulo) && text(v.cuerpo) && text(v.estado) && text(v.estado_label) && bool(v.destacado) &&
    text(v.fecha_publicacion) && text(v.fecha_vencimiento) && bool(v.esta_vencido) && text(v.creador) &&
    Array.isArray(v.adjuntos) && v.adjuntos.every((a) => record(a) && integer(a.id) && text(a.nombre_original) && text(a.url)) &&
    bool(v.can_manage) && ["editar", "publicar", "archivar", "eliminar"].every((k) => bool(p[k])) && messagesValid(v.messages);
}

// --- List (`comunicado_list.html`) -----------------------------------------

/** `search_bar.html` in simple mode with `search_name='titulo'` and its `additional_buttons`. */
function SearchBar({ data }: { data: ComunicadoListData }) {
  return <>
    <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
    <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
    <h2 className="text-center mb-4 poncho-titulo">Buscar comunicado</h2>
    <form method="GET" action="" id="simple-search-form">
      <div className="poncho-search poncho-search--solo"><div className="poncho-search__box">
        <input type="search" id="ajax-search-input" name="titulo" className="poncho-search__input" placeholder="Buscar por título..."
          title="Buscar por título." autoComplete="off" aria-label="Buscar por título." defaultValue={data.filtro_titulo} />
        <button type="submit" className="poncho-search__go" aria-label="Buscar"><i className="fas fa-search" aria-hidden="true" /></button>
      </div></div>
      <div className="poncho-search__meta"><span id="ajax-results-count" /></div>
      <div id="ajax-loading-indicator" className="text-center py-3" style={{ display: "none" }}>
        <div className="spinner-border" role="status"><span className="sr-only">Cargando...</span></div>
      </div>
    </form>
    <div className="row mt-3"><div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
      <a href={LIST} className="poncho-btn poncho-btn--neutro">Resetear</a>
      {data.can_manage && data.gestion_url && (
        <a href={data.gestion_url} className="poncho-btn poncho-btn--neutro" title="Gestionar comunicados">Gestionar</a>
      )}
    </div></div>
  </>;
}

function ComunicadoCard({ card }: { card: Card }) {
  const detail = safeInternalPath(card.detail_url) ?? "/";
  return (
    <div className="card comunicado-card mb-3 mt-4" style={card.destacado ? { borderLeft: "4px solid #e7ba61" } : undefined}>
      <div className="card-body">
        {card.destacado && (
          <div className="mb-2">
            <span style={{ color: "#e7ba61", fontSize: "12px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
              <i className="fas fa-star me-1" />{" "}Destacado
            </span>
          </div>
        )}
        <div className="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
          <h5 className="card-title mb-0"><a href={detail} className="text-decoration-none">{card.titulo}</a></h5>
          <p className="card-text comunicado-meta small mb-0" style={{ color: "#9ca3af" }}>
            <i className="fas fa-calendar" />{" "}{card.fecha_publicacion}{" "}
            <span className="ms-3"><i className="fas fa-user" />{" "}{card.creador}{" "}</span>
            {card.adjuntos_count > 0 && <span className="ms-3"><i className="fas fa-paperclip" />{" "}{card.adjuntos_count} adjunto(s){" "}</span>}
          </p>
        </div>
        <p className="card-text mb-3" style={{ color: "#d1d5db" }}>{card.cuerpo_resumen}</p>
        <a href={detail} className="btn btn-sm btn-outline-primary">Leer más{" "}<i className="fas fa-arrow-right" /></a>
      </div>
    </div>
  );
}

export function ComunicadoListContent({ data }: { data: ComunicadoListData }) {
  const { page } = data;
  return <>
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <InsumosToastList messages={data.messages} />
    <div className="mt-4">
      <SearchBar data={data} />
      {data.results.length ? data.results.map((card) => <ComunicadoCard key={card.id} card={card} />) : (
        <div className="card comunicado-card mt-4">
          <div className="card-body text-center py-5">
            <i className="fas fa-newspaper fa-3x mb-3" style={{ color: "#6b7280" }} />
            <p className="mb-0" style={{ color: "#9ca3af" }}>No hay comunicados publicados.</p>
          </div>
        </div>
      )}
      {page.is_paginated && (
        <Pagination paginated number={page.number} previous={page.previous} next={page.next} range={page.range}
          href={(n) => `?${page.query_without_page}page=${n}`} count={page.count} />
      )}
    </div>
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, listValid);
  return renderMain(state, "Cargando comunicados…", (data) => ({
    title: "Comunicados",
    heading: "Comunicados",
    breadcrumb: null,
    content: <ComunicadoListContent data={data} />,
  }));
}

// --- Detail (`comunicado_detail.html`) -------------------------------------

const BADGES: Record<string, string> = { borrador: "badge bg-secondary", publicado: "badge bg-success", archivado: "badge bg-dark" };

/** Django `linebreaks`: blank lines split paragraphs, single newlines become `<br>`. */
function Linebreaks({ value }: { value: string }) {
  const paragraphs = value.replace(/\r\n|\r/g, "\n").split(/\n{2,}/);
  return <>{paragraphs.map((p, i) => <Fragment key={i}>{i > 0 && "\n\n"}<p>{p.split("\n").map((line, j) => <Fragment key={j}>{j > 0 && <br />}{line}</Fragment>)}</p></Fragment>)}</>;
}

export function ComunicadoDetailContent({ data }: { data: ComunicadoDetailData }) {
  return <>
    <InsumosToastList messages={data.messages} />
    <div className="container mt-4">
      <div className="mb-4" />
      <div className={`card ${data.destacado ? "border-warning" : ""}`}>
        {data.destacado && <div className="card-header bg-warning text-dark"><i className="fas fa-star" />{" "}Comunicado Destacado</div>}
        <div className="card-header d-flex justify-content-between align-items-center">
          <div><h4 className="mb-0">{data.titulo}</h4></div>
          <div>{BADGES[data.estado] && <span className={BADGES[data.estado]}>{data.estado_label}</span>}</div>
        </div>
        <div className="card-body">
          <div className="text-muted small mb-4">
            <span><i className="fas fa-user" />{" "}{data.creador}{" "}</span>
            {data.fecha_publicacion && <span className="ms-3"><i className="fas fa-calendar" />{" "}Publicado: {data.fecha_publicacion}{" "}</span>}
            {data.fecha_vencimiento && (
              <span className="ms-3"><i className="fas fa-clock" />{" "}Vence: {data.fecha_vencimiento}{" "}
                {data.esta_vencido && <span className="badge bg-danger">Vencido</span>}</span>
            )}
          </div>
          <div className="comunicado-contenido mb-4"><Linebreaks value={data.cuerpo} /></div>
          {data.adjuntos.length > 0 && <>
            <hr />
            <h6><i className="fas fa-paperclip" />{" "}Archivos Adjuntos</h6>
            <ul className="list-unstyled">
              {data.adjuntos.map((a) => (
                <li key={a.id} className="mb-2">
                  <a href={a.url} target="_blank" className="btn btn-sm btn-outline-primary"><i className="fas fa-download" />{" "}{a.nombre_original}</a>
                </li>
              ))}
            </ul>
          </>}
        </div>
      </div>
    </div>
  </>;
}

function DetailPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/`, detailValid);
  return renderMain(state, "Cargando comunicado…", (data) => ({
    title: data.titulo,
    heading: "Comunicado",
    breadcrumb: null,
    content: <ComunicadoDetailContent data={data} />,
  }));
}

type Params = { id?: string };
const DETAIL = /^\/comunicados\/ver\/([0-9]+)\/$/;

export const comunicadosRoute: RouteDefinition<Params> = {
  name: "comedores-comunicados",
  match(pathname) {
    if (pathname === LIST) return {};
    const detail = DETAIL.exec(pathname);
    return detail ? { id: detail[1] } : null;
  },
  render({ id }) {
    return id ? <DetailPage id={id} /> : <ListPage />;
  },
};
