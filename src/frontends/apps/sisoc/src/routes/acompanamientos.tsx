/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { AcompanamientosListContent, acompanamientosNavigation, listValid } from "./acompanamientosList";
import type { RouteDefinition } from "./types";

/**
 * AC01 acompañamiento follow-up (`/acompanamientos/acompanamiento/`): the list
 * of comedores and the ficha with its agreements, relevant information,
 * benefits and the 23 milestones. Data comes from
 * `/api/web/comedores/acompanamientos/`, which runs the native views. Restoring
 * a milestone posts to the API with the shown `admision_id`; the next page
 * shows the native message. The CSV stays the native GET.
 */
type Params = { page: "list" } | { page: "detail"; id: string };
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Convenio = { id: number; label: string; activa: boolean; seleccionada: boolean };
type Info = { nro_convenio: string; expediente: string; disposicion: string; if_relevamiento: string; vencimiento: string; codigo_proyecto: string };
type Hito = { campo: string; descripcion: string; completado: boolean; fecha: string };
type Urls = { detalle: string; intervenciones: string; expedientes: string; seguimiento: string; informe_complementario: string | null; comedor: string; restaurar: string };
export type DetailData = {
  comedor: { id: number; nombre: string }; admision_id: number | null; convenios: Convenio[]; multiples_activos: boolean;
  informacion: Info | null; prestaciones: { dias: string[]; por_dia: { tipo: string; valores: string[] }[]; semanal: { tipo: string; cantidad: string }[] };
  hitos: Hito[] | null; puede_restaurar: boolean; urls: Urls; messages: Message[];
};

const API = "web/comedores/acompanamientos/";
const LEVELS = ["success", "error", "warning", "info"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const texts = (v: unknown, keys: string[]) => record(v) && keys.every((k) => text(v[k]));

export function detailValid(v: unknown): v is DetailData {
  if (!record(v) || !record(v.comedor) || !record(v.prestaciones) || !record(v.urls)) return false;
  const p = v.prestaciones, u = v.urls;
  return int(v.comedor.id) && text(v.comedor.nombre) && (v.admision_id === null || int(v.admision_id)) &&
    Array.isArray(v.convenios) && v.convenios.every((c) => record(c) && int(c.id) && text(c.label) && typeof c.activa === "boolean" && typeof c.seleccionada === "boolean") &&
    typeof v.multiples_activos === "boolean" && typeof v.puede_restaurar === "boolean" &&
    (v.informacion === null || texts(v.informacion, ["nro_convenio", "expediente", "disposicion", "if_relevamiento", "vencimiento", "codigo_proyecto"])) &&
    Array.isArray(p.dias) && p.dias.every(text) &&
    Array.isArray(p.por_dia) && p.por_dia.every((f) => record(f) && text(f.tipo) && Array.isArray(f.valores) && f.valores.length === 7 && f.valores.every(text)) &&
    Array.isArray(p.semanal) && p.semanal.every((f) => texts(f, ["tipo", "cantidad"])) &&
    (v.hitos === null || (Array.isArray(v.hitos) && v.hitos.every((h) => texts(h, ["campo", "descripcion", "fecha"]) && typeof (h as Hito).completado === "boolean"))) &&
    ["detalle", "intervenciones", "expedientes", "seguimiento", "comedor", "restaurar"].every((k) => internal(u[k])) &&
    (u.informe_complementario === null || internal(u.informe_complementario)) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

function Vacio({ titulo, texto }: { titulo: string; texto: string }) {
  return <div className="hitos-vacio"><i className="fas fa-exclamation-triangle" /><h4>{titulo}</h4><p>{texto}</p></div>;
}

function Card({ icon, title, children, plain = false, extra = "" }: { icon: string; title: string; children: ReactNode; plain?: boolean; extra?: string }) {
  return <div className={`row${extra}`}><div className="col-12"><div className="card card-primary card-outline">
    <div className="hitos-header card-header"><h3><i className={`fas ${icon} header-icon`} />{title}</h3></div>
    <div className="hitos-body" style={plain ? undefined : { padding: "2rem" }}>{children}</div>
  </div></div></div>;
}

function InfoItem({ label, value, fecha = false }: { label: string; value: string; fecha?: boolean }) {
  return <div className="info-item"><div className="info-label">{label}</div><div className={`info-value${fecha ? " fecha-valor" : ""}`}>{value}</div></div>;
}

type Aviso = { text: string; level: "error" } | { uncertain: true };

function HitoRow({ hito, data, restore }: { hito: Hito; data: DetailData; restore: (campo: string) => void }) {
  const estado = hito.completado ? "completado" : "pendiente";
  const enabled = hito.completado && data.puede_restaurar;
  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); if (enabled) restore(hito.campo); };
  return <div className={`hito-row ${estado}`}>
    <div className="hito-cell" data-label="Descripción"><span className="hito-descripcion">{hito.descripcion}</span></div>
    <div className="hito-cell" data-label="Estado">
      <span className={`estado-badge estado-${estado}`}><i className={`fas ${hito.completado ? "fa-check-circle" : "fa-clock"}`} />{" "}{hito.completado ? "Completado" : "Pendiente"}</span>
    </div>
    <div className="hito-cell" data-label="Fecha Completado"><span className={`fecha-completado ${hito.completado ? "" : "vacia"}`}>{hito.fecha}</span></div>
    <div className="hito-cell" data-label="Acciones"><div className="hito-acciones">
      <form method="POST" action={data.urls.restaurar} onSubmit={submit}>
        <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
        <input type="hidden" name="campo" value={hito.campo} />
        {data.admision_id !== null && <input type="hidden" name="admision_id" value={String(data.admision_id)} />}
        {enabled
          ? <button type="submit" className="btn-restaurar"><i className="fas fa-undo" />{" "}Restaurar</button>
          : <button type="button" className="btn-restaurar disabled" disabled><i className="fas fa-undo" />{" "}Restaurar</button>}
      </form>
    </div></div>
  </div>;
}

