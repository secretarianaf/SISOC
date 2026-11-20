/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import type { ReactNode } from "react";
import { Filters, filtersConfigValid, type Favorites, type FiltersConfig } from "./listControls";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { CsrfInput } from "./vatFormShared";
import { bool, integer, listUrlsValid, messagesValid, pageValid, VatPagination, VatTable, vatNavigation, type Message, type Page } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V07.01 curricular plans: `vat/catalogo/planversioncurricular_{list,detail}.html`. Data comes from
 * `/api/web/vat/catalogos/planes-curriculares/`, which runs the native views (role guard, scope, combinable filters); the form is
 * `vatPlanesForm.tsx` and the delete confirmation (`eliminar/`) stays the native page. The detail deletes through the native POST form.
 */
type Row = {
  id: number; sector: string; subsector: string; nombre: string; modalidad: string; horas: string; activo: boolean;
  detail_url: string; update_url: string; delete_url: string;
};
type Permisos = { editar: boolean; eliminar: boolean };
export type PlanListData = {
  results: Row[]; page: Page; permisos: Permisos; urls: { list: string; create: string }; messages: Message[];
  filters_config: FiltersConfig; favorites: Favorites;
};
export type PlanDetailData = {
  id: number; titulo: string; nombre: string; sector: string; subsector: string; modalidad: string; activo: boolean; normativa: string; normativa_tipo: string;
  normativa_numero: string; normativa_anio: string; horas_reloj: string; nivel_requerido: string; nivel_certifica: string; permisos: Permisos;
  urls: { list: string; update: string; delete: string }; messages: Message[];
};

const API = "web/vat/catalogos/planes-curriculares/";

const rowValid = (r: unknown) => record(r) && integer(r.id) && ["sector", "subsector", "nombre", "modalidad", "horas"].every((k) => text(r[k])) && bool(r.activo) &&
  internal(r.detail_url) && internal(r.update_url) && internal(r.delete_url);
const permisosValid = (p: unknown) => record(p) && bool(p.editar) && bool(p.eliminar);

export const planListValid = (v: unknown): v is PlanListData => record(v) && Array.isArray(v.results) && v.results.every(rowValid) && pageValid(v.page) &&
  permisosValid(v.permisos) && listUrlsValid(v.urls) && messagesValid(v.messages) && filtersConfigValid(v.filters_config) &&
  record(v.favorites) && text(v.favorites.section) && internal(v.favorites.url) && text(v.favorites.detail_url_template);

export const planDetailValid = (v: unknown): v is PlanDetailData => record(v) && integer(v.id) &&
  ["titulo", "nombre", "sector", "subsector", "modalidad", "normativa", "normativa_tipo", "normativa_numero", "normativa_anio", "horas_reloj", "nivel_requerido", "nivel_certifica"].every((k) => text(v[k])) &&
  bool(v.activo) && permisosValid(v.permisos) && record(v.urls) && internal(v.urls.list) && internal(v.urls.update) && internal(v.urls.delete) && messagesValid(v.messages);

export function PlanListContent({ data }: { data: PlanListData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <link rel="stylesheet" href="/static/custom/css/vat_design.css" />
    <div className="vat-ui">
      {/* `components/search_bar.html` in filters mode: title, combinable filters, Resetear and the add button. */}
      <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
      <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
      <h2 className="text-center mb-4 poncho-titulo">Buscar Plan de Estudio</h2>
      <Filters config={data.filters_config} action={data.urls.list} favorites={data.favorites} />
      <div className="row mt-3"><div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
        <a href={data.urls.list} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
        <a href={data.urls.create} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />Agregar</a>
      </div></div>
      <VatTable
        headers={[{ title: "Sector" }, { title: "Subsector" }, { title: "Nombre", sortable: { column: "titulo" } }, { title: "Modalidad" }, { title: "Horas" }, { title: "Estado" }, { title: "Acciones", notexport: true }]}
        rows={data.results} columns={8} sortValue={(r) => r.nombre}
        empty={{ title: "No se encontraron planes de estudio", text: "No hay planes registrados." }}
        renderRow={(p) => <tr key={p.id}>
          <td>{p.sector}</td>
          <td>{p.subsector}</td>
          <td data-titulo={p.nombre}><a href={p.detail_url} className="link-handler" title="Ver detalles">{p.nombre}</a></td>
          <td>{p.modalidad}</td>
          <td>{p.horas}</td>
          <td>{p.activo
            ? <span className="badge-validacion validado"><i className="fas fa-check-circle" />{" "}Activo</span>
            : <span className="badge-validacion no-validado"><i className="fas fa-times-circle" />{" "}Inactivo</span>}</td>
          <td><div className="action-buttons" role="group">
            <a href={p.detail_url} className="btn btn-primary link-handler" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
            {data.permisos.editar && <>{" "}<a href={p.update_url} className="btn btn-editar link-handler" title="Editar plan"><i className="fas fa-edit" />{" "}Editar</a></>}
            {data.permisos.eliminar && <>{" "}<a href={p.delete_url} className="btn btn-eliminar link-handler" title="Eliminar plan"><i className="fas fa-trash-alt" />{" "}Eliminar</a></>}
          </div></td>
        </tr>}
      />
      <VatPagination page={data.page} shown={data.results.length} />
    </div>
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, planListValid);
  return renderMain(state, "Cargando planes…", (data) => ({ title: "Planes de Estudio", breadcrumb: null, content: <PlanListContent data={data} /> }));
}

