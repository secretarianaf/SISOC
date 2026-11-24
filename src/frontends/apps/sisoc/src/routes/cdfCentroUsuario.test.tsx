import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const URL_API = "web/cdf/centros/7/generar-usuario/";
const campo = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, label, required: true, disabled: false, widget: "text", help_text: "", value: "", attrs: { maxlength: "150" }, ...over,
});
const formulario = (over: Record<string, unknown> = {}) => ({
  centro: { id: 7, nombre: "CDF Siete" }, grupo: "CDF - Referente centro", usuarios_restantes: 4,
  initial: { first_name: "Lia" },
  fields: [
    campo("first_name", "Nombre", { value: "Lia" }),
    campo("last_name", "Apellido"),
    campo("email", "Email", { widget: "email", attrs: { maxlength: "320" }, help_text: "Se usará como usuario y para enviarle las credenciales." }),
  ],
  errors: {}, non_field_errors: [], messages: [],
  ...over,
});
const creado = (over: Record<string, unknown> = {}) => ({
  usuario: { username: "ana", email: "ana@example.com" }, password: "Temp-Sintetica-9", email_enviado: true,
  puede_generar_otro: true, message: "Usuario «ana» creado correctamente.", ...over,
});

function serve(page: unknown) {
  webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
    : url === URL_API ? Promise.resolve({ data: page, status: 200 }) : Promise.reject(new Error(url))));
}
function setup() {
  window.history.replaceState({}, "", "/centrodefamilia/centros/7/generar-usuario/");
  return render(<App />);
}
const input = (id: string) => document.getElementById(id) as HTMLInputElement;
async function enviar() {
  const boton = await screen.findByRole("button", { name: "Generar usuario" });
  fireEvent.change(input("id_last_name"), { target: { value: "Gómez" } });
  fireEvent.change(input("id_email"), { target: { value: "ana@example.com" } });
  fireEvent.click(boton);
  return boton as HTMLButtonElement;
}

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CDF referente user generation route", () => {
  it("owns only the native generation path", () => {
    expect(findRoute("/centrodefamilia/centros/7/generar-usuario/")?.params).toEqual({ id: "7" });
    expect(findRoute("/centrodefamilia/centros/7/generar-usuario/")?.route.name).toBe("cdf-centro-usuario");
    expect(findRoute("/centrodefamilia/centros/7/")?.route.name).toBe("cdf-centros");
    expect(findRoute("/centrodefamilia/centros/0/generar-usuario/")?.route.name).not.toBe("cdf-centro-usuario");
  });

  it("renders the native form with the preloaded values and texts", async () => {
    serve(formulario());
    setup();
    await screen.findByText("Generar usuario referente para:", { exact: false });
    await waitFor(() => expect(document.title).toBe("SISOC - Generar usuario - Centro de Familia"));
    expect(screen.getByRole("heading", { name: "Generar usuario referente del CDF" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "CDF Siete" }).getAttribute("href")).toBe("/centrodefamilia/centros/7/");
    expect(document.querySelector(".card-body p.text-muted")?.textContent).toBe(
      "Se creará un usuario con el rol CDF - Referente centro (no editable) asociado a este centro. Cupo restante: 4.");
    expect(input("id_first_name").value).toBe("Lia");
    expect(input("id_first_name").className).toBe("form-control textinput");
    expect(input("id_first_name").getAttribute("maxlength")).toBe("150");
    expect(input("id_email").type).toBe("email");
    expect(input("id_email").getAttribute("aria-describedby")).toBe("id_email_helptext");
    expect(document.getElementById("id_email_helptext")?.textContent).toBe("Se usará como usuario y para enviarle las credenciales.");
    expect(document.querySelector("label[for=id_last_name]")?.textContent).toBe("Apellido*");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/centrodefamilia/centros/7/");
    expect(webGet).toHaveBeenCalledWith(URL_API, expect.anything());
  });

  it("shows the field and service errors of a 400 without retrying", async () => {
    serve(formulario());
    webPost.mockResolvedValueOnce({ status: 400, data: formulario({
      fields: [campo("first_name", "Nombre"), campo("last_name", "Apellido", { value: "X" }),
        campo("email", "Email", { widget: "email", value: "mal", help_text: "Se usará como usuario y para enviarle las credenciales." })],
      errors: { first_name: [{ message: "Este campo es requerido.", code: "required" }] },
      non_field_errors: ["Se alcanzó el máximo de usuarios para este CDF."],
    }) });
    setup();
    await enviar();
    await waitFor(() => expect(document.getElementById("error_1_id_first_name")?.textContent).toBe("Este campo es requerido."));
    expect(input("id_first_name").className).toBe("form-control textinput is-invalid");
    expect(input("id_first_name").getAttribute("aria-invalid")).toBe("true");
    expect(input("id_last_name").value).toBe("X");
    expect(input("id_email").value).toBe("mal");
    expect(document.querySelector("ul.errorlist.nonfield li")?.textContent).toBe("Se alcanzó el máximo de usuarios para este CDF.");
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(URL_API);
    expect((body as FormData).get("csrfmiddlewaretoken")).toBe("synthetic-csrf-token");
    expect((body as FormData).get("first_name")).toBe("Lia");
    expect((body as FormData).get("email")).toBe("ana@example.com");
  });

  it("shows the CR1 credentials once in memory after a 201", async () => {
    serve(formulario());
    webPost.mockResolvedValueOnce({ status: 201, data: creado() });
    setup();
    await enviar();
    await waitFor(() => expect(input("cred-password")?.value).toBe("Temp-Sintetica-9"));
    await waitFor(() => expect(document.title).toBe("SISOC - Usuario generado - Centro de Familia"));
    expect(screen.getByRole("heading", { name: "Usuario referente generado" })).toBeTruthy();
    expect(document.querySelector(".text-success")?.textContent).toBe("Se envió un correo con las credenciales a ana@example.com.");
    expect(input("cred-usuario").value).toBe("ana");
    expect(input("cred-usuario").readOnly).toBe(true);
    expect(input("cred-email").value).toBe("ana@example.com");
    expect(input("cred-password").className).toBe("form-control fs-5");
    expect(screen.getByText("Usuario «ana» creado correctamente.")).toBeTruthy();
    expect(screen.getByText("Seleccione el texto del campo y cópielo (Ctrl+C) antes de salir.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Generar otro" }).getAttribute("href")).toBe("/centrodefamilia/centros/7/generar-usuario/");
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("warns when the email failed and hides «Generar otro» without quota", async () => {
    serve(formulario());
    webPost.mockResolvedValueOnce({ status: 201, data: creado({ email_enviado: false, puede_generar_otro: false }) });
    setup();
    await enviar();
    await waitFor(() => expect(document.querySelector(".text-warning")?.textContent).toBe(
      "No se pudo enviar el correo de credenciales. Entregue estos datos al referente de forma segura."));
    expect(screen.queryByRole("link", { name: "Generar otro" })).toBeNull();
  });

  it("shows the uncertain G1 text on a 504 and never repeats the POST", async () => {
    serve(formulario());
    webPost.mockResolvedValueOnce({ status: 504, data: { uncertain: true } });
    setup();
    const boton = await enviar();
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe(
      "No se pudo confirmar el resultado. Verificá el estado antes de reintentar."));
    expect(boton.disabled).toBe(true);
    fireEvent.click(boton);
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(document.getElementById("cred-password")).toBeNull();
  });

  it("keeps the native 403 and 404 of the API", async () => {
    webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
      : Promise.resolve({ data: { detail: "x" }, status: 404 })));
    setup();
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("No se encontró la página."));
    expect(webPost).not.toHaveBeenCalled();
  });
});
