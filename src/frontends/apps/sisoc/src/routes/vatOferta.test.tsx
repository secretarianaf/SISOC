import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { ofertaDetailValid, ofertaListValid } from "./vatOferta";
import { cursoDetailValid } from "./vatCursoDetalle";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/ofertas-institucionales/";
const CURSO = "web/vat/cursos-detalle/";
const page = (over: Record<string, unknown> = {}) => ({ is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "", ...over });
const row = (over: Record<string, unknown> = {}) => ({
  id: 5, centro: "CFP 401", plan: "Electricidad v1", ciclo: "2026", estado: "activa", estado_label: "Activa", usa_voucher: false,
  detail_url: "/vat/ofertas-institucionales/5/", update_url: "/vat/ofertas-institucionales/5/editar/", delete_url: "/vat/ofertas-institucionales/5/eliminar/", ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [row()], page: page(), busqueda: "", permisos: { editar: false, eliminar: false },
  urls: { list: "/vat/ofertas-institucionales/", create: "/vat/ofertas-institucionales/nueva/" }, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 5, titulo: "Electricista - 2026", centro: "CFP 401", plan: "Electricidad v1", programa: "Programa Uno", ciclo: "2026", estado_label: "Activa",
  nombre_local: "Local Uno", costo: "$1234,50", usa_voucher: true, fecha_publicacion: "01/03/2026", observaciones: "Una nota",
  fecha_creacion: "02/05/2026 10:00", fecha_modificacion: "03/05/2026 11:30",
  urls: { list: "/vat/ofertas-institucionales/", update: "/vat/ofertas-institucionales/5/editar/", delete: "/vat/ofertas-institucionales/5/eliminar/" }, messages: [], ...over,
});
const curso = (over: Record<string, unknown> = {}) => ({
  id: 8, nombre: "Electricidad básica", centro: "CFP 401", plan_titulo: "Sin plan curricular", plan: "-", estado: "planificado", estado_label: "Planificado", tipo: "-",
  prioritario: "No", inscripcion_libre: "Sí", observaciones: "-", usa_voucher: "Sí", costo_creditos: "3", vouchers: ["Voucher Uno", "Voucher Dos"],
  comisiones_count: 4, puede_editar: true, urls: { update: "/vat/cursos/8/editar/" }, messages: [], ...over,
});

