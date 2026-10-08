import { expect, it } from "vitest";
import { formatDate, formatDateTime } from "./dates";

it("presenta fechas sin desplazar el día por UTC", () => {
  expect(formatDate("2026-10-01")).toMatch(/^0?1\/10\/2026$/);
  expect(formatDate("invalid")).toBe("—");
  expect(formatDateTime("2026-10-02T00:00:00Z")).toMatch(/^0?1\/10\/26/);
});
