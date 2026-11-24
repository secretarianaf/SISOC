import PasswordReset from "../PasswordReset";
import type { RouteDefinition } from "./types";

type PasswordResetParams =
  | { mode: "request" | "done" | "complete" }
  | { mode: "confirm"; uidb64: string | null };

// Recovery keeps the source token exchange server-side; only `set-password` carries a uid.
const RECOVERY = /^\/(?:reset|password\/reset\/confirm)\/([^/]+)\/([^/]+)\/$/;

export const passwordResetRoute: RouteDefinition<PasswordResetParams> = {
  name: "password-reset",
  match(pathname) {
    if (pathname === "/password_reset/") return { mode: "request" };
    if (pathname === "/password_reset/done/") return { mode: "done" };
    if (pathname === "/reset/done/") return { mode: "complete" };
    const recovery = pathname.match(RECOVERY);
    if (recovery) return { mode: "confirm", uidb64: recovery[2] === "set-password" ? recovery[1] : null };
    return null;
  },
  render: (params) => (params.mode === "confirm"
    ? <PasswordReset mode="confirm" uidb64={params.uidb64} />
    : <PasswordReset mode={params.mode} />),
};
