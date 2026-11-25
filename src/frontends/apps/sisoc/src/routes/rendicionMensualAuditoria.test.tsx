import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { auditoriaNavigation, busquedaValid, gestionValid } from "./rendicionMensualAuditoria";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const PREFIX = "/rendicioncuentasmensual/rendicioncuentasmensual";
const API = "web/comedores/rendicioncuentasmensual/auditoria/";
const campo = (name: string, label: string, over: Record<string, unknown> = {}) => ({ name, label, required: false, value: "", ...over });
const busqueda = (over: Record<string, unknown> = {}) => ({
  filtro: { value: "proyecto", choices: [{ value: "proyecto", label: "Proyecto" }, { value: "organizacion", label: "Organización" }, { value: "periodo", label: "Período" }], errors: [] },
  busqueda: { value: "P-77", maxlength: 120, errors: [] }, busqueda_realizada: true, busqueda_valida: true,
  page: { is_paginated: true, number: 1, count: 41, previous: null, next: 2, range: [1, 2, "…", 3], query_prefix: "busqueda=P-77&" },
  filas: [{ id: 5, proyecto: "P-77", organizacion: "Org <Norte>", convenio_numero: "P01 · 2", periodo: "01/03/2026 al 31/03/2026", validada: "No", gestionar_url: `${PREFIX}/auditoria/5/?origen=busqueda`, aria_label: "Gestionar auditoría de la rendición 2, convenio P01, proyecto P-77" }],
  urls: { listado: `${PREFIX}/listado/`, limpiar: `${PREFIX}/auditoria/`, volver: `${PREFIX}/listado/` }, messages: [], ...over,
});
const gestion = (over: Record<string, unknown> = {}, form: Record<string, unknown> = {}) => ({
  rendicion: { id: 5, numero: "2", convenio: "P01", periodo: "01/03/2026 al 31/03/2026", organizacion: "Org Norte", proyecto: "P-77", convenio_dato: "P01", linea_programatica: "Abordaje Comunitario - Linea Tradicional" },
  form: {
    ya_validada: false, validada: { checked: false, errors: [] },
    genera_acta_auditoria: campo("genera_acta_auditoria", "¿Se genera acta de auditoría?", { required: true, value: "False", choices: [{ value: "False", label: "No" }, { value: "True", label: "Sí" }] }),
    rendiciones_incluidas: { errors: [], opciones: [{ value: "9", id: "id_rendiciones_incluidas_0", checked: false, numero: "1", convenio: "P01", periodo: "01/02/2026 al 28/02/2026", linea: "Abordaje Comunitario - Linea Tradicional" }] },
    acta_auditoria: campo("acta_auditoria", "Acta de Auditoría"),
    resultado: campo("resultado", "Resultado de la Auditoría", { choices: [{ value: "", label: "Seleccioná un resultado" }, { value: "finalizada", label: "Finalizada Sin Observaciones" }, { value: "finalizada_con_observaciones", label: "Finalizada con Observaciones" }] }),
    observaciones: campo("observaciones", "Observaciones", { rows: 3 }), documento_regularizacion: campo("documento_regularizacion", "Acta Complementaria"),
    errors: {}, non_field_errors: [], ...form,
  },
  resumenes: [
    { id: 5, actual: true, titulo: "Rendición 2 · P01 · 01/03/2026 al 31/03/2026", documentos: [{ categoria: "Formulario II - Resumen", nombre: "doc1", estado_text: "Presentado", ver_url: `${PREFIX}/documento/1/ver/` }] },
    { id: 9, actual: false, titulo: "Rendición 1 · P01 · 01/02/2026 al 28/02/2026", documentos: [] },
  ],
  urls: { listado: `${PREFIX}/listado/`, volver: `${PREFIX}/detalle/5/` }, volver_a_busqueda: false, messages: [], ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
function setup(url: string) {
  window.history.replaceState({}, "", url);
  return render(<App />);
}
const el = (id: string) => document.getElementById(id) as HTMLInputElement;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("Rendición mensual audit routes", () => {
  it("owns only the search and the form paths with the repeated prefix", () => {
    expect(findRoute(`${PREFIX}/auditoria/`)?.route.name).toBe("comedores-rendicion-mensual-auditoria");
    expect(findRoute(`${PREFIX}/auditoria/5/`)?.route.name).toBe("comedores-rendicion-mensual-auditoria");
    for (const other of [`${PREFIX}/auditoria/5`, `${PREFIX}/auditoria/x/`, "/rendicioncuentasmensual/auditoria/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-rendicion-mensual-auditoria");
    }
  });

  it("validates both payloads", () => {
    expect(busquedaValid(busqueda())).toBe(true);
    expect(busquedaValid(busqueda({ urls: { listado: "https://x.example/", limpiar: "/a/", volver: "/b/" } }))).toBe(false);
    expect(gestionValid(gestion())).toBe(true);
    expect(gestionValid(gestion({ volver_a_busqueda: "no" }))).toBe(false);
  });
});

describe("Search", () => {
  it("renders the rows, the native links and the pagination", async () => {
    serve(busqueda());
    setup(`${PREFIX}/auditoria/?filtro=proyecto&busqueda=P-77`);
    await screen.findByText("Rendiciones disponibles");
    expect(webGet).toHaveBeenCalledWith(`${API}?filtro=proyecto&busqueda=P-77`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Auditoría de rendiciones"));
    expect(screen.getByText("Org <Norte>").tagName).toBe("TD");
    const gestionar = screen.getByRole("link", { name: "Gestionar auditoría de la rendición 2, convenio P01, proyecto P-77" });
    expect(gestionar.getAttribute("href")).toBe(`${PREFIX}/auditoria/5/?origen=busqueda`);
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?busqueda=P-77&page=2");
    expect(screen.getByText("Se encontraron 41 resultados")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Limpiar" }).getAttribute("href")).toBe(`${PREFIX}/auditoria/`);
    expect(screen.getByRole("link", { name: "Rendiciones" }).getAttribute("href")).toBe(`${PREFIX}/listado/`);
    expect(el("id_busqueda").required).toBe(true);
    expect(el("id_busqueda").maxLength).toBe(120);
  });

  it("changes the placeholder and the help text with the filter", async () => {
    serve(busqueda());
    setup(`${PREFIX}/auditoria/`);
    await screen.findByText("Rendiciones disponibles");
    expect(el("id_busqueda").placeholder).toBe("Código o nombre del proyecto");
    fireEvent.change(el("id_filtro"), { target: { value: "periodo" } });
    expect(el("id_busqueda").placeholder).toBe("MM/AAAA o DD/MM/AAAA");
    expect(document.getElementById("ayuda-busqueda-auditoria")?.textContent).toContain("Ingresá un mes, una fecha o un año");
  });

  it("shows the empty, the invalid and the not-searched states", async () => {
    serve(busqueda({ filas: [], page: { is_paginated: false, number: 1, count: 0, previous: null, next: null, range: [], query_prefix: "" } }));
    setup(`${PREFIX}/auditoria/`);
    await screen.findByText("No hay rendiciones disponibles para esta búsqueda. Probá otro texto o filtro.");
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
    cleanup();
    serve(busqueda({ filas: [], busqueda_valida: false, busqueda: { value: "xx", maxlength: 120, errors: ["Ingresá un período como MM/AAAA, DD/MM/AAAA o AAAA."] } }));
    setup(`${PREFIX}/auditoria/?busqueda=xx`);
    await screen.findByText("Ingresá un período como MM/AAAA, DD/MM/AAAA o AAAA.");
    expect(el("id_busqueda").getAttribute("aria-invalid")).toBe("true");
    expect(document.getElementById("id_busqueda_error")?.className).toBe("errorlist");
    cleanup();
    serve(busqueda({ busqueda_realizada: false, busqueda_valida: false, filas: [] }));
    setup(`${PREFIX}/auditoria/`);
    await screen.findByText("Seleccioná un filtro e ingresá un texto para buscar rendiciones.");
  });
});

describe("Audit form", () => {
  it("renders the data, the fixed current rendición and hides the act fields", async () => {
    serve(gestion());
    setup(`${PREFIX}/auditoria/5/?origen=busqueda`);
    await screen.findByText("Información general · Rendición 2");
    expect(webGet).toHaveBeenCalledWith(`${API}5/?origen=busqueda`, expect.anything());
    expect(screen.getByText("Org Norte").tagName).toBe("DD");
    expect(el("id_validada").required).toBe(true);
    expect(document.getElementById("campos-acta")?.hidden).toBe(true);
    expect(document.getElementById("campos-observaciones")?.hidden).toBe(true);
    expect(el("rendicion-actual-incluida").disabled).toBe(true);
    expect(el("id_rendiciones_incluidas_0").disabled).toBe(true);
    const summaries = document.querySelectorAll<HTMLElement>(".js-resumen-rendicion");
    expect([summaries[0].hidden, summaries[1].hidden]).toEqual([false, true]);
    expect(screen.getByRole("link", { name: "Volver al detalle" }).getAttribute("href")).toBe(`${PREFIX}/detalle/5/`);
    expect(screen.getByRole("button", { name: "Guardar y cerrar Auditoría" })).toBeTruthy();
  });

  it("shows the act fields, the observations and the selected summaries like the native script", async () => {
    serve(gestion());
    setup(`${PREFIX}/auditoria/5/`);
    await screen.findByText("Información general · Rendición 2");
    fireEvent.change(el("id_genera_acta_auditoria"), { target: { value: "True" } });
    expect(document.getElementById("campos-acta")?.hidden).toBe(false);
    expect(el("id_resultado").required).toBe(true);
    expect(el("id_rendiciones_incluidas_0").disabled).toBe(false);
    expect(el("rendicion-actual-incluida").disabled).toBe(true);
    expect(document.getElementById("campos-observaciones")?.hidden).toBe(true);
    fireEvent.change(el("id_resultado"), { target: { value: "finalizada_con_observaciones" } });
    expect(document.getElementById("campos-observaciones")?.hidden).toBe(false);
    expect(el("id_observaciones").required).toBe(true);
    fireEvent.click(el("id_rendiciones_incluidas_0"));
    expect(document.querySelectorAll<HTMLElement>(".js-resumen-rendicion")[1].hidden).toBe(false);
  });

  it("shows an already validated rendición as fixed", async () => {
    serve(gestion({}, { ya_validada: true }));
    setup(`${PREFIX}/auditoria/5/`);
    await screen.findByText("Validación guardada. No se puede modificar.");
    expect(document.getElementById("id_validada")).toBeNull();
    expect(document.getElementById("auditoria-form")?.getAttribute("data-validada")).toBe("true");
  });

  it("posts the enabled fields as multipart with the query and follows the redirect", async () => {
    const assign = vi.spyOn(auditoriaNavigation, "assign").mockImplementation(() => {});
    serve(gestion());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: `${PREFIX}/detalle/5/` } });
    setup(`${PREFIX}/auditoria/5/?origen=busqueda`);
    await screen.findByText("Información general · Rendición 2");
    fireEvent.click(el("id_validada"));
    fireEvent.submit(document.getElementById("auditoria-form")!);
    await waitFor(() => expect(assign).toHaveBeenCalledWith(`${PREFIX}/detalle/5/`));
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(`${API}5/?origen=busqueda`);
    expect(body).toBeInstanceOf(FormData);
    expect([...(body as FormData).keys()].sort()).toEqual(["csrfmiddlewaretoken", "genera_acta_auditoria", "validada"]);
  });

  it("shows the native errors after a rejected post and keeps the typed choices", async () => {
    serve(gestion());
    const rechazado = gestion({}, {
      validada: { checked: false, errors: ["Marcá Validada para poder guardar la auditoría."] },
      genera_acta_auditoria: campo("genera_acta_auditoria", "¿Se genera acta de auditoría?", { required: true, value: "True", choices: [{ value: "False", label: "No" }, { value: "True", label: "Sí" }] }),
      resultado: campo("resultado", "Resultado de la Auditoría", { value: "finalizada_con_observaciones", choices: [{ value: "", label: "Seleccioná un resultado" }, { value: "finalizada_con_observaciones", label: "Finalizada con Observaciones" }] }),
      errors: { observaciones: [{ message: "Ingresá las observaciones de auditoría." }] }, non_field_errors: ["Error general"],
    });
    webPost.mockResolvedValue({ status: 400, data: rechazado });
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    setup(`${PREFIX}/auditoria/5/`);
    await screen.findByText("Información general · Rendición 2");
    fireEvent.submit(document.getElementById("auditoria-form")!);
    await screen.findByText("Ingresá las observaciones de auditoría.");
    expect(scroll).toHaveBeenCalledWith(0, 0);
    expect(screen.getByText("Marcá Validada para poder guardar la auditoría.").className).toBe("invalid-feedback d-block");
    expect(el("id_genera_acta_auditoria").value).toBe("True");
    expect(document.getElementById("campos-observaciones")?.hidden).toBe(false);
    expect(el("id_observaciones").className).toContain("is-invalid");
    expect(document.querySelector("ul.errorlist.nonfield li")?.textContent).toBe("Error general");
  });

  it("blocks the form when the outcome is unknown", async () => {
    serve(gestion());
    webPost.mockRejectedValue(new Error("network"));
    setup(`${PREFIX}/auditoria/5/`);
    await screen.findByText("Información general · Rendición 2");
    fireEvent.submit(document.getElementById("auditoria-form")!);
    await screen.findByRole("alert");
    expect((screen.getByRole("button", { name: "Guardar y cerrar Auditoría" }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
  });
});
