import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const CREAR = "/comedores/admision/informe_tecnico/base/7/crear/";
const API = "web/comedores/admisiones/informes/base/admision/7/";
const LOCALIDADES = "/ajax/load-localidades/";
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, label: name, kind: "text", required: false, value: "", help_text: "", max_length: 255, errors: [], id: `id_${name}`,
  attrs: { maxlength: "255" }, widget: "TextInput", ...over,
});
const base = (over: Record<string, unknown> = {}) => ({
  tipo: "base", admision_id: 7, informe_id: null, estado: "", comedor: "Comedor Sintético", permite_no_corresponde: false,
  fields: [
    field("expediente_nro", { label: "Número Expediente" }),
    field("nombre_organizacion", { label: "Nombre de la Organización Solicitante" }),
    field("provincia_organizacion", { kind: "select", widget: "Select", value: "5", label: "Provincia", attrs: { "data-geografia-provincia": "id_localidad_organizacion", maxlength: "255" },
      choices: [{ value: "", label: "Seleccione una provincia" }, { value: "5", label: "Provincia Cinco" }] }),
    field("localidad_organizacion", { kind: "select", widget: "Select", value: "9", label: "Localidad", attrs: { "data-geografia-localidad": "true", maxlength: "255" },
      choices: [{ value: "", label: "Seleccione una localidad" }] }),
    field("solicitudes_desayuno_lunes", { kind: "number", widget: "NumberInput", value: "0", label: "", attrs: { "aria-label": "", placeholder: "" } }),
    field("fecha_vencimiento_mandatos", { kind: "date", widget: "DateInput", attrs: { class: "form-control" } }),
    field("no_corresponde_fecha_vencimiento", { kind: "checkbox", widget: "CheckboxInput", value: false, attrs: { class: "form-check-input", id: "no_corresponde_fecha_vencimiento" } }),
  ],
  antecedentes: [], non_field_errors: [], campos_a_subsanar: [], observacion: "",
  publicacion: { plantilla: null, error: null, configuracion_faltante: false, detalle_copiable: "" },
  urls: { volver: "/comedores/admision/7/tecnicos/editar/", previsualizar: null, reportar_faltante: "/comedores/admisiones/7/templates/reportar-faltante/", localidades: LOCALIDADES },
  messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path = CREAR) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const secciones = () => [...document.querySelectorAll<HTMLElement>(".collapse[data-informe-seccion]")];

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve([{ id: 9, nombre: "Localidad Nueve" }, { id: 10, nombre: "Localidad Diez" }]) })));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("Technical report editor route (AD02.01)", () => {
  it("owns the native create and edit pages only", () => {
    expect(findRoute(CREAR)?.params).toEqual({ tipo: "base", admision: "7" });
    expect(findRoute("/comedores/admision/informe_tecnico/juridico/3/editar/")?.params).toEqual({ tipo: "juridico", id: "3" });
    for (const other of ["/comedores/admision/informe_tecnico/base/7/crear", "/comedores/admision/informe_tecnico/base/7/ver/", "/comedores/admision/informe_tecnico/base/7/previsualizar/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-informe-tecnico-editor");
    }
  });

  it("renders the collapsed sections, headings and the native buttons", async () => {
    serve(base());
    setup();
    await screen.findByText("Datos de la Organización");
    expect(webGet).toHaveBeenCalledWith(`${API}formulario/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Informe Técnico: Comedor Sintético"));
    expect(screen.getByText("Informe Técnico: Comedor Sintético - Estado:", { exact: false })).toBeTruthy();
    expect(secciones().every((s) => !s.classList.contains("show"))).toBe(true);
    expect(screen.queryByText("Prestaciones aprobadas en el ultimo convenio")).toBeNull();
    expect(within(document.querySelector("form[data-avisar-cambios-sin-guardar]")!).getByRole("link", { name: "Volver" }).getAttribute("href")).toBe("/comedores/admision/7/tecnicos/editar/");
    const draft = screen.getByRole("button", { name: "Guardar Borrador" }) as HTMLButtonElement;
    expect([draft.name, draft.value]).toEqual(["action", "draft"]);
    expect(document.querySelector("form[data-avisar-cambios-sin-guardar]")!.getAttribute("data-localidades-url")).toBe(LOCALIDADES);
  });

  it("toggles a section and keeps the chevron state", async () => {
    serve(base());
    setup();
    const boton = (await screen.findByText("Datos de la Organización")).closest("button")!;
    expect(boton.classList.contains("collapsed")).toBe(true);
    fireEvent.click(boton);
    expect(boton.getAttribute("aria-expanded")).toBe("true");
    expect(document.getElementById("informeSeccionOrganizacion")!.classList.contains("show")).toBe(true);
    fireEvent.click(boton);
    expect(boton.classList.contains("collapsed")).toBe(true);
  });

  it("loads the localities of the selected province and reloads them when it changes", async () => {
    serve(base());
    setup();
    const localidad = (await screen.findByLabelText("Localidad")) as HTMLSelectElement;
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(`${LOCALIDADES}?provincia_id=5`, expect.objectContaining({ credentials: "same-origin" })));
    await waitFor(() => expect([...localidad.options].map((o) => o.text)).toEqual(["Seleccione una localidad", "Localidad Nueve", "Localidad Diez"]));
    expect(localidad.value).toBe("9");
    fireEvent.change(screen.getByLabelText("Provincia"), { target: { value: "" } });
    await waitFor(() => expect([...localidad.options].map((o) => o.text)).toEqual(["Seleccione una localidad"]));
    expect(localidad.value).toBe("");
  });

  it("saves a draft as JSON through the API and navigates to the native success URL", async () => {
    serve(base());
    webPost.mockResolvedValue({ status: 200, data: { success: true, redirect: "/comedores/admision/7/tecnicos/editar/" } });
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });
    setup();
    fireEvent.change(await screen.findByLabelText("Número Expediente"), { target: { value: "EX-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar Borrador" }));
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(`${API}guardar/`);
    expect(body.action).toBe("draft");
    expect(body.values.expediente_nro).toBe("EX-1");
    expect(body.values.no_corresponde_fecha_vencimiento).toBe(false);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/admision/7/tecnicos/editar/"));
  });

  it("a submit click opens every section; a rejection keeps open only the sections with errors", async () => {
    serve(base());
    const bound = base({
      fields: base().fields.map((f) => (f.name === "nombre_organizacion" ? { ...f, required: true, errors: ["Este campo es requerido."], attrs: { ...f.attrs, required: true } } : f)),
    });
    webPost.mockResolvedValue({ status: 400, data: { success: false, message: "No se pudo guardar el informe. Revisá los campos: Nombre: Este campo es requerido.", fields: bound.fields, non_field_errors: [] } });
    setup();
    await screen.findByText("Datos de la Organización");
    fireEvent.click(screen.getByRole("button", { name: "Finalizar" }));
    expect(secciones().every((s) => s.classList.contains("show"))).toBe(true);
    await screen.findByText("Este campo es requerido.");
    expect(webPost.mock.calls[0][1].action).toBe("submit");
    expect(secciones().filter((s) => s.classList.contains("show")).map((s) => s.id)).toEqual(["informeSeccionOrganizacion"]);
    const campo = screen.getByLabelText(/Nombre de la Organización Solicitante/) as HTMLInputElement;
    expect(campo.classList.contains("is-invalid")).toBe(true);
    expect(campo.getAttribute("aria-describedby")).toBe("id_nombre_organizacion_error");
    expect(screen.getByText("No se pudo guardar el informe. Revisá los campos: Nombre: Este campo es requerido.")).toBeTruthy();
  });

  it("a service rejection shows its message and keeps the typed values", async () => {
    serve(base());
    webPost.mockResolvedValue({ status: 409, data: { success: false, saved_as_draft: false, error: "El informe técnico ya fue validado y no puede editarse." } });
    setup();
    fireEvent.change(await screen.findByLabelText("Número Expediente"), { target: { value: "EX-9" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar Borrador" }));
    expect(await screen.findByText("El informe técnico ya fue validado y no puede editarse.")).toBeTruthy();
    expect((screen.getByLabelText("Número Expediente") as HTMLInputElement).value).toBe("EX-9");
  });

  it("warns before leaving with unsaved edits and can save a draft from the modal", async () => {
    serve(base());
    webPost.mockResolvedValue({ status: 200, data: { success: true, redirect: "/comedores/admision/7/tecnicos/editar/" } });
    vi.stubGlobal("location", { ...window.location, assign: vi.fn() });
    setup();
    await screen.findByLabelText("Número Expediente");
    const volver = within(document.querySelector("form[data-avisar-cambios-sin-guardar]")!).getByRole("link", { name: "Volver" });
    const limpio = new MouseEvent("click", { bubbles: true, cancelable: true, button: 0 });
    volver.dispatchEvent(limpio);
    expect(limpio.defaultPrevented).toBe(false);
    fireEvent.change(screen.getByLabelText("Número Expediente"), { target: { value: "EX-2" } });
    const sucio = new MouseEvent("click", { bubbles: true, cancelable: true, button: 0 });
    volver.dispatchEvent(sucio);
    expect(sucio.defaultPrevented).toBe(true);
    const modal = await screen.findByRole("dialog");
    expect(within(modal).getByText("Hay cambios en el Informe Técnico que todavía no se guardaron.")).toBeTruthy();
    fireEvent.click(within(modal).getByRole("button", { name: "Seguir editando" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    volver.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, button: 0 }));
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: /Guardar borrador/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    expect(webPost.mock.calls[0][1].action).toBe("draft");
  });

  it("shows the renewal sections, the antecedents and the optional fields only when exposed", async () => {
    const data = base({
      fields: [
        ...base().fields,
        field("expediente_incorporacion", { label: "Expediente de incorporación" }),
        field("convenio_incorporacion"),
        field("presentacion_avales"),
        field("aprobadas_ultimo_convenio_cena_domingo", { kind: "number", widget: "NumberInput", value: "0", label: "", attrs: {} }),
        field("antecedente_3_incluir", { kind: "checkbox", widget: "CheckboxInput", value: true, attrs: {}, label: "Incluir en el informe" }),
        field("antecedente_3_resolucion", { label: "Resolución / Disposición de Renovación" }),
        field("antecedente_3_convenio"), field("antecedente_3_expediente"),
      ],
      antecedentes: [{ admision_id: 3, incluida: "antecedente_3_incluir", resolucion: "antecedente_3_resolucion", convenio: "antecedente_3_convenio", expediente: "antecedente_3_expediente" }],
      campos_a_subsanar: ["nombre_organizacion"], observacion: "Revisar domicilio",
    });
    serve(data);
    setup();
    expect(await screen.findByText("Prestaciones aprobadas en el ultimo convenio")).toBeTruthy();
    expect(screen.getByText("Referencia a la Incorporación")).toBeTruthy();
    expect(screen.getByText("Admisión #3")).toBeTruthy();
    expect(screen.getByText("Campos para subsanar")).toBeTruthy();
    expect(screen.getByText("Revisar domicilio")).toBeTruthy();
    expect(document.getElementById("informeSeccionOrganizacion")!.classList.contains("show")).toBe(true);
    expect(document.querySelector(".border-danger input#id_nombre_organizacion")).toBeTruthy();
    expect(document.getElementById("id_if_it_complementario")).toBeNull();
  });

  it("the publication error offers the native notification POST, not the draft save", async () => {
    serve(base({ publicacion: { plantilla: null, error: "No hay plantilla.", configuracion_faltante: true, detalle_copiable: "Combinación: x" }, informe_id: 4 }));
    setup();
    const boton = await screen.findByRole("button", { name: /Notificar a referentes del sistema/ }) as HTMLButtonElement;
    expect(boton.getAttribute("formaction")).toBe("/comedores/admisiones/7/templates/reportar-faltante/");
    expect([boton.name, boton.value]).toEqual(["informe_id", "4"]);
    expect((boton.form!.querySelector('[name="csrfmiddlewaretoken"]') as HTMLInputElement).value).toBe("synthetic-csrf-token");
    expect((document.getElementById("detalle-configuracion-faltante") as HTMLTextAreaElement).value).toBe("Combinación: x");
    const enviado = new Event("submit", { bubbles: true, cancelable: true });
    Object.defineProperty(enviado, "submitter", { value: boton });
    document.querySelector("form[data-avisar-cambios-sin-guardar]")!.dispatchEvent(enviado);
    expect(enviado.defaultPrevented).toBe(false);
    expect(webPost).not.toHaveBeenCalled();
  });

  it("draws the notification message inside the form, as the native page, and not as a toast", async () => {
    serve(base({ messages: [
      { message: "La configuración pendiente fue registrada.", level: "success", tags: "success configuracion-template" },
      { message: "Otro aviso.", level: "info", tags: "info" },
    ] }));
    setup();
    await screen.findByText("Notificación enviada");
    const seccion = screen.getByText("Notificación enviada").closest("section")!;
    expect(seccion.getAttribute("role")).toBe("status");
    expect(seccion.className).toBe("alert border-0 shadow-sm mb-4");
    expect(seccion.getAttribute("style")).toContain("background: rgb(11, 95, 138)");
    expect(within(seccion).getByText("La configuración pendiente fue registrada.")).toBeTruthy();
    expect(document.querySelector("form[data-avisar-cambios-sin-guardar]")!.contains(seccion)).toBe(true);
    expect(document.querySelector("#toast-container")!.textContent).toBe("Otro aviso.");
    expect(document.querySelectorAll(".toast")).toHaveLength(1);
  });

  it("a 403 from the API is the access screen", async () => {
    serve({ detail: "denied" }, 403);
    setup();
    expect((await screen.findByRole("link", { name: "volver al inicio" })).getAttribute("href")).toBe("/inicio/");
  });
});
