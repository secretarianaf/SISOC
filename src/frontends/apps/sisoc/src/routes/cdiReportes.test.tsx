import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const reportes = (over: Record<string, unknown> = {}) => ({
  breadcrumb: [{ text: "Centro de Desarrollo Infantil", url: "/centrodeinfancia/listar" }, { text: "Reportes", url: null }],
  provincias: [{ id: 1, nombre: "Mendoza" }, { id: 2, nombre: "San Juan" }],
  provincia_seleccionada: "",
  variantes: [{ value: "completo", label: "Completo (todos los campos)" }, { value: "reducido", label: "Reducido (campos seleccionados)" }],
  resumen: {
    columnas: ["seccion", "detalle", "cantidad"],
    filas: [["Totales", "Centros de Desarrollo Infantil", "2"], ["Totales", "Trabajadores", "1"]],
  },
  urls: { pantalla: "/centrodeinfancia/reportes/", descarga: "/centrodeinfancia/reportes/descargar/" },
  messages: [],
  ...over,
});

function serve(data: unknown, status = 200, sessionStatus = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(
    url === "web/session/" ? { data: sessionStatus === 200 ? readyContext : { detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, status: sessionStatus }
      : { data, status },
  ));
}

function setup(path = "/centrodeinfancia/reportes/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("CDI reports route", () => {
  it("owns only the native reports path", () => {
    expect(findRoute("/centrodeinfancia/reportes/")?.route.name).toBe("cdi-reportes");
    expect(findRoute("/centrodeinfancia/reportes")?.route.name).toBe("business");
    expect(findRoute("/centrodeinfancia/reportes/descargar/")?.route.name).toBe("business");
  });

  it("loads the core session and the vertical web API with the same query", async () => {
    serve(reportes({ provincia_seleccionada: "2" }));
    setup("/centrodeinfancia/reportes/?provincia=2");
    await screen.findByRole("heading", { name: "Vista previa: hoja Resumen" });
    expect(webGet).toHaveBeenCalledWith("web/session/", expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(webGet).toHaveBeenCalledWith("web/cdi/reportes/?provincia=2", expect.anything());
    expect(webGet).toHaveBeenCalledTimes(2);
    expect(document.title).toBe("SISOC - Reportes de Centros de Desarrollo Infantil");
    expect((document.getElementById("provincia") as HTMLSelectElement).value).toBe("2");
    const consultas = screen.getByRole("link", { name: "Consultas (se abre en una nueva pestaña)" });
    expect(consultas.getAttribute("href")).toBe("https://consultas.capitalhumano.gob.ar/canales/sisoc-cdi");
    expect(consultas.getAttribute("target")).toBe("_blank");
    expect(consultas.closest("ul")?.firstElementChild).toBe(consultas.closest("li"));
    expect(document.body.classList.contains("app-loaded")).toBe(true);
  });

  it("renders the native selectors, download button and summary rows as given", async () => {
    serve(reportes());
    setup();
    const form = (await screen.findByRole("button", { name: "Descargar reporte (XLSX)" })).closest("form") as HTMLFormElement;
    expect(form.getAttribute("method")).toBe("get");
    expect(form.getAttribute("action")).toBe("/centrodeinfancia/reportes/");
    expect(screen.getByRole("button", { name: "Descargar reporte (XLSX)" }).getAttribute("formaction")).toBe("/centrodeinfancia/reportes/descargar/");
    expect(screen.getByRole("button", { name: "Actualizar resumen" }).getAttribute("type")).toBe("submit");
    const provincia = screen.getByLabelText("Provincia") as HTMLSelectElement;
    expect([...provincia.options].map((o) => [o.value, o.text])).toEqual([["", "Todas"], ["1", "Mendoza"], ["2", "San Juan"]]);
    expect(provincia.value).toBe("");
    const variante = screen.getByLabelText("Tipo de reporte") as HTMLSelectElement;
    expect([...variante.options].map((o) => o.value)).toEqual(["completo", "reducido"]);
    const rows = within(screen.getByRole("table")).getAllByRole("row");
    expect(rows.map((r) => r.textContent)).toEqual(["secciondetallecantidad", "TotalesCentros de Desarrollo Infantil2", "TotalesTrabajadores1"]);
    expect(screen.getAllByRole("heading", { level: 3, name: "Reportes" })).toHaveLength(2);
    const crumb = screen.getByRole("link", { name: "Centro de Desarrollo Infantil" });
    expect(crumb.getAttribute("href")).toBe("/centrodeinfancia/listar");
    expect(crumb.closest("ol")?.className).toBe("breadcrumb float-sm-right");
    expect(screen.getByText("Reportes", { selector: "li" }).className).toBe("breadcrumb-item active");
  });

  it("offers only the available variant as a hidden field when there is one", async () => {
    serve(reportes({ variantes: [{ value: "reducido", label: "Reducido (campos seleccionados)" }] }));
    setup();
    expect(await screen.findByText("Reporte disponible: Reducido (campos seleccionados).")).toBeDefined();
    expect(screen.queryByLabelText("Tipo de reporte")).toBeNull();
    const hidden = document.querySelector<HTMLInputElement>('input[type="hidden"][name="variante"]');
    expect(hidden?.value).toBe("reducido");
  });

  it("hides the province selector without provinces and shows the empty summary", async () => {
    serve(reportes({ provincias: [], resumen: { columnas: ["seccion", "detalle", "cantidad"], filas: [] } }));
    setup();
    expect(await screen.findByText("No hay centros en tu alcance.")).toBeDefined();
    expect(screen.queryByLabelText("Provincia")).toBeNull();
    expect(screen.queryByRole("button", { name: "Actualizar resumen" })).toBeNull();
  });

  it("falls back to Todas when the selected province is not offered", async () => {
    serve(reportes({ provincia_seleccionada: "abc" }));
    setup("/centrodeinfancia/reportes/?provincia=abc");
    expect(((await screen.findByLabelText("Provincia")) as HTMLSelectElement).value).toBe("");
  });

  it("shows pending messages once, like the native toasts", async () => {
    serve(reportes({ messages: [{ message: "Listo.", level: "success" }] }));
    setup();
    expect(await screen.findByText("Listo.")).toBeDefined();
  });

  it("reports a forbidden API, a pending requirement and an invalid payload", async () => {
    serve({ detail: "No tiene permiso." }, 403);
    setup();
    expect(await screen.findByText("¡Ups! Algo salió mal.")).toBeDefined();
    expect(document.title).toBe("SISOC - Error 403");
    cleanup();
    serve(reportes(), 200, 403);
    setup();
    expect(await screen.findByText("Necesitás actualizar tu contraseña para continuar.")).toBeDefined();
    expect(screen.getByRole("link", { name: "Continuar en SISOC" }).getAttribute("href")).toBe("/password/first-change/");
    cleanup();
    serve({ ...reportes(), resumen: { columnas: [], filas: [[1, 2, 3]] } });
    setup();
    expect(await screen.findByText("No se pudo cargar la página.")).toBeDefined();
  });
});
