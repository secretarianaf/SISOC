/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { Fragment, useEffect, useRef, useState, type FormEvent } from "react";
import { Breadcrumb, accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeModal, NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * Publication review (`encuestas/encuesta_revision.html`, `/encuestas/<id>/revision/`). GET
 * `/api/web/encuestas/<id>/revision/` runs `EncuestaRevisionView` (403 without `aprobar_encuesta` or
 * `change_encuesta`, 404 for an unknown survey). "Aprobar y publicar" posts to `.../aprobar/` and the rejection
 * modal to `.../rechazar/`; both run the native view and leave its message queued, so the page navigates to
 * the native redirect (the list, or this page again when the service rejects). An invalid reason is the
 * native 400: the modal stays open with its errors and the typed text, and the view goes back to the top.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Opcion = { texto: string; puntaje: number };
type Pregunta = {
  numero: number; tipo: string; tipo_label: string; obligatoria: boolean; texto: string; condicion: string | null; pondera: boolean;
  puntaje_si: number | null; puntaje_no: number | null; opciones: Opcion[];
};
type Segmentacion = { tipo: string; label: string; destinatarios: string[]; usuarios: { id: number; username: string; full_name: string }[]; grupos: string[] };
export type RevisionData = {
  id: number; titulo: string; version: number; estado: string; estado_label: string; creador: string;
  motivo_rechazo: { texto: string; usuario: string; fecha: string } | null; descripcion: string; modalidad: string; es_anonima: boolean;
  disponible_pwa: boolean; duracion_ronda_dias: number; es_recurrente: boolean; intervalo_recurrencia_dias: number | null;
  intervalo_recordatorio_dias: number; segmentacion: Segmentacion | null; preguntas: Pregunta[]; solicitada_por: string; fecha_solicitud: string;
  puede_aprobar: boolean; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const flag = (v: unknown) => typeof v === "boolean";
const list = (v: unknown, ok: (x: unknown) => boolean) => Array.isArray(v) && v.every(ok);
const strings = (v: unknown, keys: string[]) => record(v) && keys.every((k) => text(v[k]));
const nullInt = (v: unknown) => v === null || int(v);

export function revisionValid(v: unknown): v is RevisionData {
  if (!record(v)) return false;
  const seg = v.segmentacion;
  return int(v.id) && int(v.version) && strings(v, ["titulo", "estado", "estado_label", "creador", "descripcion", "modalidad", "solicitada_por", "fecha_solicitud"]) &&
    (v.motivo_rechazo === null || strings(v.motivo_rechazo, ["texto", "usuario", "fecha"])) &&
    ["es_anonima", "disponible_pwa", "es_recurrente", "puede_aprobar"].every((k) => flag(v[k])) &&
    int(v.duracion_ronda_dias) && nullInt(v.intervalo_recurrencia_dias) && int(v.intervalo_recordatorio_dias) &&
    (seg === null || (strings(seg, ["tipo", "label"]) && list((seg as Segmentacion).destinatarios, text) && list((seg as Segmentacion).grupos, text) &&
      list((seg as Segmentacion).usuarios, (u) => record(u) && int(u.id) && text(u.username) && text(u.full_name)))) &&
    list(v.preguntas, (p) => strings(p, ["tipo", "tipo_label", "texto"]) && int((p as Pregunta).numero) && flag((p as Pregunta).obligatoria) && flag((p as Pregunta).pondera) &&
      ((p as Pregunta).condicion === null || text((p as Pregunta).condicion)) && nullInt((p as Pregunta).puntaje_si) && nullInt((p as Pregunta).puntaje_no) &&
      list((p as Pregunta).opciones, (o) => strings(o, ["texto"]) && int((o as Opcion).puntaje))) &&
    list(v.messages, (m) => strings(m, ["message"]) && LEVELS.includes((m as Message).level));
}

const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);

function Estado({ d }: { d: RevisionData }) {
  const icon = d.estado === "pendiente_aprobacion" ? "fas fa-clock" : d.estado === "publicada" ? "fas fa-check-circle" : "fas fa-file-alt";
  return <span className={`encuesta-estado encuesta-estado--${d.estado}`}><i className={icon} aria-hidden="true"></i> {d.estado_label}</span>;
}

function Motivo({ d }: { d: RevisionData }) {
  const m = d.motivo_rechazo;
  if (!m) return null;
  return (
    <div className="alert alert-warning mb-3" role="note">
      <h2 className="h6 mb-2"><i className="fas fa-comment-alt me-1" aria-hidden="true"></i>{d.estado === "borrador" ? "Cambios solicitados" : "Motivo del último rechazo"}</h2>
      <p className="mb-2 text-break">{m.texto.split(/\r\n|\r|\n/).map((line, i, all) => <Fragment key={i}>{line}{i < all.length - 1 && <br />}</Fragment>)}</p>
      <p className="small mb-0">{m.usuario} · {m.fecha}</p>
      {d.estado === "borrador" && <p className="small mt-2 mb-0">Corregí la encuesta, guardá los cambios y volvé a solicitar la publicación desde el listado.</p>}
    </div>
  );
}

function Destinatarios({ s }: { s: Segmentacion | null }) {
  const todos = s !== null && !["listado_documentos", "listado_usuarios", "grupos"].includes(s.tipo);
  return (
    <>
      <p className="mb-2">{s?.label || "Sin segmentación configurada"}</p>
      {s?.tipo === "listado_documentos" && (
        <details>
          <summary>Ver {s.destinatarios.length} destinatario{plural(s.destinatarios.length, "", "s")}</summary>
          <div className="encuesta-revision__destinatarios">
            <ul className="mb-0">{s.destinatarios.length > 0 ? s.destinatarios.map((t, i) => <li key={i}>{t}</li>) : <li>No hay destinatarios cargados.</li>}</ul>
          </div>
        </details>
      )}
      {s?.tipo === "listado_usuarios" && (
        <details>
          <summary>Ver {s.usuarios.length} usuarios</summary>
          <div className="encuesta-revision__destinatarios">
            <ul className="mb-0">
              {s.usuarios.length > 0 ? s.usuarios.map((u) => <li key={u.id}>ID {u.id}: {u.username}{u.full_name ? <>{" "}· {u.full_name}</> : null}</li>) : <li>No hay usuarios cargados.</li>}
            </ul>
          </div>
        </details>
      )}
      {s?.tipo === "grupos" && (
        <>
          <p className="encuesta-meta">Usuarios que pertenezcan a cualquiera de estos grupos. La pertenencia se verifica al acceder y al responder.</p>
          <ul>{s.grupos.length > 0 ? s.grupos.map((g, i) => <li key={i}>{g}</li>) : <li>No hay grupos seleccionados.</li>}</ul>
        </>
      )}
      {todos && <p className="encuesta-meta mb-0">La encuesta estará disponible para todos los usuarios que inicien sesión.</p>}
    </>
  );
}

function PreguntaItem({ p }: { p: Pregunta }) {
  return (
    <div className="encuesta-revision__pregunta">
      <p className="encuesta-meta mb-1">Pregunta {p.numero} · {p.tipo_label} · {p.obligatoria ? "Obligatoria" : "Opcional"}</p>
      <h3>{p.texto}</h3>
      {p.condicion && <p className="encuesta-revision__nota">{p.condicion}</p>}
      {p.tipo === "si_no" ? (
        <ul className="encuesta-revision__opciones">
          <li>Sí{p.pondera && <>{" "}<span className="encuesta-meta">· {p.puntaje_si} puntos</span></>}</li>
          <li>No{p.pondera && <>{" "}<span className="encuesta-meta">· {p.puntaje_no} puntos</span></>}</li>
        </ul>
      ) : p.opciones.length > 0 ? (
        <ul className="encuesta-revision__opciones">
          {p.opciones.map((o, i) => <li key={i}>{o.texto}{p.pondera && <>{" "}<span className="encuesta-meta">· {o.puntaje} puntos</span></>}</li>)}
        </ul>
      ) : <p className="encuesta-meta mb-0">El usuario completará su respuesta al recibir la encuesta.</p>}
    </div>
  );
}

type Errors = { message: string }[];

function RechazoModal({ d, close, post, busy, errors, initial }: { d: RevisionData; close: () => void; post: (body: URLSearchParams) => void; busy: boolean; errors: Errors; initial: string }) {
  const area = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { area.current?.focus(); }, [errors]);
  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    post(new URLSearchParams(new FormData(e.currentTarget) as unknown as Record<string, string>));
  };
  return (
    <NativeModal id="rechazar-encuesta-modal" title="Rechazar solicitud de publicación" close={close} busy={busy} size=" modal-dialog-centered"
      controls="button:not([disabled]),textarea:not([disabled])">
      <div className="modal-content">
        <form method="post" onSubmit={submit}>
          <div className="modal-header">
            <h2 className="modal-title fs-5" id="rechazar-encuesta-titulo">Rechazar solicitud de publicación</h2>
            <button type="button" className="btn-close" aria-label="Cerrar" onClick={close}></button>
          </div>
          <div className="modal-body">
            <p>La encuesta <strong>{d.titulo}</strong> volverá a borrador. El gestor verá este motivo para realizar las correcciones.</p>
            <label htmlFor="id_motivo" className="form-label">Motivo del rechazo <span className="text-danger" aria-hidden="true">*</span></label>
            <textarea ref={area} name="motivo" cols={40} rows={5} className="form-control" id="id_motivo" required maxLength={2000} defaultValue={initial}
              placeholder="Explicá qué debe corregirse antes de volver a solicitar la publicación." aria-describedby="motivo-rechazo-ayuda motivo-rechazo-error"></textarea>
            <div id="motivo-rechazo-ayuda" className="form-text">Obligatorio. Máximo 2000 caracteres.</div>
            <div id="motivo-rechazo-error" className="text-danger" role="alert">
              {errors.length > 0 && <ul className="errorlist">{errors.map((e, i) => <li key={i}>{e.message}</li>)}</ul>}
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={busy}>Confirmar rechazo</button>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}

