import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { crearCliente, leerCookie } from "@sisoc/api";
import InsumosAccessError from "./InsumosAccessError";
import { InsumosToastList } from "./InsumosToast";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "./webAccess";
import type { RequiredPasswordPresentation } from "./RequiredPasswordChange";

type Question = { id: number; order: number; text: string; type: string; required: boolean; condition: null | { order: number; operator: string; value: string }; options: { id: number; value: string; text: string }[] };
type Round = { id: number; title: string; description: string; mode: "obligatoria" | "opcional" | "postergable"; anonymous: boolean; questions: Question[]; actions: { answer: string; postpone: string | null; dismiss: string | null } };
type Metadata = { presentation: RequiredPasswordPresentation; home_variant: "default" | "inet"; round: Round | null; messages: { message: string; level: "success" | "error" | "warning" | "info" }[] };
type Props = { renderFrame?: (content: ReactNode, presentation: RequiredPasswordPresentation, overlays?: ReactNode) => ReactNode; navigate?: (destination: string) => void };
type State = { status: "loading" } | { status: "error" } | { status: "redirect" } | { status: "forbidden"; prerequisite: WebPrerequisite | null } | { status: "ready"; metadata: Metadata };
type Modal = { show(): void; hide(): void; dispose(): void };
type Bootstrap = { Modal: { getOrCreateInstance(element: HTMLElement): Modal } };
const client = crearCliente("/api");
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object";
const integer = (value: unknown) => typeof value === "number" && Number.isSafeInteger(value) && value > 0;
const order = (value: unknown) => typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const types = ["texto_corto", "texto_largo", "opcion_unica", "opcion_multiple", "escala", "si_no", "numerico", "fecha"];
const acceptedStatus = (status: number) => status >= 200 && status < 300 || status === 403;

function validMetadata(value: unknown): value is Metadata {
  if (!record(value) || !record(value.presentation) || !["default", "inet"].includes(value.home_variant as string) || !Array.isArray(value.messages)) return false;
  const frame = value.presentation;
  const node = (v: unknown): boolean => record(v) && typeof v.id === "string" && typeof v.label === "string" && (v.href === null || safeInternalPath(v.href) !== null) && Array.isArray(v.children) && v.children.every(node);
  if (!record(frame.user) || !["username", "display_name", "avatar_initial", "role_label"].every(key => typeof (frame.user as Record<string, unknown>)[key] === "string") || typeof frame.footer_version_label !== "string" || !Array.isArray(frame.legacy_frame_navigation) || !frame.legacy_frame_navigation.every(node) || !value.messages.every(v => record(v) && typeof v.message === "string" && ["success", "error", "warning", "info"].includes(v.level as string))) return false;
  if (value.round === null) return true;
  const round = value.round;
  if (!record(round) || !integer(round.id) || typeof round.title !== "string" || typeof round.description !== "string" || typeof round.anonymous !== "boolean" || !["obligatoria", "opcional", "postergable"].includes(round.mode as string) || !record(round.actions) || !Array.isArray(round.questions)) return false;
  return round.actions.answer === `/encuestas/responder/${round.id}/` && round.actions.postpone === (round.mode === "postergable" ? `/encuestas/responder/${round.id}/mas-tarde/` : null) && round.actions.dismiss === (round.mode === "opcional" ? `/encuestas/responder/${round.id}/descartar/` : null) && round.questions.every(q => record(q) && integer(q.id) && order(q.order) && typeof q.text === "string" && types.includes(q.type as string) && typeof q.required === "boolean" && (q.condition === null || record(q.condition) && order(q.condition.order) && ["igual", "distinto"].includes(q.condition.operator as string) && typeof q.condition.value === "string") && Array.isArray(q.options) && q.options.every(o => record(o) && integer(o.id) && typeof o.value === "string" && typeof o.text === "string"));
}

function loadScript(src: string, integrity?: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script"); script.src = src;
    if (integrity) { script.integrity = integrity; script.crossOrigin = "anonymous"; }
    script.onload = () => { script.remove(); resolve(); };
    script.onerror = () => { script.remove(); reject(new Error("Survey asset unavailable")); };
    document.body.appendChild(script);
  });
}
let bootstrapLoading: Promise<void> | undefined;
async function loadBootstrap() {
  if ((window as Window & { bootstrap?: Bootstrap }).bootstrap?.Modal) return;
  // Exact legacy mainscripts resource; no alternate version or widget library.
  bootstrapLoading ??= loadScript("https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.min.js", "sha256-YMa+wAM6QkVyz999odX7lPRxkoYAan8suedu4k2Zur8=");
  await bootstrapLoading;
}

