/* eslint-disable react-refresh/only-export-components -- the list screen exports its validator and navigation seam for the unit tests. */
import { useCallback, useEffect, useRef, useState } from "react";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { internal, record, text } from "./MainFrame";

/**
 * `expedientespagos_list.html`: title, «Nuevo Expediente de Pago» (four read
 * codes), `data_table.html` with custom cells, the «Ver» action and the column
 * preferences modal (`column_config_modal.html` + `column_config.js`). The
 * table does not paginate, like the native include.
 */
type Column = { key: string; title: string; active: boolean; required: boolean; default: boolean };
type Columns = { list_key: string; endpoint: string; modal_id: string; script_id: string; available: Column[] };
type Row = { id: number; cells: string[]; detail_url: string };
export type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type ExpedientesListData = {
  comedor_id: number; can_create: boolean; create_url: string; breadcrumb_url: string;
  columns: Columns; headers: string[]; results: Row[]; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
export const messagesValid = (v: unknown): v is Message[] =>
  Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));

export function listValid(v: unknown): v is ExpedientesListData {
  if (!record(v) || !record(v.columns)) return false;
  const c = v.columns;
  return int(v.comedor_id) && typeof v.can_create === "boolean" && internal(v.create_url) && internal(v.breadcrumb_url) &&
    text(c.list_key) && internal(c.endpoint) && text(c.modal_id) && text(c.script_id) &&
    Array.isArray(c.available) && c.available.every((x) => record(x) && text(x.key) && text(x.title) && typeof x.active === "boolean" && typeof x.required === "boolean") &&
    Array.isArray(v.headers) && v.headers.every(text) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && int(r.id) && internal(r.detail_url) && Array.isArray(r.cells) && r.cells.every(text)) &&
    messagesValid(v.messages);
}

/** Full-page reload after saving the column preferences; replaceable in tests. */
export const expedientesNavigation = {
  assign: (to: string) => window.location.assign(to),
  reload: () => window.location.reload(),
};

function ColumnModal({ columns, close }: { columns: Columns; close: () => void }) {
  const [order, setOrder] = useState(columns.available.map((c) => c.key));
  const [selected, setSelected] = useState(() => columns.available.filter((c) => c.active).map((c) => c.key));
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const modal = useRef<HTMLDivElement>(null);
  const busy = useRef(false);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const before = document.body.style.overflow;
    document.body.classList.add("modal-open");
    document.body.style.overflow = "hidden";
    modal.current?.focus();
    const key = (e: KeyboardEvent) => { if (e.key === "Escape" && !busy.current) close(); };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      document.body.classList.remove("modal-open");
      document.body.style.overflow = before;
      previous?.focus();
    };
  }, [close]);
  const save = useCallback(async (reset: boolean) => {
    if (busy.current) return;
    const values = order.filter((k) => selected.includes(k));
    setError("");
    if (!reset && !values.length) { setError("Debe haber al menos una columna visible."); return; }
    const fallback = reset ? "No se pudo restablecer la configuracion." : "No se pudo guardar la configuracion.";
    busy.current = true; setPending(true);
    try {
      const response = await fetch(columns.endpoint, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": leerCookie("csrftoken") ?? "", "X-Requested-With": "XMLHttpRequest" },
        body: JSON.stringify(reset ? { list_key: columns.list_key, reset: true } : { list_key: columns.list_key, columns: values }),
      });
      const result: unknown = await response.json().catch(() => null);
      if (!response.ok) throw new Error(record(result) && text(result.error) ? result.error : fallback);
      expedientesNavigation.reload();
    } catch (e: unknown) {
      setError(e instanceof Error && e.message ? e.message : fallback);
      setPending(false); busy.current = false;
    }
  }, [columns, order, selected]);
  const move = (key: string, offset: number) => setOrder((current) => {
    const i = current.indexOf(key), j = i + offset;
    if (j < 0 || j >= current.length) return current;
    const copy = [...current]; [copy[i], copy[j]] = [copy[j], copy[i]];
    return copy;
  });
  const titleId = `${columns.modal_id}-title`;
  return <>
    <div className="modal-backdrop fade show" />
    <div ref={modal} className="modal fade show d-block" id={columns.modal_id} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby={titleId}
      data-column-config="true" data-config-id={columns.script_id} onClick={(e) => { if (e.target === e.currentTarget && !pending) close(); }}>
      <div className="modal-dialog modal-dialog-centered modal-lg"><div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title" id={titleId}>Columnas visibles</h5>
          <button type="button" className="btn-close" aria-label="Cerrar" disabled={pending} onClick={close} />
        </div>
        <div className="modal-body">
          <p className="text-muted mb-3">Seleccioná qué columnas mostrar y ordenalas con las flechas.</p>
          <div className="list-group column-config-list">
            {order.map((key) => {
              const column = columns.available.find((c) => c.key === key);
              if (!column) return null;
              const id = `${columns.modal_id}-${key}`;
              return <div key={key} className="list-group-item d-flex flex-wrap align-items-center justify-content-between gap-2" data-column-key={key}>
                <div className="form-check">
                  <input className="form-check-input column-config-checkbox" type="checkbox" id={id} checked={selected.includes(key)} disabled={pending || column.required}
                    onChange={(e) => setSelected((current) => (e.target.checked ? [...current, key] : current.filter((k) => k !== key)))} />
                  {" "}<label className="form-check-label" htmlFor={id}>{column.title}</label>
                </div>
                <div className="btn-group btn-group-sm" role="group">
                  <button type="button" className="btn btn-light column-move-up" title="Mover arriba" disabled={pending} onClick={() => move(key, -1)}><i className="fas fa-arrow-up" /></button>
                  <button type="button" className="btn btn-light column-move-down" title="Mover abajo" disabled={pending} onClick={() => move(key, 1)}><i className="fas fa-arrow-down" /></button>
                </div>
              </div>;
            })}
          </div>
          <div className={`alert alert-danger mt-3 column-config-error${error ? "" : " d-none"}`}>{error}</div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-outline-secondary column-config-reset" disabled={pending} onClick={() => void save(true)}>Restablecer</button>
          <button type="button" className="btn btn-primary column-config-save" disabled={pending} onClick={() => void save(false)}>Guardar</button>
        </div>
      </div></div>
    </div>
  </>;
}

