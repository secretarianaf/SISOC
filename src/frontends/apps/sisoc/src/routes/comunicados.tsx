/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { Fragment, useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { safeInternalPath } from "../webAccess";
import { Pagination } from "./listControls";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { ComunicadoFormPage } from "./comunicadosForm";
import { ComunicadoEliminarPage } from "./comunicadosEliminar";
import type { RouteDefinition } from "./types";

/**
 * CM03.01 published comunicados: `comunicado_list.html` (`search_bar.html` in
 * simple mode, the cards and `pagination.html`) and `comunicado_detail.html`;
 * CM02.01 management list (`comunicado_gestion_list.html`) and the manager
 * footer of the detail. Data comes from `/api/web/comedores/comunicados/`,
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
  fecha_creacion: string; modificado_por: string;
  can_manage: boolean; permisos: { editar: boolean; publicar: boolean; archivar: boolean; eliminar: boolean }; messages: Message[];
};
type Acciones = { editar: boolean; publicar: boolean; archivar: boolean; destacado: boolean };
type Fila = {
  id: number; titulo: string; titulo_corto: string; tipo: string; estado: string; esta_vencido: boolean; destacado: boolean;
  fecha_creacion: string; fecha_publicacion: string; creador: string; acciones: Acciones;
};
export type ComunicadoGestionData = {
  results: Fila[]; page: Page; filtros: { titulo: string; estado: string; tipo: string };
  flags: { can_create: boolean; is_admin: boolean; es_tecnico: boolean }; mailing_url: string | null; messages: Message[];
};

const API = "web/comedores/comunicados/";
const LIST = "/comunicados/";
const LEVELS = ["success", "error", "warning", "info"];
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const bool = (v: unknown): v is boolean => typeof v === "boolean";
const messagesValid = (v: unknown) => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));

const pageValid = (p: unknown) => record(p) && bool(p.is_paginated) && integer(p.number) && integer(p.num_pages) && integer(p.count) &&
  (p.previous === null || integer(p.previous)) && (p.next === null || integer(p.next)) &&
  Array.isArray(p.range) && p.range.every((n) => n === "…" || integer(n)) && text(p.query_without_page);

export function listValid(v: unknown): v is ComunicadoListData {
  if (!record(v)) return false;
  return Array.isArray(v.results) && v.results.every((c) => record(c) && integer(c.id) && text(c.titulo) && text(c.cuerpo_resumen) && bool(c.destacado) &&
      text(c.fecha_publicacion) && text(c.creador) && integer(c.adjuntos_count) && internal(c.detail_url)) &&
    pageValid(v.page) && text(v.filtro_titulo) && bool(v.can_manage) && (v.gestion_url === null || internal(v.gestion_url)) && messagesValid(v.messages);
}

export function detailValid(v: unknown): v is ComunicadoDetailData {
  if (!record(v) || !record(v.permisos)) return false;
  const p = v.permisos;
  return integer(v.id) && text(v.titulo) && text(v.cuerpo) && text(v.estado) && text(v.estado_label) && bool(v.destacado) &&
    text(v.fecha_publicacion) && text(v.fecha_vencimiento) && bool(v.esta_vencido) && text(v.creador) &&
    text(v.fecha_creacion) && text(v.modificado_por) &&
    Array.isArray(v.adjuntos) && v.adjuntos.every((a) => record(a) && integer(a.id) && text(a.nombre_original) && text(a.url)) &&
    bool(v.can_manage) && ["editar", "publicar", "archivar", "eliminar"].every((k) => bool(p[k])) && messagesValid(v.messages);
}

export function gestionValid(v: unknown): v is ComunicadoGestionData {
  if (!record(v) || !record(v.filtros) || !record(v.flags)) return false;
  const f = v.filtros, g = v.flags;
  return Array.isArray(v.results) && v.results.every((r) => record(r) && integer(r.id) && text(r.titulo) && text(r.titulo_corto) &&
      text(r.tipo) && text(r.estado) && bool(r.esta_vencido) && bool(r.destacado) && text(r.fecha_creacion) && text(r.fecha_publicacion) &&
      text(r.creador) && record(r.acciones) && ["editar", "publicar", "archivar", "destacado"].every((k) => bool((r.acciones as Record<string, unknown>)[k]))) &&
    pageValid(v.page) && text(f.titulo) && text(f.estado) && text(f.tipo) &&
    bool(g.can_create) && bool(g.is_admin) && bool(g.es_tecnico) && (v.mailing_url === null || internal(v.mailing_url)) && messagesValid(v.messages);
}

/** Full-page actions of the native forms; replaceable in tests. */
export const comunicadosNavigation = {
  confirm: (message: string) => window.confirm(message),
  submit: (form: HTMLFormElement) => form.submit(),
  assign: (to: string) => window.location.assign(to),
};

// --- List (`comunicado_list.html`) -----------------------------------------

type SearchProps = { placeholder: string; query: string; reset: string; children?: ReactNode };

/** `search_bar.html` in simple mode with `search_name='titulo'`; `children` are its add and additional buttons. */
function SearchBar({ placeholder, query, reset, children }: SearchProps) {
  return <>
    <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
    <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
    <h2 className="text-center mb-4 poncho-titulo">Buscar comunicado</h2>
    <form method="GET" action="" id="simple-search-form">
      <div className="poncho-search poncho-search--solo"><div className="poncho-search__box">
        <input type="search" id="ajax-search-input" name="titulo" className="poncho-search__input" placeholder={placeholder}
          title="Buscar por título." autoComplete="off" aria-label="Buscar por título." defaultValue={query} />
        <button type="submit" className="poncho-search__go" aria-label="Buscar"><i className="fas fa-search" aria-hidden="true" /></button>
      </div></div>
      <div className="poncho-search__meta"><span id="ajax-results-count" /></div>
      <div id="ajax-loading-indicator" className="text-center py-3" style={{ display: "none" }}>
        <div className="spinner-border" role="status"><span className="sr-only">Cargando...</span></div>
      </div>
    </form>
    <div className="row mt-3"><div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
      <a href={reset} className="poncho-btn poncho-btn--neutro">Resetear</a>
      {children}
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
      <SearchBar placeholder="Buscar por título..." query={data.filtro_titulo} reset={LIST}>
        {data.can_manage && data.gestion_url && (
          <a href={data.gestion_url} className="poncho-btn poncho-btn--neutro" title="Gestionar comunicados">Gestionar</a>
        )}
      </SearchBar>
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

// --- Management list (`comunicado_gestion_list.html`) -----------------------

const GESTION = "/comunicados/gestion/";
const PUBLICAR = "¿Publicar este comunicado?";
const ARCHIVAR = "¿Archivar este comunicado?";

const UNCERTAIN = "No se pudo confirmar el resultado. Actualice la página antes de volver a intentar.";

/**
 * A native POST form (`{% csrf_token %}`) whose button may ask `data-confirm-click` first (`base.js`).
 * CM02.03: the submit goes once to the web API (`web/comedores/comunicados/<id>/<action>/`), which runs the native
 * view; the confirmed redirect is a full-page navigation (the message waits in the queue). An unconfirmed
 * outcome is reported and never resent.
 */
function ActionForm({ action, endpoint, className, title, confirm, children }: { action: string; endpoint: string; className: string; title?: string; confirm?: string; children: ReactNode }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || error) return;
    if (confirm && !comunicadosNavigation.confirm(confirm)) return;
    busy.current = true; setPending(true);
    const outcome = await postForm(endpoint, new URLSearchParams());
    if (outcome.kind === "redirect") { comunicadosNavigation.assign(outcome.url); return; }
    const detail = outcome.kind === "forbidden" && record(outcome.data) && text(outcome.data.detail) ? outcome.data.detail : UNCERTAIN;
    setError(detail); setPending(false);
  }
  return (
    <form method="post" action={action} className="d-inline" onSubmit={submit}>
      <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
      <button type="submit" className={className} title={title} data-confirm-click={confirm} disabled={pending || !!error}>{children}</button>
      {error && <span role="alert" className="text-danger small">{error}</span>}
    </form>
  );
}

