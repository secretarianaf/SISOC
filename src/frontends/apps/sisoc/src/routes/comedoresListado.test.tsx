import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { comedoresNavigation } from "./comedores";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const LISTA = "/comedores/listar";
const API = "web/comedores/comedores/";
const columns = {
  list_key: "comedores_list", endpoint: "/ajax/columnas-preferencias/", modal_id: "m", script_id: "s",
  available: [{ key: "nombre", title: "Nombre", active: true, required: true, default: true }], active: ["nombre"], defaults: ["nombre"],
};
const urls = (id: number) => ({ detalle: `/comedores/${id}`, editar: `/comedores/${id}/editar`, eliminar: `/comedores/${id}/eliminar` });
const row = (id: number, nombre: string, value: string, date: string | null = null) => ({
  id, nombre, urls: urls(id),
  cells: [{ key: "nombre", text: nombre }, { key: "ubicacion", lines: ["Chaco", "A / B", "Centro"] }, { key: "validacion", value, date }],
});
const list = (over: Record<string, unknown> = {}) => ({
  breadcrumb: [{ text: "Espacios Comunitarios", url: LISTA }, { text: "Listar", url: null }],
  filters_config: { fields: [{ name: "nombre", label: "Nombre", type: "text" }] },
  favorites: { section: "comedores", url: "/ajax/filtros-favoritos/", detail_url_template: "/ajax/filtros-favoritos/0/" },
  urls: { list: LISTA, reset: LISTA, add: "/comedores/crear", export: "/comedores/exportar" }, can_export: true, columns,
  headers: [{ key: "nombre", title: "Nombre", sortable: true }, { key: "ubicacion", title: "Ubicación", sortable: false }, { key: "validacion", title: "Validación", sortable: true }],
  results: [row(1, "Zeta", "Pendiente"), row(2, "Alfa", "Validado", "05/11/2026"), row(3, "Beta", "No Validado")],
  page: { is_paginated: true, number: 1, previous: null, next: 2, range: [1, 2, "…"], query_without_page: "filters=x&" }, messages: [], ...over,
});

function serve(data: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
let assign: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  assign = vi.spyOn(comedoresNavigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); assign.mockRestore(); });

const names = () => [...document.querySelectorAll("tbody tr td[data-nombre]")].map((td) => td.getAttribute("data-nombre"));

describe("Comedores list route (CO07.01)", () => {
  it("owns only the native list URL", () => {
    expect(findRoute(LISTA)?.route.name).toBe("comedores-listado");
    for (const other of [`${LISTA}/`, "/comedores/1", "/comedores/crear", "/comedores/exportar"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-listado");
    }
  });

  it("renders the native table, links, window pagination without a total and the CSV GET", async () => {
    serve(list());
    setup(`${LISTA}?filters=x`);
    await screen.findByText("Buscar Espacio Comunitario");
    expect(webGet).toHaveBeenCalledWith(`${API}?filters=x`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Espacios Comunitarios"));
    expect(screen.getByRole("link", { name: "Agregar" }).getAttribute("href")).toBe("/comedores/crear");
    expect(screen.getAllByRole("link", { name: /Editar/ })[0].getAttribute("href")).toBe("/comedores/1/editar");
    expect(screen.getAllByRole("link", { name: /Eliminar/ })[2].getAttribute("href")).toBe("/comedores/3/eliminar");
    expect(screen.getByRole("link", { name: "Alfa" }).getAttribute("href")).toBe("/comedores/2");
    expect(document.querySelector('td[data-validacion="Validado"] small')!.textContent).toBe("05/11/2026");
    expect(document.querySelector('td[data-validacion="Pendiente"] small')).toBeNull();
    expect(screen.getByRole("link", { name: "2" }).getAttribute("href")).toBe("?filters=x&page=2");
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Exportar búsqueda/ }));
    expect(assign).toHaveBeenCalledWith("/comedores/exportar?filters=x");
  });

  it("orders the shown page client-side: asc, desc, then the page order", async () => {
    serve(list());
    setup(LISTA);
    await screen.findByText("Zeta");
    const th = document.querySelector('th[data-column="nombre"]') as HTMLElement;
    fireEvent.click(th);
    expect(names()).toEqual(["Alfa", "Beta", "Zeta"]);
    expect(th.className).toBe("sortable sort-asc");
    fireEvent.click(th);
    expect(names()).toEqual(["Zeta", "Beta", "Alfa"]);
    fireEvent.click(th);
    expect(names()).toEqual(["Zeta", "Alfa", "Beta"]);
    fireEvent.click(document.querySelector('th[data-column="validacion"]')!);
    expect(names()).toEqual(["Beta", "Zeta", "Alfa"]);
  });

  it("shows the native empty message and hides export without permission", async () => {
    serve(list({ results: [], can_export: false, page: { is_paginated: false, number: 1, previous: null, next: null, range: [1], query_without_page: "" } }));
    setup(LISTA);
    expect(await screen.findByText("No se encontraron comedores")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Exportar/ })).toBeNull();
  });
});
