/* eslint-disable react-refresh/only-export-components -- unit surface: the ficha sections, the chart loader and the validators travel together for the tests. */
import { useEffect, useRef, useState, type CSSProperties, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { internal, postForm, record, text } from "./MainFrame";

/**
 * C05.01: everything of `ciudadanos/ciudadano_detail.html` that is not a vertical card: the header with its actions, the
 * identity notice, the tabs, "Datos personales", "Grupo Familiar", the transfer history chart, the program cards, the
 * interactions and the observations. Values arrive already formatted by `ciudadanos.web_ficha` (the native template
 * filters), so nothing is formatted here.
 */
export type Identidad = {
  mostrar: boolean; sin_dni: boolean; no_validado: boolean; requiere_revision: boolean; motivo_texto: string; descripcion_texto: string;
};
export type Acciones = { historial_url: string | null; editar_url: string; eliminar_url: string; familiar_nuevo_url: string; marcar_revisado_url: string | null };
export type Datos = Record<Exclude<(typeof DATOS_COLUMNA_1)[number][0] | (typeof DATOS_COLUMNA_2)[number][0], "pais_emisor">, string> & { pais_emisor: string | null };
export type Familiar = { vinculo_texto: string; nombre: string; apellido: string; edad_texto: string; url: string };
export type Historial = { labels: string[]; auh: number[]; prestacion: number[]; centro_familia: number[]; comedor: number[] };
export type Interaccion = { tipo: string; fecha_texto: string; responsable_texto: string; estado: "completo" | "en_plan" | "pendiente" };
export type FichaExtra = {
  identidad: Identidad; acciones: Acciones; datos: Datos; mapa: string | null; foto_url: string | null; familia: Familiar[];
  historial: Historial; interacciones: Interaccion[]; observaciones: string; messages: { message: string; level: "success" | "error" | "warning" | "info" }[];
};

const DATOS_COLUMNA_1 = [
  ["cuil_cuit", "CUIL/CUIT:"], ["apellido", "Apellido:"], ["nombre", "Nombre:"], ["tipo_documento", "Tipo de Documento:"],
  ["numero_documento", "Número de Documento:"], ["pais_emisor", "País Emisor:"], ["provincia", "Provincia:"], ["municipio", "Municipio:"],
  ["localidad", "Localidad:"], ["calle_altura", "Calle y Altura:"], ["codigo_postal", "Código Postal:"],
] as const;
const DATOS_COLUMNA_2 = [
  ["fecha_nacimiento", "Fecha de nacimiento:"], ["edad", "Edad:"], ["genero", "Género:"], ["estado_civil", "Estado Civil:"],
  ["nacionalidad", "Nacionalidad:"], ["telefono", "Teléfono:"], ["telefono_alternativo", "Teléfono alternativo:"], ["email", "Email:"],
  ["fecha_actualizacion", "Fecha de actualización:"], ["origen_dato", "Origen del Dato:"],
] as const;

const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text);
const numbers = (v: unknown): v is number[] => Array.isArray(v) && v.every((n) => typeof n === "number" && Number.isFinite(n));
const nullable = (v: unknown) => v === null || text(v);
const flag = (v: unknown): v is boolean => typeof v === "boolean";
const LEVELS = ["success", "error", "warning", "info"];

