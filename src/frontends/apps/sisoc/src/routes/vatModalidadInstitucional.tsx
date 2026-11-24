/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { listUrlsValid, messagesValid, pageValid, VatPagination, VatSearchBar, VatTable, bool, integer, type Message, type Page } from "./vatShared";
import { CsrfInput, useForbidden } from "./vatFormShared";
import { UncertainNotice, usePostDelete, vatBreadcrumb } from "./vatCentrosListaShared";
import type { RouteDefinition } from "./types";

/**
 * V06.01 modalidades institucionales: `modalidad_institucional/list.html` and `detail.html`. Data comes
 * from `/api/web/vat/modalidades-institucionales/`, which runs the native views; the forms are
 * `vatModalidadInstitucionalForm.tsx`.
 */
type Row = { id: number; nombre: string; descripcion: string; activo: boolean; creado: string; detail_url: string; update_url: string; delete_url: string };
export type ModalidadListData = {
  results: Row[]; page: Page; busqueda: string; permisos: { editar: boolean; eliminar: boolean }; urls: { list: string; create: string }; messages: Message[];
};
export type ModalidadDetailData = {
  id: number; nombre: string; descripcion: string; activo: boolean; creado: string; modificado: string;
  urls: { list: string; update: string; delete: string }; messages: Message[];
};

const API = "web/vat/modalidades-institucionales/";

const rowValid = (r: unknown) => record(r) && integer(r.id) && ["nombre", "descripcion", "creado"].every((k) => text(r[k])) && bool(r.activo) &&
  internal(r.detail_url) && internal(r.update_url) && internal(r.delete_url);

export function modalidadListValid(v: unknown): v is ModalidadListData {
  return record(v) && Array.isArray(v.results) && v.results.every(rowValid) && pageValid(v.page) && text(v.busqueda) &&
    record(v.permisos) && bool(v.permisos.editar) && bool(v.permisos.eliminar) && listUrlsValid(v.urls) && messagesValid(v.messages);
}

export function modalidadDetailValid(v: unknown): v is ModalidadDetailData {
  return record(v) && integer(v.id) && ["nombre", "descripcion", "creado", "modificado"].every((k) => text(v[k])) && bool(v.activo) &&
    record(v.urls) && internal(v.urls.list) && internal(v.urls.update) && internal(v.urls.delete) && messagesValid(v.messages);
}

export function ModalidadListContent({ data }: { data: ModalidadListData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <VatSearchBar title="Buscar Modalidad Institucional" placeholder="Buscar por nombre o descripción" query={data.busqueda} reset={data.urls.list} add={{ url: data.urls.create, text: "Agregar" }} />
    <VatTable
      headers={[{ title: "Nombre", sortable: { column: "nombre" } }, { title: "Descripción" }, { title: "Estado" }, { title: "Creado" }, { title: "Acciones", notexport: true }]}
      rows={data.results} columns={5} sortValue={(r) => r.nombre}
      empty={{ title: "No se encontraron modalidades institucionales", text: "No hay modalidades registradas." }}
      renderRow={(r) => <tr key={r.id}>
        <td data-nombre={r.nombre}><a href={r.detail_url} className="link-handler" title="Ver detalles">{r.nombre}</a></td>
        <td>{r.descripcion}</td>
        <td>{r.activo ? <span className="badge-validacion validado"><i className="fas fa-check-circle" />{" "}Activo</span>
          : <span className="badge-validacion no-validado"><i className="fas fa-times-circle" />{" "}Inactivo</span>}</td>
        <td>{r.creado}</td>
        <td><div className="action-buttons" role="group">
          <a href={r.detail_url} className="btn btn-primary link-handler" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
          {data.permisos.editar && <>{" "}<a href={r.update_url} className="btn btn-editar link-handler" title="Editar modalidad"><i className="fas fa-edit" />{" "}Editar</a></>}
          {data.permisos.eliminar && <>{" "}<a href={r.delete_url} className="btn btn-eliminar link-handler" title="Eliminar modalidad"><i className="fas fa-trash-alt" />{" "}Eliminar</a></>}
        </div></td>
      </tr>}
    />
    <VatPagination page={data.page} shown={data.results.length} />
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, modalidadListValid);
  return renderMain(state, "Cargando modalidades…", (data) => ({ title: "Modalidades Institucionales", breadcrumb: null, content: <ModalidadListContent data={data} /> }));
}

/** `detail.html`: the delete is the native inline POST form guarded by `confirm()`. */
function DeleteButton({ endpoint, forbidden }: { endpoint: string; forbidden: (d: unknown) => void }) {
  const { uncertain, submit } = usePostDelete(endpoint, forbidden, "¿Está seguro de que desea eliminar esta modalidad?");
  return <form method="post" style={{ display: "inline" }} onSubmit={submit}>
    <CsrfInput />
    <UncertainNotice show={uncertain} />
    <button type="submit" className="btn btn-sm btn-danger"><i className="fas fa-trash" />{" "}Eliminar</button>
  </form>;
}

export function ModalidadDetailContent({ data, forbidden }: { data: ModalidadDetailData; forbidden: (d: unknown) => void }) {
  return <>
    <NativeToasts messages={data.messages} />
    <div className="row"><div className="col-md-8"><div className="card">
      <div className="card-header bg-primary text-white">
        <h3 className="card-title">{data.nombre}</h3>
        <div className="card-tools">
          <a href={data.urls.update} className="btn btn-sm btn-warning"><i className="fas fa-edit" />{" "}Editar</a>{" "}
          <DeleteButton endpoint={`${API}${data.id}/eliminar/`} forbidden={forbidden} />
        </div>
      </div>
      <div className="card-body">
        <div className="form-group"><label>Nombre:</label><p>{data.nombre}</p></div>
        <div className="form-group"><label>Descripción:</label><p>{data.descripcion ? data.descripcion : <em className="text-muted">Sin descripción</em>}</p></div>
        <div className="form-group"><label>Estado:</label><p>{data.activo ? <span className="badge badge-success">Activo</span> : <span className="badge badge-danger">Inactivo</span>}</p></div>
        <div className="form-group"><label>Creado:</label><p>{data.creado}</p></div>
        <div className="form-group"><label>Última modificación:</label><p>{data.modificado}</p></div>
      </div>
    </div></div></div>
  </>;
}

export const modalidadBreadcrumb = (last: string) => vatBreadcrumb([
  { text: "VAT", url: "/vat/centros/" }, { text: "Modalidades Institucionales", url: "/vat/modalidades-institucionales/" }, { text: last, url: null },
]);

function DetailPage({ id }: { id: string }) {
  const [state, setState] = useMainResource(`${API}${id}/`, modalidadDetailValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando modalidad…", (data) => ({
    title: "VAT - Detalle de Modalidad Institucional", breadcrumb: modalidadBreadcrumb(data.nombre),
    content: <ModalidadDetailContent data={data} forbidden={forbidden} />,
  }));
}

type Params = { id?: string };

// Native URLs of `VAT/urls.py`; `nueva/`, `<id>/editar/` and `<id>/eliminar/` are `vatModalidadInstitucionalForm.tsx`.
const PATH = /^\/vat\/modalidades-institucionales\/(?:([0-9]+)\/)?$/;

export const vatModalidadInstitucionalRoute: RouteDefinition<Params> = {
  name: "vat-modalidad-institucional",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { id: m[1] } : null;
  },
  render({ id }) {
    return id ? <DetailPage key={id} id={id} /> : <ListPage />;
  },
};
