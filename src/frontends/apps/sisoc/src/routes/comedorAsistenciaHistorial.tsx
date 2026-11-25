/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen, validator and route live here. */
import { useEffect } from "react";
import { InsumosToastList } from "../InsumosToast";
import InsumosAccessError from "../InsumosAccessError";
import { Breadcrumb, internal, record, text, useMainResource } from "./MainFrame";
import SisocShell from "./SisocShell";
import type { RouteDefinition } from "./types";
import { HITOS_STYLESHEET } from "./userImport";

/**
 * CO01 attendance history of a comedor nómina (`nomina_asistencia_historial`):
 * `comedor/nomina_asistencia_historial.html` with the list of months (count, generated PDF link, «Ver
 * detalle») or, with `?periodo=`, the attendees of that month. Data comes from
 * `/api/web/comedores/comedores/<id>/admision/<admision>/nomina/asistencia/`, which runs the native view.
 * It only reads: the attendance is taken by the PWA, and the PDF stays a native file link.
 */
type Periodo = { label: string; iso: string; total: string; documento_url: string | null };
type Asistente = { id: number; apellido: string; nombre: string; documento: string; genero: string; tomada_el: string; tomada_por: string; ciudadano_url: string | null };
export type ComedorAsistenciaData = {
  comedor: { id: number; nombre: string };
  periodo: { label: string; total: string } | null;
  asistentes: Asistente[];
  periodos: Periodo[];
  urls: { comedores: string; comedor: string; nomina: string; historial: string };
  messages: { message: string; level: "success" | "error" | "warning" | "info" }[];
};

