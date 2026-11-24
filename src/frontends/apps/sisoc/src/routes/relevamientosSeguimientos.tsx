/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { Tree, arr, bool, integer, messagesValid, nodeValid, path, type TreeNode } from "./relevamientos";
import {
  Adjuntos, Badges, Cell, CSS, DataTable, Lines, ObservacionesAlert, RevisionModal, SummaryCard, adjuntosValid, canReview, reviewValid, rowsValid, useModalState,
  type Adjunto, type Review,
} from "./relevamientosShared";
import { useToasts } from "./relevamientosApi";
import type { RouteDefinition } from "./types";

/**
 * R03.01 `primer_seguimiento_detail.html` (a cycle instance and its historical
 * alias) and `seguimiento_pnud_detail.html`. Data comes from
 * `/api/web/comedores/relevamientos/`, which runs the native views; values
 * arrive printed by the template engine. The review modal is a native POST.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type SeguimientoData = {
  seguimiento: Review & { id: number; tipo_display: string; numero_orden: number; fecha_hora: string; sincronizado_gestionar: boolean; gestionar_id: string; tecnico: string; referente: string; motivo_diferencia_aprobado_declarado: string };
  relevamiento: { id: number; fecha_visita: string }; comedor: { id: number; nombre: string };
  instancias: { id: number; numero_orden: number; tipo_display: string; detalle_url: string }[];
  bloques: { key: string; label: string; campos: { label: string; value: string | TreeNode[]; es_imagen: boolean }[] }[];
  es_primer: boolean; prestaciones: string[][]; receta_items: string[][]; adjuntos: Adjunto[];
  pdf: { url: string | null; fecha_oficial: string | null };
  capabilities: { change_primerseguimiento: boolean; review_relevamiento: boolean; delete_primerseguimiento: boolean };
  urls: { comedores: string; comedor: string; relevamiento: string; editar: string; revision: string; revision_api: string }; messages: Message[];
};
type Respuesta = { etiqueta: string; tipo: "texto" | "imagen" | "tabla"; valor?: string; columnas?: string[]; filas?: string[][] };
export type PnudData = {
  seguimiento: Review & { id: number; formulario: string; formulario_display: string; fecha_hora: string; tecnico: string; fecha_creacion: string };
  comedor: { id: number; nombre: string }; encabezado_formulario: { linea: string; titulo: string };
  secciones: { titulo: string; filas: Respuesta[] }[]; adjuntos: Adjunto[]; pdf_url: string | null;
  capabilities: { review_relevamiento: boolean };
  urls: { comedores: string; comedor: string; listado: string; revision: string; revision_api: string }; messages: Message[];
};

const API = "web/comedores/relevamientos/";

export function seguimientoValid(v: unknown): v is SeguimientoData {
  if (!record(v) || !record(v.seguimiento) || !record(v.relevamiento) || !record(v.comedor) || !record(v.capabilities) || !record(v.urls) || !record(v.pdf)) return false;
  const s = v.seguimiento, u = v.urls, c = v.capabilities;
  return reviewValid(s) && integer(s.id) && text(s.tipo_display) && integer(s.numero_orden) && text(s.fecha_hora) && bool(s.sincronizado_gestionar) && text(s.gestionar_id) &&
    text(s.tecnico) && text(s.referente) && text(s.motivo_diferencia_aprobado_declarado) &&
    integer(v.relevamiento.id) && text(v.relevamiento.fecha_visita) && integer(v.comedor.id) && text(v.comedor.nombre) &&
    arr(v.instancias, (i) => record(i) && integer(i.id) && integer(i.numero_orden) && text(i.tipo_display) && internal(i.detalle_url)) &&
    arr(v.bloques, (b) => record(b) && text(b.key) && text(b.label) && arr(b.campos, (k) => record(k) && text(k.label) && bool(k.es_imagen) && (k.es_imagen ? arr(k.value, nodeValid) : text(k.value)))) &&
    bool(v.es_primer) && rowsValid(v.prestaciones) && rowsValid(v.receta_items) && adjuntosValid(v.adjuntos) &&
    (v.pdf.url === null || internal(v.pdf.url)) && (v.pdf.fecha_oficial === null || text(v.pdf.fecha_oficial)) &&
    ["change_primerseguimiento", "review_relevamiento", "delete_primerseguimiento"].every((k) => bool(c[k])) &&
    ["comedores", "comedor", "relevamiento", "editar", "revision", "revision_api"].every((k) => internal(u[k])) && messagesValid(v.messages);
}

export function pnudValid(v: unknown): v is PnudData {
  if (!record(v) || !record(v.seguimiento) || !record(v.comedor) || !record(v.encabezado_formulario) || !record(v.capabilities) || !record(v.urls)) return false;
  const s = v.seguimiento, u = v.urls;
  return reviewValid(s) && integer(s.id) && text(s.formulario) && text(s.formulario_display) && text(s.fecha_hora) && text(s.tecnico) && text(s.fecha_creacion) &&
    integer(v.comedor.id) && text(v.comedor.nombre) && text(v.encabezado_formulario.linea) && text(v.encabezado_formulario.titulo) &&
    arr(v.secciones, (x) => record(x) && text(x.titulo) && arr(x.filas, (f) => record(f) && text(f.etiqueta) && (f.tipo === "tabla" ? arr(f.columnas, text) && rowsValid(f.filas) : text(f.valor)))) &&
    adjuntosValid(v.adjuntos) && (v.pdf_url === null || internal(v.pdf_url)) && bool(v.capabilities.review_relevamiento) &&
    ["comedores", "comedor", "listado", "revision", "revision_api"].every((k) => internal(u[k])) && messagesValid(v.messages);
}

const Breadcrumb = ({ items }: { items: { text: string; url: string | null }[] }) => <>
  {items.map((i, n) => i.url ? <div className="breadcrumb-item" key={n}><a href={path(i.url)}>{i.text}</a></div> : <div className="breadcrumb-item active" key={n}>{i.text}</div>)}
</>;

const REVISION = { modal: "modalRevisionSeguimiento", select: "revision_seguimiento_estado", textarea: "revision_seguimiento_observaciones", placeholder: "Qué debe corregir el territorial (obligatorio si devuelve el seguimiento)" };
const REVISION_PNUD = { modal: "modalRevisionSeguimientoPnud", select: "revision_pnud_estado", textarea: "revision_pnud_observaciones", placeholder: "Qué debe corregir el territorial (obligatorio si devuelve el seguimiento)" };

export function SeguimientoContent({ data }: { data: SeguimientoData }) {
  const { seguimiento: s, capabilities: caps } = data;
  const modal = useModalState<"revision">();
  const { toasts, push } = useToasts(data.messages);
  const revisar = canReview(caps.review_relevamiento, s);
  return <>
    {toasts}
    {CSS}
    <div className="row justify-content-between d-print-none mx-1 mb-3">
      <div className="col-auto">
        {data.instancias.length > 1 && (
          <div className="btn-group" role="group" aria-label="Instancias del ciclo">
            {data.instancias.map((i) => (
              <a key={i.id} href={path(i.detalle_url)} className={`btn btn-sm ${i.id === s.id ? "btn-info" : "btn-outline-info"}`} title={i.tipo_display}>#{i.numero_orden} {i.tipo_display}</a>
            ))}
          </div>
        )}
      </div>
      <div className="col-auto">
        {data.pdf.url
          ? <a href={path(data.pdf.url)} className="btn btn-secondary mr-1" title={`Formato oficial de Gestionar, enviado el ${data.pdf.fecha_oficial}`}>Descargar PDF</a>
          : <small className="text-muted mr-2">El PDF se genera cuando el territorial lo envía desde Gestionar.</small>}{" "}
        {caps.change_primerseguimiento && <><a href={path(data.urls.editar)} className="btn btn-primary mr-1">Editar</a>{" "}</>}
        {revisar && <><button type="button" className="btn btn-warning mr-1" onClick={(e) => modal.show("revision", e.currentTarget)}>Revisar</button>{" "}</>}
      </div>
    </div>
    <ObservacionesAlert r={s} />
    {modal.open === "revision" && <RevisionModal ids={REVISION} action={data.urls.revision} api={data.urls.revision_api} onError={(message) => { modal.close(); push({ message, level: "error" }); }} observaciones={s.observaciones_coordinador} close={modal.close} trigger={modal.trigger} />}
    <SummaryCard>
      <Cell label="ID SISOC" value={s.id} />
      <Cell label="ID GESTIONAR" value={s.gestionar_id} />
      <Cell label="Técnico" value={s.tecnico} />
      <Cell label="Referente" value={s.referente} />
      {s.motivo_diferencia_aprobado_declarado && <Cell label="Motivo de la diferencia entre lo aprobado y lo declarado" value={<Lines value={s.motivo_diferencia_aprobado_declarado} />} cls="nav-item col-12 d-flex mt-3" />}
    </SummaryCard>
    {data.bloques.length ? data.bloques.map((b) => (
      <div className="card mb-3" id={`bloque-${b.key}`} key={b.key}>
        <div className="card-header"><h3 className="card-title font-weight-bold mr-3 pt-1">{b.label}</h3></div>
        <div className="card-body card-comments pt-0 pb-1"><div className="nav nav-pills row my-3">
          {b.campos.map((k, i) => (
            <div className="nav-item col-md-4 col-sm-6 d-flex mb-2" key={i}>
              <div className="comment-text d-flex flex-column text-sm">
                {k.label}
                {k.es_imagen ? <Tree nodes={k.value as TreeNode[]} /> : <span className="username fw-bold fs-5">{k.value as string}</span>}
              </div>
            </div>
          ))}
        </div></div>
      </div>
    )) : <div className="alert alert-info">Todavía no se cargaron bloques para este seguimiento.</div>}
    {data.prestaciones.length > 0 && <DataTable id="bloque-prestaciones" title="Prestaciones" rows={data.prestaciones}
      head={["Días", "Tipo", ...(data.es_primer ? ["AP"] : ["AP presencial", "AP vianda"]), "DE presencial", "DE vianda"]} />}
    {data.receta_items.length > 0 && <DataTable id="bloque-receta-items" title="Items de receta del menú" rows={data.receta_items} head={["Ingrediente", "Unidad de medida", "Cantidad"]} />}
    <Adjuntos adjuntos={data.adjuntos} />
  </>;
}

function SeguimientoPage({ comedor, relevamiento, id }: { comedor: string; relevamiento: string; id?: string }) {
  const [state] = useMainResource(`${API}${comedor}/relevamiento/${relevamiento}/seguimientos/${id ?? "primero"}/`, seguimientoValid);
  return renderMain(state, "Cargando seguimiento…", (data) => {
    const s = data.seguimiento;
    const heading = <>
      {data.comedor.nombre}{" "}
      <span className="ml-2 h5">| {s.tipo_display} #{s.numero_orden}</span>{" "}
      <span className="ml-2 h5">| {s.fecha_hora} |{" "}</span>
      <Badges r={s} title="Estado del seguimiento">
        {s.origen === "app" && <><span className="badge bg-primary ml-2" title="Cargado por el territorial desde la app">App</span>{" "}</>}
        {s.sincronizado_gestionar
          ? <span className="badge bg-success ml-2" title="El seguimiento se sincronizó con GESTIONAR">Sincronizado con GESTIONAR</span>
          : <span className="badge bg-secondary ml-2" title="Todavía no se sincronizó con GESTIONAR">Pendiente sincronización</span>}
      </Badges>
    </>;
    return {
      title: `${s.tipo_display} - Comedor: ${data.comedor.nombre}`,
      // The shell prints the node inside its `<h3>`, as the native `titulo-pagina` block does.
      heading: heading as unknown as string,
      breadcrumb: <Breadcrumb items={[
        { text: "Comedores", url: data.urls.comedores }, { text: data.comedor.nombre, url: data.urls.comedor },
        { text: `Acompañamiento Territorial ${data.relevamiento.fecha_visita}`, url: data.urls.relevamiento }, { text: s.tipo_display, url: null },
      ]} />,
      content: <SeguimientoContent data={data} />,
    };
  });
}

export function PnudContent({ data }: { data: PnudData }) {
  const s = data.seguimiento;
  const modal = useModalState<"revision">();
  const { toasts, push } = useToasts(data.messages);
  const revisar = canReview(data.capabilities.review_relevamiento, s);
  const encabezado = data.encabezado_formulario;
  return <>
    {toasts}
    {CSS}
    <div className="row justify-content-between d-print-none mx-1 mb-3">
      <div className="col-auto">{data.pdf_url && <a href={path(data.pdf_url)} className="btn btn-outline-secondary">Descargar PDF</a>}</div>
      <div className="col-auto">
        {revisar && <><button type="button" className="btn btn-warning mr-1" onClick={(e) => modal.show("revision", e.currentTarget)}>Revisar</button>{" "}</>}
      </div>
    </div>
    <ObservacionesAlert r={s} />
    {modal.open === "revision" && <RevisionModal ids={REVISION_PNUD} action={data.urls.revision} api={data.urls.revision_api} onError={(message) => { modal.close(); push({ message, level: "error" }); }} observaciones={s.observaciones_coordinador} close={modal.close} trigger={modal.trigger} />}
    <SummaryCard>
      <Cell label="ID SISOC" value={s.id} />
      <Cell label="Fecha y hora" value={s.fecha_hora} />
      <Cell label="Técnico" value={s.tecnico} />
      <Cell label="Cargado el" value={s.fecha_creacion} />
    </SummaryCard>
    {encabezado.titulo && <div className="text-center mb-3"><div className="fw-bold">{encabezado.linea}</div><div>{encabezado.titulo}</div></div>}
    {data.secciones.length ? data.secciones.map((sec, n) => (
      <div className="card mb-4" key={n}>
        <div className="card-header"><h3 className="card-title font-weight-bold mr-3 pt-1">{sec.titulo}</h3></div>
        <div className="card-body"><table className="table table-sm table-striped mb-0"><tbody>
          {sec.filas.map((f, i) => (
            <tr key={i}>
              <th scope="row" className="w-50">{f.etiqueta}</th>
              <td>
                {f.tipo === "tabla" ? (
                  <table className="table table-sm table-bordered mb-0">
                    <thead><tr>{f.columnas!.map((c, j) => <th key={j}>{c}</th>)}</tr></thead>
                    <tbody>{f.filas!.map((row, r) => <tr key={r}>{row.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
                  </table>
                ) : f.tipo === "imagen" ? <img src={path(f.valor!)} alt={f.etiqueta} style={{ maxWidth: "240px", maxHeight: "120px" }} /> : <Lines value={f.valor!} />}
              </td>
            </tr>
          ))}
        </tbody></table></div>
      </div>
    )) : <p className="text-muted mx-1">El seguimiento no tiene respuestas cargadas.</p>}
    <Adjuntos adjuntos={data.adjuntos} />
  </>;
}

function PnudPage({ comedor, id }: { comedor: string; id: string }) {
  const [state] = useMainResource(`${API}${comedor}/pnud/${id}/`, pnudValid);
  return renderMain(state, "Cargando seguimiento…", (data) => {
    const s = data.seguimiento;
    const heading = <>
      {data.comedor.nombre}{" "}
      <span className="ml-2 h5">| {s.formulario_display}</span>{" "}
      <span className="ml-2 h5">| {s.fecha_hora}</span>{" "}
      <Badges r={s} title="Estado del seguimiento">
        {s.origen === "app" && <span className="badge bg-primary ml-2" title="Cargado por el territorial desde la app">App</span>}
      </Badges>
    </>;
    return {
      title: `Seguimiento PNUD - Comedor: ${data.comedor.nombre}`,
      heading: heading as unknown as string,
      breadcrumb: <Breadcrumb items={[
        { text: "Comedores", url: data.urls.comedores }, { text: data.comedor.nombre, url: data.urls.comedor },
        { text: "Acompañamiento Territorial", url: data.urls.listado }, { text: "Seguimiento PNUD", url: null },
      ]} />,
      content: <PnudContent data={data} />,
    };
  });
}

type Params = { comedor: string; relevamiento?: string; id?: string; pnud?: boolean };
const DETAIL = /^\/comedores\/([0-9]+)\/relevamiento\/([0-9]+)\/seguimiento\/([0-9]+)\/$/;
const ALIAS = /^\/comedores\/([0-9]+)\/relevamiento\/([0-9]+)\/primer-seguimiento\/$/;
const PNUD = /^\/comedores\/([0-9]+)\/seguimiento-pnud\/([0-9]+)$/;

export const relevamientosSeguimientosRoute: RouteDefinition<Params> = {
  name: "comedores-relevamientos-seguimientos",
  match(pathname) {
    const d = DETAIL.exec(pathname);
    if (d) return { comedor: d[1], relevamiento: d[2], id: d[3] };
    const a = ALIAS.exec(pathname);
    if (a) return { comedor: a[1], relevamiento: a[2] };
    const p = PNUD.exec(pathname);
    return p ? { comedor: p[1], id: p[2], pnud: true } : null;
  },
  render({ comedor, relevamiento, id, pnud }) {
    return pnud ? <PnudPage comedor={comedor} id={id!} /> : <SeguimientoPage comedor={comedor} relevamiento={relevamiento!} id={id} />;
  },
};
