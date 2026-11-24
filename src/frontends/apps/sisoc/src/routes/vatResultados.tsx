/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { listUrlsValid, messagesValid, pageValid, VatPagination, VatSearchBar, VatTable, integer, type Message, type Page } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V08.01 resultados de evaluación: `resultado_list.html` and `resultado_detail.html`. Data comes from
 * `/api/web/vat/resultados-evaluacion/`, which runs the native views; the forms are `vatResultadosForm.tsx`.
 */
type Row = {
  id: number; evaluacion: string; persona: string; calificacion: string; aprobo: boolean | null; fecha: string;
  detail_url: string; update_url: string; delete_url: string;
};
export type ResultadoListData = {
  results: Row[]; page: Page; busqueda: string; permisos: { editar: boolean; eliminar: boolean }; urls: { list: string; create: string }; messages: Message[];
};
export type ResultadoDetailData = {
  id: number; titulo: string; evaluacion: string; tipo_label: string; persona: string; comision: string; calificacion: string; aprobo: boolean | null;
  fecha_registro: string; registrado_por: string; observaciones: string; fecha_creacion: string; fecha_modificacion: string;
  urls: { list: string; update: string; delete: string }; messages: Message[];
};

const API = "web/vat/resultados-evaluacion/";
const triState = (v: unknown) => v === null || typeof v === "boolean";

const rowValid = (r: unknown) => record(r) && integer(r.id) && ["evaluacion", "persona", "calificacion", "fecha"].every((k) => text(r[k])) &&
  triState(r.aprobo) && internal(r.detail_url) && internal(r.update_url) && internal(r.delete_url);

export function resultadoListValid(v: unknown): v is ResultadoListData {
  return record(v) && Array.isArray(v.results) && v.results.every(rowValid) && pageValid(v.page) && text(v.busqueda) &&
    record(v.permisos) && typeof v.permisos.editar === "boolean" && typeof v.permisos.eliminar === "boolean" && listUrlsValid(v.urls) && messagesValid(v.messages);
}

export function resultadoDetailValid(v: unknown): v is ResultadoDetailData {
  return record(v) && integer(v.id) &&
    ["titulo", "evaluacion", "tipo_label", "persona", "comision", "calificacion", "fecha_registro", "registrado_por", "observaciones", "fecha_creacion", "fecha_modificacion"].every((k) => text(v[k])) &&
    triState(v.aprobo) && record(v.urls) && internal(v.urls.list) && internal(v.urls.update) && internal(v.urls.delete) && messagesValid(v.messages);
}

export function ResultadoListContent({ data }: { data: ResultadoListData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <VatSearchBar title="Buscar Resultado" placeholder="Buscar por evaluación o persona" query={data.busqueda} reset={data.urls.list} add={{ url: data.urls.create, text: "Agregar" }} />
    <VatTable
      headers={[{ title: "Evaluación", sortable: { column: "evaluacion" } }, { title: "Persona" }, { title: "Calificación" }, { title: "Aprobó" }, { title: "Fecha" }, { title: "Acciones", notexport: true }]}
      rows={data.results} columns={6} sortValue={(r) => r.evaluacion}
      empty={{ title: "No se encontraron resultados", text: "No hay resultados de evaluación registrados." }}
      renderRow={(r) => <tr key={r.id}>
        <td data-evaluacion={r.evaluacion}>{r.evaluacion}</td>
        <td>{r.persona}</td>
        <td>{r.calificacion}</td>
        <td>{r.aprobo === null ? <span className="badge-validacion pendiente">—</span>
          : r.aprobo ? <span className="badge-validacion validado"><i className="fas fa-check-circle" />{" "}Sí</span>
            : <span className="badge-validacion no-validado"><i className="fas fa-times-circle" />{" "}No</span>}</td>
        <td>{r.fecha}</td>
        <td><div className="action-buttons" role="group">
          <a href={r.detail_url} className="btn btn-primary link-handler" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
          {data.permisos.editar && <>{" "}<a href={r.update_url} className="btn btn-editar link-handler" title="Editar resultado"><i className="fas fa-edit" />{" "}Editar</a></>}
          {data.permisos.eliminar && <>{" "}<a href={r.delete_url} className="btn btn-eliminar link-handler" title="Eliminar resultado"><i className="fas fa-trash-alt" />{" "}Eliminar</a></>}
        </div></td>
      </tr>}
    />
    <VatPagination page={data.page} shown={data.results.length} />
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, resultadoListValid);
  return renderMain(state, "Cargando resultados…", (data) => ({ title: "Resultados de Evaluación", breadcrumb: null, content: <ResultadoListContent data={data} /> }));
}

export function ResultadoDetailContent({ data }: { data: ResultadoDetailData }) {
  const label = "form-label small fw-600 text-muted";
  return <>
    <NativeToasts messages={data.messages} />
    <div className="container-fluid py-4">
      <div className="row mb-4"><div className="col-12">
        <div className="d-flex align-items-center gap-2 mb-4">
          <a href={data.urls.list} className="btn btn-light"><i className="bi bi-arrow-left" /></a>
          <div>
            <h1 className="h2 mb-0" style={{ color: "#1f3a93" }}><i className="bi-journal-check me-2" />Resultado</h1>
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
                <div className="col-md-6"><label className={label}>Evaluación</label><br /><p className="mb-0">{data.evaluacion}</p></div>
                <div className="col-md-6"><label className={label}>Tipo</label><br /><span className="badge bg-info bg-opacity-10 text-info">{data.tipo_label}</span></div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4">
                <div className="col-md-6"><label className={label}>Persona</label><br /><p className="mb-0">{data.persona}</p></div>
                <div className="col-md-6"><label className={label}>Comisión</label><br /><p className="mb-0">{data.comision}</p></div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4">
                <div className="col-md-6"><label className={label}>Calificación</label><br /><p className="mb-0">{data.calificacion}</p></div>
                <div className="col-md-6"><label className={label}>Aprobó</label><br />
                  {data.aprobo === null ? <span className="badge bg-light text-muted">—</span>
                    : data.aprobo ? <span className="badge bg-success">Sí</span> : <span className="badge bg-danger">No</span>}</div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4">
                <div className="col-md-6"><label className={label}>Fecha Registro</label><br /><p className="mb-0">{data.fecha_registro}</p></div>
                <div className="col-md-6"><label className={label}>Registrado por</label><br /><p className="mb-0">{data.registrado_por}</p></div>
              </div>
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
  const [state] = useMainResource(`${API}${id}/`, resultadoDetailValid);
  return renderMain(state, "Cargando resultado…", (data) => ({ title: data.titulo, breadcrumb: null, content: <ResultadoDetailContent data={data} /> }));
}

type Params = { id?: string };

// Native URLs of `VAT/urls.py`; `nuevo/`, `<id>/editar/` and `<id>/eliminar/` are `vatResultadosForm.tsx`.
const PATH = /^\/vat\/resultados-evaluacion\/(?:([0-9]+)\/)?$/;

export const vatResultadosRoute: RouteDefinition<Params> = {
  name: "vat-resultados",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { id: m[1] } : null;
  },
  render({ id }) {
    return id ? <DetailPage key={id} id={id} /> : <ListPage />;
  },
};
