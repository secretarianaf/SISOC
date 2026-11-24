/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { bool, integer, listUrlsValid, messagesValid, pageValid, VatPagination, VatSearchBar, VatTable, type Message, type Page } from "./vatShared";
import { TourHelp } from "./vatTour";
import type { RouteDefinition } from "./types";

/**
 * V05.01 institutional offers: `oferta_institucional/oferta_list.html` and `oferta_detail.html`. Data comes from
 * `/api/web/vat/ofertas-institucionales/`, which runs the native views; the form and the delete confirmation live in
 * `vatOfertaForm.tsx`. The detail draws «Editar» and «Eliminar» for everyone (the native template has no permission check).
 */
type Row = {
  id: number; centro: string; plan: string; ciclo: string; estado: string; estado_label: string; usa_voucher: boolean;
  detail_url: string; update_url: string; delete_url: string;
};
export type OfertaListData = {
  results: Row[]; page: Page; busqueda: string; permisos: { editar: boolean; eliminar: boolean };
  urls: { list: string; create: string }; messages: Message[];
};
export type OfertaDetailData = {
  id: number; titulo: string; centro: string; plan: string; programa: string; ciclo: string; estado_label: string; nombre_local: string;
  costo: string; usa_voucher: boolean; fecha_publicacion: string; observaciones: string; fecha_creacion: string; fecha_modificacion: string;
  urls: { list: string; update: string; delete: string }; messages: Message[];
};

const API = "web/vat/ofertas-institucionales/";

const rowValid = (r: unknown) => record(r) && integer(r.id) && ["centro", "plan", "ciclo", "estado", "estado_label"].every((k) => text(r[k])) && bool(r.usa_voucher) &&
  internal(r.detail_url) && internal(r.update_url) && internal(r.delete_url);

export const ofertaListValid = (v: unknown): v is OfertaListData => record(v) && Array.isArray(v.results) && v.results.every(rowValid) &&
  pageValid(v.page) && text(v.busqueda) && record(v.permisos) && bool(v.permisos.editar) && bool(v.permisos.eliminar) && listUrlsValid(v.urls) && messagesValid(v.messages);

export const ofertaDetailValid = (v: unknown): v is OfertaDetailData => record(v) && integer(v.id) &&
  ["titulo", "centro", "plan", "programa", "ciclo", "estado_label", "nombre_local", "costo", "fecha_publicacion", "observaciones", "fecha_creacion", "fecha_modificacion"].every((k) => text(v[k])) &&
  bool(v.usa_voucher) && record(v.urls) && internal(v.urls.list) && internal(v.urls.update) && internal(v.urls.delete) && messagesValid(v.messages);

/** The status badge of `oferta_list.html`. */
function EstadoBadge({ estado, label }: { estado: string; label: string }) {
  if (estado === "activa") return <span className="badge-validacion validado"><i className="fas fa-check-circle" />{" "}{label}</span>;
  if (estado === "cancelada") return <span className="badge-validacion no-validado"><i className="fas fa-times-circle" />{" "}{label}</span>;
  if (estado === "finalizada") return <span className="badge-validacion" style={{ background: "#4b5563", color: "#e5e7eb", borderColor: "#6b7280" }}><i className="fas fa-flag-checkered" />{" "}{label}</span>;
  return <span className="badge-validacion pendiente"><i className="fas fa-clock" />{" "}{label}</span>;
}

export function OfertaListContent({ data }: { data: OfertaListData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <VatSearchBar title="Buscar Oferta Institucional" placeholder="Buscar por centro, plan de estudio o nombre" query={data.busqueda} reset={data.urls.list} add={{ url: data.urls.create, text: "Agregar" }} />
    <VatTable
      headers={[{ title: "Centro", sortable: { column: "centro" } }, { title: "Plan de Estudio", sortable: { column: "plan" } }, { title: "Ciclo" }, { title: "Estado" }, { title: "Voucher" }, { title: "Acciones", notexport: true }]}
      rows={data.results} columns={6} sortValue={(r, column) => (column === "plan" ? r.plan : r.centro)}
      empty={{ title: "No se encontraron ofertas institucionales", text: "No hay ofertas que coincidan con los criterios de búsqueda." }}
      renderRow={(o) => <tr key={o.id}>
        <td data-centro={o.centro}><a href={o.detail_url} className="link-handler" title="Ver detalles">{o.centro}</a></td>
        <td data-plan={o.plan}>{o.plan}</td>
        <td>{o.ciclo}</td>
        <td><EstadoBadge estado={o.estado} label={o.estado_label} /></td>
        <td>{o.usa_voucher
          ? <span className="badge-validacion validado"><i className="fas fa-ticket-alt" />{" "}Sí</span>
          : <span className="badge-validacion pendiente">—</span>}</td>
        <td><div className="action-buttons" role="group">
          <a href={o.detail_url} className="btn btn-primary link-handler" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
          {data.permisos.editar && <>{" "}<a href={o.update_url} className="btn btn-editar link-handler" title="Editar oferta"><i className="fas fa-edit" />{" "}Editar</a></>}
          {data.permisos.eliminar && <>{" "}<a href={o.delete_url} className="btn btn-eliminar link-handler" title="Eliminar oferta"><i className="fas fa-trash-alt" />{" "}Eliminar</a></>}
        </div></td>
      </tr>}
    />
    <VatPagination page={data.page} shown={data.results.length} />
    <TourHelp section="oferta_list" />
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, ofertaListValid);
  return renderMain(state, "Cargando ofertas…", (data) => ({ title: "Ofertas Institucionales", breadcrumb: null, content: <OfertaListContent data={data} /> }));
}