const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const LEVELS = ["success", "error", "warning", "info"];
/** The PDF is a FileField URL: a local path or an absolute http(s) one. */
const fileUrl = (v: unknown): v is string => internal(v) || (text(v) && /^https?:\/\//.test(v));

export function asistenciaValid(v: unknown): v is ComedorAsistenciaData {
  if (!record(v) || !record(v.comedor) || !record(v.urls)) return false;
  const c = v.comedor, u = v.urls;
  return int(c.id) && text(c.nombre) &&
    (v.periodo === null || (record(v.periodo) && text(v.periodo.label) && text(v.periodo.total))) &&
    Array.isArray(v.asistentes) && v.asistentes.every((a) => record(a) && int(a.id) &&
      ["apellido", "nombre", "documento", "genero", "tomada_el", "tomada_por"].every((k) => text(a[k])) &&
      (a.ciudadano_url === null || internal(a.ciudadano_url))) &&
    Array.isArray(v.periodos) && v.periodos.every((p) => record(p) && ["label", "iso", "total"].every((k) => text(p[k])) &&
      (p.documento_url === null || fileUrl(p.documento_url))) &&
    ["comedores", "comedor", "nomina", "historial"].every((k) => internal(u[k])) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

function Periodos({ data }: { data: ComedorAsistenciaData }) {
  return (
    <>
      <h2 className="nomina-attendance-title">Periodos de asistencia</h2>
      {data.periodos.length ? (
        <div className="nomina-period-list">
          {data.periodos.map((item) => (
            <div key={item.iso} className="nomina-period-card">
              <div>
                <p className="nomina-period-title">Periodo {item.label}</p>
                <p className="nomina-period-meta">Asistencia mensual</p>
              </div>
              <div className="nomina-period-count">
                <strong>{item.total}</strong>{" "}
                <span>asistentes</span>
              </div>
              <div className="d-flex align-items-center gap-2">
                {item.documento_url && (
                  <a href={item.documento_url} className="btn btn-outline-light btn-sm" target="_blank" rel="noopener" download>
                    <i className="fas fa-file-pdf" /> Descargar PDF
                  </a>
                )}
                <a href={`?periodo=${item.iso}`} className="btn btn-outline-light btn-sm">
                  Ver detalle <i className="fas fa-chevron-right" />
                </a>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="nomina-empty-message mb-0">No hay periodos con asistencia registrada.</p>
      )}
    </>
  );
}

function Detalle({ data, periodo }: { data: ComedorAsistenciaData; periodo: NonNullable<ComedorAsistenciaData["periodo"]> }) {
  return (
    <>
      <div className="nomina-attendance-detail-header">
        <div>
          <h2 className="nomina-attendance-title">Periodo {periodo.label}</h2>
          <p className="text-white-50 mb-0">{periodo.total} asistentes registrados</p>
        </div>
        <a href={data.urls.historial} className="btn btn-outline-light">
          <i className="fas fa-list" /> Ver periodos
        </a>
      </div>

      <div className="nomina-table-container">
        <table className="nomina-table">
          <thead>
            <tr><th>Apellido y nombre</th><th>DNI</th><th>Género</th><th>Tomada el</th><th>Tomada por</th></tr>
          </thead>
          <tbody>
            {data.asistentes.length ? data.asistentes.map((a) => (
              <tr key={a.id} className="nomina-table-row">
                <td>
                  {a.ciudadano_url
                    ? <a href={a.ciudadano_url} className="nomina-citizen-link">{a.apellido}, {a.nombre}</a>
                    : "-"}
                </td>
                <td>{a.documento}</td>
                <td>{a.genero}</td>
                <td>{a.tomada_el}</td>
                <td>{a.tomada_por}</td>
              </tr>
            )) : (
              <tr><td colSpan={5} className="nomina-empty-message">No hay asistentes registrados para este periodo.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function ComedorAsistenciaContent({ data }: { data: ComedorAsistenciaData }) {
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/nominaDetail.css" />
      <InsumosToastList messages={data.messages} />
      <div className="nomina-section bg-base-darkblue">
        {data.periodo ? <Detalle data={data} periodo={data.periodo} /> : <Periodos data={data} />}
      </div>
    </>
  );
}

/** `body.app-loaded`: AdminLTE marks the page up once its scripts run. */
function AppLoaded() {
  useEffect(() => {
    document.body.classList.add("app-loaded");
    return () => document.body.classList.remove("app-loaded");
  }, []);
  return null;
}

function AsistenciaPage({ endpoint }: { endpoint: string }) {
  const [state] = useMainResource(`${endpoint}${window.location.search}`, asistenciaValid);
  if (state.status === "loading") return <main role="status">Cargando historial de asistencia…</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar la página.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  const { data } = state;
  return <>
    <SisocShell
      context={state.session}
      pageTitle={`Historial de asistencia - ${data.comedor.nombre}`}
      heading={<>Historial de asistencia de {data.comedor.nombre}</>}
      breadcrumb={<Breadcrumb items={[
        { text: "Espacios Comunitarios", url: data.urls.comedores },
        { text: data.comedor.nombre, url: data.urls.comedor },
        { text: "Nómina", url: data.urls.nomina },
        { text: "Historial de asistencia", url: null },
      ]} />}
      content={<>{HITOS_STYLESHEET}<ComedorAsistenciaContent data={data} /></>}
      previewLinks={false}
    />
    <AppLoaded />
  </>;
}

const API = "web/comedores/comedores/";
const HISTORIAL = /^\/comedores\/([1-9]\d*)\/admision\/([1-9]\d*)\/nomina\/asistencia\/$/;

// Native URL `nomina_asistencia_historial` (trailing slash like the Django route).
export const comedorAsistenciaHistorialRoute: RouteDefinition<{ endpoint: string }> = {
  name: "comedor-asistencia-historial",
  match(pathname) {
    const m = HISTORIAL.exec(pathname);
    return m ? { endpoint: `${API}${m[1]}/admision/${m[2]}/nomina/asistencia/` } : null;
  },
  render: ({ endpoint }) => <AsistenciaPage key={endpoint} endpoint={endpoint} />,
};
