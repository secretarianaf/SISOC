import { FlashToasts } from "./organizacionesForm";
import { LegajoContent, legajoValid } from "./organizacionLegajoPagina";
import { renderMain, useMainResource } from "./MainFrame";

/**
 * O05.01 `organizacion_detail.html` (legajo). The API runs the native `OrganizacionDetailView`
 * and sends the page as data; `organizacionLegajoPagina.tsx` draws it, section by section,
 * with the template's markup, so there is no server-rendered fragment left.
 */
export { legajoValid };

export default function OrganizacionLegajo({ id }: { id: number }) {
  const [state] = useMainResource(`web/comedores/organizaciones/${id}/${window.location.search}`, legajoValid);
  return renderMain(state, "Cargando organización…", (data) => ({
    title: data.title,
    breadcrumb: <></>,
    content: (
      <>
        <FlashToasts messages={data.messages} />
        <LegajoContent page={data} />
      </>
    ),
  }));
}
