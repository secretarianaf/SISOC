import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { aplicarHorarios, conPlaceholder, formatCuit, geography, opcionesDe, seleccion } from "./cdiCentroFormBehavior";
import { navigation } from "./cdiFrame";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const DIAS = [["lunes", "Lunes"], ["martes", "Martes"], ["miercoles", "Miércoles"], ["jueves", "Jueves"], ["viernes", "Viernes"], ["sabado", "Sábado"], ["domingo", "Domingo"]];
const field = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, label, required: false, disabled: false, widget: "text", help_text: "", value: "", attrs: {}, renaper: false, errors: [], choices: null, ...over,
});
const select = (name: string, label: string, choices: [string, string][], over: Record<string, unknown> = {}) =>
  field(name, label, { widget: "select", required: true, choices: choices.map(([value, text]) => ({ value, label: text })), ...over });
const AMBITO: [string, string][] = [["", "Seleccione un ámbito"], ["rural", "Rural"], ["urbano", "Urbano"]];
const empty: [string, string] = ["", "---------"];

const fields = (over: Record<string, Record<string, unknown>> = {}) => [
  field("nombre", "Nombre del CDI", { required: true, attrs: { maxlength: "255" } }),
  field("organizacion", "Denominación del organismo u organización que gestiona el CDI", { required: true }),
  field("cuit_organizacion_gestiona", "CUIT del organismo u organización que gestiona", { required: true, attrs: { inputmode: "numeric", maxlength: "13", placeholder: "20-44535030-4" } }),
  select("ambito", "Ámbito", AMBITO),
  field("telefono", "Telefono", { required: true, attrs: { inputmode: "tel", pattern: "\\d+(?:-\\d+)*" } }),
  field("mail", "Mail", { required: true, widget: "email" }),
  field("fecha_inicio", "Año de inicio de actividades del CDI", { required: true, widget: "number", attrs: { placeholder: "AAAA", min: "1900", max: "2026" } }),
  select("modalidad_gestion", "Modalidad gestion", [empty, ["gobierno_municipal", "Gobierno municipal"], ["otra", "Otra: especificar"]]),
  field("modalidad_gestion_otra", "Modalidad gestion otra"),
  select("provincia", "Provincia", [empty, ["1", "Mendoza"], ["2", "Salta"]]),
  select("departamento", "Departamento", [empty]),
  field("decil_ipi", "Decil de IPI", { disabled: true, attrs: { readonly: "True", tabindex: "-1" } }),
  select("municipio", "Municipio", [empty]),
  select("localidad", "Localidad", [empty]),
  field("codigo_postal", "Código postal", { required: true, widget: "number", attrs: { inputmode: "numeric", maxlength: "4" } }),
  field("calle", "Calle", { required: true }),
  field("numero", "Numero", { required: true, attrs: { inputmode: "numeric" } }),
  field("latitud", "Latitud", { widget: "number", attrs: { step: "0.000001" } }),
  field("longitud", "Longitud", { widget: "number", attrs: { step: "0.000001" } }),
  ...DIAS.flatMap(([dia, etiqueta]) => [
    field(`horario_${dia}_apertura`, `${etiqueta} - apertura`, { widget: "time" }),
    field(`horario_${dia}_cierre`, `${etiqueta} - cierre`, { widget: "time" }),
  ]),
  select("tipo_jornada", "Tipo jornada", [empty, ["simple_single_shift", "Jornada simple"], ["other", "Otra (especificar)"]]),
  field("tipo_jornada_otra", "Tipo jornada otra"),
  field("dni_referente", "DNI del referente", { attrs: { maxlength: "16" } }),
  field("nombre_referente", "Nombre referente", { required: true }),
  field("apellido_referente", "Apellido referente", { required: true }),
  field("cuil_referente", "CUIL del referente", { required: true }),
  field("email_referente", "Email referente", { required: true, widget: "email" }),
  field("telefono_referente", "Telefono referente", { required: true }),
].map((f) => ({ ...f, ...over[f.name as string] }));

