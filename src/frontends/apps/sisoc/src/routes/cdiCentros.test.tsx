import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { centrosNavigation } from "./cdiCentros";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const cell = (text: string, sort = text, url: string | null = null) => ({ text, sort, url });
const row = (id: number, nombre: string, organizacion: string) => ({
  id,
  cells: [cell(nombre, nombre, `/centrodeinfancia/detalle/${id}`), organizacion ? cell(organizacion) : cell("-", "")],
  urls: { detail: `/centrodeinfancia/detalle/${id}`, edit: `/centrodeinfancia/editar/${id}`, delete: `/centrodeinfancia/eliminar/${id}` },
});
const lista = (over: Record<string, unknown> = {}) => ({
  breadcrumb: [{ text: "Centro de Desarrollo Infantil", url: "/centrodeinfancia/listar" }, { text: "Listar", url: null }],
  filters_config: { fields: [{ name: "nombre", label: "Nombre", type: "text" }], defaultField: "nombre" },
  favorites: { section: "", url: "/filtros-favoritos/", detail_url_template: "/filtros-favoritos/0/" },
  columns: {
    list_key: "centrodeinfancia_list", endpoint: "/columnas/", modal_id: "column-config-modal-centrodeinfancia_list", script_id: "column-config-data-centrodeinfancia_list",
    available: [{ key: "nombre", title: "Nombre", active: true, required: false, default: true }, { key: "organizacion", title: "Organización", active: true, required: false, default: true }],
    active: ["nombre", "organizacion"], defaults: ["nombre", "organizacion"],
  },
  headers: [{ key: "nombre", title: "Nombre" }, { key: "organizacion", title: "Organización" }],
  results: [row(2, "CDI Zeta", ""), row(1, "CDI Álamo", "Cooperadora")],
  page: { is_paginated: false, number: 1, previous: null, next: null, range: [1], count: 2, query_prefix: "" },
  can_export: false,
  nomina_ninos: null,
  urls: { list: "/centrodeinfancia/listar", add: "/centrodeinfancia/crear", export: "/centrodeinfancia/exportar" },
  messages: [],
  ...over,
});

function serve(data: unknown, status = 200, sessionStatus = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(
    url === "web/session/" ? { data: sessionStatus === 200 ? readyContext : { detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, status: sessionStatus }
      : { data, status },
  ));
}

function setup(path = "/centrodeinfancia/listar") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