function Ficha({ data }: { data: DetailData }) {
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const busy = useRef(false);
  async function restore(campo: string) {
    if (busy.current || (aviso && "uncertain" in aviso)) return;
    busy.current = true;
    const body = new URLSearchParams({ campo });
    if (data.admision_id !== null) body.set("admision_id", String(data.admision_id));
    const result = await restorePost(`${API}${data.comedor.id}/hitos/restaurar/`, body);
    busy.current = false;
    if (result.kind === "redirect") acompanamientosNavigation.assign(result.url);
    // 400/409 keep the native error text; anything else (403, 504) is not retried.
    else setAviso(result.kind === "rejected" ? { text: result.text, level: "error" } : { uncertain: true });
  }
  const h = data.hitos;
  const completados = h ? h.filter((x) => x.completado).length : 0;
  const info = data.informacion, p = data.prestaciones;
  return <>
    <link rel="stylesheet" href="/static/custom/css/hitos.css" />
    <InsumosToastList messages={aviso && "text" in aviso ? [...data.messages, { message: aviso.text, level: "error" }] : data.messages} />
    {aviso && "uncertain" in aviso && <p role="alert">No se pudo confirmar el resultado. <a href={`${data.urls.detalle}${data.admision_id ? `?admision_id=${data.admision_id}` : ""}`}>Recargar la ficha</a></p>}
    <div className="row justify-content-between">
      <div className="col-auto d-flex flex-wrap gap-2">
        <a href={data.urls.intervenciones} className="btn btn-primary mb-3"><i className="fas fa-plus me-2" />Intervenciones</a>
        <a href={data.urls.expedientes} className="btn btn-primary mb-3"><i className="fas fa-plus me-2" />Expedientes de Pagos</a>
        <a href={data.urls.seguimiento} className="btn btn-primary mb-3"><i className="fas fa-plus me-2" />Seguimiento Mensual</a>
      </div>
      {data.urls.informe_complementario && <div className="col-auto">
        <a href={data.urls.informe_complementario} className="btn btn-primary mb-3"><i className="fas fa-file-alt me-2" />Informe Técnico Complementario</a>
      </div>}
    </div>
    {data.convenios.length > 0 && <div className="row mb-3"><div className="col-12"><div className="card card-outline card-secondary">
      <div className="card-header d-flex align-items-center gap-3">
        <span className="fw-bold"><i className="fas fa-file-contract me-1" />Convenio:</span>
        {data.convenios.map((c) => <a key={c.id} href={`?admision_id=${c.id}`} className={`btn btn-sm ${c.seleccionada ? "btn-primary" : "btn-outline-secondary"}`}>
          {c.label}{!c.activa && <>{" "}<span className="badge bg-secondary ms-1">Cerrada</span></>}
        </a>)}
        {data.multiples_activos && <span className="badge bg-warning text-dark ms-2"><i className="fas fa-exclamation-triangle me-1" />Múltiples convenios activos</span>}
      </div>
    </div></div></div>}
    <Card icon="fa-info-circle" title="Información Relevante">
      {info ? <div className="info-grid" style={{ display: "grid", gap: "1.5rem" }}>
        {info.nro_convenio && <InfoItem label="Número de Convenio" value={info.nro_convenio} />}
        <InfoItem label="Número de Expediente" value={info.expediente} />
        <InfoItem label="Número de Disposición" value={info.disposicion} />
        <InfoItem label="IF de Relevamiento" value={info.if_relevamiento} />
        <InfoItem label="Vencimiento de Mandato" value={info.vencimiento} fecha />
        <InfoItem label="Código de Proyecto" value={info.codigo_proyecto} />
      </div> : <Vacio titulo="No hay información relevante disponible" texto="No hay información relevante cargada para este comedor." />}
    </Card>
    <Card icon="fa-utensils" title="Prestaciones por Día" extra=" mt-4">
      {p.por_dia.length ? <>
        <div className="prestaciones-table-container"><table className="prestaciones-table table text-center align-middle">
          <thead className="prestaciones-header"><tr><th>Tipo de Comida</th>{p.dias.map((d) => <th key={d}>{d}</th>)}</tr></thead>
          <tbody>{p.por_dia.map((f) => <tr key={f.tipo}><td className="text-start fw-bold">{f.tipo}</td>{f.valores.map((v, i) => <td key={i}>{v}</td>)}</tr>)}</tbody>
        </table></div>
        {p.semanal.length > 0 && <div className="mt-4">
          <h5>Resumen Semanal</h5>
          <div className="prestaciones-table-container"><table className="prestaciones-table table table-green text-center align-middle">
            <thead className="prestaciones-header"><tr><th className="text-start">Tipo</th><th>Total Semanal</th></tr></thead>
            <tbody>{p.semanal.map((f) => <tr key={f.tipo}><td className="text-start fw-bold">{f.tipo}</td><td>{f.cantidad}</td></tr>)}</tbody>
          </table></div>
        </div>}
      </> : <Vacio titulo="No hay prestaciones disponibles" texto="No hay información de prestaciones cargada para este comedor." />}
    </Card>
    <Card icon="fa-tasks" title="Listado de Hitos" plain extra=" mt-4">
      {h ? <>
        <div className="hitos-grid">
          <div className="hitos-grid-header"><div>Descripción del Hito</div><div>Estado</div><div>Fecha Completado</div><div>Acciones</div></div>
          {h.map((hito) => <HitoRow key={hito.campo} hito={hito} data={data} restore={(c) => void restore(c)} />)}
        </div>
        <div className="hitos-info"><div className="info-stats">
          <div className="stat-item stat-completados"><div className="stat-number" id="completados-count">{completados}</div><div className="stat-label">Completados</div></div>
          <div className="stat-item stat-pendientes"><div className="stat-number" id="pendientes-count">{h.length - completados}</div><div className="stat-label">Pendientes</div></div>
          <div className="stat-item"><div className="stat-number" id="total-count">{h.length}</div><div className="stat-label">Total</div></div>
        </div></div>
      </> : <Vacio titulo="No hay información de hitos disponible" texto="No hay hitos cargados para este comedor." />}
    </Card>
    <div className="col-md-2 text-start my-3"><a href={data.urls.comedor} className="btn btn-secondary btn-lg"><i className="fas fa-arrow-left" /></a></div>
  </>;
}

