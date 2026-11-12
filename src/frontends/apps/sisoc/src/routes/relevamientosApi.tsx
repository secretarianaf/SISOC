import { useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { InsumosToastList } from "../InsumosToast";
import { internal, record, text, webClient } from "./MainFrame";

/**
 * Mutations of the relevamiento pages (R01.02) through
 * `/api/web/comedores/relevamientos/`: a POST with the native field names and
 * `X-CSRFToken`, never retried. `{ok, message, redirect}` is a success; a 504
 * `{uncertain: true}` (or a lost connection) is shown as "No se pudo confirmar
 * el resultado." and the page is reloaded, never resubmitted.
 */
export type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export type PostResult =
  | { kind: "ok"; message: string; redirect: string; body: Record<string, unknown> }
  | { kind: "error"; message: string }
  | { kind: "invalid"; body: Record<string, unknown> }
  | { kind: "uncertain" };

export const UNCERTAIN = "No se pudo confirmar el resultado.";
const FLASH_KEY = "sisoc.relevamientos.flash";

/** Replaceable in tests. */
export const relevamientosNavigation = { assign: (to: string) => window.location.assign(to) };

export function setFlash(messages: Message[]) {
  try { window.sessionStorage.setItem(FLASH_KEY, JSON.stringify(messages)); } catch { /* the message is optional */ }
}

/** The messages a mutation queued for the next screen, read once. */
export function takeFlash(): Message[] {
  try {
    const raw = window.sessionStorage.getItem(FLASH_KEY);
    window.sessionStorage.removeItem(FLASH_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((m): m is Message => record(m) && text(m.message) && ["success", "error", "warning", "info"].includes(m.level as string)) : [];
  } catch { return []; }
}

function firstError(body: unknown): string {
  if (!record(body)) return "";
  if (text(body.detail)) return body.detail;
  if (record(body.errors)) {
    for (const list of Object.values(body.errors)) {
      if (Array.isArray(list) && record(list[0]) && text(list[0].message)) return list[0].message;
    }
  }
  return "";
}

/** `endpoint` is an absolute API path (`/api/web/...`, as the payloads carry it) or already relative to the client base `/api`. */
export async function postApi(endpoint: string, body: URLSearchParams): Promise<PostResult> {
  try {
    const { data, status } = await webClient.post(endpoint.replace(/^\/api\//, ""), body, { validateStatus: () => true });
    if (status === 200 && record(data) && data.ok === true && text(data.message) && internal(data.redirect)) return { kind: "ok", message: data.message, redirect: data.redirect, body: data };
    // A form the server re-rendered with its bound errors (`detail` + descriptors).
    if (status === 400 && record(data) && text(data.detail) && !record(data.errors)) return { kind: "invalid", body: data };
    if (status === 504 || (record(data) && data.uncertain === true)) return { kind: "uncertain" };
    return { kind: "error", message: firstError(data) || "No se pudo completar la operación." };
  } catch {
    return { kind: "uncertain" };
  }
}

/**
 * After a form is re-rendered with its errors the native page has been reloaded: the view starts at
 * the top and keyboard focus at the start of the document, so do the same.
 */
export function restartFromTop() {
  window.scrollTo(0, 0);
  const marker = document.createElement("span");
  marker.tabIndex = -1;
  document.body.prepend(marker);
  marker.focus({ preventScroll: true });
  marker.remove();
}

/** The toasts of a screen: the ones its data carried, the flash of the previous mutation and the new ones. */
export function useToasts(initial: Message[]) {
  const [state, setState] = useState<{ version: number; messages: Message[] }>(() => ({ version: 0, messages: [...initial, ...takeFlash()] }));
  const push = (message: Message) => setState((s) => ({ version: s.version + 1, messages: [message] }));
  // Toastr appends its container to the end of `<body>`: the toasts go to the same place.
  const toasts: ReactNode = createPortal(<InsumosToastList key={state.version} messages={state.messages} />, document.body);
  return { toasts, push };
}