export default function PendingSurvey({ renderFrame, navigate }: Props) {
  const [state, setState] = useState<State>({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController(); let active = true;
    client.get("web/surveys/pending/", { signal: controller.signal, validateStatus: acceptedStatus }).then(({ data, status }: { data: unknown; status?: number }) => {
      if (!active) return;
      if (status === 403) setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(data) });
      else setState(validMetadata(data) ? { status: "ready", metadata: data } : { status: "error" });
    }).catch(() => { if (active) setState({ status: "error" }); });
    return () => { active = false; controller.abort(); };
  }, []);
  if (state.status === "loading" || state.status === "redirect") return <main role="status">{state.status === "loading" ? "Cargando inicio…" : "Continuando en SISOC…"}</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar la encuesta pendiente.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  const data = state.metadata;
  const content = <>
    <link rel="stylesheet" href="/static/custom/css/inicio.css" />
    <div className={`inicio-presentacion inicio-presentacion--${data.home_variant}`}>
      <div className="card-body d-flex align-items-center justify-content-center">
        {data.home_variant === "inet" && <div className="inicio-presentacion__inet-card"><img src="/static/custom/img/LOGOS-INET-SE_BLANCO.png" alt="INET Secretaría de Educación" className="inicio-presentacion__inet-logo" /></div>}
      </div>
    </div>
  </>;
  const overlays = <>
    <InsumosToastList messages={data.messages} />
    {data.round && <SurveyModal round={data.round}
      forbidden={value => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(value) })}
      completed={destination => { setState({ status: "redirect" }); (navigate ?? window.location.assign.bind(window.location))(destination); }} />}
  </>;
  return renderFrame ? renderFrame(content, data.presentation, overlays) : <main>{content}{overlays}</main>;
}

