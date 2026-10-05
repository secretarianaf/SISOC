import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "@sisoc/ui";

/**
 * Tramo final del flujo: asignar técnico, validar con RENAPER y responder una
 * subsanación. Estaban en Django y faltaban en React.
 */

const validarRenaper = vi.fn().mockResolvedValue({
  success: true,
  ciudadano_nombre: "Ana Perez",
  documento: "27254145751",
  datos_provincia: { nombre: "Ana", apellido: "Perez" },
  datos_renaper: { nombre: "ANA", apellido: "Perez" },
  datos_ejemplar: {},
});
const guardarValidacionRenaper = vi
  .fn()
  .mockResolvedValue({ detail: "Validación Renaper guardada: Aceptado" });
const responderSubsanacion = vi
  .fn()
  .mockResolvedValue({ detail: "Archivos cargados." });
const confirmarSubsanacion = vi
  .fn()
  .mockResolvedValue({ id: 9, revision_tecnico: "SUBSANADO" });
const tecnicos = vi
  .fn()
  .mockResolvedValue([{ id: 3, nombre: "Lopez, Juan" }]);
const asignarTecnico = vi.fn().mockResolvedValue({});

vi.mock("../api", () => ({
  api: {
    legajos: {
      validarRenaper,
      guardarValidacionRenaper,
      responderSubsanacion,
      confirmarSubsanacion,
    },
    expedientes: { tecnicos, asignarTecnico, desasignarTecnico: vi.fn() },
  },
}));

const { ValidacionRenaper } = await import("../componentes/ValidacionRenaper");
const { RespuestaSubsanacion } = await import(
  "../componentes/RespuestaSubsanacion"
);
const { AsignacionTecnico } = await import("../componentes/AsignacionTecnico");

const envolver = (nodo: React.ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ThemeProvider>{nodo}</ThemeProvider>
    </QueryClientProvider>,
  );

describe("ValidacionRenaper", () => {
  it("consulta primero y recién después deja confirmar", async () => {
    envolver(<ValidacionRenaper legajoId={9} expedienteId={4} />);

    // Sin consultar no hay nada que confirmar.
    expect(screen.queryByRole("button", { name: "Datos correctos" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Validar con RENAPER/ }));

    const modal = await screen.findByRole("dialog");
    expect(within(modal).getByText(/Ana Perez/)).toBeInTheDocument();
    expect(
      within(modal).getByRole("button", { name: "Datos correctos" }),
    ).toBeEnabled();
  });

  it("muestra lado a lado lo cargado y lo que devuelve RENAPER", async () => {
    envolver(<ValidacionRenaper legajoId={9} expedienteId={4} />);
    fireEvent.click(screen.getByRole("button", { name: /Validar con RENAPER/ }));
    const modal = await screen.findByRole("dialog");

    expect(within(modal).getByText("Ana")).toBeInTheDocument();
    expect(within(modal).getByText("ANA")).toBeInTheDocument();
  });

  it("no deja pedir subsanación sin motivo", async () => {
    envolver(<ValidacionRenaper legajoId={9} expedienteId={4} />);
    fireEvent.click(screen.getByRole("button", { name: /Validar con RENAPER/ }));
    const modal = await screen.findByRole("dialog");

    const pedir = within(modal).getByRole("button", { name: /Pedir subsanación/ });
    expect(pedir).toBeDisabled();

    fireEvent.change(within(modal).getByLabelText(/Motivo/), {
      target: { value: "La foto no coincide" },
    });
    expect(pedir).toBeEnabled();
  });

  it("confirmar manda el estado que corresponde", async () => {
    envolver(<ValidacionRenaper legajoId={9} expedienteId={4} />);
    fireEvent.click(screen.getByRole("button", { name: /Validar con RENAPER/ }));
    const modal = await screen.findByRole("dialog");
    fireEvent.click(within(modal).getByRole("button", { name: "Datos correctos" }));

    await waitFor(() =>
      expect(guardarValidacionRenaper).toHaveBeenCalledWith(9, "1", undefined),
    );
  });
});

