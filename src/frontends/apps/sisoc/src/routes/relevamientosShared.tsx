/* eslint-disable react-refresh/only-export-components -- shared pieces of the relevamiento detail pages (validators and components travel together). */
import { Fragment, useState, type ReactNode } from "react";
import { internal, record, text } from "./MainFrame";
import { Cancel, CSS, Modal, ModalHeader, arr, bool, csrf, integer, path } from "./relevamientos";

/**
 * Pieces the seguimiento, PNUD and acta detail pages share (R03.01, R02.01): the
 * coordinator review block, its alert and modal, the summary card and the
 * attachments card. All of them print what the native templates print.
 */
export type Review = {
  estado: string; estado_badge: string; estado_validacion: string; a_subsanar: boolean; esta_validado: boolean; sin_cargar: boolean;
  observaciones_coordinador: string; coordinador: string | null; fecha_revision_coordinador: string | null; origen: string;
};
export type Adjunto = { id: number; nombre_original: string; es_pdf: boolean; tamano: string; fecha_subida: string; descargar_url: string };

export const reviewValid = (r: Record<string, unknown>) => text(r.estado) && text(r.estado_badge) && text(r.estado_validacion) && bool(r.a_subsanar) && bool(r.esta_validado) &&
  bool(r.sin_cargar) && text(r.observaciones_coordinador) && (r.coordinador === null || text(r.coordinador)) &&
  (r.fecha_revision_coordinador === null || text(r.fecha_revision_coordinador)) && text(r.origen);
export const adjuntosValid = (v: unknown) => arr(v, (a) => record(a) && integer(a.id) && text(a.nombre_original) && bool(a.es_pdf) && text(a.tamano) && text(a.fecha_subida) && internal(a.descargar_url));
export const rowsValid = (v: unknown) => arr(v, (r) => arr(r, text));

export { CSS };

/** Django `linebreaksbr`. */
export function Lines({ value }: { value: string }) {
  return <>{value.split(/\r\n|\r|\n/).map((line, i) => <Fragment key={i}>{i > 0 && <br />}{line}</Fragment>)}</>;
}

/** The `badge` of the unified state, the "A subsanar" one and the page-specific ones, separated like the template does. */
export function Badges({ r, title, children }: { r: Review; title: string; children?: ReactNode }) {
  return <>
    <span className={`badge ml-2 ${r.estado_badge}`} title={`${title}${r.estado_validacion ? ` (validación del coordinador: ${r.estado_validacion})` : ""}`}>{r.estado}</span>{" "}
    {r.a_subsanar && <><span className="badge bg-danger ml-1">A subsanar</span>{" "}</>}
    {children}
  </>;
}

export const canReview = (reviewer: boolean, r: Review) => reviewer && !r.esta_validado && !r.sin_cargar;

export function ObservacionesAlert({ r }: { r: Review }) {
  if (!r.observaciones_coordinador) return null;
  return (
    <div className={`alert ${r.a_subsanar ? "alert-danger" : "alert-info"} mx-1 d-print-none`}>
      <strong>Observaciones del coordinador</strong>
      {r.coordinador && <>{" "}<span className="ml-1">({r.coordinador}{r.fecha_revision_coordinador && <>{" "}· {r.fecha_revision_coordinador}</>})</span></>}
      <div className="mt-1"><Lines value={r.observaciones_coordinador} /></div>
    </div>
  );
}

type RevisionIds = { modal: string; select: string; textarea: string; placeholder: string };

/** The "Revisión del coordinador" modal: a native POST form with CSRF. */
export function RevisionModal({ ids, action, observaciones, close, trigger }: { ids: RevisionIds; action: string; observaciones: string; close: () => void; trigger: HTMLElement | null }) {
  return (
    <Modal id={ids.modal} title="Revisión del coordinador" close={close} trigger={trigger} action={action}
      footer={<><Cancel close={close} /><button type="submit" className="btn btn-warning">Guardar revisión</button></>}>
      <ModalHeader id={ids.modal} title="Revisión del coordinador" close={close} />
      <div className="modal-body">
        <div className="mb-3">
          <label htmlFor={ids.select} className="form-label">Resultado</label>
          <select id={ids.select} name="estado_validacion" className="form-select" required defaultValue="Validado">
            <option value="Validado">Validado</option>
            <option value="A subsanar">A subsanar (devolver al territorial)</option>
          </select>
        </div>
        <div className="mb-0">
          <label htmlFor={ids.textarea} className="form-label">Observaciones</label>
          <textarea id={ids.textarea} name="observaciones_coordinador" className="form-control" rows={4} defaultValue={observaciones} placeholder={ids.placeholder} />
        </div>
      </div>
    </Modal>
  );
}

/** Opens one modal at a time and remembers its trigger (focus returns to it on close). */
export function useModalState<K extends string>() {
  const [open, setOpen] = useState<K | null>(null);
  const [trigger, setTrigger] = useState<HTMLElement | null>(null);
  return { open, trigger, show: (kind: K, el: HTMLElement) => { setTrigger(el); setOpen(kind); }, close: () => setOpen(null) };
}

export const Cell = ({ label, value, cls = "nav-item col-md-3 col-sm-6 d-flex" }: { label: string; value: ReactNode; cls?: string }) => (
  <div className={cls}>
    <div className="comment-text d-flex flex-column text-sm">{label}<span className="username fw-bold fs-5">{value}</span></div>
  </div>
);

export const SummaryCard = ({ children }: { children: ReactNode }) => (
  <div className="card mb-4">
    <div className="card-header"><h3 className="card-title font-weight-bold mr-3 pt-1">Resumen</h3></div>
    <div className="card-body card-comments pt-0 pb-1"><div className="nav nav-pills row my-3">{children}</div></div>
  </div>
);

export function DataTable({ id, title, head, rows }: { id: string; title: string; head: string[]; rows: string[][] }) {
  return (
    <div className="card mb-3" id={id}>
      <div className="card-header"><h3 className="card-title font-weight-bold mr-3 pt-1">{title}</h3></div>
      <div className="card-body p-0"><div className="table-responsive">
        <table className="table table-striped mb-0">
          <thead><tr>{head.map((h) => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>{rows.map((row, i) => <tr key={i}>{row.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
        </table>
      </div></div>
    </div>
  );
}

/** `adjuntos_formulario.html`. */
export function Adjuntos({ adjuntos }: { adjuntos: Adjunto[] }) {
  if (!adjuntos.length) return null;
  return (
    <div className="card mb-4" id="bloque-adjuntos">
      <div className="card-header"><h3 className="card-title font-weight-bold mr-3 pt-1">Archivos adjuntos</h3></div>
      <div className="card-body p-0"><ul className="list-group list-group-flush">
        {adjuntos.map((a) => (
          <li className="list-group-item d-flex justify-content-between align-items-center" key={a.id}>
            <span><i className={`fas ${a.es_pdf ? "fa-file-pdf" : "fa-file-image"} mr-2`} />{" "}{a.nombre_original}{" "}
              <small className="text-muted ml-2">{a.tamano} - {a.fecha_subida}</small></span>
            <a href={path(a.descargar_url)} className="btn btn-sm btn-outline-secondary" rel="noopener">Descargar</a>
          </li>
        ))}
      </ul></div>
    </div>
  );
}

export { csrf };
