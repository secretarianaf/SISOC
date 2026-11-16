/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { internal, postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts } from "./nativeParity";
import { goTo, LoteModal, ProfesorModal, RapidaModal, type Profesor } from "./vatComisionDetalleAcciones";
import { ResultadosPanel } from "./vatComisionDetalleResultados";
import { COMISION_DETALLE_CSS } from "./vatComisionDetalleStyles";
import { CsrfInput, fieldValid, UNCERTAIN, useForbidden, type Field } from "./vatFormShared";
import { bool, integer, messagesValid, type Message } from "./vatShared";
import type { RouteDefinition } from "./types";

/**
 * V04.01 detalle de comisión: `vat/oferta_institucional/comision_detail.html`, shared by the offer and the course
 * commissions. Data comes from `/api/web/vat/comisiones-detalle/[cursos/]<id>/`, which runs the native detail view
 * (scope, permissions, tables and messages are the native ones). The tabs, the search and the local pagination are the
 * page's own JavaScript. The actions of the page (accept/reject one or a batch, quick enrolment, results of the acta) POST to
 * the U3 endpoints and to `.../cursos/<id>/{resultados,profesores}/`; the ones whose API is not part of this screen
 * (delete the commission, add/edit/delete a schedule, delete an enrolment) are plain links to the URL of their screen: the
 * schedule forms (U5, `vatComisionHorarioForm.tsx`) and the enrolment delete (U3) are React routes under those same URLs.
 */
type Estado = { id: number; apellido: string; nombre: string; documento: string; estado: string; estado_label: string; detail_url: string };
export type Inscripto = Estado & {
  busqueda: string; tipo_alumno: string; es_alumno_vat: boolean; email: string; telefono: string; asistencia: string | null; delete_url: string;
};
export type EnEspera = Estado & { fecha: string };
export type Sesion = { id: number; numero: number; dia: string; fecha: string; desde: string; hasta: string; estado: string; presentes: string; ausentes: string; asistencia_url: string };
export type Horario = {
  id: number; dia: string; dia_semana_id: number; desde: string; hasta: string; duracion: string; aula_espacio: string; vigente: boolean; update_url: string; delete_url: string;
};
export type Resultados = {
  aprobado: string; desaprobado: string; resumen: Record<"aprobados" | "desaprobados" | "sin_calificar" | "inscriptos", string>;
  alumnos: { id: number; apellido: string; nombre: string; documento: string; resultado: string }[];
  profesor_id: number | null; profesor_texto: string; fecha_fin: string; numero_acta: string;
};
const PERMISOS = [
  "gestionar_comision", "editar_comision", "eliminar_comision", "agregar_inscripcion", "cambiar_inscripcion", "eliminar_inscripcion", "gestionar_asistencia",
  "agregar_comision_horario", "editar_comision_horario", "eliminar_comision_horario", "gestionar_lote_inscriptos", "gestionar_resultados",
] as const;
export type ComisionDetalleData = {
  tipo: "curso" | "oferta"; id: number; codigo: string; nombre: string; titulo_tipo: string; subtitulo: string; estado_label: string; acepta_lista_espera: boolean;
  ubicacion: string; fecha_inicio: string; fecha_fin: string; cupo: string; cupo_lista_espera: string; cupo_ocupado: string; clases_dictadas: string; clases_pendientes: string;
  metricas: { valor: string; label: string }[]; horarios: Horario[]; sesiones: Sesion[]; inscripciones: Inscripto[]; lista_espera: EnEspera[];
  permisos: Record<(typeof PERMISOS)[number], boolean>;
  urls: { eliminar: string; exportar_preinscriptos: string | null; exportar_inscriptos: string | null; horario_nuevo: string };
  resultados: Resultados | null; formularios: { rapida: Field[] | null; profesor: Field[] | null }; messages: Message[];
};

const strings = (v: Record<string, unknown>, keys: string[]) => keys.every((k) => text(v[k]));
const list = (v: unknown, valid: (row: Record<string, unknown>) => boolean) => Array.isArray(v) && v.every((row) => record(row) && valid(row));
const baseValid = (r: Record<string, unknown>) => integer(r.id) && strings(r, ["apellido", "nombre", "documento", "estado", "estado_label"]) && internal(r.detail_url);
const inscriptoValid = (r: Record<string, unknown>) => baseValid(r) && strings(r, ["busqueda", "tipo_alumno", "email", "telefono"]) && bool(r.es_alumno_vat) &&
  (r.asistencia === null || text(r.asistencia)) && internal(r.delete_url);
