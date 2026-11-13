/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { Pagination } from "./listControls";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { PARAMETRIA_DETAIL_CSS } from "./vatParametriaDetailStyles";
import { CsrfInput, UNCERTAIN, useForbidden } from "./vatFormShared";
import { bool, integer, messagesValid, vatNavigation, type Message } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V01.01/V01.03 `parametria_detail.html`. Data comes from `/api/web/vat/vouchers/parametrias/<id>/`, which runs the
 * native view; the two assignment forms POST to the API (`asignar/`, `asignar-masivo/`), which runs the native views
 * and answers with their redirect to this page (the messages show there).
 */
type Row = { id: number; ciudadano: string; documento: string; disponible: number; inicial: number; barra: string; ancho: string; badge: string; estado_label: string; detail_url: string };
type Last = { ciudadano: string; documento: string; fecha: string; badge: string; estado_label: string };
export type ParametriaDetailData = {
  id: number; nombre: string; descripcion: string; programa: string; cantidad_inicial: number; vencimiento: string; renovacion_mensual: boolean;
  cantidad_renovacion: number | null; renovacion_tipo_label: string; inscripcion_unica_activa: boolean; activa: boolean;
  total: number; activos: number; agotados: number; vencidos: number; cancelados: number;
  creditos_emitidos: number; creditos_usados: number; creditos_disponibles: number; pct_uso: number; pct_activos: number;
  pct_agotados: string; pct_vencidos: string; pct_cancelados: string; ultimas: Last[]; vouchers: Row[]; vouchers_total_filtrados: number; search_query: string;
  page: { is_paginated: boolean; number: number; num_pages: number; count: number; previous: number | null; next: number | null; range: (number | "…")[]; query_prefix: string; shown: boolean };
  permisos: { asignar: boolean }; urls: { list: string; detail: string; asignar: string; asignar_masivo: string }; messages: Message[];
};

const API = "web/vat/vouchers/parametrias/";
const rowValid = (r: unknown) => record(r) && integer(r.id) && integer(r.disponible) && integer(r.inicial) &&
  ["ciudadano", "documento", "barra", "ancho", "badge", "estado_label"].every((k) => text(r[k])) && internal(r.detail_url);
const lastValid = (r: unknown) => record(r) && ["ciudadano", "documento", "fecha", "badge", "estado_label"].every((k) => text(r[k]));

export function parametriaDetailValid(v: unknown): v is ParametriaDetailData {
  if (!record(v) || !integer(v.id) || !["nombre", "descripcion", "programa", "vencimiento", "renovacion_tipo_label", "pct_agotados", "pct_vencidos", "pct_cancelados", "search_query"].every((k) => text(v[k])) ||
    !["cantidad_inicial", "total", "activos", "agotados", "vencidos", "cancelados", "creditos_emitidos", "creditos_usados", "creditos_disponibles", "pct_uso", "pct_activos", "vouchers_total_filtrados"].every((k) => integer(v[k])) ||
    !["renovacion_mensual", "inscripcion_unica_activa", "activa"].every((k) => bool(v[k])) || !(v.cantidad_renovacion === null || integer(v.cantidad_renovacion)) ||
    !Array.isArray(v.ultimas) || !v.ultimas.every(lastValid) || !Array.isArray(v.vouchers) || !v.vouchers.every(rowValid) || !record(v.page) || !record(v.permisos) || !record(v.urls)) return false;
  const p = v.page;
  return bool(p.is_paginated) && integer(p.number) && integer(p.num_pages) && integer(p.count) && (p.previous === null || integer(p.previous)) && (p.next === null || integer(p.next)) &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || integer(n)) && text(p.query_prefix) && bool(p.shown) && bool(v.permisos.asignar) &&
    ["list", "detail", "asignar", "asignar_masivo"].every((k) => internal((v.urls as Record<string, unknown>)[k])) && messagesValid(v.messages);
}

const SMALL = { letterSpacing: ".05em" };
const stat = { letterSpacing: ".04em", fontSize: ".72rem" };
const metric = { fontSize: ".75rem", textTransform: "uppercase" as const, letterSpacing: ".05em" };

