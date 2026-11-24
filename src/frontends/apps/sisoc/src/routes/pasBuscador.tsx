import { Fragment } from "react";
import { renderMain, text, useMainResource } from "./MainFrame";
import { EYEBROW, PAS_API, PAS_STYLESHEET, SourceChip, bool, integer, list, nullable, shape } from "./pasFrame";

/**
 * «Buscador PAS» (`pas/listar`, `pas/persona_list.html`): GET search form,
 * 10 rows per page with `NoCountPaginator` and `components/pagination.html`.
 * «Exportar tokens» is the native download (PAS02.02); React only links it.
 */
type Row = {
  id: number; apellidos: string; nombres: string; dni: number; id_persona: number; cuit: string; provincia: string; municipio: string;
  estado: { nombre: string; css_class: string }; avisos: number[];
};
type ListData = {
  page: number; is_paginated: boolean; has_previous: boolean; has_next: boolean; previous: number | null; next: number | null;
  page_range: (number | "…")[]; query_prefix: string; total_padron: number; query: string; estado_seleccionado: string;
  estados: { nombre: string }[]; capabilities: { can_import: boolean; can_export_tokens: boolean }; results: Row[];
};

const rowValid = (v: unknown): v is Row => shape(v, {
  id: integer, apellidos: text, nombres: text, dni: integer, id_persona: integer, cuit: text, provincia: text, municipio: text,
  estado: (e) => shape(e, { nombre: text, css_class: text }), avisos: list(integer),
});
const listValid = (v: unknown): v is ListData => shape(v, {
  page: integer, is_paginated: bool, has_previous: bool, has_next: bool, previous: nullable(integer), next: nullable(integer),
  page_range: list((n: unknown): n is number | "…" => n === "…" || integer(n)), query_prefix: text, total_padron: integer,
  query: text, estado_seleccionado: text, estados: list((e: unknown): e is { nombre: string } => shape(e, { nombre: text })),
  capabilities: (c) => shape(c, { can_import: bool, can_export_tokens: bool }), results: list(rowValid),
});

/** `components/pagination.html` without a count line (`NoCountPaginator`). */
function Pagination({ data }: { data: ListData }) {
  const href = (n: number) => `?${data.query_prefix}page=${n}`;
  // Page numbers carry `page-item {% if active %}active{% endif %}`; Volver/Continuar only `page-item`.
  const item = (label: string, target: number | null, extra?: string) => target === null
    ? <li className="page-item disabled"><a href="#" className="page-link">{label}</a></li>
    : <li className={extra === undefined ? "page-item" : `page-item ${extra}`}><a href={href(target)} className="page-link">{label}</a></li>;
  return <div className="mt-2">
    {data.is_paginated && <ul className="pagination">
      {item("Volver", data.previous)}
      {data.page_range.map((n, i) => <Fragment key={i}>{n === "…" ? item("...", null) : item(String(n), n, data.page === n ? "active" : "")}</Fragment>)}
      {item("Continuar", data.next)}
    </ul>}
  </div>;
}

