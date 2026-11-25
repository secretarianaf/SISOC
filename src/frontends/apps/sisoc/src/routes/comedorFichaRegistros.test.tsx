import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { ColaboradoresCard, InteraccionesCard, colaboradoresNavigation, colaboradoresValid, interaccionesChartConfig, interaccionesValid } from "./comedorFichaBloques";
import { CapacitacionesCard, capacitacionesDialogs, capacitacionesValid, pageNumbers } from "./comedorFichaCapacitaciones";
import { bloquesFixture } from "./comedorFichaFixtures";

const { webPost } = vi.hoisted(() => ({ webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: vi.fn(), post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const fixture = bloquesFixture();
let assign: ReturnType<typeof vi.spyOn>;
let confirm: ReturnType<typeof vi.spyOn>;
let alert: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.clearAllMocks();
  assign = vi.spyOn(colaboradoresNavigation, "assign").mockImplementation(() => undefined);
  confirm = vi.spyOn(colaboradoresNavigation, "confirm").mockReturnValue(true);
  alert = vi.spyOn(capacitacionesDialogs, "alert").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); assign.mockRestore(); confirm.mockRestore(); alert.mockRestore(); });

describe("Comedor ficha: colaboradores", () => {
  it("validates the payload", () => {
    expect(colaboradoresValid(fixture.colaboradores)).toBe(true);
    expect(colaboradoresValid({ ...fixture.colaboradores, agregar: "https://evil.example/" })).toBe(false);
    expect(colaboradoresValid({ ...fixture.colaboradores, items: [{ id: 1 }] })).toBe(false);
    expect(interaccionesValid(fixture.interacciones)).toBe(true);
    expect(interaccionesValid({ labels: ["a"], values: ["1"] })).toBe(false);
    expect(capacitacionesValid(null)).toBe(true);
    expect(capacitacionesValid({ items: [{ id: 1 }] })).toBe(false);
  });

  it("draws the native columns, cells, the count and the Agregar link", () => {
    render(<ColaboradoresCard data={fixture.colaboradores} />);
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Apellido y nombre", "DNI", "CUIL", "Sexo", "Género", "Teléfono", "Fecha alta", "Fecha baja", "Actividades", "Acciones"]);
    const fila = screen.getByText("Gomez, Ana").closest("tr")!;
    expect([...fila.querySelectorAll("td")].slice(0, 9).map((td) => td.textContent)).toEqual(["Gomez, Ana", "28999111", "27289991116", "Femenino", "Mujer", "11 5555", "26/03/2026", "-", "Compras,Cocina"]);
    expect(screen.getByRole("link", { name: "Agregar" }).getAttribute("href")).toBe("/comedores/7/colaboradores/crear/");
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/comedores/7/colaboradores/5/editar/");
    expect(screen.getByText("Se encontraron 2 resultados.")).toBeTruthy();
  });

  it("an inactive colaborador has no Editar and a disabled Eliminar; no permission draws no controls", () => {
    render(<ColaboradoresCard data={fixture.colaboradores} />);
    const baja = screen.getByText("Perez, Beto").closest("tr")!;
    expect(within(baja).queryByRole("link", { name: "Editar" })).toBeNull();
    expect((within(baja).getByRole("button", { name: "Eliminar" }) as HTMLButtonElement).disabled).toBe(true);
    cleanup();
    const sin = { ...fixture.colaboradores, agregar: null, items: fixture.colaboradores.items.map((c) => ({ ...c, editar: null, eliminar: null })) };
    render(<ColaboradoresCard data={sin} />);
    expect(screen.queryByRole("link", { name: "Agregar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Eliminar" })).toBeNull();
    cleanup();
    render(<ColaboradoresCard data={{ agregar: null, items: [], resultados: "Se encontraron 0 resultados." }} />);
    expect(screen.getByText("No hay colaboradores registrados para este espacio.").getAttribute("colspan")).toBe("10");
  });

  it("Eliminar asks the native confirmation, posts to the API and goes to the ficha", async () => {
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/comedores/7" } });
    render(<ColaboradoresCard data={fixture.colaboradores} />);
    const eliminar = within(screen.getByText("Gomez, Ana").closest("tr")!).getByRole("button", { name: "Eliminar" });

    confirm.mockReturnValueOnce(false);
    fireEvent.click(eliminar);
    expect(confirm).toHaveBeenCalledWith("¿Desea dar de baja a este colaborador?");
    expect(webPost).not.toHaveBeenCalled();

    fireEvent.click(eliminar);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/7"));
    expect(webPost.mock.calls[0][0]).toBe("web/comedores/colaboradores/comedor/7/5/eliminar/");
  });

  it("a refused or uncertain baja shows a toast and does not navigate", async () => {
    webPost.mockResolvedValueOnce({ status: 403, data: { detail: "Sin permiso." } });
    render(<ColaboradoresCard data={fixture.colaboradores} />);
    fireEvent.click(within(screen.getByText("Gomez, Ana").closest("tr")!).getByRole("button", { name: "Eliminar" }));
    expect(await screen.findByText("Sin permiso.")).toBeTruthy();
    webPost.mockRejectedValueOnce(new Error("network"));
    fireEvent.click(within(screen.getByText("Gomez, Ana").closest("tr")!).getByRole("button", { name: "Eliminar" }));
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
  });
});