export function fichaExtraValid(v: Record<string, unknown>): boolean {
  const { identidad: i, acciones: a, datos: d, historial: h } = v;
  const columnas = [...DATOS_COLUMNA_1, ...DATOS_COLUMNA_2];
  return record(i) && flag(i.mostrar) && flag(i.sin_dni) && flag(i.no_validado) && flag(i.requiere_revision) && text(i.motivo_texto) && text(i.descripcion_texto) &&
    record(a) && (a.historial_url === null || internal(a.historial_url)) && internal(a.editar_url) && internal(a.eliminar_url) && internal(a.familiar_nuevo_url) && (a.marcar_revisado_url === null || internal(a.marcar_revisado_url)) &&
    record(d) && columnas.every(([key]) => (key === "pais_emisor" ? nullable(d[key]) : text(d[key]))) &&
    nullable(v.mapa) && nullable(v.foto_url) &&
    Array.isArray(v.familia) && v.familia.every((f) => record(f) && text(f.vinculo_texto) && text(f.nombre) && text(f.apellido) && text(f.edad_texto) && internal(f.url)) &&
    record(h) && strings(h.labels) && numbers(h.auh) && numbers(h.prestacion) && numbers(h.centro_familia) && numbers(h.comedor) &&
    Array.isArray(v.interacciones) && v.interacciones.every((x) => record(x) && text(x.tipo) && text(x.fecha_texto) && text(x.responsable_texto) &&
      ["completo", "en_plan", "pendiente"].includes(x.estado as string)) &&
    text(v.observaciones) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

// --- Header and identity notice ---------------------------------------------

/** Full-page actions of the native form (`confirm(...)` and the redirect); replaceable in tests. */
export const ficha360Navigation = {
  confirm: (message: string) => window.confirm(message),
  assign: (to: string) => window.location.assign(to),
};

const MARCAR_CONFIRMACION = "¿Marcar este ciudadano como revisado?";
const UNCERTAIN = "No se pudo confirmar el resultado. Actualice la página antes de volver a intentar.";

/**
 * The native "Marcar revisado" form (`{% csrf_token %}`, `onsubmit="return confirm(...)"`). The submit goes once to
 * `web/ciudadanos/<pk>/marcar-revisado/`, which runs the native view; the confirmed redirect is a full-page navigation
 * (the message waits in the queue for the next GET). An unconfirmed outcome is reported and never resent.
 */
function MarcarRevisado({ endpoint }: { endpoint: string }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || error) return;
    if (!ficha360Navigation.confirm(MARCAR_CONFIRMACION)) return;
    busy.current = true; setPending(true);
    const outcome = await postForm(endpoint.replace(/^\/api\//, ""), new URLSearchParams());
    if (outcome.kind === "redirect") { ficha360Navigation.assign(outcome.url); return; }
    const detail = outcome.kind === "forbidden" && record(outcome.data) && text(outcome.data.detail) ? outcome.data.detail : UNCERTAIN;
    setError(detail); setPending(false);
  }
  return (
    <form method="post" action={endpoint.replace(/^\/api\/web/, "")} className="d-inline" onSubmit={submit}>
      <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
      <button type="submit" className="btn btn-outline-success" disabled={pending || !!error}><i className="fas fa-check" /> Marcar revisado</button>
      {error && <span role="alert" className="text-danger small">{error}</span>}
    </form>
  );
}

export function HeaderActions({ acciones }: { acciones: Acciones }) {
  return (
    <div className="btn-group">
      {acciones.historial_url && <a href={acciones.historial_url} className="btn btn-outline-light">Historial</a>}
      <a href={acciones.editar_url} className="btn btn-outline-light">Editar</a>
      {acciones.marcar_revisado_url && <MarcarRevisado endpoint={acciones.marcar_revisado_url} />}
      <a href={acciones.eliminar_url} className="btn btn-danger">Dar de baja</a>
    </div>
  );
}

const NOTICE: CSSProperties = { background: "rgba(255,193,7,0.12)", border: "1px solid rgba(255,193,7,0.35)", fontSize: "0.875rem", color: "white" };

export function IdentityNotice({ identidad: i }: { identidad: Identidad }) {
  if (!i.mostrar) return null;
  return (
    <div className="mx-3 mb-2 px-3 py-2 rounded d-flex align-items-start gap-3" style={NOTICE}>
      <div className="d-flex align-items-center gap-2 flex-wrap">
        {i.sin_dni && <span className="badge bg-warning text-dark">Sin DNI</span>}
        {i.no_validado && <span className="badge bg-danger">RENAPER no validado</span>}
        {i.requiere_revision && <span className="badge bg-secondary"><i className="fas fa-exclamation-triangle me-1" />Requiere revisión</span>}
        <span style={{ color: "rgba(255,255,255,0.8)" }}>
          {i.motivo_texto}{i.motivo_texto && i.descripcion_texto && " "}
          {i.descripcion_texto && <>— <em>{i.descripcion_texto}</em></>}
        </span>
      </div>
    </div>
  );
}

// --- Tabs ---------------------------------------------------------------------

export const TABS = [
  ["datos-personales", "Datos personales"], ["socioeconomico", "Socioeconómico"], ["pas", "PAS"], ["prestacion-alimentar", "Prestación Alimentar"],
  ["comedor", "Comedor"], ["cdf", "CDF"], ["celiaquia", "Celiaquía"], ["fch", "FCH"], ["situacion-calle", "Situación de Calle"], ["aduana", "Aduana"], ["vat", "VAT"],
] as const;
export type TabId = (typeof TABS)[number][0];

/**
 * Bootstrap `data-bs-toggle="tab"` without its script: click (and the arrow keys) show one pane. Like Bootstrap on load, the
 * links get `role="tab"`, `aria-selected` and a roving `tabindex` (only the active tab is in the Tab order).
 */
export function TabNav({ active, onSelect }: { active: TabId; onSelect: (id: TabId) => void }) {
  const links = useRef<(HTMLAnchorElement | null)[]>([]);
  const select = onSelect;
  function keys(event: React.KeyboardEvent, index: number) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    const next = (index + step + TABS.length) % TABS.length;
    event.preventDefault();
    select(TABS[next][0]);
    links.current[next]?.focus();
  }
  return (
    <ul className="nav nav-tabs nav-tabs-legajo" role="tablist">
      {TABS.map(([id, label], index) => (
        <li className="nav-item" key={id}>
          <a
            ref={(el) => { links.current[index] = el; }}
            className={`nav-link${id === active ? " active" : ""}`} href={`#${id}`}
            role="tab" aria-selected={id === active} tabIndex={id === active ? undefined : -1}
            onClick={(event) => { event.preventDefault(); select(id); }} onKeyDown={(event) => keys(event, index)}
          >{label}</a>
        </li>
      ))}
    </ul>
  );
}

