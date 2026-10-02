import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "@sisoc/ui";
import type { RegistroErroneo } from "@sisoc/api";

/**
 * Corrección de una fila que no se pudo importar.
 *
 * El bug que fijan estos tests: el modal mostraba **todo** como texto libre.
 * `municipio` y `localidad` llegan del Excel como ids internos (4468, 129) o
 * como códigos de otro sistema, y el error es literalmente
 * `municipio 40 no encontrado`. Con una caja de texto no hay forma de
 * corregirlo, porque nadie conoce el id. Esos campos van como desplegable,
 * igual que en la pantalla Django.
 */

vi.mock("../api", () => ({
  api: {
    expedientes: {
      catalogos: vi.fn().mockResolvedValue({
        sexos: [
          { id: 1, nombre: "Femenino" },
          { id: 2, nombre: "Masculino" },
        ],
        nacionalidades: [{ id: 9, nombre: "ARGENTINA" }],
      }),
      municipios: vi.fn().mockResolvedValue([{ id: 129, nombre: "La Plata" }]),
      localidades: vi.fn().mockResolvedValue([
        {
          localidad_id: 4468,
          localidad_nombre: "Tolosa",
          municipio_id: 129,
          municipio_nombre: "La Plata",
        },
        {
          localidad_id: 9001,
          localidad_nombre: "Berisso",
          municipio_id: 130,
          municipio_nombre: "Berisso",
        },
      ]),
      actualizarRegistroErroneo: vi.fn().mockResolvedValue({}),
      reprocesarRegistrosErroneos: vi.fn().mockResolvedValue({}),
      eliminarRegistroErroneo: vi.fn().mockResolvedValue({}),
    },
  },
}));

const { RegistrosErroneos } = await import("../componentes/RegistrosErroneos");

const registro: RegistroErroneo = {
  id: 2,
  expediente: 4,
  fila_excel: 2,
  datos_raw: {
    apellido: "cabrera",
    nombre: "claudia beatriz",
    documento: "27254145751",
    sexo: "F",
    nacionalidad: "ARGENTINA",
    municipio: "40",
    localidad: "",
    calle: "RUTA 40",
    nombre_responsable: "Juan",
    sexo_responsable: "M",
    localidad_responsable: "Tolosa (Buenos Aires)",
    fecha_nacimiento: "2000-06-25 00:00:00",
  },
  campo_error: "",
  mensaje_error: "Error al reprocesar: ['municipio 40 no encontrado']",
  procesado: false,
  creado_en: "2026-10-01T10:00:00-03:00",
  procesado_en: null,
};

const montar = (registros: RegistroErroneo[] = [registro]) =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ThemeProvider>
        <RegistrosErroneos registros={registros} expedienteId={4} />
      </ThemeProvider>
    </QueryClientProvider>,
  );

const abrirEditor = async () => {
  fireEvent.click(screen.getByRole("button", { name: /Corregir la fila 2/ }));
  return screen.findByRole("dialog");
};

describe("RegistrosErroneos", () => {
  it("muestra la fila con error y su mensaje", () => {
    montar();

    expect(screen.getByText(/municipio 40 no encontrado/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Corregir la fila 2/ }),
    ).toBeEnabled();
  });

  it("los campos de texto siguen siendo editables", async () => {
    montar();
    const modal = await abrirEditor();

    const documento = within(modal).getByLabelText("Documento");
    fireEvent.change(documento, { target: { value: "27222222222" } });
    expect(documento).toHaveValue("27222222222");
  });

  it("sexo y nacionalidad son desplegables, no texto libre", async () => {
    montar();
    const modal = await abrirEditor();

    for (const campo of ["Sexo", "Nacionalidad", "Municipio", "Localidad"]) {
      const control = within(modal).getByLabelText(campo);
      expect(
        control.getAttribute("role") === "combobox" ||
          control.closest(".MuiSelect-root") !== null ||
          within(modal).queryByRole("combobox", { name: campo }) !== null,
        `${campo} debería ser un desplegable`,
      ).toBe(true);
    }
  });

  it("avisa cuando el valor del Excel no está en el catálogo", async () => {
    montar();
    await abrirEditor();

    // El archivo traía municipio="40", que no existe: hay que elegir uno válido.
    expect(
      await screen.findByText(/El archivo traía "40"/),
    ).toBeInTheDocument();
  });

  it("localidad queda bloqueada hasta elegir municipio", async () => {
    montar();
    const modal = await abrirEditor();

    expect(within(modal).getByText(/Elegí primero un municipio válido/)).toBeInTheDocument();
  });

  it("no se queda sin campos cuando `datos_raw` viene vacío", async () => {
    montar([{ ...registro, datos_raw: {} }]);
    const modal = await abrirEditor();

    expect(
      within(modal).getByText(/no tiene datos para editar/),
    ).toBeInTheDocument();
  });
});


describe("campos del responsable", () => {
  it("sexo del responsable es desplegable, no texto libre", async () => {
    montar();
    const modal = await abrirEditor();

    expect(
      within(modal).queryByRole("combobox", { name: /Sexo responsable/ }) !==
        null ||
        within(modal)
          .getByLabelText(/Sexo responsable/)
          .closest(".MuiSelect-root") !== null,
    ).toBe(true);
  });

  it("la localidad del responsable tiene buscador, no un desplegable largo", async () => {
    // Una provincia llega a 2.699 localidades: con <Select> la pantalla se
    // vuelve inusable, que es el mismo problema que tiene el front viejo.
    montar();
    const modal = await abrirEditor();

    const control = await within(modal).findByRole("combobox", {
      name: /Localidad responsable/,
    });
    expect(control).toHaveAttribute("aria-autocomplete", "list");
  });

  it("avisa si el texto del Excel no coincide con ninguna localidad", async () => {
    montar();
    await abrirEditor();

    expect(
      await screen.findByText(/El archivo traía "Tolosa \(Buenos Aires\)"/),
    ).toBeInTheDocument();
  });

  it("elegir una localidad guarda su id, no el nombre", async () => {
    // El validador acepta nombre, pero si hay dos iguales falla con
    // "Localidad responsable ambigua". Mandar el id lo evita.
    montar();
    const modal = await abrirEditor();

    const control = await within(modal).findByRole("combobox", {
      name: /Localidad responsable/,
    });
    fireEvent.change(control, { target: { value: "Berisso" } });
    fireEvent.click(await screen.findByText(/Berisso \(Berisso\)/));

    expect(control).toHaveValue("Berisso (Berisso)");
  });
});


describe("campos de fecha", () => {
  it("se editan en DD/MM/YYYY, no como el timestamp crudo del Excel", async () => {
    montar();
    const modal = await abrirEditor();

    const fecha = within(modal).getByLabelText("Fecha nacimiento");
    expect(fecha).toHaveValue("25/06/2000");
  });

  it("siguen siendo editables", async () => {
    montar();
    const modal = await abrirEditor();

    const fecha = within(modal).getByLabelText("Fecha nacimiento");
    fireEvent.change(fecha, { target: { value: "01/01/1990" } });
    expect(fecha).toHaveValue("01/01/1990");
  });
});
