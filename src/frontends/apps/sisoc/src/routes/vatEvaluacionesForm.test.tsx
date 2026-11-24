import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { deleteValid, formValid } from "./vatEvaluacionesForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/evaluaciones/";
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text", required: "required" }, value: "", choices: [], errors: [], ...over,
});
const fields = (over: Record<string, Record<string, unknown>> = {}) => [
  field("comision", { label: "Comisión", tag: "select", attrs: { class: "form-control select2", "data-width": "100%", "data-placeholder": "Seleccionar comisión...", required: "required" },
    choices: [{ value: "", label: "---------" }, { value: "7", label: "COM-001 - Uno" }], value: "7" }),
  field("tipo", { label: "Tipo de Evaluación", tag: "select", attrs: { class: "form-control", required: "required" }, choices: [{ value: "parcial", label: "Parcial" }, { value: "final", label: "Final" }], value: "parcial" }),
  field("nombre", { label: "Nombre de la Evaluación", value: "Parcial 1" }),
  field("descripcion", { label: "Descripción", tag: "textarea", attrs: { class: "form-control", rows: "3", cols: "40" } }),
  field("fecha", { label: "Fecha de la Evaluación", attrs: { class: "form-control", type: "date", required: "required" }, value: "2026-05-02" }),
  field("es_final", { label: "Es Evaluación Final", attrs: { class: "form-check-input", type: "checkbox" }, value: false }),
  field("ponderacion", { label: "Ponderación (%)", attrs: { class: "form-control", type: "number", step: "0.01", required: "required" }, value: "100" }),
  field("observaciones", { label: "Observaciones", tag: "textarea", attrs: { class: "form-control", rows: "3", cols: "40" } }),
].map((f) => ({ ...f, ...(over[f.name] ?? {}) }));
const form = (over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}) => ({
  editing: false, fields: fields(fieldOver), urls: { list: "/vat/evaluaciones/" }, ...over,
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

describe("VAT evaluaciones form route", () => {
  it("owns nueva, editar and eliminar only", () => {
    for (const path of ["/vat/evaluaciones/nueva/", "/vat/evaluaciones/4/editar/", "/vat/evaluaciones/4/eliminar/"]) {
      expect(findRoute(path)?.route.name).toBe("vat-evaluaciones-form");
    }
    for (const other of ["/vat/evaluaciones/nueva", "/vat/evaluaciones/4/", "/vat/evaluaciones/x/editar/", "/vat/evaluaciones/4/otra/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-evaluaciones-form");
    }
  });

  it("renders the native layout for the create form", async () => {
    serve(form());
    setup("/vat/evaluaciones/nueva/");
    expect(await screen.findByRole("heading", { level: 1, name: "Nueva Evaluación" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}nueva/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nueva Evaluación"));
    expect(screen.getByRole("button", { name: "Crear" })).toBeTruthy();
    const nombre = screen.getByLabelText(/Nombre de la Evaluación/) as HTMLInputElement;
    expect([nombre.className, nombre.required]).toEqual(["form-control", true]);
    expect((screen.getByLabelText(/Descripción/) as HTMLTextAreaElement).rows).toBe(3);
    expect((document.querySelector(".card-body form") as HTMLFormElement).noValidate).toBe(true);
    expect(document.querySelector(".select2-container")).toBeTruthy();
    expect((document.querySelector("select[name=comision]") as HTMLSelectElement).value).toBe("7");
  });

  it("posts the whitelisted fields and navigates on success", async () => {
    serve(form({ editing: true }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/evaluaciones/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/evaluaciones/4/editar/");
    await screen.findByRole("heading", { level: 1, name: "Editar Evaluación" });
    fireEvent.click(screen.getByLabelText("Es Evaluación Final"));
    fireEvent.change(screen.getByLabelText(/Nombre de la Evaluación/), { target: { value: "Final editado" } });
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/evaluaciones/"));
    expect(webPost.mock.calls[0][0]).toBe(`${API}4/editar/`);
    const body = webPost.mock.calls[0][1] as URLSearchParams;
    expect(Object.fromEntries(body)).toEqual({
      comision: "7", tipo: "parcial", nombre: "Final editado", descripcion: "", fecha: "2026-05-02", es_final: "on", ponderacion: "100", observaciones: "",
    });
  });

  it("shows the first error of each field and keeps the typed values after a rejected post", async () => {
    serve(form());
    webPost.mockRejectedValue({ response: { status: 400, data: form({}, { nombre: { value: "", errors: ["Este campo es obligatorio.", "otro"] } }) } });
    setup("/vat/evaluaciones/nueva/");
    await screen.findByRole("heading", { level: 1, name: "Nueva Evaluación" });
    fireEvent.change(screen.getByLabelText(/Nombre de la Evaluación/), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(await screen.findByText("Este campo es obligatorio.")).toBeTruthy();
    expect(screen.queryByText("otro")).toBeNull();
    expect(screen.getByText("Este campo es obligatorio.").className).toBe("text-danger small mt-1");
  });

  it("reports an unconfirmed result and does not resend", async () => {
    serve(form());
    webPost.mockRejectedValue(new Error("network"));
    setup("/vat/evaluaciones/nueva/");
    await screen.findByRole("heading", { level: 1, name: "Nueva Evaluación" });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("renders the delete confirmation and removes through the API", async () => {
    serve({ nombre: "Parcial 1", tipo_label: "Parcial", comision: "COM-001", urls: { detail: "/vat/evaluaciones/4/" } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/evaluaciones/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/evaluaciones/4/eliminar/");
    expect(await screen.findByText("¿Estás seguro?")).toBeTruthy();
    expect(screen.getByText("Parcial • COM-001", { exact: false })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Cancelar/ }).getAttribute("href")).toBe("/vat/evaluaciones/4/");
    fireEvent.click(screen.getByRole("button", { name: /Sí, eliminar definitivamente/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/evaluaciones/"));
    expect(webPost).toHaveBeenCalledWith(`${API}4/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("validates the payload shapes", () => {
    expect(formValid(form())).toBe(true);
    expect(formValid({ ...form(), fields: [] })).toBe(false);
    expect(deleteValid({ nombre: "a", tipo_label: "b", comision: "c", urls: { detail: "/x/" } })).toBe(true);
    expect(deleteValid({ nombre: "a" })).toBe(false);
  });
});
