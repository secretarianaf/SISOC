/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { useRef, useState, type FormEvent } from "react";
import { breadcrumb, renderWithNativeToasts } from "./cdfActividades";
import { DetailHead } from "./cdfDataTable";
import { client, csrfToken, integer, internal, messagesValid, navigation, nullableText, record, text, useCdfPage, type CdfMessage } from "./cdfFrame";
import type { RouteDefinition } from "./types";

/**
 * CDF-D: `centros/actividadcentro_asistencia.html` (sheet of the enrolled for a date) and its inline
 * script (live metrics, "Presente (todos)" / "Ausente (todos)"). The API runs the native view (404,
 * then the attendance permission 403); saving converts the unmarked to absent exactly like the native
 * POST and the redirect (`?fecha=`) is followed. A POST is never retried.
 */
const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";

type Fila = { id: number; apellido: string; nombre: string; documento: string; presente: boolean | null };
export type AsistenciaData = {
  actividad: { id: number; nombre: string; categoria: string; estado_display: string; horariosdesde: string; horarioshasta: string };
  centro: { id: number; nombre: string }; fecha: string; fecha_display: string; fecha_error: string | null; ya_tomada: boolean;
  totales: { presentes: number; ausentes: number; sin_marcar: number }; filas: Fila[];
  urls: { centro_list: string; centro_detail: string; detalle: string }; messages: CdfMessage[];
};

const filaValid = (f: unknown): f is Fila => record(f) && integer(f.id) && ["apellido", "nombre", "documento"].every((k) => text(f[k])) &&
  (f.presente === null || typeof f.presente === "boolean");

export function asistenciaValid(v: unknown): v is AsistenciaData {
  if (!record(v) || !record(v.actividad) || !record(v.centro) || !record(v.totales) || !record(v.urls)) return false;
  const a = v.actividad, t = v.totales, u = v.urls;
  return integer(a.id) && ["nombre", "categoria", "estado_display", "horariosdesde", "horarioshasta"].every((k) => text(a[k])) &&
    integer(v.centro.id) && text(v.centro.nombre) && text(v.fecha) && text(v.fecha_display) && nullableText(v.fecha_error) && typeof v.ya_tomada === "boolean" &&
    ["presentes", "ausentes", "sin_marcar"].every((k) => integer(t[k])) && Array.isArray(v.filas) && v.filas.every(filaValid) &&
    ["centro_list", "centro_detail", "detalle"].every((k) => internal(u[k])) && messagesValid(v.messages);
}

type Marca = "1" | "0" | "";

