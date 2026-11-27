import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { importarExpedientesNavigation } from "./importarExpedientes";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/importarexpedientes/";
const LIST = "/importarexpedientes/listar";
const page = (over: Record<string, unknown> = {}) => ({ is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "", ...over });
const row = (id: number, over: Record<string, unknown> = {}) => ({
  id, numero_expediente_pago: "EX-9", archivo: `importados/l${id}.csv`, periodo_pago: "03/2026", periodo_orden: "03/2026", usuario: "ana",
  fecha_subida: "12 de noviembre de 2026 a las 10:30", count_exitos: "3", count_errores: "1", importacion_completada: "No",
  detail_url: `/importarexpedientes/${id}/`, download_url: `/importarexpedientes/${id}/descargar/`, ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  filters_config: { fields: [{ name: "archivo", label: "Archivo", type: "text" }], defaultField: "archivo" },
  favorites: { section: "", url: "/filtros-favoritos/", detail_url_template: "/filtros-favoritos/0/" },
  urls: { list: LIST, upload: "/importarexpedientes/upload" }, results: [row(5)], page: page(), messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  batch: { id: 5, label: "Archivo importado l5.csv", importacion_completada: false }, counts: { validos: 2, errores: 1, con_acreditacion: 0 },
  can_update_acreditacion: false, can_manage: true, motivo_no_deshacer: null, urls: { list: LIST, ajax: "/importarexpedientes/5/ajax/" }, query: "",
  results: [{ id: 1, batch_id: 5, fila: "2", mensaje: "Fila 2 mal", archivo: "Archivo importado l5.csv", detail_url: "/importarexpedientes/5/" }],
  page: page(), messages: [], ...over,
});
const FIELD = { name: "file", label: "Archivo CSV o XLSX", type: "file", required: true, accept: ".csv,.xlsx" };
const upload = (over: Record<string, unknown> = {}) => ({
  fields: [FIELD, { name: "delimiter", label: "Delimitador", type: "select", required: true, accept: "", choices: [{ value: ",", label: "Coma (,)" }, { value: ";", label: "Punto y coma (;)" }], value: "," },
    { name: "has_header", label: "Incluye cabecera", type: "checkbox", required: false, accept: "", value: true }],
  list_url: LIST, messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
let assign: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  assign = vi.spyOn(importarExpedientesNavigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); assign.mockRestore(); vi.restoreAllMocks(); });

