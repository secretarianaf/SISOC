/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { bool, integer, listUrlsValid, messagesValid, pageValid, VatPagination, VatSearchBar, VatTable, type Message, type Page } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V04.01 commission schedules: `oferta_institucional/horario_list.html` and `horario_detail.html`. Data comes from
 * `/api/web/vat/comisiones-horarios/`, which runs the native views; the forms and the delete confirmations live in
 * `vatComisionHorarioForm.tsx`. The detail draws «Editar» and «Eliminar» for everyone (the native template has no permission check); its
 * «Observaciones» block never renders natively (`ComisionHorario` has no such field), so it is not drawn.
 */
type Row = {
  id: number; comision: string; dia: string; desde: string; hasta: string; aula: string; vigente: boolean; detail_url: string; update_url: string; delete_url: string;
};
export type HorarioListData = {
  results: Row[]; page: Page; busqueda: string; permisos: { editar: boolean; eliminar: boolean }; urls: { list: string; create: string }; messages: Message[];
};
export type HorarioDetailData = {
  id: number; title: string; comision: string; dia: string; aula: string; desde: string; hasta: string; vigente: boolean;
  creado: string; modificado: string; urls: { list: string; update: string; delete: string }; messages: Message[];
};

const API = "web/vat/comisiones-horarios/";
const ACCENT = { color: "#1f3a93" };

const rowValid = (r: unknown) => record(r) && integer(r.id) && ["comision", "dia", "desde", "hasta", "aula"].every((k) => text(r[k])) && bool(r.vigente) &&
  internal(r.detail_url) && internal(r.update_url) && internal(r.delete_url);

export const horarioListValid = (v: unknown): v is HorarioListData => record(v) && Array.isArray(v.results) && v.results.every(rowValid) &&
  pageValid(v.page) && text(v.busqueda) && record(v.permisos) && bool(v.permisos.editar) && bool(v.permisos.eliminar) && listUrlsValid(v.urls) && messagesValid(v.messages);

export const horarioDetailValid = (v: unknown): v is HorarioDetailData => record(v) && integer(v.id) &&
  ["title", "comision", "dia", "aula", "desde", "hasta", "creado", "modificado"].every((k) => text(v[k])) && bool(v.vigente) &&
  record(v.urls) && internal(v.urls.list) && internal(v.urls.update) && internal(v.urls.delete) && messagesValid(v.messages);

export function HorarioListContent({ data }: { data: HorarioListData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
    <VatSearchBar title="Buscar Horario" placeholder="Buscar por comisión o día" query={data.busqueda} reset={data.urls.list} add={{ url: data.urls.create, text: "Agregar" }} />
    <VatTable
      headers={[{ title: "Comisión", sortable: { column: "comision" } }, { title: "Día" }, { title: "Desde" }, { title: "Hasta" }, { title: "Aula" }, { title: "Vigente" }, { title: "Acciones", notexport: true }]}
      rows={data.results} columns={7} sortValue={(r) => r.comision}
      empty={{ title: "No se encontraron horarios", text: "No hay horarios que coincidan con los criterios de búsqueda." }}
      renderRow={(h) => <tr key={h.id}>
        <td data-comision={h.comision}>{h.comision}</td>
        <td>{h.dia}</td>
        <td>{h.desde}</td>
        <td>{h.hasta}</td>
        <td>{h.aula}</td>
        <td>{h.vigente
          ? <span className="badge-validacion validado"><i className="fas fa-check-circle" />{" "}Sí</span>
          : <span className="badge-validacion no-validado"><i className="fas fa-times-circle" />{" "}No</span>}</td>
        <td><div className="action-buttons" role="group">
          <a href={h.detail_url} className="btn btn-primary link-handler" title="Ver detalle"><i className="fas fa-eye" />{" "}Ver</a>
          {data.permisos.editar && <>{" "}<a href={h.update_url} className="btn btn-editar link-handler" title="Editar horario"><i className="fas fa-edit" />{" "}Editar</a></>}
          {data.permisos.eliminar && <>{" "}<a href={h.delete_url} className="btn btn-eliminar link-handler" title="Eliminar horario"><i className="fas fa-trash-alt" />{" "}Eliminar</a></>}
        </div></td>
      </tr>}
    />
    <VatPagination page={data.page} shown={data.results.length} />
  </>;
}

function ListPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, horarioListValid);
  return renderMain(state, "Cargando horarios…", (data) => ({ title: "Horarios de Comisión", breadcrumb: null, content: <HorarioListContent data={data} /> }));
}

const Label = ({ children }: { children: string }) => <><label className="form-label small fw-600 text-muted">{children}</label><br /></>;

export function HorarioDetailContent({ data }: { data: HorarioDetailData }) {
  return <>
    <NativeToasts messages={data.messages} />
    <div className="container-fluid py-4">
      <div className="row mb-4"><div className="col-12"><div className="d-flex align-items-center gap-2 mb-4">
        <a href={data.urls.list} className="btn btn-light"><i className="bi bi-arrow-left" /></a>
        <div>
          <h1 className="h2 mb-0" style={ACCENT}><i className="bi-clock me-2" />Horario</h1>
          <small className="text-muted">{data.title}</small>
        </div>
      </div></div></div>
      <div className="row">
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm mb-4">
            <div className="card-header bg-light border-bottom"><h5 className="mb-0"><i className="bi bi-file-earmark-text me-2" style={ACCENT} />Información</h5></div>
            <div className="card-body p-4">
              <div className="row mb-4"><div className="col-md-12"><Label>Comisión</Label><p className="mb-0">{data.comision}</p></div></div>
              <hr className="my-4" />
              <div className="row mb-4">
                <div className="col-md-6"><Label>Día de la Semana</Label><p className="mb-0">{data.dia}</p></div>
                <div className="col-md-6"><Label>Aula/Espacio</Label><p className="mb-0">{data.aula}</p></div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4">
                <div className="col-md-6"><Label>Hora Desde</Label><p className="mb-0">{data.desde}</p></div>
                <div className="col-md-6"><Label>Hora Hasta</Label><p className="mb-0">{data.hasta}</p></div>
              </div>
              <hr className="my-4" />
              <div className="row mb-4"><div className="col-md-12"><Label>Vigente</Label>{data.vigente ? <span className="badge bg-success">Sí</span> : <span className="badge bg-secondary">No</span>}</div></div>
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
  const [state] = useMainResource(`${API}${id}/`, horarioDetailValid);
  return renderMain(state, "Cargando horario…", (data) => ({ title: data.title, breadcrumb: null, content: <HorarioDetailContent data={data} /> }));
}

type Params = { id?: string };

// Native URLs of `VAT/urls.py`; `nuevo/`, `<id>/editar/` and `<id>/eliminar/` are `vatComisionHorarioForm.tsx`.
const PATH = /^\/vat\/comisiones\/horarios\/(?:([0-9]+)\/)?$/;

export const vatComisionHorariosRoute: RouteDefinition<Params> = {
  name: "vat-comision-horarios",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { id: m[1] } : null;
  },
  render({ id }) {
    return id ? <DetailPage key={id} id={id} /> : <ListPage />;
  },
};
