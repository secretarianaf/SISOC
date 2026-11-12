/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useCallback, useEffect, useRef, useState, type FormEvent, type MouseEvent, type ReactNode } from "react";
import { InsumosToastList } from "../InsumosToast";
import { safeInternalPath } from "../webAccess";
import { Pagination } from "./listControls";
import { accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * RF01.01 final rendición de cuentas: the detail
 * (`rendicion_cuentas_final_detail.html`) and the document list
 * (`rendicion_cuentas_final_list.html` + `search_bar.html` AJAX mode). Data
 * comes from `/api/web/comedores/rendicion_cuentas_final/`, which runs the
 * native view and service; React never formats dates or states.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Documento = {
  id: number; tipo_nombre: string; estado: string; validador: string; observaciones: string | null;
  fecha_modificacion: string | null; archivo_url: string | null; editable: boolean; validable: boolean; eliminable: boolean;
};
type Historial = { tipo_nombre: string | null; accion: string; usuario: string; fecha: string | null };
export type DetalleData = {
  rendicion: { id: number; fisicamente_presentada: boolean };
  comedor: { id: number; nombre: string };
  urls: { comedores: string; comedor: string };
  documentos: Documento[];
  historial: Historial[];
  messages: Message[];
};
type Fila = {
  id: number; tipo_nombre: string; comedor_nombre: string; fecha_modificacion: string | null; estado: string;
  estado_slug: string; archivo_url: string | null; accionable: boolean;
};
export type ListaData = {
  count: number; page: number; page_size: number | null; pages: number; has_previous: boolean; has_next: boolean;
  previous: number | null; next: number | null; range: (number | "…")[]; filters: { busqueda: string };
  results: Fila[]; messages: Message[];
};

const API_LISTA = "web/comedores/rendicion_cuentas_final/documentos/";
const API_DETALLE = "web/comedores/rendicion_cuentas_final/comedor";
const LEVELS = ["success", "error", "warning", "info"];
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const nullableText = (v: unknown) => v === null || text(v);
const messagesValid = (v: unknown) => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));

export function detalleValid(v: unknown): v is DetalleData {
  if (!record(v) || !record(v.rendicion) || !record(v.comedor) || !record(v.urls)) return false;
  return integer(v.rendicion.id) && typeof v.rendicion.fisicamente_presentada === "boolean" &&
    integer(v.comedor.id) && text(v.comedor.nombre) && internal(v.urls.comedores) && internal(v.urls.comedor) &&
    Array.isArray(v.documentos) && v.documentos.every((d) => record(d) && integer(d.id) && text(d.tipo_nombre) && text(d.estado) && text(d.validador) &&
      nullableText(d.observaciones) && nullableText(d.fecha_modificacion) && (d.archivo_url === null || text(d.archivo_url)) &&
      typeof d.editable === "boolean" && typeof d.validable === "boolean" && typeof d.eliminable === "boolean") &&
    Array.isArray(v.historial) && v.historial.every((h) => record(h) && nullableText(h.tipo_nombre) && text(h.accion) && text(h.usuario) && nullableText(h.fecha)) &&
    messagesValid(v.messages);
}

export function listaValid(v: unknown): v is ListaData {
  return record(v) && integer(v.count) && integer(v.page) && (v.page_size === null || integer(v.page_size)) && integer(v.pages) &&
    typeof v.has_previous === "boolean" && typeof v.has_next === "boolean" &&
    (v.previous === null || integer(v.previous)) && (v.next === null || integer(v.next)) &&
    Array.isArray(v.range) && v.range.every((n) => n === "…" || integer(n)) && record(v.filters) && text(v.filters.busqueda) &&
    Array.isArray(v.results) && v.results.every((r) => record(r) && integer(r.id) && text(r.tipo_nombre) && text(r.comedor_nombre) &&
      nullableText(r.fecha_modificacion) && text(r.estado) && text(r.estado_slug) && (r.archivo_url === null || text(r.archivo_url)) && typeof r.accionable === "boolean") &&
    messagesValid(v.messages);
}

