import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { navigation } from "./cdiFrame";
import { geography } from "./cdiTrabajadoresForm.behavior";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const text = (name: string, label: string, value = "", extra = "") =>
  `<div id="div_id_${name}" class="mb-3"><label for="id_${name}" class="form-label">${label}</label><input type="text" name="${name}" value="${value}" class="form-control textinput${extra}" id="id_${name}"></div>`;
const sel = (name: string, label: string, options: [string, string][], value = "") =>
  `<div id="div_id_${name}" class="mb-3"><label for="id_${name}" class="form-label">${label}</label><select name="${name}" class="form-select" id="id_${name}">${options
    .map(([v, l]) => `<option value="${v}"${v === value ? " selected" : ""}>${l}</option>`).join("")}</select></div>`;
const opt = (id: string, value: string, label: string, checked = false) => ({ id, value, label, checked });

const NAMES = ["fecha_carga", "funcion_pfpi", "funcion_egp", "funcion_uaf", "registro_tipo", "fecha_actualizacion", "apellido", "sexo_registral", "dni", "cuit", "sin_cuil",
  "tipo_documentacion", "pais_nacimiento", "nacionalidad_trabajador", "formacion_academica", "anos_trabajo_primera_infancia", "tipo_contratacion", "carga_horaria_semanal",
  "email", "telefono", "calle_contacto", "unidad_funcional", "tipo_barrio", "pueblo_originario", "es_interprete", "recibe_apoyo_discapacidad", "numero_cud"];

const data = (over: Record<string, unknown> = {}) => ({
  is_edit: false,
  centro: { id: 7, nombre: "CDI Girasoles", url: "/centrodeinfancia/detalle/7", provincia: "Mendoza", departamento: "-", municipio: "-", localidad: "-", codigo_cdi: "CDI-7" },
  search: { query: "zzzz", ciudadanos: [], selected: null, no_resultados: true, renaper_precarga: false, renaper_prefill_token: null },
  mostrar_formulario: true,
  non_field_errors: [],
  fields: {
    ...Object.fromEntries(NAMES.map((n) => [n, text(n, n)])),
    nombre: text("nombre", "Nombre", "Ana"),
    subcomponente: sel("subcomponente", "Subcomponente", [["", "---------"], ["pfpi", "PFPI"], ["cdi", "CDI"]], "cdi"),
    funcion_cdi: sel("funcion_cdi", "Función (CDI)", [["", "---------"], ["a", "A"]], "a"),
    sala_cdi: sel("sala_cdi", "Sala", [["", "---------"], ["s", "S"]], "s"),
    fecha_nacimiento: `<div id="div_id_fecha_nacimiento" class="mb-3"><input type="date" name="fecha_nacimiento" value="1990-05-06" id="id_fecha_nacimiento"></div>`,
    nivel_educativo: sel("nivel_educativo", "Nivel", [["", "---------"], ["primario_completo", "P"], ["secundario_completo", "S"]]),
    tiene_discapacidad: sel("tiene_discapacidad", "¿Tiene?", [["", "---------"], ["si", "Sí"], ["no", "No"]]),
    tiene_cud: sel("tiene_cud", "¿CUD?", [["", "---------"], ["si", "Sí"]]),
    provincia_contacto: sel("provincia_contacto", "Provincia", [["", "---------"], ["1", "Mendoza"]]),
    departamento_contacto: sel("departamento_contacto", "Depto", [["", "---------"]]),
    municipio_contacto: sel("municipio_contacto", "Municipio", [["", "---------"]]),
    localidad_contacto: sel("localidad_contacto", "Localidad", [["", "---------"]]),
  },
  multiples: {
    capacitaciones_certificadas: { label: "Cap", options: [opt("id_capacitaciones_certificadas_0", "x", "Primeros auxilios")], errors: [] },
    grupo_pertenencia: { label: "Grupo", options: [opt("id_grupo_pertenencia_0", "indigena", "Indígena"), opt("id_grupo_pertenencia_1", "ninguno", "Ninguno")], errors: ["No combine"] },
    lenguajes: { label: "Lenguajes", options: [opt("id_lenguajes_0", "guarani", "Guaraní", true)], errors: [] },
    tipo_discapacidad: { label: "Tipo", options: [opt("id_tipo_discapacidad_0", "visual", "Visual")], errors: [] },
  },
  ciudadano_id: null,
  urls: { cancelar: "/centrodeinfancia/detalle/7", departamentos: "/ajax/deptos", municipios: "/ajax/municipios", localidades: "/ajax/localidades" },
  messages: [],
  ...over,
});

