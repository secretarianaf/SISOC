import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { headerItemsFor, SITUACION_CALLE_CONSULTAS_URL } from "./cdfFrame";

describe("Situación de Calle Mesa de Ayuda in the header (#2938)", () => {
  afterEach(cleanup);

  it.each(["/dispositivos/", "/dispositivos/7/", "/dispositivos/mapa/", "/datacalle/relevamientos/", "/datacalle/casos/abc/"])(
    "adds the Consultas item on %s",
    (pathname) => {
      render(<ul>{headerItemsFor(pathname)}</ul>);
      const consultas = screen.getByRole("link", { name: "Consultas (se abre en una nueva pestaña)" });
      expect(consultas.getAttribute("href")).toBe("https://consultas.capitalhumano.gob.ar/canales/equipo-situacion-de-calle");
      expect(consultas.getAttribute("href")).toBe(SITUACION_CALLE_CONSULTAS_URL);
      expect(consultas.getAttribute("target")).toBe("_blank");
      expect(consultas.getAttribute("rel")).toBe("noopener noreferrer");
    },
  );

  it.each(["/centrodefamilia/", "/centrodefamilia/7/", "/dispositivosx/", "/comedores/"])("adds nothing on %s", (pathname) => {
    expect(headerItemsFor(pathname)).toBeUndefined();
  });
});
