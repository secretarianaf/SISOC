import InsumosForm from "../InsumosForm";
import InsumosList from "../InsumosList";
import { INSUMOS_PREVIEW_LIST } from "../insumosPaths";
import type { ShellRouteAction, ShellRouteDefinition } from "./types";

const INSUMOS_FORM = /^(?:\/v2\/sisoc)?\/insumos\/(?:(crear)\/?|([0-9]+)\/(editar|eliminar)\/?)$/;

const TITLES: Record<ShellRouteAction, string> = {
  crear: "Nuevo insumo",
  editar: "Editar insumo",
  eliminar: "Eliminar insumo",
};

// Business fallback: every in-shell path without a more specific route renders the list.
export const insumosRoute: ShellRouteDefinition = {
  name: "insumos",
  listPath: INSUMOS_PREVIEW_LIST,
  match(pathname) {
    const form = pathname.match(INSUMOS_FORM);
    return { action: form?.[1] === "crear" ? "crear" : form?.[3] as "editar" | "eliminar" | undefined, id: form?.[2] };
  },
  title: ({ action }) => (action ? TITLES[action] : "Insumos"),
  render: ({ pathname, params: { action, id }, capabilities, returnToList }) => (action
    ? <InsumosForm key={pathname} action={action} id={id} onComplete={returnToList} onCancel={() => returnToList()} />
    : <InsumosList
      showManagement={capabilities?.insumos.show_management ?? false}
      showCategories={capabilities?.insumos.show_categories ?? false}
    />),
};
