/* eslint-disable react-refresh/only-export-components -- the module exports its validators and the legajo section next to the route. */
import { useRef, useState, type ReactNode } from "react";
import { InsumosToastList } from "../InsumosToast";
import { Breadcrumb, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * O02 documents of the organization: the "Documentación de la Organización"
 * table of the legajo (`legajo/documentacion.html` + its row partial, with the
 * behaviors of `organizacionesDocumentos.js`) and the history page
 * (`organizaciones/documentacion_historial.html`). The API runs the native
 * views; each operation answers the updated row as data and the Django texts
 * come back verbatim. Nothing is retried: an uncertain upload is reread by
 * reloading the legajo.
 */
const API = "web/comedores/organizaciones/";
const ACCEPT = ".pdf,.jpg,.jpeg,.png,.xls,.xlsx,.doc,.docx";

type Expiry = { date: string; iso: string; status: "vencido" | "por_vencer" | "vigente" };
type DocFile = { id: number; state: string; observations: string; url: string; expiry: Expiry | null; gde: string };
export type DocRow = {
  row_id: number | string; name: string; mandatory: boolean; custom: boolean; document_id: number | null; history_url: string | null;
  can_validate: boolean; can_send: boolean; file: DocFile | null;
};
export type DocumentosSection = { kind: "documentos"; organization_id: number; category: string; can_validate: boolean; can_send: boolean; rows: DocRow[] };
type Toast = { message: string; level: "success" | "error" };

export const documentosSectionValid = (v: unknown): v is DocumentosSection =>
  record(v) && v.kind === "documentos" && typeof v.organization_id === "number" && text(v.category) && Array.isArray(v.rows) &&
  v.rows.every((r) => record(r) && (typeof r.row_id === "number" || text(r.row_id)) && text(r.name) && (r.file === null || (record(r.file) && text(r.file.url))));

type Outcome = { ok: true; row: DocRow } | { ok: false; error: string | null };

/** One POST, no retry: `{fila}` is the updated row, `{error}` the native text, null a network failure. */
async function send(url: string, body: FormData, progress?: (percent: number) => void): Promise<Outcome> {
  try {
    const { data, status } = await webClient.post(url, body, {
      validateStatus: (s: number) => s < 500,
      onUploadProgress: progress && ((e: { loaded: number; total?: number }) => { if (e.total) progress(Math.round((e.loaded / e.total) * 100)); }),
    });
    if (status === 200 && record(data) && record(data.fila)) return { ok: true, row: data.fila as unknown as DocRow };
    return { ok: false, error: record(data) && text(data.error) && data.error ? data.error : "" };
  } catch {
    return { ok: false, error: null };
  }
}

const form = (values: Record<string, string>, file?: File) => {
  const body = new FormData();
  for (const [key, value] of Object.entries(values)) body.append(key, value);
  if (file) body.append("archivo", file);
  return body;
};

const STATES = {
  validate: ["A Validar Abogado", "Aceptado", "Rectificar"],
  send: ["Documento adjunto", "A Validar Abogado"],
};

function StateCell({ row, file, onChange }: { row: DocRow; file: DocFile | null; onChange: (value: string, observations: string | null) => void }) {
  if (!file) return <span className="badge bg-secondary">Pendiente</span>;
  const { state } = file;
  let control;
  if (state === "Aceptado") control = <span className="badge bg-success">Aceptado</span>;
  else if (state === "A Validar Abogado") {
    control = row.can_validate ? (
      <select className="form-control form-control-sm org-doc-state-select border border-2 border-primary" value={state}
        onChange={(e) => onChange(e.target.value, e.target.value === "Rectificar" ? null : "")} aria-label={`Estado de ${row.name}`}>
        {STATES.validate.map((s) => <option key={s} value={s}>{s}</option>)}
      </select>
    ) : <span className="badge bg-primary">A Validar Abogado</span>;
  } else if (row.can_send) {
    control = (
      <select className={`form-control form-control-sm org-doc-state-select${state === "Rectificar" ? " border border-danger border-2" : ""}`} value={state}
        onChange={(e) => onChange(e.target.value, "")} aria-label={`Estado de ${row.name}`}>
        {state === "Rectificar" && <option value="Rectificar" disabled>Rectificar</option>}
        <option value="Documento adjunto" disabled={state === "Documento adjunto"}>Documento adjunto</option>
        <option value="A Validar Abogado">A Validar Abogado</option>
      </select>
    );
  } else control = state === "Rectificar" ? <span className="badge bg-danger">Rectificar</span> : <span className="badge bg-secondary">{state}</span>;
  return <>{control}{file.observations && <div className="small text-warning mt-1">{file.observations}</div>}</>;
}

function InlineField({ display, value, empty, placeholder, type, editable, onSave, extra }: {
  display: ReactNode; value: string; empty: string; placeholder?: string; type: "date" | "text"; editable: boolean;
  onSave: (value: string) => Promise<boolean>; extra?: Record<string, string>;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  if (!editable) return <>{display}</>;
  if (!editing) {
    return (
      <div className="org-inline-display" role="button" tabIndex={0} onClick={() => { setDraft(value); setEditing(true); }}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setDraft(value); setEditing(true); } }}>
        {display}
      </div>
    );
  }
  const save = async () => { if (await onSave(draft.trim())) setEditing(false); else setDraft(value); };
  return (
    <div className="org-inline-edit">
      <div className="d-flex align-items-center">
        <input type={type} className="form-control form-control-sm me-2 org-inline-input" value={draft} autoFocus placeholder={placeholder} data-empty-text={empty}
          maxLength={type === "text" ? 50 : undefined} style={type === "text" ? { maxWidth: 160 } : undefined} {...extra}
          onChange={(e) => setDraft(e.target.value)} />
        <button type="button" className="btn btn-success btn-sm me-1 org-inline-save" title="Guardar" aria-label="Guardar" onClick={save}><i className="bi bi-check" /></button>
        <button type="button" className="btn btn-secondary btn-sm org-inline-cancel" title="Cancelar" aria-label="Cancelar" onClick={() => setEditing(false)}><i className="bi bi-x" /></button>
      </div>
    </div>
  );
}

