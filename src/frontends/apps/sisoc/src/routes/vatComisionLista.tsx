/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { integer, listUrlsValid, messagesValid, pageValid, bool, VatPagination, VatSearchBar, VatTable, type Message, type Page } from "./vatShared";
import { TourHelp } from "./vatTour";
import type { RouteDefinition } from "./types";

/**
 * V04.01 commission list: `oferta_institucional/comision_list.html`. Data comes from `/api/web/vat/comisiones-lista/`, which
 * runs the native `ComisionListView` (scope, `busqueda`, `estado` and `oferta_id` filters, paging); the detail is
 * `vatComisionDetalle.tsx` and the forms are `vatComisionForm.tsx`.
 */
type Row = {
  id: number; codigo: string; nombre: string; oferta: string; fecha_inicio: string; fecha_fin: string; cupo: string; estado: string; estado_label: string;
  detail_url: string; update_url: string; delete_url: string;
};
export type ComisionListaData = {
  results: Row[]; page: Page; busqueda: string; permisos: { editar: boolean; eliminar: boolean }; urls: { list: string; create: string }; messages: Message[];
};

const API = "web/vat/comisiones-lista/";

const rowValid = (r: unknown) => record(r) && integer(r.id) && ["codigo", "nombre", "oferta", "fecha_inicio", "fecha_fin", "cupo", "estado", "estado_label"].every((k) => text(r[k])) &&
  internal(r.detail_url) && internal(r.update_url) && internal(r.delete_url);

export const comisionListaValid = (v: unknown): v is ComisionListaData => record(v) && Array.isArray(v.results) && v.results.every(rowValid) &&
  pageValid(v.page) && text(v.busqueda) && record(v.permisos) && bool(v.permisos.editar) && bool(v.permisos.eliminar) && listUrlsValid(v.urls) && messagesValid(v.messages);

/** The status badge of `comision_list.html`: one look per state, the rest is the pending one. */
function EstadoBadge({ estado, label }: { estado: string; label: string }) {
  if (estado === "activa") return <span className="badge-validacion validado"><i className="fas fa-check-circle" />{" "}{label}</span>;
  if (estado === "cancelada") return <span className="badge-validacion no-validado"><i className="fas fa-times-circle" />{" "}{label}</span>;
  if (estado === "finalizada") return <span className="badge-validacion" style={{ background: "#4b5563", color: "#e5e7eb", borderColor: "#6b7280" }}><i className="fas fa-flag-checkered" />{" "}{label}</span>;
  return <span className="badge-validacion pendiente"><i className="fas fa-clock" />{" "}{label}</span>;
}

export function ComisionListaContent({ data }: { data: ComisionListaData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <VatSearchBar title="Buscar Comisión" placeholder="Buscar por código, nombre u oferta" query={data.busqueda} reset={data.urls.list} add={{ url: data.urls.create, text: "Agregar" }} />
    <VatTable
      headers={[{ title: "Código", sortable: { column: "codigo" } }, { title: "Nombre", sortable: { column: "nombre" } }, { title: "Oferta" }, { title: "Fecha Inicio" }, { title: "Fecha Fin" },
        { title: "Cupo" }, { title: "Estado" }, { title: "Acciones", notexport: true }]}
      rows={data.results} columns={8} sortValue={(r, column) => (column === "nombre" ? r.nombre : r.codigo)}
      empty={{ title: "No se encontraron comisiones", text: "No hay comisiones que coincidan con los criterios de búsqueda." }}
      renderRow={(c) => <tr key={c.id}>
        <td data-codigo={c.codigo}><a href={c.detail_url} className="link-handler" title="Ver detalles">{c.codigo}</a></td>
        <td data-nombre={c.nombre}>{c.nombre || "—"}</td>
        <td>{c.oferta}</td>
        <td>{c.fecha_inicio}</td>
        <td>{c.fecha_fin}</td>
        <td>{c.cupo}</td>
        <td><EstadoBadge estado={c.estado} label={c.estado_label} /></td>
        <td><div className="action-buttons" role="group">
          <a href={c.detail_url} className="btn btn-primary link-handler" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
          {data.permisos.editar && <>{" "}<a href={c.update_url} className="btn btn-editar link-handler" title="Editar comisión"><i className="fas fa-edit" />{" "}Editar</a></>}
          {data.permisos.eliminar && <>{" "}<a href={c.delete_url} className="btn btn-eliminar link-handler" title="Eliminar comisión"><i className="fas fa-trash-alt" />{" "}Eliminar</a></>}
        </div></td>
      </tr>}
    />
    <VatPagination page={data.page} shown={data.results.length} />
    <TourHelp section="comision_list" />
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, comisionListaValid);
  return renderMain(state, "Cargando comisiones…", (data) => ({ title: "Comisiones", breadcrumb: null, content: <ComisionListaContent data={data} /> }));
}

// Native URL of `VAT/urls.py`: the list only (`<id>/` is the detail, `horarios/` the schedule list, `nueva/` the form).
const PATH = /^\/vat\/comisiones\/$/;

export const vatComisionListaRoute: RouteDefinition<Record<string, never>> = {
  name: "vat-comision-lista",
  match: (pathname) => (PATH.test(pathname) ? {} : null),
  render: () => <ListPage />,
};
