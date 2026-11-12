/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { InsumosToastList } from "../InsumosToast";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { Cancel, ModalHeader, Modal, bool, integer, messagesValid, path } from "./relevamientos";
import {
  Adjuntos, Badges, Cell, CSS, Lines, ObservacionesAlert, RevisionModal, SummaryCard, adjuntosValid, canReview, reviewValid, rowsValid, useModalState,
  type Adjunto, type Review,
} from "./relevamientosShared";
import type { RouteDefinition } from "./types";

/**
 * R02.01 `acta_complementaria_detail.html`. Data comes from
 * `/api/web/comedores/relevamientos/<comedor>/actas/<pk>/`, which runs the native
 * view; edit, review and delete stay native links and POST forms.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type ActaData = {
  acta: Review & { id: number; comedor: { id: number; nombre: string }; fecha_hora: string; tecnico: string; fecha_creacion: string; observaciones: string };
  prestaciones: string[][]; adjuntos: Adjunto[];
  capabilities: { change_actacomplementaria: boolean; review_relevamiento: boolean; delete_actacomplementaria: boolean };
  urls: { comedores: string; comedor: string; listado: string; editar: string; revision: string; eliminar: string }; messages: Message[];
};

const API = "web/comedores/relevamientos/";

export function actaValid(v: unknown): v is ActaData {
  if (!record(v) || !record(v.acta) || !record(v.acta.comedor) || !record(v.capabilities) || !record(v.urls)) return false;
  const a = v.acta, c = v.capabilities, u = v.urls, ac = a.comedor as Record<string, unknown>;
  return reviewValid(a) && integer(a.id) && integer(ac.id) && text(ac.nombre) && text(a.fecha_hora) && text(a.tecnico) && text(a.fecha_creacion) && text(a.observaciones) &&
    rowsValid(v.prestaciones) && adjuntosValid(v.adjuntos) &&
    ["change_actacomplementaria", "review_relevamiento", "delete_actacomplementaria"].every((k) => bool(c[k])) &&
    ["comedores", "comedor", "listado", "editar", "revision", "eliminar"].every((k) => internal(u[k])) && messagesValid(v.messages);
}

const REVISION = { modal: "modalRevisionActa", select: "revision_acta_estado", textarea: "revision_acta_observaciones", placeholder: "Qué debe corregir el territorial (obligatorio si devuelve el acta)" };

function EliminarModal({ action, close, trigger }: { action: string; close: () => void; trigger: HTMLElement | null }) {
  const id = "modalEliminarActa";
  return (
    <Modal id={id} title="Eliminar acta complementaria" close={close} trigger={trigger} action={action}
      footer={<><Cancel close={close} /><button type="submit" className="btn btn-danger">Eliminar</button></>}>
      <ModalHeader id={id} title="Eliminar acta complementaria" close={close} />
      <div className="modal-body">
        <p className="mb-2">Esta acción elimina el acta y sus prestaciones.</p>
        <p className="mb-0 text-muted">No se puede deshacer.</p>
      </div>
    </Modal>
  );
}

export function ActaContent({ data }: { data: ActaData }) {
  const { acta, capabilities: caps } = data;
  const modal = useModalState<"revision" | "eliminar">();
  const revisar = canReview(caps.review_relevamiento, acta);
  return <>
    <InsumosToastList messages={data.messages} />
    {CSS}
    <div className="row justify-content-between d-print-none mx-1 mb-3">
      <div className="col-auto" />
      <div className="col-auto">
        {caps.change_actacomplementaria && <><a href={path(data.urls.editar)} className="btn btn-primary mr-1">Editar</a>{" "}</>}
        {revisar && <><button type="button" className="btn btn-warning mr-1" onClick={(e) => modal.show("revision", e.currentTarget)}>Revisar</button>{" "}</>}
        {caps.delete_actacomplementaria && <button type="button" className="btn btn-danger" onClick={(e) => modal.show("eliminar", e.currentTarget)}>Eliminar</button>}
      </div>
    </div>
    <ObservacionesAlert r={acta} />
    {modal.open === "revision" && <RevisionModal ids={REVISION} action={data.urls.revision} observaciones={acta.observaciones_coordinador} close={modal.close} trigger={modal.trigger} />}
    <SummaryCard>
      <Cell label="ID SISOC" value={acta.id} />
      <Cell label="Fecha y hora" value={acta.fecha_hora} />
      <Cell label="Técnico" value={acta.tecnico} />
      <Cell label="Cargada el" value={acta.fecha_creacion} />
      <Cell label="Motivo / observaciones del cambio de prestación" value={acta.observaciones ? <Lines value={acta.observaciones} /> : "Sin observaciones"} cls="nav-item col-12 d-flex mt-3" />
    </SummaryCard>
    <div className="card mb-3" id="bloque-prestaciones">
      <div className="card-header"><h3 className="card-title font-weight-bold mr-3 pt-1">Prestaciones</h3></div>
      <div className="card-body p-0">
        {data.prestaciones.length ? (
          <div className="table-responsive">
            <table className="table table-striped mb-0">
              <thead><tr><th>Días</th><th>Tipo</th><th>Cantidad actual</th><th>Cantidad en espera</th></tr></thead>
              <tbody>{data.prestaciones.map((row, i) => <tr key={i}>{row.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
            </table>
          </div>
        ) : <p className="text-muted m-3">El acta no tiene prestaciones cargadas.</p>}
      </div>
    </div>
    {modal.open === "eliminar" && <EliminarModal action={data.urls.eliminar} close={modal.close} trigger={modal.trigger} />}
    <Adjuntos adjuntos={data.adjuntos} />
  </>;
}

function ActaPage({ comedor, id }: { comedor: string; id: string }) {
  const [state] = useMainResource(`${API}${comedor}/actas/${id}/`, actaValid);
  return renderMain(state, "Cargando acta…", (data) => {
    const a = data.acta;
    const heading = <>
      {a.comedor.nombre}{" "}
      <span className="ml-2 h5">| Acta complementaria extraordinaria</span>{" "}
      <span className="ml-2 h5">| {a.fecha_hora}</span>{" "}
      {a.origen === "app"
        ? <span className="badge bg-primary ml-2" title="Cargada por el territorial desde la app">App</span>
        : <span className="badge bg-light text-dark ml-2" title="Cargada desde SISOC">SISOC</span>}{" "}
      <Badges r={a} title="Estado del acta" />
    </>;
    return {
      title: `Acta complementaria - Comedor: ${a.comedor.nombre}`,
      heading: heading as unknown as string,
      breadcrumb: <>
        <div className="breadcrumb-item"><a href={path(data.urls.comedores)}>Comedores</a></div>
        <div className="breadcrumb-item"><a href={path(data.urls.comedor)}>{a.comedor.nombre}</a></div>
        <div className="breadcrumb-item"><a href={path(data.urls.listado)}>Acompañamiento Territorial</a></div>
        <div className="breadcrumb-item active">Acta complementaria</div>
      </>,
      content: <ActaContent data={data} />,
    };
  });
}

type Params = { comedor: string; id: string };
const DETAIL = /^\/comedores\/([0-9]+)\/acta-complementaria\/([0-9]+)$/;

export const relevamientosActasRoute: RouteDefinition<Params> = {
  name: "comedores-relevamientos-actas",
  match(pathname) {
    const d = DETAIL.exec(pathname);
    return d ? { comedor: d[1], id: d[2] } : null;
  },
  render({ comedor, id }) {
    return <ActaPage comedor={comedor} id={id} />;
  },
};
