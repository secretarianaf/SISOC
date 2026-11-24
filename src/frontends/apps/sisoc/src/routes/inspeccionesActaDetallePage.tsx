import { Fragment, useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { crearCliente, leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "../webAccess";
import ClaroFrame, { type ClaroLayout, type ClaroUser } from "./ClaroFrame";
import { actaNavigation } from "./inspeccionesActaNavigation";
import InspToasts, { type InspMessage } from "./inspeccionesToasts";
import type { NavigationNode } from "./types";

/**
 * One acta of the Inspecciones panel (`inspecciones/acta_detalle.html`, IN04).
 * Texts come already printed by the vertical's G1 web API
 * (`/api/web/inspecciones/actas/<numero>/`); files (PDF, photos, signature,
 * notification pages) stay native URLs. "Anular acta" and the test mark POST to
 * the API, which runs the native view; its redirect is a full navigation and
 * the next load shows the native messages as toasts, like toastr.
 */
type Pair = [string, string];
export type ActaDetalleData = {
  layout: ClaroLayout;
  acta: {
    numero: string; anulada: boolean; anulada_at: string; anulada_por: string; motivo_anulacion: string;
    notificacion_cargada: boolean; prueba: boolean; linea: string; pdf_url: string | null; anular_url: string; prueba_url: string;
  };
  resumen: { abierta: string; resultado: string; motivo_parcial: string; personal: string; aulas: string };
  formulario_version: string;
  respuestas: { codigo: string; pregunta: string; respuesta: string; notas: string[] }[];
  evidencia: { url: string; titulo: string; descripcion: string; alt: string; capturada: string; subida: string }[];
  notificaciones: {
    version: number; cargada: string; notificada: string; receptor: string; condicion_firma: string; motivo: string;
    observaciones: string; motivo_correccion: string; archivos: { url: string; alt: string }[];
  }[];
  inspector: { nombre: string; usuario: string; filas: Pair[] };
  institucion: { editar_url: string | null; carga_manual: boolean; filas: Pair[] };
  ubicacion: { fuente: string; es_gps: boolean; filas: Pair[]; mapa_url: string | null };
  recepcion: { tipo: "firma" | "excepcion" | ""; imagen_url: string | null; imagen_alt: string; filas: Pair[] };
  historial: { hora: string; codigo: string; texto: string; motivo: string }[];
  messages: InspMessage[];
};
type Session = { user: ClaroUser; navigation: NavigationNode[]; footer_version_label: string };
type State =
  | { status: "loading" }
  | { status: "error" }
  | { status: "forbidden"; prerequisite: WebPrerequisite | null }
  | { status: "ready"; data: ActaDetalleData; session: Session };

const client = crearCliente("/api");
const API_PREFIX = "/api/web/inspecciones/actas/";
const MAP_PREFIX = "https://www.openstreetmap.org/?";
const accepted = (status: number) => (status >= 200 && status < 300) || status === 403;
const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object";
const text = (v: unknown): v is string => typeof v === "string";
const internal = (v: unknown) => text(v) && safeInternalPath(v) === v;
const texts = (v: unknown, keys: string[]) => record(v) && keys.every((k) => text(v[k]));
const pairs = (v: unknown) => Array.isArray(v) && v.every((p) => Array.isArray(p) && p.length === 2 && text(p[0]) && text(p[1]));

function nodeValid(n: unknown): n is NavigationNode {
  return record(n) && text(n.id) && text(n.label) && (n.href === null || safeInternalPath(n.href) !== null) &&
    Array.isArray(n.children) && n.children.every(nodeValid);
}
function sessionValid(v: unknown): v is Session {
  return record(v) && texts(v.user, ["display_name", "avatar_initial", "role_label"]) &&
    Array.isArray(v.navigation) && v.navigation.every(nodeValid) && text(v.footer_version_label);
}
function layoutValid(l: unknown): l is ClaroLayout {
  return record(l) && Array.isArray(l.breadcrumb) && l.breadcrumb.every((b) => record(b) && text(b.text) && (b.url === null || internal(b.url))) &&
    texts(l, ["display_name", "role", "initials"]);
}
function actaDetalleValid(v: unknown): v is ActaDetalleData {
  if (!record(v) || !record(v.acta) || !record(v.inspector) || !record(v.institucion) || !record(v.ubicacion) || !record(v.recepcion)) return false;
  const a = v.acta, i = v.institucion, u = v.ubicacion, r = v.recepcion;
  return layoutValid(v.layout) &&
    texts(a, ["numero", "anulada_at", "anulada_por", "motivo_anulacion", "linea"]) &&
    ["anulada", "notificacion_cargada", "prueba"].every((k) => typeof a[k] === "boolean") &&
    (a.pdf_url === null || internal(a.pdf_url)) &&
    [a.anular_url, a.prueba_url].every((url) => internal(url) && (url as string).startsWith(API_PREFIX)) &&
    texts(v.resumen, ["abierta", "resultado", "motivo_parcial", "personal", "aulas"]) && text(v.formulario_version) &&
    Array.isArray(v.respuestas) && v.respuestas.every((f) => texts(f, ["codigo", "pregunta", "respuesta"]) && Array.isArray(f.notas) && f.notas.every(text)) &&
    Array.isArray(v.evidencia) && v.evidencia.every((e) => texts(e, ["titulo", "descripcion", "alt", "capturada", "subida"]) && internal(e.url)) &&
    Array.isArray(v.notificaciones) && v.notificaciones.every((n: unknown) => record(n) &&
      texts(n, ["cargada", "notificada", "receptor", "condicion_firma", "motivo", "observaciones", "motivo_correccion"]) &&
      Number.isSafeInteger(n.version) && Array.isArray(n.archivos) && n.archivos.every((f) => record(f) && internal(f.url) && text(f.alt))) &&
    texts(v.inspector, ["nombre", "usuario"]) && pairs(v.inspector.filas) &&
    (i.editar_url === null || internal(i.editar_url)) && typeof i.carga_manual === "boolean" && pairs(i.filas) &&
    text(u.fuente) && typeof u.es_gps === "boolean" && pairs(u.filas) && (u.mapa_url === null || (text(u.mapa_url) && u.mapa_url.startsWith(MAP_PREFIX))) &&
    ["firma", "excepcion", ""].includes(r.tipo as string) && (r.imagen_url === null || internal(r.imagen_url)) && text(r.imagen_alt) && pairs(r.filas) &&
    Array.isArray(v.historial) && v.historial.every((h) => texts(h, ["hora", "codigo", "texto", "motivo"])) &&
    Array.isArray(v.messages) && v.messages.every((m) => texts(m, ["message"]) && ["success", "error", "warning", "info"].includes((m as Record<string, unknown>).level as string));
}

type Outcome = { kind: "redirect"; to: string } | { kind: "forbidden"; data: unknown } | { kind: "uncertain" };

/** POST once; an unconfirmed outcome is reported, never resubmitted. */
async function postOnce(url: string, body: URLSearchParams): Promise<Outcome> {
  try {
    const { data, status } = await client.post(url.slice("/api/".length), body, { validateStatus: accepted });
    if (status === 403) return { kind: "forbidden", data };
    if (record(data) && data.ok === true && internal(data.redirect)) return { kind: "redirect", to: data.redirect as string };
  } catch {
    // Network error or timeout after sending: the result is unknown.
  }
  return { kind: "uncertain" };
}

/** Native `<form method="post">` posted through the API, once. */
function useAction(url: string, onForbidden: (data: unknown) => void) {
  const busy = useRef(false);
  const [uncertain, setUncertain] = useState(false);
  const submit = useCallback(async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true;
    const outcome = await postOnce(url, new URLSearchParams(new FormData(event.currentTarget) as unknown as Record<string, string>));
    if (outcome.kind === "redirect") { actaNavigation.assign(outcome.to); return; }
    if (outcome.kind === "forbidden") onForbidden(outcome.data); else setUncertain(true);
    busy.current = false;
  }, [url, onForbidden]);
  return { submit, uncertain };
}

function Csrf({ next }: { next: string }) {
  return (
    <>
      <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
      <input type="hidden" name="next" value={next} />
    </>
  );
}

function Uncertain({ numero }: { numero: string }) {
  return <p role="alert">No se pudo confirmar el resultado. <a href={`/inspecciones/actas/${encodeURIComponent(numero)}/`}>Volver al acta</a></p>;
}

function Badge({ kind, children, dot = true }: { kind: string; children: string; dot?: boolean }) {
  return <span className={`insp-badge insp-badge-${kind}`}>{dot && <i aria-hidden="true" />}{children}</span>;
}

function Lines({ value }: { value: string }) {
  const lines = value.split(/\r\n|\r|\n/);
  return <>{lines.map((line, index) => <Fragment key={index}>{index > 0 && <br />}{line}</Fragment>)}</>;
}

const DD_CLASS: Record<string, string> = { Cueanexo: "insp-mono", Mail: "text-break", Coordenadas: "insp-mono", "Texto leído": "small" };

function Dl({ rows, className = "insp-dl" }: { rows: Pair[]; className?: string }) {
  return (
    <dl className={className}>
      {rows.map(([label, value]) => (
        <Pair key={label} label={label}>{value}</Pair>
      ))}
    </dl>
  );
}

function Pair({ label, children }: { label: string; children: ReactNode }) {
  return <><dt>{label}</dt><dd className={DD_CLASS[label]}>{children}</dd></>;
}

function Section({ id, title, aside, children, body = true }: { id: string; title: string; aside?: ReactNode; children: ReactNode; body?: boolean }) {
  return (
    <section className="insp-seccion" aria-labelledby={id}>
      <div className="insp-seccion-cabecera">
        <h3 id={id}>{title}</h3>
        {aside}
      </div>
      {body ? <div className="insp-seccion-cuerpo">{children}</div> : children}
    </section>
  );
}

/** Bootstrap 5 modal (`#insp-modal-anular`): focus, Tab trap, Escape, backdrop click, scrollbar padding. */
function AnularModal({ data, next, close, onForbidden }: { data: ActaDetalleData; next: string; close: () => void; onForbidden: (data: unknown) => void }) {
  const modal = useRef<HTMLDivElement>(null);
  const { submit, uncertain } = useAction(data.acta.anular_url, onForbidden);
  useEffect(() => {
    const body = document.body;
    const scrollbar = window.innerWidth - document.documentElement.clientWidth;
    const before = { overflow: body.style.overflow, padding: body.style.paddingRight };
    body.classList.add("modal-open");
    body.style.overflow = "hidden";
    if (scrollbar > 0) body.style.paddingRight = `${(parseFloat(getComputedStyle(body).paddingRight) || 0) + scrollbar}px`;
    modal.current?.focus();
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); close(); return; }
      if (event.key !== "Tab") return;
      const controls = Array.from(modal.current?.querySelectorAll<HTMLElement>("button:not([disabled]),textarea,a[href]") ?? []);
      const first = controls[0], last = controls.at(-1);
      if (!modal.current?.contains(document.activeElement)) { event.preventDefault(); first?.focus(); }
      else if (event.shiftKey && (document.activeElement === first || document.activeElement === modal.current)) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      body.classList.remove("modal-open");
      body.style.overflow = before.overflow;
      body.style.paddingRight = before.padding;
    };
  }, [close]);
  const numero = data.acta.numero;
  return (
    <>
      <div className="modal fade show" id="insp-modal-anular" tabIndex={-1} aria-labelledby="insp-modal-anular-titulo" aria-modal="true" role="dialog"
        ref={modal} style={{ display: "block" }} onClick={(event) => { if (event.target === event.currentTarget) close(); }}>
        <div className="modal-dialog">
          <form className="modal-content" method="post" action={data.acta.anular_url} onSubmit={submit}>
            <Csrf next={next} />
            <div className="modal-header">
              <h2 className="modal-title h5" id="insp-modal-anular-titulo">Anular {numero}</h2>
              <button type="button" className="btn-close" aria-label="Cerrar" onClick={close} />
            </div>
            <div className="modal-body">
              <p>
                El acta conserva su número y su contenido, pero deja de contar en los indicadores.
                {" "}Esta acción queda registrada y no se puede deshacer.
              </p>
              <label className="form-label" htmlFor="id_motivo_anulacion">
                Motivo{" "}<span className="text-danger">*</span>
              </label>
              <textarea id="id_motivo_anulacion" className="form-control" name="motivo" rows={4} minLength={10} required aria-describedby="ayuda-motivo-anulacion" />
              <div id="ayuda-motivo-anulacion" className="form-text">Al menos 10 caracteres.</div>
              {uncertain && <Uncertain numero={numero} />}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-link text-secondary" onClick={close}>Cancelar</button>
              <button type="submit" className="btn btn-danger">Anular acta</button>
            </div>
          </form>
        </div>
      </div>
      <div className="modal-backdrop fade show" />
    </>
  );
}

