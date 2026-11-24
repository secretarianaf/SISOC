import { useEffect, useRef, useState, type FormEvent } from "react";
import { postForm } from "./MainFrame";
import { comisionNav, goTo, useProfesorSearch, type Profesor } from "./vatComisionDetalleAcciones";
import { CsrfInput, UNCERTAIN } from "./vatFormShared";
import type { Resultados } from "./vatComisionDetalle";

/**
 * «Resultados» tab of `comision_detail.html` (course commissions): the acta (teacher, end date, number) and the grade of each
 * student. The filter, the buttons, the summary and the validation are the page script; saving is the native POST of the
 * results (`ComisionCursoResultadosView`), which redirects to the same tab.
 */
type Filtro = "todos" | "pendientes" | "finalizados";
const FILTROS: [Filtro, string][] = [["todos", "Todos"], ["pendientes", "A calificar"], ["finalizados", "Finalizados"]];

export function ResultadosPanel({ data, active, endpoints, profesor, setProfesor, openProfesor, forbidden }: {
  data: Resultados; active: boolean; endpoints: { save: string; buscar: string };
  profesor: Profesor | null; setProfesor: (p: Profesor | null) => void; openProfesor: () => void; forbidden: (d: unknown) => void;
}) {
  const [marks, setMarks] = useState<Record<number, string>>(() => Object.fromEntries(data.alumnos.map((a) => [a.id, a.resultado])));
  const [filtro, setFiltro] = useState<Filtro>("todos");
  const [fecha, setFecha] = useState(data.fecha_fin);
  const [numero, setNumero] = useState(data.numero_acta);
  const [query, setQuery] = useState("");
  const [alert, setAlert] = useState<string | null>(null);
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  const results = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const search = useProfesorSearch(endpoints.buscar);
  const { aprobado, desaprobado } = data;
  const pill = (v: string): [string, string] => (v === aprobado ? ["ci-pill-green", "Aprobado"] : v === desaprobado ? ["ci-pill-red", "Desaprobado"] : ["ci-pill-gray", "Sin calificar"]);
  const valor = (id: number) => marks[id] ?? "";
  const aprobados = data.alumnos.filter((a) => valor(a.id) === aprobado).length;
  const desaprobados = data.alumnos.filter((a) => valor(a.id) === desaprobado).length;
  const matches = (id: number) => (filtro === "pendientes" ? valor(id) === "" : filtro === "finalizados" ? valor(id) !== "" : true);
  const visibles = data.alumnos.filter((a) => matches(a.id)).length;
  const resumen = { aprobados, desaprobados, sin_calificar: data.alumnos.length - aprobados - desaprobados, inscriptos: data.alumnos.length };

  const { hide } = search;
  useEffect(() => {
    const outside = (e: MouseEvent) => { if (!results.current?.contains(e.target as Node) && e.target !== input.current) hide(); };
    document.addEventListener("click", outside);
    return () => document.removeEventListener("click", outside);
  }, [hide]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setAlert(null);
    if (!profesor) { setAlert("Seleccioná el profesor a cargo para guardar el acta."); return; }
    if (!fecha) { setAlert("Indicá la fecha de fin para guardar el acta."); return; }
    if (busy.current || uncertain) return;
    busy.current = true;
    const body = new URLSearchParams({ profesor: String(profesor.id), fecha_fin: fecha, numero_acta: numero });
    for (const a of data.alumnos) body.append(`resultado_${a.id}`, valor(a.id));
    const result = await postForm(endpoints.save, body);
    busy.current = false;
    if (result.kind === "redirect") goTo(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else setUncertain(true);
  }

  return (
    <section className={`sisoc-info-panel sisoc-info-panel--overflow${active ? " is-active" : ""}`} data-sisoc-panel="resultados">
      <form id="formResultados" method="post" noValidate onSubmit={(e) => void submit(e)}>
        <CsrfInput />
        <div className="sisoc-metric-grid sisoc-metric-grid--quad">
          {([["aprobados", "Aprobados"], ["desaprobados", "Desaprobados"], ["sin_calificar", "Sin calificar"], ["inscriptos", "Inscriptos"]] as const).map(([key, label]) => (
            <article key={key} className="sisoc-metric-card"><strong className="sisoc-metric-value" data-resumen={key}>{resumen[key]}</strong><span className="sisoc-metric-label">{label}</span></article>
          ))}
        </div>
        <div className="sisoc-block-card sisoc-block-card--overflow">
          <div className="sisoc-block-title"><i className="bi bi-file-earmark-text" /><span>Datos del acta</span></div>
          <div className="sisoc-block-body">
            <div id="resultadosAlert" className={alert ? "alert alert-danger" : "alert d-none"} role="alert">{alert ?? ""}</div>
            {uncertain && <p role="alert">{UNCERTAIN}</p>}
            <div className="ci-acta-grid">
              <div className="ci-prof-search">
                <label className="ci-field-label" htmlFor="profesorBuscador">Profesor a cargo<span className="text-danger">*</span></label>
                <div className="ci-prof-input-wrap">
                  <input ref={input} type="text" className="ci-field-input" id="profesorBuscador" placeholder="Buscar por nombre o DNI" autoComplete="off" value={query}
                    onChange={(e) => { setQuery(e.target.value); search.schedule(e.target.value); }}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); search.now(query); } }} />
                  <input type="hidden" name="profesor" id="profesorId" value={profesor?.id ?? ""} readOnly />
                  <div ref={results} className={`ci-prof-results${search.items ? "" : " d-none"}`} id="profesorResultados">
                    {search.items && (search.items.length
                      ? search.items.map((p) => <button key={p.id} type="button" onClick={() => { setProfesor(p); setQuery(""); search.hide(); }}>{p.text}</button>)
                      : <div className="ci-prof-results-empty">Sin coincidencias. Usá &quot;Agregar profesor&quot;.</div>)}
                  </div>
                </div>
                <div className={`ci-prof-chip${profesor ? "" : " d-none"}`} id="profesorChip">
                  <span id="profesorChipTexto">{profesor?.text ?? ""}</span>
                  <button type="button" id="profesorChipQuitar" aria-label="Quitar profesor seleccionado" onClick={() => setProfesor(null)}><i className="bi bi-x-lg" /></button>
                </div>
              </div>
              <div>
                <label className="ci-field-label" htmlFor="actaFechaFin">Fecha de fin<span className="text-danger">*</span></label>
                <input type="date" className="ci-field-input" id="actaFechaFin" name="fecha_fin" value={fecha} onChange={(e) => setFecha(e.target.value)} />
              </div>
              <div>
                <label className="ci-field-label" htmlFor="actaNumero">N° de acta (opcional)</label>
                <input type="text" className="ci-field-input" id="actaNumero" name="numero_acta" placeholder="Ej: 0245/2026" value={numero} onChange={(e) => setNumero(e.target.value)} />
              </div>
            </div>
          </div>
        </div>
        <div className="ci-tbl-card mt-4" id="resultadosTabla">
          <div className="ci-tbl-head"><i className="bi bi-list-check" /><span>Calificación de alumnos</span></div>
          <div className="ci-tbl-toolbar">
            <div className="ci-filtro-group" role="group" aria-label="Filtrar alumnos">
              {FILTROS.map(([key, label]) => <button key={key} type="button" className={`ci-filtro-btn${filtro === key ? " is-active" : ""}`} data-filtro={key} onClick={() => setFiltro(key)}>{label}</button>)}
            </div>
            <button type="button" className="sisoc-btn sisoc-btn--add" onClick={openProfesor}><i className="bi bi-person-plus" /><span>Agregar profesor</span></button>
          </div>
          <div className="ci-tbl-scroll">
            <table className="ci-tbl">
              <thead><tr><th>Apellido</th><th>Nombre</th><th>Documento</th><th>Resultado</th><th className="ci-tbl-col-actions">Acciones</th></tr></thead>
              <tbody id="resultadosTablaBody">
                {data.alumnos.map((a) => {
                  const [klass, label] = pill(valor(a.id));
                  return <tr key={a.id} className={`ci-tbl-row${matches(a.id) ? "" : " d-none"}`} data-inscripcion={a.id} data-resultado={valor(a.id)}>
                    <td className="text-uppercase">{a.apellido}</td>
                    <td>{a.nombre}</td>
                    <td>{a.documento}</td>
                    <td><span className={`ci-pill ${klass}`} data-resultado-pill>{label}</span></td>
                    <td><div className="ci-resultado-acciones">
                      <button type="button" className="sisoc-btn sisoc-btn--add" data-marcar={aprobado} onClick={() => { setMarks((m) => ({ ...m, [a.id]: aprobado })); setAlert(null); }}><i className="bi bi-check-lg" /><span>Aprobar</span></button>
                      <button type="button" className="sisoc-btn sisoc-btn--delete" data-marcar={desaprobado} onClick={() => { setMarks((m) => ({ ...m, [a.id]: desaprobado })); setAlert(null); }}><i className="bi bi-x-lg" /><span>Desaprobar</span></button>
                      <input type="hidden" name={`resultado_${a.id}`} value={valor(a.id)} readOnly data-resultado-input />
                    </div></td>
                  </tr>;
                })}
                {data.alumnos.length === 0 && <tr className="ci-tbl-empty"><td colSpan={5}>Sin alumnos para calificar. Sólo se listan las inscripciones confirmadas de la comisión.</td></tr>}
                <tr className={`ci-tbl-empty${visibles === 0 && data.alumnos.length > 0 ? "" : " d-none"}`} data-sin-resultados-row><td colSpan={5}>No hay alumnos para el filtro seleccionado.</td></tr>
              </tbody>
            </table>
          </div>
          <div className="ci-tbl-foot">
            <span id="resultadosConteo">Mostrando {visibles} de {data.alumnos.length}</span>
            <div className="d-flex gap-2">
              <button type="button" className="sisoc-btn sisoc-btn--light" id="resultadosCancelar" onClick={() => { window.location.hash = "resultados"; comisionNav.reload(); }}>Cancelar</button>
              <button type="submit" className="sisoc-btn sisoc-btn--gold"><i className="bi bi-save" /><span>Guardar resultados</span></button>
            </div>
          </div>
        </div>
      </form>
    </section>
  );
}
