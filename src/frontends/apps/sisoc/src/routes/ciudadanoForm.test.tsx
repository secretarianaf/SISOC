import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { ciudadanoFormNavigation, formularioValid, geografia } from "./ciudadanoForm";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

type Over = Record<string, unknown>;
const choices = (...rows: [string, string][]) => rows.map(([value, label]) => ({ value, label }));
const text = (name: string, label: string, value = "", attrs = {}, required = false) => ({ name, label, required, disabled: false, help_text: "", widget: "text", value, attrs, });
const select = (name: string, label: string, options: [string, string][], value = "", required = false, disabled = false) =>
  ({ name, label, required, disabled, help_text: "", widget: "select", value, attrs: {}, choices: choices(...options) });
const EMPTY: [string, string] = ["", "---------"];

function fields(over: Over = {}) {
  return [
    select("tipo_registro_identidad", "Tipo registro identidad", [["ESTANDAR", "Estándar"], ["SIN_DNI", "Sin DNI"], ["DNI_NO_VALIDADO_RENAPER", "DNI no validado por RENAPER"]], "ESTANDAR", true),
    select("motivo_sin_dni", "Motivo sin dni", [EMPTY, ["OTRO", "Otro"]]),
    { ...text("motivo_sin_dni_descripcion", "Motivo sin dni descripcion"), widget: "textarea", attrs: { rows: "2", cols: "40" } },
    select("motivo_no_validacion_renaper", "Motivo no validacion renaper", [EMPTY, ["OTRO", "Otro"]]),
    { ...text("motivo_no_validacion_descripcion", "Motivo no validacion descripcion"), widget: "textarea", attrs: { rows: "2", cols: "40" } },
    text("apellido", "Apellido", "", { maxlength: "255" }), text("nombre", "Nombre", "", { maxlength: "255" }),
    { ...text("fecha_nacimiento", "Fecha nacimiento"), widget: "date" },
    select("tipo_documento", "Tipo documento", [["DNI", "DNI"], ["CUIT", "CUIT"]], "DNI", true),
    { ...text("documento", "Documento"), widget: "number", attrs: { min: "0" } },
    select("sexo", "Sexo", [EMPTY, ["1", "F"]]),
    select("nacionalidad", "Nacionalidad", [EMPTY, ["1", "Argentina"]]),
    select("provincia", "Provincia", [EMPTY, ["1", "Buenos Aires"], ["2", "Córdoba"]]),
    select("municipio", "Municipio", [EMPTY]), select("localidad", "Localidad", [EMPTY]),
    text("barrio", "Barrio"), text("calle", "Calle"), text("altura", "Altura"), text("piso_departamento", "Piso departamento"), text("codigo_postal", "Codigo postal"),
    { ...text("latitud", "Latitud"), widget: "number", attrs: { step: "0.000001" } }, { ...text("longitud", "Longitud"), widget: "number", attrs: { step: "0.000001" } },
    text("telefono", "Telefono"), text("telefono_alternativo", "Telefono alternativo"), { ...text("email", "Email"), widget: "email" },
    { ...text("observaciones", "Observaciones"), widget: "textarea", attrs: { rows: "3", cols: "40" } },
    { name: "foto", label: "Foto", required: false, disabled: false, help_text: "", widget: "file", value: "", attrs: {}, current: null },
    { name: "activo", label: "Activo", required: false, disabled: false, help_text: "", widget: "checkbox", value: true, attrs: {} },
  ].map((f) => ({ ...f, ...((over[f.name] as Over | undefined) ?? {}) }));
}
const form = (over: Over = {}) => ({
  modo: "crear", fields: fields((over.campos as Over) ?? {}), errors: {}, non_field_errors: [], fecha_nacimiento_inicial: "", revision: null,
  busqueda: { dni: "", sexo: "M", sexos: choices(["M", "Masculino"], ["F", "Femenino"]) },
  urls: { volver: "/ciudadanos/listar", municipios: "/ajax/load-municipios/", localidades: "/ajax/load-localidades/", address_preview: "/ajax/ubicacion/previsualizar/" },
  messages: [], ...Object.fromEntries(Object.entries(over).filter(([k]) => k !== "campos")),
});
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
const section = (id: string) => document.getElementById(`status-${id}`)?.textContent?.trim();
const control = (id: string) => document.getElementById(id) as HTMLInputElement;

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.history.replaceState({}, "", "/ciudadanos/crear/");
  window.scrollTo = vi.fn();
  document.head.querySelectorAll("script[src*='leaflet'],script[src*='mapPinEditor']").forEach((s) => s.remove());
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("alta y edición de ciudadano", () => {
  it("owns /ciudadanos/crear/ and /ciudadanos/editar/<pk> and validates the payload", () => {
    expect(findRoute("/ciudadanos/crear/")?.route.name).toBe("ciudadano-form");
    expect(findRoute("/ciudadanos/editar/7")?.route.name).toBe("ciudadano-form");
    expect(findRoute("/ciudadanos/editar/7/")?.route.name).not.toBe("ciudadano-form");
    expect(formularioValid(form())).toBe(true);
    expect(formularioValid({ ...form(), modo: "otro" })).toBe(false);
    expect(formularioValid({ ...form(), urls: { ...form().urls, municipios: "http://evil/" } })).toBe(false);
    expect(formularioValid({ ...form(), errors: { apellido: [1] } })).toBe(false);
  });

  it("draws the alta: title, search card, five sections and the progress", async () => {
    serve(form());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Registrar ciudadano" })).toBeTruthy();
    expect(screen.getByText("Buscar Ciudadano")).toBeTruthy();
    expect(screen.getByPlaceholderText("Ingrese DNI (7-8 digitos)")).toBeTruthy();
    expect(document.querySelectorAll(".section-card").length).toBe(5);
    expect(screen.getByText("Crear ciudadano")).toBeTruthy();
    expect(screen.getAllByRole("link", { name: /Volver/ }).map((a) => a.getAttribute("href"))).toContain("/ciudadanos/listar");
    // Every section is optional in the markup; "Datos personales" already has the tipo and the tipo de documento.
    expect(["identidad", "domicilio", "contacto", "estado", "documentacion"].map(section)).toEqual(["Completo (Opcional)", "Opcional", "Opcional", "Opcional", "Opcional"]);
    expect(document.getElementById("completedSections")?.textContent).toBe("1");
    expect((document.getElementById("progressBarFill") as HTMLElement).style.width).toBe("20%");
  });

  it("draws the edición: no search card, the revision notice and the update labels", async () => {
    serve(form({ modo: "editar", busqueda: null, revision: { sin_dni: true, no_validado: false, motivo_texto: "Extraviado", descripcion_texto: "Perdió el DNI" },
      urls: { ...form().urls, volver: "/ciudadanos/ver/7" } }));
    window.history.replaceState({}, "", "/ciudadanos/editar/7");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Actualizar ciudadano" })).toBeTruthy();
    expect(screen.queryByText("Buscar Ciudadano")).toBeNull();
    expect(screen.getByText("Este ciudadano requiere revisión de identidad.")).toBeTruthy();
    expect(screen.getByText("Perdió el DNI")).toBeTruthy();
    expect(screen.getByText("Guardar cambios")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/ciudadanos/7/editar/", expect.anything());
  });

  it("forwards the dni search of the URL to the API", async () => {
    window.history.replaceState({}, "", "/ciudadanos/crear/?dni=30111222&sexo=F");
    serve(form({ busqueda: { dni: "30111222", sexo: "F", sexos: choices(["M", "Masculino"], ["F", "Femenino"]) } }));
    render(<App />);
    await screen.findByRole("heading", { name: "Registrar ciudadano" });
    expect(webGet).toHaveBeenCalledWith("web/ciudadanos/crear/?dni=30111222&sexo=F", expect.anything());
    expect(control("busqueda-dni").value).toBe("30111222");
    expect(control("busqueda-sexo").value).toBe("F");
  });

  it("shows the identity blocks of each tipo and hides the documento for Sin DNI", async () => {
    serve(form());
    render(<App />);
    await screen.findByRole("heading", { name: "Registrar ciudadano" });
    const tipo = control("id_tipo_registro_identidad");
    const display = (id: string) => (document.getElementById(id) as HTMLElement).style.display;
    expect([display("bloque-sin-dni"), display("bloque-no-validado")]).toEqual(["none", "none"]);
    fireEvent.change(tipo, { target: { value: "SIN_DNI" } });
    expect([display("bloque-sin-dni"), display("bloque-no-validado")]).toEqual(["", "none"]);
    expect((control("id_documento").closest(".form-group") as HTMLElement).style.display).toBe("none");
    fireEvent.change(tipo, { target: { value: "DNI_NO_VALIDADO_RENAPER" } });
    expect([display("bloque-sin-dni"), display("bloque-no-validado")]).toEqual(["none", ""]);
    expect((control("id_documento").closest(".form-group") as HTMLElement).style.display).toBe("");
  });

  it("updates the section badges as fields are filled; a checkbox counts only after the user changes it", async () => {
    serve(form());
    render(<App />);
    await screen.findByRole("heading", { name: "Registrar ciudadano" });
    expect(section("contacto")).toBe("Opcional");
    fireEvent.change(control("id_telefono"), { target: { value: "1155550000" } });
    expect(section("contacto")).toBe("Completo (Opcional)");
    fireEvent.change(control("id_telefono"), { target: { value: " " } });
    expect(section("contacto")).toBe("Opcional");
    expect(section("estado")).toBe("Opcional");
    // The switch starts checked, which does not count; once the user changes it, only checked counts.
    fireEvent.click(control("id_activo"));
    expect(section("estado")).toBe("Opcional");
    fireEvent.click(control("id_activo"));
    expect(section("estado")).toBe("Completo (Opcional)");
  });

  it("collapses a section with a click on its header", async () => {
    serve(form());
    render(<App />);
    await screen.findByRole("heading", { name: "Registrar ciudadano" });
    const header = document.querySelector("[data-toggle-section-ciudadano=contacto]") as HTMLElement;
    fireEvent.click(header);
    expect(document.getElementById("section-contacto")?.className).not.toContain("show");
    expect(header.className).toContain("collapsed");
    fireEvent.click(header);
    expect(document.getElementById("section-contacto")?.className).toContain("show");
  });

  it("an empty date takes the ISO date of the instance, like the template script", async () => {
    window.history.replaceState({}, "", "/ciudadanos/editar/7");
    serve(form({ modo: "editar", busqueda: null, fecha_nacimiento_inicial: "1990-05-17", campos: { fecha_nacimiento: { value: "17/05/1990" } } }));
    render(<App />);
    await screen.findByRole("heading", { name: "Actualizar ciudadano" });
    expect(control("id_fecha_nacimiento").value).toBe("1990-05-17");
  });

  it("loads the municipios of the chosen provincia (with the loader) and resets the localidad", async () => {
    serve(form());
    let resolver: (rows: unknown) => void = () => {};
    const load = vi.spyOn(geografia, "load").mockImplementation(() => new Promise((resolve) => { resolver = resolve; }));
    render(<App />);
    await screen.findByRole("heading", { name: "Registrar ciudadano" });
    fireEvent.mouseDown(document.querySelector("#provincia-field .select2-selection") as HTMLElement);
    fireEvent.click(screen.getByRole("option", { name: "Buenos Aires" }));
    expect(load).toHaveBeenCalledWith("/ajax/load-municipios/?provincia_id=1");
    expect(document.getElementById("municipio-loader")?.className).not.toContain("d-none");
    resolver([{ id: 5, nombre: "La Plata" }]);
    await waitFor(() => expect(document.getElementById("municipio-loader")?.className).toContain("d-none"));
    expect([...(control("id_municipio") as unknown as HTMLSelectElement).options].map((o) => o.textContent)).toEqual(["Seleccione un municipio", "La Plata"]);
    load.mockResolvedValueOnce([{ id: 9, nombre: "Centro" }]);
    fireEvent.mouseDown(document.querySelector("#municipio-field .select2-selection") as HTMLElement);
    fireEvent.click(screen.getByRole("option", { name: "La Plata" }));
    await waitFor(() => expect([...(control("id_localidad") as unknown as HTMLSelectElement).options].map((o) => o.textContent)).toEqual(["Seleccione una localidad", "Centro"]));
    expect(load).toHaveBeenLastCalledWith("/ajax/load-localidades/?municipio_id=5");
  });

  it("previews the chosen photo and removes it; the existing photo opens the modal", async () => {
    window.history.replaceState({}, "", "/ciudadanos/editar/7");
    serve(form({ modo: "editar", busqueda: null, campos: { foto: { current: { name: "ciudadanos/legajo.png", url: "/media/ciudadanos/legajo.png", initial_text: "Actualmente", clear_label: "Eliminar", input_text: "Modificar" } } } }));
    render(<App />);
    await screen.findByRole("heading", { name: "Actualizar ciudadano" });
    expect(screen.getByText("Foto actual:")).toBeTruthy();
    expect(screen.getByText("Cambiar foto:")).toBeTruthy();
    expect(screen.getByLabelText("Eliminar")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Ver completa/ }));
    expect(document.getElementById("fotoCiudadanoModal")?.className).toContain("show");
    expect((document.getElementById("fotoCiudadanoPrincipal") as HTMLImageElement).getAttribute("src")).toBe("/media/ciudadanos/legajo.png");
    fireEvent.click(within(document.getElementById("fotoCiudadanoModal") as HTMLElement).getAllByRole("button", { name: "Cerrar" })[0]);
    expect(document.getElementById("fotoCiudadanoModal")?.className).not.toContain("show");
    const file = new File([new Uint8Array(2048)], "legajo.png", { type: "image/png" });
    fireEvent.change(control("foto-input"), { target: { files: [file] } });
    expect(await screen.findByText("Imagen seleccionada: legajo.png")).toBeTruthy();
    expect(document.getElementById("fotoCiudadanoSize")?.textContent).toBe("2.0 KB");
    expect(section("documentacion")).toBe("Completo (Opcional)");
    fireEvent.click(document.querySelector(".btn-remover-preview") as HTMLElement);
    expect(document.getElementById("fotoCiudadanoPreviewContainer")?.className).toContain("d-none");
    expect(section("documentacion")).toBe("Opcional");
  });

  it("posts the native multipart form once and follows the redirect", async () => {
    serve(form());
    const assign = vi.spyOn(ciudadanoFormNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/ciudadanos/ver/9" }, status: 200 });
    render(<App />);
    await screen.findByRole("heading", { name: "Registrar ciudadano" });
    fireEvent.change(control("id_apellido"), { target: { value: "Nuevo" } });
    fireEvent.change(control("id_documento"), { target: { value: "30111222" } });
    const guardar = screen.getByRole("button", { name: /Crear ciudadano/ });
    fireEvent.click(guardar);
    fireEvent.click(guardar);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/ciudadanos/ver/9"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe("web/ciudadanos/crear/");
    const sent = body as FormData;
    expect(sent.get("apellido")).toBe("Nuevo");
    expect(sent.get("documento")).toBe("30111222");
    expect(sent.get("tipo_registro_identidad")).toBe("ESTANDAR");
    expect(sent.get("activo")).toBe("on");
    expect(sent.has("tipo_documento")).toBe(true);
  });

  it("the edición posts to its own endpoint without the disabled tipo de documento", async () => {
    window.history.replaceState({}, "", "/ciudadanos/editar/7");
    serve(form({ modo: "editar", busqueda: null, campos: { tipo_documento: { disabled: true } } }));
    vi.spyOn(ciudadanoFormNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/ciudadanos/ver/7" }, status: 200 });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Guardar cambios/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe("web/ciudadanos/7/editar/");
    expect((webPost.mock.calls[0][1] as FormData).has("tipo_documento")).toBe(false);
  });

  it("re-renders the bound form after a 400: errors, aria, values, back to the top", async () => {
    serve(form());
    const bound = form({ errors: { apellido: ["Este campo es obligatorio."] }, non_field_errors: ["Complete latitud y longitud, o deje ambas vacías."],
      campos: { observaciones: { value: "x" }, latitud: { value: "1" } } });
    webPost.mockResolvedValueOnce({ data: bound, status: 400 });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Crear ciudadano/ }));
    expect(await screen.findByText("Este campo es obligatorio.")).toBeTruthy();
    expect(control("id_apellido").getAttribute("aria-invalid")).toBe("true");
    expect(control("id_apellido").getAttribute("aria-describedby")).toBe("id_apellido_error");
    expect(screen.getByText("Complete latitud y longitud, o deje ambas vacías.")).toBeTruthy();
    expect(control("id_observaciones").value).toBe("x");
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
    expect(screen.getByRole("button", { name: /Crear ciudadano/ }).hasAttribute("disabled")).toBe(false);
  });

  it("reports a refusal or an unconfirmed outcome as a toast", async () => {
    serve(form());
    webPost.mockResolvedValueOnce({ data: { detail: "Sin permiso" }, status: 403 });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Crear ciudadano/ }));
    expect(await screen.findByText("Sin permiso")).toBeTruthy();
    webPost.mockRejectedValueOnce(new Error("network"));
    fireEvent.click(screen.getByRole("button", { name: /Crear ciudadano/ }));
    expect(await screen.findByText(/No se pudo guardar el ciudadano/)).toBeTruthy();
  });

  it("draws the pin editor of the shared map engine with the address fields of the form", async () => {
    serve(form());
    render(<App />);
    await screen.findByRole("heading", { name: "Registrar ciudadano" });
    expect(document.querySelector("[data-pin-editor]")?.getAttribute("data-address-fields")).toBe("id_calle,id_altura,id_provincia,id_municipio,id_localidad");
    expect(document.querySelector("[data-pin-editor]")?.getAttribute("data-search-url")).toBe("/ajax/ubicacion/previsualizar/");
  });

  it("Cancelar goes back in the history", async () => {
    serve(form());
    const back = vi.spyOn(ciudadanoFormNavigation, "back").mockImplementation(() => {});
    render(<App />);
    await screen.findByRole("heading", { name: "Registrar ciudadano" });
    fireEvent.click(screen.getAllByRole("link", { name: "Cancelar" })[0]);
    fireEvent.click(screen.getAllByRole("button", { name: /Cancelar/ })[0]);
    expect(back).toHaveBeenCalledTimes(2);
  });
});