export function AsistenciaContent({ data }: { data: AsistenciaData }) {
  const { actividad: a, centro, fecha } = data;
  const [marcas, setMarcas] = useState<Record<number, Marca>>(() => Object.fromEntries(data.filas.map((f) => [f.id, f.presente === true ? "1" : f.presente === false ? "0" : ""])));
  // The two header checkboxes are not tied to the rows after they are used (native script).
  const [todos, setTodos] = useState({ presentes: false, ausentes: false });
  const [uncertain, setUncertain] = useState(false);
  const sending = useRef(false);
  const valores = Object.values(marcas);
  const presentes = valores.filter((m) => m === "1").length, ausentes = valores.filter((m) => m === "0").length;

  function marcarTodos(tipo: "presentes" | "ausentes", checked: boolean) {
    if (!checked) { setTodos((t) => ({ ...t, [tipo]: false })); return; }
    setTodos({ presentes: tipo === "presentes", ausentes: tipo === "ausentes" });
    setMarcas(Object.fromEntries(data.filas.map((f) => [f.id, tipo === "presentes" ? "1" : "0"])));
  }

  async function guardar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current) return;
    sending.current = true;
    try {
      const { data: body } = await client.post(`web/cdf/actividades/${a.id}/asistencia/`, new FormData(event.currentTarget));
      if (record(body) && internal(body.url)) { navigation.assign(body.url); return; }
      setUncertain(true);
    } catch {
      setUncertain(true);
    }
    sending.current = false;
  }

  const planilla = `Planilla del ${data.fecha_display}`;
  return (
    <>
      <DetailHead />
      <div className="cdf-page">
        <div className="cdf-hero">
          <div className="cdf-hero-block">
            <h1>Asistencia — {a.nombre}</h1>
            <p className="cdf-hero-sub">
              <span><i className="fas fa-house-chimney" />{centro.nombre}</span>{" "}
              <span><i className="fas fa-layer-group" />{a.categoria}</span>{" "}
              <span><i className="fas fa-clock" />{a.horariosdesde} - {a.horarioshasta}</span>
            </p>
          </div>
          <span className="cdf-pill cdf-pill--teal">{a.estado_display}</span>
        </div>
        <div className="d-flex justify-content-between align-items-center flex-wrap mb-4" style={{ gap: "0.75rem" }}>
          <form method="get" className="cdf-actions">
            <label htmlFor="fechaAsistencia" className="mb-0 fw-bold">Fecha de la clase:</label>{" "}
            <input type="date" id="fechaAsistencia" name="fecha" className="cdf-input" defaultValue={fecha} />{" "}
            <button type="submit" className="cdf-btn cdf-btn--primary">Cambiar fecha</button>
          </form>
        </div>
        {uncertain && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
        {data.fecha_error && <div className="cdf-alert cdf-alert--warning">{data.fecha_error} Se muestra la planilla de hoy.</div>}
        {data.ya_tomada && (
          <div className="cdf-alert cdf-alert--info">
            Ya existe asistencia registrada para el {data.fecha_display}. Al guardar se actualizarán los registros.
          </div>
        )}
        <div className="cdf-metric-grid">
          <article className="cdf-metric cdf-metric--green"><strong className="cdf-metric-value" id="asisMetricPresentes">{presentes}</strong><span className="cdf-metric-label">Presentes</span></article>
          <article className="cdf-metric cdf-metric--red"><strong className="cdf-metric-value" id="asisMetricAusentes">{ausentes}</strong><span className="cdf-metric-label">Ausentes</span></article>
          <article className="cdf-metric cdf-metric--gold"><strong className="cdf-metric-value" id="asisMetricSinMarcar">{data.filas.length - presentes - ausentes}</strong><span className="cdf-metric-label">Sin marcar</span></article>
        </div>
        {data.filas.length ? (
          <form method="post" id="asisForm" onSubmit={(e) => void guardar(e)}>
            <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
            <input type="hidden" name="fecha" value={fecha} />
            <div className="cdf-card">
              <div className="cdf-card-head"><i className="fas fa-clipboard-check" /><span>{planilla}</span></div>
              <div className="cdf-card-body cdf-card-body--flush">
                <div className="cdf-tbl-scroll">
                  <table className="cdf-table">
                    <thead>
                      <tr>
                        <th>Participante</th>
                        <th>DNI</th>
                        <th className="text-center">
                          <label className="cdf-mark">
                            <input type="checkbox" className="cdf-check cdf-check--present" id="asisMarcarPresentes" checked={todos.presentes}
                              onChange={(e) => marcarTodos("presentes", e.target.checked)} />{" "}Presente (todos)
                          </label>
                        </th>
                        <th className="text-center">
                          <label className="cdf-mark">
                            <input type="checkbox" className="cdf-check cdf-check--absent" id="asisMarcarAusentes" checked={todos.ausentes}
                              onChange={(e) => marcarTodos("ausentes", e.target.checked)} />{" "}Ausente (todos)
                          </label>
                        </th>
                      </tr>
                    </thead>
                    <tbody id="asisTablaBody">
                      {data.filas.map((f) => (
                        <tr key={f.id} className="asis-row">
                          <td>{f.apellido}, {f.nombre}</td>
                          <td>{f.documento}</td>
                          <td className="text-center">
                            <label className="cdf-mark">
                              <input type="radio" className="cdf-check cdf-check--present asis-present" name={`presente_${f.id}`} value="1"
                                checked={marcas[f.id] === "1"} onChange={() => setMarcas((m) => ({ ...m, [f.id]: "1" }))} />{" "}Presente
                            </label>
                          </td>
                          <td className="text-center">
                            <label className="cdf-mark">
                              <input type="radio" className="cdf-check cdf-check--absent asis-absent" name={`presente_${f.id}`} value="0"
                                checked={marcas[f.id] === "0"} onChange={() => setMarcas((m) => ({ ...m, [f.id]: "0" }))} />{" "}Ausente
                            </label>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
            <div className="d-flex justify-content-end mb-4">
              <button type="submit" className="cdf-btn cdf-btn--success"><i className="fas fa-check" />Guardar Asistencia</button>
            </div>
          </form>
        ) : (
          <div className="cdf-card">
            <div className="cdf-card-head"><i className="fas fa-clipboard-check" /><span>{planilla}</span></div>
            <div className="cdf-empty">
              <i className="fas fa-user-plus" />
              <p className="cdf-empty-t">No hay participantes inscritos</p>
              <p className="cdf-empty-s">Agregá participantes desde el detalle de la actividad para poder tomar asistencia.</p>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function Asistencia({ id }: { id: string }) {
  const state = useCdfPage(`web/cdf/actividades/${id}/asistencia/${window.location.search}`, asistenciaValid);
  return renderWithNativeToasts(state, (data) => ({
    title: "Toma de Asistencia",
    breadcrumb: breadcrumb([["Centro de Familia", data.urls.centro_list], ["Actividades", data.urls.centro_detail], ["Detalle", data.urls.detalle], ["Asistencia", null]]),
    content: <AsistenciaContent key={data.fecha} data={data} />,
  }));
}

// Native URL of the CDF attendance sheet (CDF-D).
export const cdfAsistenciaRoute: RouteDefinition<{ id: string }> = {
  name: "cdf-asistencia",
  match: (pathname) => {
    const m = /^\/centrodefamilia\/centros\/actividades\/([1-9]\d*)\/asistencia\/$/.exec(pathname);
    return m ? { id: m[1] } : null;
  },
  render: ({ id }) => <Asistencia id={id} />,
};
