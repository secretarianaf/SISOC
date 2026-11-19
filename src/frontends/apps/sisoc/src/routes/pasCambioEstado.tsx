import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type RefObject } from "react";
import { createPortal } from "react-dom";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { prerequisiteFromForbidden } from "../webAccess";
import { accepted, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { PAS_API, list, shape } from "./pasFrame";
import { PanelContent, PanelHeader, panelEndpoint, panelValid, type PanelData, type PanelExtras, type Persona } from "./pasPanel";
import PasSelect2 from "./pasSelect2";

/**
 * PAS06.03: «Cambiar estado» of the panel (`persona_detail.html`, Bootstrap 5.3
 * modal) posting to `/api/web/pas/personas/<pk>/cambiar-estado/`. Like the
 * native view, success and every form error end on `pas/panel-control/<pk>`
 * with the message shown as a toast; a result that cannot be confirmed reloads
 * the panel instead of retrying.
 */
export type Notice = { message: string; level: "success" | "error" };
type Options = { estados: { id: number; nombre: string }[]; avisos_por_estado: Record<string, { id: number; text: string }[]> };
type Data = PanelData & { cambio_estado: Options };

const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";
const optionsValid = (v: unknown): v is Options => shape(v, {
  estados: list((e: unknown): e is object => shape(e, { id: (n) => Number.isSafeInteger(n), nombre: text })),
  avisos_por_estado: (m) => record(m) && Object.values(m).every(list((a: unknown): a is object => shape(a, { id: (n) => Number.isSafeInteger(n), text }))),
});
const dataValid = (v: unknown): v is Data => panelValid(v) && optionsValid((v as Record<string, unknown>).cambio_estado);

type Outcome = { kind: "done"; notices: Notice[] } | { kind: "forbidden"; data: unknown };

async function submit(persona: number, estado: string, avisos: string[]): Promise<Outcome> {
  const body = new URLSearchParams({ estado });
  for (const aviso of avisos) body.append("avisos", aviso);
  try {
    const { data, status } = await webClient.post(`${PAS_API}personas/${persona}/cambiar-estado/`, body, { validateStatus: accepted });
    if (status === 403) return { kind: "forbidden", data };
    if (record(data) && text(data.message)) return { kind: "done", notices: [{ message: data.message, level: "success" }] };
  } catch (error: unknown) {
    const response = (error as { response?: { status?: number; data?: unknown } }).response;
    if (response?.status === 400 && record(response.data) && Array.isArray(response.data.messages) && response.data.messages.every(text)) {
      return { kind: "done", notices: response.data.messages.map((message) => ({ message, level: "error" })) };
    }
  }
  return { kind: "done", notices: [{ message: UNCERTAIN, level: "error" }] };
}

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Bootstrap 5.3 modal: backdrop, `modal-open`, focus on the dialog, focus trap, Esc, return focus. */
function CambioEstadoModal({ data, persona, open, onClose, onDone, trigger }: {
  data: Data; persona: Persona; open: boolean; onClose: () => void; onDone: (o: Outcome) => void; trigger: RefObject<HTMLButtonElement | null>;
}) {
  const modal = useRef<HTMLDivElement>(null);
  const [parent, setParent] = useState<HTMLDivElement | null>(null);
  const [estado, setEstado] = useState("");
  const [avisos, setAvisos] = useState<string[]>([]);
  const busy = useRef(false);
  const wasOpen = useRef(false);
  useEffect(() => {
    if (!open) {
      if (wasOpen.current) trigger.current?.focus();
      wasOpen.current = false;
      return undefined;
    }
    wasOpen.current = true;
    const body = document.body;
    const scrollbar = window.innerWidth - document.documentElement.clientWidth;
    const padding = body.style.paddingRight;
    body.classList.add("modal-open");
    body.style.overflow = "hidden";
    body.style.paddingRight = `${(Number.parseFloat(getComputedStyle(body).paddingRight) || 0) + scrollbar}px`;
    modal.current?.focus();
    const lastTab = { current: "forward" as "forward" | "backward" };
    const trap = (event: FocusEvent) => {
      const root = modal.current;
      if (!root || root.contains(event.target as Node)) return;
      // Bootstrap FocusTrap: first (or last, going back) visible focusable child, else the dialog.
      const items = [...root.querySelectorAll<HTMLElement>(FOCUSABLE)].filter((el) => el.getClientRects().length > 0);
      if (!items.length) root.focus();
      else (lastTab.current === "backward" ? items[items.length - 1] : items[0]).focus();
    };
    const key = (event: globalThis.KeyboardEvent) => { if (event.key === "Tab") lastTab.current = event.shiftKey ? "backward" : "forward"; };
    document.addEventListener("focusin", trap);
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("focusin", trap);
      document.removeEventListener("keydown", key);
      body.classList.remove("modal-open");
      body.style.overflow = "";
      body.style.paddingRight = padding;
      if (!body.getAttribute("style")) body.removeAttribute("style");
    };
  }, [open, trigger]);

  const avisosDelEstado = data.cambio_estado.avisos_por_estado[estado] ?? [];
  function changeEstado(next: string[]) {
    const value = next[0] ?? "";
    setEstado(value);
    // `populateAvisos` keeps the selected notices that the new state also offers.
    const offered = new Set((data.cambio_estado.avisos_por_estado[value] ?? []).map((a) => String(a.id)));
    setAvisos((current) => current.filter((a) => offered.has(a)));
  }
  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true;
    const outcome = await submit(persona.id, estado, avisos);
    busy.current = false;
    onDone(outcome);
  }
  const keyDown = (event: KeyboardEvent<HTMLDivElement>) => { if (event.key === "Escape") { event.preventDefault(); onClose(); } };
  return <>
    <div ref={(el) => { modal.current = el; setParent((p) => p ?? el); }} className={`modal fade${open ? " show" : ""}`} id="cambiarEstadoModal" tabIndex={-1}
      aria-labelledby="cambiarEstadoModalLabel" aria-hidden={open ? undefined : "true"} aria-modal={open ? "true" : undefined} role={open ? "dialog" : undefined}
      style={open ? { display: "block" } : undefined} onKeyDown={keyDown}
      onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div className="modal-dialog modal-lg modal-dialog-centered">
        <div className="modal-content">
          <form method="post" action={`/pas/${persona.id}/cambiar-estado`} onSubmit={(e) => void send(e)}>
            <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
            <div className="modal-header">
              <h2 className="modal-title fs-5" id="cambiarEstadoModalLabel">Cambiar estado PAS</h2>
              <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Cerrar" onClick={onClose} />
            </div>
            <div className="modal-body">
              <p>Estado actual: <strong>{persona.estado.nombre}</strong></p>
              <div className="row">
                <div className="col-md-4"><div id="div_id_estado" className="mb-3">
                  <label htmlFor="id_estado" className="form-label requiredField">Nuevo estado<span className="asteriskField">*</span></label>{" "}
                  <PasSelect2 id="id_estado" name="estado" parent={parent} value={estado ? [estado] : []} onChange={changeEstado}
                    choices={[{ value: "", label: "Seleccione un estado" }, ...data.cambio_estado.estados.map((e) => ({ value: String(e.id), label: e.nombre }))]} />
                </div></div>
                <div className="col-md-8"><div id="div_id_avisos" className="mb-3">
                  <label htmlFor="id_avisos" className="form-label requiredField">Nuevos avisos<span className="asteriskField">*</span></label>{" "}
                  <PasSelect2 id="id_avisos" name="avisos" multiple parent={parent} value={avisos} onChange={setAvisos}
                    choices={avisosDelEstado.map((a) => ({ value: String(a.id), label: a.text }))} />
                </div></div>
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" data-bs-dismiss="modal" onClick={onClose}>Cancelar</button>{" "}
              <button type="submit" className="btn btn-primary">Guardar cambio</button>
            </div>
          </form>
        </div>
      </div>
    </div>
    {open && createPortal(<div className="modal-backdrop fade show" />, document.body)}
  </>;
}