function EstadoBadge({ fila }: { fila: Fila }) {
  if (fila.estado === "borrador") return <span className="badge bg-secondary">Borrador</span>;
  if (fila.estado === "publicado") return fila.esta_vencido ? <span className="badge bg-danger">Vencido</span> : <span className="badge bg-success">Publicado</span>;
  if (fila.estado === "archivado") return <span className="badge bg-dark">Archivado</span>;
  return null;
}

function GestionRow({ fila }: { fila: Fila }) {
  const ver = `/comunicados/ver/${fila.id}/`;
  const { acciones } = fila;
  return (
    <tr>
      <td>{fila.id}</td>
      <td className="text-center">{fila.destacado ? <i className="fas fa-star text-warning" /> : <i className="far fa-star text-muted" />}</td>
      <td><a href={ver}>{fila.titulo_corto}</a></td>
      <td>{fila.tipo === "interno" ? <span className="badge bg-info">Interno</span> : <span className="badge bg-warning text-dark">Externo</span>}</td>
      <td><EstadoBadge fila={fila} /></td>
      <td>{fila.fecha_creacion}</td>
      <td>{fila.fecha_publicacion || <span className="text-muted">-</span>}</td>
      <td>{fila.creador}</td>
      <td>
        <div className="btn-group btn-group-sm">
          <a href={ver} className="btn btn-outline-primary" title="Ver"><i className="fas fa-eye" /></a>
          {acciones.editar && <a href={`/comunicados/editar/${fila.id}/`} className="btn btn-outline-secondary" title="Editar"><i className="fas fa-edit" /></a>}
          {acciones.publicar && (
            <ActionForm action={`/comunicados/publicar/${fila.id}/`} endpoint={`${API}${fila.id}/publicar/`} className="btn btn-outline-success" title="Publicar" confirm={PUBLICAR}><i className="fas fa-paper-plane" /></ActionForm>
          )}
          {acciones.archivar && (
            <ActionForm action={`/comunicados/archivar/${fila.id}/`} endpoint={`${API}${fila.id}/archivar/`} className="btn btn-outline-dark" title="Archivar" confirm={ARCHIVAR}><i className="fas fa-archive" /></ActionForm>
          )}
          {acciones.destacado && (fila.destacado ? (
            <ActionForm action={`/comunicados/toggle-destacado/${fila.id}/`} endpoint={`${API}${fila.id}/destacado/`} className="btn btn-warning" title="Quitar destacado"><i className="fas fa-star" /></ActionForm>
          ) : (
            <ActionForm action={`/comunicados/toggle-destacado/${fila.id}/`} endpoint={`${API}${fila.id}/destacado/`} className="btn btn-outline-warning" title="Marcar como destacado"><i className="far fa-star" /></ActionForm>
          ))}
        </div>
      </td>
    </tr>
  );
}

