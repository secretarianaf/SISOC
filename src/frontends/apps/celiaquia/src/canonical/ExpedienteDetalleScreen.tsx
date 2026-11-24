import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { internal, loadProjection } from "./transport";
import {
  ArchivoDialog, ComentarioDialog, CorregirDialog, CruceDialog, EditarLegajoDialog, FamiliasDialog, HistorialDialog,
  MotivoDialog, RenaperDialog, RespuestaRenaperDialog, RespuestaSubsanacionDialog, type Run,
} from "./expedienteDetalle/Dialogs";
import { LegajoDetalle, safeHref, type LegajoDialog } from "./expedienteDetalle/LegajoDetalle";
import { RegistrosErroneos } from "./expedienteDetalle/RegistrosErroneos";
import { formatDate, postNative, type NativeResult } from "./expedienteDetalle/native";
import { SearchableSelect } from "./expedienteDetalle/SearchableSelect";
import { clearTimedAlert, expedienteIdFromPath, queueTimedAlert, readTimedAlert } from "./expedienteDetalle/timedAlert";
import type { Detalle, Legajo, Notice } from "./expedienteDetalle/types";

type Dialog =
  | { kind: LegajoDialog; legajo: Legajo; campo?: string }
  | { kind: "cruce"; url: string }
  | { kind: "historial" }
  | { kind: "familias" };

