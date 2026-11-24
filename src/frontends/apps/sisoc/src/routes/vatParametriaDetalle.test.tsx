import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { parametriaDetailValid } from "./vatParametriaDetalle";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/vouchers/parametrias/";
const row = (over: Record<string, unknown> = {}) => ({
  id: 9, ciudadano: "Ana Prueba", documento: "30500001", disponible: 4, inicial: 10, barra: "bg-warning", ancho: "40", badge: "bg-success", estado_label: "Activo", detail_url: "/vat/vouchers/9/", ...over,
});
const data = (over: Record<string, unknown> = {}) => ({
  id: 5, nombre: "Parametria <1>", descripcion: "Descripcion", programa: "Programa Sintetico", cantidad_inicial: 10, vencimiento: "01/03/2027", renovacion_mensual: true,
  cantidad_renovacion: 4, renovacion_tipo_label: "Reiniciar al valor configurado", inscripcion_unica_activa: false, activa: true,
  total: 3, activos: 1, agotados: 1, vencidos: 1, cancelados: 0, creditos_emitidos: 30, creditos_usados: 16, creditos_disponibles: 14, pct_uso: 53, pct_activos: 33,
  pct_agotados: "33", pct_vencidos: "33", pct_cancelados: "0",
  ultimas: [{ ciudadano: "Ana Prueba", documento: "30500001", fecha: "01/10/2026", badge: "bg-success", estado_label: "Activo" }],
  vouchers: [row()], vouchers_total_filtrados: 1, search_query: "",
  page: { is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_prefix: "", shown: true },
  permisos: { asignar: true },
  urls: { list: "/vat/vouchers/parametrias/", detail: "/vat/vouchers/parametrias/5/", asignar: "/vat/vouchers/parametrias/5/asignar/", asignar_masivo: "/vat/vouchers/parametrias/5/asignar-masivo/" },
  messages: [], ...over,
});

function serve(payload: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: payload, status: 200 }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const form = (name: string) => document.querySelector(`[name=${name}]`)!.closest("form")!;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT parametria detail route", () => {
  it("owns the numeric detail path only", () => {
    expect(findRoute("/vat/vouchers/parametrias/12/")?.route.name).toBe("vat-parametria-detalle");
    for (const other of ["/vat/vouchers/parametrias/", "/vat/vouchers/parametrias/nueva/", "/vat/vouchers/parametrias/12/asignar/"]) expect(findRoute(other)?.route.name).not.toBe("vat-parametria-detalle");
  });

  it("renders the hero, stats, rows and metric cards", async () => {
    serve(data());
    setup("/vat/vouchers/parametrias/5/?busqueda=Ana");
    expect(await screen.findByRole("heading", { level: 4, name: "Parametria <1>" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}5/?busqueda=Ana`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Parametria <1>"));
    expect(screen.getByText(/Vence 01\/03\/2027/)).toBeTruthy();
    expect(screen.getByText(/Renovación mensual/).textContent).toContain("· 4 créd.");
    expect(screen.getByText("53% usado")).toBeTruthy();
    expect(screen.getByText("14 disponibles")).toBeTruthy();
    expect(screen.queryByText("Cancelados")).toBeNull();
    expect(document.querySelector("tbody .progress-bar")?.getAttribute("style")).toContain("width: 40%");
    expect(screen.getByText("Se encontraron 1 resultados")).toBeTruthy();
  });

  it("shows the empty states with and without a search", async () => {
    serve(data({ total: 0, vouchers: [], ultimas: [], vouchers_total_filtrados: 0, page: { ...data().page, shown: false } }));
    setup("/vat/vouchers/parametrias/5/");
    expect(await screen.findByText(/Todavía no hay vouchers asignados/)).toBeTruthy();
    expect(screen.getByText("Sin datos todavía. Asigná vouchers para ver métricas.")).toBeTruthy();
    cleanup();
    serve(data({ vouchers: [], search_query: "zzz", vouchers_total_filtrados: 0, page: { ...data().page, shown: false } }));
    setup("/vat/vouchers/parametrias/5/?busqueda=zzz");
    expect(await screen.findByText("No hay vouchers que coincidan con la búsqueda.")).toBeTruthy();
  });

  it("builds the pager links like pagination.html", async () => {
    serve(data({ page: { is_paginated: true, number: 2, num_pages: 3, count: 50, previous: 1, next: 3, range: [1, 2, 3], query_prefix: "busqueda=Ana&x=1&", shown: true } }));
    setup("/vat/vouchers/parametrias/5/?vouchers_page=2");
    await screen.findByText("Anterior");
    expect(screen.getByText("Anterior").getAttribute("href")).toBe("?busqueda=Ana&x=1&vouchers_page=1");
    expect(screen.getByText("Siguiente").getAttribute("href")).toBe("?busqueda=Ana&x=1&vouchers_page=3");
  });

  it("hides the assignment panel without permission", async () => {
    serve(data({ permisos: { asignar: false } }));
    setup("/vat/vouchers/parametrias/5/");
    await screen.findByRole("heading", { level: 4, name: "Parametria <1>" });
    expect(document.querySelector(".assign-panel")).toBeNull();
  });

  it("switches tabs and posts the individual and masivo assignments to the API", async () => {
    serve(data());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/vouchers/parametrias/5/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup("/vat/vouchers/parametrias/5/");
    await screen.findByText("Individual");
    expect((document.getElementById("tab-masivo") as HTMLElement).style.display).toBe("none");
    fireEvent.change(document.querySelector("[name=dni]")!, { target: { value: "30500001" } });
    fireEvent.submit(form("dni"));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/vouchers/parametrias/5/"));
    expect(webPost).toHaveBeenCalledWith(`${API}5/asignar/`, expect.any(URLSearchParams), expect.anything());
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams)).toEqual({ dni: "30500001" });
    fireEvent.click(screen.getByRole("button", { name: /Masiva/ }));
    expect((document.getElementById("tab-masivo") as HTMLElement).style.display).toBe("block");
    expect(screen.getByRole("button", { name: /Masiva/ }).className).toBe("active");
    fireEvent.change(document.querySelector("[name=dnis]")!, { target: { value: "1\n2" } });
    fireEvent.submit(form("dnis"));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(2));
    expect(webPost.mock.calls[1][0]).toBe(`${API}5/asignar-masivo/`);
    expect(Object.fromEntries(webPost.mock.calls[1][1] as URLSearchParams)).toEqual({ dnis: "1\n2" });
  });

  it("does not resend after an unconfirmed result", async () => {
    serve(data());
    webPost.mockRejectedValue(new Error("network"));
    setup("/vat/vouchers/parametrias/5/");
    await screen.findByText("Individual");
    fireEvent.submit(form("dni"));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.submit(form("dni"));
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("validates the payload shape", () => {
    expect(parametriaDetailValid(data())).toBe(true);
    expect(parametriaDetailValid(data({ cantidad_renovacion: null }))).toBe(true);
    expect(parametriaDetailValid(data({ vouchers: [{ id: 1 }] }))).toBe(false);
    expect(parametriaDetailValid({ ...data(), urls: {} })).toBe(false);
  });
});
