import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { horarioDeleteValid, horarioFormValid } from "./vatComisionHorarioForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const OFERTA = "web/vat/comisiones-horarios/";
const CURSO = "web/vat/comisiones-horarios/cursos/";
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text" }, value: "", choices: [], errors: [], ...over,
});
const fields = (campo: string, over: Record<string, Record<string, unknown>> = {}) => [
  field(campo, { label: campo === "comision" ? "Comisión" : "Comisión de Curso", tag: "select", attrs: { class: "form-control select2", "data-width": "100%", "data-placeholder": "Seleccionar comisión...", required: "required" }, choices: [{ value: "", label: "---------" }, { value: "7", label: "COM-7" }], value: "7" }),
  field("dia_semana", { label: "Día de la Semana", tag: "select", attrs: { class: "form-control", required: "required" }, choices: [{ value: "1", label: "Lunes" }, { value: "2", label: "Martes" }], value: "1" }),
  field("hora_desde", { label: "Hora Desde", attrs: { class: "form-control", type: "time", required: "required" }, value: "09:00:00" }),
  field("hora_hasta", { label: "Hora Hasta", attrs: { class: "form-control", type: "time", required: "required" }, value: "12:00:00" }),
  field("aula_espacio", { label: "Aula/Espacio", value: "Aula 2" }),
  field("vigente", { label: "Vigente", attrs: { class: "form-check-input", type: "checkbox" }, value: true }),
].map((f) => ({ ...f, ...(over[f.name] ?? {}) }));
const form = (campo = "comision", over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}) => ({
  editing: false, campo, fields: fields(campo, fieldOver), non_field_errors: [], urls: { list: "/vat/comisiones/horarios/" }, messages: [], ...over,
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

describe("VAT comision horario form route", () => {
  it("owns the six native form URLs and leaves the list and the detail native", () => {
    for (const path of [
      "/vat/comisiones/horarios/nuevo/", "/vat/comisiones/horarios/4/editar/", "/vat/comisiones/horarios/4/eliminar/",
      "/vat/cursos/comisiones/horarios/nuevo/", "/vat/cursos/comisiones/horarios/4/editar/", "/vat/cursos/comisiones/horarios/4/eliminar/",
    ]) expect(findRoute(path)?.route.name).toBe("vat-comision-horario-form");
    for (const other of ["/vat/comisiones/horarios/", "/vat/comisiones/horarios/4/", "/vat/comisiones/horarios/nuevo", "/vat/comisiones/horarios/x/editar/", "/vat/comisiones/4/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-comision-horario-form");
    }
  });

  it("renders the create form of an offer commission and forwards the prefill query", async () => {
    serve(form());
    setup("/vat/comisiones/horarios/nuevo/?comision=7");
    expect(await screen.findByRole("heading", { level: 1, name: "Nueva Horario" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${OFERTA}nuevo/?comision=7`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nueva Horario"));
    expect(screen.getByRole("button", { name: "Crear" })).toBeTruthy();
    expect(document.querySelectorAll(".select2-container").length).toBe(1);
    expect(screen.getByText("Horario de clases para una comisión.")).toBeTruthy();
    expect(screen.getByLabelText("Vigente")).toBeTruthy();
  });

  it("posts the whitelisted fields of an edit to the clean path and navigates", async () => {
    serve(form("comision", { editing: true }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/comisiones/7/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/comisiones/horarios/4/editar/");
    await screen.findByRole("heading", { level: 1, name: "Editar Horario" });
    fireEvent.change(screen.getByLabelText(/Hora Desde/), { target: { value: "10:30" } });
    fireEvent.click(screen.getByLabelText("Vigente"));
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/comisiones/7/"));
    expect(webPost.mock.calls[0][0]).toBe(`${OFERTA}4/editar/`);
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams)).toEqual({
      comision: "7", dia_semana: "1", hora_desde: "10:30", hora_hasta: "12:00:00", aula_espacio: "Aula 2",
    });
  });

  it("keeps the empty first group of the course variant and posts the commission as a hidden input", async () => {
    serve(form("comision_curso"));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/cursos/comisiones/7/" } });
    vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/cursos/comisiones/horarios/nuevo/?comision_curso=7");
    await screen.findByRole("heading", { level: 1, name: "Nueva Horario" });
    expect(webGet).toHaveBeenCalledWith(`${CURSO}nuevo/?comision_curso=7`, expect.anything());
    expect(document.querySelectorAll(".select2-container").length).toBe(0);
    expect(document.querySelector("input[type=hidden][name=comision_curso]")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe(`${CURSO}nuevo/`);
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams).comision_curso).toBe("7");
  });

  it("shows the first error after a rejected post, keeping the typed values", async () => {
    serve(form());
    webPost.mockRejectedValue({
      response: { status: 400, data: form("comision", {}, { hora_hasta: { value: "08:00", errors: ["Este campo es obligatorio.", "otro"] } }) },
    });
    setup("/vat/comisiones/horarios/nuevo/");
    await screen.findByRole("heading", { level: 1, name: "Nueva Horario" });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(await screen.findByText("Este campo es obligatorio.")).toBeTruthy();
    expect(screen.queryByText("otro")).toBeNull();
    expect((screen.getByLabelText(/Hora Hasta/) as HTMLInputElement).value).toBe("08:00");
  });

  it("reports an unconfirmed result and does not resend", async () => {
    serve(form());
    webPost.mockRejectedValue(new Error("network"));
    setup("/vat/comisiones/horarios/nuevo/");
    await screen.findByRole("heading", { level: 1, name: "Nueva Horario" });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("renders the delete confirmation of a course schedule and removes it through the API", async () => {
    serve({ titulo: "Lunes 09:00-12:30", subtitulo: "None", urls: { detail: "/vat/comisiones/horarios/4/" } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/cursos/comisiones/7/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/cursos/comisiones/horarios/4/eliminar/");
    expect(await screen.findByText("¿Estás seguro?")).toBeTruthy();
    expect(screen.getByText("Lunes 09:00-12:30")).toBeTruthy();
    expect(screen.getByText("None")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Cancelar/ }).getAttribute("href")).toBe("/vat/comisiones/horarios/4/");
    fireEvent.click(screen.getByRole("button", { name: /Sí, eliminar definitivamente/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/cursos/comisiones/7/"));
    expect(webPost).toHaveBeenCalledWith(`${CURSO}4/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("validates the payload shapes", () => {
    expect(horarioFormValid(form())).toBe(true);
    expect(horarioFormValid(form("comision_curso"))).toBe(true);
    expect(horarioFormValid({ ...form(), campo: "otro" })).toBe(false);
    expect(horarioFormValid({ ...form("comision_curso"), campo: "comision" })).toBe(false);
    expect(horarioFormValid({ ...form(), messages: undefined })).toBe(false);
    expect(horarioDeleteValid({ titulo: "a", subtitulo: "b", urls: { detail: "/x/" } })).toBe(true);
    expect(horarioDeleteValid({ titulo: "a" })).toBe(false);
  });
});
