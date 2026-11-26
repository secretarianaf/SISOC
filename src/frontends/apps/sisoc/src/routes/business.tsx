import BusinessApp from "./BusinessApp";
import type { RouteDefinition, ShellRouteDefinition } from "./types";

// Catch-all: any path no identity route claims goes to the session-bootstrapped shell.
export function businessRoute(shellRoutes: readonly ShellRouteDefinition[]): RouteDefinition<Record<string, never>> {
  return {
    name: "business",
    match: () => ({}),
    render: () => <BusinessApp shellRoutes={shellRoutes} />,
  };
}
