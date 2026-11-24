import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { transaccionesValid } from "./comedorTransacciones";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const DETALLE = "/comedores/7/transacciones";
const ENDPOINT = "web/comedores/comedores/7/transacciones/";

const fila = (periodo: string, over: Record<string, unknown> = {}) => ({
  periodo, movimientos: "14", transferido: "$1.234.567", gastado: "$1.500", saldo: "$0", ...over,
});
const data = (over: Record<string, unknown> = {}) => ({
  comedor: { id: 7, nombre: "Comedor Norte" },
  transacciones: [fila("2026-09"), fila("2026-08", { movimientos: "3", transferido: "Sin información", gastado: "Sin información", saldo: "Sin información" })],
  urls: { comedores: "/comedores/listar", comedor: "/comedores/7" },
  messages: [], ...over,
});

function serve(payload: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: payload, status: 200 }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => { vi.clearAllMocks(); setViewport(false); });
afterEach(() => cleanup());

describe("Comedor DW transactions route (CO07.01)", () => {
  it("owns only the native history URL", () => {
    expect(findRoute(DETALLE)?.route.name).toBe("comedor-transacciones");
    for (const other of ["/comedores/7/transacciones/", "/comedores/7", "/comedores/0/transacciones", "/comedores/7/transacciones/x"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedor-transacciones");
    }
  });

  it("reads the endpoint and shows the native table with the amounts as given", async () => {
    serve(data());
    setup(DETALLE);
    await screen.findByText("2026-09");
    expect(webGet).toHaveBeenCalledWith(ENDPOINT, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Transacciones - Comedor Norte"));
    expect(screen.getByRole("heading", { level: 4, name: "Transacciones - Nación Servicios" })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 3, name: "Transacciones - Nación Servicios" })).toBeTruthy();
    expect([...document.querySelectorAll("thead th")].map((th) => th.textContent)).toEqual(["Período", "Movimientos", "Transferido", "Gastado", "Saldo Cereado"]);
    const rows = [...document.querySelectorAll("tbody tr")].map((tr) => [...tr.querySelectorAll("td")].map((td) => td.textContent));
    expect(rows).toEqual([["2026-09", "14", "$1.234.567", "$1.500", "$0"], ["2026-08", "3", "Sin información", "Sin información", "Sin información"]]);
    expect(document.querySelectorAll("td.text-end")).toHaveLength(8);
    // Read only: no control writes or filters anything.
    expect(document.querySelector("table")!.closest(".card")!.querySelector("form, input, select, button")).toBeNull();
  });

  it("forwards the page query", async () => {
    serve(data());
    setup(`${DETALLE}?page=2`);
    await screen.findByText("2026-09");
    expect(webGet).toHaveBeenCalledWith(`${ENDPOINT}?page=2`, expect.anything());
  });

  it("shows the empty message when there is no data", async () => {
    serve(data({ transacciones: [] }));
    setup(DETALLE);
    const alert = await screen.findByText("Sin información");
    expect(alert.closest(".alert")!.textContent).toBe(" Sin información - No hay registros de transacciones disponibles para este comedor.");
    expect(document.querySelector("table")).toBeNull();
  });

  it("shows the access screen on 403 and an error on an invalid payload", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "no" }, status: 403 }));
    setup(DETALLE);
    await waitFor(() => expect(screen.queryByText("Cargando transacciones…")).toBeNull());
    expect(screen.queryByRole("table")).toBeNull();
    cleanup();
    serve({ nope: true });
    setup(DETALLE);
    await screen.findByText("No se pudo cargar la página.");
  });

  it("validates the payload shape", () => {
    expect(transaccionesValid(data())).toBe(true);
    expect(transaccionesValid(data({ transacciones: [fila("2026-09", { saldo: 1 })] }))).toBe(false);
    expect(transaccionesValid(data({ urls: { comedores: "//evil.test", comedor: "/comedores/7" } }))).toBe(false);
    expect(transaccionesValid(null)).toBe(false);
  });
});
