/**
 * React port of the system-wide "Volver" (src/backends/kernel/static/custom/js/volver.js, issue #2460).
 *
 * Both share the `sisocNavStack` sessionStorage stack, so the button resolves the same destination
 * whether the previous screen was a Django template or a React page. Resolution order:
 * declared `volver_url` (enriched with its stacked querystring) → previous stacked screen →
 * same-origin referrer → `/`. It never calls `history.back()` (an external referrer would leave SISOC).
 */
import { safeInternalPath } from "./webAccess";

const STACK_KEY = "sisocNavStack";
const MAX_ENTRIES = 25;
// Native marks form/delete views server-side; React pages infer it from the path (create, edit, delete steps).
const TRANSIENT_PATH = /\/(crear|nuev[oa]|editar|eliminar|borrar|create|new|edit|update|delete)(\/|$)/i;

const currentUrl = () => window.location.pathname + window.location.search;
const pathOnly = (url: string) => url.split("?")[0];

function readStack(): string[] {
  try {
    const stack: unknown = JSON.parse(window.sessionStorage.getItem(STACK_KEY) ?? "[]");
    return Array.isArray(stack) ? stack.filter((entry): entry is string => typeof entry === "string") : [];
  } catch {
    return [];
  }
}

function saveStack(stack: string[]) {
  try {
    window.sessionStorage.setItem(STACK_KEY, JSON.stringify(stack));
  } catch {
    // Private mode or full storage: the button still works through its fallbacks.
  }
}

/** Stacks the current screen with the same rules as volver.js (no transient steps, no repeats, zigzag pops). */
export function registerVisit() {
  if (TRANSIENT_PATH.test(window.location.pathname)) return;
  const stack = readStack();
  const current = currentUrl();
  if (stack[stack.length - 1] === current) return;
  if (stack.length > 1 && stack[stack.length - 2] === current) {
    stack.pop();
    saveStack(stack);
    return;
  }
  stack.push(current);
  saveStack(stack.slice(-MAX_ENTRIES));
}

function declaredDestination(fallback?: string): string | null {
  const declared = safeInternalPath(fallback);
  if (!declared) return null;
  const path = pathOnly(declared);
  return [...readStack()].reverse().find((entry) => pathOnly(entry) === path) ?? declared;
}

function previousDestination(): string | null {
  const current = currentUrl();
  return [...readStack()].reverse().find((entry) => entry !== current) ?? null;
}

function internalReferrer(): string | null {
  if (!document.referrer) return null;
  try {
    const referrer = new URL(document.referrer);
    if (referrer.origin !== window.location.origin) return null;
    const destination = referrer.pathname + referrer.search;
    return destination === currentUrl() ? null : destination;
  } catch {
    return null;
  }
}

/** Destination of "Volver" for the current screen; `declared` is the page's hierarchical `volver_url`. */
export function resolveBackHref(declared?: string): string {
  return declaredDestination(declared) ?? safeInternalPath(previousDestination()) ?? internalReferrer() ?? "/";
}
