/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { leerCookie } from "@sisoc/api";
import { safeInternalPath } from "../webAccess";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { useBootstrapModal } from "./inspeccionesModal";
import { UNCERTAIN, postApi, relevamientosNavigation, setFlash, useToasts } from "./relevamientosApi";
import RelevamientoBaja from "./relevamientosBaja";
import type { RouteDefinition } from "./types";

/**
 * R01.01 `relevamiento_list.html` and `relevamiento_detail.html`. Data comes from
 * `/api/web/comedores/relevamientos/`, which runs the native views; the data
 * sections of the detail are the rendered native partial. The modals post a
 * native form to the CO07 popup view (`relevamiento_create_edit_ajax`), as today.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Seguimiento = { id: number; fecha: string; estado: string; estado_badge: string; tipo: string; numero_orden: number; origen: string; sincronizado_gestionar: boolean; detalle_url: string };
type Item = { id: number; fecha: string; estado: string; estado_badge: string; numero_if: string | null; origen: string; sincronizado_gestionar: boolean; has_seguimiento: boolean; detalle_url: string; seguimientos: Seguimiento[] };
type Acta = { id: number; fecha_hora: string; tecnico: string; origen: string; prestaciones_count: number; estado: string; estado_badge: string; a_subsanar: boolean; detalle_url: string; editar_url: string };
type Pnud = { id: number; formulario_display: string; fecha_hora: string; tecnico: string; origen: string; estado: string; estado_badge: string; a_subsanar: boolean; detalle_url: string };
type Option = { value: string; label: string };
export type RelevamientosListData = {
  comedor: { id: number; nombre: string }; encabezado: string; relevamientos: Item[]; actas: Acta[]; seguimientos_pnud: Pnud[];
  opciones_alta: Option[]; opciones_seguimiento: Option[];
  capabilities: { add_relevamiento: boolean; change_relevamiento: boolean; add_actacomplementaria: boolean; change_actacomplementaria: boolean };
  urls: { listado: string; alta: string; crear_formulario?: string | null; acta_crear: string; territoriales: string; territoriales_sincronizar: string; numero_if: string }; messages: Message[];
};
export type TreeNode = string | { t: string; a: Record<string, string>; c: TreeNode[] };
type Detalle = { id: number; fecha: string; estado: string; estado_badge: string; estado_validacion: string; a_subsanar: boolean; origen: string; sincronizado_gestionar: boolean; detalle_url: string; editar_url: string; eliminar_url: string; eliminar_api: string; numero_orden: number; tipo: string };
type Adjunto = { id: number; nombre_original: string; es_pdf: boolean; tamano: string; fecha_subida: string; descargar_url: string };
export type RelevamientoDetailData = {
  relevamiento: {
    id: number; comedor: { id: number; nombre: string }; nombre_comedor: string | null; fecha_visita: string; estado: string | null; estado_visible: string; estado_badge: string;
    estado_validacion: string; a_subsanar: boolean; esta_validado: boolean; sin_cargar: boolean; origen: string; sincronizado_gestionar: boolean;
    observaciones_coordinador: string; coordinador: string | null; fecha_revision_coordinador: string | null;
  };
  timeline: { id: number; step: number; fecha: string; estado: string; card_class: string; status_class: string }[];
  secciones: TreeNode[]; titulos: string[]; seguimientos: Detalle[]; adjuntos: Adjunto[];
  pdf: { disponible: boolean; url: string; oficial: boolean; fecha_oficial: string | null };
  capabilities: { change_relevamiento: boolean; review_relevamiento: boolean; change_primerseguimiento: boolean; delete_primerseguimiento: boolean; view_logentry: boolean };
  urls: { listado: string; comedores: string; comedor: string; alta: string; editar_formulario?: string | null; eliminar: string; revision: string; revision_api: string; historial: string; territoriales: string; territoriales_sincronizar: string };
  messages: Message[];
};

const API = "web/comedores/relevamientos/";
const LEVELS = ["success", "error", "warning", "info"];
export const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
export const bool = (v: unknown): v is boolean => typeof v === "boolean";
export const arr = (v: unknown, each: (x: unknown) => boolean) => Array.isArray(v) && v.every(each);
export const messagesValid = (v: unknown) => arr(v, (m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
const optionsValid = (v: unknown) => arr(v, (o) => record(o) && text(o.value) && text(o.label));
const seguimientoValid = (s: unknown) => record(s) && integer(s.id) && text(s.fecha) && text(s.estado) && text(s.estado_badge) && text(s.tipo) && integer(s.numero_orden) && text(s.origen) && bool(s.sincronizado_gestionar) && internal(s.detalle_url);

export function listValid(v: unknown): v is RelevamientosListData {
  if (!record(v) || !record(v.comedor) || !record(v.capabilities) || !record(v.urls)) return false;
  const caps = v.capabilities, urls = v.urls;
  return integer(v.comedor.id) && text(v.comedor.nombre) && text(v.encabezado) &&
    arr(v.relevamientos, (r) => record(r) && integer(r.id) && text(r.fecha) && text(r.estado) && text(r.estado_badge) && (r.numero_if === null || text(r.numero_if)) &&
      text(r.origen) && bool(r.sincronizado_gestionar) && bool(r.has_seguimiento) && internal(r.detalle_url) && arr(r.seguimientos, seguimientoValid)) &&
    arr(v.actas, (a) => record(a) && integer(a.id) && text(a.fecha_hora) && text(a.tecnico) && text(a.origen) && integer(a.prestaciones_count) && text(a.estado) &&
      text(a.estado_badge) && bool(a.a_subsanar) && internal(a.detalle_url) && internal(a.editar_url)) &&
    arr(v.seguimientos_pnud, (p) => record(p) && integer(p.id) && text(p.formulario_display) && text(p.fecha_hora) && text(p.tecnico) && text(p.origen) &&
      text(p.estado) && text(p.estado_badge) && bool(p.a_subsanar) && internal(p.detalle_url)) &&
    optionsValid(v.opciones_alta) && optionsValid(v.opciones_seguimiento) &&
    ["add_relevamiento", "change_relevamiento", "add_actacomplementaria", "change_actacomplementaria"].every((k) => bool(caps[k])) &&
    ["listado", "alta", "acta_crear", "territoriales", "territoriales_sincronizar", "numero_if"].every((k) => internal(urls[k])) && (urls.crear_formulario == null || internal(urls.crear_formulario)) && messagesValid(v.messages);
}

export function detailValid(v: unknown): v is RelevamientoDetailData {
  if (!record(v) || !record(v.relevamiento) || !record(v.capabilities) || !record(v.pdf) || !record(v.urls)) return false;
  const r = v.relevamiento, caps = v.capabilities, urls = v.urls;
  return integer(r.id) && record(r.comedor) && integer(r.comedor.id) && text(r.comedor.nombre) && (r.nombre_comedor === null || text(r.nombre_comedor)) &&
    text(r.fecha_visita) && (r.estado === null || text(r.estado)) && text(r.estado_visible) && text(r.estado_badge) && text(r.estado_validacion) && bool(r.a_subsanar) && bool(r.esta_validado) &&
    bool(r.sin_cargar) && text(r.origen) && bool(r.sincronizado_gestionar) && text(r.observaciones_coordinador) && (r.coordinador === null || text(r.coordinador)) &&
    (r.fecha_revision_coordinador === null || text(r.fecha_revision_coordinador)) &&
    arr(v.timeline, (t) => record(t) && integer(t.id) && integer(t.step) && text(t.fecha) && text(t.estado) && text(t.card_class) && text(t.status_class)) &&
    arr(v.secciones, nodeValid) && arr(v.titulos, text) &&
    arr(v.seguimientos, (s) => record(s) && integer(s.id) && integer(s.numero_orden) && text(s.tipo) && text(s.fecha) && text(s.estado) && text(s.estado_badge) && text(s.estado_validacion) &&
      bool(s.a_subsanar) && text(s.origen) && bool(s.sincronizado_gestionar) && internal(s.detalle_url) && internal(s.editar_url) && internal(s.eliminar_url) && internal(s.eliminar_api)) &&
    arr(v.adjuntos, (a) => record(a) && integer(a.id) && text(a.nombre_original) && bool(a.es_pdf) && text(a.tamano) && text(a.fecha_subida) && internal(a.descargar_url)) &&
    bool(v.pdf.disponible) && internal(v.pdf.url) && bool(v.pdf.oficial) && (v.pdf.fecha_oficial === null || text(v.pdf.fecha_oficial)) &&
    ["change_relevamiento", "review_relevamiento", "change_primerseguimiento", "delete_primerseguimiento", "view_logentry"].every((k) => bool(caps[k])) &&
    ["listado", "comedores", "comedor", "alta", "eliminar", "revision", "revision_api", "historial", "territoriales", "territoriales_sincronizar"].every((k) => internal(urls[k])) && (urls.editar_formulario == null || internal(urls.editar_formulario)) && messagesValid(v.messages);
}

export const nodeValid = (n: unknown): boolean => text(n) || (record(n) && text(n.t) && record(n.a) && Object.values(n.a).every(text) && arr(n.c, nodeValid));
export const CSS = <link rel="stylesheet" href="/static/custom/css/comedorRelevamiento.css" />;
export const path = (url: string) => safeInternalPath(url) ?? "/";
export const csrf = () => <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;

// --- Modals (Bootstrap 5.3 look, native POST) --------------------------------

type Territorial = { gestionar_uid: string; nombre: string };
const norm = (v: string) => v.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
const payload = (t: Territorial) => JSON.stringify({ gestionar_uid: t.gestionar_uid, nombre: t.nombre });

type Meta = { fuente?: string; total?: number; desactualizados?: boolean };
type Status = { text: string; cls: string };
type Toast = { message: string; type: "success" | "error" };
const MAX_AGE = 10 * 60 * 1000;

/** `updateStatus` of `comedordetail_territorial_cache.js`. */
function statusOf(meta: Meta): Status {
  const total = meta.total ?? 0;
  const by: Record<string, Status> = {
    cache_provincia: { text: `${total} territoriales (desde cache rápido)`, cls: "status-success" },
    db_provincia: { text: `${total} territoriales (desde cache local)`, cls: meta.desactualizados ? "status-warning" : "status-success" },
    gestionar_provincia_sync: { text: `${total} territoriales (sincronizado)`, cls: "status-success" },
    fallback_provincia: { text: `${total} territoriales (datos antiguos)`, cls: "status-warning" },
    sin_datos: { text: `${total} territoriales (sin datos)`, cls: "status-warning" },
    comedor_no_encontrado: { text: "Comedor no encontrado", cls: "status-error" },
    datos_ejemplo: { text: `${total} territoriales (datos de desarrollo)`, cls: "status-info" },
    vacio: { text: `${Number(total) || 0} territoriales (sin datos)`, cls: "status-warning" },
  };
  const status = by[meta.fuente ?? ""] ?? { text: "Error cargando territoriales", cls: "status-error" };
  if (meta.desactualizados && meta.fuente !== "fallback_provincia") return { text: `${status.text} (algunos desactualizados)`, cls: "status-warning" };
  return status;
}

