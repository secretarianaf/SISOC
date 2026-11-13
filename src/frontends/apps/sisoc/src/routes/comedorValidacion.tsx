/* eslint-disable react-refresh/only-export-components -- the module exports its validators and navigation seam for the unit tests. */
import { useEffect, useState, type FormEvent } from "react";
import { accepted, internal, record, text, webClient } from "./MainFrame";
import { NativeModal, NativeToasts } from "./nativeParity";
import Select2, { type Choice } from "./select2";

/**
 * CO07.03 validation of a comedor: the two modals of `comedor_detail.html` («Validación del Comedor» and
 * «Motivos de No Validación») over the native `validar_comedor` POST. The ficha owns the trigger button
 * (`header.validar`) and mounts this component with `open`; the capability and the choices come from the
 * server (`GET web/comedores/comedores/<id>/validacion/`), React never replicates the role set.
 *
 * Like the native flow, a POST ends in a full-page navigation to the ficha, which shows the flash message
 * (accepted, refused or "no capability"). Cancelling never posts.
 */
export type ValidacionData = { id: number; puede_validar: boolean; opciones: Choice[]; urls: { ficha: string } };

export function validacionValid(v: unknown): v is ValidacionData {
  return record(v) && typeof v.id === "number" && typeof v.puede_validar === "boolean" && record(v.urls) && internal(v.urls.ficha) &&
    Array.isArray(v.opciones) && v.opciones.every((o) => record(o) && text(o.value) && text(o.label));
}

/** Full-page navigation after the POST; replaceable in tests. */
export const comedorValidacionNavigation = { assign: (to: string) => window.location.assign(to) };

const FAILED = { message: "No se pudo registrar la validación. Recargá la página para ver el estado actual.", level: "error" as const };
const LOAD_FAILED = { message: "No se pudo cargar la validación del comedor. Recargá la página e intentá de nuevo.", level: "error" as const };
const MODAL_CONTROLS = "button:not([disabled]),input:not([disabled]),textarea:not([disabled])";

function Header({ id, title, close }: { id: string; title: string; close: () => void }) {
  return (
    <div className="modal-header">
      <h5 className="modal-title" id={`${id}Label`}>{title}</h5>
      <button type="button" className="btn-close" aria-label="Close" onClick={close} />
    </div>
  );
}

function ElegirModal({ busy, validar, noValidar, close }: { busy: boolean; validar: () => void; noValidar: () => void; close: () => void }) {
  return (
    <NativeModal id="modalValidacion" title="Validación del Comedor" close={close} busy={busy} size=" modal-dialog-centered" controls={MODAL_CONTROLS}>
      <div className="modal-content">
        <Header id="modalValidacion" title="Validación del Comedor" close={close} />
        <div className="modal-body text-center">
          <p className="mb-4">Seleccione una opción para validar el comedor:</p>
          <div className="d-grid gap-2">
            <button type="button" className="btn btn-success btn-lg" disabled={busy} onClick={validar}>Validar</button>
            <button type="button" className="btn btn-danger btn-lg" disabled={busy} onClick={noValidar}>No Validar</button>
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
        </div>
      </div>
    </NativeModal>
  );
}

