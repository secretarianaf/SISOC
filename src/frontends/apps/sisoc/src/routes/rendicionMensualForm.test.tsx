import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { bajaNavigation } from "./comedorIntervencionesBaja";
import { findRoute } from "./index";
import { bajaRendicionValid, editarValid, nuevaValid, rendicionFormNavigation } from "./rendicionMensualForm";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const PREFIX = "/rendicioncuentasmensual/rendicioncuentasmensual";
const API = "web/comedores/rendicioncuentasmensual/";
const MESES = [{ value: "", label: "---------" }, { value: "1", label: "Enero" }, { value: "2", label: "Febrero" }];
const campo = (name: string, label: string, over: Record<string, unknown> = {}) => ({ name, label, required: false, value: "", ...over });
const nueva = (over: Record<string, unknown> = {}) => ({
  comedor_id: 7, titulo: "Crear", urls: { listado: `${PREFIX}/7/` }, errors: {}, non_field_errors: [], messages: [],
  campos: {
    mes: campo("mes", "Mes", { required: true, choices: MESES }), anio: campo("anio", "Año", { required: true }),
    linea_programatica: campo("linea_programatica", "Linea Programatica", { required: true, choices: [{ value: "tradicional", label: "Tradicional" }, { value: "secos", label: "Secos" }] }),
    estado: campo("estado", "Estado de Rendición", { required: true, choices: [{ value: "elaboracion", label: "Presentación en elaboración" }, { value: "revision", label: "Presentación en revisión" }] }),
    observaciones: campo("observaciones", "Observaciones", { rows: 3 }),
    nombre: campo("nombre", "Nombre del Documento", { required: true, maxlength: 255 }), archivo: campo("archivo", "Archivo", { required: true }),
  }, ...over,
});
const CONVENIOS = [{ value: "", label: "---------" }, { value: "P01", label: "P01" }, { value: "P02", label: "P02" }];
const NUMEROS = [{ value: "", label: "---------" }, { value: "1", label: "1" }, { value: "2", label: "2" }];
const editar = (over: Record<string, unknown> = {}) => ({
  id: 5, numero: "2", urls: { detalle: `${PREFIX}/detalle/5/` }, errors: {}, non_field_errors: [], messages: [],
  campos: {
    convenio: campo("convenio", "Convenio", { value: "P01", choices: CONVENIOS }), numero_rendicion: campo("numero_rendicion", "Numero rendicion", { value: "2", choices: NUMEROS }),
    periodo_inicio: campo("periodo_inicio", "Periodo inicio", { value: "2026-03-01" }), periodo_fin: campo("periodo_fin", "Periodo fin", { value: "2026-03-31" }),
    nombre: campo("nombre", "Nombre de Rendición", { value: "Rendición marzo", maxlength: 255 }),
  }, ...over,
});
const baja = (over: Record<string, unknown> = {}) => ({
  id: 5, object_name: "RENDICIONCUENTAMENSUAL OBJECT (5)", confirm_text: "Dar de baja", cancel_text: "Cancelar", cancel_url: `${PREFIX}/detalle/5/`, messages: [],
  cascade_preview: { total_afectados: 1, total_baja_logica: 1, total_borrado_fisico: 0, desglose_por_modelo: [{ modelo: "Rendiciones", cantidad: 1, modo: "baja_logica", ejemplos: ["R (ID 5)"] }] },
  ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
function setup(url: string) {
  window.history.replaceState({}, "", url);
  return render(<App />);
}
const field = (id: string) => document.getElementById(id) as HTMLInputElement;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("Rendición mensual form routes", () => {
  it("owns only the three native paths with the repeated prefix", () => {
    for (const page of ["nuevo", "editar", "eliminar"]) {
      expect(findRoute(`${PREFIX}/${page}/5/`)?.route.name).toBe("comedores-rendicion-mensual-form");
      expect(findRoute(`${PREFIX}/${page}/5`)?.route.name).not.toBe("comedores-rendicion-mensual-form");
      expect(findRoute(`${PREFIX}/${page}/x/`)?.route.name).not.toBe("comedores-rendicion-mensual-form");
    }
    expect(findRoute("/rendicioncuentasmensual/nuevo/5/")?.route.name).not.toBe("comedores-rendicion-mensual-form");
  });

  it("validates the three payloads", () => {
    expect(nuevaValid(nueva())).toBe(true);
    expect(nuevaValid(nueva({ urls: { listado: "https://otro.example/" } }))).toBe(false);
    expect(nuevaValid(nueva({ campos: { mes: campo("mes", "Mes") } }))).toBe(false);
    expect(editarValid(editar())).toBe(true);
    expect(editarValid(editar({ errors: { nombre: [{ message: "x" }] } }))).toBe(false);
    expect(bajaRendicionValid(baja())).toBe(true);
    expect(bajaRendicionValid({ ...baja(), cancel_url: "" })).toBe(false);
  });
});

describe("Create form", () => {
  it("renders the native card layout, the fields and the buttons", async () => {
    serve(nueva());
    setup(`${PREFIX}/nuevo/7/`);
    await screen.findByRole("heading", { level: 2, name: "Crear Seguimiento mensual" });
    expect(webGet).toHaveBeenCalledWith(`${API}nuevo/7/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Detalle de Rendición de Cuenta"));
    expect(screen.getByRole("link", { name: "Rendiciones de Cuenta" }).getAttribute("href")).toBe(`${PREFIX}/7/`);
    expect(screen.getByText("Crear Rendición").className).toContain("active");
    expect(screen.getByText("Datos asociados").tagName).toBe("H5");
    expect(screen.getByText("Documentación Adjunta").tagName).toBe("H5");
    expect(field("id_mes").className).toBe("form-control select form-select");
    expect(Array.from((field("id_mes") as unknown as HTMLSelectElement).options).map((o) => o.text)).toEqual(["---------", "Enero", "Febrero"]);
    expect(field("id_anio").type).toBe("number");
    for (const name of ["linea_programatica", "estado"]) {
      const control = field(`id_${name}`);
      expect(control.tagName).toBe("SELECT");
      expect(control.required).toBe(true);
    }
    expect(field("id_observaciones").tagName).toBe("TEXTAREA");
    expect(field("id_nombre").maxLength).toBe(255);
    expect(field("id_archivo").type).toBe("file");
    expect(field("id_archivo").required).toBe(true);
    expect(screen.getByRole("button", { name: "Guardar" }).className).toBe("btn btn-success");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe(`${PREFIX}/7/`);
  });

  it("adds and removes attachment rows like the native script", async () => {
    serve(nueva());
    setup(`${PREFIX}/nuevo/7/`);
    await screen.findByText("Documentación Adjunta");
    const rows = () => document.querySelectorAll(".documentacion-item").length;
    fireEvent.click(screen.getByRole("button", { name: "Agregar Archivo" }));
    fireEvent.click(screen.getByRole("button", { name: "Agregar Archivo" }));
    expect(rows()).toBe(3);
    fireEvent.click(screen.getByRole("button", { name: "Eliminar Archivo" }));
    expect(rows()).toBe(2);
    fireEvent.click(screen.getByRole("button", { name: "Eliminar Archivo" }));
    fireEvent.change(document.querySelector<HTMLInputElement>('input[name="nombre"]')!, { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar Archivo" }));
    expect(rows()).toBe(1);
    expect(document.querySelector<HTMLInputElement>('input[name="nombre"]')!.value).toBe("");
  });

  it("posts every rendered field as multipart and follows the confirmed redirect", async () => {
    const assign = vi.spyOn(rendicionFormNavigation, "assign").mockImplementation(() => {});
    serve(nueva());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: `${PREFIX}/7/` } });
    setup(`${PREFIX}/nuevo/7/`);
    await screen.findByText("Documentación Adjunta");
    fireEvent.change(field("id_mes"), { target: { value: "2" } });
    fireEvent.change(field("id_anio"), { target: { value: "2026" } });
    fireEvent.change(field("id_linea_programatica"), { target: { value: "secos" } });
    fireEvent.change(field("id_estado"), { target: { value: "revision" } });
    fireEvent.change(field("id_nombre"), { target: { value: "Planilla" } });
    fireEvent.submit(screen.getByRole("button", { name: "Guardar" }).closest("form")!);
    await waitFor(() => expect(assign).toHaveBeenCalledWith(`${PREFIX}/7/`));
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(`${API}nuevo/7/`);
    expect(body).toBeInstanceOf(FormData);
    expect([...(body as FormData).keys()].sort()).toEqual(["anio", "archivo", "csrfmiddlewaretoken", "estado", "linea_programatica", "mes", "nombre", "observaciones"]);
    expect((body as FormData).get("mes")).toBe("2");
    expect((body as FormData).get("linea_programatica")).toBe("secos");
    expect((body as FormData).get("estado")).toBe("revision");
  });

  it("shows bound errors and preserves entered values after a rejected post", async () => {
    const initial = nueva();
    serve(initial);
    webPost.mockResolvedValue({
      status: 400,
      data: nueva({
        campos: { ...initial.campos, anio: { ...initial.campos.anio, value: "2026" } },
        errors: { linea_programatica: [{ message: "Este campo es obligatorio.", code: "required" }] },
        non_field_errors: ["Revise los datos de la rendición."],
      }),
    });
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    setup(`${PREFIX}/nuevo/7/`);
    await screen.findByText("Documentación Adjunta");
    fireEvent.click(screen.getByRole("button", { name: "Agregar Archivo" }));
    fireEvent.change(field("id_anio"), { target: { value: "2026" } });
    fireEvent.submit(screen.getByRole("button", { name: "Guardar" }).closest("form")!);
    await waitFor(() => expect(scroll).toHaveBeenCalledWith(0, 0));
    expect(await screen.findByText("Este campo es obligatorio.")).toBeTruthy();
    expect(screen.getByText("Revise los datos de la rendición.")).toBeTruthy();
    expect(field("id_linea_programatica").getAttribute("aria-invalid")).toBe("true");
    expect(field("id_anio").value).toBe("2026");
    expect(document.querySelectorAll(".documentacion-item")).toHaveLength(1);
    expect((screen.getByRole("button", { name: "Guardar" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("blocks the form when the outcome is unknown", async () => {
    serve(nueva());
    webPost.mockRejectedValue(new Error("network"));
    setup(`${PREFIX}/nuevo/7/`);
    await screen.findByText("Documentación Adjunta");
    fireEvent.submit(screen.getByRole("button", { name: "Guardar" }).closest("form")!);
    await screen.findByRole("alert");
    expect((screen.getByRole("button", { name: "Guardar" }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
  });
});

describe("Edit form", () => {
  it("renders the preloaded data, the hint and the native breadcrumb", async () => {
    serve(editar());
    setup(`${PREFIX}/editar/5/`);
    await screen.findByText("Editar datos de rendición", { selector: "h5" });
    expect(webGet).toHaveBeenCalledWith(`${API}editar/5/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Editar datos de rendición"));
    expect(screen.getByRole("link", { name: "Rendición 2" }).getAttribute("title")).toBe("Volver al detalle de la rendición");
    expect(screen.getByText("Editar datos").className).toContain("active");
    expect(document.querySelector("p.text-muted.small")?.textContent).toBe(
      "Los datos vienen precargados. Lo que dejes igual conserva su valor; no hace falta completar de nuevo los campos que no cambian.");
    expect(field("id_convenio").value).toBe("P01");
    expect(field("id_numero_rendicion").value).toBe("2");
    expect(field("id_periodo_inicio").value).toBe("2026-03-01");
    expect(field("id_nombre").value).toBe("Rendición marzo");
    expect(document.querySelector(".requiredField")).toBeNull();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe(`${PREFIX}/detalle/5/`);
  });

  it("posts the five fields urlencoded and navigates to the detail", async () => {
    const assign = vi.spyOn(rendicionFormNavigation, "assign").mockImplementation(() => {});
    serve(editar());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: `${PREFIX}/detalle/5/` } });
    setup(`${PREFIX}/editar/5/`);
    await screen.findByText("Editar datos de rendición", { selector: "h5" });
    fireEvent.change(field("id_convenio"), { target: { value: "P02" } });
    fireEvent.submit(screen.getByRole("button", { name: "Guardar" }).closest("form")!);
    await waitFor(() => expect(assign).toHaveBeenCalledWith(`${PREFIX}/detalle/5/`));
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(`${API}editar/5/`);
    expect(body).toBeInstanceOf(URLSearchParams);
    expect(Object.fromEntries(body as URLSearchParams)).toEqual({
      csrfmiddlewaretoken: "synthetic-csrf-token", convenio: "P02", numero_rendicion: "2", periodo_inicio: "2026-03-01", periodo_fin: "2026-03-31", nombre: "Rendición marzo",
    });
  });

  it("shows the native errors with the typed values after a rejected post", async () => {
    serve(editar());
    const rechazada = editar({
      errors: { periodo_fin: [{ message: "La fecha de fin debe ser posterior o igual a la fecha de inicio.", code: "invalid" }] },
      non_field_errors: ["Error general"],
    });
    rechazada.campos.periodo_inicio.value = "2026-03-10";
    rechazada.campos.periodo_fin.value = "2026-03-01";
    webPost.mockResolvedValue({ status: 400, data: rechazada });
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    setup(`${PREFIX}/editar/5/`);
    await screen.findByText("Editar datos de rendición", { selector: "h5" });
    fireEvent.submit(screen.getByRole("button", { name: "Guardar" }).closest("form")!);
    await screen.findByText("La fecha de fin debe ser posterior o igual a la fecha de inicio.");
    expect(scroll).toHaveBeenCalledWith(0, 0);
    expect(field("id_periodo_fin").className).toContain("is-invalid");
    expect(field("id_periodo_fin").getAttribute("aria-describedby")).toBe("id_periodo_fin_error");
    expect(field("id_periodo_inicio").value).toBe("2026-03-10");
    expect(document.querySelector("ul.errorlist.nonfield li")?.textContent).toBe("Error general");
  });

  it("does not draw the form for a 403", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "No tiene permiso" }, status: 403 }));
    setup(`${PREFIX}/editar/5/`);
    await waitFor(() => expect(webGet).toHaveBeenCalledWith(`${API}editar/5/`, expect.anything()));
    expect(screen.queryByRole("button", { name: "Guardar" })).toBeNull();
  });
});

