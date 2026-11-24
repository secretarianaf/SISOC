/* eslint-disable react-refresh/only-export-components -- the unit surface is this module: the board sections, the chart config and the loader. */
import { useEffect, useRef, type ReactNode } from "react";
import { internal, record, text } from "./MainFrame";
import { tarjetasValid, type Tarjetas } from "./comedorFichaTarjetas";

/**
 * CO07.01 ficha, board part of `comedor_detail.html`: the timeline, the four
 * summary boxes, the «Asistencia por rango etareo» chart (Chart.js, as the native
 * page), the «Detalles de Admisión» / «Datos del Convenio» card and the card-holder
 * card. Data is the `tablero` key of `GET /api/web/comedores/comedores/<pk>/`.
 * The right column (nómina) is a slot the page fills with its own component; the
 * transactions and execution month cards (`comedorFichaTarjetas`) go in `rows`.
 */
type Step = { clase: string; circulo: string };
type Fila = { label: string; value: string; mayusculas?: boolean };
export type Tablero = {
  timeline: { admision: Step & { completada: boolean; fecha: string }; conector: string; ejecucion: Step; rendicion: { circulo: string } };
  resumen: { icon: string; valor: string; label: string }[];
  grafico: { label: string; valor: number }[];
  detalles: { tipo: "admision" | "convenio"; titulo: string; filas: Fila[]; territoriales?: { territorial: string; codigo: string }[]; accion: { label: string; url: string | null } };
  responsable_tarjeta: { hay_datos: boolean; datos: [string, string][]; editar: string } | null;
} & Tarjetas;

const strs = (v: unknown, keys: string[]) => record(v) && keys.every((k) => typeof v[k] === "string");

export function tableroValid(v: unknown): v is Tablero {
  if (!record(v) || !record(v.timeline) || !record(v.detalles)) return false;
  const t = v.timeline, d = v.detalles;
  return tarjetasValid(v) && record(t.admision) && strs(t.admision, ["clase", "circulo", "fecha"]) && typeof t.admision.completada === "boolean" && typeof t.conector === "string" &&
    strs(t.ejecucion, ["clase", "circulo"]) && record(t.rendicion) && typeof t.rendicion.circulo === "string" &&
    Array.isArray(v.resumen) && v.resumen.every((c) => strs(c, ["icon", "valor", "label"])) &&
    Array.isArray(v.grafico) && v.grafico.every((g) => record(g) && text(g.label) && typeof g.valor === "number") &&
    (d.tipo === "admision" || d.tipo === "convenio") && typeof d.titulo === "string" && Array.isArray(d.filas) && d.filas.every((f) => strs(f, ["label", "value"])) &&
    record(d.accion) && typeof d.accion.label === "string" && (d.accion.url === null || internal(d.accion.url)) &&
    (v.responsable_tarjeta === null || (record(v.responsable_tarjeta) && typeof v.responsable_tarjeta.hay_datos === "boolean" && Array.isArray(v.responsable_tarjeta.datos) && internal(v.responsable_tarjeta.editar)));
}

// --- Timeline ------------------------------------------------------------------------------------

export function Timeline({ t }: { t: Tablero["timeline"] }) {
  return (
    <div className="mb-3">
      <div className="card-body">
        <div className="timeline-comedor d-flex align-items-center overflow-auto pb-2">
          <div className={t.admision.clase}>
            <div className="circle mx-2">{t.admision.completada ? <i className="bi bi-check-lg" /> : t.admision.circulo}</div>
            <p className="mt-2 mb-0 text-center">Admisión</p>
            <p className="mb-0 text-center"><small>{t.admision.fecha}</small></p>
          </div>
          <div className={`${t.conector} mb-3`} />
          <div className={t.ejecucion.clase}>
            <div className="circle mx-2">{t.ejecucion.circulo}</div>
            <p className="mt-2 mb-0 text-center">Ejecución</p>
            <p className="mb-0 text-center"><small>-</small></p>
          </div>
          <div className="connector mb-3" />
          <div className="step">
            <div className="circle mx-2">{t.rendicion.circulo}</div>
            <p className="mt-2 mb-0 text-center">Rendición</p>
            <p className="mb-0 text-center"><small>-</small></p>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Age-range chart (Chart.js, as the native page) -----------------------------------------------

const CHART_SRC = "https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js";
const COLORS = ["#F05A4F", "#8B7AD8", "#56C271", "#F3C05B", "#56C1B9", "#F2A000"];
type ChartInstance = { destroy: () => void };
type ChartConstructor = new (context: CanvasRenderingContext2D, config: unknown) => ChartInstance;
declare global { interface Window { Chart?: ChartConstructor } }

/** The native script: values as numbers, y axis up to the next ten (at most 100). */
export function edadChartConfig(grafico: Tablero["grafico"]) {
  const data = grafico.map((g) => Number(g.valor) || 0);
  const max = Math.max(...data);
  const yMax = Math.min(100, max > 0 ? Math.ceil(max / 10) * 10 : 10);
  return {
    type: "bar",
    data: { labels: grafico.map((g) => g.label), datasets: [{ data, backgroundColor: COLORS, borderWidth: 0, borderRadius: 6 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c: { parsed: { y?: number } }) => `${c.parsed.y || 0}%` } } },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#ffffff", maxRotation: 45, minRotation: 45 } },
        y: { beginAtZero: true, max: yMax, ticks: { color: "#ffffff", callback: (v: number | string) => `${v}%` }, grid: { color: "rgba(255,255,255,0.08)" } },
      },
    },
  };
}

