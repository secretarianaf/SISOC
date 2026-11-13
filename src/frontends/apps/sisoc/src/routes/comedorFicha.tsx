/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { AdmisionModal } from "./comedorFichaAdmision";
import { FichaTablero, tableroValid, type Tablero } from "./comedorFichaTablero";
import { FichaBloques, bloquesValid, type Bloques } from "./comedorFichaBloques";
import { TarjetasFila } from "./comedorFichaTarjetas";
import { NativeToasts } from "./nativeParity";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * CO07.01 ficha of the comedor (`comedor_detail.html`), hero part: the
 * `app-header` block (actions, «Acciones» menu and convenio selector), the title
 * card and the four-panel horizontal accordion (`newcomedor.js`). Data comes from
 * `GET /api/web/comedores/comedores/<pk>/`, which runs the native view.
 *
 * The screen is not registered yet: it goes live only when every card of the
 * ficha is real. Controls whose action is a later unit (the validation modal and
 * «Comenzar Admisión») are drawn only when the page passes their handler, so
 * nothing inert ships.
 */
type Dato = { icon: string; label: string; value: string };
type Convenio = { id: number; tipo: string; creado: string | null; estado: string; vigente_pwa: boolean; seleccionada: boolean; url: string };
export type FichaHeader = {
  validar: boolean; convenio_pnud: string | null; actividades: { url: string } | null; acompanamiento_territorial: string | null; historial: string | null;
  acciones: { editar: string; responsable_tarjeta: string | null; eliminar: string; equipo_tecnico: { url: string; label: string } | null; comenzar_admision: boolean };
  convenios: Convenio[];
};
type Titulo = { conformidad_pendiente: { periodo: string } | null; nombre: string; validacion: string; programa: string; etiqueta_estado: string; es_caritas: boolean; inicio_ejecucion: string | null; plazo_ejecucion: string };
type Foto = { url: string; webp: string | null; default: boolean };
type Actividad = {
  id: number; categoria: string; actividad: string; dia: string; horario: string; responsable: string; vigencia: string; inscriptos: string; activo: boolean;
  detalle: [string, string][]; editar: string | null;
};
type Marca = { label: string; marcado: boolean };
export type Acordeon = {
  ubicacion: { mapa: { tipo: "iframe" | "vacio"; src: string | null }; datos: Dato[] };
  responsables: { foto: Foto; hay_organizacion: boolean; items: Dato[]; firmantes: { icon: string; text: string }[]; avales: Dato[] };
  prestaciones: { colaboradores: string; dias_por_semana: string; prestaciones_mensuales: string; monto_mensual: string; dias: string[]; filas: { comida: string; valores: string[] }[] };
  relevamientos: { titulo: string; pnud: boolean; agregar?: string | null; actividades?: Actividad[]; puede_gestionar?: boolean } &
    Partial<{ donaciones: Marca[]; servicio: Marca[]; espacio: Marca[] }> & { actividades_anexo?: string[] };
};
export type FichaData = { id: number; nombre: string; header: FichaHeader; titulo: Titulo; acordeon: Acordeon; tablero: Tablero; messages: { message: string; level: string }[] } & Bloques;

const strs = (v: unknown, keys: string[]) => record(v) && keys.every((k) => typeof v[k] === "string");
const list = (v: unknown, ok: (x: unknown) => boolean) => Array.isArray(v) && v.every(ok);

export function fichaValid(v: unknown): v is FichaData {
  if (!record(v) || !Number.isSafeInteger(v.id) || !text(v.nombre) || !record(v.header) || !record(v.titulo) || !record(v.acordeon)) return false;
  const h = v.header, t = v.titulo, a = v.acordeon;
  const acc = h.acciones;
  return typeof h.validar === "boolean" && (h.convenio_pnud === null || internal(h.convenio_pnud)) && (h.historial === null || internal(h.historial)) &&
    (h.acompanamiento_territorial === null || internal(h.acompanamiento_territorial)) &&
    (h.actividades === null || (record(h.actividades) && typeof h.actividades.url === "string")) &&
    record(acc) && internal(acc.editar) && internal(acc.eliminar) && typeof acc.comenzar_admision === "boolean" &&
    list(h.convenios, (c) => record(c) && Number.isSafeInteger(c.id) && strs(c, ["tipo", "estado", "url"]) && internal(c.url)) &&
    strs(t, ["nombre", "validacion", "programa", "etiqueta_estado", "plazo_ejecucion"]) && typeof t.es_caritas === "boolean" &&
    record(a.ubicacion) && list(a.ubicacion.datos, (d) => strs(d, ["icon", "label", "value"])) &&
    record(a.responsables) && record(a.responsables.foto) && typeof a.responsables.foto.url === "string" &&
    record(a.prestaciones) && list(a.prestaciones.filas, (f) => record(f) && text(f.comida) && Array.isArray(f.valores)) &&
    record(a.relevamientos) && text(a.relevamientos.titulo) && tableroValid(v.tablero) && bloquesValid(v);
}

