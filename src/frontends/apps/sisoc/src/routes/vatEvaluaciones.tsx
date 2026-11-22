/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { bool, listUrlsValid, messagesValid, pageValid, VatPagination, VatSearchBar, VatTable, integer, type Message, type Page } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V08.01 evaluaciones: `evaluacion_list.html` and `evaluacion_detail.html`. Data comes from
 * `/api/web/vat/evaluaciones/`, which runs the native views; alta, edición and baja stay native.
 */
type Row = {
  id: number; nombre: string; comision: string; tipo_label: string; fecha: string; es_final: boolean; ponderacion: string;
  detail_url: string; update_url: string; delete_url: string;
};
export type EvaluacionListData = {
  results: Row[]; page: Page; busqueda: string; permisos: { editar: boolean; eliminar: boolean }; urls: { list: string; create: string }; messages: Message[];
};
export type EvaluacionDetailData = {
  id: number; titulo: string; nombre: string; tipo_label: string; comision_codigo: string; comision_nombre: string; fecha: string; es_final: boolean;
  ponderacion: string; descripcion: string; observaciones: string; fecha_creacion: string; fecha_modificacion: string;
  urls: { list: string; update: string; delete: string }; messages: Message[];
};

const API = "web/vat/evaluaciones/";

const rowValid = (r: unknown) => record(r) && integer(r.id) && ["nombre", "comision", "tipo_label", "fecha", "ponderacion"].every((k) => text(r[k])) &&
  bool(r.es_final) && internal(r.detail_url) && internal(r.update_url) && internal(r.delete_url);

export function evaluacionListValid(v: unknown): v is EvaluacionListData {
  return record(v) && Array.isArray(v.results) && v.results.every(rowValid) && pageValid(v.page) && text(v.busqueda) &&
    record(v.permisos) && bool(v.permisos.editar) && bool(v.permisos.eliminar) && listUrlsValid(v.urls) && messagesValid(v.messages);
}

export function evaluacionDetailValid(v: unknown): v is EvaluacionDetailData {
  return record(v) && integer(v.id) &&
    ["titulo", "nombre", "tipo_label", "comision_codigo", "comision_nombre", "fecha", "ponderacion", "descripcion", "observaciones", "fecha_creacion", "fecha_modificacion"].every((k) => text(v[k])) &&
    bool(v.es_final) && record(v.urls) && internal(v.urls.list) && internal(v.urls.update) && internal(v.urls.delete) && messagesValid(v.messages);
}

export function EvaluacionListContent({ data }: { data: EvaluacionListData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <VatSearchBar title="Buscar Evaluación" placeholder="Buscar por nombre o comisión" query={data.busqueda} reset={data.urls.list} add={{ url: data.urls.create, text: "Agregar" }} />
    <VatTable
      headers={[{ title: "Nombre", sortable: { column: "nombre" } }, { title: "Comisión" }, { title: "Tipo" }, { title: "Fecha" }, { title: "Final" }, { title: "Pond." }, { title: "Acciones", notexport: true }]}
      rows={data.results} columns={7} sortValue={(r) => r.nombre}
      empty={{ title: "No se encontraron evaluaciones", text: "No hay evaluaciones registradas." }}
      renderRow={(e) => <tr key={e.id}>
        <td data-nombre={e.nombre}><a href={e.detail_url} className="link-handler" title="Ver detalles">{e.nombre}</a></td>
        <td>{e.comision}</td>
        <td>{e.tipo_label}</td>
        <td>{e.fecha}</td>
        <td>{e.es_final
          ? <span className="badge-validacion validado"><i className="fas fa-check-circle" />{" "}Sí</span>
          : <span className="badge-validacion pendiente">No</span>}</td>
        <td>{e.ponderacion}%</td>
        <td><div className="action-buttons" role="group">
          <a href={e.detail_url} className="btn btn-primary link-handler" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
          {data.permisos.editar && <>{" "}<a href={e.update_url} className="btn btn-editar link-handler" title="Editar evaluación"><i className="fas fa-edit" />{" "}Editar</a></>}
          {data.permisos.eliminar && <>{" "}<a href={e.delete_url} className="btn btn-eliminar link-handler" title="Eliminar evaluación"><i className="fas fa-trash-alt" />{" "}Eliminar</a></>}
        </div></td>
      </tr>}
    />
    <VatPagination page={data.page} shown={data.results.length} />
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, evaluacionListValid);
  return renderMain(state, "Cargando evaluaciones…", (data) => ({ title: "Evaluaciones", breadcrumb: null, content: <EvaluacionListContent data={data} /> }));
}

export function EvaluacionDetailContent({ data }: { data: EvaluacionDetailData }) {
  const label = "form-label small fw-600 text-muted";
  return <>
    <NativeToasts messages={data.messages} />
    <div className="container-fluid py-4">
      <div className="row mb-4"><div className="col-12">
        <div className="d-flex align-items-center gap-2 mb-4">
          <a href={data.urls.list} className="btn btn-light"><i className="bi bi-arrow-left" /></a>
          <div>
            <h1 className="h2 mb-0" style={{ color: "#1f3a93" }}><i className="bi-clipboard2-data me-2" />Evaluación</h1>
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
                <div className="col-md-6"><label className={label}>Nombre</label><br /><p className="mb-0">{data.nombre}</p></div>
                <div className="col-md-6"><label className={label}>Tipo</label><br /><span className="badge bg-info bg-opacity-10 text-info">{data.tipo_label}</span></div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4">
                <div className="col-md-6"><label className={label}>Comisión</label><br /><p className="mb-0">{data.comision_codigo} - {data.comision_nombre}</p></div>
                <div className="col-md-6"><label className={label}>Fecha</label><br /><p className="mb-0">{data.fecha}</p></div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4">
                <div className="col-md-6"><label className={label}>Es Final</label><br />{data.es_final ? <span className="badge bg-success">Sí</span> : <span className="badge bg-secondary">No</span>}</div>
                <div className="col-md-6"><label className={label}>Ponderación</label><br /><p className="mb-0">{data.ponderacion}%</p></div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4"><div className="col-md-12"><label className={label}>Descripción</label><br /><p className="mb-0">{data.descripcion}</p></div></div>
              {data.observaciones && <>
                <hr className="my-4" />
                <div className="row"><div className="col-md-12"><label className={label}>Observaciones</label><p className="mb-0">{data.observaciones}</p></div></div>
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
  const [state] = useMainResource(`${API}${id}/`, evaluacionDetailValid);
  return renderMain(state, "Cargando evaluación…", (data) => ({ title: data.titulo, breadcrumb: null, content: <EvaluacionDetailContent data={data} /> }));
}

type Params = { id?: string };

// Native URLs of `VAT/urls.py`; `nueva/`, `<id>/editar/` and `<id>/eliminar/` are not mine.
const PATH = /^\/vat\/evaluaciones\/(?:([0-9]+)\/)?$/;

export const vatEvaluacionesRoute: RouteDefinition<Params> = {
  name: "vat-evaluaciones",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { id: m[1] } : null;
  },
  render({ id }) {
    return id ? <DetailPage key={id} id={id} /> : <ListPage />;
  },
};
