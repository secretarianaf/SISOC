import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { navigation } from "./cdfFrame";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const BASE = "web/cdf/centros/4/actividades/9/participantes/";
const PATH = "/centrodefamilia/centros/4/actividades/9/participantes/crear/";
const campo = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, label, required: true, disabled: false, widget: "text", help_text: "", value: "", attrs: {}, ...over,
});
const formulario = (over: Record<string, unknown> = {}) => ({
  query: "", ciudadanos: [], no_resultados: true,
  fields: [
    campo("nombre", "Nombre", { attrs: { maxlength: "255" } }), campo("apellido", "Apellido", { attrs: { maxlength: "255" } }),
    campo("fecha_nacimiento", "Fecha de Nacimiento", { widget: "date" }),
    campo("tipo_documento", "Tipo de Documento", { widget: "select", value: "DNI", choices: [{ value: "DNI", label: "DNI" }, { value: "CUIT", label: "CUIT" }] }),
    campo("dni", "Documento", { widget: "number" }),
    campo("genero", "Sexo", { widget: "select", choices: [{ value: "", label: "---------" }, { value: "1", label: "Mujer" }] }),
  ],
  errors: {}, non_field_errors: [], urls: { centro_list: "/centrodefamilia/centros/", actividad_list: "/centrodefamilia/centros/actividades/" },
  messages: [], ...over,
});
const borrado = () => ({
  participante: { id: 5, apellido: "Paz", nombre: "Ana", documento: "30111222" },
  urls: { centro_list: "/centrodefamilia/centros/", actividad_list: "/centrodefamilia/centros/actividades/", detail: "/centrodefamilia/centros/actividades/9/detalle/" },
  messages: [],
});
const ok = (message = "Participante agregado correctamente.") => ({ status: 200, data: { url: "/centrodefamilia/centros/actividades/9/detalle/", message, level: "success" } });