export function TabPane({ id, active, children }: { id: TabId; active: TabId; children: ReactNode }) {
  return <div className={`tab-pane fade${id === active ? " show active" : ""}`} id={id} role="tabpanel">{children}</div>;
}

// --- Datos personales, familia, history chart, programs ----------------------------

/** `tail` closes the second info column: the PWA rows, a vertical card. */
export function DatosPersonales({ extra, tail }: { extra: FichaExtra; tail: ReactNode }) {
  const { datos, acciones } = extra;
  const fila = ([key, label]: readonly [keyof Datos, string]) => (
    <div className="info-row" key={key}><strong>{label}</strong><span className="value">{datos[key]}</span></div>
  );
  return (
    <div className="datos-card" style={{ position: "relative" }}>
      <a href={acciones.editar_url} className="btn-edit-card"><i className="fas fa-pen" /></a>
      <h5>Datos Personales</h5>
      <div className="datos-card-content">
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
          {extra.mapa ? (
            <iframe title="Ubicación del ciudadano" width="100%" height="450" src={`https://www.google.com/maps?q=${extra.mapa}&output=embed`} loading="lazy" />
          ) : extra.foto_url ? (
            <img src={extra.foto_url} alt="Foto" className="foto-placeholder" style={{ objectFit: "cover" }} />
          ) : (
            <div className="foto-placeholder"><i className="fas fa-map-marker-alt" /></div>
          )}
        </div>
        <div className="info-column">
          {DATOS_COLUMNA_1.filter(([key]) => key !== "pais_emisor" || datos.pais_emisor).map((c) => fila(c))}
        </div>
        <div className="info-column">{DATOS_COLUMNA_2.map((c) => fila(c))}{tail}</div>
      </div>
    </div>
  );
}

const FAMILIAR_ROW: CSSProperties = { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "1rem 0", borderBottom: "1px solid rgba(255,255,255,0.1)" };

export function GrupoFamiliar({ familia, nuevaUrl }: { familia: Familiar[]; nuevaUrl: string }) {
  return (
    <div className="tabla-legajo">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="mb-0">Grupo Familiar</h5>
        <a href={nuevaUrl} className="btn btn-success btn-sm"><i className="fas fa-plus" /> Agregar</a>
      </div>
      {familia.length > 0 ? (
        <>
          <div style={{ borderBottom: "1px solid rgba(255,255,255,0.2)", paddingBottom: "1rem", marginBottom: "1rem" }} />
          {familia.map((f) => (
            <div style={FAMILIAR_ROW} key={f.url}>
              <div>
                <span style={{ color: "rgba(255,255,255,0.7)" }}>{f.vinculo_texto}:</span>
                {" "}<span style={{ color: "white", fontWeight: 600, marginLeft: "0.5rem" }}>{f.nombre} {f.apellido}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "2rem" }}>
                <span style={{ color: "rgba(255,255,255,0.7)" }}>Edad: <span style={{ color: "white", fontWeight: 600 }}>{f.edad_texto}</span></span>
                <a href={f.url} style={{ color: "#E7BA61", textDecoration: "underline", display: "flex", alignItems: "center", gap: "0.5rem" }}>Ver legajo <i className="fas fa-eye" /></a>
              </div>
            </div>
          ))}
        </>
      ) : <p style={{ color: "rgba(255,255,255,0.5)" }}>Aún no hay familiares cargados.</p>}
    </div>
  );
}

