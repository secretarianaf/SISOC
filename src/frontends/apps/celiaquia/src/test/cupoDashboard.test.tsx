import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "@sisoc/ui";
import type { FilaCupoProvincia } from "@sisoc/api";

/**
 * Asignar cupo a una provincia.
 *
 * El bug: `cupos/` solo devuelve los `ProvinciaCupo` que existen, así que una
 * provincia sin cupo no aparecía y no había forma de asignarle uno. La pantalla
 * Django sí las lista, con los contadores vacíos.
 */

const filas: FilaCupoProvincia[] = [
  {
    provincia_id: 9,
    provincia: "Formosa",
    cupo_id: 1,
    total_asignado: 4358,
    usados: 1,
    disponibles: 4357,
    fuera: 0,
    configurado: true,
  },
  {
    provincia_id: 2,
    provincia: "Buenos Aires",
    cupo_id: null,
    total_asignado: null,
    usados: null,
    disponibles: null,
    fuera: null,
    configurado: false,
  },
];

const dashboard = vi.fn().mockResolvedValue(filas);
const configurar = vi.fn().mockResolvedValue({});
vi.mock("../api", () => ({ api: { cupos: { dashboard, configurar } } }));

const { CupoDashboardPage } = await import("../pages/CupoDashboardPage");

const montar = () =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ThemeProvider>
        <MemoryRouter>
          <CupoDashboardPage />
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  );

describe("CupoDashboardPage", () => {
  it("lista también las provincias sin cupo configurado", async () => {
    montar();

    expect(await screen.findByText("Formosa")).toBeInTheDocument();
    expect(screen.getByText("Buenos Aires")).toBeInTheDocument();
    expect(screen.getByText("Sin configurar")).toBeInTheDocument();
  });

  it("ofrece asignar en las que no tienen y editar en las que sí", async () => {
    montar();
    await screen.findByText("Formosa");

    expect(screen.getByRole("button", { name: /Asignar cupo/ })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Editar" })).toBeEnabled();
    // Solo la configurada tiene detalle que ver.
    expect(screen.getAllByRole("link", { name: "Ver" })).toHaveLength(1);
  });

  it("asigna el cupo usando el id de provincia, no el del cupo", async () => {
    // La provincia sin cupo no tiene `cupo_id`: mandar ese id fallaría.
    montar();
    await screen.findByText("Buenos Aires");

    fireEvent.click(screen.getByRole("button", { name: /Asignar cupo/ }));
    fireEvent.change(await screen.findByLabelText("Cupo total"), {
      target: { value: "500" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(configurar).toHaveBeenCalledWith(2, 500));
  });

  it("precarga el total actual al editar una provincia ya configurada", async () => {
    montar();
    await screen.findByText("Formosa");

    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    expect(await screen.findByLabelText("Cupo total")).toHaveValue(4358);
  });

  it("no deja guardar un cupo vacío ni negativo", async () => {
    montar();
    await screen.findByText("Buenos Aires");
    fireEvent.click(screen.getByRole("button", { name: /Asignar cupo/ }));

    const guardar = screen.getByRole("button", { name: "Guardar" });
    expect(guardar).toBeDisabled();

    fireEvent.change(await screen.findByLabelText("Cupo total"), {
      target: { value: "-1" },
    });
    expect(guardar).toBeDisabled();
  });

  it("no deja pasarse del máximo que acepta la columna", async () => {
    // 4.294.967.295 es el tope del PositiveIntegerField en MySQL. Pasarse
    // hacía que la base tirara "Out of range value" y el usuario viera un 500.
    montar();
    await screen.findByText("Buenos Aires");
    fireEvent.click(screen.getByRole("button", { name: /Asignar cupo/ }));

    const campo = await screen.findByLabelText("Cupo total");
    const guardar = screen.getByRole("button", { name: "Guardar" });

    fireEvent.change(campo, { target: { value: "4294967296" } });
    expect(guardar).toBeDisabled();
    expect(screen.getByText(/entre 0 y 4\.294\.967\.295/)).toBeInTheDocument();

    // El borde exacto sí se acepta.
    fireEvent.change(campo, { target: { value: "4294967295" } });
    expect(guardar).toBeEnabled();
  });

  it("rechaza un decimal: la columna guarda enteros", async () => {
    montar();
    await screen.findByText("Buenos Aires");
    fireEvent.click(screen.getByRole("button", { name: /Asignar cupo/ }));

    fireEvent.change(await screen.findByLabelText("Cupo total"), {
      target: { value: "10.5" },
    });
    expect(screen.getByRole("button", { name: "Guardar" })).toBeDisabled();
  });
});
