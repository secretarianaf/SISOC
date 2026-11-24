import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { centroFormularioValid } from "./vatCentrosFormulario";
import { vatNavigation } from "./vatShared";
import { vatGeography } from "./vatUbicacionesForm";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/centros-formulario/";
const N = "/vat/centros/nuevo/";
const E = "/vat/centros/7/editar/";
const s2 = { class: "form-control select2", "data-width": "100%" };
const field = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label, tag: "input", help_text: "", value: "", choices: [], errors: [], disabled: false, required: false,
  attrs: { class: "form-control", type: "text" }, ...over,
});
const sel = (name: string, label: string, first: string, rows: [string, string][], over: Record<string, unknown> = {}) => field(name, label, {
  tag: "select", required: true, attrs: { class: "form-control", required: "required" },
  choices: [{ value: "", label: first }, ...rows.map(([value, text]) => ({ value, label: text }))], ...over,
});
const geo = (name: string, label: string, rows: [string, string][], over: Record<string, unknown> = {}) => sel(name, label, `Seleccionar ${name}...`, rows, {
  attrs: { ...s2, "data-placeholder": `Seleccionar ${name}...`, required: "required" }, ...over,
});
const contacto = (over: Record<string, unknown> = {}, extra: { hidden?: unknown; errors?: unknown } = {}) => ({
  hidden: [{ name: "es_principal", value: "" }, { name: "id", value: "" }, { name: "centro", value: "" }],
  fields: [
    field("nombre_contacto", "Nombre y apellido del responsable", { value: "Ana" }), field("rol_area", "Rol / Área"),
    field("documento", "Documento", { attrs: { class: "form-control", type: "text", inputmode: "numeric", pattern: "[0-9]*", maxlength: "20", oninput: "this.value=0" } }),
    field("telefono_contacto", "Teléfono"), field("email_contacto", "Correo electrónico", { attrs: { class: "form-control", type: "email" } }),
  ],
  errors: [], ...over, ...extra,
});
const usuarios = (label: string, selected: string[] = [], errors: string[] = []) => ({
  label, choices: [{ value: "2", label: "cfp1 - Ana Gómez" }, { value: "3", label: "cfp2 - Beto Ruiz" }, { value: "4", label: "cfp3 - Ana Pérez" }], selected, errors,
  options: [{ id: "2", username: "cfp1", label: "cfp1 - Ana Gómez" }, { id: "3", username: "cfp2", label: "cfp2 - Beto Ruiz" }, { id: "4", username: "cfp3", label: "cfp3 - Ana Pérez" }],
});
const form = (over: Record<string, unknown> = {}) => ({
  editing: false, title: "Nuevo Centro de Formación Profesional",
  fields: [
    field("nombre", "Denominación de la institución", { required: true, attrs: { class: "form-control", type: "text", required: "required", maxlength: "150", placeholder: "Nombre oficial de la institución" } }),
    field("codigo", "Clave Única de Establecimiento (CUE)", { required: true, help_text: "Debe contener solo números.", attrs: { class: "form-control", type: "text", required: "required", maxlength: "9" } }),
    sel("clase_institucion", "Clase de institución", "Seleccionar clase de institución...", [["Formación Profesional", "Formación Profesional"]]),
    sel("tipo_gestion", "Tipo de gestión", "Seleccionar tipo de gestión...", [["Estatal", "Estatal"], ["Privada", "Privada"]]),
    sel("situacion", "Estado ETP", "Seleccionar estado ETP...", [["Institución de ETP", "Institución de ETP"]]),
    field("domicilio_actividad", "Dirección completa", { required: true, attrs: { class: "form-control", type: "text", required: "required" } }),
    field("calle", "Calle"), field("numero", "Altura", { attrs: { class: "form-control", type: "number" } }), field("codigo_postal", "Código Postal"),
    field("lote", "Lote"), field("manzana", "Manzana"), field("entre_calles", "Entre calles"),
    geo("provincia", "Jurisdicción", [["1", "Buenos Aires"], ["2", "Chaco"]]),
    geo("municipio", "Municipio / Partido", [["10", "La Plata"]]),
    geo("localidad", "Localidad", [["20", "Tolosa"]]),
    field("correo", "Correo electrónico institucional", { required: true, attrs: { class: "form-control", type: "email", required: "required" } }),
    field("telefono", "Teléfono institucional", { required: true, attrs: { class: "form-control", type: "text", required: "required" } }),
    field("celular", "Teléfono alternativo"), field("sitio_web", "Sitio web institucional", { attrs: { class: "form-control", type: "url" } }),
  ],
  referentes: usuarios("Referente/s"), referente: field("referente", "Referente", { attrs: { type: "hidden" }, value: "" }), revisores: usuarios("Usuario Revisor"),
  non_field_errors: [],
  contactos: { initial_forms: 0, min_num: 0, max_num: 1000, forms: [contacto()], empty: contacto({ fields: contacto().fields.map((f) => ({ ...f, value: "" })) }), non_form_errors: [] },
  activo: null, actions: { cancel: "/vat/centros/", submit: "Guardar", submit_continue: "Guardar y continuar", save_continue: true },
  urls: { municipios: "/ajax/load-municipios/", localidades: "/ajax/load-localidades/" }, messages: [], ...over,
});
const named = (data: ReturnType<typeof form>, name: string, over: Record<string, unknown>) => ({
  ...data, fields: data.fields.map((f) => (f.name === name ? { ...f, ...over } : f)),
});