// --- `app-header` block ------------------------------------------------------------------------

/** Bootstrap dropdown: the toggle button, its menu and closing on outside click or Escape. */
function Dropdown({ className, toggle, menuClass, children }: { className: string; toggle: ReactNode; menuClass: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [offset, setOffset] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  // Popper aligns the end of the menu with the toggle, not with the (wider) group.
  useLayoutEffect(() => {
    const group = root.current, button = group?.querySelector("button");
    if (open && group && button) setOffset(Math.max(0, group.offsetWidth - button.offsetWidth));
  }, [open]);
  useEffect(() => {
    if (!open) return undefined;
    const fuera = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    const tecla = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("click", fuera);
    document.addEventListener("keydown", tecla);
    return () => { document.removeEventListener("click", fuera); document.removeEventListener("keydown", tecla); };
  }, [open]);
  return (
    <div className={className} ref={root}>
      <button className={`btn btn-md dropdown-toggle${open ? " show" : ""}`} type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)}>{toggle}</button>
      <ul className={`${menuClass}${open ? " show" : ""}`} style={open && offset ? { right: `${offset}px` } : undefined} onClick={(e) => { if ((e.target as HTMLElement).closest(".dropdown-item")) setOpen(false); }} {...(open ? { "data-bs-popper": "static" } : {})}>{children}</ul>
    </div>
  );
}

export function FichaHeaderBar({ header, onValidar, onComenzarAdmision }: { header: FichaHeader; onValidar?: () => void; onComenzarAdmision?: () => void }) {
  const a = header.acciones;
  return (
    <div className="row g-2 align-items-center">
      <div className="col-12 col-lg d-flex flex-wrap justify-content-start justify-content-lg-end gap-2 align-items-center header-actions">
        {header.validar && onValidar && <a href="#" className="btn btn-md btn-warning" onClick={(e) => { e.preventDefault(); onValidar(); }}><i className="bi bi-clipboard-check me-1" />Validar</a>}
        {header.convenio_pnud && <a href={header.convenio_pnud} className="btn btn-md btn-outline-light"><i className="bi bi-file-earmark-text me-1" />Cargar datos del Convenio</a>}
        {header.actividades && <a href={header.actividades.url} className="btn btn-md btn-outline-light"><i className="bi bi-person-walking me-1" />Actividades</a>}
        {header.acompanamiento_territorial && <a href={header.acompanamiento_territorial} className="btn btn-md btn-outline-light"><i className="bi bi-clipboard-check me-1" />Acompañamiento Territorial</a>}
        {header.historial && <a href={header.historial} className="btn btn-md btn-outline-light"><i className="bi bi-journal-text me-1" />Historial</a>}
        <Dropdown className="btn-group" toggle={<><i className="bi bi-list" />Acciones</>} menuClass="dropdown-menu dropdown-menu-end">
          <li><a className="dropdown-item" href={a.editar}><i className="bi bi-pencil me-1" />Editar</a></li>
          {a.responsable_tarjeta && <li><a className="dropdown-item" href={a.responsable_tarjeta}><i className="bi bi-credit-card me-1" />Responsable de la tarjeta</a></li>}
          <li><a className="dropdown-item text-danger" href={a.eliminar}><i className="bi bi-trash me-1" />Eliminar</a></li>
          {a.equipo_tecnico && <li><a className="dropdown-item" href={a.equipo_tecnico.url}><i className="bi bi-person-workspace me-1" />{" "}{a.equipo_tecnico.label}</a></li>}
          {a.comenzar_admision && onComenzarAdmision && <li><button className="dropdown-item text-start" type="button" onClick={onComenzarAdmision}><i className="bi bi-box-arrow-in-up-right me-1" />Comenzar Admisión</button></li>}
        </Dropdown>
        <Dropdown className="dropdown" toggle={<><i className="bi bi-folder2-open me-1" />Seleccionar Convenio</>} menuClass="dropdown-menu dropdown-menu-end">
          {header.convenios.length ? header.convenios.map((c) => (
            <li key={c.id}>
              <a className={`dropdown-item d-flex justify-content-between align-items-center${c.seleccionada ? " active" : ""}`} href={c.url}>
                <div><strong className="d-block">{c.tipo}</strong><small className="text-muted">{c.creado ?? ""} · {c.estado}</small></div>
                <span className="d-inline-flex align-items-center gap-1">
                  {c.vigente_pwa && <i className="bi bi-check-circle-fill text-success" title="Vigente PWA" />}
                  {c.seleccionada && <i className="bi bi-check2-circle text-primary" />}
                </span>
              </a>
            </li>
          )) : <li><span className="dropdown-item-text text-muted">Sin Convenios</span></li>}
        </Dropdown>
      </div>
    </div>
  );
}