function ExpiryDisplay({ expiry }: { expiry: Expiry | null }) {
  if (!expiry) return <><span className="text-muted">Sin vencimiento</span>{" "}<i className="bi bi-plus-circle ms-2 text-primary" title="Agregar vencimiento" /></>;
  const tone = { vencido: "text-danger", por_vencer: "text-warning", vigente: "text-success" }[expiry.status];
  const badge = { vencido: ["vencido", "Vencido"], por_vencer: ["por-vencer", "Por vencer"], vigente: ["vigente", "Vigente"] }[expiry.status];
  return <><span className={`${tone} fw-bold`}>{" "}{expiry.date}{" "}</span>{" "}<span className={`badge-status ${badge[0]} ms-1`}>{badge[1]}</span>{" "}<i className="bi bi-pencil-square ms-2 text-muted" title="Editar vencimiento" /></>;
}

function DocumentRow({ row, organizationId, onRow, toast, askObservations }: {
  row: DocRow; organizationId: number; onRow: (row: DocRow) => void; toast: (t: Toast) => void;
  askObservations: (done: (observations: string | null) => void) => void;
}) {
  const file = row.file;
  const picker = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const modifiable = row.can_validate || row.can_send;
  const id = `org-doc-row-${row.row_id}`;

  async function post(path: string, body: FormData, ok: string, fallback: string): Promise<boolean> {
    const outcome = await send(`${API}documentacion/${file!.id}/${path}/`, body);
    if (outcome.ok) { onRow(outcome.row); toast({ message: ok, level: "success" }); return true; }
    toast({ message: outcome.error || fallback, level: "error" });
    return false;
  }
  function changeState(value: string, observations: string | null) {
    const submit = (text: string) => post("estado", form(text ? { estado: value, observaciones: text } : { estado: value }), "Estado actualizado con éxito.", "No se pudo actualizar el estado.");
    if (observations === null) askObservations((text) => { if (text !== null) void submit(text); });
    else void submit("");
  }
  async function upload(chosen: File | undefined) {
    if (!chosen) return;
    setProgress(0);
    const outcome = await send(`${API}${organizationId}/documentacion/${row.document_id}/subir/`, form({}, chosen), setProgress);
    if (picker.current) picker.current.value = "";
    if (outcome.ok) { onRow(outcome.row); toast({ message: "Documento cargado con éxito.", level: "success" }); }
    else { toast({ message: outcome.error === null ? "Error de red al subir el documento." : outcome.error || "No se pudo subir el archivo.", level: "error" }); }
    setProgress(null);
  }
  const canUpload = row.can_send && !row.custom;
  return (
    <tr id={id}>
      <td className="doc-name">
        {row.custom ? <><strong>{row.name}</strong>{" "}<span className="badge bg-info text-dark ms-1">Adicional</span></> : <><strong>{row.name}</strong>{row.mandatory && <>{" "}<span className="text-danger fs-5 ms-1">*</span></>}</>}
        {row.history_url && <div className="mt-1"><a href={row.history_url} className="btn btn-sm btn-outline-secondary">Historial</a></div>}
      </td>
      <td><StateCell row={row} file={file} onChange={changeState} /></td>
      <td>
        {file ? <div className="documentacion-compact-controls"><a href={file.url} target="_blank" rel="noreferrer" className="btn btn-primary btn-sm"><i className="fas fa-eye" /> Ver Archivo</a></div>
          : <span style={{ color: "#9ca3af" }}>Sin archivo</span>}
      </td>
      <td>
        <div className="documentacion-compact-controls">
          {file && (
            <InlineField type="date" editable={modifiable} value={file.expiry?.iso ?? ""} empty="Sin vencimiento" display={<ExpiryDisplay expiry={file.expiry} />}
              onSave={(value) => post("vencimiento", form({ fecha_vencimiento: value }), "Vencimiento actualizado con éxito.", "No se pudo guardar el valor.")} />
          )}
          {canUpload && (
            <>
              <input ref={picker} type="file" id={`org-doc-file-${row.document_id}`} className="d-none org-doc-file" accept={ACCEPT} onChange={(e) => void upload(e.target.files?.[0])} />
              <button type="button" className="btn btn-sm btn-outline-light org-doc-open-file" onClick={() => picker.current?.click()}>Adjuntar</button>
            </>
          )}
        </div>
        {canUpload && (
          <div className="progress mt-2 documentacion-upload-progress" id={`org-progress-container-${row.document_id}`} style={{ display: progress === null ? undefined : "block" }}>
            <div className="progress-bar progress-bar-striped" role="progressbar" id={`org-progress-bar-${row.document_id}`} style={{ width: `${progress ?? 0}%` }}>{progress ?? 0}%</div>
          </div>
        )}
      </td>
      <td>
        {file && file.state === "Aceptado" ? (
          <InlineField type="text" editable={modifiable} value={file.gde} empty="Sin número GDE" placeholder="Ingrese número GDE"
            display={modifiable ? (file.gde ? <><span className="text-success fw-bold">{file.gde}</span>{" "}<i className="bi bi-pencil-square ms-2 text-muted" title="Editar número GDE" /></>
              : <><span className="text-muted">Sin número GDE</span>{" "}<i className="bi bi-plus-circle ms-2 text-primary" title="Agregar número GDE" /></>)
              : file.gde ? <span className="text-success fw-bold">{file.gde}</span> : <span className="text-muted">-</span>}
            onSave={(value) => post("numero-gde", form({ numero_gde: value }), "Número GDE actualizado con éxito.", "No se pudo guardar el valor.")} />
        ) : <span className="text-muted">-</span>}
      </td>
    </tr>
  );
}

