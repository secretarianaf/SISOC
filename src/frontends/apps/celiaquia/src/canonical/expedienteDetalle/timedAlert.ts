/**
 * Success alerts that survive a reload, shared with the native page
 * (`queueTimedAlert` in static/custom/js/expediente_detail.js): same storage
 * key, same `{kind, message, expiresAt}` shape, localStorage with a
 * sessionStorage fallback, and every storage failure is ignored.
 */
export const TIMED_ALERT_DURATION_MS = 120000;

export type TimedAlert = { kind: string; message: string; expiresAt: number };

function storage(): Storage | null {
  try {
    if (window.localStorage) return window.localStorage;
  } catch { /* fall back to sessionStorage */ }
  try {
    if (window.sessionStorage) return window.sessionStorage;
  } catch { /* no storage available */ }
  return null;
}

const key = (expedienteId: string) => `expediente-detail-timed-alert:${expedienteId}`;

/** The expediente pk from the canonical URL, as the native `expediente-id` meta. */
export function expedienteIdFromPath(pathname = window.location.pathname) {
  return pathname.match(/\/expedientes\/(\d+)/)?.[1] ?? "default";
}

export function queueTimedAlert(expedienteId: string, kind: string, message: string, durationMs = TIMED_ALERT_DURATION_MS) {
  try {
    storage()?.setItem(key(expedienteId), JSON.stringify({ kind, message, expiresAt: Date.now() + durationMs }));
  } catch { /* storage unavailable: the flow continues */ }
}

export function readTimedAlert(expedienteId: string): TimedAlert | null {
  const store = storage();
  if (!store) return null;
  try {
    const raw = store.getItem(key(expedienteId));
    if (!raw) return null;
    const alert = JSON.parse(raw) as Partial<TimedAlert>;
    if (!alert?.expiresAt || alert.expiresAt <= Date.now()) {
      store.removeItem(key(expedienteId));
      return null;
    }
    return alert.kind && alert.message ? (alert as TimedAlert) : null;
  } catch {
    return null;
  }
}

export function clearTimedAlert(expedienteId: string) {
  try {
    storage()?.removeItem(key(expedienteId));
  } catch { /* ignore storage errors */ }
}