const esperaValid = (r: Record<string, unknown>) => baseValid(r) && text(r.fecha);
const sesionValid = (r: Record<string, unknown>) => integer(r.id) && integer(r.numero) && strings(r, ["dia", "fecha", "desde", "hasta", "estado", "presentes", "ausentes"]) && internal(r.asistencia_url);
const horarioValid = (r: Record<string, unknown>) => integer(r.id) && integer(r.dia_semana_id) && strings(r, ["dia", "desde", "hasta", "duracion", "aula_espacio"]) && bool(r.vigente) &&
  internal(r.update_url) && internal(r.delete_url);
const resultadosValid = (v: unknown) => v === null || (record(v) && strings(v, ["aprobado", "desaprobado", "profesor_texto", "fecha_fin", "numero_acta"]) && (v.profesor_id === null || integer(v.profesor_id)) &&
  record(v.resumen) && ["aprobados", "desaprobados", "sin_calificar", "inscriptos"].every((k) => text((v.resumen as Record<string, unknown>)[k])) &&
  list(v.alumnos, (a) => integer(a.id) && strings(a, ["apellido", "nombre", "documento", "resultado"])));

export const comisionDetalleValid = (v: unknown): v is ComisionDetalleData => record(v) && (v.tipo === "curso" || v.tipo === "oferta") && integer(v.id) &&
  strings(v, ["codigo", "nombre", "titulo_tipo", "subtitulo", "estado_label", "ubicacion", "fecha_inicio", "fecha_fin", "cupo", "cupo_lista_espera", "cupo_ocupado", "clases_dictadas", "clases_pendientes"]) &&
  bool(v.acepta_lista_espera) && list(v.metricas, (m) => strings(m, ["valor", "label"])) && list(v.horarios, horarioValid) && list(v.sesiones, sesionValid) &&
  list(v.inscripciones, inscriptoValid) && list(v.lista_espera, esperaValid) && record(v.permisos) && PERMISOS.every((k) => bool((v.permisos as Record<string, unknown>)[k])) &&
  record(v.urls) && internal(v.urls.eliminar) && internal(v.urls.horario_nuevo) && [v.urls.exportar_preinscriptos, v.urls.exportar_inscriptos].every((u) => u === null || internal(u)) &&
  resultadosValid(v.resultados) && record(v.formularios) && [v.formularios.rapida, v.formularios.profesor].every((f) => f === null || (Array.isArray(f) && f.every(fieldValid))) &&
  messagesValid(v.messages);

const PAGE_SIZE = 10;
type Panel = "general" | "inscriptos" | "espera" | "sesiones" | "horarios" | "resultados";

/** `panelDesdeHash()` of the native page: the hash returns to a tab after a POST with redirect. */
const panelFromHash = (order: Panel[]): Panel => {
  const hash = window.location.hash.replace("#", "") as Panel;
  return order.includes(hash) ? hash : "general";
};

/** Pager state of the native `render()` functions: the page is clamped to the existing ones. */
function usePager(total: number) {
  const [page, setPage] = useState(1);
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const current = Math.min(Math.max(page, 1), pages);
  const start = (current - 1) * PAGE_SIZE;
  const end = start + PAGE_SIZE;
  return { current, pages, start, end, setPage, shown: (index: number) => index >= start && index < end };
}

function Foot({ id, total, pager }: { id: string; total: number; pager: ReturnType<typeof usePager> }) {
  return <div className="ci-tbl-foot">
    <span id={`${id}Conteo`}>Mostrando {total === 0 ? 0 : pager.start + 1}-{Math.min(pager.end, total)} de {total}</span>
    <div className="ci-pager">
      <button type="button" className="ci-pager-prev" id={`${id}Prev`} aria-label="Página anterior" disabled={pager.current <= 1} onClick={() => pager.setPage(pager.current - 1)}><i className="bi bi-chevron-left" /></button>
      <span className="ci-pager-label" id={`${id}Pager`}>{pager.current} de {pager.pages}</span>
      <button type="button" className="ci-pager-next" id={`${id}Next`} aria-label="Página siguiente" disabled={pager.current >= pager.pages} onClick={() => pager.setPage(pager.current + 1)}><i className="bi bi-chevron-right" /></button>
    </div>
  </div>;
}

