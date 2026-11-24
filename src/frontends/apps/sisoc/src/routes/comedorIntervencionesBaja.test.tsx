import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { bajaNavigation, bajaValid, intervencionBajaValid } from "./comedorIntervencionesBaja";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const ENDPOINT = "web/comedores/intervenciones/comedor/3/baja/5/";
const data = (over: Record<string, unknown> = {}) => ({
  id: 5, object_name: "INTERVENCIÓN EN COMEDOR SINTÉTICO - 2026-10-01", confirm_text: "Dar de baja", cancel_text: "Cancelar",
  cancel_url: "/comedores/intervencion/ver/3", messages: [], breadcrumb: { etiqueta: "Intervención en Comedor Sintético - 2026-10-01", url: "/comedores/5" },
  cascade_preview: {
    total_afectados: 2, total_baja_logica: 2, total_borrado_fisico: 0,
    desglose_por_modelo: [{ modelo: "Intervención", cantidad: 1, modo: "baja_logica", ejemplos: ["Intervención en X"] }, { modelo: "Archivo", cantidad: 1, modo: "borrado", ejemplos: [] }],
  },
  ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
function setup() {
  window.history.replaceState({}, "", "/comedores/intervencion/borrar/3/5/");
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Comedor intervention soft-delete confirmation", () => {
  it("owns the native URL and validates its payload", () => {
    expect(findRoute("/comedores/intervencion/borrar/3/5/")?.route.name).toBe("comedores-intervenciones");
    expect(findRoute("/comedores/intervencion/borrar/3/5")?.route.name).not.toBe("comedores-intervenciones");
    expect(bajaValid(data())).toBe(true);
    expect(bajaValid(data({ cascade_preview: null }))).toBe(true);
    expect(bajaValid(data({ cancel_url: "https://externo.example" }))).toBe(false);
    expect(intervencionBajaValid(data({ breadcrumb: { etiqueta: "x" } }))).toBe(false);
  });

  it("renders the native confirmation, the preview and the odd breadcrumb of the template", async () => {
    serve(data());
    setup();
    expect(await screen.findByText("Atención!")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(ENDPOINT, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Acciones"));
    expect(document.querySelector(".error-content p")?.textContent).toBe("¿Estás seguro que deseas realizar una baja lógica en cascada del registro INTERVENCIÓN EN COMEDOR SINTÉTICO - 2026-10-01?");
    expect(document.querySelector(".alert-info")?.textContent).toBe("Total de registros afectados: 2Bajas lógicas: 2");
    expect(Array.from(document.querySelectorAll("tbody tr")).map((tr) => tr.textContent)).toEqual([
      "Intervención1Baja lógicaIntervención en X", "Archivo1Borrado físico técnico-",
    ]);
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/comedores/intervencion/ver/3");
    const crumbs = Array.from(document.querySelectorAll(".breadcrumb-item")).map((li) => li.textContent);
    expect(crumbs).toEqual(["Admisiones", "Intervención en Comedor Sintético - 2026-10-01", "Detalle"]);
    expect(screen.getByRole("link", { name: "Admisiones" }).getAttribute("href")).toBe("/comedores/intervencion/borrar/3/5/");
    expect(screen.getByRole("link", { name: /Intervención en Comedor/ }).getAttribute("href")).toBe("/comedores/5");
  });

  it("posts once and follows the native redirect to the list", async () => {
    serve(data({ cascade_preview: null }));
    const assign = vi.spyOn(bajaNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/comedores/intervencion/ver/3" }, status: 200 });
    setup();
    const confirm = await screen.findByRole("button", { name: "Dar de baja" });
    fireEvent.click(confirm);
    fireEvent.click(confirm);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/intervencion/ver/3"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(ENDPOINT);
  });

  it("shows the native 403 detail or an unconfirmed notice and never navigates", async () => {
    serve(data());
    const assign = vi.spyOn(bajaNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValueOnce({ data: { detail: "Usted no tiene permiso para realizar esta acción." }, status: 403 });
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    expect(await screen.findByText("Usted no tiene permiso para realizar esta acción.")).toBeTruthy();
    cleanup();
    serve(data());
    webPost.mockRejectedValueOnce(new Error("network"));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
  });
});
