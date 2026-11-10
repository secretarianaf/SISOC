import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const session = {
  ...readyContext,
  navigation: [
    { id: "inicio", label: "Inicio", href: "/inicio/", children: [] },
    { id: "legajos", label: "Legajos", href: null, children: [{ id: "inspecciones_panel", label: "Inspecciones escolares", href: "/inspecciones/", children: [] }] },
    { id: "comunicados", label: "Comunicados", href: null, children: [{ id: "comunicados", label: "Ver Comunicados", href: "/comunicados/", children: [] }] },
    { id: "mi_cuenta", label: "Mi cuenta", href: "/mi-cuenta/", children: [] },
  ],
};
const row = (numero: string, extra: Record<string, unknown> = {}) => ({
  numero, url: `/inspecciones/actas/${numero}/`, anulada: false, prueba: false,
  escuela: { nombre: "Escuela Sintética", cueanexo: "060123400", provincia: "Buenos Aires", localidad: "San Justo" },
  turno: "tarde", inspector: "Ana Prueba", fecha: "09/11/2026", hora: "11:43", firma: "firma", notificacion: "pendiente", ...extra,
});
const actas = (over: Record<string, unknown> = {}) => ({
  layout: {
    breadcrumb: [{ text: "Inicio", url: "/inicio/" }, { text: "Inspecciones escolares", url: "/inspecciones/" }, { text: "Actas", url: null }],
    display_name: "Gestora Sintética", role: "Coordinación sintética", initials: "GS",
  },
  tabs: [
    { id: "tablero", label: "Tablero", url: "/inspecciones/tablero/" },
    { id: "escuelas", label: "Escuelas", url: "/inspecciones/" },
    { id: "asignaciones", label: "Asignaciones", url: "/inspecciones/asignaciones/" },
    { id: "actas", label: "Actas", url: "/inspecciones/actas/" },
  ],
  filters: { fecha: "", inspector: null, provincia: "", estado: "", numero: "" },
  options: {
    provincias: [{ id: 1, nombre: "Buenos Aires" }, { id: 2, nombre: "Córdoba" }],
    estados: [{ value: "", label: "Todas las actas" }, { value: "validas", label: "Válidas" }, { value: "anuladas", label: "Anuladas" }, { value: "prueba", label: "De prueba" }],
    inspectores_url: "/api/web/inspecciones/inspectores/?alcance=programa",
  },
  has_query: false,
  results: [row("ACTA-2026-000001"), row("ACTA-2026-000003", { anulada: true, prueba: true, firma: "", notificacion: "cargada", escuela: { nombre: "", cueanexo: "", provincia: "", localidad: "" } })],
  page: { number: 1, count: 30, start_index: 1, end_index: 25, has_other_pages: true, previous: null, next: 2, range: [1, 2], query_without_page: "estado=validas&" },
  ...over,
});

function serve(data: unknown, status = 200, sessionData: unknown = session) {
  webGet.mockImplementation((url: string) => Promise.resolve(
    url === "web/session/" ? { data: sessionData, status: 200 }
      : url.startsWith("web/inspecciones/inspectores/") ? { data: { results: [{ id: 3, text: "Ana Prueba", detalle: "inspector.1 · DNI 30000000" }] }, status: 200 }
        : { data, status },
  ));
}