describe("Comedor ficha: interacciones chart", () => {
  it("chart config follows the native script", () => {
    const config = interaccionesChartConfig(fixture.interacciones);
    expect(config.type).toBe("line");
    expect(config.data.labels).toEqual(["Mar 2026", "May 2026"]);
    expect(config.data.datasets[0]).toMatchObject({ data: [2, 1], borderColor: "#f2a000", tension: 0.35, fill: true });
    expect(config.options.scales.y.ticks.precision).toBe(0);
    expect(config.options.plugins.tooltip.callbacks.label({ parsed: { y: 2 } })).toBe(" 2");
  });

  it("is drawn once Chart.js is available and destroyed on unmount", () => {
    const destroy = vi.fn();
    const Chart = vi.fn(function Chart() { return { destroy }; });
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
    (window as unknown as { Chart: unknown }).Chart = Chart;
    const { unmount } = render(<InteraccionesCard data={fixture.interacciones} />);
    expect(screen.getByText("Historial de interacciones")).toBeTruthy();
    expect(document.querySelector(".w-100.comedor-chart-h220 > canvas#interaccionesChart")).toBeTruthy();
    expect(Chart).toHaveBeenCalledTimes(1);
    unmount();
    expect(destroy).toHaveBeenCalledTimes(1);
    delete (window as unknown as { Chart?: unknown }).Chart;
    getContext.mockRestore();
  });
});

const rowsOf = () => [...document.querySelectorAll("#capacitacionesTable tbody tr[data-cert-id]")].map((tr) => tr.getAttribute("data-cert-id"));

