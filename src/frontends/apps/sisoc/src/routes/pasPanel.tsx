/* eslint-disable react-refresh/only-export-components -- panel module: its validators and frame helpers travel with the screen (PAS06.03 reuses them). */
import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { internal, text } from "./MainFrame";
import {
  BuscadorButton, EmptyState, ModuleHeader, PAS_API, PAS_STYLESHEET, PasAppHeader, WorkflowNav,
  bool, formacionValid, integer, list, nullable, shape, stylesheetsReady, urlencode, workflowValid,
  type Formacion, type WorkflowCard,
} from "./pasFrame";
import { navigation } from "./userImport";

/**
 * «Panel de Control» (`pas/panel-control[/<pk>]`, `pas/<pk>`; `pas/persona_detail.html`):
 * side list of titulares, the titular card and the four Bootstrap 5.3 tabs. The
 * «Declaración Jurada» tab (PAS02.01) links the native PDF downloads only.
 */
type Aviso = { codigo: number; descripcion: string };
type Estado = { id: number; nombre: string; css_class: string };
export type Persona = {
  id: number; apellidos: string; nombres: string; dni: number; id_persona: number; cuit: string; genero: string;
  provincia: string; municipio: string; domicilio: string; correo_electronico: string; telefono_celular: string;
  estado: Estado; avisos: Aviso[]; fecha_creacion: string; fecha_actualizacion: string;
  ddjj_vigente: { id: number; download_url: string } | null;
};
type Mini = {
  id: number; apellidos: string; nombres: string; cuit: string; dni: number; provincia: string;
  estado: { nombre: string; css_class: string }; mostrar_tag_ddjj: boolean; mostrar_tag_fch: boolean;
};
type Ddjj = {
  declaraciones: { id: number; version: number; presentada: string; es_ultima: boolean }[];
  seleccionada: { id: number; version: number; presentada: string; download_url: string; respuestas: { clave: string; etiqueta: string; respuesta: string }[] } | null;
  vigente_download_url: string | null;
};
type Evento =
  | { tipo: "ddjj"; fecha: string; fecha_iso: string; id: number; version: number }
  | { tipo: "estado"; fecha: string; fecha_iso: string; estado: string; avisos: Aviso[]; usuario: string | null };
export type PanelData = {
  persona: Persona | null; workflow: WorkflowCard[]; query: string; estado_actual: string;
  estados_panel: { id: number; nombre: string }[]; personas_panel: Mini[]; ddjj: Ddjj; formaciones: Formacion[];
  eventos_historial: Evento[]; capabilities: { can_change: boolean };
};

const avisoValid = (v: unknown): v is Aviso => shape(v, { codigo: integer, descripcion: text });
const personaValid = (v: unknown): v is Persona => shape(v, {
  id: integer, apellidos: text, nombres: text, dni: integer, id_persona: integer, cuit: text, genero: text,
  provincia: text, municipio: text, domicilio: text, correo_electronico: text, telefono_celular: text,
  estado: (e) => shape(e, { id: integer, nombre: text, css_class: text }), avisos: list(avisoValid),
  fecha_creacion: text, fecha_actualizacion: text,
  ddjj_vigente: nullable((d: unknown): d is object => shape(d, { id: integer, download_url: internal })),
});
const miniValid = (v: unknown): v is Mini => shape(v, {
  id: integer, apellidos: text, nombres: text, cuit: text, dni: integer, provincia: text,
  estado: (e) => shape(e, { nombre: text, css_class: text }), mostrar_tag_ddjj: bool, mostrar_tag_fch: bool,
});
const ddjjValid = (v: unknown): v is Ddjj => shape(v, {
  declaraciones: list((d: unknown): d is object => shape(d, { id: integer, version: integer, presentada: text, es_ultima: bool })),
  seleccionada: nullable((s: unknown): s is object => shape(s, {
    id: integer, version: integer, presentada: text, download_url: internal,
    respuestas: list((r: unknown): r is object => shape(r, { clave: text, etiqueta: text, respuesta: text })),
  })),
  vigente_download_url: nullable(internal),
});
const eventoValid = (v: unknown): v is Evento => shape(v, { fecha: text, fecha_iso: text }) && (
  shape(v, { tipo: (t) => t === "ddjj", id: integer, version: integer }) ||
  shape(v, { tipo: (t) => t === "estado", estado: text, avisos: list(avisoValid), usuario: nullable(text) }));