/** The native detail deletes with a POST form of the native view and `onsubmit="return confirm('¿Está seguro?')"`. */
function DeleteForm({ action }: { action: string }) {
  return <form method="post" action={action} onSubmit={(e) => { if (!vatNavigation.confirm("¿Está seguro?")) e.preventDefault(); }}>
    <CsrfInput />
    <button type="submit" className="btn btn-danger"><i className="fas fa-trash me-1" />Eliminar</button>
  </form>;
}

const Metric = ({ label, children }: { label: string; children: ReactNode }) => <div className="vp-metric">
  <div className="vp-metric-label">{label}</div>
  <div className="vp-metric-value">{children}</div>
</div>;

export function PlanDetailContent({ data }: { data: PlanDetailData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/vat_design.css" />
    <div className="vat-ui vp-shell">
      <div className="vp-hero">
        <div>
          <h1><i className="fas fa-clipboard-list me-2" />{data.titulo}</h1>
          <p>Detalle del plan curricular con su clasificación académica, carga horaria y condiciones de certificación.</p>
        </div>
        <div className="vp-hero-actions">
          {data.permisos.editar && <a href={data.urls.update} className="btn btn-warning"><i className="fas fa-edit me-1" />Editar</a>}
          {data.permisos.eliminar && <DeleteForm action={data.urls.delete} />}
        </div>
      </div>
      <div className="card vp-panel">
        <div className="vp-panel-header"><div>
          <h3 className="card-title"><i className="fas fa-sitemap me-2" />Clasificación Académica</h3>
          <div className="small">Sector, subsector y modalidad del plan.</div>
        </div></div>
        <div className="vp-section"><div className="vp-metric-grid">
          <Metric label="Nombre">{data.nombre}</Metric>
          <Metric label="Sector">{data.sector}</Metric>
          <Metric label="Subsector">{data.subsector}</Metric>
          <Metric label="Modalidad de Cursado">{data.modalidad}</Metric>
        </div></div>
      </div>
      <div className="card vp-panel">
        <div className="vp-panel-header"><div>
          <h3 className="card-title"><i className="fas fa-book me-2" />Datos del Plan</h3>
          <div className="small">Normativa, carga horaria y niveles del trayecto.</div>
        </div></div>
        <div className="vp-section"><div className="vp-metric-grid">
          <Metric label="Estado">{data.activo
            ? <span className="vp-badge vp-badge--ok"><i className="fas fa-check-circle" />Activo</span>
            : <span className="vp-badge vp-badge--off"><i className="fas fa-times-circle" />Inactivo</span>}</Metric>
          <Metric label="Normativa">{data.normativa}</Metric>
          <Metric label="Normativa - Tipo">{data.normativa_tipo}</Metric>
          <Metric label="Normativa - Número">{data.normativa_numero}</Metric>
          <Metric label="Normativa - Año">{data.normativa_anio}</Metric>
          <Metric label="Horas Reloj">{data.horas_reloj}</Metric>
          <Metric label="Nivel Requerido">{data.nivel_requerido}</Metric>
          <Metric label="Nivel que Certifica">{data.nivel_certifica}</Metric>
        </div></div>
      </div>
    </div>
  </>;
}

function DetailPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/`, planDetailValid);
  return renderMain(state, "Cargando plan…", (data) => ({ title: "Detalle Plan de Estudio", heading: "Detalle Plan de Estudio", breadcrumb: null, content: <PlanDetailContent data={data} /> }));
}

type Params = { id?: string };

// Native URLs of `VAT/urls.py`; `nuevo/` and `<id>/editar/` are `vatPlanesForm.tsx`, `<id>/eliminar/` stays native.
const PATH = /^\/vat\/catalogos\/planes-curriculares\/(?:([0-9]+)\/)?$/;

export const vatPlanesRoute: RouteDefinition<Params> = {
  name: "vat-planes",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { id: m[1] } : null;
  },
  render({ id }) {
    return id ? <DetailPage key={id} id={id} /> : <ListPage />;
  },
};
