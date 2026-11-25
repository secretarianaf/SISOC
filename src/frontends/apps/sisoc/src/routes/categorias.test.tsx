import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
  mensajeDeError: vi.fn(() => "Error de prueba"),
  SinPermiso: class SinPermiso extends Error {},
}));

function setup(path = "/v2/sisoc/insumos/categorias/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC - Insumos";
  setViewport(false);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Insumos categories shell route", () => {
  it.each([
    ["/v2/sisoc/insumos/categorias/", "SISOC - Categorías de insumos", "web/insumos/categorias/"],
    ["/v2/sisoc/insumos/categorias/crear", "SISOC - Nueva categoría", "web/insumos/categorias/crear/"],
    ["/v2/sisoc/insumos/categorias/4/editar", "SISOC - Editar categoría", "web/insumos/categorias/4/editar/"],
    ["/v2/sisoc/insumos/categorias/4/eliminar", "SISOC - Eliminar categoría", "web/insumos/categorias/4/eliminar/"],
  ])("routes the category circuit %s to its own title and transport", async (path, title, endpoint) => {
    webGet.mockImplementation((url: string) => Promise.resolve({ data:
      url === "web/session/" ? readyContext :
      url.endsWith("eliminar/") ? { id: 4, nombre: "Manuales" } :
      url.endsWith("crear/") || url.endsWith("editar/") ? { initial: { programa: "", nombre: "", descripcion: "", orden: "0", activo: true }, options: { programa: [] } } :
      { count: 0, page: 1, page_size: 20, pages: 1, capabilities: { can_add: true, can_change: true, can_delete: true }, results: [] },
    }));
    setup(path);
    await screen.findByRole("navigation", { name: "Navegación principal" });
    await waitFor(() => expect(document.title).toBe(title));
    await waitFor(() => expect(webGet).toHaveBeenCalledWith(endpoint, expect.any(Object)));
    expect(webGet.mock.calls.some(([url]) => String(url).startsWith("web/insumos/options/"))).toBe(false);
    expect(window.location.pathname).toBe(path);
  });
  it("returns category creation to its own refreshed list and feedback", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve({ data:
      url === "web/session/" ? readyContext :
      url === "web/insumos/categorias/crear/" ? { initial: { programa: "", nombre: "", descripcion: "", orden: "0", activo: true }, options: { programa: [] } } :
      { count: 0, page: 1, page_size: 20, pages: 1, capabilities: { can_add: true, can_change: false, can_delete: false }, results: [] },
    }));
    webPost.mockResolvedValueOnce({ data: { ok: true, message: "Categoría creada correctamente.", redirect: "/insumos/categorias/" } });
    setup("/v2/sisoc/insumos/categorias/crear");
    await screen.findByRole("heading", { name: "Nueva categoría" });
    fireEvent.submit(screen.getByRole("button", { name: "Guardar categoría" }).closest("form")!);
    expect(await screen.findByText("Categoría creada correctamente.")).toBeDefined();
    expect(window.location.pathname).toBe("/v2/sisoc/insumos/categorias/");
    expect(await screen.findByRole("heading", { name: "Categorías de insumos" })).toBeDefined();
    expect(webGet).toHaveBeenCalledWith("web/insumos/categorias/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Categorías de insumos"));
    webGet.mockReset();
  });
  it("cancels a category deletion back to the category list without posting", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve({ data:
      url === "web/session/" ? readyContext :
      url === "web/insumos/categorias/4/eliminar/" ? { id: 4, nombre: "Manuales" } :
      { count: 0, page: 1, page_size: 20, pages: 1, capabilities: { can_add: false, can_change: false, can_delete: false }, results: [] },
    }));
    setup("/v2/sisoc/insumos/categorias/4/eliminar");
    fireEvent.click(await screen.findByRole("link", { name: "Cancelar" }));
    expect(window.location.pathname).toBe("/v2/sisoc/insumos/categorias/");
    expect(await screen.findByRole("heading", { name: "Categorías de insumos" })).toBeDefined();
    expect(webPost).not.toHaveBeenCalled();
    webGet.mockReset();
  });
});
