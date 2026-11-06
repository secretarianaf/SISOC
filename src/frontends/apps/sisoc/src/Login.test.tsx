import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import Login from "./Login";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get, post })),
  leerCookie: vi.fn(() => "synthetic-csrf-fixture"),
  SinPermiso: class SinPermiso extends Error {},
}));
const metadata = {
  fields: [
    { name: "username", label: "Nombre de usuario", required: true, max_length: 150 },
    { name: "password", label: "Contraseña", required: true, max_length: null },
  ],
  initial: { username: "" }, errors: {}, footer_version_label: "Versiones",
};
beforeEach(() => { vi.resetAllMocks(); window.history.replaceState({}, "", "/login/"); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const submit = () => fireEvent.submit(document.querySelector("#form-login")!);

describe("ID-A standalone public login", () => {
  it("isolates standalone legacy styles and restores the business shell on unmount", async () => {
    get.mockResolvedValue({ data: metadata });
    const business = document.createElement("link");
    business.rel = "stylesheet"; business.href = "/static/dist/css/adminlte.css"; business.disabled = false;
    const legacy = document.createElement("link");
    legacy.rel = "stylesheet"; legacy.href = "/static/custom/css/main.css"; legacy.disabled = false;
    const alreadyDisabled = document.createElement("link");
    alreadyDisabled.rel = "stylesheet"; alreadyDisabled.href = "/static/custom/css/poncho.css"; alreadyDisabled.disabled = true;
    document.head.append(business, legacy, alreadyDisabled);
    const root = document.createElement("div"); root.id = "root"; root.style.display = "grid";
    document.body.append(root);
    try {
      const view = render(<Login navigate={vi.fn()} />, { container: root });
      await screen.findByRole("button", { name: "Ingresar" });
      expect(business.disabled).toBe(true); expect(legacy.disabled).toBe(false);
      expect(root.style.display).toBe("contents");
      view.unmount();
      expect(business.disabled).toBe(false); expect(alreadyDisabled.disabled).toBe(true);
      expect(legacy.disabled).toBe(false); expect(root.style.display).toBe("grid");
      expect(post).not.toHaveBeenCalled();
    } finally { business.remove(); legacy.remove(); alreadyDisabled.remove(); root.remove(); }
  });

  it("bootstraps the public form without fetching business session context", async () => {
    get.mockResolvedValue({ data: metadata });
    render(<Login navigate={vi.fn()} />);
    await screen.findByRole("button", { name: "Ingresar" });
    expect(get.mock.calls.map(([url]) => url)).toEqual(["web/login/"]);
    expect(screen.getByLabelText("Username")).toBeDefined();
    expect((screen.getByLabelText("Password") as HTMLInputElement).type).toBe("password");
    expect(screen.getByRole("link", { name: /Restablecela/ }).getAttribute("href")).toBe("/password_reset/");
    expect(screen.getByRole("button", { name: "Cerrar sesión" }).closest("form")?.getAttribute("action")).toBe("/logout/");
  });

  it("links the footer version to the native changelog route", async () => {
    get.mockResolvedValue({ data: metadata });
    render(<Login navigate={vi.fn()} />);
    await screen.findByRole("button", { name: "Ingresar" });
    expect(screen.getByRole("link", { name: "Versiones" }).getAttribute("href")).toBe("/novedades/");
  });

  it("normalizes only username, forwards next and navigates to the server-validated result", async () => {
    get.mockResolvedValue({ data: metadata });
    post.mockResolvedValue({ data: { ok: true, redirect: "/insumos/" } });
    window.history.replaceState({}, "", "/login/?next=%2Finsumos%2F");
    const navigate = vi.fn(); const password = ` ${crypto.randomUUID()} `;
    render(<Login navigate={navigate} />);
    await screen.findByRole("button", { name: "Ingresar" });
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "  synthetic  " } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
    submit();
    await waitFor(() => expect(navigate).toHaveBeenCalledWith("/insumos/"));
    const [url, body, config] = post.mock.calls[0];
    expect(url).toBe("web/login/"); expect(body).toBeInstanceOf(URLSearchParams);
    expect(body.get("username")).toBe("synthetic");
    expect(body.get("password") === password).toBe(true);
    expect(body.get("next")).toBe("/insumos/");
    expect(config.headers["Content-Type"]).toBe("application/x-www-form-urlencoded");
  });

  it("preserves normalized username but clears password after source validation errors", async () => {
    get.mockResolvedValue({ data: metadata });
    post.mockRejectedValue({ response: { status: 400, data: { errors: { __all__: [{ message: "Usuario o contraseña inválidos.", code: "invalid_login" }] }, initial: { username: "synthetic" } } } });
    render(<Login navigate={vi.fn()} />);
    await screen.findByRole("button", { name: "Ingresar" });
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: " synthetic " } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: crypto.randomUUID() } });
    submit(); await screen.findByText("Usuario o contraseña inválidos.");
    expect((screen.getByLabelText("Username") as HTMLInputElement).value).toBe("synthetic");
    expect((screen.getByLabelText("Password") as HTMLInputElement).value).toBe("");
    expect(screen.getByLabelText("Password").getAttribute("aria-describedby")).toBe("login-error");
    expect(post).toHaveBeenCalledOnce();
  });

  it("places backend required errors by their existing controls", async () => {
    get.mockResolvedValue({ data: metadata });
    post.mockRejectedValue({ response: { status: 400, data: { errors: { username: [{ message: "Este campo es obligatorio.", code: "required" }], password: [{ message: "Este campo es obligatorio.", code: "required" }] }, initial: { username: "" } } } });
    render(<Login navigate={vi.fn()} />);
    const button = await screen.findByRole("button", { name: "Ingresar" });
    button.focus();
    submit();
    await screen.findAllByText("Este campo es obligatorio.");
    expect(screen.getByLabelText("Username").classList.contains("is-invalid")).toBe(true);
    expect(screen.getByLabelText("Password").classList.contains("is-invalid")).toBe(true);
    await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText("Username")));
    expect(post).toHaveBeenCalledOnce();
  });

  it("does not submit twice or retry an uncertain result", async () => {
    get.mockResolvedValue({ data: metadata });
    let reject!: (error: unknown) => void;
    post.mockReturnValue(new Promise((_resolve, fail) => { reject = fail; }));
    const navigate = vi.fn(); render(<Login navigate={navigate} />);
    await screen.findByRole("button", { name: "Ingresar" }); submit(); submit();
    expect(post).toHaveBeenCalledOnce();
    await act(async () => reject(new Error("Synthetic transport failure")));
    await screen.findByText(/No se pudo confirmar el inicio de sesión/);
    submit(); expect(post).toHaveBeenCalledOnce(); expect(navigate).not.toHaveBeenCalled();
    expect((screen.getByLabelText("Password") as HTMLInputElement).value).toBe("");
  });

  it("does not treat a CSRF HTML rejection as invalid credentials", async () => {
    get.mockResolvedValue({ data: metadata });
    post.mockRejectedValue({ response: { status: 403, data: "<html>Forbidden</html>" } });
    render(<Login navigate={vi.fn()} />);
    await screen.findByRole("button", { name: "Ingresar" }); submit();
    await screen.findByText(/La solicitud fue rechazada/);
    expect(screen.queryByText("Usuario o contraseña inválidos.")).toBeNull();
    expect(document.body.innerHTML.includes("<html>Forbidden</html>")).toBe(false);
  });

  it("ignores authentication completion after unmount", async () => {
    get.mockResolvedValue({ data: metadata });
    let finish!: (value: unknown) => void;
    post.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    const navigate = vi.fn(); const view = render(<Login navigate={navigate} />);
    await screen.findByRole("button", { name: "Ingresar" }); submit(); view.unmount();
    await act(async () => finish({ data: { ok: true, redirect: "/inicio/" } }));
    expect(navigate).not.toHaveBeenCalled();
  });

  it("rejects an unexpected external success destination without retry", async () => {
    get.mockResolvedValue({ data: metadata });
    post.mockResolvedValue({ data: { ok: true, redirect: "https://external.invalid/" } });
    const navigate = vi.fn(); render(<Login navigate={navigate} />);
    await screen.findByRole("button", { name: "Ingresar" }); submit();
    await screen.findByText(/No se pudo confirmar el inicio de sesión/);
    expect(navigate).not.toHaveBeenCalled(); expect(post).toHaveBeenCalledOnce();
  });

  it.each(["/inicio/", "inicio/", `${window.location.origin}/insumos/`])("preserves the framework-approved destination %s", async (destination) => {
    get.mockResolvedValue({ data: metadata });
    post.mockResolvedValue({ data: { ok: true, redirect: destination } });
    const navigate = vi.fn(); render(<Login navigate={navigate} />);
    await screen.findByRole("button", { name: "Ingresar" }); submit();
    await waitFor(() => expect(navigate).toHaveBeenCalledWith(destination));
  });

  it("uses authenticated bootstrap redirects without rendering a usable login", async () => {
    get.mockResolvedValue({ data: { ok: true, redirect: "/inicio/" } });
    const navigate = vi.fn(); render(<Login navigate={navigate} />);
    await waitFor(() => expect(navigate).toHaveBeenCalledWith("/inicio/"));
    expect(screen.queryByRole("button", { name: "Ingresar" })).toBeNull();
  });
});
