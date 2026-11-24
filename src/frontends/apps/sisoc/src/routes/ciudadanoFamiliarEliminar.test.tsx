import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { ciudadanoBajaNavigation } from "./ciudadanoBaja";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const relacion = (over = {}) => ({
  id: 5, nombre_mayusculas: "UNO, ANA - ZETA, ZOE (HIJO/A)", cancelar_url: "/ciudadanos/ver/7", messages: [],
  cascade_preview: {
    total_afectados: 1, total_baja_logica: 1, total_borrado_fisico: 0,
    desglose: [{ modelo: "Grupo familiar", cantidad: 1, baja_logica: true, ejemplos: [] }],
  }, ...over,
});
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.history.replaceState({}, "", "/ciudadanos/familiares/5/eliminar");
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("desvincular un familiar", () => {
  it("owns only /ciudadanos/familiares/<pk>/eliminar", () => {
    expect(findRoute("/ciudadanos/familiares/5/eliminar")?.route.name).toBe("ciudadano-familiar-eliminar");
    expect(findRoute("/ciudadanos/familiares/5/eliminar/")?.route.name).not.toBe("ciudadano-familiar-eliminar");
    expect(findRoute("/ciudadanos/eliminar/5")?.route.name).toBe("ciudadano-baja");
  });

  it("draws the native confirmation of the relation and its cancel link", async () => {
    serve(relacion());
    render(<App />);
    expect(await screen.findByText("UNO, ANA - ZETA, ZOE (HIJO/A)")).toBeTruthy();
    expect(screen.getByText("Bajas lógicas: 1")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/ciudadanos/ver/7");
    expect(webGet).toHaveBeenCalledWith("web/ciudadanos/familiares/5/eliminar/", expect.anything());
  });

  it("sends the native next to both calls and posts once", async () => {
    window.history.replaceState({}, "", "/ciudadanos/familiares/5/eliminar?next=/ciudadanos/listar");
    serve(relacion({ cancelar_url: "/ciudadanos/listar" }));
    const assign = vi.spyOn(ciudadanoBajaNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/ciudadanos/listar" }, status: 200 });
    render(<App />);
    const boton = await screen.findByRole("button", { name: "Dar de baja" });
    expect(webGet).toHaveBeenCalledWith("web/ciudadanos/familiares/5/eliminar/?next=/ciudadanos/listar", expect.anything());
    fireEvent.click(boton);
    fireEvent.click(boton);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/ciudadanos/listar"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/ciudadanos/familiares/5/eliminar/?next=/ciudadanos/listar");
  });

  it("shows a refusal without navigating", async () => {
    serve(relacion());
    const assign = vi.spyOn(ciudadanoBajaNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValueOnce({ data: { detail: "Sin permiso" }, status: 403 });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Sin permiso");
    expect(assign).not.toHaveBeenCalled();
  });
});
