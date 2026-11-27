import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { CupoProvinciaScreen, CuposScreen } from "./CuposScreens";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

const json = (body: unknown, ok = true, status = 200) => ({ ok, status, json: async () => body });

const dashboard = {
  version: 1,
  urls: { expedientes: "/celiaquia/expedientes/" },
  messages: [],
  rows: [
    { provincia: { id: 4, nombre: "Chaco" }, total_asignado: 10, usados: 3, disponibles: 7, fuera: 2, url: "/celiaquia/cupos/provincia/4/" },
    { provincia: { id: 9, nombre: "Salta" }, total_asignado: null, usados: null, disponibles: null, fuera: null, url: "/celiaquia/cupos/provincia/9/" },
  ],
};

const person = (id: number, documento: string, activo: boolean) => ({
  id, documento, nombre: `Nombre${id}`, apellido: `Apellido${id}`, expediente: "",
  revision_tecnico: "APROBADO", resultado_sintys: "MATCH", estado_cupo: activo ? "DENTRO" : "FUERA", es_titular_activo: activo,
});

const province = {
  version: 1,
  provincia: { id: 4, nombre: "Chaco" },
  metrics: { total_asignado: 10, usados: 3, disponibles: 7, fuera: 2 },
  ocupados: [{ ...person(1, "20111", true), actions: [
    { kind: "suspender", url: "/celiaquia/cupos/provincia/4/legajo/1/suspender/" },
    { kind: "baja", url: "/celiaquia/cupos/provincia/4/legajo/1/baja/" },
  ] }],
  suspendidos: [{ ...person(2, "20222", false), estado_cupo: "DENTRO", actions: [
    { kind: "reactivar", url: "/celiaquia/cupo/4/legajo/2/reactivar/" },
    { kind: "baja", url: "/celiaquia/cupos/provincia/4/legajo/2/baja/" },
  ] }],
  lista_espera: [{ ...person(3, "20333", false), actions: [] }],
  movimientos: [{ id: 5, fecha: "24/11/2026 10:30", tipo: "SUSPENDIDO", delta: 0, motivo: "Synthetic", usuario: "operador", expediente: "", legajo: person(2, "20222", false) }],
  forms: {
    baja: { name: "motivo", label: "Motivo de la baja", required: true },
    suspender: { name: "motivo", label: "Motivo de la suspensión", required: true },
  },
  urls: {
    dashboard: "/celiaquia/cupos/",
    config: "/celiaquia/cupos/provincia/4/",
    pagos: "/celiaquia/pagos/provincia/4/",
    crear_pago: "/celiaquia/pagos/provincia/4/crear/",
  },
  csrf_token: "synthetic-token",
  messages: [{ level: "error", text: "No se pudo crear el expediente de pago." }],
};

it("renders the native dashboard rows from the canonical projection only", async () => {
  window.history.replaceState({}, "", "/celiaquia/cupos/");
  const fetcher = vi.fn().mockResolvedValue(json(dashboard));
  vi.stubGlobal("fetch", fetcher);
  render(<CuposScreen />);
  expect(await screen.findByRole("heading", { name: "Cupos por provincia" })).toBeTruthy();
  const rows = screen.getAllByRole("row");
  expect(within(rows[1]).getByText("Chaco")).toBeTruthy();
  expect(within(rows[2]).getByText("Sin configurar")).toBeTruthy();
  expect(within(rows[2]).getAllByText("—")).toHaveLength(3);
  expect(within(rows[1]).getByRole("link", { name: "Ver cupo de Chaco" }).getAttribute("href")).toBe("/celiaquia/cupos/provincia/4/");
  expect(screen.getByRole("link", { name: "Expedientes" }).getAttribute("href")).toBe("/celiaquia/expedientes/");
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(fetcher.mock.calls[0][0]).toBe("/celiaquia/cupos/");
  expect(fetcher.mock.calls[0][1].headers.Accept).toBe("application/json");
});

it("renders province data, Django messages and only the projected actions", async () => {
  window.history.replaceState({}, "", "/celiaquia/cupos/provincia/4/");
  const fetcher = vi.fn().mockResolvedValue(json(province));
  vi.stubGlobal("fetch", fetcher);
  render(<CupoProvinciaScreen />);
  expect(await screen.findByRole("heading", { level: 1, name: "Chaco" })).toBeTruthy();
  expect(screen.getByText("No se pudo crear el expediente de pago.")).toBeTruthy();
  expect(screen.getByText("Total asignado")).toBeTruthy();
  const ocupados = screen.getByRole("table", { name: "Cupos ocupados (titulares activos)" });
  expect(within(ocupados).getByRole("button", { name: "Suspender 20111" })).toBeTruthy();
  expect(within(ocupados).getByRole("button", { name: "Baja 20111" })).toBeTruthy();
  const suspendidos = screen.getByRole("table", { name: "Suspendidos (cupo ocupado, no activos)" });
  expect(within(suspendidos).getByRole("button", { name: "Reactivar 20222" })).toBeTruthy();
  const espera = screen.getByRole("table", { name: "Lista de espera (Fuera de cupo)" });
  expect(within(espera).getByText("20333")).toBeTruthy();
  expect(within(espera).queryAllByRole("button")).toHaveLength(0);
  expect(screen.getByRole("link", { name: "Ver expedientes de pago" }).getAttribute("href")).toBe("/celiaquia/pagos/provincia/4/");
  const generate = screen.getByRole("button", { name: "Generar expediente de pago" }).closest("form")!;
  expect(generate.getAttribute("action")).toBe("/celiaquia/pagos/provincia/4/crear/");
  expect(generate.getAttribute("method")).toBe("post");
  expect((generate.querySelector("input[name=csrfmiddlewaretoken]") as HTMLInputElement).value).toBe("synthetic-token");
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(String(fetcher.mock.calls[0][0])).not.toContain("/api/");
});

