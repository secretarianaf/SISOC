/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen, validator and route live here. */
import { Fragment, useEffect, useRef, useState } from "react";
import { InsumosToastList } from "../InsumosToast";
import InsumosAccessError from "../InsumosAccessError";
import { Breadcrumb, internal, record, text, useMainResource, webClient } from "./MainFrame";
import { NativeModal } from "./nativeParity";
import SisocShell from "./SisocShell";
import type { RouteDefinition } from "./types";
import { HITOS_STYLESHEET } from "./userImport";

/**
 * CO01 comedor nómina read (`nomina_ver`, `nomina_directa_ver`): `comedor/nomina_detail.html` with the
 * header card, the four metric cards, the PNUD tabs, the DNI search, the table of up to 100 rows
 * and the native pagination. Data comes from `/api/web/comedores/comedores/…/nomina/`, which runs
 * the native detail views. The estado dropdown posts the native state change and the "Derivar" modal
 * the native derivation (`nomina_detail.js` and `nomina_derivar.js` behavior, one POST each,
 * never retried); «Agregar persona», «Historial de asistencia» and «Borrar» stay native links. «Editar» is a dead `#` link in the native page too (its handler is commented
 * out in `nomina_detail.js`).
 */
type Estado = "activo" | "espera" | "baja";
type Row = {
  id: number; estado: Estado; ciudadano_id: number; comunidad_indigena: boolean; situacion_calle: boolean; celiaquia: boolean;
  fecha: string; nombre: string; apellido: string; documento: string; sexo: string; estado_label: string; derivar_nombre: string;
  urls: { ciudadano: string; cambiar_estado: string; derivar: string; borrar: string };
};
const STATS = ["asistentes", "espera", "baja", "hombres", "mujeres", "no_binarios", "ninos", "adolescentes", "adultos", "adultos_mayores", "adulto_mayor_avanzado"] as const;
type Page = { has_other_pages: boolean; number: number; num_pages: number; count: number; start: number; end: number; previous: number | null; next: number | null };
export type ComedorNominaData = {
  comedor: { id: number; nombre: string; provincia: string | null; municipio: string | null };
  header: { inicio: string; fin: string; plazo: string };
  stats: Record<(typeof STATS)[number], string>;
  tabs: { key: string; label: string; active: boolean }[] | null;
  tab: string; dni: string; can_view_ciudadano: boolean; rows: Row[]; page: Page;
  estados: [string, string][]; comedores_para_derivar: { id: number; nombre: string }[];
  urls: { comedores: string; comedor: string; lista: string; historial: string | null; crear: string };
  messages: { message: string; level: "success" | "error" | "warning" | "info" }[];
};

const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const LEVELS = ["success", "error", "warning", "info"];