export const panelValid = (v: unknown): v is PanelData => shape(v, {
  persona: nullable(personaValid), workflow: workflowValid, query: text, estado_actual: text,
  estados_panel: list((e: unknown): e is object => shape(e, { id: integer, nombre: text })), personas_panel: list(miniValid),
  ddjj: ddjjValid, formaciones: list(formacionValid), eventos_historial: list(eventoValid),
  capabilities: (c) => shape(c, { can_change: bool }),
});

function PeoplePanel({ data, persona }: { data: PanelData; persona: Persona }) {
  return <aside className="pas-people-panel" aria-label="Titulares PAS">
    <div className="pas-people-header">
      <div><span className="pas-eyebrow">Padrón PAS</span><h2>Titulares</h2></div>
      <a href="/pas/listar" className="btn btn-sm btn-outline-light" title="Abrir buscador PAS" aria-label="Abrir buscador PAS">
        <i className="bi bi-search" aria-hidden="true" />
      </a>
    </div>
    <form method="get" className="pas-formation-search pas-panel-search">
      <label className="visually-hidden" htmlFor="pas-panel-query">Buscar titular</label>
      <div className="pas-search-input-wrap">
        <i className="bi bi-search" aria-hidden="true" />
        <input id="pas-panel-query" name="q" type="search" defaultValue={data.query} placeholder="Buscar por nombre, apellido o CUIT" />
      </div>
      <div className="pas-formation-filters" aria-label="Estado actual">
        <button type="submit" name="estado_actual" value="todos" className={data.estado_actual === "todos" ? "is-active" : ""}>Todos</button>
        {data.estados_panel.map((e) => <button key={e.id} type="submit" name="estado_actual" value={String(e.id)} className={data.estado_actual === String(e.id) ? "is-active" : ""}>{e.nombre}</button>)}
      </div>
    </form>
    <div className="pas-people-list">
      {data.personas_panel.length ? data.personas_panel.map((item) => <a key={item.id}
        href={`/pas/panel-control/${item.id}?q=${urlencode(data.query)}&estado_actual=${data.estado_actual}`}
        className={`pas-person-mini ${item.id === persona.id ? "is-active" : ""}`}>
        <div className="pas-person-mini-top">
          <span className="pas-person-mini-identity">
            <strong>{item.apellidos}, {item.nombres}</strong>
            <span className="pas-person-mini-document">{item.cuit ? item.cuit : `DNI ${item.dni}`}</span>
          </span>
          <span className={`pas-status-pill ${item.estado.css_class}`}>{item.estado.nombre}</span>
        </div>
        <span className="pas-person-mini-bottom">
          <span className="pas-person-mini-location">{item.provincia || "Sin provincia"}</span>
          <span className="pas-person-mini-conditions">
            {item.mostrar_tag_ddjj && <span className="pas-mini-condition is-ddjj" title="Declaración jurada pendiente">DDJJ</span>}
            {item.mostrar_tag_fch && <span className="pas-mini-condition is-fch" title="Puntaje FCH insuficiente en el período activo">FCH</span>}
          </span>
        </span>
      </a>) : <EmptyState icon="bi-person-x" title="Sin titulares para estos filtros" className="pas-panel-people-empty" />}
    </div>
  </aside>;
}

/** Fragment navigation of the current entry (scroll and Tab start point); a seam for tests. */
export const fragmentNavigation = { replace: (hash: string) => window.location.replace(hash) };

