import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { geography } from "./dispositivoForm";
import { navigation } from "./cdfFrame";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const empty = { value: "", label: "---------" };
const field = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, label, required: false, help_text: "", attrs: {}, errors: [], widget: "text", value: "", ...over,
});
const select = (name: string, label: string, choices: [string, string][], over: Record<string, unknown> = {}) =>
  field(name, label, { widget: "select", choices: [empty, ...choices.map(([value, text]) => ({ value, label: text }))], ...over });
const SI_NO: [string, string][] = [["si", "Sí"], ["no", "No"]];

const fields = (over: Record<string, Record<string, unknown>> = {}) => [
  field("nombre_institucion", "Nombre completo de la institución", { required: true, attrs: { maxlength: "255" } }),
  select("tipo_gestion", "Tipo de gestión del dispositivo", [["estatal", "Estatal"], ["otra", "Otra"]], { required: true, help_text: "Refiere al tipo de institución." }),
  field("tipo_gestion_otra", "Tipo gestión otra"),
  field("razon_social", "Razón social"),
  field("cuit_institucion", "CUIT de la institución", { required: true, attrs: { maxlength: "11", inputmode: "numeric", pattern: "\\d{11}" }, help_text: "Debe ingresar los 11 dígitos sin puntos ni guiones" }),
  field("calle", "Calle", { required: true }),
  field("altura", "Altura", { required: true }),
  select("provincia", "Provincia", [["1", "Buenos Aires"], ["2", "Cordoba"]], { required: true }),
  select("municipio", "Municipio", [], { required: true }),
  select("localidad", "Localidad", []),
  field("latitud", "Latitud", { widget: "number", attrs: { step: "0.000001" } }),
  field("longitud", "Longitud", { widget: "number", attrs: { step: "0.000001" } }),
  field("telefono_prefijo", "Prefijo", { required: true, attrs: { inputmode: "numeric", maxlength: "10" } }),
  field("telefono_numero", "Teléfono", { required: true }),
  field("correo_electronico", "Correo electrónico", { widget: "email" }),
  field("responsable_nombre_completo", "Nombre completo del responsable del dispositivo", { required: true }),
  field("responsable_dni", "DNI del responsable del dispositivo", { required: true }),
  select("tipo_dispositivo", "Tipo de dispositivo", [["refugio", "Refugio"], ["otro", "Otro"]], { required: true }),
  field("tipo_dispositivo_otro", "Tipo dispositivo otro"),
  select("modalidad_funcionamiento", "Modalidad de funcionamiento", [["permanente", "Permanente"]], { required: true }),
  select("capacidad_total_plazas", "Capacidad total de plazas", [["0_15", "0 a 15 plazas"]], { required: true }),
  field("poblacion_destinataria_otro", "Poblacion otro"),
  select("tiempo_permanencia_promedio", "Tiempo promedio de permanencia", [["otro", "Otro"]]),
  field("tiempo_permanencia_otro", "Tiempo otro"),
  field("modalidad_ingreso_otro", "Modalidad ingreso otro"),
  field("documentacion_ingreso_otro", "Documentacion ingreso otro"),
  field("requisitos_ingreso_otro", "Requisitos otro"),
  field("servicios_brindados_otro", "Servicios otro"),
  select("ofrece_actividades_formativas", "Ofrece actividades formativas", SI_NO),
  field("tipos_actividades_formativas_otro", "Actividades otro"),
  select("actividades_certificacion_oficial", "Certificación oficial", SI_NO),
  select("registra_informacion_personas", "Registra información", SI_NO),
  select("modo_registro", "Modo de registro", [["otro", "Otro"]]),
  field("modo_registro_otro", "Modo registro otro"),
  field("tipo_informacion_registrada_otro", "Info otro"),
  field("infraestructura_disponible_otro", "Infra otro"),
  field("infraestructura_accesibilidad_otro", "Accesibilidad otro"),
  field("principales_limitaciones", "Principales limitaciones", { widget: "textarea" }),
  field("necesidades_prioritarias", "Necesidades prioritarias", { widget: "textarea" }),
  field("articulaciones_institucionales_otro", "Articulaciones otro"),
  field("observaciones_adicionales", "Observaciones adicionales", { widget: "textarea", help_text: "Puede utilizar este espacio." }),
].map((f) => ({ ...f, ...over[f.name as string] }));

