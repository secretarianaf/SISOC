import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ThemeProvider } from "@sisoc/ui";
import type { ExclusionImportacion } from "@sisoc/api";
import { ExclusionesImportacion } from "../componentes/ExclusionesImportacion";

/**
 * Personas que no se incorporaron porque ya estaban en el programa.
 *
 * Es la validación que el usuario reportó como faltante: no se puede cargar la
 * misma persona en dos expedientes, y se valida por documento. La regla corre
 * en `ImportacionService`; lo que faltaba era mostrarla.
 */

const exclusiones: ExclusionImportacion[] = [
  {
    fila: 5,
    documento: "20111111112",
    nombre: "Ana",
    apellido: "Perez",
    motivo: "Ya está dentro del programa en otro expediente",
    expediente_origen_id: 7,
  },
  {
    fila: 9,
    documento: "20111111113",
    nombre: "Luis",
    apellido: "Gomez",
    motivo: "Ya existe en este expediente",
  },
];

const montar = (datos: ExclusionImportacion[]) =>
  render(
    <MemoryRouter>
      <ThemeProvider>
        <ExclusionesImportacion exclusiones={datos} />
      </ThemeProvider>
    </MemoryRouter>,
  );

describe("ExclusionesImportacion", () => {
  it("lista cada persona con su documento y su motivo", () => {
    montar(exclusiones);

    expect(screen.getByText(/Perez, Ana/)).toBeInTheDocument();
    expect(screen.getByText("20111111112")).toBeInTheDocument();
    expect(
      screen.getByText(/Ya está dentro del programa en otro expediente/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Ya existe en este expediente/)).toBeInTheDocument();
  });

  it("enlaza al expediente donde la persona ya está cargada", () => {
    montar(exclusiones);

    const enlace = screen.getByRole("link", { name: "#7" });
    expect(enlace).toHaveAttribute("href", "/expedientes/7");
  });

  it("no inventa un enlace cuando el back no mandó el expediente de origen", () => {
    montar([exclusiones[1]]);

    expect(screen.queryByRole("link")).toBeNull();
  });

  it("no ocupa lugar si no hubo exclusiones", () => {
    const { container } = montar([]);

    expect(container).toBeEmptyDOMElement();
  });
});