function RectifyModal({ onDone }: { onDone: (observations: string | null) => void }) {
  const [observations, setObservations] = useState("");
  const [error, setError] = useState("");
  const confirm = () => {
    const trimmed = observations.trim();
    if (!trimmed) { setError("Debe completar las observaciones."); return; }
    onDone(trimmed);
  };
  return (
    <>
      <div className="modal fade show d-block" id="orgModalObservacionRectificar" tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="orgModalObservacionRectificarLabel">
        <div className="modal-dialog modal-dialog-centered">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title" id="orgModalObservacionRectificarLabel">Observaciones obligatorias</h5>
              <button type="button" className="btn-close" aria-label="Close" onClick={() => onDone(null)} />
            </div>
            <div className="modal-body">
              <div className="mb-3">
                <label htmlFor="orgObservacionRectificar" className="form-label">Detalle el motivo de la rectificacion</label>
                <textarea className="form-control" id="orgObservacionRectificar" rows={4} maxLength={2000} autoFocus value={observations} onChange={(e) => setObservations(e.target.value)} />
                <div className="text-danger small mt-2" id="orgObservacionRectificarError">{error}</div>
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={() => onDone(null)}>Cancelar</button>
              <button type="button" className="btn btn-primary" id="orgBtnConfirmarRectificar" onClick={confirm}>Guardar observaciones</button>
            </div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop fade show" />
    </>
  );
}

