import PasswordChange from "../PasswordChange";
import type { RouteDefinition } from "./types";

type PasswordChangeParams = { mode: "form" | "done" };

// The voluntary form and its done page keep the installed admin template frame.
export const passwordChangeRoute: RouteDefinition<PasswordChangeParams> = {
  name: "password-change",
  match(pathname) {
    if (pathname === "/password_change/") return { mode: "form" };
    if (pathname === "/password_change/done/") return { mode: "done" };
    return null;
  },
  render: ({ mode }) => <PasswordChange mode={mode} />,
};
