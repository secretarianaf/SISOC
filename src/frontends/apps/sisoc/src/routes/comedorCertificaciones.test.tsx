import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { certificacionesValid } from "./comedorCertificaciones";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const HISTORIAL = "/comedores/7/certificaciones-prestaciones/";
const ENDPOINT = "web/comedores/comedores/7/certificaciones-prestaciones/";

const fila = (id: number, over: Record<string, unknown> = {}) => ({
  id, periodo: "10/2026", usuario: "Ana Gómez", conforme: true, creado: "26/10/2026 12:30", pdf_url: `/comedores/7/certificaciones-prestaciones/${id}/descargar/`, ...over,
});
const data = (over: Record<string, unknown> = {}) => ({
  comedor: { id: 7, nombre: "Comedor Norte" },
  filtros: { periodo: "", usuario: "", conforme: "" },
  generadores: [{ id: 4, label: "Ana Gómez" }, { id: 5, label: "solo_usuario" }],
  certificaciones: [fila(1), fila(2, { periodo: "09/2026", usuario: "-", conforme: false, pdf_url: null })],
  page: { number: 1, count: 2, is_paginated: false, previous: null, next: null, range: [1], query_without_page: "" },
  urls: { comedores: "/comedores/listar", comedor: "/comedores/7", historial: HISTORIAL },
  messages: [], ...over,
});

function serve(payload: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: payload, status: 200 }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => { vi.clearAllMocks(); setViewport(false); });
afterEach(() => cleanup());

describe("Comedor certifications history route (CO05.01)", () => {
  it("owns only the native history URL", () => {
    expect(findRoute(HISTORIAL)?.route.name).toBe("comedor-certificaciones");
    for (const other of ["/comedores/7/certificaciones-prestaciones", "/comedores/7/", "/comedores/0/certificaciones-prestaciones/", "/comedores/7/certificaciones-prestaciones/1/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedor-certificaciones");
    }
  });

  it("reads the endpoint and shows the native table, filters and links", async () => {
    serve(data());
    setup(HISTORIAL);
    await screen.findByText("Historial completo");
    expect(webGet).toHaveBeenCalledWith(ENDPOINT, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Certificaciones mensuales: Comedor Norte"));
    expect(document.querySelector("h3")!.textContent).toBe("Certificaciones Mensuales de Prestaciones");
    expect([...document.querySelectorAll("thead th")].map((th) => th.textContent)).toEqual(["Período", "Usuario generador", "Estado Conformidad", "Fecha de certificación", "Ver PDF"]);
    const rows = [...document.querySelectorAll("tbody tr")].map((tr) => [...tr.querySelectorAll("td")].map((td) => td.textContent));
    expect(rows).toEqual([["10/2026", "Ana Gómez", "Conforme", "26/10/2026 12:30", "Ver PDF"], ["09/2026", "-", "No conforme", "26/10/2026 12:30", "No disponible"]]);
    const pdf = screen.getByRole("link", { name: "Ver PDF" });
    expect(pdf.getAttribute("href")).toBe("/comedores/7/certificaciones-prestaciones/1/descargar/");
    expect(pdf.getAttribute("target")).toBe("_blank");
    expect(screen.getByRole("link", { name: "Limpiar" }).getAttribute("href")).toBe(HISTORIAL);
    expect(screen.getByText("Se encontraron 2 resultados")).toBeTruthy();
    const crumbs = within(document.querySelector(".breadcrumb") as HTMLElement);
    expect(crumbs.getByRole("link", { name: "Comedor Norte" }).getAttribute("href")).toBe("/comedores/7");
    expect(crumbs.getByText("Certificaciones mensuales").tagName).toBe("LI");
  });

  it("forwards the query and preselects the active filters", async () => {
    serve(data({ filtros: { periodo: "2026-10", usuario: "5", conforme: "false" } }));
    setup(`${HISTORIAL}?periodo=2026-10&usuario=5&conforme=false`);
    await screen.findByText("Historial completo");
    expect(webGet).toHaveBeenCalledWith(`${ENDPOINT}?periodo=2026-10&usuario=5&conforme=false`, expect.anything());
    expect((screen.getByLabelText("Período de Certificación") as HTMLInputElement).value).toBe("2026-10");
    expect((screen.getByLabelText("Usuario Generador") as HTMLSelectElement).value).toBe("5");
    expect((screen.getByLabelText("Estado de Conformidad") as HTMLSelectElement).value).toBe("false");
    expect(screen.getByRole("button", { name: "Filtrar" }).closest("form")!.getAttribute("method")).toBe("get");
  });

  it("keeps the first option for an unknown generator and shows the empty message without a count", async () => {
    serve(data({ filtros: { periodo: "", usuario: "99", conforme: "" }, certificaciones: [], page: { number: 1, count: 0, is_paginated: false, previous: null, next: null, range: [], query_without_page: "" } }));
    setup(HISTORIAL);
    await screen.findByText("No hay certificaciones mensuales registradas.");
    expect((screen.getByLabelText("Usuario Generador") as HTMLSelectElement).value).toBe("");
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("links the pages keeping the other filters", async () => {
    serve(data({ page: { number: 1, count: 23, is_paginated: true, previous: null, next: 2, range: [1, 2], query_without_page: "conforme=true&" } }));
    setup(`${HISTORIAL}?conforme=true`);
    await screen.findByText("Se encontraron 23 resultados");
    expect(screen.getByRole("link", { name: "2" }).getAttribute("href")).toBe("?conforme=true&page=2");
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?conforme=true&page=2");
    expect(within(document.querySelector(".pagination") as HTMLElement).getByRole("link", { name: "Volver" }).getAttribute("href")).toBe("#");
  });

  it("shows the access screen on 403 and an error on an invalid payload", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "no" }, status: 403 }));
    setup(HISTORIAL);
    await waitFor(() => expect(screen.queryByText("Cargando certificaciones…")).toBeNull());
    expect(screen.queryByText("Historial completo")).toBeNull();
    cleanup();
    serve({ nope: true });
    setup(HISTORIAL);
    await screen.findByText("No se pudo cargar la página.");
  });

  it("validates the payload shape and refuses unsafe URLs", () => {
    expect(certificacionesValid(data())).toBe(true);
    expect(certificacionesValid(data({ certificaciones: [fila(1, { pdf_url: "javascript:alert(1)" })] }))).toBe(false);
    expect(certificacionesValid(data({ certificaciones: [fila(1, { conforme: "yes" })] }))).toBe(false);
    expect(certificacionesValid(data({ generadores: [{ id: "x", label: "a" }] }))).toBe(false);
    expect(certificacionesValid(null)).toBe(false);
  });
});
