import { describe, expect, it } from "vitest";
import {
  formatearFecha,
  formatearFechaHora,
  normalizarFechaEditable,
} from "@sisoc/ui";

/**
 * Formato de fechas: DD/MM/YYYY con ceros.
 *
 * `toLocaleDateString("es-AR")` devuelve `1/10/2026` y `5/6/2000`, de ancho
 * variable. En una tabla queda desprolijo y se lee peor.
 */

describe("formatearFecha", () => {
  it("rellena con ceros el dia y el mes", () => {
    expect(formatearFecha("2000-06-05T00:00:00-03:00")).toBe("05/06/2000");
    expect(formatearFecha("2026-10-01T10:00:00-03:00")).toBe("01/10/2026");
  });

  it("devuelve un guion cuando no hay fecha, para distinguirlo de un vacio", () => {
    expect(formatearFecha(null)).toBe("—");
    expect(formatearFecha("")).toBe("—");
    expect(formatearFecha("no es una fecha")).toBe("—");
  });
});

describe("formatearFechaHora", () => {
  it("agrega la hora en 24h, que es lo que distingue dos eventos", () => {
    expect(formatearFechaHora("2026-10-01T09:05:00-03:00")).toBe(
      "01/10/2026 09:05",
    );
  });
});

describe("normalizarFechaEditable", () => {
  it("convierte el timestamp crudo del Excel a DD/MM/YYYY", () => {
    expect(normalizarFechaEditable("2000-06-25 00:00:00")).toBe("25/06/2000");
    expect(normalizarFechaEditable("2000-06-25")).toBe("25/06/2000");
  });

  it("no toca lo que ya esta en el formato correcto", () => {
    expect(normalizarFechaEditable("25/06/2000")).toBe("25/06/2000");
  });

  it("no corre un dia por interpretar la fecha como UTC", () => {
    // Con `new Date("2000-06-25")` el navegador la toma como UTC y en Argentina
    // muestra el 24. Por eso se parsea el texto, no se construye un Date.
    expect(normalizarFechaEditable("2000-01-01")).toBe("01/01/2000");
    expect(normalizarFechaEditable("2000-12-31")).toBe("31/12/2000");
  });

  it("deja intacto lo que no reconoce: puede ser el dato mal cargado", () => {
    expect(normalizarFechaEditable("25 de junio")).toBe("25 de junio");
    expect(normalizarFechaEditable("")).toBe("");
  });
});
