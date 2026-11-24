import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import InsumosCategoriasList from "./InsumosCategoriasList";

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("@sisoc/api", () => ({ crearCliente: vi.fn(() => ({ get })), SinPermiso: class SinPermiso extends Error {} }));
const page = { count: 1, page: 1, page_size: 20, pages: 1,
  capabilities: { can_add: true, can_change: false, can_delete: true },
  results: [{ id: 4, nombre: "Manuales", programa: "Programa A", orden: 2, activo: true }],
};
beforeEach(() => { vi.resetAllMocks(); window.history.replaceState({}, "", "/v2/sisoc/insumos/categorias/"); });
afterEach(cleanup);

it("uses category-specific action capabilities and local complete-circuit links", async () => {
  get.mockResolvedValue({ data: page });
  render(<InsumosCategoriasList />);
  await screen.findByText("Manuales");
  expect(screen.getByText("Programa A")).toBeDefined();
  expect(screen.getByRole("link", { name: /Agregar categoría/ }).getAttribute("href")).toBe("/v2/sisoc/insumos/categorias/crear");
  expect(screen.getByRole("link", { name: /Eliminar/ }).getAttribute("href")).toBe("/v2/sisoc/insumos/categorias/4/eliminar");
  expect(screen.queryByRole("link", { name: /Editar/ })).toBeNull();
  expect(screen.getByText("Se encontraron 1 resultados")).toBeDefined();
});

it("renders the legacy empty state and forwards the current pagination query", async () => {
  window.history.replaceState({}, "", "/v2/sisoc/insumos/categorias/?page=2");
  get.mockResolvedValue({ data: { ...page, count: 0, results: [] } });
  render(<InsumosCategoriasList />);
  await screen.findByText("No hay categorías");
  expect(screen.getByText("Todavía no se crearon categorías de insumos.")).toBeDefined();
  expect(get).toHaveBeenCalledWith("web/insumos/categorias/?page=2", expect.objectContaining({ signal: expect.any(AbortSignal) }));
});