const ICONOS = { familia: "👨‍👩‍👧‍👦", adulto: "👨‍👩", menor: "👶" } as const;
const STYLES = `.ed{max-width:1400px;margin:auto;padding:1rem;font-family:system-ui,sans-serif;color:#1d2733}
.ed h1{font-size:1.5rem;margin:.25rem 0}.ed h2{font-size:1.15rem;margin:0 0 .75rem}.ed h3,.ed h4{font-size:1rem;margin:.5rem 0}
.ed button,.ed input,.ed select,.ed textarea{font:inherit;padding:.45rem .6rem;max-width:100%;border:1px solid #8b97a6;border-radius:4px;background:#fff;color:inherit}
.ed button{cursor:pointer;background:#f3f6f9;margin:.15rem}.ed button:disabled{opacity:.55;cursor:not-allowed}.ed .ed-primary{background:#1263b5;color:#fff;border-color:#1263b5}
.ed a{color:#0b57a4}.ed :focus-visible{outline:3px solid #1263b5;outline-offset:2px}
.ed-panel{border:1px solid #c9d1db;border-radius:8px;padding:1rem;margin-bottom:1rem;background:#fff}
.ed-row{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;justify-content:space-between}
.ed-actions{display:flex;flex-wrap:wrap;gap:.35rem;align-items:center;margin:.5rem 0}.ed-actions a{padding:.45rem .6rem;border:1px solid #8b97a6;border-radius:4px;text-decoration:none}
.ed-grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:1rem}
.ed-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.75rem}.ed-metrics div{border:1px solid #c9d1db;border-radius:6px;padding:.75rem}.ed-metrics strong{display:block;font-size:1.4rem}
.ed-alert{padding:.6rem .8rem;border-radius:6px;border:1px solid;white-space:pre-line;margin:.5rem 0}.ed-success{background:#e7f6ec;border-color:#5aa874}.ed-warning,.ed-warn{background:#fff6dd;border-color:#d9a400}.ed-danger,.ed-error{background:#fdecec;border-color:#c0392b}.ed-info{background:#e8f1fb;border-color:#5b8fc7}
.ed-scroll{overflow-x:auto;max-width:100%}.ed table{width:100%;border-collapse:collapse}.ed td,.ed th{padding:.55rem;text-align:left;border-bottom:1px solid #d5dbe2;vertical-align:top}
.ed-chip{display:inline-block;padding:.1rem .45rem;margin:.1rem;border-radius:999px;background:#e7ebf0;font-size:.82rem}.ed-tone-success{background:#d6f0de}.ed-tone-warning{background:#fff0bf}.ed-tone-info{background:#d9e9fa}.ed-tone-danger,.ed-alertchip{background:#fbd5d5}
.ed-state-aprobado{background:#d6f0de}.ed-state-rechazado{background:#fbd5d5}.ed-state-subsanar{background:#fff0bf}.ed-state-subsanado{background:#d3eef2}
.ed-legajo-subsanar{border-left:4px solid #ffc107}.ed-legajo-subsanado{border-left:4px solid #17a2b8}.ed-legajo-aprobado{border-left:4px solid #28a745}.ed-legajo-rechazado{border-left:4px solid #dc3545}
.ed-detail{background:#f6f8fa;padding:.75rem;border-radius:6px}.ed-detail-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:1rem}
.ed-box{padding:.5rem .75rem;border:1px solid #d5dbe2;border-radius:6px;margin:.35rem 0}.ed-ok{color:#1e7a3c}.ed-pending{color:#8a5a00}.ed-file{margin-bottom:.6rem}.ed-list{list-style:none;padding:0}.ed-card{border:1px solid #d5dbe2;border-radius:6px;padding:.5rem;margin:.35rem 0}.ed-internal{background:#eceff2}
.ed-toolbar{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:.35rem;margin-top:.5rem}.ed-child{padding-left:1.25rem}.ed-pre{white-space:pre-line}
.ed-backdrop{position:fixed;inset:0;background:rgba(10,20,30,.55);display:flex;align-items:flex-start;justify-content:center;padding:2rem .75rem;overflow-y:auto;z-index:1000}
.ed-dialog{background:#fff;border-radius:8px;width:min(560px,100%);box-shadow:0 10px 40px rgba(0,0,0,.3)}.ed-wide{width:min(980px,100%)}
.ed-dialog header,.ed-dialog footer{display:flex;justify-content:space-between;align-items:center;gap:.5rem;padding:.75rem 1rem;border-bottom:1px solid #d5dbe2}.ed-dialog footer{border-top:1px solid #d5dbe2;border-bottom:0;justify-content:flex-end}
.ed-dialog-body{padding:1rem}.ed-dialog label,.ed-form-grid label{display:block;margin:.5rem 0}.ed-dialog label>input,.ed-dialog label>select,.ed-dialog label>textarea,.ed-form-grid label>input,.ed-form-grid label>select{display:block;width:100%;box-sizing:border-box;margin-top:.2rem}
.ed .ed-check{display:flex;gap:.5rem;align-items:flex-start}.ed .ed-check input{width:auto;display:inline}
.ed-form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:0 1rem}.ed-form-grid h4,.ed-form-grid [role=alert],.ed-form-grid>button{grid-column:1/-1}
.ed-invalid input,.ed-invalid select{border-color:#9a2a36;outline:2px solid rgba(154,42,54,.16)}.ed-match{background:#eef8f1}.ed-mismatch{background:#fff6dd}
.ed-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}.ed-pages{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.75rem}.ed-pages a[aria-current]{font-weight:700;text-decoration:none}
@media (max-width:640px){.ed{padding:.75rem}.ed-hide-sm{display:none}}`;

function useProjection() {
  const [data, setData] = useState<Detalle | null>(null);
  const [error, setError] = useState("");
  const controller = useRef<AbortController | null>(null);
  const reload = useCallback(async () => {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    try {
      const body = await loadProjection<Detalle>(undefined, current.signal);
      if (body.version !== 1 || !Array.isArray(body.legajos)) throw new Error("El expediente no es compatible con esta versión.");
      setData(body);
      setError("");
    } catch (cause) {
      if (!current.signal.aborted) setError(cause instanceof Error ? cause.message : "No se pudo cargar el expediente.");
    }
  }, []);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reload only sets state after its awaited fetch.
    void reload();
    const onPop = () => void reload();
    window.addEventListener("popstate", onPop);
    return () => { window.removeEventListener("popstate", onPop); controller.current?.abort(); };
  }, [reload]);
  return { data, error, reload };
}

