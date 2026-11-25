/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeModal, NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import { IntervencionBajaPage } from "./comedorIntervencionesBaja";
import { IntervencionFormPage } from "./comedorIntervencionesForm";
import type { RouteDefinition } from "./types";

/**
 * CO02 comedor interventions: `intervencion_detail.html` (list with filters),
 * `intervencion_detail_view.html` (one intervention and its file removal).
 * Data comes from `/api/web/comedores/intervenciones/`, which runs the native
 * views; dates arrive localized and a missing catalog value arrives as "None",
 * like the template prints it.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Comedor = { id: number; nombre: string; url: string };
type Fila = {
  id: number; fecha: string; tipo_intervencion: string; subintervencion: string; destinatario: string; forma_contacto: string;
  tiene_documentacion: boolean; url: string; url_eliminar: string | null;
};
type Opcion = { id: number; nombre: string };
export type IntervencionesListData = {
  comedor: Comedor; admision_id: number | null; admisiones: { id: number; convenio: string | null; activa: boolean }[];
  filtros: { fecha: string; tipo_intervencion: string; destinatario: string }; tipos_intervencion: Opcion[]; destinatarios: Opcion[];
  results: Fila[]; urls: { agregar: string; volver: string }; messages: Message[];
};
export type IntervencionDetailData = {
  id: number; fecha: string; tipo_intervencion: string; subintervencion: string; forma_contacto: string; observaciones: string;
  documentacion: { name: string; url: string } | null; puede_eliminar_archivo: boolean; messages: Message[];
};

const API = "web/comedores/intervenciones/";
const LEVELS = ["success", "error", "warning", "info"];
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const bool = (v: unknown): v is boolean => typeof v === "boolean";
const messagesValid = (v: unknown) => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
const opciones = (v: unknown) => Array.isArray(v) && v.every((o) => record(o) && integer(o.id) && text(o.nombre));

export function listValid(v: unknown): v is IntervencionesListData {
  if (!record(v) || !record(v.comedor) || !record(v.filtros) || !record(v.urls)) return false;
  return integer(v.comedor.id) && text(v.comedor.nombre) && internal(v.comedor.url) &&
    (v.admision_id === null || integer(v.admision_id)) &&
    Array.isArray(v.admisiones) && v.admisiones.every((a) => record(a) && integer(a.id) && (a.convenio === null || text(a.convenio)) && bool(a.activa)) &&
    text(v.filtros.fecha) && text(v.filtros.tipo_intervencion) && text(v.filtros.destinatario) &&
    opciones(v.tipos_intervencion) && opciones(v.destinatarios) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && integer(r.id) && text(r.fecha) && text(r.tipo_intervencion) && text(r.subintervencion) &&
      text(r.destinatario) && text(r.forma_contacto) && bool(r.tiene_documentacion) && internal(r.url) && (r.url_eliminar === null || internal(r.url_eliminar))) &&
    internal(v.urls.agregar) && internal(v.urls.volver) && messagesValid(v.messages);
}

export function detailValid(v: unknown): v is IntervencionDetailData {
  return record(v) && integer(v.id) && text(v.fecha) && text(v.tipo_intervencion) && text(v.subintervencion) && text(v.forma_contacto) &&
    text(v.observaciones) && (v.documentacion === null || (record(v.documentacion) && text(v.documentacion.name) && text(v.documentacion.url))) &&
    bool(v.puede_eliminar_archivo) && messagesValid(v.messages);
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const intervencionesNavigation = { assign: (to: string) => window.location.assign(to) };

function Breadcrumb({ comedor }: { comedor: Comedor }) {
  return <ol className="breadcrumb float-sm-right">
    <li className="breadcrumb-item"><a href={comedor.url} title="Ver Comedor">{comedor.nombre}</a></li>
    <li className="breadcrumb-item active">Intervenciones</li>
  </ol>;
}

function resetFilters(event: FormEvent | React.MouseEvent) {
  const form = (event.currentTarget as HTMLElement).closest("form") as HTMLFormElement;
  form.reset();
  const admision = form.querySelector<HTMLInputElement>('input[name="admision_id"]');
  window.location.href = admision ? `${window.location.pathname}?admision_id=${admision.value}` : window.location.pathname;
}

export function IntervencionesList({ data }: { data: IntervencionesListData }) {
  const { admision_id: admisionId, filtros } = data;
  return <>
    <NativeToasts messages={data.messages} />
    {data.admisiones.length > 0 && (
      <div className="row mb-2">
        <div className="col-12">
          <div className="card card-outline card-secondary">
            <div className="card-header d-flex align-items-center gap-3">
              <span className="fw-bold"><i className="fas fa-file-contract me-1" />Convenio:</span>
              {data.admisiones.map((adm) => (
                <a key={adm.id} href={`?admision_id=${adm.id}`} className={`btn btn-sm ${adm.id === admisionId ? "btn-primary" : "btn-outline-secondary"}`}>
                  {adm.convenio ? adm.convenio : `Admisión #${adm.id}`}
                  {!adm.activa && <>{" "}<span className="badge bg-secondary ms-1">Cerrada</span></>}
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    )}
    <div className="row">
      <div className="col-12 my-3 mx-2 d-print-none">
        <a href={`${data.urls.agregar}${admisionId ? `?admision_id=${admisionId}` : ""}`} className="btn btn-primary mr-1">Agregar Intervención</a>
      </div>
    </div>
    <div className="row mb-4">
      <div className="col-12">
        <form method="get" className="row g-3 align-items-center" id="filtros-form">
          {admisionId && <input type="hidden" name="admision_id" value={admisionId} />}
          <div className="col-md-3">
            <input type="date" name="fecha" className="form-control" placeholder="Fecha" defaultValue={filtros.fecha} />
          </div>
          <div className="col-md-3">
            <select name="tipo_intervencion" className="form-select" defaultValue={filtros.tipo_intervencion}>
              <option value="">Tipo de Intervención</option>
              {data.tipos_intervencion.map((tipo) => <option key={tipo.id} value={tipo.id}>{tipo.nombre}</option>)}
            </select>
          </div>
          <div className="col-md-3">
            <select name="destinatario" className="form-select" defaultValue={filtros.destinatario}>
              <option value="">Destinatario</option>
              {data.destinatarios.map((tipo) => <option key={tipo.id} value={tipo.id}>{tipo.nombre}</option>)}
            </select>
          </div>
          <div className="col-md-2 text-end">
            <button type="submit" className="btn btn-primary w-100">Filtrar</button>
          </div>
          <div className="col-md-1 text-end">
            <button type="button" onClick={resetFilters} className="btn btn-secondary w-100">Limpiar</button>
          </div>
        </form>
      </div>
    </div>
    <div className="row">
      <div className="col-12">
        <div className="card card-primary card-outline">
          <div className="card-header"><h3 className="card-title">Historial de Intervenciones</h3></div>
          <div className="card-body table-responsive">
            {data.results.length > 0 ? (
              <table className="table table-bordered">
                <thead>
                  <tr>
                    <th>Fecha</th><th>Tipo de Intervención</th><th>Subtipo de Intervención</th><th>Destinatario</th>
                    <th>Forma de Contacto</th><th>Documentación Adjunta</th><th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((fila) => (
                    <tr key={fila.id}>
                      <td>{fila.fecha}</td>
                      <td>{fila.tipo_intervencion}</td>
                      <td>{fila.subintervencion}</td>
                      <td>{fila.destinatario}</td>
                      <td>{fila.forma_contacto}</td>
                      <td>{fila.tiene_documentacion ? "Sí" : "No"}</td>
                      {/* The template nests a `td` in a `td`: the parser closes the first one empty. */}
                      <td />
                      <td>
                        <a href={fila.url} className="btn btn-sm btn-primary">Ver</a>
                        {fila.url_eliminar && <>{" "}<a href={fila.url_eliminar} className="btn btn-sm btn-danger">Eliminar</a></>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="text-center">Aún no se han registrado intervenciones</p>}
          </div>
        </div>
      </div>
    </div>
    <div className="col-md-2 text-start my-3">
      <a href={data.urls.volver} className="btn btn-secondary btn-lg"><i className="fas fa-arrow-left" /></a>
    </div>
  </>;
}

