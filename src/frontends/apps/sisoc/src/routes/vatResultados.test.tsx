import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { resultadoDetailValid, resultadoListValid } from "./vatResultados";
import { resultadoDeleteValid, resultadoFormValid } from "./vatResultadosForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/resultados-evaluacion/";
const page = (over: Record<string, unknown> = {}) => ({
  is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "", ...over,
});
const row = (over: Record<string, unknown> = {}) => ({
  id: 5, evaluacion: "Parcial 1", persona: "Ana Prueba", calificacion: "7,50", aprobo: true, fecha: "02/05/2026",
  detail_url: "/vat/resultados-evaluacion/5/", update_url: "/vat/resultados-evaluacion/5/editar/", delete_url: "/vat/resultados-evaluacion/5/eliminar/", ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [row()], page: page(), busqueda: "", permisos: { editar: false, eliminar: false },
  urls: { list: "/vat/resultados-evaluacion/", create: "/vat/resultados-evaluacion/nuevo/" }, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 5, titulo: "Ana Prueba - Parcial 1: 7,50", evaluacion: "Parcial 1", tipo_label: "Parcial", persona: "Ana Prueba", comision: "COM-001", calificacion: "7,50",
  aprobo: true, fecha_registro: "02/05/2026 10:00", registrado_por: "registrador", observaciones: "", fecha_creacion: "01/05/2026 10:00",
  fecha_modificacion: "01/05/2026 11:30",
  urls: { list: "/vat/resultados-evaluacion/", update: "/vat/resultados-evaluacion/5/editar/", delete: "/vat/resultados-evaluacion/5/eliminar/" },
  messages: [], ...over,
});
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text" }, value: "", choices: [], errors: [], ...over,
});
const fields = (over: Record<string, Record<string, unknown>> = {}) => [
  field("evaluacion", { label: "Evaluación", tag: "select", attrs: { class: "form-control select2", "data-width": "100%", "data-placeholder": "Seleccionar evaluación...", required: "required" },
    choices: [{ value: "", label: "---------" }, { value: "3", label: "Parcial 1" }], value: "3" }),
  field("inscripcion", { label: "Inscripción", tag: "select", attrs: { class: "form-control select2", "data-width": "100%", "data-placeholder": "Seleccionar inscripción...", required: "required" },
    choices: [{ value: "", label: "---------" }, { value: "9", label: "Ana Prueba" }], value: "9" }),
  field("calificacion", { label: "Calificación", attrs: { class: "form-control", type: "number", step: "0.01" }, value: "7.50" }),
  field("aprobo", { label: "¿Aprobó?", tag: "select", attrs: { class: "form-control" }, choices: [{ value: "", label: "---" }, { value: "True", label: "Sí" }, { value: "False", label: "No" }], value: "True" }),
  field("observaciones", { label: "Observaciones", tag: "textarea", attrs: { class: "form-control", rows: "3", cols: "40" } }),
].map((f) => ({ ...f, ...(over[f.name] ?? {}) }));
const form = (over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}) => ({
  editing: false, fields: fields(fieldOver), urls: { list: "/vat/resultados-evaluacion/" }, ...over,
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

describe("VAT resultados routes", () => {
  it("own their list, detail and form paths only", () => {
    for (const path of ["/vat/resultados-evaluacion/", "/vat/resultados-evaluacion/12/"]) expect(findRoute(path)?.route.name).toBe("vat-resultados");
    for (const path of ["/vat/resultados-evaluacion/nuevo/", "/vat/resultados-evaluacion/4/editar/", "/vat/resultados-evaluacion/4/eliminar/"]) {
      expect(findRoute(path)?.route.name).toBe("vat-resultados-form");
    }
    for (const other of ["/vat/resultados-evaluacion", "/vat/resultados-evaluacion/nueva/", "/vat/resultados-evaluacion/x/editar/", "/vat/evaluaciones/"]) {
      expect(["vat-resultados", "vat-resultados-form"]).not.toContain(findRoute(other)?.route.name);
    }
  });

  it("renders the list rows, the three approval states and only the allowed buttons", async () => {
    serve(list({ results: [row(), row({ id: 6, aprobo: false, calificacion: "3,00" }), row({ id: 7, aprobo: null, calificacion: "—" })], permisos: { editar: true, eliminar: false }, busqueda: "Ana" }));
    setup("/vat/resultados-evaluacion/?busqueda=Ana");
    expect(await screen.findByRole("heading", { level: 2, name: "Buscar Resultado" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}?busqueda=Ana`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Resultados de Evaluación"));
    expect(screen.getAllByRole("link", { name: /Editar/ })).toHaveLength(3);
    expect(screen.queryByRole("link", { name: /Eliminar/ })).toBeNull();
    expect(document.querySelectorAll(".badge-validacion.validado, .badge-validacion.no-validado, .badge-validacion.pendiente")).toHaveLength(3);
    expect(document.querySelector(".badge-validacion.no-validado")?.textContent).toContain("No");
    expect((screen.getByRole("searchbox") as HTMLInputElement).defaultValue).toBe("Ana");
    expect(screen.getByRole("link", { name: /Agregar/ }).getAttribute("href")).toBe("/vat/resultados-evaluacion/nuevo/");
  });

  it("shows the empty state", async () => {
    serve(list({ results: [], page: page({ count: 0 }) }));
    setup("/vat/resultados-evaluacion/");
    expect(await screen.findByText("No se encontraron resultados")).toBeTruthy();
    expect(screen.getByText("No hay resultados de evaluación registrados.")).toBeTruthy();
  });

  it("renders the detail and keeps observations only when present", async () => {
    serve(detail({ observaciones: "Obs <b>x</b>", aprobo: null }));
    setup("/vat/resultados-evaluacion/5/");
    expect(await screen.findByRole("heading", { level: 1, name: "Resultado" })).toBeTruthy();
    expect(screen.getByText("Obs <b>x</b>")).toBeTruthy();
    expect(screen.getByText("registrador")).toBeTruthy();
    expect(screen.getByText("#5")).toBeTruthy();
    cleanup();
    serve(detail());
    setup("/vat/resultados-evaluacion/5/");
    await screen.findByText("Registrado por");
    expect(screen.queryByText("Observaciones")).toBeNull();
  });

  it("renders the native layout for the create form and posts the whitelisted fields", async () => {
    serve(form());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/resultados-evaluacion/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/resultados-evaluacion/nuevo/");
    expect(await screen.findByRole("heading", { level: 1, name: "Nuevo Resultado" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}nuevo/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nueva Resultado"));
    expect(document.querySelectorAll(".select2-container")).toHaveLength(2);
    expect((document.querySelector(".card-body form") as HTMLFormElement).noValidate).toBe(true);
    fireEvent.change(screen.getByLabelText("Calificación"), { target: { value: "8.25" } });
    fireEvent.change(screen.getByLabelText("¿Aprobó?"), { target: { value: "False" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/resultados-evaluacion/"));
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams)).toEqual({
      evaluacion: "3", inscripcion: "9", calificacion: "8.25", aprobo: "False", observaciones: "",
    });
  });

  it("shows the first error and keeps the form after a rejected post, and does not resend when unconfirmed", async () => {
    serve(form({ editing: true }));
    webPost.mockRejectedValueOnce({ response: { status: 400, data: form({ editing: true }, { calificacion: { value: "x", errors: ["Introduzca un número.", "otro"] } }) } });
    setup("/vat/resultados-evaluacion/5/editar/");
    await screen.findByRole("heading", { level: 1, name: "Editar Resultado" });
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    expect(await screen.findByText("Introduzca un número.")).toBeTruthy();
    expect(screen.queryByText("otro")).toBeNull();
    webPost.mockRejectedValueOnce(new Error("network"));
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    expect(webPost).toHaveBeenCalledTimes(2);
  });

  it("renders the delete confirmation and removes through the API", async () => {
    serve({ persona: "Ana Prueba", evaluacion: "Parcial 1", calificacion: "7,50", urls: { detail: "/vat/resultados-evaluacion/5/" } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/resultados-evaluacion/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/resultados-evaluacion/5/eliminar/");
    expect(await screen.findByText("¿Estás seguro?")).toBeTruthy();
    expect(screen.getByText("Parcial 1 • Calif: 7,50")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Cancelar/ }).getAttribute("href")).toBe("/vat/resultados-evaluacion/5/");
    fireEvent.click(screen.getByRole("button", { name: /Sí, eliminar definitivamente/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/resultados-evaluacion/"));
    expect(webPost).toHaveBeenCalledWith(`${API}5/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("validates the payload shapes", () => {
    expect(resultadoListValid(list())).toBe(true);
    expect(resultadoListValid(list({ results: [row({ aprobo: "si" })] }))).toBe(false);
    expect(resultadoDetailValid(detail())).toBe(true);
    expect(resultadoDetailValid({ ...detail(), urls: {} })).toBe(false);
    expect(resultadoFormValid(form())).toBe(true);
    expect(resultadoFormValid({ ...form(), fields: [] })).toBe(false);
    expect(resultadoDeleteValid({ persona: "a", evaluacion: "b", calificacion: "c", urls: { detail: "/x/" } })).toBe(true);
    expect(resultadoDeleteValid({ persona: "a" })).toBe(false);
  });
});
