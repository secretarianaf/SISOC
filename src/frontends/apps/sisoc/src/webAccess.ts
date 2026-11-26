import type { AxiosResponse } from "axios";

export type PrerequisiteState =
  | "web_access_denied"
  | "password_change_required"
  | "profile_confirmation_required"
  | "mandatory_survey_required";
export type WebAccessState = "ready" | PrerequisiteState;

export type WebAccess = {
  state: WebAccessState;
  required_action_url: string | null;
};

export type WebPrerequisite = WebAccess & { state: PrerequisiteState };

const PREREQUISITE_STATES = new Set<PrerequisiteState>([
  "web_access_denied",
  "password_change_required",
  "profile_confirmation_required",
  "mandatory_survey_required",
]);

export function safeInternalPath(value: unknown): string | null {
  if (
    typeof value !== "string" ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\")
  ) {
    return null;
  }
  try {
    const resolved = new URL(value, window.location.origin);
    if (resolved.origin !== window.location.origin) return null;
    return `${resolved.pathname}${resolved.search}${resolved.hash}`;
  } catch {
    return null;
  }
}

export function prerequisiteFromForbidden(value: unknown): WebPrerequisite | null {
  if (!value || typeof value !== "object") return null;
  const response = value as Record<string, unknown>;
  if (
    typeof response.detail !== "string" ||
    typeof response.state !== "string" ||
    !PREREQUISITE_STATES.has(response.state as PrerequisiteState)
  ) {
    return null;
  }
  const actionUrl = response.required_action_url;
  if (actionUrl !== null && safeInternalPath(actionUrl) === null) return null;
  return {
    state: response.state as PrerequisiteState,
    required_action_url: actionUrl === null ? null : safeInternalPath(actionUrl),
  };
}

export function validateInsumosStatus(status: number): boolean {
  return (status >= 200 && status < 300) || status === 403;
}

export class InsumosForbiddenError extends Error {
  readonly response = { status: 403 };
  readonly prerequisite: WebPrerequisite | null;

  constructor(data: unknown) {
    super("Insumos request forbidden");
    this.name = "InsumosForbiddenError";
    this.prerequisite = prerequisiteFromForbidden(data);
  }
}

export async function rejectInsumosForbidden<T>(
  request: Promise<AxiosResponse<T>>,
): Promise<AxiosResponse<T>> {
  const response = await request;
  if (response.status === 403) throw new InsumosForbiddenError(response.data);
  return response;
}