const CHART_SRC = "https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js";
const MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
type ChartInstance = { destroy: () => void };
type ChartConstructor = new (context: CanvasRenderingContext2D, config: unknown) => ChartInstance;
declare global { interface Window { Chart?: ChartConstructor } }

const AXIS = { stacked: true, grid: { color: "rgba(255,255,255,0.1)" }, ticks: { color: "rgba(255,255,255,0.7)" } };
export const chartConfig = (h: Historial) => ({
  type: "bar",
  data: {
    labels: h.labels,
    datasets: [
      { label: "AUH", data: h.auh, backgroundColor: "#FF8C42", borderRadius: 0 },
      { label: "Prestación Alimentar", data: h.prestacion, backgroundColor: "#FFB84D", borderRadius: 0 },
      { label: "Centro de Familia", data: h.centro_familia, backgroundColor: "#D63384", borderRadius: 0 },
      { label: "Comedor", data: h.comedor, backgroundColor: "#F8A5C2", borderRadius: 0 },
    ],
  },
  options: { responsive: true, maintainAspectRatio: false, indexAxis: "x", scales: { x: AXIS, y: { ...AXIS, max: 500 } }, plugins: { legend: { display: false } } },
});

/** Native: Chart.js 3.9.1 from the same CDN, drawn on load and again on every month change. */
function withChartJs(run: (chart: ChartConstructor) => void): () => void {
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

export function HistorialCard({ historial }: { historial: Historial }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [{ mes, anio }, setPeriodo] = useState(() => ({ mes: new Date().getMonth() + 1, anio: new Date().getFullYear() }));
  function cambiarMes(direccion: number) {
    setPeriodo(({ mes: m, anio: a }) => {
      const next = m + direccion;
      if (next > 12) return { mes: 1, anio: a + 1 };
      if (next < 1) return { mes: 12, anio: a - 1 };
      return { mes: next, anio: a };
    });
  }
  useEffect(() => {
    let instance: ChartInstance | null = null;
    const stop = withChartJs((Chart) => {
      const context = canvas.current?.getContext("2d");
      if (context) instance = new Chart(context, chartConfig(historial));
    });
    return () => { stop(); instance?.destroy(); };
  }, [historial, mes, anio]);
  return (
    <div className="historial-card">
      <div className="historial-header">
        <h6>Historial de Transferencia directa e indirecta</h6>
        <div className="periodo-selector">
          <button className="btn" onClick={() => cambiarMes(-1)}><i className="fas fa-chevron-left" /></button>
          <span className="mes-actual" id="mes-actual">{mes} {MESES[mes]} {anio}</span>
          <button className="btn" onClick={() => cambiarMes(1)}><i className="fas fa-chevron-right" /></button>
        </div>
      </div>
      <div className="chart-container"><canvas id="historialChart" ref={canvas} /></div>
    </div>
  );
}

function Programa({ clase, icono, nombre, children }: { clase: string; icono: string; nombre: string; children: ReactNode }) {
  return (
    <div className={`programa-card ${clase}`}>
      <div className="icono"><i className={icono} /></div>
      <div className="info"><div className="nombre">{nombre}</div><div className="monto">{children}</div></div>
    </div>
  );
}

/** The program cards of the native page: the amounts are literals there, only Centro de Familia comes from its aporte. */
export function ProgramasSection({ centroFamiliaMonto }: { centroFamiliaMonto: ReactNode }) {
  return (
    <div className="programas-section">
      <h6>Programas transferencia directa</h6>
      <Programa clase="auh" icono="fas fa-users" nombre="AUH">$108.062,00</Programa>
      <Programa clase="prestacion" icono="fas fa-utensils" nombre="Prestación Alimentar">$108.062,00</Programa>
      <Programa clase="centro-familia" icono="fas fa-home" nombre="Centro de Familia">{centroFamiliaMonto}</Programa>
      <h6 style={{ marginTop: "1.5rem", marginBottom: "1.25rem", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "1.5rem" }}>Programas transferencia indirecta</h6>
      <Programa clase="comedor" icono="fas fa-utensils" nombre="Asiste a comedor">$108.062,00</Programa>
      <Programa clase="aduana" icono="fas fa-box" nombre="Aduana">2 colchones.</Programa>
      <div style={{ background: "rgba(255,255,255,0.05)", borderRadius: 8, padding: "1rem", textAlign: "center", marginTop: "1.5rem" }}>
        <small style={{ display: "block", marginBottom: "0.5rem", opacity: 0.85, fontSize: "0.8rem", fontWeight: 500 }}>Monto total mes Dic 2025</small>
        <div style={{ fontSize: "1.8rem", fontWeight: "bold", letterSpacing: "0.5px" }}>$318.124,00</div>
      </div>
    </div>
  );
}

// --- Interactions and observations (every tab repeats them; the buttons are inert in the native page) ---

const SEARCH: CSSProperties = { width: 200, background: "transparent", borderColor: "rgba(255,255,255,0.3)", color: "white" };
const EMPTY: CSSProperties = { color: "rgba(255,255,255,0.5)" };

function TablaHeader({ titulo }: { titulo: string }) {
  return (
    <div className="d-flex justify-content-between align-items-center mb-3">
      <h5 className="mb-0">{titulo}</h5>
      <div className="d-flex gap-2">
        <input type="text" className="form-control form-control-sm" placeholder="Buscar" style={SEARCH} />
        <button className="btn btn-success btn-sm"><i className="fas fa-plus" /></button>
        <button className="btn btn-outline-light btn-sm"><i className="fas fa-filter" /></button>
      </div>
    </div>
  );
}

function EstadoBadge({ estado }: { estado: Interaccion["estado"] }) {
  if (estado === "completo") return <span className="badge" style={{ background: "var(--green)" }}>Completo</span>;
  if (estado === "en_plan") return <span className="badge" style={{ background: "#FFB84D", color: "var(--navy-dark)" }}>En Plan</span>;
  return <span className="badge" style={{ background: "rgba(255,255,255,0.2)" }}>Pendiente</span>;
}

/** The native template spells the first column "Interacción" only in "Datos personales"; every other pane has "Interaccion". */
export function InteraccionesTabla({ interacciones, conTilde = false }: { interacciones: Interaccion[]; conTilde?: boolean }) {
  return (
    <div className="tabla-legajo">
      <TablaHeader titulo="Interacciones" />
      {interacciones.length > 0 ? (
        <table className="table table-sm">
          <thead><tr><th>{conTilde ? "Interacción" : "Interaccion"}</th><th>Fecha</th><th>Responsable</th><th>Estado</th><th /></tr></thead>
          <tbody>
            {interacciones.map((i, index) => (
              <tr key={index}>
                <td>{i.tipo}</td>
                <td><i className="fas fa-calendar" /> {i.fecha_texto}</td>
                <td>{i.responsable_texto}</td>
                <td><EstadoBadge estado={i.estado} /></td>
                <td className="text-end"><button className="btn btn-danger btn-sm"><i className="fas fa-trash" /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <p style={EMPTY}>No hay interacciones registradas.</p>}
    </div>
  );
}

export function ObservacionesTabla({ observaciones }: { observaciones: string }) {
  return (
    <div className="tabla-legajo">
      <TablaHeader titulo="Observaciones" />
      {observaciones ? <table className="table table-sm"><tbody><tr><td>{observaciones}</td></tr></tbody></table> : <p style={EMPTY}>No hay observaciones registradas.</p>}
    </div>
  );
}

/** A tab that is still "Contenido en desarrollo..." in the native page. */
export function PaneEnDesarrollo({ titulo, extra }: { titulo: string; extra: FichaExtra }) {
  return (
    <div className="row"><div className="col-12">
      <div className="tabla-legajo"><h5 className="mb-3">{titulo}</h5><p style={EMPTY}>Contenido en desarrollo...</p></div>
      <InteraccionesTabla interacciones={extra.interacciones} />
      <ObservacionesTabla observaciones={extra.observaciones} />
    </div></div>
  );
}