const UNCERTAIN = "No se pudo confirmar el resultado. Revise la intervención antes de volver a intentar.";

export function IntervencionDetail({ data }: { data: IntervencionDetailData }) {
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  const doc = data.documentacion;
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setPending(true);
    const outcome = await postForm(`${API}${data.id}/documentacion/eliminar/`, new URLSearchParams());
    if (outcome.kind === "redirect") { intervencionesNavigation.assign(outcome.url); return; }
    setError(outcome.kind === "forbidden" && record(outcome.data) && text(outcome.data.detail) ? outcome.data.detail : UNCERTAIN);
    busy.current = false; setPending(false);
    resetAfterRejectedPost();
  }
  const csrf = <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;
  return <>
    <NativeToasts messages={data.messages} />
    <div className="container mt-4">
      <div className="card card-primary card-outline">
        <div className="card-header"><h3 className="card-title">Detalle de Intervención</h3></div>
        <div className="card-body">
          <table className="table table-bordered table-striped">
            <tbody>
              <tr><th scope="row" className="w-25">Fecha y hora</th><td>{data.fecha}</td></tr>
              <tr><th scope="row">Tipo de intervención</th><td>{data.tipo_intervencion}</td></tr>
              <tr><th scope="row">Subtipo de intervención</th><td>{data.subintervencion}</td></tr>
              <tr><th scope="row">Forma de contacto</th><td>{data.forma_contacto}</td></tr>
              <tr><th scope="row">Descripción</th><td>{data.observaciones}</td></tr>
              <tr>
                <th scope="row">Documentación adjunta</th>
                <td>
                  {doc ? (
                    <div className="d-flex align-items-center">
                      <span className="me-3">{doc.name}</span>
                      <a href={doc.url} className="btn btn-sm btn-primary me-2" download>Descargar</a>
                      {data.puede_eliminar_archivo && (
                        <form method="post" style={{ display: "inline" }} onSubmit={(e) => e.preventDefault()}>
                          {csrf}
                          <button type="button" className="btn btn-sm btn-danger" onClick={() => setOpen(true)}>Eliminar</button>
                        </form>
                      )}
                    </div>
                  ) : "No hay documentación adjunta."}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    {open && (
      <NativeModal id="confirmDeleteModal" title="Confirmar eliminación" close={() => setOpen(false)} busy={pending}>
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title" id="confirmDeleteModalLabel">Confirmar eliminación</h5>
            <button type="button" className="btn-close" aria-label="Close" onClick={() => setOpen(false)} />
          </div>
          <div className="modal-body">
            ¿Estás seguro de que deseas eliminar el archivo adjunto?
            {error && <p role="alert" className="text-danger mb-0">{error}</p>}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setOpen(false)}>Cancelar</button>
            <form method="post" style={{ display: "inline" }} onSubmit={submit}>
              {csrf}
              <button type="submit" className="btn btn-danger" disabled={pending}>Eliminar</button>
            </form>
          </div>
        </div>
      </NativeModal>
    )}
  </>;
}

