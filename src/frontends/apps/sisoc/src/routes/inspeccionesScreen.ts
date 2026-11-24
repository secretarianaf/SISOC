import { useCallback, useEffect, useState } from "react";
import { prerequisiteFromForbidden, safeInternalPath, type WebPrerequisite } from "../webAccess";
import type { ClaroUser } from "./ClaroFrame";
import { client } from "./inspeccionesEscuelasApi";
import type { NavigationNode } from "./types";

/** Shared loading of the Inspecciones panel screens: session + screen data, access errors. */
const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object";
const text = (v: unknown): v is string => typeof v === "string";
const accepted = (status: number) => (status >= 200 && status < 300) || status === 403;
export type Session = { user: ClaroUser; navigation: NavigationNode[]; footer_version_label: string };

function nodeValid(n: unknown): n is NavigationNode {
  return record(n) && text(n.id) && text(n.label) && (n.href === null || safeInternalPath(n.href) !== null) &&
    Array.isArray(n.children) && n.children.every(nodeValid);
}
function sessionValid(v: unknown): v is Session {
  return record(v) && record(v.user) && ["display_name", "avatar_initial", "role_label"].every((k) => text((v.user as Record<string, unknown>)[k])) &&
    Array.isArray(v.navigation) && v.navigation.every(nodeValid) && text(v.footer_version_label);
}
export function submitForm(form: HTMLFormElement) {
  if (form.requestSubmit) form.requestSubmit(); else form.submit();
}

export type Loaded<T> = { status: "loading" } | { status: "error" } | { status: "forbidden"; prerequisite: WebPrerequisite | null } | { status: "ready"; data: T; session: Session };

export function useScreen<T>(url: string, valid: (v: unknown) => v is T) {
  const [state, setState] = useState<Loaded<T>>({ status: "loading" });
  const forbidden = useCallback((data: unknown) => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(data) }), []);
  useEffect(() => {
    const controller = new AbortController();
    const options = { signal: controller.signal, validateStatus: accepted };
    Promise.all([client.get("web/session/", options), client.get(url, options)]).then(([session, screen]: { data: unknown; status?: number }[]) => {
      if (controller.signal.aborted) return;
      if (session.status === 403 || screen.status === 403) forbidden(session.status === 403 ? session.data : screen.data);
      else if (sessionValid(session.data) && valid(screen.data)) setState({ status: "ready", data: screen.data, session: session.data });
      else setState({ status: "error" });
    }).catch(() => { if (!controller.signal.aborted) setState({ status: "error" }); });
    return () => controller.abort();
  }, [url, valid, forbidden]);
  return { state, forbidden };
}