const TABS = [
  ["datos", "Datos personales"],
  ["ddjj", "Declaración Jurada"],
  ["capacitacion", "Capacitación FCH"],
  ["historial", "Historial de estados"],
] as const;
type Tab = (typeof TABS)[number][0];

function Datum({ label, mono = false, children }: { label: string; mono?: boolean; children: ReactNode }) {
  return <div><dt>{label}</dt><dd className={mono ? "pas-monospace" : undefined}>{children}</dd></div>;
}

function DatosTab({ persona }: { persona: Persona }) {
  return <>
    <section className="pas-personal-data" aria-labelledby="datos-titular-title">
      <h3 id="datos-titular-title" className="pas-detail-section-title">Datos del titular</h3>
      <dl className="pas-personal-data-grid">
        <Datum label="DNI" mono>{persona.dni}</Datum>
        <Datum label="IdPersona" mono>{persona.id_persona}</Datum>
        <Datum label="CUIT" mono>{persona.cuit || "Sin dato"}</Datum>
        <Datum label="Estado actual"><span className={`pas-status-pill ${persona.estado.css_class}`}>{persona.estado.nombre}</span></Datum>
        <Datum label="Provincia">{persona.provincia}</Datum>
        <Datum label="Municipio / Localidad">{persona.municipio}</Datum>
        <Datum label="Domicilio">{persona.domicilio || "Sin dato"}</Datum>
        <Datum label="Correo electrónico">{persona.correo_electronico || "Sin dato"}</Datum>
        <Datum label="Teléfono celular">{persona.telefono_celular || "Sin dato"}</Datum>
        <Datum label="Declaración Jurada">{persona.ddjj_vigente ? <>Sí ·{" "}<a href={persona.ddjj_vigente.download_url}>Descargar última</a></> : "No"}</Datum>
        <Datum label="Alta del registro">{persona.fecha_creacion}</Datum>
        <Datum label="Última actualización">{persona.fecha_actualizacion}</Datum>
      </dl>
    </section>
    <section className="pas-financial-card" aria-labelledby="informacion-financiera-title">
      <h3 id="informacion-financiera-title" className="pas-detail-section-title">Información financiera</h3>
      <div className="pas-financial-grid">
        <div><span>Asignación mensual</span><strong>Sin dato</strong></div>
        <div><span>CBU / Cuenta BNA</span><strong className="pas-monospace">Sin dato</strong></div>
        <div><span>Estado de cuenta</span><strong className="pas-integration-status"><i className="bi bi-circle-fill" aria-hidden="true" />{" "}Integración pendiente</strong></div>
      </div>
    </section>
  </>;
}

/** PAS02.01: versions in model order; changing one navigates like `pas_ddjj_panel.js`. */
export function PasDdjjTab({ ddjj }: { ddjj: Ddjj }) {
  const chosen = ddjj.seleccionada;
  return <section className="pas-personal-data">
    <h3 className="pas-detail-section-title">Historial de Declaraciones Juradas</h3>
    {chosen ? <>
      <div className="pas-ddjj-panel-toolbar">
        <label htmlFor="pas-ddjj-version">Presentación consultada</label>
        <select id="pas-ddjj-version" className="form-select" defaultValue={`?ddjj=${chosen.id}#ddjj-panel`}
          onChange={(e) => navigation.assign(e.currentTarget.value)}>
          {ddjj.declaraciones.map((d) => <option key={d.id} value={`?ddjj=${d.id}#ddjj-panel`}>
            {`Versión ${d.version} · ${d.presentada}${d.es_ultima ? " · Última" : ""}`}
          </option>)}
        </select>
      </div>
      <article className="pas-ddjj-detail-card">
        <div>
          <span className="pas-eyebrow">Declaración Jurada</span>
          <h4>Versión {chosen.version}</h4>
          <span>{chosen.presentada}</span>
        </div>
        <a className="btn btn-sm btn-outline-light" href={chosen.download_url}><i className="bi bi-file-earmark-pdf" />{" "}Descargar PDF</a>
      </article>
      <dl className="pas-ddjj-response-grid">
        {chosen.respuestas.map((r) => <div key={r.clave}><dt>{r.etiqueta}</dt><dd>{r.respuesta}</dd></div>)}
      </dl>
    </> : <div className="pas-empty-state"><strong>Sin Declaraciones Juradas presentadas</strong></div>}
  </section>;
}

