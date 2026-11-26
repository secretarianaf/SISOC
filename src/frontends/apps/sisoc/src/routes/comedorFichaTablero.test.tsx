import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { FichaTablero, edadChartConfig, tableroValid, withChartJs } from "./comedorFichaTablero";
import { tableroFixture } from "./comedorFichaFixtures";

afterEach(cleanup);

describe("Comedor ficha: board", () => {
  it("validates the payload", () => {
    expect(tableroValid(tableroFixture())).toBe(true);
    expect(tableroValid({ ...tableroFixture(), resumen: [{ icon: 1 }] })).toBe(false);
    expect(tableroValid(null)).toBe(false);
  });

  it("timeline: sent admission shows the check, the completed connector and the active execution", () => {
    const t = tableroFixture();
    t.timeline = { admision: { clase: "step completed", circulo: "1", completada: true, fecha: "01/10/2026" }, conector: "connector completed", ejecucion: { clase: "step active", circulo: "2" }, rendicion: { circulo: "3" } };
    render(<FichaTablero data={t} />);
    expect(document.querySelector(".step.completed .circle i.bi-check-lg")).toBeTruthy();
    expect(document.querySelector(".connector.completed.mb-3")).toBeTruthy();
    expect(document.querySelector(".step.active .circle")!.textContent).toBe("2");
    expect(screen.getByText("01/10/2026")).toBeTruthy();
  });

  it("summary boxes keep the native icons and texts", () => {
    render(<FichaTablero data={tableroFixture()} />);
    expect(document.querySelectorAll(".small-box.bg-card")).toHaveLength(4);
    expect(document.querySelector(".small-box i")!.className).toBe("bi bi-cup-hot mb-1");
    expect(screen.getByText("1° / 2")).toBeTruthy();
    expect(screen.getByText("Asistencia por rango etareo")).toBeTruthy();
    expect(document.getElementById("nominaEdadChart")).toBeTruthy();
  });

  it("admission card: rows, uppercase marks and the link; a disabled button without admission", () => {
    render(<FichaTablero data={tableroFixture()} />);
    expect(screen.getByText("EX-1").className).toBe("text-uppercase");
    expect(screen.getByRole("link", { name: "Ver detalles" }).getAttribute("href")).toBe("/comedores/7/admision/3/detalle/");
    cleanup();
    const sin = tableroFixture();
    sin.detalles.accion = { label: "Ver detalles", url: null };
    render(<FichaTablero data={sin} />);
    expect((screen.getByRole("button", { name: "Ver detalles" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("convenio card: territorials and the edit link", () => {
    const t = tableroFixture({ detalles: { tipo: "convenio", titulo: "Datos del Convenio", territoriales: [{ territorial: "Ana", codigo: "P-1" }], filas: [{ label: "Nro convenio", value: "C-9" }], accion: { label: "Editar datos del Convenio", url: "/comedores/7/convenio-pnud/" } } });
    render(<FichaTablero data={t} />);
    expect(screen.getByText("Territoriales Asignados")).toBeTruthy();
    expect(screen.getByText(/Ana — Código de Proyecto: P-1/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Editar datos del Convenio" }).getAttribute("href")).toBe("/comedores/7/convenio-pnud/");
  });

  it("card-holder card only when the API sends it, with the empty text and the edit link", () => {
    render(<FichaTablero data={tableroFixture()} />);
    expect(document.getElementById("card-responsable-tarjeta")).toBeNull();
    cleanup();
    render(<FichaTablero data={tableroFixture({ responsable_tarjeta: { hay_datos: false, datos: [], editar: "/comedores/7/responsable-tarjeta/editar" } })} />);
    expect(screen.getByText("Sin datos cargados.")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Editar datos/ }).getAttribute("href")).toBe("/comedores/7/responsable-tarjeta/editar");
    cleanup();
    render(<FichaTablero data={tableroFixture({ responsable_tarjeta: { hay_datos: true, datos: [["Nombre", "Ana"]], editar: "/x/" } })} />);
    expect(screen.getByText("Nombre:").closest("p")!.textContent).toBe("Nombre: Ana");
  });

  it("slots: rows between the cards and the aside column", () => {
    render(<FichaTablero data={tableroFixture()} rows={<div id="fila-extra" />} aside={<div id="columna-nomina" className="col-12 col-lg-3" />} />);
    expect(document.getElementById("fila-extra")).toBeTruthy();
    expect(document.getElementById("columna-nomina")!.parentElement!.className).toBe("row mb-3");
  });

  it("chart config: percentages, next-ten axis maximum capped at 100, tooltip and tick suffix", () => {
    const config = edadChartConfig(tableroFixture().grafico);
    expect(config.data.labels).toEqual(["Sin dato", "0-13 años", "14-17 años", "18-49 años", "50-65 años", "+66 años"]);
    expect(config.data.datasets[0].data).toEqual([5, 12.5, 0, 60, 15, 7.5]);
    expect(config.options.scales.y.max).toBe(60);
    expect(edadChartConfig([{ label: "a", valor: 0 }]).options.scales.y.max).toBe(10);
    expect(edadChartConfig([{ label: "a", valor: 99.5 }]).options.scales.y.max).toBe(100);
    expect(config.options.scales.y.ticks.callback(30)).toBe("30%");
    expect(config.options.plugins.tooltip.callbacks.label({ parsed: { y: 12.5 } })).toBe("12.5%");
  });

  it("the chart is drawn once Chart.js is available and destroyed on unmount", () => {
    const destroy = vi.fn();
    const Chart = vi.fn(function Chart() { return { destroy }; });
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
    (window as unknown as { Chart: unknown }).Chart = Chart;
    const run = vi.fn();
    withChartJs(run);
    expect(run).toHaveBeenCalledWith(Chart);
    const { unmount } = render(<FichaTablero data={tableroFixture()} />);
    expect(Chart).toHaveBeenCalledTimes(1);
    unmount();
    expect(destroy).toHaveBeenCalledTimes(1);
    delete (window as unknown as { Chart?: unknown }).Chart;
    getContext.mockRestore();
  });
});
