/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Breadcrumb, internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { REPORTE_CSS } from "./vatReporteStyles";
import { bool, integer, messagesValid, type Message } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V08.01 reporte de inscriptos y asistencias: `vat/reportes/inscripciones_asistencia.html`. Data comes from
 * `/api/web/vat/reportes/inscripciones-asistencias/`, which runs the native view; the filter form is a plain GET
 * form and the four exports stay native downloads (`?export=...`).
 */
type Option = { value: string; label: string };
type Filter = { key: string; label: string; type: "select" | "date"; permanent: boolean; value: string; options: Option[] };
type Row = Record<string, string>;
type Detail = { documento: string; persona: string; estado: string; con_voucher: boolean; centro: string; comision: string; curso: string; fecha: string };
export type ReporteData = {
  nivel_pill: string; filters: Filter[]; resumen: Record<"inscripciones_total" | "presentes" | "ausentes" | "porcentaje_asistencia", string>;
  group_label: string; group_label_lower: string; rows: Row[];
  page: { is_paginated: boolean; number: number; num_pages: number; count: number; previous: number | null; next: number | null; summary: boolean };
  querystring: string; querystring_detalle: string;
  detalle: { rows: Detail[]; info: { number: number; num_pages: number; count: string; start_index: string; end_index: string; previous: number | null; next: number | null } };
  urls: { list: string; vat: string }; messages: Message[];
};

const API = "web/vat/reportes/inscripciones-asistencias/";
const COLUMNS = ["inscripciones_total", "preinscriptos", "en_espera", "inscriptos", "validados_presencial", "completados", "abandonados", "registros_asistencia", "presentes", "ausentes"];
const nullableInt = (v: unknown) => v === null || integer(v);

const optionValid = (o: unknown) => record(o) && text(o.value) && text(o.label);
const filterValid = (f: unknown) => record(f) && text(f.key) && text(f.label) && (f.type === "select" || f.type === "date") && bool(f.permanent) && text(f.value) &&
  Array.isArray(f.options) && f.options.every(optionValid);
const rowValid = (r: unknown) => record(r) && ["grupo", ...COLUMNS, "porcentaje_asistencia", "sesiones_programadas", "sesiones_realizadas"].every((k) => text(r[k]));
const detailValid = (d: unknown) => record(d) && ["documento", "persona", "estado", "centro", "comision", "curso", "fecha"].every((k) => text(d[k])) && bool(d.con_voucher);

export function reporteValid(v: unknown): v is ReporteData {
  if (!record(v) || !text(v.nivel_pill) || !Array.isArray(v.filters) || !v.filters.every(filterValid) || !record(v.resumen) ||
    !["inscripciones_total", "presentes", "ausentes", "porcentaje_asistencia"].every((k) => text((v.resumen as Record<string, unknown>)[k])) ||
    !text(v.group_label) || !text(v.group_label_lower) || !Array.isArray(v.rows) || !v.rows.every(rowValid) || !record(v.page) || !text(v.querystring) || !text(v.querystring_detalle) ||
    !record(v.detalle) || !Array.isArray(v.detalle.rows) || !v.detalle.rows.every(detailValid) || !record(v.detalle.info) || !record(v.urls) || !internal(v.urls.list) || !internal(v.urls.vat)) return false;
  const p = v.page, i = v.detalle.info;
  return bool(p.is_paginated) && integer(p.number) && integer(p.num_pages) && integer(p.count) && nullableInt(p.previous) && nullableInt(p.next) && bool(p.summary) &&
    integer(i.number) && integer(i.num_pages) && ["count", "start_index", "end_index"].every((k) => text(i[k])) && nullableInt(i.previous) && nullableInt(i.next) && messagesValid(v.messages);
}