export function ExpedientesListContent({ data }: { data: ExpedientesListData }) {
  const [configOpen, setConfigOpen] = useState(false);
  const close = useCallback(() => setConfigOpen(false), []);
  return <>
    <InsumosToastList messages={data.messages} />
    <div className="container mt-4">
      <h1>Listado de Expedientes de Pagos</h1>
      {data.can_create && <div className="mb-3">
        <a href={data.create_url} className="btn btn-primary"><i className="fas fa-plus" /> Nuevo Expediente de Pago</a>
      </div>}
      <div className="row mt-5 max-width-100"><div className="col-12"><div className="card"><div className="card-body">
        <div className="d-flex justify-content-start mb-2">
          <button type="button" className="btn btn-outline-warning btn-sm" data-bs-toggle="modal" data-bs-target={`#${data.columns.modal_id}`}
            onClick={() => setConfigOpen(true)}>Configurar columnas</button>
        </div>
        {configOpen && <ColumnModal columns={data.columns} close={close} />}
        <div className="table-responsive-lg">
          <table className="table table-bordered table-striped projects ">
            <thead><tr>
              {data.headers.map((h, i) => <th key={i}>{h}</th>)}
              <th style={{ width: "15%" }} className="notexport">Acciones</th>
            </tr></thead>
            <tbody>
              {data.results.length ? data.results.map((row) => <tr key={row.id}>
                {row.cells.map((cell, i) => <td key={i}>{cell}</td>)}
                <td className="project-actions text-right">
                  <div className="action-buttons flex-wrap flex-lg-nowrap" role="group">
                    <a href={row.detail_url} className="btn btn-info " title="Ver"><i className="fas fa-eye" /> Ver</a>
                  </div>
                </td>
              </tr>) : <tr><td colSpan={data.headers.length + 1} className="text-center text-muted py-4">No hay expedientes de pagos registrados para este comedor.</td></tr>}
            </tbody>
          </table>
        </div>
      </div></div></div></div>
    </div>
  </>;
}
