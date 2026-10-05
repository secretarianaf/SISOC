import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  camposInvalidosDeError,
  celiaquiaApi,
  leerCookie,
  mensajeDeError,
} from "@sisoc/api";

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

describe("camposInvalidosDeError", () => {
  it("extrae los campos que el back marco como invalidos", () => {
    const error = {
      response: {
        data: {
          detail: "Fila 3: documento invalido",
          invalid_fields: ["documento", "fecha_nacimiento"],
        },
      },
    };
    expect(camposInvalidosDeError(error)).toEqual([
      "documento",
      "fecha_nacimiento",
    ]);
  });

  it("devuelve lista vacia si la respuesta no los trae", () => {
    expect(camposInvalidosDeError({ response: { data: { detail: "x" } } })).toEqual(
      [],
    );
    expect(camposInvalidosDeError(new Error("sin respuesta"))).toEqual([]);
  });
});

describe("requests de registros erroneos", () => {
  /** Doble minimo de axios: solo interesa la URL y el cuerpo que se mandan. */
  const clienteFalso = () => {
    const llamadas: { metodo: string; url: string; body?: unknown }[] = [];
    const registrar =
      (metodo: string) => (url: string, body?: unknown) => {
        llamadas.push({ metodo, url, body });
        return Promise.resolve({ data: {} });
      };
    return {
      llamadas,
      http: {
        get: registrar("get"),
        post: registrar("post"),
        delete: registrar("delete"),
        patch: registrar("patch"),
        put: registrar("put"),
      } as never,
    };
  };

  it("actualizar manda los datos bajo la clave que espera el serializer", async () => {
    const { llamadas, http } = clienteFalso();
    await celiaquiaApi(http).expedientes.actualizarRegistroErroneo(7, 42, {
      documento: "30000001",
    });

    expect(llamadas[0].url).toBe(
      "expedientes/7/registros-erroneos/42/actualizar/",
    );
    expect(llamadas[0].body).toEqual({ datos: { documento: "30000001" } });
  });

  it("reprocesar pega al endpoint del expediente, no al de una fila", async () => {
    const { llamadas, http } = clienteFalso();
    await celiaquiaApi(http).expedientes.reprocesarRegistrosErroneos(7);

    expect(llamadas[0].metodo).toBe("post");
    expect(llamadas[0].url).toBe("expedientes/7/registros-erroneos/reprocesar/");
  });

  it("eliminar usa DELETE sobre la fila", async () => {
    const { llamadas, http } = clienteFalso();
    await celiaquiaApi(http).expedientes.eliminarRegistroErroneo(7, 42);

    expect(llamadas[0].metodo).toBe("delete");
    expect(llamadas[0].url).toBe("expedientes/7/registros-erroneos/42/");
  });
});

describe("requests de comentarios, subsanacion y lookups", () => {
  const clienteFalso = () => {
    const llamadas: {
      metodo: string;
      url: string;
      body?: unknown;
      config?: unknown;
    }[] = [];
    const registrar =
      (metodo: string) => (url: string, a?: unknown, b?: unknown) => {
        // get lleva la config en el 2do argumento; post, en el 3ro.
        const esGet = metodo === "get";
        llamadas.push({
          metodo,
          url,
          body: esGet ? undefined : a,
          config: esGet ? a : b,
        });
        return Promise.resolve({ data: {} });
      };
    return {
      llamadas,
      http: {
        get: registrar("get"),
        post: registrar("post"),
        delete: registrar("delete"),
        patch: registrar("patch"),
        put: registrar("put"),
      } as never,
    };
  };

  it("el historial de comentarios pega al legajo", async () => {
    const { llamadas, http } = clienteFalso();
    await celiaquiaApi(http).legajos.comentarios(9);
    expect(llamadas[0].url).toBe("legajos/9/comentarios/");
  });

  it("responder subsanacion manda los archivos como multipart", async () => {
    const { llamadas, http } = clienteFalso();
    const archivo = new File(["x"], "evidencia.pdf");
    await celiaquiaApi(http).legajos.responderSubsanacion(9, [archivo], {
      descripcion: "dorso del DNI",
    });

    expect(llamadas[0].url).toBe("legajos/9/responder-subsanacion/");
    const form = llamadas[0].body as FormData;
    expect(form.getAll("archivos")).toHaveLength(1);
    expect(form.get("descripcion")).toBe("dorso del DNI");
  });

  it("las descargas piden un blob y no JSON", async () => {
    const { llamadas, http } = clienteFalso();
    await celiaquiaApi(http).expedientes.plantillaExcel();
    expect(llamadas[0].url).toBe("expedientes/plantilla-excel/");
    expect(llamadas[0].config).toEqual({ responseType: "blob" });
  });

  it("el lookup de localidades va por expediente y propaga el municipio", async () => {
    // Las localidades se acotan a la provincia del expediente: el validador
    // rechaza las de otra provincia.
    const { llamadas, http } = clienteFalso();
    await celiaquiaApi(http).expedientes.localidades(7, { municipio: 129 });
    expect(llamadas[0].url).toBe("expedientes/7/localidades/");
    expect(llamadas[0].config).toEqual({ params: { municipio: 129 } });
  });

  it("los municipios tambien van por expediente", async () => {
    const { llamadas, http } = clienteFalso();
    await celiaquiaApi(http).expedientes.municipios(7);
    expect(llamadas[0].url).toBe("expedientes/7/municipios/");
  });
});
