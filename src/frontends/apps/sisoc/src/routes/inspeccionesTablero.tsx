import TableroPage from "./inspeccionesTableroPage";
import type { RouteDefinition } from "./types";

// Native URL of the Tablero tab (IN03); data, CSV and the PDF/ZIP download stay backend routes.
export const inspeccionesTableroRoute: RouteDefinition<Record<string, never>> = {
  name: "inspecciones-tablero",
  match: (pathname) => (pathname === "/inspecciones/tablero/" ? {} : null),
  render: () => <TableroPage />,
};
