import { leerCookie } from "@sisoc/api";

/** Only same-origin absolute paths; blocks protocol-relative and backslash tricks. */
export function internal(url: string) {
  if (!url.startsWith("/") || url.startsWith("//") || url.includes("\\")) throw new Error("URL de navegación inválida.");
  return url;
}

export class CanonicalError extends Error {
  constructor(message: string, readonly status: number) { super(message); }
}

/**
 * Reads the private JSON projection of the current canonical URL (or `url`).
 * Django authorizes it with the same guard as the HTML screen.
 */
export async function loadProjection<T>(url = window.location.pathname + window.location.search, signal?: AbortSignal): Promise<T> {
  const response = await fetch(internal(url), { credentials: "same-origin", headers: { Accept: "application/json" }, signal });
  if (!response.ok) {
    const message = response.status === 403 ? "No tiene permiso para ver esta pantalla." : response.status === 404 ? "No se encontró el recurso solicitado." : `No se pudo cargar la pantalla (${response.status}).`;
    throw new CanonicalError(message, response.status);
  }
  return await response.json() as T;
}

/**
 * Sends a mutation to a native Django endpoint with the session CSRF token.
 * Never retries: a transport failure after dispatch may have been committed.
 */
export async function sendNative(url: string, method: "POST" | "DELETE" | "PUT" | "PATCH", body?: URLSearchParams | FormData, accept = "application/json") {
  const headers: Record<string, string> = { "X-CSRFToken": leerCookie("csrftoken") ?? "", "X-Requested-With": "XMLHttpRequest", Accept: accept };
  if (body instanceof URLSearchParams) headers["Content-Type"] = "application/x-www-form-urlencoded";
  return fetch(internal(url), { method, credentials: "same-origin", headers, body });
}
