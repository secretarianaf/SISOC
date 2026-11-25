/* eslint-disable react-refresh/only-export-components -- the panel module exports its validator and the component for the tests. */
import { useEffect, useState, type ReactNode } from "react";
import { internal, record, text, webClient } from "./MainFrame";
import Select2 from "./select2";
import { apiPath } from "./vatCentrosDetalleShared";
import { ComisionCursoModal, CursoModal, type ComisionEdicion, type CursoEdicion } from "./vatCentrosDetalleCursoModales";
import { fieldsValid, planesValid, type Plan } from "./vatCentrosDetalleModales";
import type { Field } from "./vatFormShared";
import { bool, integer } from "./vatShared";

/**
 * V05.01 panel of courses and commissions of a centro: `vat/centros/partials/centro_cursos_panel.html`, the fragment the
 * native detail page loads by AJAX into `#centroCursosPanelContainer`. `/api/web/vat/centros-detalle/<id>/cursos/` runs the
 * native panel view. The filters, the row lock of a course and the local pagination are the page's own JavaScript
 * (`setupCursoComisionFilter`); like it, they only run when the centro has both courses and commissions. The "Agregar curso"
 * and edit buttons open the page's modals (`vatCentrosDetalleCursoModales.tsx`); a saved record reloads the panel like
 * `loadCursosPanel`. Course and commission deletion and the new-commission wizard are links, as in the native page.
 */
export type Curso = {
  id: number; nombre: string; plan: string; comisiones: number; edicion: CursoEdicion | null;
  urls: { detalle: string | null; comision_nueva: string | null; eliminar: string | null };
};
export type ComisionRow = {
  id: number; curso_id: number; curso_nombre: string; codigo: string; nombre: string; codigo_o_nombre: string; ubicacion: string;
  fecha_inicio: string; fecha_fin: string; cupo: string; estado: string; edicion: ComisionEdicion | null; urls: { detalle: string | null; eliminar: string | null };
};
type Modales = { curso: { fields: Field[]; planes: Plan[]; crear: string }; comision_curso: { fields: Field[] } } | null;
export type PanelData = {
  cursos: Curso[]; comisiones: ComisionRow[]; modales: Modales;
  permisos: { gestionar: boolean; agregar_curso: boolean; editar_curso: boolean; editar_comision: boolean };
};

const nullableInternal = (v: unknown) => v === null || internal(v);
const strings = (v: Record<string, unknown>, keys: string[]) => keys.every((k) => text(v[k]));
const cursoEdicionValid = (e: unknown) => e === null || (record(e) && strings(e, ["plan_estudio", "nombre", "estado", "observaciones", "guardar"]) && internal(e.guardar) &&
  Array.isArray(e.tipo) && e.tipo.every(text) && bool(e.inscripcion_libre));
const comisionEdicionValid = (e: unknown) => e === null || (record(e) && strings(e, ["curso", "curso_nombre", "ubicacion", "cupo_total", "cupo_lista_espera", "fecha_inicio", "fecha_fin", "estado", "observaciones", "guardar"]) &&
  internal(e.guardar) && bool(e.acepta_lista_espera));
const modalesValid = (m: unknown) => m === null || (record(m) && record(m.curso) && fieldsValid(m.curso.fields) && planesValid(m.curso.planes) && internal(m.curso.crear) &&
  record(m.comision_curso) && fieldsValid(m.comision_curso.fields));
const cursoValid = (c: unknown) => record(c) && integer(c.id) && text(c.nombre) && text(c.plan) && integer(c.comisiones) && cursoEdicionValid(c.edicion) && record(c.urls) &&
  nullableInternal(c.urls.detalle) && nullableInternal(c.urls.comision_nueva) && nullableInternal(c.urls.eliminar);
const comisionValid = (c: unknown) => record(c) && integer(c.id) && integer(c.curso_id) &&
  ["curso_nombre", "codigo", "nombre", "codigo_o_nombre", "ubicacion", "fecha_inicio", "fecha_fin", "cupo", "estado"].every((k) => text(c[k])) && comisionEdicionValid(c.edicion) &&
  record(c.urls) && nullableInternal(c.urls.detalle) && nullableInternal(c.urls.eliminar);