describe("Importar expedientes route", () => {
  it("owns the four native paths", () => {
    expect(findRoute(LIST)?.params).toEqual({ kind: "list", id: "" });
    expect(findRoute("/importarexpedientes/5/")?.params).toEqual({ kind: "detail", id: "5" });
    expect(findRoute("/importarexpedientes/upload")?.params).toEqual({ kind: "upload", id: "" });
    expect(findRoute("/importarexpedientes/5/fechas-acreditacion/")?.params).toEqual({ kind: "dates", id: "5" });
    for (const other of ["/importarexpedientes/listar/", "/importarexpedientes/ajax/", "/importarexpedientes/5/descargar/", "/importarexpedientes/5"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-importar-expedientes");
    }
  });

  it("lists the native cells, the actions and the page count", async () => {
    serve(list({ messages: [{ message: "2 filas válidas.", level: "success" }] }));
    setup(`${LIST}?page=1`);
    await screen.findByText("Buscar Expedientes de Pago");
    expect(webGet).toHaveBeenCalledWith(`${API}?page=1`, expect.anything());
    const rows = screen.getAllByRole("row");
    expect(within(rows[0]).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(
      ["Nº Expediente de Pago", "Archivo", "Periodo", "Usuario", "Fecha de Subida", "Válidos", "Errores", "Importacion Completada", "Acciones"]);
    expect(within(rows[1]).getAllByRole("cell").map((c) => c.textContent).slice(0, 8)).toEqual(
      ["EX-9", "importados/l5.csv", "03/2026", "ana", "12 de noviembre de 2026 a las 10:30", "3", "1", "No"]);
    expect(within(rows[1]).getByRole("link", { name: "Descargar" }).getAttribute("href")).toBe("/importarexpedientes/5/descargar/");
    expect(screen.getByRole("link", { name: /Importar Nuevo Archivo/ }).getAttribute("href")).toBe("/importarexpedientes/upload");
    expect(await screen.findByText("2 filas válidas.")).toBeTruthy();
    expect(screen.getByText("Se encontraron 1 resultados")).toBeTruthy();
  });

  it("shows the native empty row", async () => {
    serve(list({ results: [], page: page({ count: 0 }) }));
    setup(LIST);
    expect(await screen.findByText("No hay expedientes disponibles.")).toBeTruthy();
  });

  it("sorts the visible page like listSort.js", async () => {
    serve(list({ results: [row(1, { archivo: "b.csv" }), row(2, { archivo: "a.csv" })] }));
    setup(LIST);
    await screen.findByText("b.csv");
    fireEvent.click(screen.getByRole("columnheader", { name: "Archivo" }));
    const cells = () => screen.getAllByRole("row").slice(1).map((r) => within(r).getAllByRole("cell")[1].textContent);
    expect(cells()).toEqual(["a.csv", "b.csv"]);
  });

  it("renders the detail counters and the error table", async () => {
    serve(detail());
    setup("/importarexpedientes/5/");
    await screen.findByText("Registros Válidos");
    expect(screen.getByText("Fila 2 mal")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Completar Importación/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Eliminar Archivo/ })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Deshacer importación/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /Actualizar fechas/ })).toBeNull();
  });

  it("hides the delete and undo buttons without the manage codes", async () => {
    serve(detail({ can_manage: false }));
    setup("/importarexpedientes/5/");
    await screen.findByText("Registros Válidos");
    expect(screen.queryByRole("button", { name: /Eliminar Archivo/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Deshacer importación/ })).toBeNull();
  });

  it("offers the undo of an imported batch or explains why it cannot", async () => {
    const batch = { id: 5, label: "Archivo importado l5.csv", importacion_completada: true };
    serve(detail({ batch }));
    setup("/importarexpedientes/5/");
    expect(await screen.findByRole("button", { name: /Deshacer importación/ })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Eliminar Archivo/ })).toBeNull();
    cleanup();
    serve(detail({ batch, motivo_no_deshacer: "Solo se puede deshacer el último lote importado." }));
    setup("/importarexpedientes/5/");
    expect(await screen.findByText("Solo se puede deshacer el último lote importado.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Deshacer importación/ })).toBeNull();
  });

  it("shows the dates link only when the API allows it", async () => {
    serve(detail({ can_update_acreditacion: true }));
    setup("/importarexpedientes/5/");
    expect((await screen.findByRole("link", { name: /Actualizar fechas de acreditación/ })).getAttribute("href")).toBe("/importarexpedientes/5/fechas-acreditacion/");
  });

  it("searches the errors through the API", async () => {
    serve(detail());
    setup("/importarexpedientes/5/");
    await screen.findByText("Fila 2 mal");
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 }
      : { data: detail({ results: [], page: page({ count: 0 }) }), status: 200 }));
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: "Buscar" }));
    await waitFor(() => expect(webGet).toHaveBeenCalledWith(`${API}5/?busqueda=9`, expect.anything()));
    expect(await screen.findByText("No hay errores registrados para este archivo.")).toBeTruthy();
    expect(screen.getByText("0 resultado(s) encontrado(s)")).toBeTruthy();
  });

  it("asks for confirmation, posts once and follows the redirect", async () => {
    serve(detail());
    webPost.mockResolvedValue({ data: { ok: true, redirect: LIST }, status: 200 });
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValue(true);
    setup("/importarexpedientes/5/");
    const button = await screen.findByRole("button", { name: /Completar Importación/ });
    fireEvent.click(button);
    expect(confirm).toHaveBeenCalledWith("¿Confirmar importación del lote?");
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.click(button);
    fireEvent.click(button);
    await waitFor(() => expect(assign).toHaveBeenCalledWith(LIST));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}5/importar/`);
  });

  it("follows the native redirect after a 409 and confirms the delete text", async () => {
    serve(detail());
    webPost.mockResolvedValue({ data: { ok: false, redirect: LIST }, status: 409 });
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    setup("/importarexpedientes/5/");
    fireEvent.click(await screen.findByRole("button", { name: /Eliminar Archivo/ }));
    expect(confirm).toHaveBeenCalledWith("¿Eliminar este archivo? Se borra el lote completo y no se puede recuperar.");
    await waitFor(() => expect(assign).toHaveBeenCalledWith(LIST));
    expect(webPost.mock.calls[0][0]).toBe(`${API}5/eliminar/`);
  });

  it("does not resend after an uncertain result", async () => {
    serve(detail());
    webPost.mockRejectedValue({ response: { status: 504, data: { uncertain: true } } });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    setup("/importarexpedientes/5/");
    fireEvent.click(await screen.findByRole("button", { name: /Completar Importación/ }));
    expect(await screen.findByText("No se pudo confirmar el resultado. Revise el listado de lotes antes de volver a intentar.")).toBeTruthy();
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(assign).not.toHaveBeenCalled();
  });

  it("renders the upload form and blocks a second submit", async () => {
    serve(upload());
    webPost.mockResolvedValue({ data: { ok: true, redirect: LIST }, status: 200 });
    setup("/importarexpedientes/upload");
    await screen.findByText("Archivo CSV o XLSX");
    expect(screen.getByLabelText(/Delimitador/)).toBeTruthy();
    expect((screen.getByLabelText("Incluye cabecera") as HTMLInputElement).checked).toBe(true);
    const form = document.getElementById("csv-upload-form") as HTMLFormElement;
    fireEvent.submit(form);
    fireEvent.submit(form);
    await waitFor(() => expect(assign).toHaveBeenCalledWith(LIST));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}subir/`);
  });

  it("shows the rejection messages in place with their level", async () => {
    serve(upload());
    webPost.mockResolvedValue({ data: { ok: false, messages: [{ message: "Archivo sin cabecera no soportado por defecto.", level: "error" }, { message: "aviso", level: "warning" }] }, status: 400 });
    setup("/importarexpedientes/upload");
    await screen.findByText("Archivo CSV o XLSX");
    fireEvent.submit(document.getElementById("csv-upload-form") as HTMLFormElement);
    expect((await screen.findAllByText("Archivo sin cabecera no soportado por defecto.")).length).toBe(2);
    expect(screen.getAllByText("aviso").some((n) => n.closest(".alert-warning"))).toBe(true);
    expect(assign).not.toHaveBeenCalled();
    await waitFor(() => expect((document.getElementById("csv-upload-btn") as HTMLButtonElement).disabled).toBe(false));
  });

  it("renders the dates page with its literal text", async () => {
    serve({ batch: { id: 5, label: "x" }, fields: [FIELD], list_url: LIST, messages: [] });
    setup("/importarexpedientes/5/fechas-acreditacion/");
    expect(await screen.findByRole("heading", { name: "Actualizar fechas de acreditación" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Actualizar fechas/ })).toBeTruthy();
    expect(screen.getByText(/formato/).textContent).toContain("DD/MM/AAAA");
  });

  it("shows the access screen on 403", async () => {
    serve({ detail: "x" }, 403);
    setup(LIST);
    await waitFor(() => expect(screen.queryByText("Cargando lotes…")).toBeNull());
    expect(screen.queryByText("Buscar Expedientes de Pago")).toBeNull();
  });
});