function CapacitacionTab({ formaciones }: { formaciones: Formacion[] }) {
  return <div className="pas-table-wrap">
    <table className="pas-table pas-formation-table">
      <thead><tr><th>Curso</th><th>Inicio</th><th>Fin</th><th>Progreso</th><th>Puntos</th><th>Estado</th></tr></thead>
      <tbody>
        {formaciones.length ? formaciones.map((f, i) => <tr key={i}>
          <td><strong>{f.curso}</strong>{" "}<span className="pas-cell-secondary">{f.fuente}</span></td>
          <td>{f.inicio || "-"}</td><td>{f.fin || "-"}</td><td>Sin dato</td><td>Sin dato</td>
          <td><span className="pas-training-status">{f.estado}</span></td>
        </tr>) : <tr><td colSpan={6}><EmptyState icon="bi-mortarboard" title="Sin formación registrada en SISOC" /></td></tr>}
      </tbody>
    </table>
  </div>;
}

function HistorialTab({ eventos }: { eventos: Evento[] }) {
  return <ol className="pas-timeline">
    {eventos.length ? eventos.map((e, i) => <li key={i}>
      <time dateTime={e.fecha_iso}>{e.fecha}</time>
      {e.tipo === "ddjj" ? <>
        <strong>Declaración Jurada · Versión {e.version}</strong>
        <div className="pas-aviso-stack"><span className="pas-aviso-card">DDJJ presentada</span></div>
        <a className="pas-cell-secondary" href={`?ddjj=${e.id}#ddjj-panel`}>Ver presentación</a>
      </> : <>
        <strong>{e.estado}</strong>
        <div className="pas-aviso-stack">
          {e.avisos.length ? e.avisos.map((a, j) => <span key={j} className="pas-aviso-card">{a.codigo} · {a.descripcion}</span>) : <span className="pas-cell-secondary">Sin avisos</span>}
        </div>
        <span className="pas-cell-secondary">{e.usuario ?? "Sistema"}</span>
      </>}
    </li>) : <li><strong>Sin cambios registrados</strong></li>}
  </ol>;
}

/** Bootstrap 5.3 tabs: inactive tabs leave the Tab order; arrows move and show. */
function Tabs({ data, persona }: { data: PanelData; persona: Persona }) {
  const [active, setActive] = useState<Tab>(() => (window.location.hash === "#ddjj-panel" ? "ddjj" : "datos"));
  const buttons = useRef<Record<string, HTMLButtonElement | null>>({});
  useEffect(() => {
    // The browser scrolls to `#ddjj-panel` (and starts Tab there) once the native page loads;
    // the pane exists only now, so repeat that fragment navigation without a new history entry.
    if (window.location.hash !== "#ddjj-panel") return undefined;
    let active = true;
    void stylesheetsReady().then(() => { if (active) fragmentNavigation.replace("#ddjj-panel"); });
    return () => { active = false; };
  }, []);
  function keydown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const step = ({ ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 } as Record<string, number>)[event.key];
    if (!step) return;
    event.preventDefault();
    const next = TABS[(index + step + TABS.length) % TABS.length][0];
    buttons.current[next]?.focus({ preventScroll: true });
    setActive(next);
  }
  const panes: Record<Tab, ReactNode> = {
    datos: <DatosTab persona={persona} />,
    ddjj: <PasDdjjTab ddjj={data.ddjj} />,
    capacitacion: <CapacitacionTab formaciones={data.formaciones} />,
    historial: <HistorialTab eventos={data.eventos_historial} />,
  };
  return <>
    <ul className="nav pas-tabs" role="tablist">
      {TABS.map(([key, label], index) => <li key={key} className="nav-item" role="presentation">
        <button ref={(el) => { buttons.current[key] = el; }} className={`nav-link${active === key ? " active" : ""}`} id={`${key}-tab`}
          data-bs-toggle="tab" data-bs-target={`#${key}-panel`} type="button" role="tab" aria-controls={`${key}-panel`}
          aria-selected={active === key} tabIndex={active === key ? undefined : -1}
          onClick={() => setActive(key)} onKeyDown={(e) => keydown(e, index)}>{label}</button>
      </li>)}
    </ul>
    <div className="tab-content">
      {TABS.map(([key]) => <div key={key} className={`tab-pane fade${active === key ? " show active" : ""}`} id={`${key}-panel`}
        role="tabpanel" aria-labelledby={`${key}-tab`} tabIndex={0}>{panes[key]}</div>)}
    </div>
  </>;
}

