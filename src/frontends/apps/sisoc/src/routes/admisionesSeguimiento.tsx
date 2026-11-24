/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { useState } from "react";
import { renderMain, useMainResource } from "./MainFrame";
import { DetalleBreadcrumb, DetalleContent, DetalleHeading, detalleValid } from "./admisionesDetalle";
import { EditorBreadcrumb, EditorContent, EditorHeading, editorValid } from "./admisionesEditor";
import { resetAfterRejectedPost } from "./nativeParity";
import { AdmisionesListContent, ListCrumbs, listValid } from "./admisionesListas";
import type { RouteDefinition } from "./types";

/**
 * AD03 admision circuit (`/comedores/admisiones/tecnicos/listar`, `/comedores/admisiones/legales/listar`,
 * the detail and the technical editor `/comedores/admisiones/tecnicos/editar/<pk>`). Data comes from
 * `/api/web/comedores/admisiones/`, which runs the native views; the rows keep
 * linking to the native pages.
 */
type Params = { page: "tecnicos" | "legales" } | { page: "detalle"; comedor: string; id: string } | { page: "editor"; id: string };
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
    // `titulo-pagina` carries the active/closed badge.
    heading: <DetalleHeading activa={data.activa} />,
    breadcrumb: <DetalleBreadcrumb data={data} />,
    content: <DetalleContent data={data} />,
  }));
}

/** AD03.02 editor (`admisiones_tecnicos_editar`): every action reloads the data, as the native redirect reloads the page. */
function EditorParams({ id }: { id: string }) {
  const [version, setVersion] = useState(0);
  const [state] = useMainResource(`${API}${id}/${version ? `?r=${version}` : ""}`, editorValid);
  return renderMain(state, "Cargando admisión…", (data) => ({
    title: `Admision: ${data.comedor.nombre}`,
    heading: <EditorHeading data={data} />,
    breadcrumb: <EditorBreadcrumb data={data} />,
    content: <EditorContent data={data} onDone={(_messages, rejected) => { setVersion((v) => v + 1); if (rejected) resetAfterRejectedPost(); }} />,
  }));
}

// Native GET pages of `admisiones/urls/web_urls.py`; the list URLs have no trailing slash.
const PATH = /^\/comedores\/admisiones\/(tecnicos|legales)\/listar$/;
const EDITOR = /^\/comedores\/admisiones\/tecnicos\/editar\/([0-9]+)$/;
const DETALLE = /^\/comedores\/([0-9]+)\/admision\/([0-9]+)\/detalle\/$/;

export const admisionesSeguimientoRoute: RouteDefinition<Params> = {
  name: "comedores-admisiones-seguimiento",
  match(pathname) {
    const e = pathname.match(EDITOR);
    if (e) return { page: "editor", id: e[1] };
    const d = pathname.match(DETALLE);
    if (d) return { page: "detalle", comedor: d[1], id: d[2] };
    const m = pathname.match(PATH);
    return m ? { page: m[1] as ListName } : null;
  },
  render(params) {
    if (params.page === "editor") return <EditorParams key={params.id} id={params.id} />;
    if (params.page === "detalle") return <DetalleParams key={`${params.comedor}/${params.id}`} comedor={params.comedor} id={params.id} />;
    return <ListPage key={params.page} page={params.page} />;
  },
};
