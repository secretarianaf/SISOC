import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const areas = ["panel", "formacion", "cruces", "mesa-ayuda", "liquidacion"].map((key, i) => ({
  key, number: `0${i + 1}`, title: key, subtitle: key, url: `/pas/${key}`, active: key === "cruces", source_status: "disponible",
}));
const etapa = (numero: number, nombre: string, extra = {}) => ({
  numero, nombre, fecha: null, fecha_texto: "", completada: false, integracion_pendiente: numero > 2, ...extra,
});
const etapas = (first = {}) => [
  etapa(1, "Exportación a SINTyS (VIAS)", first), etapa(2, "Importación retorno SINTyS"), etapa(3, "Cruce FTP Justicia"),
  etapa(4, "Cruce Migraciones"), etapa(5, "Procesamiento de alertas"), etapa(6, "Cierre del circuito mensual"),
];
const page = (extra = {}) => ({
  can_change: true, total_padron: 12,
  circuito: { periodo: "2026-11-01", periodo_texto: "11/2026", existe: false },
  etapas: etapas(), renaper: { fecha: null, total: 0, fallecidas: 0, errores: 0 }, incompatibilidades: [], areas, ...extra,
});
const row = (n: number) => ({
  titular: `Apellido${n}, Nombre${n}`, dni: 30000000 + n, categoria: "Supervivencia", detalle: `Detalle ${n}`,
  fecha_deteccion: "03/11/2026 10:15", periodo_impacto: "12/2026", estado: "Pendiente",
});

function serve(...pages: unknown[]) {
  const queue = [...pages];
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/"
    ? { data: readyContext, status: 200 } : { data: queue.length > 1 ? queue.shift() : queue[0], status: 200 }));
}
const cruces = () => webGet.mock.calls.filter(([url]) => url === "web/pas/cruces/").length;
async function open() {
  window.history.replaceState({}, "", "/pas/cruces");
  render(<App />);
  return screen.findByRole("heading", { name: "Circuito administrativo mensual" });
}
const toast = () => document.querySelector("body > #toast-container");

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => cleanup());

describe("PAS03.02 results and evidence", () => {
  it("prints the pending circuit with the native texts and order", async () => {
    serve(page());
    await open();
    expect(document.title).toContain("Cruces y Novedades · PAS");
    expect(screen.getByRole("heading", { level: 1, name: "Cruces y Novedades" })).toBeTruthy();
    expect(screen.getByText("RENAPER · control diario").className).toBe("pas-source-chip");
    expect(screen.getByText("Período 11/2026 · 12 titulares incluidos")).toBeTruthy();
    const steps = [...document.querySelectorAll(".pas-circuit-steps li")];
    expect(steps.map((li) => li.querySelector("strong")?.textContent)).toEqual([
      "Exportación a SINTyS (VIAS)", "Importación retorno SINTyS", "Cruce FTP Justicia", "Cruce Migraciones", "Procesamiento de alertas", "Cierre del circuito mensual",
    ]);
    expect(steps.map((li) => li.className)).toEqual(Array(6).fill("is-pending"));
    expect(steps.map((li) => li.querySelector(".pas-stage-marker")?.textContent)).toEqual(["1", "2", "3", "4", "5", "6"]);
    expect(steps.map((li) => li.querySelector(".pas-stage-status")?.textContent)).toEqual(Array(6).fill("Pendiente"));
    expect(steps.map((li) => !!li.querySelector("small"))).toEqual([false, false, true, true, true, true]);
    expect(screen.getAllByText("Integración no disponible")).toHaveLength(4);
    const grid = screen.getByLabelText("Estado de fuentes externas");
    expect([...grid.children].map((c) => c.textContent)).toEqual([
      "Supervivencia (RENAPER)Sin ejecución registrada Actualizar", "Ingresos (AFIP / Empleo)Pendiente de API", "Patrimonio (DNRPA / CNPB)Pendiente de API",
      "Situación penal (M. Justicia)Pendiente de FTP", "Cuentas BNA sin movimientoPendiente de API", "Migraciones — traslados ext.Pendiente de API",
    ]);
    expect(screen.getByText("0 pendientes").className).toBe("pas-source-chip is-pending");
    expect(screen.getByText("Sin incompatibilidades de supervivencia")).toBeTruthy();
    expect(screen.getByText("Los resultados RENAPER fallecidos impactarán aquí para el período siguiente.")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Buscador PAS/ }).getAttribute("href")).toBe("/pas/listar");
  });

  it("prints a completed stage, the RENAPER state and the tray rows", async () => {
    serve(page({
      etapas: etapas({ completada: true, fecha: "2026-11-03T10:15:00-03:00", fecha_texto: "03/11/2026 10:15" }),
      renaper: { fecha: "29/07/2026", total: 1, fallecidas: 1, errores: 0 }, incompatibilidades: [row(1), row(2)],
    }));
    await open();
    const first = document.querySelector(".pas-circuit-steps li")!;
    expect(first.className).toBe("is-complete");
    expect(first.querySelector(".pas-stage-marker i.bi-check-lg")).toBeTruthy();
    expect(first.querySelector("time")?.getAttribute("datetime")).toBe("2026-11-03T10:15:00-03:00");
    expect(first.querySelector("time")?.textContent).toBe("03/11/2026 10:15");
    expect(screen.getByText("Actualizado 29/07/2026 · 1 control").className).toBe("is-synced");
    expect(screen.getByText("2 pendientes")).toBeTruthy();
    const cells = [...document.querySelectorAll(".pas-incompatibility-table tbody tr")[0].children].map((c) => c.textContent);
    expect(cells).toEqual(["Apellido1, Nombre1", "30000001", "Supervivencia", "Detalle 1", "03/11/2026 10:15", "12/2026", "Pendiente"]);
    expect([...document.querySelectorAll(".pas-incompatibility-table th")].map((c) => c.textContent)).toEqual(
      ["Titular", "DNI", "Categoría", "Detalle", "Detección", "Impacta en", "Estado"]);
  });

  it("pluralizes the checks and marks errors", async () => {
    serve(page({ renaper: { fecha: "29/07/2026", total: 3, fallecidas: 0, errores: 2 }, incompatibilidades: [row(1)] }));
    await open();
    expect(screen.getByText("Actualizado 29/07/2026 · 3 controles").className).toBe("has-errors");
    expect(screen.getByText("1 pendiente")).toBeTruthy();
  });

  it("hides every action without the change permission", async () => {
    serve(page({ can_change: false }));
    await open();
    expect(screen.queryByRole("button", { name: /Exportar a SINTyS/ })).toBeNull();
    expect(screen.queryByText("Importar retorno")).toBeNull();
    expect(screen.queryByRole("button", { name: /Actualizar/ })).toBeNull();
    expect(screen.getByText("Sin ejecución registrada")).toBeTruthy();
  });
});

