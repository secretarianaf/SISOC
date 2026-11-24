/* eslint-disable react-refresh/only-export-components -- the unit surface is this module: the modal and its navigation seam. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import { NativeModal, NativeToasts } from "./nativeParity";
import { accepted, internal, record, text, webClient } from "./MainFrame";

/**
 * «Seleccione el tipo de Admisión» (`#modalAdmision` of `comedor_detail.html`), opened
 * from «Comenzar Admisión». The POST goes to
 * `/api/web/comedores/comedores/<pk>/admision/`, which runs the native service: it
 * answers with a redirect to the ficha either way (created, or refused with a message
 * the ficha shows), exactly as the native form did.
 */
export const admisionNavigation = { assign: (to: string) => window.location.assign(to) };

const UNCERTAIN = { message: "No se pudo confirmar el resultado. Revisá las admisiones del comedor antes de volver a intentar.", level: "error" as const };

export function AdmisionModal({ comedorId, close }: { comedorId: number; close: () => void }) {
  const [busy, setBusy] = useState(false);
  const [toasts, setToasts] = useState<{ message: string; level: "error" }[]>([]);
  const inFlight = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current) return;
    const tipo = new FormData(event.currentTarget).get("admision");
    inFlight.current = true; setBusy(true); setToasts([]);
    try {
      const body = new URLSearchParams({ admision: typeof tipo === "string" ? tipo : "" });
      const { data, status } = await webClient.post(`web/comedores/comedores/${comedorId}/admision/`, body, { validateStatus: accepted });
      if (status === 403) {
        setToasts([{ message: record(data) && text(data.detail) ? data.detail : UNCERTAIN.message, level: "error" }]);
        return;
      }
      if (record(data) && typeof data.created === "boolean" && internal(data.redirect)) {
        // Created or refused: the native page redirects to the ficha, which shows the queued message.
        admisionNavigation.assign(data.redirect);
        return;
      }
      setToasts([UNCERTAIN]);
    } catch {
      // Network error or 5xx/504: the outcome is uncertain and nothing is retried.
      setToasts([UNCERTAIN]);
    } finally { inFlight.current = false; setBusy(false); }
  }
  return (
    <>
      {toasts.length > 0 && <NativeToasts messages={toasts.filter((t) => text(t.message))} />}
      <NativeModal id="modalAdmision" title="Seleccione el tipo de Admisión" close={close} busy={busy} size=" modal-dialog-centered"
        controls="button:not([disabled]),select:not([disabled])">
        <div className="modal-content">
          <form method="POST" action="" onSubmit={(e) => void submit(e)}>
            <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
            <div className="modal-header">
              <h5 className="modal-title">Seleccione el tipo de Admisión</h5>
              <button type="button" className="btn-close" aria-label="Close" onClick={close} disabled={busy} />
            </div>
            <div className="modal-body">
              <select name="admision" id="admisionID" className="form-control form-select" required defaultValue="">
                <option value="" disabled>-- Seleccione --</option>
                <option value="incorporacion">Incorporación</option>
                <option value="renovacion">Renovación</option>
              </select>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={close} disabled={busy}>Cancelar</button>{" "}
              <button type="submit" className="btn btn-primary" id="seleccionAdmision" disabled={busy}>Seleccionar</button>
            </div>
          </form>
        </div>
      </NativeModal>
    </>
  );
}
