import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { preinscripcionBrowser } from "./cdfPreinscripcion";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const input = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, label, required: true, kind: "input", column: "col-md-6", attrs: { type: "text", class: "textinput form-control", required: "" }, ...over,
});
const readonly = (name: string, label: string, type = "text") =>
  input(name, label, { attrs: { type, readonly: "", class: "form-control bg-secondary textinput", required: "" } });
const select = (name: string, label: string, choices: string[][], over: Record<string, unknown> = {}) => ({
  name, label, required: true, kind: "select", column: "col-md-4", attrs: { class: "select form-select", required: "" },
  choices: [{ value: "", label: "---------" }, ...choices.map(([value, l]) => ({ value, label: l }))], ...over,
});
const opciones = {
  beneficiario: [
    readonly("nombre", "Nombre"), readonly("apellido", "Apellido"), readonly("dni", "Dni", "number"), input("cuil", "Cuil", { attrs: { type: "number", class: "numberinput form-control", required: "" } }),
    select("genero", "Genero", [["F", "Femenino"], ["M", "Masculino"]], { attrs: { disabled: "", readonly: "", class: "form-control bg-secondary select form-select", required: "" } }),
    readonly("fecha_nacimiento", "Fecha nacimiento", "date"), input("domicilio", "Domicilio"),
    select("provincia", "Provincia", [["1", "Buenos Aires"]]), select("municipio", "Municipio", [], { required: false, attrs: { class: "select form-select" } }),
    select("localidad", "Localidad", [], { required: false, attrs: { class: "select form-select" } }),
    input("calle", "Calle"), select("maximo_nivel_educativo", "Maximo nivel educativo", [["Primario incompleto", "Primario incompleto"]]),
    { name: "estado_academico", label: "Estado academico", required: false, kind: "checkbox", column: "col-md-2", attrs: { type: "checkbox", class: "checkboxinput form-check-input" } },
    select("nivel_educativo_actual", "Nivel educativo actual", [["Primario", "Primario"]], { required: false, column: "col-md-5", attrs: { class: "select form-select" } }),
    { name: "actividad_preferida", label: "Actividad preferida", required: true, kind: "selectmultiple", column: "col-6", attrs: { class: "select2 selectmultiple form-select", required: "" },
      choices: [{ value: "Deportiva", label: "Deportiva" }, { value: "Educativa", label: "Educativa" }] },
    { name: "actividades_extracurriculares", label: "Actividades extracurriculares", required: false, kind: "checkbox", column: "col-3", attrs: { type: "checkbox", class: "checkboxinput form-check-input" } },
    { name: "actividades_detalle", label: "", required: false, kind: "checkboxmultiple", column: "col-3", attrs: {}, choices: [{ value: "9", label: "Fútbol" }] },
  ],
  responsable: [
    readonly("nombre", "Nombre"), readonly("apellido", "Apellido"), readonly("dni", "Dni", "number"), input("cuil", "Cuil"),
    select("genero", "Genero", [["F", "Femenino"]], { attrs: { disabled: "", class: "form-control bg-secondary select form-select", required: "" } }),
    readonly("fecha_nacimiento", "Fecha nacimiento", "date"), select("vinculo_parental", "Vinculo parental", [["Padre/Madre", "Padre/Madre"], ["Tutor/Tutora", "Tutor/Tutora"]]),
    input("calle", "Calle"), select("provincia", "Provincia", [["1", "Buenos Aires"]]),
    select("municipio", "Municipio", [], { required: false, attrs: { class: "select form-select" } }),
    select("localidad", "Localidad", [], { required: false, attrs: { class: "select form-select" } }),
  ],
  urls: { municipios: "/ajax/load-municipios/", localidades: "/ajax/load-localidades/" },
  messages: [],
};
const posible = { status: "possible", data: { nombre: "Sofía", apellido: "Pérez", genero: "F", fecha_nacimiento: "2012-03-04", domicilio: "Siempreviva 742", cuil: "20451112223",
  dni: "45111222", calle: "Siempreviva", provincia_tabla: "BA", provincia_api: "BUENOS AIRES" } };
