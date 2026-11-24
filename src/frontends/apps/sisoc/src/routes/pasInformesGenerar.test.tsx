import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const OPTIONS = {
  breadcrumb: [{ text: "PAS", url: "/pas/listar" }, { text: "Informes", url: "/pas/informes" }, { text: "Generar", url: null }],
  estados: [{ id: 1, nombre: "Activo" }, { id: 2, nombre: "Baja" }],
  avisos: [{ id: 5, texto: "101 - Alta" }],
  provincias: [{ id: 9, nombre: "Provincia A" }],
  municipios: [],
};
const columns = [{ key: "a", label: "IdPersona" }, { key: "b", label: "Apellido" }];
const bytes = (value: string) => new TextEncoder().encode(value).buffer as ArrayBuffer;

function serve(options: unknown = OPTIONS) {
  webGet.mockImplementation((url: string, config?: { params?: { provincia: string } }) => Promise.resolve(
    url === "web/session/" ? { data: readyContext, status: 200 }
      : { data: config?.params ? { ...OPTIONS, municipios: [{ id: 70, nombre: "Municipio A" }] } : options, status: 200 }));
}
async function open() {
  window.history.replaceState({}, "", "/pas/informes/generar");
  render(<App />);
  await screen.findByRole("heading", { name: "Rangos temporales" });
}
const field = (id: string) => document.getElementById(id) as HTMLInputElement & HTMLSelectElement;
const sent = (url: string) => webPost.mock.calls.find((c) => c[0] === url) as [string, URLSearchParams, Record<string, unknown>];

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: vi.fn(() => "blob:csv"), revokeObjectURL: vi.fn() }));
});
afterEach(() => cleanup());

