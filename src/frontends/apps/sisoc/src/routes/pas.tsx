/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its area screens live here with the route. */
import { useEffect, useRef, useState } from "react";
import { renderMain, text, useMainResource, webClient } from "./MainFrame";
import {
  BuscadorButton, EmptyState, ModuleHeader, PAS_API, PAS_STYLESHEET, SourceChip, WorkflowNav,
  bool, formacionValid, integer, list, nullable, shape, stylesheetsReady, urlencode, workflowValid,
  type Formacion, type WorkflowCard,
} from "./pasFrame";
import PasBuscadorPage from "./pasBuscador";
import PasPanelRoute from "./pasCambioEstado";
import type { RouteDefinition } from "./types";

/**
 * PAS back office (PAS05.01, PAS06.01) on the native URLs of `pas/urls.py`:
 * «Buscador PAS» (`pas/listar`), «Panel de Control» (`pas/panel-control[/<pk>]`,
 * `pas/<pk>`, with «Cambiar estado», PAS06.03) and the areas «Formación FCH»,
 * «Mesa de Ayuda» and «Liquidación».
 * Native templates: `pas/persona_list.html`, `pas/persona_detail.html`, `pas/area.html`.
 */
type Area = "formacion" | "mesa-ayuda" | "liquidacion";
type Params = { page: "listar" } | { page: "panel"; id?: string } | { page: "area"; area: Area };

type AreaInfo = { key: string; number: string; title: string; subtitle: string };
type BaseArea = { area: AreaInfo; workflow: WorkflowCard[]; total_padron: number };
type PersonaFormacion = { id: number; apellidos: string; nombres: string; puntos_formacion: number; estado_formacion: string };
type Resumen = {
  puntos: number; objetivo: number; excedente: number; cursos_completados: number; total_cursos: number; estado: string;
  titulo: string; detalle: string; inicio_base: string; inicio_actual: string; fin_actual: string; duracion_dias: number; dia_actual: number;
};
type FormacionData = BaseArea & {
  query: string; estado_formacion: string; persona_solicitada_id: number | null; personas: PersonaFormacion[];
  has_next: boolean; next_page: number | null;
  persona_seleccionada: { id: number; apellidos: string; nombres: string; dni: number } | null;
  resumen: Resumen | null; formaciones: Formacion[];
};
type PersonasPage = { personas: PersonaFormacion[]; has_next: boolean; next_page: number | null; query: string; estado_formacion: string; persona_seleccionada_id: number | null };

const personaFormacionValid = (v: unknown): v is PersonaFormacion =>
  shape(v, { id: integer, apellidos: text, nombres: text, puntos_formacion: integer, estado_formacion: text });
const baseValid = (v: unknown): v is BaseArea =>
  shape(v, { area: (a) => shape(a, { key: text, number: text, title: text, subtitle: text }), workflow: workflowValid, total_padron: integer });
const resumenValid = nullable((v: unknown): v is Resumen => shape(v, {
  puntos: integer, objetivo: integer, excedente: integer, cursos_completados: integer, total_cursos: integer, estado: text,
  titulo: text, detalle: text, inicio_base: text, inicio_actual: text, fin_actual: text, duracion_dias: integer, dia_actual: integer,
}));
const formacionDataValid = (v: unknown): v is FormacionData => baseValid(v) && shape(v, {
  query: text, estado_formacion: text, persona_solicitada_id: nullable(integer), personas: list(personaFormacionValid),
  has_next: bool, next_page: nullable(integer),
  persona_seleccionada: nullable((p: unknown): p is object => shape(p, { id: integer, apellidos: text, nombres: text, dni: integer })),
  resumen: resumenValid, formaciones: list(formacionValid),
});
const personasPageValid = (v: unknown): v is PersonasPage => shape(v, {
  personas: list(personaFormacionValid), has_next: bool, next_page: nullable(integer), query: text, estado_formacion: text,
  persona_seleccionada_id: nullable(integer),
});