const respExiste = { status: "exists", cantidad_beneficiarios: 1, message: "Este Responsable ya tiene 1 beneficiario a su cargo",
  data: { nombre: "Ana", apellido: "Resp", genero: "F", fecha_nacimiento: "1985-01-02", cuil: 27301112224, dni: 30111222, calle: "Vieja", provincia: 1, municipio: 5, localidad: 8 } };

let searches: Record<string, unknown>;
function serve() {
  webGet.mockImplementation((url: string) => {
    if (url === "web/session/") return Promise.resolve({ data: readyContext, status: 200 });
    if (url === "web/cdf/beneficiarios/preinscripcion/options/") return Promise.resolve({ data: opciones, status: 200 });
    if (url in searches) return Promise.resolve({ data: searches[url], status: 200 });
    return Promise.reject(new Error(url));
  });
}
const el = <T extends HTMLElement>(selector: string) => document.querySelector(selector) as T;
async function setup() {
  window.history.replaceState({}, "", "/centrodefamilia/beneficiarios/nuevo/");
  render(<App />);
  await screen.findByText("Buscar Preinscripto por CUIL");
}
async function buscarCuil(valor = "20451112223") {
  fireEvent.change(el<HTMLInputElement>("#cuil-input"), { target: { value: valor } });
  fireEvent.click(el("#buscar-btn"));
}
async function completar() {
  await buscarCuil();
  await waitFor(() => expect(el("#form-container").style.display).toBe("block"));
  fireEvent.change(el<HTMLSelectElement>("#beneficiario-form #id_provincia"), { target: { value: "1" } });
  fireEvent.change(el<HTMLSelectElement>("#beneficiario-form #id_maximo_nivel_educativo"), { target: { value: "Primario incompleto" } });
  fireEvent.mouseDown(el("#beneficiario-form .select2-selection"));
  fireEvent.click(await screen.findByRole("option", { name: "Deportiva" }));
  fireEvent.change(el<HTMLInputElement>("#dni-input"), { target: { value: "30111222" } });
  fireEvent.click(el("#femenino"));
  fireEvent.click(el("#buscar-responsable-btn"));
  await waitFor(() => expect(el("#responsable-form-container").style.display).toBe("block"));
  fireEvent.change(el<HTMLSelectElement>("#responsable-form #id_vinculo_parental"), { target: { value: "Tutor/Tutora" } });
}

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  searches = {
    "web/cdf/beneficiarios/buscar-cuil/?cuil=20451112223": posible,
    "web/cdf/beneficiarios/buscar-cuil/?cuil=20000000001": { status: "exists", message: "El CUIL ingresado ya se encuentra en el programa." },
    "web/cdf/beneficiarios/buscar-cuil/?cuil=20000000002": { status: "not_found", message: "El CUIL ingresado no se encuentra en la base de datos" },
    "web/cdf/beneficiarios/buscar-responsable/?dni=30111222&sexo=F": respExiste,
    "web/cdf/beneficiarios/buscar-responsable/?dni=99999999&sexo=M": { status: "not_found", message: "No se encontraron datos en RENAPER" },
  };
  vi.spyOn(preinscripcionBrowser, "load").mockImplementation((url: string) =>
    Promise.resolve(url.includes("municipios") ? [{ id: 5, nombre: "La Matanza" }] : [{ id: 8, nombre: "San Justo" }]));
  serve();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CDF preinscription route", () => {
  it("starts with only the CUIL search, the mask and the native texts", async () => {
    await setup();
    await waitFor(() => expect(document.title).toBe("SISOC - Preinscripto"));
    expect(screen.getByRole("heading", { name: "Formulario de Preinscripto" })).toBeTruthy();
    expect(el<HTMLInputElement>("#cuil-input").placeholder).toBe("__-________-_");
    expect(el("#form-container").style.display).toBe("none");
    expect(el("#responsable-form-container").style.display).toBe("none");
    fireEvent.change(el<HTMLInputElement>("#cuil-input"), { target: { value: "20451112223" } });
    expect(el<HTMLInputElement>("#cuil-input").value).toBe("20-45111222-3");
    const alert = vi.spyOn(preinscripcionBrowser, "alert").mockImplementation(() => undefined);
    fireEvent.change(el<HTMLInputElement>("#cuil-input"), { target: { value: "" } });
    fireEvent.click(el("#buscar-btn"));
    expect(alert).toHaveBeenCalledWith("Debe ingresar un CUIL");
  });

  it("shows the CUIL search outcomes and fills the beneficiary form", async () => {
    await setup();
    await buscarCuil("20000000001");
    await waitFor(() => expect(el("#resultado").textContent).toBe("El CUIL ingresado ya se encuentra en el programa."));
    expect(el("#resultado").className).toBe("alert alert-warning text-center");
    await buscarCuil("20000000002");
    await waitFor(() => expect(el("#resultado").className).toBe("alert alert-danger text-center"));
    expect(el("#form-container").style.display).toBe("none");
    await buscarCuil();
    await waitFor(() => expect(el("#form-container").style.display).toBe("block"));
    expect(el("#resultado").style.display).toBe("none");
    expect(el<HTMLInputElement>("#beneficiario-form #id_nombre").value).toBe("Sofía");
    expect(el<HTMLInputElement>("#beneficiario-form #id_nombre").readOnly).toBe(true);
    expect(el<HTMLSelectElement>("#beneficiario-form #id_genero").value).toBe("F");
    expect(el<HTMLInputElement>("#id_provincia_tabla").value).toBe("BA");
    expect(webGet).toHaveBeenCalledWith("web/cdf/beneficiarios/buscar-cuil/?cuil=20451112223", expect.anything());
  });

  it("toggles the academic level and the activities detail like the native script", async () => {
    await setup();
    await buscarCuil();
    await waitFor(() => expect(el("#form-container").style.display).toBe("block"));
    expect(el("#nivel-educativo-container").style.display).toBe("none");
    fireEvent.click(el("#id_estado_academico"));
    expect(el("#nivel-educativo-container").style.display).toBe("block");
    fireEvent.click(el("#id_actividades_extracurriculares"));
    expect(el("#actividades-detalle-container").style.display).toBe("block");
    fireEvent.click(el("#id_actividades_detalle_0"));
    fireEvent.click(el("#id_actividades_extracurriculares"));
    expect(el("#actividades-detalle-container").style.display).toBe("none");
    expect(el<HTMLInputElement>("#id_actividades_detalle_0").checked).toBe(false);
  });

  it("finds an existing responsable, fills it and loads its geography", async () => {
    await setup();
    await buscarCuil();
    await waitFor(() => expect(el("#form-container").style.display).toBe("block"));
    fireEvent.click(el("#buscar-responsable-btn"));
    expect(el("#resultado_responsable").textContent).toBe("Debe ingresar DNI y seleccionar sexo");
    fireEvent.change(el<HTMLInputElement>("#dni-input"), { target: { value: "30a111222999" } });
    expect(el<HTMLInputElement>("#dni-input").value).toBe("30111222");
    fireEvent.click(el("#femenino"));
    fireEvent.click(el("#buscar-responsable-btn"));
    await waitFor(() => expect(el("#responsable-form-container").style.display).toBe("block"));
    expect(el("#responsable-alert-container").textContent).toBe("Responsable encontrado: Este Responsable ya tiene 1 beneficiario a su cargo");
    expect(el<HTMLInputElement>("#responsable-form #id_dni").value).toBe("30111222");
    await waitFor(() => expect(el<HTMLSelectElement>("#responsable-form #id_localidad").value).toBe("8"));
    expect(el<HTMLSelectElement>("#responsable-form #id_municipio").value).toBe("5");
    expect(preinscripcionBrowser.load).toHaveBeenCalledWith("/ajax/load-municipios/?provincia_id=1");
    fireEvent.change(el<HTMLInputElement>("#dni-input"), { target: { value: "99999999" } });
    fireEvent.click(el("#masculino"));
    fireEvent.click(el("#buscar-responsable-btn"));
    await waitFor(() => expect(el("#resultado_responsable").textContent).toBe("No se encontraron datos en RENAPER"));
    expect(el("#responsable-form-container").style.display).toBe("none");
  });

  it("checks the required fields before posting", async () => {
    await setup();
    await buscarCuil();
    await waitFor(() => expect(el("#form-container").style.display).toBe("block"));
    fireEvent.change(el<HTMLInputElement>("#dni-input"), { target: { value: "30111222" } });
    fireEvent.click(el("#femenino"));
    fireEvent.click(el("#buscar-responsable-btn"));
    await waitFor(() => expect(el("#responsable-form-container").style.display).toBe("block"));
    fireEvent.click(el("#id_actividades_extracurriculares"));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar Preinscripción" }));
    await waitFor(() => expect(el("#beneficiario-form #id_provincia").className).toBe("select form-select is-invalid"));
    expect(el("#div_id_provincia .invalid-feedback").textContent).toBe("Este campo es requerido");
    expect(el("#responsable-form #id_vinculo_parental").className).toContain("is-invalid");
    expect(el("#actividades-detalle-container .invalid-feedback").textContent).toBe("Debe seleccionar al menos una actividad");
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.change(el<HTMLSelectElement>("#beneficiario-form #id_provincia"), { target: { value: "1" } });
    expect(el("#beneficiario-form #id_provincia").className).toBe("select form-select");
  });

  it("posts both forms once, toasts the native message and starts clean", async () => {
    webPost.mockResolvedValueOnce({ status: 200, data: { status: "success", message: "Preinscripción confirmada exitosamente", toast: "Datos cargados con éxito" } });
    await setup();
    await completar();
    fireEvent.click(screen.getByRole("button", { name: "Confirmar Preinscripción" }));
    await screen.findByText("Datos cargados con éxito");
    await waitFor(() => expect(el("#form-container").style.display).toBe("none"));
    expect(el<HTMLInputElement>("#cuil-input").value).toBe("");
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    const datos = body as FormData;
    expect(url).toBe("web/cdf/beneficiarios/preinscripcion/");
    expect(datos.get("csrfmiddlewaretoken")).toBe("synthetic-csrf-token");
    expect(datos.get("beneficiario_nombre")).toBe("Sofía");
    expect(datos.get("beneficiario_genero")).toBe("F");
    expect(datos.getAll("beneficiario_actividad_preferida")).toEqual(["Deportiva"]);
    expect(datos.get("beneficiario_estado_academico")).toBe("false");
    expect(datos.get("beneficiario_provincia_tabla")).toBe("BA");
    expect(datos.get("responsable_dni")).toBe("30111222");
    expect(datos.get("responsable_vinculo_parental")).toBe("Tutor/Tutora");
    expect(datos.get("responsable_localidad")).toBe("8");
  });

  it("alerts the native error text on a 400 and marks the field errors", async () => {
    const alert = vi.spyOn(preinscripcionBrowser, "alert").mockImplementation(() => undefined);
    webPost.mockResolvedValueOnce({ status: 400, data: { status: "error", errors: { beneficiario: { cuil: ["Ya existe Beneficiario con este Cuil."] } } } });
    await setup();
    await completar();
    fireEvent.click(screen.getByRole("button", { name: "Confirmar Preinscripción" }));
    await waitFor(() => expect(alert).toHaveBeenCalledWith("Error al enviar los datos: Error en el servidor"));
    expect(el("#beneficiario-form #div_id_cuil .invalid-feedback").textContent).toBe("Ya existe Beneficiario con este Cuil.");
    expect((screen.getByRole("button", { name: "Confirmar Preinscripción" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("shows the uncertain text on a 504 and never repeats the POST", async () => {
    webPost.mockResolvedValueOnce({ status: 504, data: { uncertain: true } });
    await setup();
    await completar();
    const boton = screen.getByRole("button", { name: "Confirmar Preinscripción" }) as HTMLButtonElement;
    fireEvent.click(boton);
    await screen.findByText("No se pudo confirmar el resultado. Verificá el estado antes de reintentar.");
    expect(boton.disabled).toBe(true);
    fireEvent.click(boton);
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("cancel reloads like the native page", async () => {
    const reload = vi.spyOn(preinscripcionBrowser, "reload").mockImplementation(() => undefined);
    await setup();
    fireEvent.click(screen.getByRole("button", { name: "Cancelar", hidden: true }));
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
