import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const crumbs = (last: string) => [
  { text: "PAS", url: "/pas/listar" }, { text: "Informes", url: "/pas/informes" }, { text: last, url: null },
];
const row = (id: number, extra: Record<string, unknown> = {}) => ({
  id, numero: `PAS-INF-${String(id).padStart(6, "0")}`, creado: "02/01/2026 09:05", usuario: "Ana Gómez",
  total_personas: 3, total_cambios: 1, detail_path: `/pas/informes/${id}`, download_url: null, ...extra,
});
const listado = (extra: Record<string, unknown> = {}) => ({
  page: 1, page_size: 10, has_previous: false, has_next: true, previous: null, next: 2, is_paginated: true,
  page_range: [1, 2, "…"], count: null, query_prefix: "busqueda=ana&q=ana&", breadcrumb: crumbs("Listar"), query: "ana",
  can_generate: false, results: [row(12), row(7, { usuario: "", download_url: "/pas/informes/7/descargar" })], ...extra,
});
const columns = ["IdPersona", "Apellido"].map((label, i) => ({ key: `k${i}`, label }));
const detalle = (extra: Record<string, unknown> = {}) => ({
  id: 12, numero: "PAS-INF-000012", creado: "08/07/2026 14:03", usuario: "", total_personas: 2, total_cambios: 0,
  breadcrumb: crumbs("PAS-INF-000012"), filtros: [{ clave: "estado_actual", valor: "Activo" }, { clave: "dni", valor: "30111222" }],
  columns, rows: [["7", "None"]], download_url: "/pas/informes/12/descargar", ...extra,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => cleanup());

describe("PAS informes routes", () => {
  it("owns only the native list and detail URLs", () => {
    expect(findRoute("/pas/informes")?.params).toEqual({ page: "listar" });
    expect(findRoute("/pas/informes/12")?.params).toEqual({ page: "detalle", id: "12" });
    for (const other of ["/pas/informes/", "/pas/informes/generar", "/pas/informes/12/descargar", "/pas/informes/x"]) {
      expect(findRoute(other)?.route.name).not.toBe("pas-informes");
    }
  });

  it("renders the native list: rows, author fallback, download link and pager", async () => {
    serve(listado());
    setup("/pas/informes?q=ana");
    await screen.findByRole("heading", { name: "Informes PAS" });
    await waitFor(() => expect(document.title).toContain("Informes PAS"));
    expect(webGet).toHaveBeenCalledWith("web/pas/informes/?q=ana", expect.anything());
    expect((screen.getByPlaceholderText("PAS-INF-000001, usuario, nombre o apellido") as HTMLInputElement).value).toBe("ana");
    expect(screen.queryByRole("link", { name: /Nuevo informe/ })).toBeNull();
    const rows = screen.getAllByRole("row").slice(1);
    expect(within(rows[0]).getAllByRole("cell").map((c) => c.textContent?.trim())).toEqual(
      ["PAS-INF-000012", "02/01/2026 09:05", "Ana Gómez", "3", "1", "Ver"]);
    expect((within(rows[1]).getAllByRole("cell")[2]).textContent).toContain("-");
    expect((within(rows[1]).getByRole("link", { name: "Descargar" })).getAttribute("href")).toBe("/pas/informes/7/descargar");
    expect((screen.getByRole("link", { name: "Continuar" })).getAttribute("href")).toBe("?busqueda=ana&q=ana&page=2");
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("shows «Nuevo informe» with the capability and the empty row", async () => {
    serve(listado({ can_generate: true, results: [], is_paginated: false }));
    setup("/pas/informes");
    expect((await screen.findByRole("link", { name: /Nuevo informe/ })).getAttribute("href")).toBe("/pas/informes/generar");
    expect(screen.getByText("No se encontraron informes PAS")).toBeTruthy();
    expect(screen.getByText("Genere un informe o modifique la busqueda.")).toBeTruthy();
  });

  it("renders the detail snapshot, filters, author fallback and download", async () => {
    serve(detalle());
    setup("/pas/informes/12");
    await screen.findByRole("heading", { name: "PAS-INF-000012", level: 1 });
    await waitFor(() => expect(document.title).toContain("PAS-INF-000012"));
    expect(webGet).toHaveBeenCalledWith("web/pas/informes/12/", expect.anything());
    expect(screen.getByText("Generado el 08/07/2026 14:03 por -")).toBeTruthy();
    expect((screen.getByRole("link", { name: /Descargar CSV/ })).getAttribute("href")).toBe("/pas/informes/12/descargar");
    expect(screen.getByText((_, el) => el?.textContent === "estado_actual: Activo ")).toBeTruthy();
    expect(screen.getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["IdPersona", "Apellido"]);
    expect(screen.getByRole("cell", { name: "None" })).toBeTruthy();
  });

  it("detail without filters, rows or download permission", async () => {
    serve(detalle({ filtros: [], rows: [], download_url: null }));
    setup("/pas/informes/12");
    expect(await screen.findByText("Sin filtros. Incluye el universo PAS disponible.")).toBeTruthy();
    expect(screen.getByText("Sin registros para los filtros seleccionados.")).toBeTruthy();
    expect(screen.queryByRole("link", { name: /Descargar CSV/ })).toBeNull();
  });

  it("shows the access screen on 403 and an error on an unexpected shape", async () => {
    serve({ detail: "x" }, 403);
    setup("/pas/informes");
    await waitFor(() => expect(document.title).toBe("SISOC - Error 403"));
    cleanup();
    serve({ results: "x" });
    setup("/pas/informes");
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudo cargar la página.");
  });
});
