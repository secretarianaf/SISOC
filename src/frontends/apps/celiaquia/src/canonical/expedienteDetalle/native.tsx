import { useEffect, useId, useRef, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { internal, sendNative } from "../transport";

/** Native JSON endpoints answer `{success, message|error}`; anything else is a rejection. */
export type NativeResult = Record<string, unknown> & { success?: boolean; message?: string; error?: string };

/** A native rejection that keeps the response body (e.g. `saved_partial`, `invalid_fields`). */
export class NativeError extends Error {
  readonly data: NativeResult;
  constructor(message: string, data: NativeResult) {
    super(message);
    this.data = data;
  }
}

async function readResult(response: Response): Promise<NativeResult> {
  if (response.redirected) throw new Error("Tu sesión expiró o no tenés permisos. Volvé a iniciar sesión.");
  const type = response.headers?.get?.("Content-Type") ?? "application/json";
  const data: NativeResult = type.includes("application/json") ? await response.json() : {};
  if (!response.ok || data.success === false) {
    throw new NativeError(String(data.error || data.message || `La acción fue rechazada (${response.status}).`), data);
  }
  return data;
}

/** POST to a native endpoint with the session CSRF token. Never retried. */
export async function postNative(url: string, body?: FormData | URLSearchParams) {
  return readResult(await sendNative(url, "POST", body));
}

/** POST a JSON body (registros erróneos expect it) with the same guarantees. */
export async function postNativeJson(url: string, body: Record<string, string>) {
  return readResult(await fetch(internal(url), {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": leerCookie("csrftoken") ?? "", "X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  }));
}

/** GET an auxiliary native JSON endpoint (comments, motive preview, legajo data). */
export async function getNative(url: string) {
  return readResult(await fetch(internal(url), {
    credentials: "same-origin",
    headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
  }));
}

export function formatDate(value: string | null, withTime = false) {
  if (!value) return "-";
  const date = new Date(value);
  return withTime ? date.toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" }) : date.toLocaleDateString("es-AR");
}

/** Accessible modal: labelled, focus moves inside, Escape and backdrop close it. */
export function Modal({ title, onClose, children, footer, wide }: { title: string; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean }) {
  const id = useId();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const first = ref.current?.querySelector<HTMLElement>("input:not([type=hidden]),select,textarea,button");
    first?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); previous?.focus?.(); };
  }, [onClose]);
  return <div className="ed-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={id} className={wide ? "ed-dialog ed-wide" : "ed-dialog"}>
      <header><h2 id={id}>{title}</h2><button type="button" onClick={onClose} aria-label="Cerrar">×</button></header>
      <div className="ed-dialog-body">{children}</div>
      {footer && <footer>{footer}</footer>}
    </div>
  </div>;
}

export function ErrorText({ error }: { error: string }) {
  return error ? <p role="alert" className="ed-alert ed-danger">{error}</p> : null;
}
