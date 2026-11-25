import { useCallback, useEffect, useRef, useState } from "react";
import { crearCliente } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "../webAccess";
import ClaroFrame, { type ClaroLayout, type ClaroUser } from "./ClaroFrame";
import InspSelect2, { type InspOption } from "./InspSelect2";
import type { NavigationNode } from "./types";

/**
 * Actas tab of the Inspecciones panel (`inspecciones/actas.html`). Data comes
 * from the vertical's G1 web API (`/api/web/inspecciones/actas/`, forwarded by
 * the core); the frame (menu, user, footer) from the core session. Filters stay
 * a native GET form with the same auto-submit rules as `panel.js`.
 */
type Row = {
  numero: string; url: string; anulada: boolean; prueba: boolean;
  escuela: { nombre: string; cueanexo: string; provincia: string; localidad: string };
  turno: string; inspector: string; fecha: string; hora: string;
  firma: "firma" | "excepcion" | ""; notificacion: "cargada" | "pendiente";
};
type Page = {
  number: number; count: number; start_index: number; end_index: number; has_other_pages: boolean;
  previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string;
};
export type ActasData = {
  layout: ClaroLayout;
  tabs: { id: string; label: string; url: string }[];
  filters: { fecha: string; inspector: InspOption | null; provincia: string; estado: string; numero: string };
  options: { provincias: { id: number; nombre: string }[]; estados: { value: string; label: string }[]; inspectores_url: string };
  has_query: boolean;
  results: Row[];
  page: Page;
};
type Session = { user: ClaroUser; navigation: NavigationNode[]; footer_version_label: string };
type State =
  | { status: "loading" }
  | { status: "error" }
  | { status: "forbidden"; prerequisite: WebPrerequisite | null }
  | { status: "ready"; data: ActasData; session: Session };

const client = crearCliente("/api");
const accepted = (status: number) => (status >= 200 && status < 300) || status === 403;
const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object";
const text = (v: unknown): v is string => typeof v === "string";

function nodeValid(n: unknown): n is NavigationNode {
  return record(n) && text(n.id) && text(n.label) && (n.href === null || safeInternalPath(n.href) !== null) &&
    Array.isArray(n.children) && n.children.every(nodeValid);
}
function sessionValid(v: unknown): v is Session {
  return record(v) && record(v.user) && ["display_name", "avatar_initial", "role_label"].every((k) => text((v.user as Record<string, unknown>)[k])) &&
    Array.isArray(v.navigation) && v.navigation.every(nodeValid) && text(v.footer_version_label);
}
function rowValid(r: unknown): r is Row {
  return record(r) && text(r.numero) && safeInternalPath(r.url) !== null && typeof r.anulada === "boolean" && typeof r.prueba === "boolean" &&
    record(r.escuela) && ["nombre", "cueanexo", "provincia", "localidad"].every((k) => text((r.escuela as Record<string, unknown>)[k])) &&
    ["turno", "inspector", "fecha", "hora"].every((k) => text(r[k])) && ["firma", "excepcion", ""].includes(r.firma as string) &&
    ["cargada", "pendiente"].includes(r.notificacion as string);
}
function actasValid(v: unknown): v is ActasData {
  if (!record(v) || !record(v.layout) || !record(v.filters) || !record(v.options) || !record(v.page)) return false;
  const l = v.layout, f = v.filters, o = v.options, p = v.page;
  return Array.isArray(l.breadcrumb) && l.breadcrumb.every((b) => record(b) && text(b.text) && (b.url === null || safeInternalPath(b.url) !== null)) &&
    text(l.display_name) && text(l.role) && text(l.initials) &&
    Array.isArray(v.tabs) && v.tabs.every((t) => record(t) && text(t.id) && text(t.label) && safeInternalPath(t.url) !== null) &&
    ["fecha", "provincia", "estado", "numero"].every((k) => text(f[k])) &&
    (f.inspector === null || (record(f.inspector) && Number.isSafeInteger(f.inspector.id) && text(f.inspector.text))) &&
    Array.isArray(o.provincias) && o.provincias.every((x) => record(x) && Number.isSafeInteger(x.id) && text(x.nombre)) &&
    Array.isArray(o.estados) && o.estados.every((x) => record(x) && text(x.value) && text(x.label)) &&
    safeInternalPath(o.inspectores_url) !== null && typeof v.has_query === "boolean" &&
    Array.isArray(v.results) && v.results.every(rowValid) &&
    ["number", "count", "start_index", "end_index"].every((k) => Number.isSafeInteger(p[k])) &&
    typeof p.has_other_pages === "boolean" && Array.isArray(p.range) && text(p.query_without_page);
}

