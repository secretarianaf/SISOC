import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { bajaValid, ciudadanoBajaNavigation } from "./ciudadanoBaja";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const baja = (over = {}) => ({
  id: 7, nombre_mayusculas: "BAJA, ANA", cancelar_url: "/ciudadanos/ver/7", messages: [],
  cascade_preview: {
    total_afectados: 3, total_baja_logica: 2, total_borrado_fisico: 1,
    desglose: [
      { modelo: "Ciudadano", cantidad: 1, baja_logica: true, ejemplos: ["Baja, Ana"] },
      { modelo: "Grupo familiar", cantidad: 1, baja_logica: true, ejemplos: [] },
      { modelo: "Aporte", cantidad: 1, baja_logica: false, ejemplos: ["a", "b"] },
    ],
  }, ...over,
});
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.history.replaceState({}, "", "/ciudadanos/eliminar/7");
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("baja de ciudadano", () => {
  it("owns only /ciudadanos/eliminar/<pk> and validates the payload", () => {
    expect(findRoute("/ciudadanos/eliminar/7")?.route.name).toBe("ciudadano-baja");
    expect(findRoute("/ciudadanos/eliminar/7/")?.route.name).not.toBe("ciudadano-baja");
    expect(bajaValid(baja())).toBe(true);
    expect(bajaValid(baja({ cancelar_url: "http://evil/" }))).toBe(false);
    expect(bajaValid({ ...baja(), cascade_preview: { total_afectados: 1 } })).toBe(false);
  });

  it("draws the native confirmation with the cascade preview", async () => {
    serve(baja());
    render(<App />);
    expect(await screen.findByText("BAJA, ANA")).toBeTruthy();
    expect(screen.getByText("Bajas lógicas: 2")).toBeTruthy();
    expect(screen.getByText("Borrados físicos técnicos: 1")).toBeTruthy();
    expect(screen.getByText("a, b")).toBeTruthy();
    expect(screen.getAllByText("Baja lógica").length).toBe(2);
    expect(screen.getByText("Borrado físico técnico")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/ciudadanos/ver/7");
  });

  it("omits the zero totals", async () => {
    serve(baja({ cascade_preview: { total_afectados: 0, total_baja_logica: 0, total_borrado_fisico: 0, desglose: [] } }));
    render(<App />);
    await screen.findByText("BAJA, ANA");
    expect(screen.queryByText(/Bajas lógicas:/)).toBeNull();
    expect(screen.queryByText(/Borrados físicos técnicos:/)).toBeNull();
  });

  it("posts once and follows the redirect", async () => {
    serve(baja());
    const assign = vi.spyOn(ciudadanoBajaNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/ciudadanos/listar" }, status: 200 });
    render(<App />);
    const boton = await screen.findByRole("button", { name: "Dar de baja" });
    fireEvent.click(boton);
    fireEvent.click(boton);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/ciudadanos/listar"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/ciudadanos/7/baja/");
  });

  it("shows a refusal or an unconfirmed outcome without navigating or resending", async () => {
    serve(baja());
    const assign = vi.spyOn(ciudadanoBajaNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValueOnce({ data: { detail: "Sin permiso" }, status: 403 });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Sin permiso");
    expect(assign).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Dar de baja" }).hasAttribute("disabled")).toBe(true);
    cleanup();
    webPost.mockRejectedValueOnce(new Error("network"));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudo confirmar el resultado");
    expect(webPost).toHaveBeenCalledTimes(2);
  });
});