describe("Comedor ficha: capacitaciones", () => {
  it("native DataTables skin: first column ascending, info and pagination texts", () => {
    render(<CapacitacionesCard data={fixture.capacitaciones!} />);
    expect(rowsOf()).toEqual(["12", "13", "11"]);
    expect(document.querySelector("th.sorting_asc")!.textContent).toBe("Capacitación");
    expect(screen.getByText("Showing 1 to 3 of 3 entries")).toBeTruthy();
    expect([...document.querySelectorAll(".paginate_button")].map((li) => li.textContent)).toEqual(["Previous", "1", "Next"]);
    expect(document.querySelector("tr[data-cert-id='11'] .cert-estado .badge.bg-warning.text-dark")!.textContent).toBe("PRESENTADO");
    expect(screen.getByRole("link", { name: "Ver archivo" }).getAttribute("rel")).toBe("noreferrer");
  });

  it("buttons are enabled only for a presented certificate", () => {
    render(<CapacitacionesCard data={fixture.capacitaciones!} />);
    const state = (id: string) => [...document.querySelectorAll<HTMLButtonElement>(`tr[data-cert-id='${id}'] .btn`)].map((b) => b.disabled);
    expect(state("11")).toEqual([false, false]);
    expect(state("12")).toEqual([true, true]);
    expect(state("13")).toEqual([true, true]);
  });

  it("sorting by a header toggles direction; the search filters rows", () => {
    render(<CapacitacionesCard data={fixture.capacitaciones!} />);
    fireEvent.click(screen.getByRole("columnheader", { name: /Capacitación/ }));
    expect(rowsOf()).toEqual(["11", "13", "12"]);
    fireEvent.click(screen.getByRole("columnheader", { name: /^Estado/ }));
    expect(rowsOf()).toEqual(["11", "13", "12"]);
    fireEvent.change(document.querySelector("input[type=search]")!, { target: { value: "higiene" } });
    expect(rowsOf()).toEqual(["13"]);
    expect(screen.getByText("Showing 1 to 1 of 1 entries (filtered from 3 total entries)")).toBeTruthy();
    fireEvent.change(document.querySelector("input[type=search]")!, { target: { value: "zzz" } });
    expect(screen.getByText("No matching records found")).toBeTruthy();
    expect(screen.getByText("Showing 0 to 0 of 0 entries (filtered from 3 total entries)")).toBeTruthy();
  });

  it("Aceptar posts the state and updates the row in place", async () => {
    webPost.mockResolvedValue({ status: 200, data: { success: true, item: { estado: "aceptado", observacion: null } } });
    render(<CapacitacionesCard data={fixture.capacitaciones!} />);
    fireEvent.click(document.querySelector("tr[data-cert-id='11'] .cert-accept-btn")!);
    await waitFor(() => expect(document.querySelector("tr[data-cert-id='11'] .cert-estado")!.textContent).toBe("ACEPTADO"));
    expect(webPost.mock.calls[0][0]).toBe("web/comedores/comedores/7/capacitaciones/11/estado/");
    expect(webPost.mock.calls[0][1].toString()).toBe("estado=aceptado");
    expect(document.querySelector("tr[data-cert-id='11'] .cert-observacion")!.textContent).toBe("-");
    expect((document.querySelector("tr[data-cert-id='11'] .cert-accept-btn") as HTMLButtonElement).disabled).toBe(true);
  });

  it("Rechazar opens the editor row, needs an observation, and a successful reject closes it", async () => {
    webPost.mockResolvedValue({ status: 200, data: { success: true, item: { estado: "rechazado", observacion: "Ilegible" } } });
    render(<CapacitacionesCard data={fixture.capacitaciones!} />);
    fireEvent.click(document.querySelector("tr[data-cert-id='11'] .cert-reject-btn")!);
    expect(screen.getByPlaceholderText("Ingrese una observacion")).toBeTruthy();
    fireEvent.click(document.querySelector("tr[data-cert-id='11'] .cert-reject-btn")!);
    expect(document.querySelector(".cert-reject-editor")).toBeNull();
    fireEvent.click(document.querySelector("tr[data-cert-id='11'] .cert-reject-btn")!);
    fireEvent.click(document.querySelector(".cert-reject-confirm-btn")!);
    expect(alert).toHaveBeenCalledWith("Debe ingresar una observación para rechazar.");
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.change(screen.getByPlaceholderText("Ingrese una observacion"), { target: { value: "  Ilegible  " } });
    fireEvent.click(document.querySelector(".cert-reject-confirm-btn")!);
    await waitFor(() => expect(document.querySelector("tr[data-cert-id='11'] .cert-observacion")!.textContent).toBe("Ilegible"));
    expect(webPost.mock.calls[0][1].toString()).toBe("estado=rechazado&observacion=Ilegible");
    expect(document.querySelector(".cert-reject-editor")).toBeNull();
    expect(document.querySelector("tr[data-cert-id='11'] .cert-estado")!.textContent).toBe("RECHAZADO");
  });

  it("Cancelar closes the editor; a refused review alerts with the API error or the native fallback", async () => {
    webPost.mockResolvedValueOnce({ status: 400, data: { success: false, error: ["El certificado ya fue revisado y no puede cambiar de estado."] } });
    render(<CapacitacionesCard data={fixture.capacitaciones!} />);
    fireEvent.click(document.querySelector("tr[data-cert-id='11'] .cert-reject-btn")!);
    fireEvent.click(document.querySelector(".cert-reject-cancel-btn")!);
    expect(document.querySelector(".cert-reject-editor")).toBeNull();
    fireEvent.click(document.querySelector("tr[data-cert-id='11'] .cert-accept-btn")!);
    // The native script only reads a string error: a list falls back to its own text.
    await waitFor(() => expect(alert).toHaveBeenCalledWith("No se pudo actualizar el estado."));
    webPost.mockResolvedValueOnce({ status: 400, data: { success: false, error: "Estado inválido." } });
    fireEvent.click(document.querySelector("tr[data-cert-id='11'] .cert-accept-btn")!);
    await waitFor(() => expect(alert).toHaveBeenCalledWith("Estado inválido."));
    expect(document.querySelector("tr[data-cert-id='11'] .cert-estado")!.textContent).toBe("PRESENTADO");
  });

  it("DataTables page numbers", () => {
    expect(pageNumbers(0, 1)).toEqual([0]);
    expect(pageNumbers(0, 10)).toEqual([0, 1, 2, 3, 4, "ellipsis", 9]);
    expect(pageNumbers(9, 10)).toEqual([0, "ellipsis", 5, 6, 7, 8, 9]);
    expect(pageNumbers(5, 12)).toEqual([0, "ellipsis", 4, 5, 6, "ellipsis", 11]);
  });

  it("pagination moves by the page length", () => {
    const items = Array.from({ length: 12 }, (_, i) => ({ id: i + 1, capacitacion: `Cap ${String(i + 1).padStart(2, "0")}`, estado: "sin_presentar", archivo: null, observacion: "-", revisar: `/api/x/${i}/` }));
    render(<CapacitacionesCard data={{ items }} />);
    expect(rowsOf()).toHaveLength(10);
    expect(screen.getByText("Showing 1 to 10 of 12 entries")).toBeTruthy();
    fireEvent.click(screen.getByRole("link", { name: "Next" }));
    expect(rowsOf()).toEqual(["11", "12"]);
    expect(screen.getByText("Showing 11 to 12 of 12 entries")).toBeTruthy();
    fireEvent.change(document.querySelector("select")!, { target: { value: "25" } });
    expect(rowsOf()).toHaveLength(12);
  });
});
