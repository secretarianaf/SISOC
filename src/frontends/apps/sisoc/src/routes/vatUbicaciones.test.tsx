import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { ubicacionDetailValid, ubicacionListValid } from "./vatUbicaciones";
import { ubicacionDeleteValid, ubicacionFormValid, vatGeography } from "./vatUbicacionesForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/institucion/ubicaciones/";
const L = "/vat/institucion/ubicaciones/";
const page = { is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "" };
const row = (over: Record<string, unknown> = {}) => ({
  id: 5, centro: "CFP 401", localidad: "Tolosa", rol: "Sede Principal", domicilio: "Calle 12", es_principal: true,
  detail_url: `${L}5/`, update_url: `${L}5/editar/`, delete_url: `${L}5/eliminar/`, ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [row()], page, busqueda: "", permisos: { editar: false, eliminar: false }, urls: { list: L, create: `${L}nuevo/` }, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 5, title: "CFP 401 - Sede Principal (Tolosa)", centro: "CFP 401", rol: "Sede Principal", localidad: "Tolosa", domicilio: "Calle 12",
  es_principal: false, vigencia_hasta: "Vigente", latitud: "-34,921000", longitud: "—", observaciones: "",
  creado: "01/05/2026 10:00", modificado: "02/05/2026 11:00", urls: { list: L, update: `${L}5/editar/`, delete: `${L}5/eliminar/` }, messages: [], ...over,
});
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text" }, value: "", choices: [], errors: [], ...over,
});
const select2 = { class: "form-control select2", "data-width": "100%" };
const form = (over: Record<string, unknown> = {}, domicilio: Record<string, unknown> = {}, centro: Record<string, unknown> = {}) => ({
  editing: false, non_field_errors: [], urls: { list: L, municipios: "/vat/ajax/municipios-por-centro/", localidades: "/ajax/load-localidades/" }, ...over,
  fields: [
    field("centro", { id: "id_centro_ubicacion", label: "Centro", tag: "select", attrs: select2, value: "3", choices: [{ value: "", label: "---------" }, { value: "3", label: "CFP 401" }], ...centro }),
    field("departamento", { id: "id_departamento_ubicacion", label: "Departamento", tag: "select", attrs: { ...select2, "data-placeholder": "Todos los departamentos..." }, value: "7", choices: [{ value: "", label: "---------" }, { value: "7", label: "La Plata" }] }),
    field("localidad", { id: "id_localidad_ubicacion", label: "Localidad", tag: "select", attrs: select2, value: "", choices: [{ value: "", label: "" }] }),
    field("rol_ubicacion", { label: "Rol de la ubicación", tag: "select", attrs: { class: "form-control" }, value: "sede_principal", choices: [{ value: "sede_principal", label: "Sede Principal" }, { value: "anexo", label: "Anexo" }] }),
    field("domicilio", { label: "Domicilio", ...domicilio }),
    field("es_principal", { label: "Es principal", attrs: { class: "form-check-input", type: "checkbox" }, value: false }),
    field("observaciones", { label: "Observaciones", tag: "textarea", attrs: { class: "form-control", rows: "3", cols: "40" } }),
  ],
});