const CSS = <link rel="stylesheet" href="/static/custom/css/nomina.css" />;
const dash = (value: string | null) => value ?? "-";

/** «Visualizar»: the native storage URL in a new tab, or a disabled button. */
function Visualizar({ url }: { url: string | null }) {
  return url
    ? <a href={url} target="_blank" className="btn btn-primary btn-sm" rel="noreferrer">Visualizar</a>
    : <button className="btn btn-sm btn-secondary" disabled>Visualizar</button>;
}

// --- Detail -----------------------------------------------------------------

/** Bootstrap-like modal: focus inside, Escape and backdrop close it (unless busy). */
function Modal({ id, title, close, busy = false, size = "", children }: { id: string; title: string; close: () => void; busy?: boolean; size?: string; children: ReactNode }) {
  const modal = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    document.body.classList.add("modal-open");
    modal.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) close();
      if (e.key !== "Tab") return;
      const controls = Array.from(modal.current?.querySelectorAll<HTMLElement>("button:not([disabled]),input:not([disabled]),textarea:not([disabled]),a[href]") ?? []);
      const first = controls[0], last = controls.at(-1);
      if (e.shiftKey && (document.activeElement === first || document.activeElement === modal.current)) { e.preventDefault(); last?.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    };
    document.addEventListener("keydown", key);
    return () => { document.removeEventListener("keydown", key); document.body.classList.remove("modal-open"); previous?.focus(); };
  }, [close, busy]);
  return (
    <>
      <div className="modal-backdrop fade show" />
      <div ref={modal} className="modal fade show d-block" id={id} tabIndex={-1} role="dialog" aria-modal="true"
        aria-labelledby={`${id}-label`} onClick={(e) => { if (e.target === e.currentTarget && !busy) close(); }}>
        <div className={`modal-dialog${size}`}>{children}<span hidden id={`${id}-label`}>{title}</span></div>
      </div>
    </>
  );
}

function ModalHeader({ id, title, close, closeLabel = true }: { id: string; title: string; close: () => void; closeLabel?: boolean }) {
  return (
    <div className="modal-header">
      <h5 className="modal-title" id={`${id}-title`}>{title}</h5>
      <button type="button" className="btn-close" aria-label={closeLabel ? "Cerrar" : undefined} onClick={close} />
    </div>
  );
}

function ObservacionesModal({ titulo, cuerpo, close }: { titulo: string; cuerpo: string; close: () => void }) {
  return (
    <Modal id="modal-observaciones" title={titulo || "Observaciones"} close={close} size=" modal-dialog-scrollable">
      <div className="modal-content">
        <ModalHeader id="modal-observaciones" title={titulo || "Observaciones"} close={close} />
        <div className="modal-body" id="modal-observaciones-body">{cuerpo || "Sin observaciones"}</div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={close}>Cerrar</button>
        </div>
      </div>
    </Modal>
  );
}

type Aviso = { message: string; level: "success" | "error" | "warning" | "info" };
const INCIERTO = "No se pudo confirmar el resultado.";
const CONFIRMAR = {
  validar: "¿Estás seguro de que querés validar este documento?",
  eliminar: "¿Estás seguro de que querés eliminar este documento?",
  adjuntar: "¿Estás seguro de que querés adjuntar este documento?",
  crear: "¿Estás seguro de que querés crear este documento?",
};
const BASE_API = "web/comedores/rendicion_cuentas_final";

/**
 * One POST per action through the web API (CSRF added by the client). A
 * confirmed 200 or a native-style 400 shows its message and reloads the screen
 * with a GET; an unconfirmed outcome is reported and never resent.
 */
