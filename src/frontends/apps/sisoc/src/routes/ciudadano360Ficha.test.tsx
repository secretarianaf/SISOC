import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { fichaValid } from "./ciudadano360";
import { chartConfig, DatosPersonales, ficha360Navigation, HistorialCard, InteraccionesTabla, TABS } from "./ciudadano360Ficha";
import { fichaExtra } from "./ciudadano360Fixtures";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const base = { id: 7, nombre: "Ana", apellido: "Aporte", tipo_documento_texto: "DNI", numero_documento: "30111222", pais_emisor: null, identificador_interno: null, aportes: [] };
const ficha = (over: Parameters<typeof fichaExtra>[0] = {}) => ({ ...base, ...fichaExtra(over) });
const CHART_SRC = 'script[src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"]';
const setChart = (chart: unknown) => { (window as unknown as { Chart: unknown }).Chart = chart; };
const periodo = () => document.getElementById("mes-actual")?.textContent;
const arrow = (name: string) => document.querySelector(`.${name}`)?.closest("button") as HTMLElement;

function serve(data: unknown) {
  webGet.mockImplementation((url: string) =>
    Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
}

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.history.replaceState({}, "", "/ciudadanos/ver/7");
  delete window.Chart;
  document.querySelectorAll(CHART_SRC).forEach((s) => s.remove());
  // jsdom has no canvas: the chart only needs a 2d context to be handed over.
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("fichaValid", () => {
  it("accepts the projection and rejects a missing or malformed section", () => {
    expect(fichaValid(ficha())).toBe(true);
    expect(fichaValid({ ...ficha(), historial: undefined })).toBe(false);
    expect(fichaValid(ficha({ acciones: { ...fichaExtra().acciones, editar_url: "http://evil/" } }))).toBe(false);
    expect(fichaValid(ficha({ interacciones: [{ tipo: "x", fecha_texto: "1", responsable_texto: "y", estado: "raro" as never }] }))).toBe(false);
    expect(fichaValid(ficha({ messages: [{ message: "m", level: "fatal" as never }] }))).toBe(false);
  });
});

describe("Ciudadano 360 page", () => {
  it("draws the header actions: Historial only with permission, Editar and Dar de baja as links", async () => {
    serve(ficha({ acciones: { ...fichaExtra().acciones, historial_url: "/audittrail/ciudadanos/ciudadano/7/" } }));
    render(<App />);
    expect((await screen.findByRole("link", { name: "Historial" })).getAttribute("href")).toBe("/audittrail/ciudadanos/ciudadano/7/");
    expect(screen.getAllByRole("link", { name: "Editar" })[0].getAttribute("href")).toBe("/ciudadanos/editar/7");
    expect(screen.getByRole("link", { name: "Dar de baja" }).getAttribute("href")).toBe("/ciudadanos/eliminar/7");
  });

  it("has no Historial link without permission", async () => {
    serve(ficha());
    render(<App />);
    await screen.findByRole("heading", { level: 1, name: /Ana Aporte/ });
    expect(screen.queryByRole("link", { name: "Historial" })).toBeNull();
  });

  it("shows the identity notice with the reason and the description", async () => {
    serve(ficha({ identidad: { mostrar: true, sin_dni: true, no_validado: false, requiere_revision: true, motivo_texto: "Extravío", descripcion_texto: "Perdió el DNI" } }));
    render(<App />);
    expect(await screen.findByText("Sin DNI")).toBeTruthy();
    expect(screen.getByText("Requiere revisión")).toBeTruthy();
    expect(screen.getByText(/Extravío/).textContent).toBe("Extravío — Perdió el DNI");
    expect(screen.queryByText("RENAPER no validado")).toBeNull();
  });

  it("lists the eleven tabs and shows one pane at a time (click and arrow keys)", async () => {
    serve(ficha());
    render(<App />);
    const nav = await screen.findByRole("tablist");
    const links = within(nav).getAllByRole("tab");
    expect(links.map((l) => l.textContent)).toEqual(TABS.map(([, label]) => label));
    expect(links[0].className).toContain("active");
    const pane = (id: string) => document.getElementById(id) as HTMLElement;
    expect(pane("datos-personales").className).toContain("show active");
    fireEvent.click(links[4]);
    expect(pane("comedor").className).toContain("show active");
    expect(pane("datos-personales").className).not.toContain("active");
    expect(links[4].getAttribute("aria-selected")).toBe("true");
    expect(links[0].getAttribute("tabindex")).toBe("-1");
    fireEvent.keyDown(links[4], { key: "ArrowRight" });
    expect(pane("cdf").className).toContain("show active");
    fireEvent.keyDown(links[5], { key: "ArrowLeft" });
    expect(pane("comedor").className).toContain("show active");
  });

  it("marks up the tabs like Bootstrap does on load: only the active tab is in the Tab order", async () => {
    serve(ficha());
    render(<App />);
    const pas = (await screen.findAllByRole("tab", { name: "PAS" }))[0];
    expect(pas.getAttribute("aria-selected")).toBe("false");
    expect(pas.getAttribute("tabindex")).toBe("-1");
    expect(screen.getByRole("tab", { name: "Datos personales" }).getAttribute("tabindex")).toBeNull();
    expect(document.getElementById("pas")?.getAttribute("role")).toBe("tabpanel");
  });

  it("shows the family, the interactions and the observations the server sent", async () => {
    serve(ficha({
      familia: [{ vinculo_texto: "Hijo/a", nombre: "Zoe", apellido: "Zeta", edad_texto: "-", url: "/ciudadanos/ver/9" }],
      interacciones: [
        { tipo: "Llamada", fecha_texto: "04 Mar 2026", responsable_texto: "Julia Paz", estado: "completo" },
        { tipo: "Visita", fecha_texto: "01 Feb 2026", responsable_texto: "Sin asignar", estado: "en_plan" },
        { tipo: "Aviso", fecha_texto: "02 Feb 2026", responsable_texto: "Sin asignar", estado: "pendiente" },
      ],
      observaciones: "Sin novedades <b>",
    }));
    render(<App />);
    expect((await screen.findByRole("link", { name: /Ver legajo/ })).getAttribute("href")).toBe("/ciudadanos/ver/9");
    expect(screen.getByText("Hijo/a:")).toBeTruthy();
    expect(screen.getAllByText("Completo")[0].getAttribute("style")).toContain("var(--green)");
    expect(screen.getAllByText("En Plan").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Pendiente").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Sin novedades <b>").length).toBeGreaterThan(0);
    expect(screen.queryByText("No hay observaciones registradas.")).toBeNull();
  });

  it("shows the empty states", async () => {
    serve(ficha());
    render(<App />);
    expect(await screen.findByText("Aún no hay familiares cargados.")).toBeTruthy();
    expect(screen.getAllByText("No hay interacciones registradas.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("No hay observaciones registradas.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Contenido en desarrollo...").length).toBe(6);
  });

  it("renders the flash messages the server consumed", async () => {
    serve(ficha({ messages: [{ message: "Ciudadano Aporte, Ana marcado como revisado.", level: "success" }] }));
    render(<App />);
    expect(await screen.findByText("Ciudadano Aporte, Ana marcado como revisado.")).toBeTruthy();
  });

  it("shows $0.00 as the Centro de Familia amount when that provider is not listed", async () => {
    serve(ficha());
    render(<App />);
    await screen.findByRole("heading", { level: 1, name: /Ana Aporte/ });
    expect(document.querySelector(".programa-card.centro-familia .monto")?.textContent).toBe("$0.00");
  });
});

describe("Datos personales", () => {
  it("draws the map when there are coordinates, else the photo, else the placeholder", () => {
    const { container, rerender } = render(<DatosPersonales extra={fichaExtra({ mapa: "-34.6,-58.4" })} tail={null} />);
    expect(container.querySelector("iframe")?.getAttribute("src")).toBe("https://www.google.com/maps?q=-34.6,-58.4&output=embed");
    rerender(<DatosPersonales extra={fichaExtra({ foto_url: "/media/f.png" })} tail={null} />);
    expect(container.querySelector("img")?.getAttribute("src")).toBe("/media/f.png");
    rerender(<DatosPersonales extra={fichaExtra()} tail={null} />);
    expect(container.querySelector(".foto-placeholder .fa-map-marker-alt")).not.toBeNull();
  });

  it("omits País Emisor when empty and draws it when present", () => {
    const { rerender } = render(<DatosPersonales extra={fichaExtra()} tail={null} />);
    expect(screen.queryByText("País Emisor:")).toBeNull();
    rerender(<DatosPersonales extra={fichaExtra({ datos: { ...fichaExtra().datos, pais_emisor: "Chile" } })} tail={null} />);
    expect(screen.getByText("Chile")).toBeTruthy();
    expect(screen.getByText("Calle y Altura:").nextSibling?.textContent).toBe("Mitre 123");
  });
});

describe("History chart", () => {
  it("uses the native chart configuration", () => {
    const config = chartConfig(fichaExtra().historial) as { data: { datasets: { label: string; backgroundColor: string }[] }; options: { scales: { y: { max: number } } } };
    expect(config.data.datasets.map((d) => [d.label, d.backgroundColor])).toEqual([["AUH", "#FF8C42"], ["Prestación Alimentar", "#FFB84D"], ["Centro de Familia", "#D63384"], ["Comedor", "#F8A5C2"]]);
    expect(config.options.scales.y.max).toBe(500);
  });

  it("draws with Chart.js once the script has loaded and redraws on a month change", async () => {
    const destroy = vi.fn();
    const Chart = vi.fn(function Chart() { return { destroy }; });
    render(<HistorialCard historial={fichaExtra().historial} />);
    const script = document.querySelector<HTMLScriptElement>(CHART_SRC);
    expect(script).not.toBeNull();
    setChart(Chart);
    act(() => { script?.dispatchEvent(new Event("load")); });
    await waitFor(() => expect(Chart).toHaveBeenCalledTimes(1));
    const before = periodo();
    fireEvent.click(arrow("fa-chevron-right"));
    await waitFor(() => expect(Chart).toHaveBeenCalledTimes(2));
    expect(destroy).toHaveBeenCalledTimes(1);
    expect(periodo()).not.toBe(before);
  });

  it("rolls the year over at the ends of the period", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-01-15T12:00:00Z"));
    setChart(vi.fn(function Chart() { return { destroy: vi.fn() }; }));
    render(<HistorialCard historial={fichaExtra().historial} />);
    expect(periodo()).toBe("1 Enero 2026");
    fireEvent.click(arrow("fa-chevron-left"));
    expect(periodo()).toBe("12 Diciembre 2025");
    fireEvent.click(arrow("fa-chevron-right"));
    expect(periodo()).toBe("1 Enero 2026");
    vi.useRealTimers();
  });
});

describe("Interacciones", () => {
  const una = [{ tipo: "Llamada", fecha_texto: "04 Mar 2026", responsable_texto: "Sin asignar", estado: "pendiente" as const }];
  it("keeps the inert search control of the native table", () => {
    render(<InteraccionesTabla interacciones={[]} />);
    expect(screen.getByPlaceholderText("Buscar")).toBeTruthy();
  });

  it("keeps the native spelling of the first column: accented only in Datos personales", () => {
    const { rerender } = render(<InteraccionesTabla interacciones={una} conTilde />);
    expect(screen.getByRole("columnheader", { name: "Interacción" })).toBeTruthy();
    rerender(<InteraccionesTabla interacciones={una} />);
    expect(screen.getByRole("columnheader", { name: "Interaccion" })).toBeTruthy();
  });
});

describe("Marcar revisado", () => {
  const MARCAR = "/api/web/ciudadanos/7/marcar-revisado/";
  const withButton = () => serve(ficha({ acciones: { ...fichaExtra().acciones, marcar_revisado_url: MARCAR } }));
  const button = async () => screen.findByRole("button", { name: /Marcar revisado/ });

  it("draws the native form only when the server offers the action", async () => {
    withButton();
    render(<App />);
    const form = (await button()).closest("form") as HTMLFormElement;
    expect(form.getAttribute("action")).toBe("/ciudadanos/7/marcar-revisado/");
    expect(form.method).toBe("post");
    expect((form.querySelector("input[name=csrfmiddlewaretoken]") as HTMLInputElement).value).toBe("synthetic-csrf-token");
    cleanup();
    serve(ficha());
    render(<App />);
    await screen.findByRole("heading", { level: 1, name: /Ana Aporte/ });
    expect(screen.queryByRole("button", { name: /Marcar revisado/ })).toBeNull();
  });

  it("asks first and sends nothing when the confirmation is declined", async () => {
    withButton();
    const confirm = vi.spyOn(ficha360Navigation, "confirm").mockReturnValue(false);
    render(<App />);
    fireEvent.click(await button());
    expect(confirm).toHaveBeenCalledWith("¿Marcar este ciudadano como revisado?");
    expect(webPost).not.toHaveBeenCalled();
  });

  it("posts once and follows the redirect (a second click does not resend)", async () => {
    withButton();
    vi.spyOn(ficha360Navigation, "confirm").mockReturnValue(true);
    const assign = vi.spyOn(ficha360Navigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/ciudadanos/ver/7" }, status: 200 });
    render(<App />);
    const marcar = await button();
    fireEvent.click(marcar);
    fireEvent.click(marcar);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/ciudadanos/ver/7"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/ciudadanos/7/marcar-revisado/");
  });

  it("shows the server's refusal and an unconfirmed outcome without navigating or resending", async () => {
    withButton();
    vi.spyOn(ficha360Navigation, "confirm").mockReturnValue(true);
    const assign = vi.spyOn(ficha360Navigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValueOnce({ data: { detail: "Sin permiso" }, status: 403 });
    render(<App />);
    fireEvent.click(await button());
    expect((await screen.findByRole("alert")).textContent).toBe("Sin permiso");
    expect(assign).not.toHaveBeenCalled();
    expect((await button()).hasAttribute("disabled")).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("reports an unconfirmed outcome (network failure) with the standard text", async () => {
    withButton();
    vi.spyOn(ficha360Navigation, "confirm").mockReturnValue(true);
    webPost.mockRejectedValueOnce(new Error("network"));
    render(<App />);
    fireEvent.click(await button());
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo confirmar el resultado. Actualice la página antes de volver a intentar.");
  });
});