/** Cache, status line and forced sync of the CO07 territorial list (`comedordetail_territorial_cache.js`). */
function useTerritoriales(url: string, syncUrl: string) {
  const [list, setList] = useState<(Territorial & { desactualizado?: boolean })[]>([]);
  const [stale, setStale] = useState(false);
  const [status, setStatus] = useState<Status>({ text: "Cargando territoriales...", cls: "status-loading" });
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<Toast | null>(null);
  const last = useRef<number | null>(null);
  const busy = useRef(false);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 5000);
    return () => window.clearTimeout(timer);
  }, [toast]);
  const apply = (d: unknown) => {
    if (!record(d) || d.success !== true) throw new Error((record(d) && text(d.error) ? d.error : "") || "Error desconocido");
    const territoriales = Array.isArray(d.territoriales) ? (d.territoriales as Territorial[]) : [];
    const meta = (record(d.meta) ? d.meta : { total: territoriales.length }) as Meta;
    setList(territoriales);
    setStale(Boolean(meta.desactualizados));
    setStatus(statusOf(meta));
  };
  const fail = (error: unknown) => {
    const message = error instanceof Error ? error.message : String(error);
    setStatus({ text: `Error: ${message}`, cls: "status-error" });
    setToast({ message: `Error cargando territoriales: ${message}`, type: "error" });
  };
  const run = (request: Promise<Response>, after: () => void) => {
    busy.current = true;
    setLoading(true);
    request
      .then((r) => { if (!r.ok && r.status >= 500) throw new Error(`HTTP ${r.status}: ${r.statusText}`); return r.json(); })
      .then((d: unknown) => { if (!alive.current) return; apply(d); after(); })
      .catch((e: unknown) => { if (alive.current) fail(e); })
      .finally(() => { busy.current = false; if (alive.current) setLoading(false); });
  };
  const load = (force = false) => {
    if (busy.current) return;
    run(fetch(`${url}${force ? "?force_sync=true" : ""}`, { headers: { "X-Requested-With": "XMLHttpRequest", "Cache-Control": force ? "no-cache" : "max-age=600" } }), () => { last.current = Date.now(); });
  };
  const sync = () => {
    if (busy.current) return;
    setStatus({ text: "Sincronizando con GESTIONAR...", cls: "status-loading" });
    run(fetch(syncUrl, { method: "POST", headers: { "X-CSRFToken": leerCookie("csrftoken") ?? "", "X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json" } }),
      () => setToast({ message: "Territoriales sincronizados correctamente", type: "success" }));
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps -- one load per modal, like `init()`.
  useEffect(() => { load(); }, [url]);
  const refresh = () => { if (last.current === null || Date.now() - last.current > MAX_AGE) load(); };
  return { list, stale, notify: (message: string) => setToast({ message, type: "error" }), status: loading && status.cls !== "status-loading" ? { text: "Cargando...", cls: "status-loading" } : status, loading, sync, refresh, toast };
}

