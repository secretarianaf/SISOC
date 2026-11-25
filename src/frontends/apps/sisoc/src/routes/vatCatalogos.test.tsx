import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { catalogoDetailValid, catalogoListValid } from "./vatCatalogos";
import { catalogoDeleteValid, catalogoFormValid } from "./vatCatalogosForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/catalogos/";
const page = { is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "" };
const urls = (slug: string) => ({ list: `/vat/catalogos/${slug}/`, create: `/vat/catalogos/${slug}/nuevo/` });
const rowUrls = (slug: string) => ({ detail_url: `/vat/catalogos/${slug}/5/`, update_url: `/vat/catalogos/${slug}/5/editar/`, delete_url: `/vat/catalogos/${slug}/5/eliminar/` });
const list = (slug: string, results: Record<string, unknown>[], over: Record<string, unknown> = {}) => ({
  results: results.map((r) => ({ id: 5, ...rowUrls(slug), ...r })), page, busqueda: "", permisos: { editar: true, eliminar: false }, urls: urls(slug), messages: [], ...over,
});
const detailUrls = (slug: string) => ({ vat: "/vat/centros/", list: `/vat/catalogos/${slug}/`, update: `/vat/catalogos/${slug}/5/editar/`, delete: `/vat/catalogos/${slug}/5/eliminar/` });
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text" }, value: "", choices: [], errors: [], ...over,
});
const form = (slug: string, fields: Record<string, unknown>[], over: Record<string, unknown> = {}) => ({
  editing: false, fields, non_field_errors: [], urls: { list: `/vat/catalogos/${slug}/`, vat: "/vat/centros/" }, messages: [], ...over,
});
const sectorFields = () => [field("nombre", { label: "Nombre del Sector", attrs: { class: "form-control", type: "text", required: "required" } }),
  field("descripcion", { label: "Descripción", tag: "textarea", attrs: { class: "form-control", rows: "4" } })];
const modalidadFields = () => [field("nombre", { label: "Nombre de la Modalidad" }), field("descripcion", { label: "Descripción", tag: "textarea", attrs: { class: "form-control", rows: "4" } }),
  field("activo", { label: "Activo", attrs: { class: "form-check-input", type: "checkbox" }, value: true })];

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

