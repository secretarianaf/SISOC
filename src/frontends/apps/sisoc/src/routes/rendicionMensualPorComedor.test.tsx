import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { rendicionMensualPorComedorRoute } from "./rendicionMensualPorComedor";
import { readyContext } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("@sisoc/api")>(),
  crearCliente: vi.fn(() => ({ get: webGet })),
}));

const PREFIX = "/rendicioncuentasmensual/rendicioncuentasmensual";
const LIST = `${PREFIX}/9/`;
const API = "web/comedores/rendicioncuentasmensual/por-comedor/9/?page=last";
const payload = {
  comedor: "Comedor Centro",
  new_url: `${PREFIX}/nuevo/9/`,
  back_url: "/comedores/9/acompanamiento/",
  rows: [
    {
      id: 12, mes: 11, anio: 2026, observaciones: "<Control pendiente>",
      detail_url: `${PREFIX}/detalle/12/`, edit_url: `${PREFIX}/editar/12/`,
      delete_url: `${PREFIX}/eliminar/12/`,
    },
  ],
};

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(
    url === "web/session/" ? { data: readyContext, status: 200 } : { data, status },
  ));
  const params = rendicionMensualPorComedorRoute.match(LIST)!;
  return render(rendicionMensualPorComedorRoute.render(params));
}

afterEach(() => {
  cleanup();
  webGet.mockReset();
  window.history.replaceState({}, "", "/");
});

describe("Canonical monthly seguimiento per comedor", () => {
  it("owns only the exact native list path", () => {
    expect(rendicionMensualPorComedorRoute.match(LIST)).toEqual({ comedorId: "9" });
    for (const other of [`${PREFIX}/listado/`, `${PREFIX}/detalle/9/`, "/rendicioncuentasmensual/9/", `${PREFIX}/9`]) {
      expect(rendicionMensualPorComedorRoute.match(other)).toBeNull();
    }
  });

  it("keeps the selected URL and presents the native navigation and actions", async () => {
    window.history.replaceState({}, "", `${LIST}?page=last`);
    serve(payload);

    await screen.findByRole("heading", { name: "Seguimiento mensual - Comedor Centro" });
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    expect(screen.getByRole("link", { name: "Volver al acompañamiento" }).getAttribute("href")).toBe(payload.back_url);
    expect(screen.getByRole("link", { name: "Nuevo seguimiento mensual" }).getAttribute("href")).toBe(payload.new_url);
    const rows = within(screen.getByRole("table")).getAllByRole("row");
    expect(within(rows[1]).getAllByRole("cell").slice(0, 4).map((cell) => cell.textContent)).toEqual(["1", "11", "2026", "<Control pendiente>"]);
    for (const [name, href] of [
      ["Ver Detalle", payload.rows[0].detail_url],
      ["Editar", payload.rows[0].edit_url],
      ["Dar de baja", payload.rows[0].delete_url],
    ]) {
      expect(within(rows[1]).getByRole("link", { name }).getAttribute("href")).toBe(href);
    }
  });

  it("does not offer actions the native destination would deny", async () => {
    serve({ ...payload, new_url: null, rows: [{ ...payload.rows[0], edit_url: null, delete_url: null }] });
    await screen.findByRole("link", { name: "Ver Detalle" });
    for (const name of ["Nuevo seguimiento mensual", "Editar", "Dar de baja"]) {
      expect(screen.queryByRole("link", { name })).toBeNull();
    }
  });

  it("describes an empty list and keeps its responsive table keyboard-reachable", async () => {
    serve({ ...payload, rows: [] });
    await screen.findByText("No hay seguimientos mensuales.");
    const tableRegion = screen.getByRole("region", { name: "Seguimientos mensuales" });
    tableRegion.focus();
    expect(document.activeElement).toBe(tableRegion);
  });
});
