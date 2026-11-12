/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen, validator and navigation seam live here with the route. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { safeInternalPath } from "../webAccess";
import { client, internal, messagesValid, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import { NativeModal } from "./nativeParity";
import { Pagination } from "./listControls";
import type { RouteDefinition } from "./types";

/**
 * CDI09.01 centre detail / legajo (`centrodeinfancia/centrodeinfancia_detail.html`): hero, header
 * actions, the side-tab folder (general, funcionamiento, users), the nómina summary, workers,
 * recent forms, quality form and the observations table. Every value comes rendered by the
 * backend with the native template expressions. Writes keep the native views: the user status
 * modal, the worker soft delete and the observation modal each POST once and then reload the
 * page the way the native redirect does. The interventions card (flag off everywhere) stays
 * native: the backend answers 409 and the preview entry serves the native page.
 */
type Item = { icon: string; label: string; value: string };
type Password = { kind: "value" | "changed" | "unavailable"; value: string };
type Acciones = { activo: boolean; usuario: string; url: string };
type Usuario = {
  id: number; username: string; responsable: boolean; nombre: string; email: string; estado: "activo" | "suspendido" | "baja";
  motivo: string; password?: Password; acciones?: Acciones | null;
};
type Trabajador = { id: number; nombre: string; subcomponente: string; funcion: string; fecha_carga: string; ver: string; editar: string | null; eliminar: string | null };
type Formulario = { id: string; fecha: string; respondente: string; actualizado: string; ver: string; editar: string | null };
type Calidad = { id: string; fecha: string; enviado_por: string; ver: string };
type Observacion = { id: number; fecha: string; observador: string; texto: string; ver: string };
export type CentroDetalleData = {
  centro: { id: number; nombre: string; codigo_cdi: string; lista_url: string };
  hero: { nomina: number; trabajadores: number; formularios: number | null; anio_inicio: string };
  header: { nomina_url: string; historial_url: string | null; generar_usuario_url: string | null; editar_url: string; eliminar_url: string };
  general: Item[];
  mapa: string | null;
  referente: { nombre: string; items: Item[] };
  funcionamiento: { items: Item[]; horarios: { dia: string; apertura: string; cierre: string }[] };
  usuarios: { credenciales: boolean; administrar: boolean; generar_url: string | null; columnas: number; filas: Usuario[] } | null;
  nomina: { asistencia_url: string | null; ver_url: string; hombres: number; mujeres: number; x: number; menores: number };
  trabajadores: { crear_url: string | null; filas: Trabajador[] };
  formularios: { listado_url: string; crear_url: string | null; filas: Formulario[] } | null;
  calidad: { listado_url: string; cargar_url: string | null; borrador: boolean; borrador_fecha: string; total: number; filas: Calidad[] } | null;
  observaciones: {
    filas: Observacion[]; paginated: boolean; number: number; previous: number | null; next: number | null; range: (number | string)[];
    count: number | null; query_prefix: string; crear_url: string; campo: { label: string; rows: number; placeholder: string };
  };
  messages: CdiMessage[];
};

const integer = (v: unknown): v is number => Number.isSafeInteger(v);
const nullableText = (v: unknown) => v === null || text(v);
const nullablePath = (v: unknown) => v === null || internal(v);
const itemsValid = (v: unknown) => Array.isArray(v) && v.every((i) => record(i) && text(i.icon) && text(i.label) && text(i.value));
const rowsValid = (v: unknown, ok: (r: Record<string, unknown>) => boolean) => Array.isArray(v) && v.every((r) => record(r) && ok(r));

function usuariosValid(u: unknown) {
  if (u === null) return true;
  if (!record(u) || typeof u.credenciales !== "boolean" || typeof u.administrar !== "boolean" || !nullablePath(u.generar_url) || !integer(u.columnas)) return false;
  return rowsValid(u.filas, (f) => integer(f.id) && text(f.username) && typeof f.responsable === "boolean" && text(f.nombre) && text(f.email) &&
    ["activo", "suspendido", "baja"].includes(f.estado as string) && text(f.motivo) &&
    (f.password === undefined || (record(f.password) && ["value", "changed", "unavailable"].includes(f.password.kind as string) && text(f.password.value))) &&
    (f.acciones === undefined || f.acciones === null || (record(f.acciones) && typeof f.acciones.activo === "boolean" && text(f.acciones.usuario) && text(f.acciones.url))));
}

export function centroDetalleValid(v: unknown): v is CentroDetalleData {
  if (!record(v) || !record(v.centro) || !record(v.hero) || !record(v.header) || !record(v.referente) || !record(v.funcionamiento) ||
    !record(v.nomina) || !record(v.trabajadores) || !record(v.observaciones)) return false;
  const c = v.centro, h = v.header, o = v.observaciones, n = v.nomina;
  const t = v.trabajadores, f = v.formularios, q = v.calidad;
  return integer(c.id) && text(c.nombre) && text(c.codigo_cdi) && internal(c.lista_url) &&
    integer(v.hero.nomina) && integer(v.hero.trabajadores) && (v.hero.formularios === null || integer(v.hero.formularios)) && text(v.hero.anio_inicio) &&
    internal(h.nomina_url) && nullablePath(h.historial_url) && nullablePath(h.generar_usuario_url) && internal(h.editar_url) && internal(h.eliminar_url) &&
    itemsValid(v.general) && nullableText(v.mapa) && text(v.referente.nombre) && itemsValid(v.referente.items) && itemsValid(v.funcionamiento.items) &&
    rowsValid(v.funcionamiento.horarios, (x) => text(x.dia) && text(x.apertura) && text(x.cierre)) && usuariosValid(v.usuarios) &&
    nullablePath(n.asistencia_url) && internal(n.ver_url) && ["hombres", "mujeres", "x", "menores"].every((k) => integer(n[k])) &&
    nullablePath(t.crear_url) && rowsValid(t.filas, (r) => integer(r.id) && text(r.nombre) && text(r.subcomponente) && text(r.funcion) && text(r.fecha_carga) && internal(r.ver) && nullablePath(r.editar) && nullableText(r.eliminar)) &&
    (f === null || (record(f) && internal(f.listado_url) && nullablePath(f.crear_url) && rowsValid(f.filas, (r) => text(r.id) && text(r.fecha) && text(r.respondente) && text(r.actualizado) && internal(r.ver) && nullablePath(r.editar)))) &&
    (q === null || (record(q) && internal(q.listado_url) && nullablePath(q.cargar_url) && typeof q.borrador === "boolean" && text(q.borrador_fecha) && integer(q.total) &&
      rowsValid(q.filas, (r) => text(r.id) && text(r.fecha) && text(r.enviado_por) && internal(r.ver)))) &&
    rowsValid(o.filas, (r) => integer(r.id) && text(r.fecha) && text(r.observador) && text(r.texto) && internal(r.ver)) &&
    typeof o.paginated === "boolean" && integer(o.number) && (o.previous === null || integer(o.previous)) && (o.next === null || integer(o.next)) &&
    Array.isArray(o.range) && o.range.every((x) => integer(x) || text(x)) && (o.count === null || integer(o.count)) && text(o.query_prefix) && text(o.crear_url) &&
    record(o.campo) && text(o.campo.label) && integer(o.campo.rows) && text(o.campo.placeholder) && messagesValid(v.messages);
}

/**
 * Full-page load of the page the native redirect points to. A redirect that only changes the hash
 * (`#usuarios`) would not reload, so the same path reloads with the hash kept; replaceable in tests.
 */
export const centroDetalleNavigation = {
  go(to: string) {
    const target = new URL(to, window.location.href);
    if (target.pathname + target.search === window.location.pathname + window.location.search) {
      if (target.hash) window.location.hash = target.hash;
      window.location.reload();
    } else window.location.assign(target.pathname + target.search + target.hash);
  },
};

const api = (url: string) => url.replace(/^\/api\//, "");
const href = (url: string) => safeInternalPath(url) ?? "/";

function InfoItem({ item }: { item: Item }) {
  return (
    <div className="cdf-info-item">
      <i className={`bi ${item.icon}`} />
      <div>
        <div className="cdf-info-label">{item.label}</div>
        <div className="cdf-info-value">{item.value}</div>
      </div>
    </div>
  );
}

/** `{% block app-header %}`: native links plus the "Acciones" Bootstrap dropdown. */
function HeaderActions({ header }: { header: CentroDetalleData["header"] }) {
  const [open, setOpen] = useState(false);
  const group = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const outside = (e: MouseEvent) => { if (!group.current?.contains(e.target as Node)) setOpen(false); };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("click", outside);
    document.addEventListener("keydown", key);
    return () => { document.removeEventListener("click", outside); document.removeEventListener("keydown", key); };
  }, [open]);
  return (
    <div className="row g-2 align-items-center">
      <div className="col-12 col-lg d-flex flex-wrap justify-content-start justify-content-lg-end gap-2 align-items-center header-actions">
        <a href={href(header.nomina_url)} className="btn btn-md btn-outline-light"><i className="bi bi-people me-1" />Ver Nómina</a>
        {header.historial_url && <a href={href(header.historial_url)} className="btn btn-md btn-outline-light"><i className="bi bi-journal-text me-1" />Historial</a>}
        <div className="btn-group" ref={group}>
          <button className={`btn btn-md dropdown-toggle${open ? " show" : ""}`} type="button" aria-expanded={open} onClick={() => setOpen(!open)}>
            <i className="bi bi-list" />Acciones{" "}
          </button>
          <ul className={`dropdown-menu dropdown-menu-end${open ? " show" : ""}`} data-bs-popper={open ? "static" : undefined}>
            {header.generar_usuario_url && (
              <li><a className="dropdown-item" href={href(header.generar_usuario_url)}><i className="bi bi-person-plus me-1" />Generar usuario</a></li>
            )}
            <li><a className="dropdown-item" href={href(header.editar_url)}><i className="bi bi-pencil me-1" />Editar</a></li>
            <li><a className="dropdown-item text-danger" href={href(header.eliminar_url)}><i className="bi bi-trash me-1" />Eliminar</a></li>
          </ul>
        </div>
      </div>
    </div>
  );
}

