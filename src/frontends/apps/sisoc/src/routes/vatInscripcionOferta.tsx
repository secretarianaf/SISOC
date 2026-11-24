/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { bool, integer, listUrlsValid, messagesValid, pageValid, VatPagination, VatSearchBar, VatTable, type Message, type Page } from "./vatShared";
import { TourHelp } from "./vatTour";
import type { RouteDefinition } from "./types";

/**
 * V03.01 inscripciones a comisiones de oferta: `vat/inscripcion_oferta/list.html` and `detail.html`. Data comes from
 * `/api/web/vat/inscripciones-oferta/`, which runs the native views; the form and the delete confirmation live in
 * `vatInscripcionOfertaForm.tsx`.
 */
type Row = {
  id: number; ciudadano: string; documento: string; oferta: string; centro: string; estado: string; estado_label: string; fecha: string;
  detail_url: string; update_url: string; delete_url: string;
};
type Permisos = { editar: boolean; eliminar: boolean };
export type InscripcionOfertaListData = { results: Row[]; page: Page; busqueda: string; permisos: Permisos; urls: { list: string; create: string }; messages: Message[] };
export type InscripcionOfertaDetailData = {
  id: number; ciudadano: string; documento: string; oferta: string; centro: string; estado: string; estado_label: string; periodo: string; horario: string;
  dias: string[]; costo: string; inscrito_por: string; fecha_inscripcion: string; fecha_modificacion: string; permisos: Permisos;
  urls: { list: string; update: string; delete: string }; messages: Message[];
};

const API = "web/vat/inscripciones-oferta/";
const permisosValid = (p: unknown) => record(p) && bool(p.editar) && bool(p.eliminar);

const rowValid = (r: unknown) => record(r) && integer(r.id) && ["ciudadano", "documento", "oferta", "centro", "estado", "estado_label", "fecha"].every((k) => text(r[k])) &&
  internal(r.detail_url) && internal(r.update_url) && internal(r.delete_url);

export const inscripcionOfertaListValid = (v: unknown): v is InscripcionOfertaListData => record(v) && Array.isArray(v.results) && v.results.every(rowValid) &&
  pageValid(v.page) && text(v.busqueda) && permisosValid(v.permisos) && listUrlsValid(v.urls) && messagesValid(v.messages);

export const inscripcionOfertaDetailValid = (v: unknown): v is InscripcionOfertaDetailData => record(v) && integer(v.id) &&
  ["ciudadano", "documento", "oferta", "centro", "estado", "estado_label", "periodo", "horario", "costo", "inscrito_por", "fecha_inscripcion", "fecha_modificacion"].every((k) => text(v[k])) &&
  Array.isArray(v.dias) && v.dias.every(text) && permisosValid(v.permisos) && record(v.urls) && internal(v.urls.list) && internal(v.urls.update) && internal(v.urls.delete) &&
  messagesValid(v.messages);

/** The status badge of `list.html`. */
function EstadoBadge({ estado, label }: { estado: string; label: string }) {
  if (estado === "inscrito") return <span className="badge-validacion validado"><i className="fas fa-check-circle" />{" "}{label}</span>;
  if (estado === "completado") return <span className="badge-validacion" style={{ background: "#4b5563", color: "#e5e7eb", borderColor: "#6b7280" }}><i className="fas fa-flag-checkered" />{" "}{label}</span>;
  if (estado === "abandonado") return <span className="badge-validacion no-validado"><i className="fas fa-times-circle" />{" "}{label}</span>;
  return <span className="badge-validacion pendiente"><i className="fas fa-clock" />{" "}{label}</span>;
}

export function InscripcionOfertaListContent({ data }: { data: InscripcionOfertaListData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <VatSearchBar title="Buscar Inscripción a Oferta" placeholder="Buscar por ciudadano, documento u oferta" query={data.busqueda} reset={data.urls.list} add={{ url: data.urls.create, text: "Agregar" }} />
    <VatTable
      headers={[{ title: "Ciudadano", sortable: { column: "ciudadano" } }, { title: "Documento" }, { title: "Oferta" }, { title: "Centro" }, { title: "Estado" }, { title: "Fecha Inscripción" }, { title: "Acciones", notexport: true }]}
      rows={data.results} columns={7} sortValue={(r) => r.ciudadano}
      empty={{ title: "No se encontraron inscripciones", text: "No hay inscripciones a ofertas registradas." }}
      renderRow={(i) => <tr key={i.id}>
        <td data-ciudadano={i.ciudadano}>{i.ciudadano}</td>
        <td>{i.documento}</td>
        <td>{i.oferta}</td>
        <td>{i.centro}</td>
        <td><EstadoBadge estado={i.estado} label={i.estado_label} /></td>
        <td>{i.fecha}</td>
        <td><div className="action-buttons" role="group">
          <a href={i.detail_url} className="btn btn-primary link-handler" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
          {data.permisos.editar && <>{" "}<a href={i.update_url} className="btn btn-editar link-handler" title="Editar inscripción"><i className="fas fa-edit" />{" "}Editar</a></>}
          {data.permisos.eliminar && <>{" "}<a href={i.delete_url} className="btn btn-eliminar link-handler" title="Eliminar inscripción"><i className="fas fa-trash-alt" />{" "}Eliminar</a></>}
        </div></td>
      </tr>}
    />
    <VatPagination page={data.page} shown={data.results.length} />
    <TourHelp section="inscripcion_oferta_list" />
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, inscripcionOfertaListValid);
  return renderMain(state, "Cargando inscripciones…", (data) => ({ title: "Inscripciones a Ofertas", breadcrumb: null, content: <InscripcionOfertaListContent data={data} /> }));
}

