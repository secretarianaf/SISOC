import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { usuarioFormValid, usuarioGeneradoValid } from "./vatCentrosUsuario";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/centros-usuarios/";
const U = "/vat/centros/5/generar-usuario/";
const field = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label, tag: "input", help_text: "", value: "", choices: [], errors: [],
  attrs: { class: "form-control", type: name === "email" ? "email" : "text", required: "required", ...(name === "email" ? {} : { maxlength: "150" }) }, ...over,
});
const form = (over: Record<string, unknown> = {}, email: Record<string, unknown> = {}) => ({
  centro: { id: 5, nombre: "CFP 401", url: "/vat/centros/5/" }, usuarios_restantes: 9,
  fields: [field("first_name", "Nombre", { value: "Lia" }), field("last_name", "Apellido", { value: "Paz" }),
    field("email", "Email", { value: "lia@example.com", help_text: "Se usará como usuario y para enviarle las credenciales.", ...email })],
  non_field_errors: [], urls: { cancelar: "/vat/centros/5/", generar: U }, messages: [], ...over,
});
const generado = (over: Record<string, unknown> = {}) => ({
  ok: true, centro: { id: 5, nombre: "CFP 401", url: "/vat/centros/5/" }, usuario: { username: "ana@example.com", email: "ana@example.com" },
  password: "Tmp-secreta-123", email_enviado: true, puede_generar_otro: true, urls: { generar: U },
  messages: [{ message: "Usuario «ana@example.com» creado correctamente.", level: "success" }], ...over,
});

function setup(data: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
  window.history.replaceState({}, "", U);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT centro generar usuario route", () => {
  it("owns its path only", () => {
    expect(findRoute(U)?.route.name).toBe("vat-centros-usuario");
    for (const other of ["/vat/centros/5/generar-usuario", "/vat/centros/x/generar-usuario/", "/vat/centros/5/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-centros-usuario");
    }
  });

  it("renders the prefilled crispy form, the quota and the native links", async () => {
    setup(form());
    expect(await screen.findByRole("heading", { level: 3, name: "Generar usuario referente del Centro" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}5/generar/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Generar usuario - Centro VAT"));
    expect((screen.getByLabelText(/Nombre/) as HTMLInputElement).value).toBe("Lia");
    expect(screen.getByLabelText(/Nombre/).getAttribute("maxlength")).toBe("150");
    expect(screen.getByText(/Cupo restante/).querySelector("strong:last-child")?.textContent).toBe("9");
    expect(document.querySelector("label[for=id_first_name] .asteriskField")?.textContent).toBe("*");
    expect(screen.getByText("Se usará como usuario y para enviarle las credenciales.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "CFP 401" }).getAttribute("href")).toBe("/vat/centros/5/");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/vat/centros/5/");
  });

  it("shows the rejected form, then the credentials once, and never stores the password", async () => {
    setup(form());
    webPost.mockResolvedValueOnce({ status: 400, data: form({}, { value: "x", errors: ["Introduzca una dirección de correo electrónico válida."] }) });
    webPost.mockResolvedValueOnce({ status: 201, data: generado() });
    const storage = vi.spyOn(Storage.prototype, "setItem");
    fireEvent.click(await screen.findByRole("button", { name: "Generar usuario" }));
    expect(await screen.findByText("Introduzca una dirección de correo electrónico válida.")).toBeTruthy();
    expect(screen.getByLabelText(/Email/).className).toContain("is-invalid");
    fireEvent.change(screen.getByLabelText(/Email/), { target: { value: "ana@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Generar usuario" }));
    expect(await screen.findByDisplayValue("Tmp-secreta-123")).toBeTruthy();
    expect(Object.fromEntries(webPost.mock.calls[1][1] as URLSearchParams)).toEqual({
      csrfmiddlewaretoken: "synthetic-csrf-token", first_name: "Lia", last_name: "Paz", email: "ana@example.com",
    });
    expect(webPost.mock.calls[1][0]).toBe(`${API}5/generar/`);
    expect(screen.getByText("ana@example.com", { selector: "strong" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Generar otro" }).getAttribute("href")).toBe(U);
    expect(screen.getByRole("heading", { level: 3, name: "Usuario referente generado" })).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Usuario generado - Centro VAT"));
    expect(storage).not.toHaveBeenCalled();
    expect(window.location.pathname).toBe(U);
    expect(window.location.search + window.location.hash).toBe("");
  });

  it("warns when the email could not be sent and hides the generate-another link without quota", async () => {
    setup(form());
    webPost.mockResolvedValueOnce({ status: 201, data: generado({ email_enviado: false, puede_generar_otro: false }) });
    fireEvent.click(await screen.findByRole("button", { name: "Generar usuario" }));
    expect(await screen.findByText(/No se pudo enviar el correo de credenciales/)).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Generar otro" })).toBeNull();
  });

  it("never resubmits when the outcome is unknown", async () => {
    setup(form());
    webPost.mockRejectedValue({ response: { status: 500 } });
    fireEvent.click(await screen.findByRole("button", { name: "Generar usuario" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Generar usuario" }));
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("validates the payload shapes", () => {
    expect(usuarioFormValid(form())).toBe(true);
    expect(usuarioFormValid({ ...form(), fields: [] })).toBe(false);
    expect(usuarioFormValid({ ...form(), urls: {} })).toBe(false);
    expect(usuarioGeneradoValid(generado())).toBe(true);
    expect(usuarioGeneradoValid(generado({ password: 1 }))).toBe(false);
    expect(usuarioGeneradoValid({ ...generado(), ok: false })).toBe(false);
  });
});
