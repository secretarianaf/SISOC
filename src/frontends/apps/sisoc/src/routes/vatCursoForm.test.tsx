import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { cursoDeleteValid, cursoFormValid } from "./vatCursoForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/cursos-formularios/";
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text" }, value: "", choices: [], errors: [], help_text: "", required: false, ...over,
});
const fields = (over: Record<string, Record<string, unknown>> = {}) => [
  field("plan_estudio", { label: "Plan Curricular", tag: "select", attrs: { class: "form-control select2", "data-width": "100%", "data-placeholder": "Seleccionar plan curricular...", required: "required" }, choices: [{ value: "", label: "Seleccionar plan de estudio..." }, { value: "3", label: "Electricidad" }], value: "", required: true, help_text: "Se listan todos los planes." }),
  field("nombre", { label: "Nombre", value: "", required: true }),
  field("estado", { label: "Estado", tag: "select", attrs: { class: "form-control" }, choices: [{ value: "planificado", label: "Planificado" }, { value: "activo", label: "Activo" }], value: "planificado", required: true }),
  field("inscripcion_libre", { label: "Inscripción libre", attrs: { class: "form-check-input", type: "checkbox" }, value: false, help_text: "Permite altas públicas." }),
  field("observaciones", { label: "Observaciones", tag: "textarea", attrs: { class: "form-control", rows: "3", cols: "40" }, value: "" }),
].map((f) => ({ ...f, ...(over[f.name] ?? {}) }));
const form = (over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}) => ({
  editing: false, fields: fields(fieldOver), non_field_errors: [], urls: { cancel: "/vat/centros/4/#cursos" }, messages: [], ...over,
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

describe("VAT course form route", () => {
  it("owns the three native form URLs and leaves the detail and the course commissions alone", () => {
    for (const path of ["/vat/cursos/nuevo/", "/vat/cursos/4/editar/", "/vat/cursos/4/eliminar/"]) expect(findRoute(path)?.route.name).toBe("vat-curso-form");
    for (const other of ["/vat/cursos/4/", "/vat/cursos/nuevo", "/vat/cursos/x/editar/", "/vat/cursos/comisiones/nueva/", "/vat/cursos/comisiones/4/editar/", "/vat/cursos/4/comision/nueva/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-curso-form");
    }
  });

  it("validates its payloads strictly", () => {
    expect(cursoFormValid(form())).toBe(true);
    expect(cursoFormValid({ ...form(), urls: { cancel: "https://x.test/" } })).toBe(false);
    expect(cursoFormValid({ ...form(), fields: fields().reverse() })).toBe(false);
    expect(cursoDeleteValid({ titulo: "a", urls: { detail: "/vat/centros/4/#cursos" } })).toBe(true);
    expect(cursoDeleteValid({ titulo: 3, urls: { detail: "/x/" } })).toBe(false);
  });

  it("renders the create form, forwards the centro query and counts the key fields like the native script", async () => {
    serve(form());
    setup("/vat/cursos/nuevo/?centro=4");
    expect(await screen.findByRole("heading", { level: 1, name: "Nuevo Curso" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}nuevo/?centro=4`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nuevo Curso"));
    expect(screen.getByRole("link", { name: "" }).getAttribute("href")).toBe("/vat/centros/4/#cursos");
    expect(Array.from(document.querySelectorAll("label.form-label")).map((e) => e.textContent?.trim())).toEqual(["Plan Curricular", "Nombre *", "Estado *", "Observaciones"]);
    // «Estado» always has a value, so one of the four key fields is complete.
    expect(screen.getByText("1 de 4 campos clave completados")).toBeTruthy();
    expect(screen.getByRole("progressbar").getAttribute("aria-valuenow")).toBe("25");
    fireEvent.change(screen.getByLabelText(/^Nombre/), { target: { value: "  " } });
    expect(screen.getByText("1 de 4 campos clave completados")).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/^Nombre/), { target: { value: "Electricidad básica" } });
    fireEvent.change(screen.getByLabelText("Observaciones"), { target: { value: "Una nota" } });
    expect(screen.getByText("3 de 4 campos clave completados")).toBeTruthy();
    expect((document.getElementById("cursoProgressBar") as HTMLElement).style.width).toBe("75%");
    expect(screen.getByText("La modalidad se toma automáticamente del plan de estudio seleccionado.")).toBeTruthy();
    // The native template prints its multi-line `{# #}` note as text.
    expect(screen.getByText(/^\{# REQ 2026-09-23: "Usa voucher" se oculta/)).toBeTruthy();
  });

  it("opens one guide item at a time", async () => {
    serve(form());
    setup("/vat/cursos/nuevo/?centro=4");
    await screen.findByRole("heading", { level: 1, name: "Nuevo Curso" });
    const nombre = screen.getByRole("button", { name: "Nombre del curso" });
    const plan = screen.getByRole("button", { name: "Plan curricular" });
    expect(nombre.className).toBe("accordion-button collapsed");
    fireEvent.click(nombre);
    expect(nombre.getAttribute("aria-expanded")).toBe("true");
    expect(document.getElementById("guiaNombre")?.className).toBe("accordion-collapse collapse show");
    fireEvent.click(plan);
    expect(nombre.getAttribute("aria-expanded")).toBe("false");
    expect(document.getElementById("guiaPlan")?.className).toBe("accordion-collapse collapse show");
    fireEvent.click(plan);
    expect(document.getElementById("guiaPlan")?.className).toBe("accordion-collapse collapse");
  });

  it("posts the five fields the template draws to the path with the centro query and navigates", async () => {
    serve(form());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/centros/4/?refresh=1#cursos" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/cursos/nuevo/?centro=4");
    await screen.findByRole("heading", { level: 1, name: "Nuevo Curso" });
    fireEvent.change(screen.getByLabelText(/^Nombre/), { target: { value: "Electricidad básica" } });
    fireEvent.click(screen.getByLabelText("Inscripción libre"));
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/centros/4/?refresh=1#cursos"));
    expect(webPost.mock.calls[0][0]).toBe(`${API}nuevo/?centro=4`);
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams)).toEqual({
      plan_estudio: "", nombre: "Electricidad básica", estado: "planificado", inscripcion_libre: "on", observaciones: "",
    });
  });

  it("shows the bound form with its errors after a rejected POST", async () => {
    serve(form());
    webPost.mockRejectedValue({ response: { status: 400, data: form({}, { nombre: { value: "", errors: ["Este campo es obligatorio."] } }) } });
    setup("/vat/cursos/nuevo/?centro=4");
    await screen.findByRole("heading", { level: 1, name: "Nuevo Curso" });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(await screen.findByText("Este campo es obligatorio.")).toBeTruthy();
    expect(window.location.pathname).toBe("/vat/cursos/nuevo/");
  });

  it("edits to the clean path and cancels to the centers panel", async () => {
    serve(form({ editing: true }, { nombre: { value: "Electricidad básica" } }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/centros/4/?refresh=1#cursos" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/cursos/8/editar/");
    expect(await screen.findByRole("heading", { level: 1, name: "Editar Curso" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/vat/centros/4/#cursos");
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    await waitFor(() => expect(assign).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe(`${API}8/editar/`);
  });

  it("renders the delete card and posts the delete", async () => {
    serve({ titulo: "Electricidad básica", urls: { detail: "/vat/centros/4/#cursos" } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/centros/4/?refresh=1#cursos" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/cursos/8/eliminar/");
    expect(await screen.findByRole("heading", { level: 1, name: "Eliminar curso" })).toBeTruthy();
    expect(screen.getByText("Electricidad básica").tagName).toBe("STRONG");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/vat/centros/4/#cursos");
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/centros/4/?refresh=1#cursos"));
    expect(webPost.mock.calls[0][0]).toBe(`${API}8/eliminar/`);
  });
});
