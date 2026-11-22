import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, waitFor } from "@testing-library/react";
import App from "../App";
import { setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
  mensajeDeError: vi.fn(() => "Error de prueba"),
  SinPermiso: class SinPermiso extends Error {},
}));

function setup(path = "/password_reset/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC - Insumos";
  setViewport(false);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Password recovery routes", () => {
  it.each([
    ["/password_reset/", ["web/password/reset/"], "Recuperar contraseña"],
    ["/password_reset/done/", ["web/password/reset/"], "Solicitud recibida"],
    ["/reset/done/", ["web/password/reset/"], "Contraseña actualizada"],
    ["/reset/MQ/set-password/", ["web/password/reset/", "web/password/reset/MQ/"], "Restablecer contraseña"],
    ["/password/reset/confirm/MQ/set-password/", ["web/password/reset/", "web/password/reset/MQ/"], "Restablecer contraseña"],
    ["/reset/MQ/synthetic-reset-token/", ["web/password/reset/"], "Restablecer contraseña"],
    ["/password/reset/confirm/MQ/synthetic-reset-token/", ["web/password/reset/"], "Restablecer contraseña"],
  ])("renders %s without the business shell or the URL token", async (path, endpoints, heading) => {
    webGet.mockReturnValue(new Promise(() => {}));
    setup(path);
    expect(document.querySelector(".password-reset-content h5")!.textContent).toBe(heading);
    await waitFor(() => expect(webGet).toHaveBeenCalledTimes(endpoints.length));
    expect(webGet.mock.calls.map(([url]) => url).sort()).toEqual(endpoints);
    expect(JSON.stringify(webGet.mock.calls)).not.toContain("synthetic-reset-token");
    expect(document.querySelector(".app-sidebar")).toBeNull();
    expect(window.location.pathname).toBe(path);
  });
});