function serve(page: unknown, api = BASE) {
  webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
    : url === api ? Promise.resolve({ data: page, status: 200 }) : Promise.reject(new Error(url))));
}
function setup(path = PATH) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const field = (id: string) => document.getElementById(id) as HTMLInputElement;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CDF participant routes", () => {
  it("owns only the native create and delete paths", () => {
    expect(findRoute(PATH)?.route.name).toBe("cdf-participantes");
    expect(findRoute(PATH)?.params).toMatchObject({ centro: "4", actividad: "9" });
    expect(findRoute("/centrodefamilia/centros/4/actividades/9/participantes/5/eliminar/")?.params).toMatchObject({ id: "5" });
    expect(findRoute("/centrodefamilia/centros/4/actividades/9/lista-espera/")?.route.name).not.toBe("cdf-participantes");
    expect(findRoute("/centrodefamilia/centros/4/actividades/9/lista-espera/5/promover/")?.route.name).not.toBe("cdf-participantes");
  });

  it("renders the search card only, with the native threshold text, when there is no query", async () => {
    serve(formulario());
    setup();
    await screen.findByRole("heading", { name: "Nuevo Participante" });
    await waitFor(() => expect(document.title).toBe("SISOC - Agregar Participante"));
    expect(screen.getByPlaceholderText("Ingrese DNI (mín 4 dígitos)")).toBeTruthy();
    expect(document.querySelector("form.form-inline")?.getAttribute("method")).toBe("get");
    expect(screen.queryByText("Crear Nuevo Ciudadano")).toBeNull();
    expect(screen.queryByText("Resultados de Búsqueda")).toBeNull();
    expect(document.querySelector(".breadcrumb")?.textContent).toBe("Centro de FamiliaActividadesNuevo Participante");
  });

  it("lists the results and posts one Agregar with the citizen id and a spinner", async () => {
    serve(formulario({ query: "3011122", no_resultados: false, ciudadanos: [{ id: 7, apellido: "Paz", nombre: "Ana", documento: "30111222" }] }), `${BASE}${"?query=3011122"}`);
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue(ok());
    setup(`${PATH}?query=3011122`);
    const boton = await screen.findByRole("button", { name: "Agregar" });
    expect(screen.queryByText("Crear Nuevo Ciudadano")).toBeNull();
    fireEvent.click(boton);
    fireEvent.click(boton);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodefamilia/centros/actividades/9/detalle/"));
    expect(boton.textContent).toBe(" Agregando…");
    expect((boton as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(`${BASE}?query=3011122`);
    expect((body as FormData).get("ciudadano_id")).toBe("7");
    expect((body as FormData).get("csrfmiddlewaretoken")).toBe("synthetic-csrf-token");
  });

  it("shows the citizen form after a search without results and submits it without browser validation", async () => {
    serve(formulario({ query: "3011122" }), `${BASE}?query=3011122`);
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue(ok());
    setup(`${PATH}?query=3011122`);
    await screen.findByText("Crear Nuevo Ciudadano");
    expect(document.querySelector("label[for=id_nombre]")?.textContent).toBe("Nombre*");
    expect(field("id_fecha_nacimiento").type).toBe("date");
    expect(field("id_dni").className).toContain("numberinput");
    expect((document.getElementById("id_tipo_documento") as HTMLSelectElement).value).toBe("DNI");
    fireEvent.click(screen.getByRole("button", { name: "Crear y Asociar" }));
    await waitFor(() => expect(assign).toHaveBeenCalled());
    const body = webPost.mock.calls[0][1] as FormData;
    expect(body.get("nombre")).toBe("");
    expect(body.get("tipo_documento")).toBe("DNI");
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("shows the field and form errors of a 400, keeps the typed values and re-enables the button", async () => {
    serve(formulario({ query: "3011122" }), `${BASE}?query=3011122`);
    webPost.mockResolvedValueOnce({ status: 400, data: formulario({
      query: "3011122",
      fields: formulario().fields.map((f) => (f.name === "nombre" ? { ...f, value: "Solo" } : f)),
      errors: { apellido: [{ message: "Este campo es requerido.", code: "required" }] },
      non_field_errors: ["El ciudadano ya está inscrito o en lista de espera."],
    }) });
    setup(`${PATH}?query=3011122`);
    fireEvent.click(await screen.findByRole("button", { name: "Crear y Asociar" }));
    await waitFor(() => expect(document.getElementById("error_1_id_apellido")?.textContent).toBe("Este campo es requerido."));
    expect(field("id_apellido").className).toContain("is-invalid");
    expect(field("id_nombre").value).toBe("Solo");
    expect(document.querySelector(".alert-danger ul.errorlist.nonfield li")?.textContent).toBe("El ciudadano ya está inscrito o en lista de espera.");
    expect(document.querySelector(".alert-block.alert-danger li")?.textContent).toBe("El ciudadano ya está inscrito o en lista de espera.");
    expect((screen.getByRole("button", { name: "Crear y Asociar" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("does not repeat an uncertain enrolment", async () => {
    serve(formulario({ query: "3011122" }), `${BASE}?query=3011122`);
    webPost.mockRejectedValue(Object.assign(new Error("timeout"), { response: { status: 504 } }));
    setup(`${PATH}?query=3011122`);
    fireEvent.click(await screen.findByRole("button", { name: "Crear y Asociar" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe(
      "No se pudo confirmar el resultado. Verificá el estado antes de reintentar."));
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("renders the queued flash messages as dismissible alerts inside the page", async () => {
    serve(formulario({ messages: [{ message: "Aviso previo", level: "warning" }] }));
    setup();
    const alerta = (await screen.findAllByText("Aviso previo")).map((e) => e.closest(".alert")).find(Boolean) as HTMLElement;
    expect(alerta.className).toBe("alert alert-warning alert-dismissible fade show");
    fireEvent.click(alerta.querySelector("button.close") as HTMLElement);
    expect(document.querySelector(".alert-warning")).toBeNull();
  });

  it("confirms the baja once and goes where the native redirect says", async () => {
    serve(borrado(), `${BASE}5/eliminar/`);
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { url: "/centrodefamilia/centros/actividades/9/detalle/", message: "Participante dado de baja correctamente.", level: "success" } });
    setup("/centrodefamilia/centros/4/actividades/9/participantes/5/eliminar/");
    await screen.findByText("¿Estás seguro que querés eliminar al siguiente participante?");
    await waitFor(() => expect(document.title).toBe("SISOC - Confirmar Eliminación"));
    expect(document.querySelector("p.mb-4")?.textContent).toBe("Paz, AnaDNI: 30111222");
    expect(screen.getByRole("link", { name: /Cancelar/ }).getAttribute("href")).toBe("/centrodefamilia/centros/actividades/9/detalle/");
    expect(document.querySelector(".breadcrumb")?.textContent).toBe("Centro de FamiliaActividadesDetalle ActividadConfirmar Eliminación");
    const boton = screen.getByRole("button", { name: /Eliminar Participante/ });
    fireEvent.click(boton);
    fireEvent.click(boton);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodefamilia/centros/actividades/9/detalle/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${BASE}5/eliminar/`);
  });

  it("keeps the 404 of a missing participant", async () => {
    webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
      : Promise.resolve({ data: { detail: "x" }, status: 404 })));
    setup("/centrodefamilia/centros/4/actividades/9/participantes/5/eliminar/");
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("No se encontró la página."));
    expect(webPost).not.toHaveBeenCalled();
  });
});