export function OfertaDetailContent({ data }: { data: OfertaDetailData }) {
  const label = (title: string) => <><label className="form-label small fw-600 text-muted">{title}</label><br /></>;
  return <>
    <NativeToasts messages={data.messages} />
    <div className="container-fluid py-4">
      <div className="row mb-4"><div className="col-12">
        <div className="d-flex align-items-center gap-2 mb-4">
          <a href={data.urls.list} className="btn btn-light"><i className="bi bi-arrow-left" /></a>
          <div>
            <h1 className="h2 mb-0" style={{ color: "#1f3a93" }}><i className="bi-book me-2" />Oferta Institucional</h1>
            <small className="text-muted">{data.titulo}</small>
          </div>
        </div>
      </div></div>
      <div className="row">
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm mb-4">
            <div className="card-header bg-light border-bottom"><h5 className="mb-0"><i className="bi bi-file-earmark-text me-2" style={{ color: "#1f3a93" }} />Información</h5></div>
            <div className="card-body p-4">
              <div className="row mb-4">
                <div className="col-md-6">{label("Centro")}<p className="mb-0">{data.centro}</p></div>
                <div className="col-md-6">{label("Plan de Estudio")}<p className="mb-0">{data.plan}</p></div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4">
                <div className="col-md-6">{label("Programa")}<p className="mb-0">{data.programa}</p></div>
                <div className="col-md-6">{label("Ciclo Lectivo")}<p className="mb-0">{data.ciclo}</p></div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4">
                <div className="col-md-6">{label("Estado")}<span className="badge bg-info bg-opacity-10 text-info">{data.estado_label}</span></div>
                <div className="col-md-6">{label("Nombre Local")}<p className="mb-0">{data.nombre_local}</p></div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4">
                <div className="col-md-3">{label("Costo")}<p className="mb-0 fw-semibold">{data.costo ? data.costo : <span className="text-success">Gratuito</span>}</p></div>
                <div className="col-md-3">{label("Usa Voucher")}{data.usa_voucher
                  ? <span className="badge bg-success"><i className="bi bi-ticket-perforated me-1" />Sí</span>
                  : <span className="badge bg-secondary">No</span>}</div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4"><div className="col-md-12">{label("Fecha Publicación")}<p className="mb-0">{data.fecha_publicacion}</p></div></div>
              {data.observaciones && <>
                <hr className="my-4" />
                <div className="row"><div className="col-md-12"><label className="form-label small fw-600 text-muted">Observaciones</label><p className="mb-0">{data.observaciones}</p></div></div>
              </>}
            </div>
          </div>
          <div className="card border-0 shadow-sm">
            <div className="card-header bg-light border-bottom"><h5 className="mb-0"><i className="bi bi-clock-history me-2" style={{ color: "#1f3a93" }} />Auditoría</h5></div>
            <div className="card-body p-4"><div className="small text-muted"><dl>
              <dt>Creado</dt><dd>{data.fecha_creacion}</dd>
              <dt>Modificado</dt><dd>{data.fecha_modificacion}</dd>
            </dl></div></div>
          </div>
        </div>
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm mb-4 bg-primary bg-opacity-10"><div className="card-body">
            <h6 className="card-title fw-600" style={{ color: "#1f3a93" }}><i className="bi bi-lightning me-2" />Acciones</h6>
            <div className="d-grid gap-2">
              <a href={data.urls.update} className="btn btn-primary"><i className="bi bi-pencil me-2" />Editar</a>
              <a href={data.urls.delete} className="btn btn-danger"><i className="bi bi-trash me-2" />Eliminar</a>
            </div>
          </div></div>
          <div className="card border-0 shadow-sm bg-light"><div className="card-body">
            <h6 className="card-title fw-600" style={{ color: "#1f3a93" }}><i className="bi bi-info-circle me-2" />Registro</h6>
            <div className="small text-muted"><dl><dt>ID</dt><dd>#{data.id}</dd></dl></div>
          </div></div>
        </div>
      </div>
    </div>
    <style>{".fw-600 { font-weight: 600 !important; }"}</style>
  </>;
}

function DetailPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/`, ofertaDetailValid);
  return renderMain(state, "Cargando oferta…", (data) => ({ title: data.titulo, breadcrumb: null, content: <OfertaDetailContent data={data} /> }));
}

type Params = { id?: string };

// Native URLs `vat_oferta_institucional_{list,detail}`; `nueva/`, `<id>/editar/` and `<id>/eliminar/` belong to the form module.
const PATH = /^\/vat\/ofertas-institucionales\/(?:([0-9]+)\/)?$/;

export const vatOfertaRoute: RouteDefinition<Params> = {
  name: "vat-oferta-institucional",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { id: m[1] } : null;
  },
  render({ id }) {
    return id ? <DetailPage key={id} id={id} /> : <ListPage />;
  },
};
