import { describe, expect, it } from "vitest";
import type { AxiosResponse } from "axios";
import {
  InsumosForbiddenError,
  prerequisiteFromForbidden,
  rejectInsumosForbidden,
  validateInsumosStatus,
} from "./webAccess";

function response<T>(status: number, data: T): AxiosResponse<T> {
  return { status, data } as AxiosResponse<T>;
}

describe("INS-A permission response adapter", () => {
  it("accepts only ordinary success statuses and 403 for local inspection", () => {
    expect(validateInsumosStatus(200)).toBe(true);
    expect(validateInsumosStatus(299)).toBe(true);
    expect(validateInsumosStatus(403)).toBe(true);
    expect(validateInsumosStatus(400)).toBe(false);
    expect(validateInsumosStatus(401)).toBe(false);
    expect(validateInsumosStatus(500)).toBe(false);
  });

  it("turns HTML or other 403 bodies into a static denial error without exposing them", async () => {
    await expect(rejectInsumosForbidden(Promise.resolve(
      response(403, "<html>server-only content</html>"),
    ))).rejects.toBeInstanceOf(InsumosForbiddenError);
    await expect(rejectInsumosForbidden(Promise.resolve(
      response(200, { ok: true }),
    ))).resolves.toMatchObject({ status: 200, data: { ok: true } });
  });

  it("accepts only known non-ready prerequisite states with safe optional action paths", () => {
    expect(prerequisiteFromForbidden({
      detail: "Debe completar el requisito de acceso web.",
      state: "password_change_required",
      required_action_url: "/password/first-change/",
    })).toEqual({
      state: "password_change_required",
      required_action_url: "/password/first-change/",
    });
    expect(prerequisiteFromForbidden({
      detail: "Debe completar el requisito de acceso web.",
      state: "web_access_denied",
      required_action_url: null,
    })).toEqual({ state: "web_access_denied", required_action_url: null });
    expect(prerequisiteFromForbidden({ detail: "Forbidden" })).toBeNull();
    expect(prerequisiteFromForbidden({
      detail: "Not a prerequisite",
      state: "ready",
      required_action_url: "/inicio/",
    })).toBeNull();
    expect(prerequisiteFromForbidden({
      detail: "Unsafe destination",
      state: "profile_confirmation_required",
      required_action_url: "https://example.invalid/",
    })).toBeNull();
  });
});
