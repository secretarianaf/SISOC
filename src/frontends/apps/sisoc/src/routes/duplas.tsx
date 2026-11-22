import DuplaDetail from "./duplasDetail";
import DuplasList from "./duplasList";
import type { RouteDefinition } from "./types";

type DuplasParams = { page: "list" } | { page: "detail"; id: string };

// Native URLs of the Duplas list and detail (DU01.01); same trailing slashes.
export const duplasRoute: RouteDefinition<DuplasParams> = {
  name: "duplas",
  match(pathname) {
    if (pathname === "/equipo-tecnico/") return { page: "list" };
    const detail = pathname.match(/^\/equipo-tecnico\/([0-9]+)\/$/);
    return detail ? { page: "detail", id: detail[1] } : null;
  },
  render: (params) => (params.page === "list" ? <DuplasList /> : <DuplaDetail key={params.id} id={params.id} />),
};
