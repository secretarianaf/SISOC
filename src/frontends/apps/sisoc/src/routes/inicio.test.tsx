import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import App from "../App";
import { setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
  mensajeDeError: vi.fn(() => "Error de prueba"),
  SinPermiso: class SinPermiso extends Error {},
}));

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC - Insumos";
  setViewport(false);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Pending-survey home route", () => {
  it("renders the pending-survey home in the legacy frame without the back button", async () => {
    window.history.replaceState(null, "", "/inicio/");
    webGet.mockResolvedValue({ data: { presentation: { user: { username: "synthetic", display_name: "Ana", avatar_initial: "A", role_label: "-" }, footer_version_label: "Versiones", legacy_frame_navigation: [{ id: "inicio", label: "Inicio", href: "/inicio/", children: [] }] }, home_variant: "default", round: null, messages: [] } });
    render(<App />);
    await screen.findByRole("navigation", { name: "Navegación principal" });
    expect(document.querySelector(".inicio-presentacion--default")).not.toBeNull();
    expect(document.querySelector(".sisoc-volver")).toBeNull();
    expect(webGet.mock.calls.some(([url]) => url === "web/session/")).toBe(false);
    webGet.mockReset();
  });
});
