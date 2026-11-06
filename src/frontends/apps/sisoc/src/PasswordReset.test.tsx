import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import PasswordReset from "./PasswordReset";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: () => ({ get, post }),
  leerCookie: () => "synthetic-csrf-token",
  SinPermiso: class SinPermiso extends Error {},
}));

const requestMetadata = {
  fields: [
    { name: "username", label: "Usuario", type: "text", required: true, attrs: { id: "id_username", maxlength: "150" } },
    { name: "email", label: "Email", type: "email", required: true, attrs: { id: "id_email", autocomplete: "email", maxlength: "254" } },
  ],
  footer_version_label: "v-sintetica",
};
const confirmMetadata = {
  validlink: true,
  fields: [
    { name: "new_password1", label: "Contraseña nueva", required: true, help_text: "<ul><li>Su contraseña debe contener por lo menos 8 caracteres.</li><li>Su contraseña no puede estar formada exclusivamente por números.</li></ul>", attrs: { id: "id_new_password1", autocomplete: "new-password", "aria-describedby": "id_new_password1_helptext" } },
    { name: "new_password2", label: "Confirmación de contraseña nueva", required: true, help_text: "Introduzca la misma contraseña nuevamente, para poder verificar la misma.", attrs: { id: "id_new_password2", autocomplete: "new-password", "aria-describedby": "id_new_password2_helptext" } },
  ],
};
const TOKEN = "synthetic-reset-token";
const navigate = vi.fn();
const input = (name: string) => document.querySelector<HTMLInputElement>(`[name=${name}]`)!;
const type = (name: string, value: string) => fireEvent.change(input(name), { target: { value } });
const card = () => document.querySelector(".password-reset-content")!;

beforeEach(() => {
  vi.resetAllMocks();
  get.mockImplementation((url: string) => Promise.resolve({ data: url === "web/password/reset/" ? requestMetadata : confirmMetadata }));
});
afterEach(() => { cleanup(); });

