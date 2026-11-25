import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { inscripcionDetailValid, inscripcionListValid } from "./vatInscripcion";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/inscripciones-persona/";
const page = (over: Record<string, unknown> = {}) => ({
  is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "", ...over,
});
const row = (over: Record<string, unknown> = {}) => ({
  id: 5, ciudadano: "Ana Pérez", comision: "COM-001", programa: "Programa Uno", canal: "Backoffice", fecha: "02/05/2026", estado: "inscripta", estado_label: "Inscripta",
  detail_url: "/vat/inscripciones/5/", update_url: "/vat/inscripciones/5/editar/", delete_url: "/vat/inscripciones/5/eliminar/", ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [row()], page: page(), busqueda: "", permisos: { editar: false, eliminar: false },
  urls: { list: "/vat/inscripciones/", create: "/vat/inscripciones/nueva/" }, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 5, ciudadano: "Ana Pérez", dni: "", comision_codigo: "COM-001", comision_label: "COM-001 — Comisión & Uno", programa: "Programa Uno", estado: "inscripta",
  estado_label: "Inscripta", canal: "Backoffice", fecha_inscripcion: "02/05/2026 10:00", fecha_validacion: "—", observaciones: "", fecha_creacion: "01/05/2026 10:00",
  fecha_modificacion: "01/05/2026 11:30", permisos: { editar: true, eliminar: true },
  urls: { comision: "/vat/comisiones/9/", update: "/vat/inscripciones/5/editar/", delete: "/vat/inscripciones/5/eliminar/" }, messages: [], ...over,
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

describe("VAT inscripciones route", () => {
  it("owns the list and the detail paths only", () => {
    for (const path of ["/vat/inscripciones/", "/vat/inscripciones/12/"]) expect(findRoute(path)?.route.name).toBe("vat-inscripcion");
    for (const other of ["/vat/inscripciones", "/vat/inscripciones/nueva/", "/vat/inscripciones/12/editar/", "/vat/inscripciones-oferta/", "/vat/inscripciones/12/cambiar-estado/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-inscripcion");
    }
  });

  it("renders the rows, one badge per state and only the buttons the permissions allow", async () => {
    serve(list({
      results: [row(), row({ id: 6, ciudadano: "Luis Gómez", estado: "completada", estado_label: "Completada" }), row({ id: 7, estado: "rechazada", estado_label: "Rechazada" }),
        row({ id: 8, estado: "validada_presencial", estado_label: "Validada" }), row({ id: 9, estado: "en_espera", estado_label: "En espera" })],
      busqueda: "Ana",
    }));
    setup("/vat/inscripciones/?busqueda=Ana");
    await screen.findByText("Luis Gómez");
    expect(webGet).toHaveBeenCalledWith(`${API}?busqueda=Ana`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Inscripciones"));
    expect(screen.getByRole("heading", { level: 2, name: "Buscar Inscripción" })).toBeTruthy();
    expect((screen.getByRole("searchbox") as HTMLInputElement).placeholder).toBe("Buscar por ciudadano, comisión o programa");
    expect(screen.getByRole("link", { name: "Agregar" }).getAttribute("href")).toBe("/vat/inscripciones/nueva/");
    expect([...document.querySelectorAll("thead th")].map((th) => th.textContent?.trim())).toEqual(["Ciudadano", "Comisión", "Programa", "Canal", "Fecha", "Estado", "Acciones"]);
    const badges = [...document.querySelectorAll(".badge-validacion")].map((b) => [b.className, b.querySelector("i")?.className, b.textContent]);
    expect(badges).toEqual([
      ["badge-validacion validado", "fas fa-check-circle", " Inscripta"],
      ["badge-validacion", "fas fa-flag-checkered", " Completada"],
      ["badge-validacion no-validado", "fas fa-times-circle", " Rechazada"],
      ["badge-validacion validado", "fas fa-user-check", " Validada"],
      ["badge-validacion pendiente", "fas fa-clock", " En espera"],
    ]);
    expect((document.querySelectorAll(".badge-validacion")[1] as HTMLElement).style.background).toBe("rgb(75, 85, 99)");
    expect(screen.queryByRole("link", { name: "Editar" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Eliminar" })).toBeNull();
  });

  it("adds the edit and delete buttons for managers and the empty message", async () => {
    serve(list({ permisos: { editar: true, eliminar: true } }));
    setup("/vat/inscripciones/");
    await screen.findByText("COM-001");
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/vat/inscripciones/5/editar/");
    expect(screen.getByRole("link", { name: "Eliminar" }).getAttribute("href")).toBe("/vat/inscripciones/5/eliminar/");
    cleanup();
    serve(list({ results: [], page: page({ count: 0 }) }));
    setup("/vat/inscripciones/");
    expect(await screen.findByText("No se encontraron inscripciones")).toBeTruthy();
    expect(screen.getByText("No hay inscripciones que coincidan con los criterios de búsqueda.")).toBeTruthy();
  });

  it("renders the detail with its pill and the actions the API allows", async () => {
    serve(detail({ observaciones: "Obs <b>x</b>" }));
    setup("/vat/inscripciones/5/");
    expect(await screen.findByText("Acciones rápidas")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}5/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Inscripción — Ana Pérez"));
    expect(screen.getByText("Inscripta", { selector: ".ci-pill" }).className).toBe("ci-pill ci-pill-green");
    expect(screen.getByText("Obs <b>x</b>")).toBeTruthy();
    expect(screen.getByText("#5")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Editar inscripción/ }).getAttribute("href")).toBe("/vat/inscripciones/5/editar/");
    expect(screen.getByRole("link", { name: /Eliminar/ }).getAttribute("href")).toBe("/vat/inscripciones/5/eliminar/");
    expect(screen.getByRole("link", { name: /Ver comisión/ }).getAttribute("href")).toBe("/vat/comisiones/9/");
  });

  it("hides the edit and delete controls when the API says so and omits empty observaciones", async () => {
    serve(detail({ permisos: { editar: false, eliminar: false } }));
    setup("/vat/inscripciones/5/");
    await screen.findByText("Acciones rápidas");
    expect(screen.queryByRole("link", { name: /Editar/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /Eliminar/ })).toBeNull();
    expect(screen.queryByText("Observaciones")).toBeNull();
  });

  it("validates the payload shapes", () => {
    expect(inscripcionListValid(list())).toBe(true);
    expect(inscripcionListValid(list({ permisos: null }))).toBe(false);
    expect(inscripcionDetailValid(detail())).toBe(true);
    expect(inscripcionDetailValid(detail({ id: "5" }))).toBe(false);
  });
});