function Ficha({ data, persona }: { data: PanelData; persona: Persona }) {
  return <section className="pas-panel pas-person-panel">
    <div className="pas-person-summary">
      <div>
        <span className="pas-eyebrow">Titular PAS</span>
        <h2>{persona.apellidos}, {persona.nombres}</h2>
        <span>{persona.cuit || "CUIT no informado"}</span>
      </div>
      <div className="pas-aviso-stack">
        {persona.avisos.length ? persona.avisos.map((a, i) => <span key={i} className={`pas-aviso-card ${persona.estado.css_class}`}>{a.codigo} · {a.descripcion}</span>)
          : <span className="pas-cell-secondary">Sin avisos vigentes</span>}
      </div>
    </div>
    <Tabs data={data} persona={persona} />
  </section>;
}

export type PanelExtras = { stylesheets?: ReactNode; actions?: (data: PanelData, persona: Persona) => ReactNode; overlays?: (data: PanelData, persona: Persona) => ReactNode; notices?: ReactNode };

export function PanelContent({ data, extras = {} }: { data: PanelData; extras?: PanelExtras }) {
  const persona = data.persona;
  return <>
    {extras.stylesheets}
    {PAS_STYLESHEET}
    {extras.notices}
    <PasAppHeader><div className="pas-top-actions">
      <BuscadorButton />
      {persona && data.capabilities.can_change && <div className="d-flex gap-2">
        {extras.actions ? extras.actions(data, persona) : <button type="button" className="btn btn-warning" data-bs-toggle="modal" data-bs-target="#cambiarEstadoModal">
          <i className="bi bi-arrow-left-right" aria-hidden="true" />{" "}Cambiar estado
        </button>}
        <a href={`/pas/${persona.id}/editar`} className="btn btn-outline-light" title="Editar datos personales" aria-label="Editar datos personales">
          <i className="bi bi-pencil" aria-hidden="true" />
        </a>
      </div>}
    </div></PasAppHeader>
    <main className="pas-workspace">
      <ModuleHeader title="Panel de Control"
        subtitle={persona ? `${persona.apellidos}, ${persona.nombres} · DNI ${persona.dni}` : "Consulta integral de titulares PAS"}
        aside={persona && <span className={`pas-status-pill ${persona.estado.css_class}`}>{persona.estado.nombre}</span>} />
      <WorkflowNav cards={data.workflow} />
      {persona ? <div className="pas-control-layout">
        <PeoplePanel data={data} persona={persona} />
        <Ficha data={data} persona={persona} />
      </div> : <section className="pas-panel pas-empty-state pas-empty-state-large">
        <i className="bi bi-people" aria-hidden="true" />
        <strong>No hay titulares PAS registrados</strong>
        <span>El panel estará disponible cuando exista al menos un titular en el padrón.</span>
      </section>}
    </main>
    {persona && extras.overlays?.(data, persona)}
  </>;
}

export function panelEndpoint(id?: string) {
  return `${PAS_API}panel/${id ? `${id}/` : ""}${window.location.search}`;
}