export function panelValid(v: unknown): v is PanelData {
  return record(v) && Array.isArray(v.cursos) && v.cursos.every(cursoValid) && Array.isArray(v.comisiones) && v.comisiones.every(comisionValid) && modalesValid(v.modales) &&
    record(v.permisos) && ["gestionar", "agregar_curso", "editar_curso", "editar_comision"].every((k) => bool((v.permisos as Record<string, unknown>)[k]));
}

const normalize = (value: string) => value.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
const PAGE_SIZES = [["5", "5"], ["10", "10"], ["25", "25"], ["50", "50"], ["todos", "Todos"]];
const pageSizeOf = (value: string): number | null => (value === "todos" ? null : Number.parseInt(value, 10) || null);

/** The rows that match, the page that is shown (the page is clamped like the native filter) and its summary text. */
function paginate<T>(matched: T[], size: number | null, requested: number) {
  const pages = size === null ? 1 : Math.max(Math.ceil(matched.length / size), 1);
  const page = Math.min(requested, pages);
  const visible = size === null ? matched : matched.slice((page - 1) * size, page * size);
  const first = size === null ? 1 : (page - 1) * size + 1;
  const summary = matched.length === 0 ? "Mostrando 0 de 0" : `Mostrando ${first}-${first + visible.length - 1} de ${matched.length}`;
  return { visible, page, pages: size === null || matched.length <= size ? 0 : pages, summary };
}

function Actions({ children }: { children: ReactNode }) {
  return <td><div className="sisoc-table-actions">{children}</div></td>;
}

type Modal = { kind: "curso"; edicion: CursoEdicion | null } | { kind: "comision"; edicion: ComisionEdicion } | null;

const EditButton = ({ className, onClick }: { className: string; onClick: () => void }) => (
  <button type="button" className={`sisoc-btn sisoc-btn--edit ${className}`} onClick={onClick}><i className="fas fa-pen" />{" "}<span>Editar</span></button>
);

