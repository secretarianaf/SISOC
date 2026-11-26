import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { PagoDetalleScreen, PagosScreen } from "./PagosScreens";

const json = (body: unknown, ok = true, status = 200) => ({ ok, status, json: async () => body });

beforeEach(() => { document.cookie = "csrftoken=synthetic-token; path=/"; });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

const list = {
  version: 1,
  provincia: { id: 7, nombre: "Provincia Sintética" },
  rows: [
    { id: 11, periodo: "2026-02", estado: "BORRADOR", candidatos: 1, validados: 0, excluidos: 0, creado: "2026-02-03", url: "/celiaquia/pagos/expediente/11/" },
    { id: 10, periodo: "2026-01", estado: "PROCESADO", candidatos: 5, validados: 3, excluidos: 2, creado: "2026-01-05", url: "/celiaquia/pagos/expediente/10/" },
  ],
  urls: { volver: "/celiaquia/cupos/provincia/7/", crear: "/celiaquia/pagos/provincia/7/crear/" },
  messages: [{ level: "error", text: "No se pudo crear el expediente de pago." }],
};

const detail = (archivo: string | null) => ({
  version: 1,
  pago: { id: 10, provincia: { id: 7, nombre: "Provincia Sintética" }, periodo: "2026-01", estado: "PROCESADO", candidatos: 5, validados: 3, excluidos: 2 },
  urls: { volver: "/celiaquia/cupos/provincia/7/", archivo_envio: archivo, exportar_nomina: "/celiaquia/pagos/expediente/10/exportar-nomina-actual/" },
  upload: { action: "/celiaquia/pagos/expediente/10/", field: "archivo", label: "Respuesta de Sintys (XLSX/CSV)", required: true },
  nomina: [{ documento: "20111222", nombre: "Nombre", apellido: "Apellido", estado: "VALIDADO", observacion: "ok" }],
  messages: [{ level: "success", text: "Respuesta procesada. Validados: 3 — Excluidos: 2." }],
});