const TERRITORIAL_CSS = `
.territorial-status { margin: 8px 0; padding: 8px 12px; border-radius: 4px; background: #f8f9fa; border: 1px solid #dee2e6; display: flex; justify-content: space-between; align-items: center; font-size: 0.875rem; }
.status-text { flex: 1; }
.status-success { color: #28a745; }
.status-warning { color: #856404; background-color: #fff3cd; }
.status-error { color: #721c24; background-color: #f8d7da; }
.status-info { color: #0c5460; background-color: #d1ecf1; }
.status-loading { color: #0c5460; }
.territorial-autocomplete { position: relative; }
.territorial-suggestions { position: absolute; top: calc(100% + 4px); left: 0; right: 0; z-index: 1060; max-height: 260px; overflow-y: auto; border: 1px solid #ced4da; border-radius: 0.375rem; background: #fff; box-shadow: 0 0.75rem 1.5rem rgba(0, 0, 0, 0.12); }
.territorial-suggestion-item, .territorial-suggestion-empty { width: 100%; display: block; padding: 0.55rem 0.75rem; border: 0; background: transparent; text-align: left; font-size: 0.875rem; color: #212529; }
.territorial-suggestion-item:hover, .territorial-suggestion-item:focus { background: #f8f9fa; color: #212529; outline: none; }
.territorial-suggestion-stale { color: #856404; }
.territorial-suggestion-empty { color: #6c757d; }
.sync-btn { background: #007bff; border: none; color: white; padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 0.75rem; }
.sync-btn:hover { background: #0056b3; }
.sync-btn:disabled { background: #6c757d; cursor: not-allowed; }
.territorial-loading { opacity: 0.6; cursor: wait; }
`;

type Territoriales = ReturnType<typeof useTerritoriales>;

/** `#territorial-status`: the status line and the GESTIONAR sync button. */
function TerritorialStatus({ t }: { t: Territoriales }) {
  return <>
    <style>{TERRITORIAL_CSS}</style>
    <div id="territorial-status" className="territorial-status">
      <span className={`status-text ${t.status.cls}`}>{t.status.text}</span>
      <button className="sync-btn" title="Sincronizar con GESTIONAR" disabled={t.loading} onClick={(e) => { e.preventDefault(); t.sync(); }}>
        <i className={`fas fa-sync-alt${t.loading ? " fa-spin" : ""}`} />
      </button>
    </div>
    {t.toast && createPortal(<div className={`toast toast-${t.toast.type}`} style={{ position: "fixed", top: "20px", right: "20px", padding: "12px 20px", borderRadius: "4px", color: "white", zIndex: 10000, opacity: 1, backgroundColor: t.toast.type === "success" ? "#28a745" : "#dc3545" }}>{t.toast.message}</div>, document.body)}
  </>;
}