export function RevisionContent({ data }: { data: RevisionData }) {
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [errors, setErrors] = useState<Errors>([]);
  const [typed, setTyped] = useState("");
  const [toasts, setToasts] = useState<Message[]>(data.messages);
  const pendiente = data.estado === "pendiente_aprobacion";

  const send = async (url: string, body: URLSearchParams) => {
    setBusy(true);
    try {
      const { data: result, status } = await webClient.post(url, body, { validateStatus: (s) => accepted(s) || s === 400 });
      if (status === 200 && record(result) && result.ok === true && internal(result.redirect)) { window.location.assign(result.redirect); return; }
      if (status === 400 && record(result) && record(result.errors) && Array.isArray(result.errors.motivo)) {
        setErrors((result.errors.motivo as { message: string }[]).map((e) => ({ message: String(e.message) })));
        setTyped(body.get("motivo") ?? "");
        setOpen(true);
        resetAfterRejectedPost();
        setBusy(false);
        return;
      }
    } catch { /* uncertain outcome: reported below, never retried */ }
    setToasts([{ message: "No se pudo completar la operación.", level: "error" }]);
    setBusy(false);
  };
  const aprobar = (e: FormEvent) => { e.preventDefault(); void send(`web/encuestas/${data.id}/aprobar/`, new URLSearchParams()); };

  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/user_form.css" />
      <link rel="stylesheet" href="/static/custom/css/encuestaGestion.css" />
      <div className="encuesta-revision">
        <div className="encuesta-revision__cabecera">
          <Estado d={data} />
          <h1 className="mt-3 mb-2">{data.titulo}</h1>
          <p className="encuesta-meta mb-0">Versión {data.version} · Creada por {data.creador}</p>
        </div>
        <div className="encuesta-revision__layout">
          <div>
            <Motivo d={data} />
            <section className="card card-custom mb-3 shadow-sm" aria-labelledby="datos-encuesta">
              <div className="card-header card-header-custom"><h2 id="datos-encuesta"><i className="fas fa-file-alt" aria-hidden="true"></i>Datos de la encuesta</h2></div>
              <div className="card-body">
                {data.descripcion && <p className="mb-4">{data.descripcion.split(/\r\n|\r|\n/).map((line, i, all) => <Fragment key={i}>{line}{i < all.length - 1 && <br />}</Fragment>)}</p>}
                <dl className="encuesta-revision__datos">
                  <div><dt>Modalidad de respuesta</dt><dd>{data.modalidad}</dd></div>
                  <div><dt>Identidad de las respuestas</dt><dd>{data.es_anonima ? "Anónimas" : "Identificadas"}<span className="d-block">PWA de Espacios Comunitarios: {data.disponible_pwa ? "Habilitada" : "No habilitada"}</span></dd></div>
                  <div><dt>Duración de cada ronda</dt><dd>{data.duracion_ronda_dias} días</dd></div>
                  <div><dt>Frecuencia</dt><dd>{data.es_recurrente ? `Cada ${data.intervalo_recurrencia_dias} días` : "Una única ronda"}</dd></div>
                  {data.intervalo_recordatorio_dias > 0 && <div><dt>Recordatorio</dt><dd>Cada {data.intervalo_recordatorio_dias} días</dd></div>}
                </dl>
              </div>
            </section>
            <section className="card card-custom mb-3 shadow-sm" aria-labelledby="destinatarios-encuesta">
              <div className="card-header card-header-custom"><h2 id="destinatarios-encuesta"><i className="fas fa-users" aria-hidden="true"></i>¿Quiénes van a responder?</h2></div>
              <div className="card-body"><Destinatarios s={data.segmentacion} /></div>
            </section>
            <section className="card card-custom mb-3 shadow-sm" aria-labelledby="preguntas-encuesta">
              <div className="card-header card-header-custom"><h2 id="preguntas-encuesta"><i className="fas fa-list-ol" aria-hidden="true"></i>Preguntas ({data.preguntas.length})</h2></div>
              <div className="card-body">
                {data.preguntas.map((p) => <PreguntaItem key={p.numero} p={p} />)}
                {data.preguntas.length === 0 && <p className="mb-0">La encuesta todavía no tiene preguntas.</p>}
              </div>
            </section>
          </div>
          <aside className="encuesta-revision__decision">
            <section className="card card-custom mb-3 shadow-sm" aria-labelledby="decision-encuesta">
              <div className="card-header card-header-custom"><h2 id="decision-encuesta"><i className="fas fa-clipboard-check" aria-hidden="true"></i>Revisión de publicación</h2></div>
              <div className="card-body">
                {pendiente ? (
                  <>
                    <p>Revisá las preguntas y los destinatarios antes de resolver la solicitud.</p>
                    <dl className="mb-3">
                      <dt className="encuesta-meta">Solicitada por</dt><dd>{data.solicitada_por}</dd>
                      <dt className="encuesta-meta">Fecha de solicitud</dt><dd>{data.fecha_solicitud}</dd>
                    </dl>
                    <p className="encuesta-meta">El contenido queda bloqueado durante la revisión.</p>
                    {data.puede_aprobar ? (
                      <>
                        <form method="post" onSubmit={aprobar}>
                          <button type="submit" className="btn btn-primary w-100" disabled={busy}><i className="fas fa-check me-1" aria-hidden="true"></i>Aprobar y publicar</button>
                          <p className="encuesta-meta mt-2 mb-3">Publica la encuesta y habilita la primera ronda de respuestas.</p>
                        </form>
                        <button type="button" className="btn btn-secondary w-100" onClick={() => { setErrors([]); setTyped(""); setOpen(true); }}><i className="fas fa-undo me-1" aria-hidden="true"></i>Rechazar solicitud</button>
                        <p className="encuesta-meta mt-2 mb-0">Indicá el motivo para que el gestor sepa qué corregir.</p>
                      </>
                    ) : <p className="mb-0">Un administrador de encuestas debe aprobar o rechazar la solicitud.</p>}
                  </>
                ) : <p className="mb-0">Esta encuesta no tiene una solicitud pendiente de aprobación.</p>}
              </div>
            </section>
          </aside>
        </div>
      </div>
      {pendiente && data.puede_aprobar && open && (
        <RechazoModal d={data} close={() => setOpen(false)} busy={busy} errors={errors} initial={typed}
          post={(body) => void send(`web/encuestas/${data.id}/rechazar/`, body)} />
      )}
      <NativeToasts messages={toasts} />
    </>
  );
}

function RevisionPage({ id }: { id: string }) {
  const [state] = useMainResource(`web/encuestas/${id}/revision/`, revisionValid);
  return renderMain(state, "Cargando revisión…", (data) => ({
    title: "Revisar encuesta", heading: "Encuestas", activePath: "/encuestas/",
    breadcrumb: <Breadcrumb items={[{ text: "Encuestas", url: "/encuestas/" }, { text: "Revisar solicitud", url: null }]} />,
    content: <RevisionContent data={data} />,
  }));
}

export const encuestasRevisionRoute: RouteDefinition<{ id: string }> = {
  name: "encuestas-revision",
  match(pathname) {
    const found = /^\/encuestas\/([0-9]+)\/revision\/$/.exec(pathname);
    return found ? { id: found[1] } : null;
  },
  render: ({ id }) => <RevisionPage id={id} />,
};
