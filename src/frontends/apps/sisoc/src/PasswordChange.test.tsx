import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import PasswordChange from "./PasswordChange";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@sisoc/api", () => ({ crearCliente: () => ({ get, post }), leerCookie: () => null }));

const metadata = {
  title: "Cambio de contraseña",
  done_title: "Cambio de contraseña exitoso",
  done_text: "Su contraseña ha sido cambiada.",
  intro_text: "Por favor, por razones de seguridad, introduzca primero su contraseña antigua y luego introduzca la nueva contraseña dos veces para verificar que la ha escrito correctamente.",
  submit_label: "Cambiar contraseña",
  fields: [
    { name: "old_password", label: "Contraseña antigua", required: true, help_text: "", attrs: { id: "id_old_password", autocomplete: "current-password", autofocus: true } },
    { name: "new_password1", label: "Contraseña nueva", required: true, help_text: "<ul><li>Su contraseña debe contener por lo menos 8 caracteres.</li></ul>", attrs: { id: "id_new_password1", autocomplete: "new-password" } },
    { name: "new_password2", label: "Confirmación de contraseña nueva", required: true, help_text: "Para verificar, introduzca la misma contraseña anterior.", attrs: { id: "id_new_password2", autocomplete: "new-password" } },
  ],
};
const fill = () => {
  for (const name of ["old_password", "new_password1", "new_password2"]) {
    fireEvent.change(document.querySelector(`[name=${name}]`)!, { target: { value: "Synthetic-Password-739!" } });
  }
};
const clear = () => [...document.querySelectorAll<HTMLInputElement>('input[type="password"]')].every((e) => e.value === "");

