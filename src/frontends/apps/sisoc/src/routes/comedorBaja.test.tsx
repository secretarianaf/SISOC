import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { comedorBajaNavigation } from "./comedorBaja";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const PATH = "/comedores/7/eliminar";
const API = "web/comedores/comedores/7/baja/";
const data = (over: Record<string, unknown> = {}) => ({
  id: 7, nombre: "Comedor Norte", messages: [],
  cascade_preview: { total_afectados: 2, total_baja_logica: 2, desglose_por_modelo: [{ modelo: "Comedor", cantidad: 1, modo: "baja_logica", ejemplos: ["Comedor Norte"] }] },
  urls: { cancel: "/comedores/7", list: "/comedores/listar" }, ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
let assign: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  assign = vi.spyOn(comedorBajaNavigation, "assign").mockImplementation(() => undefined);
  window.history.replaceState({}, "", PATH);
});
afterEach(() => { cleanup(); assign.mockRestore(); });

describe("Comedor baja route (CO07.01)", () => {
  it("owns only the native baja URL", () => {
    expect(findRoute(PATH)?.route.name).toBe("comedores-baja");
    for (const other of [`${PATH}/`, "/comedores/7/editar", "/comedores/7"]) expect(findRoute(other)?.route.name).not.toBe("comedores-baja");
  });

  it("shows the cascade preview and the native texts", async () => {
    serve(data());
    render(<App />);
    expect(await screen.findByText("COMEDOR NORTE")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Espacio Comunitario - Comedor Norte"));
    expect(screen.getByText("Bajas lógicas: 2")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/comedores/7");
    expect(screen.getByRole("link", { name: "Comedor Norte" }).getAttribute("href")).toBe("/comedores/7");
  });

  it("posts the baja and goes to the list", async () => {
    serve(data());
    webPost.mockResolvedValue({ status: 200, data: { redirect: "/comedores/listar" } });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/listar"));
    expect(webPost.mock.calls[0][0]).toBe(API);
  });

  it("a failed baja stays on the page with an error and does not navigate", async () => {
    serve(data());
    webPost.mockRejectedValue({ response: { status: 504, data: { uncertain: true } } });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    expect(await screen.findByText(/No se pudo dar de baja el comedor/)).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
  });
});
