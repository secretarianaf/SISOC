/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { renderMain, useMainResource } from "./MainFrame";
import { DetalleBreadcrumb, DetalleContent, DetalleHeading, detalleValid } from "./admisionesDetalle";
import { AdmisionesListContent, ListCrumbs, listValid } from "./admisionesListas";
import type { RouteDefinition } from "./types";

/**
 * AD03.01 follow-up of the admision circuit (`/comedores/admisiones/tecnicos/listar`,
 * `/comedores/admisiones/legales/listar`). Data comes from
 * `/api/web/comedores/admisiones/`, which runs the native views; the rows keep
 * linking to the native pages.
 */
type Params = { page: "tecnicos" | "legales" } | { page: "detalle"; comedor: string; id: string };
type ListName = "tecnicos" | "legales";

const API = "web/comedores/admisiones/";
const PAGES = {
  tecnicos: { title: "Admisiones", empty: "No hay admisiones registradas." },
  legales: { title: "Comedores - Expedientes", empty: "No hay expedientes registrados." },
} as const;

function ListPage({ page }: { page: ListName }) {
  const [state] = useMainResource(`${API}${page}/${window.location.search}`, listValid);
  return renderMain(state, "Cargando admisiones…", (data) => ({
    title: PAGES[page].title,
    breadcrumb: <ListCrumbs items={data.breadcrumb} />,
    content: <AdmisionesListContent data={data} empty={PAGES[page].empty} />,
  }));
}

function DetalleParams({ comedor, id }: { comedor: string; id: string }) {
  const [state] = useMainResource(`${API}${comedor}/${id}/detalle/${window.location.search}`, detalleValid);
  return renderMain(state, "Cargando admisión…", (data) => ({
    title: `Admision ${data.id}`,
    // `titulo-pagina` carries the active/closed badge; the shell types its heading as text but renders any node.
    heading: DetalleHeading({ activa: data.activa }) as unknown as string,
    breadcrumb: <DetalleBreadcrumb data={data} />,
    content: <DetalleContent data={data} />,
  }));
}

// Native GET pages of `admisiones/urls/web_urls.py`; the list URLs have no trailing slash.
const PATH = /^\/comedores\/admisiones\/(tecnicos|legales)\/listar$/;
const DETALLE = /^\/comedores\/([0-9]+)\/admision\/([0-9]+)\/detalle\/$/;

export const admisionesSeguimientoRoute: RouteDefinition<Params> = {
  name: "comedores-admisiones-seguimiento",
  match(pathname) {
    const d = pathname.match(DETALLE);
    if (d) return { page: "detalle", comedor: d[1], id: d[2] };
    const m = pathname.match(PATH);
    return m ? { page: m[1] as ListName } : null;
  },
  render(params) {
    if (params.page === "detalle") return <DetalleParams key={`${params.comedor}/${params.id}`} comedor={params.comedor} id={params.id} />;
    return <ListPage key={params.page} page={params.page} />;
  },
};