function mount(path: string, body: unknown, ok = true, status = 200) {
  window.history.pushState({}, "", path);
  const fetchMock = vi.fn().mockResolvedValue(json(body, ok, status));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function expectOnlyCanonicalProjection(fetchMock: ReturnType<typeof vi.fn>, path: string) {
  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe(path);
  expect(init.headers).toEqual({ Accept: "application/json" });
  expect(String(url)).not.toContain("/api/");
}

it("lists the province payment files from the canonical projection", async () => {
  const fetchMock = mount("/celiaquia/pagos/provincia/7/", list);
  render(<PagosScreen />);

  expect(await screen.findByRole("heading", { name: "Expedientes de pago — Provincia Sintética" })).toBeInTheDocument();
  expectOnlyCanonicalProjection(fetchMock, "/celiaquia/pagos/provincia/7/");
  expect(screen.getByRole("alert")).toHaveTextContent("No se pudo crear el expediente de pago.");
  expect(screen.getByRole("link", { name: "← Volver" })).toHaveAttribute("href", "/celiaquia/cupos/provincia/7/");

  const table = screen.getByRole("table");
  const rows = within(table).getAllByRole("row");
  expect(within(rows[2]).getAllByRole("cell").map((cell) => cell.textContent)).toEqual(["10", "2026-01", "PROCESADO", "5", "3", "2", "2026-01-05", "Ver"]);
  expect(within(rows[2]).getByRole("link", { name: "Ver detalle del expediente 10" })).toHaveAttribute("href", "/celiaquia/pagos/expediente/10/");

  const create = screen.getByRole("button", { name: "Generar expediente de pago" }).closest("form")!;
  expect(create).toHaveAttribute("method", "post");
  expect(create).toHaveAttribute("action", "/celiaquia/pagos/provincia/7/crear/");
  expect(create.querySelector<HTMLInputElement>('input[name="csrfmiddlewaretoken"]')!.value).toBe("synthetic-token");
});

it("sorts the payment list by a column like the native table", async () => {
  mount("/celiaquia/pagos/provincia/7/", list);
  render(<PagosScreen />);
  fireEvent.click(await screen.findByRole("button", { name: "ID" }));
  const firstId = () => within(screen.getAllByRole("row")[1]).getAllByRole("cell")[0].textContent;
  expect(firstId()).toBe("10");
  expect(screen.getByRole("columnheader", { name: "ID" })).toHaveAttribute("aria-sort", "ascending");
  fireEvent.click(screen.getByRole("button", { name: "ID" }));
  expect(firstId()).toBe("11");
});

it("shows the native empty state", async () => {
  mount("/celiaquia/pagos/provincia/7/", { ...list, rows: [], messages: [] });
  render(<PagosScreen />);
  expect(await screen.findByText("No hay expedientes de pago.")).toBeInTheDocument();
});

it("reports a denied projection", async () => {
  mount("/celiaquia/pagos/provincia/7/", {}, false, 403);
  render(<PagosScreen />);
  expect(await screen.findByRole("alert")).toHaveTextContent("No tiene permiso para ver esta pantalla.");
});

it("shows payment detail, downloads and the native multipart upload form", async () => {
  const fetchMock = mount("/celiaquia/pagos/expediente/10/", detail("/celiaquia/pagos/expediente/10/exportar/"));
  render(<PagoDetalleScreen />);

  expect(await screen.findByRole("heading", { name: "Pago — Provincia Sintética — 2026-01" })).toBeInTheDocument();
  expectOnlyCanonicalProjection(fetchMock, "/celiaquia/pagos/expediente/10/");
  expect(screen.getByRole("status")).toHaveTextContent("Respuesta procesada. Validados: 3 — Excluidos: 2.");
  const term = (label: string) => screen.getAllByText(label).find((node) => node.tagName === "DT")!;
  expect(term("Estado").nextElementSibling).toHaveTextContent("PROCESADO");
  expect(term("Excluidos").nextElementSibling).toHaveTextContent("2");
  expect(screen.getByRole("link", { name: "Descargar Excel" })).toHaveAttribute("href", "/celiaquia/pagos/expediente/10/exportar/");
  expect(screen.getByRole("link", { name: "Exportar nómina" })).toHaveAttribute("href", "/celiaquia/pagos/expediente/10/exportar-nomina-actual/");

  const input = screen.getByLabelText("Respuesta de Sintys (XLSX/CSV)");
  expect(input).toHaveAttribute("type", "file");
  expect(input).toHaveAttribute("name", "archivo");
  expect(input).toBeRequired();
  const form = input.closest("form")!;
  expect(form).toHaveAttribute("method", "post");
  expect(form).toHaveAttribute("enctype", "multipart/form-data");
  expect(form).toHaveAttribute("action", "/celiaquia/pagos/expediente/10/");
  expect(form.querySelector<HTMLInputElement>('input[name="csrfmiddlewaretoken"]')!.value).toBe("synthetic-token");
  expect(screen.getByRole("button", { name: "Procesar respuesta" })).toBeEnabled();

  const nomina = screen.getByRole("table", { name: "Nómina validada" });
  expect(within(nomina).getAllByRole("cell").map((cell) => cell.textContent)).toEqual(["20111222", "Nombre", "Apellido", "VALIDADO", "ok"]);
});

it("shows the missing export file like the native page", async () => {
  mount("/celiaquia/pagos/expediente/10/", { ...detail(null), nomina: [], messages: [] });
  render(<PagoDetalleScreen />);
  expect(await screen.findByText("No generado")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Descargar Excel" })).not.toBeInTheDocument();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});

it("rejects an incompatible projection version", async () => {
  mount("/celiaquia/pagos/expediente/10/", { ...detail(null), version: 2 });
  render(<PagoDetalleScreen />);
  expect(await screen.findByRole("alert")).toHaveTextContent("La pantalla no es compatible con esta versión.");
});