function serve(data: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
}
async function open(path = N) {
  window.history.replaceState({}, "", path);
  render(<App />);
  await screen.findByRole("heading", { level: 1 });
}
const pick = (id: string, label: string) => {
  fireEvent.mouseDown(document.querySelector(`#${id} + .select2-container .select2-selection`)!);
  fireEvent.click(screen.getByRole("option", { name: label }));
};
const body = () => Object.fromEntries(webPost.mock.calls.at(-1)![1] as URLSearchParams);

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  vi.spyOn(vatGeography, "load").mockResolvedValue([]);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT centro create and edit form route", () => {
  it("owns its two paths only", () => {
    expect(findRoute(N)?.route.name).toBe("vat-centros-formulario");
    expect(findRoute(E)?.route.name).toBe("vat-centros-formulario");
    for (const other of ["/vat/centros/nuevo", "/vat/centros/x/editar/", "/vat/centros/7/", "/vat/centros/7/editar"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-centros-formulario");
    }
  });

  it("validates the payload shape", () => {
    expect(centroFormularioValid(form())).toBe(true);
    expect(centroFormularioValid({ ...form(), activo: { id: "id_activo" } })).toBe(false);
    expect(centroFormularioValid({ ...form(), urls: { municipios: "https://x.test/", localidades: "/ajax/load-localidades/" } })).toBe(false);
    expect(centroFormularioValid({ ...form(), fields: [{ name: "x" }] })).toBe(false);
  });

  it("draws the native form: panels, crispy fields, help text, select2 and the actions", async () => {
    serve(form());
    await open();
    expect(webGet).toHaveBeenCalledWith(`${API}nuevo/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nuevo Centro de Formación Profesional"));
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Datos de la institución", "Ubicación", "Contacto institucional", "Contactos adicionales"]);
    expect(document.querySelector("label[for=id_nombre] .asteriskField")?.textContent).toBe("*");
    expect(document.querySelector("#id_nombre")?.className).toBe("form-control textinput");
    expect(document.querySelector("#id_correo")?.className).toBe("form-control emailinput");
    expect(document.querySelector("#id_clase_institucion")?.className).toBe("form-control select form-select");
    expect(document.querySelector("#id_provincia")?.className).toBe("form-control select2 form-select select2-hidden-accessible");
    expect(document.querySelector("#div_id_nombre")?.parentElement?.className).toBe("col-md-8 vp-field");
    expect(screen.getByText("Debe contener solo números.")).toBeTruthy();
    expect(document.querySelector("#id_codigo")?.getAttribute("aria-describedby")).toBe("id_codigo_helptext");
    expect((document.querySelector("#id_referentes") as HTMLSelectElement).multiple).toBe(true);
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/vat/centros/");
    expect(screen.getByRole("button", { name: "Guardar" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Guardar y continuar" })).toBeTruthy();
    expect(document.querySelector("input[name=activo_present]")).toBeNull();
  });

  it("searches referentes and revisores, shows chips and removes them", async () => {
    serve(form({ referentes: usuarios("Referente/s", ["3"]) }));
    await open();
    const box = screen.getByPlaceholderText("Buscar referente por usuario o nombre");
    expect(document.querySelector("#referentes-selected-items")?.textContent).toBe("cfp2 - Beto Ruiz×");
    fireEvent.change(box, { target: { value: "ana" } });
    const results = document.querySelector("#referentes-search-results") as HTMLElement;
    expect(results.hidden).toBe(false);
    expect([...results.querySelectorAll("button")].map((b) => b.textContent)).toEqual(["cfp1 - Ana Gómez", "cfp3 - Ana Pérez"]);
    fireEvent.click(results.querySelectorAll("button")[1]);
    expect((box as HTMLInputElement).value).toBe("");
    expect(results.hidden).toBe(true);
    expect(document.querySelector("#referentes-selected-items")?.textContent).toBe("cfp2 - Beto Ruiz×cfp3 - Ana Pérez×");
    expect([...(document.querySelector("#id_referentes") as HTMLSelectElement).selectedOptions].map((o) => o.value)).toEqual(["3", "4"]);
    fireEvent.click(document.querySelector("#referentes-selected-items button[data-user-id='3']")!);
    expect(document.querySelector("#referentes-selected-items")?.textContent).toBe("cfp3 - Ana Pérez×");
    fireEvent.change(box, { target: { value: "zzz" } });
    expect(results.textContent).toBe("No hay usuarios CFP para esa busqueda.");
    fireEvent.change(screen.getByPlaceholderText("Buscar revisor por usuario o nombre"), { target: { value: "zzz" } });
    expect(document.querySelector("#revisores-search-results")?.textContent).toBe("No hay usuarios CFPRevisor para esa busqueda.");
  });

  it("closes the results 150 ms after the box loses focus", async () => {
    serve(form());
    await open();
    const box = screen.getByPlaceholderText("Buscar referente por usuario o nombre");
    fireEvent.change(box, { target: { value: "cfp" } });
    const results = document.querySelector("#referentes-search-results") as HTMLElement;
    vi.useFakeTimers();
    fireEvent.blur(box);
    expect(results.hidden).toBe(false);
    act(() => { vi.advanceTimersByTime(150); });
    expect(results.hidden).toBe(true);
    vi.useRealTimers();
  });

  it("does not post without a referente and asks for one with the native message", async () => {
    serve(form());
    await open();
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    const box = screen.getByPlaceholderText("Buscar referente por usuario o nombre") as HTMLInputElement;
    expect(box.validationMessage).toBe("Selecciona al menos un usuario valido de la lista.");
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.change(box, { target: { value: "beto" } });
    expect(box.validationMessage).toBe("");
  });

  it("reloads the municipios of a jurisdiction and leaves the localidad as it was; clearing empties both", async () => {
    serve(form());
    const load = vi.spyOn(vatGeography, "load").mockImplementation((url: string) => Promise.resolve(
      url.includes("provincia_id=2") ? [{ id: 30, nombre: "Resistencia" }] : [{ id: 21, nombre: "Los Talas" }]));
    await open();
    pick("id_localidad", "Tolosa");
    pick("id_provincia", "Chaco");
    expect(load).toHaveBeenCalledWith("/ajax/load-municipios/?provincia_id=2");
    await waitFor(() => expect(document.querySelectorAll("#id_municipio option")).toHaveLength(2));
    expect([...document.querySelectorAll("#id_municipio option")].map((o) => o.textContent)).toEqual(["Seleccionar municipio...", "Resistencia"]);
    expect((document.querySelector("#id_localidad") as HTMLSelectElement).value).toBe("20");
    pick("id_municipio", "Resistencia");
    expect(load).toHaveBeenCalledWith("/ajax/load-localidades/?municipio_id=30");
    await waitFor(() => expect([...document.querySelectorAll("#id_localidad option")].map((o) => o.textContent)).toEqual(["Seleccionar localidad...", "Los Talas"]));
    expect((document.querySelector("#id_localidad") as HTMLSelectElement).value).toBe("");
    pick("id_localidad", "Los Talas");
    fireEvent.mouseDown(document.querySelector("#id_provincia + .select2-container .select2-selection__clear")!);
    await waitFor(() => expect(document.querySelectorAll("#id_municipio option")).toHaveLength(1));
    expect(document.querySelectorAll("#id_localidad option")).toHaveLength(1);
    expect((document.querySelector("#id_localidad") as HTMLSelectElement).value).toBe("");
  });

  it("adds contacts with the script's own classes, never removes the last one and reindexes the names", async () => {
    serve(form());
    await open();
    expect(document.querySelectorAll(".contacto-form-item")).toHaveLength(1);
    expect(document.querySelector(".contacto-form-item")?.className).toBe("vp-contact-item mb-3 contacto-form-item");
    fireEvent.click(screen.getByRole("button", { name: /Quitar/ }));
    expect(document.querySelectorAll(".contacto-form-item")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: /Agregar contacto/ }));
    const items = document.querySelectorAll(".contacto-form-item");
    expect(items).toHaveLength(2);
    expect(items[1].className).toBe("border rounded p-3 mb-3 contacto-form-item");
    expect(items[1].getAttribute("data-form-index")).toBe("1");
    expect(items[1].querySelector("input[name='contactos-1-nombre_contacto']")).toBeTruthy();
    fireEvent.click(items[0].querySelector(".remove-contacto-btn")!);
    const left = document.querySelectorAll(".contacto-form-item");
    expect(left).toHaveLength(1);
    expect(left[0].querySelector("input[name='contactos-0-nombre_contacto']")).toBeTruthy();
    expect(left[0].querySelector("label[for='id_contactos-0-nombre_contacto']")).toBeTruthy();
    fireEvent.change(left[0].querySelector("#id_contactos-0-documento")!, { target: { value: "30.111-222" } });
    expect((left[0].querySelector("#id_contactos-0-documento") as HTMLInputElement).value).toBe("30111222");
  });

  it("posts the rendered fields only, then follows the native redirect", async () => {
    serve(form({ referentes: usuarios("Referente/s", ["2"]) }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/centros/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    await open();
    fireEvent.change(document.querySelector("#id_nombre")!, { target: { value: "CFP 9" } });
    fireEvent.change(document.querySelector("#id_tipo_gestion")!, { target: { value: "Estatal" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/centros/"));
    expect(webPost.mock.calls[0][0]).toBe(`${API}nuevo/`);
    expect(body()).toEqual({
      csrfmiddlewaretoken: "synthetic-csrf-token", nombre: "CFP 9", codigo: "", clase_institucion: "", tipo_gestion: "Estatal", situacion: "", referentes: "2", referente: "", domicilio_actividad: "", calle: "", numero: "", codigo_postal: "", lote: "", manzana: "", entre_calles: "", provincia: "", municipio: "", localidad: "", correo: "", telefono: "", celular: "", sitio_web: "",
      "contactos-TOTAL_FORMS": "1", "contactos-INITIAL_FORMS": "0", "contactos-MIN_NUM_FORMS": "0", "contactos-MAX_NUM_FORMS": "1000",
      "contactos-0-es_principal": "", "contactos-0-id": "", "contactos-0-centro": "", "contactos-0-nombre_contacto": "Ana", "contactos-0-rol_area": "", "contactos-0-documento": "",
      "contactos-0-telefono_contacto": "", "contactos-0-email_contacto": "",
    });
    expect(new URLSearchParams(webPost.mock.calls[0][1] as URLSearchParams).getAll("referentes")).toEqual(["2"]);
  });

  it("sends save_continue only with the continue button and posts every chosen referente", async () => {
    serve(form({ referentes: usuarios("Referente/s", ["2", "4"]) }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/centros/7/" } });
    vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    await open();
    fireEvent.click(screen.getByRole("button", { name: "Guardar y continuar" }));
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    expect((webPost.mock.calls[0][1] as URLSearchParams).getAll("referentes")).toEqual(["2", "4"]);
    expect(body().save_continue).toBe("1");
  });

  it("shows the bound form after a rejection: field errors, contact errors, alerts and the reset to the top", async () => {
    serve(form({ referentes: usuarios("Referente/s", ["2"]) }));
    const rejected = named(form({
      referentes: usuarios("Referente/s", [], ["Debe seleccionar al menos un referente."]), non_field_errors: ["Error general."],
      contactos: { initial_forms: 0, min_num: 0, max_num: 1000, non_form_errors: ["Solo puede existir un contacto principal."], empty: contacto(),
        forms: [contacto({}, { errors: [{ field: "telefono_contacto", messages: ["Teléfono inválido."] }, { field: "__all__", messages: ["Falta un canal."] }] })] },
    }), "nombre", { errors: ["Este campo es requerido."], value: "" });
    webPost.mockRejectedValueOnce({ response: { status: 400, data: named(rejected, "localidad", { errors: ["Este campo es requerido."] }) } });
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    await open();
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Error general.")).toBeTruthy();
    expect(document.querySelector("#id_nombre")?.className).toBe("form-control textinput is-invalid");
    expect(document.querySelector("#id_nombre")?.getAttribute("aria-describedby")).toBe("id_nombre_error");
    expect(document.querySelector("#id_nombre_error")?.className).toBe("invalid-feedback");
    expect(document.querySelector("#error_1_id_nombre")?.textContent).toBe("Este campo es requerido.");
    expect(document.querySelector("#id_localidad")?.className).toContain("is-invalid");
    expect(document.querySelector("#id_localidad_error")?.textContent).toBe("Este campo es requerido.");
    // the feedback comes after the select2 container, as in the native page
    expect(document.querySelector("#id_localidad")?.nextElementSibling?.className).toContain("select2-container");
    expect(document.querySelector("#id_localidad_error")?.previousElementSibling?.className).toContain("select2-container");
    expect(document.querySelector(".referente-search-error")?.textContent).toBe("Debe seleccionar al menos un referente.");
    expect(document.querySelector("#id_referentes_search")?.className).toBe("form-control is-invalid");
    expect(document.querySelector(".alert-danger .errorlist.nonfield")?.textContent).toBe("Error general.");
    expect(document.querySelector(".alert-danger .errorlist.nonform")?.textContent).toBe("Solo puede existir un contacto principal.");
    expect(document.querySelector("#id_contactos-0-telefono_contacto_error")?.textContent).toBe("Teléfono inválido.");
    expect(document.querySelector(".contacto-form-item .alert-danger.mt-2.mb-0")?.textContent).toBe("telefono_contactoTeléfono inválido.__all__Falta un canal.");
    // the native page repeats that id: the crispy feedback block and the `errorlist` of `{{ contacto_form.errors }}`
    expect([...document.querySelectorAll("[id='id_contactos-0-telefono_contacto_error']")].map((e) => `${e.tagName}.${e.className}`)).toEqual(["DIV.invalid-feedback", "UL.errorlist"]);
    expect(document.querySelector(".contacto-form-item ul.errorlist.nonfield")?.textContent).toBe("Falta un canal.");
    expect(scroll).toHaveBeenCalledWith(0, 0);
  });

  it("does not repeat a post whose outcome is unknown", async () => {
    serve(form({ referentes: usuarios("Referente/s", ["2"]) }));
    webPost.mockRejectedValue(new Error("network"));
    await open();
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("edits: stored values, hidden jurisdiction, activo switch posted with its marker, locked fields not posted, no continue", async () => {
    const edit = named(named(form({
      editing: true, title: "Editar Centro de Formación Profesional", referentes: usuarios("Referente/s", ["2"]),
      activo: { id: "id_activo", label: "Activo", checked: true, errors: [] },
      actions: { cancel: "/vat/centros/7/", submit: "Guardar", submit_continue: "Guardar y continuar", save_continue: false },
      contactos: { initial_forms: 1, min_num: 0, max_num: 1000, non_form_errors: [], empty: contacto(), forms: [contacto({}, { hidden: [{ name: "es_principal", value: "True" }, { name: "id", value: "5" }, { name: "centro", value: "7" }] })] },
    }), "provincia", { tag: "input", choices: [], attrs: { type: "hidden" }, value: "1", required: false }), "codigo", { value: "060144900", disabled: true, attrs: { class: "form-control", type: "text", maxlength: "9", disabled: "disabled" } });
    serve(edit);
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/centros/7/" } });
    vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    await open(E);
    expect(webGet).toHaveBeenCalledWith(`${API}7/editar/`, expect.anything());
    expect(screen.getByRole("heading", { level: 1, name: "Editar Centro de Formación Profesional" })).toBeTruthy();
    expect(document.querySelector("#div_id_provincia")).toBeNull();
    expect((document.querySelector("input[type=hidden][name=provincia]") as HTMLInputElement).value).toBe("1");
    expect((document.querySelector("#id_codigo") as HTMLInputElement).disabled).toBe(true);
    expect(screen.queryByRole("button", { name: "Guardar y continuar" })).toBeNull();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/vat/centros/7/");
    expect(screen.getByRole("heading", { level: 3, name: "Estado de Centro de Formación Profesional" })).toBeTruthy();
    fireEvent.click(screen.getByLabelText("Activo"));
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe(`${API}7/editar/`);
    const sent = body();
    expect(sent.activo_present).toBe("1");
    expect(sent.activo).toBeUndefined();
    expect(sent.codigo).toBeUndefined();
    expect(sent.provincia).toBe("1");
    expect(sent["contactos-INITIAL_FORMS"]).toBe("1");
    expect(sent["contactos-0-id"]).toBe("5");
    expect(sent["contactos-0-es_principal"]).toBe("True");
    expect(sent.save_continue).toBeUndefined();
  });

  it("shows the access screen when the API answers 403", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "x" }, status: 403 }));
    window.history.replaceState({}, "", N);
    render(<App />);
    expect(await screen.findByText("¡Ups! Algo salió mal.")).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 1, name: "Nuevo Centro de Formación Profesional" })).toBeNull();
  });
});