export function DocumentosSection({ section }: { section: DocumentosSection }) {
  const [rows, setRows] = useState(section.rows);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [rectify, setRectify] = useState<((observations: string | null) => void) | null>(null);
  const [name, setName] = useState("");
  const [expiry, setExpiry] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const nameInput = useRef<HTMLInputElement>(null);
  const toast = (t: Toast) => setToasts((current) => [...current, t]);
  const replace = (row: DocRow) => setRows((current) => (current.some((r) => r.row_id === row.row_id) ? current.map((r) => (r.row_id === row.row_id ? row : r)) : [...current, row]));

  async function addAdditional(chosen: File | undefined) {
    if (!chosen) return;
    setProgress(0);
    const values: Record<string, string> = { nombre: name.trim() };
    if (expiry) values.fecha_vencimiento = expiry;
    const outcome = await send(`${API}${section.organization_id}/documentacion/personalizada/`, form(values, chosen), setProgress);
    setProgress(null);
    if (file.current) file.current.value = "";
    if (outcome.ok) {
      replace(outcome.row);
      toast({ message: "Documento adicional agregado con éxito.", level: "success" });
      setName(""); setExpiry("");
    } else toast({ message: outcome.error === null ? "Error de red al agregar el documento." : outcome.error || "No se pudo agregar el documento.", level: "error" });
  }
  function pickAdditional() {
    if (!name.trim()) { toast({ message: "Debe indicar un nombre para el documento.", level: "error" }); nameInput.current?.focus(); return; }
    file.current?.click();
  }
  return (
    <div className="tabla-legajo card-programa card-alco" id="documentacion">
      <InsumosToastList messages={toasts} />
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="mb-0">Documentación de la Organización</h5>
        <span className="badge" style={{ background: "rgba(245, 166, 35, 0.2)", color: "var(--gold)", border: "1px solid var(--gold)" }}>{section.category}</span>
      </div>
      <div>
        <table className="table table-sm documentacion-table">
          <thead><tr><th>Documento</th><th>Estado / validación</th><th>Archivo</th><th>Vencimiento / carga</th><th>Número de GDE</th></tr></thead>
          <tbody>
            {rows.map((row) => <DocumentRow key={row.row_id} row={row} organizationId={section.organization_id} onRow={replace} toast={toast} askObservations={(done) => setRectify(() => done)} />)}
            {rows.length === 0 && <tr><td colSpan={5} className="text-center">No hay documentación configurada.</td></tr>}
          </tbody>
        </table>
      </div>
      {section.can_send && (
        <div className="mt-3 pt-3 border-top" id="org-doc-adicional">
          <h6 className="mb-2">Documentación Adicional</h6>
          <p className="small text-muted mb-2">Opcional. Indicá un nombre y adjuntá el archivo. Podés agregar tantos como necesites.</p>
          <div className="row g-2 align-items-end">
            <div className="col-md-5">
              <label className="form-label small mb-1" htmlFor="nuevoDocOrgNombre">Nombre del documento</label>
              <input ref={nameInput} type="text" id="nuevoDocOrgNombre" className="form-control form-control-sm" maxLength={255} placeholder="Nombre del documento adicional" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="col-md-3">
              <label className="form-label small mb-1" htmlFor="nuevoDocOrgVencimiento">Vencimiento (opcional)</label>
              <input type="date" id="nuevoDocOrgVencimiento" className="form-control form-control-sm" value={expiry} onChange={(e) => setExpiry(e.target.value)} />
            </div>
            <div className="col-md-4">
              <input ref={file} type="file" id="nuevoDocOrgArchivo" className="d-none" accept={ACCEPT} onChange={(e) => void addAdditional(e.target.files?.[0])} />
              <button type="button" id="btnAgregarDocOrg" className="btn btn-sm btn-primary" disabled={progress !== null} onClick={pickAdditional}><i className="fas fa-plus" /> Agregar documento adicional</button>
            </div>
          </div>
          <div className={`progress mt-2 documentacion-upload-progress${progress === null ? " d-none" : ""}`} id="org-doc-adicional-progress-container">
            <div className="progress-bar progress-bar-striped" role="progressbar" id="org-doc-adicional-progress-bar" style={{ width: `${progress ?? 0}%` }}>{progress ?? 0}%</div>
          </div>
        </div>
      )}
      {rectify && <RectifyModal onDone={(observations) => { rectify(observations); setRectify(null); }} />}
    </div>
  );
}

