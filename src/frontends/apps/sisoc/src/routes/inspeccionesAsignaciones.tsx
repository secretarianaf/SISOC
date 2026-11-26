import { AsignacionFormPage, AsignacionesPanelPage } from "./inspeccionesAsignacionesPage";
import type { RouteDefinition } from "./types";

// Native URLs of the Asignaciones tab (IN02): the day list and the assignment form as a page.
export const inspeccionesAsignacionesRoute: RouteDefinition<{ form: boolean }> = {
  name: "inspecciones-asignaciones",
  match: (pathname) => {
    if (pathname === "/inspecciones/asignaciones/") return { form: false };
    return pathname === "/inspecciones/asignaciones/nueva/" ? { form: true } : null;
  },
  render: ({ form }) => (form ? <AsignacionFormPage /> : <AsignacionesPanelPage />),
};