export function Modal({ id, close, trigger, children, footer, action, onSubmit }: { id: string; title: string; close: () => void; trigger: HTMLElement | null; children: ReactNode; footer: ReactNode; action: string; onSubmit?: (fields: URLSearchParams) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useBootstrapModal(ref, close, trigger);
  // The dialog stays in the page flow, like the native one, so Tab leaves its last control the same way; only the backdrop goes to `<body>`.
  return <>
    <div className="modal fade show" id={id} tabIndex={-1} aria-labelledby={`${id}Label`} aria-modal="true" role="dialog" style={{ display: "block" }} ref={ref}
      onMouseDown={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div className="modal-dialog modal-dialog-centered"><div className="modal-content">
        <form method="post" action={path(action)}
          onSubmit={onSubmit ? (e) => { e.preventDefault(); onSubmit(new URLSearchParams(new FormData(e.currentTarget) as unknown as Record<string, string>)); } : undefined}>
          {csrf()}
          {children}
          <div className="modal-footer">{footer}</div>
        </form>
      </div></div>
    </div>
    {createPortal(<div className="modal-backdrop fade show" />, document.body)}
  </>;
}

export const ModalHeader = ({ id, title, close }: { id: string; title: string; close: () => void }) => (
  <div className="modal-header"><h5 className="modal-title" id={`${id}Label`}>{title}</h5><button type="button" className="btn-close" aria-label="Cerrar" onClick={close} /></div>
);
export const Cancel = ({ close }: { close: () => void }) => <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>;

function AltaModal({ data, close, trigger }: { data: RelevamientosListData; close: () => void; trigger: HTMLElement | null }) {
  const t = useTerritoriales(data.urls.territoriales, data.urls.territoriales_sincronizar);
  const territoriales = t.list;
  const [query, setQuery] = useState("");
  const [value, setValue] = useState("");
  const [open, setOpen] = useState(false);
  // A click anywhere else hides the suggestions (`document` click listener of the native script).
  useEffect(() => {
    const away = (e: MouseEvent) => {
      const target = e.target as Node;
      if (document.getElementById("new_territorial_suggestions")?.contains(target) || target === document.getElementById("new_territorial_input")) return;
      setOpen(false);
    };
    document.addEventListener("click", away);
    return () => document.removeEventListener("click", away);
  }, []);
  const matches = territoriales.filter((x) => !norm(query) || norm(x.nombre).includes(norm(query))).slice(0, 8);
  const exact = territoriales.find((x) => norm(x.nombre) === norm(query) && norm(query));
  const pick = (t: Territorial) => { setQuery(t.nombre); setValue(payload(t)); setOpen(false); };
  const id = "modalRelevamientoNuevo";
  return (
    <Modal id={id} title="Nuevo acompañamiento territorial" close={close} trigger={trigger} action={data.urls.alta}
      footer={<><Cancel close={close} /><button type="submit" className="btn btn-primary"
        onClick={(e) => { if (!exact) { e.preventDefault(); setValue(""); t.notify("Seleccioná un territorial de la lista antes de crear el relevamiento."); document.getElementById("new_territorial_input")?.focus(); } else setValue(payload(exact)); }}>Crear acompañamiento territorial</button></>}>
      <ModalHeader id={id} title="Nuevo acompañamiento territorial" close={close} />
      <div className="modal-body">
        <div className="mb-2">
          <label htmlFor="tipo_relevamiento_select" className="form-label">Tipo</label>
          <select id="tipo_relevamiento_select" name="tipo_relevamiento" className="form-select" required defaultValue={data.opciones_alta[0]?.value}>
            {data.opciones_alta.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <TerritorialStatus t={t} />
        <div id="new_territorial_container" className="mb-2 position-relative territorial-autocomplete">
          <label htmlFor="new_territorial_input" className="form-label">Territorial asignado</label>
          <input type="text" id="new_territorial_input" className={`form-control${t.loading ? " territorial-loading" : ""}`} placeholder="Escribí el nombre del territorial" autoComplete="off" aria-autocomplete="list"
            aria-controls="new_territorial_suggestions" required value={query} disabled={t.loading}
            onChange={(e) => { setQuery(e.target.value); setValue(""); setOpen(true); }} onFocus={() => { t.refresh(); setOpen(true); }}
            onKeyDown={(e) => { if (e.key === "Escape") setOpen(false); if (e.key === "Enter" && exact) { e.preventDefault(); pick(exact); } }} />
          <input type="hidden" name="territorial" id="new_territorial_value" value={value} />
          <div id="new_territorial_suggestions" className={`territorial-suggestions${open ? "" : " d-none"}`} role="listbox" aria-label="Sugerencias de territoriales">
            {matches.length ? matches.map((m) => <button key={m.gestionar_uid} type="button" className={`territorial-suggestion-item${m.desactualizado ? " territorial-suggestion-stale" : ""}`} onMouseDown={(e) => { e.preventDefault(); pick(m); }}>{m.nombre}</button>)
              : <div className="territorial-suggestion-empty">No hay territoriales que coincidan</div>}
          </div>
        </div>
        <small className="text-muted">El acompañamiento territorial se crea asignado al territorial seleccionado. Las opciones dependen del programa del comedor.</small>
      </div>
    </Modal>
  );
}

function SeguimientoModal({ data, relevamientoId, close, trigger }: { data: RelevamientosListData; relevamientoId: number; close: () => void; trigger: HTMLElement | null }) {
  const id = "modalSeguimientoNuevo";
  return (
    <Modal id={id} title="Agregar seguimiento" close={close} trigger={trigger} action={data.urls.alta}
      footer={<><Cancel close={close} /><button type="submit" className="btn btn-primary">Crear seguimiento</button></>}>
      <input type="hidden" name="relevamiento_id" id="seguimiento_relevamiento_id" value={relevamientoId} />
      <ModalHeader id={id} title="Agregar seguimiento" close={close} />
      <div className="modal-body">
        <div className="mb-2">
          <label htmlFor="tipo_seguimiento_select" className="form-label">Tipo</label>
          <select id="tipo_seguimiento_select" name="tipo_relevamiento" className="form-select" required defaultValue={data.opciones_seguimiento[0]?.value}>
            {data.opciones_seguimiento.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <small className="text-muted">El seguimiento se agrega a este acompañamiento territorial y hereda su territorial asignado.</small>
      </div>
    </Modal>
  );
}

// --- List ----------------------------------------------------------------------

const CardHead = ({ title, children }: { title: string; children?: ReactNode }) => (
  <div className="card-header d-flex align-items-center">
    <h3 className="card-title font-weight-bold mr-3 pt-1 mb-0">{title}</h3>
    {children}
    <div className="card-tools ml-auto"><button type="button" className="btn btn-tool" data-card-widget="collapse"><i className="fas fa-minus" /></button></div>
  </div>
);
const Rows = ({ children }: { children: ReactNode }) => (
  <div className="card-body card-comments p-0 pb-1"><div className="nav nav-pills row my-3"><div className="col-12"><div className="nav-item d-flex"><div className="comment-text w-100">{children}</div></div></div></div></div>
);

function IfCell({ item, can, url, value, onSaved, onError }: { item: Item; can: boolean; url: string; value: string | null; onSaved: (id: number, numeroIf: string | null, message: string) => void; onError: (message: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    const result = await postApi(url, new URLSearchParams(new FormData(event.currentTarget) as unknown as Record<string, string>));
    if (result.kind === "ok") {
      const saved = result.body.numero_if;
      onSaved(item.id, typeof saved === "string" ? saved : null, result.message);
      setEditing(false);
    } else if (result.kind === "error") onError(result.message);
    else setUncertain(true);
    setPending(false);
  }
  return <>
    <div id={`numero-if-display-${item.id}`} className={`d-flex align-items-end gap-2${editing ? " d-none" : ""}`}>
      <div className="flex-grow-1 d-flex align-items-center gap-2"><span>Número de IF:</span><span className="fw-semibold">{value || "Sin número de IF"}</span></div>
      {can && <button type="button" className="btn btn-sm btn-primary mb-0 py-1 px-2" onClick={() => setEditing(true)}>Actualizar IF</button>}
    </div>
    {can && editing && (
      <form method="post" id={`numero-if-form-${item.id}`} className="d-flex align-items-end gap-2" onSubmit={submit}>
        {csrf()}
        <input type="hidden" name="relevamiento_id" value={item.id} />
        <div className="flex-grow-1"><label className="form-label mb-1">Número de IF</label>
          <input type="text" name="numero_if" maxLength={255} className="form-control form-control-sm" defaultValue={value ?? ""} autoFocus /></div>
        <button type="submit" className="btn btn-sm btn-primary mb-0" disabled={pending || uncertain}>Guardar</button>
        <button type="button" className="btn btn-sm btn-secondary mb-0" onClick={() => setEditing(false)}>Cancelar</button>
        {uncertain && <UncertainNotice />}
      </form>
    )}
  </>;
}

/** A lost answer is never resubmitted: the page is reloaded by GET to read the real state. */
export const UncertainNotice = () => (
  <div role="alert" className="alert alert-warning mb-2">
    {UNCERTAIN}{" "}<button type="button" className="btn btn-link p-0 align-baseline" onClick={() => relevamientosNavigation.assign(window.location.pathname + window.location.search)}>Recargar</button>
  </div>
);

const estadoBadge = (item: { estado_badge: string }) => `badge align-self-start ${item.estado_badge}`;

function Parent({ item, data, ifs, onSeguimiento, onSaved, onError }: { item: Item; data: RelevamientosListData; ifs: Record<number, string | null>; onSeguimiento: (id: number, el: HTMLElement) => void; onSaved: (id: number, numeroIf: string | null, message: string) => void; onError: (message: string) => void }) {
  const caps = data.capabilities;
  return <>
    <div className="row align-items-center w-100 mx-0 mb-2">
      <div className="col-3 d-flex"><a href={path(item.detalle_url)}>{item.id} - {item.fecha}</a></div>
      <div className="col-2 d-flex"><span className={estadoBadge(item)}>{item.estado}</span></div>
      <div className="col-5"><div className="d-flex flex-column gap-1">
        {item.sincronizado_gestionar ? <span className="badge bg-success align-self-start">Sincronizado</span> : <span className="badge bg-secondary align-self-start">No sincronizado</span>}
        {item.origen === "app" && <span className="badge bg-primary align-self-start" title="Creado desde la app">App</span>}
        <IfCell item={item} can={caps.change_relevamiento} url={data.urls.numero_if} value={item.id in ifs ? ifs[item.id] : item.numero_if} onSaved={onSaved} onError={onError} />
      </div></div>
      <div className="col-2 d-flex justify-content-end">
        {caps.add_relevamiento && data.opciones_seguimiento.length > 0 && (
          <button type="button" className="btn btn-sm btn-primary mb-0 py-1 px-2" onClick={(e) => onSeguimiento(item.id, e.currentTarget)}>Agregar</button>
        )}
      </div>
    </div>
    {item.seguimientos.map((s) => (
      <div className="row align-items-center w-100 mx-0 mb-2" key={`s${s.id}`}>
        <div className="col-3 d-flex"><div style={{ paddingLeft: "20px" }}><span className="text-muted">└─</span>{" "}<a href={path(s.detalle_url)}>{s.id} - {s.fecha}</a></div></div>
        <div className="col-2 d-flex"><span className={estadoBadge(s)}>{s.estado}</span></div>
        <div className="col-5"><div className="d-flex flex-wrap gap-1">
          <span className="badge bg-info">{s.tipo} #{s.numero_orden}</span>
          {s.origen === "app" && <span className="badge bg-primary" title="Cargado desde la app">App</span>}
          {s.sincronizado_gestionar ? <span className="badge bg-success">Sincronizado</span> : <span className="badge bg-secondary">No sincronizado</span>}
        </div></div>
        <div className="col-2 d-flex justify-content-end" />
      </div>
    ))}
  </>;
}

export function RelevamientosListContent({ data }: { data: RelevamientosListData }) {
  useCardCollapse();
  const { toasts, push } = useToasts(data.messages);
  const [ifs, setIfs] = useState<Record<number, string | null>>({});
  const caps = data.capabilities;
  const [modal, setModal] = useState<{ kind: "alta" } | { kind: "seguimiento"; id: number } | null>(null);
  const [trigger, setTrigger] = useState<HTMLElement | null>(null);
  const open = (next: NonNullable<typeof modal>, el: HTMLElement) => { setTrigger(el); setModal(next); };
  const close = () => setModal(null);
  return <>
    {toasts}
    {CSS}
    <div className="row relevamiento-container"><div className="col-12"><div className="row"><div className="col-12"><div className="card card-informacion">
      <CardHead title="Acompañamiento Territorial">
        {data.urls.crear_formulario && <a href={path(data.urls.crear_formulario)} className="btn btn-outline-primary btn-sm me-2">Cargar formulario</a>}
        {caps.add_relevamiento && <button type="button" className="btn btn-primary btn-sm" onClick={(e) => open({ kind: "alta" }, e.currentTarget)}>Agregar</button>}
      </CardHead>
      <Rows>{data.relevamientos.map((item) => <Parent key={item.id} item={item} data={data} ifs={ifs} onSeguimiento={(id, el) => open({ kind: "seguimiento", id }, el)}
        onSaved={(id, numeroIf, message) => { setIfs((c) => ({ ...c, [id]: numeroIf })); push({ message, level: "success" }); }} onError={(message) => push({ message, level: "error" })} />)}</Rows>
    </div></div></div></div></div>

    <div className="row relevamiento-container mt-3"><div className="col-12"><div className="card card-informacion">
      <CardHead title="Actas complementarias extraordinarias">
        {caps.add_actacomplementaria && <a href={path(data.urls.acta_crear)} className="btn btn-primary btn-sm">Agregar</a>}
      </CardHead>
      <Rows>
        {data.actas.map((a) => (
          <div className="row align-items-center w-100 mx-0 mb-2" key={a.id}>
            <div className="col-3 d-flex"><a href={path(a.detalle_url)}>{a.id} - {a.fecha_hora}</a></div>
            <div className="col-3 d-flex"><p className="mb-0">{a.tecnico}</p></div>
            <div className="col-4 d-flex flex-wrap gap-1">
              {a.origen === "app" ? <span className="badge bg-primary" title="Cargada desde la app">App</span> : <span className="badge bg-light text-dark" title="Cargada desde SISOC">SISOC</span>}
              <span className="badge bg-info">{a.prestaciones_count} prestación{a.prestaciones_count === 1 ? "" : "es"}</span>
              <span className={`badge ${a.estado_badge}`}>{a.estado}</span>
              {a.a_subsanar && <span className="badge bg-danger ml-1">A subsanar</span>}
            </div>
            <div className="col-2 d-flex justify-content-end">
              {caps.change_actacomplementaria && <a href={path(a.editar_url)} className="btn btn-sm btn-primary mb-0 py-1 px-2">Editar</a>}
            </div>
          </div>
        ))}
        {data.actas.length === 0 && <p className="text-muted mb-0 px-2">No hay actas complementarias cargadas para este comedor.</p>}
      </Rows>
    </div></div></div>

    <div className="row relevamiento-container mt-3"><div className="col-12"><div className="card card-informacion">
      <CardHead title="Seguimientos PNUD" />
      <Rows>
        {data.seguimientos_pnud.map((s) => (
          <div className="row align-items-center w-100 mx-0 mb-2" key={s.id}>
            <div className="col-5 d-flex"><a href={path(s.detalle_url)}>{s.id} - {s.formulario_display}</a></div>
            <div className="col-2 d-flex"><p className="mb-0">{s.fecha_hora}</p></div>
            <div className="col-2 d-flex"><p className="mb-0">{s.tecnico}</p></div>
            <div className="col-3 d-flex flex-wrap gap-1">
              <span className={`badge ${s.estado_badge}`}>{s.estado}</span>
              {s.a_subsanar && <span className="badge bg-danger ml-1">A subsanar</span>}
              {s.origen === "app" && <span className="badge bg-primary" title="Cargado desde la app">App</span>}
            </div>
          </div>
        ))}
        {data.seguimientos_pnud.length === 0 && <p className="text-muted mb-0 px-2">No hay seguimientos PNUD cargados para este comedor.</p>}
      </Rows>
    </div></div></div>

    {modal?.kind === "alta" && <AltaModal data={data} close={close} trigger={trigger} />}
    {modal?.kind === "seguimiento" && <SeguimientoModal data={data} relevamientoId={modal.id} close={close} trigger={trigger} />}
  </>;
}

function ListPage({ comedor }: { comedor: string }) {
  const [state] = useMainResource(`${API}${comedor}/`, listValid);
  return renderMain(state, "Cargando acompañamiento territorial…", (data) => ({
    title: `Acompañamiento Territorial - Comedor: ${data.comedor.nombre}`,
    // The native `titulo-pagina` block: an empty name, then the header and the (unset) visit date in two spans.
    heading: <><span className="ml-2 h5"> {data.encabezado}</span><span className="ml-2 h5" /></> as unknown as string,
    breadcrumb: null,
    content: <RelevamientosListContent data={data} />,
  }));
}

// --- Detail --------------------------------------------------------------------

const UNSAFE = /^\s*(javascript|vbscript):/i;
const PROPS: Record<string, string> = { class: "className", colspan: "colSpan", srcset: "srcSet", "aria-label": "aria-label" };
const VOID = new Set(["img", "source", "input"]);
/** Attributes of form widgets: name, constraints and the boolean ones. */
const CONTROL_PROPS: Record<string, string> = {
  name: "name", placeholder: "placeholder", pattern: "pattern", accept: "accept", scope: "scope", autocomplete: "autoComplete", inputmode: "inputMode",
  maxlength: "maxLength", minlength: "minLength", min: "min", max: "max", step: "step", rows: "rows", cols: "cols",
};
const CONTROL_FLAGS: Record<string, string> = { required: "required", disabled: "disabled", readonly: "readOnly", multiple: "multiple" };

/** `style="height: 500px"` as a React style object. */
function styleOf(value: string) {
  const out: Record<string, string> = {};
  for (const part of value.split(";")) {
    const [k, v] = part.split(":");
    if (k && v) out[k.trim().replace(/-([a-z])/g, (_m, c: string) => c.toUpperCase())] = v.trim();
  }
  return out;
}

function propsOf(a: Record<string, string>) {
  const props: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(a)) {
    if ((k === "href" || k === "src" || k === "srcset") && UNSAFE.test(v)) continue;
    if (k === "style") props.style = styleOf(v);
    else if (k === "target" || k === "rel" || k === "title" || k === "loading" || k === "width" || k === "height" || k === "border" || k === "alt" || k === "type" || k === "href" || k === "src" || k === "id" || k === "role" || k.startsWith("aria-") || k.startsWith("data-")) props[PROPS[k] ?? k] = v;
    else if (PROPS[k]) props[PROPS[k]] = k === "colspan" ? Number(v) : v;
    else if (CONTROL_PROPS[k]) props[CONTROL_PROPS[k]] = ["rows", "cols", "maxlength", "minlength"].includes(k) ? Number(v) : v;
    else if (CONTROL_FLAGS[k]) props[CONTROL_FLAGS[k]] = true;
  }
  return props;
}

/** The native partial as React elements: same tags, classes and text (`relevamiento_detail_secciones.html`). */
export function Tree({ nodes }: { nodes: TreeNode[] }) {
  return <>{nodes.map((n, i) => {
    if (typeof n === "string") return n;
    if (n.a.id === "carouselExample") return <Carousel key={i} node={n} />;
    if (n.t === "input" || n.t === "select" || n.t === "textarea") return <Control key={i} node={n} />;
    if (n.t === "option") return <option key={i} value={n.a.value}><Tree nodes={n.c} /></option>;
    const Tag = n.t as "div";
    return VOID.has(n.t) ? <Tag key={i} {...propsOf(n.a)} /> : <Tag key={i} {...propsOf(n.a)}><Tree nodes={n.c} /></Tag>;
  })}</>;
}

/** A form widget as an uncontrolled control: the server's value, selection or text is its default. */
function Control({ node }: { node: Exclude<TreeNode, string> }) {
  const { value, checked, ...rest } = node.a;
  const props = propsOf(rest) as Record<string, unknown>;
  if (node.t === "input") {
    if (node.a.type === "checkbox" || node.a.type === "radio") return <input {...props} value={value} defaultChecked={checked !== undefined} />;
    return <input {...props} defaultValue={value} />;
  }
  if (node.t === "textarea") return <textarea {...props} defaultValue={node.c.filter((c): c is string => typeof c === "string").join("")} />;
  const options = node.c.filter((c): c is Exclude<TreeNode, string> => typeof c !== "string" && c.t === "option");
  const selected = options.filter((o) => o.a.selected !== undefined).map((o) => o.a.value ?? "");
  const initial = node.a.multiple !== undefined ? selected : (selected[0] ?? options[0]?.a.value ?? "");
  return <select {...props} defaultValue={initial}><Tree nodes={node.c} /></select>;
}

const hasClass = (n: TreeNode, c: string): n is Exclude<TreeNode, string> => typeof n !== "string" && (n.a.class ?? "").split(" ").includes(c);

/** `data-bs-ride="carousel"`: auto-advances every 5 s, pauses while hovered or focused; controls and indicators as Bootstrap. */
function Carousel({ node }: { node: Exclude<TreeNode, string> }) {
  const inner = node.c.find((n) => hasClass(n, "carousel-inner"));
  const items = inner && typeof inner !== "string" ? inner.c.filter((n) => hasClass(n, "carousel-item")) : [];
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const go = (delta: number) => setIndex((i) => (i + delta + items.length) % items.length);
  useEffect(() => {
    if (paused || items.length < 2) return;
    const timer = window.setInterval(() => setIndex((i) => (i + 1) % items.length), 5000);
    return () => window.clearInterval(timer);
  }, [paused, index, items.length]);
  return (
    <div id="carouselExample" className="carousel slide" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
      <div className="carousel-indicators">
        {items.map((_m, i) => <button key={i} type="button" className={i === index ? "active" : ""} aria-current={i === index ? "true" : undefined} aria-label={`Slide ${i + 1}`} onClick={() => setIndex(i)} />)}
      </div>
      <div className="carousel-inner">
        {items.map((m, i) => (
          <div key={i} className={`carousel-item${i === index ? " active" : ""}`}><Tree nodes={typeof m === "string" ? [] : m.c} /></div>
        ))}
      </div>
      <button className="carousel-control-prev" type="button" onClick={() => go(-1)}><span className="carousel-control-prev-icon" aria-hidden="true" /><span className="visually-hidden">Anterior</span></button>
      <button className="carousel-control-next" type="button" onClick={() => go(1)}><span className="carousel-control-next-icon" aria-hidden="true" /><span className="visually-hidden">Siguiente</span></button>
    </div>
  );
}

/** AdminLTE `data-card-widget="collapse"`: `collapsed-card`, the card body hidden and the icon swapped. */
export function useCardCollapse() {
  useEffect(() => {
    const click = (e: MouseEvent) => {
      const button = (e.target as Element).closest?.('[data-card-widget="collapse"]');
      const card = button?.closest(".card");
      if (!button || !card) return;
      const collapsed = card.classList.toggle("collapsed-card");
      Array.from(card.children).filter((el) => el.classList.contains("card-body") || el.classList.contains("card-footer")).forEach((el) => { (el as HTMLElement).style.display = collapsed ? "none" : ""; });
      const icon = button.querySelector("i");
      icon?.classList.toggle("fa-minus", !collapsed);
      icon?.classList.toggle("fa-plus", collapsed);
    };
    document.addEventListener("click", click);
    return () => document.removeEventListener("click", click);
  }, []);
}

function AsignarModal({ data, close, trigger }: { data: RelevamientoDetailData; close: () => void; trigger: HTMLElement | null }) {
  const t = useTerritoriales(data.urls.territoriales, data.urls.territoriales_sincronizar);
  const id = "modalAsignarTerritorial";
  return (
    <Modal id={id} title="Asignar territorial" close={close} trigger={trigger} action={data.urls.alta}
      footer={<><Cancel close={close} /><button type="submit" className="btn btn-primary">Asignar</button></>}>
      <input type="hidden" name="relevamiento_id" value={data.relevamiento.id} />
      <ModalHeader id={id} title="Asignar territorial" close={close} />
      <div className="modal-body">
        <div className="mb-2">
          <label htmlFor="update_territorial_select" className="form-label">Territorial asignado</label>
          <TerritorialStatus t={t} />
          <select id="update_territorial_select" name="territorial_editar" className={`form-select${t.loading ? " territorial-loading" : ""}${t.stale ? " territorial-stale" : ""}`} required defaultValue="" disabled={t.loading} onFocus={t.refresh}>
            <option value="" disabled>Seleccionar territorial</option>
            {t.list.map((x) => <option key={x.gestionar_uid} value={payload(x)} className={x.desactualizado || t.stale ? "territorial-stale" : undefined} title={x.desactualizado || t.stale ? "Datos posiblemente desactualizados" : undefined}>{x.nombre}</option>)}
          </select>
        </div>
        <small className="text-muted">Al confirmar, el acompañamiento territorial pasará a estado Visita pendiente.</small>
      </div>
    </Modal>
  );
}

function RevisionModal({ data, close, trigger, onError }: { data: RelevamientoDetailData; close: () => void; trigger: HTMLElement | null; onError: (message: string) => void }) {
  const id = "modalRevisionCoordinador";
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  async function submit(fields: URLSearchParams) {
    setPending(true);
    const result = await postApi(data.urls.revision_api, fields);
    if (result.kind === "ok") {
      setFlash([{ message: result.message, level: "success" }]);
      relevamientosNavigation.assign(result.redirect);
      return;
    }
    if (result.kind === "error") onError(result.message);
    else setUncertain(true);
    setPending(false);
  }
  return (
    <Modal id={id} title="Revisión del coordinador" close={close} trigger={trigger} action={data.urls.revision} onSubmit={submit}
      footer={<><Cancel close={close} /><button type="submit" className="btn btn-primary" disabled={pending || uncertain}>Guardar revisión</button></>}>
      <ModalHeader id={id} title="Revisión del coordinador" close={close} />
      <div className="modal-body">
        <div className="mb-2">
          <label htmlFor="revision_estado_validacion" className="form-label">Resultado</label>
          <select id="revision_estado_validacion" name="estado_validacion" className="form-select" required defaultValue="">
            <option value="" disabled>Seleccionar resultado</option>
            <option value="Validado">Validado</option>
            <option value="A subsanar">A subsanar (devolver al territorial)</option>
          </select>
        </div>
        <div className="mb-2">
          <label htmlFor="revision_observaciones" className="form-label">Observaciones</label>
          <textarea id="revision_observaciones" name="observaciones_coordinador" className="form-control" rows={4} defaultValue={data.relevamiento.observaciones_coordinador}
            placeholder="Qué debe corregir el territorial (obligatorio si devuelve el acompañamiento territorial)" />
        </div>
        <small className="text-muted">Si valida, el territorial ya no podrá modificar el acompañamiento territorial desde la app.</small>
        {uncertain && <UncertainNotice />}
      </div>
    </Modal>
  );
}

function EliminarSeguimientoModal({ s, close, trigger, onError }: { s: Detalle; close: () => void; trigger: HTMLElement | null; onError: (message: string) => void }) {
  const id = `modalEliminarSeguimiento${s.id}`;
  const titulo = `Eliminar ${s.tipo.toLowerCase()} #${s.numero_orden}`;
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  async function submit(fields: URLSearchParams) {
    setPending(true);
    const result = await postApi(s.eliminar_api, fields);
    if (result.kind === "ok") {
      setFlash([{ message: result.message, level: "success" }]);
      relevamientosNavigation.assign(result.redirect);
      return;
    }
    if (result.kind === "uncertain") setUncertain(true);
    else onError(result.kind === "error" ? result.message : "No se pudo completar la operación.");
    setPending(false);
  }
  return (
    <Modal id={id} title={titulo} close={close} trigger={trigger} action={s.eliminar_url} onSubmit={submit}
      footer={<><Cancel close={close} /><button type="submit" className="btn btn-danger" disabled={pending || uncertain}>Eliminar</button></>}>
      <ModalHeader id={id} title={titulo} close={close} />
      <div className="modal-body">
        <p className="mb-2">Esta accion eliminara la instancia del ciclo de seguimiento y dara de baja el registro asociado en GESTIONAR.</p>
        <p className="mb-0 text-muted">No se puede deshacer.</p>
        {uncertain && <UncertainNotice />}
      </div>
    </Modal>
  );
}

function Cycle({ data, onError }: { data: RelevamientoDetailData; onError: (message: string) => void }) {
  const { seguimientos, capabilities: caps } = data;
  const [deleting, setDeleting] = useState<Detalle | null>(null);
  const [trigger, setTrigger] = useState<HTMLElement | null>(null);
  if (!seguimientos.length) return null;
  return <>
    <div className="card mt-4" id="section-seguimientos">
      <div className="card-header d-flex align-items-center justify-content-between">
        <h5 className="mb-0">Ciclo de seguimiento</h5>
        <span className="text-muted small">{seguimientos.length} instancia{seguimientos.length === 1 ? "" : "s"}</span>
      </div>
      <div className="card-body p-0"><div className="table-responsive">
        <table className="table table-striped mb-0">
          <thead><tr><th>#</th><th>Tipo</th><th>Fecha</th><th>Estado</th><th>Validación</th><th>Origen</th><th>GESTIONAR</th><th className="text-right">Acciones</th></tr></thead>
          <tbody>{seguimientos.map((s) => (
            <tr key={s.id}>
              <td>{s.numero_orden}</td><td>{s.tipo}</td><td>{s.fecha}</td>
              <td><span className={`badge ${s.estado_badge}`}>{s.estado}</span>{s.a_subsanar && <>{" "}<span className="badge bg-danger ml-1">A subsanar</span></>}</td>
              <td>{s.estado_validacion || <span className="text-muted">-</span>}</td>
              <td>{s.origen === "app" ? <span className="badge bg-primary" title="Cargado desde la app">App</span> : <span className="badge bg-light text-dark" title="Cargado desde SISOC">SISOC</span>}</td>
              <td>{s.sincronizado_gestionar ? <span className="badge bg-success">Sincronizado</span> : <span className="badge bg-secondary">Pendiente</span>}</td>
              <td className="text-right text-nowrap">
                <a href={path(s.detalle_url)} className="btn btn-sm btn-primary">Ver</a>{" "}
                {caps.change_primerseguimiento && <a href={path(s.editar_url)} className="btn btn-sm btn-outline-primary">Editar</a>}{" "}
                {caps.delete_primerseguimiento && <button type="button" className="btn btn-sm btn-danger" onClick={(e) => { setTrigger(e.currentTarget); setDeleting(s); }}>Eliminar</button>}
              </td>
            </tr>
          ))}</tbody>
        </table>
      </div></div>
    </div>
    {deleting && <EliminarSeguimientoModal s={deleting} close={() => setDeleting(null)} trigger={trigger} onError={(message) => { setDeleting(null); onError(message); }} />}
  </>;
}

export function RelevamientoDetailContent({ data }: { data: RelevamientoDetailData }) {
  const { relevamiento: r, capabilities: caps } = data;
  const { toasts, push } = useToasts(data.messages);
  const [modal, setModal] = useState<"asignar" | "revision" | null>(null);
  const [trigger, setTrigger] = useState<HTMLElement | null>(null);
  const open = (kind: "asignar" | "revision", el: HTMLElement) => { setTrigger(el); setModal(kind); };
  const finalizado = r.estado === "Finalizado" || r.estado === "Finalizado/Excepciones";
  const reasignar = !finalizado && caps.change_relevamiento;
  const revisar = caps.review_relevamiento && !r.esta_validado && !r.sin_cargar;
  useCardCollapse();
  return <>
    {toasts}
    {CSS}
    <div className="row justify-content-between d-print-none mx-1 mb-3">
      <div className="col-auto" />
      <div className="col-auto">
        {reasignar && <>{" "}<button type="button" className="btn btn-primary mr-1" onClick={(e) => open("asignar", e.currentTarget)}>Reasignar territorial</button></>}
        {finalizado && <>{" "}
          <a href={path(data.pdf.url)} className="btn btn-secondary mr-1 d-none d-sm-inline"
            title={data.pdf.oficial ? `Formato oficial de Gestionar, enviado el ${data.pdf.fecha_oficial}` : undefined}>Descargar PDF</a>{" "}
          {data.pdf.oficial && <><small className="text-muted mr-2 d-none d-sm-inline">Formato oficial de Gestionar</small>{" "}</>}
        </>}
        {data.seguimientos.length > 0 && <>{" "}<a href="#section-seguimientos" className="btn btn-info mr-1 d-none d-sm-inline">Ver seguimientos</a>{" "}</>}
        {revisar && <>{" "}<button type="button" className="btn btn-warning mr-1" onClick={(e) => open("revision", e.currentTarget)}>Revisar</button>{" "}</>}
        {caps.view_logentry && <>{" "}<a href={path(data.urls.historial)} className="btn btn-outline-light mr-1">Historial</a>{" "}</>}
        {data.urls.editar_formulario && <>{" "}<a href={path(data.urls.editar_formulario)} className="btn btn-primary mr-1" aria-label="Editar relevamiento">Editar</a>{" "}</>}
        <a href={path(data.urls.eliminar)} className="btn btn-danger">Eliminar</a>
      </div>
    </div>
    {r.observaciones_coordinador && (
      <div className={`alert ${r.a_subsanar ? "alert-danger" : "alert-info"} mx-1 d-print-none`}>
        <strong>Observaciones del coordinador</strong>
        {r.coordinador && <span className="ml-1">{" "}({r.coordinador}{r.fecha_revision_coordinador && <>{" "}· {r.fecha_revision_coordinador}</>})</span>}
        <div className="mt-1">{r.observaciones_coordinador.split(/\r\n|\r|\n/).map((line, i) => <span key={i}>{i > 0 && <br />}{line}</span>)}</div>
      </div>
    )}
    {modal === "revision" && <RevisionModal data={data} close={() => setModal(null)} trigger={trigger} onError={(message) => { setModal(null); push({ message, level: "error" }); }} />}
    {modal === "asignar" && <AsignarModal data={data} close={() => setModal(null)} trigger={trigger} />}
    <div className="comedor-header-card mb-5"><div className="row align-items-center">
      <div className="col-md-8"><h1 className="comedor-header-title">{r.nombre_comedor ?? "None"}{" "}<span className="comedor-header-divider">|</span></h1></div>
      <div className="col-md-4"><div className="comedor-header-dates">
        {["Inicio de Ejecución", "Final de Ejecución", "Plazo de Ejecución"].map((label) => (
          <p className="comedor-date-item" key={label}><span className="comedor-date-label">{label}</span>{" "}<span className="comedor-date-value">-</span></p>
        ))}
      </div></div>
    </div></div>
    {data.timeline.length > 0 && (
      <div className="comedor-steps-timeline mt-5 mb-5">
        {data.timeline.map((t) => (
          <div className={`timeline-step-card ${t.card_class}`} key={t.id}>
            <div className="timeline-step-number">{t.step}</div>
            <div className="timeline-step-info"><p className="timeline-step-date">{t.fecha}</p><p className={`timeline-step-status ${t.status_class}`}>{t.estado}</p></div>
          </div>
        ))}
      </div>
    )}
    <Tree nodes={data.secciones} />
    <Cycle data={data} onError={(message) => push({ message, level: "error" })} />
    {data.adjuntos.length > 0 && (
      <div className="card mb-4" id="bloque-adjuntos">
        <div className="card-header"><h3 className="card-title font-weight-bold mr-3 pt-1">Archivos adjuntos</h3></div>
        <div className="card-body p-0"><ul className="list-group list-group-flush">
          {data.adjuntos.map((a) => (
            <li className="list-group-item d-flex justify-content-between align-items-center" key={a.id}>
              <span><i className={`fas ${a.es_pdf ? "fa-file-pdf" : "fa-file-image"} mr-2`} />{" "}{a.nombre_original}{" "}
                <small className="text-muted ml-2">{a.tamano} - {a.fecha_subida}</small></span>
              <a href={path(a.descargar_url)} className="btn btn-sm btn-outline-secondary" rel="noopener">Descargar</a>
            </li>
          ))}
        </ul></div>
      </div>
    )}
  </>;
}

function DetailPage({ comedor, id }: { comedor: string; id: string }) {
  const [state] = useMainResource(`${API}${comedor}/relevamiento/${id}/`, detailValid);
  return renderMain(state, "Cargando acompañamiento territorial…", (data) => {
    const r = data.relevamiento;
    const heading = <>
      {r.nombre_comedor ?? "None"}{" "}
      <span className="ml-2 h5">| Acompañamiento Territorial</span>{" "}
      <span className="ml-2 h5">| {r.fecha_visita} |</span>{" "}
      <span className={`badge ml-2 ${r.estado_badge}`} title={`Estado de la visita${r.estado_validacion ? ` (validación del coordinador: ${r.estado_validacion})` : ""}`}>{r.estado_visible}</span>{" "}
      {r.a_subsanar && <><span className="badge bg-danger ml-1">A subsanar</span>{" "}</>}
      {r.sincronizado_gestionar && <><span className="badge bg-success ml-2" title="El acompañamiento territorial se sincronizó con GESTIONAR">Sincronizado con GESTIONAR</span>{" "}</>}
      {r.origen === "app" && <span className="badge bg-primary ml-2" title="Creado por el territorial desde la app">App</span>}
    </>;
    return {
      // The native detail has no `comedor` in its context, so its title ends after "Comedor:".
      title: "Acompañamiento Territorial - Comedor:",
      // The native `titulo-pagina` block carries badges; the shell prints the node inside its `<h3>`.
      heading: heading as unknown as string,
      // `relevamiento_detail.html` prints its own divs inside the breadcrumb list.
      breadcrumb: <>
        <div className="breadcrumb-item"><a href={path(data.urls.comedores)}>Comedores</a></div>
        <div className="breadcrumb-item"><a href={path(data.urls.comedor)}>{r.comedor.nombre}</a></div>
        <div className="breadcrumb-item active">Acompañamiento Territorial {r.fecha_visita}</div>
      </>,
      content: <RelevamientoDetailContent data={data} />,
    };
  });
}

const LIST = /^\/comedores\/([0-9]+)\/relevamiento\/listar$/;
const BAJA = /^\/comedores\/([0-9]+)\/relevamiento\/([0-9]+)\/eliminar$/;
const DETAIL = /^\/comedores\/([0-9]+)\/relevamiento\/([0-9]+)$/;
type Params = { comedor: string; id?: string; baja?: boolean };

export const relevamientosRoute: RouteDefinition<Params> = {
  name: "comedores-relevamientos",
  match(pathname) {
    const list = LIST.exec(pathname);
    if (list) return { comedor: list[1] };
    const baja = BAJA.exec(pathname);
    if (baja) return { comedor: baja[1], id: baja[2], baja: true };
    const detail = DETAIL.exec(pathname);
    return detail ? { comedor: detail[1], id: detail[2] } : null;
  },
  render({ comedor, id, baja }) {
    if (baja) return <RelevamientoBaja comedor={comedor} id={id!} />;
    return id ? <DetailPage comedor={comedor} id={id} /> : <ListPage comedor={comedor} />;
  },
};
