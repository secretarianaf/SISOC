import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { identificadorDetailValid, identificadorListValid } from "./vatIdentificadores";
import { identificadorDeleteValid, identificadorFormValid } from "./vatIdentificadoresForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/institucion/identificadores/";
const L = "/vat/institucion/identificadores/";
const page = { is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "" };
const row = (over: Record<string, unknown> = {}) => ({
  id: 5, centro: "CFP 401", tipo: "CUE", valor: "0601449", rol: "—", es_actual: true,
  detail_url: `${L}5/`, update_url: `${L}5/editar/`, delete_url: `${L}5/eliminar/`, ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [row()], page, busqueda: "", permisos: { editar: false, eliminar: false }, urls: { list: L, create: `${L}nuevo/` }, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 5, title: "CFP 401 - CUE: 0601449", centro: "CFP 401", tipo: "CUE", valor: "0601449", rol: "—", es_actual: false,
  vigencia_hasta: "Vigente", motivo: "Alta inicial", creado: "01/05/2026 10:00", modificado: "02/05/2026 11:00",
  urls: { list: L, update: `${L}5/editar/`, delete: `${L}5/eliminar/` }, messages: [], ...over,
});
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text" }, value: "", choices: [], errors: [], ...over,
});
const form = (over: Record<string, unknown> = {}, valor: Record<string, unknown> = {}) => ({
  editing: false, non_field_errors: [], urls: { list: L }, ...over,
  fields: [
    field("centro", { label: "Centro", tag: "select", attrs: { class: "form-control" }, value: "3", choices: [{ value: "3", label: "CFP 401" }] }),
    field("tipo_identificador", { label: "Tipo de Identificador", tag: "select", attrs: { class: "form-control" }, value: "cue", choices: [{ value: "cue", label: "CUE" }, { value: "cuie", label: "CUIE" }] }),
    field("valor_identificador", { label: "Valor del Identificador", ...valor }),
    field("rol_institucional", { label: "Rol institucional", tag: "select", attrs: {}, choices: [{ value: "", label: "---------" }, { value: "sede", label: "Sede" }] }),
    field("es_actual", { label: "Es Actual", attrs: { class: "form-check-input", type: "checkbox" }, value: true }),
    field("vigencia_hasta", { label: "Vigencia Hasta", attrs: { class: "form-control", type: "date" } }),
    field("motivo", { label: "Motivo del Cambio" }),
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

describe("VAT identificadores routes", () => {
  it("own their list, detail and form paths only", () => {
    for (const path of [L, `${L}12/`]) expect(findRoute(path)?.route.name).toBe("vat-identificadores");
    for (const path of [`${L}nuevo/`, `${L}4/editar/`, `${L}4/eliminar/`]) expect(findRoute(path)?.route.name).toBe("vat-identificadores-form");
    for (const other of ["/vat/institucion/identificadores", `${L}nueva/`, `${L}x/editar/`]) {
      expect(["vat-identificadores", "vat-identificadores-form"]).not.toContain(findRoute(other)?.route.name);
    }
  });

  it("renders the list keeping the filters, the yes/no badges and only the allowed buttons", async () => {
    serve(list({ results: [row(), row({ id: 6, es_actual: false })], permisos: { editar: false, eliminar: true } }));
    setup(`${L}?tipo_identificador=cue`);
    expect(await screen.findByRole("heading", { level: 2, name: "Buscar Identificador" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}?tipo_identificador=cue`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Identificadores Históricos"));
    expect(screen.getAllByRole("link", { name: /Eliminar/ })).toHaveLength(2);
    expect(screen.queryByRole("link", { name: /Editar/ })).toBeNull();
    expect(document.querySelector(".badge-validacion.no-validado")?.textContent).toContain("No");
  });

  it("shows the empty state", async () => {
    serve(list({ results: [], page: { ...page, count: 0 } }));
    setup(L);
    expect(await screen.findByText("No se encontraron identificadores")).toBeTruthy();
  });

  it("renders the detail and links to the delete confirmation", async () => {
    serve(detail());
    setup(`${L}5/`);
    expect(await screen.findByText("Alta inicial")).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - CFP 401 - CUE: 0601449"));
    expect(screen.getByText("Vigente")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Eliminar/ }).getAttribute("href")).toBe(`${L}5/eliminar/`);
    expect(screen.getByText("#5")).toBeTruthy();
  });

  it("posts the rendered fields only, keeps the query and shows errors after a rejection", async () => {
    serve(form());
    webPost.mockRejectedValueOnce({ response: { status: 400, data: form({}, { errors: ["Este campo es obligatorio."] }) } });
    webPost.mockResolvedValueOnce({ status: 200, data: { ok: true, redirect: L } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup(`${L}nuevo/?centro=3`);
    await screen.findByRole("heading", { level: 1, name: "Nuevo Identificador" });
    expect(webGet).toHaveBeenCalledWith(`${API}nuevo/?centro=3`, expect.anything());
    fireEvent.click(screen.getByRole("button", { name: /Crear/ }));
    expect(await screen.findByText("Este campo es obligatorio.")).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/Valor del Identificador/), { target: { value: "0601449" } });
    fireEvent.click(screen.getByLabelText("Es Actual"));
    fireEvent.click(screen.getByRole("button", { name: /Crear/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(L));
    expect(webPost.mock.calls[1][0]).toBe(`${API}nuevo/?centro=3`);
    expect(Object.fromEntries(webPost.mock.calls[1][1] as URLSearchParams)).toEqual({
      centro: "3", tipo_identificador: "cue", valor_identificador: "0601449", rol_institucional: "", vigencia_hasta: "", motivo: "",
    });
  });

  it("renders the delete confirmation and removes through the API", async () => {
    serve({ valor: "0601449", tipo: "CUE", centro: "CFP 401", urls: { detail: `${L}5/` } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: L } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup(`${L}5/eliminar/`);
    expect(await screen.findByText("0601449")).toBeTruthy();
    expect(screen.getByText("CUE • CFP 401")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Cancelar/ }).getAttribute("href")).toBe(`${L}5/`);
    fireEvent.click(screen.getByRole("button", { name: /Sí, eliminar definitivamente/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(L));
    expect(webPost).toHaveBeenCalledWith(`${API}5/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("validates the payload shapes", () => {
    expect(identificadorListValid(list())).toBe(true);
    expect(identificadorListValid(list({ results: [row({ es_actual: "si" })] }))).toBe(false);
    expect(identificadorDetailValid(detail())).toBe(true);
    expect(identificadorDetailValid({ ...detail(), urls: {} })).toBe(false);
    expect(identificadorFormValid(form())).toBe(true);
    expect(identificadorFormValid({ ...form(), fields: [] })).toBe(false);
    expect(identificadorDeleteValid({ valor: "a", tipo: "b", centro: "c", urls: { detail: "/x/" } })).toBe(true);
    expect(identificadorDeleteValid({ valor: "a" })).toBe(false);
  });
});