const FILTERS: [string, string][] = [["todos", "Todos"], ["cumplido", "Cumplido"], ["en-curso", "En curso"], ["sin-formacion", "Sin formación"]];

/** `pas/includes/formacion_personas.html`: one batch with the values its links repeat. */
type Batch = { personas: PersonaFormacion[]; query: string; estado: string; selected: number | null };

function PersonLinks({ batch }: { batch: Batch }) {
  if (!batch.personas.length) return <EmptyState title="Sin titulares para los filtros elegidos" className="pas-formation-empty" />;
  return <>{batch.personas.map((p) => <a key={p.id} href={`?persona=${p.id}&q=${urlencode(batch.query)}&estado_formacion=${batch.estado}`}
    className={`${batch.selected === p.id ? "is-active" : ""} pas-formation-person-link`}>
    <strong>{p.apellidos}, {p.nombres}</strong>
    <span className={`pas-points-badge is-${p.estado_formacion}`}>{p.puntos_formacion} pts</span>
  </a>)}</>;
}

/** `pas_formacion.js`: IntersectionObserver over the list, next page on the sentinel. */
function FormacionPeople({ data }: { data: FormacionData }) {
  const container = useRef<HTMLDivElement>(null);
  const sentinel = useRef<HTMLDivElement>(null);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [status, setStatus] = useState(data.has_next ? "Desplazate para cargar más titulares" : "");
  const next = useRef(data.next_page);
  const loading = useRef(false);
  useEffect(() => {
    if (!container.current || !sentinel.current || !("IntersectionObserver" in window)) return undefined;
    let active = true;
    let observer: IntersectionObserver | null = null;
    const observe = () => {
      if (!active || !container.current || !sentinel.current) return;
      observer = new IntersectionObserver(callback, { root: container.current, rootMargin: "120px 0px", threshold: 0.1 });
      observer.observe(sentinel.current);
    };
    const callback = async (entries: IntersectionObserverEntry[]) => {
      if (!entries[0].isIntersecting || !next.current || loading.current) return;
      loading.current = true;
      setStatus("Cargando titulares…");
      const params = new URLSearchParams({
        page: String(next.current), q: data.query, estado_formacion: data.estado_formacion || "todos",
        persona: data.persona_solicitada_id === null ? "" : String(data.persona_solicitada_id),
      });
      try {
        const { data: page } = await webClient.get(`${PAS_API}formacion/personas/?${params}`);
        if (!active) return;
        if (!personasPageValid(page)) throw new Error("payload");
        setBatches((b) => [...b, { personas: page.personas, query: page.query, estado: page.estado_formacion, selected: page.persona_seleccionada_id }]);
        next.current = page.has_next ? page.next_page : null;
        setStatus(next.current ? "Desplazate para cargar más titulares" : "Fin del padrón filtrado");
        if (!next.current) observer?.disconnect();
      } catch {
        if (active) setStatus("No se pudieron cargar más titulares.");
      } finally {
        loading.current = false;
      }
    };
    void stylesheetsReady().then(observe);
    return () => { active = false; observer?.disconnect(); };
  }, [data]);
  const first: Batch = { personas: data.personas, query: data.query, estado: data.estado_formacion, selected: data.persona_seleccionada?.id ?? null };
  return <div className="pas-formation-people" id="pas-formacion-personas" ref={container}>
    <div id="pas-formacion-personas-items">
      <PersonLinks batch={first} />
      {batches.map((b, i) => <PersonLinks key={i} batch={b} />)}
    </div>
    <div className="pas-infinite-scroll-status" id="pas-formacion-scroll-status" aria-live="polite">{status}</div>
    <div id="pas-formacion-scroll-sentinel" ref={sentinel} aria-hidden="true" />
  </div>;
}