// --- Title card -------------------------------------------------------------------------------

function TituloCard({ t }: { t: Titulo }) {
  const validado = t.validacion === "Validado";
  const no = t.validacion === "No Validado";
  return (
    <div className="card mb-3">
      <div className="card-body">
        {t.conformidad_pendiente && (
          <div className="alert alert-warning d-flex align-items-center gap-2 mb-3" role="alert">
            <i className="bi bi-exclamation-triangle-fill" />
            <span>Pendiente la conformidad de prestaciones del periodo {t.conformidad_pendiente.periodo}.</span>
          </div>
        )}
        <div className="row gy-3 align-items-center">
          <div className="col-12 col-lg-9 d-flex align-items-center flex-wrap">
            <ul className="list-inline mb-0 align-middle">
              <li className="list-inline-item"><h2 className="mb-0 mx-1 fw-bold">{t.nombre} <span className="fw-light">|</span></h2></li>{" "}
              <li className="list-inline-item">
                {validado ? <button className="btn btn-sm btn-success mb-2"><i className="bi bi-check2-circle me-1" />Validado</button>
                  : no ? <button className="btn btn-sm btn-danger mb-2"><i className="bi bi-x-circle me-1" />No Validado</button>
                    : <button className="btn btn-sm btn-warning mb-2"><i className="bi bi-exclamation-triangle me-1" />Validación Pendiente</button>}
              </li>{" "}
              <li className="list-inline-item"><button className="btn btn-sm btn-primary mb-2">{t.programa}</button></li>{" "}
              <li className="list-inline-item"><button className="btn btn-sm btn-success mb-2">{t.etiqueta_estado}</button></li>
              {t.es_caritas && <li className="list-inline-item"><span className="badge badge-caritas mb-2"><i className="bi bi-heart-fill me-1" />CARITAS</span></li>}
            </ul>
          </div>
          <div className="col-12 col-lg-auto ms-lg-auto d-flex flex-column justify-content-end">
            <p className="mb-0 fs-7"><small>Inicio de Ejecución: <strong>{t.inicio_ejecucion ?? "Sin información"}</strong></small></p>
            <p className="mb-0 fs-7"><small>Final de Ejecución: <strong>--/--/--</strong></small></p>
            <p className="mb-0 fs-7"><small>Plazo de Ejecución: <strong>{t.plazo_ejecucion}</strong></small></p>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Accordion (`newcomedor.js`) ----------------------------------------------------------------

const CLOSED = 60;
const isMobile = () => window.innerWidth <= 768;

/** Widths, height and the loading state of the horizontal accordion, as the native script computes them. */
function useAccordion(abiertos: boolean[]) {
  const shell = useRef<HTMLDivElement>(null);
  const accordion = useRef<HTMLDivElement>(null);
  const [cargando, setCargando] = useState(true);
  const panels = () => Array.from(accordion.current?.querySelectorAll<HTMLElement>(".accordion-panel") ?? []);
  const anchos = () => {
    const all = panels();
    if (isMobile()) { all.forEach((p) => { p.style.width = "100%"; }); return; }
    const open = all.find((p) => p.classList.contains("open"));
    if (!open) { all.forEach((p) => { p.style.width = `${CLOSED}px`; }); return; }
    const openWidth = `calc(100% - ${(all.length - 1) * CLOSED}px)`;
    all.forEach((p) => { p.style.width = p === open ? openWidth : `${CLOSED}px`; });
  };
  const altura = () => {
    const el = accordion.current;
    const all = panels();
    if (!el || !all.length) return;
    if (isMobile()) { el.style.height = "auto"; all.forEach((p) => { p.style.height = "auto"; }); return; }
    const openWidth = el.clientWidth - (all.length - 1) * CLOSED;
    if (openWidth <= 0) return;
    // A repeated measure starts from the natural height, so it can shrink (the native script measures once).
    el.style.height = ""; all.forEach((p) => { p.style.height = ""; });
    const original = all.find((p) => p.classList.contains("open")) ?? all[0];
    el.classList.add("is-measuring");
    let max = 0;
    all.forEach((panel, i) => {
      all.forEach((item, j) => { item.classList.toggle("open", j === i); item.style.width = j === i ? `${openWidth}px` : `${CLOSED}px`; });
      const content = panel.querySelector<HTMLElement>(".accordion-content");
      if (content && content.scrollHeight > max) max = content.scrollHeight;
    });
    all.forEach((p) => p.classList.toggle("open", p === original));
    el.classList.remove("is-measuring");
    if (max > 0) { el.style.height = `${max}px`; all.forEach((p) => { p.style.height = `${max}px`; }); }
    anchos();
  };
  useLayoutEffect(() => { anchos(); });
  useEffect(() => {
    let frame = 0;
    const medir = () => { anchos(); altura(); };
    const cargar = () => { altura(); setCargando(false); };
    frame = requestAnimationFrame(medir);
    window.addEventListener("resize", medir);
    if (document.readyState === "complete") cargar(); else window.addEventListener("load", cargar);
    // The native page measures at `load`, with its stylesheet and fonts applied: measure again when they arrive.
    const hoja = document.querySelector<HTMLLinkElement>('link[href$="comedor_detail.css"]');
    if (hoja && !hoja.sheet) hoja.addEventListener("load", cargar);
    void document.fonts?.ready.then(altura);
    return () => { cancelAnimationFrame(frame); window.removeEventListener("resize", medir); window.removeEventListener("load", cargar); hoja?.removeEventListener("load", cargar); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!cargando) altura(); }, [abiertos.length]); // eslint-disable-line react-hooks/exhaustive-deps
  return { shell, accordion, cargando };
}

function Panel({ cls, titulo, abierto, onToggle, id, children }: { cls: string; titulo: string; abierto: boolean; onToggle: () => void; id?: string; children: ReactNode }) {
  return (
    <div className={`accordion-panel${abierto ? " open" : ""}`} id={id}>
      <div className={`accordion-header h5 accordion-header--${cls}`} onClick={onToggle}>{titulo}</div>
      <div className="accordion-content">{children}</div>
    </div>
  );
}

const DatoP = ({ d }: { d: Dato }) => <p className="mb-2"><i className={`${d.icon} me-2`} /><strong>{d.label}:</strong> {d.value}</p>;

function PanelUbicacion({ u }: { u: Acordeon["ubicacion"] }) {
  return (
    <div className="row">
      <div className="col-12 col-lg-5">
        {u.mapa.tipo === "iframe" && u.mapa.src
          ? <div className="w-100 comedor-map-wrapper"><iframe width="100%" height="365px" frameBorder="0" className="comedor-map-iframe" src={u.mapa.src} allowFullScreen title="Mapa" /></div>
          : (
            <div className="w-100 comedor-map-wrapper comedor-map-placeholder d-flex align-items-center justify-content-center">
              <div className="d-flex align-items-center px-3 py-2">
                <div className="d-flex align-items-center justify-content-center text-secondary rounded-circle mx-2 me-3 comedor-icon-60"><i className="bi bi-geo fs-1" /></div>
                <p className="mb-0 fw-bold text-body">No hay coordenadas ni datos suficientes para cargar el mapa.</p>
              </div>
            </div>
          )}
      </div>
      <div className="col-12 col-lg-7 overflow-auto mt-3 mt-lg-0 comedor-scroll-370">{u.datos.map((d) => <DatoP key={d.label} d={d} />)}</div>
    </div>
  );
}

function PanelResponsables({ r }: { r: Acordeon["responsables"] }) {
  const img = <img src={r.foto.url} alt={r.foto.default ? "Imagen del comedor" : "Foto del comedor"} className="img-fluid rounded comedor-photo" loading="lazy" />;
  return (
    <div className="row">
      <div className="col-12 col-lg-6">
        <div className="comedor-photo-wrapper">{r.foto.webp ? <picture><source srcSet={r.foto.webp} type="image/webp" />{img}</picture> : img}</div>
      </div>
      <div className="col-12 col-lg-6 overflow-auto mt-3 mt-lg-0 comedor-scroll-370">
        {r.hay_organizacion ? (
          <>
            {r.items.map((d) => <DatoP key={d.label} d={d} />)}
            {r.firmantes.length > 0 && <><hr className="my-3" /><p className="mb-2 fw-semibold"><i className="bi bi-people-fill me-2" />Firmantes</p>
              {r.firmantes.map((f, i) => <p key={i} className="mb-2"><i className={`${f.icon} me-2`} />{f.text}</p>)}</>}
            {r.avales.length > 0 && <><hr className="my-3" /><p className="mb-2 fw-semibold"><i className="bi bi-shield-check me-2" />Avales</p>
              {r.avales.map((d) => <DatoP key={d.label} d={d} />)}</>}
          </>
        ) : <div className="alert alert-secondary mb-0" role="status">No hay una organizacion vinculada para mostrar responsables.</div>}
      </div>
    </div>
  );
}

function PanelPrestaciones({ p }: { p: Acordeon["prestaciones"] }) {
  const box = (icon: string, valor: string, label: string, last = false) => (
    <div className={`col-12 col-md-6 col-lg-3${last ? "" : " mb-3 mb-lg-0"}`}>
      <div className="small-box"><div className="inner">
        <div className="fs-2 mb-1"><i className={`bi ${icon}`} /></div>
        <div className="fw-bold fs-3 mb-0">{valor}</div>
        <div className="fw-bold fs-6">{label}</div>
      </div></div>
    </div>
  );
  return (
    <>
      <div className="row text-center mb-1">
        {box("bi-people", p.colaboradores, "Colaboradores")}{box("bi-calendar-week", p.dias_por_semana, "Dias a la semana")}
        {box("bi-cup-hot", p.prestaciones_mensuales, "Prestaciones mensuales", true)}{box("bi-currency-dollar", p.monto_mensual, "Monto prestacion mensual", true)}
      </div>
      <div className="table-responsive prestaciones-table-wrap">
        <table className="table table-bordered table-sm align-middle text-center mb-0 prestaciones-table">
          <thead>
            <tr className="prestaciones-table-head">
              <th scope="col" className="text-start">Prestacion</th>
              {p.dias.map((d) => <th scope="col" key={d}><span className="d-block">{d}</span><span className="d-block prestaciones-subhead">Prestaciones</span></th>)}
            </tr>
          </thead>
          <tbody>
            {p.filas.map((f) => <tr key={f.comida}><th scope="row" className="text-start prestaciones-row">{f.comida}</th>{f.valores.map((v, i) => <td key={i}>{v}</td>)}</tr>)}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Marcas({ titulo, items, col }: { titulo: string; items: Marca[]; col: string }) {
  return (
    <div className={col}>
      <h4 className="mb-3 fw-bold">{titulo}</h4>
      <ul className="list-unstyled mb-0">
        {items.map((m) => <li key={m.label} className="mb-1"><i className={`bi ${m.marcado ? "bi-check-circle-fill" : "bi-circle"} text-white me-2`} />{m.label}</li>)}
      </ul>
    </div>
  );
}

function PanelRelevamientos({ r }: { r: Acordeon["relevamientos"] }) {
  if (r.pnud) {
    const filas = r.actividades ?? [];
    return (
      <>
        {r.agregar && <div className="mb-3"><a href={r.agregar} className="btn btn-primary btn-sm">Agregar actividad</a></div>}
        {filas.length ? (
          <div className="table-responsive">
            <table className="table table-sm table-bordered align-middle text-white mb-0">
              <thead><tr>
                {["Categoría", "Actividad", "Día", "Horario", "Responsable", "Vigencia", "Inscriptos", "Estado", "Detalle"].map((h) => <th key={h}>{h}</th>)}
                {r.puede_gestionar && <th>Acciones</th>}
              </tr></thead>
              <tbody>
                {filas.map((a) => (
                  <tr key={a.id}>
                    <td>{a.categoria}</td><td>{a.actividad}</td><td>{a.dia}</td><td>{a.horario}</td><td>{a.responsable}</td><td>{a.vigencia}</td><td>{a.inscriptos}</td>
                    <td>{a.activo ? <span className="badge bg-success">Activa</span> : <span className="badge bg-secondary">Inactiva</span>}</td>
                    <td><details><summary className="btn btn-sm btn-outline-light py-0">Ver detalles</summary>
                      <div className="mt-2 small">{a.detalle.map(([k, v]) => <div key={k}>{k}: <strong>{v}</strong></div>)}</div></details></td>
                    {r.puede_gestionar && <td>{a.editar ? <a href={a.editar} className="btn btn-sm btn-primary">Editar</a> : "-"}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p className="mb-0 text-white">No hay actividades cargadas para este espacio.</p>}
      </>
    );
  }
  const anexo = r.actividades_anexo ?? [];
  return (
    <>
      <div className="row mb-4">
        <Marcas titulo="Donaciones" items={r.donaciones ?? []} col="col-12 col-lg-4 mb-4 mb-lg-0" />
        <Marcas titulo="Tipo de servicio" items={r.servicio ?? []} col="col-12 col-lg-4 mb-4 mb-lg-0" />
        <Marcas titulo="Tipo de espacio" items={r.espacio ?? []} col="col-12 col-lg-4" />
      </div>
      <div className="row"><div className="col-12 d-flex flex-wrap gap-2">
        {anexo.length ? anexo.map((a) => <span key={a} className="badge rounded-pill border border-light text-light fw-normal px-2 py-1">{a}</span>) : <span className="text-white">-</span>}
      </div></div>
    </>
  );
}

/** The accordion: one open panel on desktop, each panel toggles on mobile. */
export function FichaAcordeon({ data }: { data: Acordeon }) {
  const [abiertos, setAbiertos] = useState([true, false, false, false]);
  const { shell, accordion, cargando } = useAccordion(abiertos);
  const toggle = (i: number) => setAbiertos((cur) => {
    if (isMobile()) return cur.map((o, j) => (j === i ? !o : o));
    return cur[i] ? cur : cur.map((_, j) => j === i);
  });
  return (
    <div className={`accordion-shell${cargando ? " is-loading" : ""}`} ref={shell}>
      <div className="accordion-loader" aria-live="polite" aria-busy="true">
        <div className="d-flex align-items-center gap-2">
          <div className="spinner-border text-warning" role="status"><span className="visually-hidden">Cargando...</span></div>
          <span className="fw-semibold">Cargando información...</span>
        </div>
      </div>
      <div className="accordion-horizontal border rounded shadow shadow-sm mb-3" ref={accordion}>
        <Panel cls="ubicacion" titulo="Ubicación" abierto={abiertos[0]} onToggle={() => toggle(0)}><PanelUbicacion u={data.ubicacion} /></Panel>
        <Panel cls="responsables" titulo="Responsables" abierto={abiertos[1]} onToggle={() => toggle(1)}><PanelResponsables r={data.responsables} /></Panel>
        <Panel cls="prestaciones" titulo="Prestaciones" abierto={abiertos[2]} onToggle={() => toggle(2)}><PanelPrestaciones p={data.prestaciones} /></Panel>
        <Panel cls="relevamientos" titulo={data.relevamientos.titulo} abierto={abiertos[3]} onToggle={() => toggle(3)} id="legajo-actividades-pnud"><PanelRelevamientos r={data.relevamientos} /></Panel>
      </div>
    </div>
  );
}

/** Title card and accordion: the first screens of the ficha. */
export function FichaHero({ data }: { data: FichaData }) {
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/comedor_detail.css" />
      <TituloCard t={data.titulo} />
      <FichaAcordeon data={data.acordeon} />
    </>
  );
}

// --- Page and route (not registered in `routes/index.ts` until the whole ficha is real) ------------

export function FichaPage({ id }: { id: string }) {
  const [state] = useMainResource(`web/comedores/comedores/${id}/${window.location.search}`, fichaValid);
  const [admision, setAdmision] = useState(false);
  return renderMain(state, "Cargando comedor…", (data) => ({
    title: `Espacio Comunitario: ${data.nombre}`, breadcrumb: null,
    appHeader: <FichaHeaderBar header={data.header} onComenzarAdmision={() => setAdmision(true)} />,
    content: <>
      <NativeToasts messages={data.messages as Parameters<typeof NativeToasts>[0]["messages"]} />
      <FichaHero data={data} />
      <FichaTablero data={data.tablero} rows={<TarjetasFila data={data.tablero} />} />
      <FichaBloques data={data} />
      {admision && <AdmisionModal comedorId={data.id} close={() => setAdmision(false)} />}
    </>,
  }));
}

// Native GET page `comedores/<pk>` (no trailing slash).
export const comedorFichaRoute: RouteDefinition<{ id: string }> = {
  name: "comedores-ficha",
  match(pathname) {
    const m = pathname.match(/^\/comedores\/([0-9]+)$/);
    return m ? { id: m[1] } : null;
  },
  render(params) {
    return <FichaPage key={params.id} id={params.id} />;
  },
};
