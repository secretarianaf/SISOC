import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "@sisoc/ui";

/**
 * Expedientes de pago de una provincia.
 *
 * El bug: la ruta llevaba el **nombre** de la provincia y la pantalla hacía
 * `Number(nombre)`, que da NaN. El listado salía vacío y "Generar" mandaba
 * `provincia_id: null`. La ruta lleva el id y el back filtra por él.
 */

const listar = vi.fn().mockResolvedValue({
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 3,
      provincia: "Formosa",
      provincia_id: 9,
      periodo: "2026-10",
      estado: "BORRADOR",
      total_candidatos: 10,
      total_validados: 0,
      total_excluidos: 0,
      creado_en: "2026-10-01T10:00:00-03:00",
      modificado_en: "2026-10-01T10:00:00-03:00",
    },
  ],
});
const crear = vi.fn().mockResolvedValue({});
vi.mock("../api", () => ({ api: { pagos: { listar, crear } } }));

const { PagoListPage } = await import("../pages/PagoListPage");

const montar = () =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ThemeProvider>
        <MemoryRouter initialEntries={["/pagos/9"]}>
          <Routes>
            <Route path="pagos/:provinciaId" element={<PagoListPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  );

describe("PagoListPage", () => {
  it("pide al back los pagos de la provincia de la ruta", async () => {
    montar();

    expect(await screen.findByText("2026-10")).toBeInTheDocument();
    expect(listar).toHaveBeenCalledWith({ provincia: 9, page: 1 });
  });

  it("genera el expediente de pago con el id de la provincia", async () => {
    montar();
    await screen.findByText("2026-10");

    fireEvent.click(
      screen.getByRole("button", { name: /Generar expediente de pago/ }),
    );

    await waitFor(() => expect(crear).toHaveBeenCalledWith(9));
  });
});