/** A success alert queued before a reload, shown until it expires (native `getTimedAlert`). */
function useTimedAlert() {
  const [expedienteId] = useState(() => expedienteIdFromPath());
  const [alert, setAlert] = useState(() => readTimedAlert(expedienteId));
  useEffect(() => {
    if (!alert) return undefined;
    const timer = setTimeout(() => { clearTimedAlert(expedienteId); setAlert(null); }, Math.max(0, alert.expiresAt - Date.now()));
    return () => clearTimeout(timer);
  }, [alert, expedienteId]);
  return alert;
}

/**
 * "Procesar Expediente" with the native simulated counter: the total is the
 * number of preview rows and the counter advances every 200 ms in about 20
 * steps until the native response arrives (static/custom/js/expediente_detail.js).
 */
function ProcesarButton({ url, total, run, disabled }: { url: string; total: number; run: Run; disabled: boolean }) {
  const [progress, setProgress] = useState<{ current: number; done: boolean } | null>(null);
  const procesar = async () => {
    let current = 0;
    setProgress({ current, done: false });
    const step = Math.max(1, Math.floor(total / 20));
    const timer = setInterval(() => {
      current = Math.min(current + step, total);
      setProgress({ current, done: false });
    }, 200);
    const ok = await run(() => postNative(url), (data) => {
      const base = String(data.alerta_resumen || data.message || `Se crearon ${data.creados ?? "-"} legajos y el expediente pasó a EN ESPERA.`);
      const errores = Number(data.errores || 0);
      if (errores === 0 && Number(data.creados ?? 0) > 0) queueTimedAlert(expedienteIdFromPath(), "success", base);
      return { tone: errores > 0 ? "warning" : "success", text: `¡Listo! ${base}${errores ? ` ${errores} errores.` : ""}` };
    });
    clearInterval(timer);
    if (!ok) { setProgress(null); return; }
    setProgress({ current: total, done: true });
    setTimeout(() => setProgress(null), 2000);
  };
  const label = !progress ? "Procesar Expediente" : progress.done ? `✓ Completado ${total} / ${total} registros` : `Procesando ${progress.current} / ${total} registros...`;
  return <button type="button" className="ed-primary" disabled={disabled || Boolean(progress)} aria-busy={Boolean(progress && !progress.done)} onClick={() => void procesar()}>{label}</button>;
}

