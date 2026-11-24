/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens, the question model and the validators live here with the route. */
import { Fragment, useCallback, useEffect, useLayoutEffect, useRef, useState, type DragEvent, type FormEvent, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { Breadcrumb, accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeModal, NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * Survey create/edit form (`encuestas/encuesta_form.html` + `encuestaPreguntasBuilder.js`, `/encuestas/crear/` and
 * `/encuestas/<id>/editar/`). GET `/api/web/encuestas/crear/` and `.../<id>/editar/` run the native create and update
 * views (403 without `encuestas.add_encuesta` / `encuestas.change_encuesta`; an approval-pending survey answers the
 * native redirect to its review). The page posts what the native form submits (the form's own `FormData`, so the
 * disabled reminder interval stays out, plus `preguntas_json` built by the same serialisation as the native editor) to
 * the same path: a valid form answers the native redirect with its message queued; an invalid one is the native
 * re-render (400 with the bound values, the errors and the posted questions) and the view goes back to the top.
 * The question editor keeps the native behaviour: drag and drop (and the arrow keys) to reorder with the dependency
 * check, conditions that only reference earlier questions, fixed-choice condition values and scoring rows.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Campo = { value: string | boolean; errors: string[]; invalid: boolean; describedby: string };
type PreguntaDatos = Record<string, unknown>;
export type FormularioData = {
  id: number | null; motivo_rechazo: { texto: string; usuario: string; fecha: string; estado: string } | null;
  non_field_errors: string[]; fields: Record<string, Campo>; preguntas: PreguntaDatos[];
  tipos_pregunta: [string, string][]; operadores_condicion: [string, string][]; tipos_con_opciones: string; tipos_ponderables: string;
  urls: { exportar: string } | null; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const CAMPOS = ["titulo", "descripcion", "es_anonima", "modalidad", "es_recurrente", "intervalo_recordatorio_dias", "duracion_ronda_dias", "intervalo_recurrencia_dias"];
const pares = (v: unknown) => Array.isArray(v) && v.every((p) => Array.isArray(p) && p.length === 2 && text(p[0]) && text(p[1]));

export function formularioValid(v: unknown): v is FormularioData {
  return record(v) && (v.id === null || (typeof v.id === "number" && Number.isSafeInteger(v.id))) &&
    (v.motivo_rechazo === null || (record(v.motivo_rechazo) && ["texto", "usuario", "fecha", "estado"].every((k) => text((v.motivo_rechazo as Record<string, unknown>)[k])))) &&
    Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) &&
    record(v.fields) && CAMPOS.every((k) => {
      const f = (v.fields as Record<string, unknown>)[k];
      return record(f) && (text(f.value) || typeof f.value === "boolean") && Array.isArray(f.errors) && f.errors.every(text) && typeof f.invalid === "boolean" && text(f.describedby);
    }) &&
    Array.isArray(v.preguntas) && v.preguntas.every(record) && pares(v.tipos_pregunta) && pares(v.operadores_condicion) &&
    text(v.tipos_con_opciones) && text(v.tipos_ponderables) &&
    (v.urls === null || (record(v.urls) && internal(v.urls.exportar))) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

const redirectValid = (v: unknown): v is { redirect: string } => record(v) && internal(v.redirect) && !("fields" in v);

/* ---- question model: the state the native builder keeps in the DOM ---- */

type Fila = {
  key: number; texto: string; bloque: string; maxCaracteres: string; tipo: string; obligatoria: boolean; opciones: string; pondera: boolean;
  puntajeSi: string; puntajeNo: string; puntajes: Map<string, string>;
  ref: number | null; operador: string; valorTexto: string; valorSelect: string; sel: boolean;
};

const SI_NO: [string, string][] = [["si", "Sí"], ["no", "No"]];
const csv = (v: string) => v.split(",").map((t) => t.trim()).filter(Boolean);
const lineas = (v: string) => v.split("\n").map((l) => l.trim()).filter(Boolean);
const esTexto = (tipo: string) => tipo === "texto_corto" || tipo === "texto_largo";
const entero = (v: unknown) => parseInt(String(v), 10) || 0;

type Reglas = { conOpciones: string[]; ponderables: string[]; tiposDefault: string; operadorDefault: string };

/** Fixed value set of a condition on `fila`, or null when the type takes free text. */
function opcionesCondicion(fila: Fila, conOpciones: string[]): [string, string][] | null {
  if (fila.tipo === "si_no") return SI_NO;
  if (conOpciones.includes(fila.tipo)) return lineas(fila.opciones).map((l) => [l, l]);
  return null;
}

/**
 * The native `renumerarFilas` + `refrescarCondicionesValor`: a reference survives only while its row stays earlier,
 * and the value control is the select of the referenced fixed set (keeping the previous value when it still exists)
 * or the free-text input.
 */
function normalizar(filas: Fila[], conOpciones: string[]): Fila[] {
  return filas.map((fila, indice) => {
    const index = fila.ref === null ? -1 : filas.findIndex((f) => f.key === fila.ref);
    const ref = index >= 0 && index < indice ? fila.ref : null;
    const referida = ref === null ? null : filas[index];
    const opciones = referida ? opcionesCondicion(referida, conOpciones) : null;
    if (!opciones) return fila.ref === ref && !fila.sel ? fila : { ...fila, ref, sel: false };
    const previo = fila.sel ? fila.valorSelect : fila.valorTexto;
    const valorSelect = opciones.some(([v]) => v === previo) ? previo : (opciones[0]?.[0] ?? "");
    return { ...fila, ref, sel: true, valorSelect };
  });
}

let siguiente = 1;
function nuevaFila(reglas: Reglas, datos?: PreguntaDatos): Fila {
  const fila: Fila = {
    key: siguiente++, texto: "", bloque: "", maxCaracteres: "", tipo: reglas.tiposDefault, obligatoria: true, opciones: "", pondera: false,
    puntajeSi: "0", puntajeNo: "0", puntajes: new Map(), ref: null, operador: reglas.operadorDefault, valorTexto: "", valorSelect: "", sel: false,
  };
  if (!datos) return fila;
  const opciones = (Array.isArray(datos.opciones) ? datos.opciones : []).map((o) => (record(o) ? o : { texto: o, puntaje: 0 }));
  opciones.forEach((o) => fila.puntajes.set(String(o.texto), String(o.puntaje || 0)));
  const tipo = text(datos.tipo) && datos.tipo ? datos.tipo : fila.tipo;
  const ponderable = reglas.ponderables.includes(tipo);
  return {
    ...fila, texto: String(datos.texto || ""), bloque: String(datos.bloque || ""), tipo, obligatoria: datos.obligatoria !== false,
    maxCaracteres: esTexto(tipo) ? String(datos.max_caracteres || "") : "", opciones: opciones.map((o) => String(o.texto)).join("\n"),
    pondera: ponderable && Boolean(datos.pondera), puntajeSi: String(datos.puntaje_si || 0), puntajeNo: String(datos.puntaje_no || 0),
  };
}

/** Hydration: the rows first, then each saved condition once every row exists (`aplicarCondicionesIniciales`). */
function filasIniciales(datos: PreguntaDatos[], reglas: Reglas, operadores: string[]): Fila[] {
  const filas = datos.map((d) => nuevaFila(reglas, d));
  filas.forEach((fila, indice) => {
    const cond = datos[indice].condicion;
    if (!record(cond)) return;
    const orden = Number(cond.orden);
    const referida = orden >= 1 && orden - 1 < indice ? filas[orden - 1] : null;
    fila.ref = referida ? referida.key : null;
    fila.operador = operadores.includes(String(cond.operador)) ? String(cond.operador) : "";
    const opciones = referida ? opcionesCondicion(referida, reglas.conOpciones) : null;
    const valor = String(cond.valor ?? "");
    if (opciones) {
      fila.sel = true;
      fila.valorSelect = opciones.some(([v]) => v === valor) ? valor : "";
    } else fila.valorTexto = valor;
  });
  return filas;
}

/** The native `serializarPreguntas`. */
export function serializar(filas: Fila[]) {
  return filas.map((fila, indice) => {
    const item: Record<string, unknown> = {
      orden: indice + 1, texto: fila.texto.trim(), bloque: fila.bloque.trim(), max_caracteres: fila.maxCaracteres ? Number(fila.maxCaracteres) : null,
      tipo: fila.tipo, obligatoria: fila.obligatoria,
      opciones: lineas(fila.opciones).map((texto) => ({ texto, puntaje: entero(fila.puntajes.get(texto)) })),
      pondera: fila.pondera, puntaje_si: entero(fila.puntajeSi), puntaje_no: entero(fila.puntajeNo), condicion: null,
    };
    if (fila.ref !== null) {
      const orden = filas.findIndex((f) => f.key === fila.ref) + 1;
      item.condicion = { orden, operador: fila.operador, valor: (fila.sel ? fila.valorSelect : fila.valorTexto).trim() };
    }
    return item;
  });
}

/* ---- order announcements: toastr bottom-right, 3 s, hidden at once ---- */

type Aviso = { id: number; message: string; level: "success" | "warning" };

function Avisos({ avisos, quitar }: { avisos: Aviso[]; quitar: (id: number) => void }) {
  if (!avisos.length) return null;
  return createPortal(
    <div id="toast-container" className="toast-bottom-right">
      {[...avisos].reverse().map((a) => <AvisoToast key={a.id} aviso={a} quitar={quitar} />)}
    </div>,
    document.body,
  );
}

function AvisoToast({ aviso, quitar }: { aviso: Aviso; quitar: (id: number) => void }) {
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => {
    timer.current = setTimeout(() => quitar(aviso.id), 3000);
    return () => clearTimeout(timer.current);
  }, [aviso.id, quitar]);
  return (
    <div className={`toast toast-${aviso.level} sisoc-operation-toast`} role="status" aria-live="polite" aria-atomic="true"
      onClick={() => quitar(aviso.id)} onMouseEnter={() => clearTimeout(timer.current)} onMouseLeave={() => quitar(aviso.id)}>
      <div className="toast-message">{aviso.message}</div>
    </div>
  );
}

/* ---- "Exportar JSON" dropdown (Bootstrap markup, opened by the button) ---- */

function Exportar({ url }: { url: string }) {
  const [abierto, setAbierto] = useState(false);
  const raiz = useRef<HTMLDivElement>(null);
  const boton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!abierto) return;
    const fuera = (e: Event) => { if (!raiz.current?.contains(e.target as Node)) setAbierto(false); };
    document.addEventListener("click", fuera);
    return () => document.removeEventListener("click", fuera);
  }, [abierto]);
  const teclas = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape" && abierto) { e.preventDefault(); setAbierto(false); boton.current?.focus(); return; }
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    if (!abierto) { setAbierto(true); return; }
    const items = Array.from(raiz.current?.querySelectorAll<HTMLElement>(".dropdown-item") ?? []);
    const actual = items.indexOf(document.activeElement as HTMLElement);
    const paso = e.key === "ArrowDown" ? 1 : -1;
    items[actual < 0 ? (paso > 0 ? 0 : items.length - 1) : Math.min(items.length - 1, Math.max(0, actual + paso))]?.focus();
  };
  return (
    <div className="dropdown" ref={raiz} onKeyDown={teclas}>
      <button type="button" id="exportar-encuesta-menu" ref={boton} className={`poncho-btn poncho-btn--descarga dropdown-toggle${abierto ? " show" : ""}`}
        aria-expanded={abierto} onClick={() => setAbierto(!abierto)}>
        <i className="fas fa-download me-1" aria-hidden="true"></i> Exportar JSON
      </button>
      <ul className={`dropdown-menu dropdown-menu-end shadow${abierto ? " show" : ""}`} aria-labelledby="exportar-encuesta-menu" {...(abierto ? { "data-bs-popper": "static" } : {})}>
        <li>
          <a href={url} className="dropdown-item py-2">
            <span className="d-block fw-semibold"><i className="fas fa-file-alt me-2" aria-hidden="true"></i>Solo encuesta</span>
            <small className="d-block text-body-secondary">Elegir destinatarios al importar</small>
          </a>
        </li>
        <li><hr className="dropdown-divider" /></li>
        <li>
          <a href={`${url}?incluir_segmentacion=1`} className="dropdown-item py-2">
            <span className="d-block fw-semibold"><i className="fas fa-users me-2" aria-hidden="true"></i>Con segmentación</span>
            <small className="d-block text-body-secondary">Incluye los documentos cargados</small>
          </a>
        </li>
      </ul>
    </div>
  );
}

