import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { planDetailValid, planListValid } from "./vatPlanes";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/catalogos/planes-curriculares/";
const BASE = "/vat/catalogos/planes-curriculares/";
const page = (over: Record<string, unknown> = {}) => ({ is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "", ...over });
const row = (over: Record<string, unknown> = {}) => ({
  id: 5, sector: "Industria", subsector: "Electricidad", nombre: "Electricista", modalidad: "Presencial", horas: "120", activo: true,
  detail_url: `${BASE}5/`, update_url: `${BASE}5/editar/`, delete_url: `${BASE}5/eliminar/`, ...over,
});
const filtersConfig = { fields: [{ name: "nombre", label: "Nombre", type: "text" }], defaultField: "nombre" };
const list = (over: Record<string, unknown> = {}) => ({
  results: [row()], page: page(), permisos: { editar: false, eliminar: false }, urls: { list: BASE, create: `${BASE}nuevo/` }, messages: [],
  filters_config: filtersConfig, favorites: { section: "", url: "/filtros/favoritos/", detail_url_template: "/filtros/favoritos/0/" }, ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 5, titulo: "Electricista", nombre: "Electricista", sector: "Industria", subsector: "Electricidad", modalidad: "Presencial", activo: true, normativa: "Res. 1",
  normativa_tipo: "Resolución", normativa_numero: "45", normativa_anio: "2020", horas_reloj: "120", nivel_requerido: "primario_completo", nivel_certifica: "nivel_2",
  permisos: { editar: true, eliminar: true }, urls: { list: BASE, update: `${BASE}5/editar/`, delete: `${BASE}5/eliminar/` }, messages: [], ...over,
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

describe("VAT curricular plan list and detail routes", () => {
  it("own their list and detail paths and leave the rest alone", () => {
    for (const path of [BASE, `${BASE}5/`]) expect(findRoute(path)?.route.name).toBe("vat-planes");
    for (const other of ["/vat/catalogos/planes-curriculares", `${BASE}nuevo/`, `${BASE}5/editar/`, `${BASE}5/eliminar/`, `${BASE}x/`, "/vat/catalogos/sectores/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-planes");
    }
  });

  it("validates both payloads strictly", () => {
    expect(planListValid(list())).toBe(true);
    expect(planListValid(list({ results: [row({ activo: "si" })] }))).toBe(false);
    expect(planListValid(list({ results: [row({ detail_url: "https://x.test/" })] }))).toBe(false);
    expect(planListValid({ ...list(), favorites: { section: "" } })).toBe(false);
    expect(planListValid({ ...list(), filters_config: null })).toBe(false);
    expect(planDetailValid(detail())).toBe(true);
    expect(planDetailValid(detail({ permisos: { editar: true } }))).toBe(false);
    expect(planDetailValid(detail({ urls: { list: BASE, update: BASE } }))).toBe(false);
  });

  it("renders the list with its filters, the badge, the buttons by permission and the sort header", async () => {
    serve(list({ results: [row(), row({ id: 6, nombre: "Albañil", activo: false, subsector: "—", horas: "—" })], permisos: { editar: true, eliminar: false } }));
    setup(`${BASE}?activo=true`);
    expect(await screen.findByRole("heading", { level: 2, name: "Buscar Plan de Estudio" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}?activo=true`, expect.anything());
    expect(screen.getByText("Activo").className).toBe("badge-validacion validado");
    expect(screen.getByText("Inactivo").className).toBe("badge-validacion no-validado");
    expect(screen.getAllByRole("link", { name: /Editar/ })).toHaveLength(2);
    expect(screen.queryByRole("link", { name: /Eliminar/ })).toBeNull();
    expect(screen.getByRole("link", { name: /Agregar/ }).getAttribute("href")).toBe(`${BASE}nuevo/`);
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("href")).toBe(BASE);
    expect(screen.getByRole("link", { name: "Electricista" }).getAttribute("href")).toBe(`${BASE}5/`);
    const names = () => Array.from(document.querySelectorAll("tbody td[data-titulo]")).map((c) => c.textContent);
    expect(names()).toEqual(["Electricista", "Albañil"]);
    screen.getByText("Nombre", { selector: "th" }).click();
    await waitFor(() => expect(names()).toEqual(["Albañil", "Electricista"]));
    await waitFor(() => expect(document.title).toBe("SISOC - Planes de Estudio"));
  });

  it("draws the delete link with its permission and shows the empty message", async () => {
    serve(list({ permisos: { editar: false, eliminar: true } }));
    setup(BASE);
    expect((await screen.findByRole("link", { name: /Eliminar/ })).getAttribute("href")).toBe(`${BASE}5/eliminar/`);
    cleanup();
    serve(list({ results: [], page: page({ count: 0 }) }));
    setup(BASE);
    expect(await screen.findByText("No se encontraron planes de estudio")).toBeTruthy();
    expect(screen.getByText("No hay planes registrados.")).toBeTruthy();
  });

  it("renders the detail panels and deletes through the native POST form after the confirmation", async () => {
    serve(detail());
    setup(`${BASE}5/`);
    expect(await screen.findByRole("heading", { level: 1, name: "Electricista" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}5/`, expect.anything());
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(expect.arrayContaining(["Clasificación Académica", "Datos del Plan"]));
    expect(screen.getByText("Activo").className).toBe("vp-badge vp-badge--ok");
    expect(screen.getByText("primario_completo")).toBeTruthy();
    expect(screen.getByText("Normativa - Número").nextElementSibling?.textContent).toBe("45");
    expect(screen.getByRole("link", { name: /Editar/ }).getAttribute("href")).toBe(`${BASE}5/editar/`);
    const form = document.querySelector(".vp-hero-actions form") as HTMLFormElement;
    expect(form.getAttribute("method")).toBe("post");
    expect(form.getAttribute("action")).toBe(`${BASE}5/eliminar/`);
    expect((form.querySelector("input[name=csrfmiddlewaretoken]") as HTMLInputElement).value).toBe("synthetic-csrf-token");
    const confirm = vi.spyOn(vatNavigation, "confirm").mockReturnValue(false);
    expect(fireEvent.submit(form)).toBe(false);
    expect(confirm).toHaveBeenCalledWith("¿Está seguro?");
    confirm.mockReturnValue(true);
    expect(fireEvent.submit(form)).toBe(true);
    await waitFor(() => expect(document.title).toBe("SISOC - Detalle Plan de Estudio"));
  });

  it("hides the hero actions the native template hides and shows the inactive badge", async () => {
    serve(detail({ permisos: { editar: false, eliminar: false }, activo: false }));
    setup(`${BASE}5/`);
    expect((await screen.findByText("Inactivo")).className).toBe("vp-badge vp-badge--off");
    expect(screen.queryByRole("link", { name: /Editar/ })).toBeNull();
    expect(document.querySelector(".vp-hero-actions form")).toBeNull();
  });
});
