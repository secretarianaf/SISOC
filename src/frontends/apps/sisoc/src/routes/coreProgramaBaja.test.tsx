import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { bajaValid, coreProgramaBajaNavigation } from "./coreProgramaBaja";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const baja = (over = {}) => ({ id: 7, nombre: "Alimentar", urls: { detail: "/programas/7/" }, messages: [], ...over });
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.history.replaceState({}, "", "/programas/7/eliminar/");
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("baja de programa (T05.02)", () => {
  it("owns only /programas/<pk>/eliminar/ and validates the payload", () => {
    expect(findRoute("/programas/7/eliminar/")?.route.name).toBe("core-programa-baja");
    expect(findRoute("/programas/7/eliminar")?.route.name).not.toBe("core-programa-baja");
    expect(bajaValid(baja())).toBe(true);
    expect(bajaValid(baja({ urls: { detail: "http://evil/" } }))).toBe(false);
  });

  it("draws the native confirmation with its verbatim texts and links", async () => {
    serve(baja());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Confirmar eliminación" })).toBeTruthy();
    expect(webGet.mock.calls.map((c) => c[0])).toContain("web/core/programas/7/eliminar/");
    expect(screen.getByText("Alimentar").tagName).toBe("STRONG");
    expect(screen.getByText("Esta acción no se puede deshacer. Verificá que el programa no esté en uso antes de eliminarlo.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/programas/7/");
    await waitFor(() => expect(document.title).toBe("SISOC - Confirmar eliminación"));
  });

  it("posts once and follows the redirect to the list", async () => {
    serve(baja());
    const assign = vi.spyOn(coreProgramaBajaNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/programas/" }, status: 200 });
    render(<App />);
    const boton = await screen.findByRole("button", { name: /Eliminar/ });
    fireEvent.click(boton);
    fireEvent.click(boton);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/programas/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/core/programas/7/eliminar/");
  });

  it("shows a refusal or an unconfirmed outcome without navigating or resending", async () => {
    serve(baja());
    const assign = vi.spyOn(coreProgramaBajaNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValueOnce({ data: { detail: "Sin permiso" }, status: 403 });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Eliminar/ }));
    expect((await screen.findByRole("alert")).textContent).toBe("Sin permiso");
    expect((screen.getByRole("button", { name: /Eliminar/ }) as HTMLButtonElement).disabled).toBe(true);
    cleanup();
    webPost.mockRejectedValueOnce(new Error("network"));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Eliminar/ }));
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudo confirmar el resultado");
    expect(assign).not.toHaveBeenCalled();
    expect(webPost).toHaveBeenCalledTimes(2);
  });
});