/** Chart.js 4.4.4 from the same CDN the native layout loads. */
export function withChartJs(run: (chart: ChartConstructor) => void): () => void {
  if (window.Chart) { run(window.Chart); return () => undefined; }
  let script = document.querySelector<HTMLScriptElement>(`script[src="${CHART_SRC}"]`);
  if (!script) {
    script = document.createElement("script");
    script.src = CHART_SRC;
    document.head.appendChild(script);
  }
  const onLoad = () => { if (window.Chart) run(window.Chart); };
  script.addEventListener("load", onLoad);
  return () => script.removeEventListener("load", onLoad);
}

function EdadChart({ grafico }: { grafico: Tablero["grafico"] }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    let instance: ChartInstance | null = null;
    const stop = withChartJs((Chart) => {
      const context = canvas.current?.getContext("2d");
      if (context) instance = new Chart(context, edadChartConfig(grafico));
    });
    return () => { stop(); instance?.destroy(); };
  }, [grafico]);
  return (
    <div className="col-12 col-lg-6 mb-3 mb-lg-0" style={{ marginTop: "5px" }}>
      <div className="card bg-card h-100">
        <div className="card-header py-1"><h6 className="fw-bold my-1 text-center">Asistencia por rango etareo</h6></div>
        <div className="card-body d-flex align-items-center"><div className="w-100 h-100 comedor-chart-h240"><canvas id="nominaEdadChart" ref={canvas} /></div></div>
      </div>
    </div>
  );
}

// --- Cards ---------------------------------------------------------------------------------------

function Resumen({ items }: { items: Tablero["resumen"] }) {
  return (
    <div className="row">
      {items.map((c) => (
        <div className="col-md-3 mx-auto" key={c.label}>
          <div className="small-box bg-card text-center"><div className="inner">
            <h3 className="mb-1 mt-2"><i className={c.icon === "bi bi-cup-hot" ? `${c.icon} mb-1` : c.icon} /></h3>
            <h4 className="fw-bold my-1">{c.valor}</h4>
            <p className="fw-bold fs-7">{c.label}</p>
          </div></div>
        </div>
      ))}
    </div>
  );
}

function Detalles({ d }: { d: Tablero["detalles"] }) {
  const convenio = d.tipo === "convenio";
  return (
    <div className="col-12 col-lg-6">
      <div className="card bg-card h-100">
        <div className="card-header py-1"><h6 className="fw-bold my-1 text-center">{d.titulo}</h6></div>
        <div className="card-body">
          {convenio && (d.territoriales?.length ?? 0) > 0 && (
            <>
              <p className="fw-bold mb-1">Territoriales Asignados</p>
              <ul className="list-unstyled">{d.territoriales!.map((t, i) => <li key={i}>{t.territorial} — Código de Proyecto: {t.codigo}</li>)}</ul>
            </>
          )}
          {d.filas.map((f) => (
            <p className="mb-0 fs-7" key={f.label}>{f.label}: <strong className={f.mayusculas ? "text-uppercase" : undefined}>{f.value}</strong></p>
          ))}
          {convenio ? (
            <div className="mt-3 d-flex justify-content-center"><a href={d.accion.url ?? "#"} className="btn btn-primary px-2 py-1 fs-7 w-100 w-sm-auto">{d.accion.label}</a></div>
          ) : (
            <div className="mt-3 d-flex flex-column flex-sm-row justify-content-center gap-2">
              {d.accion.url ? <a href={d.accion.url} className="btn btn-primary px-2 py-1 fs-7 w-100 w-sm-auto">{d.accion.label}</a>
                : <button className="btn btn-primary px-2 py-1 fs-7 w-100 w-sm-auto" disabled>{d.accion.label}</button>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ResponsableTarjeta({ r }: { r: NonNullable<Tablero["responsable_tarjeta"]> }) {
  return (
    <div className="card bg-card mt-3" id="card-responsable-tarjeta">
      <div className="card-header py-1"><h6 className="fw-bold my-1 text-center"><i className="bi bi-credit-card me-1" />Responsable de la tarjeta</h6></div>
      <div className="card-body d-flex flex-column">
        {r.hay_datos ? (
          <div className="row gy-2">{r.datos.map(([k, v]) => <p key={k} className="col-12 col-md-6 mb-0 fs-7"><strong>{k}:</strong> {v}</p>)}</div>
        ) : <p className="mb-0 fs-7 text-center">Sin datos cargados.</p>}
        <div className="mt-auto pt-3 d-flex justify-content-center">
          <a className="btn btn-primary px-2 py-1 fs-7 w-100 w-sm-auto" href={r.editar}><i className="bi bi-pencil me-1" />Editar datos</a>
        </div>
      </div>
    </div>
  );
}

/**
 * The timeline and the central block. `rows` goes between the details row and the card-holder card
 * (transactions / execution month cards); `aside` is the right column (nómina).
 */
export function FichaTablero({ data, rows, aside }: { data: Tablero; rows?: ReactNode; aside?: ReactNode }) {
  return (
    <>
      <Timeline t={data.timeline} />
      <div className="row mb-3">
        <div className="col-12 col-lg-9 mb-3 mb-lg-0">
          <Resumen items={data.resumen} />
          <div className="row"><EdadChart grafico={data.grafico} /><Detalles d={data.detalles} /></div>
          {rows}
          {data.responsable_tarjeta && <ResponsableTarjeta r={data.responsable_tarjeta} />}
        </div>
        {aside}
      </div>
    </>
  );
}