const MULTIPLES = ["dias_atencion", "horarios_funcionamiento", "poblacion_destinataria", "franja_etaria_destinataria", "modalidad_ingreso", "documentacion_ingreso",
  "requisitos_ingreso", "servicios_brindados", "tipos_actividades_formativas", "tipo_informacion_registrada", "infraestructura_disponible", "infraestructura_accesibilidad",
  "articulaciones_institucionales"];
const multiples = (checked: Record<string, string[]> = {}) => Object.fromEntries(MULTIPLES.map((name) => [name, {
  name, label: `Grupo ${name}`, required: false, help_text: "", errors: [],
  options: [["uno", "Uno"], ["otro", "Otro"]].map(([value, label], i) => ({ id: `id_${name}_${i}`, value, label, checked: (checked[name] ?? []).includes(value) })),
}]));
const slot = (name: string, saved: unknown = null) => ({ name, accept: ".pdf,.jpg,.jpeg,.png", saved });
const archivos = (saved: Record<string, unknown> = {}) => ["documentacion_dispositivo", "documentacion_dispositivo_adicional_1", "documentacion_dispositivo_adicional_2",
  "documentacion_dispositivo_adicional_3", "documentacion_dispositivo_adicional_4"].map((name) => slot(name, saved[name] ?? null));

