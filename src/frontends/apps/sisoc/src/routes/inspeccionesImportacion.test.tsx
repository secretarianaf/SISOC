import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { inspeccionesImportacionRoute } from "./inspeccionesImportacion";
import { readyContext, setViewport } from "./testFixtures";

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: () => ({ get }),
  leerCookie: () => "synthetic-csrf",
}));

const upload = "/inspecciones/escuelas/importar/";
const review = upload + "a".repeat(32) + "/";
const result = review + "confirmar/";
const volver = "/inspecciones/";
const filename = "padrón de prueba.csv";
const base = {
  tipo: "escuelas", titulo: "Importar escuelas", csrf: "synthetic-csrf",
  layout: { breadcrumb: [], display_name: "Gestora", role: "Gestión", initials: "GP" },
  tabs: [{ id: "escuelas", label: "Escuelas", url: volver }],
  totales: { escuelas: 2, escuelas_a_revisar: 1, jornada: "24/11", asignaciones_hoy: 3, actas_hoy: 4 },
};
const summary = {
  nombre_archivo: filename,
  resumen: {
    total: 2, fila_encabezado: 1, a_importar: 1, nuevas_sin_observaciones: 1,
    actualizadas_sin_observaciones: 0, a_revisar: 0, rechazadas: 1, sin_cambios: 0,
    columnas: [{ original: "Jurisdicción", campo: "Provincia", renombrada: true }],
    motivos: [], equivalencias: [],
  },
  observaciones: [{ fila: 3, cueanexo: "", nombre: "Escuela fuera de catálogo", tipo: "rechazada", motivo: "No existe", detalle: "Sin localidad" }],
  total_observaciones: 1,
};

function open(path: string, data: Record<string, unknown>) {
  window.history.replaceState({}, "", path);
  const script = document.createElement("script");
  script.type = "application/json";
  script.id = "inspecciones-importacion-data";
  script.textContent = JSON.stringify(data);
  document.head.append(script);
  const match = inspeccionesImportacionRoute.match(path);
  if (!match) throw new Error("The canonical path did not match");
  render(inspeccionesImportacionRoute.render(match));
}

beforeEach(() => {
  setViewport(false);
  get.mockReset();
  get.mockResolvedValue({ data: readyContext, status: 200 });
});
afterEach(() => { cleanup(); document.getElementById("inspecciones-importacion-data")?.remove(); });

describe("Inspecciones import canonical pages", () => {
  it("owns the visible canonical pages, but not cancel or CSV", () => {
    expect(inspeccionesImportacionRoute.match(upload)).toBeTruthy();
    expect(inspeccionesImportacionRoute.match(review)).toBeTruthy();
    expect(inspeccionesImportacionRoute.match(result)).toBeTruthy();
    expect(inspeccionesImportacionRoute.match(review + "cancelar/")).toBeNull();
    expect(inspeccionesImportacionRoute.match(review + "observaciones.csv")).toBeNull();
    expect(inspeccionesImportacionRoute.match("/inspecciones/asignaciones/importar/")).toBeTruthy();
  });

  it("renders only the owner's embedded review, posts by native forms and links the unchanged CSV", async () => {
    open(review, { ...base, ...summary, paso: 2, urls: { subir: upload, volver, confirmar: result, cancelar: review + "cancelar/", observaciones: review + "observaciones.csv" } });
    expect(await screen.findByText(filename)).toBeTruthy();
    expect(screen.getByText("Escuela fuera de catálogo")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Descargar las 1 observaciones/ }).getAttribute("href")).toBe(review + "observaciones.csv");
    const confirm = screen.getByRole("button", { name: "Importar 1 escuelas" }) as HTMLButtonElement;
    expect(confirm.form?.getAttribute("method")).toBe("post");
    expect(confirm.form?.getAttribute("action")).toBe(result);
    expect(confirm.form?.querySelector("input[name=csrfmiddlewaretoken]")?.getAttribute("value")).toBe("synthetic-csrf");
    expect((screen.getByRole("button", { name: "Cancelar" }) as HTMLButtonElement).form?.getAttribute("action")).toBe(review + "cancelar/");
    expect(get.mock.calls.map(([url]) => url)).toEqual(["web/session/"]);
  });

  it("renders the POST result without reloading or offering to repeat the POST", async () => {
    open(result, { ...base, ...summary, paso: 3, urls: { volver } });
    expect(await screen.findByText("Importación terminada.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Volver al listado" }).getAttribute("href")).toBe(volver);
    expect(screen.queryByRole("button", { name: /^Importar/ })).toBeNull();
    expect(get.mock.calls.map(([url]) => url)).toEqual(["web/session/"]);
  });

  it("shows native field errors and keeps a multipart file form", async () => {
    open(upload, { ...base, paso: 1, errores: ["Archivo inválido"], urls: { subir: upload, volver } });
    expect(await screen.findByText("Archivo inválido")).toBeTruthy();
    const file = screen.getByLabelText("Archivo Excel (.xlsx) o CSV") as HTMLInputElement;
    expect(file.name).toBe("archivo");
    expect(file.form?.enctype).toBe("multipart/form-data");
    expect(file.form?.getAttribute("action")).toBe(upload);
  });
});
