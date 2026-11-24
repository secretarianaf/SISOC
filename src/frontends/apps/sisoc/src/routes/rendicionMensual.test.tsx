import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { listValid, rendicionNavigation } from "./rendicionMensual";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const LISTADO = "/rendicioncuentasmensual/rendicioncuentasmensual/listado/";
const API = "web/comedores/rendicioncuentasmensual/listado/";
const HEADERS = ["Proyecto", "Organización", "Convenio", "Rendición", "Período", "Etapa", "Estado", "Última modificación"];
const fields = [
  { name: "codigo_proyecto", label: "Proyecto", type: "text" },
  { name: "mes", label: "Mes", type: "number", input: { min: "1", max: "12" } },
  { name: "periodo_inicio", label: "Periodo inicio", type: "date" },
  { name: "estado_proceso", label: "Estado", type: "choice", choices: [{ value: "auditoria:pendiente", label: "Auditoría pendiente" }, { value: "auditoria:en_curso", label: "Auditoría en curso" }] },
  { name: "documento_adjunto", label: "Documento adjunto", type: "boolean" },
];
const columns = {
  list_key: "rendiciones_global_list", endpoint: "/ajax/columnas-preferencias/",
  modal_id: "column-config-modal-rendiciones_global_list", script_id: "column-config-data-rendiciones_global_list",
  available: HEADERS.map((title, i) => ({ key: `k${i}`, title, active: true, required: false, default: true })),
  active: HEADERS.map((_t, i) => `k${i}`), defaults: HEADERS.map((_t, i) => `k${i}`),
};
const cells = (over: Partial<Record<number, { text: string; badge: string | null }>> = {}) => [
  "P-77", "Org <Norte>", "P01", "2", "01/03/2026 - 31/03/2026", "Revisión Territorial", "Revisión Territorial pendiente de correcciones", "11/11/2026 10:30",
].map((t, i) => over[i] ?? { text: t, badge: i === 5 ? "badge etapa-badge etapa-territorial" : i === 6 ? "badge-validacion no-validado" : null });
const list = (over: Record<string, unknown> = {}) => ({
  breadcrumb: [{ text: "Organizaciones", url: "/organizaciones/listar" }, { text: "Rendiciones", url: null }],
  filters_config: { defaultField: "codigo_proyecto", fields, operators: {} },
  favorites: { section: "rendiciones", url: "/ajax/filtros-favoritos/", detail_url_template: "/ajax/filtros-favoritos/0/" },
  urls: { list: LISTADO, reset: LISTADO, export: `${LISTADO}?export=csv`, nueva_auditoria: "/rendicioncuentasmensual/rendicioncuentasmensual/auditoria/" },
  can_export: true, can_nueva_auditoria: true, columns, headers: HEADERS,
  results: [{ id: 5, cells: cells(), detail_url: "/rendicioncuentasmensual/rendicioncuentasmensual/detalle/5/" }],
  page: { is_paginated: true, number: 1, count: 36, previous: null, next: 2, range: [1, 2], query_without_page: "filters=%7B%7D&" },
  messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path = LISTADO) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const filtersUrl = (items: unknown[]) => `${LISTADO}?filters=${encodeURIComponent(JSON.stringify({ logic: "AND", items }))}`;
const rowsOf = () => [...document.querySelectorAll<HTMLElement>("#filters-form .poncho-search--row")];

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Rendición mensual global list route", () => {
  it("owns only the native list path with the repeated prefix", () => {
    expect(findRoute(LISTADO)?.route.name).toBe("comedores-rendicion-mensual");
    for (const other of ["/rendicioncuentasmensual/rendicioncuentasmensual/listado", "/rendicioncuentasmensual/listado/",
      "/rendicioncuentasmensual/rendicioncuentasmensual/7/", "/rendicioncuentasmensual/rendicioncuentasmensual/detalle/5/",
      "/rendicioncuentasmensual/rendicioncuentasmensual/auditoria/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-rendicion-mensual");
    }
  });

  it("renders the native frame, cells, badges and actions from the API", async () => {
    serve(list());
    setup(`${LISTADO}?filters=%7B%7D&page=1`);
    await screen.findByText("Org <Norte>");
    expect(webGet).toHaveBeenCalledWith(`${API}?filters=%7B%7D&page=1`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Rendiciones"));
    expect(screen.getByRole("heading", { level: 2, name: "Buscar Rendiciones" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Organizaciones" }).getAttribute("href")).toBe("/organizaciones/listar");
    const rows = screen.getAllByRole("row");
    expect(within(rows[0]).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([...HEADERS, "Acciones"]);
    const tds = within(rows[1]).getAllByRole("cell");
    expect(tds.map((c) => c.textContent)).toEqual([...cells().map((c) => c.text), " Ver"]);
    expect(tds[5].querySelector("span")?.className).toBe("badge etapa-badge etapa-territorial");
    expect(tds[6].querySelector("span")?.className).toBe("badge-validacion no-validado");
    expect(tds[0].querySelector("span")).toBeNull();
    const ver = within(rows[1]).getByRole("link", { name: "Ver" });
    expect(ver.getAttribute("href")).toBe("/rendicioncuentasmensual/rendicioncuentasmensual/detalle/5/");
    expect(ver.className).toBe("btn btn-ver");
    expect(screen.getByRole("link", { name: "Nueva Auditoría" }).getAttribute("href")).toBe("/rendicioncuentasmensual/rendicioncuentasmensual/auditoria/");
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("href")).toBe(LISTADO);
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?filters=%7B%7D&page=2");
    expect(document.querySelector(".pagination .page-link")?.closest("li")?.className).toBe("page-item disabled");
    expect(document.querySelector(".pagination .page-link")?.textContent).toBe("Volver");
    expect(screen.getByText("Se encontraron 36 resultados")).toBeTruthy();
  });

  it("hides the role buttons and shows the native empty row", async () => {
    serve(list({ can_export: false, can_nueva_auditoria: false, results: [],
      page: { is_paginated: false, number: 1, count: 0, previous: null, next: null, range: [1], query_without_page: "" } }));
    setup();
    const empty = await screen.findByText("No hay rendiciones registradas.");
    expect(empty.getAttribute("colspan")).toBe("9");
    expect(screen.queryByRole("link", { name: "Nueva Auditoría" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Exportar búsqueda" })).toBeNull();
    expect(document.querySelector(".poncho-topbar")).not.toBeNull();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
    expect(document.querySelector(".pagination")).toBeNull();
  });

  it("exports through the native CSV GET with the current filters", async () => {
    const assign = vi.spyOn(rendicionNavigation, "assign").mockImplementation(() => undefined);
    serve(list());
    setup(`${LISTADO}?filters=%7B%7D&page=2`);
    fireEvent.click(await screen.findByRole("button", { name: "Exportar búsqueda" }));
    expect(assign).toHaveBeenCalledWith(`${LISTADO}?export=csv&filters=%7B%7D&page=2`);
  });

  it("prefills typed rows like advanced_filters.js and serializes the native GET", async () => {
    serve(list());
    setup(filtersUrl([
      { field: "mes", op: "eq", value: "3" },
      { field: "estado_proceso", op: "eq", value: "auditoria:en_curso" },
      { field: "estado_proceso", op: "eq", value: "otra:cosa" },
      { field: "no_existe", op: "eq", value: "x" },
    ]));
    await screen.findByText("Org <Norte>");
    const form = document.getElementById("filters-form") as HTMLFormElement;
    expect(form.getAttribute("action")).toBe(LISTADO);
    expect(form.dataset.seccionFiltrosFavoritos).toBe("rendiciones");
    const [mes, estado, desconocido, fallback] = rowsOf();
    const valueOf = (row: HTMLElement) => row.querySelector<HTMLInputElement>("[data-rol=valor]")!;
    const selectOf = (row: HTMLElement) => row.querySelector<HTMLSelectElement>("[data-rol=valor-select]")!;
    expect(valueOf(mes).type).toBe("number");
    expect([valueOf(mes).value, valueOf(mes).min, valueOf(mes).max, valueOf(mes).step]).toEqual(["3", "1", "12", "1"]);
    expect(selectOf(mes).hidden).toBe(true);
    expect(valueOf(estado).hidden).toBe(true);
    expect(selectOf(estado).value).toBe("auditoria:en_curso");
    // An unknown value is appended as its own option, as the native script does.
    expect([...selectOf(desconocido).options].map((o) => o.textContent)).toEqual(["Auditoría pendiente", "Auditoría en curso", "otra:cosa"]);
    expect(fallback.querySelector<HTMLSelectElement>("[data-rol=campo]")!.value).toBe("codigo_proyecto");
    expect(valueOf(fallback).placeholder).toBe("Buscar por filtro 4");
    fireEvent.change(fallback.querySelector("[data-rol=campo]")!, { target: { value: "documento_adjunto" } });
    await waitFor(() => expect(selectOf(rowsOf()[3]).value).toBe("true"));
    fireEvent.change(rowsOf()[2].querySelector("[data-rol=campo]")!, { target: { value: "periodo_inicio" } });
    await waitFor(() => expect(valueOf(rowsOf()[2]).type).toBe("date"));
    fireEvent.change(valueOf(rowsOf()[2]), { target: { value: "2026-03-01" } });
    fireEvent.submit(form);
    expect(JSON.parse((document.getElementById("filters-input") as HTMLInputElement).value)).toEqual({
      logic: "AND",
      items: [
        { field: "mes", op: "eq", value: "3" },
        { field: "estado_proceso", op: "eq", value: "auditoria:en_curso" },
        { field: "periodo_inicio", op: "eq", value: "2026-03-01" },
        { field: "documento_adjunto", op: "eq", value: "true" },
      ],
    });
    fireEvent.click(rowsOf()[0].querySelector("[data-rol=agregar]")!);
    await waitFor(() => expect(rowsOf()).toHaveLength(5));
    expect(valueOf(rowsOf()[4]).type).toBe("text");
    fireEvent.click(rowsOf()[4].querySelector("[data-rol=quitar]")!);
    await waitFor(() => expect(rowsOf()).toHaveLength(4));
  });

  it("saves column preferences to the native endpoint and reloads", async () => {
    const reload = vi.spyOn(rendicionNavigation, "reload").mockImplementation(() => undefined);
    const fetchMock = vi.fn(() => Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    serve(list());
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Configurar columnas" }));
    const dialog = await screen.findByRole("dialog", { name: "Columnas visibles" });
    fireEvent.click(within(dialog).getByRole("checkbox", { name: "Convenio" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/ajax/columnas-preferencias/");
    expect(JSON.parse(String(init.body))).toEqual({ list_key: "rendiciones_global_list", columns: ["k0", "k1", "k3", "k4", "k5", "k6", "k7"] });
    expect((init.headers as Record<string, string>)["X-CSRFToken"]).toBe("synthetic-csrf-token");
    vi.unstubAllGlobals();
  });

  it("shows the access screen on 403 and an error on an invalid payload", async () => {
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    setup();
    await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
    expect(screen.queryByRole("table")).toBeNull();
    cleanup();
    serve({ ...list(), results: [{ id: 1, cells: [{ text: 1 }], detail_url: "/x/" }] });
    setup();
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(listValid(list())).toBe(true);
    expect(listValid(list({ urls: { ...list().urls, export: "https://evil.example/" } }))).toBe(false);
  });
});
