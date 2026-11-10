import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../App";
import { duplasNavigation } from "./duplasList";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const session = {
  ...readyContext,
  navigation: [
    { id: "inicio", label: "Inicio", href: "/inicio/", children: [] },
    { id: "legajos", label: "Legajos", href: null, children: [] },
    {
      id: "configuracion-comedores", label: "Configuración de Comedores", href: null,
      children: [{ id: "dupla_list", label: "Equipos Técnicos", href: "/equipo-tecnico/", children: [] }],
    },
    { id: "mi_cuenta", label: "Mi cuenta", href: "/mi-cuenta/", children: [] },
  ],
};
const actions = (id: number) => [
  { label: "Editar", url: `/equipo-tecnico/${id}/editar/`, type: "editar", icon: "edit" },
  { label: "Eliminar", url: `/equipo-tecnico/${id}/eliminar/`, type: "eliminar", icon: "trash-alt" },
];
const fields = [
  { name: "nombre", label: "Nombre", type: "text" },
  { name: "tecnico", label: "Técnico (Nombre)", type: "text" },
  { name: "estado", label: "Estado", type: "text" },
];
const list = (over: Record<string, unknown> = {}) => ({
  breadcrumb: [{ text: "Equipos técnicos", url: "/equipo-tecnico/" }, { text: "Listar", url: null }],
  filters_config: { fields, operators: { text: ["contains"], number: ["eq"] }, defaultOperators: { text: "contains", number: "eq" } },
  favorites: { section: "duplas", url: "/ajax/filtros-favoritos/", detail_url_template: "/ajax/filtros-favoritos/0/" },
  urls: { list: "/equipo-tecnico/", reset: "/equipo-tecnico/", add: "/equipo-tecnico/crear/", export: "/equipo-tecnico/exportar/" },
  can_export: true,
  columns: {
    list_key: "duplas_list", endpoint: "/ajax/columnas-preferencias/", modal_id: "column-config-modal-duplas_list", script_id: "column-config-data-duplas_list",
    available: [
      { key: "nombre", title: "Nombre", active: true, required: true, default: true },
      { key: "estado", title: "Estado", active: true, required: false, default: true },
      { key: "id", title: "ID", active: false, required: false, default: false },
    ],
    active: ["nombre", "estado"], defaults: ["nombre", "estado"],
  },
  headers: [{ title: "Nombre", sortable: true, sort_key: "nombre" }, { title: "Estado", sortable: true, sort_key: "estado" }],
  results: [
    { id: 2, cells: ["Equipo Beta", "Activo"], actions: actions(2) },
    { id: 1, cells: ["Equipo Álamo", "Inactivo"], actions: actions(1) },
  ],
  page: { is_paginated: true, number: 1, count: 12, previous: null, next: 2, range: [1, 2], query_without_page: "filters=%7B%7D&" },
  messages: [],
  ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 7, nombre: "Equipo Siete", estado: "Activo", tecnicos: "Prueba Ana, Ejemplo Bruno", abogado: "Laura Legal",
  coordinador: "Clara Coordina", fecha: "01/10/2026 12:00",
  urls: { list: "/equipo-tecnico/", edit: "/equipo-tecnico/7/editar/", delete: "/equipo-tecnico/7/eliminar/" },
  messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(
    url === "web/session/" ? { data: session, status: 200 } : { data, status },
  ));
}