function FormacionSidebar({ data }: { data: FormacionData }) {
  return <aside className="pas-formation-sidebar">
    <form method="get" className="pas-formation-search">
      <label className="visually-hidden" htmlFor="pas-formacion-query">Buscar titular</label>
      <div className="pas-search-input-wrap">
        <i className="bi bi-search" aria-hidden="true" />
        <input id="pas-formacion-query" name="q" type="search" defaultValue={data.query} placeholder="Buscar por CUIT, DNI o nombre" />
      </div>
      <div className="pas-formation-filters" aria-label="Estado de formación">
        {FILTERS.map(([value, label]) => <button key={value} type="submit" name="estado_formacion" value={value} className={data.estado_formacion === value ? "is-active" : ""}>{label}</button>)}
      </div>
    </form>
    <div className="pas-formation-sidebar-title">Seleccionar titular</div>
    <FormacionPeople data={data} />
  </aside>;
}

function CoursesTable({ formaciones }: { formaciones: Formacion[] }) {
  return <div className="pas-table-wrap">
    <table className="pas-table pas-formation-table">
      <thead><tr><th>Curso</th><th>Inicio</th><th>Fin</th><th>Progreso</th><th>Puntos</th><th>Estado</th><th>Certificado</th></tr></thead>
      <tbody>
        {formaciones.length ? formaciones.map((f, i) => <tr key={i}>
          <td><strong>{f.curso}</strong>{" "}<span className="pas-cell-secondary">{f.fuente}</span></td>
          <td>{f.inicio || "-"}</td>
          <td>{f.fin || "-"}</td>
          <td><div className="pas-progress-cell"><span className="pas-progress-track"><span style={{ width: `${f.progreso}%` }} /></span><strong>{f.progreso}%</strong></div></td>
          <td className="pas-monospace">{f.puntos} pts</td>
          <td><span className={`pas-training-status is-${f.estado_codigo}`}>{f.estado}</span></td>
          <td>{f.certificado_url ? <a href={f.certificado_url}>Descargar</a> : <span className="pas-cell-secondary">Sin dato</span>}</td>
        </tr>) : <tr><td colSpan={7}><EmptyState icon="bi-mortarboard" title="La fuente de formación todavía no está integrada" /></td></tr>}
      </tbody>
    </table>
  </div>;
}

function FormacionContent({ data }: { data: FormacionData }) {
  const persona = data.persona_seleccionada;
  const r = data.resumen;
  if (!persona || !r) {
    return <div className="pas-formation-content"><section className="pas-panel">
      <EmptyState large icon="bi-person-x" title="No hay un titular seleccionado" detail="Ajustá los filtros para consultar su formación." />
    </section></div>;
  }
  return <div className="pas-formation-content">
    <section className={`pas-validation-card is-${r.estado}`}>
      <div className="pas-score-ring"><strong>{r.puntos}</strong><span>pts</span></div>
      <div>
        <span className="pas-eyebrow">Semáforo de validación de formación</span>
        <h2>{r.titulo}</h2>
        <p>{r.detalle}</p>
      </div>
    </section>
    <div className="pas-period-definition">
      <i className="bi bi-calendar3" aria-hidden="true" />
      <span>Períodos de {r.duracion_dias} días corridos desde{" "}<strong>{r.inicio_base}</strong></span>
    </div>
    <section className="pas-formation-metrics">
      <div><span>Puntos acumulados</span><strong>{r.puntos}</strong><small>/ {r.objetivo} requeridos</small></div>
      <div><span>Día del período</span><strong>{r.dia_actual}</strong><small>/ {r.duracion_dias} · inició {r.inicio_actual}</small></div>
      <div><span>Crédito excedente</span><strong>+{r.excedente}</strong><small>para próximo período</small></div>
    </section>
    <section className="pas-panel pas-formation-courses">
      <div className="pas-formation-table-heading">
        <div>
          <h2>Cursos registrados</h2>
          <span>{persona.apellidos}, {persona.nombres} · DNI {persona.dni}</span>
        </div>
        <SourceChip>Fuente pendiente</SourceChip>
      </div>
      <CoursesTable formaciones={data.formaciones} />
    </section>
  </div>;
}