function useAcciones(reload: () => void) {
  const busy = useRef(false);
  const [pendiente, setPendiente] = useState(false);
  const [avisos, setAvisos] = useState<Aviso[]>([]);
  const enviar = useCallback(async (endpoint: string, body: FormData): Promise<boolean> => {
    if (busy.current) return false;
    busy.current = true; setPendiente(true);
    let aviso: Aviso | null = null;
    let hecho = false;
    try {
      const { data, status } = await webClient.post(endpoint, body, { validateStatus: () => true });
      const mensaje = record(data) && text(data.message) ? data.message : null;
      if (status === 200 && record(data) && data.ok === true) { hecho = true; aviso = mensaje ? { message: mensaje, level: "success" } : null; }
      else if (status === 400 && mensaje) aviso = { message: mensaje, level: "error" };
      else if (status === 401 || status === 403) aviso = { message: record(data) && text(data.detail) ? data.detail : "No tiene permiso para realizar esta acción.", level: "error" };
      else aviso = { message: INCIERTO, level: "error" };
    } catch {
      aviso = { message: INCIERTO, level: "error" };
    }
    // A new toast each time: its timers belong to the mounted list item.
    if (aviso) setAvisos((actual) => [...actual, aviso as Aviso]);
    busy.current = false; setPendiente(false);
    reload();
    return hecho || aviso?.level === "error";
  }, [reload]);
  return { enviar, pendiente, avisos };
}

function formData(campos: Record<string, string | File | null | undefined>) {
  const form = new FormData();
  for (const [clave, valor] of Object.entries(campos)) if (valor !== undefined && valor !== null) form.append(clave, valor);
  return form;
}

/** «Validar»: native confirm, then one POST. */
function ValidarBoton({ id, activo, onEnviar, pendiente }: { id: number; activo: boolean; onEnviar: (endpoint: string, body: FormData) => Promise<boolean>; pendiente: boolean }) {
  if (!activo) return <button className="btn btn-sm btn-secondary" disabled>Validar</button>;
  return (
    <form onSubmit={(e) => { e.preventDefault(); if (window.confirm(CONFIRMAR.validar)) void onEnviar(`${BASE_API}/documentos/${id}/validar/`, formData({})); }}>
      <button type="submit" className="btn btn-warning btn-sm" disabled={pendiente}>Validar</button>
    </form>
  );
}

function AdjuntarModal({ documento, onEnviar, pendiente, close }: { documento: Documento; onEnviar: (endpoint: string, body: FormData) => Promise<boolean>; pendiente: boolean; close: () => void }) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!archivo || !window.confirm(CONFIRMAR.adjuntar)) return;
    if (await onEnviar(`${BASE_API}/documentos/adjuntar/`, formData({ documento_id: String(documento.id), archivo }))) close();
  };
  return (
    <Modal id="modalAdjuntarDocumentoRendicionFinal" title="Adjuntar archivo" close={close} busy={pendiente}>
      <form id="formAdjuntar" onSubmit={(e) => void submit(e)}>
        <div className="modal-content">
          <ModalHeader id="modalAdjuntarDocumentoRendicionFinal" title="Adjuntar archivo" close={close} />
          <div className="modal-body">
            <p id="tipoDocumentoTexto">Documento: {documento.tipo_nombre}</p>
            <div className="mb-3">
              <label htmlFor="archivo" className="form-label">Archivo</label>
              <input className="form-control" type="file" id="archivo" name="archivo" required onChange={(e) => setArchivo(e.target.files?.[0] ?? null)} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={pendiente}>Subir</button>
          </div>
        </div>
      </form>
    </Modal>
  );
}

