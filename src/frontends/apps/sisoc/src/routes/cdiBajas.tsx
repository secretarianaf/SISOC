/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen lives here with the route. */
import { renderCdi, text, useCdiPage } from "./cdiFrame";
import { ConfirmContent, deleteConfirmValid, type DeleteConfirm } from "./cdiObservaciones";
import type { RouteDefinition } from "./types";

/**
 * CDI soft-delete confirmations (`centrodeinfancia_confirm_delete.html` and
 * `nomina_confirm_delete.html`) on their native URLs. The native delete views
 * stay the authority through `/api/web/cdi/`: scope, auditor veto, cascade,
 * message and redirect. A confirmed POST navigates to the native redirect.
 */
type Baja = DeleteConfirm & { title: string };
type Params = { kind: "centro" | "nomina"; endpoint: string };

const bajaValid = (v: unknown): v is Baja => deleteConfirmValid(v) && text((v as { title?: unknown }).title);

function BajaPage({ endpoint }: { endpoint: string }) {
  const [state] = useCdiPage(endpoint, bajaValid);
  return renderCdi(state, (data) => ({ title: data.title, heading: data.title, content: <ConfirmContent data={data} endpoint={endpoint} /> }));
}

const CENTRO = /^\/centrodeinfancia\/eliminar\/([1-9]\d*)$/;
const NOMINA = /^\/centrodeinfancia\/([1-9]\d*)\/nomina\/([1-9]\d*)\/eliminar\/$/;

// Native URLs of the CDI soft-delete confirmations; same trailing slashes.
export const cdiBajasRoute: RouteDefinition<Params> = {
  name: "cdi-bajas",
  match: (pathname) => {
    const centro = CENTRO.exec(pathname);
    if (centro) return { kind: "centro", endpoint: `web/cdi/centros/${centro[1]}/eliminar/` };
    const nomina = NOMINA.exec(pathname);
    if (nomina) return { kind: "nomina", endpoint: `web/cdi/centros/${nomina[1]}/nomina/${nomina[2]}/eliminar/` };
    return null;
  },
  render: (params) => <BajaPage key={params.endpoint} endpoint={params.endpoint} />,
};
