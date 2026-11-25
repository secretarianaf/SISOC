import Groups from "../Groups";
import { groupsFrame } from "../identityFrames";
import type { RouteDefinition } from "./types";

type GroupsParams = { mode: "list" | "create" | "edit"; id?: string };

export const groupsRoute: RouteDefinition<GroupsParams> = {
  name: "groups",
  match(pathname) {
    const groupEdit = pathname.match(/^\/grupos\/editar\/([0-9]+)\/$/);
    if (groupEdit) return { mode: "edit", id: groupEdit[1] };
    if (pathname === "/grupos/crear/") return { mode: "create" };
    if (pathname === "/grupos/") return { mode: "list" };
    return null;
  },
  render: ({ mode, id }) => <Groups mode={mode} id={id} renderFrame={groupsFrame(mode)} />,
};