/** What the browser keeps of a value: a select with no matching option shows its first one, a date input only a valid date. */
function normalized(f: Filter) {
  if (f.type === "select") return f.options.some((o) => o.value === f.value) ? f.value : f.options[0]?.value ?? "";
  const m = /^(\d{4,})-(\d{2})-(\d{2})$/.exec(f.value);
  if (!m) return "";
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  return d.getUTCFullYear() === Number(m[1]) && d.getUTCMonth() === Number(m[2]) - 1 && d.getUTCDate() === Number(m[3]) ? f.value : "";
}

/** Filters and export of the card: the fields beyond `Nivel` and `Agrupar por` appear when they carry a value or are added. */
function FiltersCard({ data }: { data: ReporteData }) {
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(data.filters.map((f) => [f.key, normalized(f)])));
  const [shown, setShown] = useState<Record<string, boolean>>(() => Object.fromEntries(data.filters.map((f) => [f.key, f.permanent || normalized(f) !== ""])));
  const focus = useRef<string | null>(null);
  useEffect(() => {
    if (focus.current) { document.getElementById(`id_${focus.current}`)?.focus(); focus.current = null; }
  });
  const optional = data.filters.filter((f) => !f.permanent);
  const visibles = optional.filter((f) => shown[f.key]).length;
  const qs = data.querystring ? `${data.querystring}&` : "";
  return (
    <div className="rep-card">
      <div className="rep-card-head"><i className="bi bi-funnel" /><span>Filtros y exportación</span></div>
      <div className="rep-card-body">
        <form method="get">
          <div className="rep-filter-toolbar">
            <span className="rep-filter-toolbar__title">Filtros</span>
            <select className="rep-add-filter" id="repAddFilter" aria-label="Agregar filtro" value=""
              onChange={(e) => { const key = e.target.value; if (!key) return; setShown((s) => ({ ...s, [key]: true })); focus.current = key; }}>
              <option value="">+ Agregar filtro…</option>
              {optional.filter((f) => !shown[f.key]).map((f) => <option key={f.key} value={f.key}>{f.label}</option>)}
            </select>
            <span className="rep-filter-hint" id="repFilterHint">{visibles ? (visibles === 1 ? "1 filtro aplicado" : `${visibles} filtros aplicados`) : "Sin filtros adicionales — se muestra todo."}</span>
          </div>
          <div className="rep-filter-grid">
            {data.filters.map((f) => (
              <label key={f.key} className={shown[f.key] ? "rep-field" : "rep-field is-hidden"} htmlFor={`id_${f.key}`}>
                <span className="rep-field__label">{f.label}</span>
                {f.type === "select"
                  ? <select id={`id_${f.key}`} name={f.key} value={values[f.key]} onChange={(e) => setValues((s) => ({ ...s, [f.key]: e.target.value }))}>
                    {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                  : <input id={`id_${f.key}`} type="date" name={f.key} value={values[f.key]} onChange={(e) => setValues((s) => ({ ...s, [f.key]: e.target.value }))} />}
                {!f.permanent && <button type="button" className="rep-field__remove" aria-label={`Quitar filtro ${f.label}`}
                  onClick={() => { setShown((s) => ({ ...s, [f.key]: false })); setValues((s) => ({ ...s, [f.key]: "" })); }}>&times;</button>}
              </label>
            ))}
          </div>
          <div className="rep-filter-actions">
            <button type="submit" className="rep-btn rep-btn--primary"><i className="bi bi-search" />Aplicar filtros</button>
            <a href={data.urls.list} className="rep-btn rep-btn--ghost"><i className="bi bi-arrow-clockwise" />Limpiar</a>
            <a href={`?${qs}export=csv`} className="rep-btn rep-btn--ghost" title="Exporta el resumen agrupado (una fila por grupo)"><i className="bi bi-filetype-csv" />Resumen CSV</a>
            <a href={`?${qs}export=xlsx`} className="rep-btn rep-btn--ghost" title="Exporta el resumen agrupado (una fila por grupo)"><i className="bi bi-file-earmark-excel" />Resumen Excel</a>
          </div>
        </form>
      </div>
    </div>
  );
}