function CrearModal({ rendicionId, onEnviar, pendiente, close }: { rendicionId: number; onEnviar: (endpoint: string, body: FormData) => Promise<boolean>; pendiente: boolean; close: () => void }) {
  const [nombre, setNombre] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!nombre || !window.confirm(CONFIRMAR.crear)) return;
    if (await onEnviar(`${BASE_API}/${rendicionId}/crear/`, formData({ nombre, archivo }))) close();
  };
  return (
    <Modal id="modalCrearDocumento" title="Nuevo Documento Personalizado" close={close} busy={pendiente}>
      <form onSubmit={(e) => void submit(e)}>
        <div className="modal-content">
          <ModalHeader id="modalCrearDocumento" title="Nuevo Documento Personalizado" close={close} />
          <div className="modal-body">
            <div className="mb-3">
              <label htmlFor="nombre" className="form-label">Nombre del documento</label>
              <input type="text" id="nombre" className="form-control" name="nombre" required value={nombre} onChange={(e) => setNombre(e.target.value)} />
            </div>
            <div className="mb-3">
              <label htmlFor="archivo-crear" className="form-label">Archivo</label>
              <input type="file" id="archivo-crear" className="form-control" name="archivo" onChange={(e) => setArchivo(e.target.files?.[0] ?? null)} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="submit" className="btn btn-success" disabled={pendiente}>Crear</button>
          </div>
        </div>
      </form>
    </Modal>
  );
}

function SubsanarModal({ id, onEnviar, pendiente, close }: { id: number; onEnviar: (endpoint: string, body: FormData) => Promise<boolean>; pendiente: boolean; close: () => void }) {
  const [observacion, setObservacion] = useState("");
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!observacion) return;
    if (await onEnviar(`${BASE_API}/documentos/${id}/subsanar/`, formData({ observacion }))) close();
  };
  return (
    <Modal id="modalSubsanar" title="Subsanar Documento" close={close} busy={pendiente}>
      <form id="formSubsanar" onSubmit={(e) => void submit(e)}>
        <div className="modal-content">
          <ModalHeader id="modalSubsanar" title="Subsanar Documento" close={close} closeLabel={false} />
          <div className="modal-body">
            <div className="mb-3">
              <label htmlFor="observacion" className="form-label">Observación</label>
              <textarea maxLength={150} name="observacion" id="observacion" className="form-control" required value={observacion} onChange={(e) => setObservacion(e.target.value)} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
            <button type="submit" className="btn btn-danger" disabled={pendiente}>Enviar a Subsanar</button>
          </div>
        </div>
      </form>
    </Modal>
  );
}

