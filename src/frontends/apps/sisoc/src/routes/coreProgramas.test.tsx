import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, waitFor, render, screen, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { programaDetailValid, programasListValid } from "./coreProgramas";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const urls = (id: number) => ({ detail: `/programas/${id}/`, edit: `/programas/${id}/editar/`, delete: `/programas/${id}/eliminar/` });
const list = (over = {}) => ({
  items: [
    { id: 1, nombre: "Alimentar", organismo: "Org Uno", estado: true, urls: urls(1) },
    { id: 2, nombre: "Inactivo", organismo: null, estado: false, urls: urls(2) },
  ],
  urls: { create: "/programas/crear/" },
  pagination: { paginated: true, number: 1, previous: null, next: 2, range: [1, 2, "…"], count: 30 },
  messages: [], ...over,
});
const detail = (over = {}) => ({
  id: 1, nombre: "Alimentar", estado: true, organismo: "Org Uno", observaciones: null, descripcion: "Texto",
  urls: { list: "/programas/", ...urls(1) }, messages: [], ...over,
});
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("programas (T05.01)", () => {
  it("owns /programas/ and /programas/<pk>/ only and validates the payloads", () => {
    expect(findRoute("/programas/")?.route.name).toBe("core-programas");
    expect(findRoute("/programas/7/")?.route.name).toBe("core-programas");
    expect(findRoute("/programas/7")?.route.name).not.toBe("core-programas");
    expect(findRoute("/programas/crear/")?.route.name).toBe("core-programa-form");
    expect(programasListValid(list())).toBe(true);
    expect(programasListValid(list({ items: [{ id: "x" }] }))).toBe(false);
    expect(programasListValid(list({ urls: { create: "http://evil/" } }))).toBe(false);
    expect(programaDetailValid(detail())).toBe(true);
    expect(programaDetailValid(detail({ estado: "si" }))).toBe(false);
  });

  it("draws the native list and asks for the page's own query string", async () => {
    window.history.replaceState({}, "", "/programas/?page=2");
    serve(list({ messages: [{ message: "Programa creado correctamente.", level: "success" }] }));
    render(<App />);
    expect(await screen.findByText("Alimentar")).toBeTruthy();
    expect(webGet.mock.calls.map((c) => c[0])).toContain("web/core/programas/?page=2");
    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getByText("Org Uno")).toBeTruthy();
    expect(within(rows[1]).getByText("Activo").className).toBe("badge badge-success");
    expect(within(rows[2]).getByText("-")).toBeTruthy();
    expect(within(rows[2]).getByText("Inactivo", { selector: "span" }).className).toBe("badge badge-secondary");
    expect(within(rows[1]).getByRole("link", { name: "Ver" }).getAttribute("href")).toBe("/programas/1/");
    expect(within(rows[1]).getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/programas/1/editar/");
    expect(within(rows[1]).getByRole("link", { name: "Eliminar" }).getAttribute("href")).toBe("/programas/1/eliminar/");
    expect(screen.getByRole("link", { name: /Agregar/ }).getAttribute("href")).toBe("/programas/crear/");
    expect(screen.getByText("Se encontraron 30 resultados")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?page=2");
    expect(screen.getByText("Programa creado correctamente.")).toBeTruthy();
  });

  it("shows the empty state and keeps other query parameters in the page links", async () => {
    window.history.replaceState({}, "", "/programas/?x=1&page=2");
    serve(list({ items: [], pagination: { paginated: true, number: 2, previous: 1, next: null, range: [1, 2], count: 0 } }));
    const { container } = render(<App />);
    expect(await screen.findByText("No hay programas registrados.")).toBeTruthy();
    const pagination = container.querySelector(".pagination") as HTMLElement;
    expect(within(pagination).getByRole("link", { name: "Volver" }).getAttribute("href")).toBe("?x=1&page=1");
  });

  it("draws the native detail with dashes for empty values", async () => {
    window.history.replaceState({}, "", "/programas/1/");
    serve(detail());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Alimentar" })).toBeTruthy();
    expect(webGet.mock.calls.map((c) => c[0])).toContain("web/core/programas/1/");
    expect(screen.getByText("Estado:").parentElement?.textContent).toBe("Estado: Activo");
    expect(screen.getByText("Observaciones:").parentElement?.textContent).toBe("Observaciones: -");
    expect(screen.getByText("Texto")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Editar/ }).getAttribute("href")).toBe("/programas/1/editar/");
    expect(screen.getByRole("link", { name: /Eliminar/ }).getAttribute("href")).toBe("/programas/1/eliminar/");
    await waitFor(() => expect(document.title).toBe("SISOC - Detalle Programa"));
  });

  it("shows the access screen on 403 and the error screen on a malformed payload", async () => {
    window.history.replaceState({}, "", "/programas/");
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/"
      ? { data: readyContext, status: 200 } : { data: { detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, status: 403 }));
    render(<App />);
    expect((await screen.findByRole("heading", { level: 1 })).textContent).toBe("Antes de continuar");
    expect(screen.getByText("Necesitás actualizar tu contraseña para continuar.")).toBeTruthy();
    cleanup();
    serve({ items: "mal" });
    render(<App />);
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar la página.");
  });
});
