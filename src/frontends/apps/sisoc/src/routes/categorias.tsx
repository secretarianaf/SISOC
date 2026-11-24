import InsumosCategoriaForm from "../InsumosCategoriaForm";
import InsumosCategoriasList from "../InsumosCategoriasList";
import type { ShellRouteAction, ShellRouteDefinition } from "./types";

const CATEGORY_LIST_PATH = "/v2/sisoc/insumos/categorias/";
// Category routes keep the exact public slashes of the source circuit.
const CATEGORY_FORM = /^\/v2\/sisoc\/insumos\/categorias\/(?:(crear)|([0-9]+)\/(editar|eliminar))$/;

const TITLES: Record<ShellRouteAction, string> = {
  crear: "Nueva categoría",
  editar: "Editar categoría",
  eliminar: "Eliminar categoría",
};

export const categoriasRoute: ShellRouteDefinition = {
  name: "insumos-categorias",
  listPath: CATEGORY_LIST_PATH,
  match(pathname) {
    if (!pathname.startsWith(CATEGORY_LIST_PATH)) return null;
    const form = pathname.match(CATEGORY_FORM);
    return { action: form?.[1] === "crear" ? "crear" : form?.[3] as "editar" | "eliminar" | undefined, id: form?.[2] };
  },
  title: ({ action }) => (action ? TITLES[action] : "Categorías de insumos"),
  render: ({ pathname, params: { action, id }, returnToList }) => (action
    ? <InsumosCategoriaForm key={pathname} action={action} id={id} onComplete={returnToList} onCancel={() => returnToList()} />
    : <InsumosCategoriasList key={pathname} />),
};