function NoValidarModal({ opciones, busy, submit, close }: { opciones: Choice[]; busy: boolean; submit: (opciones: string[], comentario: string) => void; close: () => void }) {
  const [chosen, setChosen] = useState<string[]>([]);
  const [comentario, setComentario] = useState("");
  const [parent, setParent] = useState<HTMLElement | null>(null);
  const otro = chosen.includes("otro");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    // Native `validarFormNoValidar`: the same alerts, and nothing is posted while one applies.
    if (chosen.length === 0) { window.alert("Debe seleccionar al menos una opción."); return; }
    if (otro && !comentario.trim()) { window.alert('El comentario es obligatorio cuando selecciona "Otro".'); return; }
    submit(chosen, otro ? comentario : "");
  }

  return (
    <NativeModal id="modalNoValidar" title="Motivos de No Validación" close={close} busy={busy} size=" modal-dialog-centered" controls={MODAL_CONTROLS}>
      <div className="modal-content">
        <form method="post" id="formNoValidar" onSubmit={onSubmit} noValidate ref={(el) => setParent(el?.closest<HTMLElement>(".modal") ?? null)}>
          <Header id="modalNoValidar" title="Motivos de No Validación" close={close} />
          <div className="modal-body">
            <div className="mb-3">
              <label htmlFor="opcionesSelect" className="form-label">Seleccione uno o más motivos: *</label>
              <Select2 id="opcionesSelect" name="opciones" multiple choices={opciones} value={chosen} onChange={setChosen}
                placeholder="Seleccione una o más opciones..." selectClassName="form-control" noResults="No se encontraron resultados"
                focusMarker="search" termHandling="keep" enterOnSelected="close" removeOpensResults clearTrigger="click" outsideClick="results" dropdownParent={parent} />
            </div>
            <div className={`mb-3${otro ? "" : " d-none"}`} id="comentarioDiv">
              <label htmlFor="comentario" className="form-label">Comentario: *</label>
              <textarea className="form-control" id="comentario" name="comentario" rows={3} placeholder="Especifique el motivo..."
                required={otro} value={comentario} onChange={(e) => setComentario(e.target.value)} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>{" "}
            <button type="submit" className="btn btn-danger" disabled={busy}>No Validar</button>
          </div>
        </form>
      </div>
    </NativeModal>
  );
}

type Message = { message: string; level: "error" };

export default function ComedorValidacion({ comedorId, open, onClose }: { comedorId: number; open: boolean; onClose: () => void }) {
  const [data, setData] = useState<ValidacionData | null>(null);
  const [step, setStep] = useState<"elegir" | "no-validar">("elegir");
  const [busy, setBusy] = useState(false);
  const [toasts, setToasts] = useState<Message[]>([]);

  useEffect(() => {
    if (!open || data) return undefined;
    let active = true;
    webClient.get(`web/comedores/comedores/${comedorId}/validacion/`, { validateStatus: accepted }).then(({ data: body }) => {
      if (!active) return;
      if (validacionValid(body) && body.puede_validar) setData(body);
      else { setToasts([LOAD_FAILED]); onClose(); }
    }).catch(() => { if (active) { setToasts([LOAD_FAILED]); onClose(); } });
    return () => { active = false; };
  }, [open, data, comedorId, onClose]);

  async function post(fields: URLSearchParams) {
    if (!data) return;
    setBusy(true);
    fields.set("next", data.urls.ficha);
    try {
      const { data: body, status } = await webClient.post(`web/comedores/comedores/${comedorId}/validar/`, fields, { validateStatus: accepted });
      if (status === 200 && record(body) && internal(body.redirect)) { comedorValidacionNavigation.assign(body.redirect); return; }
      setToasts([FAILED]);
    } catch {
      // Network error or 5xx/504: the outcome is uncertain, nothing is retried.
      setToasts([FAILED]);
    }
    setBusy(false);
  }

  const close = () => { setStep("elegir"); onClose(); };

  const noValidar = (opciones: string[], comentario: string) => {
    const fields = new URLSearchParams({ accion: "no_validar", comentario });
    opciones.forEach((o) => fields.append("opciones", o));
    void post(fields);
  };

  return (
    <>
      {toasts.length > 0 && <NativeToasts messages={toasts} />}
      {open && data && step === "elegir" && (
        <ElegirModal busy={busy} close={close} validar={() => void post(new URLSearchParams({ accion: "validar" }))} noValidar={() => setStep("no-validar")} />
      )}
      {open && data && step === "no-validar" && <NoValidarModal opciones={data.opciones} busy={busy} close={close} submit={noValidar} />}
    </>
  );
}
