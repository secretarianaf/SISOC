import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const centro = { id: 4, nombre: "CDI Sintético", url: "/centrodeinfancia/detalle/4" };
const field = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, label, required: true, disabled: false, widget: "text", help_text: "", value: "", attrs: {}, renaper: false, errors: [], choices: null, ...over,
});
const renaper = (over: Record<string, unknown> = {}) => ({
  bloque: "usuario_cdi", url: "/centrodeinfancia/ajax/renaper/usuario_cdi/", modo: "dni", campos: ["dni", "last_name", "first_name", "cuil"],
  tipo_field: "", tipos_con_dni: ["dni_permanente", "dni_temporario", "naturalizacion"], verificado: false, permite_cambiar: true, opcional: false, token: "", ...over,
});
const fields = (over: Record<string, Record<string, unknown>> = {}) => [
  field("dni", "DNI", { attrs: { inputmode: "numeric", maxlength: "16" }, ...over.dni }),
  field("first_name", "Nombre", { attrs: { maxlength: "150" }, ...over.first_name }),
  field("last_name", "Apellido", { attrs: { maxlength: "150" }, ...over.last_name }),
  field("cuil", "CUIL", { attrs: { inputmode: "numeric", maxlength: "16" }, ...over.cuil }),
  field("email", "Email", { widget: "email", help_text: "Se usará para enviarle las credenciales. Si otra cuenta ya usa este email, el usuario será el DNI.", ...over.email }),
];
const form = (over: Record<string, unknown> = {}) => ({
  centro, usuarios_restantes: 3, fields: fields(), non_field_errors: [], renaper: renaper(), urls: { cancelar: centro.url }, messages: [], ...over,
});
const result = (over: Record<string, unknown> = {}) => ({
  ok: true, centro, usuario: { username: "lperez", email: "luis@example.com" }, password: "Tmp-Secreta-9", email_enviado: true,
  puede_generar_otro: true, urls: { generar: "/centrodeinfancia/4/generar-usuario/" },
  messages: [{ message: "Usuario «lperez» creado correctamente.", level: "success" }], ...over,
});
const valores = { dni: 28456789, last_name: "Pérez", first_name: "Luis", cuil: "20284567898" };

