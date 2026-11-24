/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { Breadcrumb, breadcrumbValid, internal, renderMain, text, useMainResource, type Breadcrumbs } from "./MainFrame";
import { Pagination } from "./listControls";
import { PAS_API, bool, integer, list, nullable, shape } from "./pasFrame";
import type { RouteDefinition } from "./types";

/**
 * PAS reports (PAS04.01) on the native URLs `pas/informes` and
 * `pas/informes/<pk>` (`pas/informe_list.html`, `pas/informe_detail.html`).
 * Data comes from `/api/web/pas/informes/`, which runs the native views. The
 * CSV download (PAS04.03) stays the native GET; React only links it.
 */
type Params = { page: "listar" } | { page: "detalle"; id: string };
type Row = {
  id: number; numero: string; creado: string; usuario: string; total_personas: number; total_cambios: number;
  detail_path: string; download_url: string | null;
};
export type InformeListData = {
  page: number; is_paginated: boolean; previous: number | null; next: number | null; page_range: (number | "…")[];
  query_prefix: string; count: number | null; breadcrumb: Breadcrumbs; query: string; can_generate: boolean; results: Row[];
};
export type InformeDetailData = {
  id: number; numero: string; creado: string; usuario: string; total_personas: number; total_cambios: number;
  breadcrumb: Breadcrumbs; filtros: { clave: string; valor: string }[]; columns: { key: string; label: string }[];
  rows: string[][]; download_url: string | null;
};

const link = nullable(internal);
const rowValid = (v: unknown): v is Row => shape(v, {
  id: integer, numero: text, creado: text, usuario: text, total_personas: integer, total_cambios: integer,
  detail_path: internal, download_url: link,
});
export const listValid = (v: unknown): v is InformeListData => shape(v, {
  page: integer, is_paginated: bool, previous: nullable(integer), next: nullable(integer),
  page_range: list((n: unknown): n is number | "…" => n === "…" || integer(n)), query_prefix: text, count: nullable(integer),
  breadcrumb: breadcrumbValid, query: text, can_generate: bool, results: list(rowValid),
});
export const detailValid = (v: unknown): v is InformeDetailData => shape(v, {
  id: integer, numero: text, creado: text, usuario: text, total_personas: integer, total_cambios: integer,
  breadcrumb: breadcrumbValid, filtros: list((f: unknown): f is object => shape(f, { clave: text, valor: text })),
  columns: list((c: unknown): c is object => shape(c, { key: text, label: text })),
  rows: list(list(text)), download_url: link,
});

/** `usuario.get_full_name|default:usuario.username|default:"-"`. */
const autor = (usuario: string) => usuario || "-";