function PruebaForm({ data, next, onForbidden }: { data: ActaDetalleData; next: string; onForbidden: (data: unknown) => void }) {
  const { submit, uncertain } = useAction(data.acta.prueba_url, onForbidden);
  return (
    <form method="post" action={data.acta.prueba_url} onSubmit={submit}>
      <Csrf next={next} />
      {data.acta.prueba ? (
        <><input type="hidden" name="es_prueba" value="0" /><button type="submit" className="btn btn-outline-secondary">Quitar marca de prueba</button></>
      ) : (
        <><input type="hidden" name="es_prueba" value="1" /><button type="submit" className="btn btn-outline-secondary">Marcar como prueba</button></>
      )}
      {uncertain && <Uncertain numero={data.acta.numero} />}
    </form>
  );
}

function Encabezado({ data, next, openAnular, onForbidden }: { data: ActaDetalleData; next: string; openAnular: (button: HTMLButtonElement) => void; onForbidden: (data: unknown) => void }) {
  const { acta, recepcion, ubicacion } = data;
  return (
    <div className="insp-acta-encabezado">
      <div className="d-flex flex-column gap-2">
        <div className="insp-acta-rotulo">Acta de inspección</div>
        <h1 className="insp-acta-numero">{acta.numero}</h1>
        <div className="insp-acta-badges">
          {acta.anulada ? <Badge kind="error">Anulada</Badge> : <Badge kind="ok">Finalizada</Badge>}
          {recepcion.tipo === "firma" ? <Badge kind="info">Firmada por quien recibe</Badge>
            : recepcion.tipo === "excepcion" ? <Badge kind="alerta">Excepción de firma</Badge> : null}
          {acta.notificacion_cargada ? <Badge kind="ok">Notificación cargada</Badge> : <Badge kind="alerta">Notificación pendiente</Badge>}
          {acta.prueba && <Badge kind="neutro" dot={false}>Prueba</Badge>}
        </div>
        <div className="insp-acta-linea">{acta.linea}</div>
      </div>
      <div className="insp-acta-acciones">
        {!acta.anulada && (
          <button type="button" className="btn btn-outline-danger" onClick={(event) => openAnular(event.currentTarget)}>Anular acta</button>
        )}
        {!acta.anulada && <PruebaForm data={data} next={next} onForbidden={onForbidden} />}
        {ubicacion.mapa_url && <a className="btn btn-outline-primary" href={ubicacion.mapa_url} target="_blank" rel="noopener noreferrer">Ver en el mapa</a>}
        {acta.pdf_url ? (
          <a className="btn btn-primary" href={acta.pdf_url}><i className="fas fa-download" aria-hidden="true" />Descargar PDF</a>
        ) : <span className="btn btn-primary disabled" aria-disabled="true">PDF pendiente</span>}
      </div>
    </div>
  );
}

