/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen lives here with the route. */
import { Fragment } from "react";
import { Breadcrumb, crumbsValid, internal, messagesValid, record, renderCdi, text, useCdiPage, type CdiMessage, type Crumb } from "./cdiFrame";
import type { RouteDefinition } from "./types";

/**
 * CDI08.02 reports screen (`centrodeinfancia/reportes.html`): province and
 * variant selectors, the native XLSX download and the Resumen preview. The
 * summary rows come computed from the backend; this page never recalculates them.
 */
export type ReportesData = {
  breadcrumb: Crumb[];
  provincias: { id: number; nombre: string }[];
  provincia_seleccionada: string;
  variantes: { value: string; label: string }[];
  resumen: { columnas: string[]; filas: string[][] };
  urls: { pantalla: string; descarga: string };
  messages: CdiMessage[];
};

function reportesValid(v: unknown): v is ReportesData {
  if (!record(v) || !record(v.resumen) || !record(v.urls)) return false;
  const r = v.resumen, u = v.urls;
  return crumbsValid(v.breadcrumb) && text(v.provincia_seleccionada) && messagesValid(v.messages) &&
    Array.isArray(v.provincias) && v.provincias.every((p) => record(p) && Number.isSafeInteger(p.id) && text(p.nombre)) &&
    Array.isArray(v.variantes) && v.variantes.every((x) => record(x) && text(x.value) && text(x.label)) &&
    Array.isArray(r.columnas) && r.columnas.every(text) &&
    Array.isArray(r.filas) && r.filas.every((f) => Array.isArray(f) && f.length === 3 && f.every(text)) &&
    internal(u.pantalla) && internal(u.descarga);
}

export function ReportesContent({ data }: { data: ReportesData }) {
  const selected = data.provincias.some((p) => String(p.id) === data.provincia_seleccionada) ? data.provincia_seleccionada : "";
  return (
    <div className="container-fluid">
      <div className="card">
        <div className="card-body">
          <h3 className="mb-1">Reportes</h3>
          <p className="text-muted">
            El archivo Excel trae seis hojas: Resumen, Centros de Desarrollo
            Infantil, Trabajadores, Nómina, Diccionario y Metadatos. La hoja de
            Nómina incluye la validación RENAPER de cada niño o niña y de sus
            responsables legales.
          </p>
          <form method="get" action={data.urls.pantalla} className="row g-2 align-items-end">
            {data.provincias.length > 0 && <>
              <div className="col-12 col-md-4">
                <label htmlFor="provincia" className="form-label">Provincia</label>
                <select className="form-select" id="provincia" name="provincia" defaultValue={selected}>
                  <option value="">Todas</option>
                  {data.provincias.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                </select>
              </div>
              <div className="col-12 col-md-auto">
                <button type="submit" className="btn btn-secondary">
                  <i className="nav-icon bi bi-arrow-clockwise" />{" "}
                  Actualizar resumen
                </button>
              </div>
            </>}
            {data.variantes.length > 1 ? (
              <div className="col-12 col-md-4">
                <label htmlFor="variante" className="form-label">Tipo de reporte</label>
                <select className="form-select" id="variante" name="variante">
                  {data.variantes.map((v) => <option key={v.value} value={v.value}>{v.label}</option>)}
                </select>
              </div>
            ) : data.variantes.map((v) => (
              <Fragment key={v.value}>
                <input type="hidden" name="variante" value={v.value} />
                <p className="col-12 text-muted mb-0">Reporte disponible: {v.label}.</p>
              </Fragment>
            ))}
            <div className="col-12 col-md-auto">
              <button type="submit" className="btn btn-primary" formAction={data.urls.descarga}>
                <i className="nav-icon bi bi-file-earmark-excel" />{" "}
                Descargar reporte (XLSX)
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="card mt-3">
        <div className="card-body">
          <h3 className="mb-1">Vista previa: hoja Resumen</h3>
          <p className="text-muted">Es la primera hoja del archivo, tal como se descarga.</p>
          <div className="table-responsive">
            <table className="table table-bordered table-striped">
              <thead>
                <tr>{data.resumen.columnas.map((c) => <th key={c}>{c}</th>)}</tr>
              </thead>
              <tbody>
                {data.resumen.filas.length ? data.resumen.filas.map((fila, index) => (
                  <tr key={index}>{fila.map((celda, i) => <td key={i}>{celda}</td>)}</tr>
                )) : (
                  <tr><td colSpan={3} className="text-muted">No hay centros en tu alcance.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function ReportesPage() {
  const [state] = useCdiPage(`web/cdi/reportes/${window.location.search}`, reportesValid);
  return renderCdi(state, (data) => ({
    title: "Reportes de Centros de Desarrollo Infantil",
    heading: "Reportes",
    breadcrumb: <Breadcrumb items={data.breadcrumb} />,
    content: <ReportesContent data={data} />,
  }));
}

// Native URL of the CDI reports screen (CDI08.02); same trailing slash.
export const cdiReportesRoute: RouteDefinition<Record<string, never>> = {
  name: "cdi-reportes",
  match: (pathname) => (pathname === "/centrodeinfancia/reportes/" ? {} : null),
  render: () => <ReportesPage />,
};
