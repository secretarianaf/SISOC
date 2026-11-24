import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { evaluacionDetailValid, evaluacionListValid } from "./vatEvaluaciones";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/evaluaciones/";
const page = (over: Record<string, unknown> = {}) => ({
  is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "", ...over,
});
const row = (over: Record<string, unknown> = {}) => ({
  id: 5, nombre: "Parcial 1", comision: "COM-001", tipo_label: "Parcial", fecha: "02/05/2026", es_final: false, ponderacion: "100,00",
  detail_url: "/vat/evaluaciones/5/", update_url: "/vat/evaluaciones/5/editar/", delete_url: "/vat/evaluaciones/5/eliminar/", ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [row()], page: page(), busqueda: "", permisos: { editar: false, eliminar: false },
  urls: { list: "/vat/evaluaciones/", create: "/vat/evaluaciones/nueva/" }, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 5, titulo: "COM-001 - Parcial 1 (Parcial)", nombre: "Parcial 1", tipo_label: "Parcial", comision_codigo: "COM-001", comision_nombre: "Comisión & Uno",
  fecha: "02/05/2026", es_final: false, ponderacion: "100,00", descripcion: "—", observaciones: "", fecha_creacion: "01/05/2026 10:00",
  fecha_modificacion: "01/05/2026 11:30", urls: { list: "/vat/evaluaciones/", update: "/vat/evaluaciones/5/editar/", delete: "/vat/evaluaciones/5/eliminar/" },
  messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
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

describe("VAT evaluaciones route", () => {
  it("owns the list and the detail paths only", () => {
    for (const path of ["/vat/evaluaciones/", "/vat/evaluaciones/12/"]) expect(findRoute(path)?.route.name).toBe("vat-evaluaciones");
    for (const other of ["/vat/evaluaciones", "/vat/evaluaciones/nueva/", "/vat/evaluaciones/12/editar/", "/vat/evaluaciones/12/eliminar/",
      "/vat/resultados-evaluacion/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-evaluaciones");
    }
  });

  it("renders the list rows and only the buttons the permissions allow", async () => {
    serve(list({ results: [row(), row({ id: 6, nombre: "Examen final", es_final: true, tipo_label: "Final", detail_url: "/vat/evaluaciones/6/" })], busqueda: "COM" }));
    setup("/vat/evaluaciones/?busqueda=COM");
    await screen.findByText("Parcial 1");
    expect(webGet).toHaveBeenCalledWith(`${API}?busqueda=COM`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Evaluaciones"));
    expect(screen.getByRole("heading", { level: 2, name: "Buscar Evaluación" })).toBeTruthy();
    expect((screen.getByRole("searchbox") as HTMLInputElement).placeholder).toBe("Buscar por nombre o comisión");
    expect(screen.getByRole("link", { name: "Agregar" }).getAttribute("href")).toBe("/vat/evaluaciones/nueva/");
    expect([...document.querySelectorAll("thead th")].map((th) => th.textContent?.trim())).toEqual(["Nombre", "Comisión", "Tipo", "Fecha", "Final", "Pond.", "Acciones"]);
    const cells = [...document.querySelectorAll("tbody tr")[1].querySelectorAll("td")].map((td) => td.textContent);
    expect(cells.slice(1, 6)).toEqual(["COM-001", "Final", "02/05/2026", " Sí", "100,00%"]);
    expect(document.querySelector(".badge-validacion.pendiente")?.textContent).toBe("No");
    expect(screen.queryByRole("link", { name: "Editar" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Eliminar" })).toBeNull();
  });

  it("adds the edit and delete buttons for managers and the empty message", async () => {
    serve(list({ permisos: { editar: true, eliminar: true } }));
    setup("/vat/evaluaciones/");
    await screen.findByText("Parcial 1");
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/vat/evaluaciones/5/editar/");
    expect(screen.getByRole("link", { name: "Editar" }).className).toBe("btn btn-editar link-handler");
    expect(screen.getByRole("link", { name: "Eliminar" }).getAttribute("href")).toBe("/vat/evaluaciones/5/eliminar/");
    cleanup();
    serve(list({ results: [], page: page({ count: 0 }) }));
    setup("/vat/evaluaciones/");
    expect(await screen.findByText("No se encontraron evaluaciones")).toBeTruthy();
    expect(screen.getByText("No hay evaluaciones registradas.")).toBeTruthy();
  });

  it("renders the detail, the optional observaciones and the always-on actions", async () => {
    serve(detail({ observaciones: "Obs <b>x</b>", es_final: true, descripcion: "Texto" }));
    setup("/vat/evaluaciones/5/");
    expect(await screen.findByRole("heading", { level: 1, name: "Evaluación" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}5/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - COM-001 - Parcial 1 (Parcial)"));
    expect(screen.getByText("COM-001 - Comisión & Uno")).toBeTruthy();
    expect(screen.getByText("Sí").className).toBe("badge bg-success");
    expect(screen.getByText("Obs <b>x</b>")).toBeTruthy();
    expect(screen.getByText("Texto")).toBeTruthy();
    expect(screen.getByText("#5")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/vat/evaluaciones/5/editar/");
    expect(screen.getByRole("link", { name: "Eliminar" }).getAttribute("href")).toBe("/vat/evaluaciones/5/eliminar/");
  });

  it("omits the observaciones block when empty and keeps the dash description", async () => {
    serve(detail());
    setup("/vat/evaluaciones/5/");
    await screen.findByRole("heading", { level: 1, name: "Evaluación" });
    expect(screen.queryByText("Observaciones")).toBeNull();
    expect(screen.getByText("—")).toBeTruthy();
    expect(screen.getByText("No").className).toBe("badge bg-secondary");
  });

  it("validates the payload shapes", () => {
    expect(evaluacionListValid(list())).toBe(true);
    expect(evaluacionListValid(list({ permisos: null }))).toBe(false);
    expect(evaluacionDetailValid(detail())).toBe(true);
    expect(evaluacionDetailValid(detail({ id: "5" }))).toBe(false);
  });
});