beforeEach(() => {
  vi.resetAllMocks();
  get.mockResolvedValue({ data: metadata });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Voluntary password circuit", () => {
  it("renders three source password fields without required-password styling or an extra shell", async () => {
    render(<PasswordChange mode="form" />);
    expect(await screen.findByLabelText(/Contraseña antigua/)).toBeDefined();
    expect(document.querySelectorAll('input[type="password"]')).toHaveLength(3);
    const old = document.querySelector<HTMLInputElement>('[name=old_password]')!;
    expect(old.className).toBe("");
    expect(old.autocomplete).toBe("current-password");
    expect(screen.getByText("Su contraseña debe contener por lo menos 8 caracteres.")).toBeDefined();
    expect(document.querySelector(".app-sidebar")).toBeNull();
    expect(post).not.toHaveBeenCalled();
  });

  it("posts only source fields URL-encoded, clears rejected passwords and keeps real Form errors", async () => {
    post.mockRejectedValue({ response: { status: 400, data: { errors: { old_password: [{ message: "Su contraseña antigua es incorrecta.", code: "password_incorrect" }] } } } });
    render(<PasswordChange />);
    await screen.findByLabelText(/Contraseña antigua/);
    fill();
    const submit = screen.getByRole("button", { name: metadata.submit_label });
    submit.focus();
    fireEvent.click(submit);
    expect(await screen.findByText("Su contraseña antigua es incorrecta.")).toBeDefined();
    expect(clear()).toBe(true);
    expect(document.activeElement).toBe(submit);
    expect(post).toHaveBeenCalledOnce();
    expect(post.mock.calls[0][1]).toBeInstanceOf(URLSearchParams);
    expect([...post.mock.calls[0][1].keys()]).toEqual(["old_password", "new_password1", "new_password2"]);
    expect(screen.getByRole<HTMLButtonElement>("button", { name: metadata.submit_label }).disabled).toBe(false);
  });

  it("blocks duplicate POST and manual retry after an uncertain outcome", async () => {
    let reject!: (value: unknown) => void;
    post.mockReturnValue(new Promise((_resolve, fail) => { reject = fail; }));
    render(<PasswordChange />);
    const button = await screen.findByRole<HTMLButtonElement>("button", { name: metadata.submit_label });
    fill(); fireEvent.click(button); fireEvent.click(button);
    expect(post).toHaveBeenCalledOnce();
    await act(async () => reject(new Error("unknown outcome")));
    expect(clear()).toBe(true);
    expect(await screen.findByRole("alert")).toBeDefined();
    expect(screen.getByRole("link", { name: "Volver al formulario" }).getAttribute("href")).toBe("/password_change/");
    expect(screen.queryByText(metadata.done_text)).toBeNull();
    expect(button.disabled).toBe(true);
    fireEvent.click(button);
    expect(post).toHaveBeenCalledOnce();
  });

  it("follows only the exact source done destination after success", async () => {
    const navigate = vi.fn();
    post.mockResolvedValue({ data: { ok: true, redirect: "/password_change/done/" } });
    render(<PasswordChange navigate={navigate} />);
    await screen.findByLabelText(/Contraseña antigua/); fill();
    fireEvent.click(screen.getByRole("button", { name: metadata.submit_label }));
    await screen.findByRole("status");
    expect(navigate).toHaveBeenCalledWith("/password_change/done/");
    expect(document.querySelectorAll('input[type="password"]')).toHaveLength(0);
  });

  it("rejects an unexpected success destination without retrying", async () => {
    const navigate = vi.fn();
    post.mockResolvedValue({ data: { ok: true, redirect: "//outside.invalid/" } });
    render(<PasswordChange navigate={navigate} />);
    await screen.findByLabelText(/Contraseña antigua/); fill();
    fireEvent.click(screen.getByRole("button", { name: metadata.submit_label }));
    await screen.findByRole("alert");
    expect(navigate).not.toHaveBeenCalled();
    expect(clear()).toBe(true);
    expect(post).toHaveBeenCalledOnce();
  });

  it("removes form data on a raw HTML CSRF403 without assuming JSON", async () => {
    post.mockResolvedValue({ status: 403, data: "<html>CSRF rejected</html>" });
    render(<PasswordChange />);
    await screen.findByLabelText(/Contraseña antigua/); fill();
    fireEvent.click(screen.getByRole("button", { name: metadata.submit_label }));
    await screen.findByRole("alert");
    expect(document.querySelector('input[type="password"]')).toBeNull();
    expect(post).toHaveBeenCalledOnce();
  });

  it("shows done only after the same authenticated metadata guard and never POSTs", async () => {
    render(<PasswordChange mode="done" />);
    expect(await screen.findByText(metadata.done_text)).toBeDefined();
    expect(document.querySelector('input[type="password"]')).toBeNull();
    expect(get).toHaveBeenCalledWith("web/password/change/", expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(post).not.toHaveBeenCalled();
  });

  it("fails closed for denied done metadata and malformed field descriptors", async () => {
    get.mockResolvedValueOnce({ status: 403, data: { state: "profile_confirmation_required", required_action_url: "/mi-cuenta/confirmar/" } });
    const view = render(<PasswordChange mode="done" />);
    await screen.findByRole("alert");
    expect(screen.queryByText(metadata.done_text)).toBeNull();
    view.unmount();
    get.mockResolvedValueOnce({ data: { ...metadata, fields: metadata.fields.slice(1) } });
    render(<PasswordChange />);
    await screen.findByRole("alert");
    expect(document.querySelector('input[type="password"]')).toBeNull();
  });

  it("ignores a late metadata response after unmount", async () => {
    let resolve!: (value: unknown) => void;
    get.mockReturnValue(new Promise((finish) => { resolve = finish; }));
    const view = render(<PasswordChange />); view.unmount();
    await act(async () => resolve({ data: metadata }));
    expect(document.querySelector('input[type="password"]')).toBeNull();
    expect(post).not.toHaveBeenCalled();
  });

  it("ignores a late successful mutation after unmount", async () => {
    let resolve!: (value: unknown) => void;
    post.mockReturnValue(new Promise((finish) => { resolve = finish; }));
    const navigate = vi.fn();
    const view = render(<PasswordChange navigate={navigate} />);
    await screen.findByLabelText(/Contraseña antigua/); fill();
    fireEvent.click(screen.getByRole("button", { name: metadata.submit_label })); view.unmount();
    await act(async () => resolve({ data: { ok: true, redirect: "/password_change/done/" } }));
    expect(navigate).not.toHaveBeenCalled();
  });
});
