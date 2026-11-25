/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import type { ReactNode } from "react";
import { safeInternalPath } from "../webAccess";
import { internal, messagesValid, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import type { RouteDefinition } from "./types";

/**
 * CDI03 institutional forms: the list (`formulario_cdi_list.html`, pages of 10
 * with `components/pagination.html`) and the detail (`formulario_cdi_detail.html`,
 * section cards, per-day schedule and the three fixed tables). Every value comes
 * rendered by the backend with the native template expressions; the new and edit
 * links keep the native URLs.
 */
type Fila = { id: number; codigo: string; fecha: string; respondente: string; creado: string; actualizado: string; ver_url: string; editar_url: string };
type Pagina = { is_paginated: boolean; number: number; count: number; previous: number | null; next: number | null; range: (number | string)[] };
export type ListaData = {
  centro: { id: number; nombre: string; url: string };
  crear_url: string;
  rows: Fila[];
  page: Pagina;
  messages: CdiMessage[];
};
type Tabla = string[][];
export type DetalleData = {
  id: number;
  centro: { id: number; nombre: string; url: string };
  codigo_cdi: string;
  creado: string;
  creado_por: string | null;
  editar_url: string;
  sections: { title: string; items: { label: string; value: string }[] }[];
  horarios: Tabla;
  salas: { rows: Tabla; totales: string[] };
  demanda: { rows: Tabla; total: string };
  articulacion: Tabla;
  messages: CdiMessage[];
};

const int = (v: unknown): v is number => Number.isSafeInteger(v);
const tabla = (v: unknown, width: number): v is Tabla => Array.isArray(v) && v.every((r) => Array.isArray(r) && r.length === width && r.every(text));
const centroValid = (c: unknown) => record(c) && int(c.id) && text(c.nombre) && internal(c.url);

export function listaValid(v: unknown): v is ListaData {
  if (!record(v) || !centroValid(v.centro) || !record(v.page)) return false;
  const p = v.page;
  return internal(v.crear_url) && messagesValid(v.messages) && Array.isArray(v.rows) &&
    v.rows.every((r) => record(r) && int(r.id) && ["codigo", "fecha", "respondente", "creado", "actualizado"].every((k) => text(r[k])) && internal(r.ver_url) && internal(r.editar_url)) &&
    typeof p.is_paginated === "boolean" && int(p.number) && int(p.count) && (p.previous === null || int(p.previous)) && (p.next === null || int(p.next)) &&
    Array.isArray(p.range) && p.range.every((i) => int(i) || i === "…");
}

export function detalleValid(v: unknown): v is DetalleData {
  if (!record(v) || !centroValid(v.centro) || !record(v.salas) || !record(v.demanda)) return false;
  return int(v.id) && text(v.codigo_cdi) && text(v.creado) && (v.creado_por === null || text(v.creado_por)) && internal(v.editar_url) && messagesValid(v.messages) &&
    Array.isArray(v.sections) && v.sections.every((s) => record(s) && text(s.title) && Array.isArray(s.items) && s.items.every((i) => record(i) && text(i.label) && text(i.value))) &&
    tabla(v.horarios, 3) && tabla(v.salas.rows, 6) && Array.isArray(v.salas.totales) && v.salas.totales.length === 4 && v.salas.totales.every(text) &&
    tabla(v.demanda.rows, 2) && text(v.demanda.total) && tabla(v.articulacion, 2);
}

const href = (url: string) => safeInternalPath(url) ?? "/";

/** `components/pagination.html`: the other query parameters are kept, `busqueda` and `page` are rebuilt. */
function pageLink(search: string, page: number) {
  const kept = Array.from(new URLSearchParams(search)).filter(([k]) => k !== "page" && k !== "busqueda")
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}&`).join("");
  return `?${kept}page=${page}`;
}

/** `page_obj` is falsy when the page has no rows, so the template shows no count then. */
function Pagination({ page, empty }: { page: Pagina; empty: boolean }) {
  const search = window.location.search;
  return (
    <div className="mt-2">
      {page.is_paginated && (
        <ul className="pagination">
          <li className={`page-item${page.previous === null ? " disabled" : ""}`}>
            <a href={page.previous === null ? "#" : pageLink(search, page.previous)} className="page-link">Volver</a>
          </li>
          {page.range.map((i, n) => i === "…" ? (
            <li key={`e${n}`} className="page-item disabled"><a href="#" className="page-link">...</a></li>
          ) : (
            <li key={i} className={`page-item ${page.number === i ? "active" : ""}`}><a href={pageLink(search, i as number)} className="page-link">{i}</a></li>
          ))}
          <li className={`page-item${page.next === null ? " disabled" : ""}`}>
            <a href={page.next === null ? "#" : pageLink(search, page.next)} className="page-link">Continuar</a>
          </li>
        </ul>
      )}
      {!empty && <p className="text-center text-muted mb-0 mt-1">Se encontraron {page.count} resultados</p>}
    </div>
  );
}

export function ListaContent({ data }: { data: ListaData }) {
  return (
    <div className="container-fluid">
      <div className="d-flex justify-content-between mb-3">
        <a href={href(data.crear_url)} className="btn btn-primary">Nuevo formulario</a>
      </div>
      <div className="card">
        <div className="card-body">
          <h3 className="mb-1">{data.centro.nombre}</h3>
          <p className="text-muted mb-0">Listado completo de formularios vinculados al centro.</p>
        </div>
      </div>
      <div className="table-responsive mt-3">
        <table className="table table-bordered table-striped">
          <thead>
            <tr><th>CDI / ID</th><th>Fecha relevamiento</th><th>Quien responde</th><th>Creado</th><th>Actualizado</th><th>Acciones</th></tr>
          </thead>
          <tbody>
            {data.rows.length ? data.rows.map((f) => (
              <tr key={f.id}>
                <td>{f.codigo}</td><td>{f.fecha}</td><td>{f.respondente}</td><td>{f.creado}</td><td>{f.actualizado}</td>
                <td className="d-flex gap-2">
                  <a href={href(f.ver_url)} className="btn btn-sm btn-primary">Ver</a>
                  <a href={href(f.editar_url)} className="btn btn-sm btn-warning">Editar</a>
                </td>
              </tr>
            )) : <tr><td colSpan={6} className="text-center text-muted py-4">Todavia no hay formularios cargados para este centro.</td></tr>}
          </tbody>
        </table>
      </div>
      <Pagination page={data.page} empty={data.rows.length === 0} />
    </div>
  );
}

function Card({ title, last, children }: { title: string; last?: boolean; children: ReactNode }) {
  return (
    <div className={`card ${last ? "mb-4" : "mb-3"}`}>
      <div className="card-header"><strong>{title}</strong></div>
      <div className="card-body">{children}</div>
    </div>
  );
}

function Table({ head, rows, foot }: { head: string[]; rows: Tabla; foot?: string[] }) {
  return (
    <div className="table-responsive">
      <table className="table table-bordered">
        <thead><tr>{head.map((h) => <th key={h}>{h}</th>)}</tr></thead>
        <tbody>{rows.map((r, n) => <tr key={n}>{r.map((c, i) => <td key={i}>{c}</td>)}</tr>)}</tbody>
        {foot && <tfoot><tr>{foot.map((c, i) => <th key={i}>{c}</th>)}</tr></tfoot>}
      </table>
    </div>
  );
}

export function DetalleContent({ data }: { data: DetalleData }) {
  return (
    <div className="container-fluid">
      <div className="d-flex justify-content-between mb-3">
        <a href={href(data.editar_url)} className="btn btn-warning">Editar</a>
      </div>
      <div className="card mb-3">
        <div className="card-body">
          <h3 className="mb-1">{data.centro.nombre}</h3>
          <p className="text-muted mb-1">Formulario #{data.id} | Código CDI {data.codigo_cdi}</p>
          <p className="text-muted mb-0">Creado {data.creado}{data.creado_por !== null && ` por ${data.creado_por}`}</p>
        </div>
      </div>
      {data.sections.map((s, n) => (
        <div className="card mb-3" key={n}>
          <div className="card-header"><strong>{s.title}</strong></div>
          <div className="card-body">
            <div className="row">
              {s.items.map((i, k) => (
                <div className="col-md-6 mb-3" key={k}>
                  <div className="text-muted small">{i.label}</div>
                  <div>{i.value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
      <Card title="Horarios de funcionamiento por día">
        {data.horarios.length
          ? <Table head={["Día", "Horario de apertura", "Horario de cierre"]} rows={data.horarios} />
          : <p className="mb-0 text-muted">Sin horarios cargados.</p>}
      </Card>
      <Card title="Organización de Salas: ¿Cómo se distribuyen los niños y niñas en las salas dentro del CDI? Complete la siguiente tabla consignando para cada grupo existente, la cantidad de salas, la superficie exclusiva en m², la cantidad de niñas y niños que concurren y la cantidad de personal de sala disponible.">
        <Table head={["Grupo etario", "Cantidad de Salas (A)", "Superficie m2", "Niñas y niños", "Cantidad de Personal de Sala (B)", "Cantidad de personal por sala (B/A)"]}
          rows={data.salas.rows} foot={["Totales", ...data.salas.totales, "-"]} />
      </Card>
      <Card title="Demanda insatisfecha por sala">
        <Table head={["Grupo etario", "Lista de espera"]} rows={data.demanda.rows} foot={["Total", data.demanda.total]} />
      </Card>
      <Card title="Articulaciones institucionales" last>
        <Table head={["Institucion", "Frecuencia"]} rows={data.articulacion} />
      </Card>
    </div>
  );
}

function ListaPage({ centro }: { centro: string }) {
  const [state] = useCdiPage(`web/cdi/centros/${centro}/formularios/${window.location.search}`, listaValid);
  return renderCdi(state, (data) => ({ title: "Formularios CDI", heading: "Formularios CDI", content: <ListaContent data={data} /> }));
}

function DetallePage({ centro, id }: { centro: string; id: string }) {
  const [state] = useCdiPage(`web/cdi/centros/${centro}/formularios/${id}/`, detalleValid);
  return renderCdi(state, (data) => ({ title: `Formulario CDI #${data.id}`, heading: `Formulario CDI #${data.id}`, content: <DetalleContent data={data} /> }));
}

// Native URLs of the CDI institutional form list and detail (CDI03); same trailing slash.
export const cdiFormulariosListaRoute: RouteDefinition<{ centro: string }> = {
  name: "cdi-formularios-lista",
  match: (pathname) => {
    const own = /^\/centrodeinfancia\/([1-9]\d*)\/formularios\/$/.exec(pathname);
    return own ? { centro: own[1] } : null;
  },
  render: ({ centro }) => <ListaPage centro={centro} />,
};

export const cdiFormularioDetalleRoute: RouteDefinition<{ centro: string; id: string }> = {
  name: "cdi-formulario-detalle",
  match: (pathname) => {
    const own = /^\/centrodeinfancia\/([1-9]\d*)\/formularios\/([1-9]\d*)\/$/.exec(pathname);
    return own ? { centro: own[1], id: own[2] } : null;
  },
  render: ({ centro, id }) => <DetallePage centro={centro} id={id} />,
};
