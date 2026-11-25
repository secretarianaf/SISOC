import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const URL_API = "web/cdi/nomina/9/formulario/";
const payload = (over: Record<string, unknown> = {}) => ({
  rows: [
    { label: "ID", value: "9" },
    { label: "Centro", value: "CDI Girasoles" },
    { label: "Recibe apoyo por discapacidad", value: "-" },
    { label: "Observaciones", value: "Primera línea" },
  ],
  messages: [],
  ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(
    url === "web/session/" ? { data: readyContext, status: 200 } : { data, status },
  ));
}

function setup(path = "/centrodeinfancia/9/nomina/formulario/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => cleanup());

describe("CDI nomina form detail route", () => {
  it("owns only the native path with its trailing slash", () => {
    expect(findRoute("/centrodeinfancia/9/nomina/formulario/")?.route.name).toBe("cdi-nomina-formulario");
    expect(findRoute("/centrodeinfancia/9/nomina/formulario")?.route.name).toBe("business");
    expect(findRoute("/centrodeinfancia/0/nomina/formulario/")?.route.name).toBe("business");
  });

  it("loads the nomina by id and draws the heading and every row in order", async () => {
    serve(payload());
    setup();
    expect(await screen.findByRole("heading", { level: 1, name: "Detalle del Formulario de Nómina" })).toBeDefined();
    expect(webGet).toHaveBeenCalledWith(URL_API, expect.anything());
    expect(webGet).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(document.title).toBe("SISOC - Detalle - Formulario de Nómina"));
    expect(screen.getByRole("heading", { level: 5, name: "Información General" })).toBeDefined();
    const rows = within(screen.getByRole("table")).getAllByRole("row").map((r) => r.textContent);
    expect(rows).toEqual(["ID9", "CentroCDI Girasoles", "Recibe apoyo por discapacidad-", "ObservacionesPrimera línea"]);
    expect(screen.getByRole("table").className).toBe("table table-striped");
    expect(screen.getByText("ID").tagName).toBe("STRONG");
  });

  it("shows pending messages and reports forbidden, not found and invalid payloads", async () => {
    serve(payload({ messages: [{ message: "Listo.", level: "success" }] }));
    setup();
    expect(await screen.findByText("Listo.")).toBeDefined();
    cleanup();
    serve({ detail: "No tiene permiso." }, 403);
    setup();
    expect(await screen.findByText("¡Ups! Algo salió mal.")).toBeDefined();
    cleanup();
    serve({ detail: "No encontrado." }, 404);
    setup();
    expect(await screen.findByText("No se encontró la página.")).toBeDefined();
    cleanup();
    serve(payload({ rows: [{ label: "x" }] }));
    setup();
    expect(await screen.findByText("No se pudo cargar la página.")).toBeDefined();
  });
});
