import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { reporteValid } from "./vatReporte";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/reportes/inscripciones-asistencias/";
const filter = (key: string, label: string, over: Record<string, unknown> = {}) => ({
  key, label, type: "select", permanent: false, value: "", options: [{ value: "", label: "Todos" }, { value: "3", label: "Opcion tres" }], ...over,
});
const filters = (over: Record<string, Record<string, unknown>> = {}) => [
  filter("nivel", "Nivel", { permanent: true, value: "inet", options: [{ value: "centro", label: "Centro" }, { value: "provincia", label: "Provincia" }, { value: "inet", label: "INET (Global)" }] }),
  filter("group_by", "Agrupar por", { permanent: true, value: "centro", options: [{ value: "centro", label: "Centro" }, { value: "comision", label: "Comisión" }] }),
  filter("fecha_desde", "Fecha desde", { type: "date" }),
  filter("fecha_hasta", "Fecha hasta", { type: "date" }),
  filter("provincia_id", "Provincia"),
  filter("estado", "Estado inscripción"),
].map((f) => ({ ...f, ...(over[f.key] ?? {}) }));
const row = (over: Record<string, string> = {}) => ({
  grupo: "CFP Uno", inscripciones_total: "2", preinscriptos: "1", en_espera: "0", inscriptos: "1", validados_presencial: "0", completados: "0", abandonados: "0",
  registros_asistencia: "1", presentes: "1", ausentes: "0", porcentaje_asistencia: "100,0", sesiones_programadas: "1", sesiones_realizadas: "1", ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  documento: "40111001", persona: "Apellido1, Nombre1", estado: "inscripta", con_voucher: false, centro: "CFP Uno", comision: "COM-1", curso: "Curso 1", fecha: "01/04/2026 10:00", ...over,
});
const data = (over: Record<string, unknown> = {}) => ({
  nivel_pill: "INET", filters: filters(), resumen: { inscripciones_total: "2", presentes: "1", ausentes: "0", porcentaje_asistencia: "100,0" },
  group_label: "Centro", group_label_lower: "centro", rows: [row(), row({ grupo: "CFP Dos", inscripciones_total: "5" })],
  page: { is_paginated: false, number: 1, num_pages: 1, count: 2, previous: null, next: null, summary: true },
  querystring: "", querystring_detalle: "",
  detalle: { rows: [detail(), detail({ con_voucher: true, persona: "Otro, Nombre" })], info: { number: 1, num_pages: 1, count: "2", start_index: "1", end_index: "2", previous: null, next: null } },
  urls: { list: "/vat/reportes/inscripciones-asistencias/", vat: "/vat/centros/" }, messages: [], ...over,
});