const grupo = (label: string, options: [string, string, boolean?][], over: Record<string, unknown> = {}) => ({
  label, required: true, errors: [] as string[],
  options: options.map(([value, text, checked], i) => ({ id: `id_${label}_${i}`, value, label: text, checked: Boolean(checked) })), ...over,
});
const form = (over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}, dias: string[] = []) => ({
  is_edit: false,
  non_field_errors: [],
  fields: fields(fieldOver),
  multiples: {
    meses_funcionamiento: grupo("Meses funcionamiento", [["enero", "Enero"], ["febrero", "Febrero"]]),
    dias_funcionamiento: grupo("Dias funcionamiento", DIAS.map(([dia, etiqueta]) => [dia, etiqueta, dias.includes(dia)] as [string, string, boolean])),
    oferta_servicios: grupo("Oferta servicios", [["1", "Multiedad"]]),
  },
  dias: DIAS.map(([dia, etiqueta]) => ({ dia, etiqueta })),
  renaper: {
    bloque: "referente", url: "/centrodeinfancia/ajax/renaper/referente/", modo: "dni", campos: ["dni_referente", "apellido_referente", "nombre_referente", "cuil_referente"],
    tipo_field: "", tipos_con_dni: ["dni_permanente", "dni_temporario", "naturalizacion"], verificado: false, permite_cambiar: true, opcional: false, token: "",
  },
  urls: {
    cancelar: "/centrodeinfancia/listar", departamentos: "/centrodeinfancia/ajax/load-departamentos-ipi/", municipios: "/ajax/load-municipios/",
    localidades: "/ajax/load-localidades/", address_preview: "/ajax/ubicacion/previsualizar/",
  },
  messages: [],
  ...over,
});

function serve(data: unknown, lookup?: unknown) {
  webGet.mockImplementation((url: string) => {
    if (url === "web/session/") return Promise.resolve({ data: readyContext, status: 200 });
    if (url.startsWith("web/cdi/renaper/")) return Promise.resolve({ data: lookup, status: 200 });
    return Promise.resolve({ data, status: 200 });
  });
}
const setup = (path = "/centrodeinfancia/crear") => {
  window.history.replaceState({}, "", path);
  return render(<App />);
};
const input = (name: string) => document.getElementById(`id_${name}`) as HTMLInputElement;
const col = (name: string) => input(name).closest("[class*='col-']") as HTMLElement;
const type = (name: string, value: string) => fireEvent.change(input(name), { target: { value } });
const row = (dia: string) => document.querySelector(`.horario-row[data-dia='${dia}']`) as HTMLElement;
const block = () => document.querySelector("[data-renaper-bloque]") as HTMLElement;
const posted = () => webPost.mock.calls[0][1] as URLSearchParams;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  window.localStorage.clear();
  window.sessionStorage.clear();
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  geography.load = vi.fn(() => Promise.resolve([]));
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("CDI centre form behaviour rules", () => {
  it("masks the CUIT as NN-NNNNNNNN-N", () => {
    expect(formatCuit("20445350304")).toBe("20-44535030-4");
    expect(formatCuit("2044")).toBe("20-44");
    expect(formatCuit("20-44535030-4999")).toBe("20-44535030-4");
    expect(formatCuit("")).toBe("");
  });

  it("copies the first schedule into the empty fields of the untouched selected days and clears the unchecked ones", () => {
    const dias = ["lunes", "martes", "miercoles"];
    const horarios = { lunes: { apertura: "08:00", cierre: "12:00" }, martes: { apertura: "", cierre: "13:00" }, miercoles: { apertura: "09:00", cierre: "10:00" } };
    const result = aplicarHorarios(dias, ["lunes", "martes", "miercoles"], horarios, { miercoles: true });
    expect(result.horarios.martes).toEqual({ apertura: "08:00", cierre: "13:00" });
    expect(result.horarios.miercoles).toEqual({ apertura: "09:00", cierre: "10:00" });
    const cleared = aplicarHorarios(dias, ["lunes"], horarios, { martes: true });
    expect(cleared.horarios.martes).toEqual({ apertura: "", cierre: "" });
    expect(cleared.tocados.martes).toBe(false);
  });

  it("keeps the empty option and only the decile the AJAX rows carry", () => {
    expect(conPlaceholder([{ value: "1", label: "A" }], "Seleccione")).toEqual([{ value: "", label: "Seleccione" }, { value: "1", label: "A" }]);
    expect(conPlaceholder([{ value: "", label: "---------" }], "Seleccione")).toEqual([{ value: "", label: "---------" }]);
    expect(opcionesDe([{ id: 3, nombre: "Moreno", decil_ipi: 0 }, { id: 4, nombre_region: "Sur", decil_ipi: null }], "Seleccione")).toEqual([
      { value: "", label: "Seleccione" }, { value: "3", label: "Moreno", decil: "0" }, { value: "4", label: "Sur" },
    ]);
    expect(opcionesDe("nope", "Seleccione")).toEqual([{ value: "", label: "Seleccione" }]);
    expect(seleccion([{ value: "3", label: "x" }], "9")).toBe("");
    expect(seleccion([{ value: "3", label: "x" }], "3")).toBe("3");
  });
});