export function DetalleContent({ data: inicial, pk }: { data: DetalleData; pk: string }) {
  const [data, setData] = useState(inicial);
  const [observacion, setObservacion] = useState<{ titulo: string; cuerpo: string } | null>(null);
  const [modal, setModal] = useState<{ tipo: "adjuntar"; documento: Documento } | { tipo: "crear" } | null>(null);
  const close = useCallback(() => { setObservacion(null); setModal(null); }, []);
  const reload = useCallback(() => {
    webClient.get(`${API_DETALLE}/${pk}/`, { validateStatus: accepted }).then(({ data: nueva, status }: { data: unknown; status?: number }) => {
      if (status === 200 && detalleValid(nueva)) setData(nueva);
    }).catch(() => undefined);
  }, [pk]);
  const { enviar, pendiente, avisos } = useAcciones(reload);
  return (
    <>
      {CSS}
      <InsumosToastList messages={[...data.messages, ...avisos]} />
      <div className="row"><div className="col-md-12" /></div>
      <div className="row">
        <button className="btn btn-primary mb-3 w-auto" onClick={() => setModal({ tipo: "crear" })}>Añadir documento personalizado</button>
        <form onSubmit={(e) => e.preventDefault()}>
          <div className="form-check form-switch mb-3">
            <input className="form-check-input" type="checkbox" id="fisicamentePresentadaSwitch" name="fisicamente_presentada"
              checked={data.rendicion.fisicamente_presentada} disabled={pendiente}
              onChange={() => void enviar(`${BASE_API}/${data.rendicion.id}/fisicamente_presentada/`, formData({}))} />
            {" "}<label className="form-check-label" htmlFor="fisicamentePresentadaSwitch">Revisión físicamente presentada</label>
          </div>
        </form>
        <table className="w-100 table table-stripped text-center">
          <thead>
            <tr>
              <th className="text-start">Tipo de Documento</th><th>Estado</th><th>Validador</th><th>Observaciones</th><th>Última Modificación</th>
              <th></th><th></th><th></th><th></th>
            </tr>
          </thead>
          <tbody>
            {data.documentos.map((doc) => (
              <tr key={doc.id}>
                <td className="text-start">{doc.tipo_nombre}</td>
                <td>{doc.estado}</td>
                <td>{doc.validador}</td>
                <td>
                  {doc.observaciones
                    ? <a href="#" className="btn btn-link p-0 ver-observaciones"
                        onClick={(e: MouseEvent) => { e.preventDefault(); setObservacion({ titulo: `Observaciones del documento ${doc.tipo_nombre}`, cuerpo: doc.observaciones ?? "" }); }}>Ver</a>
                    : "-"}
                </td>
                <td>{dash(doc.fecha_modificacion)}</td>
                <td>{doc.editable
                  ? <button className="btn btn-success btn-sm" onClick={() => setModal({ tipo: "adjuntar", documento: doc })}>Adjuntar</button>
                  : <button className="btn btn-sm btn-secondary" disabled>Adjuntar</button>}</td>
                <td><Visualizar url={doc.archivo_url} /></td>
                <td><ValidarBoton id={doc.id} activo={doc.validable} onEnviar={enviar} pendiente={pendiente} /></td>
                <td>{doc.eliminable
                  ? <form onSubmit={(e) => { e.preventDefault(); if (window.confirm(CONFIRMAR.eliminar)) void enviar(`${BASE_API}/documentos/${doc.id}/eliminar/`, formData({})); }}>
                      <button type="submit" className="btn btn-danger btn-sm bi bi-trash" disabled={pendiente} />
                    </form>
                  : <button type="submit" className="btn btn-sm bi bi-trash btn-secondary" disabled />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="row mt-3">
        <h3>Historial de Documentos</h3>
        <table className="w-100 table table-stripped text-center">
          <thead>
            <tr><th className="text-start">Tipo de Documento</th><th>Acción</th><th>Usuario</th><th>Fecha</th></tr>
          </thead>
          <tbody>
            {data.historial.length ? data.historial.map((h, i) => (
              <tr key={i}>
                <td className="text-start">{h.tipo_nombre === null ? <span className="text-muted">No disponible</span> : h.tipo_nombre}</td>
                <td>{h.accion}</td>
                <td>{h.usuario}</td>
                <td>{dash(h.fecha)}</td>
              </tr>
            )) : <tr><td colSpan={4} className="text-center">No hay registros aun.</td></tr>}
          </tbody>
        </table>
      </div>
      {observacion && <ObservacionesModal titulo={observacion.titulo} cuerpo={observacion.cuerpo} close={close} />}
      {modal?.tipo === "adjuntar" && <AdjuntarModal documento={modal.documento} onEnviar={enviar} pendiente={pendiente} close={close} />}
      {modal?.tipo === "crear" && <CrearModal rendicionId={data.rendicion.id} onEnviar={enviar} pendiente={pendiente} close={close} />}
    </>
  );
}

function DetallePage({ pk }: { pk: string }) {
  const [state] = useMainResource(`${API_DETALLE}/${pk}/`, detalleValid);
  return renderMain(state, "Cargando rendición…", (data) => ({
    title: "Rendicion de Cuentas Final",
    heading: "Rendicion de Cuentas Final",
    breadcrumb: (
      <ol className="breadcrumb float-sm-right">
        <div className="breadcrumb-item"><a href={safeInternalPath(data.urls.comedores) ?? "/"}>Espacios Comunitarios</a></div>
        {/* The native template reads a missing attribute, so the link text is empty (kept). */}
        <div className="breadcrumb-item"><a href={safeInternalPath(data.urls.comedor) ?? "/"}></a></div>
        <div className="breadcrumb-item active">Rendicion de Cuentas Final</div>
      </ol>
    ),
    content: <DetalleContent data={data} pk={pk} />,
  }));
}

// --- List -------------------------------------------------------------------

const LISTADO = "/rendicion_cuentas_final/listar/";
const FALLO = "Error al cargar los datos. Intente nuevamente.";

export function ListaContent({ initial, hasQuery, initialQuery }: { initial: ListaData; hasQuery: boolean; initialQuery: string }) {
  const [datos, setDatos] = useState<ListaData>(initial);
  const [consultada, setConsultada] = useState(hasQuery);
  const [consulta, setConsulta] = useState(initialQuery);
  const [cargando, setCargando] = useState(false);
  const [fallo, setFallo] = useState(false);
  const [subsanar, setSubsanar] = useState<number | null>(null);
  const actual = useRef(initialQuery);
  const paginaActual = useRef(1);
  const yaBusco = useRef(hasQuery);
  const [termino, setTermino] = useState(initialQuery);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const control = useRef<AbortController>(undefined);
  const buscar = useCallback((query: string, page = 1, plano = false) => {
    if (!plano) yaBusco.current = true;
    actual.current = query;
    paginaActual.current = page;
    setTermino(query);
    control.current?.abort();
    const controller = new AbortController();
    control.current = controller;
    setCargando(true);
    const params = new URLSearchParams({ busqueda: query });
    if (page > 1) params.set("page", String(page));
    // Before any search the native list shows every row: reload that same view.
    webClient.get(plano ? API_LISTA : `${API_LISTA}?${params}`, { signal: controller.signal, validateStatus: accepted }).then(({ data, status }: { data: unknown; status?: number }) => {
      if (controller.signal.aborted) return;
      if (status !== 200 || !listaValid(data)) throw new Error("invalid");
      setDatos(data); setConsultada(!plano); setFallo(false); setCargando(false);
    }).catch(() => { if (!controller.signal.aborted) { setFallo(true); setCargando(false); } });
  }, []);
  useEffect(() => {
    // Native script: an initial value runs the search once on load.
    const start = initialQuery.trim() ? setTimeout(() => buscar(initialQuery.trim()), 0) : undefined;
    return () => { clearTimeout(start); clearTimeout(timer.current); control.current?.abort(); };
  }, [initialQuery, buscar]);
  const recargar = useCallback(() => buscar(actual.current, paginaActual.current, !yaBusco.current), [buscar]);
  const { enviar, pendiente, avisos } = useAcciones(recargar);
  const onPaginacion = (e: MouseEvent<HTMLDivElement>) => {
    const link = (e.target as HTMLElement).closest<HTMLAnchorElement>('a[href*="page="]');
    if (!link) return;
    e.preventDefault();
    buscar(actual.current, Number(new URL(link.href).searchParams.get("page")) || 1);
  };
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
      <link rel="stylesheet" href="/static/custom/css/poncho_listados.css" />
      <InsumosToastList messages={[...datos.messages, ...avisos]} />
      <h2 className="text-center mb-4 poncho-titulo">Buscar Documento</h2>
      <div className="poncho-search poncho-search--solo">
        <div className="poncho-search__box">
          <input type="search" id="ajax-search-input" className="poncho-search__input" placeholder="Buscar por comedor o tipo de documento"
            title="Ingresar comedor o tipo de documento." autoComplete="off" aria-label="Ingresar comedor o tipo de documento." value={consulta}
            onChange={(e) => {
              const valor = e.target.value; setConsulta(valor);
              clearTimeout(timer.current);
              timer.current = setTimeout(() => buscar(valor.trim()), 300);
            }}
            onKeyDown={(e) => { if (e.key === "Escape") { clearTimeout(timer.current); setConsulta(""); buscar(""); } }} />
          <button type="button" id="ajax-search-go" className="poncho-search__go" aria-label="Buscar"
            onClick={() => { clearTimeout(timer.current); buscar(consulta.trim()); }}><i className="fas fa-search" aria-hidden="true" /></button>
        </div>
      </div>
      <div className="poncho-search__meta">
        <span id="ajax-results-count">{consultada && termino.trim() ? `${datos.count} resultado(s) encontrado(s)` : ""}</span>
      </div>
      <div id="ajax-loading-indicator" className="text-center py-3" style={{ display: cargando ? "block" : "none" }}>
        <div className="spinner-border" role="status"><span className="sr-only">Cargando...</span></div>
      </div>
      <div className="row mt-3">
        <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
          <a href={LISTADO} className="poncho-btn poncho-btn--neutro">Resetear</a>
        </div>
      </div>
      <div className="row mt-5 max-width-100">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <table className="table table-bordered table-striped projects">
                <thead>
                  <tr><th>Nombre</th><th>Comedor</th><th>Fecha de modificacion</th><th>Estado</th><th>Acciones</th><th>Validar</th><th>Subsanar</th></tr>
                </thead>
                <tbody id="rendicion-cuentas-table-body" style={{ opacity: cargando ? 0.5 : 1 }}>
                  {fallo ? (
                    <tr><td colSpan={7} className="text-center text-danger py-4">{FALLO}</td></tr>
                  ) : datos.results.length ? datos.results.map((fila) => (
                    <tr key={fila.id} className={`documento-row estado-${fila.estado_slug}`}>
                      <td>{fila.tipo_nombre}</td>
                      <td>{fila.comedor_nombre}</td>
                      <td>{dash(fila.fecha_modificacion)}</td>
                      <td>{fila.estado}</td>
                      <td><Visualizar url={fila.archivo_url} /></td>
                      <td><ValidarBoton id={fila.id} activo={fila.accionable} onEnviar={enviar} pendiente={pendiente} /></td>
                      <td>{fila.accionable
                        ? <button type="button" className="btn btn-danger btn-sm" onClick={() => setSubsanar(fila.id)}>Subsanar</button>
                        : <button className="btn btn-sm btn-secondary" disabled>Subsanar</button>}</td>
                    </tr>
                  )) : (
                    <tr><td colSpan={7} className="text-center">No se encontraron documentos.</td></tr>
                  )}
                </tbody>
              </table>
              <div id="pagination-container" onClick={onPaginacion}>
                {consultada && !fallo && (
                  <Pagination paginated={datos.pages > 1} number={datos.page} previous={datos.previous} next={datos.next} range={datos.range}
                    count={datos.count} href={(n) => `?${termino ? `busqueda=${encodeURIComponent(termino)}&` : ""}page=${n}`} />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      {subsanar !== null && <SubsanarModal id={subsanar} onEnviar={enviar} pendiente={pendiente} close={() => setSubsanar(null)} />}
    </>
  );
}

function ListaPage() {
  const query = new URLSearchParams(window.location.search);
  const busqueda = query.get("busqueda") ?? "";
  const endpoint = `${API_LISTA}${window.location.search}`;
  const [state] = useMainResource(endpoint, listaValid);
  return renderMain(state, "Cargando documentos…", (data) => ({
    title: "Espacios Comunitarios",
    breadcrumb: <ol className="breadcrumb float-sm-right" />,
    content: <ListaContent initial={data} hasQuery={false} initialQuery={busqueda} />,
  }));
}

const DETALLE = /^\/comedores\/([0-9]+)\/rendicion_cuentas_final\/$/;

export const rendicionFinalRoute: RouteDefinition<{ kind: "detalle"; pk: string } | { kind: "lista" }> = {
  name: "comedores-rendicion-final",
  match(pathname) {
    if (pathname === LISTADO) return { kind: "lista" };
    const found = DETALLE.exec(pathname);
    return found ? { kind: "detalle", pk: found[1] } : null;
  },
  render(params) {
    return params.kind === "detalle" ? <DetallePage pk={params.pk} /> : <ListaPage />;
  },
};
