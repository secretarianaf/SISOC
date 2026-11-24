/* eslint-disable react-refresh/only-export-components -- shared loader and frame of the CDF route modules. */
import { useEffect, useLayoutEffect, useState, type ReactNode } from "react";
import { crearCliente, leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { InsumosToastList } from "../InsumosToast";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "../webAccess";
import SisocShell from "./SisocShell";
import type { NavigationNode } from "./types";
import { HITOS_STYLESHEET } from "./userImport";

/**
 * CDF pages extend `includes/main.html` (dark business layout). Their data comes
 * from the vertical's G1 web API (`/api/web/cdf/...`, forwarded by the core);
 * the frame (menu, user, footer) from the core session, like the CDI screens.
 */
export type CdfMessage = { message: string; level: "success" | "error" | "warning" | "info" };
type Session = {
  user: { username: string; display_name: string; avatar_initial: string; role_label: string };
  navigation: NavigationNode[];
  footer_version_label: string;
};
export type CdfState<T> =
  | { status: "loading" }
  | { status: "error" }
  | { status: "notfound" }
  | { status: "forbidden"; prerequisite: WebPrerequisite | null }
  | { status: "ready"; data: T; session: Session };

export const client = crearCliente("/api");
/** Full-page navigation (native reloads, confirmed POSTs); replaceable in tests. */
export const navigation = {
  assign: (to: string) => window.location.assign(to),
  confirm: (message: string) => window.confirm(message),
};
export const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object";
export const text = (v: unknown): v is string => typeof v === "string";
export const nullableText = (v: unknown): v is string | null => v === null || typeof v === "string";
export const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
export const internal = (v: unknown): v is string => safeInternalPath(v) !== null;
export const csrfToken = () => leerCookie("csrftoken") ?? "";
const accepted = (status: number) => (status >= 200 && status < 300) || status === 403 || status === 404;

function nodeValid(n: unknown): n is NavigationNode {
  return record(n) && text(n.id) && text(n.label) && (n.href === null || safeInternalPath(n.href) !== null) &&
    Array.isArray(n.children) && n.children.every(nodeValid);
}
function sessionValid(v: unknown): v is Session {
  return record(v) && record(v.user) && ["username", "display_name", "avatar_initial", "role_label"].every((k) => text((v.user as Record<string, unknown>)[k])) &&
    Array.isArray(v.navigation) && v.navigation.every(nodeValid) && text(v.footer_version_label);
}
export const messagesValid = (v: unknown): v is CdfMessage[] => Array.isArray(v) &&
  v.every((m) => record(m) && text(m.message) && ["success", "error", "warning", "info"].includes(m.level as string));

/** Session and page data in one round trip; one GET each per mount, never retried. */
export function useCdfPage<T>(endpoint: string, valid: (v: unknown) => v is T) {
  const [state, setState] = useState<CdfState<T>>({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    const options = { signal: controller.signal, validateStatus: accepted };
    Promise.all([client.get("web/session/", options), client.get(endpoint, options)])
      .then(([session, page]: { data: unknown; status?: number }[]) => {
        if (controller.signal.aborted) return;
        if (session.status === 403 || page.status === 403) {
          setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(session.status === 403 ? session.data : page.data) });
        } else if (page.status === 404) setState({ status: "notfound" });
        else if (sessionValid(session.data) && valid(page.data)) setState({ status: "ready", data: page.data, session: session.data });
        else setState({ status: "error" });
      })
      .catch(() => { if (!controller.signal.aborted) setState({ status: "error" }); });
    return () => controller.abort();
  }, [endpoint, valid]);
  return state;
}

/** AdminLTE marks the body `app-loaded` once its scripts run; undone on unmount. */
function AppLoadedBody() {
  useLayoutEffect(() => {
    const body = document.body;
    const hadLoaded = body.classList.contains("app-loaded");
    body.classList.add("app-loaded");
    return () => {
      if (!hadLoaded) body.classList.remove("app-loaded");
    };
  }, []);
  return null;
}

export type CdfPage = { title: string; heading?: string; breadcrumb: ReactNode; content: ReactNode; overlays?: ReactNode };

export function renderCdf<T extends { messages: CdfMessage[] }>(state: CdfState<T>, render: (data: T) => CdfPage) {
  if (state.status === "loading") return <main role="status">Cargando…</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar la página.</main>;
  if (state.status === "notfound") return <main role="alert">No se encontró la página.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  const { title, heading = "", content, breadcrumb, overlays } = render(state.data);
  return (
    <SisocShell
      context={state.session}
      pageTitle={title}
      heading={heading}
      breadcrumb={breadcrumb}
      previewLinks={false}
      overlays={overlays}
      content={<>{HITOS_STYLESHEET}<AppLoadedBody /><InsumosToastList messages={state.data.messages} />{content}</>}
    />
  );
}
