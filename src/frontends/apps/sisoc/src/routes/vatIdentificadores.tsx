/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { listUrlsValid, messagesValid, pageValid, VatPagination, VatSearchBar, VatTable, bool, integer, type Message, type Page } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V06.01 identificadores históricos de institución: `institucion/identificador_list.html` and `identificador_detail.html`.
 * Data comes from `/api/web/vat/institucion/identificadores/`, which runs the native views; the forms are `vatIdentificadoresForm.tsx`.
 */
type Row = { id: number; centro: string; tipo: string; valor: string; rol: string; es_actual: boolean; detail_url: string; update_url: string; delete_url: string };
export type IdentificadorListData = {
  results: Row[]; page: Page; busqueda: string; permisos: { editar: boolean; eliminar: boolean }; urls: { list: string; create: string }; messages: Message[];
};
export type IdentificadorDetailData = {
  id: number; title: string; centro: string; tipo: string; valor: string; rol: string; es_actual: boolean; vigencia_hasta: string; motivo: string;
  creado: string; modificado: string; urls: { list: string; update: string; delete: string }; messages: Message[];
};

const API = "web/vat/institucion/identificadores/";
const ACCENT = { color: "#1f3a93" };

const rowValid = (r: unknown) => record(r) && integer(r.id) && ["centro", "tipo", "valor", "rol"].every((k) => text(r[k])) && bool(r.es_actual) &&
  internal(r.detail_url) && internal(r.update_url) && internal(r.delete_url);

export function identificadorListValid(v: unknown): v is IdentificadorListData {
  return record(v) && Array.isArray(v.results) && v.results.every(rowValid) && pageValid(v.page) && text(v.busqueda) &&
    record(v.permisos) && bool(v.permisos.editar) && bool(v.permisos.eliminar) && listUrlsValid(v.urls) && messagesValid(v.messages);
}

export function identificadorDetailValid(v: unknown): v is IdentificadorDetailData {
  return record(v) && integer(v.id) && ["title", "centro", "tipo", "valor", "rol", "vigencia_hasta", "motivo", "creado", "modificado"].every((k) => text(v[k])) &&
    bool(v.es_actual) && record(v.urls) && internal(v.urls.list) && internal(v.urls.update) && internal(v.urls.delete) && messagesValid(v.messages);
}

export function IdentificadorListContent({ data }: { data: IdentificadorListData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <link rel="stylesheet" href="/static/custom/css/vat_design.css" />
    <div className="vat-ui">
      <VatSearchBar title="Buscar Identificador" placeholder="Buscar por centro, tipo o valor" query={data.busqueda} reset={data.urls.list} add={{ url: data.urls.create, text: "Agregar" }} />
      <VatTable
        headers={[{ title: "Centro", sortable: { column: "centro" } }, { title: "Tipo" }, { title: "Valor" }, { title: "Rol" }, { title: "Actual" }, { title: "Acciones", notexport: true }]}
        rows={data.results} columns={6} sortValue={(r) => r.centro}
        empty={{ title: "No se encontraron identificadores", text: "No hay identificadores registrados." }}
        renderRow={(r) => <tr key={r.id}>
          <td data-centro={r.centro}>{r.centro}</td>
          <td>{r.tipo}</td>
          <td>{r.valor}</td>
          <td>{r.rol}</td>
          <td>{r.es_actual ? <span className="badge-validacion validado"><i className="fas fa-check-circle" />{" "}Sí</span> : <span className="badge-validacion no-validado"><i className="fas fa-times-circle" />{" "}No</span>}</td>
          <td><div className="action-buttons" role="group">
            <a href={r.detail_url} className="btn btn-primary link-handler" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
            {data.permisos.editar && <>{" "}<a href={r.update_url} className="btn btn-editar link-handler" title="Editar identificador"><i className="fas fa-edit" />{" "}Editar</a></>}
            {data.permisos.eliminar && <>{" "}<a href={r.delete_url} className="btn btn-eliminar link-handler" title="Eliminar identificador"><i className="fas fa-trash-alt" />{" "}Eliminar</a></>}
          </div></td>
        </tr>}
      />
      <VatPagination page={data.page} shown={data.results.length} />
    </div>
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, identificadorListValid);
  return renderMain(state, "Cargando identificadores…", (data) => ({ title: "Identificadores Históricos", breadcrumb: null, content: <IdentificadorListContent data={data} /> }));
}