function AssignPanel({ data, forbidden }: { data: ParametriaDetailData; forbidden: (d: unknown) => void }) {
  const [tab, setTab] = useState<"individual" | "masivo">("individual");
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  const send = (endpoint: string) => async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true;
    const body = new URLSearchParams();
    for (const [k, v] of new FormData(event.currentTarget)) if (k !== "csrfmiddlewaretoken") body.append(k, String(v));
    const result = await postForm(endpoint, body);
    busy.current = false;
    if (result.kind === "redirect") vatNavigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else setUncertain(true);
  };
  return (
    <div className="col-md-5"><div className="assign-panel shadow-sm">
      <div className="assign-tab">
        <button className={tab === "individual" ? "active" : undefined} onClick={() => setTab("individual")} type="button"><i className="bi bi-person-plus me-1" />Individual</button>{" "}
        <button className={tab === "masivo" ? "active" : undefined} onClick={() => setTab("masivo")} type="button"><i className="bi bi-people me-1" />Masiva</button>
      </div>
      <div id="tab-individual" className="assign-body" style={{ display: tab === "individual" ? "block" : "none" }}>
        <p className="text-muted small mb-3">Buscá al ciudadano por DNI. Se asignarán <strong>{data.cantidad_inicial} créditos</strong> con vencimiento <strong>{data.vencimiento}</strong>.</p>
        <form method="post" action={data.urls.asignar} onSubmit={(e) => void send(data.urls.asignar.replace(/^\/vat\//, "web/vat/"))(e)}>
          <CsrfInput />
          {uncertain && <p role="alert">{UNCERTAIN}</p>}
          <label className="form-label small fw-semibold text-uppercase text-muted" style={SMALL}>DNI</label>{" "}
          <div className="input-group">
            <span className="input-group-text"><i className="bi bi-search" /></span>
            <input type="text" name="dni" className="form-control font-monospace" placeholder="Ej: 30123456" required pattern="[0-9]+" title="Solo números" autoComplete="off" />
            <button type="submit" className="btn btn-primary"><i className="bi bi-check-lg" /></button>
          </div>
          <div className="text-muted small mt-2"><i className="bi bi-info-circle me-1" />Si ya tiene voucher agotado o vencido, se reactivará.</div>
        </form>
      </div>
      <div id="tab-masivo" className="assign-body" style={{ display: tab === "masivo" ? "block" : "none" }}>
        <p className="text-muted small mb-3">Pegá hasta <strong>500 DNIs</strong> separados por coma, espacio o salto de línea.</p>
        <form method="post" action={data.urls.asignar_masivo} onSubmit={(e) => void send(data.urls.asignar_masivo.replace(/^\/vat\//, "web/vat/"))(e)}>
          <CsrfInput />
          <label className="form-label small fw-semibold text-uppercase text-muted" style={SMALL}>DNIs</label>{" "}
          <textarea name="dnis" className="form-control form-control-sm font-monospace mb-3" rows={7} placeholder={"30123456\n28765432\n35987654"} />{" "}
          <button type="submit" className="btn btn-primary w-100"><i className="bi bi-check-all me-1" />Procesar asignación masiva</button>
        </form>
      </div>
    </div></div>
  );
}

const Bar = ({ tone, height, radius, width }: { tone: string; height: number; radius: number; width: string }) => (
  <div className="progress" style={{ height: `${height}px`, borderRadius: `${radius}px` }}><div className={`progress-bar bg-${tone}`} style={{ width: `${width}%` }} /></div>
);

function Distribution({ tone, badge, label, n, pct }: { tone: string; badge: string; label: string; n: number; pct: string }) {
  return <div>
    <div className="d-flex justify-content-between align-items-center mb-1">
      <span><span className={`badge ${badge} me-1`} style={{ fontSize: ".55rem" }}>●</span>{label}</span>
      <span className="fw-bold">{n}{" "}<span className="text-muted fw-normal small">({pct}%)</span></span>
    </div>
    <Bar tone={tone} height={6} radius={3} width={pct} />
  </div>;
}

export function ParametriaDetailContent({ data, forbidden }: { data: ParametriaDetailData; forbidden: (d: unknown) => void }) {
  const p = data.page;
  const pill = (b: string, label: string) => <span className={`badge rounded-pill ${b}`}>{label}</span>;
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/cardsDetail.css" />
    <style>{PARAMETRIA_DETAIL_CSS}</style>
    <div className="parametria-hero">
      <div className="d-flex justify-content-between align-items-start flex-wrap gap-3">
        <div>
          <div className="hero-label mb-1">Parametría de voucher</div>
          <h4 className="mb-1 text-white fw-bold">{data.nombre}</h4>
          {data.descripcion && <div className="small mb-2" style={{ opacity: 0.75 }}>{data.descripcion}</div>}
          <div className="d-flex flex-wrap gap-2 mt-2">
            <span className="badge" style={{ background: "rgba(255,255,255,.2)", color: "#fff" }}><i className="bi bi-collection me-1" />{data.programa}</span>{" "}
            <span className="badge" style={{ background: "rgba(255,255,255,.2)", color: "#fff" }}><i className="bi bi-calendar-x me-1" />Vence {data.vencimiento}</span>
            {data.renovacion_mensual && <>{" "}<span className="badge bg-warning text-dark"><i className="bi bi-arrow-repeat me-1" />Renovación mensual{" "}
              {data.cantidad_renovacion !== null && <>· {data.cantidad_renovacion} créd.</>}{" "}· {data.renovacion_tipo_label}</span></>}
            {data.inscripcion_unica_activa && <>{" "}<span className="badge" style={{ background: "rgba(255,255,255,.2)", color: "#fff" }}><i className="bi bi-1-circle me-1" />Inscripción única activa</span></>}
          </div>
        </div>
        <div className="d-flex gap-2 align-items-start">
          {data.activa ? <span className="badge bg-success px-3 py-2">Activa</span> : <span className="badge bg-secondary px-3 py-2">Inactiva</span>}
        </div>
      </div>
    </div>
    <div className="row g-2 mb-3">
      {([["", data.total, "Total"], ["text-success", data.activos, "Activos"], ["text-warning", data.agotados, "Agotados"], ["text-danger", data.vencidos, "Vencidos"]] as const).map(([cls, n, label]) => (
        <div key={label} className="col-6 col-md-3"><div className="card text-center py-3">
          <div className={`fs-2 fw-bold ${cls}`.trimEnd()}>{n}</div>
          <div className="text-muted small text-uppercase" style={stat}>{label}</div>
        </div></div>
      ))}
    </div>
    <div className="row g-3">
      <div className="col-md-7"><div className="card h-100">
        <div className="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
          <h3 className="card-title mb-0 fs-6 fw-semibold"><i className="bi bi-ticket-perforated me-2 text-primary" />Vouchers asignados</h3>
          {data.total > 0 && <span className="badge bg-primary rounded-pill">{data.total}</span>}
        </div>
        <div className="card-body p-0">
          <div className="p-3 border-bottom bg-body-tertiary">
            <form method="get" className="row g-2 align-items-end">
              <div className="col-sm-8">
                <label className="form-label small fw-semibold text-uppercase text-muted mb-1" style={SMALL}>Buscar por ciudadano o DNI</label>{" "}
                <input type="search" name="busqueda" className="form-control form-control-sm" placeholder="Ej: Pérez o 30123456" defaultValue={data.search_query} autoComplete="off" />
              </div>
              <div className="col-sm-auto"><button type="submit" className="btn btn-primary btn-sm w-100"><i className="bi bi-search me-1" />Filtrar</button></div>
              <div className="col-sm-auto"><a href={data.urls.detail} className="btn btn-outline-secondary btn-sm w-100">Limpiar</a></div>
            </form>
            <div className="text-muted small mt-2">
              Mostrando {data.vouchers_total_filtrados} voucher{data.vouchers_total_filtrados === 1 ? "" : "s"}{" "}
              {data.search_query && <>para la búsqueda actual</>}{" "}.
            </div>
          </div>
          {data.vouchers.length > 0 ? <>
            <div className="table-responsive"><table className="table table-sm table-hover mb-0 align-middle">
              <thead><tr><th>Ciudadano</th><th>DNI</th><th className="text-end">Créditos</th><th>Estado</th><th /></tr></thead>
              <tbody>{data.vouchers.map((v) => <tr key={v.id}>
                <td className="fw-semibold">{v.ciudadano}</td>
                <td className="text-muted small font-monospace">{v.documento}</td>
                <td className="text-end">
                  <span className="fw-bold">{v.disponible}</span>{" "}<span className="text-muted small">/ {v.inicial}</span>
                  <div className="progress mt-1" style={{ height: "3px", width: "60px", marginLeft: "auto" }}><div className={`progress-bar ${v.barra}`} style={{ width: `${v.ancho}%` }} /></div>
                </td>
                <td>{pill(v.badge, v.estado_label)}</td>
                <td className="text-end"><a href={v.detail_url} className="btn btn-sm btn-outline-primary py-0 px-2"><i className="bi bi-eye" /></a></td>
              </tr>)}</tbody>
            </table></div>
            <div className="p-3 pt-2">
              <Pagination paginated={p.is_paginated} number={p.number} previous={p.previous} next={p.next} range={p.range} href={(n) => `?${p.query_prefix}vouchers_page=${n}`}
                count={p.shown ? p.count : null} prevText="Anterior" nextText="Siguiente" />
            </div>
          </> : <div className="empty-state">
            <i className="bi bi-ticket-perforated" />
            <p>{data.search_query ? "No hay vouchers que coincidan con la búsqueda." : <>Todavía no hay vouchers asignados<br />desde esta parametría.</>}</p>
          </div>}
        </div>
      </div></div>
      {data.permisos.asignar && <AssignPanel data={data} forbidden={forbidden} />}
    </div>
    {data.total > 0 ? <div className="row g-3 mt-1">
      <div className="col-md-4"><div className="card h-100">
        <div className="card-header"><h3 className="card-title mb-0 fs-6 fw-semibold"><i className="bi bi-lightning-charge me-2 text-primary" />Uso de créditos</h3></div>
        <div className="card-body d-flex flex-column justify-content-between gap-3">
          <div className="row g-2 text-center">
            <div className="col-6"><div className="fs-3 fw-bold text-primary">{data.creditos_usados}</div><div className="text-muted" style={metric}>Usados</div></div>
            <div className="col-6"><div className="fs-3 fw-bold">{data.creditos_emitidos}</div><div className="text-muted" style={metric}>Emitidos</div></div>
          </div>
          <div>
            <div className="d-flex justify-content-between mb-1"><span className="small fw-bold text-primary">{data.pct_uso}% usado</span><span className="small text-muted">{data.creditos_disponibles} disponibles</span></div>
            <Bar tone="primary" height={10} radius={5} width={String(data.pct_uso)} />
          </div>
        </div>
      </div></div>
      <div className="col-md-4"><div className="card h-100">
        <div className="card-header"><h3 className="card-title mb-0 fs-6 fw-semibold"><i className="bi bi-pie-chart me-2 text-primary" />Distribución por estado</h3></div>
        <div className="card-body d-flex flex-column gap-3">
          <Distribution tone="success" badge="bg-success" label="Activos" n={data.activos} pct={String(data.pct_activos)} />
          {data.agotados > 0 && <Distribution tone="warning" badge="bg-warning text-dark" label="Agotados" n={data.agotados} pct={data.pct_agotados} />}
          {data.vencidos > 0 && <Distribution tone="danger" badge="bg-danger" label="Vencidos" n={data.vencidos} pct={data.pct_vencidos} />}
          {data.cancelados > 0 && <Distribution tone="secondary" badge="bg-secondary" label="Cancelados" n={data.cancelados} pct={data.pct_cancelados} />}
        </div>
      </div></div>
      <div className="col-md-4"><div className="card h-100">
        <div className="card-header"><h3 className="card-title mb-0 fs-6 fw-semibold"><i className="bi bi-clock-history me-2 text-primary" />Últimas asignaciones</h3></div>
        <div className="card-body p-0">{data.ultimas.map((v, i) => (
          <div key={i} className={`d-flex justify-content-between align-items-center px-3 py-3${i < data.ultimas.length - 1 ? " border-bottom" : ""}`}>
            <div>
              <div className="fw-semibold">{v.ciudadano}</div>
              <div className="text-muted small font-monospace">{v.documento}</div>
              <div className="text-muted small mt-1">{v.fecha}</div>
            </div>
            {pill(v.badge, v.estado_label)}
          </div>
        ))}</div>
      </div></div>
    </div> : <div className="row g-3 mt-1"><div className="col-12"><div className="card"><div className="card-body">
      <div className="empty-state"><i className="bi bi-bar-chart-line" /><p>Sin datos todavía. Asigná vouchers para ver métricas.</p></div>
    </div></div></div></div>}
  </>;
}

function DetailPage({ id }: { id: string }) {
  const [state, setState] = useMainResource(`${API}${id}/${window.location.search}`, parametriaDetailValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando parametría…", (data) => ({
    title: data.nombre, heading: "Parametría de Voucher", breadcrumb: null, activePath: "/vat/vouchers/parametrias/",
    content: <ParametriaDetailContent data={data} forbidden={forbidden} />,
  }));
}

// Native URL of `VAT/urls.py`; `nueva/` and the POST routes are not mine.
const PATH = /^\/vat\/vouchers\/parametrias\/([0-9]+)\/$/;

export const vatParametriaDetalleRoute: RouteDefinition<{ id: string }> = {
  name: "vat-parametria-detalle",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { id: m[1] } : null;
  },
  render: ({ id }) => <DetailPage key={id} id={id} />,
};