const ACCIONES_USUARIO = {
  suspender: { texto: "¿Suspender a {usuario}? No va a poder ingresar al centro hasta que se lo reactive.", boton: "Suspender", clase: "btn-warning", motivo: true },
  reactivar: { texto: "¿Reactivar a {usuario}? Vuelve a tener acceso al centro.", boton: "Reactivar", clase: "btn-success", motivo: false },
  baja: { texto: "¿Dar de baja a {usuario}? Pierde el acceso a este centro de forma definitiva y libera un cupo.", boton: "Dar de baja", clase: "btn-danger", motivo: true },
} as const;
type Accion = keyof typeof ACCIONES_USUARIO;

/** One POST per confirmation to a native write; the native redirect is followed, a failure is announced, never retried. */
function useWrite() {
  const [busy, setBusy] = useState(false);
  const sending = useRef(false);
  async function send(url: string, body: URLSearchParams, onRejected?: (data: unknown) => void) {
    if (sending.current) return;
    sending.current = true;
    setBusy(true);
    try {
      const { data, status } = await client.post(api(url), body, { validateStatus: () => true });
      if (record(data) && data.ok === true && internal(data.redirect)) { centroDetalleNavigation.go(data.redirect as string); return; }
      if (onRejected) onRejected(status === 400 ? data : null);
      else window.alert(record(data) && text(data.detail) ? data.detail : "No se pudo completar la acción.");
    } catch {
      window.alert("Error de conexión. Intentá nuevamente.");
    }
    sending.current = false;
    setBusy(false);
  }
  return { busy, send };
}

