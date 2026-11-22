import { DuplaDeletePage, DuplaFormPage } from "./duplasForm";
import type { RouteDefinition } from "./types";

type DuplasFormParams = { page: "create" } | { page: "edit" | "delete"; id: string };

// Native URLs of the Duplas create, edit and soft delete (DU01.02); same trailing slashes.
export const duplasFormRoute: RouteDefinition<DuplasFormParams> = {
  name: "duplas-form",
  match(pathname) {
    if (pathname === "/equipo-tecnico/crear/") return { page: "create" };
    const action = pathname.match(/^\/equipo-tecnico\/([0-9]+)\/(editar|eliminar)\/$/);
    if (!action) return null;
    return { page: action[2] === "editar" ? "edit" : "delete", id: action[1] };
  },
  render: (params) => (params.page === "create" ? <DuplaFormPage key="create" />
    : params.page === "edit" ? <DuplaFormPage key={`edit:${params.id}`} id={params.id} />
      : <DuplaDeletePage key={params.id} id={params.id} />),
};
