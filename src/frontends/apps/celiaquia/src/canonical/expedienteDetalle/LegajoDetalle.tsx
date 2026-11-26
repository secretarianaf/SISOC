import { useEffect, useState } from "react";
import { internal } from "../transport";
import { formatDate, getNative } from "./native";
import type { Archivo, Legajo, Subsanacion } from "./types";

export type LegajoDialog = "rechazar" | "subsanar" | "corregir" | "archivo" | "respuesta" | "renaper-respuesta" | "renaper" | "editar" | "comentario";
export type LegajoHandlers = {
  open: (kind: LegajoDialog, legajo: Legajo, campo?: string) => void;
  aprobar: (legajo: Legajo) => void;
  confirmarSubsanacion: (legajo: Legajo) => void;
  disabled: boolean;
};

type Comentario = {
  usuario?: string; fecha?: string; texto?: string; archivo_url?: string; tiene_archivo?: boolean;
  es_provincia?: boolean; es_interno?: boolean; publicado_en?: string;
  es_comentario_tecnico?: boolean; tipo_documento_display?: string; tiene_observaciones?: boolean;
};

/** Stored-file URLs: same-origin paths, or http(s) when media lives in remote storage. */
export function safeHref(url: string | null) {
  if (url && /^https?:\/\//i.test(url)) return url;
  try { return url ? internal(url) : undefined; } catch { return undefined; }
}

function FileLink({ archivo }: { archivo: Archivo }) {
  return <li><a href={safeHref(archivo.url)} target="_blank" rel="noopener noreferrer">{archivo.nombre}</a>
    {" "}<span className="ed-chip">{archivo.origen}</span>{archivo.observacion && <span className="ed-chip">{archivo.observacion}</span>}
    {archivo.descripcion && ` — ${archivo.descripcion}`} <small>({formatDate(archivo.creado_en, true)}{archivo.usuario && ` · ${archivo.usuario}`})</small></li>;
}

function SubsanacionItem({ sub }: { sub: Subsanacion }) {
  return <li className="ed-card">
    <strong>#{sub.id}</strong> <span className="ed-chip">{sub.estado_display}</span>
    <div><small>Solicitada{sub.solicitada_por && ` por ${sub.solicitada_por}`}{sub.solicitada_en && ` el ${formatDate(sub.solicitada_en, true)}`}</small></div>
    {sub.respondida_en && <div><small>Respondida{sub.respondida_por && ` por ${sub.respondida_por}`} el {formatDate(sub.respondida_en, true)}</small></div>}
    <ul>{sub.observaciones.map((obs) => <li key={obs.id}><strong>{obs.tipo}</strong>{obs.detalle && `: ${obs.detalle}`}</li>)}</ul>
    {sub.archivos.length > 0 && <ul>{sub.archivos.map((archivo) => <FileLink key={archivo.id} archivo={archivo} />)}</ul>}
  </li>;
}

function Comentarios({ legajo, onAdd, disabled }: { legajo: Legajo; onAdd?: () => void; disabled: boolean }) {
  const [items, setItems] = useState<Comentario[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    getNative(legajo.actions.comentarios).then((data) => setItems((data.comentarios as Comentario[]) ?? [])).catch(() => setError("No se pudieron cargar los comentarios."));
  }, [legajo.actions.comentarios]);
  return <section aria-label={`Comentarios técnicos de ${legajo.nombre} ${legajo.apellido}`}>
    <div className="ed-row"><h4>Comentarios Técnicos</h4>{onAdd && <button type="button" onClick={onAdd} disabled={disabled}>Agregar</button>}</div>
    {error ? <p role="alert">{error}</p> : items === null ? <p role="status">Cargando comentarios...</p> : items.length === 0 ? <p>Sin comentarios técnicos</p>
      : <ul className="ed-list">{items.map((c, index) => <li key={index} className={c.es_interno ? "ed-card ed-internal" : "ed-card"}>
        <small>{c.usuario} <span className="ed-chip">{c.es_provincia ? "Provincia" : "Técnico"}</span>
          {c.es_interno ? <span className="ed-chip">Interno</span> : c.publicado_en ? <span className="ed-chip" title={`Publicado a la provincia el ${c.publicado_en}`}>Publicado</span> : null}
          {c.es_comentario_tecnico && <> <span className="ed-chip">{c.tipo_documento_display}</span> <span className="ed-chip">{c.tiene_observaciones ? "Con observaciones" : "Sin observaciones"}</span></>}
          {" "}· {c.fecha}</small>
        {!(c.es_comentario_tecnico && c.tiene_observaciones === false) && <p>{c.texto}</p>}
        {c.tiene_archivo && <a href={safeHref(c.archivo_url ?? null)} target="_blank" rel="noopener noreferrer">Ver archivo</a>}
      </li>)}</ul>}
  </section>;
}

