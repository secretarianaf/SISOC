import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "@sisoc/ui";
import type { ArchivoLegajo } from "@sisoc/api";

/**
 * Carga de documentación por persona.
 *
 * Se habilita una vez procesado el Excel: recién ahí existen los legajos. Qué
 * slots pide cada uno depende del rol y lo decide el back, así que el
 * componente no asume cuáles son ni cuántos.
 */

const subirArchivo = vi.fn().mockResolvedValue([]);
vi.mock("../api", () => ({ api: { legajos: { subirArchivo } } }));

const { ArchivosLegajo } = await import("../componentes/ArchivosLegajo");

const archivos: ArchivoLegajo[] = [
  {
    slot: 2,
    campo: "archivo2",
    etiqueta: "DNI (foto) o partida de nacimiento",
    cargado: true,
    url: "https://sisoc.test/media/dni.pdf",
  },
  {
    slot: 3,
    campo: "archivo3",
    etiqueta: "Certificacion de ANSES",
    cargado: false,
    url: "",
  },
];

const montar = (datos: ArchivoLegajo[] = archivos, deshabilitado = false) =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ThemeProvider>
        <ArchivosLegajo
          legajoId={9}
          expedienteId={4}
          archivos={datos}
          deshabilitado={deshabilitado}
        />
      </ThemeProvider>
    </QueryClientProvider>,
  );

describe("ArchivosLegajo", () => {
  it("usa las etiquetas que manda el back, no una lista fija", () => {
    montar();

    expect(screen.getByText(/DNI \(foto\)/)).toBeInTheDocument();
    expect(screen.getByText(/Certificacion de ANSES/)).toBeInTheDocument();
  });

  it("avisa cuántos faltan, porque bloquean el envío del expediente", () => {
    montar();
    expect(screen.getByText("Faltan 1")).toBeInTheDocument();
  });

  it("marca la documentación completa cuando no falta ninguno", () => {
    montar(archivos.map((a) => ({ ...a, cargado: true, url: "x" })));
    expect(screen.getByText("Completa")).toBeInTheDocument();
  });

  it("ofrece ver el archivo ya cargado y subir el que falta", () => {
    montar();

    expect(screen.getByRole("link", { name: "Ver archivo" })).toHaveAttribute(
      "href",
      "https://sisoc.test/media/dni.pdf",
    );
    expect(screen.getByText("Sin cargar")).toBeInTheDocument();
    // El cargado se reemplaza; el que falta se sube.
    expect(screen.getByRole("button", { name: /Reemplazar/ })).toBeEnabled();
    expect(screen.getByRole("button", { name: /Subir/ })).toBeEnabled();
  });

  it("sube al slot que corresponde, no al primero libre", async () => {
    const { container } = montar();
    const inputs = container.querySelectorAll('input[type="file"]');
    const archivo = new File(["x"], "anses.pdf", { type: "application/pdf" });

    // `files` es de solo lectura en jsdom: hay que definirlo a mano.
    Object.defineProperty(inputs[1], "files", { value: [archivo] });
    fireEvent.change(inputs[1]);

    // `mutate()` dispara la request de forma asincrónica.
    // El segundo input es el del slot 3: subir ahí no puede caer en el slot 2.
    await waitFor(() =>
      expect(subirArchivo).toHaveBeenCalledWith(9, archivo, 3),
    );
  });

  it("acepta solo los formatos que acepta el back", () => {
    const { container } = montar();
    const input = container.querySelector('input[type="file"]');

    expect(input).toHaveAttribute("accept", ".pdf,.jpg,.jpeg,.png");
  });

  it("no muestra nada si el legajo no pide documentación", () => {
    const { container } = montar([]);
    expect(container).toBeEmptyDOMElement();
  });
});
