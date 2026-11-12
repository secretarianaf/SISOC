import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { comunicadosEliminarNavigation, eliminarValid } from "./comunicadosEliminar";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/comunicados/";
const data = (over: Record<string, unknown> = {}) => ({
  id: 7, titulo: "Aviso <a borrar>", fecha_creacion: "03/03/2026 09:00", creador: "Ana Pérez", adjuntos_count: 0, messages: [], ...over,
});

function serve(body: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status }));
}
function setup() {
  window.history.replaceState({}, "", "/comunicados/eliminar/7/");
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Comunicados delete confirmation", () => {
  it("is owned by the comunicados module and validates its payload", () => {
    expect(findRoute("/comunicados/eliminar/7/")?.route.name).toBe("comedores-comunicados");
    expect(findRoute("/comunicados/eliminar/x/")?.route.name).not.toBe("comedores-comunicados");
    expect(eliminarValid(data())).toBe(true);
    expect(eliminarValid(data({ adjuntos_count: "1" }))).toBe(false);
  });

  it("renders the native confirmation with the attachment warning only when there are files", async () => {
    serve(data({ adjuntos_count: 2 }));
    setup();
    expect(await screen.findByText("¿Estás seguro de que deseas eliminar el siguiente comunicado?")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}7/eliminar/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Eliminar Comunicado"));
    expect(screen.getByText("Confirmar Eliminación")).toBeTruthy();
    expect(screen.getByText("Aviso <a borrar>")).toBeTruthy();
    expect(document.querySelector(".alert-secondary small")?.textContent).toBe("Creado el 03/03/2026 09:00 por Ana Pérez");
    expect(document.querySelector(".alert-warning")?.textContent).toBe(" Este comunicado tiene 2 archivo(s) adjunto(s) que también serán eliminados.");
    expect(screen.getByText("Esta acción no se puede deshacer.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/comunicados/gestion/");
    cleanup();
    serve(data());
    setup();
    await screen.findByText("Confirmar Eliminación");
    expect(document.querySelector(".alert-warning")).toBeNull();
  });

  it("posts once and navigates to the confirmed redirect", async () => {
    serve(data());
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/comunicados/gestion/" }, status: 200 });
    const assign = vi.spyOn(comunicadosEliminarNavigation, "assign").mockImplementation(() => {});
    setup();
    const boton = await screen.findByRole("button", { name: "Sí, Eliminar" });
    fireEvent.click(boton);
    fireEvent.click(boton);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comunicados/gestion/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}7/eliminar/`);
  });

  it("shows the native 403 message or the unconfirmed notice and never resends", async () => {
    serve(data());
    webPost.mockResolvedValueOnce({ data: { detail: "No tiene permisos para eliminar este comunicado." }, status: 403 });
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Sí, Eliminar" }));
    expect((await screen.findByRole("alert")).textContent).toBe("No tiene permisos para eliminar este comunicado.");
    expect((screen.getByRole("button", { name: "Sí, Eliminar" }) as HTMLButtonElement).disabled).toBe(true);
    cleanup();
    webPost.mockRejectedValueOnce(new Error("timeout"));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Sí, Eliminar" }));
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo confirmar el resultado. Revise la gestión de comunicados antes de volver a intentar.");
    expect(webPost).toHaveBeenCalledTimes(2);
  });
});