const PILL: Record<string, string> = { inscripta: "ci-pill-green", validada_presencial: "ci-pill-green", pre_inscripta: "ci-pill-yellow", completada: "ci-pill-blue", rechazada: "ci-pill-red" };
const SESION: Record<string, [string, string, string]> = {
  realizada: ["ci-pill-green", "bi-check-circle-fill", "Completada"], cancelada: ["ci-pill-red", "bi-x-circle-fill", "Cancelada"],
};

function Metric({ value, label }: { value: ReactNode; label: string }) {
  return <article className="sisoc-metric-card"><strong className="sisoc-metric-value">{value}</strong><span className="sisoc-metric-label">{label}</span></article>;
}

function Section({ panel, active, className = "", children }: { panel: Panel; active: Panel; className?: string; children: ReactNode }) {
  return <section className={`sisoc-info-panel${className ? ` ${className}` : ""}${active === panel ? " is-active" : ""}`} data-sisoc-panel={panel}>{children}</section>;
}

const A = "web/vat/inscripciones-persona/";
type Modal = { kind: "rapida" } | { kind: "lote"; estado: string; resumen: string; detalle: string } | { kind: "profesor" } | null;
type Scope = { data: ComisionDetalleData; active: Panel; forbidden: (d: unknown) => void; setModal: (m: Modal) => void };

