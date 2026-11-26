import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { navigation } from "./cdiFrame";
import { formatCuit, geography } from "./cdiFormulariosForm.behavior";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const input = (name: string, label: string, v = "") =>
  `<div id="div_id_${name}" class="mb-3"><label for="id_${name}" class="form-label">${label}</label><input type="text" name="${name}" value="${v}" class="form-control textinput" id="id_${name}"></div>`;
const select = (name: string, label: string, options: [string, string][], v = "") =>
  `<div id="div_id_${name}" class="mb-3"><label for="id_${name}" class="form-label">${label}</label><select name="${name}" class="form-select" id="id_${name}">${options.map(([o, l]) => `<option value="${o}"${o === v ? " selected" : ""}>${l}</option>`).join("")}</select></div>`;
const checks = (name: string, opts: [string, string][], on: string[] = []) =>
  `<div id="div_id_${name}" class="mb-3">${opts.map(([o, l], i) => `<div class="form-check"><input type="checkbox" name="${name}" value="${o}" id="id_${name}_${i}"${on.includes(o) ? " checked" : ""}><label for="id_${name}_${i}">${l}</label></div>`).join("")}</div>`;
const num = (name: string, v = "") => `<input type="number" name="${name}" value="${v}" id="id_${name}">`;
const prefijo = (p: string, total: number) => ["TOTAL_FORMS", "INITIAL_FORMS", "MIN_NUM_FORMS", "MAX_NUM_FORMS"].map((n) => ({ name: `${p}-${n}`, id: `id_${p}-${n}`, value: n === "TOTAL_FORMS" ? String(total) : "0" }));
const fila = (p: string, i: number, code: string, label: string, cells: string[]) => ({
  hidden: [{ name: `${p}-${i}-id`, id: `id_${p}-${i}-id`, value: "" }, { name: `${p}-${i}-codigo`, id: `id_${p}-${i}-codigo`, value: code }],
  label,
  cells: cells.map((c) => ({ html: c, errors: [] as string[] })),
});

const data = (over: Record<string, unknown> = {}) => ({
  is_edit: false,
  centro: { id: 7, nombre: "CDI Girasoles", codigo: "CDI-7", listado_url: "/centrodeinfancia/7/formularios/", cancelar_url: "/centrodeinfancia/detalle/7" },
  has_errors: false,
  non_field_errors: [] as string[],
  sections: [
    { title: "Datos generales", rows: [[{ name: "nombre_cdi", col_class: "col-md-6", html: input("nombre_cdi", "Nombre", "CDI Girasoles") }, { name: "cuit_organizacion_gestora", col_class: "col-md-6", html: input("cuit_organizacion_gestora", "CUIT", "30712345678") }]] },
    { title: "Funcionamiento", rows: [
      [{ name: "dias_funcionamiento", col_class: "col-md-6", html: checks("dias_funcionamiento", [["lunes", "Lunes"], ["martes", "Martes"]], ["lunes", "martes"]) }],
      [{ name: "tipo_jornada", col_class: "col-md-6", html: select("tipo_jornada", "Jornada", [["", "---"], ["other", "Otra"]]) },
        { name: "tipo_jornada_otra", col_class: "col-md-6", html: input("tipo_jornada_otra", "Cuál", "Mixta") }],
      [{ name: "prestaciones_alimentarias", col_class: "col-12", html: checks("prestaciones_alimentarias", [["otra", "Otra"], ["ninguna", "Ninguna"]]) }],
    ] },
    { title: "Ubicación", rows: [[{ name: "provincia_cdi", col_class: "col-md-6", html: select("provincia_cdi", "Provincia", [["", "---"], ["1", "Mendoza"]], "1") },
      { name: "departamento_cdi", col_class: "col-md-6", html: select("departamento_cdi", "Dpto", [["", "---"]]) }],
      [{ name: "municipio_cdi", col_class: "col-md-6", html: select("municipio_cdi", "Municipio", [["", "---"]]) }, { name: "localidad_cdi", col_class: "col-md-6", html: select("localidad_cdi", "Localidad", [["", "---"]]) }]] },
  ],
  horarios: [
    { dia: "lunes", etiqueta: "Lunes", apertura: input("horario_lunes_apertura", "Apertura", "08:00"), cierre: input("horario_lunes_cierre", "Cierre", "16:00") },
    { dia: "martes", etiqueta: "Martes", apertura: input("horario_martes_apertura", "Apertura"), cierre: input("horario_martes_cierre", "Cierre") },
  ],
  formsets: {
    salas: { management: prefijo("distribucion_salas", 2), non_form_errors: [] as string[], rows: [
      fila("distribucion_salas", 0, "lactantes", "Lactantes", [num("distribucion_salas-0-cantidad_salas", "2"), num("distribucion_salas-0-superficie_exclusiva_m2", "12.5"), num("distribucion_salas-0-cantidad_ninos", "10"), num("distribucion_salas-0-cantidad_personal_sala", "4")]),
      fila("distribucion_salas", 1, "dos_anos", "2 años", [num("distribucion_salas-1-cantidad_salas"), num("distribucion_salas-1-superficie_exclusiva_m2"), num("distribucion_salas-1-cantidad_ninos"), num("distribucion_salas-1-cantidad_personal_sala")]),
    ] },
    demanda: { management: prefijo("demanda", 1), non_form_errors: [] as string[], rows: [fila("demanda", 0, "lactantes", "Lactantes", [num("demanda-0-cantidad_demanda_insatisfecha", "5")])] },
    articulacion: { management: prefijo("art", 1), non_form_errors: [] as string[], rows: [fila("art", 0, "justicia", "Justicia", [num("art-0-frecuencia")])] },
  },
  urls: { departamentos: "/ajax/deptos", municipios: "/ajax/municipios", localidades: "/ajax/localidades" },
  messages: [],
  ...over,
});