const names = () => within(screen.getByRole("table")).getAllByRole("row").slice(1).map((r) => r.querySelector("td")?.textContent);

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("CDI centres list route", () => {
  it("owns only the native list path", () => {
    expect(findRoute("/centrodeinfancia/listar")?.route.name).toBe("cdi-centros");
    expect(findRoute("/centrodeinfancia/listar/")?.route.name).toBe("business");
    expect(findRoute("/centrodeinfancia/detalle/1")?.route.name).toBe("business");
  });

  it("loads the session and the API with the page query and draws the native table", async () => {
    serve(lista());
    setup("/centrodeinfancia/listar?busqueda=CDI&page=2");
    await screen.findByRole("heading", { name: "Buscar Centro de Desarrollo Infantil" });
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/?busqueda=CDI&page=2", expect.anything());
    expect(webGet).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(document.title).toBe("SISOC - Centros de Desarrollo Infantil"));
    const table = screen.getByRole("table");
    expect(table.className).toBe("table table-comedor-moderno");
    expect(within(table).getAllByRole("row").map((r) => r.textContent)).toEqual([
      "Nombre Organización Acciones", "CDI Zeta- Ver Editar Eliminar", "CDI ÁlamoCooperadora Ver Editar Eliminar",
    ]);
    expect(screen.getByRole("link", { name: "CDI Zeta" }).getAttribute("href")).toBe("/centrodeinfancia/detalle/2");
    expect(screen.getAllByRole("link", { name: /Editar/ })[0].getAttribute("href")).toBe("/centrodeinfancia/editar/2");
    expect(screen.getByRole("link", { name: "Nuevo Centro" }).getAttribute("href")).toBe("/centrodeinfancia/crear");
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("href")).toBe("/centrodeinfancia/listar");
    expect(screen.getByText("Se encontraron 2 resultados")).toBeDefined();
    expect(screen.queryByRole("button", { name: /Exportar búsqueda/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Descargar nómina de niños" })).toBeNull();
  });

  it("sorts locally by the data value and cycles asc, desc, none", async () => {
    serve(lista());
    setup();
    const header = await screen.findByRole("columnheader", { name: "Nombre" });
    fireEvent.click(header);
    expect(names()).toEqual(["CDI Álamo", "CDI Zeta"]);
    expect(header.className).toBe("sortable sort-asc");
    fireEvent.click(header);
    expect(names()).toEqual(["CDI Zeta", "CDI Álamo"]);
    expect(header.className).toBe("sortable sort-desc");
    fireEvent.click(header);
    expect(header.className).toBe("sortable");
    expect(names()).toEqual(["CDI Zeta", "CDI Álamo"]);
  });

  it("builds pagination links with the native prefix and Volver/Continuar", async () => {
    serve(lista({ page: { is_paginated: true, number: 2, previous: 1, next: 3, range: [1, 2, 3], count: 25, query_prefix: "busqueda=CDI&x=a%20b&" } }));
    setup();
    await screen.findByRole("link", { name: "Continuar" });
    const paginacion = within(document.querySelector(".pagination") as HTMLElement);
    expect(paginacion.getByRole("link", { name: "Volver" }).getAttribute("href")).toBe("?busqueda=CDI&x=a%20b&page=1");
    expect(paginacion.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?busqueda=CDI&x=a%20b&page=3");
    expect(paginacion.getByRole("link", { name: "2" }).closest("li")?.className).toContain("active");
    expect(screen.getByText("Se encontraron 25 resultados")).toBeDefined();
  });

  it("shows the empty message without a total", async () => {
    serve(lista({ results: [], page: { is_paginated: false, number: 1, previous: null, next: null, range: [1], count: null, query_prefix: "" } }));
    setup();
    expect(await screen.findByText("No se encontraron centros de desarrollo infantil")).toBeDefined();
    expect(screen.getByText("No hay centros que coincidan con los criterios de búsqueda.")).toBeDefined();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("exports with the current query and the active sort through the navigation seam", async () => {
    const assign = vi.spyOn(centrosNavigation, "assign").mockImplementation(() => undefined);
    serve(lista({ can_export: true }));
    setup("/centrodeinfancia/listar?busqueda=CDI");
    fireEvent.click(await screen.findByRole("columnheader", { name: "Nombre" }));
    fireEvent.click(screen.getByRole("button", { name: /Exportar búsqueda/ }));
    expect(assign).toHaveBeenCalledWith("/centrodeinfancia/exportar?busqueda=CDI&sort=nombre&direction=asc");
  });

  it("opens the children PDF modal with a required province select and closes with Escape", async () => {
    serve(lista({ nomina_ninos: { provincias: [{ id: 1, nombre: "Mendoza" }], url: "/centrodeinfancia/nomina-ninos/descargar/" } }));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Descargar nómina de niños" }));
    const dialog = screen.getByRole("dialog");
    const form = dialog.querySelector("form") as HTMLFormElement;
    expect(form.getAttribute("method")).toBe("get");
    expect(form.getAttribute("action")).toBe("/centrodeinfancia/nomina-ninos/descargar/");
    const select = within(dialog).getByLabelText("Provincia") as HTMLSelectElement;
    expect(select.required).toBe(true);
    expect([...select.options].map((o) => o.text)).toEqual(["Seleccionar provincia", "Mendoza"]);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("opens the column preferences and reloads after saving", async () => {
    const reload = vi.spyOn(centrosNavigation, "reload").mockImplementation(() => undefined);
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) })));
    serve(lista());
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Configurar columnas" }));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(reload).toHaveBeenCalled());
  });

  it("shows pending messages once", async () => {
    serve(lista({ messages: [{ message: "Centro de Desarrollo Infantil dado de baja correctamente.", level: "success" }] }));
    setup();
    expect(await screen.findByText("Centro de Desarrollo Infantil dado de baja correctamente.")).toBeDefined();
  });

  it("reports forbidden, not found and invalid payloads", async () => {
    serve({ detail: "No tiene permiso." }, 403);
    setup();
    expect(await screen.findByText("¡Ups! Algo salió mal.")).toBeDefined();
    cleanup();
    serve({ detail: "No encontrado." }, 404);
    setup();
    expect(await screen.findByText("No se encontró la página.")).toBeDefined();
    cleanup();
    serve({ ...lista(), results: [{ id: "x" }] });
    setup();
    expect(await screen.findByText("No se pudo cargar la página.")).toBeDefined();
  });
});
