import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { deleteValid, formValid } from "./vatInscripcionForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/inscripciones-persona/";
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text", required: "required" }, value: "", choices: [], errors: [], ...over,
});
const select2 = (name: string, label: string, value: string) => field(name, {
  label, tag: "select", attrs: { class: "form-control select2", "data-width": "100%", "data-placeholder": `Seleccionar ${label}...`, required: "required" },
  choices: [{ value: "", label: "---------" }, { value: "7", label: "Opción 7" }, { value: "8", label: "Opción 8" }], value,
});
const fields = (over: Record<string, Record<string, unknown>> = {}) => [
  select2("ciudadano", "Ciudadano", "7"),
  select2("comision", "Comisión", "7"),
  select2("programa", "Programa", "8"),
  field("estado", { label: "Estado", tag: "select", attrs: { class: "form-control", required: "required" }, choices: [{ value: "inscripta", label: "Inscripta" }, { value: "rechazada", label: "Rechazada" }], value: "inscripta" }),
  field("origen_canal", { label: "Origen del Canal", tag: "select", attrs: { class: "form-control", required: "required" }, choices: [{ value: "backoffice", label: "Backoffice" }], value: "backoffice" }),
  field("observaciones", { label: "Observaciones", tag: "textarea", attrs: { class: "form-control", rows: "3", cols: "40" } }),
].map((f) => ({ ...f, ...(over[f.name] ?? {}) }));
const form = (over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}) => ({
  editing: false, fields: fields(fieldOver), urls: { list: "/vat/inscripciones/" }, messages: [], ...over,
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

describe("VAT inscripcion form route", () => {
  it("owns nueva, editar and eliminar only", () => {
    for (const path of ["/vat/inscripciones/nueva/", "/vat/inscripciones/4/editar/", "/vat/inscripciones/4/eliminar/"]) {
      expect(findRoute(path)?.route.name).toBe("vat-inscripcion-form");
    }
    for (const other of ["/vat/inscripciones/nueva", "/vat/inscripciones/4/", "/vat/inscripciones/x/editar/", "/vat/inscripciones/4/otra/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-inscripcion-form");
    }
  });

  it("renders the create form and forwards the prefill query of the native GET", async () => {
    serve(form());
    setup("/vat/inscripciones/nueva/?ciudadano=7");
    expect(await screen.findByRole("heading", { level: 1, name: "Nueva Inscripción" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}nueva/?ciudadano=7`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nueva Inscripción"));
    expect(screen.getByRole("button", { name: "Crear" })).toBeTruthy();
    expect((document.querySelector(".card-body form") as HTMLFormElement).noValidate).toBe(true);
    expect(document.querySelectorAll(".select2-container").length).toBe(3);
    expect((screen.getByLabelText(/Observaciones/) as HTMLTextAreaElement).rows).toBe(3);
    expect(screen.getByText("Vincula una persona con una comisión y programa.")).toBeTruthy();
  });

  it("posts the whitelisted fields to the clean path and navigates on success", async () => {
    serve(form({ editing: true }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/inscripciones/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/inscripciones/4/editar/");
    await screen.findByRole("heading", { level: 1, name: "Editar Inscripción" });
    fireEvent.change(screen.getByLabelText(/Estado/), { target: { value: "rechazada" } });
    fireEvent.change(screen.getByLabelText(/Observaciones/), { target: { value: "Nota" } });
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/inscripciones/"));
    expect(webPost.mock.calls[0][0]).toBe(`${API}4/editar/`);
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams)).toEqual({
      ciudadano: "7", comision: "7", programa: "8", estado: "rechazada", origen_canal: "backoffice", observaciones: "Nota",
    });
  });

  it("posts the create form without the prefill query", async () => {
    serve(form());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/inscripciones/" } });
    vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/inscripciones/nueva/?ciudadano=7");
    await screen.findByRole("heading", { level: 1, name: "Nueva Inscripción" });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe(`${API}nueva/`);
  });

  it("shows the first error and the service message after a rejected post, keeping the typed values", async () => {
    serve(form());
    webPost.mockRejectedValue({
      response: { status: 400, data: form({ messages: [{ message: "El ciudadano ya está inscripto en esta comisión.", level: "error" }] }, { estado: { value: "rechazada", errors: ["Elija una opción válida.", "otro"] } }) },
    });
    setup("/vat/inscripciones/nueva/");
    await screen.findByRole("heading", { level: 1, name: "Nueva Inscripción" });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(await screen.findByText("Elija una opción válida.")).toBeTruthy();
    expect(screen.queryByText("otro")).toBeNull();
    expect(screen.getByText("Elija una opción válida.").className).toBe("text-danger small mt-1");
    expect(await screen.findByText("El ciudadano ya está inscripto en esta comisión.")).toBeTruthy();
    expect((screen.getByLabelText(/Estado/) as HTMLSelectElement).value).toBe("rechazada");
  });

  it("reports an unconfirmed result and does not resend", async () => {
    serve(form());
    webPost.mockRejectedValue(new Error("network"));
    setup("/vat/inscripciones/nueva/");
    await screen.findByRole("heading", { level: 1, name: "Nueva Inscripción" });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("renders the delete confirmation and removes through the API", async () => {
    serve({ ciudadano: "Ana Pérez", comision: "COM-001", estado_label: "Inscripta", urls: { detail: "/vat/inscripciones/4/" } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/inscripciones/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/inscripciones/4/eliminar/");
    expect(await screen.findByText("¿Estás seguro?")).toBeTruthy();
    expect(screen.getByText("COM-001 • Inscripta")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Cancelar/ }).getAttribute("href")).toBe("/vat/inscripciones/4/");
    fireEvent.click(screen.getByRole("button", { name: /Sí, eliminar definitivamente/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/inscripciones/"));
    expect(webPost).toHaveBeenCalledWith(`${API}4/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("validates the payload shapes", () => {
    expect(formValid(form())).toBe(true);
    expect(formValid({ ...form(), fields: [] })).toBe(false);
    expect(formValid({ ...form(), messages: undefined })).toBe(false);
    expect(deleteValid({ ciudadano: "a", comision: "b", estado_label: "c", urls: { detail: "/x/" } })).toBe(true);
    expect(deleteValid({ ciudadano: "a" })).toBe(false);
  });
});
