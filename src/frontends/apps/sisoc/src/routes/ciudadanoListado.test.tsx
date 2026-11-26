import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { ciudadanoListadoNavigation, listadoValid } from "./ciudadanoListado";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const celdas = (apellido: string, documento: string) => [
  { text: apellido, sort: apellido }, { text: "Nora", sort: "Nora" },
  documento ? { text: documento, sort: documento } : { text: "-", sort: "" }, { text: "-", sort: "" }, { text: "Chaco", sort: "Chaco" },
];
const fila = (id: number, apellido: string, documento = "30111222", over = {}) => ({
  id, cells: celdas(apellido, documento), tipo_registro: "ESTANDAR", requiere_revision: false, ver_url: `/ciudadanos/ver/${id}`, ...over,
});
const opciones = (...pares: [string, string][]) => pares.map(([value, label]) => ({ value, label }));
const listado = (over: Record<string, unknown> = {}) => ({
  filters_config: { fields: [{ name: "apellido", label: "Apellido", type: "text" }], defaultField: "apellido" },
  favorites: { section: "", url: "/filtros-favoritos/", detail_url_template: "/filtros-favoritos/0/" },
  filtros: {
    q: "", filters: "",
    tipo_registro: { label: "Estado identidad:", value: "", options: opciones(["", "Todos"], ["ESTANDAR", "Estándar"], ["SIN_DNI", "Sin DNI"], ["DNI_NO_VALIDADO_RENAPER", "DNI no validado RENAPER"]) },
    estado_revision: { label: "Estado de Revisión:", value: "FINALIZADA", options: opciones(["FINALIZADA", "Finalizada"], ["PENDIENTE", "Pendiente"], ["TODOS", "Todos"]) },
  },
  results: [fila(2, "Zeta"), fila(1, "Álamo", "", { tipo_registro: "SIN_DNI", requiere_revision: true })],
  page: { is_paginated: false, number: 1, previous: null, next: null, range: [1], query_prefix: "" },
  can_export: false, additional_buttons: [],
  urls: { list: "/ciudadanos/listar", add: "/ciudadanos/crear/", export: "/ciudadanos/exportar" },
  messages: [], ...over,
});
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
const apellidos = () => within(screen.getByRole("table")).getAllByRole("row").slice(1).map((r) => r.querySelector("td")?.textContent);

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.history.replaceState({}, "", "/ciudadanos/listar");
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("listado de ciudadanos", () => {
  it("owns only /ciudadanos/listar and validates the payload", () => {
    expect(findRoute("/ciudadanos/listar")?.route.name).toBe("ciudadano-listado");
    expect(findRoute("/ciudadanos/listar/")?.route.name).not.toBe("ciudadano-listado");
    expect(listadoValid(listado())).toBe(true);
    expect(listadoValid(listado({ urls: { list: "http://evil/", add: "/a", export: "/e" } }))).toBe(false);
    expect(listadoValid(listado({ results: [{ ...fila(1, "A"), cells: [] }] }))).toBe(false);
    expect(listadoValid(listado({ additional_buttons: [{ label: "x", url: "//evil", class: "", title: "" }] }))).toBe(false);
  });

  it("draws the search bar, the identity form, the headers and the rows", async () => {
    serve(listado());
    render(<App />);
    expect(await screen.findByText("Buscar ciudadano")).toBeTruthy();
    expect(screen.getByText("Listado de ciudadanos")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("href")).toBe("/ciudadanos/listar");
    expect(screen.getByRole("link", { name: /Nuevo ciudadano/ }).getAttribute("href")).toBe("/ciudadanos/crear/");
    expect(screen.queryByRole("button", { name: /Exportar búsqueda/ })).toBeNull();
    expect((screen.getByLabelText("Estado identidad:") as HTMLSelectElement).value).toBe("");
    expect((screen.getByLabelText("Estado de Revisión:") as HTMLSelectElement).value).toBe("FINALIZADA");
    expect(screen.getByRole("button", { name: "Aplicar" })).toBeTruthy();
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent?.trim())).toEqual(
      ["Apellido", "Nombre", "Documento", "Sexo", "Provincia", "Estado identidad", "Acciones"]);
    expect(apellidos()).toEqual(["Zeta", "Álamo"]);
    expect(screen.getByText("Sin DNI", { selector: "span" })).toBeTruthy();
    expect(screen.getByText("Revisión")).toBeTruthy();
    expect(screen.getByText("Estándar", { selector: "span" })).toBeTruthy();
    expect(screen.getAllByRole("link", { name: /^Ver$/ }).map((a) => a.getAttribute("href"))).toEqual(["/ciudadanos/ver/2", "/ciudadanos/ver/1"]);
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
    expect(webGet).toHaveBeenCalledWith("web/ciudadanos/listar/", expect.anything());
  });

  it("keeps the query in the request and the hidden fields of the search bar", async () => {
    window.history.replaceState({}, "", "/ciudadanos/listar?q=Zeta&filters_mode=ui&estado_revision=TODOS");
    serve(listado({ filtros: { ...listado().filtros, q: "Zeta", filters: "{}" } }));
    const { container } = render(<App />);
    await screen.findByText("Buscar ciudadano");
    expect(webGet).toHaveBeenCalledWith("web/ciudadanos/listar/?q=Zeta&filters_mode=ui&estado_revision=TODOS", expect.anything());
    const hidden = [...container.querySelectorAll<HTMLInputElement>('input[form="filters-form"]')].map((i) => [i.name, i.value]);
    expect(hidden).toEqual([["q", "Zeta"], ["filters_mode", "ui"], ["tipo_registro", ""], ["estado_revision", "FINALIZADA"]]);
    expect(container.querySelector<HTMLInputElement>("#province-hidden-q")?.value).toBe("Zeta");
    expect(container.querySelector<HTMLInputElement>('#province-filter-form input[name="filters"]')?.value).toBe("{}");
  });

  it("hides and disables the review state unless the identity allows it", async () => {
    serve(listado());
    const { container } = render(<App />);
    const tipo = (await screen.findByLabelText("Estado identidad:")) as HTMLSelectElement;
    const grupo = container.querySelector("#estado-revision-group");
    const estado = screen.getByLabelText("Estado de Revisión:") as HTMLSelectElement;
    expect(grupo?.classList.contains("invisible")).toBe(false);
    fireEvent.change(tipo, { target: { value: "ESTANDAR" } });
    expect(grupo?.classList.contains("invisible")).toBe(true);
    expect(estado.disabled).toBe(true);
    fireEvent.change(tipo, { target: { value: "SIN_DNI" } });
    expect(grupo?.classList.contains("invisible")).toBe(false);
    expect(estado.disabled).toBe(false);
    expect(grupo?.getAttribute("data-enabled-values")).toBe(",SIN_DNI,DNI_NO_VALIDADO_RENAPER");
  });

  it("sorts locally like listSort.js and leaves the order when the sort is cleared", async () => {
    serve(listado());
    render(<App />);
    const apellido = (await screen.findByRole("columnheader", { name: /Apellido/ })) as HTMLElement;
    fireEvent.click(apellido);
    expect(apellidos()).toEqual(["Álamo", "Zeta"]);
    expect(apellido.className).toBe("sortable sort-asc");
    fireEvent.click(apellido);
    expect(apellidos()).toEqual(["Zeta", "Álamo"]);
    expect(apellido.className).toBe("sortable sort-desc");
    fireEvent.click(apellido);
    expect(apellidos()).toEqual(["Zeta", "Álamo"]);
    expect(apellido.className).toBe("sortable");
    // Documento: an empty data value sorts before a number, as the native comparison does.
    fireEvent.click(screen.getByRole("columnheader", { name: /Documento/ }));
    expect(apellidos()).toEqual(["Álamo", "Zeta"]);
  });

  it("downloads the CSV with the query and the active sort, as export_helper.js does", async () => {
    window.history.replaceState({}, "", "/ciudadanos/listar?q=Ana&page=2");
    serve(listado({ can_export: true }));
    const assign = vi.spyOn(ciudadanoListadoNavigation, "assign").mockImplementation(() => {});
    render(<App />);
    const boton = await screen.findByRole("button", { name: /Exportar búsqueda/ });
    expect(boton.getAttribute("data-url")).toBe("/ciudadanos/exportar");
    fireEvent.click(boton);
    expect(assign).toHaveBeenLastCalledWith("/ciudadanos/exportar?q=Ana&page=2");
    fireEvent.click(screen.getByRole("columnheader", { name: /Provincia/ }));
    fireEvent.click(boton);
    expect(assign).toHaveBeenLastCalledWith("/ciudadanos/exportar?q=Ana&page=2&sort=provincia&direction=asc");
  });

  it("allows navigation on the mass import link exposed by the API", async () => {
    serve(listado({ additional_buttons: [{ label: "IMPORTACION MASIVA", url: "/ciudadanos/importacion-masiva/", class: "btn btn-lg btn-import-xlsx", title: "Importar ciudadanos desde Excel" }] }));
    render(<App />);
    const enlace = await screen.findByRole("link", { name: "IMPORTACION MASIVA" });
    expect(enlace.getAttribute("href")).toBe("/ciudadanos/importacion-masiva/");
    expect(enlace.getAttribute("title")).toBe("Importar ciudadanos desde Excel");
    expect(fireEvent.click(enlace)).toBe(true);
  });

  it("says so when there are no citizens and draws the pagination without a total", async () => {
    serve(listado({ results: [] }));
    render(<App />);
    expect(await screen.findByText("No se encontraron ciudadanos.")).toBeTruthy();
    cleanup();
    window.history.replaceState({}, "", "/ciudadanos/listar?q=Ana&busqueda=x&page=2");
    serve(listado({ page: { is_paginated: true, number: 2, previous: 1, next: 3, range: [1, 2, 3, "..."], query_prefix: "q=Ana&" } }));
    render(<App />);
    expect(await screen.findByRole("link", { name: "Continuar" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?q=Ana&page=3");
    expect(screen.getAllByRole("link", { name: "Volver" }).map((a) => a.getAttribute("href"))).toContain("?q=Ana&page=1");
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("shows the queued messages and the access screen on a 403", async () => {
    serve(listado({ messages: [{ message: "Ciudadano eliminado.", level: "success" }] }));
    render(<App />);
    await screen.findByText("Buscar ciudadano");
    await waitFor(() => expect(document.body.textContent).toContain("Ciudadano eliminado."));
    cleanup();
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "No tiene permiso" }, status: 403 }));
    render(<App />);
    await waitFor(() => expect(screen.queryByText("Buscar ciudadano")).toBeNull());
    expect(screen.queryByText("Listado de ciudadanos")).toBeNull();
  });
});
