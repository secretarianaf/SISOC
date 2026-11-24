/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { sameOriginTarget } from "./cdiObservaciones";
import { internal, record, text, useMainResource, webClient, type MainState } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import SisocShell from "./SisocShell";
import type { RouteDefinition } from "./types";

/**
 * RM01.03 monthly rendición audit: the search page and the audit form of
 * `rendicioncuentasmensual_auditoria.html` with `rendicioncuentasmensual_auditoria.js` (help text of the filter,
 * the show/hide of the minute fields and of the summaries). Data and the POST go through
 * `/api/web/comedores/rendicioncuentasmensual/auditoria/`, which runs the native `RendicionAuditoriaView`.
 * The search is the native GET form (a full-page navigation); the save is a multipart POST whose confirmed
 * redirect is a full-page navigation like the native 302.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Campo = { name: string; label: string; required: boolean; value: string; choices?: { value: string; label: string }[]; maxlength?: number; rows?: number };
type Resumen = { id: number; actual: boolean; titulo: string; documentos: { categoria: string; nombre: string; estado_text: string; ver_url: string }[] };
type Page = { is_paginated: boolean; number: number; count: number; previous: number | null; next: number | null; range: (number | "…")[]; query_prefix: string };
export type AuditoriaBusquedaData = {
  filtro: { value: string; choices: { value: string; label: string }[]; errors: string[] };
  busqueda: { value: string; maxlength: number; errors: string[] };
  busqueda_realizada: boolean; busqueda_valida: boolean; page: Page;
  filas: { id: number; proyecto: string; organizacion: string; convenio_numero: string; periodo: string; validada: string; gestionar_url: string; aria_label: string }[];
  urls: { listado: string; limpiar: string; volver: string }; messages: Message[];
};
type Opcion = { value: string; id: string; checked: boolean; numero: string; convenio: string; periodo: string; linea: string };
export type AuditoriaGestionData = {
  rendicion: { id: number; numero: string; convenio: string; periodo: string; organizacion: string; proyecto: string; convenio_dato: string; linea_programatica: string };
  form: {
    ya_validada: boolean; validada: { checked: boolean; errors: string[] }; genera_acta_auditoria: Campo;
    rendiciones_incluidas: { errors: string[]; opciones: Opcion[] }; acta_auditoria: Campo; resultado: Campo; observaciones: Campo; documento_regularizacion: Campo;
    errors: Record<string, { message: string }[]>; non_field_errors: string[];
  };
  resumenes: Resumen[]; urls: { listado: string; volver: string }; volver_a_busqueda: boolean; messages: Message[];
};

const API = "web/comedores/rendicioncuentasmensual/auditoria/";
const LEVELS = ["success", "error", "warning", "info"];
const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";
const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const strings = (v: unknown) => Array.isArray(v) && v.every(text);
const messagesValid = (v: unknown) => Array.isArray(v) && v.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
const campoValid = (v: unknown) => record(v) && text(v.name) && text(v.label) && typeof v.required === "boolean" && text(v.value) &&
  (v.choices === undefined || (Array.isArray(v.choices) && v.choices.every((c) => record(c) && text(c.value) && text(c.label))));
const resumenValid = (s: unknown) => record(s) && integer(s.id) && typeof s.actual === "boolean" && text(s.titulo) && Array.isArray(s.documentos) &&
  s.documentos.every((d) => record(d) && text(d.categoria) && text(d.nombre) && text(d.estado_text) && internal(d.ver_url));

export function busquedaValid(v: unknown): v is AuditoriaBusquedaData {
  if (!record(v) || !record(v.filtro) || !record(v.busqueda) || !record(v.page) || !record(v.urls)) return false;
  const p = v.page;
  return text(v.filtro.value) && Array.isArray(v.filtro.choices) && v.filtro.choices.every((c) => record(c) && text(c.value) && text(c.label)) && strings(v.filtro.errors) &&
    text(v.busqueda.value) && integer(v.busqueda.maxlength) && strings(v.busqueda.errors) && typeof v.busqueda_realizada === "boolean" && typeof v.busqueda_valida === "boolean" &&
    typeof p.is_paginated === "boolean" && integer(p.number) && integer(p.count) && (p.previous === null || integer(p.previous)) && (p.next === null || integer(p.next)) &&
    Array.isArray(p.range) && p.range.every((n) => n === "…" || integer(n)) && text(p.query_prefix) &&
    Array.isArray(v.filas) && v.filas.every((f) => record(f) && integer(f.id) && ["proyecto", "organizacion", "convenio_numero", "periodo", "validada", "aria_label"].every((k) => text(f[k])) && internal(f.gestionar_url)) &&
    internal(v.urls.listado) && internal(v.urls.limpiar) && internal(v.urls.volver) && messagesValid(v.messages);
}

export function gestionValid(v: unknown): v is AuditoriaGestionData {
  if (!record(v) || !record(v.rendicion) || !record(v.form) || !record(v.urls)) return false;
  const r = v.rendicion, f = v.form;
  return integer(r.id) && ["numero", "convenio", "periodo", "organizacion", "proyecto", "convenio_dato", "linea_programatica"].every((k) => text(r[k])) &&
    typeof f.ya_validada === "boolean" && record(f.validada) && typeof f.validada.checked === "boolean" && strings(f.validada.errors) &&
    ["genera_acta_auditoria", "acta_auditoria", "resultado", "observaciones", "documento_regularizacion"].every((k) => campoValid(f[k])) &&
    record(f.rendiciones_incluidas) && strings(f.rendiciones_incluidas.errors) && Array.isArray(f.rendiciones_incluidas.opciones) &&
    f.rendiciones_incluidas.opciones.every((o) => record(o) && text(o.value) && text(o.id) && typeof o.checked === "boolean" && ["numero", "convenio", "periodo", "linea"].every((k) => text(o[k]))) &&
    record(f.errors) && Object.values(f.errors).every((l) => Array.isArray(l) && l.every((e) => record(e) && text(e.message))) && strings(f.non_field_errors) &&
    Array.isArray(v.resumenes) && v.resumenes.every(resumenValid) && internal(v.urls.listado) && internal(v.urls.volver) && typeof v.volver_a_busqueda === "boolean" && messagesValid(v.messages);
}

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const auditoriaNavigation = { assign: (to: string) => window.location.assign(to) };

const STYLES = <>
  <link rel="stylesheet" href="/static/custom/css/listModerno.css" />
  <link rel="stylesheet" href="/static/custom/css/rendicioncuentasmensual_detail.css" />
  <link rel="stylesheet" href="/static/custom/css/rendicioncuentasmensual_auditoria.css" />
</>;

const ErrorList = ({ id, errors }: { id: string; errors: string[] }) => errors.length > 0
  ? <ul className="errorlist" id={`${id}_error`}>{errors.map((e, i) => <li key={i}>{e}</li>)}</ul> : null;

const INDICACIONES: Record<string, [string, string]> = {
  proyecto: ["Código o nombre del proyecto", "Buscá por el código o el nombre del proyecto."],
  organizacion: ["Nombre de la organización", "Buscá por el nombre de la organización."],
  periodo: ["MM/AAAA o DD/MM/AAAA", "Ingresá un mes, una fecha o un año. Se incluyen los períodos que lo contengan."],
};

// --- Search -----------------------------------------------------------------------

function Pagination({ page }: { page: Page }) {
  const href = (n: number) => `?${page.query_prefix}page=${n}`;
  return (
    <div className="mt-2">
      {page.is_paginated && (
        <ul className="pagination">
          <li className={`page-item${page.previous === null ? " disabled" : ""}`}><a href={page.previous === null ? "#" : href(page.previous)} className="page-link">Volver</a></li>
          {page.range.map((n, i) => (n === "…"
            ? <li key={`g${i}`} className="page-item disabled"><a href="#" className="page-link">...</a></li>
            : <li key={n} className={`page-item ${page.number === n ? "active" : ""}`}><a href={href(n)} className="page-link">{n}</a></li>))}
          <li className={`page-item${page.next === null ? " disabled" : ""}`}><a href={page.next === null ? "#" : href(page.next)} className="page-link">Continuar</a></li>
        </ul>
      )}
      {page.count > 0 && <p className="text-center text-muted mb-0 mt-1">Se encontraron {page.count} resultados</p>}
    </div>
  );
}

function Intro() {
  return (
    <div className="card mb-4">
      <div className="card-body">
        <h2 className="fw-bold">Auditoría de rendiciones</h2>
        <p className="text-muted mb-0">Validá la rendición y, si corresponde, generá un acta compartida entre los períodos seleccionados.</p>
      </div>
    </div>
  );
}

function BusquedaContent({ data }: { data: AuditoriaBusquedaData }) {
  const [filtro, setFiltro] = useState(data.filtro.value);
  const [placeholder, ayuda] = INDICACIONES[filtro] ?? INDICACIONES.proyecto;
  const invalid = data.busqueda.errors.length > 0;
  return (
    <>
      {STYLES}
      <NativeToasts messages={data.messages} />
      <div className="comedor-list-container">
        <Intro />
        <div className="card mb-4">
          <div className="card-body">
            <h5 className="mb-3">Buscar una rendición para auditar</h5>
            <form method="get" className="auditoria-busqueda">
              <div>
                <label htmlFor="id_filtro" className="form-label">Filtro</label>
                <select name="filtro" className="form-select" id="id_filtro" value={filtro} onChange={(e) => setFiltro(e.target.value)}>
                  {data.filtro.choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
                <ErrorList id="id_filtro" errors={data.filtro.errors} />
              </div>
              <div>
                <label htmlFor="id_busqueda" className="form-label">Búsqueda</label>
                <input type="search" name="busqueda" defaultValue={data.busqueda.value} className="form-control" placeholder={placeholder} aria-describedby="ayuda-busqueda-auditoria"
                  maxLength={data.busqueda.maxlength} required aria-invalid={invalid ? "true" : undefined} id="id_busqueda" />
                <ErrorList id="id_busqueda" errors={data.busqueda.errors} />
                <small id="ayuda-busqueda-auditoria" className="text-muted d-block mt-1">{ayuda}</small>
              </div>
              <div className="d-flex gap-2 auditoria-busqueda-acciones">
                <button type="submit" className="btn btn-primary"><i className="fas fa-search" aria-hidden="true" />{" "}Buscar</button>
                <a className="btn btn-outline-secondary" href={data.urls.limpiar}>Limpiar</a>
              </div>
            </form>
          </div>
        </div>
        <div className="card comedor-table-card">
          <div className="card-body">
            <h5>Rendiciones disponibles</h5>
            <p className="text-muted">
              {data.busqueda_realizada
                ? "Solo se muestran rendiciones que todavía permiten gestionar su auditoría. Elegí una con el botón Gestionar."
                : "Seleccioná un filtro e ingresá un texto para buscar rendiciones."}
            </p>
            <div className="table-responsive">
              <table className="table table-comedor-moderno">
                <caption className="visually-hidden">Rendiciones disponibles para iniciar la gestión de auditoría</caption>
                <thead><tr><th>Proyecto</th><th>Organización</th><th>Convenio / Rendición</th><th>Período</th><th>Validada</th><th>Acción</th></tr></thead>
                <tbody>
                  {data.filas.map((f) => (
                    <tr key={f.id}>
                      <td>{f.proyecto}</td><td>{f.organizacion}</td><td>{f.convenio_numero}</td><td>{f.periodo}</td><td>{f.validada}</td>
                      <td><a href={f.gestionar_url} className="btn btn-primary btn-sm" aria-label={f.aria_label}>Gestionar{" "}<i className="fas fa-arrow-right" aria-hidden="true" /></a></td>
                    </tr>
                  ))}
                  {data.filas.length === 0 && data.busqueda_valida && (
                    <tr><td colSpan={6} className="text-center py-4">No hay rendiciones disponibles para esta búsqueda. Probá otro texto o filtro.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            {data.busqueda_valida && <Pagination page={data.page} />}
          </div>
        </div>
      </div>
    </>
  );
}

// --- Audit form -------------------------------------------------------------------

function Crispy({ campo, children, errors }: { campo: Campo; children: ReactNode; errors: { message: string }[] }) {
  const id = `id_${campo.name}`;
  return (
    <div id={`div_${id}`} className="mb-3">
      <label htmlFor={id} className={`form-label${campo.required ? " requiredField" : ""}`}>{campo.label}{campo.required && <span className="asteriskField">*</span>}</label>
      {children}
      {errors.length > 0 && <div id={`${id}_error`} className="invalid-feedback">{errors.map((e, i) => <p key={i} id={`error_${i + 1}_${id}`}><strong>{e.message}</strong></p>)}</div>}
    </div>
  );
}

function GestionForm({ data, endpoint }: { data: AuditoriaGestionData; endpoint: string }) {
  const [state, setState] = useState({ data, revision: 0 });
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState("");
  const busy = useRef(false);
  const { rendicion: r, form: f } = state.data;
  const [genera, setGenera] = useState(f.genera_acta_auditoria.value);
  const [resultado, setResultado] = useState(f.resultado.value);
  const [elegidas, setElegidas] = useState(() => new Set(f.rendiciones_incluidas.opciones.filter((o) => o.checked).map((o) => o.value)));
  const conActa = genera === "True";
  const conObservaciones = conActa && resultado === "finalizada_con_observaciones";
  const errs = (name: string) => f.errors[name] ?? [];
  const invalid = (name: string) => errs(name).length > 0;
  const cls = (base: string, name: string) => `${base}${invalid(name) ? " is-invalid" : ""}`;
  const attrs = (name: string) => ({ "aria-invalid": invalid(name) ? ("true" as const) : undefined, "aria-describedby": invalid(name) ? `id_${name}_error` : undefined });

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    let message = UNCERTAIN;
    try {
      const { data: body, status } = await webClient.post(endpoint, new FormData(event.currentTarget), { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403 });
      if (status === 400 && gestionValid(body)) {
        setState((s) => ({ data: body, revision: s.revision + 1 }));
        setGenera(body.form.genera_acta_auditoria.value); setResultado(body.form.resultado.value);
        setElegidas(new Set(body.form.rendiciones_incluidas.opciones.filter((o) => o.checked).map((o) => o.value)));
        busy.current = false; setPending(false); resetAfterRejectedPost();
        return;
      }
      const to = status < 300 && record(body) && body.ok === true ? sameOriginTarget(body.redirect) : null;
      if (to) { auditoriaNavigation.assign(to); return; }
      if (status === 403 && record(body) && text(body.detail)) message = body.detail;
    } catch {
      // Network error or timeout after sending: the result is unknown.
    }
    busy.current = false; setPending(false); setUncertain(message);
  }

  const toggle = (value: string) => setElegidas((s) => { const n = new Set(s); if (n.has(value)) n.delete(value); else n.add(value); return n; });
  return (
    <>
      {STYLES}
      <NativeToasts messages={state.data.messages} />
      <div className="comedor-list-container">
        <Intro />
        <div className="card mb-4">
          <div className="card-body">
            <h5 className="mb-3">Información general · Rendición {r.numero}</h5>
            <dl className="auditoria-informacion mb-0">
              <div><dt>Organización</dt><dd>{r.organizacion}</dd></div>
              <div><dt>Proyecto</dt><dd>{r.proyecto}</dd></div>
              <div><dt>Convenio</dt><dd>{r.convenio_dato}</dd></div>
              <div><dt>Período</dt><dd>{r.periodo}</dd></div>
              <div><dt>Línea programática</dt><dd>{r.linea_programatica}</dd></div>
            </dl>
          </div>
        </div>
        <div className="card mb-4">
          <div className="card-body">
            <h5 className="mb-3">Auditoría</h5>
            <form method="post" encType="multipart/form-data" id="auditoria-form" data-validada={f.ya_validada ? "true" : "false"} onSubmit={submit} key={state.revision}>
              <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
              {f.non_field_errors.length > 0 && <ul className="errorlist nonfield">{f.non_field_errors.map((m, i) => <li key={i}>{m}</li>)}</ul>}
              <div className="auditoria-decisiones">
                <div className="mb-3">
                  {f.ya_validada ? (
                    <>
                      <div className="form-label">Validada</div>
                      <div className="auditoria-validacion-estado"><i className="fas fa-check-circle text-success" aria-hidden="true" /><strong>Sí</strong></div>
                      <small className="text-muted d-block">Validación guardada. No se puede modificar.</small>
                    </>
                  ) : (
                    <>
                      <div className="form-label">Validada<span className="asteriskField">*</span></div>
                      <label className="auditoria-validacion-control" htmlFor="id_validada">
                        <input type="checkbox" name="validada" className="form-check-input" required id="id_validada" defaultChecked={f.validada.checked}
                          aria-invalid={f.validada.errors.length ? "true" : undefined} aria-describedby={f.validada.errors.length ? "id_validada_error" : undefined} />
                        <span>Confirmar validación</span>
                      </label>
                      {f.validada.errors.map((e, i) => <div key={i} className="invalid-feedback d-block">{e}</div>)}
                    </>
                  )}
                </div>
                <div>
                  <Crispy campo={f.genera_acta_auditoria} errors={errs("genera_acta_auditoria")}>
                    <select name="genera_acta_auditoria" className={cls("form-select", "genera_acta_auditoria")} id="id_genera_acta_auditoria" required {...attrs("genera_acta_auditoria")}
                      value={genera} onChange={(e) => setGenera(e.target.value)}>
                      {(f.genera_acta_auditoria.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                    </select>
                  </Crispy>
                </div>
              </div>
              <div id="campos-acta" hidden={!conActa}>
                <fieldset className="border rounded p-2 mb-3 auditoria-inclusion" disabled={undefined}>
                  <legend className="float-none w-auto px-2 fs-6">Rendiciones incluidas en el acta</legend>
                  <p className="text-muted small mb-2">La actual se incluye siempre. Podés sumar rendiciones del mismo proyecto y organización, validadas y auditadas sin acta.</p>
                  <label className="auditoria-rendicion-opcion auditoria-rendicion-actual" htmlFor="rendicion-actual-incluida">
                    <input id="rendicion-actual-incluida" type="checkbox" className="form-check-input" data-inclusion-obligatoria="true" checked disabled readOnly />
                    <span className="auditoria-opcion-datos">
                      <strong>Rendición {r.numero} · {r.convenio}</strong>
                      <span>{r.periodo}</span>
                      <small><i className="fas fa-lock" aria-hidden="true" />{" "}Actual · Inclusión fija</small>
                    </span>
                  </label>
                  <ErrorList id="id_rendiciones_incluidas" errors={f.rendiciones_incluidas.errors} />
                  {f.rendiciones_incluidas.opciones.map((o) => (
                    <label key={o.id} className="auditoria-rendicion-opcion" htmlFor={o.id}>
                      <input type="checkbox" name="rendiciones_incluidas" value={o.value} className="form-check-input" id={o.id} disabled={!conActa} checked={elegidas.has(o.value)} onChange={() => toggle(o.value)} />
                      <span className="auditoria-opcion-datos">
                        <strong>Rendición {o.numero} · {o.convenio}</strong>
                        <span>{o.periodo}</span>
                        <small className="text-muted">{o.linea}</small>
                      </span>
                    </label>
                  ))}
                  {f.rendiciones_incluidas.opciones.length === 0 && <p className="mb-0 text-muted">No hay otras rendiciones elegibles para incluir.</p>}
                </fieldset>
                <div className="row">
                  <div className="col-md-6">
                    <Crispy campo={f.acta_auditoria} errors={errs("acta_auditoria")}>
                      <div><input type="file" name="acta_auditoria" className={cls("form-control form-control", "acta_auditoria")} id="id_acta_auditoria" disabled={!conActa} {...attrs("acta_auditoria")} /></div>
                    </Crispy>
                  </div>
                  <div className="col-md-6">
                    <Crispy campo={f.resultado} errors={errs("resultado")}>
                      <select name="resultado" className={cls("form-select", "resultado")} id="id_resultado" required={conActa} disabled={!conActa} {...attrs("resultado")}
                        value={resultado} onChange={(e) => setResultado(e.target.value)}>
                        {(f.resultado.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                      </select>
                    </Crispy>
                  </div>
                </div>
                <div id="campos-observaciones" hidden={!conObservaciones}>
                  <Crispy campo={f.observaciones} errors={errs("observaciones")}>
                    <textarea name="observaciones" cols={40} rows={f.observaciones.rows ?? 3} className={cls("form-control textarea", "observaciones")} id="id_observaciones"
                      defaultValue={f.observaciones.value} required={conObservaciones} disabled={!conObservaciones} {...attrs("observaciones")} />
                  </Crispy>
                  <Crispy campo={f.documento_regularizacion} errors={errs("documento_regularizacion")}>
                    <div><input type="file" name="documento_regularizacion" className={cls("form-control form-control", "documento_regularizacion")} id="id_documento_regularizacion" disabled={!conObservaciones} {...attrs("documento_regularizacion")} /></div>
                  </Crispy>
                </div>
              </div>
              <p className="text-muted">
                <i id="auditoria-cierre-icono" className="fas fa-lock" aria-hidden="true" />{" "}
                <span id="auditoria-guardar-ayuda">Al guardar la decisión sobre el acta, la gestión de esta rendición se cierra.</span>
              </p>
              <button type="submit" className="btn btn-success" id="auditoria-guardar" disabled={pending || !!uncertain}>Guardar y cerrar Auditoría</button>
              {" "}<a className="btn btn-secondary" href={state.data.urls.volver} data-sisoc-volver data-volver-fallback={state.data.urls.volver}>
                {state.data.volver_a_busqueda ? "Volver a resultados" : "Volver al detalle"}
              </a>
              {uncertain && <p role="alert" className="mb-0">{uncertain}</p>}
            </form>
          </div>
        </div>
        <div className="card comedor-table-card">
          <div className="card-body">
            <h5>Documentación de las rendiciones seleccionadas</h5>
            {state.data.resumenes.map((s) => (
              <details key={s.id} className="border rounded p-3 mb-3 js-resumen-rendicion" data-rendicion={s.id} data-actual={s.actual ? "true" : "false"}
                hidden={!s.actual && (!conActa || !elegidas.has(String(s.id)))}>
                <summary>{s.titulo}</summary>
                <div className="table-responsive mt-3">
                  <table className="table table-comedor-moderno">
                    <thead><tr><th>Categoría</th><th>Documento</th><th>Estado</th></tr></thead>
                    <tbody>
                      {s.documentos.map((d, i) => (
                        <tr key={i}><td>{d.categoria}</td><td><a href={d.ver_url} target="_blank" rel="noopener">{d.nombre}</a></td><td>{d.estado_text}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

// --- Frame ------------------------------------------------------------------------

function AppLoaded() {
  useEffect(() => {
    document.body.classList.add("app-loaded");
    return () => document.body.classList.remove("app-loaded");
  }, []);
  return null;
}

function frame<T extends { urls: { listado: string; volver: string } }>(state: MainState<T>, loading: string, content: (d: T) => ReactNode): ReactNode {
  if (state.status === "loading") return <main role="status">{loading}</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar la página.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  const { data, session } = state;
  const breadcrumb = (
    <ol className="breadcrumb float-sm-right">
      <li className="breadcrumb-item"><a href={data.urls.listado}>Rendiciones</a></li>
      <li className="breadcrumb-item active">Auditoría</li>
    </ol>
  );
  return (
    <>
      <SisocShell context={session} content={content(data)} pageTitle="Auditoría de rendiciones" heading="" breadcrumb={breadcrumb} previewLinks={false} backHref={data.urls.volver} />
      <AppLoaded />
    </>
  );
}

function BusquedaPage() {
  const [state] = useMainResource(`${API}${window.location.search}`, busquedaValid);
  return <>{frame(state, "Cargando auditoría…", (d) => <BusquedaContent data={d} />)}</>;
}

function GestionPage({ pk }: { pk: string }) {
  const endpoint = `${API}${pk}/${window.location.search}`;
  const [state] = useMainResource(endpoint, gestionValid);
  return <>{frame(state, "Cargando auditoría…", (d) => <GestionForm key={endpoint} data={d} endpoint={endpoint} />)}</>;
}

// Native URLs of `rendicioncuentasmensual/urls.py` under the runtime's include (the prefix is repeated on purpose).
const OWN = /^\/rendicioncuentasmensual\/rendicioncuentasmensual\/auditoria\/(?:([0-9]+)\/)?$/;

export const rendicionMensualAuditoriaRoute: RouteDefinition<{ pk: string | null }> = {
  name: "comedores-rendicion-mensual-auditoria",
  match(pathname) {
    const found = OWN.exec(pathname);
    return found ? { pk: found[1] ?? null } : null;
  },
  render(params) {
    return params.pk ? <GestionPage key={params.pk} pk={params.pk} /> : <BusquedaPage />;
  },
};