function setup(path = "/equipo-tecnico/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC - Insumos";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("Duplas routes (DU01.01)", () => {
  it("owns only the native list and detail paths", () => {
    expect(findRoute("/equipo-tecnico/")?.route.name).toBe("duplas");
    expect(findRoute("/equipo-tecnico/7/")?.route.name).toBe("duplas");
    for (const other of ["/equipo-tecnico", "/equipo-tecnico/7", "/equipo-tecnico/exportar/", "/equipo-tecnico/x/"]) {
      expect(findRoute(other)?.route.name).not.toBe("duplas");
    }
  });

  it("loads the core session and the list API with the same query, inside the native frame", async () => {
    serve(list());
    setup("/equipo-tecnico/?filters=%7B%7D&page=1");
    await screen.findByRole("table", {}, { timeout: 5000 });
    expect(webGet).toHaveBeenCalledWith("web/session/", expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(webGet).toHaveBeenCalledWith("web/comedores/duplas/?filters=%7B%7D&page=1", expect.anything());
    expect(document.title).toBe("SISOC - Listado de Equipos técnicos");
    expect(screen.getByRole("heading", { level: 3, name: "Equipo técnico" })).toBeDefined();
    expect(document.body.className).toContain("app-loaded");
    // The native sidebar opens its branch and marks the list for every page under the prefix.
    expect(document.querySelector('aside a[href="/equipo-tecnico/"]')?.className).toContain("active");
    const crumbs = document.querySelector("ol.breadcrumb.float-sm-right")!;
    expect(within(crumbs as HTMLElement).getByRole("link", { name: "Equipos técnicos" }).getAttribute("href")).toBe("/equipo-tecnico/");
    expect(crumbs.querySelectorAll("li")[1].className).toBe("breadcrumb-item active");
  });

  it("renders rows, actions, sortable headers, pagination and the count", async () => {
    serve(list());
    setup();
    const table = await screen.findByRole("table", {}, { timeout: 5000 });
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(3);
    expect([...rows[0].querySelectorAll("th")].map((th) => th.textContent?.trim())).toEqual(["Nombre", "Estado", "Acciones"]);
    expect(rows[1].querySelectorAll("td")[0].textContent).toBe("Equipo Beta");
    expect(within(rows[1]).getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/equipo-tecnico/2/editar/");
    expect(within(rows[1]).getByRole("link", { name: "Eliminar" }).className).toBe("btn btn-eliminar ");
    expect(screen.getByRole("link", { name: "2" }).getAttribute("href")).toBe("?filters=%7B%7D&page=2");
    expect(screen.getByRole("link", { name: "Siguiente" }).getAttribute("href")).toBe("?filters=%7B%7D&page=2");
    expect(screen.getByRole("link", { name: "Anterior" }).closest("li")?.className).toBe("page-item disabled");
    expect(screen.getByText("Se encontraron 12 resultados")).toBeDefined();
    expect(screen.getByRole("link", { name: "Agregar" }).getAttribute("href")).toBe("/equipo-tecnico/crear/");
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("data-restablecer-filtros-favoritos")).toBe("true");
  });

  it("sorts on the client like listSort.js and keeps the order on the third click", async () => {
    serve(list());
    setup();
    await screen.findByRole("table", {}, { timeout: 5000 });
    const header = document.querySelector<HTMLElement>('th[data-column="nombre"]')!;
    const names = () => [...document.querySelectorAll("tbody tr")].map((tr) => tr.querySelector("td")?.textContent);
    fireEvent.click(header);
    expect(names()).toEqual(["Equipo Álamo", "Equipo Beta"]);
    expect(header.className).toBe("sortable sort-asc");
    fireEvent.click(header);
    expect(names()).toEqual(["Equipo Beta", "Equipo Álamo"]);
    expect(header.querySelector("i")?.className).toBe("fas sort-icon fa-sort-down");
    fireEvent.click(header);
    expect(names()).toEqual(["Equipo Beta", "Equipo Álamo"]);
    expect(header.querySelector("i")?.className).toBe("fas sort-icon fa-sort");
  });

  it("exports through the native CSV GET with the filters and the current sort", async () => {
    const assign = vi.spyOn(duplasNavigation, "assign").mockImplementation(() => undefined);
    serve(list());
    setup("/equipo-tecnico/?filters=%7B%7D");
    await screen.findByRole("table", {}, { timeout: 5000 });
    fireEvent.click(document.querySelector<HTMLElement>('th[data-column="estado"]')!);
    fireEvent.click(document.querySelector<HTMLElement>('th[data-column="estado"]')!);
    fireEvent.click(screen.getByRole("button", { name: "Exportar búsqueda" }));
    expect(assign).toHaveBeenCalledWith("/equipo-tecnico/exportar/?filters=%7B%7D&sort=estado&direction=desc");
  });

  it("hides the export button without the export role and shows no count on an empty list", async () => {
    serve(list({ can_export: false, results: [], page: { is_paginated: false, number: 1, count: 0, previous: null, next: null, range: [1], query_without_page: "" } }));
    setup();
    await screen.findByRole("table", {}, { timeout: 5000 });
    expect(screen.queryByRole("button", { name: "Exportar búsqueda" })).toBeNull();
    expect(document.querySelector(".poncho-topbar")).not.toBeNull();
    expect(screen.getByText("No hay equipos técnicos disponibles.").getAttribute("colspan")).toBe("3");
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
    expect(document.querySelector(".pagination")).toBeNull();
  });

  it("serializes the filter rows into the native GET form like advanced_filters.js", async () => {
    serve(list());
    setup(`/equipo-tecnico/?filters=${encodeURIComponent(JSON.stringify({ logic: "AND", items: [{ field: "estado", op: "contains", value: "Activo" }] }))}`);
    await screen.findByRole("table", {}, { timeout: 5000 });
    const form = document.getElementById("filters-form") as HTMLFormElement;
    expect(form.getAttribute("method")).toBe("GET");
    expect(form.getAttribute("action")).toBe("/equipo-tecnico/");
    expect(form.dataset.seccionFiltrosFavoritos).toBe("duplas");
    const rowsOf = () => [...form.querySelectorAll(".poncho-search--row")];
    expect((rowsOf()[0].querySelector("[data-rol=campo]") as HTMLSelectElement).value).toBe("estado");
    expect((rowsOf()[0].querySelector("[data-rol=valor]") as HTMLInputElement).value).toBe("Activo");
    expect((rowsOf()[0].querySelector("[data-rol=quitar]") as HTMLElement).hidden).toBe(true);
    fireEvent.click(rowsOf()[0].querySelector("[data-rol=agregar]")!);
    expect(rowsOf()).toHaveLength(2);
    const second = rowsOf()[1];
    expect((second.querySelector("[data-rol=valor]") as HTMLInputElement).placeholder).toBe("Buscar por filtro 2");
    expect((second.querySelector("[data-rol=quitar]") as HTMLElement).hidden).toBe(false);
    // "Buscar por" (empty field) searches by the first field.
    fireEvent.change(second.querySelector("[data-rol=valor]")!, { target: { value: "  Beta " } });
    fireEvent.submit(form);
    expect(JSON.parse((document.getElementById("filters-input") as HTMLInputElement).value)).toEqual({
      logic: "AND",
      items: [{ field: "estado", op: "contains", value: "Activo" }, { field: "nombre", op: "contains", value: "Beta" }],
    });
    fireEvent.click(second.querySelector("[data-rol=quitar]")!);
    expect(rowsOf()).toHaveLength(1);
  });

  it("saves column preferences to the native endpoint and reloads", async () => {
    const reload = vi.spyOn(duplasNavigation, "reload").mockImplementation(() => undefined);
    const fetchMock = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) }));
    vi.stubGlobal("fetch", fetchMock);
    serve(list());
    setup();
    await screen.findByRole("table", {}, { timeout: 5000 });
    fireEvent.click(screen.getByRole("button", { name: "Configurar columnas" }));
    const dialog = screen.getByRole("dialog", { name: "Columnas visibles" });
    expect((within(dialog).getByLabelText("Nombre") as HTMLInputElement).disabled).toBe(true);
    expect(within(dialog).getByText("Obligatoria")).toBeDefined();
    fireEvent.click(within(dialog).getByLabelText("ID"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Guardar" }));
    await vi.waitFor(() => expect(reload).toHaveBeenCalled());
    expect(fetchMock).toHaveBeenCalledWith("/ajax/columnas-preferencias/", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ list_key: "duplas_list", columns: ["nombre", "estado", "id"] }),
    }));
  });

  it("shows queued messages as toasts", async () => {
    serve(list({ messages: [{ message: "Equipo técnico dado de baja correctamente.", level: "success" }] }));
    setup();
    expect(await screen.findByText("Equipo técnico dado de baja correctamente.")).toBeDefined();
  });

  it("renders the native detail card with and without coordinator", async () => {
    serve(detail());
    const { unmount } = setup("/equipo-tecnico/7/");
    expect(await screen.findByRole("heading", { name: "Información de la Dupla" })).toBeDefined();
    expect(webGet).toHaveBeenCalledWith("web/comedores/duplas/7/", expect.anything());
    expect(document.title).toBe("SISOC - Dupla: Equipo Siete");
    expect(screen.getByRole("heading", { level: 3, name: "Equipo Siete" })).toBeDefined();
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/equipo-tecnico/7/editar/");
    expect(screen.getByRole("link", { name: "Eliminar" }).className).toBe("btn btn-danger");
    expect(screen.getByRole("link", { name: "Duplas" }).getAttribute("href")).toBe("/equipo-tecnico/");
    const terms = [...document.querySelectorAll("dt")].map((dt) => `${dt.textContent}${dt.nextElementSibling?.textContent}`);
    expect(terms).toEqual(["Nombre:Equipo Siete", "Estado:Activo", "Técnico/s:Prueba Ana, Ejemplo Bruno", "Abogado:Laura Legal",
      "Coordinador:Clara Coordina", "Fecha de creación:01/10/2026 12:00"]);
    expect(document.querySelector('aside a[href="/equipo-tecnico/"]')?.className).toContain("active");
    unmount();
    serve(detail({ coordinador: null }));
    setup("/equipo-tecnico/7/");
    expect((await screen.findByText("Sin asignar")).className).toBe("badge badge-warning");
  });

  it("reports access prerequisites, denials and invalid payloads without rendering data", async () => {
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    const first = setup();
    expect((await screen.findByRole("link", { name: "Continuar en SISOC" })).getAttribute("href")).toBe("/password/first-change/");
    expect(screen.queryByRole("table")).toBeNull();
    first.unmount();
    serve({ results: "nope" });
    setup();
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar el equipo técnico.");
  });
});