function InformeList({ data }: { data: InformeListData }) {
  return <>
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <div className="comedor-list-container">
      <div className="search-section">
        <form method="get" className="search-form">
          <div className="search-header">
            <div>
              <h2 className="search-title">Informes PAS</h2>
              <p className="search-help">Buscar por numero de informe o usuario generador.</p>
            </div>
            {data.can_generate && <a href="/pas/informes/generar" className="btn btn-primary">
              <i className="fas fa-plus me-1" /> Nuevo informe
            </a>}
          </div>
          <div className="search-input-group">
            <input type="text" name="q" defaultValue={data.query} className="form-control search-input" placeholder="PAS-INF-000001, usuario, nombre o apellido" />
            <button className="btn btn-search" type="submit"><i className="fas fa-search" /> Buscar</button>
            {" "}<a href="/pas/informes" className="btn btn-reset">Limpiar</a>
          </div>
        </form>
      </div>
      <div className="row mt-5 max-width-100">
        <div className="col-12">
          <div className="card comedor-table-card">
            <div className="card-body">
              <div className="table-responsive-lg">
                <table className="table table-comedor-moderno">
                  <thead><tr>
                    <th>Numero</th><th>Fecha</th><th>Usuario</th><th>Personas</th><th>Cambios</th><th className="notexport">Acciones</th>
                  </tr></thead>
                  <tbody>
                    {data.results.length ? data.results.map((r) => <tr key={r.id}>
                      <td><a href={r.detail_path} className="link-handler">{r.numero}</a></td>
                      <td>{r.creado}</td>
                      <td>{autor(r.usuario)}</td>
                      <td>{r.total_personas}</td>
                      <td>{r.total_cambios}</td>
                      <td><div className="comedor-actions">
                        <a href={r.detail_path} className="btn btn-ver link-handler" title="Ver informe"><i className="fas fa-eye" /> Ver</a>
                        {r.download_url && <>{" "}<a href={r.download_url} className="btn btn-editar" title="Descargar CSV"><i className="fas fa-download" /> Descargar</a></>}
                      </div></td>
                    </tr>) : <tr><td colSpan={6}><div className="no-comedores-message">
                      <h3>No se encontraron informes PAS</h3>
                      <p>Genere un informe o modifique la busqueda.</p>
                    </div></td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
      <Pagination paginated={data.is_paginated} number={data.page} previous={data.previous} next={data.next} range={data.page_range}
        href={(n) => `?${data.query_prefix}page=${n}`} count={data.count} />
    </div>
  </>;
}

function InformeDetail({ data }: { data: InformeDetailData }) {
  return <>
    <link rel="stylesheet" href="/static/custom/css/comedor_detail.css" />
    <div className="container-fluid pas-detail-page p-0">
      <div className="pas-legajo-header">
        <div className="d-flex flex-column flex-lg-row justify-content-between align-items-start align-items-lg-center gap-3">
          <div>
            <h1>{data.numero}</h1>
            <p className="mb-0">Generado el {data.creado} por {autor(data.usuario)}</p>
          </div>
          <div className="d-flex gap-2">
            {data.download_url && <a href={data.download_url} className="btn btn-warning"><i className="fas fa-download me-1" /> Descargar CSV</a>}
          </div>
        </div>
      </div>
      <div className="pas-detail-content">
        <section className="pas-state-summary">
          {([["Personas incluidas", data.total_personas], ["Cambios detectados", data.total_cambios], ["Numero", data.numero]] as const).map(([label, value]) =>
            <div key={label} className="pas-state-summary-item">
              <span className="pas-summary-label">{label}</span>
              {" "}<span className="pas-last-change">{value}</span>
            </div>)}
        </section>
        <section className="pas-data-card">
          <h5>Filtros aplicados</h5>
          <div className="pas-filter-chipset">
            {data.filtros.length ? data.filtros.map((f, i) => <span key={i} className="pas-aviso-card">{f.clave}: {f.valor}{" "}</span>)
              : <span className="text-muted">Sin filtros. Incluye el universo PAS disponible.</span>}
          </div>
        </section>
        <div className="row relevamiento-container mb-3">
          <div className="col-12">
            <div className="card bg-card">
              <div className="card-header"><h3 className="card-title font-weight-bold me-3 pt-1">Resultado del CSV</h3></div>
              <div className="card-body">
                <div className="table-responsive">
                  <table className="table table-sm table-bordered table-striped mb-0 pas-history-table">
                    <thead><tr>{data.columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr></thead>
                    <tbody>
                      {data.rows.length ? data.rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>)
                        : <tr><td colSpan={16} className="text-center text-muted py-3">Sin registros para los filtros seleccionados.</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${PAS_API}informes/${window.location.search}`, listValid);
  return renderMain(state, "Cargando informes…", (data) => ({
    title: "Informes PAS", breadcrumb: <Breadcrumb items={data.breadcrumb} />, content: <InformeList data={data} />,
  }));
}

function DetailPage({ id }: { id: string }) {
  const [state] = useMainResource(`${PAS_API}informes/${id}/`, detailValid);
  return renderMain(state, "Cargando informe…", (data) => ({
    title: data.numero, breadcrumb: <Breadcrumb items={data.breadcrumb} />, content: <InformeDetail data={data} />,
  }));
}

const PATH = /^\/pas\/informes(?:\/([0-9]+))?$/;

export const pasInformesRoute: RouteDefinition<Params> = {
  name: "pas-informes",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    return m[1] ? { page: "detalle", id: m[1] } : { page: "listar" };
  },
  render(params) {
    return params.page === "listar" ? <ListPage /> : <DetailPage id={params.id} />;
  },
};
