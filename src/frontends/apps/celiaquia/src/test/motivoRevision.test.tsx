import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "@sisoc/ui";

/**
 * Motivo de subsanación o rechazo (issue #2592).
 *
 * Cada instancia lleva solo las observaciones que se eligen: las que todavía
 * no se comunicaron a la provincia vienen tildadas, el resto no. Lo que se
 * manda al back son los ids, no el texto.
 */

const motivoPreview = vi.fn().mockResolvedValue({
  tiene_observaciones: true,
  opciones: [
    { id: 11, etiqueta: "RENAPER: el DNI no coincide", pendiente: true },
    { id: 12, etiqueta: "ANSES: certificación vencida", pendiente: false },
  ],
});
vi.mock("../api", () => ({ api: { legajos: { motivoPreview } } }));

const { MotivoRevision } = await import("../componentes/MotivoRevision");

const montar = (onConfirmar = vi.fn()) => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ThemeProvider>
        <MotivoRevision
          legajoId={5}
          accion="SUBSANAR"
          onCancelar={vi.fn()}
          onConfirmar={onConfirmar}
        />
      </ThemeProvider>
    </QueryClientProvider>,
  );
  return onConfirmar;
};

describe("MotivoRevision", () => {
  it("tilda de entrada solo las observaciones pendientes", async () => {
    montar();

    const pendiente = await screen.findByLabelText("RENAPER: el DNI no coincide");
    expect(pendiente).toBeChecked();
    expect(screen.getByLabelText("ANSES: certificación vencida")).not.toBeChecked();
  });

  it("manda los ids elegidos y el texto libre", async () => {
    const onConfirmar = montar();

    fireEvent.click(await screen.findByLabelText("ANSES: certificación vencida"));
    fireEvent.change(screen.getByLabelText("Texto complementario"), {
      target: { value: "Revisar la documentación" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));

    expect(onConfirmar).toHaveBeenCalledWith({
      texto_libre: "Revisar la documentación",
      observaciones_ids: [11, 12],
      documentacion_complementaria: [],
    });
  });

  it("no deja confirmar sin observaciones ni texto", async () => {
    montar();

    fireEvent.click(await screen.findByLabelText("RENAPER: el DNI no coincide"));

    expect(screen.getByRole("button", { name: "Confirmar" })).toBeDisabled();
  });
});
