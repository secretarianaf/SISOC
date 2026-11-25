import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { asignarValid, masivoValid, parametriaValid } from "./vatVouchersForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/vouchers/";
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text", required: "required" }, value: "", choices: [], errors: [], help_text: "", ...over,
});
const select2 = (name: string, label: string, value = "") => field(name, { label, tag: "select", attrs: { class: "form-control select2", "data-width": "100%", "data-placeholder": `Seleccionar ${label}...`, required: "required" },
  choices: [{ value: "", label: "---------" }, { value: "3", label: `${label} tres` }], value });
const vencimiento = (over: Record<string, unknown> = {}) => field("fecha_vencimiento", { label: "Fecha de vencimiento", attrs: { class: "form-control", type: "date", required: "required" }, ...over });
const base = { urls: { list: "/vat/vouchers/" }, messages: [] };
const asignar = (over: Record<string, unknown> = {}) => ({
  ...base, titulo: "Asignar Voucher", fields: [select2("ciudadano", "Ciudadano", "3"), select2("programa", "Programa"), field("cantidad_inicial", { label: "Cantidad de créditos", attrs: { class: "form-control", type: "number", required: "required" }, value: "10" }), vencimiento({ value: "2027-01-01" })], ...over,
});
const masivo = (over: Record<string, unknown> = {}) => ({
  ...base, titulo: "Asignación Masiva", resultado: null,
  fields: [select2("programa", "Programa", "3"), field("cantidad_inicial", { label: "Cantidad de créditos por ciudadano", value: "5" }), vencimiento(), field("dnis", { label: "DNIs", tag: "textarea", attrs: { class: "form-control", rows: "5", cols: "40" }, help_text: "ayuda dnis" })], ...over,
});
const parametria = (over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}) => ({
  ...base, titulo: "Nueva parametría de voucher",
  fields: [
    field("nombre", { label: "Nombre" }), field("descripcion", { label: "Descripción", tag: "textarea", attrs: { class: "form-control", rows: "2", cols: "40" } }), select2("programa", "Programa"),
    field("cantidad_inicial", { label: "Créditos por ciudadano" }), vencimiento(),
    field("renovacion_mensual", { label: "Renovación mensual", attrs: { class: "form-check-input", type: "checkbox" }, value: false, help_text: "Si está activo" }),
    field("cantidad_renovacion", { label: "Créditos en cada renovación", help_text: "Dejar vacío" }),
    field("renovacion_tipo", { label: "Tipo de renovación", tag: "radio", attrs: {}, value: "suma", choices: [{ value: "suma", label: "Sumar al saldo existente", id: "id_renovacion_tipo_0" }, { value: "reinicia", label: "Reiniciar al valor configurado", id: "id_renovacion_tipo_1" }] }),
    field("inscripcion_unica_activa", { label: "Inscripción única activa", attrs: { class: "form-check-input", type: "checkbox" }, value: false, help_text: "Solo una" }),
  ].map((f) => ({ ...f, ...(fieldOver[f.name] ?? {}) })), ...over,
});

const pageForm = () => Array.from(document.querySelectorAll("form")).find((f) => f.querySelector("button.btn-primary"))!;

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

