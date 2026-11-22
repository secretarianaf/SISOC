import RequiredPasswordChange from "../RequiredPasswordChange";
import { requiredPasswordFrame } from "../identityFrames";
import type { RouteDefinition } from "./types";

export const requiredPasswordRoute: RouteDefinition<Record<string, never>> = {
  name: "required-password",
  match: (pathname) => (pathname === "/password/first-change/" ? {} : null),
  render: () => <RequiredPasswordChange renderFrame={requiredPasswordFrame} />,
};
