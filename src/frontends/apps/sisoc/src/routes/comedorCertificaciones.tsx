/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen, validator and route live here. */
import { InsumosToastList } from "../InsumosToast";
import { Breadcrumb, internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { Pagination } from "./listControls";
import type { RouteDefinition } from "./types";

/**
 * CO05.01 monthly benefits certifications history (`certificaciones_prestaciones_historial`):
 * `comedor/certificaciones_prestaciones_historial.html` with its GET filters (period, generator,
 * conformity), the table and `components/pagination.html`. Data comes from
 * `/api/web/comedores/comedores/<id>/certificaciones-prestaciones/`, which runs the native view. It only
 * reads: the certification is produced by the PWA and the PDF stays the native binary download link.
 */
type Certificacion = { id: number; periodo: string; usuario: string; conforme: boolean; creado: string; pdf_url: string | null };
type Page = { number: number; count: number; is_paginated: boolean; previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string };
export type ComedorCertificacionesData = {
  comedor: { id: number; nombre: string };
  filtros: { periodo: string; usuario: string; conforme: string };
  generadores: { id: number; label: string }[];
  certificaciones: Certificacion[];
  page: Page;
  urls: { comedores: string; comedor: string; historial: string };
  messages: { message: string; level: "success" | "error" | "warning" | "info" }[];
};

const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const LEVELS = ["success", "error", "warning", "info"];

export function certificacionesValid(v: unknown): v is ComedorCertificacionesData {
  if (!record(v) || !record(v.comedor) || !record(v.filtros) || !record(v.page) || !record(v.urls)) return false;
  const p = v.page, f = v.filtros, u = v.urls;
  return int(v.comedor.id) && text(v.comedor.nombre) &&
    ["periodo", "usuario", "conforme"].every((k) => text(f[k])) &&
    Array.isArray(v.generadores) && v.generadores.every((g) => record(g) && int(g.id) && text(g.label)) &&
    Array.isArray(v.certificaciones) && v.certificaciones.every((c) => record(c) && int(c.id) &&
      ["periodo", "usuario", "creado"].every((k) => text(c[k])) && typeof c.conforme === "boolean" &&
      (c.pdf_url === null || internal(c.pdf_url))) &&
    int(p.number) && int(p.count) && typeof p.is_paginated === "boolean" &&
    (p.previous === null || int(p.previous)) && (p.next === null || int(p.next)) &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || int(n)) && text(p.query_without_page) &&
    ["comedores", "comedor", "historial"].every((k) => internal(u[k])) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

export function ComedorCertificacionesContent({ data }: { data: ComedorCertificacionesData }) {
  const { filtros, page } = data;
  // `{% if filtros.usuario == item.usuario_id|stringformat:"s" %}selected`: no match keeps «Todos».
  const usuario = data.generadores.some((g) => String(g.id) === filtros.usuario) ? filtros.usuario : "";
  return (
    <>
      <InsumosToastList messages={data.messages} />
      <div className="card">
        <div className="card-header d-flex justify-content-between align-items-center">
          <h3 className="card-title mb-0">Historial completo</h3>
        </div>
        <div className="card-body">
          <form method="get" className="row g-3 mb-4">
            <div className="col-md-3">
              <label htmlFor="periodo" className="form-label">Período de Certificación</label>
              <input type="month" id="periodo" name="periodo" className="form-control" defaultValue={filtros.periodo} />
            </div>
            <div className="col-md-4">
              <label htmlFor="usuario" className="form-label">Usuario Generador</label>
              <select id="usuario" name="usuario" className="form-control" defaultValue={usuario}>
                <option value="">Todos</option>
                {data.generadores.map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}
              </select>
            </div>
            <div className="col-md-3">
              <label htmlFor="conforme" className="form-label">Estado de Conformidad</label>
              <select id="conforme" name="conforme" className="form-control" defaultValue={["true", "false"].includes(filtros.conforme) ? filtros.conforme : ""}>
                <option value="">Todos</option>
                <option value="true">Conforme</option>
                <option value="false">No conforme</option>
              </select>
            </div>
            <div className="col-md-2 d-flex align-items-end gap-2">
              <button type="submit" className="btn btn-primary">Filtrar</button>
              <a href={data.urls.historial} className="btn btn-secondary">Limpiar</a>
            </div>
          </form>
          <div className="table-responsive">
            <table className="table table-bordered table-striped">
              <thead>
                <tr><th>Período</th><th>Usuario generador</th><th>Estado Conformidad</th><th>Fecha de certificación</th><th>Ver PDF</th></tr>
              </thead>
              <tbody>
                {data.certificaciones.length ? data.certificaciones.map((c) => (
                  <tr key={c.id}>
                    <td>{c.periodo}</td>
                    <td>{c.usuario}</td>
                    <td>{c.conforme ? <span className="badge bg-success">Conforme</span> : <span className="badge bg-danger">No conforme</span>}</td>
                    <td>{c.creado}</td>
                    <td>
                      {c.pdf_url
                        ? <a href={c.pdf_url} className="btn btn-sm btn-primary" target="_blank" rel="noopener">Ver PDF</a>
                        : <span className="text-muted">No disponible</span>}
                    </td>
                  </tr>
                )) : (
                  <tr><td colSpan={5} className="text-center text-muted">No hay certificaciones mensuales registradas.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {/* `{% if page_obj %}`: an empty page is falsy, so no count line without rows. */}
          <Pagination paginated={page.is_paginated} number={page.number} previous={page.previous} next={page.next}
            range={page.range} href={(n) => `?${page.query_without_page}page=${n}`} count={page.count > 0 ? page.count : null} />
        </div>
      </div>
    </>
  );
}

function CertificacionesPage({ endpoint }: { endpoint: string }) {
  const [state] = useMainResource(`${endpoint}${window.location.search}`, certificacionesValid);
  return renderMain(state, "Cargando certificaciones…", (data) => ({
    title: `Certificaciones mensuales: ${data.comedor.nombre}`,
    heading: "Certificaciones Mensuales de Prestaciones",
    breadcrumb: <Breadcrumb items={[
      { text: data.comedor.nombre, url: data.urls.comedor },
      { text: "Certificaciones mensuales", url: null },
    ]} />,
    content: <ComedorCertificacionesContent data={data} />,
  }));
}

const API = "web/comedores/comedores/";
const HISTORIAL = /^\/comedores\/([1-9]\d*)\/certificaciones-prestaciones\/$/;

// Native URL `certificaciones_prestaciones_historial` (trailing slash like the Django route).
export const comedorCertificacionesRoute: RouteDefinition<{ endpoint: string }> = {
  name: "comedor-certificaciones",
  match(pathname) {
    const m = HISTORIAL.exec(pathname);
    return m ? { endpoint: `${API}${m[1]}/certificaciones-prestaciones/` } : null;
  },
  render: ({ endpoint }) => <CertificacionesPage key={endpoint} endpoint={endpoint} />,
};
