import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { resultadosValid } from "./encuestasResultados";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const opcion = (texto: string, cantidad: number, porcentaje: string) => ({ texto, cantidad, porcentaje });
const resultado = (over = {}) => ({
  texto: "¿Cómo calificás?", tipo: "opcion_unica", total_respuestas: 3, opciones: [opcion("Bueno", 2, "66,7"), opcion("Malo", 1, "33,3")],
  opcion_lider_texto: "Bueno", numerico: null, respuestas_texto: [], ...over,
});
const page = (over = {}) => ({
  id: 7, titulo: "Satisfacción 2026",
  rondas: [{ id: 12, selected: true, label: "Ronda 2 — Abierta (01/10/2026)" }, { id: 11, selected: false, label: "Ronda 1 — Cerrada (01/09/2026)" }],
  ronda_actual: { id: 12, respuestas: 3, abierta: true, estado_label: "Abierta", cierre: "08/10/2026", export_url: "/encuestas/7/resultados/rondas/12/exportar/" },
  puntajes: [], resultados: [resultado()], messages: [], ...over,
});
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  window.history.replaceState({}, "", "/encuestas/7/resultados/");
  setViewport(false);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("resultados de una encuesta", () => {
  it("owns /encuestas/<id>/resultados/ and validates the payload", () => {
    expect(findRoute("/encuestas/7/resultados/")?.route.name).toBe("encuestas-resultados");
    expect(findRoute("/encuestas/7/resultados/rondas/12/exportar/")?.route.name).not.toBe("encuestas-resultados");
    expect(resultadosValid(page())).toBe(true);
    expect(resultadosValid(page({ ronda_actual: { id: 1, respuestas: 1, abierta: true, estado_label: "x", cierre: "", export_url: "http://evil/" } }))).toBe(false);
    expect(resultadosValid(page({ resultados: [resultado({ numerico: { promedio: "1" } })] }))).toBe(false);
  });

  it("draws the toolbar, the stat cards and the option bars with the native text", async () => {
    serve(page());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Resultados" })).toBeTruthy();
    await waitFor(() => expect(document.title).toContain("Resultados: Satisfacción 2026"));
    expect(webGet).toHaveBeenCalledWith("web/encuestas/7/resultados/", expect.anything());
    expect((screen.getByLabelText("Ronda") as HTMLSelectElement).value).toBe("12");
    expect(screen.getByRole("link", { name: /CSV/ }).getAttribute("href")).toBe("/encuestas/7/resultados/rondas/12/exportar/?formato=csv");
    expect(screen.getByRole("link", { name: /Excel/ }).getAttribute("href")).toBe("/encuestas/7/resultados/rondas/12/exportar/?formato=xlsx");
    expect(document.querySelector(".stat-card-value")?.textContent).toBe("3");
    expect(document.querySelector(".stat-accent-estado")?.className).toContain("is-abierta");
    expect(document.querySelector(".stat-accent-estado i")?.className).toContain("fa-lock-open");
    expect(screen.getByText("08/10/2026")).toBeTruthy();
    expect(screen.getByText("3 respuestas")).toBeTruthy();
    expect(screen.getByText("Opción única")).toBeTruthy();
    const rows = document.querySelectorAll(".result-bar-row");
    expect(rows[0].className).toContain("is-leading");
    expect(rows[1].className).not.toContain("is-leading");
    expect(rows[0].textContent).toContain("Bueno2 (66,7%)");
  });

  it("changes the round with a GET to the page, like the native onchange", async () => {
    serve(page());
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign, pathname: "/encuestas/7/resultados/", search: "" });
    render(<App />);
    await screen.findByRole("heading", { name: "Resultados" });
    fireEvent.change(screen.getByLabelText("Ronda"), { target: { value: "11" } });
    expect(assign).toHaveBeenCalledWith("/encuestas/7/resultados/?ronda=11");
  });

  it("passes the page query through and falls back to the first round when none is current", async () => {
    window.history.replaceState({}, "", "/encuestas/7/resultados/?ronda=99");
    serve(page({ ronda_actual: null, rondas: [{ id: 12, selected: false, label: "Ronda 2" }, { id: 11, selected: false, label: "Ronda 1" }], resultados: [] }));
    render(<App />);
    await screen.findByRole("heading", { name: "Resultados" });
    expect(webGet).toHaveBeenCalledWith("web/encuestas/7/resultados/?ronda=99", expect.anything());
    expect((screen.getByLabelText("Ronda") as HTMLSelectElement).value).toBe("12");
    expect(screen.queryByRole("link", { name: /CSV/ })).toBeNull();
    expect(document.querySelector(".stat-cards")).toBeNull();
  });

  it("says so when the survey has no rounds", async () => {
    serve(page({ rondas: [], ronda_actual: null, resultados: [] }));
    render(<App />);
    expect(await screen.findByText("Esta encuesta todavía no tiene rondas.")).toBeTruthy();
    expect(screen.queryByLabelText("Ronda")).toBeNull();
  });

  it("draws the score ranking, the numeric range and the free text answers", async () => {
    serve(page({
      ronda_actual: { id: 12, respuestas: 1, abierta: false, estado_label: "Cerrada", cierre: "08/10/2026", export_url: "/encuestas/7/resultados/rondas/12/exportar/" },
      puntajes: [{ usuario: "Ana", obtenido: 3, total_posible: 3, porcentaje: "100,0" }, { usuario: "", obtenido: 1, total_posible: 3, porcentaje: "33,3" }],
      resultados: [
        resultado({ tipo: "escala", total_respuestas: 1, opciones: [], opcion_lider_texto: null, numerico: { promedio: "6,0", minimo: "4", maximo: "8", posicion: "50,0" } }),
        resultado({ tipo: "texto_largo", total_respuestas: 1, opciones: [], opcion_lider_texto: null, respuestas_texto: ["Todo bien"] }),
        resultado({ tipo: "texto_corto", total_respuestas: 0, opciones: [], opcion_lider_texto: null }),
      ],
    }));
    render(<App />);
    await screen.findByRole("heading", { name: "Resultados" });
    expect(document.querySelector(".stat-accent-estado i")?.className).toContain("fa-lock");
    expect(document.querySelector(".stat-accent-estado i")?.className).not.toContain("fa-lock-open");
    expect(document.querySelector(".count-badge")?.textContent).toBe("Total posible: 3 pts");
    expect(screen.getByText("#1").parentElement?.textContent).toBe("#1 Ana");
    expect(screen.getByText("#2").parentElement?.textContent).toBe("#2 Respuesta anónima");
    expect(document.querySelectorAll(".result-bar-row")[0].className).toContain("is-leading");
    expect(document.querySelector(".result-bar-valor")?.textContent).toBe("3 / 3 (100,0%)");
    expect(document.querySelector(".numeric-range-marker-label")?.textContent).toBe("6,0");
    expect(document.querySelectorAll(".numeric-stat-value")[0].textContent).toBe("4");
    expect(screen.getByText("Escala")).toBeTruthy();
    expect(screen.getByText("Todo bien")).toBeTruthy();
    expect(screen.getAllByText("1 respuesta").length).toBe(2);
    expect(screen.getByText("0 respuestas")).toBeTruthy();
    expect(screen.getByText("Sin respuestas todavía.")).toBeTruthy();
  });

  it("shows the access screen on 403", async () => {
    webGet.mockImplementation((url: string) =>
      Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "No tiene permisos para esta acción." }, status: 403 }));
    render(<App />);
    expect(await screen.findByText(/permiso/i)).toBeTruthy();
    expect(screen.queryByLabelText("Ronda")).toBeNull();
  });
});