const Label = ({ children }: { children: string }) => <label className="form-label small fw-600 text-muted">{children}</label>;

export function IdentificadorDetailContent({ data }: { data: IdentificadorDetailData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <div className="container-fluid py-4">
      <div className="row mb-4"><div className="col-12"><div className="d-flex align-items-center gap-2 mb-4">
        <a href={data.urls.list} className="btn btn-light"><i className="bi bi-arrow-left" /></a>
        <div>
          <h1 className="h2 mb-0" style={ACCENT}><i className="bi-hash me-2" />Identificador</h1>
          <small className="text-muted">{data.title}</small>
        </div>
      </div></div></div>
      <div className="row">
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm mb-4">
            <div className="card-header bg-light border-bottom"><h5 className="mb-0"><i className="bi bi-file-earmark-text me-2" style={ACCENT} />Información</h5></div>
            <div className="card-body p-4">
              <div className="row mb-4">
                <div className="col-md-6"><Label>Centro</Label><br /><p className="mb-0">{data.centro}</p></div>
                <div className="col-md-6"><Label>Tipo</Label><br /><span className="badge bg-info bg-opacity-10 text-info">{data.tipo}</span></div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4">
                <div className="col-md-6"><Label>Valor del Identificador</Label><br /><p className="mb-0">{data.valor}</p></div>
                <div className="col-md-6"><Label>Rol Institucional</Label><br /><p className="mb-0">{data.rol}</p></div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4">
                <div className="col-md-6"><Label>Actual</Label><br />{data.es_actual ? <span className="badge bg-success">Sí</span> : <span className="badge bg-secondary">No</span>}</div>
                <div className="col-md-6"><Label>Vigencia Hasta</Label><br /><p className="mb-0">{data.vigencia_hasta}</p></div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4"><div className="col-md-12"><Label>Motivo del Cambio</Label><br /><p className="mb-0">{data.motivo}</p></div></div>
            </div>
          </div>
          <div className="card border-0 shadow-sm">
            <div className="card-header bg-light border-bottom"><h5 className="mb-0"><i className="bi bi-clock-history me-2" style={ACCENT} />Auditoría</h5></div>
            <div className="card-body p-4"><div className="small text-muted"><dl>
              <dt>Creado</dt><dd>{data.creado}</dd>
              <dt>Modificado</dt><dd>{data.modificado}</dd>
            </dl></div></div>
          </div>
        </div>
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm mb-4 bg-primary bg-opacity-10"><div className="card-body">
            <h6 className="card-title fw-600" style={ACCENT}><i className="bi bi-lightning me-2" />Acciones</h6>
            <div className="d-grid gap-2">
              <a href={data.urls.update} className="btn btn-primary"><i className="bi bi-pencil me-2" />Editar</a>
              <a href={data.urls.delete} className="btn btn-danger"><i className="bi bi-trash me-2" />Eliminar</a>
            </div>
          </div></div>
          <div className="card border-0 shadow-sm bg-light"><div className="card-body">
            <h6 className="card-title fw-600" style={ACCENT}><i className="bi bi-info-circle me-2" />Registro</h6>
            <div className="small text-muted"><dl><dt>ID</dt><dd>#{data.id}</dd></dl></div>
          </div></div>
        </div>
      </div>
    </div>
    <style>{".fw-600 { font-weight: 600 !important; }"}</style>
  </>;
}

function DetailPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/`, identificadorDetailValid);
  return renderMain(state, "Cargando identificador…", (data) => ({ title: data.title, breadcrumb: null, content: <IdentificadorDetailContent data={data} /> }));
}

type Params = { id?: string };

// Native URLs of `VAT/urls.py`; `nuevo/`, `<id>/editar/` and `<id>/eliminar/` are `vatIdentificadoresForm.tsx`.
const PATH = /^\/vat\/institucion\/identificadores\/(?:([0-9]+)\/)?$/;

export const vatIdentificadoresRoute: RouteDefinition<Params> = {
  name: "vat-identificadores",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { id: m[1] } : null;
  },
  render({ id }) {
    return id ? <DetailPage key={id} id={id} /> : <ListPage />;
  },
};
