import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { horarioDetailValid, horarioListValid } from "./vatComisionHorarios";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/comisiones-horarios/";
const page = (over: Record<string, unknown> = {}) => ({ is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "", ...over });
const row = (over: Record<string, unknown> = {}) => ({
  id: 4, comision: "COM-001 - Comision Uno", dia: "Lunes", desde: "09:00", hasta: "12:30", aula: "Aula 2", vigente: true,
  detail_url: "/vat/comisiones/horarios/4/", update_url: "/vat/comisiones/horarios/4/editar/", delete_url: "/vat/comisiones/horarios/4/eliminar/", ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [row()], page: page(), busqueda: "", permisos: { editar: false, eliminar: false },
  urls: { list: "/vat/comisiones/horarios/", create: "/vat/comisiones/horarios/nuevo/" }, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 4, title: "COM-001 - Lunes 09:00-12:30", comision: "COM-001 - Comision Uno", dia: "Lunes", aula: "Aula 2", desde: "09:00", hasta: "12:30", vigente: true,
  creado: "02/05/2026 10:00", modificado: "03/05/2026 11:30",
  urls: { list: "/vat/comisiones/horarios/", update: "/vat/comisiones/horarios/4/editar/", delete: "/vat/comisiones/horarios/4/eliminar/" }, messages: [], ...over,
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

describe("VAT commission schedule list and detail routes", () => {
  it("own their list and detail paths and leave the rest alone", () => {
    for (const path of ["/vat/comisiones/horarios/", "/vat/comisiones/horarios/4/"]) expect(findRoute(path)?.route.name).toBe("vat-comision-horarios");
    for (const other of ["/vat/comisiones/horarios", "/vat/comisiones/horarios/nuevo/", "/vat/comisiones/horarios/4/editar/", "/vat/comisiones/horarios/x/", "/vat/comisiones/", "/vat/cursos/comisiones/horarios/4/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-comision-horarios");
    }
  });

  it("validates both payloads strictly", () => {
    expect(horarioListValid(list())).toBe(true);
    expect(horarioListValid(list({ results: [row({ vigente: "si" })] }))).toBe(false);
    expect(horarioListValid(list({ results: [row({ delete_url: "https://x.test/" })] }))).toBe(false);
    expect(horarioListValid({ ...list(), permisos: { editar: true } })).toBe(false);
    expect(horarioDetailValid(detail())).toBe(true);
    expect(horarioDetailValid(detail({ urls: { list: "/a/", update: "/b/" } }))).toBe(false);
    expect(horarioDetailValid(detail({ id: "4" }))).toBe(false);
  });

  it("renders the list rows, the badge, the buttons by permission and the search and add controls", async () => {
    serve(list({
      results: [row(), row({ id: 5, vigente: false, aula: "—", detail_url: "/vat/comisiones/horarios/5/" })], permisos: { editar: true, eliminar: false }, busqueda: "Lunes",
    }));
    setup("/vat/comisiones/horarios/?dia_semana=1");
    expect(await screen.findAllByText("COM-001 - Comision Uno", { selector: "td" })).toHaveLength(2);
    expect(webGet).toHaveBeenCalledWith(`${API}?dia_semana=1`, expect.anything());
    expect(screen.getByText("Sí").className).toBe("badge-validacion validado");
    expect(screen.getByText("No").className).toBe("badge-validacion no-validado");
    expect(screen.getAllByRole("link", { name: /Editar/ })).toHaveLength(2);
    expect(screen.queryByRole("link", { name: /Eliminar/ })).toBeNull();
    expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe("Lunes");
    expect(screen.getByRole("link", { name: /Agregar/ }).getAttribute("href")).toBe("/vat/comisiones/horarios/nuevo/");
    await waitFor(() => expect(document.title).toBe("SISOC - Horarios de Comisión"));
  });

  it("draws the delete link with its permission and shows the empty message", async () => {
    serve(list({ permisos: { editar: false, eliminar: true } }));
    setup("/vat/comisiones/horarios/");
    expect((await screen.findByRole("link", { name: /Eliminar/ })).getAttribute("href")).toBe("/vat/comisiones/horarios/4/eliminar/");
    cleanup();
    serve(list({ results: [], page: page({ count: 0 }) }));
    setup("/vat/comisiones/horarios/");
    expect(await screen.findByText("No se encontraron horarios")).toBeTruthy();
    expect(screen.getByText("No hay horarios que coincidan con los criterios de búsqueda.")).toBeTruthy();
  });

  it("renders the detail with the audit block and both action links", async () => {
    serve(detail());
    setup("/vat/comisiones/horarios/4/");
    expect(await screen.findByRole("heading", { level: 1, name: "Horario" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}4/`, expect.anything());
    expect(screen.getByText("COM-001 - Lunes 09:00-12:30").tagName).toBe("SMALL");
    expect(screen.getByText("Aula 2")).toBeTruthy();
    expect(screen.getByText("Sí").className).toBe("badge bg-success");
    expect(screen.getByText("02/05/2026 10:00")).toBeTruthy();
    expect(screen.getByText("#4")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Editar/ }).getAttribute("href")).toBe("/vat/comisiones/horarios/4/editar/");
    expect(screen.getByRole("link", { name: /Eliminar/ }).getAttribute("href")).toBe("/vat/comisiones/horarios/4/eliminar/");
    await waitFor(() => expect(document.title).toBe("SISOC - COM-001 - Lunes 09:00-12:30"));
    cleanup();
    serve(detail({ vigente: false }));
    setup("/vat/comisiones/horarios/4/");
    expect((await screen.findByText("No")).className).toBe("badge bg-secondary");
  });
});