function MesaAyuda() {
  return <section className="pas-panel">
    <div className="pas-section-heading"><div><span className="pas-eyebrow">Reclamos y atención</span><h2>Bandeja de tickets</h2></div></div>
    <EmptyState large icon="bi-chat-square-text" title="Sin tickets vinculados" detail="La identificación, conversación, adjuntos y estados dependerán de la API de Mesa de Ayuda." />
  </section>;
}

function Liquidacion({ total }: { total: number }) {
  return <>
    <section className="pas-metrics">
      <div><span>Padrón PAS</span><strong>{total}</strong></div>
      <div><span>Preliquidación</span><strong>No iniciada</strong></div>
      <div><span>Nómina disponible</span><strong>No</strong></div>
    </section>
    <section className="pas-panel">
      <div className="pas-section-heading"><div><span className="pas-eyebrow">Validaciones previas</span><h2>Motor de liquidación</h2></div></div>
      <EmptyState large icon="bi-cash-stack" title="Liquidación bloqueada" detail="Faltan reglas confirmadas de FCH, DDJJ, incompatibilidades y el formato definitivo de nómina." />
    </section>
  </>;
}

function AreaPage({ area }: { area: Area }) {
  const valid = area === "formacion" ? formacionDataValid : baseValid;
  const [state] = useMainResource<BaseArea>(`${PAS_API}areas/${area}/${area === "formacion" ? window.location.search : ""}`, valid);
  return renderMain(state, "Cargando área…", (data) => ({
    title: `${data.area.title} · PAS`,
    breadcrumb: null,
    appHeader: <div className="pas-top-actions"><BuscadorButton /></div>,
    content: <>
      {PAS_STYLESHEET}
      <main className="pas-workspace">
        <ModuleHeader title={data.area.title} aside={area === "formacion"
          ? <SourceChip>Fuente de formación pendiente</SourceChip>
          : <SourceChip>Integración pendiente</SourceChip>} />
        <WorkflowNav cards={data.workflow} />
        {area === "formacion" && <section className="pas-formation-layout">
          <FormacionSidebar data={data as FormacionData} />
          <FormacionContent data={data as FormacionData} />
        </section>}
        {area === "mesa-ayuda" && <MesaAyuda />}
        {area === "liquidacion" && <Liquidacion total={data.total_padron} />}
      </main>
    </>,
  }));
}

/** `area.html`: the page reloads itself at 00:00:05 of the next local day; React asks the GET again. */
function FormacionRoute() {
  const [generation, setGeneration] = useState(0);
  useEffect(() => {
    const now = new Date();
    const next = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 5);
    const timer = window.setTimeout(() => setGeneration((n) => n + 1), next.getTime() - now.getTime());
    return () => window.clearTimeout(timer);
  }, [generation]);
  return <AreaPage key={generation} area="formacion" />;
}

const PATH = /^\/pas\/(?:(listar)|panel-control(?:\/([0-9]+))?|([0-9]+)|(formacion|mesa-ayuda|liquidacion))$/;

export const pasRoute: RouteDefinition<Params> = {
  name: "pas-backoffice",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    if (m[1]) return { page: "listar" };
    if (m[4]) return { page: "area", area: m[4] as Area };
    if (m[3]) return { page: "panel", id: m[3] };
    if (pathname.startsWith("/pas/panel-control")) return m[2] ? { page: "panel", id: m[2] } : { page: "panel" };
    return null;
  },
  render(params) {
    if (params.page === "listar") return <PasBuscadorPage />;
    if (params.page === "panel") return <PasPanelRoute id={params.id} />;
    if (params.area === "formacion") return <FormacionRoute />;
    return <AreaPage area={params.area} />;
  },
};