/** Expanded legajo detail: same three columns and actions as the native collapse row. */
export function LegajoDetalle({ legajo, isProvincial, handlers }: { legajo: Legajo; isProvincial: boolean; handlers: LegajoHandlers }) {
  const { actions } = legajo;
  const activa = legajo.subsanacion_activa;
  const { open, disabled } = handlers;
  const hasRenaperResponse = Boolean(legajo.renaper.respuesta_label);
  return <div className="ed-detail">
    <div className="ed-detail-grid">
      <section>
        <h4>{legajo.nombre} {legajo.apellido}</h4>
        <p><small>CUIL: {legajo.documento}</small></p>
        <p>Estado: <span className={`ed-chip ed-state-${legajo.estado.toLowerCase()}`}>{legajo.estado}</span></p>
      </section>
      <section>
        {legajo.observacion.texto ? <><p><small>{legajo.observacion.titulo || "Observación técnica"}:</small></p><ul className="ed-box">{legajo.observacion.items.map((item, i) => <li key={i}>{item}</li>)}</ul></>
          : <><p><small>{isProvincial ? "Observación (subsanación):" : "Comentario enviado a provincia:"}</small></p><p>-</p></>}
        {legajo.renaper.comentario && <><p><small>{isProvincial ? "Respuesta provincia:" : "Respuesta de provincia:"}</small></p><p className="ed-box">{legajo.renaper.comentario}</p></>}
      </section>
      <section>
        <p><span className="ed-chip">{legajo.es_doble_rol ? "Beneficiario y Responsable" : legajo.tipo_legajo}</span> <small>Archivos requeridos</small></p>
        {legajo.archivos.map((archivo) => <div key={archivo.campo} className="ed-file">
          <strong>{archivo.label}</strong>
          {archivo.url ? <p className="ed-ok">Archivo cargado <a href={safeHref(archivo.url)} target="_blank" rel="noopener noreferrer">Ver</a></p> : <p className="ed-pending">Pendiente de carga</p>}
          {actions.subir_archivo && <button type="button" disabled={disabled} onClick={() => open("archivo", legajo, archivo.campo)} aria-label={`${archivo.url ? "Editar" : "Subir"} ${archivo.label} de ${legajo.nombre} ${legajo.apellido}`}>{archivo.url ? "Editar" : "Subir"}</button>}
        </div>)}
        {activa && <div className="ed-box ed-warn">
          <strong>Subsanación solicitada</strong>
          <p><small>{activa.solicitada_por && `Por ${activa.solicitada_por}`}{activa.solicitada_en && ` el ${formatDate(activa.solicitada_en, true)}`}</small></p>
          <ul>{activa.observaciones.map((obs) => <li key={obs.id}><strong>{obs.tipo}</strong>{obs.detalle && `: ${obs.detalle}`}</li>)}</ul>
          {activa.archivos_de_nacion.length > 0 && <><strong>Documentación complementaria</strong><p><small>Adjuntada por Nación junto con la solicitud, como complemento de las observaciones.</small></p><ul>{activa.archivos_de_nacion.map((a) => <FileLink key={a.id} archivo={a} />)}</ul></>}
          <strong>Archivos corregidos (evidencia nueva)</strong>
          <p><small>Los documentos originales se conservan; los corregidos se agregan sin reemplazarlos.</small></p>
          {activa.archivos_de_provincia.length ? <ul>{activa.archivos_de_provincia.map((a) => <FileLink key={a.id} archivo={a} />)}</ul> : <p><small>Sin archivos de respuesta todavía.</small></p>}
          {actions.responder_subsanacion && <button type="button" disabled={disabled} onClick={() => open("respuesta", legajo)}>Adjuntar archivos de subsanación</button>}
        </div>}
        {legajo.subsanaciones_historial.length > 0 && <details><summary>Historial de subsanaciones</summary><ul className="ed-list">{legajo.subsanaciones_historial.map((sub) => <SubsanacionItem key={sub.id} sub={sub} />)}</ul></details>}
        {legajo.es_responsable && <div><small>Hijos a cargo en este expediente</small><p>{legajo.hijos_a_cargo.length ? legajo.hijos_a_cargo.map((h) => <span key={h.id} className="ed-chip">{h.apellido}, {h.nombre} ({h.documento})</span>) : <small>No se registraron hijos en este expediente.</small>}</p></div>}
        {legajo.comentarios_visibles && <Comentarios legajo={legajo} disabled={disabled} onAdd={actions.agregar_comentario ? () => open("comentario", legajo) : undefined} />}
        {actions.confirmar_subsanacion && <button type="button" className="ed-primary" disabled={disabled} onClick={() => handlers.confirmarSubsanacion(legajo)}>Confirmar subsanación</button>}
        {(hasRenaperResponse || legajo.renaper.pendiente) && <div className="ed-box ed-warn">
          <p><small>{hasRenaperResponse ? legajo.renaper.respuesta_label : legajo.renaper.solicitud_label}</small></p>
          {legajo.renaper.pendiente && <p><small>Pendiente de respuesta</small></p>}
          {legajo.renaper.comentario && <p><strong>Comentario:</strong> {legajo.renaper.comentario}</p>}
          {legajo.renaper.archivo_url && <a href={safeHref(legajo.renaper.archivo_url)} target="_blank" rel="noopener noreferrer">Ver archivo</a>}
          {actions.responder_renaper && <button type="button" disabled={disabled} onClick={() => open("renaper-respuesta", legajo)}>{hasRenaperResponse ? "Editar respuesta" : "Responder"}</button>}
        </div>}
      </section>
    </div>
    {(actions.revisar || actions.corregir_evaluacion) && <div className="ed-toolbar" role="toolbar" aria-label={`Acciones del legajo ${legajo.nombre} ${legajo.apellido}`}>
      {actions.validar_renaper && <button type="button" disabled={disabled} onClick={() => open("renaper", legajo)}>Validar Renaper</button>}
      {actions.revisar && <>
        <button type="button" disabled={disabled} onClick={() => handlers.aprobar(legajo)}>Aprobar</button>
        <button type="button" disabled={disabled} onClick={() => open("subsanar", legajo)}>Subsanar</button>
        <button type="button" disabled={disabled} onClick={() => open("rechazar", legajo)}>Rechazar</button>
      </>}
      {actions.corregir_evaluacion && <button type="button" disabled={disabled} onClick={() => open("corregir", legajo)} title="Corregir resultado de la evaluación final">Corregir evaluación</button>}
    </div>}
  </div>;
}