const METRICS: [string, string, "inscripciones_total" | "presentes" | "ausentes" | "porcentaje_asistencia", string, string][] = [
  ["gold", "Inscriptos totales", "inscripciones_total", "Total del corte filtrado", ""],
  ["green", "Presentes", "presentes", "Con asistencia registrada", ""],
  ["red", "Ausentes", "ausentes", "Sin asistencia", ""],
  ["gold", "% asistencia", "porcentaje_asistencia", "Sobre presentes + ausentes", "%"],
];

function Pager({ previous, next, label, href, aria }: { previous: number | null; next: number | null; label: string; href: (n: number) => string; aria: boolean }) {
  return <div className="rep-pager">
    {previous !== null
      ? <a className="rep-pager-prev" {...(aria ? { "aria-label": "Página anterior" } : {})} href={href(previous)}><i className="bi bi-chevron-left" /></a>
      : <span className="rep-pager-prev is-disabled"><i className="bi bi-chevron-left" /></span>}
    <span className="rep-pager-label">{label}</span>
    {next !== null
      ? <a className="rep-pager-next" {...(aria ? { "aria-label": "Página siguiente" } : {})} href={href(next)}><i className="bi bi-chevron-right" /></a>
      : <span className="rep-pager-next is-disabled"><i className="bi bi-chevron-right" /></span>}
  </div>;
}