export function ExpedienteDetalleScreen() {
  const { data, error: loadError, reload } = useProjection();
  const [notices, setNotices] = useState<Notice[]>([]);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [search, setSearch] = useState("");
  const timed = useTimedAlert();

  // Django messages arrive once per projection; show them with the local notices.
  const serverNotices = useMemo<Notice[]>(() => [
    ...(timed ? [{ tone: timed.kind as Notice["tone"], text: timed.message }] : []),
    ...(data?.messages ?? []).map((m) => ({ tone: (m.level === "error" ? "danger" : m.level) as Notice["tone"], text: m.text })),
  ], [data, timed]);

  const navigate = useCallback((href: string) => {
    window.history.pushState({}, "", internal(href));
    void reload();
  }, [reload]);

  const closeDialog = useCallback(() => { setDialog(null); setError(""); }, []);

  const run: Run = useCallback(async (task, success) => {
    if (pending || uncertain) return false;
    setPending(true); setError("");
    try {
      const result = await task();
      if (result === undefined) return false; // cancelled by the user before dispatch
      const notice = success ? success(result) : String(result.message ?? "Acción realizada.");
      setNotices([typeof notice === "string" ? { tone: "success", text: notice } : notice]);
      setDialog(null);
      await reload();
      return true;
    } catch (cause) {
      // A transport failure after dispatch may have been committed: never retry.
      if (cause instanceof TypeError) setUncertain(true);
      setError(cause instanceof Error ? cause.message : "No se pudo completar la acción.");
      return false;
    } finally { setPending(false); }
  }, [pending, uncertain, reload]);

  const legajos = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!data || !term) return data?.legajos ?? [];
    return data.legajos.filter((leg) => `${leg.id} ${leg.nombre} ${leg.apellido} ${leg.documento}`.toLowerCase().includes(term));
  }, [data, search]);

  if (!data) return <main className="ed"><style>{STYLES}</style><h1>Expediente</h1>{loadError ? <p role="alert">{loadError}</p> : <p role="status">Cargando…</p>}</main>;

  const { expediente, actions, roles } = data;
  const disabled = pending || uncertain;
  const common = { onClose: closeDialog, run, pending, error };
  const simplePost = (url: string, body?: FormData, fallback = "Acción realizada.") => void run(() => postNative(url, body), (r) => String(r.alerta_resumen ?? r.message ?? fallback));
  const handlers = {
    disabled,
    open: (kind: LegajoDialog, legajo: Legajo, campo?: string) => { setError(""); setDialog({ kind, legajo, campo }); },
    aprobar: (legajo: Legajo) => { const body = new FormData(); body.append("accion", "APROBAR"); simplePost(legajo.actions.revisar!, body, "Legajo aprobado."); },
    confirmarSubsanacion: (legajo: Legajo) => { const body = new FormData(); body.append("legajo_id", String(legajo.id)); simplePost(legajo.actions.confirmar_subsanacion!, body, "Subsanación confirmada."); },
  };
  const eliminarLegajo = (legajo: Legajo) => void run(async () => {
    const preview = new FormData(); preview.append("accion", "ELIMINAR"); preview.append("preview", "1");
    let message = "¿Estás seguro de que querés dar de baja este legajo?";
    try {
      const data = await postNative(legajo.actions.eliminar!, preview);
      const summary = data.preview as { total_afectados: number; desglose_por_modelo?: { modelo: string; cantidad: number }[] } | undefined;
      if (summary) message = `Se aplicará baja lógica en cascada.\nTotal afectados: ${summary.total_afectados}\n${(summary.desglose_por_modelo ?? []).map((i) => `- ${i.modelo}: ${i.cantidad}`).join("\n")}`;
      const aviso = data.menores_sin_responsable as { mensaje?: string; detalle?: string[] } | undefined;
      if (aviso?.mensaje) message += `\n\n⚠️ ${aviso.mensaje}${aviso.detalle?.length ? `\n${aviso.detalle.map((d) => `- ${d}`).join("\n")}` : ""}`;
    } catch { /* the native flow also asks the generic question when the preview fails */ }
    if (!window.confirm(message)) return undefined;
    const body = new FormData(); body.append("accion", "ELIMINAR");
    return postNative(legajo.actions.eliminar!, body) as Promise<NativeResult>;
  }, (r) => String(r.message ?? "Legajo eliminado."));
  const asignar = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    simplePost(actions.asignar_tecnico!, new FormData(event.currentTarget), "Técnico asignado.");
  };
  const toggle = (id: number) => setExpanded((previous) => { const next = new Set(previous); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  const setPreviewLimit = (value: string) => {
    const params = new URLSearchParams(window.location.search);
    params.set("preview_limit", value);
    navigate(`${window.location.pathname}?${params}`);
  };

  return <main className="ed">
    <style>{STYLES}</style>
    <nav aria-label="Ruta de navegación"><a href="/celiaquia/expedientes/">Expedientes</a> › <span>Expediente</span></nav>
    <h1>Expediente {expediente.numero !== "-" ? expediente.numero : `#${expediente.id}`}</h1>

    <div className="ed-actions" aria-label="Acciones del expediente">
      {actions.editar && <a href={internal(actions.editar)}>Editar Metadatos</a>}
      {expediente.excel && <a href={internal(expediente.excel.url)}>Descargar Excel Provincia</a>}
      {actions.nomina_sintys && <a href={internal(actions.nomina_sintys)}>Descargar nómina Sintys</a>}
      {actions.historial && <button type="button" onClick={() => setDialog({ kind: "historial" })}>Ver Historial</button>}
      {actions.familias && <button type="button" onClick={() => setDialog({ kind: "familias" })}>Ver Familias</button>}
      {actions.subir_cruce && <button type="button" disabled={disabled} onClick={() => setDialog({ kind: "cruce", url: actions.subir_cruce! })}>Subir Excel de Documentos (Cruce)</button>}
      {actions.reprocesar_cruce && <button type="button" disabled={disabled} onClick={() => setDialog({ kind: "cruce", url: actions.reprocesar_cruce! })}>Reprocesar cruce</button>}
      {actions.padron_final && <a href={internal(actions.padron_final)}>Descargar nómina aprobados</a>}
    </div>

    <div aria-live="polite">{[...serverNotices, ...notices].map((n, i) => <p key={i} className={`ed-alert ed-${n.tone}`} role={n.tone === "danger" ? "alert" : "status"}>{n.text}</p>)}</div>
    {error && !dialog && <p role="alert" className="ed-alert ed-danger">{error}</p>}
    {uncertain && <p role="alert" className="ed-alert ed-warning">Resultado incierto. Recargue la página antes de volver a operar.</p>}

    {data.cupo && <section className="ed-panel" aria-labelledby="ed-cupo"><h2 id="ed-cupo">Provincial de {expediente.provincia}</h2>
      <div className="ed-metrics"><div>Total asignado<strong>{data.cupo.total_asignado}</strong></div><div>Usados<strong>{data.cupo.usados}</strong></div><div>Disponibles<strong>{data.cupo.disponibles}</strong></div><div>Fuera de cupo<strong>{data.cupo.fuera}</strong></div></div>
    </section>}
    {data.alertas.map((alerta, i) => <p key={i} className={`ed-alert ed-${alerta.style}`} role="alert">{alerta.text}</p>)}

    <section className="ed-panel" aria-labelledby="ed-detalle">
      <h2 id="ed-detalle">Detalle del Expediente <span className="ed-chip">ID #{expediente.id}</span></h2>
      <div className="ed-grid2">
        <dl>
          <dt>ID del expediente</dt><dd>{expediente.id}</dd>
          <dt>Numero de expediente</dt><dd>{expediente.numero}</dd>
          <dt>Estado</dt><dd>{expediente.estado_display}</dd>
          <dt>Fecha de creacion</dt><dd>{formatDate(expediente.fecha_creacion)}</dd>
          {expediente.excel && <><dt>Excel original</dt><dd><a href={internal(expediente.excel.url)} target="_blank" rel="noopener noreferrer">{expediente.excel.nombre}</a>
            {expediente.excel.audit && <><div><small>Cargado por {expediente.excel.cargado_por ?? "-"}{expediente.excel.cargado_en && ` el ${formatDate(expediente.excel.cargado_en, true)}`}</small></div>
              <div><small>Procesado por {expediente.excel.procesado_por ?? "-"}{expediente.excel.procesado_en && ` el ${formatDate(expediente.excel.procesado_en, true)}`}</small></div></>}</dd></>}
          {expediente.documento_url && <><dt>PRD generado</dt><dd><a href={safeHref(expediente.documento_url)} target="_blank" rel="noopener noreferrer">ver documento</a></dd></>}
        </dl>
        <dl>
          <dt>Provincia</dt><dd>{expediente.provincia}</dd>
          <dt>Técnicos asignados</dt><dd>{expediente.tecnicos.length ? expediente.tecnicos.map((t) => <span key={t} className="ed-chip">{t}</span>) : "No asignado"}</dd>
        </dl>
      </div>
    </section>

    {data.fuera_de_cupo.length > 0 && <section className="ed-panel" aria-labelledby="ed-fuera"><h2 id="ed-fuera">Lista de espera (Fuera de cupo)</h2>
      <div className="ed-scroll"><table><thead><tr><th scope="col">CUIL</th><th scope="col">Nombre</th><th scope="col">Apellido</th></tr></thead><tbody>{data.fuera_de_cupo.map((l) => <tr key={l.id}><td>{l.documento}</td><td>{l.nombre}</td><td>{l.apellido}</td></tr>)}</tbody></table></div>
    </section>}

    {data.preview ? <section className="ed-panel" aria-labelledby="ed-preview">
      <div className="ed-row"><h2 id="ed-preview">Vista previa del Excel</h2>
        <label>Registros a leer del Excel <select value={data.preview.limit} onChange={(e) => setPreviewLimit(e.target.value)}>{data.preview.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select></label></div>
      <div className="ed-scroll" tabIndex={0} role="region" aria-label="Vista previa del Excel"><table><thead><tr>{data.preview.headers.map((h) => <th key={h} scope="col">{h.charAt(0).toUpperCase() + h.slice(1)}</th>)}</tr></thead>
        <tbody>{data.preview.rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>)}</tbody></table></div>
      {data.preview.procesar && <ProcesarButton url={data.preview.procesar} total={data.preview.rows.length} run={run} disabled={disabled} />}
    </section> : data.preview_error ? <p className="ed-alert ed-danger" role="alert">{data.preview_error}</p> : null}

    <section className="ed-panel" aria-labelledby="ed-legajos">
      <div className="ed-row"><h2 id="ed-legajos">Legajos <span className="ed-chip" title="Cantidad total de personas asociadas al expediente">{data.legajos_total} persona{data.legajos_total === 1 ? "" : "s"}</span></h2>
        <label>Buscar legajos <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar por ID, nombre, apellido o CUIL..." /></label></div>
      {data.legajos.length === 0 ? <p>No hay legajos cargados.</p> : <div className="ed-scroll" tabIndex={0} role="region" aria-label="Legajos del expediente"><table>
        <thead><tr><th scope="col">ID</th><th scope="col">Beneficiario</th><th scope="col">Estado</th><th scope="col" className="ed-hide-sm">Archivos</th><th scope="col" className="ed-hide-sm">Observaciones</th><th scope="col">Acciones</th></tr></thead>
        <tbody>{legajos.map((leg) => <Fragment key={leg.id}>
          <tr className={`ed-legajo-${leg.estado.toLowerCase()}`}>
            <td>#{leg.id}</td>
            <td><div className={leg.es_hijo ? "ed-child" : undefined}>
              <strong>{leg.es_hijo && "└─ "}<span aria-hidden="true">{ICONOS[leg.icono]} </span>{leg.nombre} {leg.apellido}</strong>
              <div><small>CUIL: {leg.documento}</small></div>
              {leg.badges.map((b) => <span key={b.text} className={`ed-chip ed-tone-${b.tone}`}>{b.text}</span>)}
              {leg.hijos_texto && <div><small>{leg.hijos_texto}</small></div>}
              {leg.alertas.map((a) => <div key={a}><span className="ed-chip ed-alertchip">⚠️ {a}</span></div>)}
            </div></td>
            <td><span className={`ed-chip ed-state-${leg.estado.toLowerCase()}`}>{leg.estado}</span></td>
            <td className="ed-hide-sm">{leg.documentos.map((d) => <span key={d.label} className={`ed-chip ${d.cargado ? "ed-tone-success" : "ed-tone-warning"}`} title={`${d.nombre} (${d.cargado ? "cargado" : "pendiente"})`}>{d.nombre.length > 24 ? `${d.nombre.slice(0, 23)}…` : d.nombre}</span>)}</td>
            <td className="ed-hide-sm">{leg.observacion.texto ? <>{leg.observacion.titulo && <small style={{ display: "block" }}>{leg.observacion.titulo}</small>}<small>{leg.observacion.texto.length > 80 ? `${leg.observacion.texto.slice(0, 79)}…` : leg.observacion.texto}</small></>
              : leg.subsanacion_motivo ? <small>{leg.subsanacion_motivo.length > 80 ? `${leg.subsanacion_motivo.slice(0, 79)}…` : leg.subsanacion_motivo}</small> : null}</td>
            <td>
              <button type="button" aria-expanded={expanded.has(leg.id)} onClick={() => toggle(leg.id)} aria-label={`Ver detalle de ${leg.nombre} ${leg.apellido}`}>Ver</button>
              {leg.actions.editar && <button type="button" disabled={disabled} onClick={() => handlers.open("editar", leg)} aria-label={`Editar datos del legajo de ${leg.nombre} ${leg.apellido}`}>Editar</button>}
              {leg.actions.eliminar && <button type="button" disabled={disabled} onClick={() => eliminarLegajo(leg)} aria-label={`Eliminar legajo de ${leg.nombre} ${leg.apellido}`}>Eliminar</button>}
            </td>
          </tr>
          {expanded.has(leg.id) && <tr><td colSpan={6}><LegajoDetalle legajo={leg} isProvincial={roles.provincial} handlers={handlers} /></td></tr>}
        </Fragment>)}</tbody>
      </table>{legajos.length === 0 && <p>Ningún legajo coincide con la búsqueda.</p>}</div>}
      {actions.confirmar_envio && <div className="ed-toolbar"><button type="button" className="ed-primary" disabled={disabled} onClick={() => simplePost(actions.confirmar_envio!, undefined, "Envío confirmado.")}>Confirmar Envío</button></div>}
    </section>

    {data.registros_erroneos.length > 0 && <RegistrosErroneos registros={data.registros_erroneos} catalogos={data.catalogos} reprocesarUrl={actions.reprocesar_errores} run={run} disabled={disabled} />}

    {actions.asignar_tecnico && <section className="ed-panel" aria-labelledby="ed-asignar"><h2 id="ed-asignar">Asignar Técnico</h2>
      <form onSubmit={asignar}><SearchableSelect label="Seleccionar Técnico:" searchLabel="Buscar Técnico" name="tecnico_id" required options={data.tecnicos.map((t) => ({ value: String(t.id), label: t.name }))} />
        <button type="submit" className="ed-primary" disabled={disabled}>Asignar</button></form>
    </section>}

    {dialog?.kind === "historial" && <HistorialDialog historial={data.historial} onClose={closeDialog} onNavigate={navigate} />}
    {dialog?.kind === "familias" && <FamiliasDialog legajos={data.legajos} onClose={closeDialog} />}
    {dialog?.kind === "cruce" && <CruceDialog url={dialog.url} {...common} />}
    {dialog && "legajo" in dialog && <>
      {(dialog.kind === "rechazar" || dialog.kind === "subsanar") && <MotivoDialog kind={dialog.kind === "rechazar" ? "RECHAZAR" : "SUBSANAR"} legajo={dialog.legajo} complementaria={data.complementaria} {...common} />}
      {dialog.kind === "corregir" && <CorregirDialog legajo={dialog.legajo} {...common} />}
      {dialog.kind === "archivo" && <ArchivoDialog legajo={dialog.legajo} campo={dialog.campo ?? dialog.legajo.archivos[0]?.campo ?? "archivo2"} {...common} />}
      {dialog.kind === "respuesta" && <RespuestaSubsanacionDialog legajo={dialog.legajo} {...common} />}
      {dialog.kind === "renaper-respuesta" && <RespuestaRenaperDialog legajo={dialog.legajo} {...common} />}
      {dialog.kind === "renaper" && <RenaperDialog legajo={dialog.legajo} onClose={closeDialog} />}
      {dialog.kind === "editar" && <EditarLegajoDialog legajo={dialog.legajo} catalogos={data.catalogos} {...common} />}
      {dialog.kind === "comentario" && <ComentarioDialog legajo={dialog.legajo} comentarios={data.comentarios} {...common} />}
    </>}
  </main>;
}
