/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useRef, useState, type FormEvent } from "react";
import { postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import { CsrfInput, UNCERTAIN, useForbidden } from "./vatFormShared";
import { ASISTENCIA_CSS } from "./vatAsistenciaStyles";
import { bool, integer, messagesValid, vatNavigation, type Message } from "./vatShared";
import { TourHelp } from "./vatTour";
import type { RouteDefinition } from "./types";

/**
 * V02.01 registro de asistencia por sesión: `vat/oferta_institucional/asistencia_sesion.html`, shared by the course
 * and the offer routes. Data comes from `/api/web/vat/**\/sesiones/<id>/asistencia/`, which runs the native view; the
 * POST runs its native `post` (saves every active row, flips the session state, queues the message).
 */
type Fila = { id: number; apellido: string; nombre: string; tipo_alumno: string; es_alumno_vat: boolean; presente: boolean | null; observaciones: string };
export type AsistenciaData = {
  numero_sesion: number; comision_label: string; curso: string; estado: string; dia: string; horario: string;
  totales: Record<"presentes" | "ausentes" | "sin_marcar", string>; filas: Fila[]; messages: Message[];
};

const PAGE_SIZE = 10;

const filaValid = (f: unknown) => record(f) && integer(f.id) && text(f.apellido) && text(f.nombre) && text(f.tipo_alumno) && bool(f.es_alumno_vat) &&
  (f.presente === null || bool(f.presente)) && text(f.observaciones);

export const asistenciaValid = (v: unknown): v is AsistenciaData => record(v) && integer(v.numero_sesion) && ["comision_label", "curso", "estado", "dia", "horario"].every((k) => text(v[k])) &&
  record(v.totales) && ["presentes", "ausentes", "sin_marcar"].every((k) => text((v.totales as Record<string, unknown>)[k])) &&
  Array.isArray(v.filas) && v.filas.every(filaValid) && messagesValid(v.messages);

type Marca = boolean | null;

function AsistenciaContent({ data, endpoint, forbidden }: { data: AsistenciaData; endpoint: string; forbidden: (d: unknown) => void }) {
  const [marcas, setMarcas] = useState<Record<number, Marca>>(() => Object.fromEntries(data.filas.map((f) => [f.id, f.presente])));
  const [todosPresentes, setTodosPresentes] = useState(false);
  const [todosAusentes, setTodosAusentes] = useState(false);
  const [pagina, setPagina] = useState(1);
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  const { filas } = data;
  const total = filas.length;
  const paginas = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const actual = Math.min(Math.max(pagina, 1), paginas);
  const inicio = (actual - 1) * PAGE_SIZE;
  const fin = inicio + PAGE_SIZE;
  const valores = filas.map((f) => marcas[f.id]);
  // `updateMetrics()` of the native page recounts on load, so the three cards always agree with the rows.
  const presentes = valores.filter((v) => v === true).length;
  const ausentes = valores.filter((v) => v === false).length;
  const sinMarcar = total - presentes - ausentes;

  const marcarTodos = (presente: boolean) => (checked: boolean) => {
    if (presente) setTodosPresentes(checked); else setTodosAusentes(checked);
    if (!checked) return;
    if (presente) setTodosAusentes(false); else setTodosPresentes(false);
    setMarcas(Object.fromEntries(filas.map((f) => [f.id, presente])));
  };

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true;
    const body = new URLSearchParams();
    for (const f of filas) {
      body.append(`obs_${f.id}`, f.observaciones);
      const marca = marcas[f.id];
      if (marca !== null) body.append(`presente_${f.id}`, marca ? "1" : "0");
    }
    const result = await postForm(endpoint, body);
    busy.current = false;
    if (result.kind === "redirect") vatNavigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else { setUncertain(true); resetAfterRejectedPost(); }
  }

  return <>
    <NativeToasts messages={data.messages} />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
    <link href="https://fonts.googleapis.com/css2?family=Lora:wght@600;700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <style>{ASISTENCIA_CSS}</style>
    <div className="asis-page">
      <div className="asis-title-row">
        <div className="asis-title-block">
          <h1>{data.comision_label}</h1>
          <p className="asis-title-sub"><i className="bi bi-book me-1" />{data.curso}</p>
        </div>
        <span className="asis-status-pill">{data.estado}</span>
      </div>
      <div className="asis-metric-grid">
        <article className="asis-metric-card asis-metric-card--green">
          <strong className="asis-metric-value" id="asisMetricPresentes">{total ? presentes : data.totales.presentes}</strong>
          <span className="asis-metric-label">Estudiantes presentes</span>
        </article>
        <article className="asis-metric-card asis-metric-card--red">
          <strong className="asis-metric-value" id="asisMetricAusentes">{total ? ausentes : data.totales.ausentes}</strong>
          <span className="asis-metric-label">Estudiantes ausentes</span>
        </article>
        <article className="asis-metric-card asis-metric-card--gold">
          <strong className="asis-metric-value" id="asisMetricSinMarcar">{total ? sinMarcar : data.totales.sin_marcar}</strong>
          <span className="asis-metric-label">Estudiantes sin marcar</span>
        </article>
      </div>
      {total ? (
        <form method="post" id="asisForm" onSubmit={(e) => void submit(e)}>
          <CsrfInput />
          {uncertain && <p role="alert">{UNCERTAIN}</p>}
          <div className="asis-card" id="asisTabla">
            <div className="asis-card-head"><i className="bi bi-people" /><span>Registro de asistencia clase #{data.numero_sesion}</span></div>
            <div className="asis-subhead">
              <span><i className="bi bi-calendar3" />{data.dia}</span>
              <span><i className="bi bi-clock" />{data.horario}</span>
            </div>
            <div className="asis-tbl-scroll">
              <table className="asis-tbl">
                <thead><tr>
                  <th>Apellido</th><th>Nombre</th><th>Tipo de alumno</th>
                  <th className="asis-col-check"><label className="asis-mark asis-mark-all">
                    <input type="checkbox" className="asis-check asis-check--present" id="asisMarcarPresentes" checked={todosPresentes} onChange={(e) => marcarTodos(true)(e.target.checked)} />Marcar todos
                  </label></th>
                  <th className="asis-col-check"><label className="asis-mark asis-mark-all">
                    <input type="checkbox" className="asis-check asis-check--absent" id="asisMarcarAusentes" checked={todosAusentes} onChange={(e) => marcarTodos(false)(e.target.checked)} />Marcar todos
                  </label></th>
                </tr></thead>
                <tbody id="asisTablaBody">
                  {filas.map((f, i) => (
                    <tr key={f.id} className={`asis-row${i >= inicio && i < fin ? "" : " d-none"}`}>
                      <td>{f.apellido}</td>
                      <td>{f.nombre}</td>
                      <td>{f.es_alumno_vat ? <span className="asis-chip-vat">{f.tipo_alumno}</span> : <span className="asis-tipo-sin-plan">{f.tipo_alumno}</span>}</td>
                      <td>
                        <input type="hidden" name={`obs_${f.id}`} defaultValue={f.observaciones} />
                        <label className="asis-mark">
                          <input type="radio" className="asis-check asis-check--present asis-present" name={`presente_${f.id}`} value="1" checked={marcas[f.id] === true}
                            onChange={() => setMarcas((m) => ({ ...m, [f.id]: true }))} />Presente
                        </label>
                      </td>
                      <td>
                        <label className="asis-mark">
                          <input type="radio" className="asis-check asis-check--absent asis-absent" name={`presente_${f.id}`} value="0" checked={marcas[f.id] === false}
                            onChange={() => setMarcas((m) => ({ ...m, [f.id]: false }))} />Ausente
                        </label>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="asis-foot">
              <span id="asisConteo">Mostrando {total === 0 ? 0 : inicio + 1}-{Math.min(fin, total)} de {total}</span>
              <div className="asis-pager">
                <button type="button" className="asis-pager-prev" id="asisPrev" aria-label="Página anterior" disabled={actual <= 1} onClick={() => setPagina(actual - 1)}><i className="bi bi-chevron-left" /></button>
                <span className="asis-pager-label" id="asisPager">{actual} de {paginas}</span>
                <button type="button" className="asis-pager-next" id="asisNext" aria-label="Página siguiente" disabled={actual >= paginas} onClick={() => setPagina(actual + 1)}><i className="bi bi-chevron-right" /></button>
              </div>
            </div>
          </div>
          <div className="asis-actions"><button type="submit" className="asis-save"><i className="bi bi-check-lg" />Guardar Asistencia</button></div>
        </form>
      ) : (
        <div className="asis-card">
          <div className="asis-card-head"><i className="bi bi-people" /><span>Registro de asistencia clase #{data.numero_sesion}</span></div>
          <div className="asis-empty">
            <i className="bi bi-person-plus" />
            <p className="asis-empty-t">Sin inscriptos aceptados</p>
            <p className="asis-empty-s">Aceptá inscripciones desde el detalle de la comisión para poder tomar asistencia.</p>
          </div>
        </div>
      )}
    </div>
    <TourHelp section="asistencia" />
  </>;
}

function AsistenciaPage({ curso, id }: { curso: boolean; id: string }) {
  const endpoint = `web/vat/${curso ? "cursos/" : ""}comisiones/sesiones/${id}/asistencia/`;
  const [state, setState] = useMainResource(endpoint, asistenciaValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando asistencia…", (data) => ({
    title: `Registro de asistencia — Clase #${data.numero_sesion}`, breadcrumb: null,
    content: <AsistenciaContent data={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { curso: boolean; id: string };

// Native URLs of `VAT/urls.py`.
const PATH = /^\/vat\/(cursos\/)?comisiones\/sesiones\/([0-9]+)\/asistencia\/$/;

export const vatAsistenciaRoute: RouteDefinition<Params> = {
  name: "vat-asistencia",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { curso: m[1] !== undefined, id: m[2] } : null;
  },
  render: ({ curso, id }) => <AsistenciaPage key={`${curso}:${id}`} curso={curso} id={id} />,
};
