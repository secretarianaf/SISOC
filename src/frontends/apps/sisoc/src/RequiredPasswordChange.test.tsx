import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import RequiredPasswordChange from "./RequiredPasswordChange";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@sisoc/api", () => ({ crearCliente: vi.fn(() => ({ get, post })) }));

const metadata = {
  access: { state: "password_change_required", required_action_url: "/password/first-change/" },
  fields: [
    { name: "new_password1", label: "Contraseña nueva", help_text: "<ul><li>Utilice una contraseña segura.</li></ul>", required: true },
    { name: "new_password2", label: "Confirmación de contraseña nueva", help_text: "", required: true },
  ],
  presentation: {
    user: { username: "synthetic", display_name: "Persona sintética", avatar_initial: "S", role_label: "Prueba" },
    footer_version_label: "v0",
    legacy_frame_navigation: [{ id: "inicio", label: "Inicio", href: "/inicio/", children: [] }],
  },
};
const passwordsCleared = () => Array.from(document.querySelectorAll<HTMLInputElement>('input[type="password"]')).every((input) => input.value === "");
const fill = () => {
  fireEvent.change(screen.getByLabelText(/Contraseña nueva/), { target: { value: "Synthetic-new-password-48!" } });
  fireEvent.change(screen.getByLabelText(/Confirmación/), { target: { value: "Synthetic-new-password-48!" } });
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Mandatory password React circuit", () => {
  it("renders the existing two password fields and passes presentation without fabricating ready", async () => {
    get.mockResolvedValue({ data: metadata });
    const frame = vi.fn((content) => <section data-testid="frame">{content}</section>);
    render(<RequiredPasswordChange renderFrame={frame} />);
    expect(await screen.findByRole("button", { name: "Guardar contraseña" })).toBeDefined();
    expect(screen.getByText("Debes actualizar tu contraseña")).toBeDefined();
    expect(screen.getByText("Utilice una contraseña segura.")).toBeDefined();
    expect(document.querySelector('input[name="old_password"]')).toBeNull();
    expect(document.querySelectorAll('input[type="password"]')).toHaveLength(2);
    expect(frame).toHaveBeenLastCalledWith(expect.anything(), metadata.presentation);
    expect(get).toHaveBeenCalledWith("web/password/first-change/", expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(post).not.toHaveBeenCalled();
  });

  it("submits URL-encoded fields once and clears rejected passwords while retaining field errors", async () => {
    get.mockResolvedValue({ data: metadata });
    post.mockRejectedValue({ response: { status: 400, data: { errors: { new_password2: [{ message: "Las dos contraseñas no coinciden.", code: "password_mismatch" }] } } } });
    render(<RequiredPasswordChange />);
    await screen.findByRole("button", { name: "Guardar contraseña" });
    fill();
    fireEvent.click(screen.getByRole("button", { name: "Guardar contraseña" }));
    expect(await screen.findByText("Las dos contraseñas no coinciden.")).toBeDefined();
    expect(passwordsCleared()).toBe(true);
    expect(post).toHaveBeenCalledOnce();
    const body = post.mock.calls[0][1];
    expect(body).toBeInstanceOf(URLSearchParams);
    expect(Array.from(body.keys())).toEqual(["new_password1", "new_password2"]);
    expect(screen.getByRole("button", { name: "Guardar contraseña" }).hasAttribute("disabled")).toBe(false);
    expect(window.scrollTo).toHaveBeenCalled();
  });

  it("blocks double submit and refuses an automatic retry after an uncertain mutation", async () => {
    get.mockResolvedValue({ data: metadata });
    let reject!: (reason: unknown) => void;
    post.mockReturnValue(new Promise((_resolve, fail) => { reject = fail; }));
    render(<RequiredPasswordChange />);
    const button = await screen.findByRole("button", { name: "Guardar contraseña" });
    fill(); fireEvent.click(button); fireEvent.click(button);
    expect(post).toHaveBeenCalledOnce();
    await act(async () => reject(new Error("network outcome unknown")));
    expect(passwordsCleared()).toBe(true);
    expect(screen.getByRole("alert").textContent).toContain("No se pudo confirmar el resultado");
    fireEvent.click(button);
    expect(post).toHaveBeenCalledOnce();
    expect(button.hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("link", { name: "Revisar el estado" }).getAttribute("href")).toBe("/inicio/");
  });

  it("hides the previous frame on a raw HTML CSRF403 and does not retry", async () => {
    get.mockResolvedValue({ data: metadata });
    post.mockResolvedValue({ status: 403, data: "<html>CSRF rejected</html>" });
    const frame = vi.fn((content) => <section data-testid="private-frame">{content}</section>);
    render(<RequiredPasswordChange renderFrame={frame} />);
    await screen.findByRole("button", { name: "Guardar contraseña" }); fill();
    fireEvent.click(screen.getByRole("button", { name: "Guardar contraseña" }));
    await screen.findByText("403");
    expect(screen.queryByTestId("private-frame")).toBeNull();
    expect(document.querySelectorAll('input[type="password"]')).toHaveLength(0);
    expect(post).toHaveBeenCalledOnce();
  });

  it("ignores late metadata after unmount", async () => {
    let finish!: (value: unknown) => void;
    get.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    const frame = vi.fn((content) => content);
    const view = render(<RequiredPasswordChange renderFrame={frame} />);
    view.unmount();
    await act(async () => finish({ data: metadata }));
    expect(frame).not.toHaveBeenCalled();
    expect(document.querySelectorAll('input[type="password"]')).toHaveLength(0);
  });

  it("ignores a late mutation response after unmount", async () => {
    get.mockResolvedValue({ data: metadata });
    let finish!: (value: unknown) => void;
    post.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    const view = render(<RequiredPasswordChange />);
    await screen.findByRole("button", { name: "Guardar contraseña" }); fill();
    fireEvent.click(screen.getByRole("button", { name: "Guardar contraseña" })); view.unmount();
    await act(async () => finish({ data: { ok: true, message: "Contraseña actualizada correctamente.", redirect: "/inicio/" } }));
    expect(consoleError).not.toHaveBeenCalled();
    expect(post).toHaveBeenCalledOnce();
  });

  it("fails closed on malformed metadata or an unsafe presentation destination", async () => {
    get.mockResolvedValue({ data: { ...metadata, presentation: { ...metadata.presentation, legacy_frame_navigation: [{ id: "outside", label: "Outside", href: "https://outside.invalid/", children: [] }] } } });
    render(<RequiredPasswordChange />);
    expect(await screen.findByRole("alert")).toBeDefined();
    expect(document.querySelector('input[type="password"]')).toBeNull();
    expect(post).not.toHaveBeenCalled();
  });

  it("rejects an unexpected successful destination instead of following it", async () => {
    get.mockResolvedValue({ data: metadata });
    post.mockResolvedValue({ data: { ok: true, message: "not trusted", redirect: "//outside.invalid/" } });
    render(<RequiredPasswordChange />);
    await screen.findByRole("button", { name: "Guardar contraseña" }); fill();
    fireEvent.click(screen.getByRole("button", { name: "Guardar contraseña" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("No se pudo confirmar el resultado"));
    expect(passwordsCleared()).toBe(true);
    expect(post).toHaveBeenCalledOnce();
  });

  it("clears and withholds the form after the source success response", async () => {
    get.mockResolvedValue({ data: metadata });
    post.mockResolvedValue({ data: { ok: true, message: "Contraseña actualizada correctamente.", redirect: "/inicio/" } });
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(<RequiredPasswordChange />);
    await screen.findByRole("button", { name: "Guardar contraseña" }); fill();
    fireEvent.click(screen.getByRole("button", { name: "Guardar contraseña" }));
    expect(await screen.findByRole("status")).toBeDefined();
    expect(document.querySelectorAll('input[type="password"]')).toHaveLength(0);
    expect(post).toHaveBeenCalledOnce();
  });

  it("does not mount a form or submit when metadata says the requirement was completed", async () => {
    get.mockResolvedValue({ data: { ok: true, redirect: "/inicio/" } });
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(<RequiredPasswordChange />);
    await screen.findByText("Continuando en SISOC…");
    expect(document.querySelectorAll('input[type="password"]')).toHaveLength(0);
    expect(post).not.toHaveBeenCalled();
  });
});