function Summary({ data }: { data: ReporteData }) {
  const [term, setTerm] = useState("");
  const needle = term.trim().toLowerCase();
  const match = (row: Row) => Object.values(row).join("").toLowerCase().includes(needle);
  const visible = data.rows.filter(match).length;
  const qs = data.querystring ? `${data.querystring}&` : "";
  const { page } = data;
  return (
    <div className="rep-card">
      <div className="rep-card-head"><i className="bi bi-bar-chart" /><span>Resumen por {data.group_label_lower}</span></div>
      <div className="rep-tbl-toolbar">
        <label className="rep-field" htmlFor="reporteQuickSearch">
          <span className="rep-field__label">Buscar en esta página</span>
          <input type="search" id="reporteQuickSearch" placeholder="Filtrar filas visibles" value={term} onChange={(e) => setTerm(e.target.value)} />
        </label>
        <span id="reporteQuickCounter" className="rep-tbl-counter">{data.rows.length ? `${visible}${visible === 1 ? " fila visible" : " filas visibles"} en esta página` : ""}</span>
      </div>
      <div className="rep-tbl-scroll">
        <table className="rep-tbl" id="reporteResumenTabla">
          <thead><tr>
            <th>{data.group_label}</th><th>Inscriptos</th><th>Preinscriptos</th><th>En espera</th><th>Inscriptos</th><th>Validados</th><th>Completados</th><th>Abandonados</th>
            <th>Reg. asistencia</th><th>Presentes</th><th>Ausentes</th><th>% asistencia</th><th>Sesiones programadas</th><th>Sesiones realizadas</th>
          </tr></thead>
          <tbody>
            {data.rows.length ? data.rows.map((row, i) => (
              <tr key={i} data-reporter-row="" hidden={!match(row)}>
                <td>{row.grupo}</td>
                {COLUMNS.map((k) => <td key={k}>{row[k]}</td>)}
                <td>{row.porcentaje_asistencia}%</td>
                <td>{row.sesiones_programadas}</td>
                <td>{row.sesiones_realizadas}</td>
              </tr>
            )) : <tr className="rep-tbl-empty"><td colSpan={14}>No hay datos para los filtros seleccionados.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="rep-tbl-foot">
        <span>{page.summary && `Página ${page.number} de ${page.num_pages} · ${page.count} grupo${page.count === 1 ? "" : "s"}`}</span>
        {page.is_paginated && <Pager previous={page.previous} next={page.next} label={`${page.number} de ${page.num_pages}`} href={(n) => `?${qs}page=${n}`} aria={false} />}
      </div>
    </div>
  );
}

function DetailCard({ data }: { data: ReporteData }) {
  const { info, rows } = data.detalle;
  const qs = data.querystring ? `${data.querystring}&` : "";
  const qd = data.querystring_detalle ? `${data.querystring_detalle}&` : "";
  return (
    <div className="rep-card" id="repDetalleTabla">
      <div className="rep-card-head">
        <i className="bi bi-person-lines-fill" />
        <span>Personas inscriptas{" "}<small style={{ fontWeight: 400, opacity: 0.8 }}>({info.count} en total)</small></span>
        <div className="rep-detalle-export">
          <a href={`?${qs}export=detalle_csv`} className="rep-btn rep-btn--ghost" title="Exporta TODAS las personas (con los filtros aplicados)"><i className="bi bi-filetype-csv" />Detalle CSV</a>
          <a href={`?${qs}export=detalle_xlsx`} className="rep-btn rep-btn--ghost" title="Exporta TODAS las personas (con los filtros aplicados)"><i className="bi bi-file-earmark-excel" />Detalle Excel</a>
        </div>
      </div>
      <div className="rep-tbl-scroll">
        <table className="rep-tbl">
          <thead><tr><th>DNI</th><th>Apellido y nombre</th><th>Estado</th><th>Tipo de alumno</th><th>Centro</th><th>Comisión</th><th>Curso/Oferta</th><th>Fecha inscripción</th></tr></thead>
          <tbody id="repDetalleBody">
            {rows.length ? rows.map((r, i) => (
              <tr key={i} className="rep-detalle-row">
                <td>{r.documento}</td>
                <td>{r.persona}</td>
                <td><span className="rep-pill">{r.estado}</span></td>
                <td>{r.con_voucher ? <span className="rep-pill rep-pill--vat">VAT</span> : <span className="rep-pill rep-pill--sin-plan">Sin Plan</span>}</td>
                <td>{r.centro}</td>
                <td>{r.comision}</td>
                <td>{r.curso}</td>
                <td>{r.fecha}</td>
              </tr>
            )) : <tr className="rep-tbl-empty"><td colSpan={8}>No hay personas para los filtros seleccionados.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="rep-tbl-foot">
        <span id="repDetalleConteo">{`Mostrando ${info.start_index}-${info.end_index} de ${info.count}`}</span>
        {info.num_pages > 1 && <Pager previous={info.previous} next={info.next} label={`${info.number} de ${info.num_pages}`} href={(n) => `?${qd}detalle_page=${n}#repDetalleTabla`} aria />}
      </div>
    </div>
  );
}

const loaded = new Map<string, Promise<void>>();
function loadScript(src: string) {
  if (!loaded.has(src)) loaded.set(src, new Promise<void>((resolve) => {
    const element = document.createElement("script");
    element.src = src;
    element.onload = () => resolve();
    element.onerror = () => { loaded.delete(src); resolve(); };
    document.body.appendChild(element);
  }));
  return loaded.get(src)!;
}

type VatTour = { runSection: () => void; runGeneral: () => void; resetSeen: () => void };
const tour = () => (window as Window & { SisocVatTour?: VatTour }).SisocVatTour;

const TOUR_CSS = `
    #sisoc-vat-tour-btn {
        position: fixed;
        right: 1.5rem;
        bottom: 1.5rem;
        z-index: 1080;
        border-radius: 999px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        padding: 0.65rem 1.1rem;
        font-weight: 600;
    }
    #sisoc-vat-tour-btn .dropdown-menu {
        min-width: 14rem;
    }
`;

/** `vat/partials/tour.html`: the floating help menu and the driver.js tour of the screen (it never starts by itself). */
function TourHelp() {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    (window as Window & { SISOC_VAT_TOUR?: unknown }).SISOC_VAT_TOUR = { section: "reporte_inscripciones", autoStart: true };
    void loadScript("/static/custom/js/driver.js.iife.js").then(() => loadScript("/static/custom/js/vat_tour.js?v=20260607b"));
  }, []);
  useEffect(() => {
    if (!open) return undefined;
    const outside = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    const escape = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("click", outside);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("click", outside); document.removeEventListener("keydown", escape); };
  }, [open]);
  const run = (action: "section" | "general" | "reset") => (e: { preventDefault: () => void }) => {
    e.preventDefault();
    setOpen(false);
    const t = tour();
    if (!t) return;
    if (action === "general") t.runGeneral();
    else if (action === "reset") { t.resetSeen(); t.runSection(); } else t.runSection();
  };
  // The native partial sits in `customJS`, at the end of `<body>`: same DOM and Tab position.
  return createPortal(<>
    <link rel="stylesheet" href="/static/custom/css/driver.css" />
    <style>{TOUR_CSS}</style>
    <div ref={root} className={`dropup${open ? " show" : ""}`} id="sisoc-vat-tour-container">
      <button id="sisoc-vat-tour-btn" type="button" className={`btn btn-primary dropdown-toggle${open ? " show" : ""}`} data-vat-tour="help-button" aria-expanded={open}
        onClick={() => setOpen((v) => !v)}>
        <i className="fas fa-question-circle me-1" />{" "}Tour de ayuda{" "}
      </button>
      <ul className={`dropdown-menu dropdown-menu-end${open ? " show" : ""}`} style={open ? { position: "fixed", right: "1.5rem", bottom: "4.6rem", left: "auto", top: "auto", margin: 0 } : undefined}>
        <li><a className="dropdown-item" href="#" data-vat-tour-action="section" onClick={run("section")}><i className="fas fa-location-arrow me-2" />{" "}Tour de esta pantalla</a></li>
        <li><a className="dropdown-item" href="#" data-vat-tour-action="general" onClick={run("general")}><i className="fas fa-map me-2" />{" "}Tour general del modulo VAT</a></li>
        <li><hr className="dropdown-divider" /></li>
        <li><a className="dropdown-item text-muted" href="#" data-vat-tour-action="reset" onClick={run("reset")}><i className="fas fa-rotate-left me-2" />{" "}Reiniciar tours vistos</a></li>
      </ul>
    </div>
  </>, document.body);
}

