import { describe, expect, it } from "vitest";
import { inetClient } from "./inet";

describe("inetClient", () => {
  it("uses the G1 session web API of VAT, without the old INET alias", () => {
    expect(inetClient.defaults.baseURL).toBe("/api/web/vat/");
    expect(inetClient.defaults.withCredentials).toBe(true);
  });
});
