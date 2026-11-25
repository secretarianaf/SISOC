import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { ofertaDeleteValid, ofertaFormValid } from "./vatOfertaForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/ofertas-institucionales/";
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text" }, value: "", choices: [], errors: [], help_text: "", required: false, ...over,
});
const s2 = (placeholder: string) => ({ class: "form-control select2", "data-width": "100%", "data-placeholder": placeholder, required: "required" });
const fields = (over: Record<string, Record<string, unknown>> = {}) => [
  field("plan_curricular", { attrs: { type: "hidden" }, value: "" }),
  field("centro", { label: "Centro", tag: "select", attrs: s2("Seleccionar centro..."), choices: [{ value: "", label: "---------" }, { value: "4", label: "CFP 401" }], value: "4", required: true }),
  field("titulo_referencia", { label: "Título de Referencia", tag: "select", attrs: s2("Seleccionar título..."), choices: [{ value: "", label: "---------" }, { value: "6", label: "Electricista" }], value: "6", required: true }),
  field("programa", { label: "Programa", tag: "select", attrs: s2("Seleccionar programa..."), choices: [{ value: "", label: "---------" }, { value: "1", label: "Programa Uno" }, { value: "2", label: "Programa Dos" }], value: "1", required: true }),
  field("ciclo_lectivo", { label: "Ciclo Lectivo", attrs: { class: "form-control", type: "number" }, value: "2026", required: true }),
  field("nombre_local", { label: "Nombre Local", value: "Local" }),
  field("estado", { label: "Estado de Oferta", tag: "select", attrs: { class: "form-control" }, choices: [{ value: "planificada", label: "Planificada" }, { value: "activa", label: "Activa" }], value: "planificada", required: true }),
  field("usa_voucher", { label: "Usa Voucher", attrs: { class: "form-check-input", type: "checkbox" }, value: false, help_text: "Al inscribirse, se valida un crédito." }),
  field("costo", { label: "Costo ($)", attrs: { class: "form-control", type: "number", step: "0.01" }, value: "150.5", help_text: "Dejar en 0 si el curso es gratuito." }),
  field("fecha_publicacion", { label: "Fecha de Publicación", attrs: { class: "form-control", type: "date" }, value: "" }),
  field("observaciones", { label: "Observaciones", tag: "textarea", attrs: { class: "form-control", rows: "3", cols: "40" }, value: "" }),
].map((f) => ({ ...f, ...(over[f.name] ?? {}) }));
const vouchers = (over: Record<string, unknown> = {}) => ({
  name: "voucher_parametrias", id: "id_voucher_parametrias", label: "Vouchers", help_text: "Seleccioná uno o más vouchers.", errors: [], values: [],
  attrs: { class: "form-select select2", "data-width": "100%", "data-placeholder": "Seleccionar vouchers...", size: "7", style: "min-height: 170px;" },
  choices: [{ value: "10", label: "Voucher Uno", programa_id: "1" }, { value: "11", label: "Voucher Dos", programa_id: "1" }, { value: "12", label: "Voucher Tres", programa_id: "2" }], ...over,
});
const form = (over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}) => ({
  editing: false, fields: fields(fieldOver), vouchers: vouchers(), non_field_errors: [], urls: { list: "/vat/ofertas-institucionales/" }, messages: [], ...over,
});