function serve(payload: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: payload, status }));
}
function setup(path = "/centrodeinfancia/7/formularios/crear/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const theForm = () => screen.getByRole("button", { name: "Guardar" }).closest("form") as HTMLFormElement;
const $ = (id: string) => document.getElementById(id) as HTMLElement;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
  vi.spyOn(geography, "load").mockResolvedValue([]);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("CDI institutional form route", () => {
  it("owns only the native create and edit paths", () => {
    expect(findRoute("/centrodeinfancia/7/formularios/crear/")?.route.name).toBe("cdi-formulario-form");
    expect(findRoute("/centrodeinfancia/7/formularios/5/editar/")?.route.name).toBe("cdi-formulario-form");
    expect(findRoute("/centrodeinfancia/7/formularios/crear")?.route.name).toBe("business");
    expect(findRoute("/centrodeinfancia/7/formularios/0/editar/")?.route.name).toBe("business");
  });

  it("draws the header, the sections, the schedule card after the days row and the three formsets", async () => {
    serve(data());
    setup();
    await screen.findByText("Formulario vinculado al centro #7 (CDI-7)");
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/7/formularios/crear/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nuevo Formulario CDI"));
    expect(screen.getByRole("link", { name: "Ver formularios" }).getAttribute("href")).toBe("/centrodeinfancia/7/formularios/");
    const dias = document.querySelector("[data-field-name=dias_funcionamiento]") as HTMLElement;
    expect(dias.closest(".row")?.nextElementSibling?.id).toBe("horarios-funcionamiento-card");
    expect(document.querySelectorAll("table").length).toBe(3);
    expect($("id_distribucion_salas-TOTAL_FORMS").getAttribute("type")).toBe("hidden");
    expect(($("id_distribucion_salas-0-codigo") as HTMLInputElement).value).toBe("lactantes");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/centrodeinfancia/detalle/7");
    expect(theForm().hasAttribute("novalidate")).toBe(true);
  });

  it("shows the schedule rows of the checked days and hides the rest", async () => {
    serve(data());
    setup();
    await screen.findByText("Formulario vinculado al centro #7 (CDI-7)");
    const [lunes, martes] = Array.from(document.querySelectorAll<HTMLElement>(".formulario-horario-row"));
    // bindFormularioForm applies the row visibility in an effect; wait for it before clicking.
    await waitFor(() => expect(lunes.className).not.toContain("d-none"));
    fireEvent.click($("id_dias_funcionamiento_1"));
    await waitFor(() => expect(martes.className).toContain("d-none"));
    expect(($("id_horario_martes_apertura") as HTMLInputElement).disabled).toBe(true);
    fireEvent.click($("id_dias_funcionamiento_1"));
    expect(martes.className).not.toContain("d-none");
    expect(($("id_horario_martes_apertura") as HTMLInputElement).value).toBe("08:00");
  });

  it("applies the conditional fields and clears what no longer applies", async () => {
    serve(data());
    setup();
    await screen.findByText("Formulario vinculado al centro #7 (CDI-7)");
    const wrapper = document.querySelector("[data-field-name=tipo_jornada_otra]") as HTMLElement;
    await waitFor(() => expect(wrapper.className).toContain("d-none"));
    expect(($("id_tipo_jornada_otra") as HTMLInputElement).value).toBe("");
    fireEvent.change($("id_tipo_jornada"), { target: { value: "other" } });
    await waitFor(() => expect(wrapper.className).not.toContain("d-none"));
    fireEvent.click($("id_prestaciones_alimentarias_1"));
    await waitFor(() => expect(($("id_tipo_jornada_otra") as HTMLInputElement).disabled).toBe(false));
  });

  it("masks the CUIT and computes the room totals and ratios", async () => {
    serve(data());
    setup();
    await screen.findByText("Formulario vinculado al centro #7 (CDI-7)");
    expect(($("id_cuit_organizacion_gestora") as HTMLInputElement).value).toBe("30-71234567-8");
    expect(formatCuit("1")).toBe("1");
    expect(formatCuit("2012345678")).toBe("20-12345678");
    expect($("room-total-count").textContent).toBe("2");
    expect($("room-total-area").textContent).toBe("12.50");
    expect($("room-total-staff").textContent).toBe("4");
    expect($("room-total-ratio").textContent).toBe("2.00");
    fireEvent.input($("id_distribucion_salas-1-cantidad_salas"), { target: { value: "2" } });
    fireEvent.input($("id_distribucion_salas-1-cantidad_personal_sala"), { target: { value: "2" } });
    expect($("room-total-count").textContent).toBe("4");
    expect($("room-total-ratio").textContent).toBe("1.50");
    expect(document.querySelectorAll(".room-staff-ratio")[1].textContent).toBe("1.00");
  });

  it("loads the departments, municipalities and localities of the chosen province", async () => {
    serve(data());
    const load = vi.spyOn(geography, "load").mockImplementation(async (url) => (url.startsWith("/ajax/deptos") ? [{ id: 4, nombre: "Godoy Cruz" }] : url.startsWith("/ajax/municipios") ? [{ id: 9, nombre: "Maipú" }] : [{ id: 2, nombre: "Luzuriaga" }]));
    setup();
    await screen.findByText("Formulario vinculado al centro #7 (CDI-7)");
    await waitFor(() => expect(($("id_departamento_cdi") as HTMLSelectElement).options.length).toBe(2));
    expect(load).toHaveBeenCalledWith("/ajax/deptos?provincia_id=1");
    fireEvent.change($("id_municipio_cdi"), { target: { value: "9" } });
    await waitFor(() => expect(load).toHaveBeenCalledWith("/ajax/localidades?municipio_id=9"));
  });

  it("posts once as urlencoded without the disabled fields and follows the native redirect", async () => {
    serve(data());
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/centrodeinfancia/7/formularios/3/" }, status: 200 });
    setup();
    await screen.findByText("Formulario vinculado al centro #7 (CDI-7)");
    const form = theForm();
    fireEvent.submit(form);
    fireEvent.submit(form);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodeinfancia/7/formularios/3/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/cdi/centros/7/formularios/crear/");
    const body = webPost.mock.calls[0][1] as URLSearchParams;
    expect(body.getAll("dias_funcionamiento")).toEqual(["lunes", "martes"]);
    expect(body.get("distribucion_salas-TOTAL_FORMS")).toBe("2");
    expect(body.get("distribucion_salas-0-codigo")).toBe("lactantes");
    expect(body.has("tipo_jornada_otra")).toBe(false);
  });

  it("redraws a rejected form with the alert, the cell errors and the formset errors", async () => {
    serve(data());
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    const invalid = data({ has_errors: true, non_field_errors: ["Revise el formulario."] });
    invalid.formsets.salas.rows[0].cells[0].errors = ["Ingrese un número mayor o igual a 0."];
    invalid.formsets.salas.non_form_errors = ["Faltan filas."];
    webPost.mockResolvedValue({ data: invalid, status: 400 });
    setup();
    await screen.findByText("Formulario vinculado al centro #7 (CDI-7)");
    fireEvent.submit(theForm());
    await screen.findByText("Revise el formulario.");
    expect(screen.getByText(/No se pudo guardar el formulario/)).toBeDefined();
    expect(within(document.querySelector("tbody") as HTMLElement).getByText("Ingrese un número mayor o igual a 0.").className).toBe("invalid-feedback d-block");
    expect(screen.getByText("Faltan filas.").closest(".alert")?.className).toBe("alert alert-danger");
    expect(scroll).toHaveBeenCalledWith(0, 0);
    expect(screen.getByRole("button", { name: "Guardar" }).hasAttribute("disabled")).toBe(false);
  });

  it("announces a forbidden or uncertain result without retrying", async () => {
    serve(data());
    const alert = vi.spyOn(window, "alert").mockImplementation(() => undefined);
    webPost.mockResolvedValueOnce({ data: { detail: "El rol Auditoría tiene acceso de solo lectura." }, status: 403 });
    setup();
    await screen.findByText("Formulario vinculado al centro #7 (CDI-7)");
    fireEvent.submit(theForm());
    await waitFor(() => expect(alert).toHaveBeenCalledWith("El rol Auditoría tiene acceso de solo lectura."));
    webPost.mockRejectedValueOnce(new Error("network"));
    fireEvent.submit(theForm());
    await screen.findByRole("alert");
    expect(webPost).toHaveBeenCalledTimes(2);
  });

  it("draws the edit screen with its own endpoint and title", async () => {
    serve(data({ is_edit: true, centro: { ...data().centro, cancelar_url: "/centrodeinfancia/7/formularios/3/" } }));
    setup("/centrodeinfancia/7/formularios/3/editar/");
    await screen.findByText("Formulario vinculado al centro #7 (CDI-7)");
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/7/formularios/3/editar/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Editar Formulario CDI"));
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/centrodeinfancia/7/formularios/3/");
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
