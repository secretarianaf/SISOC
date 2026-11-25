import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { bajaNavigation } from "./comedorIntervencionesBaja";
import { bajaObservacionValid, detailValid, formValid, observacionesNavigation } from "./comedorObservaciones";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/observaciones/";
const comedor = { id: 3, nombre: "Comedor Sintético", url: "/comedores/3" };
const form = (over: Record<string, unknown> = {}) => ({
  comedor, observacion_id: null, urls: { comedores: "/comedores/", observacion: null },
  field: { name: "observacion", label: "Observación", required: true, rows: 4, placeholder: "Describa la observación" },
  value: "", errors: {}, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 8, comedor, observador: "Luis Gómez", fecha: "13 de noviembre de 2026 a las 09:30", observacion: "Texto <libre>",
  urls: { comedores: "/comedores/", editar: "/comedores/observacion/8/editar", eliminar: "/comedores/observacion/8/eliminar" }, messages: [], ...over,
});
const baja = (over: Record<string, unknown> = {}) => ({
  id: 8, object_name: "OBSERVACIÓN 2026-10-01 - COMEDOR SINTÉTICO", confirm_text: "Dar de baja", cancel_text: "Cancelar",
  cancel_url: "/comedores/observacion/8", messages: [], cascade_preview: null, comedor, urls: { comedores: "/comedores/" }, ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
function setup(url: string) {
  window.history.replaceState({}, "", url);
  return render(<App />);
}
const textarea = () => document.getElementById("id_observacion") as HTMLTextAreaElement;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Comedor observations", () => {
  it("owns the four native URLs (no trailing slash) and validates its payloads", () => {
    for (const path of ["/comedores/3/observacion/crear", "/comedores/observacion/8", "/comedores/observacion/8/editar", "/comedores/observacion/8/eliminar"]) {
      expect(findRoute(path)?.route.name, path).toBe("comedores-observaciones");
    }
    expect(findRoute("/comedores/observacion/8/")?.route.name).not.toBe("comedores-observaciones");
    expect(findRoute("/comedores/observacion/x")?.route.name).not.toBe("comedores-observaciones");
    expect(formValid(form())).toBe(true);
    expect(formValid(form({ field: { name: "otro" } }))).toBe(false);
    expect(detailValid(detail())).toBe(true);
    expect(detailValid(detail({ urls: { comedores: "/c", editar: "https://x.example", eliminar: "/e" } }))).toBe(false);
    expect(bajaObservacionValid(baja())).toBe(true);
    expect(bajaObservacionValid(baja({ comedor: null }))).toBe(false);
  });

  it("renders the create form with the native breadcrumb and the crispy field", async () => {
    serve(form());
    setup("/comedores/3/observacion/crear?next=/comedores/3");
    expect(await screen.findByText(/Agregar observacion al comedor:/)).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}comedor/3/crear/?next=/comedores/3`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Observacion - Espacio Comunitario: Comedor Sintético"));
    expect(Array.from(document.querySelectorAll(".breadcrumb-item")).map((li) => li.textContent)).toEqual(["Espacios Comunitarios", "Comedor Sintético", "Agregar"]);
    expect(document.querySelector('label[for="id_observacion"]')?.textContent).toBe("Observación*");
    expect(textarea().getAttribute("placeholder")).toBe("Describa la observación");
    expect(Array.from(document.querySelectorAll("form .btn")).map((b) => b.textContent)).toEqual(["Confirmar", "Imprimir", "Cancelar"]);
  });

  it("renders the edit breadcrumb and posts only the observation, then follows the native redirect", async () => {
    serve(form({ observacion_id: 8, urls: { comedores: "/comedores/", observacion: "/comedores/observacion/8" }, value: "Texto original" }));
    const assign = vi.spyOn(observacionesNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/comedores/observacion/8" }, status: 200 });
    setup("/comedores/observacion/8/editar");
    await screen.findByText(/Agregar observacion al comedor:/);
    expect(Array.from(document.querySelectorAll(".breadcrumb-item")).map((li) => li.textContent)).toEqual(["Espacios Comunitarios", "Comedor Sintético", "8", "Editar"]);
    expect(textarea().value).toBe("Texto original");
    fireEvent.change(textarea(), { target: { value: "Texto editado" } });
    const confirmar = screen.getByRole("button", { name: "Confirmar" });
    fireEvent.click(confirmar);
    fireEvent.click(confirmar);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/observacion/8"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}8/editar/`);
    expect(Object.fromEntries((webPost.mock.calls[0][1] as URLSearchParams).entries())).toEqual({ observacion: "Texto editado" });
  });

  it("shows the native field error for a rejected POST and never navigates", async () => {
    serve(form());
    const assign = vi.spyOn(observacionesNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValueOnce({ data: form({ errors: { observacion: [{ message: "Este campo es requerido.", code: "required" }] } }), status: 400 });
    setup("/comedores/3/observacion/crear");
    await screen.findByText(/Agregar observacion al comedor:/);
    fireEvent.change(textarea(), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));
    expect(await screen.findByText("Este campo es requerido.")).toBeTruthy();
    expect(textarea().className).toContain("is-invalid");
    expect(textarea().getAttribute("aria-describedby")).toBe("id_observacion_error");
    expect(assign).not.toHaveBeenCalled();
  });

  it("reports a forbidden or unconfirmed post and does not retry", async () => {
    serve(form());
    webPost.mockResolvedValueOnce({ data: { detail: "Usted no tiene permiso para realizar esta acción." }, status: 403 });
    setup("/comedores/3/observacion/crear");
    await screen.findByText(/Agregar observacion al comedor:/);
    fireEvent.change(textarea(), { target: { value: "Texto" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));
    expect(await screen.findByText("Usted no tiene permiso para realizar esta acción.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Confirmar" }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("renders the detail card, escapes the text and collapses it like AdminLTE", async () => {
    serve(detail());
    setup("/comedores/observacion/8");
    expect(await screen.findByText("Texto <libre>")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}8/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Observacion - Espacio Comunitario: Comedor Sintético"));
    expect(Array.from(document.querySelectorAll(".breadcrumb-item")).map((li) => li.textContent)).toEqual(["Espacios Comunitarios", "Comedor Sintético", "Observacion 8"]);
    expect(Array.from(document.querySelectorAll(".comment-text")).map((c) => c.textContent)).toEqual([
      "Usuario observadorLuis Gómez", "Fecha y hora de observacion13 de noviembre de 2026 a las 09:30", "ObservacionTexto <libre>",
    ]);
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/comedores/observacion/8/editar");
    expect(screen.getByRole("link", { name: "Eliminar" }).getAttribute("href")).toBe("/comedores/observacion/8/eliminar");
    const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
    fireEvent.click(screen.getByRole("link", { name: "Imprimir" }));
    expect(print).toHaveBeenCalledTimes(1);
    fireEvent.click(document.querySelector('[data-card-widget="collapse"]')!);
    expect(document.querySelector(".card")?.className).toContain("collapsed-card");
  });

  it("renders the shared soft-delete confirmation with the observation breadcrumb and posts to the API", async () => {
    serve(baja());
    const assign = vi.spyOn(bajaNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/comedores/3" }, status: 200 });
    setup("/comedores/observacion/8/eliminar");
    expect(await screen.findByText("Atención!")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}8/eliminar/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Espacio Comunitario - Comedor Sintético"));
    expect(Array.from(document.querySelectorAll(".breadcrumb-item")).map((li) => li.textContent)).toEqual(["Espacios Comunitarios", "Comedor Sintético", "Observacion - 8", "Eliminar"]);
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/comedores/observacion/8");
    fireEvent.click(screen.getByRole("button", { name: "Dar de baja" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/3"));
    expect(webPost.mock.calls[0][0]).toBe(`${API}8/eliminar/`);
  });
});
