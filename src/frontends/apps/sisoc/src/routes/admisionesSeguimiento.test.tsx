import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { listValid } from "./admisionesListas";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const TECNICOS = "/comedores/admisiones/tecnicos/listar";
const LEGALES = "/comedores/admisiones/legales/listar";
const headers = ["ID Comedor", "Tipo", "Nombre", "Organización", "N° Expediente", "N° Convenio", "Provincia", "Equipo técnico", "Estado", "Última Modificación"]
  .map((title) => ({ title, sort_url: title === "Nombre" ? "?order_by=nombre&direction=asc" : null, sort_direction: null }));
const cell = (content: string, extra: Record<string, unknown> = {}) => ({ content, data_attr: null, data_value: null, link_url: null, link_class: null, link_title: null, ...extra });
const lista = (over: Record<string, unknown> = {}) => ({
  title: "Admisiones - Equipos técnicos",
  breadcrumb: [{ text: "", url: "admisiones_tecnicos_listar", active: false }, { text: "", url: null, active: true }],
  filters_config: { fields: [{ name: "comedor_nombre", label: "Nombre del comedor", type: "text" }] },
  favorites: { section: "admisiones_tecnicos", url: "/filtros-favoritos/", detail_url_template: "/filtros-favoritos/0/" },
  urls: { list: TECNICOS, reset: TECNICOS },
  columns: { list_key: "admisiones_tecnicos_list", endpoint: "/columnas/", modal_id: "columnConfigModal", script_id: "column-config-json", available: [], active: [], defaults: [] },
  headers,
  results: [{
    cells: [cell("7"), cell("Incorporación"), cell("Comedor Sintético", { data_attr: "nombre", data_value: "Comedor Sintético", link_url: "/comedores/7", link_class: "font-weight-bold link-handler", link_title: "Ver detalles" }),
      cell("Org"), cell("EX-1"), cell("3°"), cell("Chaco"), cell("-"), cell("Iniciado"), cell("01/11/2026")],
    actions: [{ label: "Ver", badge: "Rectificar", url: "/comedores/admisiones/tecnicos/editar/5", type: "warning" }],
  }],
  page: { is_paginated: false, number: 1, count: 1, has_rows: true, previous: null, next: null, range: [1], query_without_page: "" },
  messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => cleanup());

describe("Admision lists route (AD03.01)", () => {
  it("owns only the two native list pages, without a trailing slash", () => {
    expect(findRoute(TECNICOS)?.params).toEqual({ page: "tecnicos" });
    expect(findRoute(LEGALES)?.params).toEqual({ page: "legales" });
    for (const other of [`${TECNICOS}/`, "/comedores/admisiones/tecnicos/editar/5", "/comedores/admisiones/legales/ver/5"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-admisiones-seguimiento");
    }
  });

  it("renders the technical list with the name link, the badge and the native action", async () => {
    serve(lista());
    setup(`${TECNICOS}?page=1`);
    await screen.findByText("Admisiones - Equipos técnicos");
    expect(webGet).toHaveBeenCalledWith("web/comedores/admisiones/tecnicos/?page=1", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Admisiones"));
    expect(screen.getByRole("link", { name: "Comedor Sintético" }).getAttribute("href")).toBe("/comedores/7");
    const ver = screen.getByTitle("Ver");
    expect(ver.getAttribute("href")).toBe("/comedores/admisiones/tecnicos/editar/5");
    expect(ver.className).toBe("btn btn-warning position-relative");
    expect(within(ver).getByText("Rectificar").className).toContain("bg-danger");
    expect(screen.getByRole("link", { name: "Nombre" }).getAttribute("href")).toBe("?order_by=nombre&direction=asc");
  });

  it("renders the legal list and its empty message", async () => {
    serve(lista({ title: "Expedientes - Legales", results: [], page: { is_paginated: false, number: 1, count: 0, has_rows: false, previous: null, next: null, range: [], query_without_page: "" } }));
    setup(LEGALES);
    await screen.findByText("Expedientes - Legales");
    expect(webGet).toHaveBeenCalledWith("web/comedores/admisiones/legales/", expect.anything());
    expect(screen.getByText("No hay expedientes registrados.")).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Comedores - Expedientes"));
  });

  it("keeps the 403 and malformed envelopes out of the page", async () => {
    expect(listValid({})).toBe(false);
    expect(listValid({ ...lista(), results: [{ cells: [cell("x", { link_url: "https://evil.example" })], actions: [] }] })).toBe(false);
    expect(listValid(lista())).toBe(true);
    serve({}, 200);
    setup(TECNICOS);
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});
