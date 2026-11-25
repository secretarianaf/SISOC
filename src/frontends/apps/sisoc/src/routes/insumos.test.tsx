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

function setup(path = "/v2/sisoc/insumos/") {
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

describe("Insumos shell route", () => {
  it.each(["session", "form", "list"])("restores the outer title after unmounting a %s denial", async (kind) => {
    document.title = "Outer title";
    webGet.mockImplementation((url: string) => url === "web/session/" && kind !== "session"
      ? Promise.resolve({ data: readyContext })
      : Promise.resolve({ status: 403, data: { detail: "Forbidden" } }));
    const view = setup(kind === "list" ? "/v2/sisoc/insumos/" : "/v2/sisoc/insumos/crear/");
    await screen.findByRole("heading", { name: "¡Ups! Algo salió mal." });
    await waitFor(() => expect(document.title).toBe("SISOC - Error 403"));
    view.unmount();
    expect(document.title).toBe("Outer title");
  });
  it.each([
    ["/v2/sisoc/insumos/crear/", "SISOC - Nuevo insumo"],
    ["/v2/sisoc/insumos/9/editar/", "SISOC - Editar insumo"],
    ["/v2/sisoc/insumos/9/eliminar/", "SISOC - Eliminar insumo"],
    ["/v2/sisoc/insumos/", "SISOC - Insumos"],
  ])("matches the legacy document title at %s", async (path, title) => {
    webGet.mockImplementation((url: string) => Promise.resolve({ data:
      url === "web/session/" ? readyContext :
      url.endsWith("eliminar/") ? { id: 9, titulo: "Manual de prueba" } :
      url.endsWith("crear/") || url.endsWith("editar/") ? { initial: { programa: "", categoria: "", titulo: "", descripcion: "", activo: true }, options: { programa: [], categoria: [] }, current_file: null } :
      url === "web/insumos/options/" ? { categories: [] } :
      { count: 0, page: 1, page_size: 20, pages: 1, filters: { busqueda: "", categoria: "" }, results: [] },
    }));
    setup(path);
    await screen.findByRole("navigation", { name: "Navegación principal" });
    await waitFor(() => expect(document.title).toBe(title));
  });
  it("navigates from the canonical management action and returns to the canonical list", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve({ data:
      url === "web/session/" ? readyContext :
      url === "web/insumos/crear/" ? { initial: { programa: "", categoria: "", titulo: "", descripcion: "", activo: true }, options: { programa: [], categoria: [] }, current_file: null } :
      url === "web/insumos/options/" ? { categories: [] } :
      { count: 0, page: 1, page_size: 20, pages: 1, filters: { busqueda: "", categoria: "" }, results: [] },
    }));
    const list = setup("/insumos/?busqueda=Manual");
    const add = await screen.findByRole("link", { name: /Agregar insumo/ });
    expect(add.getAttribute("href")).toBe("/insumos/crear");
    expect(screen.getByRole("link", { name: "Insumos" }).getAttribute("href")).toBe("/insumos/");
    list.unmount();

    setup(add.getAttribute("href")!);
    await screen.findByRole("heading", { name: "Nuevo insumo" });
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/insumos/");
    webPost.mockResolvedValueOnce({ data: { ok: true, message: "Insumo creado correctamente.", redirect: "/insumos/" } });
    fireEvent.submit(screen.getByRole("button", { name: "Guardar insumo" }).closest("form")!);
    expect(await screen.findByText("Insumo creado correctamente.")).toBeDefined();
    expect(window.location.pathname).toBe("/insumos/");
    webGet.mockReset();
  });
  it("opens and cancels a canonical category action without using the preview", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve({ data:
      url === "web/session/" ? readyContext :
      url === "web/insumos/categorias/4/eliminar/" ? { id: 4, nombre: "Manuales" } :
      {
        count: 1, page: 1, page_size: 20, pages: 1,
        capabilities: { can_add: true, can_change: true, can_delete: true },
        results: [{ id: 4, nombre: "Manuales", programa: "Comedores", orden: 0, activo: true }],
      },
    }));
    const list = setup("/insumos/categorias/");
    expect((await screen.findByRole("link", { name: /Agregar categoría/ })).getAttribute("href"))
      .toBe("/insumos/categorias/crear");
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/insumos/categorias/4/editar");
    const removePath = screen.getByRole("link", { name: "Eliminar" }).getAttribute("href");
    expect(removePath).toBe("/insumos/categorias/4/eliminar");
    list.unmount();

    setup(removePath!);
    const cancel = await screen.findByRole("link", { name: "Cancelar" });
    expect(cancel.getAttribute("href")).toBe("/insumos/categorias/");
    fireEvent.click(cancel);
    expect(window.location.pathname).toBe("/insumos/categorias/");
    expect(await screen.findByRole("heading", { name: "Categorías de insumos" })).toBeDefined();
    expect(webPost).not.toHaveBeenCalled();
    webGet.mockReset();
  });
  it("opens the React create route, keeps legacy active ancestry and returns with feedback", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve({ data:
      url === "web/session/" ? readyContext :
      url === "web/insumos/crear/" ? { initial: { programa: "", categoria: "", titulo: "", descripcion: "", activo: true }, options: { programa: [], categoria: [] }, current_file: null } :
      url === "web/insumos/options/" ? { categories: [] } :
      { count: 0, page: 1, page_size: 20, pages: 1, filters: { busqueda: "", categoria: "" }, results: [] },
    }));
    webPost.mockResolvedValueOnce({ data: { ok: true, message: "Insumo creado correctamente.", redirect: "/insumos/" } });
    setup("/v2/sisoc/insumos/crear/");
    await screen.findByRole("heading", { name: "Nuevo insumo" });
    await waitFor(() => expect(document.title).toBe("SISOC - Nuevo insumo"));
    expect(screen.getByRole("link", { name: "Insumos" }).className).toContain("active");
    expect(screen.getByRole("button", { name: "Configuración de Comedores" }).getAttribute("aria-expanded")).toBe("true");
    fireEvent.submit(screen.getByRole("button", { name: "Guardar insumo" }).closest("form")!);
    expect(await screen.findByText("Insumo creado correctamente.")).toBeDefined();
    expect(window.location.pathname).toBe("/v2/sisoc/insumos/");
    expect(await screen.findByRole("heading", { name: "Buscar insumos" })).toBeDefined();
    await waitFor(() => expect(document.title).toBe("SISOC - Insumos"));
    webGet.mockReset();
  });
});
