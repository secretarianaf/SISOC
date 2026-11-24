import Login from "../Login";
import type { RouteDefinition } from "./types";

export const loginRoute: RouteDefinition<Record<string, never>> = {
  name: "login",
  match: (pathname) => (pathname === "/" || pathname === "/login/" ? {} : null),
  render: () => <Login />,
};
