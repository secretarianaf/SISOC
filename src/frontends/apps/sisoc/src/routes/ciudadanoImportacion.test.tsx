import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { ciudadanoImportacionNavigation, importacionValid, loteValid } from "./ciudadanoImportacion";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const lotes = [
  { id: 4, fecha_texto: "13/11/2026 12:00", usuario_texto: "ana", estado: "completed_with_errors", creados: 2, existentes: 3, fallidos: 1, pendientes: 0, detalle_url: "/ciudadanos/importacion-masiva/lotes/4/" },
  { id: 3, fecha_texto: "12/11/2026 09:30", usuario_texto: "ana", estado: "processing", creados: 0, existentes: 0, fallidos: 0, pendientes: 8, detalle_url: "/ciudadanos/importacion-masiva/lotes/3/" },
];
const carga = (over = {}) => ({
  campo: { label: "Archivo Excel", accept: ".xlsx" }, errors: {}, plantilla_url: "/ciudadanos/importacion-masiva/plantilla/",
  volver_url: "/ciudadanos/listar", lotes, messages: [], ...over,
});
const fila = (n: number, over = {}) => ({
  fila: n, documento: `2030000000${n}`, dni: "-", sexo: "M", estado: "created", sexos_intentados: "M", intentos: 1, mensaje: "Creado", error_tipo: "",
  ciudadano_url: "/ciudadanos/ver/9", ...over,
});
const lote = (over = {}) => ({
  id: 4, archivo: "padron.xlsx", fecha_texto: "13/11/2026 12:00", estado: "failed", reanudaciones: 1, totales: 60, procesadas: 10, creados: 4,
  existentes: 3, fallidos: 2, pendientes: 1, ultimo_correcto: { documento: "30111222", fila_texto: "3" }, ultimo_intentado: { documento: "", fila_texto: "-" },
  error_mensaje: "Se cayó el servicio", error_tipo: "TimeoutError", puede_reanudar: true,
  filas: [fila(1), fila(2, { estado: "failed", mensaje: "Sin datos", error_tipo: "ValueError", ciudadano_url: null })],
  paginacion: { number: 1, num_pages: 2, previous: false, next: true },
  volver_url: "/ciudadanos/importacion-masiva/", lista_url: "/ciudadanos/listar", lote_url: "/ciudadanos/importacion-masiva/lotes/4/",
  exportar_url: "/ciudadanos/importacion-masiva/lotes/4/exportar/", reanudar_url: "/ciudadanos/importacion-masiva/lotes/4/reanudar/", messages: [], ...over,
});
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.scrollTo = vi.fn();
  window.history.replaceState({}, "", "/ciudadanos/importacion-masiva/");
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("importación masiva de ciudadanos", () => {
  it("owns only the two native URLs and validates both payloads", () => {
    expect(findRoute("/ciudadanos/importacion-masiva/")?.route.name).toBe("ciudadano-importacion");
    expect(findRoute("/ciudadanos/importacion-masiva/lotes/4/")?.route.name).toBe("ciudadano-importacion-lote");
    expect(findRoute("/ciudadanos/importacion-masiva/lotes/4")?.route.name).not.toBe("ciudadano-importacion-lote");
    expect(findRoute("/ciudadanos/importacion-masiva/plantilla/")?.route.name).not.toBe("ciudadano-importacion");
    expect(importacionValid(carga())).toBe(true);
    expect(importacionValid(carga({ plantilla_url: "http://evil/" }))).toBe(false);
    expect(importacionValid(carga({ errors: { archivo: [1] } }))).toBe(false);
    expect(loteValid(lote())).toBe(true);
    expect(loteValid(lote({ exportar_url: "http://evil/" }))).toBe(false);
    expect(loteValid(lote({ filas: [{ fila: 1 }] }))).toBe(false);
  });

  it("draws the upload form, the template download and the recent batches", async () => {
    serve(carga());
    render(<App />);
    expect(await screen.findByText("Nuevo lote")).toBeTruthy();
    expect(screen.getByText("Formato esperado")).toBeTruthy();
    expect((screen.getByLabelText(/Archivo Excel/) as HTMLInputElement).getAttribute("accept")).toBe(".xlsx");
    const plantilla = screen.getByRole("button", { name: "Descargar plantilla" });
    expect(plantilla.getAttribute("formaction")).toBe("/ciudadanos/importacion-masiva/plantilla/");
    expect(plantilla.getAttribute("formmethod")).toBe("get");
    expect(screen.getByText("Con errores")).toBeTruthy();
    expect(screen.getByText("Procesando")).toBeTruthy();
    expect(screen.getAllByRole("link", { name: "Ver detalle" }).map((a) => a.getAttribute("href"))).toEqual([
      "/ciudadanos/importacion-masiva/lotes/4/", "/ciudadanos/importacion-masiva/lotes/3/",
    ]);
  });

  it("says so when there are no batches", async () => {
    serve(carga({ lotes: [] }));
    render(<App />);
    expect(await screen.findByText("Todavia no hay lotes de importacion masiva.")).toBeTruthy();
  });

  it("uploads the file once and follows the redirect to the batch", async () => {
    serve(carga());
    const assign = vi.spyOn(ciudadanoImportacionNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/ciudadanos/importacion-masiva/lotes/9/" }, status: 200 });
    render(<App />);
    const boton = await screen.findByRole("button", { name: "Crear lote" });
    fireEvent.click(boton);
    fireEvent.click(boton);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/ciudadanos/importacion-masiva/lotes/9/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/ciudadanos/importacion-masiva/");
    expect(webPost.mock.calls[0][1]).toBeInstanceOf(FormData);
  });

  it("shows the field error of a rejected upload and clears the file", async () => {
    serve(carga());
    webPost.mockRejectedValueOnce({ response: undefined });
    webPost.mockResolvedValueOnce({ data: carga({ errors: { archivo: ["Este campo es requerido."] } }), status: 400 });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Crear lote" }));
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudo confirmar el resultado");
    fireEvent.click(screen.getByRole("button", { name: "Crear lote" }));
    expect(await screen.findByText("Este campo es requerido.")).toBeTruthy();
    expect(screen.getByLabelText(/Archivo Excel/).getAttribute("aria-invalid")).toBe("true");
    expect(window.scrollTo).toHaveBeenCalled();
  });

  it("draws the batch with counters, the last rows, the systemic error and the pagination", async () => {
    window.history.replaceState({}, "", "/ciudadanos/importacion-masiva/lotes/4/?page=1");
    serve(lote());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Lote #4" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Importacion masiva" }).getAttribute("href")).toBe("/ciudadanos/importacion-masiva/");
    expect(webGet).toHaveBeenCalledWith("web/ciudadanos/importacion-masiva/lotes/4/?page=1", expect.anything());
    expect(screen.getByText("padron.xlsx | 13/11/2026 12:00")).toBeTruthy();
    expect(screen.getByText("Se cayó el servicio")).toBeTruthy();
    expect(screen.getByText("Tipo: TimeoutError")).toBeTruthy();
    expect(screen.getByText("Todavia no se intento ninguna fila.")).toBeTruthy();
    expect(screen.getByText("Fila 3")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Exportar Excel" }).getAttribute("href")).toBe("/ciudadanos/importacion-masiva/lotes/4/exportar/");
    expect(screen.getByRole("link", { name: "Actualizar estado" }).getAttribute("href")).toBe("/ciudadanos/importacion-masiva/lotes/4/");
    expect(screen.getAllByRole("link", { name: "Ver" }).map((a) => a.getAttribute("href"))).toEqual(["/ciudadanos/ver/9"]);
    expect(screen.getByText("Pagina 1 de 2")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Siguiente" }).getAttribute("href")).toBe("?page=2");
    expect(screen.queryByRole("link", { name: "Anterior" })).toBeNull();
  });

  it("shows the refresh hint for a running batch and hides Reanudar", async () => {
    window.history.replaceState({}, "", "/ciudadanos/importacion-masiva/lotes/4/");
    serve(lote({ estado: "processing", error_mensaje: "", error_tipo: "", puede_reanudar: false, filas: [], paginacion: { number: 1, num_pages: 1, previous: false, next: false } }));
    render(<App />);
    expect(await screen.findByText(/El lote se procesa fuera de la request web/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Reanudar" })).toBeNull();
    expect(screen.getByText("Aun no hay filas registradas para este lote.")).toBeTruthy();
    expect(screen.queryByRole("navigation", { name: "Paginacion de filas" })).toBeNull();
  });

  it("resumes a failed batch once and follows the redirect; a refusal stays on the page", async () => {
    window.history.replaceState({}, "", "/ciudadanos/importacion-masiva/lotes/4/");
    serve(lote());
    const assign = vi.spyOn(ciudadanoImportacionNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValueOnce({ data: { detail: "Sin permiso" }, status: 403 });
    webPost.mockResolvedValueOnce({ data: { ok: true, redirect: "/ciudadanos/importacion-masiva/lotes/4/" }, status: 200 });
    render(<App />);
    const boton = await screen.findByRole("button", { name: "Reanudar" });
    fireEvent.click(boton);
    expect((await screen.findByRole("alert")).textContent).toBe("Sin permiso");
    expect(assign).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Reanudar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/ciudadanos/importacion-masiva/lotes/4/"));
    expect(webPost.mock.calls.map((c) => c[0])).toEqual(["web/ciudadanos/importacion-masiva/lotes/4/reanudar/", "web/ciudadanos/importacion-masiva/lotes/4/reanudar/"]);
  });
});
