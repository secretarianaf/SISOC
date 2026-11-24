import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { comedorFormNavigation } from "./comedorForm";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/comedores/";
const sel = (value: string, label: string) => ({ value, label });
const field = (name: string, section: string, label: string, over: Record<string, unknown> = {}) => ({
  name, section, label, type: "text", required: false, disabled: false, help: "", value: "", options: null, errors: [], attrs: {}, ...over,
});
const EMPTY = [sel("", "---------")];
const fields = (over: Record<string, Record<string, unknown>> = {}) => [
  field("nombre", "basic", "Nombre", { required: true, attrs: { maxlength: "255" } }),
  field("id_externo", "basic", "Id Externo", { type: "number" }),
  field("tipocomedor", "basic", "Tipo comedor", { type: "select", options: EMPTY }),
  field("categoria_espacio_comunitario", "basic", "Categorización de espacio comunitario", { type: "select", options: [...EMPTY, sel("otra", "Otra")] }),
  field("categoria_espacio_comunitario_otra", "basic", "Otra categoría"),
  field("organizacion", "basic", "Organizacion", { type: "select", options: EMPTY }),
  field("programa", "basic", "Programa", { type: "select", options: [...EMPTY, sel("1", "Programa 1")] }),
  field("proyecto", "basic", "Código de Proyecto", { type: "select", options: [sel("", "Seleccione un proyecto")] }),
  field("es_judicializado", "basic", "Es judicializado", { type: "select", options: [...EMPTY, sel("True", "Sí"), sel("False", "No")] }),
  field("es_caritas", "basic", "¿Es CARITAS?", { type: "select", required: true, options: [...EMPTY, sel("True", "Sí"), sel("False", "No")] }),
  field("estado_general", "estado", "Estado general", { type: "select", required: true, options: [sel("", "Seleccione un estado general"), sel("1", "Activo")] }),
  field("subestado", "estado", "Subestado", { type: "select", required: true, options: [sel("", "Seleccione un subestado")] }),
  field("motivo", "estado", "Motivo", { type: "select", options: [sel("", "Seleccione un motivo")] }),
  field("comienzo", "estado", "Comienzo", { type: "number", attrs: { min: "1900", max: "2026" } }),
  field("provincia", "ubicacion", "Provincia", { type: "select", required: true, options: [sel("", "---------"), sel("5", "Chaco")] }),
  field("municipio", "ubicacion", "Municipio", { type: "select", options: EMPTY }),
  field("localidad", "ubicacion", "Localidad", { type: "select", options: EMPTY }),
  ...["partido", "barrio", "codigo_postal", "calle", "numero", "piso", "departamento", "manzana", "lote", "entre_calle_1", "entre_calle_2", "latitud", "longitud"].map((n) => field(n, "ubicacion", n)),
  ...["nombre", "apellido", "mail", "celular", "documento", "funcion"].map((n) => field(`referente-${n}`, "referente", `${n} del referente`)),
].map((f) => ({ ...f, ...(over[f.name] ?? {}) }));
const TREE = { "1": { id: 1, label: "Activo", procesos: [{ id: 10, label: "En ejecución", detalles: [{ id: 100, label: "Sin novedad" }] }] } };
const form = (over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}) => ({
  form: {
    comedor_id: null, fields: fields(fieldOver), non_field_errors: [], referente_non_field_errors: [], estado_locked: false, estado_tree: TREE, codigo_de_proyecto_programa_ids: "1",
    foto_legajo: { file: null, required: false, initial_text: "Actualmente", input_text: "Modificar", clear_label: "Eliminar", errors: [] }, imagenes: [],
    urls: { cancel: "/comedores/listar", municipios: "/ajax/load-municipios/", localidades: "/ajax/load-localidades/", organizaciones: "/ajax/orgs/", proyectos: "/organizaciones/0/proyectos/ajax/", address_preview: "/ajax/ubicacion/previsualizar/" },
    ...over,
  },
  messages: [],
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
let assign: ReturnType<typeof vi.spyOn>, confirm: ReturnType<typeof vi.spyOn>, load: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  assign = vi.spyOn(comedorFormNavigation, "assign").mockImplementation(() => undefined);
  confirm = vi.spyOn(comedorFormNavigation, "confirm").mockReturnValue(true);
  load = vi.spyOn(comedorFormNavigation, "load").mockResolvedValue([]);
});
afterEach(() => { cleanup(); assign.mockRestore(); confirm.mockRestore(); load.mockRestore(); });

const input = (name: string) => document.querySelector(`[name="${name}"]`) as HTMLInputElement;

