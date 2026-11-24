import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { modalidadDetailValid, modalidadListValid } from "./vatModalidadInstitucional";
import { modalidadDeleteValid, modalidadFormValid } from "./vatModalidadInstitucionalForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/modalidades-institucionales/";
const L = "/vat/modalidades-institucionales/";
const page = { is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "" };
const row = (over: Record<string, unknown> = {}) => ({
  id: 5, nombre: "Presencial", descripcion: "Con clases", activo: true, creado: "01/05/2026",
  detail_url: `${L}5/`, update_url: `${L}5/editar/`, delete_url: `${L}5/eliminar/`, ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [row()], page, busqueda: "", permisos: { editar: false, eliminar: false }, urls: { list: L, create: `${L}nueva/` }, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 5, nombre: "Presencial", descripcion: "", activo: false, creado: "01/05/2026 10:00", modificado: "02/05/2026 11:00",
  urls: { list: L, update: `${L}5/editar/`, delete: `${L}5/eliminar/` }, messages: [], ...over,
});
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text" }, value: "", choices: [], errors: [], ...over,
});
const form = (over: Record<string, unknown> = {}, nombre: Record<string, unknown> = {}) => ({
  editing: false, non_field_errors: [], urls: { list: L }, ...over,
  fields: [field("nombre", { label: "Nombre de la Modalidad", ...nombre }), field("descripcion", { label: "Descripción", tag: "textarea" }),
    field("activo", { label: "Activo", attrs: { class: "form-check-input", type: "checkbox" }, value: true })],
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

describe("VAT modalidad institucional routes", () => {
  it("own their list, detail and form paths only", () => {
    for (const path of [L, `${L}12/`]) expect(findRoute(path)?.route.name).toBe("vat-modalidad-institucional");
    for (const path of [`${L}nueva/`, `${L}4/editar/`, `${L}4/eliminar/`]) expect(findRoute(path)?.route.name).toBe("vat-modalidad-institucional-form");
    for (const other of ["/vat/modalidades-institucionales", `${L}nuevo/`, `${L}x/editar/`]) {
      expect(["vat-modalidad-institucional", "vat-modalidad-institucional-form"]).not.toContain(findRoute(other)?.route.name);
    }
  });

  it("renders the list with its two states and only the allowed buttons", async () => {
    serve(list({ results: [row(), row({ id: 6, activo: false })], permisos: { editar: false, eliminar: true } }));
    setup(`${L}?activo=true`);
    expect(await screen.findByRole("heading", { level: 2, name: "Buscar Modalidad Institucional" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}?activo=true`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Modalidades Institucionales"));
    expect(screen.getAllByRole("link", { name: /Eliminar/ })).toHaveLength(2);
    expect(screen.queryByRole("link", { name: /Editar/ })).toBeNull();
    expect(document.querySelector(".badge-validacion.no-validado")?.textContent).toContain("Inactivo");
  });

  it("shows the empty state", async () => {
    serve(list({ results: [], page: { ...page, count: 0 } }));
    setup(L);
    expect(await screen.findByText("No se encontraron modalidades institucionales")).toBeTruthy();
  });

  it("renders the detail and deletes only after the native confirm", async () => {
    serve(detail());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: L } });
    const confirm = vi.spyOn(vatNavigation, "confirm").mockReturnValueOnce(false).mockReturnValue(true);
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup(`${L}5/`);
    expect(await screen.findByText("Sin descripción")).toBeTruthy();
    expect(screen.getByText("Inactivo")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Eliminar/ }));
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Eliminar/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(L));
    expect(confirm).toHaveBeenCalledWith("¿Está seguro de que desea eliminar esta modalidad?");
    expect(webPost).toHaveBeenCalledWith(`${API}5/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("posts the whitelisted fields of the create form and shows errors after a rejection", async () => {
    serve(form());
    webPost.mockRejectedValueOnce({ response: { status: 400, data: form({}, { errors: ["Este campo es requerido."] }) } });
    webPost.mockResolvedValueOnce({ status: 200, data: { ok: true, redirect: `${L}9/` } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup(`${L}nueva/`);
    await screen.findByText("Nueva Modalidad Institucional", { selector: "h3" });
    await waitFor(() => expect(document.title).toBe("SISOC - VAT - Nueva Modalidad Institucional"));
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(await screen.findByText("Este campo es requerido.")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Nombre de la Modalidad"), { target: { value: "Virtual" } });
    fireEvent.click(screen.getByLabelText("Activo"));
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(`${L}9/`));
    expect(Object.fromEntries(webPost.mock.calls[1][1] as URLSearchParams)).toEqual({ nombre: "Virtual", descripcion: "" });
  });

  it("renders the delete confirmation and removes through the API", async () => {
    serve({ nombre: "Presencial", urls: { detail: `${L}5/` } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: L } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup(`${L}5/eliminar/`);
    expect(await screen.findByText("Presencial")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Cancelar/ }).getAttribute("href")).toBe(`${L}5/`);
    fireEvent.click(screen.getByRole("button", { name: /Eliminar/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(L));
  });

  it("validates the payload shapes", () => {
    expect(modalidadListValid(list())).toBe(true);
    expect(modalidadListValid(list({ results: [row({ activo: "si" })] }))).toBe(false);
    expect(modalidadDetailValid(detail())).toBe(true);
    expect(modalidadDetailValid({ ...detail(), urls: {} })).toBe(false);
    expect(modalidadFormValid(form())).toBe(true);
    expect(modalidadFormValid({ ...form(), fields: [] })).toBe(false);
    expect(modalidadDeleteValid({ nombre: "a", urls: { detail: "/x/" } })).toBe(true);
    expect(modalidadDeleteValid({ nombre: "a" })).toBe(false);
  });
});