describe("PAS informes request route", () => {
  it("owns only the native request URL", () => {
    expect(findRoute("/pas/informes/generar")?.route.name).toBe("pas-informes-generar");
    expect(findRoute("/pas/informes/generar/")?.route.name).not.toBe("pas-informes-generar");
  });

  it("renders the native form: sections, fields in order, empty labels and buttons", async () => {
    serve();
    await open();
    await waitFor(() => expect(document.title).toContain("Generar informe PAS"));
    expect([...document.querySelectorAll(".section-title")].map((h) => h.textContent)).toEqual(
      ["Rangos temporales", "Estado y motivos", "Filtros sugeridos"]);
    expect([...document.querySelectorAll("#pasInformeForm label")].map((l) => l.textContent)).toEqual([
      "Fecha creación desde", "Fecha creación hasta", "Fecha de cambios desde", "Fecha de cambios hasta", "Estado anterior", "Estado resultante",
      "Estado actual", "Aviso del cambio", "Aviso actual", "Provincia", "Municipio", "DNI", "IdPersona", "Usuario que modificó"]);
    expect([...field("id_estado_actual").options].map((o) => o.text)).toEqual(["Todos", "Activo", "Baja"]);
    expect([...field("id_aviso_actual").options].map((o) => o.text)).toEqual(["Todos", "101 - Alta"]);
    expect([...field("id_provincia").options].map((o) => o.text)).toEqual(["Todas", "Provincia A"]);
    expect([...field("id_municipio").options].map((o) => o.text)).toEqual(["Todos"]);
    expect(field("id_usuario_cambio").placeholder).toBe("Usuario, nombre o apellido");
    expect([...document.querySelectorAll(".d-flex.justify-content-between.mb-3 .btn, .sticky-actions .btn")].map((b) => b.textContent?.trim())).toEqual(["Cancelar", "Volver", "Previsualizar", "Realizar informe"]);
    expect(document.querySelector(".sticky-actions a")?.getAttribute("href")).toBe("/pas/informes");
    expect(document.getElementById("pasInformePreview")).toBeNull();
  });

  it("reloads the municipios of the chosen province and resets the list", async () => {
    serve();
    await open();
    fireEvent.change(field("id_provincia"), { target: { value: "9" } });
    await waitFor(() => expect([...field("id_municipio").options].map((o) => o.text)).toEqual(["---------", "Municipio A"]));
    expect(webGet).toHaveBeenCalledWith("web/pas/informes/opciones/", expect.objectContaining({ params: { provincia: "9" } }));
    fireEvent.change(field("id_provincia"), { target: { value: "" } });
    expect([...field("id_municipio").options].map((o) => o.text)).toEqual(["---------"]);
  });

  it("previews: text, columns, rows and the empty result", async () => {
    serve();
    webPost.mockResolvedValueOnce({ status: 200, data: { ok: true, modo: "cambios", total: 51, total_personas: 40, total_cambios: 51, limit: 50, columns, rows: [{ a: 7, b: "Pérez" }] } });
    await open();
    fireEvent.change(field("id_estado_actual"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: /Previsualizar/ }));
    await screen.findByText("51 filas encontradas. Se muestran hasta 50. Modo: cambios.");
    expect(screen.getByRole("heading", { name: "Previsualizacion del CSV" })).toBeTruthy();
    expect([...document.querySelectorAll("#pasInformePreviewHead th")].map((th) => th.textContent)).toEqual(["IdPersona", "Apellido"]);
    expect([...document.querySelectorAll("#pasInformePreviewBody td")].map((td) => td.textContent)).toEqual(["7", "Pérez"]);
    const [, body] = sent("web/pas/informes/previsualizar/");
    expect(body.get("estado_actual")).toBe("2");
    expect(body.get("dni")).toBe("");

    webPost.mockResolvedValueOnce({ status: 200, data: { ok: true, modo: "registros", total: 0, total_personas: 0, total_cambios: 0, limit: 50, columns, rows: [] } });
    fireEvent.click(screen.getByRole("button", { name: /Previsualizar/ }));
    await screen.findByText("Sin resultados para los filtros aplicados.");
    expect(screen.getByText("0 filas encontradas. Se muestran hasta 50. Modo: registros.")).toBeTruthy();
  });

  it("shows the preview errors as field: message and keeps the previous table; a failure is generic", async () => {
    serve();
    webPost.mockResolvedValueOnce({ status: 200, data: { ok: true, modo: "registros", total: 1, total_personas: 1, total_cambios: 0, limit: 50, columns, rows: [{ a: 1, b: "X" }] } });
    webPost.mockResolvedValueOnce({ status: 400, data: { ok: false, errors: { fecha_cambio_hasta: ["La fecha de cambios desde no puede ser posterior a la fecha hasta."], dni: ["Introduzca un número entero."] } } });
    webPost.mockRejectedValueOnce(new Error("network"));
    await open();
    const button = () => screen.getByRole("button", { name: /Previsualiz/ });
    fireEvent.click(button());
    await screen.findByText("1 filas encontradas. Se muestran hasta 50. Modo: registros.");
    fireEvent.click(button());
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("fecha_cambio_hasta: La fecha de cambios desde no puede ser posterior a la fecha hasta.dni: Introduzca un número entero.");
    expect(alert.querySelectorAll("br")).toHaveLength(1);
    expect(document.querySelector("#pasInformePreviewBody td")?.textContent).toBe("1");
    fireEvent.click(button());
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("preview: No se pudo previsualizar el informe."));
    expect(button().textContent).toContain("Previsualizar");
  });

  it("generates once: disabled while waiting, saves the CSV with the native name, no retry", async () => {
    serve();
    let finish: (value: unknown) => void = () => undefined;
    webPost.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    await open();
    fireEvent.change(field("id_dni"), { target: { value: "30111222" } });
    const submit = screen.getByRole("button", { name: /Realizar informe/ }) as HTMLButtonElement;
    fireEvent.click(submit);
    await waitFor(() => expect(submit.disabled).toBe(true));
    fireEvent.submit(document.getElementById("pasInformeForm")!);
    expect(webPost).toHaveBeenCalledTimes(1);
    finish({ status: 200, data: bytes("﻿IdPersona\r\n"), headers: { "content-disposition": 'attachment; filename="pas-inf-000012.csv"', "x-pas-informe-id": "12" } });
    await waitFor(() => expect(submit.disabled).toBe(false));
    const [url, body, config] = sent("web/pas/informes/generar/");
    expect(url).toBe("web/pas/informes/generar/");
    expect(body.get("dni")).toBe("30111222");
    expect(config.responseType).toBe("arraybuffer");
    expect(click).toHaveBeenCalledTimes(1);
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
    expect(webPost).toHaveBeenCalledTimes(1);
    click.mockRestore();
  });

  it("shows the form errors inline and creates no download", async () => {
    serve();
    const error = { ok: false, errors: { fecha_creacion_hasta: ["La fecha de creación desde no puede ser posterior a la fecha hasta."], municipio: ["El municipio seleccionado no pertenece a la provincia elegida."] } };
    webPost.mockResolvedValueOnce({ status: 400, data: bytes(JSON.stringify(error)) });
    await open();
    fireEvent.click(screen.getByRole("button", { name: /Realizar informe/ }));
    await screen.findByText("La fecha de creación desde no puede ser posterior a la fecha hasta.");
    expect(field("id_fecha_creacion_hasta").classList.contains("is-invalid")).toBe(true);
    expect(field("id_fecha_creacion_hasta").getAttribute("aria-describedby")).toBe("id_fecha_creacion_hasta_error");
    expect(screen.getByText("El municipio seleccionado no pertenece a la provincia elegida.")).toBeTruthy();
    expect(field("id_dni").classList.contains("is-invalid")).toBe(false);
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it("an unconfirmed result is the G1 text with a link to the list and is not retried", async () => {
    serve();
    webPost.mockResolvedValueOnce({ status: 504, data: bytes('{"detail":"x","uncertain":true}') });
    await open();
    fireEvent.click(screen.getByRole("button", { name: /Realizar informe/ }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("No se pudo confirmar el resultado. Verificá el estado antes de reintentar.");
    expect(alert.querySelector("a")?.getAttribute("href")).toBe("/pas/informes");
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it("shows the access screen when the request is forbidden and on a 403 of the options", async () => {
    serve();
    webPost.mockResolvedValueOnce({ status: 403, data: bytes('{"detail":"No tienes permiso."}') });
    await open();
    fireEvent.click(screen.getByRole("button", { name: /Realizar informe/ }));
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Rangos temporales" })).toBeNull());
    cleanup();
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "x" }, status: 403 }));
    window.history.replaceState({}, "", "/pas/informes/generar");
    render(<App />);
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Rangos temporales" })).toBeNull());
    expect(screen.queryByRole("main", { name: "" })).toBeNull();
  });

  it("an invalid options payload is the load error", async () => {
    serve({ ...OPTIONS, estados: "x" });
    window.history.replaceState({}, "", "/pas/informes/generar");
    render(<App />);
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar la página.");
  });
});