describe("PAS03.01 preparation and execution", () => {
  it("shows the native controls of the actions", async () => {
    serve(page());
    await open();
    const importLabel = screen.getByText("Importar retorno");
    expect(importLabel.getAttribute("for")).toBe("id_archivo");
    const input = document.getElementById("id_archivo") as HTMLInputElement;
    expect(input.type).toBe("file");
    expect(input.name).toBe("archivo");
    expect(input.accept).toBe(".xlsx,.xls,.csv");
    expect(input.className).toBe("form-control");
    expect(input.required).toBe(true);
    expect(screen.getByRole("button", { name: "Confirmar importación" }).className).toBe("visually-hidden");
    expect(screen.getByRole("button", { name: /Exportar a SINTyS \(VIAS\)/ }).className).toBe("btn pas-primary-action");
  });

  it("exports through the POST, saves the returned file and reads the page again", async () => {
    serve(page(), page({ etapas: etapas({ completada: true, fecha: "2026-11-03T10:15:00-03:00", fecha_texto: "03/11/2026 10:15" }) }));
    const create = vi.fn(() => "blob:nomina");
    const revoke = vi.fn();
    Object.assign(URL, { createObjectURL: create, revokeObjectURL: revoke });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    let download = "";
    click.mockImplementation(function save(this: HTMLAnchorElement) { download = this.download; });
    webPost.mockResolvedValue({ status: 200, data: new ArrayBuffer(4), headers: { "content-disposition": 'attachment; filename="nomina_pas_sintys_vias_20261103_1015.xlsx"', "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" } });
    await open();
    fireEvent.click(screen.getByRole("button", { name: /Exportar a SINTyS/ }));
    await waitFor(() => expect(cruces()).toBe(2));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/pas/cruces/exportar-sintys/");
    expect(download).toBe("nomina_pas_sintys_vias_20261103_1015.xlsx");
    expect(create).toHaveBeenCalledTimes(1);
    expect(revoke).toHaveBeenCalledWith("blob:nomina");
    await waitFor(() => expect(document.querySelector(".pas-circuit-steps li")?.className).toBe("is-complete"));
    expect(toast()).toBeNull();
    click.mockRestore();
  });

  it("alerts with the native text when the export fails and lets the user try again", async () => {
    serve(page());
    const alert = vi.spyOn(window, "alert").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 500, data: new ArrayBuffer(0), headers: {} });
    await open();
    const button = screen.getByRole("button", { name: /Exportar a SINTyS/ }) as HTMLButtonElement;
    fireEvent.click(button);
    await waitFor(() => expect(alert).toHaveBeenCalledWith("No se pudo generar la nómina."));
    expect(button.disabled).toBe(false);
    expect(cruces()).toBe(1);
    alert.mockRestore();
  });

  it("reports an unconfirmed export (504) once and never retries", async () => {
    serve(page());
    const alert = vi.spyOn(window, "alert").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 504, data: new ArrayBuffer(0), headers: {} });
    await open();
    fireEvent.click(screen.getByRole("button", { name: /Exportar a SINTyS/ }));
    await waitFor(() => expect(alert).toHaveBeenCalledWith("No se pudo confirmar el resultado. Verificá el estado antes de reintentar."));
    expect(webPost).toHaveBeenCalledTimes(1);
    alert.mockRestore();
  });

  it("imports as soon as a file is chosen and shows the message as a toast after reading again", async () => {
    serve(page(), page({ etapas: [etapa(1, "Exportación a SINTyS (VIAS)"), etapa(2, "Importación retorno SINTyS", { completada: true, fecha: "2026-11-03T10:15:00-03:00", fecha_texto: "03/11/2026 10:15" }), ...etapas().slice(2)] }));
    webPost.mockResolvedValue({ status: 200, data: { message: "Retorno SINTyS importado correctamente." } });
    await open();
    const input = document.getElementById("id_archivo") as HTMLInputElement;
    const file = new File(["numero_cuil\n1"], "retorno.csv", { type: "text/csv" });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(cruces()).toBe(2));
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe("web/pas/cruces/importar-sintys/");
    expect((body as FormData).get("archivo")).toBe(file);
    const container = await waitFor(() => { const t = toast(); expect(t).toBeTruthy(); return t as Element; });
    expect(within(container as HTMLElement).getByText("Retorno SINTyS importado correctamente.")).toBeTruthy();
    expect(container.querySelector(".toast-success")).toBeTruthy();
    expect(document.body.lastElementChild).toBe(container);
  });

  it("shows the exact rejection as an error toast and changes no stage", async () => {
    serve(page());
    const message = "No se pudo importar el retorno: El retorno debe ser un archivo XLSX, XLS o CSV.";
    webPost.mockResolvedValue({ status: 400, data: { message, errors: { archivo: ["El retorno debe ser un archivo XLSX, XLS o CSV."] } } });
    await open();
    fireEvent.change(document.getElementById("id_archivo")!, { target: { files: [new File(["x"], "retorno.pdf")] } });
    const container = await waitFor(() => { const t = toast(); expect(t).toBeTruthy(); return t as Element; });
    expect(within(container as HTMLElement).getByText(message)).toBeTruthy();
    expect(container.querySelector(".toast-error")).toBeTruthy();
    await waitFor(() => expect(document.querySelectorAll(".pas-circuit-steps li.is-complete")).toHaveLength(0));
  });

  it("reports an unconfirmed import without retrying", async () => {
    serve(page());
    webPost.mockRejectedValue(new Error("timeout"));
    await open();
    fireEvent.change(document.getElementById("id_archivo")!, { target: { files: [new File(["x"], "retorno.csv")] } });
    const container = await waitFor(() => { const t = toast(); expect(t).toBeTruthy(); return t as Element; });
    expect(container.textContent).toContain("No se pudo confirmar el resultado. Verificá el estado antes de reintentar.");
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("asks before consulting RENAPER and posts nothing when declined", async () => {
    serve(page());
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    await open();
    fireEvent.click(screen.getByRole("button", { name: /Actualizar/ }));
    expect(confirm).toHaveBeenCalledWith("Se consultará todo el padrón PAS contra RENAPER. ¿Continuar?");
    expect(webPost).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: /Actualizar/ }) as HTMLButtonElement).disabled).toBe(false);
    confirm.mockRestore();
  });

  it("confirms, shows Actualizando, posts once and toasts the run message", async () => {
    serve(page());
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    let finish: (value: unknown) => void = () => undefined;
    webPost.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    await open();
    fireEvent.click(screen.getByRole("button", { name: /Actualizar/ }));
    const busy = await screen.findByRole("button", { name: /Actualizando/ }) as HTMLButtonElement;
    expect(busy.disabled).toBe(true);
    expect(busy.querySelector(".spinner-border.spinner-border-sm")).toBeTruthy();
    fireEvent.click(busy);
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/pas/cruces/actualizar-renaper/");
    finish({ status: 200, data: { run_id: 7, message: "Control mensual #7 registrado. Consulte el avance en esta pantalla." } });
    const container = await waitFor(() => { const t = toast(); expect(t).toBeTruthy(); return t as Element; });
    expect(container.textContent).toBe("Control mensual #7 registrado. Consulte el avance en esta pantalla.");
    expect(cruces()).toBe(2);
    await waitFor(() => expect(screen.getByRole("button", { name: /Actualizar/ })).toBeTruthy());
    confirm.mockRestore();
  });

  it("shows the access screen when an action is refused", async () => {
    serve(page());
    vi.spyOn(window, "confirm").mockReturnValue(true);
    webPost.mockResolvedValue({ status: 403, data: { detail: "No tiene permiso." } });
    await open();
    fireEvent.click(screen.getByRole("button", { name: /Actualizar/ }));
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Circuito administrativo mensual" })).toBeNull());
    expect(cruces()).toBe(1);
  });

  it("keeps the page in an error state for an invalid payload", async () => {
    serve({ can_change: true });
    window.history.replaceState({}, "", "/pas/cruces");
    render(<App />);
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});
