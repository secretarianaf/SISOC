/* eslint-disable react-refresh/only-export-components -- route module: only the route definition is exported. */
import { BajaContent, bajaValid } from "./ciudadanoBaja";
import { renderMain, useMainResource } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * C03.02: `ciudadanos/grupofamiliar_confirm_delete.html`, the same `components/delete_confirm.html` card as the ciudadano baja.
 * GET `/api/web/ciudadanos/familiares/<pk>/eliminar/` runs `GrupoFamiliarDeleteView` (403 without `change_ciudadano`, then 404);
 * the confirmed POST runs its `post()` (logical delete of the relation) and the redirect is a full-page navigation. The native
 * `next` travels in the query of both calls, as in the native page.
 */
function EliminarPage({ pk }: { pk: string }) {
  const endpoint = `web/ciudadanos/familiares/${pk}/eliminar/${window.location.search}`;
  const [state] = useMainResource(endpoint, bajaValid);
  // The native template defines no title block ("SISOC - ").
  return renderMain(state, "Cargando relación…", (data) => ({ title: "", heading: "", breadcrumb: null, content: <BajaContent data={data} endpoint={endpoint} /> }));
}

const ELIMINAR = /^\/ciudadanos\/familiares\/([0-9]+)\/eliminar$/;

export const ciudadanoFamiliarEliminarRoute: RouteDefinition<{ pk: string }> = {
  name: "ciudadano-familiar-eliminar",
  match(pathname) {
    const found = ELIMINAR.exec(pathname);
    return found ? { pk: found[1] } : null;
  },
  render: ({ pk }) => <EliminarPage pk={pk} />,
};