function serve(data: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const column = (id: string) => document.getElementById(id) as HTMLElement;
const chips = () => Array.from(document.querySelectorAll(".select2-selection__choice__display")).map((e) => e.textContent);

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT institutional offer form route", () => {
  it("owns the three native form URLs and leaves the list and the detail alone", () => {
    for (const path of ["/vat/ofertas-institucionales/nueva/", "/vat/ofertas-institucionales/4/editar/", "/vat/ofertas-institucionales/4/eliminar/"]) expect(findRoute(path)?.route.name).toBe("vat-oferta-institucional-form");
    for (const other of ["/vat/ofertas-institucionales/", "/vat/ofertas-institucionales/4/", "/vat/ofertas-institucionales/nueva", "/vat/ofertas-institucionales/x/editar/", "/vat/ofertas-institucionales/4/editar"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-oferta-institucional-form");
    }
  });

  it("validates its payloads strictly", () => {
    expect(ofertaFormValid(form())).toBe(true);
    expect(ofertaFormValid({ ...form(), vouchers: vouchers({ choices: [{ value: "1", label: "x" }] }) })).toBe(false);
    expect(ofertaFormValid({ ...form(), fields: fields().slice(1) })).toBe(false);
    expect(ofertaDeleteValid({ titulo: "a", subtitulo: "b", urls: { detail: "/vat/ofertas-institucionales/1/" } })).toBe(true);
    expect(ofertaDeleteValid({ titulo: "a", subtitulo: "b", urls: { detail: "https://x.test/" } })).toBe(false);
  });

  it("renders the create form like the native template, forwards the prefill query and draws the tour in place", async () => {
    serve(form());
    setup("/vat/ofertas-institucionales/nueva/?centro=4");
    expect(await screen.findByRole("heading", { level: 1, name: "Nueva Oferta Materia" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}nueva/?centro=4`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nueva Oferta Institucional"));
    expect(screen.getByRole("button", { name: "Crear" })).toBeTruthy();
    expect(Array.from(document.querySelectorAll("label.form-label")).map((e) => e.textContent?.trim())).toEqual([
      "Centro *", "Título de Referencia *", "Programa *", "Ciclo Lectivo *", "Nombre Local", "Estado de Oferta *", "Vouchers", "Costo ($)", "Fecha de Publicación", "Observaciones",
    ]);
    expect(column("campo-vouchers").style.display).toBe("none");
    expect(column("campo-costo").style.display).toBe("none");
    expect((document.getElementById("id_costo") as HTMLInputElement).value).toBe("0");
    expect(screen.getByText("Oferta educativa basada en un plan de estudio para un ciclo lectivo.")).toBeTruthy();
    expect(document.querySelectorAll(".select2-container").length).toBe(4);
    const tour = document.getElementById("sisoc-vat-tour-btn") as HTMLElement;
    // In place (inside the page content), not in a `<body>` portal like the list help.
    expect(tour.parentElement?.id).toBe("sisoc-vat-tour-container");
    expect(tour.parentElement?.parentElement).not.toBe(document.body);
  });

  it("shows the voucher and cost columns with the switch and drops the vouchers of another program", async () => {
    serve(form({ editing: true, vouchers: vouchers({ values: ["10", "12"] }) }, { usa_voucher: { value: true } }));
    setup("/vat/ofertas-institucionales/4/editar/");
    expect(await screen.findByRole("heading", { level: 1, name: "Editar Oferta Institucional" })).toBeTruthy();
    expect(column("campo-vouchers").style.display).toBe("block");
    expect(column("campo-costo").style.display).toBe("block");
    expect((document.getElementById("id_costo") as HTMLInputElement).value).toBe("150.5");
    // The chosen voucher of program 2 is dropped on load by `filtrarVouchersPorPrograma`.
    await waitFor(() => expect(chips()).toEqual(["Voucher Uno"]));
    fireEvent.mouseDown(document.querySelector(".select2-selection--multiple") as HTMLElement);
    expect(screen.queryByRole("option", { name: "Voucher Tres" })).toBeNull();
    fireEvent.click(screen.getByRole("option", { name: "Voucher Dos" }));
    expect(chips()).toEqual(["Voucher Uno", "Voucher Dos"]);
    fireEvent.click(screen.getByLabelText("Usa Voucher"));
    expect(column("campo-vouchers").style.display).toBe("none");
    expect(chips()).toEqual([]);
    expect((document.getElementById("id_costo") as HTMLInputElement).value).toBe("0");
  });

  it("posts the whitelisted fields with the repeated vouchers and navigates", async () => {
    serve(form({}, { usa_voucher: { value: true } }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/ofertas-institucionales/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/ofertas-institucionales/nueva/?centro=4");
    await screen.findByRole("heading", { level: 1, name: "Nueva Oferta Materia" });
    fireEvent.mouseDown(document.querySelector(".select2-selection--multiple") as HTMLElement);
    fireEvent.click(screen.getByRole("option", { name: "Voucher Dos" }));
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/ofertas-institucionales/"));
    expect(webPost.mock.calls[0][0]).toBe(`${API}nueva/`);
    const body = webPost.mock.calls[0][1] as URLSearchParams;
    expect(Array.from(body.keys())).toEqual([
      "plan_curricular", "centro", "titulo_referencia", "programa", "ciclo_lectivo", "nombre_local", "estado", "usa_voucher", "costo", "fecha_publicacion", "observaciones", "voucher_parametrias",
    ]);
    expect(Object.fromEntries(body)).toMatchObject({ centro: "4", programa: "1", usa_voucher: "on", costo: "150.5", voucher_parametrias: "11" });
  });

  it("shows the bound form with its errors after a rejected POST and keeps the chosen vouchers", async () => {
    serve(form({}, { usa_voucher: { value: true } }));
    webPost.mockRejectedValue({ response: { status: 400, data: form({ vouchers: vouchers({ values: ["10"], errors: ["Debés seleccionar al menos un voucher cuando la oferta usa voucher."] }) }, { usa_voucher: { value: true }, ciclo_lectivo: { value: "", errors: ["Este campo es obligatorio."] } }) } });
    setup("/vat/ofertas-institucionales/nueva/");
    await screen.findByRole("heading", { level: 1, name: "Nueva Oferta Materia" });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(await screen.findByText("Este campo es obligatorio.")).toBeTruthy();
    expect(screen.getByText("Debés seleccionar al menos un voucher cuando la oferta usa voucher.")).toBeTruthy();
    expect(chips()).toEqual(["Voucher Uno"]);
    expect(window.location.pathname).toBe("/vat/ofertas-institucionales/nueva/");
  });

  it("keeps the locked fields of the provincial role disabled and still posts the other fields", async () => {
    serve(form({ editing: true }, { centro: { attrs: { ...s2("Seleccionar centro..."), disabled: "disabled" } }, ciclo_lectivo: { attrs: { class: "form-control", type: "number", disabled: "disabled" } } }));
    setup("/vat/ofertas-institucionales/4/editar/");
    await screen.findByRole("heading", { level: 1, name: "Editar Oferta Institucional" });
    expect(document.querySelectorAll(".select2-container--disabled").length).toBe(1);
    expect((document.getElementById("id_ciclo_lectivo") as HTMLInputElement).disabled).toBe(true);
  });

  it("renders the delete confirmation and posts the delete", async () => {
    serve({ titulo: "Electricista - 2026", subtitulo: "Ciclo 2026 • CFP 401", urls: { detail: "/vat/ofertas-institucionales/4/" } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/ofertas-institucionales/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/ofertas-institucionales/4/eliminar/");
    expect(await screen.findByText("Ciclo 2026 • CFP 401")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Cancelar/ }).getAttribute("href")).toBe("/vat/ofertas-institucionales/4/");
    fireEvent.click(screen.getByRole("button", { name: /Sí, eliminar definitivamente/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/ofertas-institucionales/"));
    expect(webPost.mock.calls[0][0]).toBe(`${API}4/eliminar/`);
  });
});