export function nominaValid(v: unknown): v is ComedorNominaData {
  if (!record(v) || !record(v.comedor) || !record(v.header) || !record(v.stats) || !record(v.page) || !record(v.urls)) return false;
  const c = v.comedor, h = v.header, p = v.page, u = v.urls;
  return int(c.id) && text(c.nombre) && (c.provincia === null || text(c.provincia)) && (c.municipio === null || text(c.municipio)) &&
    ["inicio", "fin", "plazo"].every((k) => text(h[k])) && STATS.every((k) => text((v.stats as Record<string, unknown>)[k])) &&
    (v.tabs === null || (Array.isArray(v.tabs) && v.tabs.every((t) => record(t) && text(t.key) && text(t.label) && typeof t.active === "boolean"))) &&
    text(v.tab) && text(v.dni) && typeof v.can_view_ciudadano === "boolean" &&
    Array.isArray(v.rows) && v.rows.every((r) => record(r) && int(r.id) && ["activo", "espera", "baja"].includes(r.estado as string) && int(r.ciudadano_id) &&
      ["comunidad_indigena", "situacion_calle", "celiaquia"].every((k) => typeof r[k] === "boolean") &&
      ["fecha", "nombre", "apellido", "documento", "sexo", "estado_label", "derivar_nombre"].every((k) => text(r[k])) &&
      record(r.urls) && ["ciudadano", "cambiar_estado", "derivar", "borrar"].every((k) => internal((r.urls as Record<string, unknown>)[k]))) &&
    typeof p.has_other_pages === "boolean" && ["number", "num_pages", "count", "start", "end"].every((k) => int(p[k])) &&
    (p.previous === null || int(p.previous)) && (p.next === null || int(p.next)) &&
    Array.isArray(v.estados) && v.estados.every((e) => Array.isArray(e) && e.length === 2 && text(e[0]) && text(e[1])) &&
    Array.isArray(v.comedores_para_derivar) && v.comedores_para_derivar.every((x) => record(x) && int(x.id) && text(x.nombre)) &&
    ["comedores", "comedor", "lista", "crear"].every((k) => internal(u[k])) && (u.historial === null || internal(u.historial)) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

// Django's `urlencode` keeps «/» (the template filter's safe set).
const urlencode = (value: string) => encodeURIComponent(value).replace(/%2F/g, "/");

const CARDS: { footer: string; rows: { icon: string; label: string; key: (typeof STATS)[number] }[] }[] = [
  { footer: "Nómina", rows: [
    { icon: "fas fa-users", label: "Asistentes", key: "asistentes" },
    { icon: "far fa-clock", label: "Lista de espera", key: "espera" },
    { icon: "fas fa-user-minus", label: "Dados de baja", key: "baja" },
  ] },
  { footer: "Género", rows: [
    { icon: "fas fa-male", label: "Hombres", key: "hombres" },
    { icon: "fas fa-female", label: "Mujeres", key: "mujeres" },
    { icon: "fas fa-transgender", label: "No binarios", key: "no_binarios" },
  ] },
  { footer: "Menores de edad", rows: [
    { icon: "fas fa-child", label: "Niñez (0-13)", key: "ninos" },
    { icon: "fas fa-user-graduate", label: "Adolescentes (14-17)", key: "adolescentes" },
  ] },
  { footer: "Mayores de edad", rows: [
    { icon: "fas fa-user-friends", label: "Adultos (18-49)", key: "adultos" },
    { icon: "fas fa-user-friends", label: "Adultos mayores (50-65)", key: "adultos_mayores" },
    { icon: "fas fa-user-clock", label: "Adultos mayores + (+66)", key: "adulto_mayor_avanzado" },
  ] },
];

/** Full-page reload after a confirmed change (`location.reload()`); replaceable in tests. */
export const comedorNominaNavigation = { reload: () => window.location.reload() };

const ACTIONS = "web/comedores/comedores/nomina/";

/** `nomina_detail.js`: one POST of the new estado, then reload; every failure is an alert, never a retry. */
async function cambiarEstado(id: number, estado: string) {
  try {
    const { data, status } = await webClient.post(`${ACTIONS}${id}/cambiar-estado/`, new URLSearchParams({ estado }), { validateStatus: () => true });
    if (status < 200 || status >= 300) throw new Error("Error al cambiar el estado.");
    if (record(data) && data.success === true) comedorNominaNavigation.reload();
    else window.alert(`No se pudo cambiar el estado: ${record(data) && text(data.error) && data.error ? data.error : "error desconocido"}`);
  } catch (error) {
    window.alert(error instanceof Error && error.message ? error.message : "Ocurrió un error al cambiar el estado.");
  }
}

/** Bootstrap's focus trap: focus landing outside the open modal goes back to its first (or last) control. */
function useBootstrapFocusTrap(modalId: string) {
  useEffect(() => {
    let backward = false;
    const keydown = (e: KeyboardEvent) => { if (e.key === "Tab") backward = e.shiftKey; };
    const focusin = (e: FocusEvent) => {
      const modal = document.getElementById(modalId);
      const target = e.target as Node | null;
      if (!modal || target === document || target === modal || modal.contains(target)) return;
      const items = Array.from(modal.querySelectorAll<HTMLElement>("a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled])"));
      (backward ? items.at(-1) : items[0])?.focus();
    };
    document.addEventListener("keydown", keydown);
    document.addEventListener("focusin", focusin);
    return () => { document.removeEventListener("keydown", keydown); document.removeEventListener("focusin", focusin); };
  }, [modalId]);
}

/**
 * Bootstrap's trap does not wrap Tab at the edges of the dialog: focus leaves the page and the
 * `focusin` handler above brings it back. A selector that matches nothing keeps the shared
 * `NativeModal` Tab trap from wrapping in its own way.
 */
const NO_EDGE_WRAP = "[data-no-edge-wrap]";

type DerivarResult = { kind: "idle" } | { kind: "warning" | "danger"; message: string };

/** `nomina_derivar.js`: one POST per confirmation; the outcome shows in the alert and is never retried. */
function DerivarModal({ row, centros, close }: { row: Row; centros: ComedorNominaData["comedores_para_derivar"]; close: () => void }) {
  const [centro, setCentro] = useState("");
  const [motivo, setMotivo] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<DerivarResult>({ kind: "idle" });
  const sending = useRef(false);
  useBootstrapFocusTrap("derivarNominaModal");
  async function confirm() {
    if (sending.current) return;
    if (!centro) { setResult({ kind: "warning", message: "Seleccioná un centro destino." }); return; }
    sending.current = true;
    setBusy(true);
    try {
      const { data } = await webClient.post(`${ACTIONS}${row.id}/derivar/`, new URLSearchParams({ centro_destino_id: centro, motivo }), { validateStatus: () => true });
      if (!record(data)) throw new Error("not json");
      if (data.success === true) { comedorNominaNavigation.reload(); return; }
      setResult({ kind: "danger", message: text(data.message) && data.message ? data.message : "Error al derivar." });
    } catch {
      setResult({ kind: "danger", message: "Error de conexión. Intentá nuevamente." });
    }
    sending.current = false;
    setBusy(false);
  }
  return (
    <NativeModal id="derivarNominaModal" title="Derivar persona" close={close} busy={busy} controls={NO_EDGE_WRAP}>
      <div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title" id="derivarNominaLabel">Derivar persona</h5>
          <button type="button" className="btn-close" aria-label="Cerrar" onClick={close} />
        </div>
        <div className="modal-body">
          <p className="mb-3">Persona: <strong id="derivarNombreCiudadano">{row.derivar_nombre}</strong></p>
          <div className="mb-3">
            <label htmlFor="derivarCentroSelect" className="form-label">Centro destino</label>
            <select id="derivarCentroSelect" className="form-select" value={centro} onChange={(e) => setCentro(e.target.value)}>
              <option value="">-- Seleccionar centro --</option>
              {centros.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
            </select>
          </div>
          <div className="mb-3">
            <label htmlFor="derivarMotivo" className="form-label">Motivo / observaciones <span className="text-muted">(opcional)</span></label>
            <textarea id="derivarMotivo" className="form-control" rows={3} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </div>
          <div id="derivarMensaje" className={result.kind === "idle" ? "alert d-none" : `alert alert-${result.kind}`}>{result.kind === "idle" ? "" : result.message}</div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-sm btn-secondary" onClick={close}>Cancelar</button>
          <button type="button" id="derivarConfirmarBtn" className="btn btn-sm btn-primary" disabled={busy} onClick={confirm}>Confirmar derivación</button>
        </div>
      </div>
    </NativeModal>
  );
}

type Menu = { row: number; kind: "estado" | "acciones" } | null;

/** The two Bootstrap dropdowns of a row, opened and closed by React (one at a time). */
function RowActions({ row, data, menu, setMenu, derivar }: { row: Row; data: ComedorNominaData; menu: Menu; setMenu: (m: Menu) => void; derivar: (id: number) => void }) {
  const toggle = (kind: "estado" | "acciones") => setMenu(menu?.row === row.id && menu.kind === kind ? null : { row: row.id, kind });
  const open = (kind: "estado" | "acciones") => menu?.row === row.id && menu.kind === kind;
  const popper = (kind: "estado" | "acciones") => (open(kind) ? { "data-bs-popper": "static" } : {});
  return (
    <>
      <td>
        <div className="dropdown">
          <button className={`nomina-btn nomina-estado-btn nomina-estado-${row.estado} dropdown-toggle${open("estado") ? " show" : ""}`} type="button"
            data-bs-toggle="dropdown" data-cambiar-url={row.urls.cambiar_estado} aria-expanded={open("estado")} onClick={() => toggle("estado")}>{row.estado_label}</button>
          <ul className={`dropdown-menu dropdown-menu-dark${open("estado") ? " show" : ""}`} {...popper("estado")}>
            {data.estados.map(([value, label]) => (
              <li key={value}>
                <a className={`dropdown-item nomina-estado-opcion${row.estado === value ? " active" : ""}`} href="#" data-estado={value}
                  onClick={(e) => { e.preventDefault(); setMenu(null); void cambiarEstado(row.id, value); }}>{label}</a>
              </li>
            ))}
          </ul>
        </div>
      </td>
      <td>
        <div className="nomina-action-buttons">
          <button className={`nomina-btn nomina-btn-actions dropdown-toggle${open("acciones") ? " show" : ""}`} type="button" data-bs-toggle="dropdown"
            aria-expanded={open("acciones")} onClick={() => toggle("acciones")}>Acciones</button>
          <ul className={`dropdown-menu dropdown-menu-dark${open("acciones") ? " show" : ""}`} {...popper("acciones")}>
            <li>
              <a className="dropdown-item editar-nomina" href="#" data-id={row.id} onClick={(e) => { e.preventDefault(); setMenu(null); }}>
                <i className="fas fa-edit" /> Editar
              </a>
            </li>
            {data.can_view_ciudadano && (
              <li>
                <a className="dropdown-item" href={row.urls.ciudadano}><i className="fas fa-eye" /> Ver detalles</a>
              </li>
            )}
            {row.estado === "activo" && (
              <li>
                <a className="dropdown-item nomina-derivar-btn" href="#" data-nomina-id={row.id} data-url={row.urls.derivar} data-ciudadano={row.derivar_nombre}
                  onClick={(e) => { e.preventDefault(); setMenu(null); derivar(row.id); }}>
                  <i className="fas fa-share-square" /> Derivar
                </a>
              </li>
            )}
          </ul>{" "}
          <a href={row.urls.borrar} className="nomina-btn nomina-btn-delete"
            onClick={(e) => { if (!window.confirm("¿Está seguro de eliminar este registro?")) { e.preventDefault(); e.stopPropagation(); } }}>
            <i className="fas fa-trash-alt" /> Borrar
          </a>
        </div>
      </td>
    </>
  );
}

export function ComedorNominaContent({ data, derivar }: { data: ComedorNominaData; derivar: (id: number) => void }) {
  const [menu, setMenu] = useState<Menu>(null);
  const table = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!menu) return;
    const outside = (e: MouseEvent) => { if (!table.current?.contains(e.target as Node)) setMenu(null); };
    const escape = (e: KeyboardEvent) => { if (e.key === "Escape") setMenu(null); };
    document.addEventListener("click", outside);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("click", outside); document.removeEventListener("keydown", escape); };
  }, [menu]);
  const { page, urls } = data;
  const tabQuery = data.tabs ? `&tab=${data.tab}` : "";
  const dniQuery = data.dni ? `&dni=${urlencode(data.dni)}` : "";
  const pageHref = (n: number) => `?page=${n}${tabQuery}${dniQuery}`;
  const limpiar = `${urls.lista}${data.tabs ? `?tab=${data.tab}` : ""}`;
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/nominaDetail.css" />
      <InsumosToastList messages={data.messages} />
      <div className="nomina-header-card bg-base-darkblue">
        <div className="row align-items-center">
          <div className="col-md-8">
            <h1 className="nomina-header-title">
              {data.comedor.nombre}{" "}
              <span className="nomina-header-divider">|</span>
            </h1>
          </div>
          <div className="col-md-4">
            <div className="nomina-header-dates">
              <p className="nomina-date-item">
                <span className="nomina-date-label">Inicio de Ejecución</span>{" "}
                <span className="nomina-date-value">{data.header.inicio}</span>
              </p>
              <p className="nomina-date-item">
                <span className="nomina-date-label">Final de Ejecución</span>{" "}
                <span className="nomina-date-value">{data.header.fin}</span>
              </p>
              <p className="nomina-date-item">
                <span className="nomina-date-label">Plazo de Ejecución</span>{" "}
                <span className="nomina-date-value">{data.header.plazo}</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="nomina-dashboard-grid">
        {CARDS.map((card) => (
          <article key={card.footer} className="nomina-dashboard-card">
            <div className="nomina-dashboard-body">
              {card.rows.map((r) => (
                <p key={r.key} className="nomina-dashboard-row">
                  <i className={r.icon} />{" "}
                  <span>{r.label} {data.stats[r.key]}</span>
                </p>
              ))}
            </div>
            <p className="nomina-dashboard-footer">{card.footer}</p>
          </article>
        ))}
      </div>

      <div className="nomina-section bg-base-darkblue">
        <div className="nomina-section-header">
          <h2 className="nomina-section-title">Nómina</h2>
          {data.tabs && (
            <nav className="nomina-tabs" aria-label="Filtro de nómina">
              {data.tabs.map((o) => (
                <Fragment key={o.key}>
                  <a href={`?tab=${o.key}${data.dni ? `&dni=${urlencode(data.dni)}` : ""}`} className={`nomina-tab-link ${o.active ? "active" : ""}`}>{o.label}</a>{" "}
                </Fragment>
              ))}
            </nav>
          )}
        </div>

        <div className="nomina-actions-bar">
          <form method="get" className="nomina-search-box">
            {data.tabs && <input type="hidden" name="tab" value={data.tab} />}
            <div className="nomina-search-field">
              <i className="fas fa-search nomina-search-icon" />{" "}
              <input type="text" className="nomina-search-input" name="dni" id="nominaSearch" defaultValue={data.dni} inputMode="numeric" placeholder="Buscar por DNI" />
            </div>
            <div className="nomina-search-actions">
              <button type="submit" className="btn btn-light">Buscar</button>{" "}
              {data.dni && <a href={limpiar} className="btn btn-outline-light">Limpiar</a>}
            </div>
          </form>
          {urls.historial && (
            <a href={urls.historial} className="nomina-add-btn">
              <i className="fas fa-user-check" />{" "}
              <span>Historial de asistencia</span>
            </a>
          )}
          <a href={urls.crear} className="nomina-add-btn">
            <i className="fas fa-plus" />{" "}
            <span>Agregar persona</span>
          </a>
        </div>

        <div className="nomina-table-container" ref={table}>
          <table className="nomina-table">
            <thead>
              <tr><th>Fecha</th><th>Nombre</th><th>Apellido</th><th>CUIT</th><th>Género</th><th>Estado</th><th /></tr>
            </thead>
            <tbody>
              {data.rows.length ? data.rows.map((e) => (
                <tr key={e.id} className="nomina-table-row">
                  <td>
                    <i className="far fa-calendar-alt" style={{ marginRight: "5px", color: "#7f8c8d" }} />{" "}
                    {e.fecha}
                  </td>
                  <td>
                    {e.nombre}
                    {(e.comunidad_indigena || e.situacion_calle || e.celiaquia) && (
                      <div className="nomina-person-badges">
                        {e.comunidad_indigena && <><span className="nomina-person-badge">Comunidad indígena</span>{" "}</>}
                        {e.situacion_calle && <><span className="nomina-person-badge">Sit. de calle</span>{" "}</>}
                        {e.celiaquia && <span className="nomina-person-badge">Celiaquía</span>}
                      </div>
                    )}
                  </td>
                  <td>
                    {data.can_view_ciudadano
                      ? <a href={e.urls.ciudadano} style={{ color: "#3498db", textDecoration: "none" }}>{e.apellido}</a>
                      : e.apellido}
                  </td>
                  <td>{e.documento}</td>
                  <td>{e.sexo}</td>
                  <RowActions row={e} data={data} menu={menu} setMenu={setMenu} derivar={derivar} />
                </tr>
              )) : (
                <tr><td colSpan={7} className="nomina-empty-message">No hay registros en la nómina.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {page.has_other_pages && (
          <div className="nomina-pagination">
            <span className="nomina-pagination-info">Mostrando {page.start}-{page.end} de {page.count}</span>
            <div className="nomina-pagination-buttons">
              {page.previous !== null
                ? <a href={pageHref(page.previous)} className="nomina-page-btn"><i className="fas fa-chevron-left" /></a>
                : <button className="nomina-page-btn" disabled><i className="fas fa-chevron-left" /></button>}{" "}
              <span className="nomina-page-number">{page.number} de {page.num_pages}</span>{" "}
              {page.next !== null
                ? <a href={pageHref(page.next)} className="nomina-page-btn"><i className="fas fa-chevron-right" /></a>
                : <button className="nomina-page-btn" disabled><i className="fas fa-chevron-right" /></button>}
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function Heading({ data }: { data: ComedorNominaData }) {
  const { comedor } = data;
  return <>Nómina de {comedor.nombre}{" "}<span className="ml-2 h5">| {comedor.provincia ?? "-"} , {comedor.municipio ?? "-"}</span></>;
}

/** `body.app-loaded`: AdminLTE marks the page up once its scripts run. */
function AppLoaded() {
  useEffect(() => {
    document.body.classList.add("app-loaded");
    return () => document.body.classList.remove("app-loaded");
  }, []);
  return null;
}

/**
 * The frame of `renderMain` plus the shell's `overlays` slot: `{% block modals %}` sits after the footer
 * in `base.html`, so the derive modal is rendered there and not inside the page content.
 */
function NominaPage({ endpoint }: { endpoint: string }) {
  const [state] = useMainResource(`${endpoint}${window.location.search}`, nominaValid);
  const [derivando, setDerivando] = useState<number | null>(null);
  if (state.status === "loading") return <main role="status">Cargando nómina…</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar la página.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  const { data } = state;
  const row = data.rows.find((r) => r.id === derivando);
  return <>
    <SisocShell
      context={state.session}
      pageTitle={`Nómina – ${data.comedor.nombre}`}
      heading={<Heading data={data} />}
      breadcrumb={<Breadcrumb items={[
        { text: "Espacios Comunitarios", url: data.urls.comedores },
        { text: data.comedor.nombre, url: data.urls.comedor },
        { text: "Nómina", url: null },
      ]} />}
      content={<>{HITOS_STYLESHEET}<ComedorNominaContent data={data} derivar={setDerivando} /></>}
      previewLinks={false}
      overlays={row && <DerivarModal key={row.id} row={row} centros={data.comedores_para_derivar} close={() => setDerivando(null)} />}
    />
    <AppLoaded />
  </>;
}

const API = "web/comedores/comedores/";
const ADMISION = /^\/comedores\/([1-9]\d*)\/admision\/([1-9]\d*)\/nomina\/$/;
const DIRECTA = /^\/comedores\/([1-9]\d*)\/nomina\/$/;

// Native URLs `nomina_ver` and `nomina_directa_ver` (trailing slash like the Django routes).
export const comedorNominaRoute: RouteDefinition<{ endpoint: string }> = {
  name: "comedor-nomina",
  match(pathname) {
    const admision = ADMISION.exec(pathname);
    if (admision) return { endpoint: `${API}${admision[1]}/admision/${admision[2]}/nomina/` };
    const directa = DIRECTA.exec(pathname);
    return directa ? { endpoint: `${API}${directa[1]}/nomina/` } : null;
  },
  render: ({ endpoint }) => <NominaPage key={endpoint} endpoint={endpoint} />,
};