describe("Comedor form route (CO07.02)", () => {
  it("owns only the native create and edit URLs", () => {
    expect(findRoute("/comedores/crear")?.route.name).toBe("comedores-form");
    expect(findRoute("/comedores/7/editar")?.params).toEqual({ id: "7" });
    for (const other of ["/comedores/crear/", "/comedores/7/editar/", "/comedores/7/eliminar", "/comedores/7"]) expect(findRoute(other)?.route.name).not.toBe("comedores-form");
  });

  it("draws the crispy fields, the sections and the empty progress", async () => {
    serve(form());
    setup("/comedores/crear");
    await screen.findByText("Progreso del Formulario");
    expect(webGet).toHaveBeenCalledWith(`${API}formulario/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Espacios Comunitarios"));
    expect(document.querySelector("#div_id_nombre label")!.className).toBe("form-label requiredField");
    expect(document.querySelector("#div_id_nombre label .asteriskField")!.textContent).toBe("*");
    expect(input("nombre").className).toBe("textinput form-control");
    expect(input("nombre").required).toBe(true);
    expect(document.querySelector("#div_id_comienzo label .tooltip-in-label .tooltip-text")!.textContent).toBe("Año de inicio (1900 en adelante)");
    expect(document.getElementById("completedSections")!.textContent).toBe("0");
    expect(document.getElementById("status-basic")!.className).toBe("status-badge empty");
    expect(document.getElementById("categoria-espacio-otra-wrapper")!.className).toContain("d-none");
    expect(document.getElementById("codigo-proyecto-wrapper")!.className).toContain("d-none");
  });

  it("progress and badges follow the values, and the sections collapse", async () => {
    serve(form());
    setup("/comedores/crear");
    await screen.findByText("Progreso del Formulario");
    fireEvent.change(input("nombre"), { target: { value: "Comedor Norte" } });
    expect(document.getElementById("status-basic")!.className).toBe("status-badge incomplete");
    fireEvent.change(input("referente-nombre"), { target: { value: "Ana" } });
    fireEvent.change(input("referente-apellido"), { target: { value: "Pérez" } });
    fireEvent.change(input("referente-celular"), { target: { value: "1155" } });
    expect(document.getElementById("status-referente")!.className).toBe("status-badge complete");
    expect(document.getElementById("completedSections")!.textContent).toBe("1");
    expect(document.getElementById("progressBarFill")!.style.width).toBe("20%");
    fireEvent.click(document.querySelector('[data-toggle-section="basic"]')!);
    expect(document.getElementById("section-basic")!.className).toBe("section-body collapse");
  });

  it("the extra category shows only for «otra» and is cleared otherwise", async () => {
    serve(form());
    setup("/comedores/crear");
    await screen.findByText("Progreso del Formulario");
    const cat = input("categoria_espacio_comunitario") as unknown as HTMLSelectElement;
    fireEvent.change(cat, { target: { value: "otra" } });
    expect(document.getElementById("categoria-espacio-otra-wrapper")!.className).not.toContain("d-none");
    fireEvent.change(input("categoria_espacio_comunitario_otra"), { target: { value: "Texto" } });
    fireEvent.change(cat, { target: { value: "" } });
    expect(input("categoria_espacio_comunitario_otra").value).toBe("");
  });

  it("the estado cascade offers the subestados and motivos of the tree", async () => {
    serve(form());
    setup("/comedores/crear");
    await screen.findByText("Progreso del Formulario");
    const options = (name: string) => [...(input(name) as unknown as HTMLSelectElement).options].map((o) => o.value);
    expect(options("subestado")).toEqual([""]);
    const choose = (field: string, label: string) => {
      fireEvent.mouseDown(document.querySelector(`#div_id_${field} .select2-selection`) as HTMLElement);
      fireEvent.click(screen.getByRole("option", { name: label }));
    };
    choose("estado_general", "Activo");
    expect(options("subestado")).toEqual(["", "10"]);
    choose("subestado", "En ejecución");
    expect(options("motivo")).toEqual(["", "100"]);
    choose("estado_general", "Activo");
    expect([input("subestado").value, input("motivo").value]).toEqual(["", ""]);
  });

  it("the provincia loads the municipios through the native endpoint", async () => {
    load.mockResolvedValue([{ id: 7, nombre: "Resistencia" }]);
    serve(form());
    setup("/comedores/crear");
    await screen.findByText("Progreso del Formulario");
    fireEvent.mouseDown(document.querySelector("#div_id_provincia .select2-selection") as HTMLElement);
    fireEvent.click(screen.getByRole("option", { name: "Chaco" }));
    await waitFor(() => expect(load).toHaveBeenCalledWith("/ajax/load-municipios/?provincia_id=5"));
    await waitFor(() => expect([...(input("municipio") as unknown as HTMLSelectElement).options].map((o) => o.value)).toEqual(["", "7"]));
  });

  it("asks before saving, posts the form with the added images and goes to the ficha", async () => {
    serve(form());
    webPost.mockResolvedValue({ status: 201, data: { redirect: "/comedores/9" } });
    setup("/comedores/crear");
    await screen.findByText("Progreso del Formulario");
    fireEvent.change(input("nombre"), { target: { value: "Comedor Norte" } });
    fireEvent.change(input("referente-nombre"), { target: { value: "Ana" } });
    const file = new File(["x"], "a.png", { type: "image/png" });
    fireEvent.change(document.getElementById("imagenesInput")!, { target: { files: [file] } });
    expect(document.getElementById("selectedImagesInfo")!.className).toBe("contador-imagenes");
    fireEvent.submit(document.getElementById("comedorForm")!);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/9"));
    expect(confirm).toHaveBeenCalledWith("¿Estás seguro de que deseas guardar el comedor?");
    const [endpoint, body] = webPost.mock.calls[0];
    expect(endpoint).toBe(`${API}crear/`);
    expect((body as FormData).get("nombre")).toBe("Comedor Norte");
    expect((body as FormData).get("referente-nombre")).toBe("Ana");
    expect((body as FormData).getAll("imagenes")).toHaveLength(1);
  });

  it("a declined confirmation sends nothing", async () => {
    serve(form());
    confirm.mockReturnValue(false);
    setup("/comedores/crear");
    await screen.findByText("Progreso del Formulario");
    fireEvent.submit(document.getElementById("comedorForm")!);
    expect(webPost).not.toHaveBeenCalled();
    expect(assign).not.toHaveBeenCalled();
  });

  it("a 400 shows the native errors with the submitted values and stays", async () => {
    serve(form());
    const rechazo = form({}, { nombre: { value: "Repetido", errors: ["Este campo es requerido."] } });
    webPost.mockResolvedValue({ status: 400, data: { errors: {}, non_field_errors: [], form: rechazo.form } });
    setup("/comedores/crear");
    await screen.findByText("Progreso del Formulario");
    fireEvent.submit(document.getElementById("comedorForm")!);
    expect(await screen.findByText("Este campo es requerido.")).toBeTruthy();
    expect(input("nombre").value).toBe("Repetido");
    expect(input("nombre").className).toBe("textinput form-control is-invalid");
    expect(assign).not.toHaveBeenCalled();
  });

  it("an uncertain outcome shows the notice and is not retried", async () => {
    serve(form());
    webPost.mockRejectedValue({ response: { status: 504, data: { uncertain: true } } });
    setup("/comedores/crear");
    await screen.findByText("Progreso del Formulario");
    fireEvent.submit(document.getElementById("comedorForm")!);
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("edit: existing photo and images, mark one for deletion and post to the edit endpoint", async () => {
    serve(form({ comedor_id: 7, foto_legajo: { file: { url: "/media/comedor/f.png", name: "comedor/f.png" }, required: false, initial_text: "Actualmente", input_text: "Modificar", clear_label: "Eliminar", errors: [] },
      imagenes: [{ id: 3, url: "/media/comedor/i.png", name: "comedor/i.png" }], urls: { ...form().form.urls, cancel: "/comedores/7" } }, { nombre: { value: "Comedor Norte" } }));
    webPost.mockResolvedValue({ status: 200, data: { redirect: "/comedores/7" } });
    setup("/comedores/7/editar");
    await screen.findByText("Foto actual:");
    expect(webGet).toHaveBeenCalledWith(`${API}7/formulario/`, expect.anything());
    expect(screen.getByText("f.png")).toBeTruthy();
    expect(document.getElementById("status-multimedia")!.className).toBe("status-badge complete");
    fireEvent.click(document.querySelector(".btn-eliminar-custom")!);
    expect(document.querySelector(".imagen-existente")!.className).toContain("imagen-eliminada");
    expect(document.querySelector(".overlay-eliminar")!.className).toBe("overlay-eliminar");
    fireEvent.submit(document.getElementById("comedorForm")!);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/7"));
    const [endpoint, body] = webPost.mock.calls[0];
    expect(endpoint).toBe(`${API}7/editar/`);
    expect((body as FormData).get("imagen_ciudadano-borrar-3")).toBe("on");
    expect((body as FormData).get("nombre")).toBe("Comedor Norte");
  });

  it("the locked estado of a PAC comedor keeps the server options and disables the controls", async () => {
    serve(form({ estado_locked: true }, { estado_general: { disabled: true, value: "1" }, subestado: { disabled: true, value: "10", options: [sel("", "Seleccione un subestado"), sel("10", "En ejecución")] } }));
    setup("/comedores/crear");
    await screen.findByText("Progreso del Formulario");
    expect((input("estado_general") as unknown as HTMLSelectElement).disabled).toBe(true);
    expect(document.querySelector('[data-section="estado"]')!.getAttribute("data-estado-locked")).toBe("true");
  });
});