function Panel({ id, notices, onDone }: { id?: string; notices: Notice[]; onDone: (pk: number, o: Outcome) => void }) {
  const [state, setState] = useMainResource(panelEndpoint(id), dataValid);
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  return renderMain(state, "Cargando panel…", (data) => {
    const extras: PanelExtras = {
      // `includes/base.html` loads Select2 and its theme before the page's `pas.css`.
      stylesheets: <>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css" />
        <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
      </>,
      notices: <InsumosToastList messages={notices} />,
      actions: () => <button ref={trigger} type="button" className="btn btn-warning" data-bs-toggle="modal" data-bs-target="#cambiarEstadoModal" onClick={() => setOpen(true)}>
        <i className="bi bi-arrow-left-right" aria-hidden="true" />{" "}Cambiar estado
      </button>,
      overlays: (_, persona) => <CambioEstadoModal data={data} persona={persona} open={open} trigger={trigger} onClose={() => setOpen(false)}
        onDone={(outcome) => {
          setOpen(false);
          if (outcome.kind === "forbidden") setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(outcome.data) });
          else onDone(persona.id, outcome);
        }} />,
    };
    return { title: "Panel de Control · PAS", breadcrumb: null, appHeader: <PanelHeader data={data} extras={extras} />, content: <PanelContent data={data} extras={extras} /> };
  });
}

/** The native view redirects to `pas/panel-control/<pk>` (without the list filters) after every POST. */
export default function PasPanelRoute({ id, notices = [] }: { id?: string; notices?: Notice[] }) {
  const [view, setView] = useState({ id, generation: 0, notices });
  return <Panel key={view.generation} id={view.id} notices={view.notices} onDone={(pk, outcome) => {
    if (outcome.kind !== "done") return;
    window.history.pushState({}, "", `/pas/panel-control/${pk}`);
    setView((v) => ({ id: String(pk), generation: v.generation + 1, notices: outcome.notices }));
  }} />;
}