it("shows the unconfigured state when no metrics are projected", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ ...province, metrics: null, messages: [] })));
  render(<CupoProvinciaScreen />);
  expect(await screen.findByText("La provincia no tiene cupo configurado.")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Configurar ahora" })).toBeTruthy();
  expect(screen.queryByText("Total asignado")).toBeNull();
});

it("suspends through the native endpoint with the reason and CSRF header", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  document.cookie = "csrftoken=cookie-token";
  const fetcher = vi.fn()
    .mockResolvedValueOnce(json(province))
    .mockResolvedValueOnce(json({ success: true, message: "Suspensión registrada." }));
  vi.stubGlobal("fetch", fetcher);
  render(<CupoProvinciaScreen />);
  fireEvent.click(await screen.findByRole("button", { name: "Suspender 20111" }));
  const dialog = screen.getByRole("dialog", { name: "Suspender titular" });
  fireEvent.change(within(dialog).getByLabelText("Motivo de la suspensión"), { target: { value: "Motivo sintético" } });
  fireEvent.click(within(dialog).getByRole("button", { name: "Confirmar" }));
  expect(await screen.findByText("Suspensión registrada y cupo actualizado.")).toBeTruthy();
  const [url, init] = fetcher.mock.calls[1];
  expect(url).toBe("/celiaquia/cupos/provincia/4/legajo/1/suspender/");
  expect(init.method).toBe("POST");
  expect(init.headers["X-CSRFToken"]).toBe("cookie-token");
  expect((init.body as URLSearchParams).get("motivo")).toBe("Motivo sintético");
  vi.useRealTimers();
});

it("shows the native rejection message and keeps the dialog open", async () => {
  const fetcher = vi.fn()
    .mockResolvedValueOnce(json(province))
    .mockResolvedValueOnce(json({ success: false, message: "No se pudo validar el legajo." }, false, 400));
  vi.stubGlobal("fetch", fetcher);
  render(<CupoProvinciaScreen />);
  fireEvent.click(await screen.findByRole("button", { name: "Baja 20111" }));
  const dialog = screen.getByRole("dialog", { name: "Dar de baja titular" });
  fireEvent.change(within(dialog).getByLabelText("Motivo de la baja"), { target: { value: "x" } });
  fireEvent.click(within(dialog).getByRole("button", { name: "Confirmar" }));
  expect(await screen.findByText("No se pudo validar el legajo.")).toBeTruthy();
  expect(screen.getByRole("dialog", { name: "Dar de baja titular" })).toBeTruthy();
});

it("validates the cupo total before calling the native configuration", async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(json(province));
  vi.stubGlobal("fetch", fetcher);
  render(<CupoProvinciaScreen />);
  fireEvent.click(await screen.findByRole("button", { name: "Configurar cupo" }));
  const dialog = screen.getByRole("dialog", { name: "Configurar cupo para Chaco" });
  const input = within(dialog).getByLabelText("Total asignado") as HTMLInputElement;
  expect(input.value).toBe("10");
  fireEvent.change(input, { target: { value: "-1" } });
  fireEvent.submit(input.closest("form")!);
  expect(await screen.findByText("Ingresá un valor de cupo válido (entero ≥ 0).")).toBeTruthy();
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it("filters a table by CUIL, name or expediente and closes dialogs with Escape", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(province)));
  render(<CupoProvinciaScreen />);
  const filter = await screen.findByLabelText("Filtrar cupos ocupados");
  fireEvent.change(filter, { target: { value: "nada" } });
  expect(within(screen.getByRole("table", { name: "Cupos ocupados (titulares activos)" })).queryByText("20111")).toBeNull();
  fireEvent.change(filter, { target: { value: "nombre1" } });
  expect(within(screen.getByRole("table", { name: "Cupos ocupados (titulares activos)" })).getByText("20111")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Historico" }));
  const dialog = screen.getByRole("dialog", { name: "Histórico de movimientos — Chaco" });
  expect(within(dialog).getByText("SUSPENDIDO")).toBeTruthy();
  fireEvent.keyDown(dialog, { key: "Escape" });
  expect(screen.queryByRole("dialog")).toBeNull();
});