describe("Delete confirmation", () => {
  it("renders the shared confirmation under the native breadcrumb", async () => {
    serve(baja());
    setup(`${PREFIX}/eliminar/5/`);
    await screen.findByText("RENDICIONCUENTAMENSUAL OBJECT (5)");
    expect(webGet).toHaveBeenCalledWith(`${API}eliminar/5/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Acciones"));
    expect(screen.getByRole("link", { name: "Seguimiento mensual" }).getAttribute("title")).toBe("Ver listado de admisiones");
    const vacio = document.querySelector('a[title="Ver ciudadano"]');
    expect(vacio?.getAttribute("href")).toBe(`${PREFIX}/detalle/5/`);
    expect(vacio?.textContent).toBe("");
    expect(screen.getByText("Eliminar").className).toContain("active");
    expect(screen.getByText("Total de registros afectados:")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe(`${PREFIX}/detalle/5/`);
  });

  it("confirms with a POST and follows the redirect to the list", async () => {
    const assign = vi.spyOn(bajaNavigation, "assign").mockImplementation(() => {});
    serve(baja());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: `${PREFIX}/7/` } });
    setup(`${PREFIX}/eliminar/5/`);
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(`${PREFIX}/7/`));
    expect(webPost.mock.calls[0][0]).toBe(`${API}eliminar/5/`);
  });
});