describe("VAT vouchers form routes", () => {
  it("own the three form paths only", () => {
    for (const p of ["/vat/vouchers/asignar/", "/vat/vouchers/asignar-masivo/", "/vat/vouchers/parametrias/nueva/"]) expect(findRoute(p)?.route.name).toBe("vat-vouchers-form");
    for (const p of ["/vat/vouchers/asignar", "/vat/vouchers/parametrias/4/", "/vat/vouchers/4/recargar/"]) expect(findRoute(p)?.route.name).not.toBe("vat-vouchers-form");
  });

  it("renders the asignar form with the initial citizen and posts the whitelisted fields", async () => {
    serve(asignar());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/vouchers/9/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/vouchers/asignar/?ciudadano=3");
    expect((await screen.findAllByRole("heading", { name: "Asignar Voucher" })).length).toBe(2);
    expect(webGet).toHaveBeenCalledWith(`${API}asignar/?ciudadano=3`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Asignar Voucher"));
    expect((document.querySelector("select[name=ciudadano]") as HTMLSelectElement).value).toBe("3");
    expect(pageForm().noValidate).toBe(false);
    fireEvent.submit(pageForm());
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/vouchers/9/"));
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams)).toEqual({ ciudadano: "3", programa: "", cantidad_inicial: "10", fecha_vencimiento: "2027-01-01" });
  });

  it("joins the errors of a field with a comma after a rejected post and keeps the toast message", async () => {
    serve(asignar());
    const rechazado = asignar({ messages: [{ message: "Error al crear el voucher: boom", level: "error" }],
      fields: asignar().fields.map((f) => (f.name === "cantidad_inicial" ? { ...f, errors: ["uno", "dos"] } : f)) });
    webPost.mockRejectedValue({ response: { status: 400, data: rechazado } });
    setup("/vat/vouchers/asignar/");
    await screen.findByRole("button", { name: /Asignar/ });
    fireEvent.submit(pageForm());
    expect(await screen.findByText("uno, dos")).toBeTruthy();
    expect(await screen.findByText("Error al crear el voucher: boom")).toBeTruthy();
  });

  it("shows the masivo result cards and keeps the form after processing", async () => {
    serve(masivo());
    const resultado = { creados: ["111"], ya_tenia: ["222", "333"], no_encontrados: [], errores: [] };
    webPost.mockResolvedValue({ status: 200, data: masivo({ resultado }) });
    setup("/vat/vouchers/asignar-masivo/");
    expect(await screen.findByRole("button", { name: /Procesar/ })).toBeTruthy();
    expect(screen.queryByText("Resultado")).toBeNull();
    fireEvent.change(document.querySelector("textarea[name=dnis]")!, { target: { value: "111 222" } });
    fireEvent.submit(pageForm());
    expect(await screen.findByText("Resultado")).toBeTruthy();
    expect(screen.getByText("Asignados (1)")).toBeTruthy();
    expect(screen.getByText("Ya tenían voucher activo (2)")).toBeTruthy();
    expect(screen.queryByText(/DNIs no encontrados \(/)).toBeNull();
    expect(screen.getByText("222, 333")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Ver todos los vouchers/ }).getAttribute("href")).toBe("/vat/vouchers/");
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams).dnis).toBe("111 222");
  });

  it("renders the parametria layout, posts checkbox and radio and navigates", async () => {
    serve(parametria());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/vouchers/parametrias/7/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/vouchers/parametrias/nueva/");
    expect(await screen.findByRole("heading", { level: 1, name: /Nueva parametría de voucher/ })).toBeTruthy();
    expect(screen.getByText("Identificación")).toBeTruthy();
    expect(screen.getByText("Si está activo")).toBeTruthy();
    expect(screen.getByText("Usá este campo para aclarar alcance, público objetivo o criterios especiales.")).toBeTruthy();
    fireEvent.click(screen.getByLabelText("Renovación mensual"));
    fireEvent.click(screen.getByLabelText("Reiniciar al valor configurado"));
    fireEvent.change(screen.getByLabelText(/^Nombre/), { target: { value: "P" } });
    fireEvent.submit(pageForm());
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/vouchers/parametrias/7/"));
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams)).toMatchObject({ nombre: "P", renovacion_mensual: "on", renovacion_tipo: "reinicia" });
    expect(Object.keys(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams))).not.toContain("inscripcion_unica_activa");
  });

  it("does not resend after an unconfirmed result", async () => {
    serve(parametria());
    webPost.mockRejectedValue(new Error("network"));
    setup("/vat/vouchers/parametrias/nueva/");
    await screen.findByRole("button", { name: /Guardar parametría/ });
    fireEvent.submit(pageForm());
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.submit(pageForm());
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("validates the payload shapes", () => {
    expect(asignarValid(asignar())).toBe(true);
    expect(masivoValid(masivo({ resultado: { creados: [], ya_tenia: [], no_encontrados: [], errores: [] } }))).toBe(true);
    expect(masivoValid(masivo({ resultado: { creados: [1] } }))).toBe(false);
    expect(parametriaValid(parametria())).toBe(true);
    expect(parametriaValid({ ...parametria(), fields: [] })).toBe(false);
  });
});
