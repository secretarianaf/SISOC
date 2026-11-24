import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { listValid, organizacionesNavigation } from "./organizacionesList";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const LISTADO = "/organizaciones/listar";
const API = "web/comedores/organizaciones/listado/";
const HEADERS = ["CUIT", "Nombre", "Comedores", "Tipo de entidad", "Subtipo de entidad", "Teléfono", "Email", "Acciones"];
const fields = [
  { name: "nombre", label: "Nombre", type: "text" },
  { name: "cuit", label: "CUIT", type: "number" },
  { name: "sin_vencimiento", label: "Sin vencimiento", type: "boolean" },
];
const cell = (text: string, sort: string | null = text) => ({ text, sort });
const actions = (id: number, manage = true) => [
  { label: "Ver", url: `/organizaciones/detalle/${id}`, class: "btn btn-primary link-handler", title: "Ver detalle de la organización", icon: "fas fa-eye" },
  ...(manage ? [
    { label: "Editar", url: `/organizaciones/editar/${id}`, class: "btn btn-editar link-handler", title: "Editar organización", icon: "fas fa-edit" },
    { label: "Eliminar", url: `/organizaciones/eliminar/${id}`, class: "btn btn-eliminar link-handler", title: "Eliminar organización", icon: "fas fa-trash-alt" },
  ] : []),
];
const row = (id: number, nombre: string, cuit: string, comedores: string, manage = true) => ({
  id, detail_url: `/organizaciones/detalle/${id}`, actions: actions(id, manage),
  cells: [cell(cuit, cuit === "-" ? "" : cuit), cell(nombre), cell(comedores), cell("-", ""), cell("-", ""), cell("-", ""), cell("-", "")],
});
const list = (over: Record<string, unknown> = {}) => ({
  breadcrumb: [{ text: "Organizaciones", url: LISTADO }, { text: "Listar", url: null }],
  filters_config: { fields, operators: {} },
  favorites: { section: "", url: "/ajax/filtros-favoritos/", detail_url_template: "/ajax/filtros-favoritos/0/" },
  urls: { list: LISTADO, reset: LISTADO, add: "/organizaciones/crear", export: "/organizaciones/exportar" },
  can_add: true, can_export: true,
  results: [row(9, "Ñandú <Sur>", "-", "0"), row(8, "Álamo", "30111222333", "12"), row(7, "Beta", "20111222333", "3")],
  empty: null,
  page: { is_paginated: true, number: 2, previous: 1, next: 3, range: [1, 2, 3, "…"], query_prefix: "busqueda=a&filters=%7B%7D&" },
  messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path = LISTADO) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const bodyRows = () => within(document.getElementById("organizaciones-tbody")!).getAllByRole("row");
const names = () => bodyRows().map((r) => within(r).getAllByRole("cell")[1].textContent);

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Organizaciones list route", () => {
  it("owns only the native list path without trailing slash", () => {
    expect(findRoute(LISTADO)?.route.name).toBe("comedores-organizaciones");
    for (const other of ["/organizaciones/listar/", "/organizaciones/", "/organizaciones/exportar", "/organizaciones/ajax/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-organizaciones");
    }
  });

  it("renders the native frame, rows, actions and pagination from the API", async () => {
    serve(list());
    setup(`${LISTADO}?busqueda=a&page=2`);
    await screen.findByText("Álamo");
    expect(webGet).toHaveBeenCalledWith(`${API}?busqueda=a&page=2`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Organizaciones"));
    expect(screen.getByRole("heading", { level: 2, name: "Buscar Organización" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Organizaciones" }).getAttribute("href")).toBe(LISTADO);
    const header = within(document.querySelector("thead")!).getAllByRole("columnheader");
    expect(header.map((c) => c.textContent?.trim())).toEqual(HEADERS);
    const tds = within(bodyRows()[1]).getAllByRole("cell");
    expect(tds.map((c) => c.textContent)).toEqual(["30111222333", "Álamo", "12", "-", "-", "-", "-", " Ver Editar Eliminar"]);
    expect(tds[0].getAttribute("data-cuit")).toBe("30111222333");
    expect(within(bodyRows()[0]).getAllByRole("cell")[0].getAttribute("data-cuit")).toBe("");
    const nombre = within(tds[1]).getByRole("link", { name: "Álamo" });
    expect([nombre.getAttribute("href"), nombre.className, nombre.title]).toEqual(["/organizaciones/detalle/8", "font-weight-bold link-handler", "Ver detalles"]);
    const eliminar = within(tds[7]).getByRole("link", { name: "Eliminar" });
    expect([eliminar.getAttribute("href"), eliminar.className]).toEqual(["/organizaciones/eliminar/8", "btn btn-eliminar link-handler"]);
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("href")).toBe(LISTADO);
    expect(screen.getByRole("link", { name: "Agregar" }).getAttribute("href")).toBe("/organizaciones/crear");
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?busqueda=a&filters=%7B%7D&page=3");
    expect(within(document.getElementById("pagination-container")!).getByRole("link", { name: "Volver" }).getAttribute("href")).toBe("?busqueda=a&filters=%7B%7D&page=1");
    expect(document.querySelector("#pagination-container .page-item.active")?.textContent).toBe("2");
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("hides the role buttons and shows the native empty row", async () => {
    serve(list({ can_add: false, can_export: false, results: [], empty: "No hay organizaciones disponibles.",
      page: { is_paginated: false, number: 1, previous: null, next: null, range: [], query_prefix: "" } }));
    setup();
    const empty = await screen.findByText("No hay organizaciones disponibles.");
    expect(empty.getAttribute("colspan")).toBe("8");
    expect(screen.queryByRole("link", { name: "Agregar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Exportar búsqueda" })).toBeNull();
    expect(document.querySelector(".poncho-topbar")).not.toBeNull();
    expect(document.querySelector(".pagination")).toBeNull();
  });

  it("sorts the visible page like listSort.js and exports with that sort", async () => {
    const assign = vi.spyOn(organizacionesNavigation, "assign").mockImplementation(() => undefined);
    serve(list());
    setup(`${LISTADO}?busqueda=a&page=2`);
    await screen.findByText("Álamo");
    const th = document.querySelector<HTMLElement>('th[data-column="nombre"]')!;
    fireEvent.click(th);
    await waitFor(() => expect(names()).toEqual(["Álamo", "Beta", "Ñandú <Sur>"]));
    expect(th.className).toBe("sortable sort-asc");
    fireEvent.click(th);
    await waitFor(() => expect(names()).toEqual(["Ñandú <Sur>", "Beta", "Álamo"]));
    fireEvent.click(document.querySelector<HTMLElement>('th[data-column="comedores"]')!);
    await waitFor(() => expect(names()).toEqual(["Ñandú <Sur>", "Beta", "Álamo"]));
    // CUIT: the data value "" of the first row is not a number, so the strings compare.
    fireEvent.click(document.querySelector<HTMLElement>('th[data-column="cuit"]')!);
    await waitFor(() => expect(names()).toEqual(["Ñandú <Sur>", "Beta", "Álamo"]));
    fireEvent.click(screen.getByRole("button", { name: "Exportar búsqueda" }));
    expect(assign).toHaveBeenCalledWith("/organizaciones/exportar?busqueda=a&page=2&sort=cuit&direction=asc");
  });

  it("serializes the filters as the native GET", async () => {
    serve(list());
    setup(`${LISTADO}?filters=${encodeURIComponent(JSON.stringify({ logic: "AND", items: [{ field: "sin_vencimiento", op: "eq", value: "true" }] }))}`);
    await screen.findByText("Álamo");
    const form = document.getElementById("filters-form") as HTMLFormElement;
    expect(form.getAttribute("method")).toBe("GET");
    expect(form.querySelector<HTMLSelectElement>("[data-rol=valor-select]")!.value).toBe("true");
    fireEvent.change(form.querySelector("[data-rol=campo]")!, { target: { value: "nombre" } });
    fireEvent.change(form.querySelector("[data-rol=valor]")!, { target: { value: "  Sur " } });
    fireEvent.submit(form);
    expect(JSON.parse((document.getElementById("filters-input") as HTMLInputElement).value)).toEqual({
      logic: "AND", items: [{ field: "nombre", op: "contains", value: "Sur" }],
    });
  });

  it("shows the access screen on 403 and an error on an invalid payload", async () => {
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    setup();
    await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
    expect(screen.queryByRole("table")).toBeNull();
    cleanup();
    serve({ ...list(), results: [{ id: 1, cells: [{ text: 1 }], detail_url: "/x", actions: [] }] });
    setup();
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(listValid(list())).toBe(true);
    expect(listValid(list({ urls: { ...list().urls, export: "https://evil.example/" } }))).toBe(false);
  });
});
