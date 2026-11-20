/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen, validator and navigation seam live here with the route. */
import { useEffect, useRef, useState } from "react";
import { safeInternalPath } from "../webAccess";
import { Breadcrumb, client, internal, messagesValid, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import { NativeModal } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDI04.02/CDI04.03 nómina list (`centrodeinfancia/nomina_detail.html`): hero, metric cards, the
 * collapsible age distribution (`nomina_detail.js`), client-side search/state/room filters over the
 * current page, the table of 100 rows, the native pagination and the "Derivar" modal
 * (`nomina_derivar.js`). Cell texts come computed from the backend with the native template
 * expressions; "Agregar persona", "Ver", "Editar" and "Borrar" stay native links (create and edit
 * forms, soft-delete confirmation), the derivation is the only POST of this screen.
 */
type Estado = "activo" | "pendiente" | "baja";
type Row = {
  id: number; estado: Estado; sala_filtro: string; fecha: string; nombre: string; ciudadano_url: string; dni: string; sexo: string;
  edad: string; sala: string; derivar_nombre: string; urls: { ver: string; editar: string; borrar: string };
};
type Range = { num: string; pct: string; width: number; zero: boolean };
const RANGES = ["ninos", "adolescentes", "adultos", "adultos_mayores", "adulto_mayor_avanzado"] as const;
const STATS = ["asistentes", "hombres", "mujeres", "x", "menores", "espera"] as const;
export type NominaListaData = {
  centro: { id: number; nombre: string; url: string; codigo_cdi: string; ubicacion: string };
  stats: Record<(typeof STATS)[number], string>;
  rangos: Record<(typeof RANGES)[number], Range>;
  rows: Row[];
  page: { has_other_pages: boolean; number: number; num_pages: number; count: number; start: number; end: number; previous: number | null; next: number | null };
  centros_para_derivar: { id: number; nombre: string }[];
  urls: { lista: string; crear: string };
  messages: CdiMessage[];
};

const integer = (v: unknown): v is number => Number.isSafeInteger(v);
const rangeValid = (v: unknown) => record(v) && text(v.num) && text(v.pct) && integer(v.width) && typeof v.zero === "boolean";

export function nominaListaValid(v: unknown): v is NominaListaData {
  if (!record(v) || !record(v.centro) || !record(v.stats) || !record(v.rangos) || !record(v.page) || !record(v.urls)) return false;
  const c = v.centro, p = v.page, u = v.urls;
  return integer(c.id) && text(c.nombre) && internal(c.url) && text(c.codigo_cdi) && text(c.ubicacion) &&
    STATS.every((k) => text((v.stats as Record<string, unknown>)[k])) &&
    RANGES.every((k) => rangeValid((v.rangos as Record<string, unknown>)[k])) &&
    Array.isArray(v.rows) && v.rows.every((r) => record(r) && integer(r.id) && ["activo", "pendiente", "baja"].includes(r.estado as string) &&
      ["sala_filtro", "fecha", "nombre", "dni", "sexo", "edad", "sala", "derivar_nombre"].every((k) => text(r[k])) && internal(r.ciudadano_url) &&
      record(r.urls) && internal(r.urls.ver) && internal(r.urls.editar) && internal(r.urls.borrar)) &&
    typeof p.has_other_pages === "boolean" && integer(p.number) && integer(p.num_pages) && integer(p.count) && integer(p.start) && integer(p.end) &&
    (p.previous === null || integer(p.previous)) && (p.next === null || integer(p.next)) &&
    Array.isArray(v.centros_para_derivar) && v.centros_para_derivar.every((x) => record(x) && integer(x.id) && text(x.nombre)) &&
    internal(u.lista) && internal(u.crear) && messagesValid(v.messages);
}

/** Full-page reload after a confirmed derivation (`window.location.reload()`); replaceable in tests. */
export const nominaListaNavigation = { reload: () => window.location.reload() };

const STORAGE_KEY = "nominaDetailsExpanded";
const readExpanded = () => {
  try { return window.localStorage.getItem(STORAGE_KEY) === "true"; } catch { return false; }
};
const writeExpanded = (open: boolean) => {
  try { window.localStorage.setItem(STORAGE_KEY, String(open)); } catch { /* storage unavailable: the toggle still works */ }
};

const STAT_CARDS: { key: (typeof STATS)[number]; dot: string; label: string }[] = [
  { key: "asistentes", dot: "teal", label: "Asistentes" },
  { key: "hombres", dot: "blue", label: "Hombres" },
  { key: "mujeres", dot: "pink", label: "Mujeres" },
  { key: "x", dot: "purple", label: "Género X" },
  { key: "menores", dot: "gold", label: "Menores de edad" },
  { key: "espera", dot: "red", label: "Lista de espera" },
];

const DIST: ({ title: string } | { key: (typeof RANGES)[number]; label: string })[] = [
  { title: "Menores de edad (0–17 años)" },
  { key: "ninos", label: "Niños (0–13)" },
  { key: "adolescentes", label: "Adolescentes (14–17)" },
  { title: "Adultos (18+ años)" },
  { key: "adultos", label: "Adultos (18–49)" },
  { key: "adultos_mayores", label: "Adultos mayores (50–65)" },
  { key: "adulto_mayor_avanzado", label: "Adulto mayor avanzado (66+)" },
];

function Distribution({ data }: { data: NominaListaData }) {
  const [open, setOpen] = useState(readExpanded);
  function toggle() {
    writeExpanded(!open);
    setOpen(!open);
  }
  return (
    <div className="cdi-dist-card">
      <button className="nomina-toggle-details" type="button" onClick={toggle}>
        <span>{open ? "Ocultar estadísticas detalladas" : "Ver estadísticas detalladas"}</span>{" "}
        <i className={`fas fa-chevron-down nomina-toggle-icon${open ? " rotated" : ""}`} />
      </button>
      <div id="detailedStatsContent" className="cdi-dist-body" style={{ display: open ? "block" : "none" }}>
        {DIST.map((item) => "title" in item ? <p key={item.title} className="cdi-dist-group-title">{item.title}</p> : (
          <div key={item.key} className={`cdi-dist-row${data.rangos[item.key].zero ? " is-zero" : ""}`}>
            <span className="cdi-dist-lbl">{item.label}</span>{" "}
            <span className="cdi-dist-num">{data.rangos[item.key].num}</span>{" "}
            <div className="cdi-dist-bar"><div className="cdi-dist-fill" style={{ width: `${data.rangos[item.key].width}%` }} /></div>{" "}
            <span className="cdi-dist-pct">{data.rangos[item.key].pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const PILLS: Record<Estado, [string, string]> = {
  activo: ["cdf-pill--success", "Activo"],
  pendiente: ["cdf-pill--gold", "Pendiente"],
  baja: ["cdf-pill--muted", "Baja"],
};

/**
 * Bootstrap's focus trap (`focustrap.js`): focus landing outside the open modal goes back to its first
 * focusable control (last one after Shift+Tab). The shared Tab trap only acts while the focus is
 * on an edge control, so a Tab that starts from the page (after a blur) needs this one too.
 */
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

type DerivarResult = { kind: "idle" } | { kind: "warning" | "danger"; message: string };

/** `nomina_derivar.js`: one POST per confirmation; the outcome is shown in the alert, never retried. */
function DerivarModal({ row, centros, close }: { row: Row; centros: NominaListaData["centros_para_derivar"]; close: () => void }) {
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
      const body = new URLSearchParams({ centro_destino_id: centro, motivo });
      const { data } = await client.post(`web/cdi/nomina/${row.id}/derivar/`, body, { validateStatus: () => true });
      if (!record(data)) throw new Error("not json");
      if (data.success === true) { nominaListaNavigation.reload(); return; }
      setResult({ kind: "danger", message: text(data.message) && data.message ? data.message : "Error al derivar." });
    } catch {
      setResult({ kind: "danger", message: "Error de conexión. Intentá nuevamente." });
    }
    sending.current = false;
    setBusy(false);
  }
  return (
    <NativeModal id="derivarNominaModal" title="Derivar persona" close={close} busy={busy} controls="button:not([disabled]),select:not([disabled]),textarea:not([disabled])">
      <div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title" id="derivarNominaLabel">Derivar persona</h5>
          <button type="button" className="btn-close btn-close-white" aria-label="Cerrar" onClick={close} />
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

function pageLink(n: number | null) {
  return n === null ? undefined : `?page=${n}`;
}

export function NominaListaContent({ data }: { data: NominaListaData }) {
  const { centro, page } = data;
  const [term, setTerm] = useState("");
  const [estado, setEstado] = useState("");
  const [sala, setSala] = useState("");
  const [derivando, setDerivando] = useState<number | null>(null);
  const tbody = useRef<HTMLTableSectionElement>(null);
  const salas = Array.from(new Set(data.rows.map((r) => r.sala_filtro).filter(Boolean))).sort();
  const row = data.rows.find((r) => r.id === derivando);
  // `nomina_detail.html` filters by toggling `hidden` on the rows over their whole text content.
  useEffect(() => {
    const needle = term.trim().toLowerCase();
    tbody.current?.querySelectorAll<HTMLTableRowElement>("tr[data-estado]").forEach((tr) => {
      const matchText = needle === "" || (tr.textContent ?? "").toLowerCase().includes(needle);
      tr.hidden = !(matchText && (estado === "" || tr.dataset.estado === estado) && (sala === "" || tr.dataset.sala === sala));
    });
  }, [term, estado, sala, data.rows]);
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
            <p className="cdi-hero-kicker">Centro de Desarrollo Infantil · Nómina</p>
            <h1>{centro.nombre}</h1>
            <p className="cdf-hero-sub"><span><i className="bi bi-geo-alt" />{centro.ubicacion}</span></p>
          </div>
          <div className="cdf-hero-side">
            {centro.codigo_cdi && <><span className="cdf-pill cdf-pill--gold">N° {centro.codigo_cdi}</span>{" "}</>}
            <span className="cdf-pill cdf-pill--success">Activo</span>
          </div>
        </div>
        <div className="cdi-stats-row">
          {STAT_CARDS.map((card) => (
            <div key={card.key} className="cdi-stat-card">
              <span className={`cdi-stat-dot cdi-stat-dot--${card.dot}`} />
              <div>
                <div className="cdi-stat-num">{data.stats[card.key]}</div>
                <div className="cdi-stat-lbl">{card.label}</div>
              </div>
            </div>
          ))}
        </div>
        <Distribution data={data} />
        <div className="cdf-card">
          <div className="cdf-card-head"><i className="bi bi-people" /><span>Nómina</span></div>
          <div className="cdf-card-body">
            <div className="cdi-toolbar">
              <div className="cdi-toolbar-left">
                <input type="search" className="cdf-search" id="nominaSearch" placeholder="Buscar en nómina…" value={term} onChange={(e) => setTerm(e.target.value)} />
                <select className="cdf-search" id="nominaFiltroEstado" aria-label="Filtrar por estado" value={estado} onChange={(e) => setEstado(e.target.value)}>
                  <option value="">Todos los estados</option>
                  <option value="activo">Activo</option>
                  <option value="pendiente">Pendiente</option>
                  <option value="baja">Baja</option>
                </select>
                <select className="cdf-search" id="nominaFiltroSala" aria-label="Filtrar por sala" value={sala} onChange={(e) => setSala(e.target.value)}>
                  <option value="">Todas las salas</option>
                  {salas.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <a href={safeInternalPath(data.urls.crear) ?? "/"} className="cdf-btn cdf-btn--primary"><i className="bi bi-plus-lg" />Agregar persona</a>
            </div>
            <div className="cdf-tbl-scroll">
              <table className="cdf-table" id="tablaNomina">
                <thead>
                  <tr><th>Fecha</th><th>Apellido y nombre</th><th>DNI</th><th>Sexo</th><th>Edad</th><th>Sala</th><th>Estado</th><th>Acciones</th></tr>
                </thead>
                <tbody ref={tbody}>
                  {data.rows.length ? data.rows.map((e) => (
                    <tr key={e.id} data-estado={e.estado} data-sala={e.sala_filtro}>
                      <td>{e.fecha}</td>
                      <td><a href={safeInternalPath(e.ciudadano_url) ?? "/"}>{e.nombre}</a></td>
                      <td>{e.dni}</td>
                      <td>{e.sexo}</td>
                      <td>{e.edad}</td>
                      <td>{e.sala}</td>
                      <td><span className={`cdf-pill ${PILLS[e.estado][0]}`}>{PILLS[e.estado][1]}</span></td>
                      <td>
                        <div className="cdf-actions">
                          <a href={safeInternalPath(e.urls.ver) ?? "/"} className="cdf-btn cdf-btn--primary">Ver</a>{" "}
                          <a href={safeInternalPath(e.urls.editar) ?? "/"} className="cdf-btn cdf-btn--gold">Editar</a>{" "}
                          {e.estado === "activo" && <><button type="button" className="cdf-btn nomina-derivar-btn" data-nomina-id={e.id} onClick={() => setDerivando(e.id)}>Derivar</button>{" "}</>}
                          <a href={safeInternalPath(e.urls.borrar) ?? "/"} className="cdf-btn cdf-btn--danger"
                            onClick={(ev) => { if (!window.confirm("¿Está seguro de eliminar este registro?")) { ev.preventDefault(); ev.stopPropagation(); } }}>Borrar</a>
                        </div>
                      </td>
                    </tr>
                  )) : (
                    <tr><td colSpan={8} className="text-center cdf-td-muted py-3">No hay registros en la nómina.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
          {page.has_other_pages && (
            <div className="cdf-card-foot justify-content-between">
              <span className="cdf-td-muted">Mostrando {page.start}-{page.end} de {page.count}</span>
              <ul className="pagination mb-0">
                <li className={`page-item${page.previous === null ? " disabled" : ""}`}>
                  {page.previous !== null
                    ? <a className="page-link" href={pageLink(page.previous)} aria-label="Página anterior">Anterior</a>
                    : <a className="page-link disabled" href="#" tabIndex={-1} aria-disabled="true">Anterior</a>}
                </li>
                <li className="page-item disabled"><span className="page-link">{page.number} de {page.num_pages}</span></li>
                <li className={`page-item${page.next === null ? " disabled" : ""}`}>
                  {page.next !== null
                    ? <a className="page-link" href={pageLink(page.next)} aria-label="Página siguiente">Siguiente</a>
                    : <a className="page-link disabled" href="#" tabIndex={-1} aria-disabled="true">Siguiente</a>}
                </li>
              </ul>
            </div>
          )}
        </div>
        {row && <DerivarModal key={row.id} row={row} centros={data.centros_para_derivar} close={() => setDerivando(null)} />}
      </div>
    </>
  );
}

function NominaListaPage({ centro }: { centro: string }) {
  const [state] = useCdiPage(`web/cdi/centros/${centro}/nomina/${window.location.search}`, nominaListaValid);
  return renderCdi(state, (data) => ({
    title: `Nómina – ${data.centro.nombre}`,
    heading: "",
    breadcrumb: <Breadcrumb items={[
      { text: "Centros de Desarrollo Infantil", url: data.urls.lista },
      { text: data.centro.nombre, url: data.centro.url },
      { text: "Nómina", url: null },
    ]} />,
    content: <NominaListaContent data={data} />,
  }));
}

const OWN = /^\/centrodeinfancia\/([1-9]\d*)\/nomina\/$/;

// Native URL of the CDI nómina list (CDI04.02); same trailing slash as the Django route.
export const cdiNominaListaRoute: RouteDefinition<{ centro: string }> = {
  name: "cdi-nomina-lista",
  match: (pathname) => {
    const own = OWN.exec(pathname);
    return own ? { centro: own[1] } : null;
  },
  render: ({ centro }) => <NominaListaPage centro={centro} />,
};