const BADGE: Record<string, string> = { inscrito: "bg-success", lista_espera: "bg-warning", completado: "bg-info", abandonado: "bg-secondary" };

export function InscripcionOfertaDetailContent({ data }: { data: InscripcionOfertaDetailData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <div className="container-fluid py-4">
      <div className="row mb-4">
        <div className="col-md-8">
          <h1 className="h3 text-dark">{data.ciudadano}</h1>
          <p className="text-muted">{data.oferta}</p>
        </div>
        <div className="col-md-4 text-end">
          {data.permisos.editar && <a href={data.urls.update} className="btn btn-warning"><i className="fas fa-edit" />{" "}Editar</a>}
        </div>
      </div>
      <div className="row">
        <div className="col-md-8">
          <div className="card mb-4">
            <div className="card-header bg-light"><h5 className="mb-0">Información de la Inscripción</h5></div>
            <div className="card-body">
              <div className="row mb-3">
                <div className="col-md-6"><strong>Ciudadano:</strong><br />{data.ciudadano}<br /><small className="text-muted">{data.documento}</small></div>
                <div className="col-md-6"><strong>Oferta Formativa:</strong><br />{data.oferta}<br /><small className="text-muted">{data.centro}</small></div>
              </div>
              <div className="row mb-3">
                <div className="col-md-6"><strong>Estado:</strong><br /><span className={`badge ${BADGE[data.estado] ?? "bg-danger"}`}>{data.estado_label}</span></div>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="card-header bg-light"><h5 className="mb-0">Detalles de la Oferta</h5></div>
            <div className="card-body">
              <div className="row mb-3">
                <div className="col-md-6"><strong>Período:</strong><br />{data.periodo}</div>
                <div className="col-md-6"><strong>Horario:</strong><br />{data.horario}</div>
              </div>
              <div className="row mb-3">
                <div className="col-md-6"><strong>Días:</strong><br />{data.dias.map((d, n) => <span key={n} className="badge bg-info">{d}</span>)}</div>
                <div className="col-md-6"><strong>Centro:</strong><br />{data.centro}</div>
              </div>
              {data.costo && <div className="row"><div className="col-md-6"><strong>Costo:</strong><br />{data.costo}</div></div>}
            </div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="card">
            <div className="card-header bg-light"><h5 className="mb-0">Detalles de Auditoría</h5></div>
            <div className="card-body small">
              <div className="mb-3"><strong>Inscrito por:</strong><br />{data.inscrito_por}</div>
              <div className="mb-3"><strong>Fecha de Inscripción:</strong><br />{data.fecha_inscripcion}</div>
              <div><strong>Última Modificación:</strong><br />{data.fecha_modificacion}</div>
            </div>
          </div>
          {data.permisos.eliminar && <div className="card mt-3 border-danger">
            <div className="card-header bg-danger text-white"><h5 className="mb-0">Peligro</h5></div>
            <div className="card-body"><a href={data.urls.delete} className="btn btn-danger btn-sm w-100"><i className="fas fa-trash" />{" "}Eliminar Inscripción</a></div>
          </div>}
        </div>
      </div>
    </div>
  </>;
}

function DetailPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/`, inscripcionOfertaDetailValid);
  return renderMain(state, "Cargando inscripción…", (data) => ({ title: `Inscripción - ${data.ciudadano} - VAT`, breadcrumb: null, content: <InscripcionOfertaDetailContent data={data} /> }));
}

type Params = { id?: string };

// Native URLs of `VAT/urls.py`; `nueva/`, `<id>/editar/` and `<id>/eliminar/` belong to the form module.
const PATH = /^\/vat\/inscripciones-oferta\/(?:([0-9]+)\/)?$/;

export const vatInscripcionOfertaRoute: RouteDefinition<Params> = {
  name: "vat-inscripcion-oferta",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { id: m[1] } : null;
  },
  render({ id }) {
    return id ? <DetailPage key={id} id={id} /> : <ListPage />;
  },
};