export function CursosPanel({ data, reload = () => undefined }: { data: PanelData; reload?: () => void }) {
  const { cursos, comisiones, modales } = data;
  const [modal, setModal] = useState<Modal>(null);
  // `setupCursoComisionFilter` returns early unless both tables exist.
  const live = cursos.length > 0 && comisiones.length > 0;
  const [cSearch, setCSearch] = useState("");
  const [cEstado, setCEstado] = useState("");
  const [cSize, setCSize] = useState("5");
  const [cPage, setCPage] = useState(1);
  const [mSearch, setMSearch] = useState("");
  const [mCurso, setMCurso] = useState("");
  const [mEstado, setMEstado] = useState("");
  const [mSize, setMSize] = useState("5");
  const [mPage, setMPage] = useState(1);
  const [locked, setLocked] = useState<{ id: string; nombre: string } | null>(null);

  const search = normalize(cSearch);
  const cursosMatched = !live ? cursos : cursos.filter((c) => (!search || normalize(c.nombre).includes(search) || normalize(c.plan).includes(search)) &&
    (!cEstado || (c.comisiones ? "con_comision" : "sin_comision") === cEstado));
  const cursosView = live ? paginate(cursosMatched, pageSizeOf(cSize), cPage) : null;
  const cursoNombre = (id: string) => cursos.find((c) => String(c.id) === id)?.nombre ?? "Curso";
  const effective = mCurso ? { id: mCurso, nombre: cursoNombre(mCurso) } : locked ? { id: locked.id, nombre: locked.nombre || cursoNombre(locked.id) } : { id: "", nombre: "" };
  const mSearchValue = normalize(mSearch);
  const comisionesMatched = !live ? comisiones : comisiones.filter((c) =>
    (!mSearchValue || [c.codigo, c.nombre, c.curso_nombre, c.ubicacion].map(normalize).join(" ").includes(mSearchValue)) &&
    (!effective.id || String(c.curso_id) === effective.id) && (!mEstado || c.estado === mEstado));
  const comisionesView = live ? paginate(comisionesMatched, pageSizeOf(mSize), mPage) : null;
  const cursosShown = new Set(cursosView?.visible.map((c) => c.id));
  const comisionesShown = new Set(comisionesView?.visible.map((c) => c.id));

  const lockRow = (c: Curso) => {
    if (!live) return;
    const id = String(c.id);
    setMPage(1);
    if (locked?.id === id) { setLocked(null); setMCurso(""); } else { setLocked({ id, nombre: c.nombre }); setMCurso(id); }
  };
  const release = () => { setLocked(null); setMCurso(""); setMPage(1); };

  const cursosSummary = cursosView ? cursosView.summary : `Mostrando 1-${cursos.length} de ${cursos.length}`;
  const comisionesSummary = comisionesView ? comisionesView.summary : `Mostrando 1-${comisiones.length} de ${comisiones.length}`;
  const hint = live && effective.id ? `Mostrando comisiones de: ${effective.nombre} (${comisionesView!.visible.length})` : "Comisiones vinculadas a cursos del centro.";

  return (
    <div data-panel-rendered="1" className="sisoc-section-stack">
      <section>
        <div className="sisoc-section-header-bar">Oferta educativa 2026</div>
        <div className="sisoc-section-card">
          <div className="sisoc-toolbar">
            <div className="sisoc-toolbar-left">
              <label className="sisoc-toolbar-field" htmlFor="cursosFilterSearch">
                <i className="fas fa-search" />{" "}
                <input type="search" id="cursosFilterSearch" placeholder="Buscar curso..." autoComplete="off" value={cSearch}
                  onChange={(e) => { setCSearch(e.target.value); setCPage(1); }} />
              </label>
              <label className="sisoc-toolbar-field" htmlFor="cursosFilterEstado">
                <select id="cursosFilterEstado" value={cEstado} onChange={(e) => { setCEstado(e.target.value); setCPage(1); }}>
                  <option value="">Filtrar por Estado de carga</option>
                  <option value="con_comision">Creado con comisión</option>
                  <option value="sin_comision">Creado sin comisión</option>
                </select>
              </label>
              <select id="cursosFilterPageSize" className="sisoc-hidden-control" value={cSize} onChange={(e) => { setCSize(e.target.value); setCPage(1); }}>
                {PAGE_SIZES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
              <button type="button" id="cursosFilterClear" className="sisoc-hidden-control" onClick={() => { setCSearch(""); setCEstado(""); setCSize("5"); setCPage(1); }}>Limpiar</button>
            </div>
            {data.permisos.gestionar && data.permisos.agregar_curso && (
              <button type="button" className="sisoc-btn sisoc-btn--add" onClick={() => setModal({ kind: "curso", edicion: null })}>
                <i className="fas fa-plus" />{" "}<span>Agregar curso</span>
              </button>
            )}
          </div>
          {cursos.length > 0 ? (
            <>
              <div className="sisoc-table-shell">
                <div className="sisoc-table-wrap">
                  <table className="sisoc-table" id="tablaCursosCentro">
                    <thead><tr><th>Plan Curricular</th><th>Curso FP</th><th>Cant De Comisiones</th><th>Estado</th><th>Acciones</th></tr></thead>
                    <tbody>
                      {cursos.map((c) => {
                        const selected = live && effective.id === String(c.id);
                        const hidden = live && !cursosShown.has(c.id);
                        return (
                          <tr key={c.id} className={`curso-row${selected ? " curso-row-selected" : ""}${hidden ? " d-none" : ""}`} tabIndex={0} role="button"
                            aria-label={`Seleccionar curso ${c.nombre} para filtrar comisiones`} aria-pressed={live ? selected : undefined}
                            onClick={() => lockRow(c)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ") { e.preventDefault(); lockRow(c); }
                              if (e.key === "Escape") release();
                            }}>
                            <td>{c.plan || "-"}</td>
                            <td>{c.nombre}</td>
                            <td>{c.comisiones}</td>
                            <td>
                              {c.comisiones
                                ? <span className="sisoc-data-badge sisoc-data-badge--commission">Creado con comisión</span>
                                : <span className="sisoc-data-badge sisoc-data-badge--no-commission">Creado sin comisión</span>}
                            </td>
                            <Actions>
                              {c.urls.detalle && <a href={c.urls.detalle} className="sisoc-btn sisoc-btn--view"><i className="fas fa-eye" />{" "}<span>Ver</span></a>}
                              {c.urls.comision_nueva && <a href={c.urls.comision_nueva} className="sisoc-btn sisoc-btn--add"><i className="fas fa-plus" />{" "}<span>Comisión</span></a>}
                              {c.edicion && <EditButton className="btn-editar-curso" onClick={() => setModal({ kind: "curso", edicion: c.edicion })} />}
                              {c.urls.eliminar && <a href={c.urls.eliminar} className="sisoc-btn sisoc-btn--delete"><i className="fas fa-trash" />{" "}<span>Borrar</span></a>}
                            </Actions>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
              <div id="cursosTableEmptyState" className={`sisoc-empty-state${!live || cursosView!.visible.length > 0 ? " d-none" : ""}`}>
                No hay cursos que coincidan con los filtros seleccionados.
              </div>
              <div className="sisoc-table-footer">
                <span id="cursosFilterSummary">{cursosSummary}</span>
                <div id="cursosPagination" className="sisoc-page-buttons" aria-label="Paginación de cursos">
                  {cursosView && Array.from({ length: cursosView.pages }, (_, i) => i + 1).map((n) => (
                    <button key={n} type="button" className={n === cursosView.page ? "is-active" : undefined} aria-current={n === cursosView.page ? "page" : undefined} onClick={() => setCPage(n)}>{n}</button>
                  ))}
                </div>
              </div>
            </>
          ) : <div className="sisoc-empty-state">Sin cursos registrados para este centro.</div>}
        </div>
      </section>
      <section>
        <div className="sisoc-section-header-bar">Comisiones</div>
        <div className="sisoc-section-card">
          <div className="sisoc-toolbar">
            <div className="sisoc-toolbar-left">
              <label className="sisoc-toolbar-field" htmlFor="comisionesFilterSearch">
                <i className="fas fa-search" />{" "}
                <input type="search" id="comisionesFilterSearch" placeholder="Buscar Comisión..." autoComplete="off" value={mSearch}
                  onChange={(e) => { setMSearch(e.target.value); setMPage(1); }} />
              </label>
              <label className="sisoc-toolbar-field" htmlFor="comisionesFilterCurso">
                <Select2 id="comisionesFilterCurso" name="comisionesFilterCurso" value={[mCurso]}
                  onChange={(v) => { const id = v[0] ?? ""; setMCurso(id); setLocked(id ? { id, nombre: cursoNombre(id) } : null); setMPage(1); }}
                  choices={[{ value: "", label: "Filtrar por Curso" }, ...cursos.map((c) => ({ value: String(c.id), label: c.nombre }))]}
                  placeholder="Filtrar por Curso" selectClassName="select2" selectProps={{ "data-width": "100%" }}
                  hideEmptyChoice noResults="No results found" clearTrigger="mousedown" focusMarker="container" termHandling="reset" enterOnSelected="toggle" outsideClick="dropdown" />
              </label>
              <select id="comisionesFilterEstado" className="sisoc-hidden-control" value={mEstado} onChange={(e) => { setMEstado(e.target.value); setMPage(1); }}>
                <option value="">Todos</option>
                <option value="activa">Activa</option>
                <option value="planificada">Planificada</option>
                <option value="cerrada">Cerrada</option>
              </select>
              <select id="comisionesFilterPageSize" className="sisoc-hidden-control" value={mSize} onChange={(e) => { setMSize(e.target.value); setMPage(1); }}>
                {PAGE_SIZES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
              <button type="button" id="comisionesFilterClear" className="sisoc-hidden-control"
                onClick={() => { setMSearch(""); setMEstado(""); setMSize("5"); release(); }}>Limpiar</button>
            </div>
          </div>
          <div id="comisionesCursoHint" className="sisoc-panel-note">{hint}</div>
          {comisiones.length > 0 ? (
            <>
              <div className="sisoc-table-shell">
                <div className="sisoc-table-wrap">
                  <table className="sisoc-table" id="tablaComisionesCursoCentro">
                    <thead><tr><th>Curso</th><th>Comisión</th><th>Ubicación</th><th>Fecha Inicio</th><th>Fecha Fin</th><th>Cupo</th><th>Acciones</th></tr></thead>
                    <tbody>
                      {comisiones.map((c) => (
                        <tr key={c.id} className={`comision-curso-row${live && !comisionesShown.has(c.id) ? " d-none" : ""}`}>
                          <td>{c.curso_nombre}</td>
                          <td>{c.codigo_o_nombre}</td>
                          <td>{c.ubicacion || "-"}</td>
                          <td>{c.fecha_inicio}</td>
                          <td>{c.fecha_fin}</td>
                          <td>{c.cupo}</td>
                          <Actions>
                            {c.urls.detalle && <a href={c.urls.detalle} className="sisoc-btn sisoc-btn--view"><i className="fas fa-eye" />{" "}<span>Ver</span></a>}
                            {c.edicion && <EditButton className="btn-editar-comision-curso" onClick={() => setModal({ kind: "comision", edicion: c.edicion as ComisionEdicion })} />}
                            {c.urls.eliminar && <a href={c.urls.eliminar} className="sisoc-btn sisoc-btn--delete"><i className="fas fa-trash" />{" "}<span>Borrar</span></a>}
                          </Actions>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <div id="comisionesCursoEmptyState" className={`sisoc-empty-state${!live || comisionesView!.visible.length > 0 ? " d-none" : ""}`}>
                No hay comisiones que coincidan con los filtros seleccionados.
              </div>
              <div className="sisoc-table-footer">
                <span id="comisionesFilterSummary">{comisionesSummary}</span>
                <div id="comisionesPagination" className="sisoc-page-buttons" aria-label="Paginación de comisiones">
                  {comisionesView && Array.from({ length: comisionesView.pages }, (_, i) => i + 1).map((n) => (
                    <button key={n} type="button" className={n === comisionesView.page ? "is-active" : undefined} aria-current={n === comisionesView.page ? "page" : undefined} onClick={() => setMPage(n)}>{n}</button>
                  ))}
                </div>
              </div>
            </>
          ) : <div className="sisoc-empty-state">No hay comisiones de curso para este centro.</div>}
        </div>
      </section>
      {modales && modal?.kind === "curso" && (
        <CursoModal key={modal.edicion?.guardar ?? "nuevo"} fields={modales.curso.fields} planes={modales.curso.planes} edicion={modal.edicion}
          endpoint={apiPath(modal.edicion?.guardar ?? modales.curso.crear)} close={() => setModal(null)} onSaved={reload} />
      )}
      {modales && modal?.kind === "comision" && (
        <ComisionCursoModal key={modal.edicion.guardar} fields={modales.comision_curso.fields} edicion={{ ...modal.edicion, guardar: apiPath(modal.edicion.guardar) }}
          close={() => setModal(null)} onSaved={reload} />
      )}
    </div>
  );
}

/** `#centroCursosPanelContainer`: the loading card, the panel, or the error card with its retry button. */
export function CursosPanelContainer({ endpoint }: { endpoint: string }) {
  const [state, setState] = useState<{ kind: "loading" } | { kind: "error" } | { kind: "ready"; data: PanelData }>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let alive = true;
    webClient.get(endpoint).then(
      ({ data }) => { if (alive) setState(panelValid(data) ? { kind: "ready", data } : { kind: "error" }); },
      () => { if (alive) setState({ kind: "error" }); },
    );
    return () => { alive = false; };
  }, [endpoint, attempt]);
  const retry = () => { setState({ kind: "loading" }); setAttempt((n) => n + 1); };
  return (
    <div className="sisoc-cursos-pane" id="cursos">
      <div id="centroCursosPanelContainer" data-panel-loaded={state.kind === "ready" ? "1" : "0"}>
        {state.kind === "ready" && <CursosPanel data={state.data} reload={retry} />}
        {state.kind === "loading" && (
          <div className="sisoc-section-card"><div className="sisoc-empty-state">
            <div className="spinner-border spinner-border-sm text-light mb-3" role="status" aria-hidden="true" />
            <p className="mb-0">Cargando oferta educativa y comisiones...</p>
          </div></div>
        )}
        {state.kind === "error" && (
          <div className="sisoc-section-card"><div className="sisoc-empty-state">
            <i className="fas fa-exclamation-triangle text-warning fa-2x mb-3" />
            <p className="mb-3">No se pudo cargar la sección de cursos.</p>
            <button type="button" className="sisoc-btn sisoc-btn--ghost" data-retry-cursos-panel="1" onClick={retry}>Reintentar</button>
          </div></div>
        )}
      </div>
    </div>
  );
}