describe("CDI centre form route", () => {
  it("owns only the native create and edit paths", () => {
    expect(findRoute("/centrodeinfancia/crear")?.route.name).toBe("cdi-centro-form");
    expect(findRoute("/centrodeinfancia/editar/7")?.params).toEqual({ id: "7" });
    for (const other of ["/centrodeinfancia/crear/", "/centrodeinfancia/editar/7/", "/centrodeinfancia/editar/0", "/centrodeinfancia/editar/x", "/centrodeinfancia/detalle/7"]) {
      expect(findRoute(other)?.route.name).not.toBe("cdi-centro-form");
    }
  });

  it("draws the four section cards, the top cancel button and the title of the native page", async () => {
    serve(form());
    setup();
    await screen.findByRole("heading", { name: "Información básica" });
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/crear/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Centro de Desarrollo Infantil"));
    expect(Array.from(document.querySelectorAll(".section-title")).map((h) => h.textContent)).toEqual(["Información básica", "Ubicación", "Funcionamiento", "Referente"]);
    const top = screen.getAllByRole("link", { name: "Cancelar" })[0];
    expect(top.getAttribute("data-history-back")).toBe("true");
    const history = vi.spyOn(window.history, "back").mockImplementation(() => undefined);
    fireEvent.click(top);
    expect(history).toHaveBeenCalledTimes(1);
    expect(screen.getAllByRole("link", { name: "Cancelar" })[1].getAttribute("href")).toBe("/centrodeinfancia/listar");
    expect((document.querySelector("#centrodesarrolloinfantil-form") as HTMLFormElement).noValidate).toBe(true);
    expect(screen.getByRole("button", { name: "Guardar" })).toBeTruthy();
    expect(document.querySelector("[data-pin-editor]")?.getAttribute("data-search-url")).toBe("/ajax/ubicacion/previsualizar/");
    expect(input("decil_ipi").disabled).toBe(true);
    expect(input("decil_ipi").tabIndex).toBe(-1);
  });

  it("shows the opening hours only for the checked days", async () => {
    serve(form({}, { horario_lunes_apertura: { value: "08:00:00" }, horario_lunes_cierre: { value: "12:00:00" } }, ["lunes", "martes"]));
    setup("/centrodeinfancia/editar/7");
    await screen.findByRole("heading", { name: "Funcionamiento" });
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/7/editar/", expect.anything());
    expect(row("lunes").classList.contains("d-none")).toBe(false);
    expect(row("domingo").classList.contains("d-none")).toBe(true);
    expect(input("horario_domingo_apertura").disabled).toBe(true);
    // The first day's hours fill the empty fields of the other checked day, as the page does on load.
    expect(input("horario_martes_apertura").value).toBe("08:00:00");
    fireEvent.click(screen.getByLabelText("Miércoles"));
    expect(row("miercoles").classList.contains("d-none")).toBe(false);
    expect(input("horario_miercoles_cierre").value).toBe("12:00:00");
    fireEvent.click(screen.getByLabelText("Miércoles"));
    expect(row("miercoles").classList.contains("d-none")).toBe(true);
    expect(input("horario_miercoles_cierre").value).toBe("");
  });

  it("propagates an edit of the first day to the untouched days only", async () => {
    serve(form({}, {}, ["lunes", "martes", "jueves"]));
    setup();
    await screen.findByRole("heading", { name: "Funcionamiento" });
    type("horario_martes_apertura", "10:00");
    type("horario_lunes_apertura", "07:30");
    expect(input("horario_jueves_apertura").value).toBe("07:30");
    expect(input("horario_martes_apertura").value).toBe("10:00");
  });

  it("shows the conditional fields only for their option and clears them when hidden", async () => {
    serve(form({}, { tipo_jornada: { value: "other" }, tipo_jornada_otra: { value: "Rotativa" }, modalidad_gestion: { value: "otra" }, modalidad_gestion_otra: { value: "Mixta" } }));
    setup();
    await screen.findByRole("heading", { name: "Funcionamiento" });
    expect(col("tipo_jornada_otra").classList.contains("d-none")).toBe(false);
    expect(input("tipo_jornada_otra").value).toBe("Rotativa");
    fireEvent.change(input("tipo_jornada"), { target: { value: "simple_single_shift" } });
    expect(col("tipo_jornada_otra").classList.contains("d-none")).toBe(true);
    expect(input("tipo_jornada_otra").disabled).toBe(true);
    expect(input("tipo_jornada_otra").value).toBe("");
    fireEvent.change(input("modalidad_gestion"), { target: { value: "gobierno_municipal" } });
    expect(col("modalidad_gestion_otra").classList.contains("d-none")).toBe(true);
    expect(input("modalidad_gestion_otra").value).toBe("");
  });

  it("formats the CUIT while typing", async () => {
    serve(form());
    setup();
    await screen.findByLabelText(/CUIT del organismo/);
    type("cuit_organizacion_gestiona", "20445350304");
    expect(input("cuit_organizacion_gestiona").value).toBe("20-44535030-4");
  });

  it("reloads departamento and municipio when the province changes and takes the decile from the AJAX row", async () => {
    serve(form());
    geography.load = vi.fn((url: string) => Promise.resolve(
      url.includes("departamentos") ? [{ id: 31, nombre: "Capital", decil_ipi: 4 }] : url.includes("municipios") ? [{ id: 41, nombre: "Godoy Cruz" }] : [{ id: 51, nombre: "Villa" }]));
    setup();
    await screen.findByLabelText(/Provincia/);
    fireEvent.change(input("provincia"), { target: { value: "1" } });
    await waitFor(() => expect(within(input("departamento")).getByRole("option", { name: "Capital" })).toBeTruthy());
    expect(geography.load).toHaveBeenCalledWith("/centrodeinfancia/ajax/load-departamentos-ipi/?provincia_id=1");
    await waitFor(() => expect(within(input("municipio")).getByRole("option", { name: "Godoy Cruz" })).toBeTruthy());
    expect(within(input("departamento")).getByRole("option", { name: "Seleccione un departamento" })).toBeTruthy();
    fireEvent.change(input("departamento"), { target: { value: "31" } });
    expect(input("decil_ipi").value).toBe("4");
    fireEvent.change(input("municipio"), { target: { value: "41" } });
    await waitFor(() => expect(within(input("localidad")).getByRole("option", { name: "Villa" })).toBeTruthy());
    expect(geography.load).toHaveBeenCalledWith("/ajax/load-localidades/?municipio_id=41");
    fireEvent.change(input("provincia"), { target: { value: "" } });
    await waitFor(() => expect(within(input("departamento")).queryByRole("option", { name: "Capital" })).toBeNull());
    expect(input("decil_ipi").value).toBe("");
  });

  it("loads the lists the server left empty for a saved province", async () => {
    serve(form({}, { provincia: { value: "1" }, departamento: { value: "31" }, municipio: { value: "41" }, localidad: { value: "51" } }));
    geography.load = vi.fn((url: string) => Promise.resolve(
      url.includes("departamentos") ? [{ id: 31, nombre: "Capital", decil_ipi: 4 }] : url.includes("municipios") ? [{ id: 41, nombre: "Godoy Cruz" }] : [{ id: 51, nombre: "Villa" }]));
    setup("/centrodeinfancia/editar/7");
    await waitFor(() => expect(input("localidad").value).toBe("51"));
    expect(input("departamento").value).toBe("31");
    expect(input("municipio").value).toBe("41");
    expect(input("decil_ipi").value).toBe("4");
  });
});