/** The module selects submit the search form on change (`onchange="this.form.submit()"`). */
function FiltroSelect({ id, name, label, value, options, className }: { id: string; name: string; label: string; value: string; options: [string, string][]; className: string }) {
  return <>
    <label htmlFor={id} className={className}>{label}</label>
    <select id={id} name={name} form="simple-search-form" className="form-select" defaultValue={value}
      onChange={(e) => { if (e.currentTarget.form) comunicadosNavigation.submit(e.currentTarget.form); }}>
      <option value="">Todos</option>
      {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
    </select>
  </>;
}

export function ComunicadoGestionContent({ data }: { data: ComunicadoGestionData }) {
  const { page, filtros } = data;
  const limpiar = `?${filtros.estado ? `estado=${filtros.estado}` : ""}${filtros.tipo ? `${filtros.estado ? "&" : ""}tipo=${filtros.tipo}` : ""}`;
  return <>
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <InsumosToastList messages={data.messages} />
    <div className="mt-4">
      <SearchBar placeholder="Buscar comunicado..." query={filtros.titulo} reset={GESTION}>
        {data.flags.can_create && <a href="/comunicados/crear/" className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />Nuevo</a>}
        {data.mailing_url && <a href={data.mailing_url} className="poncho-btn poncho-btn--neutro" title="Enviar mailing masivo">Mailing masivo</a>}
      </SearchBar>
      <div className="poncho-filtros-modulo">
        <FiltroSelect id="filtro-estado" name="estado" label="Estado" className="mb-0" value={filtros.estado}
          options={[["borrador", "Borrador"], ["publicado", "Publicado"], ["archivado", "Archivado"]]} />
        {!data.flags.es_tecnico && (
          <FiltroSelect id="filtro-tipo" name="tipo" label="Tipo" className="mb-0 ms-3" value={filtros.tipo}
            options={[["interno", "Interno"], ["externo", "Externo"]]} />
        )}
        {filtros.titulo && <a href={limpiar} className="btn btn-outline-danger btn-sm" title="Limpiar búsqueda"><i className="fas fa-times" /></a>}
      </div>
      <div className="card">
        <div className="card-header d-flex justify-content-between align-items-center">
          <h5 className="mb-0">Comunicados{" "}{page.is_paginated && <span className="text-muted">({page.count})</span>}</h5>
          <a href={LIST} className="btn btn-sm btn-outline-secondary"><i className="fas fa-eye" />{" "}Ver Vista Pública</a>
        </div>
        <div className="card-body">
          <div className="table-responsive">
            <table className="table table-bordered table-striped table-hover">
              <thead>
                <tr>
                  <th style={{ width: "5%" }}>ID</th><th style={{ width: "5%" }}>Destacado</th><th>Título</th>
                  <th style={{ width: "8%" }}>Tipo</th><th style={{ width: "8%" }}>Estado</th><th style={{ width: "10%" }}>Creación</th>
                  <th style={{ width: "10%" }}>Publicación</th><th style={{ width: "12%" }}>Creador</th><th style={{ width: "15%" }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {data.results.length ? data.results.map((fila) => <GestionRow key={fila.id} fila={fila} />) : (
                  <tr>
                    <td colSpan={9} className="text-center py-4">
                      <i className="fas fa-newspaper fa-2x text-muted mb-2" />
                      <p className="text-muted mb-0">No hay comunicados.</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {page.is_paginated && (
            <Pagination paginated number={page.number} previous={page.previous} next={page.next} range={page.range}
              href={(n) => `?${page.query_without_page}page=${n}`} count={page.count} />
          )}
        </div>
      </div>
    </div>
  </>;
}

function GestionPage() {
  const [state] = useMainResource(`${API}gestion/${window.location.search}`, gestionValid);
  return renderMain(state, "Cargando comunicados…", (data) => ({
    title: "Gestión de Comunicados",
    heading: "Gestión de Comunicados",
    breadcrumb: null,
    content: <ComunicadoGestionContent data={data} />,
  }));
}

// --- Detail (`comunicado_detail.html`) -------------------------------------

/** The footer of the detail: only with one of the native permissions. */
function DetailFooter({ data }: { data: ComunicadoDetailData }) {
  const p = data.permisos;
  if (!(p.editar || p.publicar || p.archivar || p.eliminar)) return null;
  const borrador = data.estado === "borrador";
  return (
    <div className="card-footer">
      <div className="d-flex justify-content-between align-items-center">
        <div>
          <small className="text-muted">Creado: {data.fecha_creacion}{data.modificado_por && <>{" "}| Modificado por: {data.modificado_por}</>}</small>
        </div>
        <div className="btn-group">
          {p.editar && borrador && <a href={`/comunicados/editar/${data.id}/`} className="btn btn-outline-secondary"><i className="fas fa-edit" />{" "}Editar</a>}
          {p.publicar && borrador && (
            <ActionForm action={`/comunicados/publicar/${data.id}/`} endpoint={`${API}${data.id}/publicar/`} className="btn btn-outline-success" confirm={PUBLICAR}><i className="fas fa-paper-plane" />{" "}Publicar</ActionForm>
          )}
          {p.archivar && data.estado === "publicado" && (
            <ActionForm action={`/comunicados/archivar/${data.id}/`} endpoint={`${API}${data.id}/archivar/`} className="btn btn-outline-dark" confirm={ARCHIVAR}><i className="fas fa-archive" />{" "}Archivar</ActionForm>
          )}
          {p.eliminar && borrador && <a href={`/comunicados/eliminar/${data.id}/`} className="btn btn-outline-danger"><i className="fas fa-trash" />{" "}Eliminar</a>}
        </div>
      </div>
    </div>
  );
}

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
        <DetailFooter data={data} />
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

type Params = { id?: string; gestion?: boolean; eliminar?: string; form?: { id?: string } };
const DETAIL = /^\/comunicados\/ver\/([0-9]+)\/$/;
const EDITAR = /^\/comunicados\/editar\/([0-9]+)\/$/;
const ELIMINAR = /^\/comunicados\/eliminar\/([0-9]+)\/$/;

export const comunicadosRoute: RouteDefinition<Params> = {
  name: "comedores-comunicados",
  match(pathname) {
    if (pathname === LIST) return {};
    if (pathname === GESTION) return { gestion: true };
    if (pathname === "/comunicados/crear/") return { form: {} };
    const editar = EDITAR.exec(pathname);
    if (editar) return { form: { id: editar[1] } };
    const eliminar = ELIMINAR.exec(pathname);
    if (eliminar) return { eliminar: eliminar[1] };
    const detail = DETAIL.exec(pathname);
    return detail ? { id: detail[1] } : null;
  },
  render({ id, gestion, eliminar, form }) {
    if (form) return <ComunicadoFormPage id={form.id} />;
    if (eliminar) return <ComunicadoEliminarPage id={eliminar} />;
    if (gestion) return <GestionPage />;
    return id ? <DetailPage id={id} /> : <ListPage />;
  },
};