describe("VAT catalogos routes", () => {
  it("own their list, detail and form paths only", () => {
    for (const slug of ["sectores", "subsectores", "modalidades-cursado", "titulos-referencia"]) {
      for (const path of [`/vat/catalogos/${slug}/`, `/vat/catalogos/${slug}/12/`]) expect(findRoute(path)?.route.name).toBe("vat-catalogos");
      for (const path of [`/vat/catalogos/${slug}/4/editar/`, `/vat/catalogos/${slug}/4/eliminar/`]) expect(findRoute(path)?.route.name).toBe("vat-catalogos-form");
    }
    expect(findRoute("/vat/catalogos/sectores/nuevo/")?.route.name).toBe("vat-catalogos-form");
    expect(findRoute("/vat/catalogos/modalidades-cursado/nueva/")?.route.name).toBe("vat-catalogos-form");
    for (const other of ["/vat/catalogos/sectores", "/vat/catalogos/sectores/nueva/", "/vat/catalogos/modalidades-cursado/nuevo/", "/vat/catalogos/planes/", "/vat/catalogos/ajax/subsectores/"]) {
      expect(["vat-catalogos", "vat-catalogos-form"]).not.toContain(findRoute(other)?.route.name);
    }
  });

  it("renders the sector list with the search bar, the buttons by permission and no tour", async () => {
    serve(list("sectores", [{ nombre: "Industria", descripcion: "—", subsectores: 2 }], { busqueda: "ind" }));
    setup("/vat/catalogos/sectores/?busqueda=ind");
    expect(await screen.findByText("Industria")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}sectores/?busqueda=ind`, expect.anything());
    expect(screen.getByRole("heading", { name: "Buscar Sector" })).toBeTruthy();
    expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe("ind");
    expect(screen.getByRole("link", { name: /Editar/ }).getAttribute("title")).toBe("Editar sector");
    expect(screen.queryByRole("link", { name: /Eliminar/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Tour de ayuda/ })).toBeNull();
    await waitFor(() => expect(document.title).toBe("SISOC - Sectores"));
    // A validator rebuilt on every render would refetch forever (`useMainResource` depends on it).
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(webGet.mock.calls.filter(([url]) => String(url).startsWith(API))).toHaveLength(1);
  });

  it("renders the subsector, title and empty lists", async () => {
    serve(list("subsectores", [{ sector: "Industria", nombre: "Metalurgia", descripcion: "None" }]));
    setup("/vat/catalogos/subsectores/");
    expect(await screen.findByText("Metalurgia")).toBeTruthy();
    expect(screen.getByText("Industria")).toBeTruthy();
    cleanup();
    serve(list("titulos-referencia", [{ nombre: "Electricista", plan_estudio: "—", codigo: "E-1", activo: false }]));
    setup("/vat/catalogos/titulos-referencia/");
    expect(await screen.findByText("Electricista")).toBeTruthy();
    expect(screen.getByText("Inactivo").className).toBe("badge-validacion no-validado");
    cleanup();
    serve(list("titulos-referencia", [], { page: { ...page, count: 0 } }));
    setup("/vat/catalogos/titulos-referencia/");
    expect(await screen.findByText("No se encontraron títulos de referencia")).toBeTruthy();
    expect(screen.getByText("No hay títulos registrados.")).toBeTruthy();
  });

  it("renders the modalidad list in filters mode", async () => {
    serve(list("modalidades-cursado", [{ nombre: "Presencial", descripcion: "—", activo: true }], {
      filters_config: { fields: [{ name: "nombre", label: "Nombre", type: "text" }], defaultField: "nombre" },
      favorites: { section: "", url: "/ajax/filtros-favoritos/", detail_url_template: "/ajax/filtros-favoritos/0/" },
    }));
    setup("/vat/catalogos/modalidades-cursado/");
    expect(await screen.findByText("Presencial")).toBeTruthy();
    expect(screen.getByText("Activo").className).toBe("badge-validacion validado");
    expect(screen.getByRole("heading", { name: "Buscar Modalidad de Cursado" })).toBeTruthy();
    expect(document.querySelector("#filters-form")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("data-restablecer-filtros-favoritos")).toBe("true");
    expect(screen.getByRole("link", { name: /Agregar/ }).getAttribute("href")).toBe("/vat/catalogos/modalidades-cursado/nuevo/");
  });

  it("renders every detail and deletes the sector through the confirming POST form", async () => {
    serve({ id: 5, nombre: "Industria", descripcion: "Sin descripción", subsectores: ["Metalurgia"], urls: detailUrls("sectores"), messages: [] });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/catalogos/sectores/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    const confirm = vi.spyOn(vatNavigation, "confirm").mockReturnValueOnce(false).mockReturnValue(true);
    setup("/vat/catalogos/sectores/5/");
    expect(await screen.findByRole("heading", { name: "Industria" })).toBeTruthy();
    expect(screen.getByText("Subsectores (1)")).toBeTruthy();
    const borrar = document.querySelector("form button.btn-danger") as HTMLButtonElement;
    fireEvent.click(borrar);
    expect(confirm).toHaveBeenCalledWith("¿Está seguro?");
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.click(borrar);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/catalogos/sectores/"));
    expect(webPost).toHaveBeenCalledWith(`${API}sectores/5/eliminar/`, expect.any(URLSearchParams), expect.anything());
    cleanup();
    serve({ id: 5, nombre: "Metalurgia", descripcion: "Sin descripción", sector: { nombre: "Industria", url: "/vat/catalogos/sectores/1/" }, urls: detailUrls("subsectores"), messages: [] });
    setup("/vat/catalogos/subsectores/5/");
    expect(await screen.findByRole("link", { name: "Industria" })).toBeTruthy();
    expect(document.querySelector("a.btn-danger")?.getAttribute("href")).toBe("/vat/catalogos/subsectores/5/eliminar/");
    cleanup();
    serve({ id: 5, nombre: "Presencial", descripcion: "Sin descripción", activo: false, urls: detailUrls("modalidades-cursado"), messages: [] });
    setup("/vat/catalogos/modalidades-cursado/5/");
    expect(await screen.findByText("No", { exact: false })).toBeTruthy();
    cleanup();
    serve({ id: 5, nombre: "Electricista", plan_estudio: "-", codigo: "E-1", activo: true, planes: ["Industria / Metalurgia - Presencial"], urls: detailUrls("titulos-referencia"), messages: [] });
    setup("/vat/catalogos/titulos-referencia/5/");
    expect(await screen.findByText("Industria / Metalurgia - Presencial")).toBeTruthy();
    expect(screen.getByText("Activo").className).toBe("badge badge-success");
  });

  it("posts the form fields, shows the errors list after a rejection and keeps the sector form on a plain post", async () => {
    serve(form("sectores", sectorFields()));
    webPost.mockRejectedValueOnce({ response: { status: 400, data: form("sectores", [{ ...sectorFields()[0], value: "Servicios", errors: ["Este campo es obligatorio."] }, sectorFields()[1]]) } })
      .mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/catalogos/sectores/7/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/catalogos/sectores/nuevo/");
    expect(await screen.findByRole("heading", { name: "Nuevo Sector" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    // The native form keeps the browser validation: the empty required field never reaches the server.
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.change(document.querySelector("input[name=nombre]") as HTMLInputElement, { target: { value: "Servicios" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    const error = await screen.findByText("Este campo es obligatorio.");
    expect(error.closest("ul")?.className).toBe("errorlist");
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/catalogos/sectores/7/"));
    expect(webPost.mock.calls[1][0]).toBe(`${API}sectores/nuevo/`);
    expect(Object.fromEntries(webPost.mock.calls[1][1] as URLSearchParams)).toEqual({ nombre: "Servicios", descripcion: "" });
  });

  it("renders the modalidad form with the title, switch and cancel of the native view and reports an unconfirmed result", async () => {
    serve(form("modalidades-cursado", modalidadFields(), {
      editing: true, page: { page_title: "Editar Modalidad de Cursado", page_description: "Actualizá la definición.", submit_text: "Guardar cambios" },
      urls: { list: "/vat/catalogos/modalidades-cursado/", vat: "/vat/centros/", cancel: "/vat/catalogos/modalidades-cursado/5/" },
    }));
    webPost.mockRejectedValue(new Error("network"));
    setup("/vat/catalogos/modalidades-cursado/5/editar/");
    expect(await screen.findByRole("heading", { level: 1, name: "Editar Modalidad de Cursado" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Cancelar/ }).getAttribute("href")).toBe("/vat/catalogos/modalidades-cursado/5/");
    fireEvent.click(screen.getByRole("button", { name: /Guardar cambios/ }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Guardar cambios/ }));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams)).toEqual({ nombre: "", descripcion: "", activo: "on" });
  });

  it("renders the delete confirmation of the subsector and removes through the API", async () => {
    serve({ nombre: "Metalurgia", sector: "Industria", urls: { detail: "/vat/catalogos/subsectores/5/" } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/catalogos/subsectores/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/catalogos/subsectores/5/eliminar/");
    expect(await screen.findByText("Metalurgia")).toBeTruthy();
    expect(screen.getByText(/\(Industria\)/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/vat/catalogos/subsectores/5/");
    fireEvent.click(screen.getByRole("button", { name: /Eliminar/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/catalogos/subsectores/"));
    expect(webPost).toHaveBeenCalledWith(`${API}subsectores/5/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("validates the payload shapes", () => {
    expect(catalogoListValid("sectores")(list("sectores", [{ nombre: "a", descripcion: "b", subsectores: 1 }]))).toBe(true);
    expect(catalogoListValid("sectores")(list("sectores", [{ nombre: "a" }]))).toBe(false);
    expect(catalogoListValid("modalidades-cursado")(list("modalidades-cursado", [{ nombre: "a", descripcion: "b", activo: true }]))).toBe(false);
    expect(catalogoDetailValid("sectores")({ id: 1, nombre: "a", descripcion: "b", subsectores: [], urls: detailUrls("sectores"), messages: [] })).toBe(true);
    expect(catalogoDetailValid("titulos-referencia")({ id: 1, nombre: "a", urls: detailUrls("sectores"), messages: [] })).toBe(false);
    expect(catalogoFormValid("sectores")(form("sectores", sectorFields()))).toBe(true);
    expect(catalogoFormValid("subsectores")(form("sectores", sectorFields()))).toBe(false);
    expect(catalogoDeleteValid({ nombre: "a", sector: "", urls: { detail: "/x/" } })).toBe(true);
    expect(catalogoDeleteValid({})).toBe(false);
  });
});