function serve(payload: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: payload, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT reporte route", () => {
  it("owns the report path only", () => {
    expect(findRoute("/vat/reportes/inscripciones-asistencias/")?.route.name).toBe("vat-reporte");
    for (const other of ["/vat/reportes/inscripciones-asistencias", "/vat/reportes/"]) expect(findRoute(other)?.route.name).not.toBe("vat-reporte");
  });

  it("renders the title, metrics, summary and detail tables with the native texts", async () => {
    serve(data());
    setup("/vat/reportes/inscripciones-asistencias/");
    expect(await screen.findByRole("heading", { level: 1, name: "Reporte general de inscriptos y asistencias" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - VAT - Reporte de Inscriptos y Asistencias"));
    expect(document.querySelector(".rep-status-pill")?.textContent).toBe("Nivel: INET");
    expect(Array.from(document.querySelectorAll(".rep-metric__value")).map((n) => n.textContent)).toEqual(["2", "1", "0", "100,0%"]);
    expect(screen.getByText("Resumen por centro")).toBeTruthy();
    expect(screen.getByText("Página 1 de 1 · 2 grupos")).toBeTruthy();
    expect(screen.getByText("Mostrando 1-2 de 2")).toBeTruthy();
    expect(screen.getByText("(2 en total)")).toBeTruthy();
    expect(screen.getByText("Sin Plan")).toBeTruthy();
    expect(document.querySelector(".rep-pill--vat")?.textContent).toBe("VAT");
    expect(document.querySelector("a[href='/vat/centros/']")?.textContent).toBe("VAT");
    expect(document.querySelector(".pagination, .rep-pager")).toBeNull();
  });

  it("keeps the native downloads as links with the current filters", async () => {
    serve(data({ querystring: "estado=inscripta" }));
    setup("/vat/reportes/inscripciones-asistencias/?estado=inscripta");
    await screen.findByText("Resumen CSV");
    const href = (name: string) => screen.getByRole("link", { name }).getAttribute("href");
    expect(href("Resumen CSV")).toBe("?estado=inscripta&export=csv");
    expect(href("Resumen Excel")).toBe("?estado=inscripta&export=xlsx");
    expect(href("Detalle CSV")).toBe("?estado=inscripta&export=detalle_csv");
    expect(href("Detalle Excel")).toBe("?estado=inscripta&export=detalle_xlsx");
  });

  it("shows only the filters with a value, adds and removes the others like the native script", async () => {
    serve(data({ filters: filters({ estado: { value: "3" }, fecha_desde: { value: "2026-04-01" }, provincia_id: { value: "999" } }) }));
    setup("/vat/reportes/inscripciones-asistencias/?estado=3");
    await screen.findByText("2 filtros aplicados");
    const hidden = () => Array.from(document.querySelectorAll(".rep-field.is-hidden .rep-field__label")).map((n) => n.textContent);
    expect(hidden()).toEqual(["Fecha hasta", "Provincia"]);
    const add = screen.getByLabelText("Agregar filtro") as HTMLSelectElement;
    expect(Array.from(add.options).map((o) => o.textContent)).toEqual(["+ Agregar filtro…", "Fecha hasta", "Provincia"]);
    fireEvent.change(add, { target: { value: "provincia_id" } });
    await waitFor(() => expect(screen.getByText("3 filtros aplicados")).toBeTruthy());
    expect(document.activeElement?.id).toBe("id_provincia_id");
    fireEvent.click(screen.getByRole("button", { name: "Quitar filtro Estado inscripción" }));
    expect(screen.getByText("2 filtros aplicados")).toBeTruthy();
    expect((document.getElementById("id_estado") as HTMLSelectElement).value).toBe("");
    expect(screen.queryByRole("button", { name: "Quitar filtro Nivel" })).toBeNull();
    for (const n of ["Fecha desde", "Provincia"]) fireEvent.click(screen.getByRole("button", { name: `Quitar filtro ${n}` }));
    expect(screen.getByText("Sin filtros adicionales — se muestra todo.")).toBeTruthy();
    expect(document.querySelector("form[method=get]")).toBeTruthy();
  });

  it("filters the visible summary rows and counts them", async () => {
    serve(data());
    setup("/vat/reportes/inscripciones-asistencias/");
    const box = await screen.findByPlaceholderText("Filtrar filas visibles");
    expect(screen.getByText("2 filas visibles en esta página")).toBeTruthy();
    fireEvent.change(box, { target: { value: "dos" } });
    expect(screen.getByText("1 fila visible en esta página")).toBeTruthy();
    expect(document.querySelectorAll("[data-reporter-row][hidden]")).toHaveLength(1);
  });

  it("shows the pagers of the groups and of the detail", async () => {
    serve(data({
      querystring: "group_by=comision", querystring_detalle: "group_by=comision&page=2",
      page: { is_paginated: true, number: 2, num_pages: 3, count: 120, previous: 1, next: 3, summary: true },
      detalle: { rows: [detail()], info: { number: 1, num_pages: 4, count: "200", start_index: "1", end_index: "50", previous: null, next: 2 } },
    }));
    setup("/vat/reportes/inscripciones-asistencias/?group_by=comision&page=2");
    await screen.findByText("Página 2 de 3 · 120 grupos");
    const groups = document.querySelectorAll(".rep-pager")[0] as HTMLElement;
    expect(groups.querySelector(".rep-pager-prev")?.getAttribute("href")).toBe("?group_by=comision&page=1");
    expect(groups.querySelector(".rep-pager-next")?.getAttribute("href")).toBe("?group_by=comision&page=3");
    const detalle = document.querySelectorAll(".rep-pager")[1] as HTMLElement;
    expect(detalle.querySelector(".rep-pager-prev")?.className).toBe("rep-pager-prev is-disabled");
    expect(within(detalle).getByLabelText("Página siguiente").getAttribute("href")).toBe("?group_by=comision&page=2&detalle_page=2#repDetalleTabla");
  });

  it("prints the empty states without the page summary", async () => {
    serve(data({ rows: [], detalle: { rows: [], info: { number: 1, num_pages: 1, count: "0", start_index: "0", end_index: "0", previous: null, next: null } },
      page: { is_paginated: false, number: 1, num_pages: 1, count: 0, previous: null, next: null, summary: false } }));
    setup("/vat/reportes/inscripciones-asistencias/");
    expect(await screen.findByText("No hay datos para los filtros seleccionados.")).toBeTruthy();
    expect(screen.getByText("No hay personas para los filtros seleccionados.")).toBeTruthy();
    expect(document.querySelector("#reporteQuickCounter")?.textContent).toBe("");
    expect(screen.queryByText(/^Página /)).toBeNull();
  });

  it("opens the help menu and runs the tour of the screen without starting by itself", async () => {
    serve(data());
    const run = vi.fn();
    (window as unknown as { SisocVatTour: unknown }).SisocVatTour = { runSection: run, runGeneral: vi.fn(), resetSeen: vi.fn() };
    setup("/vat/reportes/inscripciones-asistencias/");
    const button = await screen.findByRole("button", { name: /Tour de ayuda/ });
    expect(run).not.toHaveBeenCalled();
    expect(button.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(button);
    expect(button.getAttribute("aria-expanded")).toBe("true");
    fireEvent.click(screen.getByRole("link", { name: /Tour de esta pantalla/ }));
    expect(run).toHaveBeenCalledTimes(1);
    expect(button.getAttribute("aria-expanded")).toBe("false");
    delete (window as unknown as { SisocVatTour?: unknown }).SisocVatTour;
  });

  it("validates the payload shape", () => {
    expect(reporteValid(data())).toBe(true);
    expect(reporteValid({ ...data(), rows: [{ grupo: "x" }] })).toBe(false);
    expect(reporteValid({ ...data(), filters: [{ key: "x" }] })).toBe(false);
  });
});