describe("Password recovery request", () => {
  it("renders the source crispy form, frame, title and footer from the real Form metadata", async () => {
    render(<PasswordReset mode="request" navigate={navigate} />);
    expect(await screen.findByLabelText(/Usuario/)).toBeDefined();
    expect(document.title).toBe("Recuperar contraseña");
    expect(document.body.className).toBe("password-reset-page");
    expect(card().querySelector("h5")!.textContent).toBe("Recuperar contraseña");
    expect(card().querySelector("p.text-muted")!.textContent).toBe("Ingresá tu usuario y el correo registrado. Ambos deben coincidir con los datos de tu cuenta.");
    const username = input("username");
    expect(username.className).toBe("textinput form-control");
    expect(username.maxLength).toBe(150);
    expect(input("email").className).toBe("emailinput form-control");
    expect(input("email").type).toBe("email");
    expect(input("email").autocomplete).toBe("email");
    expect(document.querySelector("label[for=id_email]")!.innerHTML).toBe('Email<span class="asteriskField">*</span>');
    expect(document.querySelector("#div_id_username.mb-3")).not.toBeNull();
    expect(screen.getByRole("link", { name: "Volver al login" }).getAttribute("href")).toBe("/login/");
    expect(screen.getByRole("button", { name: "Enviar enlace" }).className).toBe("btn btn-primary");
    expect(document.querySelector(".app-footer a")!.textContent).toBe("v-sintetica");
    expect(get.mock.calls.map(([url]) => url)).toEqual(["web/password/reset/"]);
    expect(post).not.toHaveBeenCalled();
  });

  it("posts only username and email URL-encoded and follows only the source done page", async () => {
    post.mockResolvedValue({ data: { ok: true, redirect: "/password_reset/done/" } });
    render(<PasswordReset mode="request" navigate={navigate} />);
    await screen.findByLabelText(/Usuario/);
    type("username", " persona ");
    type("email", "persona@example.invalid");
    fireEvent.click(screen.getByRole("button", { name: "Enviar enlace" }));
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith("/password_reset/done/"));
    expect(post).toHaveBeenCalledOnce();
    const [endpoint, body, config] = post.mock.calls[0];
    expect(endpoint).toBe("web/password/reset/");
    expect(body).toBeInstanceOf(URLSearchParams);
    expect([...body.entries()]).toEqual([["username", " persona "], ["email", "persona@example.invalid"]]);
    expect(config.headers["Content-Type"]).toBe("application/x-www-form-urlencoded");
  });

  it("shows source field errors with crispy ids and keeps the entered values", async () => {
    post.mockRejectedValue({ response: { status: 400, data: { errors: {
      username: [{ message: "Este campo es requerido.", code: "required" }],
      email: [{ message: "Introduzca una dirección de correo electrónico válida.", code: "invalid" }],
    } } } });
    render(<PasswordReset mode="request" navigate={navigate} />);
    await screen.findByLabelText(/Usuario/);
    type("email", "x");
    fireEvent.click(screen.getByRole("button", { name: "Enviar enlace" }));
    expect(await screen.findByText("Este campo es requerido.")).toBeDefined();
    const email = input("email");
    expect(email.value).toBe("x");
    expect(email.className).toBe("emailinput form-control is-invalid");
    expect(email.getAttribute("aria-invalid")).toBe("true");
    expect(email.getAttribute("aria-describedby")).toBe("id_email_error");
    expect(document.querySelector("#id_email_error.invalid-feedback > p#error_1_id_email > strong")!.textContent)
      .toBe("Introduzca una dirección de correo electrónico válida.");
    expect(navigate).not.toHaveBeenCalled();
    expect(screen.getByRole<HTMLButtonElement>("button", { name: "Enviar enlace" }).disabled).toBe(false);
  });

  it("blocks duplicate and retried submits after an uncertain or rejected outcome", async () => {
    let reject!: (value: unknown) => void;
    post.mockReturnValue(new Promise((_resolve, fail) => { reject = fail; }));
    render(<PasswordReset mode="request" navigate={navigate} />);
    const button = await screen.findByRole<HTMLButtonElement>("button", { name: "Enviar enlace" });
    fireEvent.click(button); fireEvent.click(button);
    expect(post).toHaveBeenCalledOnce();
    await act(async () => reject(new Error("unknown outcome")));
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudo confirmar el resultado.");
    expect(button.disabled).toBe(true);
    fireEvent.click(button);
    expect(post).toHaveBeenCalledOnce();
    cleanup();
    post.mockResolvedValue({ data: { ok: true, redirect: "https://example.invalid/password_reset/done/" } });
    render(<PasswordReset mode="request" navigate={navigate} />);
    fireEvent.click(await screen.findByRole("button", { name: "Enviar enlace" }));
    expect(await screen.findByRole("alert")).toBeDefined();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("disables the form after a CSRF rejection", async () => {
    post.mockRejectedValue({ response: { status: 403 } });
    render(<PasswordReset mode="request" navigate={navigate} />);
    fireEvent.click(await screen.findByRole("button", { name: "Enviar enlace" }));
    expect((await screen.findByRole("alert")).textContent).toContain("La solicitud fue rechazada.");
    expect(screen.getByRole<HTMLButtonElement>("button", { name: "Enviar enlace" }).disabled).toBe(true);
  });
});

describe("Password recovery static pages", () => {
  it.each([
    ["done", "Correo enviado", "Solicitud recibida", "Si los datos son correctos, recibirás un enlace de recuperación al correo registrado."],
    ["complete", "Contraseña actualizada", "Contraseña actualizada", "Ya puedes ingresar con tu nueva contraseña."],
  ] as const)("renders the source %s page with only the login return", async (mode, title, heading, text) => {
    render(<PasswordReset mode={mode} navigate={navigate} />);
    expect(card().querySelector("h5")!.textContent).toBe(heading);
    expect(card().querySelector("p.text-muted")!.textContent).toBe(text);
    expect(document.title).toBe(title);
    const login = screen.getByRole("link", { name: "Volver al login" });
    expect(login.className).toBe("btn password-reset-login-btn");
    expect(login.getAttribute("href")).toBe("/login/");
    expect(card().querySelector("form")).toBeNull();
    await vi.waitFor(() => expect(document.querySelector(".app-footer a")!.textContent).toBe("v-sintetica"));
    expect(get.mock.calls.map(([url]) => url)).toEqual(["web/password/reset/"]);
    expect(post).not.toHaveBeenCalled();
  });
});

describe("Password recovery confirmation", () => {
  it("shows the source invalid-link state for a token path without sending the token anywhere", async () => {
    window.history.replaceState({}, "", `/reset/MQ/${TOKEN}/`);
    render(<PasswordReset mode="confirm" uidb64={null} navigate={navigate} />);
    expect(card().querySelector("p.text-danger")!.textContent).toBe("El enlace no es válido o expiró. Solicita uno nuevo.");
    const link = screen.getByRole("link", { name: "Solicitar nuevo enlace" });
    expect(link.className).toBe("btn btn-primary");
    expect(link.getAttribute("href")).toBe("/password_reset/");
    expect(document.title).toBe("Restablecer contraseña");
    expect(card().querySelector("form")).toBeNull();
    await vi.waitFor(() => expect(get).toHaveBeenCalled());
    expect(get.mock.calls.map(([url]) => url)).toEqual(["web/password/reset/"]);
    expect(JSON.stringify(get.mock.calls)).not.toContain(TOKEN);
    window.history.replaceState({}, "", "/");
  });

  it("renders the source set-password form from the session-validated link", async () => {
    render(<PasswordReset mode="confirm" uidb64="MQ" navigate={navigate} />);
    expect(await screen.findByLabelText(/Contraseña nueva/)).toBeDefined();
    expect(get.mock.calls.map(([url]) => url).sort()).toEqual(["web/password/reset/", "web/password/reset/MQ/"]);
    const first = input("new_password1");
    expect(first.className).toBe("passwordinput form-control");
    expect(first.type).toBe("password");
    expect(first.autocomplete).toBe("new-password");
    expect(first.getAttribute("aria-describedby")).toBe("id_new_password1_helptext");
    expect([...document.querySelectorAll("#id_new_password1_helptext.form-text li")].map((item) => item.textContent)).toEqual([
      "Su contraseña debe contener por lo menos 8 caracteres.",
      "Su contraseña no puede estar formada exclusivamente por números.",
    ]);
    expect(document.querySelector("#id_new_password2_helptext")!.textContent).toBe("Introduzca la misma contraseña nuevamente, para poder verificar la misma.");
    expect(screen.getByRole("button", { name: "Guardar contraseña" })).toBeDefined();
    expect(screen.queryByRole("link", { name: "Volver al login" })).toBeNull();
  });

  it("posts only the new passwords and follows only the source complete page", async () => {
    post.mockResolvedValue({ data: { ok: true, redirect: "/reset/done/" } });
    render(<PasswordReset mode="confirm" uidb64="MQ" navigate={navigate} />);
    await screen.findByLabelText(/Contraseña nueva/);
    type("new_password1", "Synthetic-Reset-482!");
    type("new_password2", "Synthetic-Reset-482!");
    fireEvent.click(screen.getByRole("button", { name: "Guardar contraseña" }));
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith("/reset/done/"));
    const [endpoint, body] = post.mock.calls[0];
    expect(endpoint).toBe("web/password/reset/MQ/");
    expect([...body.keys()]).toEqual(["new_password1", "new_password2"]);
  });

  it("clears rejected passwords and keeps errors before the helptext", async () => {
    post.mockRejectedValue({ response: { status: 400, data: { validlink: true, errors: {
      new_password2: [{ message: "La contraseña tiene un valor demasiado común.", code: "password_too_common" },
        { message: "La contraseña está formada completamente por dígitos.", code: "password_entirely_numeric" }],
    } } } });
    render(<PasswordReset mode="confirm" uidb64="MQ" navigate={navigate} />);
    await screen.findByLabelText(/Contraseña nueva/);
    type("new_password1", "12345678"); type("new_password2", "12345678");
    fireEvent.click(screen.getByRole("button", { name: "Guardar contraseña" }));
    expect(await screen.findByText("La contraseña tiene un valor demasiado común.")).toBeDefined();
    expect(input("new_password1").value).toBe("");
    expect(input("new_password2").value).toBe("");
    expect(input("new_password2").getAttribute("aria-describedby")).toBe("id_new_password2_helptext id_new_password2_error");
    const children = [...document.querySelector("#div_id_new_password2")!.children].map((child) => child.id || child.tagName);
    expect(children).toEqual(["LABEL", "id_new_password2", "id_new_password2_error", "id_new_password2_helptext"]);
    expect(document.querySelector("#error_2_id_new_password2")!.textContent).toBe("La contraseña está formada completamente por dígitos.");
  });

  it.each([["load", false], ["submit", true]])("shows the invalid-link state when the server revalidation fails on %s", async (_when, onSubmit) => {
    if (!onSubmit) get.mockImplementation((url: string) => Promise.resolve({ data: url === "web/password/reset/" ? requestMetadata : { validlink: false } }));
    post.mockResolvedValue({ data: { validlink: false } });
    render(<PasswordReset mode="confirm" uidb64="MQ" navigate={navigate} />);
    if (onSubmit) {
      await screen.findByLabelText(/Contraseña nueva/);
      type("new_password1", "Synthetic-Reset-482!");
      fireEvent.click(screen.getByRole("button", { name: "Guardar contraseña" }));
    }
    expect(await screen.findByRole("link", { name: "Solicitar nuevo enlace" })).toBeDefined();
    expect(card().querySelector("form")).toBeNull();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("never renders remote help HTML as markup", async () => {
    get.mockImplementation((url: string) => Promise.resolve({ data: url === "web/password/reset/" ? requestMetadata : {
      ...confirmMetadata,
      fields: [{ ...confirmMetadata.fields[0], help_text: '<img src=x onerror="alert(1)">Texto' }, confirmMetadata.fields[1]],
    } }));
    render(<PasswordReset mode="confirm" uidb64="MQ" navigate={navigate} />);
    await screen.findByLabelText(/Contraseña nueva/);
    expect(document.querySelector("#id_new_password1_helptext")!.innerHTML).toBe("Texto");
  });
});