function serve(data: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT ubicaciones routes", () => {
  it("own their list, detail and form paths only", () => {
    for (const path of [L, `${L}12/`]) expect(findRoute(path)?.route.name).toBe("vat-ubicaciones");
    for (const path of [`${L}nuevo/`, `${L}4/editar/`, `${L}4/eliminar/`]) expect(findRoute(path)?.route.name).toBe("vat-ubicaciones-form");
    for (const other of ["/vat/institucion/ubicaciones", `${L}nueva/`, `${L}x/editar/`]) {
      expect(["vat-ubicaciones", "vat-ubicaciones-form"]).not.toContain(findRoute(other)?.route.name);
    }
  });

  it("renders the list keeping the filters and only the allowed buttons", async () => {
    serve(list({ results: [row(), row({ id: 6, es_principal: false })], permisos: { editar: true, eliminar: false } }));
    setup(`${L}?rol_ubicacion=anexo`);
    expect(await screen.findByRole("heading", { level: 2, name: "Buscar Ubicación" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}?rol_ubicacion=anexo`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Ubicaciones de Institución"));
    expect(screen.getAllByRole("link", { name: /Editar/ })).toHaveLength(2);
    expect(screen.queryByRole("link", { name: /Eliminar/ })).toBeNull();
    expect(document.querySelector(".badge-validacion.pendiente")?.textContent).toBe("No");
  });

  it("shows the empty state", async () => {
    serve(list({ results: [], page: { ...page, count: 0 } }));
    setup(L);
    expect(await screen.findByText("No se encontraron ubicaciones")).toBeTruthy();
  });

  it("renders the detail with its optional block and links to the delete confirmation", async () => {
    serve(detail({ observaciones: "Frente a la plaza" }));
    setup(`${L}5/`);
    expect(await screen.findByText("Frente a la plaza")).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - CFP 401 - Sede Principal (Tolosa)"));
    expect(screen.getByText("-34,921000")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Eliminar/ }).getAttribute("href")).toBe(`${L}5/eliminar/`);
    expect(screen.getByText("#5")).toBeTruthy();
  });

  it("loads the localidades of the initial departamento, posts the rendered fields and shows errors after a rejection", async () => {
    serve(form());
    const load = vi.spyOn(vatGeography, "load").mockResolvedValue([{ id: 11, nombre: "Tolosa" }, { id: 12, nombre: "Gonnet" }]);
    webPost.mockRejectedValueOnce({ response: { status: 400, data: form({}, { errors: ["Dato inválido."] }) } });
    webPost.mockResolvedValueOnce({ status: 200, data: { ok: true, redirect: L } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup(`${L}nuevo/?centro=3`);
    await screen.findByRole("heading", { level: 1, name: "Nueva Ubicación" });
    expect(webGet).toHaveBeenCalledWith(`${API}nuevo/?centro=3`, expect.anything());
    await waitFor(() => expect(load).toHaveBeenCalledWith("/ajax/load-localidades/?municipio_id=7"));
    fireEvent.click(screen.getByRole("button", { name: /Crear/ }));
    expect(await screen.findByText("Dato inválido.")).toBeTruthy();
    fireEvent.click(screen.getByLabelText("Es principal"));
    fireEvent.click(screen.getByRole("button", { name: /Crear/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(L));
    expect(webPost.mock.calls[1][0]).toBe(`${API}nuevo/?centro=3`);
    expect(Object.fromEntries(webPost.mock.calls[1][1] as URLSearchParams)).toEqual({
      centro: "3", departamento: "7", localidad: "", rol_ubicacion: "sede_principal", domicilio: "", es_principal: "on", observaciones: "",
    });
  });

  it("chooses the only departamento of a new centro and reloads the localidades", async () => {
    serve(form({}, {}, { value: "" }));
    const load = vi.spyOn(vatGeography, "load").mockImplementation((url: string) => Promise.resolve(
      url.startsWith("/vat/ajax/municipios-por-centro/") ? { municipios: [{ id: 9, nombre: "Berisso" }] } : [{ id: 21, nombre: "Los Talas" }]));
    setup(`${L}nuevo/`);
    await screen.findByRole("heading", { level: 1, name: "Nueva Ubicación" });
    expect(load).not.toHaveBeenCalled();
    fireEvent.mouseDown(document.querySelector("#id_centro_ubicacion + .select2-container .select2-selection")!);
    fireEvent.click(screen.getByRole("option", { name: "CFP 401" }));
    await waitFor(() => expect(load).toHaveBeenCalledWith("/vat/ajax/municipios-por-centro/?centro_id=3"));
    await waitFor(() => expect(load).toHaveBeenCalledWith("/ajax/load-localidades/?municipio_id=9"));
  });

  it("renders the delete confirmation and removes through the API", async () => {
    serve({ rol: "Sede Principal", localidad: "Tolosa", centro: "CFP 401", urls: { detail: `${L}5/` } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: L } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup(`${L}5/eliminar/`);
    expect(await screen.findByText("Sede Principal")).toBeTruthy();
    expect(screen.getByText("Tolosa • CFP 401")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Cancelar/ }).getAttribute("href")).toBe(`${L}5/`);
    fireEvent.click(screen.getByRole("button", { name: /Sí, eliminar definitivamente/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(L));
    expect(webPost).toHaveBeenCalledWith(`${API}5/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("validates the payload shapes", () => {
    expect(ubicacionListValid(list())).toBe(true);
    expect(ubicacionListValid(list({ results: [row({ es_principal: "si" })] }))).toBe(false);
    expect(ubicacionDetailValid(detail())).toBe(true);
    expect(ubicacionDetailValid({ ...detail(), urls: {} })).toBe(false);
    expect(ubicacionFormValid(form())).toBe(true);
    expect(ubicacionFormValid({ ...form(), fields: [] })).toBe(false);
    expect(ubicacionFormValid({ ...form(), urls: { list: L } })).toBe(false);
    expect(ubicacionDeleteValid({ rol: "a", localidad: "b", centro: "c", urls: { detail: "/x/" } })).toBe(true);
    expect(ubicacionDeleteValid({ rol: "a" })).toBe(false);
  });
});