function EstadoUsuarioModal({ acceso, accion, close }: { acceso: Acciones; accion: Accion; close: () => void }) {
  const cfg = ACCIONES_USUARIO[accion];
  const [motivo, setMotivo] = useState("");
  const { busy, send } = useWrite();
  function submit(e: FormEvent) {
    e.preventDefault();
    void send(acceso.url, new URLSearchParams({ accion, motivo }));
  }
  return (
    <NativeModal id="modalEstadoUsuario" title="Confirmar" close={close} busy={busy} size=" modal-dialog-centered" controls="button:not([disabled]),textarea:not([disabled])">
      <div className="modal-content">
        <form method="post" id="usuarioEstadoForm" onSubmit={submit}>
          <div className="modal-header">
            <h5 className="modal-title" id="modalEstadoUsuarioLabel">Confirmar</h5>
            <button type="button" className="btn-close btn-close-white" aria-label="Cerrar" onClick={close} />
          </div>
          <div className="modal-body">
            <p id="usuarioEstadoTexto">{cfg.texto.replace("{usuario}", acceso.usuario || "este usuario")}</p>
            <div id="usuarioEstadoMotivoGrupo" hidden={!cfg.motivo}>
              <label htmlFor="usuarioEstadoMotivo" className="form-label">Motivo *</label>
              <textarea className="form-control" id="usuarioEstadoMotivo" name="motivo" rows={3} maxLength={500} required={cfg.motivo}
                value={motivo} onChange={(e) => setMotivo(e.target.value)} />
              <small className="text-muted">Queda registrado en la auditoría.</small>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
            <button type="submit" className={`btn ${cfg.clase}`} id="usuarioEstadoConfirmar" disabled={busy}>{cfg.boton}</button>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}

function EliminarTrabajadorModal({ trabajador, close }: { trabajador: Trabajador; close: () => void }) {
  const { busy, send } = useWrite();
  function submit(e: FormEvent) {
    e.preventDefault();
    void send(trabajador.eliminar as string, new URLSearchParams());
  }
  return (
    <NativeModal id="modalEliminarTrabajador" title="Confirmar eliminación" close={close} busy={busy} size=" modal-dialog-centered">
      <div className="modal-content">
        <form method="post" id="trabajadorDeleteForm" onSubmit={submit}>
          <div className="modal-header">
            <h5 className="modal-title" id="modalEliminarTrabajadorLabel">Confirmar eliminación</h5>
            <button type="button" className="btn-close btn-close-white" aria-label="Cerrar" onClick={close} />
          </div>
          <div className="modal-body">
            <p className="mb-0">¿Está seguro de eliminar a <strong id="trabajadorDeleteName">{trabajador.nombre || "este trabajador"}</strong>?</p>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
            <button type="submit" className="btn btn-danger" disabled={busy}>Eliminar</button>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}

function ObservacionModal({ data, centroUrl, close }: { data: CentroDetalleData["observaciones"]; centroUrl: string; close: () => void }) {
  const [valor, setValor] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { busy, send } = useWrite();
  function submit(e: FormEvent) {
    e.preventDefault();
    void send(data.crear_url, new URLSearchParams({ observacion: valor, next: centroUrl }), (body) => {
      const errors = record(body) && record(body.errors) ? body.errors.observacion : null;
      const first = Array.isArray(errors) && record(errors[0]) && text(errors[0].message) ? errors[0].message : null;
      setError(first ?? "No se pudo guardar la observación.");
    });
  }
  return (
    <NativeModal id="modalObservacion" title="Nueva observación" close={close} busy={busy} size=" modal-dialog-centered" controls="button:not([disabled]),textarea:not([disabled])">
      <div className="modal-content">
        <form method="post" id="observacionModalForm" onSubmit={submit}>
          <div className="modal-header">
            <h5 className="modal-title" id="modalObservacionLabel">Nueva observación</h5>
            <button type="button" className="btn-close btn-close-white" aria-label="Close" onClick={close} />
          </div>
          <div className="modal-body">
            <div className="mb-3">
              <label htmlFor="id_observacion" className="form-label">{data.campo.label}</label>
              <textarea name="observacion" cols={40} rows={data.campo.rows} className="form-control" placeholder={data.campo.placeholder}
                required id="id_observacion" value={valor} onChange={(e) => setValor(e.target.value)} aria-invalid={error ? "true" : undefined} />
              {error && <div className="text-danger small" role="alert">{error}</div>}
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={busy}>Guardar observación</button>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}

const PILLS = { activo: ["cdf-pill--success", "Activo"], suspendido: ["cdf-pill--gold", "Suspendido"], baja: ["cdf-pill--muted", "Baja"] } as const;

function UsuariosPanel({ data, open }: { data: NonNullable<CentroDetalleData["usuarios"]>; open: (acceso: Acciones, accion: Accion) => void }) {
  return (
    <>
      <div className="cdi-section-head">
        <h2 className="cdi-section-title">Usuarios del centro</h2>
        {data.generar_url && <a href={href(data.generar_url)} className="cdf-btn cdf-btn--primary"><i className="bi bi-person-plus" />Generar usuario</a>}
      </div>
      {data.credenciales && <small className="text-muted">Credenciales visibles solo para el referente del centro y administradores. La contraseña temporal se oculta automáticamente cuando el usuario la cambia.</small>}
      <hr className="cdi-divider" />
      <div className="cdf-tbl-scroll">
        <table className="cdf-table">
          <thead>
            <tr>
              <th>Usuario</th><th>Nombre</th><th>Email</th><th>Estado</th>
              {data.credenciales && <th>Contraseña temporal</th>}
              {data.administrar && <th>Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {data.filas.length ? data.filas.map((u) => {
              const [tone, label] = PILLS[u.estado];
              return (
                <tr key={u.id}>
                  <td>
                    <code>{u.username}</code>
                    {u.responsable && <>{" "}<span className="cdf-pill cdf-pill--teal ms-1" title="Referente vigente en la ficha del CDI">Responsable</span></>}
                  </td>
                  <td>{u.nombre}</td>
                  <td>{u.email}</td>
                  <td><span className={`cdf-pill ${tone}`} title={u.estado !== "activo" && u.motivo ? `Motivo: ${u.motivo}` : undefined}>{label}</span></td>
                  {data.credenciales && (
                    <td>
                      {u.password?.kind === "value" ? <code>{u.password.value}</code>
                        : u.password?.kind === "changed" ? <span className="cdf-td-muted">Ya cambiada</span>
                        : <span className="cdf-td-muted">No disponible</span>}
                    </td>
                  )}
                  {data.administrar && (
                    <td>
                      {!u.acciones ? <span className="cdf-td-muted">—</span> : (
                        <div className="d-flex flex-wrap gap-1">
                          {u.acciones.activo
                            ? <button type="button" className="cdf-btn cdf-btn--gold usuario-estado-btn" onClick={() => open(u.acciones as Acciones, "suspender")}>Suspender</button>
                            : <button type="button" className="cdf-btn cdf-btn--success usuario-estado-btn" onClick={() => open(u.acciones as Acciones, "reactivar")}>Reactivar</button>}
                          {" "}<button type="button" className="cdf-btn cdf-btn--danger usuario-estado-btn" onClick={() => open(u.acciones as Acciones, "baja")}>Dar de baja</button>
                        </div>
                      )}
                    </td>
                  )}
                </tr>
              );
            }) : (
              <tr><td colSpan={data.columnas} className="text-center cdf-td-muted py-3">Sin usuarios generados para este centro.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

type Panel = { key: string; label: string; body: ReactNode };

/** "Carpeta con solapas laterales": sections up to the active one on the left rail, the rest on the right. */
function Folder({ panels }: { panels: Panel[] }) {
  const [active, setActive] = useState(() => Math.max(0, panels.findIndex((p) => `#${p.key}` === window.location.hash)));
  const rail = (side: "left" | "right") => panels.map((p, i) => ({ p, i })).filter(({ i }) => (side === "left" ? i <= active : i > active)).map(({ p, i }) => (
    <button key={p.key} type="button" className="cdi-side-tab" role="tab" aria-selected={i === active} onClick={() => setActive(i)}>
      <span>{p.label}</span>
    </button>
  ));
  return (
    <div className="cdi-shell">
      <div className="cdi-side-tabs cdi-side-tabs--left" id="cdiTabsLeft" role="tablist" aria-label="Secciones del centro">{rail("left")}</div>
      <div className="cdi-shell-content">
        {panels.map((p, i) => (
          <section key={p.key} className={`cdi-panel${i === active ? " is-active" : ""}`} data-panel={p.key} data-label={p.label} role="tabpanel">{p.body}</section>
        ))}
      </div>
      <div className="cdi-side-tabs cdi-side-tabs--right" id="cdiTabsRight" role="tablist" aria-label="Secciones pendientes">{rail("right")}</div>
    </div>
  );
}

const STATS = [["blue", "hombres", "Hombres"], ["pink", "mujeres", "Mujeres"], ["purple", "x", "Género X"], ["gold", "menores", "Menores de edad"]] as const;

type Dialog = { kind: "estado"; acceso: Acciones; accion: Accion } | { kind: "trabajador"; trabajador: Trabajador } | { kind: "observacion" } | null;

export function CentroDetalleContent({ data }: { data: CentroDetalleData }) {
  const { centro, hero, usuarios, nomina, formularios, calidad, observaciones: obs } = data;
  const [dialog, setDialog] = useState<Dialog>(null);
  const [term, setTerm] = useState("");
  const centroUrl = `/centrodeinfancia/detalle/${centro.id}`;
  const needle = term.trim().toLowerCase();
  const panels: Panel[] = [
    {
      key: "general", label: "Información general",
      body: (
        <>
          <div className="cdi-section-head"><h2 className="cdi-section-title">Información general del centro</h2></div>
          <hr className="cdi-divider" />
          <div className="row gx-4 gy-3">
            <div className="col-lg-7"><div className="cdf-info-grid">{data.general.map((i) => <InfoItem key={i.label} item={i} />)}</div></div>
            <div className="col-lg-5">
              <div className="cdf-map">
                {data.mapa ? <iframe src={data.mapa} title="Mapa de ubicación del centro" allowFullScreen /> : <span>No hay datos suficientes para cargar el mapa.</span>}
              </div>
            </div>
          </div>
          <hr className="cdi-divider" />
          <div className="cdi-section-head"><h2 className="cdi-section-title">Referente del centro</h2></div>
          <div className="cdf-info-grid">
            <InfoItem item={{ icon: "bi-person", label: "Nombre y apellido", value: data.referente.nombre }} />
            {data.referente.items.map((i) => <InfoItem key={i.label} item={i} />)}
          </div>
        </>
      ),
    },
    {
      key: "funcionamiento", label: "Funcionamiento",
      body: (
        <>
          <div className="cdi-section-head"><h2 className="cdi-section-title">Funcionamiento</h2></div>
          <hr className="cdi-divider" />
          <div className="cdf-info-grid">
            {data.funcionamiento.items.map((i) => <InfoItem key={i.label} item={i} />)}
            <div className="cdf-info-item">
              <i className="bi bi-clock" />
              <div>
                <div className="cdf-info-label">Horarios por día</div>
                <div className="cdf-info-value">
                  {data.funcionamiento.horarios.length
                    ? <ul className="mb-0 ps-3">{data.funcionamiento.horarios.map((h) => <li key={h.dia}>{h.dia}: {h.apertura} a {h.cierre}</li>)}</ul>
                    : <span>-</span>}
                </div>
              </div>
            </div>
          </div>
        </>
      ),
    },
  ];
  if (usuarios) panels.push({ key: "usuarios", label: "Usuarios del centro", body: <UsuariosPanel data={usuarios} open={(acceso, accion) => setDialog({ kind: "estado", acceso, accion })} /> });
  const close = () => setDialog(null);
  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      <link href="https://fonts.googleapis.com/css2?family=Lora:wght@600;700&display=swap" rel="stylesheet" />
      <link rel="stylesheet" href="/static/custom/css/cdf.css" />
      <link rel="stylesheet" href="/static/custom/css/centrodeinfancia.css" />
      <div className="cdf-page cdi-page">
        <div className="cdf-hero">
          <div className="cdf-hero-block">
            <p className="cdi-hero-kicker">Centro de Desarrollo Infantil</p>
            <h1>{centro.nombre}</h1>
          </div>
          <div className="cdf-hero-side">
            {centro.codigo_cdi && <><span className="cdf-pill cdf-pill--gold">N° {centro.codigo_cdi}</span>{" "}</>}
            <span className="cdf-pill cdf-pill--success">Activo</span>
          </div>
          <div className="cdi-hero-stats">
            <div className="cdi-hero-stat"><b>{hero.nomina}</b><span>Nómina</span></div>
            <div className="cdi-hero-stat-sep" />
            <div className="cdi-hero-stat"><b>{hero.trabajadores}</b><span>Trabajadores</span></div>
            {hero.formularios !== null && <><div className="cdi-hero-stat-sep" /><div className="cdi-hero-stat"><b>{hero.formularios}</b><span>Formularios</span></div></>}
            <div className="cdi-hero-stat-sep" />
            <div className="cdi-hero-stat"><b>{hero.anio_inicio}</b><span>Año de inicio</span></div>
          </div>
        </div>
        <Folder panels={panels} />
        <div className="cdi-section-head">
          <h2 className="cdi-section-title">Nómina</h2>
          {nomina.asistencia_url && <><a href={href(nomina.asistencia_url)} className="cdf-btn cdf-btn--gold"><i className="bi bi-calendar-check" />Tomar asistencia</a>{" "}</>}
          <a href={href(nomina.ver_url)} className="cdf-btn cdf-btn--primary"><i className="bi bi-people" />Ver nómina completa</a>
        </div>
        <div className="cdi-stats-row">
          {STATS.map(([dot, key, label]) => (
            <div key={key} className="cdi-stat-card">
              <span className={`cdi-stat-dot cdi-stat-dot--${dot}`} />
              <div><div className="cdi-stat-num">{nomina[key]}</div><div className="cdi-stat-lbl">{label}</div></div>
            </div>
          ))}
        </div>
        <div className="cdf-card">
          <div className="cdf-card-head">
            <i className="bi bi-person-badge" /><span>Trabajadores</span>
            <div className="cdf-head-tools">
              <input id="trabajadorSearch" type="search" className="cdf-search" placeholder="Buscar trabajador…" value={term} onChange={(e) => setTerm(e.target.value)} />
              {data.trabajadores.crear_url && <>{" "}<a href={href(data.trabajadores.crear_url)} className="cdf-btn cdf-btn--gold">Agregar trabajador</a></>}
            </div>
          </div>
          <div className="cdf-tbl-scroll">
            <table className="cdf-table" id="tablaTrabajadores">
              <thead><tr><th>Apellido y nombre</th><th>Subcomponente</th><th>Función</th><th>Fecha de carga</th><th>Acciones</th></tr></thead>
              <tbody>
                {data.trabajadores.filas.length ? data.trabajadores.filas.map((t) => {
                  const row = `${t.nombre}${t.subcomponente}${t.funcion}${t.fecha_carga}Ver${t.editar ? "Editar" : ""}${t.eliminar ? "Eliminar" : ""}`;
                  return (
                    <tr key={t.id} hidden={needle !== "" && !row.toLowerCase().includes(needle)}>
                      <td>{t.nombre}</td><td>{t.subcomponente}</td><td>{t.funcion}</td><td>{t.fecha_carga}</td>
                      <td>
                        <div className="cdf-actions">
                          <a href={href(t.ver)} className="cdf-btn cdf-btn--primary">Ver</a>
                          {t.editar && <>{" "}<a href={href(t.editar)} className="cdf-btn cdf-btn--gold">Editar</a></>}
                          {t.eliminar && <>{" "}<button type="button" className="cdf-btn cdf-btn--danger trabajador-eliminar-btn" onClick={() => setDialog({ kind: "trabajador", trabajador: t })}>Eliminar</button></>}
                        </div>
                      </td>
                    </tr>
                  );
                }) : <tr><td colSpan={5} className="text-center cdf-td-muted py-3">No hay trabajadores asociados a este centro.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
        {formularios && (
          <div className="cdf-card">
            <div className="cdf-card-head">
              <i className="bi bi-file-earmark-text" /><span>Formularios</span>
              <div className="cdf-head-tools">
                <a href={href(formularios.listado_url)} className="cdf-btn">Ver todos</a>
                {formularios.crear_url && <>{" "}<a href={href(formularios.crear_url)} className="cdf-btn cdf-btn--primary">Nuevo formulario</a></>}
              </div>
            </div>
            <div className="cdf-card-body pb-2"><small className="text-muted">Últimas 3 instancias del formulario del centro.</small></div>
            <div className="cdf-tbl-scroll">
              <table className="cdf-table">
                <thead><tr><th>ID</th><th>Fecha relevamiento</th><th>Quien responde</th><th>Actualizado</th><th>Acciones</th></tr></thead>
                <tbody>
                  {formularios.filas.length ? formularios.filas.map((f) => (
                    <tr key={f.id}>
                      <td>{f.id}</td><td>{f.fecha}</td><td>{f.respondente}</td><td>{f.actualizado}</td>
                      <td><div className="cdf-actions"><a href={href(f.ver)} className="cdf-btn cdf-btn--primary">Ver</a>{f.editar && <>{" "}<a href={href(f.editar)} className="cdf-btn cdf-btn--gold">Editar</a></>}</div></td>
                    </tr>
                  )) : <tr><td colSpan={5} className="text-center cdf-td-muted py-3">Todavía no hay formularios cargados para este centro.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {calidad && (
          <div className="cdf-card">
            <div className="cdf-card-head">
              <i className="bi bi-clipboard-check" /><span>Formulario de Calidad</span>
              <div className="cdf-head-tools">
                <a href={href(calidad.listado_url)} className="cdf-btn">Ver historial</a>
                {calidad.cargar_url && <>{" "}<a href={href(calidad.cargar_url)} className="cdf-btn cdf-btn--primary">{calidad.borrador ? "Continuar borrador" : "Nuevo formulario"}</a></>}
              </div>
            </div>
            <div className="cdf-card-body pb-2">
              <small className="text-muted">
                Últimos envíos ({calidad.total} en total).{calidad.borrador && <> Hay un borrador sin enviar, guardado el {calidad.borrador_fecha}.</>}
              </small>
            </div>
            <div className="cdf-tbl-scroll">
              <table className="cdf-table">
                <thead><tr><th>ID</th><th>Fecha de envío</th><th>Enviado por</th><th>Acciones</th></tr></thead>
                <tbody>
                  {calidad.filas.length ? calidad.filas.map((f) => (
                    <tr key={f.id}>
                      <td>{f.id}</td><td>{f.fecha}</td><td>{f.enviado_por}</td>
                      <td><div className="cdf-actions"><a href={href(f.ver)} className="cdf-btn cdf-btn--primary">Ver</a></div></td>
                    </tr>
                  )) : <tr><td colSpan={4} className="text-center cdf-td-muted py-3">Todavía no hay formularios de calidad enviados para este centro.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        )}
        <div className="cdf-card">
          <div className="cdf-card-head"><i className="bi bi-chat-left-text" /><span>Observaciones</span></div>
          <div className="cdf-card-body">
            <div className="d-flex mb-2">
              <button type="button" className="cdf-btn cdf-btn--primary ms-auto" onClick={() => setDialog({ kind: "observacion" })}>Agregar observación</button>
            </div>
            <div className="row mt-5 max-width-100">
              <div className="col-12">
                <div className="card">
                  <div className="card-body">
                    <div className="table-responsive-lg">
                      <table className="table table-bordered table-striped projects table-sm table-compact">
                        <thead><tr><th>Fecha</th><th>Observador</th><th>Observación</th><th>Acciones</th></tr></thead>
                        <tbody>
                          {obs.filas.length ? obs.filas.map((o) => (
                            <tr key={o.id}>
                              <td>{o.fecha}</td><td>{o.observador}</td><td>{o.texto}</td>
                              <td><a href={href(o.ver)} className="btn btn-sm btn-primary">Ver</a></td>
                            </tr>
                          )) : <tr><td colSpan={4} className="text-center text-muted py-4">Sin observaciones registradas.</td></tr>}
                        </tbody>
                      </table>
                    </div>
                    <Pagination paginated={obs.paginated} number={obs.number} previous={obs.previous} next={obs.next} range={obs.range}
                      href={(page) => `?${obs.query_prefix}observaciones_page=${page}`} count={obs.count} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        {dialog?.kind === "estado" && <EstadoUsuarioModal key={dialog.acceso.url + dialog.accion} acceso={dialog.acceso} accion={dialog.accion} close={close} />}
        {dialog?.kind === "trabajador" && <EliminarTrabajadorModal key={dialog.trabajador.id} trabajador={dialog.trabajador} close={close} />}
        {dialog?.kind === "observacion" && <ObservacionModal data={obs} centroUrl={centroUrl} close={close} />}
      </div>
    </>
  );
}

function CentroDetallePage({ centro }: { centro: string }) {
  const [state] = useCdiPage(`web/cdi/centros/${centro}/${window.location.search}`, centroDetalleValid);
  return renderCdi(state, (data) => ({
    title: `Centro de Desarrollo Infantil: ${data.centro.nombre}`,
    heading: "",
    appHeader: <HeaderActions header={data.header} />,
    bodyToasts: true,
    content: <CentroDetalleContent data={data} />,
  }));
}

const OWN = /^\/centrodeinfancia\/detalle\/([1-9]\d*)$/;

// Native URL of the CDI centre detail (CDI09.01); no trailing slash, like the Django route.
export const cdiCentroDetalleRoute: RouteDefinition<{ centro: string }> = {
  name: "cdi-centro-detalle",
  match: (pathname) => {
    const own = OWN.exec(pathname);
    return own ? { centro: own[1] } : null;
  },
  render: ({ centro }) => <CentroDetallePage centro={centro} />,
};
