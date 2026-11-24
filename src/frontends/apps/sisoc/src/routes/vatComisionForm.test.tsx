import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { comisionDeleteValid, cursoFormValid, ofertaFormValid } from "./vatComisionForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const OFERTA = "web/vat/comisiones-formularios/";
const CURSO = "web/vat/comisiones-formularios/cursos/";
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text" }, value: "", choices: [], errors: [], required: false, ...over,
});
const optional = { class: "form-control select2", "data-width": "100%", "data-placeholder": "Seleccionar..." };
const select2 = { ...optional, required: "required" };
const ofertaFields = (over: Record<string, Record<string, unknown>> = {}) => [
  field("oferta", { label: "Oferta Institucional", tag: "select", attrs: select2, choices: [{ value: "", label: "---------" }, { value: "3", label: "Oferta 3" }], value: "3", required: true }),
  field("ubicacion", { label: "Ubicación", tag: "select", attrs: optional, choices: [{ value: "", label: "---------" }, { value: "5", label: "Sede" }], value: "" }),
  field("codigo_comision", { label: "Código de Comisión", value: "COM-1", required: true }),
  field("nombre", { label: "Nombre", value: "Uno", required: true }),
  field("fecha_inicio", { label: "Fecha de Inicio", attrs: { class: "form-control", type: "date" }, value: "01/03/2026", required: true }),
  field("fecha_fin", { label: "Fecha de Fin", attrs: { class: "form-control", type: "date" }, value: "", required: true }),
  field("cupo", { label: "Cupo Total", attrs: { class: "form-control", type: "number" }, value: "10", required: true }),
  field("estado", { label: "Estado", tag: "select", attrs: { class: "form-control" }, choices: [{ value: "planificada", label: "Planificada" }, { value: "activa", label: "Activa" }], value: "planificada", required: true }),
  field("observaciones", { label: "Observaciones", tag: "textarea", attrs: { class: "form-control", rows: "3", cols: "40" }, value: "" }),
].map((f) => ({ ...f, ...(over[f.name] ?? {}) }));
const oferta = (over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}) => ({
  editing: false, fields: ofertaFields(fieldOver), non_field_errors: [], subtitulo: "", urls: { list: "/vat/comisiones/", detail: "" }, messages: [], ...over,
});
const cursoFields = (over: Record<string, Record<string, unknown>> = {}) => [
  field("curso", { label: "Curso", tag: "select", attrs: select2, choices: [{ value: "", label: "---------" }, { value: "9", label: "Curso 9" }], value: "9", required: true }),
  field("ubicacion", { label: "Ubicación", tag: "select", attrs: select2, choices: [{ value: "", label: "---------" }, { value: "5", label: "Sede" }], value: "5", required: true }),
  field("cupo_total", { label: "Cupo Total", attrs: { class: "form-control", type: "number" }, value: "5", required: true }),
  field("acepta_lista_espera", { label: "Acepta Lista de Espera", attrs: { class: "form-check-input", type: "checkbox" }, value: false }),
  field("cupo_lista_espera", { label: "Cupo Lista de Espera", attrs: { class: "form-control", type: "number" }, value: "" }),
  field("fecha_inicio", { label: "Fecha de Inicio", attrs: { class: "form-control", type: "date" }, value: "", required: true }),
  field("fecha_fin", { label: "Fecha de Fin", attrs: { class: "form-control", type: "date" }, value: "", required: true }),
  field("estado", { label: "Estado", tag: "select", attrs: { class: "form-control" }, choices: [{ value: "planificada", label: "Planificada" }], value: "planificada", required: true }),
  field("observaciones", { label: "Observaciones", tag: "textarea", attrs: { class: "form-control", rows: "3", cols: "40" }, value: "" }),
].map((f) => ({ ...f, ...(over[f.name] ?? {}) }));
const curso = (over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}) => ({
  editing: false, fields: cursoFields(fieldOver), non_field_errors: [], urls: { list: "/vat/centros/", cancel: "" }, messages: [], ...over,
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

describe("VAT comision form route", () => {
  it("owns the twelve native form URLs and leaves the rest of the commission URLs alone", () => {
    for (const path of [
      "/vat/comisiones/nueva/", "/vat/comisiones/4/editar/", "/vat/comisiones/4/eliminar/",
      "/vat/cursos/comisiones/nueva/", "/vat/cursos/comisiones/4/editar/", "/vat/cursos/comisiones/4/eliminar/",
    ]) expect(findRoute(path)?.route.name).toBe("vat-comision-form");
    for (const other of ["/vat/comisiones/", "/vat/comisiones/4/", "/vat/comisiones/nueva", "/vat/comisiones/x/editar/", "/vat/comisiones/horarios/nuevo/", "/vat/cursos/comisiones/4/", "/vat/cursos/4/comision/nueva/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-comision-form");
    }
  });

  it("renders the offer create form like the native template and forwards the prefill query", async () => {
    serve(oferta());
    setup("/vat/comisiones/nueva/?oferta=3");
    expect(await screen.findByText("Nueva Comisión")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${OFERTA}nueva/?oferta=3`, expect.anything());
    expect(webGet.mock.calls.filter((c) => c[0] === `${OFERTA}nueva/?oferta=3`)).toHaveLength(1);
    await waitFor(() => expect(document.title).toBe("SISOC - Nueva Comisión"));
    expect(screen.getByText("Completá los datos para crear una nueva comisión")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Crear" })).toBeTruthy();
    expect(document.querySelectorAll(".select2-container").length).toBe(2);
    expect(document.querySelectorAll("label .text-danger").length).toBe(7);
    expect(screen.getByText(/Una comisión es un grupo de estudiantes/)).toBeTruthy();
    expect(screen.queryByText("Ver detalle")).toBeNull();
    expect(Array.from(document.querySelectorAll(".ci-form .form-label")).map((e) => e.textContent?.trim())).toEqual([
      "Oferta Institucional *", "Ubicación", "Código de Comisión *", "Nombre *", "Fecha de Inicio *", "Fecha de Fin *", "Cupo Total *", "Estado *", "Observaciones",
    ]);
  });

  it("posts only the nine fields of an offer edit to the clean path and navigates", async () => {
    serve(oferta({ editing: true, subtitulo: "COM-1 — Uno", urls: { list: "/vat/comisiones/", detail: "/vat/comisiones/4/" } }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/comisiones/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/comisiones/4/editar/");
    expect(await screen.findByText("Editar Comisión")).toBeTruthy();
    expect(screen.getByText("COM-1 — Uno")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Ver detalle/ }).getAttribute("href")).toBe("/vat/comisiones/4/");
    fireEvent.change(screen.getByLabelText(/^Nombre/), { target: { value: "Dos" } });
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/comisiones/"));
    expect(webPost.mock.calls[0][0]).toBe(`${OFERTA}4/editar/`);
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams)).toEqual({
      oferta: "3", ubicacion: "", codigo_comision: "COM-1", nombre: "Dos", fecha_inicio: "01/03/2026", fecha_fin: "", cupo: "10", estado: "planificada", observaciones: "",
    });
  });

  it("shows the first error after a rejected offer post, keeping the typed values", async () => {
    serve(oferta());
    webPost.mockRejectedValue({ response: { status: 400, data: oferta({}, { codigo_comision: { value: "zz", errors: ["Ya existe una comisión con ese código.", "otro"] } }) } });
    setup("/vat/comisiones/nueva/");
    await screen.findByText("Nueva Comisión");
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(await screen.findByText("Ya existe una comisión con ese código.")).toBeTruthy();
    expect(screen.queryByText("otro")).toBeNull();
    expect((screen.getByLabelText(/^Código de Comisión/) as HTMLInputElement).value).toBe("zz");
  });

  it("reports an unconfirmed result and does not resend", async () => {
    serve(oferta());
    webPost.mockRejectedValue(new Error("network"));
    setup("/vat/comisiones/nueva/");
    await screen.findByText("Nueva Comisión");
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("renders the course form with the waiting-list capacity hidden until the waiting list is on", async () => {
    serve(curso());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/centros/2/?refresh=1#cursos" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    const back = vi.spyOn(window.history, "back").mockImplementation(() => undefined);
    setup("/vat/cursos/comisiones/nueva/?curso=9");
    expect(await screen.findByRole("heading", { level: 1, name: "Nueva Comisión de Curso" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${CURSO}nueva/?curso=9`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nueva Comisión de Curso"));
    const wrapper = document.querySelector("[data-waitlist-capacity-wrapper]")!;
    expect(wrapper.classList.contains("d-none")).toBe(true);
    expect(wrapper.querySelector("label .text-danger")).toBeNull();
    fireEvent.click(screen.getByLabelText("Acepta Lista de Espera"));
    expect(wrapper.classList.contains("d-none")).toBe(false);
    expect(wrapper.querySelector("input")!.hasAttribute("required")).toBe(true);
    fireEvent.change(screen.getByLabelText("Cupo Lista de Espera"), { target: { value: "4" } });
    fireEvent.click(screen.getByLabelText("Acepta Lista de Espera"));
    expect(wrapper.classList.contains("d-none")).toBe(true);
    await waitFor(() => expect((screen.getByLabelText("Cupo Lista de Espera") as HTMLInputElement).value).toBe(""));
    fireEvent.click(screen.getByLabelText("Acepta Lista de Espera"));
    fireEvent.change(screen.getByLabelText("Cupo Lista de Espera"), { target: { value: "6" } });
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(back).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/centros/2/?refresh=1#cursos"));
    expect(webPost.mock.calls[0][0]).toBe(`${CURSO}nueva/`);
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams)).toMatchObject({ curso: "9", cupo_total: "5", acepta_lista_espera: "on", cupo_lista_espera: "6" });
  });

  it("renders the course edit form with the native cancel link and the required marks", async () => {
    serve(curso({ editing: true, urls: { list: "/vat/centros/", cancel: "/vat/centros/2/#cursos" } }, { acepta_lista_espera: { value: true }, cupo_lista_espera: { value: "3" } }));
    setup("/vat/cursos/comisiones/4/editar/");
    expect(await screen.findByRole("heading", { level: 1, name: "Editar Comisión de Curso" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/vat/centros/2/#cursos");
    expect(screen.getByRole("button", { name: "Actualizar" })).toBeTruthy();
    expect(document.querySelector("[data-waitlist-capacity-wrapper]")!.classList.contains("d-none")).toBe(false);
    expect((screen.getByLabelText("Cupo Lista de Espera") as HTMLInputElement).value).toBe("3");
    expect(document.querySelectorAll("label .text-danger").length).toBe(6);
    expect(webGet).toHaveBeenCalledWith(`${CURSO}4/editar/`, expect.anything());
  });

  it("renders the offer delete confirmation and removes the commission through the API", async () => {
    serve({ titulo: "COM-1 - Uno", subtitulo: "Oferta 3", urls: { detail: "/vat/comisiones/4/" } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/comisiones/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/comisiones/4/eliminar/");
    expect(await screen.findByText("¿Estás seguro?")).toBeTruthy();
    expect(screen.getByText("COM-1 - Uno")).toBeTruthy();
    expect(screen.getByText("Oferta 3")).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Eliminar Comisión"));
    fireEvent.click(screen.getByRole("button", { name: /Sí, eliminar definitivamente/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/comisiones/"));
    expect(webPost).toHaveBeenCalledWith(`${OFERTA}4/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("renders the plain course delete card and removes the commission through the API", async () => {
    serve({ titulo: "COM-9 - Curso", subtitulo: "", urls: { detail: "/vat/centros/2/#cursos" } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/centros/2/?refresh=1#cursos" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/cursos/comisiones/4/eliminar/");
    expect(await screen.findByRole("heading", { level: 1, name: "Eliminar comisión de curso" })).toBeTruthy();
    expect(screen.getByText("COM-9 - Curso")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/vat/centros/2/#cursos");
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/centros/2/?refresh=1#cursos"));
    expect(webPost).toHaveBeenCalledWith(`${CURSO}4/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("validates the payload shapes", () => {
    expect(ofertaFormValid(oferta())).toBe(true);
    expect(cursoFormValid(curso())).toBe(true);
    expect(ofertaFormValid(curso())).toBe(false);
    expect(cursoFormValid(oferta())).toBe(false);
    expect(ofertaFormValid({ ...oferta(), subtitulo: undefined })).toBe(false);
    expect(cursoFormValid({ ...curso(), messages: undefined })).toBe(false);
    expect(cursoFormValid({ ...curso(), urls: { list: "/vat/centros/", cancel: "https://x.test/" } })).toBe(false);
    expect(comisionDeleteValid({ titulo: "a", subtitulo: "", urls: { detail: "/x/" } })).toBe(true);
    expect(comisionDeleteValid({ titulo: "a" })).toBe(false);
  });
});