function Buscador({ data }: { data: ListData }) {
  const { capabilities } = data;
  return <main className="pas-workspace">
    <header className="pas-module-header">
      <div><span className="pas-eyebrow">{EYEBROW}</span><h1>Buscador PAS</h1></div>
      <SourceChip pending={false} icon="bi-database-check">Padrón SISOC</SourceChip>
    </header>
    <section className="pas-search-panel" aria-labelledby="pas-search-title">
      <div className="pas-section-heading">
        <div><span className="pas-eyebrow">Panel de Control</span><h2 id="pas-search-title">Buscador PAS</h2></div>
        <div className="pas-panel-actions">
          {capabilities.can_import && <a href="/pas/titulares/importar" className="btn btn-primary" title="Importar titulares desde CSV">
            <i className="bi bi-file-earmark-arrow-up" aria-hidden="true" />{" "}Importar titulares
          </a>}
          {capabilities.can_import && capabilities.can_export_tokens && " "}
          {capabilities.can_export_tokens && <a href="/pas/ddjj/tokens/exportar" className="btn btn-outline-light" title="Descargar tokens vigentes de DDJJ">
            <i className="bi bi-file-earmark-excel" aria-hidden="true" />{" "}Exportar tokens
          </a>}
        </div>
      </div>
      <form method="get" className="pas-search-form" role="search">
        <label className="visually-hidden" htmlFor="pas-query">Buscar titular</label>
        <div className="pas-search-input">
          <i className="bi bi-search" aria-hidden="true" />
          <input id="pas-query" type="search" name="q" defaultValue={data.query} placeholder="Buscar por nombre, CUIT, DNI o IdPersona" autoComplete="off" />
        </div>
        <label className="visually-hidden" htmlFor="pas-estado">Estado</label>
        <select id="pas-estado" name="estado" className="form-select" defaultValue={data.estados.some((e) => e.nombre === data.estado_seleccionado) ? data.estado_seleccionado : ""}>
          <option value="">Todos los estados</option>
          {data.estados.map((e) => <option key={e.nombre} value={e.nombre}>{e.nombre}</option>)}
        </select>
        <button type="submit" className="btn btn-primary" title="Buscar">
          <i className="bi bi-search" aria-hidden="true" />{" "}<span>Buscar</span>
        </button>
        {(data.query || data.estado_seleccionado) && <a href="/pas/listar" className="btn btn-outline-light" title="Limpiar búsqueda">
          <i className="bi bi-x-lg" aria-hidden="true" />
        </a>}
      </form>
      <div className="pas-table-wrap">
        <table className="pas-table">
          <thead><tr>
            <th>Titular</th><th>CUIT</th><th>Ubicación</th><th>Estado</th><th>Avisos</th>
            <th className="pas-table-actions"><span className="visually-hidden">Acciones</span></th>
          </tr></thead>
          <tbody>
            {data.results.length ? data.results.map((p) => <tr key={p.id}>
              <td><a href={`/pas/panel-control/${p.id}`} className="pas-person-link">
                <strong>{p.apellidos}, {p.nombres}</strong>
                <span>DNI {p.dni} · IdPersona {p.id_persona}</span>
              </a></td>
              <td>{p.cuit || "-"}</td>
              <td>{p.provincia || "-"}{" "}<span className="pas-cell-secondary">{p.municipio}</span></td>
              <td><span className={`pas-status-pill ${p.estado.css_class}`}>{p.estado.nombre}</span></td>
              <td><div className="pas-aviso-stack">
                {p.avisos.length ? p.avisos.map((codigo, i) => <span key={i} className="pas-aviso-card">{codigo}</span>) : <span className="pas-cell-secondary">Sin avisos</span>}
              </div></td>
              <td className="pas-table-actions">
                <a href={`/pas/panel-control/${p.id}`} className="btn btn-sm btn-outline-light" title={`Abrir panel de control de ${p.nombres} ${p.apellidos}`}>
                  <i className="bi bi-chevron-right" aria-hidden="true" />
                </a>
              </td>
            </tr>) : <tr><td colSpan={6}><div className="pas-empty-state">
              <i className="bi bi-person-x" aria-hidden="true" />
              <strong>Sin titulares para los criterios seleccionados</strong>
            </div></td></tr>}
          </tbody>
        </table>
      </div>
      <footer className="pas-list-footer">
        <span>Padrón actual: {data.total_padron} titular{data.total_padron === 1 ? "" : "es"}</span>
        <Pagination data={data} />
      </footer>
    </section>
  </main>;
}

export default function PasBuscadorPage() {
  const [state] = useMainResource(`${PAS_API}personas/${window.location.search}`, listValid);
  return renderMain(state, "Cargando titulares…", (data) => ({
    title: "Buscador PAS",
    breadcrumb: null,
    appHeader: <div className="pas-top-actions">
      <a href="/pas/informes" className="btn btn-outline-light">
        <i className="bi bi-file-earmark-bar-graph" aria-hidden="true" />{" "}Informes
      </a>
    </div>,
    content: <>
      {PAS_STYLESHEET}
      <Buscador data={data} />
    </>,
  }));
}