export function ReporteContent({ data }: { data: ReporteData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
    <link href="https://fonts.googleapis.com/css2?family=Lora:wght@600;700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <style>{REPORTE_CSS}</style>
    <div className="rep-page">
      <div className="rep-title-row">
        <div className="rep-title-block">
          <h1>Reporte general de inscriptos y asistencias</h1>
          <p className="rep-title-sub">{"Vista consolidada para centro, provincia e INET con métricas de inscripción, asistencia y sesiones para seguimiento operativo."}</p>
        </div>
        <span className="rep-status-pill">Nivel: {data.nivel_pill}</span>
      </div>
      <FiltersCard data={data} />
      <div className="rep-metric-grid">
        {METRICS.map(([tone, label, key, support, suffix]) => (
          <article key={label} className={`rep-metric-card rep-metric-card--${tone}`}>
            <p className="rep-metric__label">{label}</p>
            <strong className="rep-metric__value">{data.resumen[key]}{suffix}</strong>
            <span className="rep-metric__support">{support}</span>
          </article>
        ))}
      </div>
      <Summary data={data} />
      <DetailCard data={data} />
    </div>
    <TourHelp />
  </>;
}

function ReportePage() {
  const [state] = useMainResource(`${API}${window.location.search}`, reporteValid);
  return renderMain(state, "Cargando reporte…", (data) => ({
    title: "VAT - Reporte de Inscriptos y Asistencias",
    breadcrumb: <Breadcrumb items={[{ text: "VAT", url: data.urls.vat }, { text: "Reporte General", url: null }]} />,
    content: <ReporteContent data={data} />,
  }));
}

// Native URL of `VAT/urls.py`.
const PATH = /^\/vat\/reportes\/inscripciones-asistencias\/$/;

export const vatReporteRoute: RouteDefinition<Record<string, never>> = {
  name: "vat-reporte",
  match: (pathname) => (PATH.test(pathname) ? {} : null),
  render: () => <ReportePage />,
};
