/* eslint-disable react-refresh/only-export-components -- frame module: hook, helpers and the frame renderer travel together. */
import { useEffect, useState, type ReactElement, type ReactNode } from "react";
import { crearCliente } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "../webAccess";
import SisocShell from "./SisocShell";
import { HITOS_STYLESHEET } from "./userImport";
import type { NavigationNode, ReadyContext } from "./types";

/**
 * Frame of the vertical pages that extend `includes/main.html` (dark layout).
 * The menu, user and footer come from the core session (`/api/web/session/`);
 * the page data from the vertical's G1 web API, forwarded by the core.
 */
export type MainSession = Pick<ReadyContext, "user" | "navigation" | "footer_version_label">;
export type MainState<T> =
  | { status: "loading" }
  | { status: "error" }
  | { status: "forbidden"; prerequisite: WebPrerequisite | null }
  | { status: "ready"; data: T; session: MainSession };
/** `activePath`: the menu entry the native sidebar marks (it matches by path fragment). */
/** `appHeader`: the page's `{% block app-header %}` (the shell's empty row otherwise). */
export type MainPage = { title: string; heading?: string; breadcrumb: ReactNode; content: ReactNode; activePath?: string; appHeader?: ReactNode };

export const webClient = crearCliente("/api");
export const accepted = (status: number) => (status >= 200 && status < 300) || status === 403;
export const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object";
export const text = (v: unknown): v is string => typeof v === "string";
export const internal = (v: unknown): v is string => safeInternalPath(v) !== null;

function nodeValid(n: unknown): n is NavigationNode {
  return record(n) && text(n.id) && text(n.label) && (n.href === null || internal(n.href)) &&
    Array.isArray(n.children) && n.children.every(nodeValid);
}

function sessionValid(v: unknown): v is MainSession {
  return record(v) && record(v.user) && ["username", "display_name", "avatar_initial", "role_label"].every((k) => text((v.user as Record<string, unknown>)[k])) &&
    Array.isArray(v.navigation) && v.navigation.every(nodeValid) && text(v.footer_version_label);
}

/** Loads the session and one vertical endpoint; a 403 from either one is the access screen. */
export function useMainResource<T>(endpoint: string, valid: (v: unknown) => v is T) {
  const [state, setState] = useState<MainState<T>>({ status: "loading" });
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const get = (url: string) => webClient.get(url, { signal: controller.signal, validateStatus: accepted });
    Promise.all([get("web/session/"), get(endpoint)]).then(([session, page]) => {
      if (!active) return;
      const denied = [page, session].find((r) => r.status === 403);
      if (denied) setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(denied.data) });
      else if (sessionValid(session.data) && valid(page.data)) setState({ status: "ready", data: page.data, session: session.data });
      else setState({ status: "error" });
    }).catch(() => { if (active) setState({ status: "error" }); });
    return () => { active = false; controller.abort(); };
  }, [endpoint, valid]);
  return [state, setState] as const;
}

export function renderMain<T>(state: MainState<T>, loading: string, page: (data: T) => MainPage): ReactElement | null {
  if (state.status === "loading") return <main role="status">{loading}</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar la página.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  const { title, heading = "", breadcrumb, content, activePath, appHeader } = page(state.data);
  return <>
    <SisocShell context={state.session} content={<>{HITOS_STYLESHEET}{content}</>} pageTitle={title} heading={heading} breadcrumb={breadcrumb} previewLinks={false} activePath={activePath} appHeader={appHeader} />
    <AppLoaded />
  </>;
}

// AdminLTE marks the body `app-loaded` once the page is up; it runs after the shell's own body classes.
function AppLoaded() {
  useEffect(() => {
    document.body.classList.add("app-loaded");
    return () => document.body.classList.remove("app-loaded");
  }, []);
  return null;
}

/** `components/breadcrumb.html`: every item but the last links when it has a URL. */
export function Breadcrumb({ items }: { items: { text: string; url: string | null }[] }) {
  return <ol className="breadcrumb float-sm-right">
    {items.map((item, i) => {
      const link = item.url && i < items.length - 1;
      return <li key={i} className={`breadcrumb-item ${link ? "" : "active"}`}>{link ? <a href={item.url!}>{item.text}</a> : item.text}</li>;
    })}
  </ol>;
}

export type Breadcrumbs = { text: string; url: string | null }[];
export const breadcrumbValid = (v: unknown): v is Breadcrumbs =>
  Array.isArray(v) && v.every((b) => record(b) && text(b.text) && (b.url === null || internal(b.url)));

/** Native POST through the vertical API: `{ok, redirect}` navigates, 400 returns the bound form. */
export async function postForm(endpoint: string, body: URLSearchParams) {
  try {
    const { data, status } = await webClient.post(endpoint, body, { validateStatus: accepted });
    if (status === 403) return { kind: "forbidden" as const, data };
    if (record(data) && data.ok === true && internal(data.redirect)) return { kind: "redirect" as const, url: data.redirect };
    return { kind: "uncertain" as const };
  } catch (error: unknown) {
    const response = (error as { response?: { status?: number; data?: unknown } }).response;
    if (response?.status === 400) return { kind: "invalid" as const, data: response.data };
    return { kind: "uncertain" as const };
  }
}