function serve(data: unknown, lookup?: unknown, lookupStatus = 200) {
  webGet.mockImplementation((url: string) => {
    if (url === "web/session/") return Promise.resolve({ data: readyContext, status: 200 });
    if (url.startsWith("web/cdi/renaper/")) return Promise.resolve({ data: lookup, status: lookupStatus });
    return Promise.resolve({ data, status: 200 });
  });
}
const setup = () => {
  window.history.replaceState({}, "", "/centrodeinfancia/4/generar-usuario/");
  return render(<App />);
};
const input = (name: string) => document.getElementById(`id_${name}`) as HTMLInputElement;
const col = (name: string) => input(name).closest("[class*='col-']") as HTMLElement;
const type = (name: string, value: string) => fireEvent.change(input(name), { target: { value } });
const block = () => document.querySelector("[data-renaper-bloque]") as HTMLElement;
const panel = (name: string) => block().querySelector(`[data-renaper-panel='${name}']`) as HTMLElement;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  window.localStorage.clear();
  window.sessionStorage.clear();
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("CDI generar usuario route", () => {
  it("owns only the native path", () => {
    expect(findRoute("/centrodeinfancia/4/generar-usuario/")?.params).toEqual({ pk: "4" });
    for (const other of ["/centrodeinfancia/4/generar-usuario", "/centrodeinfancia/x/generar-usuario/", "/centrodeinfancia/detalle/4/"]) {
      expect(findRoute(other)?.route.name).toBe("business");
    }
  });

  it("renders the native card and starts the RENAPER block asking only for the DNI", async () => {
    serve(form());
    setup();
    await screen.findByText("Generar usuario referente para:", { exact: false });
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/4/usuarios/generar/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Generar usuario - Centro de Desarrollo Infantil"));
    expect(screen.getByRole("link", { name: "CDI Sintético" }).getAttribute("href")).toBe("/centrodeinfancia/detalle/4");
    expect(document.querySelector(".card-body p.text-muted")?.textContent).toBe(
      "Se creará un usuario con el rol CDI - Referente centro (no editable) asociado a este centro. Cupo restante: 3.");
    expect(block().dataset.renaperModo).toBe("dni");
    expect(panel("dni").hidden).toBe(false);
    expect(panel("manual").hidden).toBe(true);
    expect(panel("verificado").hidden).toBe(true);
    expect(col("dni").hidden).toBe(false);
    for (const name of ["first_name", "last_name", "cuil", "email"]) expect(col(name).hidden).toBe(true);
    expect(screen.getByText("Ingresá el DNI y validalo con RENAPER: los datos de identidad se completan solos.")).toBeTruthy();
    expect((block().querySelector("[data-renaper-manual]") as HTMLElement).hidden).toBe(true);
    expect(screen.getByRole("button", { name: "Generar usuario" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/centrodeinfancia/detalle/4");
  });

  it("validates a lookup: locks the identity, shows the card and keeps the email editable", async () => {
    serve(form(), { success: true, message: "Datos obtenidos desde RENAPER.", valores, token: "signed-token" });
    setup();
    await screen.findByLabelText(/DNI/);
    type("dni", "28.456.789");
    fireEvent.click(screen.getAllByRole("button", { name: "Validar con RENAPER" })[0]);
    await waitFor(() => expect(block().dataset.renaperModo).toBe("verificado"));
    expect(webGet).toHaveBeenCalledWith("web/cdi/renaper/usuario_cdi/", expect.objectContaining({ params: { dni: "28456789" } }));
    expect(panel("verificado").hidden).toBe(false);
    expect(input("first_name").readOnly).toBe(true);
    expect(input("first_name").value).toBe("Luis");
    expect(input("cuil").value).toBe("20284567898");
    // Locked columns hide (the card shows them); the email column is the one left to complete.
    for (const name of ["dni", "first_name", "last_name", "cuil"]) expect(col(name).hidden).toBe(true);
    expect(col("email").hidden).toBe(false);
    const card = Array.from(block().querySelectorAll("[data-renaper-datos] > div")).map((d) => d.textContent);
    expect(card).toEqual(["DNI28456789", "ApellidoPérez", "NombreLuis", "CUIL20-28456789-8"]);
    expect((block().querySelector("input[name='renaper_token_usuario_cdi']") as HTMLInputElement).value).toBe("signed-token");
  });

  it("asks for a 7 or 8 digit DNI and does not call RENAPER otherwise", async () => {
    serve(form());
    setup();
    await screen.findByLabelText(/DNI/);
    type("dni", "123");
    fireEvent.click(screen.getAllByRole("button", { name: "Validar con RENAPER" })[0]);
    expect(await screen.findByText("Ingresá un DNI de 7 u 8 dígitos.")).toBeTruthy();
    expect(webGet.mock.calls.some(([url]) => String(url).startsWith("web/cdi/renaper/"))).toBe(false);
    expect(document.activeElement).toBe(input("dni"));
  });

  it("offers the manual load after a failed lookup and discards nothing it did not lock", async () => {
    serve(form(), { success: false, message: "No se encontraron datos en RENAPER." }, 400);
    setup();
    await screen.findByLabelText(/DNI/);
    type("dni", "28456789");
    fireEvent.click(screen.getAllByRole("button", { name: "Validar con RENAPER" })[0]);
    const mensaje = await screen.findByText("No se encontraron datos en RENAPER.");
    expect((mensaje as HTMLElement).style.color).toBe("rgb(248, 113, 113)");
    const manual = screen.getByRole("button", { name: "Cargar manualmente" });
    fireEvent.click(manual);
    expect(block().dataset.renaperModo).toBe("manual");
    expect(panel("manual").hidden).toBe(false);
    for (const name of ["dni", "first_name", "last_name", "cuil", "email"]) expect(col(name).hidden).toBe(false);
    expect(input("first_name").readOnly).toBe(false);
  });

  it("keeps a refusal of the lookup (auditor veto) as a failed request, never as data", async () => {
    serve(form(), { detail: "El rol Auditoría tiene acceso de solo lectura." }, 403);
    setup();
    await screen.findByLabelText(/DNI/);
    type("dni", "28456789");
    fireEvent.click(screen.getAllByRole("button", { name: "Validar con RENAPER" })[0]);
    expect(await screen.findByText("No se pudo consultar RENAPER. Intentá de nuevo.")).toBeTruthy();
    expect(block().dataset.renaperModo).toBe("dni");
    expect(input("first_name").readOnly).toBe(false);
  });

  it("validates with Enter in the DNI instead of submitting the form", async () => {
    serve(form(), { success: true, message: "ok", valores, token: "t" });
    setup();
    await screen.findByLabelText(/DNI/);
    type("dni", "28456789");
    fireEvent.keyDown(input("dni"), { key: "Enter" });
    await waitFor(() => expect(block().dataset.renaperModo).toBe("verificado"));
    expect(webPost).not.toHaveBeenCalled();
  });

  it("switches the person of a verified ficha with Cambiar persona and Cancelar restores it", async () => {
    const locked = { disabled: true, renaper: true, value: "30123456" };
    serve(form({
      fields: fields({ dni: locked, first_name: { ...locked, value: "Ana" }, last_name: { ...locked, value: "Gómez" }, cuil: { ...locked, value: "27301234568" } }),
      renaper: renaper({ modo: "verificado", verificado: true }),
    }));
    setup();
    await screen.findByText("Verificado por RENAPER");
    expect(input("first_name").disabled).toBe(true);
    expect(input("first_name").getAttribute("data-renaper")).toBe("1");
    expect(col("email").hidden).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Cambiar persona" }));
    expect(block().dataset.renaperModo).toBe("dni");
    expect(input("dni").value).toBe("");
    expect(input("dni").disabled).toBe(false);
    expect(screen.getByText("Ingresá el DNI de la nueva persona y validalo con RENAPER.")).toBeTruthy();
    expect((block().querySelector("[data-renaper-cancelar]") as HTMLElement).hidden).toBe(false);
    // The manual option is never offered for a person the ficha already verified.
    type("dni", "28456789");
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { success: false, message: "No existe." }, status: 400 }));
    fireEvent.click(screen.getAllByRole("button", { name: "Validar con RENAPER" })[0]);
    await screen.findByText("No existe.");
    expect((block().querySelector("[data-renaper-manual]") as HTMLElement).hidden).toBe(true);
    fireEvent.click(block().querySelector("[data-renaper-cancelar]") as HTMLElement);
    expect(block().dataset.renaperModo).toBe("verificado");
    expect(input("dni").value).toBe("30123456");
  });

  it("tells the block when a required field of a hidden column blocks the submit", async () => {
    serve(form());
    setup();
    await screen.findByLabelText(/DNI/);
    const email = input("email");
    act(() => { email.dispatchEvent(new Event("invalid", { bubbles: false, cancelable: true })); });
    expect(await screen.findByText("Falta completar esta persona: validá el DNI con RENAPER.")).toBeTruthy();
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
    expect(document.activeElement).toBe(input("dni"));
  });
});

