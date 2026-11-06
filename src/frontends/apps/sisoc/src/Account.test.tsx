import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Account from "./Account";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const shellStyles = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "shell.css"), "utf8");

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@sisoc/api", () => ({ crearCliente: () => ({ get, post }) }));
const presentation = { user: { username: "synthetic", display_name: "Ana Pérez", avatar_initial: "S", role_label: "-" }, footer_version_label: "Versiones", legacy_frame_navigation: [] };
const initial = { first_name: "Ana", last_name: "Pérez", email: "ana@example.invalid", dni: "12345678", cuil: "20123456786", correo_institucional: "" };
const labels = ["Nombre", "Apellido", "Mail", "DNI", "CUIL", "Correo institucional"];
const metadata = { fields: Object.keys(initial).map((name, i) => ({ name, label: labels[i], help_text: name === "dni" ? "Solo números, sin puntos." : "", input_type: ["email", "correo_institucional"].includes(name) ? "email" : "text", required: name !== "correo_institucional", max_length: 150 })), initial, errors: {}, presentation };
beforeEach(() => { vi.resetAllMocks(); vi.spyOn(window, "scrollTo").mockImplementation(() => undefined); });
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });
const submit = () => fireEvent.submit(document.querySelector("form")!);

describe("ID-D account and required confirmation", () => {

  it.each(["account", "confirm"] as const)("leaves submit and shell control focus to the native stylesheets (%s)", async mode => {
    get.mockResolvedValue({ data: metadata });
    const focusSelectors = [...shellStyles.matchAll(/([^{}]*):focus(?:-visible|-within)?[^{}]*\{/g)]
      .flatMap(([rule]) => rule.replace(/\{$/, "").split(","))
      .map(selector => selector.trim().replace(/:focus(-visible|-within)?/g, ""));
    const link = document.createElement("a"); link.href = "/inicio/"; link.className = "brand-link d-flex align-items-center";
    const other = document.createElement("button"); other.className = "nav-link nav-link-rounded border-0 bg-transparent";
    document.body.append(link, other);
    try {
      render(<Account mode={mode} />);
      const button = await screen.findByRole<HTMLButtonElement>("button", { name: "Guardar datos" });
      await waitFor(() => expect(button.disabled).toBe(false));
      for (const control of [button, other, link]) {
        control.focus();
        expect(document.activeElement).toBe(control);
        expect(focusSelectors.filter(selector => control.matches(selector))).toEqual([]);
      }
    } finally { link.remove(); other.remove(); }
  });

  it("restores required modal scroll after invalid data like the native document reload", async () => {
    get.mockResolvedValue({ data: metadata });
    post.mockRejectedValue({ response: { status: 400, data: { ...metadata, errors: { dni: [{ message: "Ingrese un DNI válido (solo números).", code: "invalid" }] } } } });
    render(<Account mode="confirm" />); await screen.findByRole("button", { name: "Guardar datos" });
    const body = document.querySelector<HTMLElement>(".modal-body")!;
    body.scrollTop = 95;
    submit(); await screen.findByText("Ingrese un DNI válido (solo números).");
    expect(body.scrollTop).toBe(0);
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: "instant" });
    expect(post).toHaveBeenCalledOnce();
  });

  it("refreshes the legacy frame from the invalid bound Form without claiming a save", async () => {
    get.mockResolvedValue({ data: metadata });
    post.mockRejectedValue({ response: { status: 400, data: { ...metadata, initial: { ...initial, first_name: "Cambiado" }, presentation: { ...presentation, user: { ...presentation.user, display_name: "Cambiado Pérez" } }, errors: { dni: [{ message: "Ingrese un DNI válido (solo números).", code: "invalid" }] } } } });
    const frame = vi.fn((content, framePresentation) => <section data-frame-name={framePresentation.user.display_name}>{content}</section>);
    render(<Account renderFrame={frame} />); await screen.findByRole("button", { name: "Guardar datos" }); submit(); await screen.findByText("Ingrese un DNI válido (solo números).");
    expect(frame.mock.calls.at(-1)?.[1]).toMatchObject({ user: { display_name: "Cambiado Pérez" } });
    expect(post).toHaveBeenCalledOnce();
  });

  it("remounts timers for a later identical consumed notice without duplicating its container", async () => {
    const delivered = { ...metadata, messages: [{ message: "Aviso repetido.", level: "success" }] };
    get.mockResolvedValueOnce({ data: metadata }).mockResolvedValue({ data: delivered });
    post.mockResolvedValue({ data: { ok: true, redirect: "/mi-cuenta/", message: "Datos personales actualizados correctamente." } });
    render(<Account />); await screen.findByRole("button", { name: "Guardar datos" }); submit(); await screen.findByText("Aviso repetido.");
    vi.useFakeTimers(); fireEvent.click(screen.getByText("Aviso repetido.").closest('[role="status"]')!);
    await act(async () => vi.advanceTimersByTime(1000)); expect(screen.queryByText("Aviso repetido.")).toBeNull(); vi.useRealTimers();
    submit(); await screen.findByText("Aviso repetido.");
    expect(document.querySelectorAll("#toast-container").length).toBe(1); expect(get).toHaveBeenCalledTimes(3); expect(post).toHaveBeenCalledTimes(2);
  });

  it("refreshes the same canonical account path and shows consumed GET notices only once", async () => {
    get.mockResolvedValueOnce({ data: { ...metadata, messages: [] } }).mockResolvedValueOnce({ data: { ...metadata, messages: [{ message: "Aviso entregado por el servidor.", level: "success" }] } });
    post.mockResolvedValue({ data: { ok: true, redirect: "/mi-cuenta/", message: "Datos personales actualizados correctamente." } });
    window.history.replaceState(null, "", "/mi-cuenta/"); render(<Account />);
    await screen.findByRole("button", { name: "Guardar datos" }); submit();
    await screen.findByText("Aviso entregado por el servidor.");
    expect(screen.queryByText("Datos personales actualizados correctamente.")).toBeNull();
    expect(get).toHaveBeenCalledTimes(2); expect(post).toHaveBeenCalledOnce();
    expect(window.location.pathname).toBe("/mi-cuenta/");
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: "instant" });
  });

  it("loads only own-account metadata and renders the authorized six fields", async () => {
    get.mockResolvedValue({ data: metadata }); render(<Account />);
    await screen.findByRole("button", { name: "Guardar datos" });
    expect(get.mock.calls[0][0]).toBe("web/account/");
    expect(document.querySelectorAll("input").length).toBe(6);
    expect(screen.getByLabelText(/Nombre/).getAttribute("name")).toBe("first_name");
    expect(screen.queryByText("rol")).toBeNull();
  });
  it("sends only six current values once and navigates to the source return", async () => {
    get.mockResolvedValue({ data: metadata }); let resolve!: (value: unknown) => void;
    post.mockReturnValue(new Promise(r => { resolve = r; })); const navigate = vi.fn(); render(<Account navigate={navigate} />);
    await screen.findByRole("button", { name: "Guardar datos" }); submit(); submit(); expect(post).toHaveBeenCalledOnce();
    const body = post.mock.calls[0][1] as URLSearchParams;
    expect([...body.keys()]).toEqual(Object.keys(initial));
    await act(async () => resolve({ data: { ok: true, redirect: "/mi-cuenta/", message: "Datos personales actualizados correctamente." } }));
    expect(navigate).toHaveBeenCalledWith("/mi-cuenta/");
  });
  it("preserves source field errors and values without saving or automatic retry", async () => {
    get.mockResolvedValue({ data: metadata }); post.mockRejectedValue({ response: { status: 400, data: { ...metadata, errors: { dni: [{ message: "Ingrese un DNI válido (solo números).", code: "invalid" }] } } } });
    render(<Account />); await screen.findByRole("button", { name: "Guardar datos" }); submit();
    await screen.findByText("Ingrese un DNI válido (solo números).");
    expect((screen.getByLabelText(/DNI/) as HTMLInputElement).value).toBe("12345678");
    expect(screen.getByLabelText(/DNI/).className).toContain("is-invalid"); expect(post).toHaveBeenCalledOnce();
  });
  it("puts confirmation overlays in the third frame slot and cannot dismiss them", async () => {
    get.mockResolvedValue({ data: metadata }); const frame = vi.fn((content, _presentation, overlays) => <section>{content}{overlays}</section>);
    render(<Account mode="confirm" renderFrame={frame} />); await screen.findByRole("dialog");
    expect(get.mock.calls[0][0]).toBe("web/account/confirm/");
    expect(screen.getByRole("dialog").getAttribute("aria-modal")).toBe("true");
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" }); fireEvent.click(document.querySelector(".modal-backdrop")!);
    expect(screen.getByRole("dialog")).toBeDefined(); expect(screen.getAllByRole("button").length).toBe(1);
    expect(frame.mock.calls.at(-1)?.[1]).toEqual(presentation);
  });
  it("does not render protected values after denied prerequisite metadata", async () => {
    get.mockResolvedValue({ status: 403, data: { detail: "Complete el requisito.", state: "password_change_required", required_action_url: "/password/first-change/" } });
    render(<Account />); await screen.findByRole("heading", { name: "Antes de continuar" }); expect(document.querySelector("input")).toBeNull();
  });
  it("treats uncertain submission as nonretryable and ignores abandoned results", async () => {
    get.mockResolvedValue({ data: metadata }); post.mockRejectedValue(new Error("Synthetic unavailable"));
    render(<Account />); await screen.findByRole("button", { name: "Guardar datos" }); submit();
    await screen.findByText(/No se pudo confirmar/); submit(); expect(post).toHaveBeenCalledOnce();
  });
  it("ignores a late success after unmount", async () => {
    get.mockResolvedValue({ data: metadata }); let resolve!: (value: unknown) => void; post.mockReturnValue(new Promise(r => { resolve = r; }));
    const navigate = vi.fn(); const view = render(<Account navigate={navigate} />); await screen.findByRole("button", { name: "Guardar datos" }); submit(); view.unmount();
    await act(async () => resolve({ data: { ok: true, redirect: "/mi-cuenta/", message: "Datos personales actualizados correctamente." } }));
    expect(navigate).not.toHaveBeenCalled();
  });
  it("rejects a substituted external success destination", async () => {
    get.mockResolvedValue({ data: metadata }); post.mockResolvedValue({ data: { ok: true, redirect: "https://external.invalid/" } });
    const navigate = vi.fn(); render(<Account navigate={navigate} />); await screen.findByRole("button", { name: "Guardar datos" }); submit();
    await screen.findByText(/No se pudo confirmar/); expect(navigate).not.toHaveBeenCalled();
  });
});
