import ActaDetallePage from "./inspeccionesActaDetallePage";
import type { RouteDefinition } from "./types";

const DETAIL = /^\/inspecciones\/actas\/([^/]+)\/$/;

// Native URL of one acta (IN04): `/inspecciones/actas/<numero>/`, same trailing slash.
export const inspeccionesActaDetalleRoute: RouteDefinition<{ numero: string }> = {
  name: "inspecciones-acta-detalle",
  match: (pathname) => {
    const found = DETAIL.exec(pathname);
    if (!found) return null;
    try {
      return { numero: decodeURIComponent(found[1]) };
    } catch {
      return null;
    }
  },
  render: ({ numero }) => <ActaDetallePage numero={numero} />,
};