describe("CDI generar usuario submit", () => {
  async function verified() {
    serve(form(), { success: true, message: "ok", valores, token: "signed-token" });
    setup();
    await screen.findByLabelText(/DNI/);
    type("dni", "28456789");
    fireEvent.click(screen.getAllByRole("button", { name: "Validar con RENAPER" })[0]);
    await waitFor(() => expect(block().dataset.renaperModo).toBe("verificado"));
    type("email", "luis@example.com");
  }

  it("posts URL-encoded once with the token, shows the result and never stores the password", async () => {
    await verified();
    let resolve: (v: unknown) => void = () => undefined;
    webPost.mockReturnValue(new Promise((r) => { resolve = r; }));
    const button = screen.getByRole("button", { name: "Generar usuario" });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(webPost).toHaveBeenCalledTimes(1);
    const [endpoint, body] = webPost.mock.calls[0];
    expect(endpoint).toBe("web/cdi/centros/4/usuarios/generar/");
    expect(body).toBeInstanceOf(URLSearchParams);
    expect(Object.fromEntries(body)).toEqual({
      csrfmiddlewaretoken: "synthetic-csrf-token", dni: "28456789", first_name: "Luis", last_name: "Pérez", cuil: "20284567898",
      email: "luis@example.com", renaper_token_usuario_cdi: "signed-token",
    });
    await act(async () => { resolve({ data: result(), status: 200 }); });
    expect(await screen.findByText("Usuario generado para:", { exact: false })).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Usuario generado - Centro de Desarrollo Infantil"));
    expect((screen.getByLabelText("Contraseña temporal") as HTMLInputElement).value).toBe("Tmp-Secreta-9");
    expect((screen.getByLabelText("Contraseña temporal") as HTMLInputElement).readOnly).toBe(true);
    expect((screen.getByLabelText("Usuario") as HTMLInputElement).value).toBe("lperez");
    expect(screen.getByText("Se envió un correo con las credenciales a", { exact: false }).textContent).toBe(
      "Se envió un correo con las credenciales a luis@example.com.");
    expect(screen.getByText("Esta contraseña temporal también queda visible en la edición del usuario hasta su primer cambio. Cópiela ahora.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Generar otro" }).getAttribute("href")).toBe("/centrodeinfancia/4/generar-usuario/");
    expect(await screen.findByText("Usuario «lperez» creado correctamente.")).toBeTruthy();
    // The password is exposed only where the native page shows it: not in storage, URL or history.
    for (const store of [window.localStorage, window.sessionStorage]) expect(JSON.stringify({ ...store })).not.toContain("Tmp-Secreta-9");
    expect(window.location.href).not.toContain("Tmp-Secreta-9");
    expect(JSON.stringify(window.history.state)).not.toContain("Tmp-Secreta-9");
    // Only the one GET per mount ran: the result is not re-fetched and nothing repeats the secret.
    expect(webGet.mock.calls.filter(([url]) => String(url).startsWith("web/cdi/centros/"))).toHaveLength(1);
  });

  it("shows the native warning when the mail could not be sent and hides Generar otro without cupo", async () => {
    await verified();
    webPost.mockResolvedValue({ data: result({ email_enviado: false, puede_generar_otro: false }), status: 200 });
    fireEvent.click(screen.getByRole("button", { name: "Generar usuario" }));
    expect(await screen.findByText("No se pudo enviar el correo de credenciales. Entregue estos datos al referente de forma segura.")).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Generar otro" })).toBeNull();
  });

  it("re-renders the rejected form with its errors, starts at the top and sends nothing again", async () => {
    await verified();
    const rejected = form({
      fields: fields({ email: { errors: [{ message: "Introduzca una dirección de correo electrónico válida.", code: "invalid" }], value: "luis@" } }),
      renaper: renaper({ modo: "verificado", verificado: true, token: "signed-token" }),
      messages: [],
    });
    webPost.mockResolvedValue({ data: rejected, status: 400 });
    fireEvent.click(screen.getByRole("button", { name: "Generar usuario" }));
    expect(await screen.findByText("Introduzca una dirección de correo electrónico válida.")).toBeTruthy();
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
    expect(input("email").className).toBe("form-control emailinput is-invalid");
    expect(input("email").getAttribute("aria-describedby")).toBe("id_email_helptext id_email_error");
    expect(input("email").value).toBe("luis@");
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(screen.queryByLabelText("Contraseña temporal")).toBeNull();
  });

  it("reports an unconfirmed outcome without resubmitting", async () => {
    await verified();
    webPost.mockRejectedValue(new Error("network"));
    fireEvent.click(screen.getByRole("button", { name: "Generar usuario" }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "No se pudo confirmar el resultado. Recargue la página antes de reintentar.");
    expect((screen.getByRole("button", { name: "Generar usuario" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Generar usuario" }));
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("answers a refused POST with the access error, not the result", async () => {
    await verified();
    webPost.mockResolvedValue({ data: { detail: "No tiene permisos para esta acción." }, status: 403 });
    fireEvent.click(screen.getByRole("button", { name: "Generar usuario" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Generar usuario" })).toBeNull());
    expect(screen.queryByLabelText("Contraseña temporal")).toBeNull();
  });
});