function serve(data: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
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

describe("VAT institutional offer and course detail routes", () => {
  it("own their list and detail paths and leave the rest alone", () => {
    for (const path of ["/vat/ofertas-institucionales/", "/vat/ofertas-institucionales/12/"]) expect(findRoute(path)?.route.name).toBe("vat-oferta-institucional");
    expect(findRoute("/vat/cursos/12/")?.route.name).toBe("vat-curso-detalle");
    for (const other of ["/vat/ofertas-institucionales", "/vat/ofertas-institucionales/nueva/", "/vat/ofertas-institucionales/x/", "/vat/cursos/", "/vat/cursos/nuevo/", "/vat/cursos/comisiones/4/", "/vat/cursos/12/editar/", "/vat/centros/4/panel/cursos/"]) {
      expect(["vat-oferta-institucional", "vat-curso-detalle"]).not.toContain(findRoute(other)?.route.name);
    }
  });

  it("validates the three payloads strictly", () => {
    expect(ofertaListValid(list())).toBe(true);
    expect(ofertaListValid(list({ results: [row({ usa_voucher: "no" })] }))).toBe(false);
    expect(ofertaListValid({ ...list(), permisos: { editar: true } })).toBe(false);
    expect(ofertaDetailValid(detail())).toBe(true);
    expect(ofertaDetailValid(detail({ urls: { list: "/a/", update: "https://x.test/", delete: "/b/" } }))).toBe(false);
    expect(cursoDetailValid(curso())).toBe(true);
    expect(cursoDetailValid(curso({ vouchers: [3] }))).toBe(false);
    expect(cursoDetailValid(curso({ puede_editar: "si" }))).toBe(false);
  });

  it("renders the list rows, the badge of every state, the buttons by permission and the tour help", async () => {
    serve(list({
      results: [row(), row({ id: 6, estado: "cancelada", estado_label: "Cancelada", usa_voucher: true }), row({ id: 7, estado: "finalizada", estado_label: "Finalizada" }), row({ id: 8, estado: "planificada", estado_label: "Planificada" })],
      permisos: { editar: true, eliminar: false }, busqueda: "Elec",
    }));
    setup("/vat/ofertas-institucionales/?busqueda=Elec");
    expect(await screen.findByText("Activa")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}?busqueda=Elec`, expect.anything());
    expect(screen.getByText("Cancelada").className).toBe("badge-validacion no-validado");
    expect(screen.getByText("Planificada").className).toBe("badge-validacion pendiente");
    expect(screen.getByText("Finalizada").getAttribute("style")).toContain("rgb(75, 85, 99)");
    expect(screen.getAllByText("Editar")).toHaveLength(4);
    expect(screen.queryByText("Eliminar")).toBeNull();
    expect(screen.getByText("Sí").className).toBe("badge-validacion validado");
    expect(screen.getAllByText("—")).toHaveLength(3);
    expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe("Elec");
    expect(screen.getByRole("button", { name: /Tour de ayuda/ })).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Ofertas Institucionales"));
  });

  it("shows the empty message", async () => {
    serve(list({ results: [], page: page({ count: 0 }) }));
    setup("/vat/ofertas-institucionales/");
    expect(await screen.findByText("No se encontraron ofertas institucionales")).toBeTruthy();
    expect(screen.getByText("No hay ofertas que coincidan con los criterios de búsqueda.")).toBeTruthy();
  });

  it("renders the offer detail with cost, voucher badge, notes and both action buttons", async () => {
    serve(detail());
    setup("/vat/ofertas-institucionales/5/");
    expect(await screen.findByRole("heading", { level: 1, name: "Oferta Institucional" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}5/`, expect.anything());
    expect(screen.getByText("Electricista - 2026").tagName).toBe("SMALL");
    expect(screen.getByText("$1234,50")).toBeTruthy();
    expect(screen.getByText("Sí").className).toBe("badge bg-success");
    expect(screen.getByText("Una nota")).toBeTruthy();
    expect(screen.getByText("#5")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Editar/ }).getAttribute("href")).toBe("/vat/ofertas-institucionales/5/editar/");
    expect(screen.getByRole("link", { name: /Eliminar/ }).getAttribute("href")).toBe("/vat/ofertas-institucionales/5/eliminar/");
    await waitFor(() => expect(document.title).toBe("SISOC - Electricista - 2026"));
  });

  it("shows «Gratuito», the plain voucher badge and no notes block when the native template does", async () => {
    serve(detail({ costo: "", usa_voucher: false, observaciones: "" }));
    setup("/vat/ofertas-institucionales/5/");
    expect(await screen.findByText("Gratuito")).toBeTruthy();
    expect(screen.getByText("No").className).toBe("badge bg-secondary");
    expect(screen.queryByText("Observaciones")).toBeNull();
  });

  it("renders the course detail read only and draws the edit link only when allowed", async () => {
    serve(curso());
    setup("/vat/cursos/8/");
    expect(await screen.findByRole("heading", { level: 1, name: "Electricidad básica" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${CURSO}8/`, expect.anything());
    expect(screen.getByText("Sin plan curricular · CFP 401")).toBeTruthy();
    expect(screen.getByText("Planificado", { selector: "span" }).className).toBe("sisoc-status-pill sisoc-status-pill--planificado");
    expect(screen.getByText("Voucher Dos").tagName).toBe("LI");
    expect(screen.getByText("4").className).toBe("sisoc-metric-value");
    expect(screen.getByRole("link", { name: /Editar curso/ }).getAttribute("href")).toBe("/vat/cursos/8/editar/");
    await waitFor(() => expect(document.title).toBe("SISOC - Electricidad básica - Curso"));
    cleanup();
    serve(curso({ puede_editar: false, vouchers: [] }));
    setup("/vat/cursos/8/");
    await screen.findByRole("heading", { level: 1, name: "Electricidad básica" });
    expect(screen.queryByRole("link", { name: /Editar curso/ })).toBeNull();
    expect(screen.getAllByText("-").length).toBeGreaterThan(1);
  });
});