/** POST through the API: `{ok, redirect}` navigates; 400/409 bring the native message. */
async function restorePost(endpoint: string, body: URLSearchParams) {
  try {
    const { data } = await webClient.post(endpoint, body, { validateStatus: (status: number) => accepted(status) || status === 400 || status === 409 });
    if (record(data) && data.ok === true && internal(data.redirect)) return { kind: "redirect" as const, url: data.redirect };
    if (record(data) && data.ok === false && record(data.message) && text(data.message.text)) return { kind: "rejected" as const, text: data.message.text };
  } catch {
    // Network error or 5xx/504: the outcome is uncertain.
  }
  return { kind: "uncertain" as const };
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, listValid);
  return renderMain(state, "Cargando comedores…", (data) => ({ title: "Comedores en Acompañamiento", breadcrumb: null, content: <AcompanamientosListContent data={data} /> }));
}

function DetailPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/${window.location.search}`, detailValid);
  return renderMain(state, "Cargando acompañamiento…", (data) => ({
    title: "Acompañamiento", heading: "Acompañamiento",
    breadcrumb: <ol className="breadcrumb float-sm-right">
      <li className="breadcrumb-item"><a href={data.urls.detalle} title="Ver Comedor">{data.comedor.nombre}</a></li>
      <li className="breadcrumb-item active">Acompañamiento</li>
    </ol>,
    // `{% block app-header %}` of the template: the comedor name.
    appHeader: <div className="row"><div className="col-12"><h2 className="mb-0">{data.comedor.nombre}</h2></div></div>,
    content: <Ficha data={data} />,
  }));
}

// Native GET pages of `acompanamientos/urls.py`, same trailing slashes.
const PATH = /^\/acompanamientos\/acompanamiento\/(?:([0-9]+)\/detalle\/)?$/;

export const acompanamientosRoute: RouteDefinition<Params> = {
  name: "comedores-acompanamientos",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    return m[1] ? { page: "detail", id: m[1] } : { page: "list" };
  },
  render(params) {
    return params.page === "detail" ? <DetailPage key={params.id} id={params.id} /> : <ListPage />;
  },
};
