import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { TableroScreen } from "./TableroScreen";

const json = (body: unknown, ok = true, status = 200) => ({ ok, status, json: async () => body });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

const zero = { leg: 0, pend: 0, apr: 0, rech: 0, sub: 0, match: 0, nomatch: 0, sincruce: 0, tit: 0, susp: 0, fuera: 0 };
const datos = {
  provincias: [
    { p: "Salta", cupo: 10, exp: 2, expProc: 1, per: 6, ...zero, leg: 6, pend: 1, apr: 3, rech: 1, sub: 1, match: 2, nomatch: 1, tit: 1, susp: 1 },
    { p: "Jujuy", cupo: 0, exp: 1, expProc: 1, per: 1, ...zero, leg: 1, pend: 1 },
  ],
  piramide: { Salta: { F: [0, 1, 0, 0, 0, 0, 0], M: [0, 0, 0, 0, 0, 0, 0] } },
  rechazo: { Salta: { "Tiene obra social": 1, "Sin motivo registrado": 1 } },
  subsanacion: { Salta: { Documentación: 1, Otros: 1 } },
  errores: { Jujuy: { "Falta documento": 2 } },
  expedientes: [
    { id: 5, n: "EX-<b>2026</b>", est: "CRUCE_FINALIZADO", d: 3, p: "Salta", ...zero, leg: 5, pend: 0, apr: 3, rech: 1, sub: 1, match: 2, nomatch: 1, tit: 1, susp: 1 },
    { id: 6, n: "", est: "EN_ESPERA", d: 1, p: "Salta", ...zero, leg: 1, pend: 1 },
    { id: 7, n: "", est: "EN_ESPERA", d: 1, p: "Jujuy", ...zero, leg: 1, pend: 1 },
  ],
  tramos: ["0-5", "6-12", "13-17", "18-29", "30-44", "45-64", "65+"],
};

function mount(urlExpediente: string) {
  window.history.pushState({}, "", "/celiaquia/tablero/");
  const fetchMock = vi.fn().mockResolvedValue(json({ version: 1, datos, url_expediente: urlExpediente, messages: [] }));
  vi.stubGlobal("fetch", fetchMock);
  render(<TableroScreen />);
  return fetchMock;
}

it("renders the aggregated dashboard from the canonical projection only", async () => {
  const fetchMock = mount("");
  expect(await screen.findByText("Datos en vivo")).toBeInTheDocument();
  expect(screen.getByRole("heading", { level: 1, name: "Celiaquía Seguimiento" })).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock.mock.calls[0][0]).toBe("/celiaquia/tablero/");
  expect(fetchMock.mock.calls[0][1].headers).toEqual({ Accept: "application/json" });
  expect(document.getElementById("cel-chip-alcance")).toHaveTextContent(/^Todas las provincias$/);
  expect(screen.getByText("7 personas cargadas")).toBeInTheDocument();
  const kpis = screen.getByRole("region", { name: "Cifras principales" });
  expect(within(kpis).getByText("Personas cargadas")).toBeInTheDocument();
  // Free text from the database is rendered as text, never as HTML.
  expect(screen.getByText("cargado como «EX-<b>2026</b>»")).toBeInTheDocument();
});

it("filters by province over the aggregated data like the native page", async () => {
  mount("");
  fireEvent.change(await screen.findByLabelText("Provincia"), { target: { value: "Jujuy" } });
  expect(document.getElementById("cel-chip-alcance")).toHaveTextContent(/^Jujuy$/);
  expect(screen.getByText("1 personas cargadas")).toBeInTheDocument();
  const expediente = screen.getByLabelText("Expediente");
  expect(within(expediente).getAllByRole("option").map((option) => option.textContent)).toEqual(["Todos (1)", "#7 · Jujuy · 1 benef."]);
});

it("toggles a chart section to its data table", async () => {
  mount("");
  const section = (await screen.findByRole("heading", { name: /Cupo usado por provincia/ })).closest("section")!;
  fireEvent.click(within(section).getByRole("button", { name: "Tabla" }));
  const table = within(section).getByRole("table");
  expect(within(table).getAllByRole("columnheader").map((cell) => cell.textContent)).toEqual(["Provincia", "Cupo asignado", "Titulares", "Disponible", "% usado"]);
  expect(within(table).getAllByRole("row")[1]).toHaveTextContent("Salta101910,0 %");
  expect(within(section).getByRole("button", { name: "Gráfico" })).toBeInTheDocument();
});

it("links to the expediente only when the projection grants the link", async () => {
  mount("");
  fireEvent.change(await screen.findByLabelText("Expediente"), { target: { value: "5" } });
  expect(screen.getByText(/Expediente #5/)).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Abrir en SISOC" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Quitar filtro" }));
  expect(screen.queryByText(/Expediente #5/)).not.toBeInTheDocument();
});

it("opens the selected expediente on its canonical URL when allowed", async () => {
  mount("/celiaquia/expedientes/0/");
  fireEvent.click(await screen.findByRole("button", { name: "Filtrar por el expediente #5" }));
  expect(screen.getByRole("link", { name: "Abrir en SISOC" })).toHaveAttribute("href", "/celiaquia/expedientes/5/");
  expect(document.getElementById("cel-chip-alcance")).toHaveTextContent(/^Todas las provincias · expediente #5$/);
});

it("reports a denied projection", async () => {
  window.history.pushState({}, "", "/celiaquia/tablero/");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({}, false, 403)));
  render(<TableroScreen />);
  expect(await screen.findByRole("alert")).toHaveTextContent("No tiene permiso para ver esta pantalla.");
});