describe("RespuestaSubsanacion", () => {
  it("muestra el motivo por el que se pidió", () => {
    envolver(
      <RespuestaSubsanacion
        legajoId={9}
        expedienteId={4}
        motivo="Falta el dorso del DNI"
      />,
    );
    expect(screen.getByText("Falta el dorso del DNI")).toBeInTheDocument();
  });

  it("no deja enviar sin adjuntar: el back lo rechaza igual", () => {
    envolver(<RespuestaSubsanacion legajoId={9} expedienteId={4} motivo="x" />);

    expect(screen.getByRole("button", { name: /Enviar respuesta/ })).toBeDisabled();
    expect(screen.getByText(/Adjuntá al menos un archivo/)).toBeInTheDocument();
  });

  it("confirmar es un paso aparte: subir la evidencia no cambia el estado", async () => {
    // Era el bug: se subian los archivos, se enviaba el comentario, y el
    // legajo seguia en SUBSANAR, asi que no se podia aprobar ni rechazar.
    envolver(<RespuestaSubsanacion legajoId={9} expedienteId={4} motivo="x" />);

    const confirmar = screen.getByRole("button", {
      name: /Confirmar subsanación/,
    });
    expect(confirmar).toBeEnabled();
    fireEvent.click(confirmar);

    await waitFor(() => expect(confirmarSubsanacion).toHaveBeenCalledWith(9));
    expect(
      await screen.findByText(/vuelve a revisión técnica/),
    ).toBeInTheDocument();
  });

  it("avisa que falta confirmar despues de subir la evidencia", async () => {
    const { container } = envolver(
      <RespuestaSubsanacion legajoId={9} expedienteId={4} motivo="x" />,
    );
    const input = container.querySelector('input[type="file"]')!;
    const a = new File(["x"], "frente.pdf");
    Object.defineProperty(input, "files", { value: [a], configurable: true });
    fireEvent.change(input);
    fireEvent.click(screen.getByRole("button", { name: /Enviar respuesta/ }));

    expect(await screen.findByText(/Falta confirmar/)).toBeInTheDocument();
  });

  it("acepta varios archivos a la vez, porque son evidencia nueva", async () => {
    const { container } = envolver(
      <RespuestaSubsanacion legajoId={9} expedienteId={4} motivo="x" />,
    );
    const input = container.querySelector('input[type="file"]')!;
    expect(input).toHaveAttribute("multiple");

    const a = new File(["x"], "frente.pdf");
    const b = new File(["y"], "dorso.pdf");
    Object.defineProperty(input, "files", { value: [a, b], configurable: true });
    fireEvent.change(input);

    expect(await screen.findByText("frente.pdf")).toBeInTheDocument();
    expect(screen.getByText("dorso.pdf")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Enviar respuesta/ }));
    await waitFor(() =>
      expect(responderSubsanacion).toHaveBeenCalledWith(9, [a, b], {
        descripcion: undefined,
      }),
    );
  });
});

describe("AsignacionTecnico", () => {
  it("avisa cuando no hay técnico, porque bloquea la revisión", async () => {
    envolver(<AsignacionTecnico expedienteId={4} asignaciones={[]} />);
    expect(screen.getByText("Sin asignar")).toBeInTheDocument();
  });

  it("asigna el técnico elegido", async () => {
    envolver(<AsignacionTecnico expedienteId={4} asignaciones={[]} />);

    const select = await screen.findByLabelText("Técnico");
    fireEvent.mouseDown(select);
    fireEvent.click(await screen.findByText("Lopez, Juan"));
    fireEvent.click(screen.getByRole("button", { name: "Asignar" }));

    await waitFor(() => expect(asignarTecnico).toHaveBeenCalledWith(4, 3));
  });
});