function Kpi({ title, value, extra, wide = false }: { title: string; value: string; extra?: string; wide?: boolean }) {
  return (
    <div className="insp-kpi">
      <div className="insp-kpi-titulo">{title}</div>
      <div className={`insp-kpi-valor${wide ? " insp-kpi-valor-texto" : ""}`}>{value}</div>
      {extra && <span className="insp-nota">Motivo: {extra}</span>}
    </div>
  );
}

function Izquierda({ data }: { data: ActaDetalleData }) {
  return (
    <div>
      <Section id="h-resp" title="Respuestas del formulario" body={false} aside={<span className="insp-seccion-nota">Versión {data.formulario_version}</span>}>
        <div className="table-responsive">
          <table className="table insp-tabla">
            <thead><tr><th scope="col">Cód.</th><th scope="col">Pregunta</th><th scope="col">Respuesta</th></tr></thead>
            <tbody>
              {data.respuestas.map((fila) => (
                <tr key={fila.codigo}>
                  <td className="insp-mono text-muted">{fila.codigo}</td>
                  <td>{fila.pregunta}</td>
                  <td><Lines value={fila.respuesta} />{fila.notas.length > 0 && " "}{fila.notas.map((nota, index) => <span key={index} className="insp-nota">{nota}</span>)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
      <Section id="h-evid" title="Evidencia fotográfica" aside={<span className="insp-seccion-nota">{data.evidencia.length} imágenes</span>}>
        {data.evidencia.length ? (
          <div className="insp-figuras">
            {data.evidencia.map((imagen) => (
              <figure key={imagen.url}>
                <a href={imagen.url} target="_blank" rel="noopener"><img className="insp-miniatura" src={imagen.url} alt={imagen.alt} loading="lazy" /></a>
                <figcaption>
                  <strong>{imagen.titulo}</strong>
                  {imagen.descripcion && <div>{imagen.descripcion}</div>}
                  <div className="text-muted">{imagen.capturada ? `Tomada ${imagen.capturada}` : "Fecha de captura no disponible"}{imagen.subida && ` · subida ${imagen.subida}`}</div>
                </figcaption>
              </figure>
            ))}
          </div>
        ) : <p className="text-muted mb-0">El acta no tiene imágenes.</p>}
      </Section>
      <Section id="h-notif" title="Notificación en papel" aside={data.notificaciones.length ? <Badge kind="ok" dot={false}>Cargada</Badge> : <Badge kind="alerta" dot={false}>Pendiente</Badge>}>
        {data.notificaciones.length ? data.notificaciones.map((n, index) => (
          <div key={n.version} className={index ? "border-top pt-3 mt-3 text-muted" : ""}>
            {index > 0 && <div className="small mb-2">Versión anterior (v{n.version})</div>}
            <dl className="insp-dl mb-2">
              <Pair label="Cargada">{n.cargada}</Pair>
              <Pair label="Notificada">{n.notificada}</Pair>
              <Pair label="Recibió">{n.receptor}</Pair>
              <Pair label="Firma del papel">{n.condicion_firma}{n.motivo && <>{" "}<span className="insp-nota">{n.motivo}</span></>}</Pair>
              {n.observaciones && <Pair label="Observaciones">{n.observaciones}</Pair>}
              {n.motivo_correccion && <Pair label="Corrección">{n.motivo_correccion}</Pair>}
            </dl>
            <div className="d-flex gap-2 flex-wrap">
              {n.archivos.map((archivo) => (
                <div key={archivo.url}>
                  <a href={archivo.url} target="_blank" rel="noopener"><img className="insp-miniatura insp-miniatura-chica" src={archivo.url} alt={archivo.alt} loading="lazy" /></a>
                </div>
              ))}
            </div>
          </div>
        )) : <p className="text-muted mb-0">Todavía no se cargó la notificación en papel.</p>}
      </Section>
    </div>
  );
}

function Derecha({ data }: { data: ActaDetalleData }) {
  const { inspector, institucion, ubicacion, recepcion } = data;
  return (
    <div>
      <Section id="h-visita" title="Inspector a cargo">
        <dl className="insp-dl">
          <Pair label="Inspector">{inspector.nombre}{" "}<span className="text-muted">· {inspector.usuario}</span></Pair>
          {inspector.filas.map(([label, value]) => <Pair key={label} label={label}>{value}</Pair>)}
        </dl>
      </Section>
      <Section id="h-esc" title="Institución" aside={institucion.editar_url ? <a className="insp-seccion-nota" href={institucion.editar_url}>Editar institución</a>
        : institucion.carga_manual ? <Badge kind="alerta" dot={false}>Carga manual</Badge> : undefined}>
        <Dl rows={institucion.filas} />
      </Section>
      <Section id="h-ubic" title="Geolocalización" aside={<Badge kind={ubicacion.es_gps ? "ok" : "alerta"} dot={false}>{ubicacion.fuente}</Badge>}>
        <Dl rows={ubicacion.filas} />
      </Section>
      <Section id="h-rec" title="Firma responsable">
        {recepcion.tipo === "firma" ? (
          <>
            {recepcion.imagen_url && <img className="insp-firma mb-2" src={recepcion.imagen_url} alt={recepcion.imagen_alt} />}
            <Dl rows={recepcion.filas} />
            <div className="small text-muted mt-2">Firma en pantalla. No es una firma digital certificada.</div>
          </>
        ) : recepcion.tipo === "excepcion" ? <Dl rows={recepcion.filas} /> : <p className="text-muted mb-0">Sin datos de recepción.</p>}
      </Section>
      <Section id="h-hist" title="Avance de la inspección">
        <ol className="insp-linea-tiempo">
          {data.historial.length ? data.historial.map((evento, index) => (
            <li key={index} className={`insp-hito insp-hito-${evento.codigo}`}>
              <span className="insp-hito-punto" aria-hidden="true" />
              <span className="insp-hito-hora">{evento.hora}</span>
              <span className="insp-hito-texto">{evento.texto}{evento.motivo && <span className="insp-nota">Motivo: {evento.motivo}</span>}</span>
            </li>
          )) : <li className="insp-hito"><span className="insp-hito-texto text-muted">Sin eventos.</span></li>}
        </ol>
      </Section>
    </div>
  );
}

export function ActaDetalleContent({ data, onForbidden }: { data: ActaDetalleData; onForbidden: (data: unknown) => void }) {
  const [anular, setAnular] = useState<HTMLButtonElement | null>(null);
  const next = window.location.pathname;
  const close = useCallback(() => {
    setAnular((trigger) => { trigger?.focus(); return null; });
  }, []);
  const { acta, resumen } = data;
  return (
    <>
      {acta.anulada && (
        <div className="insp-aviso insp-aviso-rojo" role="alert">
          <strong>Acta anulada</strong>
          {acta.anulada_at && ` el ${acta.anulada_at}`}
          {acta.anulada_por && ` por ${acta.anulada_por}`}
          {" ."}
          {acta.motivo_anulacion && ` Motivo: ${acta.motivo_anulacion}`}
          {" "}<div className="small">Conserva su número y su contenido, pero no cuenta en los indicadores.</div>
        </div>
      )}
      <Encabezado data={data} next={next} openAnular={setAnular} onForbidden={onForbidden} />
      <div className="insp-totales">
        <Kpi title="Escuela abierta" value={resumen.abierta} />
        <Kpi title="Resultado de la constatación" value={resumen.resultado} extra={resumen.motivo_parcial} wide />
        <Kpi title="Personal presente / previsto" value={resumen.personal} />
        <Kpi title="Aulas funcionando / previstas" value={resumen.aulas} />
      </div>
      <div className="insp-columnas-2-1">
        <Izquierda data={data} />
        <Derecha data={data} />
      </div>
      {anular && !acta.anulada && <AnularModal data={data} next={next} close={close} onForbidden={onForbidden} />}
      <InspToasts messages={data.messages} />
    </>
  );
}

export default function ActaDetallePage({ numero }: { numero: string }) {
  const [state, setState] = useState<State>({ status: "loading" });
  const forbidden = useCallback((data: unknown) => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(data) }), []);
  useEffect(() => {
    const controller = new AbortController();
    const options = { signal: controller.signal, validateStatus: accepted };
    Promise.all([
      client.get("web/session/", options),
      client.get(`web/inspecciones/actas/${encodeURIComponent(numero)}/`, options),
    ]).then(([session, acta]: { data: unknown; status?: number }[]) => {
      if (controller.signal.aborted) return;
      if (session.status === 403 || acta.status === 403) {
        setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(session.status === 403 ? session.data : acta.data) });
      } else if (sessionValid(session.data) && actaDetalleValid(acta.data)) {
        setState({ status: "ready", data: acta.data, session: session.data });
      } else setState({ status: "error" });
    }).catch(() => { if (!controller.signal.aborted) setState({ status: "error" }); });
    return () => controller.abort();
  }, [numero]);
  if (state.status === "loading") return <main role="status">Cargando acta…</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar el acta.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  return (
    <ClaroFrame title="Inspecciones escolares" user={state.session.user} layout={state.data.layout} navigation={state.session.navigation} footerLabel={state.session.footer_version_label}>
      <ActaDetalleContent data={state.data} onForbidden={forbidden} />
    </ClaroFrame>
  );
}