describe("CDI centre form referente block", () => {
  it("starts asking only for the DNI and validates a lookup through the native RENAPER view", async () => {
    serve(form(), { success: true, message: "ok", valores: { dni_referente: "30111222", nombre_referente: "Rita", apellido_referente: "Verificada", cuil_referente: "20445350304" }, token: "signed-token" });
    setup();
    await screen.findByLabelText(/DNI del referente/);
    expect(block().dataset.renaperModo).toBe("dni");
    for (const name of ["nombre_referente", "apellido_referente", "cuil_referente", "email_referente", "telefono_referente"]) expect(col(name).hidden).toBe(true);
    expect(col("dni_referente").hidden).toBe(false);
    type("dni_referente", "30.111.222");
    fireEvent.click(screen.getAllByRole("button", { name: "Validar con RENAPER" })[0]);
    await waitFor(() => expect(block().dataset.renaperModo).toBe("verificado"));
    expect(webGet).toHaveBeenCalledWith("web/cdi/renaper/referente/", expect.objectContaining({ params: { dni: "30111222" } }));
    expect(input("nombre_referente").value).toBe("Rita");
    expect(input("nombre_referente").readOnly).toBe(true);
    expect(col("email_referente").hidden).toBe(false);
    expect((block().querySelector("input[name='renaper_token_referente']") as HTMLInputElement).value).toBe("signed-token");
  });

  it("opens verified and locked on the server data and keeps the locked fields out of the post", async () => {
    const locked = { disabled: true, renaper: true };
    serve(form({ is_edit: true, renaper: { ...form().renaper, modo: "verificado", verificado: true } }, {
      dni_referente: { value: "30111222", ...locked }, nombre_referente: { value: "Rita", ...locked }, apellido_referente: { value: "Verificada", ...locked },
      cuil_referente: { value: "20445350304", ...locked }, email_referente: { value: "rita@cdi.test" },
    }));
    vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    setup("/centrodeinfancia/editar/7");
    await screen.findByLabelText(/Email referente/);
    expect(block().dataset.renaperModo).toBe("verificado");
    expect(input("dni_referente").disabled).toBe(true);
    expect(screen.getByText("Verificado por RENAPER")).toBeTruthy();
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/centrodeinfancia/detalle/7" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    expect(posted().has("dni_referente")).toBe(false);
    expect(posted().get("email_referente")).toBe("rita@cdi.test");
    expect(posted().has("renaper_token_referente")).toBe(true);
  });
});

