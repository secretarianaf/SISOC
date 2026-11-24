import { useEffect, useState } from "react";
import { crearCliente } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { safeInternalPath, validateInsumosStatus, type WebAccessState } from "../webAccess";
import SisocShell from "./SisocShell";
import type { NavigationNode, ReadyContext, ShellRouteDefinition, WebSessionContext } from "./types";

type AccessState = WebAccessState;

type LoadState =
  | { status: "loading" }
  | { status: "ready"; context: ReadyContext }
  | { status: "prerequisite"; context: WebSessionContext }
  | { status: "forbidden" }
  | { status: "error" };

const webClient = crearCliente("/api");
const ACCESS_STATES = new Set<AccessState>([
  "ready",
  "web_access_denied",
  "password_change_required",
  "profile_confirmation_required",
  "mandatory_survey_required",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object";
}

function internalPath(value: unknown): string | null {
  return safeInternalPath(value);
}

function isNavigationNode(value: unknown): value is NavigationNode {
  if (!value || typeof value !== "object") return false;
  const node = value as Record<string, unknown>;
  return (
    typeof node.id === "string" &&
    typeof node.label === "string" &&
    (node.href === null || internalPath(node.href) !== null) &&
    Array.isArray(node.children) &&
    node.children.every(isNavigationNode)
  );
}

function isWebSessionContext(value: unknown): value is WebSessionContext {
  if (!value || typeof value !== "object") return false;
  const context = value as Record<string, unknown>;
  const access = context.access as Record<string, unknown> | null;
  const user = context.user as Record<string, unknown> | null;
  const capabilities = context.capabilities as Record<string, unknown> | null;
  const insumos = capabilities?.insumos as Record<string, unknown> | null;
  if (
    !access ||
    !ACCESS_STATES.has(access.state as AccessState) ||
    (access.required_action_url !== null &&
      internalPath(access.required_action_url) === null) ||
    !Array.isArray(context.navigation) ||
    !context.navigation.every(isNavigationNode) ||
    typeof context.footer_version_label !== "string" ||
    !insumos ||
    typeof insumos.can_view !== "boolean" ||
    typeof insumos.show_management !== "boolean" ||
    typeof insumos.show_categories !== "boolean"
  ) {
    return false;
  }
  return (
    user === null ||
    (typeof user.username === "string" &&
      typeof user.display_name === "string" &&
      typeof user.avatar_initial === "string" &&
      typeof user.role_label === "string")
  );
}

function isCompleteReadyContext(
  context: WebSessionContext,
): context is ReadyContext {
  const requiredItems = new Set(context.navigation.map((item) => item.id));
  return (
    context.access.state === "ready" &&
    context.user !== null &&
    ["inicio", "legajos", "mi_cuenta"].every((id) => requiredItems.has(id))
  );
}

function loginPath(): string {
  const next = window.location.pathname + window.location.search;
  return `/login/?next=${encodeURIComponent(next)}`;
}

function AccessMessage({ context }: { context: WebSessionContext }) {
  return <InsumosAccessError prerequisite={context.access} />;
}

function ErrorMessage() {
  return (
    <main className="sisoc-message" role="main">
      <section className="sisoc-message-card" role="alert">
        <h1>No se pudo verificar tu sesión</h1>
        <p>Volvé a ingresar para continuar en SISOC.</p>
        <a className="sisoc-action-link" href={loginPath()}>
          Iniciar sesión
        </a>
      </section>
    </main>
  );
}

// Business paths bootstrap the cookie session before rendering the private shell.
export default function BusinessApp({ shellRoutes }: { shellRoutes: readonly ShellRouteDefinition[] }) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();
    webClient
      .get<WebSessionContext>("web/session/", {
        signal: controller.signal,
        validateStatus: validateInsumosStatus,
      })
      .then(({ data, status }) => {
        if (!mounted) return;
        if (status === 403) {
          if (isWebSessionContext(data) && data.access.state !== "ready") {
            setState({ status: "prerequisite", context: data });
          } else {
            setState({ status: "forbidden" });
          }
        } else if (!isWebSessionContext(data)) {
          setState({ status: "error" });
        } else if (data.access.state !== "ready") {
          setState({ status: "prerequisite", context: data });
        } else if (isCompleteReadyContext(data)) {
          setState({ status: "ready", context: data });
        } else {
          setState({ status: "error" });
        }
      })
      .catch((error: unknown) => {
        if (!mounted) return;
        const status =
          isRecord(error) && isRecord(error.response) && typeof error.response.status === "number"
            ? error.response.status
            : undefined;
        setState({ status: status === 403 ? "forbidden" : "error" });
      });
    return () => {
      mounted = false;
      controller.abort();
    };
  }, []);

  if (state.status === "loading") {
    return (
      <main className="sisoc-message" role="status">
        Cargando SISOC…
      </main>
    );
  }
  if (state.status === "forbidden") return <InsumosAccessError />;
  if (state.status === "error") return <ErrorMessage />;
  if (state.status === "prerequisite") return <AccessMessage context={state.context} />;
  return <SisocShell context={state.context} routes={shellRoutes} />;
}