// --- history page ---------------------------------------------------------------------------

type Version = { id: number; created: string; state: string; expiry: string; observations: string; url: string };
export type HistorialData = {
  organization: { id: number; name: string }; document: { id: number; name: string }; files: Version[]; urls: { list: string; legajo: string };
};

export function historialValid(v: unknown): v is HistorialData {
  return record(v) && record(v.organization) && text(v.organization.name) && record(v.document) && text(v.document.name) && Array.isArray(v.files) &&
    v.files.every((f) => record(f) && text(f.created) && text(f.state) && text(f.url)) && record(v.urls) && internal(v.urls.list) && internal(v.urls.legajo);
}

const BADGES: Record<string, string> = { Aceptado: "bg-success", Rectificar: "bg-danger", "A Validar Abogado": "bg-primary" };

function Historial({ data }: { data: HistorialData }) {
  return (
    <div className="card">
      <div className="card-header d-flex justify-content-between align-items-center">
        <div>
          <h3 className="card-title mb-0">{data.document.name}</h3>
          <div className="text-muted small">{data.organization.name}</div>
        </div>
      </div>
      <div className="card-body">
        <table className="table table-bordered table-striped">
          <thead><tr><th>Fecha de carga</th><th>Estado</th><th>Fecha de vencimiento</th><th>Observaciones</th><th>Archivo</th></tr></thead>
          <tbody>
            {data.files.map((f) => (
              <tr key={f.id}>
                <td>{f.created}</td>
                <td><span className={`badge ${BADGES[f.state] ?? "bg-secondary"}`}>{f.state}</span></td>
                <td>{f.expiry}</td>
                <td>{f.observations}</td>
                <td><a href={f.url} target="_blank" rel="noreferrer" className="btn btn-primary btn-sm">Ver archivo</a></td>
              </tr>
            ))}
            {data.files.length === 0 && <tr><td colSpan={5} className="text-center text-muted py-4">No hay documentos cargados.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function OrganizacionHistorial({ id, documentId }: { id: number; documentId: number }) {
  const [state] = useMainResource(`${API}${id}/documentacion/${documentId}/historial/`, historialValid);
  return renderMain(state, "Cargando historial…", (data) => ({
    title: "Historial de documentacion",
    breadcrumb: <Breadcrumb items={[{ text: "Organizaciones", url: data.urls.list }, { text: data.organization.name, url: data.urls.legajo }, { text: "Historial", url: null }]} />,
    content: <Historial data={data} />,
  }));
}

// Native URL (trailing slash, as `urls.py` declares it).
export const organizacionDocumentosRoute: RouteDefinition<{ id: number; documentId: number }> = {
  name: "comedores-organizaciones-documentos",
  match(pathname) {
    const found = /^\/organizaciones\/([1-9]\d{0,14})\/documentacion\/([1-9]\d{0,14})\/historial\/$/.exec(pathname);
    return found ? { id: Number(found[1]), documentId: Number(found[2]) } : null;
  },
  render: ({ id, documentId }) => <OrganizacionHistorial id={id} documentId={documentId} />,
};
