import PendingSurvey from "../PendingSurvey";
import { homeFrame } from "../identityFrames";
import type { RouteDefinition } from "./types";

// The legacy home hosts the pending-survey answer circuit.
export const inicioRoute: RouteDefinition<Record<string, never>> = {
  name: "inicio",
  match: (pathname) => (pathname === "/inicio/" ? {} : null),
  render: () => <PendingSurvey renderFrame={homeFrame} />,
};
