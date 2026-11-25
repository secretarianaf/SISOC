import ActasPage from "./ActasPage";
import type { RouteDefinition } from "./types";

// Native URL of the Inspecciones Actas tab (IN04.01, list slice); same trailing slash.
export const inspeccionesActasRoute: RouteDefinition<Record<string, never>> = {
  name: "inspecciones-actas",
  match: (pathname) => (pathname === "/inspecciones/actas/" ? {} : null),
  render: () => <ActasPage />,
};
