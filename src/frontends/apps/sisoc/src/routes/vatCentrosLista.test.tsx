import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { centrosListValid } from "./vatCentrosLista";
import { centroBajaValid } from "./vatCentrosBaja";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/centros-lista/";
const L = "/vat/centros/";
const CONFIRM = "¿Estás seguro de que deseas eliminar este centro? Esta acción no se puede deshacer.";
const row = (over: Record<string, unknown> = {}) => ({
  id: 5, nombre: "CFP 401", calle: "Calle 12", telefono: "221 555", celular: "None", activo: true,
  detail_url: `${L}5/`, update_url: `${L}5/editar/`, delete_url: `${L}5/eliminar/`, ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  filters_config: { fields: [{ name: "nombre", label: "Nombre", type: "text" }, { name: "estado_carga", label: "Estado de carga", type: "boolean", options: [{ value: "true", label: "COMPLETO" }, { value: "false", label: "INCOMPLETO" }] }] },
  favorites: { section: "vat_centros", url: "/filtros-favoritos/", detail_url_template: "/filtros-favoritos/0/" },
  results: [row()], page: { is_paginated: false, number: 1, previous: null, next: null, range: [1], query_prefix: "" },
  can_add: true, permisos: { eliminar: true }, urls: { list: L, create: `${L}nuevo/` }, messages: [], ...over,
});
const baja = (over: Record<string, unknown> = {}) => ({
  id: 5, nombre: "CFP 401", confirm_text: "Dar de baja", cancel_text: "Cancelar", urls: { detail: `${L}5/` }, messages: [],
  preview: { total_afectados: 3, total_baja_logica: 3, desglose_por_modelo: [{ modelo: "Centro", cantidad: 1, modo: "baja_logica", ejemplos: ["CFP 401"] }, { modelo: "Curso", cantidad: 2, modo: "baja_logica", ejemplos: [] }] },
  ...over,
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

describe("VAT centros list and delete routes", () => {
  it("own the list and the delete confirmation only", () => {
    expect(findRoute(L)?.route.name).toBe("vat-centros-lista");
    expect(findRoute(`${L}12/eliminar/`)?.route.name).toBe("vat-centros-baja");
    for (const other of ["/vat/centros", `${L}12/`, `${L}12/editar/`, `${L}nuevo/`, `${L}ajax/`, `${L}x/eliminar/`]) {
      expect(["vat-centros-lista", "vat-centros-baja"]).not.toContain(findRoute(other)?.route.name);
    }
  });

  it("renders the filters bar, the rows and the native actions", async () => {
    serve(list());
    setup(`${L}?busqueda=cfp&page=2`);
    expect(await screen.findByRole("heading", { level: 2, name: "Buscar Centros de Formación Profesional" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}?busqueda=cfp&page=2`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - INET - Centros"));
    expect(screen.getByRole("link", { name: "Agregar CFP" }).getAttribute("href")).toBe(`${L}nuevo/`);
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("href")).toBe(L);
    expect(screen.getByRole("link", { name: "CFP 401" }).getAttribute("href")).toBe(`${L}5/`);
    expect(screen.getByRole("link", { name: /Editar/ }).getAttribute("href")).toBe(`${L}5/editar/`);
    expect(screen.getByText("221 555 / None")).toBeTruthy();
    expect(screen.getByText("Activo", { selector: ".badge-success" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Tour de ayuda" })).toBeTruthy();
    expect(document.getElementById("pagination-container")?.querySelector("ul")).toBeNull();
  });

  it("hides the add button and the delete form without those rights and shows the empty state", async () => {
    serve(list({ can_add: false, permisos: { eliminar: false }, results: [] }));
    setup(L);
    expect(await screen.findByText("No se encontraron centros.")).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Agregar CFP" })).toBeNull();
    expect(screen.queryByRole("button", { name: /Eliminar/ })).toBeNull();
  });

  it("deletes a row only after the native confirm and goes to the redirect", async () => {
    serve(list());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: L } });
    const confirm = vi.spyOn(vatNavigation, "confirm").mockReturnValueOnce(false).mockReturnValue(true);
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup(L);
    fireEvent.click(await screen.findByRole("button", { name: /Eliminar/ }));
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Eliminar/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(L));
    expect(confirm).toHaveBeenCalledWith(CONFIRM);
    expect(webPost).toHaveBeenCalledWith(`${API}5/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("shows the uncertain notice when the delete cannot be confirmed", async () => {
    serve(list());
    webPost.mockRejectedValue({ response: { status: 500 } });
    vi.spyOn(vatNavigation, "confirm").mockReturnValue(true);
    setup(L);
    fireEvent.click(await screen.findByRole("button", { name: /Eliminar/ }));
    expect(await screen.findByRole("alert")).toBeTruthy();
  });

  it("sorts locally in three states and keeps the pagination links of the native query", async () => {
    serve(list({
      results: [row({ id: 1, nombre: "Beta" }), row({ id: 2, nombre: "alfa" }), row({ id: 3, nombre: "Gamma" })],
      page: { is_paginated: true, number: 2, previous: 1, next: 3, range: [1, 2, 3, "…"], query_prefix: "busqueda=cfp&" },
    }));
    setup(`${L}?busqueda=cfp&page=2`);
    const header = await screen.findByRole("columnheader", { name: /Nombre/ });
    const names = () => screen.getAllByRole("row").slice(1).map((r) => within(r).getAllByRole("cell")[0].textContent);
    expect(names()).toEqual(["Beta", "alfa", "Gamma"]);
    fireEvent.click(header);
    expect(names()).toEqual(["alfa", "Beta", "Gamma"]);
    expect(header.className).toBe("sortable sort-asc");
    fireEvent.click(header);
    expect(names()).toEqual(["Gamma", "Beta", "alfa"]);
    fireEvent.click(header);
    expect(header.className).toBe("sortable");
    const pager = within(document.getElementById("pagination-container")!);
    expect(pager.getByRole("link", { name: "Volver" }).getAttribute("href")).toBe("?busqueda=cfp&page=1");
    expect(pager.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?busqueda=cfp&page=3");
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("renders the delete confirmation with the cascade preview and removes through the API", async () => {
    serve(baja());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: L } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup(`${L}5/eliminar/`);
    expect(await screen.findByText("CFP 401", { selector: "span.font-weight-bold" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}5/eliminar/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Confirmar Eliminación"));
    expect(screen.getByText("Total de registros afectados:")).toBeTruthy();
    expect(screen.getByText("Bajas lógicas: 3")).toBeTruthy();
    expect(screen.getAllByText("-")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe(`${L}5/`);
    fireEvent.click(screen.getByRole("button", { name: "Dar de baja" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(L));
    expect(webPost).toHaveBeenCalledWith(`${API}5/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("renders the confirmation without a preview and with a failed delete", async () => {
    serve(baja({ preview: null }));
    webPost.mockRejectedValue({ response: { status: 500 } });
    setup(`${L}5/eliminar/`);
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.queryByText("Total de registros afectados:")).toBeNull();
  });

  it("validates the payload shapes", () => {
    expect(centrosListValid(list())).toBe(true);
    expect(centrosListValid(list({ results: [row({ activo: "si" })] }))).toBe(false);
    expect(centrosListValid(list({ filters_config: { fields: [] } }))).toBe(false);
    expect(centrosListValid(list({ permisos: {} }))).toBe(false);
    expect(centroBajaValid(baja())).toBe(true);
    expect(centroBajaValid(baja({ preview: null }))).toBe(true);
    expect(centroBajaValid(baja({ urls: {} }))).toBe(false);
    expect(centroBajaValid(baja({ preview: { total_afectados: 1 } }))).toBe(false);
  });
});
