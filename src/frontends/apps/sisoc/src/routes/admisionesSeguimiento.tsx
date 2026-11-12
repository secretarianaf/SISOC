/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { renderMain, useMainResource } from "./MainFrame";
import { AdmisionesListContent, ListCrumbs, listValid } from "./admisionesListas";
import type { RouteDefinition } from "./types";

/**
 * AD03.01 follow-up of the admision circuit (`/comedores/admisiones/tecnicos/listar`,
 * `/comedores/admisiones/legales/listar`). Data comes from
 * `/api/web/comedores/admisiones/`, which runs the native views; the rows keep
 * linking to the native pages.
 */
type Params = { page: "tecnicos" | "legales" };

const API = "web/comedores/admisiones/";
const PAGES = {
  tecnicos: { title: "Admisiones", empty: "No hay admisiones registradas." },
  legales: { title: "Comedores - Expedientes", empty: "No hay expedientes registrados." },
} as const;

function ListPage({ page }: { page: Params["page"] }) {
  const [state] = useMainResource(`${API}${page}/${window.location.search}`, listValid);
  return renderMain(state, "Cargando admisiones…", (data) => ({
    title: PAGES[page].title,
    breadcrumb: <ListCrumbs items={data.breadcrumb} />,
    content: <AdmisionesListContent data={data} empty={PAGES[page].empty} />,
  }));
}

// Native GET pages of `admisiones/urls/web_urls.py`; these URLs have no trailing slash.
const PATH = /^\/comedores\/admisiones\/(tecnicos|legales)\/listar$/;

export const admisionesSeguimientoRoute: RouteDefinition<Params> = {
  name: "comedores-admisiones-seguimiento",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { page: m[1] as Params["page"] } : null;
  },
  render(params) {
    return <ListPage key={params.page} page={params.page} />;
  },
};