function ListPage({ pk }: { pk: string }) {
  const [state] = useMainResource(`${API}comedor/${pk}/${window.location.search}`, listValid);
  return renderMain(state, "Cargando intervenciones…", (data) => ({
    title: "Intervenciones",
    heading: "Intervenciones",
    breadcrumb: <Breadcrumb comedor={data.comedor} />,
    content: <IntervencionesList data={data} />,
  }));
}

function DetailPage({ pk }: { pk: string }) {
  const [state] = useMainResource(`${API}${pk}/`, detailValid);
  return renderMain(state, "Cargando intervención…", (data) => ({
    title: "Detalle de Intervención",
    breadcrumb: null,
    content: <IntervencionDetail data={data} />,
  }));
}

type Params = { page: "list" | "detail" | "create"; pk: string } | { page: "edit"; pk: string; comedor: string } | { page: "baja"; pk: string; comedor: string };

// Native URLs of `comedores/urls.py`: the list and the forms have no trailing slash, the delete and the detail have one.
const LIST = /^\/comedores\/intervencion\/ver\/(\d+)$/;
const CREATE = /^\/comedores\/intervencion\/crear\/(\d+)$/;
const EDIT = /^\/comedores\/intervencion\/editar\/(\d+)\/(\d+)$/;
const BAJA = /^\/comedores\/intervencion\/borrar\/(\d+)\/(\d+)\/$/;
const DETAIL = /^\/intervencion\/detalle\/(\d+)\/$/;

export const comedorIntervencionesRoute: RouteDefinition<Params> = {
  name: "comedores-intervenciones",
  match(pathname) {
    const list = LIST.exec(pathname);
    if (list) return { page: "list", pk: list[1] };
    const create = CREATE.exec(pathname);
    if (create) return { page: "create", pk: create[1] };
    const edit = EDIT.exec(pathname);
    if (edit) return { page: "edit", pk: edit[1], comedor: edit[2] };
    const baja = BAJA.exec(pathname);
    if (baja) return { page: "baja", comedor: baja[1], pk: baja[2] };
    const detail = DETAIL.exec(pathname);
    return detail ? { page: "detail", pk: detail[1] } : null;
  },
  render(params) {
    // The native form posts to its own URL, so `admision_id` and `next` travel in the query string.
    const search = window.location.search;
    if (params.page === "create") return <IntervencionFormPage key={params.pk} endpoint={`${API}comedor/${params.pk}/crear/${search}`} />;
    if (params.page === "edit") return <IntervencionFormPage key={`${params.pk}/${params.comedor}`} endpoint={`${API}${params.pk}/editar/${params.comedor}/${search}`} />;
    if (params.page === "baja") return <IntervencionBajaPage key={`${params.comedor}/${params.pk}`} comedor={params.comedor} intervencion={params.pk} />;
    return params.page === "list" ? <ListPage key={params.pk} pk={params.pk} /> : <DetailPage key={params.pk} pk={params.pk} />;
  },
};