/* ---- the question rows ---- */

type Arrastre = { fila: number | null; destino: number | null };
type Handlers = {
  cambiar: (key: number, cambios: Partial<Fila>) => void; cambiarTipo: (key: number, tipo: string) => void; puntaje: (key: number, texto: string, valor: string) => void;
  quitar: (key: number) => void; mover: (key: number, destino: number) => void;
  dragStart: (e: DragEvent<HTMLButtonElement>, key: number) => void; dragEnd: (key: number) => void;
  dragOver: (e: DragEvent<HTMLDivElement>, key: number) => void; drop: (e: DragEvent<HTMLDivElement>, key: number) => void;
};

function FilaPregunta({ fila, indice, filas, data, reglas, estado, h, registrar }: {
  fila: Fila; indice: number; filas: Fila[]; data: FormularioData; reglas: Reglas; estado: { arrastrando: number | null; destino: number | null; lado: string };
  h: Handlers; registrar: (key: number, el: HTMLDivElement | null, boton: HTMLButtonElement | null) => void;
}) {
  const conOpciones = reglas.conOpciones.includes(fila.tipo);
  const ponderable = reglas.ponderables.includes(fila.tipo);
  const referida = fila.ref === null ? null : filas.find((f) => f.key === fila.ref) ?? null;
  const fijas = referida ? opcionesCondicion(referida, reglas.conOpciones) : null;
  const detalle = fila.pondera;
  const clase = ["pregunta-row", estado.arrastrando === fila.key ? "pregunta-arrastrando" : "", estado.destino === fila.key ? estado.lado : ""].filter(Boolean).join(" ");
  const botonRef = useRef<HTMLButtonElement>(null);
  const rowRef = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => { registrar(fila.key, rowRef.current, botonRef.current); return () => registrar(fila.key, null, null); }, [fila.key, registrar]);
  const selectRef = (el: HTMLSelectElement | null) => {
    // The native select keeps no selection when its value is set to a choice that does not exist.
    if (el && fila.sel && !(fijas ?? []).some(([v]) => v === fila.valorSelect)) el.selectedIndex = -1;
  };
  const teclas = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
    e.preventDefault();
    h.mover(fila.key, indice + (e.key === "ArrowUp" ? -1 : 1));
  };
  return (
    <div className={clase} ref={rowRef} onDragOver={(e) => h.dragOver(e, fila.key)} onDrop={(e) => h.drop(e, fila.key)}>
      <div className="pregunta-head">
        <div className="pregunta-identificador">
          <button type="button" className="pregunta-arrastrar" draggable="true" aria-label="Mover pregunta" aria-keyshortcuts="ArrowUp ArrowDown"
            title="Arrastrar para mover o usar las flechas del teclado" ref={botonRef} onKeyDown={teclas}
            onDragStart={(e) => h.dragStart(e, fila.key)} onDragEnd={() => h.dragEnd(fila.key)}>
            <i className="fas fa-grip-vertical" aria-hidden="true"></i>
          </button>
          <span className="pregunta-numero">Pregunta {indice + 1}</span>
        </div>
        <button type="button" className="btn-quitar-pregunta poncho-btn" onClick={() => h.quitar(fila.key)}>
          <i className="fas fa-trash-alt"></i> Quitar
        </button>
      </div>
      <div className="mb-2">
        <label>Texto de la pregunta</label>
        <input type="text" className="form-control pregunta-texto" required value={fila.texto} onChange={(e) => h.cambiar(fila.key, { texto: e.target.value })} />
      </div>
      <div className="pregunta-grid">
        <div>
          <label>Tipo de respuesta esperada</label>
          <select className="form-select pregunta-tipo" value={fila.tipo} onChange={(e) => h.cambiarTipo(fila.key, e.target.value)}>
            {data.tipos_pregunta.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
        <div className="pregunta-obligatoria-wrap">
          <div className="form-check form-switch">
            <input type="checkbox" className="form-check-input pregunta-obligatoria" checked={fila.obligatoria} onChange={(e) => h.cambiar(fila.key, { obligatoria: e.target.checked })} />
            <label className="form-check-label">Obligatoria</label>
          </div>
        </div>
      </div>
      <details className="mb-2">
        <summary>Presentación en la PWA</summary>
        <div className="pregunta-grid">
          <div>
            <label>Bloque (opcional)</label>
            <input type="text" className="form-control pregunta-bloque" maxLength={120} value={fila.bloque} onChange={(e) => h.cambiar(fila.key, { bloque: e.target.value })} />
          </div>
          <div className={`pregunta-max-caracteres-wrap${esTexto(fila.tipo) ? "" : " d-none"}`}>
            <label>Máximo de caracteres (opcional)</label>
            <input type="number" className="form-control pregunta-max-caracteres" min="1" max="10000" value={fila.maxCaracteres} onChange={(e) => h.cambiar(fila.key, { maxCaracteres: e.target.value })} />
          </div>
        </div>
      </details>
      <div className={`pregunta-opciones-wrap${conOpciones ? "" : " d-none"}`}>
        <label>Opciones (una por línea, mínimo dos)</label>
        <OpcionesArea value={fila.opciones} onChange={(valor) => h.cambiar(fila.key, { opciones: valor })} />
      </div>
      <div className={`pregunta-pondera-wrap${ponderable ? "" : " d-none"}`}>
        <div className="form-check form-switch">
          <input type="checkbox" className="form-check-input pregunta-pondera" checked={fila.pondera} onChange={(e) => h.cambiar(fila.key, { pondera: e.target.checked })} />
          <label className="form-check-label">¿Pondera para el puntaje total?</label>
        </div>
        <div className={`pregunta-puntaje-detalle${detalle ? "" : " d-none"}`}>
          <div className={`pregunta-puntaje-si-no pregunta-grid${detalle && fila.tipo === "si_no" ? "" : " d-none"}`}>
            <div>
              <label>Puntaje si responde "Sí"</label>
              <input type="number" min="0" className="form-control pregunta-puntaje-si" value={fila.puntajeSi} onChange={(e) => h.cambiar(fila.key, { puntajeSi: e.target.value })} />
            </div>
            <div>
              <label>Puntaje si responde "No"</label>
              <input type="number" min="0" className="form-control pregunta-puntaje-no" value={fila.puntajeNo} onChange={(e) => h.cambiar(fila.key, { puntajeNo: e.target.value })} />
            </div>
          </div>
          <div className={`pregunta-puntaje-opciones-wrap${detalle && conOpciones ? "" : " d-none"}`}>
            <label>Puntaje por opción</label>
            <div className="pregunta-puntaje-opciones-list">
              {detalle && conOpciones && lineas(fila.opciones).map((texto, i) => (
                <div className="puntaje-opcion-row" key={i}>
                  <span className="puntaje-opcion-texto" title={texto}>{texto}</span>
                  <input type="number" min="0" className="form-control puntaje-opcion-input" value={fila.puntajes.get(texto) ?? "0"} onChange={(e) => h.puntaje(fila.key, texto, e.target.value)} />
                </div>
              ))}
            </div>
          </div>
          <small className={`pregunta-puntaje-escala-nota switch-help${detalle && fila.tipo === "escala" ? "" : " d-none"}`}>
            El puntaje de esta pregunta es directamente el número (1 a 10) que responda la persona.
          </small>
        </div>
      </div>
      <div className={`pregunta-condicion-wrap${indice > 0 ? "" : " d-none"}`}>
        <div className="cond-label"><i className="fas fa-code-branch"></i> Mostrar esta pregunta solo si...</div>
        <div className="cond-grid">
          <select className="form-select pregunta-condicion-referencia" value={fila.ref === null ? "" : String(filas.findIndex((f) => f.key === fila.ref) + 1)}
            onChange={(e) => h.cambiar(fila.key, { ref: e.target.value ? (filas[Number(e.target.value) - 1]?.key ?? null) : null })}>
            <option value="">(siempre visible)</option>
            {filas.slice(0, indice).map((anterior, i) => <option key={anterior.key} value={String(i + 1)}>{anterior.texto.trim() || `Pregunta ${i + 1}`}</option>)}
          </select>
          <select className="form-select pregunta-condicion-operador" value={fila.operador} onChange={(e) => h.cambiar(fila.key, { operador: e.target.value })}>
            {fila.operador === "" && <option value="" hidden></option>}
            {data.operadores_condicion.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          <div>
            <input type="text" className={`form-control pregunta-condicion-valor${fila.sel ? " d-none" : ""}`} placeholder="Valor esperado" value={fila.valorTexto}
              onChange={(e) => h.cambiar(fila.key, { valorTexto: e.target.value })} />
            <select className={`form-select pregunta-condicion-valor-select${fila.sel ? "" : " d-none"}`} ref={selectRef} value={fila.valorSelect}
              onChange={(e) => h.cambiar(fila.key, { valorSelect: e.target.value })}>
              {fila.sel && (fijas ?? []).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * The native editor fills the options textarea through its `value`, so its text content stays empty; a controlled React
 * textarea would also write the options as its text content. Keeping it uncontrolled leaves the DOM as the native one.
 */
function OpcionesArea({ value, onChange }: { value: string; onChange: (valor: string) => void }) {
  const area = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => { if (area.current && area.current.value !== value) area.current.value = value; }, [value]);
  return <textarea ref={area} className="form-control pregunta-opciones" rows={3} onChange={(e) => onChange(e.target.value)}></textarea>;
}

/* ---- the form ---- */

type Campos = { titulo: string; descripcion: string; es_anonima: boolean; modalidad: string; es_recurrente: boolean; intervalo_recordatorio_dias: string; duracion_ronda_dias: string; intervalo_recurrencia_dias: string };

function Error1({ campo }: { campo: Campo }) {
  return campo.errors.length > 0 ? <div className="invalid-feedback d-block">{campo.errors[0]}</div> : null;
}

function describe(campo: Campo) {
  return { ...(campo.invalid ? { "aria-invalid": true as const } : {}), ...(campo.describedby ? { "aria-describedby": campo.describedby } : {}) };
}

export function FormularioContent({ data }: { data: FormularioData }) {
  const [actual, setActual] = useState(data);
  const [version, setVersion] = useState(0);
  return <FormularioEditor key={version} data={actual} rechazado={(result) => { setActual(result); setVersion((v) => v + 1); resetAfterRejectedPost(); }} />;
}

function FormularioEditor({ data: actual, rechazado }: { data: FormularioData; rechazado: (result: FormularioData) => void }) {
  const [reglas] = useState<Reglas>(() => ({
    conOpciones: csv(actual.tipos_con_opciones), ponderables: csv(actual.tipos_ponderables),
    tiposDefault: actual.tipos_pregunta[0]?.[0] ?? "", operadorDefault: actual.operadores_condicion[0]?.[0] ?? "",
  }));
  const f = actual.fields;
  const [campos, setCampos] = useState<Campos>(() => ({
    titulo: String(f.titulo.value), descripcion: String(f.descripcion.value), es_anonima: f.es_anonima.value === true, modalidad: String(f.modalidad.value),
    es_recurrente: f.es_recurrente.value === true, intervalo_recordatorio_dias: String(f.intervalo_recordatorio_dias.value),
    duracion_ronda_dias: String(f.duracion_ronda_dias.value), intervalo_recurrencia_dias: String(f.intervalo_recurrencia_dias.value),
  }));
  const [filas, setFilas] = useState<Fila[]>(() => filasIniciales(actual.preguntas, reglas, actual.operadores_condicion.map(([v]) => v)));
  const filasRef = useRef(filas);
  useLayoutEffect(() => { filasRef.current = filas; }, [filas]);
  const [busy, setBusy] = useState(false);
  const [mensajes, setMensajes] = useState<Message[]>(actual.messages);
  const [avisos, setAvisos] = useState<Aviso[]>([]);
  const [modal, setModal] = useState<{ key: number; aviso: string } | null>(null);
  const [arrastre, setArrastreEstado] = useState<{ arrastrando: number | null; destino: number | null; lado: string }>({ arrastrando: null, destino: null, lado: "" });
  const drag = useRef<Arrastre>({ fila: null, destino: null });
  const elementos = useRef(new Map<number, { fila: HTMLDivElement | null; boton: HTMLButtonElement | null }>());
  const pendiente = useRef<{ tops: Map<number, number>; x: number; y: number; foco: number | null } | null>(null);
  const foco = useRef<number | "primera" | null>(null);
  const scroll = useRef<number | null>(null);
  const velocidad = useRef(0);
  const agregar = useRef<HTMLButtonElement>(null);
  const avisoId = useRef(0);

  const aplicar = (cambio: (previas: Fila[]) => Fila[]) => setFilas((previas) => normalizar(cambio(previas), reglas.conOpciones));
  // The native toastr keeps one announcement at a time: a new one replaces the previous.
  const anunciar = (message: string, level: "success" | "warning") => setAvisos([{ id: ++avisoId.current, message, level }]);
  const quitarAviso = useCallback((id: number) => setAvisos((a) => a.filter((x) => x.id !== id)), []);

  const cambiar = (key: number, cambios: Partial<Fila>) => aplicar((previas) => previas.map((fila) => (fila.key === key ? { ...fila, ...cambios } : fila)));
  const cambiarTipo = (key: number, tipo: string) => aplicar((previas) => previas.map((fila) => {
    if (fila.key !== key) return fila;
    return { ...fila, tipo, maxCaracteres: esTexto(tipo) ? fila.maxCaracteres : "", pondera: reglas.ponderables.includes(tipo) ? fila.pondera : false };
  }));
  const puntaje = (key: number, texto: string, valor: string) => aplicar((previas) => previas.map((fila) => (fila.key === key ? { ...fila, puntajes: new Map(fila.puntajes).set(texto, valor) } : fila)));

  const registrar = useCallback((key: number, fila: HTMLDivElement | null, boton: HTMLButtonElement | null) => {
    if (fila) elementos.current.set(key, { fila, boton });
    else elementos.current.delete(key);
  }, []);

  const detenerScroll = () => {
    if (scroll.current !== null) window.clearInterval(scroll.current);
    scroll.current = null;
    velocidad.current = 0;
  };
  const limpiarDestino = () => { drag.current.destino = null; setArrastreEstado((e) => ({ ...e, destino: null, lado: "" })); };

  const mover = (key: number, destino: number, conFoco = true) => {
    const previas = filasRef.current;
    const origen = previas.findIndex((x) => x.key === key);
    if (origen < 0 || destino < 0 || destino >= previas.length || origen === destino) return;
    const nuevas = [...previas];
    const [fila] = nuevas.splice(origen, 1);
    nuevas.splice(destino, 0, fila);
    const invalido = nuevas.some((actualFila, indice) => actualFila.ref !== null && nuevas.findIndex((x) => x.key === actualFila.ref) >= indice);
    if (invalido) {
      anunciar("No se puede mover: una pregunta condicional debe quedar después de la pregunta de la que depende.", "warning");
      return;
    }
    const tops = new Map<number, number>();
    nuevas.forEach((x) => { const el = elementos.current.get(x.key)?.fila; if (el) tops.set(x.key, el.getBoundingClientRect().top); });
    pendiente.current = { tops, x: window.scrollX, y: window.scrollY, foco: conFoco ? key : null };
    setFilas(normalizar(nuevas, reglas.conOpciones));
    anunciar(`Pregunta movida a la posición ${destino + 1}. Guardá la encuesta para conservar el orden.`, "success");
  };

  useLayoutEffect(() => {
    const p = pendiente.current;
    if (!p) return;
    pendiente.current = null;
    if (window.scrollX !== p.x || window.scrollY !== p.y) window.scrollTo({ left: p.x, top: p.y, behavior: "instant" });
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      filas.forEach((x) => {
        const el = elementos.current.get(x.key)?.fila;
        const desplazamiento = (p.tops.get(x.key) ?? 0) - (el?.getBoundingClientRect().top ?? 0);
        if (el && desplazamiento && el.animate) el.animate([{ transform: `translateY(${desplazamiento}px)` }, { transform: "translateY(0)" }], { duration: 180, easing: "ease-out" });
      });
    }
    if (p.foco !== null) elementos.current.get(p.foco)?.boton?.focus({ preventScroll: true });
  }, [filas]);

  const soltar = (destino: number) => {
    const indice = filasRef.current.findIndex((x) => x.key === destino);
    limpiarDestino();
    if (drag.current.fila !== null) mover(drag.current.fila, indice, false);
  };

  useEffect(() => {
    const over = (event: globalThis.DragEvent) => {
      if (drag.current.fila === null) return;
      event.preventDefault();
      const margen = Math.min(100, window.innerHeight / 4);
      const distancia = event.clientY < margen ? event.clientY - margen : event.clientY > window.innerHeight - margen ? event.clientY - window.innerHeight + margen : 0;
      if (!distancia || event.clientX < 0 || event.clientX > window.innerWidth) { detenerScroll(); return; }
      velocidad.current = Math.max(-18, Math.min(18, (distancia / margen) * 18));
      if (scroll.current === null) {
        scroll.current = window.setInterval(() => {
          if (drag.current.fila === null) { detenerScroll(); return; }
          window.scrollBy({ top: velocidad.current, left: 0, behavior: "instant" });
        }, 16);
      }
    };
    const drop = (event: globalThis.DragEvent) => {
      detenerScroll();
      const contenedor = document.getElementById("preguntas-container");
      if (drag.current.fila !== null && drag.current.destino !== null && contenedor?.contains(event.target as Node)) {
        event.preventDefault();
        soltar(drag.current.destino);
      }
      limpiarDestino();
    };
    const leave = (event: globalThis.DragEvent) => { if (!event.relatedTarget) detenerScroll(); };
    document.addEventListener("dragover", over);
    document.addEventListener("drop", drop);
    document.addEventListener("dragend", detenerScroll);
    document.addEventListener("dragleave", leave);
    return () => {
      document.removeEventListener("dragover", over);
      document.removeEventListener("drop", drop);
      document.removeEventListener("dragend", detenerScroll);
      document.removeEventListener("dragleave", leave);
      detenerScroll();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- the handlers read refs only.
  }, []);

  const handlers: Handlers = {
    cambiar, cambiarTipo, puntaje, mover: (key, destino) => mover(key, destino),
    quitar: (key) => {
      const indice = filasRef.current.findIndex((x) => x.key === key);
      let aviso = `¿Quitar la pregunta ${indice + 1}? Se eliminarán su texto, opciones y configuración. El cambio se aplicará al guardar la encuesta.`;
      if (filasRef.current.some((otra) => otra.ref === key)) aviso += " Las preguntas que dependen de esta quedarán siempre visibles.";
      setModal({ key, aviso });
    },
    dragStart: (e, key) => {
      drag.current.fila = key;
      e.dataTransfer.effectAllowed = "move";
      const indice = filasRef.current.findIndex((x) => x.key === key);
      e.dataTransfer.setData("text/plain", `Pregunta ${indice + 1}`);
      const el = elementos.current.get(key)?.fila;
      if (el) {
        const rect = el.getBoundingClientRect();
        e.dataTransfer.setDragImage(el, e.clientX - rect.left, e.clientY - rect.top);
      }
      // The browser captures the whole card first; then the origin is dimmed.
      requestAnimationFrame(() => { if (drag.current.fila === key) setArrastreEstado((s) => ({ ...s, arrastrando: key })); });
    },
    dragEnd: () => {
      detenerScroll();
      drag.current.fila = null;
      setArrastreEstado({ arrastrando: null, destino: null, lado: "" });
      drag.current.destino = null;
    },
    dragOver: (e, key) => {
      if (drag.current.fila === null) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      // The gap changes the geometry under the cursor: keep it until another card is entered.
      if (key === drag.current.destino || key === drag.current.fila) return;
      drag.current.destino = key;
      const todas = filasRef.current;
      const lado = todas.findIndex((x) => x.key === drag.current.fila) < todas.findIndex((x) => x.key === key) ? "pregunta-destino-despues" : "pregunta-destino-antes";
      setArrastreEstado((s) => ({ ...s, destino: key, lado }));
    },
    drop: (e, key) => {
      if (drag.current.fila === null) return;
      e.preventDefault();
      detenerScroll();
      soltar(key);
    },
  };

  const cerrarModal = (quitada: boolean) => {
    const que = modal;
    if (!que) return;
    foco.current = quitada ? "primera" : que.key;
    if (quitada) aplicar((previas) => previas.filter((x) => x.key !== que.key));
    setModal(null);
  };
  useEffect(() => {
    if (modal !== null || foco.current === null) return;
    const destino = foco.current;
    foco.current = null;
    if (destino === "primera") (elementos.current.get(filasRef.current[0]?.key ?? -1)?.boton ?? agregar.current)?.focus();
    else elementos.current.get(destino)?.fila?.querySelector<HTMLElement>(".btn-quitar-pregunta")?.focus();
  }, [modal, filas]);

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const datos = new FormData(e.currentTarget);
    datos.set("preguntas_json", JSON.stringify(serializar(filas)));
    const body = new URLSearchParams(datos as unknown as Record<string, string>);
    setBusy(true);
    try {
      const { data: result, status } = await webClient.post(actual.id === null ? "web/encuestas/crear/" : `web/encuestas/${actual.id}/editar/`, body, { validateStatus: (s) => accepted(s) || s === 400 });
      if (status === 200 && record(result) && result.ok === true && internal(result.redirect)) { window.location.assign(result.redirect); return; }
      if (status === 400 && formularioValid(result)) {
        rechazado(result);
        return;
      }
    } catch { /* uncertain outcome: reported below, never retried */ }
    setMensajes([{ message: "No se pudo completar la operación.", level: "error" }]);
    setBusy(false);
  };

  const editando = actual.id !== null;
  const postergable = campos.modalidad === "postergable";
  const hechas = <T,>(clave: keyof Campos, valor: T) => setCampos((c) => ({ ...c, [clave]: valor }));
  const motivo = actual.motivo_rechazo;
  const estadoArrastre = { arrastrando: arrastre.arrastrando, destino: arrastre.destino, lado: arrastre.lado };
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/encuestaForm.css" />
      <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
      <div className="encuesta-editor" data-tipos-con-opciones={actual.tipos_con_opciones} data-tipos-ponderables={actual.tipos_ponderables}>
        {motivo && (
          <div className="alert alert-warning mb-3" role="note">
            <h2 className="h6 mb-2"><i className="fas fa-comment-alt me-1" aria-hidden="true"></i>{motivo.estado === "borrador" ? "Cambios solicitados" : "Motivo del último rechazo"}</h2>
            <p className="mb-2 text-break">{motivo.texto.split(/\r\n|\r|\n/).map((line, i, all) => <Fragment key={i}>{line}{i < all.length - 1 && <br />}</Fragment>)}</p>
            <p className="small mb-0">{motivo.usuario} · {motivo.fecha}</p>
            {motivo.estado === "borrador" && <p className="small mt-2 mb-0">Corregí la encuesta, guardá los cambios y volvé a solicitar la publicación desde el listado.</p>}
          </div>
        )}
        <div className="d-flex justify-content-between align-items-start mb-3">
          <h2 className="mb-0">{editando ? "Editar encuesta" : "Generar encuesta"}</h2>
          <div className="d-flex flex-wrap align-items-center gap-2">
            {editando && actual.urls && <Exportar url={actual.urls.exportar} />}
          </div>
        </div>
        <form method="post" id="encuesta-form" noValidate onSubmit={(e) => void submit(e)}>
          {actual.non_field_errors.length > 0 && <div className="alert alert-danger"><ul className="errorlist nonfield">{actual.non_field_errors.map((m, i) => <li key={i}>{m}</li>)}</ul></div>}
          <div className="editor-panel">
            <div className="panel-label"><span className="panel-label-title"><i className="fas fa-sliders-h"></i> Datos generales</span></div>
            <div className="panel-body">
              <div className="mb-3">
                <label htmlFor="id_titulo">Título <span className="text-danger">*</span></label>
                <input type="text" name="titulo" className="form-control" maxLength={200} required id="id_titulo" {...describe(f.titulo)} value={campos.titulo} onChange={(e) => hechas("titulo", e.target.value)} />
                <Error1 campo={f.titulo} />
              </div>
              <div className="mb-0">
                <label htmlFor="id_descripcion">Descripción</label>
                <textarea name="descripcion" cols={40} rows={3} className="form-control" id="id_descripcion" {...describe(f.descripcion)} value={campos.descripcion} onChange={(e) => hechas("descripcion", e.target.value)}></textarea>
                <Error1 campo={f.descripcion} />
              </div>
              <div className="options-row">
                <div className="option-item">
                  <div className="form-check form-switch">
                    <input type="checkbox" name="es_anonima" className="form-check-input" role="switch" id="id_es_anonima" {...describe(f.es_anonima)} checked={campos.es_anonima} onChange={(e) => hechas("es_anonima", e.target.checked)} />
                    <label className="form-check-label" htmlFor="id_es_anonima">Anónima</label>
                  </div>
                  <small className="switch-help">No se vincula el contenido a la identidad de quien responde.</small>
                </div>
                <div className="option-item">
                  <label htmlFor="id_modalidad">Modalidad de respuesta</label>
                  <select name="modalidad" className="form-select" id="id_modalidad" {...describe(f.modalidad)} value={campos.modalidad} onChange={(e) => hechas("modalidad", e.target.value)}>
                    <option value="obligatoria">Obligatoria</option>
                    <option value="opcional">Opcional</option>
                    <option value="postergable">Postergable</option>
                  </select>
                  <small className="switch-help">Obligatoria: bloquea el sistema. Opcional: permite no responder. Postergable: vuelve a recordarse.</small>
                  <Error1 campo={f.modalidad} />
                </div>
                <div className="option-item">
                  <div className="form-check form-switch">
                    <input type="checkbox" name="es_recurrente" className="form-check-input" role="switch" id="id_es_recurrente" {...describe(f.es_recurrente)} checked={campos.es_recurrente} onChange={(e) => hechas("es_recurrente", e.target.checked)} />
                    <label className="form-check-label" htmlFor="id_es_recurrente">Recurrente</label>
                  </div>
                  <small className="switch-help">Abre una ronda nueva cada N días, en vez de una única vez.</small>
                </div>
              </div>
              <div className="subfields">
                <div className="field-col" id="recordatorio-field" style={postergable ? undefined : { display: "none" }}>
                  <label htmlFor="id_intervalo_recordatorio_dias">Intervalo de recordatorio (días)</label>
                  <input type="number" name="intervalo_recordatorio_dias" className="form-control" min="1" id="id_intervalo_recordatorio_dias" disabled={!postergable} required={postergable}
                    {...describe(f.intervalo_recordatorio_dias)} value={campos.intervalo_recordatorio_dias} onChange={(e) => hechas("intervalo_recordatorio_dias", e.target.value)} />
                  <small className="form-text d-block">Solo aplica si la encuesta es postergable.</small>
                  <Error1 campo={f.intervalo_recordatorio_dias} />
                </div>
                <div className="field-col">
                  <label htmlFor="id_duracion_ronda_dias">Duración de la ronda (días)</label>
                  <input type="number" name="duracion_ronda_dias" className="form-control" min="0" required id="id_duracion_ronda_dias" {...describe(f.duracion_ronda_dias)} value={campos.duracion_ronda_dias} onChange={(e) => hechas("duracion_ronda_dias", e.target.value)} />
                  <Error1 campo={f.duracion_ronda_dias} />
                </div>
                <div className="field-col" id="recurrencia-field" style={campos.es_recurrente ? undefined : { display: "none" }}>
                  <label htmlFor="id_intervalo_recurrencia_dias">Intervalo de recurrencia (días)</label>
                  <input type="number" name="intervalo_recurrencia_dias" className="form-control" min="0" id="id_intervalo_recurrencia_dias" {...describe(f.intervalo_recurrencia_dias)} value={campos.intervalo_recurrencia_dias} onChange={(e) => hechas("intervalo_recurrencia_dias", e.target.value)} />
                  <Error1 campo={f.intervalo_recurrencia_dias} />
                </div>
              </div>
            </div>
          </div>
          <div className="editor-panel">
            <div className="panel-label"><span className="panel-label-title"><i className="fas fa-question-circle"></i> Preguntas</span></div>
            <div className="panel-body">
              <div className="preguntas-toolbar">
                <span className="pregunta-count">
                  <b id="preguntas-cantidad">{filas.length}</b> preguntas agregadas{" "}
                  <span className="preguntas-arrastre-ayuda">- Modificá el orden de las preguntas arrastrando <i className="fas fa-grip-vertical" aria-hidden="true"></i></span>
                </span>
              </div>
              <div id="preguntas-container">
                {filas.map((fila, indice) => (
                  <FilaPregunta key={fila.key} fila={fila} indice={indice} filas={filas} data={actual} reglas={reglas} estado={estadoArrastre} h={handlers} registrar={registrar} />
                ))}
              </div>
              <p id="preguntas-vacio-msg" className={`switch-help mb-0${filas.length > 0 ? " d-none" : ""}`}>Todavía no agregaste preguntas.</p>
              <div className="mt-3 d-flex justify-content-end">
                <button type="button" id="agregar-pregunta" ref={agregar} className="poncho-btn poncho-btn--cta" onClick={() => aplicar((previas) => [...previas, nuevaFila(reglas)])}>
                  <i className="fas fa-plus"></i> Agregar pregunta
                </button>
              </div>
            </div>
          </div>
          <input type="hidden" name="preguntas_json" id="preguntas_json" />
          <div className="editor-actions">
            <a href="/encuestas/" className="poncho-btn poncho-btn--neutro">Cancelar</a>
            <button type="submit" className="poncho-btn poncho-btn--cta" disabled={busy}><i className="fas fa-save me-1"></i> Guardar encuesta</button>
          </div>
        </form>
        {modal && <QuitarModal aviso={modal.aviso} cerrar={cerrarModal} />}
      </div>
      <Avisos avisos={avisos} quitar={quitarAviso} />
      <NativeToasts messages={mensajes} />
    </>
  );
}

function QuitarModal({ aviso, cerrar }: { aviso: string; cerrar: (quitada: boolean) => void }) {
  const cancelar = useRef<HTMLButtonElement>(null);
  useEffect(() => { const t = setTimeout(() => cancelar.current?.focus(), 0); return () => clearTimeout(t); }, []);
  return (
    <NativeModal id="quitar-pregunta-modal" title="Quitar pregunta" close={() => cerrar(false)} size=" modal-dialog-centered">
      <div className="modal-content">
        <div className="modal-header">
          <h2 className="modal-title fs-5" id="quitar-pregunta-titulo">Quitar pregunta</h2>
          <button type="button" className="btn-close" aria-label="Cerrar" onClick={() => cerrar(false)}></button>
        </div>
        <div className="modal-body"><p id="quitar-pregunta-advertencia" className="mb-0">{aviso}</p></div>
        <div className="modal-footer">
          <button type="button" id="cancelar-quitar-pregunta" ref={cancelar} className="poncho-btn poncho-btn--neutro" onClick={() => cerrar(false)}>Cancelar</button>
          <button type="button" id="confirmar-quitar-pregunta" className="btn-quitar-pregunta poncho-btn" onClick={() => cerrar(true)}>Quitar pregunta</button>
        </div>
      </div>
    </NativeModal>
  );
}

const pageValid = (v: unknown): v is FormularioData | { redirect: string } => formularioValid(v) || redirectValid(v);

function FormularioPage({ id }: { id: string | null }) {
  const endpoint = id === null ? "web/encuestas/crear/" : `web/encuestas/${id}/editar/`;
  const [state] = useMainResource(endpoint, pageValid);
  useEffect(() => {
    if (state.status === "ready" && redirectValid(state.data)) window.location.replace(state.data.redirect);
  }, [state]);
  return renderMain(state, "Cargando encuesta…", (data) => {
    if (!formularioValid(data)) return { title: "Encuesta", breadcrumb: <Breadcrumb items={[]} />, content: null };
    return {
      title: data.id === null ? "Generar encuesta" : "Editar encuesta", activePath: "/encuestas/",
      breadcrumb: <Breadcrumb items={[]} />,
      content: <FormularioContent data={data} />,
    };
  });
}

export const encuestasFormularioRoute: RouteDefinition<{ id: string | null }> = {
  name: "encuestas-formulario",
  match(pathname) {
    if (pathname === "/encuestas/crear/") return { id: null };
    const found = /^\/encuestas\/([0-9]+)\/editar\/$/.exec(pathname);
    return found ? { id: found[1] } : null;
  },
  render: ({ id }) => <FormularioPage id={id} />,
};