/** Posts the batch/state change and follows the native redirect (a full reload that shows the queued message). */
function useAccion(forbidden: (d: unknown) => void) {
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  async function enviar(endpoint: string, body: URLSearchParams) {
    if (busy.current || uncertain) return;
    busy.current = true;
    const result = await postForm(endpoint, body);
    busy.current = false;
    if (result.kind === "redirect") goTo(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else setUncertain(true);
  }
  return { uncertain, enviar };
}

const LOTE_ETIQUETAS: Record<string, string> = { inscripta: "aceptar", rechazada: "rechazar" };

function InscriptosPanel({ data, active, setModal, selection }: Scope & { selection: ReturnType<typeof useSelection> }) {
  const { permisos: p, urls, inscripciones } = data;
  const [term, setTerm] = useState("");
  const { checked, setChecked } = selection;
  const all = useRef<HTMLInputElement>(null);
  const needle = term.trim().toLowerCase();
  const filtered = needle ? inscripciones.filter((i) => i.busqueda.includes(needle)) : inscripciones;
  const pager = usePager(filtered.length);
  const visible = new Set(filtered.filter((_, index) => pager.shown(index)).map((i) => i.id));
  const acciones = p.cambiar_inscripcion || p.eliminar_inscripcion;
  const lote = p.gestionar_lote_inscriptos;
  const colspan = lote ? 10 : acciones ? 9 : 8;
  const marcados = filtered.filter((i) => checked.has(i.id)).length;
  const total = checked.size;
  useEffect(() => {
    if (all.current) all.current.indeterminate = marcados > 0 && marcados < filtered.length;
  });
  // «Seleccionar todos» applies to the rows that pass the filter, not to the page and not to every row of the commission.
  function toggleAll(on: boolean) {
    setChecked((current) => {
      const next = new Set(current);
      for (const i of filtered) { if (on) next.add(i.id); else next.delete(i.id); }
      return next;
    });
  }
  function toggle(id: number, on: boolean) {
    setChecked((current) => {
      const next = new Set(current);
      if (on) next.add(id); else next.delete(id);
      return next;
    });
  }
  function abrir(estado: string) {
    const elegidos = inscripciones.filter((i) => checked.has(i.id));
    if (!elegidos.length) return;
    const cambian = elegidos.filter((i) => i.estado !== estado).length;
    const sinCambios = elegidos.length - cambian;
    setModal({
      kind: "lote", estado,
      resumen: `¿Confirmás ${LOTE_ETIQUETAS[estado]} ${elegidos.length}${elegidos.length === 1 ? " inscripción" : " inscripciones"}?`,
      detalle: sinCambios ? `${cambian} cambian de estado; ${sinCambios} ya estaban en ese estado y no se modifican.` : "",
    });
  }
  return <Section panel="inscriptos" active={active} className="sisoc-info-panel--overflow">
    <div className="sisoc-metric-grid sisoc-metric-grid--pair">
      <Metric value={data.cupo} label="Cupo total" />
      <Metric value={inscripciones.length} label="Inscriptos" />
    </div>
    <div className="ci-tbl-card" id="inscriptosTabla">
      <div className="ci-tbl-head"><i className="bi bi-people" /><span>Inscriptos</span></div>
      {lote && <form id="formInscriptosLote" method="post"><CsrfInput /><input type="hidden" name="estado" id="inscriptosLoteEstado" /></form>}
      <div className="ci-tbl-toolbar">
        <div className="ci-tbl-search">
          <i className="bi bi-search" />
          <input type="text" id="inscriptosBuscador" placeholder="Buscar por nombre..." autoComplete="off" aria-label="Buscar inscriptos por nombre" value={term}
            onChange={(e) => { setTerm(e.target.value); setChecked(new Set()); pager.setPage(1); }} />
        </div>
        {lote && <div className="ci-lote-acciones">
          <span className="ci-lote-conteo" id="inscriptosLoteConteo">{total} {total === 1 ? "seleccionado" : "seleccionados"}</span>
          <button type="button" className="sisoc-btn sisoc-btn--add" id="inscriptosLoteAceptar" data-lote-estado="inscripta" disabled={total === 0} onClick={() => abrir("inscripta")}><i className="bi bi-check-lg" /><span>Aceptar</span></button>
          <button type="button" className="sisoc-btn sisoc-btn--delete" id="inscriptosLoteRechazar" data-lote-estado="rechazada" disabled={total === 0} onClick={() => abrir("rechazada")}><i className="bi bi-x-lg" /><span>Rechazar</span></button>
        </div>}
        {p.agregar_inscripcion && <button type="button" className="sisoc-btn sisoc-btn--add" onClick={() => setModal({ kind: "rapida" })}><i className="bi bi-plus-lg" /><span>Agregar inscripto</span></button>}
        {urls.exportar_preinscriptos && <a href={urls.exportar_preinscriptos} className="sisoc-btn sisoc-btn--ghost"><i className="bi bi-file-earmark-excel" /><span>Descargar preinscriptos</span></a>}
        {urls.exportar_inscriptos && <a href={urls.exportar_inscriptos} className="sisoc-btn sisoc-btn--ghost"><i className="bi bi-file-earmark-excel" /><span>Descargar inscriptos</span></a>}
      </div>
      {selection.uncertain && <p role="alert">{UNCERTAIN}</p>}
      <div className="ci-tbl-scroll">
        <table className="ci-tbl">
          <thead><tr>
            {lote && <th className="ci-tbl-col-check"><input ref={all} type="checkbox" id="inscriptosLoteTodos" aria-label="Seleccionar todos los inscriptos"
              checked={filtered.length > 0 && marcados === filtered.length} onChange={(e) => toggleAll(e.target.checked)} /></th>}
            <th>Apellido</th><th>Nombre</th><th>Documento</th><th>Tipo de alumno</th><th>Estado</th><th>Email</th><th>Teléfono</th><th>Asistencia</th>
            {acciones && <th className="ci-tbl-col-actions">&nbsp;</th>}
          </tr></thead>
          <tbody id="inscriptosTablaBody">
            {inscripciones.map((i) => (
              <tr key={i.id} className={`ci-tbl-row${visible.has(i.id) ? "" : " d-none"}`} data-nombre={i.busqueda} data-estado={i.estado}>
                {lote && <td className="ci-tbl-col-check"><input type="checkbox" className="ci-lote-check" value={i.id} aria-label={`Seleccionar a ${i.apellido} ${i.nombre}`}
                  checked={checked.has(i.id)} onChange={(e) => toggle(i.id, e.target.checked)} /></td>}
                <td><a href={i.detail_url}>{i.apellido}</a></td>
                <td>{i.nombre}</td>
                <td>{i.documento}</td>
                <td><span className={`ci-pill ${i.es_alumno_vat ? "ci-pill-teal" : "ci-pill-gray"}`}>{i.tipo_alumno}</span></td>
                <td><span className={`ci-pill ${PILL[i.estado] ?? "ci-pill-gray"}`}>{i.estado_label}</span></td>
                <td>{i.email}</td>
                <td>{i.telefono}</td>
                <td>{i.asistencia === null ? "—" : `${i.asistencia}%`}</td>
                {acciones && <td><div className="ci-tbl-actions">
                  {p.eliminar_inscripcion && <a href={i.delete_url} className="sisoc-btn sisoc-btn--delete"><i className="bi bi-trash" /><span>Borrar</span></a>}
                </div></td>}
              </tr>
            ))}
            {inscripciones.length === 0 && <tr className="ci-tbl-empty" data-empty-row><td colSpan={colspan}>Sin inscriptos aún. Inscribí ciudadanos a esta comisión para verlos aquí.</td></tr>}
            <tr className={`ci-tbl-empty${filtered.length === 0 && inscripciones.length > 0 ? "" : " d-none"}`} data-no-results-row><td colSpan={colspan}>No se encontraron inscriptos para la búsqueda.</td></tr>
          </tbody>
        </table>
      </div>
      <Foot id="inscriptos" total={filtered.length} pager={pager} />
    </div>
  </Section>;
}

/** The batch selection lives in the page so the confirmation modal (rendered at the end, like the native one) can read it. */
function useSelection(data: ComisionDetalleData, forbidden: (d: unknown) => void) {
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const { uncertain, enviar } = useAccion(forbidden);
  const confirmar = (estado: string) => {
    const body = new URLSearchParams({ estado });
    for (const id of checked) body.append("inscripciones", String(id));
    return enviar(`${A}cursos/comisiones/${data.id}/cambiar-estado-lote/`, body);
  };
  return { checked, setChecked, uncertain, confirmar };
}

function EsperaPanel({ data, active, forbidden }: Scope) {
  const rows = data.lista_espera;
  const pager = usePager(rows.length);
  const { uncertain, enviar } = useAccion(forbidden);
  const cambiar = data.permisos.cambiar_inscripcion;
  const endpoint = (id: number) => `${A}${data.tipo === "curso" ? "cursos/" : ""}${id}/cambiar-estado/`;
  const form = (id: number, estado: string, klass: string, title: string, icon: string, label: string) => (
    <form method="post" className="d-inline" onSubmit={(e) => { e.preventDefault(); void enviar(endpoint(id), new URLSearchParams({ estado })); }}>
      <CsrfInput />
      <input type="hidden" name="estado" value={estado} />
      <button type="submit" className={`sisoc-btn ${klass}`} title={title}><i className={`bi ${icon}`} /><span>{label}</span></button>
    </form>
  );
  return <Section panel="espera" active={active} className="sisoc-info-panel--overflow">
    <div className="sisoc-metric-grid sisoc-metric-grid--pair">
      <Metric value={data.cupo_lista_espera} label="Cupo de espera" />
      <Metric value={rows.length} label="En espera" />
    </div>
    <div className="ci-tbl-card" id="esperaTabla">
      <div className="ci-tbl-head"><i className="bi bi-hourglass-split" /><span>Lista de espera</span></div>
      {uncertain && <p role="alert">{UNCERTAIN}</p>}
      <div className="ci-tbl-scroll">
        <table className="ci-tbl">
          <thead><tr>
            <th>Apellido</th><th>Nombre</th><th>Documento</th><th>Fecha</th><th>Estado</th>
            {cambiar && <th className="ci-tbl-col-actions">Acciones</th>}
          </tr></thead>
          <tbody id="esperaTablaBody">
            {rows.map((i, index) => (
              <tr key={i.id} className={`ci-tbl-row${pager.shown(index) ? "" : " d-none"}`}>
                <td><a href={i.detail_url}>{i.apellido}</a></td>
                <td>{i.nombre}</td>
                <td>{i.documento}</td>
                <td>{i.fecha}</td>
                <td><span className="ci-pill ci-pill-yellow">{i.estado_label}</span></td>
                {cambiar && <td><div className="ci-tbl-actions">
                  {form(i.id, "inscripta", "sisoc-btn--add", "Admitir desde la lista de espera", "bi-check-lg", "Admitir")}
                  {form(i.id, "rechazada", "sisoc-btn--delete", "Rechazar inscripción en espera", "bi-x-lg", "Rechazar")}
                </div></td>}
              </tr>
            ))}
            {rows.length === 0 && <tr className="ci-tbl-empty"><td colSpan={cambiar ? 6 : 5}>Sin personas en espera. Cuando la comisión esté llena, las nuevas altas quedarán listadas aquí.</td></tr>}
          </tbody>
        </table>
      </div>
      <Foot id="espera" total={rows.length} pager={pager} />
    </div>
  </Section>;
}

function SesionesPanel({ data, active }: { data: ComisionDetalleData; active: Panel }) {
  const rows = data.sesiones;
  const pager = usePager(rows.length);
  const gestionar = data.permisos.gestionar_asistencia;
  return <Section panel="sesiones" active={active}>
    <div className="sisoc-metric-grid sisoc-metric-grid--triple">
      <Metric value={rows.length} label="Clases totales" />
      <Metric value={data.clases_dictadas} label="Clases completadas" />
      <Metric value={data.clases_pendientes} label="Clases pendientes" />
    </div>
    <div className="ci-tbl-card" id="sesionesTabla">
      <div className="ci-tbl-head"><i className="bi bi-calendar3" /><span>Clases</span></div>
      <div className="ci-tbl-scroll">
        <table className="ci-tbl">
          <thead><tr>
            <th>Clase N</th><th>Día</th><th>Fecha</th><th>Desde</th><th>Hasta</th><th>Estado</th><th>Presentes</th><th>Ausentes</th>
            {gestionar && <th className="ci-tbl-col-actions">Acciones</th>}
          </tr></thead>
          <tbody id="sesionesTablaBody">
            {rows.map((s, index) => {
              const [klass, icon, label] = SESION[s.estado] ?? ["ci-pill-gray", "bi-circle", "Pendiente"];
              return <tr key={s.id} className={`ci-tbl-row${pager.shown(index) ? "" : " d-none"}`}>
                <td>Clase {s.numero}</td>
                <td>{s.dia}</td>
                <td>{s.fecha}</td>
                <td>{s.desde} hs</td>
                <td>{s.hasta} hs</td>
                <td><span className={`ci-pill ${klass}`}><i className={`bi ${icon} me-1`} />{label}</span></td>
                <td>{s.estado === "realizada" ? s.presentes : "—"}</td>
                <td>{s.estado === "realizada" ? s.ausentes : "—"}</td>
                {gestionar && <td><div className="ci-tbl-actions">
                  {s.estado === "realizada"
                    ? <a href={s.asistencia_url} className="sisoc-btn sisoc-btn--edit"><i className="bi bi-eye" /><span>Ver</span></a>
                    : <a href={s.asistencia_url} className="sisoc-btn sisoc-btn--view"><i className="bi bi-pencil-square" /><span>Asistencia</span></a>}
                </div></td>}
              </tr>;
            })}
            {rows.length === 0 && <tr className="ci-tbl-empty"><td colSpan={gestionar ? 9 : 8}>Sin clases generadas. Agregá un horario para generar las clases automáticamente.</td></tr>}
          </tbody>
        </table>
      </div>
      <Foot id="sesiones" total={rows.length} pager={pager} />
    </div>
  </Section>;
}

function HorariosPanel({ data, active }: { data: ComisionDetalleData; active: Panel }) {
  const rows = data.horarios;
  const { permisos: p } = data;
  const pager = usePager(rows.length);
  const acciones = p.editar_comision_horario || p.eliminar_comision_horario;
  return <Section panel="horarios" active={active}>
    <div className="ci-tbl-card" id="horariosTabla">
      <div className="ci-tbl-head"><i className="bi bi-clock-history" /><span>Horarios</span></div>
      {p.agregar_comision_horario && <div className="ci-tbl-toolbar">
        <span />
        <a href={data.urls.horario_nuevo} className="sisoc-btn sisoc-btn--add"><i className="bi bi-plus-lg" /><span>Agregar</span></a>
      </div>}
      <div className="ci-tbl-scroll">
        <table className="ci-tbl">
          <thead><tr>
            <th>Día</th><th>Desde</th><th>Hasta</th><th>Aula / Espacio</th><th>Estado</th>
            {acciones && <th className="ci-tbl-col-actions">Acciones</th>}
          </tr></thead>
          <tbody id="horariosTablaBody">
            {rows.map((h, index) => (
              <tr key={h.id} className={`ci-tbl-row${pager.shown(index) ? "" : " d-none"}`}>
                <td>{h.dia}</td>
                <td>{h.desde} hs</td>
                <td>{h.hasta} hs</td>
                <td>{h.aula_espacio || "—"}</td>
                <td><span className={`ci-pill ${h.vigente ? "ci-pill-green" : "ci-pill-gray"}`}>{h.vigente ? "Vigente" : "Inactivo"}</span></td>
                {acciones && <td><div className="ci-tbl-actions">
                  {p.editar_comision_horario && <a href={h.update_url} className="sisoc-btn sisoc-btn--edit" title="Editar horario" aria-label={`Editar horario ${h.dia} ${h.desde} a ${h.hasta}`}><i className="bi bi-pencil-square" /><span>Editar</span></a>}
                  {p.eliminar_comision_horario && <a href={h.delete_url} className="sisoc-btn sisoc-btn--delete" title="Eliminar horario" aria-label={`Eliminar horario ${h.dia} ${h.desde} a ${h.hasta}`}><i className="bi bi-trash" /><span>Borrar</span></a>}
                </div></td>}
              </tr>
            ))}
            {rows.length === 0 && <tr className="ci-tbl-empty"><td colSpan={acciones ? 6 : 5}>Sin horarios cargados. Agregá un horario para esta comisión.</td></tr>}
          </tbody>
        </table>
      </div>
      <Foot id="horarios" total={rows.length} pager={pager} />
    </div>
  </Section>;
}

function GeneralPanel({ data, active }: { data: ComisionDetalleData; active: Panel }) {
  const item = (label: string, value: string) => <div className="sisoc-data-item"><p className="sisoc-data-label">{label}</p><p className="sisoc-data-value">{value}</p></div>;
  return <Section panel="general" active={active}>
    <div className="sisoc-panel-section">
      <div className="sisoc-block-card">
        <div className="sisoc-block-title"><i className="bi bi-info-circle" /><span>Datos generales</span></div>
        <div className="sisoc-block-body"><div className="sisoc-general-layout"><div className="sisoc-general-grid">
          {item("Ubicación", data.ubicacion)}
          {item("Fecha de inicio", data.fecha_inicio)}
          {item("Fecha de finalización", data.fecha_fin)}
          {item("Cupo", data.cupo)}
          {item("Inscriptos", data.cupo_ocupado)}
        </div></div></div>
      </div>
      <div className="sisoc-block-card">
        <div className="sisoc-block-title"><i className="bi bi-clock-history" /><span>Horarios</span></div>
        <div className="sisoc-block-body">
          {data.horarios.length ? <div className="sisoc-horarios-grid">
            {data.horarios.map((h) => <Fragment key={h.id}>
              {item(h.dia, `${h.desde} a ${h.hasta}`)}
              {item("Duración", h.duracion)}
            </Fragment>)}
          </div> : <div className="ci-empty">
            <i className="bi bi-clock-history" />
            <p className="ci-empty-t">Sin horarios cargados</p>
            <p className="ci-empty-s">Agregá un horario para esta comisión.</p>
          </div>}
        </div>
      </div>
    </div>
  </Section>;
}

export function ComisionDetalleContent({ data, forbidden = () => undefined }: { data: ComisionDetalleData; forbidden?: (d: unknown) => void }) {
  const espera = data.acepta_lista_espera || data.lista_espera.length > 0;
  const order: Panel[] = ["general", "inscriptos", ...(espera ? ["espera" as const] : []), "sesiones", "horarios", ...(data.permisos.gestionar_resultados ? ["resultados" as const] : [])];
  const [active, setActive] = useState<Panel>(() => panelFromHash(order));
  const [modal, setModal] = useState<Modal>(null);
  const [profesor, setProfesor] = useState<Profesor | null>(() => (data.resultados?.profesor_id == null ? null : { id: data.resultados.profesor_id, text: data.resultados.profesor_texto }));
  const selection = useSelection(data, forbidden);
  useEffect(() => {
    const onHash = () => setActive(panelFromHash(order));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  });
  const counts: Record<Panel, number> = {
    general: 0, inscriptos: data.inscripciones.length, espera: data.lista_espera.length, sesiones: data.sesiones.length, horarios: data.horarios.length, resultados: data.resultados?.alumnos.length ?? 0,
  };
  const labels: Record<Panel, string> = { general: "Información", inscriptos: "Inscriptos", espera: "Lista de espera", sesiones: "Sesiones", horarios: "Horarios", resultados: "Resultados" };
  const rail: Record<Panel, string> = { ...labels, sesiones: "Clases" };
  const side = (panel: Panel, hidden: boolean) => <button key={panel} type="button" className={`sisoc-side-tab${active === panel ? " is-active" : ""}`} data-sisoc-tab-target={panel}
    aria-selected={active === panel} hidden={hidden} onClick={() => setActive(panel)}>
    <span>{labels[panel]}{counts[panel] ? ` (${counts[panel]})` : ""}</span>
  </button>;
  const hideGlobalMetrics = ["inscriptos", "sesiones", "espera", "resultados"].includes(active);
  const canDelete = data.permisos.eliminar_comision;
  const curso = data.tipo === "curso";
  const scope = { data, active, forbidden, setModal };
  const detail = `web/vat/comisiones-detalle/cursos/${data.id}/`;
  return <>
    <NativeToasts messages={data.messages} />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
    <link href="https://fonts.googleapis.com/css2?family=Lora:wght@600;700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <style>{COMISION_DETALLE_CSS}</style>
    <div className="sisoc-centro-page">
      <div className="sisoc-page-top">
        <div className="sisoc-header-actions">
          {canDelete && <a href={data.urls.eliminar} className="sisoc-btn sisoc-btn--delete"><i className="bi bi-trash" /><span>Eliminar</span></a>}
        </div>
      </div>
      <div className="sisoc-title-row">
        <div className="sisoc-title-block">
          <h1>{data.nombre}</h1>
          <p className="sisoc-title-sub"><i className="bi bi-book me-1" />{data.subtitulo}</p>
        </div>
        <div className="sisoc-title-meta">
          <span className="sisoc-cue-text">{data.codigo}</span>
          <span className="sisoc-status-pill">{data.estado_label}</span>
        </div>
      </div>
      <div className="sisoc-tabs-rail" role="tablist" aria-label="Secciones de la comisión">
        {order.map((panel) => <button key={panel} type="button" className={`sisoc-tab-chip${active === panel ? " is-active" : ""}`} data-sisoc-tab-target={panel}
          aria-selected={active === panel} onClick={() => setActive(panel)}>{rail[panel]}</button>)}
      </div>
      <div className="sisoc-metric-grid" id="sisocMetricGridGlobal" style={hideGlobalMetrics ? { display: "none" } : undefined}>
        {data.metricas.map((m) => <Metric key={m.label} value={m.valor} label={m.label} />)}
      </div>
      <div className="sisoc-info-shell">
        <div className="sisoc-side-tabs sisoc-side-tabs--left" role="tablist" aria-label="Secciones visitadas">
          {order.map((panel) => side(panel, panel !== "general"))}
        </div>
        <div className="sisoc-info-content">
          <GeneralPanel data={data} active={active} />
          <InscriptosPanel {...scope} selection={selection} />
          {espera && <EsperaPanel {...scope} />}
          <SesionesPanel data={data} active={active} />
          <HorariosPanel data={data} active={active} />
          {data.resultados && <ResultadosPanel data={data.resultados} active={active === "resultados"} endpoints={{ save: `${detail}resultados/`, buscar: `${detail}profesores/buscar/` }}
            profesor={profesor} setProfesor={setProfesor} openProfesor={() => setModal({ kind: "profesor" })} forbidden={forbidden} />}
        </div>
        <div className="sisoc-side-tabs sisoc-side-tabs--right" role="tablist" aria-label="Secciones pendientes">
          {order.map((panel) => side(panel, panel === "general"))}
        </div>
      </div>
    </div>
    {modal?.kind === "rapida" && data.formularios.rapida && <RapidaModal comision={data.id} fields={data.formularios.rapida} close={() => setModal(null)}
      endpoint={`${A}${curso ? "cursos/" : ""}rapida-comision/`} />}
    {modal?.kind === "lote" && <LoteModal resumen={modal.resumen} detalle={modal.detalle} close={() => setModal(null)}
      confirm={async () => { await selection.confirmar(modal.estado); setModal(null); }} />}
    {modal?.kind === "profesor" && data.formularios.profesor && <ProfesorModal fields={data.formularios.profesor} endpoint={`${detail}profesores/nuevo/`} close={() => setModal(null)} created={setProfesor} />}
  </>;
}

function ComisionDetallePage({ curso, id }: { curso: boolean; id: string }) {
  const [state, setState] = useMainResource(`web/vat/comisiones-detalle/${curso ? "cursos/" : ""}${id}/`, comisionDetalleValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando comisión…", (data) => ({ title: `${data.codigo} — ${data.titulo_tipo}`, breadcrumb: null, content: <ComisionDetalleContent data={data} forbidden={forbidden} /> }));
}

type Params = { curso: boolean; id: string };

// Native URLs of `VAT/urls.py` (`vat_comision_detail` and `vat_comision_curso_detail`).
const PATH = /^\/vat\/(cursos\/)?comisiones\/([0-9]+)\/$/;

export const vatComisionDetalleRoute: RouteDefinition<Params> = {
  name: "vat-comision-detalle",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { curso: m[1] !== undefined, id: m[2] } : null;
  },
  render: ({ curso, id }) => <ComisionDetallePage key={`${curso}:${id}`} curso={curso} id={id} />,
};
