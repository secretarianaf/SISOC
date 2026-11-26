import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
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

describe("Groups route", () => {
  it("keeps the native groups-list Administration tree closed and shows its breadcrumb", async () => {
    window.history.replaceState(null, "", "/grupos/");
    webGet.mockResolvedValue({ data: { presentation: { user: { username: "synthetic", display_name: "Ana", avatar_initial: "A", role_label: "-" }, footer_version_label: "Versiones", legacy_frame_navigation: [{ id: "administracion-sistema", label: "Administración del sistema", href: null, children: [{ id: "grupos", label: "Grupos", href: "/grupos/", children: [] }] }] }, query: "", messages: [], can_export: false, items: [], columns: { list_key: "grupos_list", endpoint: "/ajax/columnas-preferencias/", active: ["name"], defaults: ["name"], available: [{ key: "name", title: "Nombre", active: true, required: false, default: true }] } } });
    render(<App />);
    const control = await screen.findByRole("button", { name: "Administración del sistema" });
    expect(control.getAttribute("aria-expanded")).toBe("false");
    expect(document.querySelector('.breadcrumb a[href="/grupos/"]')?.textContent).toBe("Grupos");
    expect(document.querySelector(".sisoc-volver")).not.toBeNull();
    webGet.mockReset();
  });
  it.each([
    ["/grupos/", "web/groups/"],
    ["/grupos/crear/", "web/groups/create/"],
    ["/grupos/editar/7/", "web/groups/7/edit/"],
  ])("routes the group circuit %s to its own guarded transport", async (path, endpoint) => {
    window.history.replaceState(null, "", path);
    webGet.mockResolvedValue({ status: 403, data: { detail: "Denegado" } });
    render(<App />);
    await waitFor(() => expect(webGet).toHaveBeenCalledWith(endpoint, expect.any(Object)));
    expect(webGet.mock.calls.some(([url]) => url === "web/session/")).toBe(false);
    webGet.mockReset();
  });
});