const form = (over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}, rest: { checked?: Record<string, string[]>; saved?: Record<string, unknown> } = {}) => ({
  is_edit: false, has_errors: false, fields: fields(fieldOver), multiples: multiples(rest.checked), files: archivos(rest.saved),
  breadcrumb: [{ text: "Dispositivos", url: "/dispositivos/" }, { text: "Nuevo dispositivo", url: null }],
  urls: { listar: "/dispositivos/", municipios: "/ajax/load-municipios/", localidades: "/ajax/load-localidades/", address_preview: "/dispositivos/ubicacion/previsualizar/", saved_location: "" },
  messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => {
    if (url === "web/session/") return Promise.resolve({ data: readyContext, status: 200 });
    return Promise.resolve({ data, status });
  });
}
const setup = (path = "/dispositivos/crear") => {
  window.history.replaceState({}, "", path);
  return render(<App />);
};
const input = (name: string) => document.getElementById(`id_${name}`) as HTMLInputElement;
const type = (name: string, value: string) => fireEvent.change(input(name), { target: { value } });
const wrapper = (name: string) => document.getElementById(`wrapper-${name}`) as HTMLElement;
const posted = () => webPost.mock.calls[0][1] as FormData;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  window.scrollTo = vi.fn();
  geography.load = vi.fn(() => Promise.resolve([]));
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("Dispositivos form", () => {
  it("owns only the native create and edit paths, with no trailing slash", () => {
    expect(findRoute("/dispositivos/crear")?.route.name).toBe("dispositivo-form");
    expect(findRoute("/dispositivos/7/editar")?.params).toEqual({ id: "7" });
    for (const other of ["/dispositivos/crear/", "/dispositivos/07/editar", "/dispositivos/7/editar/", "/dispositivos/7/eliminar", "/dispositivos/7/ubicacion/"]) {
      expect(findRoute(other)?.route.name).not.toBe("dispositivo-form");
    }
  });

  it("loads the form from the matching endpoint and draws the nine sections with the progress", async () => {
    serve(form());
    setup();
    await screen.findByRole("heading", { name: "Identificación del dispositivo" });
    expect(webGet).toHaveBeenCalledWith("web/dispositivos/crear/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nuevo dispositivo"));
    expect(document.querySelectorAll(".section-card")).toHaveLength(9);
    expect(screen.getByText("Progreso del Formulario")).toBeTruthy();
    expect(document.getElementById("completedSections")?.textContent).toBe("0");
    expect(document.getElementById("status-identificacion")?.textContent).toBe(" Sin completar");
    expect(document.querySelector("label[for='id_nombre_institucion'] .asteriskField")).toBeTruthy();
    expect(input("cuit_institucion").getAttribute("maxlength")).toBe("11");
    expect(document.getElementById("id_cuit_institucion_helptext")?.textContent).toBe("Debe ingresar los 11 dígitos sin puntos ni guiones");
    expect(screen.getByRole("button", { name: "Guardar dispositivo" })).toBeTruthy();
  });

  it("loads the edit form of the device and shows the saved documents", async () => {
    serve(form({ is_edit: true, urls: { ...form().urls, saved_location: "/dispositivos/7/ubicacion/" } }, { nombre_institucion: { value: "Hogar" } },
      { saved: { documentacion_dispositivo: { full_name: "dispositivos/documentacion/x.pdf", label: "x.pdf", url: "/media/x.pdf", pdf: true } } }));
    setup("/dispositivos/7/editar");
    await screen.findByRole("heading", { name: "Identificación del dispositivo" });
    expect(webGet).toHaveBeenCalledWith("web/dispositivos/7/editar/", expect.anything());
    expect(input("nombre_institucion").value).toBe("Hogar");
    expect(document.querySelector(".doc-file-name")?.textContent).toBe("x.pdf");
    expect(document.querySelector(".btn-subir-doc")?.textContent).toContain("Cambiar");
    expect(document.querySelector("[data-pin-editor]")?.getAttribute("data-location-url")).toBe("/dispositivos/7/ubicacion/");
  });

  it("collapses a section from its header with the mouse and the keyboard", async () => {
    serve(form());
    setup();
    const header = (await screen.findByRole("heading", { name: "Servicios brindados" })).closest(".section-header") as HTMLElement;
    const body = document.getElementById("section-servicios") as HTMLElement;
    expect(header.getAttribute("aria-expanded")).toBe("true");
    fireEvent.click(header);
    expect(header.getAttribute("aria-expanded")).toBe("false");
    expect(body.classList.contains("show")).toBe(false);
    fireEvent.keyDown(header, { key: "Enter" });
    expect(body.classList.contains("show")).toBe(true);
    fireEvent.keyDown(header, { key: " " });
    expect(header.getAttribute("aria-expanded")).toBe("false");
  });

  it("completes a section as its fields are filled and counts the completed ones", async () => {
    serve(form());
    setup();
    await screen.findByRole("heading", { name: "Identificación del dispositivo" });
    type("nombre_institucion", "Hogar");
    await waitFor(() => expect(document.getElementById("status-identificacion")?.textContent).toBe(" Incompleta"));
    type("tipo_gestion", "estatal");
    fireEvent.change(input("provincia"), { target: { value: "1" } });
    await waitFor(() => expect(document.getElementById("status-identificacion")?.textContent).toBe(" Completada"));
    expect(document.getElementById("completedSections")?.textContent).toBe("1");
    expect(document.getElementById("progressBarFill")?.style.width).toBe(`${(1 / 9) * 100}%`);
  });

  it("shows the 'otro' fields only for their trigger and clears the text when it stops showing", async () => {
    serve(form());
    setup();
    await screen.findByRole("heading", { name: "Identificación del dispositivo" });
    expect(wrapper("tipo_gestion_otra").classList.contains("d-none")).toBe(true);
    type("tipo_gestion", "otra");
    await waitFor(() => expect(wrapper("tipo_gestion_otra").classList.contains("d-none")).toBe(false));
    type("tipo_gestion_otra", "Cooperativa");
    type("tipo_gestion", "estatal");
    await waitFor(() => expect(wrapper("tipo_gestion_otra").classList.contains("d-none")).toBe(true));
    expect(input("tipo_gestion_otra").value).toBe("");

    expect(wrapper("modalidad_ingreso_otro").classList.contains("d-none")).toBe(true);
    fireEvent.click(document.getElementById("id_modalidad_ingreso_1") as HTMLInputElement);
    await waitFor(() => expect(wrapper("modalidad_ingreso_otro").classList.contains("d-none")).toBe(false));
    type("modalidad_ingreso_otro", "Por red");
    fireEvent.click(document.getElementById("id_modalidad_ingreso_1") as HTMLInputElement);
    await waitFor(() => expect(wrapper("modalidad_ingreso_otro").classList.contains("d-none")).toBe(true));
    expect(input("modalidad_ingreso_otro").value).toBe("");

    expect(document.getElementById("actividades-detalle")?.classList.contains("d-none")).toBe(true);
    type("ofrece_actividades_formativas", "si");
    await waitFor(() => expect(document.getElementById("actividades-detalle")?.classList.contains("d-none")).toBe(false));
    type("registra_informacion_personas", "si");
    await waitFor(() => expect(document.getElementById("registro-detalle")?.classList.contains("d-none")).toBe(false));
  });

  it("starts with the 'otro' fields the server drew as visible", async () => {
    serve(form({}, { tipo_dispositivo: { value: "otro" } }, { checked: { poblacion_destinataria: ["otro"] } }));
    setup();
    await screen.findByRole("heading", { name: "Identificación del dispositivo" });
    expect(wrapper("tipo_dispositivo_otro").classList.contains("d-none")).toBe(false);
    expect(wrapper("poblacion_destinataria_otro").classList.contains("d-none")).toBe(false);
  });

  it("keeps only digits in the numeric inputs", async () => {
    serve(form());
    setup();
    await screen.findByRole("heading", { name: "Identificación del dispositivo" });
    fireEvent.input(input("cuit_institucion"), { target: { value: "20-12a" } });
    expect(input("cuit_institucion").value).toBe("2012");
  });

  it("marks a required field valid or invalid when it loses the focus", async () => {
    serve(form());
    setup();
    await screen.findByRole("heading", { name: "Identificación del dispositivo" });
    const col = input("nombre_institucion").closest(".col-md-4") as HTMLElement;
    fireEvent.blur(input("nombre_institucion"));
    expect(col.classList.contains("invalid")).toBe(true);
    type("nombre_institucion", "Hogar");
    fireEvent.input(input("nombre_institucion"), { target: { value: "Hogar" } });
    expect(col.classList.contains("valid")).toBe(true);
    expect(col.classList.contains("invalid")).toBe(false);
  });

  it("reloads the municipios of a province and clears the dependent lists", async () => {
    serve(form({}, { localidad: { choices: [empty, { value: "9", label: "Tolosa" }] } }));
    geography.load = vi.fn(() => Promise.resolve([{ id: 5, nombre: "La Plata" }]));
    setup();
    await screen.findByRole("heading", { name: "Identificación del dispositivo" });
    fireEvent.change(input("provincia"), { target: { value: "1" } });
    await waitFor(() => expect(Array.from(input("municipio").querySelectorAll("option")).map((o) => o.textContent)).toEqual(["---------", "La Plata"]));
    expect(geography.load).toHaveBeenCalledWith("/ajax/load-municipios/?provincia_id=1");
    expect(Array.from(input("localidad").querySelectorAll("option")).map((o) => o.textContent)).toEqual(["---------"]);
    geography.load = vi.fn(() => Promise.resolve([{ id: 8, nombre: "Tolosa" }]));
    fireEvent.change(input("municipio"), { target: { value: "5" } });
    await waitFor(() => expect(Array.from(input("localidad").querySelectorAll("option")).map((o) => o.textContent)).toEqual(["---------", "Tolosa"]));
    expect(geography.load).toHaveBeenCalledWith("/ajax/load-localidades/?municipio_id=5");
  });

  it("reports a localidades load that fails in the map status", async () => {
    serve(form({}, { municipio: { choices: [empty, { value: "5", label: "La Plata" }] } }));
    geography.load = vi.fn(() => Promise.reject(new Error("x")));
    setup();
    await screen.findByRole("heading", { name: "Identificación del dispositivo" });
    fireEvent.change(input("municipio"), { target: { value: "5" } });
    await waitFor(() => expect(document.getElementById("dispositivo-mapa-estado")?.textContent).toBe("No se pudieron cargar las localidades. Volvé a seleccionar el municipio para reintentar."));
  });

  it("previews the location from the coordinates or the address, and asks for what is missing", async () => {
    serve(form());
    setup();
    await screen.findByRole("heading", { name: "Identificación del dispositivo" });
    const estado = () => document.getElementById("dispositivo-mapa-estado")?.textContent;
    const buscar = () => fireEvent.click(screen.getByRole("button", { name: "Previsualizar ubicación" }));
    expect(estado()).toContain("Se priorizan latitud y longitud.");
    buscar();
    expect(estado()).toBe("Completá provincia, municipio, calle y altura para previsualizar el domicilio.");
    type("latitud", "95");
    type("longitud", "-58");
    buscar();
    expect(estado()).toBe("Completá ambas coordenadas válidas: latitud entre -90 y 90 y longitud entre -180 y 180.");
    type("latitud", "-34.9");
    buscar();
    expect(estado()).toBe("Ubicación previsualizada. Guardá el dispositivo para confirmar los datos.");
    expect(document.getElementById("dispositivo-mapa")?.getAttribute("src")).toBe("https://www.google.com/maps?q=-34.9%2C-58&output=embed");
  });

  it("adds document slots one at a time, previews a chosen file and marks a saved one for removal", async () => {
    serve(form({}, {}, { saved: { documentacion_dispositivo: { full_name: "dispositivos/documentacion/x.pdf", label: "x.pdf", url: "/media/x.pdf", pdf: true } } }));
    setup();
    await screen.findByRole("heading", { name: "Observaciones y documentación del dispositivo" });
    const slots = () => Array.from(document.querySelectorAll(".doc-slot")).filter((s) => !s.classList.contains("d-none"));
    expect(slots()).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Añadir archivo" }));
    expect(slots()).toHaveLength(2);
    for (let i = 0; i < 3; i += 1) fireEvent.click(screen.getByRole("button", { name: "Añadir archivo" }));
    expect(slots()).toHaveLength(5);
    expect(document.getElementById("btn-add-doc")?.classList.contains("d-none")).toBe(true);

    const file = new File(["%PDF"], "plan.pdf", { type: "application/pdf" });
    fireEvent.change(input("documentacion_dispositivo_adicional_1"), { target: { files: [file] } });
    const preview = document.getElementById("preview-documentacion_dispositivo_adicional_1") as HTMLElement;
    expect(preview.classList.contains("d-none")).toBe(false);
    expect(preview.querySelector(".doc-preview-name")?.textContent).toBe("plan.pdf");
    expect(preview.querySelector(".doc-preview-size")?.textContent).toBe("4 B");
    fireEvent.click(preview.querySelector(".btn-quitar-preview") as HTMLElement);
    expect(preview.classList.contains("d-none")).toBe(true);

    const clear = document.getElementById("documentacion_dispositivo-clear_id") as HTMLInputElement;
    const overlay = document.querySelector(".doc-eliminar-overlay") as HTMLElement;
    fireEvent.click(document.querySelector(".btn-eliminar-doc") as HTMLElement);
    expect(clear.checked).toBe(true);
    expect(overlay.classList.contains("d-none")).toBe(false);
    fireEvent.click(overlay);
    expect(clear.checked).toBe(false);
  });

  it("posts the native fields once as multipart and goes to the legajo", async () => {
    serve(form());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/dispositivos/7/" } });
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    setup();
    await screen.findByRole("heading", { name: "Identificación del dispositivo" });
    type("nombre_institucion", "Hogar");
    fireEvent.click(document.getElementById("id_dias_atencion_0") as HTMLInputElement);
    const file = new File(["%PDF"], "plan.pdf", { type: "application/pdf" });
    fireEvent.change(input("documentacion_dispositivo"), { target: { files: [file] } });
    const send = screen.getByRole("button", { name: "Guardar dispositivo" });
    fireEvent.click(send);
    fireEvent.click(send);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/dispositivos/7/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/dispositivos/crear/");
    expect(posted()).toBeInstanceOf(FormData);
    expect(posted().get("nombre_institucion")).toBe("Hogar");
    expect(posted().getAll("dias_atencion")).toEqual(["uno"]);
    expect(posted().has("documentacion_dispositivo")).toBe(true);
    expect(posted().has("csrfmiddlewaretoken")).toBe(false);
  });

  it("redraws a rejected form with its errors, the typed values and the page at the top", async () => {
    serve(form());
    webPost.mockResolvedValue({
      status: 400,
      data: form({ has_errors: true }, { nombre_institucion: { value: "", errors: [{ message: "Este campo es requerido.", code: "required" }] }, calle: { value: "Calle 1" } }),
    });
    setup();
    await screen.findByRole("heading", { name: "Identificación del dispositivo" });
    fireEvent.click(screen.getByRole("button", { name: "Guardar dispositivo" }));
    await screen.findByText("No se pudo guardar el formulario. Revisá los campos marcados.");
    expect(document.getElementById("error_1_id_nombre_institucion")?.textContent).toBe("Este campo es requerido.");
    expect(input("nombre_institucion").getAttribute("aria-invalid")).toBe("true");
    expect(input("nombre_institucion").getAttribute("aria-describedby")).toBe("id_nombre_institucion_error");
    expect(input("calle").value).toBe("Calle 1");
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
    expect((screen.getByRole("button", { name: "Guardar dispositivo" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("reports an unconfirmed result without resubmitting and a forbidden one as access error", async () => {
    serve(form());
    webPost.mockRejectedValueOnce(new Error("network"));
    setup();
    await screen.findByRole("heading", { name: "Identificación del dispositivo" });
    fireEvent.click(screen.getByRole("button", { name: "Guardar dispositivo" }));
    await screen.findByText("No se pudo confirmar el resultado. Verificá el estado antes de reintentar.");
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("shows the not-found and error states of the load", async () => {
    serve({ detail: "No encontrado." }, 404);
    setup("/dispositivos/9/editar");
    expect(await screen.findByText("No se encontró la página.")).toBeTruthy();
    cleanup();
    serve({ fields: [] });
    setup();
    expect(await screen.findByText("No se pudo cargar la página.")).toBeTruthy();
  });
});
