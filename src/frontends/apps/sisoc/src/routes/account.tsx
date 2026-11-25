import Account from "../Account";
import { accountFrame, confirmationFrame } from "../identityFrames";
import type { RouteDefinition } from "./types";

type AccountParams = { mode: "account" | "confirm" };

export const accountRoute: RouteDefinition<AccountParams> = {
  name: "account",
  match(pathname) {
    if (pathname === "/mi-cuenta/") return { mode: "account" };
    if (pathname === "/mi-cuenta/confirmar/") return { mode: "confirm" };
    return null;
  },
  render: ({ mode }) => (mode === "account"
    ? <Account mode="account" renderFrame={accountFrame} />
    : <Account mode="confirm" renderFrame={confirmationFrame} />),
};