function serve(payload: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(
    url === "web/session/" ? { data: readyContext, status: 200 } : { data: payload, status },
  ));
}
function setup(path = "/centrodeinfancia/7/trabajadores/crear/?query=zzzz") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const $ = (id: string) => document.getElementById(id) as HTMLElement;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
  vi.spyOn(geography, "load").mockResolvedValue([]);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("CDI worker form route", () => {
  it("owns only the native create and edit paths", () => {
    expect(findRoute("/centrodeinfancia/7/trabajadores/crear/")?.route.name).toBe("cdi-trabajador-form");
    expect(findRoute("/centrodeinfancia/7/trabajadores/5/editar/")?.route.name).toBe("cdi-trabajador-form");
    expect(findRoute("/centrodeinfancia/7/trabajadores/crear")?.route.name).toBe("business");
    expect(findRoute("/centrodeinfancia/7/trabajadores/0/editar/")?.route.name).toBe("business");
    expect(findRoute("/centrodeinfancia/7/trabajadores/5/")?.route.name).toBe("cdi-trabajador");
  });

  it("loads the search query along with the page and draws the search, the progress and the seven cards", async () => {
    serve(data());
    setup();
    await screen.findByRole("heading", { level: 3, name: "Institución" });
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/7/trabajadores/crear/?query=zzzz", expect.anything());
    expect(screen.getByRole("heading", { level: 3, name: "Agregar trabajador" })).toBeDefined();
    expect(($("busqueda-dni") as HTMLInputElement).value).toBe("zzzz");
    expect(screen.getByText("No se encontraron coincidencias. Puede completar la ficha manualmente.")).toBeDefined();
    expect(document.querySelectorAll(".section-card").length).toBe(8);
    expect(($("cdi-codigo") as HTMLInputElement).value).toBe("CDI-7");
    expect($("completedSections").textContent).toBe("0");
    expect($("status-espacio_temporal").className).toBe("status-badge empty");
    expect(screen.getByRole("button", { name: "Agregar trabajador" })).toBeDefined();
  });

  it("shows the RENAPER prefill text, the results table and the selected citizen like the template", async () => {
    serve(data({ search: { query: "30999888", ciudadanos: [], selected: null, no_resultados: true, renaper_precarga: true, renaper_prefill_token: "tok" } }));
    setup();
    await screen.findByRole("heading", { name: "Institución" });
    expect(screen.getByText(/Se precargaron datos desde RENAPER/)).toBeDefined();
    expect((document.querySelector("input[name=renaper_prefill_token]") as HTMLInputElement).value).toBe("tok");
    cleanup();
    const c = { id: 3, apellido: "Ramírez", nombre: "Sofía", documento: "1234567" };
    serve(data({ mostrar_formulario: false, search: { query: "1234567", ciudadanos: [c], selected: null, no_resultados: false, renaper_precarga: false, renaper_prefill_token: null } }));
    setup();
    const link = await screen.findByRole("link", { name: "Completar ficha" });
    expect(link.getAttribute("href")).toBe("?query=1234567&ciudadano_id=3");
    expect(document.getElementById("trabajadorForm")).toBeNull();
    cleanup();
    serve(data({ ciudadano_id: 3, search: { query: "1234567", ciudadanos: [c], selected: c, no_resultados: false, renaper_precarga: false, renaper_prefill_token: null } }));
    setup();
    await screen.findByText("Ramírez, Sofía");
    expect(screen.queryByRole("link", { name: "Completar ficha" })).toBeNull();
    expect((document.querySelector("input[name=ciudadano_id]") as HTMLInputElement).value).toBe("3");
  });

  it("applies the native conditional rows and the age", async () => {
    serve(data());
    setup();
    await screen.findByRole("heading", { name: "Institución" }, { timeout: 4000 });
    await waitFor(() => expect($("row-funcion-pfpi").className).toContain("d-none"));
    expect($("row-funcion-cdi").className).not.toContain("d-none");
    await waitFor(() => expect(($("id_funcion_pfpi") as HTMLInputElement).disabled).toBe(true));
    fireEvent.change($("id_subcomponente"), { target: { value: "pfpi" } });
    expect($("row-funcion-pfpi").className).not.toContain("d-none");
    expect($("row-funcion-cdi").className).toContain("d-none");
    expect(($("id_funcion_cdi") as HTMLSelectElement).value).toBe("");
    expect($("row-formacion-academica").className).toContain("d-none");
    fireEvent.change($("id_nivel_educativo"), { target: { value: "secundario_completo" } });
    expect($("row-formacion-academica").className).not.toContain("d-none");
    expect($("bloque-discapacidad").className).toContain("d-none");
    fireEvent.change($("id_tiene_discapacidad"), { target: { value: "si" } });
    expect($("bloque-discapacidad").className).not.toContain("d-none");
    expect($("row-numero-cud").className).toContain("d-none");
    fireEvent.change($("id_tiene_cud"), { target: { value: "si" } });
    expect($("row-numero-cud").className).not.toContain("d-none");
    expect($("row-pueblo-originario").className).toContain("d-none");
    fireEvent.click($("id_grupo_pertenencia_0"));
    expect($("row-pueblo-originario").className).not.toContain("d-none");
    await waitFor(() => expect(($("id_edad_calculada") as HTMLInputElement).value).not.toBe(""));
  });

  it("updates the progress and the status badges while typing", async () => {
    serve(data());
    setup();
    await screen.findByRole("heading", { name: "Institución" });
    await waitFor(() => {
      fireEvent.input($("id_fecha_carga"), { target: { value: "2026-09-01" } });
      expect($("status-espacio_temporal").className).toBe("status-badge complete");
    });
    expect($("status-espacio_temporal").textContent).toContain("Completada");
    expect($("completedSections").textContent).toBe("1");
    expect($("progressBarFill").style.width).toContain("%");
    fireEvent.input($("id_email"), { target: { value: "a@b.test" } });
    expect($("status-contacto").className).toBe("status-badge complete");
    fireEvent.input($("id_calle_contacto"), { target: { value: "x" } });
    expect($("status-contacto").className).toBe("status-badge complete");
  });

  it("loads the departments and municipalities of the chosen province", async () => {
    serve(data());
    const load = vi.spyOn(geography, "load").mockImplementation(async (url) =>
      url.startsWith("/ajax/deptos") ? [{ nombre: "Godoy Cruz" }] : [{ id: 9, nombre: "Maipú" }]);
    setup();
    await screen.findByRole("heading", { name: "Institución" });
    fireEvent.change($("id_provincia_contacto"), { target: { value: "1" } });
    await waitFor(() => expect((($("id_municipio_contacto") as HTMLSelectElement).options.length)).toBe(2));
    expect(load).toHaveBeenCalledWith("/ajax/deptos?provincia_id=1");
    expect(load).toHaveBeenCalledWith("/ajax/municipios?provincia_id=1");
    expect(($("id_departamento_contacto") as HTMLSelectElement).options[1].value).toBe("Godoy Cruz");
  });

  it("collapses a card with the keyboard", async () => {
    serve(data());
    setup();
    const header = (await screen.findByRole("heading", { name: "Contacto" })).closest(".section-header") as HTMLElement;
    fireEvent.keyDown(header, { key: "Enter" });
    expect(header.getAttribute("aria-expanded")).toBe("false");
    expect($("section-contacto").className).toBe("section-body collapse");
  });

  it("posts once as urlencoded without the disabled fields and follows the native redirect", async () => {
    serve(data());
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/centrodeinfancia/detalle/7" }, status: 200 });
    setup();
    await screen.findByRole("heading", { name: "Institución" });
    // The binding effect disables the controls of the hidden function rows after the first paint.
    await waitFor(() => expect(($("id_funcion_pfpi") as HTMLInputElement).disabled).toBe(true));
    const button = screen.getByRole("button", { name: "Agregar trabajador" });
    fireEvent.click(button);
    fireEvent.click(button);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodeinfancia/detalle/7"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/cdi/centros/7/trabajadores/crear/?query=zzzz");
    const body = webPost.mock.calls[0][1] as URLSearchParams;
    expect(body.get("nombre")).toBe("Ana");
    expect(body.getAll("lenguajes")).toEqual(["guarani"]);
    expect(body.has("funcion_pfpi")).toBe(false);
  });

  it("redraws a rejected form with its errors, scrolls to the top and allows a new try", async () => {
    serve(data());
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    const invalid = data({ non_field_errors: ["Revise el formulario."], fields: { ...data().fields, nombre: text("nombre", "Nombre", "A1", " is-invalid") } });
    webPost.mockResolvedValue({ data: invalid, status: 400 });
    setup();
    await screen.findByRole("heading", { name: "Institución" });
    fireEvent.click(screen.getByRole("button", { name: "Agregar trabajador" }));
    await screen.findByText("Revise el formulario.");
    expect(($("id_nombre") as HTMLInputElement).value).toBe("A1");
    expect($("id_nombre").className).toContain("is-invalid");
    expect(scroll).toHaveBeenCalledWith(0, 0);
    expect(screen.getByRole("button", { name: "Agregar trabajador" }).hasAttribute("disabled")).toBe(false);
  });

  it("announces a forbidden or uncertain result without retrying", async () => {
    serve(data());
    const alert = vi.spyOn(window, "alert").mockImplementation(() => undefined);
    webPost.mockResolvedValueOnce({ data: { detail: "El rol Auditoría tiene acceso de solo lectura." }, status: 403 });
    setup();
    await screen.findByRole("heading", { name: "Institución" });
    fireEvent.click(screen.getByRole("button", { name: "Agregar trabajador" }));
    await waitFor(() => expect(alert).toHaveBeenCalledWith("El rol Auditoría tiene acceso de solo lectura."));
    webPost.mockRejectedValueOnce(new Error("network"));
    fireEvent.click(screen.getByRole("button", { name: "Agregar trabajador" }));
    await screen.findByRole("alert");
    expect(webPost).toHaveBeenCalledTimes(2);
  });

  it("draws the edit screen without the search and with its own endpoint and button", async () => {
    serve(data({ is_edit: true, search: null }));
    setup("/centrodeinfancia/7/trabajadores/5/editar/");
    await screen.findByRole("heading", { name: "Institución" });
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/7/trabajadores/5/editar/", expect.anything());
    expect(document.getElementById("busqueda-dni")).toBeNull();
    expect(screen.getByRole("heading", { level: 3, name: "Editar trabajador" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeDefined();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/centrodeinfancia/detalle/7");
  });

  it("shows the not found and invalid payload states", async () => {
    serve({}, 404);
    setup();
    expect((await screen.findByRole("alert")).textContent).toBe("No se encontró la página.");
    cleanup();
    serve({ is_edit: 1 });
    setup();
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar la página.");
  });
});
