/**
 * A rejected post of the ficha modals (intervención / observación). The native page reloads as the
 * create form with the posted values and the errors; here the 400 body of the web API (the very
 * payload the create page's GET returns) waits in `sessionStorage` under the endpoint it came from,
 * and the browser goes to the create page. The create page takes it once with `tomarRechazo`
 * instead of asking the API for an empty form.
 */
const KEY = "sisoc:comedor-ficha:rechazo";

type Rechazo = { endpoint: string; payload: unknown };

/** True when the payload is stored; false (nothing to hand over) when storage is unavailable. */
export function guardarRechazo(endpoint: string, payload: unknown): boolean {
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify({ endpoint, payload } satisfies Rechazo));
    return true;
  } catch {
    return false;
  }
}

let taken: Rechazo | null = null;

/**
 * The stored payload of `endpoint`. It leaves the storage on the first read (a reload shows the empty
 * form, as reloading the native page would not re-post), but the page that took it can ask again, as
 * a remount does, until another endpoint asks. An invalid payload is ignored.
 */
export function tomarRechazo<T>(endpoint: string, valid: (v: unknown) => v is T): T | null {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    if (raw) {
      window.sessionStorage.removeItem(KEY);
      taken = JSON.parse(raw) as Rechazo;
    }
  } catch {
    taken = null;
  }
  if (taken && taken.endpoint !== endpoint) taken = null;
  return taken && valid(taken.payload) ? taken.payload : null;
}
