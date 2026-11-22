import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { inscripcionOfertaDetailValid, inscripcionOfertaListValid } from "./vatInscripcionOferta";
import { inscripcionDeleteValid, inscripcionFormValid } from "./vatInscripcionOfertaForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/inscripciones-oferta/";
const page = (over: Record<string, unknown> = {}) => ({ is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "", ...over });
const row = (over: Record<string, unknown> = {}) => ({
  id: 5, ciudadano: "Ana Prueba", documento: "30111222", oferta: "Electricista", centro: "CFP 401", estado: "inscrito", estado_label: "Inscrito", fecha: "02/05/2026 10:00",
  detail_url: "/vat/inscripciones-oferta/5/", update_url: "/vat/inscripciones-oferta/5/editar/", delete_url: "/vat/inscripciones-oferta/5/eliminar/", ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [row()], page: page(), busqueda: "", permisos: { editar: false, eliminar: false },
  urls: { list: "/vat/inscripciones-oferta/", create: "/vat/inscripciones-oferta/nueva/" }, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 5, ciudadano: "Ana Prueba", documento: "30111222", oferta: "Electricista", centro: "CFP 401", estado: "lista_espera", estado_label: "Lista de Espera",
  periodo: "01/03/2026 - 01/12/2026", horario: "09:00 - 12:00", dias: ["Lunes", "Martes"], costo: "$100", inscrito_por: "Ines Inscriptora",
  fecha_inscripcion: "02/05/2026 10:00", fecha_modificacion: "03/05/2026 11:30", permisos: { editar: true, eliminar: true },
  urls: { list: "/vat/inscripciones-oferta/", update: "/vat/inscripciones-oferta/5/editar/", delete: "/vat/inscripciones-oferta/5/eliminar/" }, messages: [], ...over,
});
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "select", attrs: { class: "form-control", required: "required" }, value: "", choices: [], errors: [], ...over,
});
const fields = (over: Record<string, Record<string, unknown>> = {}) => [
  field("oferta", { label: "Comisión", attrs: { class: "form-control select2", "data-width": "100%", "data-placeholder": "Seleccionar comisión...", required: "required" }, choices: [{ value: "", label: "---------" }, { value: "3", label: "COM-001" }], value: "3" }),
  field("ciudadano", { label: "Ciudadano", attrs: { class: "form-control select2", "data-width": "100%", "data-placeholder": "Seleccionar ciudadano...", required: "required" }, choices: [{ value: "", label: "---------" }, { value: "9", label: "Ana Prueba" }], value: "9" }),
  field("estado", { label: "Estado", choices: [{ value: "inscrito", label: "Inscrito" }, { value: "lista_espera", label: "Lista de Espera" }], value: "inscrito" }),
].map((f) => ({ ...f, ...(over[f.name] ?? {}) }));
const form = (over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}) => ({
  editing: false, fields: fields(fieldOver), non_field_errors: [], urls: { list: "/vat/inscripciones-oferta/" }, messages: [], ...over,
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

describe("VAT inscripciones de oferta routes", () => {
  it("own their list, detail and form paths only", () => {
    for (const path of ["/vat/inscripciones-oferta/", "/vat/inscripciones-oferta/12/"]) expect(findRoute(path)?.route.name).toBe("vat-inscripcion-oferta");
    for (const path of ["/vat/inscripciones-oferta/nueva/", "/vat/inscripciones-oferta/4/editar/", "/vat/inscripciones-oferta/4/eliminar/"]) expect(findRoute(path)?.route.name).toBe("vat-inscripcion-oferta-form");
    for (const other of ["/vat/inscripciones-oferta", "/vat/inscripciones-oferta/nuevo/", "/vat/inscripciones-oferta/x/editar/", "/vat/inscripciones/", "/vat/inscripciones/4/"]) {
      expect(["vat-inscripcion-oferta", "vat-inscripcion-oferta-form"]).not.toContain(findRoute(other)?.route.name);
    }
  });

  it("renders the list rows, the badge of every state, the buttons by permission and the tour help", async () => {
    serve(list({ results: [row(), row({ id: 6, estado: "lista_espera", estado_label: "Lista de Espera" }), row({ id: 7, estado: "completado", estado_label: "Completado" }),
      row({ id: 8, estado: "abandonado", estado_label: "Abandonado" }), row({ id: 9, estado: "rechazado", estado_label: "Rechazado" })], permisos: { editar: true, eliminar: false }, busqueda: "Ana" }));
    setup("/vat/inscripciones-oferta/?busqueda=Ana");
    expect(await screen.findByText("Inscrito")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}?busqueda=Ana`, expect.anything());
    expect(screen.getByText("Lista de Espera").className).toBe("badge-validacion pendiente");
    expect(screen.getByText("Rechazado").className).toBe("badge-validacion pendiente");
    expect(screen.getByText("Abandonado").className).toBe("badge-validacion no-validado");
    expect(screen.getByText("Completado").getAttribute("style")).toContain("rgb(75, 85, 99)");
    expect(screen.getAllByText("Editar")).toHaveLength(5);
    expect(screen.queryByText("Eliminar")).toBeNull();
    expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe("Ana");
    expect(screen.getByRole("button", { name: /Tour de ayuda/ })).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Inscripciones a Ofertas"));
  });

  it("shows the empty message", async () => {
    serve(list({ results: [], page: page({ count: 0 }) }));
    setup("/vat/inscripciones-oferta/");
    expect(await screen.findByText("No se encontraron inscripciones")).toBeTruthy();
    expect(screen.getByText("No hay inscripciones a ofertas registradas.")).toBeTruthy();
  });

  it("renders the detail with its badge, days, cost and the delete card by permission", async () => {
    serve(detail());
    setup("/vat/inscripciones-oferta/5/");
    expect(await screen.findByRole("heading", { level: 1, name: "Ana Prueba" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}5/`, expect.anything());
    expect(screen.getByText("Lista de Espera").className).toBe("badge bg-warning");
    expect(screen.getByText("Martes").className).toBe("badge bg-info");
    expect(screen.getByText("$100")).toBeTruthy();
    expect(screen.getByText("Ines Inscriptora")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Eliminar Inscripción/ }).getAttribute("href")).toBe("/vat/inscripciones-oferta/5/eliminar/");
  });

  it("hides the cost and the delete card when the native template does", async () => {
    serve(detail({ costo: "", dias: [], estado: "rechazado", estado_label: "Rechazado", permisos: { editar: false, eliminar: false } }));
    setup("/vat/inscripciones-oferta/5/");
    await screen.findByRole("heading", { level: 1, name: "Ana Prueba" });
    expect(screen.queryByText("Costo:")).toBeNull();
    expect(screen.queryByText("Peligro")).toBeNull();
    expect(screen.queryByRole("link", { name: /Editar/ })).toBeNull();
    expect(screen.getByText("Rechazado").className).toBe("badge bg-danger");
  });

  it("posts the whitelisted fields of the form and navigates on success", async () => {
    serve(form());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/inscripciones-oferta/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/inscripciones-oferta/nueva/");
    expect(await screen.findByRole("heading", { level: 1, name: "Nueva Inscripción" })).toBeTruthy();
    fireEvent.change(document.querySelector("select[name=estado]") as HTMLSelectElement, { target: { value: "lista_espera" } });
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/inscripciones-oferta/"));
    expect(webPost.mock.calls[0][0]).toBe(`${API}nueva/`);
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams)).toEqual({ oferta: "3", ciudadano: "9", estado: "lista_espera" });
  });

  it("shows field errors, the general alert and the queued toast after a rejected post", async () => {
    serve(form());
    webPost.mockRejectedValue({ response: { status: 400, data: form({ non_field_errors: ["General."], messages: [{ message: "Error al crear la inscripción.", level: "error" }] }, { ciudadano: { errors: ["Este campo es obligatorio."] } }) } });
    setup("/vat/inscripciones-oferta/nueva/");
    await screen.findByRole("heading", { level: 1, name: "Nueva Inscripción" });
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    expect(await screen.findByText("Este campo es obligatorio.")).toBeTruthy();
    expect(screen.getByText("General.")).toBeTruthy();
    expect(await screen.findByText("Error al crear la inscripción.")).toBeTruthy();
  });

  it("reports an unconfirmed result and does not resend", async () => {
    serve(form({ editing: true }));
    webPost.mockRejectedValue(new Error("network"));
    setup("/vat/inscripciones-oferta/5/editar/");
    await screen.findByRole("heading", { level: 1, name: "Editar Inscripción" });
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}5/editar/`);
  });

  it("renders the delete confirmation and removes through the API", async () => {
    serve({ ciudadano: "Ana Prueba", oferta: "Electricista", estado_label: "Inscrito", urls: { detail: "/vat/inscripciones-oferta/5/" } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/inscripciones-oferta/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/inscripciones-oferta/5/eliminar/");
    expect(await screen.findByText("¿Está seguro que desea eliminar esta inscripción?")).toBeTruthy();
    expect(screen.getByText("Ana Prueba").tagName).toBe("STRONG");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/vat/inscripciones-oferta/5/");
    fireEvent.click(screen.getByRole("button", { name: /Eliminar/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/inscripciones-oferta/"));
    expect(webPost).toHaveBeenCalledWith(`${API}5/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("validates the payload shapes", () => {
    expect(inscripcionOfertaListValid(list())).toBe(true);
    expect(inscripcionOfertaListValid({ ...list(), results: [{ id: 1 }] })).toBe(false);
    expect(inscripcionOfertaDetailValid(detail())).toBe(true);
    expect(inscripcionOfertaDetailValid({ ...detail(), dias: [1] })).toBe(false);
    expect(inscripcionFormValid(form())).toBe(true);
    expect(inscripcionFormValid({ ...form(), fields: [] })).toBe(false);
    expect(inscripcionDeleteValid({ ciudadano: "a", oferta: "b", estado_label: "c", urls: { detail: "/x/" } })).toBe(true);
    expect(inscripcionDeleteValid({})).toBe(false);
  });
});
