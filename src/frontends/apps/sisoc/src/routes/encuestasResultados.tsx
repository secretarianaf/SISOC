/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { Breadcrumb, internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * Survey results (`encuestas/encuesta_resultados.html`, `/encuestas/<id>/resultados/`). GET
 * `/api/web/encuestas/<id>/resultados/?ronda=` runs `EncuestaResultadosView` (403 without
 * `encuestas.ver_resultados`, 404 for an unknown survey). Numbers and dates arrive formatted by Django
 * (`66,7`, `d/m/Y`), so a width such as `66,7%` is as invalid here as in the native `style` attribute. The
 * round selector submits a GET like the native `onchange`; the CSV and Excel exports are the native
 * downloads. Read only.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Opcion = { texto: string; cantidad: number; porcentaje: string };
type Resultado = {
  texto: string; tipo: string; total_respuestas: number; opciones: Opcion[]; opcion_lider_texto: string | null;
  numerico: { promedio: string; minimo: string; maximo: string; posicion: string } | null; respuestas_texto: string[];
};
export type ResultadosData = {
  id: number; titulo: string; rondas: { id: number; selected: boolean; label: string }[];
  ronda_actual: { id: number; respuestas: number; abierta: boolean; estado_label: string; cierre: string; export_url: string } | null;
  puntajes: { usuario: string; obtenido: number; total_posible: number; porcentaje: string }[];
  resultados: Resultado[]; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const list = (v: unknown, ok: (x: unknown) => boolean) => Array.isArray(v) && v.every(ok);
const strings = (v: unknown, keys: string[]) => record(v) && keys.every((k) => text(v[k]));

export function resultadosValid(v: unknown): v is ResultadosData {
  return record(v) && int(v.id) && text(v.titulo) &&
    list(v.rondas, (r) => record(r) && int(r.id) && typeof r.selected === "boolean" && text(r.label)) &&
    (v.ronda_actual === null || (record(v.ronda_actual) && int(v.ronda_actual.id) && int(v.ronda_actual.respuestas) && typeof v.ronda_actual.abierta === "boolean" &&
      text(v.ronda_actual.estado_label) && text(v.ronda_actual.cierre) && internal(v.ronda_actual.export_url))) &&
    list(v.puntajes, (p) => strings(p, ["usuario", "porcentaje"]) && int((p as Record<string, unknown>).obtenido) && int((p as Record<string, unknown>).total_posible)) &&
    list(v.resultados, (r) => strings(r, ["texto", "tipo"]) && int((r as Record<string, unknown>).total_respuestas) &&
      list((r as Record<string, unknown>).opciones, (o) => strings(o, ["texto", "porcentaje"]) && int((o as Record<string, unknown>).cantidad)) &&
      ((r as Record<string, unknown>).opcion_lider_texto === null || text((r as Record<string, unknown>).opcion_lider_texto)) &&
      ((r as Record<string, unknown>).numerico === null || strings((r as Record<string, unknown>).numerico, ["promedio", "minimo", "maximo", "posicion"])) &&
      list((r as Record<string, unknown>).respuestas_texto, text)) &&
    list(v.messages, (m) => strings(m, ["message"]) && LEVELS.includes((m as Message).level));
}

const TIPOS: Record<string, [string, string]> = {
  opcion_unica: ["fas fa-dot-circle", "Opción única"], opcion_multiple: ["fas fa-check-square", "Opción múltiple"],
  si_no: ["fas fa-check-double", "Sí / No"], escala: ["fas fa-sliders-h", "Escala"], numerico: ["fas fa-hashtag", "Numérico"],
  fecha: ["fas fa-calendar-alt", "Fecha"],
};

function Pregunta({ r }: { r: Resultado }) {
  const [icon, label] = TIPOS[r.tipo] ?? ["fas fa-align-left", "Texto libre"];
  return (
    <div className="editor-panel">
      <div className="panel-body">
        <div className="resultado-head">
          <div>
            <p className="resultado-titulo">{r.texto}</p>
            <span className="resultado-meta">{r.total_respuestas} respuesta{r.total_respuestas === 1 ? "" : "s"}</span>
          </div>
          <span className="tipo-chip"><i className={icon}></i> {label}</span>
        </div>
        {r.opciones.length > 0 ? (
          <div className="result-bars">
            {r.opciones.map((o, i) => (
              <div key={i} className={`result-bar-row ${o.texto === r.opcion_lider_texto ? "is-leading" : ""}`}>
                <div className="result-bar-labels">
                  <span className="result-bar-opcion">{o.texto}</span>
                  <span className="result-bar-valor"><b>{o.cantidad}</b> ({o.porcentaje}%)</span>
                </div>
                <div className="result-bar-track"><div className="result-bar-fill" style={{ width: `${o.porcentaje}%` }}></div></div>
              </div>
            ))}
          </div>
        ) : r.numerico ? (
          <>
            <div className="numeric-range">
              <div className="numeric-range-track">
                <div className="numeric-range-marker" style={{ left: `${r.numerico.posicion}%` }}>
                  <span className="numeric-range-marker-label">{r.numerico.promedio}</span>
                </div>
              </div>
              <div className="numeric-range-endpoints"><span>{r.numerico.minimo}</span><span>{r.numerico.maximo}</span></div>
            </div>
            <div className="numeric-range-stats">
              <div className="numeric-stat"><div className="numeric-stat-value">{r.numerico.minimo}</div><div className="numeric-stat-label">Mínimo</div></div>
              <div className="numeric-stat"><div className="numeric-stat-value">{r.numerico.promedio}</div><div className="numeric-stat-label">Promedio</div></div>
              <div className="numeric-stat"><div className="numeric-stat-value">{r.numerico.maximo}</div><div className="numeric-stat-label">Máximo</div></div>
            </div>
          </>
        ) : r.respuestas_texto.length > 0 ? (
          <div className="texto-respuestas-list">
            {r.respuestas_texto.map((t, i) => (
              <div key={i} className="texto-respuesta-item"><i className="fas fa-quote-left"></i><span>{t}</span></div>
            ))}
          </div>
        ) : <p className="resultado-vacio mb-0">Sin respuestas todavía.</p>}
      </div>
    </div>
  );
}

export function ResultadosContent({ data }: { data: ResultadosData }) {
  const actual = data.ronda_actual;
  const selected = data.rondas.find((r) => r.selected) ?? data.rondas[0];
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/encuestaForm.css" />
      <link rel="stylesheet" href="/static/custom/css/encuestaResultados.css" />
      <div className="encuesta-editor">
        <div className="d-flex justify-content-between align-items-start mb-3">
          <div>
            <h2 className="mb-1">Resultados</h2>
            <p className="switch-help mb-0">{data.titulo}</p>
          </div>
        </div>
        {data.rondas.length === 0 ? (
          <div className="editor-panel"><div className="panel-body"><p className="resultado-vacio mb-0">Esta encuesta todavía no tiene rondas.</p></div></div>
        ) : (
          <>
            <div className="resultados-toolbar">
              <form method="get" className="ronda-select-wrap" onSubmit={(e) => e.preventDefault()}>
                <label htmlFor="ronda">Ronda</label>
                <select name="ronda" id="ronda" className="form-select" value={selected.id}
                  onChange={(e) => window.location.assign(`${window.location.pathname}?ronda=${encodeURIComponent(e.target.value)}`)}>
                  {data.rondas.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
                </select>
              </form>
              {actual && (
                <div className="export-actions">
                  <a href={`${actual.export_url}?formato=csv`} className="btn-cancel"><i className="fas fa-file-csv me-1"></i> CSV</a>{" "}
                  <a href={`${actual.export_url}?formato=xlsx`} className="btn-cancel"><i className="fas fa-file-excel me-1"></i> Excel</a>
                </div>
              )}
            </div>
            {actual && (
              <>
                <div className="stat-cards">
                  <div className="stat-card stat-accent-respuestas">
                    <div className="stat-card-icon"><i className="fas fa-poll"></i></div>
                    <div><div className="stat-card-value">{actual.respuestas}</div><div className="stat-card-label">Respuestas recibidas</div></div>
                  </div>
                  <div className={`stat-card stat-accent-estado ${actual.abierta ? "is-abierta" : ""}`}>
                    <div className="stat-card-icon"><i className={`fas ${actual.abierta ? "fa-lock-open" : "fa-lock"}`}></i></div>
                    <div><div className="stat-card-value">{actual.estado_label}</div><div className="stat-card-label">Estado de la ronda</div></div>
                  </div>
                  <div className="stat-card stat-accent-cierre">
                    <div className="stat-card-icon"><i className="fas fa-calendar-check"></i></div>
                    <div><div className="stat-card-value">{actual.cierre}</div><div className="stat-card-label">Cierre programado</div></div>
                  </div>
                </div>
                {data.puntajes.length > 0 && (
                  <div className="editor-panel">
                    <div className="panel-label">
                      <span className="panel-label-title"><i className="fas fa-medal"></i> Puntaje por respuesta</span>
                      <span className="count-badge">Total posible: <b>{data.puntajes[0].total_posible}</b> pts</span>
                    </div>
                    <div className="panel-body">
                      <div className="result-bars">
                        {data.puntajes.map((p, i) => (
                          <div key={i} className={`result-bar-row ${i === 0 ? "is-leading" : ""}`}>
                            <div className="result-bar-labels">
                              <span className="result-bar-opcion"><span className="puntaje-rank">#{i + 1}</span> {p.usuario || "Respuesta anónima"}</span>
                              <span className="result-bar-valor"><b>{p.obtenido}</b> / {p.total_posible} ({p.porcentaje}%)</span>
                            </div>
                            <div className="result-bar-track"><div className="result-bar-fill" style={{ width: `${p.porcentaje}%` }}></div></div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
                {data.resultados.map((r, i) => <Pregunta key={i} r={r} />)}
              </>
            )}
          </>
        )}
      </div>
      <NativeToasts messages={data.messages} />
    </>
  );
}

function ResultadosPage({ id }: { id: string }) {
  const [state] = useMainResource(`web/encuestas/${id}/resultados/${window.location.search}`, resultadosValid);
  return renderMain(state, "Cargando resultados…", (data) => ({
    title: `Resultados: ${data.titulo}`, activePath: "/encuestas/",
    breadcrumb: <Breadcrumb items={[]} />,
    content: <ResultadosContent data={data} />,
  }));
}

export const encuestasResultadosRoute: RouteDefinition<{ id: string }> = {
  name: "encuestas-resultados",
  match(pathname) {
    const found = /^\/encuestas\/([0-9]+)\/resultados\/$/.exec(pathname);
    return found ? { id: found[1] } : null;
  },
  render: ({ id }) => <ResultadosPage id={id} />,
};