function setup(path = "/inspecciones/actas/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC - Insumos";
  document.documentElement.setAttribute("data-bs-theme", "dark");
  document.body.className = "layout-fixed dark-mode";
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("Inspecciones actas route", () => {
  it("owns only the native list path", () => {
    expect(findRoute("/inspecciones/actas/")?.route.name).toBe("inspecciones-actas");
    expect(findRoute("/inspecciones/actas")?.route.name).not.toBe("inspecciones-actas");
    expect(findRoute("/inspecciones/actas/ACTA-2026-000001/")?.route.name).not.toBe("inspecciones-actas");
  });

  it("loads the core session and the vertical web API with the same query", async () => {
    serve(actas());
    setup("/inspecciones/actas/?estado=validas&page=1");
    await screen.findByRole("heading", { name: "Inspecciones escolares" });
    expect(webGet).toHaveBeenCalledWith("web/session/", expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(webGet).toHaveBeenCalledWith("web/inspecciones/actas/?estado=validas&page=1", expect.anything());
    expect(document.title).toBe("SISOC - Inspecciones escolares");
    expect(document.documentElement.getAttribute("data-bs-theme")).toBe("light");
    expect(document.body.className).toBe("layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary insp-cuerpo app-loaded");
    const sheets = [...document.querySelectorAll<HTMLLinkElement>('link[data-claro-frame]')].map((l) => l.getAttribute("href"));
    expect(sheets.at(-1)).toBe("/static/inspecciones/css/panel.css");
    expect(sheets).toContain("/static/custom/css/layout_claro.css");
  });

  it("renders the native frame, tabs, rows, badges and pagination", async () => {
    serve(actas());
    setup();
    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(3);
    expect(within(rows[1]).getByRole("link", { name: "ACTA-2026-000001" }).getAttribute("href")).toBe("/inspecciones/actas/ACTA-2026-000001/");
    expect(rows[1].textContent).toContain("Buenos Aires · San Justo");
    expect(within(rows[1]).getByText("Firmada").className).toBe("insp-badge insp-badge-info");
    expect(within(rows[2]).getByText("Anulada").className).toBe("insp-badge insp-badge-error");
    expect(within(rows[2]).getByText("Prueba").className).toBe("insp-badge insp-badge-neutro");
    expect(within(rows[2]).getByText("Cargada").className).toBe("insp-badge insp-badge-ok");
    expect(rows[2].querySelectorAll("td")[1].textContent).toBe("— ");
    expect(screen.getByRole("link", { name: "Actas" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByText("Mostrando 1–25 de 30")).toBeDefined();
    expect(screen.getByRole("link", { name: "2" }).getAttribute("href")).toBe("?estado=validas&page=2");
    expect(screen.getByRole("link", { name: "Página siguiente" }).getAttribute("href")).toBe("?estado=validas&page=2");
    expect(screen.queryByRole("link", { name: "Página anterior" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Limpiar filtros" })).toBeNull();
    const crumbs = screen.getByRole("navigation", { name: "Ubicación" });
    expect(within(crumbs).getByText("Actas").tagName).toBe("STRONG");
    expect(document.querySelector('aside a[href="/inspecciones/"]')?.className).toBe("nav-link nav-dot ms-2 active");
    expect(screen.getByText("Legajos").closest("li")?.className).toBe("nav-item nav-main-item menu-open");
    expect(screen.getByText("GS")).toBeDefined();
    expect(screen.getByRole("link", { name: "Versión local de prueba" }).getAttribute("href")).toBe("/novedades/");
  });

  it("shows the empty state with the clear-filters link and echoes the filters", async () => {
    serve(actas({
      has_query: true, results: [],
      filters: { fecha: "2026-11-09", inspector: { id: 3, text: "Ana Prueba", detalle: "x" }, provincia: "2", estado: "anuladas", numero: "999" },
      page: { number: 1, count: 0, start_index: 0, end_index: 0, has_other_pages: false, previous: null, next: null, range: [1], query_without_page: "numero=999&" },
    }));
    setup("/inspecciones/actas/?numero=999");
    expect(await screen.findByText("No hay actas")).toBeDefined();
    expect(screen.getByText("No hay actas con los filtros elegidos.", { exact: false })).toBeDefined();
    expect(screen.getByRole("link", { name: "Limpiar filtros" }).getAttribute("href")).toBe("/inspecciones/actas/");
    expect(screen.queryByText(/Mostrando/)).toBeNull();
    expect((document.getElementById("filtro-numero") as HTMLInputElement).value).toBe("999");
    expect((document.getElementById("filtro-provincia") as HTMLSelectElement).value).toBe("2");
    expect((document.getElementById("filtro-estado") as HTMLSelectElement).value).toBe("anuladas");
    expect((document.getElementById("filtro-fecha") as HTMLInputElement).value).toBe("2026-11-09");
    expect((document.getElementById("filtro-inspector") as HTMLSelectElement).value).toBe("3");
    expect(document.getElementById("select2-filtro-inspector-container")?.textContent).toBe("Ana Prueba");
  });

  it("auto-submits the native GET form on change and on clearing the search box", async () => {
    serve(actas());
    setup();
    await screen.findByRole("table");
    const form = document.querySelector<HTMLFormElement>("form.insp-filtros")!;
    expect(form.getAttribute("method")).toBe("get");
    expect(form.getAttribute("action")).toBe("/inspecciones/actas/");
    const requestSubmit = vi.fn();
    form.requestSubmit = requestSubmit;
    fireEvent.change(document.getElementById("filtro-estado")!, { target: { value: "anuladas" } });
    expect(requestSubmit).toHaveBeenCalledTimes(1);
    const numero = document.getElementById("filtro-numero") as HTMLInputElement;
    fireEvent.input(numero, { target: { value: "12" } });
    expect(requestSubmit).toHaveBeenCalledTimes(1);
    numero.value = "";
    numero.dispatchEvent(new Event("search", { bubbles: true }));
    expect(requestSubmit).toHaveBeenCalledTimes(2);
    expect(Object.fromEntries(new FormData(form))).toEqual({ fecha: "", inspector: "", provincia: "", estado: "anuladas", numero: "" });
  });

  it("searches inspectors from three letters and submits the chosen one", async () => {
    serve(actas());
    setup();
    await screen.findByRole("table");
    const form = document.querySelector<HTMLFormElement>("form.insp-filtros")!;
    const requestSubmit = vi.fn();
    form.requestSubmit = requestSubmit;
    vi.useFakeTimers();
    fireEvent.mouseDown(document.querySelector(".select2-selection")!);
    expect(screen.getByText("Escribí al menos 3 letras")).toBeDefined();
    const field = document.querySelector<HTMLInputElement>(".select2-search__field")!;
    expect(document.activeElement).toBe(field);
    fireEvent.change(field, { target: { value: "An" } });
    expect(screen.getByText("Escribí al menos 3 letras")).toBeDefined();
    fireEvent.change(field, { target: { value: "Ana" } });
    expect(screen.getByText("Buscando…")).toBeDefined();
    await act(async () => { vi.advanceTimersByTime(260); });
    vi.useRealTimers();
    expect(webGet).toHaveBeenCalledWith("web/inspecciones/inspectores/?alcance=programa&q=Ana", expect.anything());
    const option = await within(document.getElementById("select2-filtro-inspector-results")!).findByRole("option");
    expect(option.textContent).toBe("Ana Pruebainspector.1 · DNI 30000000");
    fireEvent.mouseUp(option);
    await waitFor(() => expect(requestSubmit).toHaveBeenCalledTimes(1));
    expect((document.getElementById("filtro-inspector") as HTMLSelectElement).value).toBe("3");
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("clears the chosen inspector with the Select2 clear button", async () => {
    serve(actas({ filters: { fecha: "", inspector: { id: 3, text: "Ana Prueba" }, provincia: "", estado: "", numero: "" } }));
    setup();
    await screen.findByRole("table");
    const form = document.querySelector<HTMLFormElement>("form.insp-filtros")!;
    form.requestSubmit = vi.fn();
    fireEvent.mouseDown(screen.getByRole("button", { name: "Remove all items" }));
    await waitFor(() => expect(form.requestSubmit).toHaveBeenCalledTimes(1));
    expect((document.getElementById("filtro-inspector") as HTMLSelectElement).value).toBe("");
    expect(screen.getByText("Todos los inspectores").className).toBe("select2-selection__placeholder");
  });

  it("reports a pending web requirement from either API without rendering the list", async () => {
    serve({ detail: "Debe completar el requisito de acceso web.", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    setup();
    expect(await screen.findByText("Necesitás actualizar tu contraseña para continuar.")).toBeDefined();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("treats a malformed response as an error and restores the previous document on unmount", async () => {
    serve({ results: "nope" });
    const view = setup();
    expect(await screen.findByRole("alert")).toBeDefined();
    view.unmount();
    serve(actas());
    const again = setup();
    await screen.findByRole("table");
    again.unmount();
    expect(document.documentElement.getAttribute("data-bs-theme")).toBe("dark");
    expect(document.body.className).toBe("layout-fixed dark-mode");
    expect(document.querySelectorAll("link[data-claro-frame]")).toHaveLength(0);
    expect(document.title).toBe("SISOC - Insumos");
  });

  it("marks the body as AdminLTE does on mobile and toggles the sidebar", async () => {
    setViewport(true);
    serve(actas());
    setup();
    await screen.findByRole("table");
    expect(document.body.className).toBe("layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary insp-cuerpo sidebar-collapse app-loaded");
    fireEvent.click(screen.getByRole("button", { name: "Abrir menú" }));
    expect(document.body.classList.contains("sidebar-open")).toBe(true);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(document.body.classList.contains("sidebar-collapse")).toBe(true);
  });
});
