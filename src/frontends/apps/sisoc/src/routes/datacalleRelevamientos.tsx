/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { Fragment, useState, type FormEvent } from "react";
import { useLegacyScrollHints } from "../useLegacyScrollHints";
import { client, csrfToken, integer, internal, messagesValid, navigation, nullableText, record, renderCdf, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import { Breadcrumb, breadcrumbValid, type Breadcrumbs } from "./MainFrame";
import { RelevamientoForm } from "./datacalleRelevamientoForm";
import type { RouteDefinition } from "./types";

/**
 * DC01.01-DC01.03 (contract DC01-DC02, #2785): `datacalle/relevamiento_list.html`,
 * `relevamiento_detail.html`, `relevamiento_form.html` and
 * `relevamiento_confirm_delete.html` on their native URLs. Data comes projected
 * from the native views through `/api/web/dispositivos/datacalle/` (G1 v1). A
 * POST is never retried: after any outcome the page goes where the native
 * redirect goes, or reloads the ficha to show its real state.
 */
export const API = "web/dispositivos/datacalle/relevamientos/";
const plural = (n: number, suffix = "s") => (n === 1 ? "" : suffix);

// --- List -------------------------------------------------------------------

type Fila = {
  id: string; denominacion: string; fase_display: string; lugar: string; modalidad_papel: boolean; provincia: string; zonas: string;
  fecha_inicio: string; fecha_fin: string; dias: number; equipo: number; estado: string; estado_display: string;
  urls: { detail: string; edit: string };
};
type Opcion = { value: string; label: string };
type Resumen = { total: number; por_estado: { valor: string; etiqueta: string; total: number }[] };
export type RelevamientosListData = {
  count: number; page: number; page_size: number; pages: number; filters: { busqueda: string; estado: string; fase: string };
  results: Fila[]; is_paginated: boolean; has_next: boolean; has_previous: boolean; page_range: (number | "…" | "...")[]; query_prefix: string;
  resumen: Resumen; estados: Opcion[]; fases: Opcion[]; add_url: string | null; can_change: boolean; messages: CdfMessage[];
};

const opcionesValid = (v: unknown): v is Opcion[] => Array.isArray(v) && v.every((o) => record(o) && text(o.value) && text(o.label));
const filaValid = (f: unknown): f is Fila => record(f) && record(f.urls) &&
  ["id", "denominacion", "fase_display", "lugar", "provincia", "zonas", "fecha_inicio", "fecha_fin", "estado", "estado_display"].every((k) => text(f[k])) &&
  typeof f.modalidad_papel === "boolean" && integer(f.dias) && integer(f.equipo) && internal(f.urls.detail) && internal(f.urls.edit);
const resumenValid = (r: unknown): r is Resumen => record(r) && integer(r.total) && Array.isArray(r.por_estado) &&
  r.por_estado.every((e) => record(e) && text(e.valor) && text(e.etiqueta) && integer(e.total));

export function listValid(v: unknown): v is RelevamientosListData {
  if (!record(v) || !record(v.filters)) return false;
  return ["count", "page", "page_size", "pages"].every((k) => integer(v[k])) &&
    ["busqueda", "estado", "fase"].every((k) => text((v.filters as Record<string, unknown>)[k])) &&
    Array.isArray(v.results) && v.results.every(filaValid) && typeof v.is_paginated === "boolean" &&
    typeof v.has_next === "boolean" && typeof v.has_previous === "boolean" &&
    Array.isArray(v.page_range) && v.page_range.every((n) => n === "…" || n === "..." || integer(n)) && text(v.query_prefix) &&
    resumenValid(v.resumen) && opcionesValid(v.estados) && opcionesValid(v.fases) && (v.add_url === null || internal(v.add_url)) &&
    typeof v.can_change === "boolean" && messagesValid(v.messages);
}

/** `components/pagination.html` («Volver»/«Continuar») and its results line. */
function Pagination({ data }: { data: RelevamientosListData }) {
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

function Stat({ modifier, value, label }: { modifier: string; value: number; label: string }) {
  return <div className={`dc-stat dc-stat--${modifier}`}><span className="dc-stat__valor">{value}</span>{" "}<span className="dc-stat__label">{label}</span></div>;
}

function Vacio({ icon, title, body }: { icon: string; title: string; body: string }) {
  return <div className="dc-vacio"><i className={`fas ${icon}`} />{" "}<h3>{title}</h3>{" "}<p>{body}</p></div>;
}

export function RelevamientosListContent({ data }: { data: RelevamientosListData }) {
  const { cardRef, tableRef, classes } = useLegacyScrollHints(String(data.results.length));
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
      <link rel="stylesheet" href="/static/custom/css/datacalle.css" />
      <div className="list-container">
        <div className="dc-header">
          <div>
            <h1 className="dc-header__title">Relevamientos DataCalle</h1>
            <div className="dc-header__meta">
              <span><i className="fas fa-street-view" />Operativos de situación de calle</span>{" "}
              <span>·</span>{" "}
              <span>Le llegan como tarea al equipo en SISOC - Mobile</span>
            </div>
          </div>
          {data.add_url && (
            <div className="dc-header__actions">
              <a href={data.add_url} className="btn btn-primary"><i className="fas fa-plus mr-1" /> Planificar relevamiento{" "}</a>
            </div>
          )}
        </div>
        <div className="dc-stats">
          <Stat modifier="total" value={data.resumen.total} label="Total" />
          {data.resumen.por_estado.map((item) => <Fragment key={item.valor}>{" "}<Stat modifier={item.valor} value={item.total} label={item.etiqueta} /></Fragment>)}
        </div>
        <form method="get" className="dc-filtros">
          <div className="row g-2">
            <div className="col-md-4">
              <input type="text" name="busqueda" defaultValue={data.filters.busqueda} className="form-control"
                placeholder="Buscar por denominación, área, provincia, localidad, encuestador o DNI" />
            </div>
            <div className="col-md-3">
              <select name="estado" className="form-select" defaultValue={data.estados.some((e) => e.value === data.filters.estado) ? data.filters.estado : ""}>
                <option value="">Todos los estados</option>
                {data.estados.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
              </select>
            </div>
            <div className="col-md-3">
              <select name="fase" className="form-select" defaultValue={data.fases.some((f) => f.value === data.filters.fase) ? data.filters.fase : ""}>
                <option value="">Ambos tipos de operativo</option>
                {data.fases.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
              </select>
            </div>
            <div className="col-md-2 d-grid">
              <button type="submit" className="btn btn-primary"><i className="fas fa-filter mr-1" /> Filtrar{" "}</button>
            </div>
          </div>
        </form>
        <div className="card comedor-table-card">
          <div ref={cardRef} className={`card-body ${classes.card}`}>
            <div ref={tableRef} className={`table-responsive-lg ${classes.table}`}>
              <table className="table table-comedor-moderno">
                <thead>
                  <tr><th>Operativo</th><th>Jurisdicción</th><th>Fechas</th><th>Equipo</th><th>Estado</th><th>Acciones</th></tr>
                </thead>
                <tbody>
                  {data.results.length ? data.results.map((fila) => (
                    <tr key={fila.id}>
                      <td>
                        <div className="dc-celda-principal">
                          <span className="dc-celda-principal__titulo">{fila.denominacion}</span>{" "}
                          <span className="dc-celda-principal__sub">
                            {" "}{fila.fase_display}{" "}{fila.lugar && <>· {fila.lugar}</>}{fila.lugar && " "}{fila.modalidad_papel && <>· papel </>}
                          </span>
                        </div>
                      </td>
                      <td>
                        <div className="dc-celda-principal">
                          <span className="dc-celda-principal__titulo">{fila.provincia}</span>{" "}
                          <span className="dc-celda-principal__sub">{fila.zonas || "—"}</span>
                        </div>
                      </td>
                      <td>
                        <div className="dc-fechas">{fila.fecha_inicio} → {fila.fecha_fin}</div>{" "}
                        <div className="dc-fechas__dias">{fila.dias} día{plural(fila.dias)}</div>
                      </td>
                      <td><span className="dc-equipo-contador"><i className="fas fa-users" /> {fila.equipo}</span></td>
                      <td><span className={`dc-chip dc-chip--${fila.estado}`}>{fila.estado_display}</span></td>
                      <td>
                        <div className="comedor-actions">
                          <a href={fila.urls.detail} className="btn btn-ver" title="Ver detalles"><i className="fas fa-eye" /> Ver{" "}</a>
                          {data.can_change && <>{" "}<a href={fila.urls.edit} className="btn btn-editar" title="Editar"><i className="fas fa-edit" /> Editar{" "}</a></>}
                        </div>
                      </td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan={6}>
                        <Vacio icon="fa-map-marked-alt" title="Todavía no hay operativos" body="Planificá uno para que le aparezca como tarea al equipo en la app." />
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <Pagination data={data} />
      </div>
    </>
  );
}

function RelevamientosList() {
  const state = useCdfPage(`${API}${window.location.search}`, listValid);
  return renderCdf(state, (data) => ({ title: "Relevamientos DataCalle", breadcrumb: null, content: <RelevamientosListContent data={data} /> }));
}

// --- Detail -----------------------------------------------------------------

type Integrante = { iniciales: string; nombre: string; dni: string };
type Cierre = { fecha: string; por: string | null; gps: string | null; observacion_asentamiento: string[]; otra_observacion: string };
type Caso = {
  id: string; codigo: string; persona: string; lugar: string; sin_entrevista_por_franja: boolean; estado: string; estado_display: string;
  es_formulario_menores: boolean; cargado: string; url: string;
};
type ResumenCasos = { casos: number; personas_observadas: number; entrevistas: number; sin_entrevista: number; sin_entrevista_por_franja: number };
export type RelevamientoDetailData = {
  id: string; denominacion: string; estado: string; estado_display: string; provincia: string; municipio: string | null; zonas: string; dias: number;
  fase: string; fase_display: string; lugar: string; localidades: string[]; fecha_inicio: string; fecha_fin: string; modalidad_papel: boolean;
  creado_por: string | null; resumen_casos: ResumenCasos; equipo: Integrante[]; observaciones: string; cierre: Cierre | null; casos: Caso[];
  breadcrumb: Breadcrumbs; can_change: boolean; can_close: boolean; can_delete: boolean;
  urls: { list: string; edit: string; close: string; delete: string }; messages: CdfMessage[];
};

const casoValid = (c: unknown): c is Caso => record(c) && ["id", "codigo", "persona", "lugar", "estado", "estado_display", "cargado"].every((k) => text(c[k])) &&
  typeof c.sin_entrevista_por_franja === "boolean" && typeof c.es_formulario_menores === "boolean" && internal(c.url);
const cierreValid = (c: unknown): c is Cierre | null => c === null || (record(c) && text(c.fecha) && nullableText(c.por) && nullableText(c.gps) &&
  Array.isArray(c.observacion_asentamiento) && c.observacion_asentamiento.every(text) && text(c.otra_observacion));

export function detailValid(v: unknown): v is RelevamientoDetailData {
  if (!record(v) || !record(v.urls) || !record(v.resumen_casos)) return false;
  const r = v.resumen_casos;
  return ["id", "denominacion", "estado", "estado_display", "provincia", "zonas", "fase", "fase_display", "lugar", "fecha_inicio", "fecha_fin", "observaciones"].every((k) => text(v[k])) &&
    nullableText(v.municipio) && nullableText(v.creado_por) && integer(v.dias) && typeof v.modalidad_papel === "boolean" &&
    Array.isArray(v.localidades) && v.localidades.every(text) &&
    ["casos", "personas_observadas", "entrevistas", "sin_entrevista", "sin_entrevista_por_franja"].every((k) => integer(r[k])) &&
    Array.isArray(v.equipo) && v.equipo.every((i) => record(i) && text(i.iniciales) && text(i.nombre) && text(i.dni)) &&
    cierreValid(v.cierre) && Array.isArray(v.casos) && v.casos.every(casoValid) && breadcrumbValid(v.breadcrumb) &&
    ["can_change", "can_close", "can_delete"].every((k) => typeof v[k] === "boolean") &&
    ["list", "edit", "delete"].every((k) => internal((v.urls as Record<string, unknown>)[k])) && text(v.urls.close) && messagesValid(v.messages);
}

function Dato({ label, empty = false, children }: { label: string; empty?: boolean; children: React.ReactNode }) {
  return (
    <div className="dc-dato">
      <div className="dc-dato__label">{label}</div>{" "}
      <div className={`dc-dato__valor${empty ? " dc-dato__valor--vacio" : ""}`}>{children}</div>
    </div>
  );
}

/** `|linebreaksbr`: each line break becomes a `<br>`. */
const lines = (value: string) => value.split(/\r\n|\r|\n/).map((line, i) => <Fragment key={i}>{i > 0 && <br />}{line}</Fragment>);

/** The «Cerrar relevamiento» POST: no confirmation (as native), never retried. */
function CloseButton({ data }: { data: RelevamientoDetailData }) {
  const [sending, setSending] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending) return;
    setSending(true);
    // Native redirect target is the ficha; on any other outcome (504 `uncertain`, lost
    // response) the ficha is reloaded so the real state decides whether the button returns.
    const ficha = `${data.urls.list}${data.id}/`;
    try {
      const { data: body } = await client.post(data.urls.close.replace(/^\/api\//, ""), new FormData(event.currentTarget));
      navigation.assign(record(body) && internal(body.url) ? body.url : ficha);
    } catch {
      navigation.assign(ficha);
    }
  }
  return (
    <form method="post" action={data.urls.close} className="d-inline" onSubmit={submit}>
      <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
      <button type="submit" className="btn btn-warning btn-sm" disabled={sending || undefined}><i className="fas fa-flag-checkered mr-1" /> Cerrar relevamiento{" "}</button>
    </form>
  );
}

export function RelevamientoDetailContent({ data }: { data: RelevamientoDetailData }) {
  const { resumen_casos: r, cierre } = data;
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/datacalle.css" />
      <div className="dc-header">
        <div>
          <h1 className="dc-header__title">{data.denominacion}</h1>
          <div className="dc-header__meta">
            <span className={`dc-chip dc-chip--${data.estado}`}>{data.estado_display}</span>{" "}
            <span>·</span>{" "}
            <span><i className="fas fa-map-marker-alt" />{data.provincia}</span>{" "}
            {data.zonas && <><span>·</span><span>{data.zonas}</span>{" "}</>}
            <span>·</span>{" "}
            <span><i className="fas fa-calendar-alt" />{data.dias} día{plural(data.dias)}</span>
          </div>
        </div>
        <div className="dc-header__actions">
          {data.can_change && <a href={data.urls.edit} className="btn btn-primary btn-sm"><i className="fas fa-pencil-alt mr-1" /> Editar{" "}</a>}
          {data.can_close && <>{" "}<CloseButton data={data} /></>}
          {data.can_delete && <>{" "}<a href={data.urls.delete} className="btn btn-danger btn-sm"><i className="fas fa-trash-alt mr-1" /> Eliminar{" "}</a></>}
        </div>
      </div>
      <div className="dc-secciones">
        <div className="dc-seccion">
          <div className="dc-seccion__header"><i className="fas fa-map-marked-alt" /> Dónde se releva{" "}</div>{" "}
          <div className="dc-seccion__body">
            <Dato label="Fase">{data.fase_display}</Dato>{" "}
            <Dato label={data.fase === "dispositivo_alojamiento" ? "Dispositivo" : "Área operativa"} empty={!data.lugar}>{data.lugar || "—"}</Dato>{" "}
            <Dato label="Jurisdicción">{data.provincia}{data.municipio !== null && <>{" "}· {data.municipio}</>}</Dato>{" "}
            <Dato label="Localidades / comunas" empty={!data.localidades.length}>
              {data.localidades.length
                ? data.localidades.map((l, i) => <Fragment key={i}>{i > 0 && " "}<span className="dc-chip dc-chip--zona">{l}</span></Fragment>)
                : "—"}
            </Dato>
          </div>
        </div>{" "}
        <div className="dc-seccion">
          <div className="dc-seccion__header"><i className="fas fa-calendar-alt" /> Cuándo{" "}</div>{" "}
          <div className="dc-seccion__body">
            <Dato label="Período planificado">
              {data.fecha_inicio} → {data.fecha_fin}{" "}<span className="dc-fechas__dias">({data.dias} día{plural(data.dias)})</span>
            </Dato>{" "}
            <Dato label="Formato en papel">{data.modalidad_papel ? "Sí" : "No"}</Dato>{" "}
            <Dato label="Planificado por" empty={data.creado_por === null}>{data.creado_por ?? "—"}</Dato>
          </div>
        </div>
      </div>
      <div className="dc-stats">
        <Stat modifier="total" value={r.casos} label="Casos" />{" "}
        <Stat modifier="planificado" value={r.personas_observadas} label="Personas observadas" />{" "}
        <Stat modifier="finalizado" value={r.entrevistas} label="Entrevistas" />{" "}
        <Stat modifier="en_curso" value={r.sin_entrevista} label="Sin entrevista" />{" "}
        <Stat modifier="en_curso" value={r.sin_entrevista_por_franja} label="Sin entrevista por edad" />
      </div>
      <div className="dc-seccion mb-3">
        <div className="dc-seccion__header">
          <i className="fas fa-users" /> Equipo asignado{" "}
          <span className="dc-seccion__ayuda ms-auto text-lowercase">{data.equipo.length} entrevistador{plural(data.equipo.length, "es")}</span>
        </div>{" "}
        <div className="dc-seccion__body">
          <div className="dc-equipo">
            {data.equipo.length ? data.equipo.map((p, i) => (
              <Fragment key={i}>{i > 0 && " "}
                <div className="dc-persona">
                  <span className="dc-persona__avatar">{" "}{p.iniciales}{" "}</span>{" "}
                  <span>
                    {" "}<span className="dc-persona__nombre">{p.nombre}</span>{" "}
                    {p.dni && <><br />{" "}<span className="dc-persona__dni">DNI {p.dni}</span>{" "}</>}
                  </span>
                </div>
              </Fragment>
            )) : <p className="dc-dato__valor dc-dato__valor--vacio mb-0">Sin equipo asignado: nadie va a ver este operativo en la app.</p>}
          </div>
        </div>
      </div>
      {data.observaciones && (
        <div className="dc-seccion mb-3">
          <div className="dc-seccion__header"><i className="fas fa-sticky-note" /> Observaciones{" "}</div>{" "}
          <div className="dc-seccion__body"><div className="dc-dato__valor">{lines(data.observaciones)}</div></div>
        </div>
      )}
      <div className="dc-seccion mb-4">
        <div className="dc-seccion__header"><i className="fas fa-flag-checkered" /> Cierre en campo{" "}</div>{" "}
        <div className="dc-seccion__body">
          {cierre ? <>
            <Dato label="Cerrado">{" "}{cierre.fecha}{" "}{cierre.por !== null && <>por {cierre.por}{" "}</>}</Dato>{" "}
            <Dato label="Punto GPS" empty={cierre.gps === null}>{cierre.gps ?? "—"}</Dato>{" "}
            <Dato label="Observación del asentamiento" empty={!cierre.observacion_asentamiento.length}>
              {cierre.observacion_asentamiento.join(", ") || "—"}
            </Dato>
            {cierre.otra_observacion && <>{" "}<Dato label="Otra observación">{cierre.otra_observacion}</Dato></>}
          </> : (
            <Vacio icon="fa-hourglass-half" title="Todavía sin cerrar"
              body="El equipo cierra el operativo desde la app y ahí llegan el punto GPS y la observación del asentamiento." />
          )}
        </div>
      </div>
      <div className="dc-seccion mb-4">
        <div className="dc-seccion__header">
          <i className="fas fa-clipboard-list" /> Casos relevados{" "}
          <span className="dc-seccion__ayuda ms-auto text-lowercase">se cargan desde la app</span>
        </div>{" "}
        <div className="dc-seccion__body">
          <div className="table-responsive-lg">
            <table className="table table-comedor-moderno">
              <thead>
                <tr><th>Código</th><th>Persona</th><th>Lugar</th><th>Estado</th><th>Cargado</th><th>Acciones</th></tr>
              </thead>
              <tbody>
                {data.casos.length ? data.casos.map((caso) => (
                  <tr key={caso.id}>
                    <td>{caso.codigo || "—"}</td>
                    <td>{caso.persona || "—"}</td>
                    <td>{caso.lugar || "—"}</td>
                    <td>
                      {caso.sin_entrevista_por_franja ? <span className="dc-chip dc-chip--zona">Sin entrevista (edad)</span> : <>
                        <span className={`dc-chip dc-chip--${caso.estado === "completa" ? "finalizado" : "planificado"}`}>{" "}{caso.estado_display}{" "}</span>
                        {caso.es_formulario_menores && <>{" "}<span className="dc-chip dc-chip--zona">Menores (14 a 17)</span></>}
                      </>}
                    </td>
                    <td>{caso.cargado || "—"}</td>
                    <td>
                      <div className="comedor-actions">
                        <a href={caso.url} className="btn btn-ver"><i className="fas fa-eye" /> Ver{" "}</a>
                      </div>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={6}>
                      <Vacio icon="fa-clipboard" title="Todavía no llegaron casos" body="Aparecen acá a medida que el equipo sincroniza desde la app." />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}

function RelevamientoDetail({ id }: { id: string }) {
  const state = useCdfPage(`${API}${id}/`, detailValid);
  return renderCdf(state, (data) => ({
    title: data.denominacion,
    breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <RelevamientoDetailContent data={data} />,
  }));
}

// --- Delete (`relevamiento_confirm_delete.html`) ------------------------------

export type RelevamientoDeleteData = { id: string; denominacion: string; urls: { cancel: string }; messages: CdfMessage[] };
export const deleteValid = (v: unknown): v is RelevamientoDeleteData => record(v) && record(v.urls) && text(v.id) && text(v.denominacion) &&
  internal(v.urls.cancel) && messagesValid(v.messages);

export function RelevamientoDeleteContent({ data }: { data: RelevamientoDeleteData }) {
  const [sending, setSending] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending) return;
    setSending(true);
    try {
      const { data: body } = await client.post(`${API}${data.id}/eliminar/`, new FormData(event.currentTarget));
      // The native redirect: the list, without a message.
      navigation.assign(record(body) && internal(body.url) ? body.url : data.urls.cancel);
    } catch {
      navigation.assign(data.urls.cancel);
    }
  }
  return (
    <div className="container mt-4">
      <div className="card">
        <div className="card-header bg-danger text-white"><h5 className="mb-0">Confirmar eliminación</h5></div>{" "}
        <div className="card-body">
          <p className="mb-3"> ¿Seguro que desea eliminar el relevamiento <strong>{data.denominacion}</strong>? </p>{" "}
          <p className="text-muted"> Se da de baja de forma lógica: deja de verse como tarea en la app y queda recuperable desde la papelera. </p>{" "}
          <form method="post" onSubmit={submit}>
            <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />{" "}
            <button type="submit" className="btn btn-danger" disabled={sending || undefined}>Eliminar</button>{" "}
            <a href={data.urls.cancel} className="btn btn-secondary">Cancelar</a>
          </form>
        </div>
      </div>
    </div>
  );
}

function RelevamientoDelete({ id }: { id: string }) {
  const state = useCdfPage(`${API}${id}/eliminar/`, deleteValid);
  return renderCdf(state, (data) => ({ title: "Eliminar relevamiento", breadcrumb: null, content: <RelevamientoDeleteContent data={data} /> }));
}

// --- Route ------------------------------------------------------------------

type Params = { id?: string; action: "list" | "detail" | "crear" | "editar" | "eliminar" };
const UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
const OBJECT = new RegExp(`^/datacalle/relevamientos/(${UUID})/(?:(editar|eliminar)/)?$`);

// Native URLs of the DataCalle operativos (DC01.01-DC01.03); same trailing slash, lower-case UUID as `<uuid:pk>`.
export const datacalleRelevamientosRoute: RouteDefinition<Params> = {
  name: "datacalle-relevamientos",
  match: (pathname) => {
    if (pathname === "/datacalle/relevamientos/") return { action: "list" };
    if (pathname === "/datacalle/relevamientos/crear/") return { action: "crear" };
    const m = OBJECT.exec(pathname);
    return m ? { id: m[1], action: (m[2] as "editar" | "eliminar" | undefined) ?? "detail" } : null;
  },
  render: ({ id, action }) => {
    if (action === "list") return <RelevamientosList />;
    if (action === "detail" && id) return <RelevamientoDetail id={id} />;
    if (action === "eliminar" && id) return <RelevamientoDelete id={id} />;
    return <RelevamientoForm id={id} />;
  },
};
