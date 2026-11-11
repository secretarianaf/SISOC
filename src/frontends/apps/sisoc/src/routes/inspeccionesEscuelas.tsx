import { EscuelaFormPage, EscuelasPanelPage } from "./inspeccionesEscuelasPage";
import type { RouteDefinition } from "./types";

const EDITAR = /^\/inspecciones\/escuelas\/([1-9][0-9]*)\/editar\/$/;

// Native URLs of the Escuelas tab (IN05): the panel and the school form as a page.
export const inspeccionesEscuelasRoute: RouteDefinition<{ form: "panel" | "nueva" | "editar"; pk: number | null }> = {
  name: "inspecciones-escuelas",
  match: (pathname) => {
    if (pathname === "/inspecciones/") return { form: "panel", pk: null };
    if (pathname === "/inspecciones/escuelas/nueva/") return { form: "nueva", pk: null };
    const editar = EDITAR.exec(pathname);
    return editar ? { form: "editar", pk: Number(editar[1]) } : null;
  },
  render: ({ form, pk }) => (form === "panel" ? <EscuelasPanelPage /> : <EscuelaFormPage pk={pk} />),
};
