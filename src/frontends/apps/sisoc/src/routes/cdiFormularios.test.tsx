import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const centro = { id: 7, nombre: "CDI Girasoles", url: "/centrodeinfancia/detalle/7" };
const lista = (over: Record<string, unknown> = {}) => ({
  centro,
  crear_url: "/centrodeinfancia/7/formularios/crear/",
  rows: [{ id: 3, codigo: "CDI-7 / 3", fecha: "13/03/2026", respondente: "Ana Pérez", creado: "13/03/2026 10:00", actualizado: "14/03/2026 11:00",
    ver_url: "/centrodeinfancia/7/formularios/3/", editar_url: "/centrodeinfancia/7/formularios/3/editar/" }],
  page: { is_paginated: true, number: 2, count: 31, previous: 1, next: 3, range: [1, 2, 3, "…", 4] },
  messages: [],
  ...over,
});
const detalle = (over: Record<string, unknown> = {}) => ({
  id: 3, centro, codigo_cdi: "CDI-7", creado: "13/03/2026 10:00", creado_por: "Lu Gómez",
  editar_url: "/centrodeinfancia/7/formularios/3/editar/",
  sections: [{ title: "Datos del CDI", items: [{ label: "Nombre del CDI", value: "CDI Girasoles" }, { label: "Teléfono", value: "-" }] }],
  horarios: [["Lunes", "08:00", "-"]],
  salas: { rows: [["Lactantes", "2", "12,50", "-", "4", "2"]], totales: ["2", "12,50", "0", "4"] },
  demanda: { rows: [["Lactantes", "5"]], total: "5" },
  articulacion: [["Justicia", "Mensual"]],
  messages: [],
  ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => { vi.clearAllMocks(); document.title = "SISOC"; setViewport(false); });
afterEach(() => cleanup());

describe("CDI institutional form routes", () => {
  it("owns only the native list and detail paths", () => {
    expect(findRoute("/centrodeinfancia/7/formularios/")?.route.name).toBe("cdi-formularios-lista");
    expect(findRoute("/centrodeinfancia/7/formularios/3/")?.route.name).toBe("cdi-formulario-detalle");
    expect(findRoute("/centrodeinfancia/7/formularios")?.route.name).toBe("business");
    expect(findRoute("/centrodeinfancia/7/formularios/0/")?.route.name).toBe("business");
    expect(findRoute("/centrodeinfancia/7/formularios/crear/")?.route.name).toBe("cdi-formulario-form");
    expect(findRoute("/centrodeinfancia/7/formularios/3/editar/")?.route.name).toBe("cdi-formulario-form");
  });

  it("draws the list with its cells, links and the native pagination keeping the other parameters", async () => {
    serve(lista());
    setup("/centrodeinfancia/7/formularios/?page=2&x=a%20b");
    await screen.findByRole("heading", { level: 3, name: "CDI Girasoles" });
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/7/formularios/?page=2&x=a%20b", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Formularios CDI"));
    expect(screen.getByRole("link", { name: "Nuevo formulario" }).getAttribute("href")).toBe("/centrodeinfancia/7/formularios/crear/");
    const fila = screen.getByText("CDI-7 / 3").closest("tr") as HTMLElement;
    expect(within(fila).getByText("Ana Pérez")).toBeDefined();
    expect(within(fila).getByRole("link", { name: "Ver" }).getAttribute("href")).toBe("/centrodeinfancia/7/formularios/3/");
    expect(within(fila).getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/centrodeinfancia/7/formularios/3/editar/");
    expect(within(document.querySelector("ul.pagination") as HTMLElement).getByRole("link", { name: "Volver" }).getAttribute("href")).toBe("?x=a%20b&page=1");
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?x=a%20b&page=3");
    expect(screen.getByRole("link", { name: "2" }).closest("li")?.className).toBe("page-item active");
    expect(screen.getByRole("link", { name: "..." }).closest("li")?.className).toBe("page-item disabled");
    expect(screen.getByText("Se encontraron 31 resultados")).toBeDefined();
  });

  it("shows the empty list message and no pagination controls on a single page", async () => {
    serve(lista({ rows: [], page: { is_paginated: false, number: 1, count: 0, previous: null, next: null, range: [] } }));
    setup("/centrodeinfancia/7/formularios/");
    expect(await screen.findByText("Todavia no hay formularios cargados para este centro.")).toBeDefined();
    expect(document.querySelector("ul.pagination")).toBeNull();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("disables the first pagination button", async () => {
    serve(lista({ page: { is_paginated: true, number: 1, count: 12, previous: null, next: 2, range: [1, 2] } }));
    setup("/centrodeinfancia/7/formularios/");
    const volver = await waitFor(() => { if (!document.querySelector("ul.pagination")) throw new Error("wait"); }).then(() => within(document.querySelector("ul.pagination") as HTMLElement).getByRole("link", { name: "Volver" }));
    expect(volver.closest("li")?.className).toBe("page-item disabled");
    expect(volver.getAttribute("href")).toBe("#");
  });

  it("draws the detail cards, the schedule, the tables with their totals and the edit link", async () => {
    serve(detalle());
    setup("/centrodeinfancia/7/formularios/3/");
    await screen.findByText("Formulario #3 | Código CDI CDI-7");
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/7/formularios/3/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Formulario CDI #3"));
    expect(screen.getByText("Creado 13/03/2026 10:00 por Lu Gómez")).toBeDefined();
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/centrodeinfancia/7/formularios/3/editar/");
    expect(screen.getByText("Nombre del CDI").nextElementSibling?.textContent).toBe("CDI Girasoles");
    expect(screen.getByText("Lunes").closest("tr")?.textContent).toBe("Lunes08:00-");
    expect(screen.getByText("Totales").closest("tr")?.textContent).toBe("Totales212,5004-");
    expect(screen.getByText("Total").closest("tr")?.textContent).toBe("Total5");
    expect(screen.getByText("Articulaciones institucionales").closest(".card")?.className).toBe("card mb-4");
  });

  it("omits the author and shows the empty schedule note", async () => {
    serve(detalle({ creado_por: null, horarios: [] }));
    setup("/centrodeinfancia/7/formularios/3/");
    expect(await screen.findByText("Creado 13/03/2026 10:00")).toBeDefined();
    expect(screen.getByText("Sin horarios cargados.")).toBeDefined();
  });

  it("shows the not found and invalid payload states", async () => {
    serve({}, 404);
    setup("/centrodeinfancia/7/formularios/3/");
    expect((await screen.findByRole("alert")).textContent).toBe("No se encontró la página.");
    cleanup();
    serve(detalle({ horarios: [["x"]] }));
    setup("/centrodeinfancia/7/formularios/3/");
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar la página.");
  });
});
