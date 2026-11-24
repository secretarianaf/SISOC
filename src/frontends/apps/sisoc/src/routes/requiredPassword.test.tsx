import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
  mensajeDeError: vi.fn(() => "Error de prueba"),
  SinPermiso: class SinPermiso extends Error {},
}));

function setup(path = "/password/first-change/") {
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

describe("Required password route", () => {
  it("renders the restricted presentation frame without business capability or session fetch", async () => {
    webGet.mockResolvedValue({ data: {
      access: { state: "password_change_required", required_action_url: "/password/first-change/" },
      fields: ["new_password1", "new_password2"].map((name) => ({ name, label: name, help_text: "", required: true })),
      presentation: { user: readyContext.user, footer_version_label: readyContext.footer_version_label, legacy_frame_navigation: readyContext.navigation },
    } });
    setup("/password/first-change/");
    await screen.findByRole("heading", { name: "Actualizar contraseña" });
    fireEvent.click(screen.getByRole("button", { name: "Configuración de Comedores" }));
    expect(screen.getByRole("link", { name: "Insumos" }).getAttribute("href")).toBe("/insumos/");
    expect(webGet.mock.calls.every(([url]) => url === "web/password/first-change/")).toBe(true);
    await waitFor(() => expect(document.title).toBe("SISOC - Cambio obligatorio de contraseña"));
  });
});
