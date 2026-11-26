import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { registerVisit, resolveBackHref } from "./volver";

const visit = (url: string) => {
  window.history.replaceState({}, "", url);
  registerVisit();
};
const stack = () => JSON.parse(window.sessionStorage.getItem("sisocNavStack") ?? "[]");

beforeEach(() => window.sessionStorage.clear());
afterEach(() => vi.restoreAllMocks());

describe("volver", () => {
  it("returns to the previous screen with its filters instead of home", () => {
    visit("/comedores/?provincia=3&page=2");
    visit("/comedores/7");
    expect(resolveBackHref()).toBe("/comedores/?provincia=3&page=2");
  });

  it("shares the stack written by native Django pages", () => {
    window.sessionStorage.setItem("sisocNavStack", JSON.stringify(["/centrodeinfancia/listar?q=x"]));
    visit("/cdi/centros/4/");
    expect(resolveBackHref()).toBe("/centrodeinfancia/listar?q=x");
  });

  it("prefers the declared destination, keeping its stacked querystring", () => {
    visit("/rendiciones/?estado=1");
    visit("/otra/");
    visit("/rendiciones/5/");
    expect(resolveBackHref("/rendiciones/")).toBe("/rendiciones/?estado=1");
    expect(resolveBackHref("/sin-visitar/")).toBe("/sin-visitar/");
  });

  it("does not stack transient steps, repeats or zigzags", () => {
    visit("/comedores/");
    visit("/comedores/7/editar/");
    visit("/comedores/7");
    visit("/comedores/7");
    visit("/comedores/");
    expect(stack()).toEqual(["/comedores/"]);
  });

  it("falls back to a same-origin referrer, then home, ignoring external URLs", () => {
    visit("/comedores/7");
    vi.spyOn(document, "referrer", "get").mockReturnValue("https://example.invalid/x");
    expect(resolveBackHref("//example.invalid/y")).toBe("/");
    vi.spyOn(document, "referrer", "get").mockReturnValue(window.location.origin + "/auditoria/?page=2");
    expect(resolveBackHref()).toBe("/auditoria/?page=2");
  });
});
