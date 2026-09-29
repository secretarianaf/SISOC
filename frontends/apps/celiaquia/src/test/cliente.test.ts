import { beforeEach, describe, expect, it, vi } from "vitest";
import { leerCookie, mensajeDeError } from "@sisoc/api";

/**
 * El cliente HTTP es lo que sostiene la sesion: si el CSRF deja de viajar, toda
 * escritura pasa a fallar con 403 y el sintoma aparece lejos de la causa.
 */

describe("leerCookie", () => {
  beforeEach(() => {
    vi.spyOn(document, "cookie", "get").mockReturnValue(
      "otra=1; csrftoken=abc%20123; mas=2",
    );
  });

  it("encuentra la cookie por nombre exacto", () => {
    expect(leerCookie("csrftoken")).toBe("abc 123");
  });

  it("no confunde una cookie cuyo nombre es prefijo de otra", () => {
    expect(leerCookie("csrf")).toBeNull();
  });

  it("devuelve null si no esta", () => {
    expect(leerCookie("inexistente")).toBeNull();
  });
});

describe("mensajeDeError", () => {
  it("usa el detail de DRF para errores generales", () => {
    const error = { response: { data: { detail: "No se pudo procesar." } } };
    expect(mensajeDeError(error)).toBe("No se pudo procesar.");
  });

  it("aplana los errores de validacion por campo", () => {
    const error = {
      response: { data: { total_asignado: ["Debe ser un entero >= 0."] } },
    };
    expect(mensajeDeError(error)).toBe(
      "total_asignado: Debe ser un entero >= 0.",
    );
  });

  it("cae a un mensaje generico si la respuesta viene vacia", () => {
    expect(mensajeDeError({})).toBe("No se pudo completar la operación.");
  });
});
