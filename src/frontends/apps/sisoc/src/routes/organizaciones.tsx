import OrganizacionBaja from "./organizacionesBaja";
import OrganizacionForm from "./organizacionesForm";
import OrganizacionLegajo from "./organizacionesLegajo";
import OrganizacionesList from "./organizacionesList";
import type { RouteDefinition } from "./types";

type OrganizacionesParams = { page: "list" } | { page: "crear" } | { page: "legajo" | "editar" | "baja"; id: number };

const DETAIL_PAGES = { detalle: "legajo", editar: "editar", eliminar: "baja" } as const;

// Native URLs of `gestion_organizaciones/urls.py` (O05): no trailing slash, as today.
export const organizacionesRoute: RouteDefinition<OrganizacionesParams> = {
  name: "comedores-organizaciones",
  match(pathname) {
    if (pathname === "/organizaciones/listar") return { page: "list" };
    if (pathname === "/organizaciones/crear") return { page: "crear" };
    const detail = /^\/organizaciones\/(detalle|editar|eliminar)\/([1-9]\d{0,14})$/.exec(pathname);
    if (!detail) return null;
    return { page: DETAIL_PAGES[detail[1] as keyof typeof DETAIL_PAGES], id: Number(detail[2]) };
  },
  render: (params) => {
    switch (params.page) {
      case "legajo": return <OrganizacionLegajo id={params.id} />;
      case "editar": return <OrganizacionForm id={params.id} />;
      case "baja": return <OrganizacionBaja id={params.id} />;
      case "crear": return <OrganizacionForm id={null} />;
      default: return <OrganizacionesList />;
    }
  },
};
