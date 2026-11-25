import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { comisionListaValid } from "./vatComisionLista";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/comisiones-lista/";
const page = (over: Record<string, unknown> = {}) => ({ is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "", ...over });
const row = (over: Record<string, unknown> = {}) => ({
  id: 5, codigo: "COM-001", nombre: "Comision Uno", oferta: "CFP 401 - Electricidad (2026)", fecha_inicio: "01/03/2026", fecha_fin: "01/12/2026", cupo: "10",
  estado: "activa", estado_label: "Activa",
  detail_url: "/vat/comisiones/5/", update_url: "/vat/comisiones/5/editar/", delete_url: "/vat/comisiones/5/eliminar/", ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [row()], page: page(), busqueda: "", permisos: { editar: false, eliminar: false },
  urls: { list: "/vat/comisiones/", create: "/vat/comisiones/nueva/" }, messages: [], ...over,
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

describe("VAT commission list route", () => {
  it("owns the list path only", () => {
    expect(findRoute("/vat/comisiones/")?.route.name).toBe("vat-comision-lista");
    for (const other of ["/vat/comisiones", "/vat/comisiones/4/", "/vat/comisiones/nueva/", "/vat/comisiones/horarios/", "/vat/comisiones/4/editar/", "/vat/cursos/comisiones/4/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-comision-lista");
    }
  });

  it("validates the payload strictly", () => {
    expect(comisionListaValid(list())).toBe(true);
    expect(comisionListaValid(list({ results: [row({ cupo: 10 })] }))).toBe(false);
    expect(comisionListaValid(list({ results: [row({ update_url: "https://x.test/" })] }))).toBe(false);
    expect(comisionListaValid({ ...list(), permisos: { editar: true } })).toBe(false);
    expect(comisionListaValid({ ...list(), urls: { list: "/a/" } })).toBe(false);
  });

  it("renders the rows, the badge of every state, the buttons by permission and the tour help", async () => {
    serve(list({
      results: [
        row(), row({ id: 6, codigo: "COM-002", estado: "cancelada", estado_label: "Cancelada" }), row({ id: 7, codigo: "COM-003", estado: "finalizada", estado_label: "Finalizada" }),
        row({ id: 8, codigo: "COM-004", nombre: "", estado: "planificada", estado_label: "Planificada" }),
      ],
      permisos: { editar: true, eliminar: false }, busqueda: "COM",
    }));
    setup("/vat/comisiones/?busqueda=COM");
    expect(await screen.findByText("Activa")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}?busqueda=COM`, expect.anything());
    expect(screen.getByText("Cancelada").className).toBe("badge-validacion no-validado");
    expect(screen.getByText("Planificada").className).toBe("badge-validacion pendiente");
    expect(screen.getByText("Finalizada").getAttribute("style")).toContain("rgb(75, 85, 99)");
    expect(screen.getByRole("link", { name: "COM-001" }).getAttribute("href")).toBe("/vat/comisiones/5/");
    expect(screen.getAllByText("—")).toHaveLength(1);
    expect(screen.getAllByRole("link", { name: /Editar/ })).toHaveLength(4);
    expect(screen.queryByRole("link", { name: /Eliminar/ })).toBeNull();
    expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe("COM");
    expect(screen.getByRole("link", { name: /Agregar/ }).getAttribute("href")).toBe("/vat/comisiones/nueva/");
    expect(screen.getByRole("button", { name: /Tour de ayuda/ })).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Comisiones"));
  });

  it("draws the delete link with its permission and shows the empty message", async () => {
    serve(list({ permisos: { editar: false, eliminar: true } }));
    setup("/vat/comisiones/");
    expect((await screen.findByRole("link", { name: /Eliminar/ })).getAttribute("href")).toBe("/vat/comisiones/5/eliminar/");
    expect(screen.queryByRole("link", { name: /Editar/ })).toBeNull();
    cleanup();
    serve(list({ results: [], page: page({ count: 0 }) }));
    setup("/vat/comisiones/");
    expect(await screen.findByText("No se encontraron comisiones")).toBeTruthy();
    expect(screen.getByText("No hay comisiones que coincidan con los criterios de búsqueda.")).toBeTruthy();
  });

  it("sorts by code and by name on the client like listSort.js", async () => {
    serve(list({ results: [row({ id: 1, codigo: "B-2", nombre: "Zeta" }), row({ id: 2, codigo: "A-1", nombre: "Alfa" })] }));
    setup("/vat/comisiones/");
    await screen.findByText("B-2");
    const codes = () => Array.from(document.querySelectorAll("tbody td:first-child")).map((c) => c.textContent);
    expect(codes()).toEqual(["B-2", "A-1"]);
    screen.getByText("Código").click();
    await waitFor(() => expect(codes()).toEqual(["A-1", "B-2"]));
  });
});
