import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { dashboardValid, tableroValid } from "./dashboardTableros";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const metricas = { cantidad_comedores_activos: "1234", cantidad_relevamientos_activos: "56", presupuesto_desayuno: "7000", presupuesto_merienda: "8000", presupuesto_comida: "9000" };
const dash = (over = {}) => ({ can_view: true, metricas_desactualizadas: false, metricas_disponibles: true, metricas, messages: [], ...over });
const tablero = (over = {}) => ({
  titulo: "Tablero Prueba", nombre: "Prueba", url: "https://app.powerbi.com/view?r=abc", embed_url: "https://app.powerbi.com/view?r=abc",
  looker_compartible: false, mensaje_construccion: "", messages: [], ...over,
});
const serve = (data: unknown, status = 200) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("dashboard de Centro de Familia", () => {
  beforeEach(() => window.history.replaceState({}, "", "/dashboard/centro-de-familia"));

  it("owns the exact native paths and validates both payloads", () => {
    expect(findRoute("/dashboard/centro-de-familia")?.route.name).toBe("dashboard-centro-de-familia");
    expect(findRoute("/dashboard/prueba/")?.route.name).toBe("dashboard-tablero");
    expect(findRoute("/dashboard/centro-de-familia/")?.route.name).toBe("dashboard-tablero");
    expect(dashboardValid(dash())).toBe(true);
    expect(dashboardValid(dash({ can_view: false, metricas: null }))).toBe(true);
    expect(dashboardValid(dash({ metricas: null }))).toBe(false);
    expect(dashboardValid(dash({ can_view: false, metricas }))).toBe(false);
    expect(tableroValid(tablero())).toBe(true);
    expect(tableroValid(tablero({ url: "javascript:alert(1)" }))).toBe(false);
    expect(tableroValid(tablero({ embed_url: "http://insecure/" }))).toBe(false);
  });

  it("draws the indicators, the cards and the two remote reports for a viewer", async () => {
    serve(dash());
    render(<App />);
    expect(await screen.findByText("Datos de Centro De Familia")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/dashboard/centro-de-familia/", expect.anything());
    expect(screen.getByText("Comedores Activos").previousElementSibling?.textContent).toBe("1234");
    expect(screen.getByText("Relevamientos Activos").previousElementSibling?.textContent).toBe("56");
    expect(screen.getByText("Beneficiarios").previousElementSibling?.textContent).toBe("0");
    expect(screen.getByText("Duplas").nextElementSibling?.textContent).toBe("7000");
    expect(screen.getByText("Presupuesto Desayuno").nextElementSibling?.textContent).toBe("$7000");
    expect(screen.getByText("Presupuesto Merienda").nextElementSibling?.textContent).toBe("$8000");
    expect(screen.getByText("Presupuesto Comida").nextElementSibling?.textContent).toBe("$9000");
    expect(screen.getByTitle("Tablero - Comedores").getAttribute("src")).toContain("reportEmbed?reportId=35d6f754");
    expect(screen.getByTitle("Centros de Familia - Seguimiento del programa v3").getAttribute("src")).toContain("app.powerbi.com/view?r=");
    expect(document.querySelector('link[href="https://cdn.jsdelivr.net/npm/charts.css/dist/charts.min.css"]')).toBeTruthy();
    expect(document.querySelector('link[href="https://code.ionicframework.com/ionicons/2.0.1/css/ionicons.min.css"]')).toBeTruthy();
  });

  it("collapses the Centro de Familia card with its tool button", async () => {
    serve(dash());
    render(<App />);
    await screen.findByText("Datos de Centro De Familia");
    const card = document.querySelector(".card") as HTMLElement;
    fireEvent.click(card.querySelector('[data-card-widget="collapse"]') as HTMLElement);
    expect(card.classList.contains("collapsed-card")).toBe(true);
    expect((card.querySelector(".card-body") as HTMLElement).style.display).toBe("none");
    fireEvent.click(card.querySelector('[data-card-widget="collapse"]') as HTMLElement);
    expect(card.classList.contains("collapsed-card")).toBe(false);
  });

  it("shows the logo only, with no numbers, when the user cannot view the dashboard", async () => {
    serve(dash({ can_view: false, metricas: null }));
    render(<App />);
    expect(await screen.findByAltText("Capacitación Humano")).toBeTruthy();
    expect(screen.queryByText("Comedores Activos")).toBeNull();
    expect(document.querySelector("iframe")).toBeNull();
  });

  it("warns that the remote source failed and never turns a missing value into zero", async () => {
    const sin = Object.fromEntries(Object.keys(metricas).map((k) => [k, "Sin información"]));
    serve(dash({ metricas_desactualizadas: true, metricas_disponibles: false, metricas: sin }));
    render(<App />);
    const alert = await screen.findByText(/No se pudieron actualizar/);
    expect(alert.textContent).toBe("No se pudieron actualizar los indicadores de Comedores. Todavía no hay información disponible.");
    expect(screen.getByText("Comedores Activos").previousElementSibling?.textContent).toBe("Sin información");
    expect(screen.getByText("Presupuesto Comida").nextElementSibling?.textContent).toBe("$Sin información");
  });

  it("keeps the last available values when the refresh failed", async () => {
    serve(dash({ metricas_desactualizadas: true }));
    render(<App />);
    const alert = await screen.findByText(/No se pudieron actualizar/);
    expect(alert.textContent).toContain("Se muestran los últimos valores disponibles.");
    expect(screen.getByText("Comedores Activos").previousElementSibling?.textContent).toBe("1234");
  });

  it("shows the access screen on 403", async () => {
    serve({ detail: "No tiene permisos para esta acción." }, 403);
    render(<App />);
    expect(await screen.findByText(/permiso/i)).toBeTruthy();
    expect(screen.queryByText("Datos de Centro De Familia")).toBeNull();
  });
});

describe("tablero embebido", () => {
  beforeEach(() => window.history.replaceState({}, "", "/dashboard/prueba/"));

  it("draws the iframe, the new-tab link and no Looker hint for a plain board", async () => {
    serve(tablero());
    render(<App />);
    expect(await screen.findByText("Tablero Prueba")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/dashboard/prueba/", expect.anything());
    expect(screen.getByTitle("Prueba").getAttribute("src")).toBe("https://app.powerbi.com/view?r=abc");
    const link = screen.getByRole("link", { name: "Abrir tablero en una pestana nueva" });
    expect(link.getAttribute("href")).toBe("https://app.powerbi.com/view?r=abc");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(screen.queryByText(/Looker Studio sigue bloqueando/)).toBeNull();
  });

  it("explains the Looker Studio share URL and keeps the embed URL apart", async () => {
    serve(tablero({ url: "https://lookerstudio.google.com/u/0/reporting/abc", embed_url: "https://lookerstudio.google.com/embed/reporting/abc", looker_compartible: true }));
    render(<App />);
    await screen.findByText("Tablero Prueba");
    expect(screen.getByTitle("Prueba").getAttribute("src")).toBe("https://lookerstudio.google.com/embed/reporting/abc");
    expect(screen.getByText(/Si Looker Studio sigue bloqueando el iframe/).textContent).toBe("Si Looker Studio sigue bloqueando el iframe, reemplaza esta URL por la generada en File > Embed report.");
  });

  it("shows the under-construction state with the board message and no iframe", async () => {
    serve(tablero({ url: "", embed_url: "", mensaje_construccion: "El tablero de Prueba estará disponible próximamente." }));
    render(<App />);
    expect(await screen.findByText("Tablero en confección")).toBeTruthy();
    expect(screen.getByText("El tablero de Prueba estará disponible próximamente.")).toBeTruthy();
    expect(document.querySelector("iframe")).toBeNull();
  });

  it("collapses the card like the native tool button", async () => {
    serve(tablero());
    render(<App />);
    await screen.findByText("Tablero Prueba");
    const card = document.querySelector(".card") as HTMLElement;
    fireEvent.click(card.querySelector('[data-card-widget="collapse"]') as HTMLElement);
    expect(card.querySelector("i.fa-plus")).toBeTruthy();
  });

  it("follows the native redirect of a board with its own screen", async () => {
    serve({ redirect: "/celiaquia/tablero/" });
    const replace = vi.fn();
    vi.stubGlobal("location", { ...window.location, replace, pathname: "/dashboard/prueba/", search: "" });
    render(<App />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/celiaquia/tablero/"));
  });

  it("shows the access screen when the board denies the user", async () => {
    serve({ detail: "No tiene permisos para esta acción." }, 403);
    render(<App />);
    expect(await screen.findByText(/permiso/i)).toBeTruthy();
    expect(screen.queryByText("Tablero Prueba")).toBeNull();
  });
});
