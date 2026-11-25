import type { ReactElement } from "react";
import type { WebAccessState } from "../webAccess";

export type NavigationNode = {
  id: string;
  label: string;
  href: string | null;
  children: NavigationNode[];
};

export type WebSessionContext = {
  user: {
    username: string;
    display_name: string;
    avatar_initial: string;
    role_label: string;
  } | null;
  access: { state: WebAccessState; required_action_url: string | null };
  navigation: NavigationNode[];
  capabilities: {
    insumos: {
      can_view: boolean;
      show_management: boolean;
      show_categories: boolean;
    };
  };
  footer_version_label: string;
};

export type ReadyContext = WebSessionContext & {
  user: NonNullable<WebSessionContext["user"]>;
};

/**
 * One top-level path family owned by a React unit. The App renders the first
 * route in `ROUTES` whose `match` returns params; `null` means "not mine".
 * Methods (not function properties) keep `RouteDefinition<P>` assignable to
 * the untyped registry array.
 */
export interface RouteDefinition<P = unknown> {
  name: string;
  match(pathname: string): P | null;
  render(params: P): ReactElement;
}

export type ShellRouteAction = "crear" | "editar" | "eliminar";

export type ShellRouteParams = { action?: ShellRouteAction; id?: string };

export type ShellRouteContext = {
  pathname: string;
  params: ShellRouteParams;
  capabilities?: ReadyContext["capabilities"];
  /** Pushes the route's `listPath` without reloading and shows an optional toast. */
  returnToList: (message?: string) => void;
};

/**
 * A page rendered inside the session-bootstrapped business shell. The shell
 * keeps its own pathname state, so these routes navigate in place.
 */
export interface ShellRouteDefinition {
  name: string;
  listPath: string;
  match(pathname: string): ShellRouteParams | null;
  title(params: ShellRouteParams): string;
  render(context: ShellRouteContext): ReactElement;
}
