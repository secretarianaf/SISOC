/* eslint-disable react-refresh/only-export-components -- route module: the screen and its route definition live here. */
import { BajaContent, intervencionBajaValid } from "./comedorIntervencionesBaja";
import { renderMain, useMainResource } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * CO01 «Dar de baja» of a nómina record (`nomina_borrar`, `nomina_directa_borrar`):
 * `comedor/nomina_confirm_delete.html`, the same breadcrumb and `components/delete_confirm.html`
 * as the intervention confirmation. GET and the confirmed POST go to
 * `/api/web/comedores/comedores/…/nomina/<pk2>/eliminar/`, which runs the native delete views
 * (scope, soft delete, message, redirect to the nómina); the POST is sent once and never retried.
 */
function NominaBajaPage({ endpoint }: { endpoint: string }) {
  const [state] = useMainResource(endpoint, intervencionBajaValid);
  return renderMain(state, "Cargando nómina…", (data) => ({
    title: "Acciones",
    breadcrumb: <ol className="breadcrumb float-sm-right">
      {/* The template has `href=""`, which resolves to this very page (React drops an empty href). */}
      <li className="breadcrumb-item"><a href={`${window.location.pathname}${window.location.search}`} title="Ver listado de admisiones">Admisiones</a></li>
      <li className="breadcrumb-item "><a href={data.breadcrumb.url} title="Ver ciudadano">{data.breadcrumb.etiqueta}</a></li>
      <li className="breadcrumb-item active">Detalle</li>
    </ol>,
    content: <BajaContent data={data} endpoint={endpoint} />,
  }));
}

const API = "web/comedores/comedores/";
const ADMISION = /^\/comedores\/([1-9]\d*)\/admision\/([1-9]\d*)\/nomina\/([1-9]\d*)\/eliminar\/$/;
const DIRECTA = /^\/comedores\/([1-9]\d*)\/nomina\/([1-9]\d*)\/eliminar\/$/;

export const comedorNominaBajaRoute: RouteDefinition<{ endpoint: string }> = {
  name: "comedor-nomina-baja",
  match(pathname) {
    const admision = ADMISION.exec(pathname);
    if (admision) return { endpoint: `${API}${admision[1]}/admision/${admision[2]}/nomina/${admision[3]}/eliminar/` };
    const directa = DIRECTA.exec(pathname);
    return directa ? { endpoint: `${API}${directa[1]}/nomina/${directa[2]}/eliminar/` } : null;
  },
  render: ({ endpoint }) => <NominaBajaPage key={endpoint} endpoint={endpoint} />,
};