const LIST_PATH = "/inspecciones/actas/";

function submit(form: HTMLFormElement) {
  if (form.requestSubmit) form.requestSubmit(); else form.submit();
}

function Filters({ data }: { data: ActasData }) {
  const form = useRef<HTMLFormElement>(null);
  const { filters, options } = data;
  // `panel.js`: any [data-insp-auto-submit] change submits; clearing a search box too.
  useEffect(() => {
    const element = form.current;
    if (!element) return undefined;
    const change = (event: Event) => {
      if ((event.target as HTMLElement).hasAttribute?.("data-insp-auto-submit")) submit(element);
    };
    const search = (event: Event) => {
      const input = event.target as HTMLInputElement;
      if (input.type === "search" && input.hasAttribute("data-insp-auto-submit") && !input.value) submit(element);
    };
    element.addEventListener("change", change);
    element.addEventListener("search", search);
    return () => { element.removeEventListener("change", change); element.removeEventListener("search", search); };
  }, []);
  const searchInspectores = useCallback((term: string, signal: AbortSignal) => {
    const separator = options.inspectores_url.includes("?") ? "&" : "?";
    const url = `${options.inspectores_url.replace(/^\/api\//, "")}${separator}q=${encodeURIComponent(term)}`;
    return client.get(url, { signal }).then(({ data: body }: { data: unknown }) => body);
  }, [options.inspectores_url]);
  return (
    <form ref={form} method="get" action={LIST_PATH} className="insp-filtros">
      <label className="visually-hidden" htmlFor="filtro-fecha">Fecha de la visita</label>
      <input id="filtro-fecha" className="form-control" type="date" name="fecha" defaultValue={filters.fecha} data-insp-auto-submit="" />
      <label className="visually-hidden" htmlFor="filtro-inspector">Inspector</label>
      <InspSelect2 id="filtro-inspector" name="inspector" placeholder="Todos los inspectores" minimum={3} initial={filters.inspector} search={searchInspectores} />
      <label className="visually-hidden" htmlFor="filtro-provincia">Provincia</label>
      <select id="filtro-provincia" className="form-select" name="provincia" defaultValue={options.provincias.some((p) => String(p.id) === filters.provincia) ? filters.provincia : ""} data-insp-auto-submit="">
        <option value="">Todas las provincias</option>
        {options.provincias.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
      </select>
      <label className="visually-hidden" htmlFor="filtro-estado">Estado del acta</label>
      <select id="filtro-estado" className="form-select" name="estado" defaultValue={options.estados.some((e) => e.value === filters.estado) ? filters.estado : ""} data-insp-auto-submit="">
        {options.estados.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
      </select>
      <label className="visually-hidden" htmlFor="filtro-numero">Buscar por número de acta</label>
      <input id="filtro-numero" className="form-control" type="search" name="numero" maxLength={50} placeholder="Buscar por número de acta" defaultValue={filters.numero} data-insp-auto-submit="" />
      {data.has_query && <>{" "}<a className="btn btn-link" href={LIST_PATH}>Limpiar filtros</a></>}
    </form>
  );
}

function Badge({ kind, children }: { kind: string; children: string }) {
  return <span className={`insp-badge insp-badge-${kind}`}>{children}</span>;
}

function ActaRow({ row }: { row: Row }) {
  const e = row.escuela;
  return (
    <tr>
      <td>
        <a href={row.url}>{row.numero}</a>
        {row.anulada && <>{" "}<Badge kind="error">Anulada</Badge></>}
        {row.prueba && <>{" "}<Badge kind="neutro">Prueba</Badge></>}
      </td>
      <td>{e.nombre || "—"}{" "}<span className="insp-detalle insp-mono">{e.cueanexo}</span></td>
      <td>{e.provincia || "—"}{e.localidad && ` · ${e.localidad}`}</td>
      <td>{row.turno}</td>
      <td>{row.inspector}</td>
      <td>{row.fecha}{" "}<span className="insp-detalle">{row.hora}</span></td>
      <td>{row.firma === "firma" ? <Badge kind="info">Firmada</Badge> : row.firma === "excepcion" ? <Badge kind="alerta">Excepción</Badge> : "—"}</td>
      <td>{row.notificacion === "cargada" ? <Badge kind="ok">Cargada</Badge> : <Badge kind="alerta">Pendiente</Badge>}</td>
    </tr>
  );
}

function Pagination({ page }: { page: Page }) {
  if (!page.has_other_pages) return null;
  const href = (n: number) => `?${page.query_without_page}page=${n}`;
  return (
    <nav className="insp-paginacion" aria-label="Páginas">
      {page.previous !== null ? <a className="insp-pagina" href={href(page.previous)} aria-label="Página anterior">‹</a>
        : <span className="insp-pagina deshabilitada" aria-hidden="true">‹</span>}
      {page.range.map((n, index) => n === "…" ? <span key={`gap-${index}`} className="insp-pagina-puntos" aria-hidden="true">…</span>
        : n === page.number ? <span key={n} className="insp-pagina activa" aria-current="page">{n}</span>
          : <a key={n} className="insp-pagina" href={href(n)}>{n}</a>)}
      {page.next !== null ? <a className="insp-pagina" href={href(page.next)} aria-label="Página siguiente">›</a>
        : <span className="insp-pagina deshabilitada" aria-hidden="true">›</span>}
    </nav>
  );
}

export function ActasContent({ data }: { data: ActasData }) {
  return (
    <>
      <h1 className="insp-titulo">Inspecciones escolares</h1>
      <ul className="nav insp-tabs border-bottom mb-3" aria-label="Secciones">
        {data.tabs.map((tab) => (
          <li key={tab.id} className="nav-item">
            <a className={`nav-link${tab.id === "actas" ? " active" : ""}`} href={tab.url} aria-current={tab.id === "actas" ? "page" : undefined}>{tab.label}</a>
          </li>
        ))}
      </ul>
      <section className="insp-seccion">
        <div className="insp-seccion-barra"><Filters data={data} /></div>
        {data.results.length ? (
          <div className="table-responsive">
            <table className="table insp-tabla">
              <thead>
                <tr>
                  {["Número", "Escuela", "Provincia · Localidad", "Turno", "Inspector", "Hora", "Firma", "Notificación"].map((h) => <th key={h} scope="col">{h}</th>)}
                </tr>
              </thead>
              <tbody>{data.results.map((row) => <ActaRow key={row.numero} row={row} />)}</tbody>
            </table>
          </div>
        ) : (
          <div className="insp-vacio">
            <i className="fas fa-file-signature" aria-hidden="true" />
            {" "}<strong>No hay actas</strong>
            {" "}No hay actas con los filtros elegidos.
          </div>
        )}
        {data.page.count > 0 && (
          <div className="insp-seccion-pie">
            <span>Mostrando {data.page.start_index}–{data.page.end_index} de {data.page.count}</span>
            {" "}<Pagination page={data.page} />
          </div>
        )}
      </section>
    </>
  );
}

export default function ActasPage() {
  const [state, setState] = useState<State>({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    const options = { signal: controller.signal, validateStatus: accepted };
    Promise.all([
      client.get("web/session/", options),
      client.get(`web/inspecciones/actas/${window.location.search}`, options),
    ]).then(([session, actas]: { data: unknown; status?: number }[]) => {
      if (controller.signal.aborted) return;
      if (session.status === 403 || actas.status === 403) {
        setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(session.status === 403 ? session.data : actas.data) });
      } else if (sessionValid(session.data) && actasValid(actas.data)) {
        setState({ status: "ready", data: actas.data, session: session.data });
      } else setState({ status: "error" });
    }).catch(() => { if (!controller.signal.aborted) setState({ status: "error" }); });
    return () => controller.abort();
  }, []);
  if (state.status === "loading") return <main role="status">Cargando actas…</main>;
  if (state.status === "error") return <main role="alert">No se pudieron cargar las actas.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  return (
    <ClaroFrame title="Inspecciones escolares" user={state.session.user} layout={state.data.layout} navigation={state.session.navigation} footerLabel={state.session.footer_version_label}>
      <ActasContent data={state.data} />
    </ClaroFrame>
  );
}
