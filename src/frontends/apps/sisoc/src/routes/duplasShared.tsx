/* eslint-disable react-refresh/only-export-components -- shared surface of the Duplas unit: loaders, validators and the legacy frame. */
import { useEffect, useState, type ReactNode } from "react";
import { crearCliente } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import type { RequiredPasswordPresentation } from "../RequiredPasswordChange";
import { legacyIdentityFrame } from "../identityFrames";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "../webAccess";
import type { NavigationNode } from "./types";

/**
 * Duplas (equipo técnico) screens of the comedores backend. Data comes from
 * its G1 web API (`/api/web/comedores/duplas/`, forwarded by the core); the
 * frame (menu, user, footer) from the core session. The pages keep the
 * native `includes/main.html` frame through the legacy shell.
 */
export const client = crearCliente("/api");
export const API = "web/comedores/duplas/";
export const LIST_PATH = "/equipo-tecnico/";
export const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object";
export const text = (v: unknown): v is string => typeof v === "string";
export const integer = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const accepted = (status: number) => (status >= 200 && status < 300) || status === 403;

export type Message = { message: string; level: "success" | "error" | "warning" | "info" };
export const messagesValid = (v: unknown): v is Message[] => Array.isArray(v) &&
  v.every((m) => record(m) && text(m.message) && ["success", "error", "warning", "info"].includes(m.level as string));

type Session = { user: RequiredPasswordPresentation["user"]; navigation: NavigationNode[]; footer_version_label: string };

function nodeValid(n: unknown): n is NavigationNode {
  return record(n) && text(n.id) && text(n.label) && (n.href === null || safeInternalPath(n.href) !== null) &&
    Array.isArray(n.children) && n.children.every(nodeValid);
}
function sessionValid(v: unknown): v is Session {
  return record(v) && record(v.user) &&
    ["username", "display_name", "avatar_initial", "role_label"].every((k) => text((v.user as Record<string, unknown>)[k])) &&
    Array.isArray(v.navigation) && v.navigation.every(nodeValid) && text(v.footer_version_label);
}

export type Loaded<T> =
  | { status: "loading" | "error" }
  | { status: "forbidden"; prerequisite: WebPrerequisite | null }
  | { status: "ready"; data: T; presentation: RequiredPasswordPresentation };

/** One session GET plus one API GET per mount; never polled or retried. */
export function useDuplasResource<T>(endpoint: string, valid: (v: unknown) => v is T): Loaded<T> {
  const [state, setState] = useState<Loaded<T>>({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    const options = { signal: controller.signal, validateStatus: accepted };
    Promise.all([client.get("web/session/", options), client.get(endpoint, options)])
      .then(([session, page]: { data: unknown; status?: number }[]) => {
        if (controller.signal.aborted) return;
        if (session.status === 403 || page.status === 403) {
          setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(session.status === 403 ? session.data : page.data) });
        } else if (sessionValid(session.data) && valid(page.data)) {
          const { user, navigation, footer_version_label } = session.data;
          setState({ status: "ready", data: page.data, presentation: { user, footer_version_label, legacy_frame_navigation: navigation } });
        } else setState({ status: "error" });
      })
      .catch(() => { if (!controller.signal.aborted) setState({ status: "error" }); });
    return () => controller.abort();
  }, [endpoint, valid]);
  return state;
}

/** AdminLTE marks the native body `app-loaded` once its script runs. */
function AppLoaded() {
  // After the shell's own body effects, so the class order matches the native body.
  useEffect(() => {
    const had = document.body.classList.contains("app-loaded");
    document.body.classList.add("app-loaded");
    return () => { if (!had) document.body.classList.remove("app-loaded"); };
  }, []);
  return null;
}

/** Loading, error and access states, then the native `includes/main.html` frame. */
export function renderDuplas<T>(
  state: Loaded<T>,
  render: (data: T) => { content: ReactNode; title: string; heading: string; breadcrumb: ReactNode; overlays?: ReactNode },
) {
  if (state.status === "loading") return <main role="status">Cargando equipos técnicos…</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar el equipo técnico.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  if (state.status !== "ready") return null;
  const { content, title, heading, breadcrumb, overlays } = render(state.data);
  // Native sidebar marks "Equipos Técnicos" for every page under its prefix ('equipo-tecnico' in pagina_actual).
  return <>
    {legacyIdentityFrame(content, state.presentation, title, heading, overlays, breadcrumb, false, "/", LIST_PATH)}
    <AppLoaded />
  </>;
}
