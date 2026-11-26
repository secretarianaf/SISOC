import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { contactoDetailValid, contactoListValid } from "./vatContactos";
import { contactoDeleteValid, contactoFormValid } from "./vatContactosForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/institucion/contactos/";
const L = "/vat/institucion/contactos/";
const page = { is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "" };
const row = (over: Record<string, unknown> = {}) => ({
  id: 5, centro: "CFP 401", tipo: "Email", valor: "cfp@example.com", es_principal: true,
  detail_url: `${L}5/`, update_url: `${L}5/editar/`, delete_url: `${L}5/eliminar/`, ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [row()], page, busqueda: "", permisos: { editar: false, eliminar: false }, urls: { list: L, create: `${L}nuevo/` }, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 5, title: "CFP 401 - Email", centro: "CFP 401", centro_id: 3, tipo: "Email", valor: "cfp@example.com", es_principal: false,
  vigencia_hasta: "Vigente", observaciones: "", creado: "01/05/2026 10:00", modificado: "02/05/2026 11:00",
  urls: { list: L, update: `${L}5/editar/`, delete: `${L}5/eliminar/` }, messages: [], ...over,
});
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text" }, value: "", choices: [], errors: [], ...over,
});
const form = (over: Record<string, unknown> = {}, documento: Record<string, unknown> = {}) => ({
  editing: false, non_field_errors: [], urls: { list: L }, ...over,
  fields: [
    field("centro", { label: "Centro", tag: "select", attrs: { class: "form-control" }, value: "3", choices: [{ value: "3", label: "CFP 401" }] }),
    field("nombre_contacto", { label: "Nombre y apellido del responsable" }),
    field("rol_area", { label: "Rol / Área" }),
    field("documento", { label: "Documento", attrs: { class: "form-control", type: "text", oninput: "this.value=this.value.replace(/\\D/g, '')" }, ...documento }),
    field("telefono_contacto", { label: "Teléfono" }),
    field("email_contacto", { label: "Correo electrónico", attrs: { class: "form-control", type: "email" } }),
    field("es_principal", { label: "Es Principal", attrs: { class: "form-check-input", type: "checkbox" }, value: false }),
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

describe("VAT contactos routes", () => {
  it("own their list, detail and form paths only", () => {
    for (const path of [L, `${L}12/`]) expect(findRoute(path)?.route.name).toBe("vat-contactos");
    for (const path of [`${L}nuevo/`, `${L}4/editar/`, `${L}4/eliminar/`]) expect(findRoute(path)?.route.name).toBe("vat-contactos-form");
    for (const other of ["/vat/institucion/contactos", `${L}nueva/`, `${L}x/editar/`]) {
      expect(["vat-contactos", "vat-contactos-form"]).not.toContain(findRoute(other)?.route.name);
    }
  });

  it("renders the list keeping the filters and only the allowed buttons", async () => {
    serve(list({ results: [row(), row({ id: 6, es_principal: false })], permisos: { editar: false, eliminar: true } }));
    setup(`${L}?tipo=email`);
    expect(await screen.findByRole("heading", { level: 2, name: "Buscar Contacto" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}?tipo=email`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Contactos de Institución"));
    expect(screen.getAllByRole("link", { name: /Eliminar/ })).toHaveLength(2);
    expect(screen.queryByRole("link", { name: /Editar/ })).toBeNull();
    expect(document.querySelector(".badge-validacion.pendiente")?.textContent).toBe("No");
  });

  it("shows the empty state", async () => {
    serve(list({ results: [], page: { ...page, count: 0 } }));
    setup(L);
    expect(await screen.findByText("No se encontraron contactos")).toBeTruthy();
  });

  it("renders the detail with its optional block and links to the delete confirmation", async () => {
    serve(detail({ observaciones: "Atiende de lunes a viernes" }));
    setup(`${L}5/`);
    expect(await screen.findByText("Atiende de lunes a viernes")).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - CFP 401 - Email"));
    expect(screen.getByText("Vigente")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Eliminar/ }).getAttribute("href")).toBe(`${L}5/eliminar/`);
    expect(screen.getByText("#5")).toBeTruthy();
  });

  it("posts the whitelisted fields of the create form, filters the digits and shows errors after a rejection", async () => {
    serve(form());
    webPost.mockRejectedValueOnce({ response: { status: 400, data: form({}, { errors: ["Ingresá solo números."] }) } });
    webPost.mockResolvedValueOnce({ status: 200, data: { ok: true, redirect: L } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup(`${L}nuevo/?centro=3`);
    await screen.findByRole("heading", { level: 1, name: "Nuevo Contacto" });
    expect(webGet).toHaveBeenCalledWith(`${API}nuevo/?centro=3`, expect.anything());
    fireEvent.click(screen.getByRole("button", { name: /Crear/ }));
    expect(await screen.findByText("Ingresá solo números.")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Documento"), { target: { value: "12a3-4" } });
    expect((screen.getByLabelText("Documento") as HTMLInputElement).value).toBe("1234");
    fireEvent.click(screen.getByLabelText("Es Principal"));
    fireEvent.click(screen.getByRole("button", { name: /Crear/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(L));
    expect(webPost.mock.calls[1][0]).toBe(`${API}nuevo/?centro=3`);
    expect(Object.fromEntries(webPost.mock.calls[1][1] as URLSearchParams)).toEqual({
      centro: "3", nombre_contacto: "", rol_area: "", documento: "1234", telefono_contacto: "", email_contacto: "", es_principal: "on",
    });
  });

  it("renders the delete confirmation and removes through the API", async () => {
    serve({ valor: "cfp@example.com", tipo: "Email", centro: "CFP 401", urls: { detail: `${L}5/` } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: L } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup(`${L}5/eliminar/`);
    expect(await screen.findByText("cfp@example.com")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Cancelar/ }).getAttribute("href")).toBe(`${L}5/`);
    fireEvent.click(screen.getByRole("button", { name: /Sí, eliminar definitivamente/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(L));
    expect(webPost).toHaveBeenCalledWith(`${API}5/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("validates the payload shapes", () => {
    expect(contactoListValid(list())).toBe(true);
    expect(contactoListValid(list({ results: [row({ es_principal: "si" })] }))).toBe(false);
    expect(contactoDetailValid(detail())).toBe(true);
    expect(contactoDetailValid({ ...detail(), urls: {} })).toBe(false);
    expect(contactoFormValid(form())).toBe(true);
    expect(contactoFormValid({ ...form(), fields: [] })).toBe(false);
    expect(contactoDeleteValid({ valor: "a", tipo: "b", centro: "c", urls: { detail: "/x/" } })).toBe(true);
    expect(contactoDeleteValid({ valor: "a" })).toBe(false);
  });
});