function SurveyModal({ round, completed, forbidden }: { round: Round; completed: (destination: string) => void; forbidden: (value: unknown) => void }) {
  const element = useRef<HTMLDivElement>(null); const active = useRef(false); const submitting = useRef(false);
  const [pending, setPending] = useState(false); const [uncertain, setUncertain] = useState(false); const [assetError, setAssetError] = useState(false);
  useEffect(() => {
    active.current = true; let cancelled = false;
    loadBootstrap().then(async () => {
      if (cancelled) return;
      // Reuse source visibility, disabled-field, focus and Bootstrap behavior.
      await loadScript("/static/custom/js/encuestaPendienteModal.js");
    }).catch(() => { if (!cancelled) setAssetError(true); });
    const modalElement = element.current;
    return () => {
      active.current = false; cancelled = true;
      const bootstrap = (window as Window & { bootstrap?: Bootstrap }).bootstrap;
      if (modalElement && bootstrap?.Modal) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        if (modalElement.classList.contains("show")) { modalElement.addEventListener("hidden.bs.modal", () => modal.dispose(), { once: true }); modal.hide(); }
        else modal.dispose();
      }
    };
  }, []);
  async function submit(event: FormEvent<HTMLFormElement>, action: "answer" | "postpone" | "dismiss") {
    event.preventDefault();
    if (submitting.current || uncertain || assetError || !round.actions[action]) return;
    const body = new URLSearchParams();
    new FormData(event.currentTarget).forEach((value, name) => { if (typeof value === "string") body.append(name, value); });
    submitting.current = true; setPending(true);
    try {
      const { data, status } = await client.post(`web/surveys/${round.id}/${action}/`, body, { validateStatus: acceptedStatus });
      if (!active.current) return;
      if (status === 403) { forbidden(data); return; }
      if (!record(data) || typeof data.redirect !== "string") throw new Error("Invalid survey response");
      const target = new URL(data.redirect, window.location.href);
      if (target.origin !== window.location.origin || target.username || target.password || !safeInternalPath(target.pathname + target.search + target.hash)) throw new Error("Unsafe survey destination");
      completed(target.pathname + target.search + target.hash);
    } catch { if (active.current) { setUncertain(true); setPending(false); } }
  }
  const hidden = <><input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} /><input type="hidden" name="next" value={window.location.pathname} /></>;
  const disabled = pending || uncertain || assetError;
  return <>
    <link rel="stylesheet" href="/static/custom/css/comedoresSearchBar.css" />
    <link rel="stylesheet" href="/static/custom/css/encuestaResponder.css" />
    {assetError && <p role="alert">No se pudo cargar el formulario. <a href="/inicio/">Volver al inicio</a></p>}
    <div ref={element} className="modal fade" id="modal-encuesta-pendiente" tabIndex={-1} aria-labelledby="modal-encuesta-pendiente-label" aria-hidden="true" data-bs-backdrop={round.mode === "obligatoria" ? "static" : undefined} data-bs-keyboard={round.mode === "obligatoria" ? "false" : undefined}>
      <div className="modal-dialog modal-dialog-centered modal-dialog-scrollable modal-lg"><div className="modal-content">
        <div className="modal-header"><div>
          <div className="encuesta-responder-etiqueta"><i className="fas fa-clipboard-list" aria-hidden="true" /> Encuesta</div>
          <h2 className="modal-title" id="modal-encuesta-pendiente-label">{round.title}</h2>
          <div className="encuesta-responder-datos"><span>{round.mode.charAt(0).toUpperCase() + round.mode.slice(1)}</span>{round.anonymous && <span><i className="fas fa-user-shield" aria-hidden="true" /> Respuestas anónimas</span>}</div>
        </div>{round.mode !== "obligatoria" && <button type="button" className="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Cerrar" />}</div>
        <div className="modal-body">
          {uncertain && <p role="alert">No se pudo confirmar el resultado. No vuelva a enviar la solicitud. <a href="/inicio/">Volver al inicio</a></p>}
          {round.description && <p className="encuesta-responder-descripcion">{round.description}</p>}
          <p className="encuesta-responder-ayuda">Las preguntas marcadas con * requieren una respuesta. {round.mode === "opcional" ? "Podés elegir no responder. No volverá a aparecer en esta ronda." : round.mode === "obligatoria" ? "Completá la encuesta para continuar usando el sistema." : ""}</p>
          <form method="post" action={round.actions.answer} id="form-responder-encuesta" onSubmit={event => void submit(event, "answer")}>{hidden}
            {round.questions.map((question, index) => <fieldset key={question.id} className="pregunta-respuesta" data-orden={question.order} data-condicion-orden={question.condition?.order} data-condicion-operador={question.condition?.operator} data-condicion-valor={question.condition?.value}>
              <legend id={`pregunta-titulo-${question.id}`}><span className="encuesta-responder-numero" aria-hidden="true">{index + 1}</span>{" "}{question.text}{" "}{question.required && <span className="encuesta-responder-requerida">*</span>}</legend>
              {question.type === "opcion_multiple" && <p className="encuesta-responder-ayuda">Podés seleccionar más de una opción.</p>}
              {question.type === "escala" && <p className="encuesta-responder-ayuda">Ingresá un valor del 1 al 10.</p>}
              <QuestionInput question={question} />
            </fieldset>)}
          </form>
        </div>
        <div className="modal-footer">
          {round.actions.dismiss && <form method="post" action={round.actions.dismiss} onSubmit={event => void submit(event, "dismiss")}>{hidden}<button type="submit" disabled={disabled} className="poncho-btn poncho-btn--neutro">Prefiero no responder</button></form>}
          {round.actions.postpone && <form method="post" action={round.actions.postpone} onSubmit={event => void submit(event, "postpone")}>{hidden}<button type="submit" disabled={disabled} className="poncho-btn poncho-btn--neutro"><i className="far fa-clock" aria-hidden="true" /> Responder más tarde</button></form>}
          <button type="submit" form="form-responder-encuesta" disabled={disabled} className="poncho-btn poncho-btn--cta"><i className="fas fa-paper-plane" aria-hidden="true" /> Enviar respuestas</button>
        </div>
      </div></div>
    </div>
  </>;
}

function QuestionInput({ question }: { question: Question }) {
  const common = { name: `respuesta-${question.id}`, required: question.required };
  if (question.type === "texto_largo") return <textarea {...common} className="form-control" rows={3} />;
  if (question.type === "si_no") return <select {...common} className="form-select" defaultValue=""><option value="">Seleccioná...</option><option value="si">Sí</option><option value="no">No</option></select>;
  if (question.type === "opcion_unica" || question.type === "opcion_multiple") {
    const multiple = question.type === "opcion_multiple";
    return <>{question.options.map(option => <div className="form-check" key={option.id}><input className={`form-check-input${multiple ? " toggle-switch" : ""}`} type={multiple ? "checkbox" : "radio"} role={multiple ? "switch" : undefined} name={common.name} required={!multiple && question.required} value={option.value} id={`opcion-${option.id}`} /><label className="form-check-label" htmlFor={`opcion-${option.id}`}>{option.text}</label></div>)}</>;
  }
  return <input {...common} className="form-control" type={question.type === "fecha" ? "date" : ["escala", "numerico"].includes(question.type) ? "number" : "text"} min={question.type === "escala" ? 1 : undefined} max={question.type === "escala" ? 10 : undefined} step={question.type === "numerico" ? "any" : undefined} />;
}