describe("CDI centre form submit", () => {
  it("posts what the native form posts, once, and goes where the server says", async () => {
    serve(form({}, { nombre: { value: "PULGARCITO" }, provincia: { value: "1" } }, ["lunes"]));
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/centrodeinfancia/detalle/9" } });
    setup();
    await screen.findByLabelText(/Nombre del CDI/);
    fireEvent.click(screen.getByLabelText("Enero"));
    fireEvent.click(screen.getByLabelText("Multiedad"));
    type("horario_lunes_apertura", "08:00");
    type("horario_lunes_cierre", "12:00");
    const button = screen.getByRole("button", { name: "Guardar" });
    fireEvent.click(button);
    fireEvent.click(button);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodeinfancia/detalle/9"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/cdi/centros/crear/");
    const body = posted();
    expect(body.get("nombre")).toBe("PULGARCITO");
    expect(body.get("provincia")).toBe("1");
    expect(body.getAll("meses_funcionamiento")).toEqual(["enero"]);
    expect(body.getAll("dias_funcionamiento")).toEqual(["lunes"]);
    expect(body.getAll("oferta_servicios")).toEqual(["1"]);
    expect(body.get("horario_lunes_apertura")).toBe("08:00");
    // Disabled controls (the decile, the hours of an unchecked day, the hidden "otra" fields) are not sent.
    for (const name of ["decil_ipi", "horario_martes_apertura", "tipo_jornada_otra", "modalidad_gestion_otra"]) expect(body.has(name)).toBe(false);
    expect(body.has("latitud")).toBe(true);
    expect(body.has("csrfmiddlewaretoken")).toBe(false);
  });

  it("shows the errors of a rejected save where the native page does and keeps what was typed", async () => {
    serve(form());
    const rejected = form({ non_field_errors: ["Ya existe el CDI “X”."], messages: [{ message: "Revisá los datos.", level: "warning" }] }, {
      nombre: { value: "", errors: [{ message: "Este campo es obligatorio.", code: "required" }] }, organizacion: { value: "Mi org" },
    });
    rejected.multiples.meses_funcionamiento.errors = ["Este campo es obligatorio."];
    webPost.mockResolvedValue({ status: 400, data: rejected });
    setup();
    await screen.findByLabelText(/Nombre del CDI/);
    type("organizacion", "Mi org");
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await screen.findByText("No se pudo guardar el legajo. Revisá los campos marcados.", { exact: false });
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
    expect(screen.getByText("Ya existe el CDI “X”.")).toBeTruthy();
    expect(input("nombre").classList.contains("is-invalid")).toBe(true);
    expect(input("nombre").getAttribute("aria-describedby")).toBe("id_nombre_error");
    expect(document.getElementById("error_1_id_nombre")?.textContent).toBe("Este campo es obligatorio.");
    expect(input("organizacion").value).toBe("Mi org");
    const meses = document.getElementById("div_id_meses_funcionamiento") as HTMLElement;
    expect(meses.querySelector("fieldset")?.getAttribute("aria-describedby")).toBe("id_meses_funcionamiento_error");
    expect(meses.querySelectorAll("input.is-invalid")).toHaveLength(2);
    expect(meses.querySelector(".form-check:last-child #id_meses_funcionamiento_error")).toBeTruthy();
    await waitFor(() => expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "center" }));
    expect(await screen.findByText("Revisá los datos.")).toBeTruthy();
  });

  it("reports an unconfirmed result without sending again and refuses with the native message", async () => {
    serve(form());
    webPost.mockRejectedValueOnce(new Error("network"));
    setup();
    await screen.findByLabelText(/Nombre del CDI/);
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect((await screen.findByRole("alert", { name: "" })).textContent).toContain("No se pudo confirmar el resultado.");
    expect(webPost).toHaveBeenCalledTimes(1);

    const alert = vi.spyOn(window, "alert").mockImplementation(() => undefined);
    webPost.mockResolvedValueOnce({ status: 403, data: { detail: "El rol Auditoría tiene acceso de solo lectura." } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(alert).toHaveBeenCalledWith("El rol Auditoría tiene acceso de solo lectura."));
  });

  it("shows the access page when the gate asks for a requirement", async () => {
    serve(form());
    webPost.mockResolvedValue({ status: 403, data: { state: "password_change_required", required_action_url: "/mi-cuenta/cambiar-password/" } });
    setup();
    await screen.findByLabelText(/Nombre del CDI/);
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Guardar" })); });
    await waitFor(() => expect(document.querySelector("#centrodesarrolloinfantil-form")).toBeNull());
  });

  it("explains a page that cannot load", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { nope: true }, status: 200 }));
    setup();
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar la página.");
  });
});
