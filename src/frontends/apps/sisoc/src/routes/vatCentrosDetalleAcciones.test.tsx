import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { readyContext, setViewport } from "./testFixtures";
import { centroAcciones } from "./vatCentrosDetalleModales";
import { vatNavigation } from "./vatShared";
import { vatGeography } from "./vatUbicacionesForm";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API_PANEL = "web/vat/centros-detalle/5/cursos/";
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control", type: "text" }, value: "", choices: [], errors: [], help_text: "", ...over,
});
const select2 = (name: string, label: string, choices: [string, string][], value = "", attrs: Record<string, string> = {}, required = false) => field(name, {
  label, required, tag: "select", attrs: { class: "form-control select2", "data-width": "100%", ...attrs }, value, choices: choices.map(([v, l]) => ({ value: v, label: l })),
});
const contactoFields = () => [
  select2("centro", "Centro", [["5", "CFP 401"]], "5"),
  field("nombre_contacto", { label: "Nombre y apellido" }),
  field("documento", { label: "Documento", attrs: { class: "form-control", type: "text", oninput: "this.value=this.value.replace(/\\D/g, '')" } }),
  field("telefono_contacto", { label: "Teléfono", attrs: { class: "form-control", type: "text", required: "required" } }),
  field("es_principal", { label: "Es principal", value: false, attrs: { class: "form-check-input", type: "checkbox" } }),
];
const ubicacionFields = () => [
  select2("centro", "Centro", [["5", "CFP 401"]], "5"),
  select2("departamento", "Departamento", [["", ""], ["7", "La Plata"]]),
  select2("localidad", "Localidad", [["", ""]]),
  field("domicilio", { label: "Domicilio" }),
];
const acciones = (base: string, id: number) => ({
  form: `/api/web/vat/centros-acciones/${base}/${id}/editar/`, guardar: `/api/web/vat/institucion/${base}/${id}/editar/`, eliminar: `/api/web/vat/institucion/${base}/${id}/eliminar/`,
});
const permisosTodos = { editar_centro: true, agregar_ubicacion: true, editar_ubicacion: true, eliminar_ubicacion: true, agregar_contacto: true, editar_contacto: true, eliminar_contacto: true };
const detalle = (over: Record<string, unknown> = {}) => ({
  id: 5, nombre: "CFP 401", codigo: "060144900", activo: true, mostrar_datos_administrativos: true, tipo_gestion: "Estatal", domicilio: "Calle 7 1234",
  telefono: "221 555 0101", celular: "-", correo: null, mapa: null,
  referente: { nombre: "Lia Paz", telefono: "-", dni: "-", correo: "-", usuarios: [] },
  ubicaciones: [{ id: 1, nombre: "Sede principal", caracteristica: "Sede principal", localidad: "Tolosa", domicilio: "7 123", urls: acciones("ubicaciones", 1) }],
  contactos: [{ id: 2, nombre: "Ana Gómez", documento: "30111222", rol: "Dirección", principal: true, telefono: "221 555 0202", urls: acciones("contactos", 2) }],
  permisos: permisosTodos, urls: { cursos: `/api/${API_PANEL}` }, messages: [],
  modales: {
    contacto: { fields: contactoFields(), crear: "/api/web/vat/institucion/contactos/nuevo/?centro=5" },
    ubicacion: { fields: ubicacionFields(), crear: "/api/web/vat/institucion/ubicaciones/nuevo/?centro=5", localidades: "/ajax/load-localidades/" },
  },
  ...over,
});

const cursoFields = () => [
  select2("plan_estudio", "Plan Curricular", [["", "Seleccionar plan de estudio..."], ["30", "Plan A"], ["31", "Plan B"]], "", { required: "required" }, true),
  field("nombre", { label: "Nombre", required: true, attrs: { class: "form-control", type: "text", required: "required" } }),
  field("tipo", { label: "Tipo", tag: "select", attrs: { class: "form-select select2", multiple: "multiple" }, choices: [{ value: "a", label: "Tipo A" }, { value: "b", label: "Tipo B" }], help_text: "Podés seleccionar uno o varios tipos." }),
  field("estado", { label: "Estado", required: true, tag: "select", attrs: { class: "form-control" }, value: "activo", choices: [{ value: "activo", label: "Activo" }, { value: "inactivo", label: "Inactivo" }] }),
  field("inscripcion_libre", { label: "Inscripción libre", value: false, attrs: { class: "form-check-input", type: "checkbox" } }),
  field("observaciones", { label: "Observaciones", tag: "textarea", attrs: { class: "form-control", rows: "3", cols: "40" } }),
];
const comisionFields = () => [
  select2("curso", "Curso", [["", ""], ["1", "Electricidad"]]),
  select2("ubicacion", "Ubicación", [["", ""], ["9", "Sede principal"]]),
  field("cupo_total", { label: "Cupo Total", attrs: { class: "form-control", type: "number", required: "required" } }),
  field("acepta_lista_espera", { label: "Acepta Lista de Espera", value: false, attrs: { class: "form-check-input", type: "checkbox" } }),
  field("cupo_lista_espera", { label: "Cupo Lista de Espera", attrs: { class: "form-control", type: "number" } }),
  field("fecha_inicio", { label: "Fecha de Inicio", attrs: { class: "form-control", type: "date", required: "required" } }),
  field("fecha_fin", { label: "Fecha de Fin", attrs: { class: "form-control", type: "date", required: "required" } }),
  field("estado", { label: "Estado", tag: "select", attrs: { class: "form-control" }, value: "planificada", choices: [{ value: "planificada", label: "Planificada" }, { value: "activa", label: "Activa" }] }),
  field("observaciones", { label: "Observaciones", tag: "textarea", attrs: { class: "form-control", rows: "3", cols: "40" } }),
];
const panel = () => ({
  cursos: [{
    id: 1, nombre: "Electricidad", plan: "Plan A", comisiones: 1,
    edicion: { plan_estudio: "30", nombre: "Electricidad", tipo: ["b"], estado: "activo", inscripcion_libre: true, observaciones: "Nota", guardar: "/api/web/vat/centros-acciones/cursos/1/editar/" },
    urls: { detalle: "/vat/cursos/1/", comision_nueva: "/vat/cursos/1/comision/nueva/", eliminar: "/vat/cursos/1/eliminar/" },
  }],
  comisiones: [{
    id: 11, curso_id: 1, curso_nombre: "Electricidad", codigo: "COM-1", nombre: "Turno", codigo_o_nombre: "COM-1", ubicacion: "Sede", fecha_inicio: "01/03/2026", fecha_fin: "30/06/2026", cupo: "20", estado: "activa",
    edicion: { curso: "1", curso_nombre: "Electricidad", ubicacion: "9", cupo_total: "20", acepta_lista_espera: false, cupo_lista_espera: "", fecha_inicio: "2026-03-01", fecha_fin: "2026-06-30", estado: "activa", observaciones: "", guardar: "/api/web/vat/comisiones-formularios/cursos/11/editar/" },
    urls: { detalle: "/vat/cursos/comisiones/11/", eliminar: "/vat/cursos/comisiones/11/eliminar/" },
  }],
  modales: {
    curso: { fields: cursoFields(), planes: [{ id: 30, etiqueta: "Plan A", normativa: "Res. 1" }, { id: 31, etiqueta: "Plan B", normativa: "" }], crear: "/api/web/vat/centros-acciones/cursos/nuevo/?centro=5" },
    comision_curso: { fields: comisionFields() },
  },
  permisos: { gestionar: true, agregar_curso: true, editar_curso: true, editar_comision: true },
});

let panelCalls = 0;
function setup(data: unknown = detalle(), panelData: unknown = panel(), extra: Record<string, unknown> = {}) {
  panelCalls = 0;
  webGet.mockImplementation((url: string) => {
    if (url === "web/session/") return Promise.resolve({ data: readyContext, status: 200 });
    if (url === API_PANEL) { panelCalls += 1; return Promise.resolve({ data: panelData, status: 200 }); }
    if (url in extra) return extra[url] instanceof Error ? Promise.reject(extra[url]) : Promise.resolve({ data: extra[url], status: 200 });
    return Promise.resolve({ data, status: 200 });
  });
  window.history.replaceState({}, "", "/vat/centros/5/");
  return render(<App />);
}
const saved = { status: 200, data: { ok: true, redirect: "/vat/centros/5/" } };
const rejected = (fields: unknown[]) => Promise.reject({ response: { status: 400, data: { editing: false, fields, non_field_errors: [], urls: { list: "/vat/centros/" } } } });
const bodyOf = (call: number) => Object.fromEntries([...(webPost.mock.calls[call][1] as URLSearchParams).entries()]);
// the side panels are CSS-hidden until their tab is picked: query them as hidden
const buttons = (name: RegExp) => screen.findAllByRole("button", { name, hidden: true });
const rowButtons = (label: string) => [...document.querySelectorAll(".sisoc-info-content .sisoc-table-actions button")].filter((b) => b.textContent?.trim() === label).length;
const modal = (id: string) => document.getElementById(id) as HTMLElement;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  vi.spyOn(centroAcciones, "reload").mockImplementation(() => undefined);
  vi.spyOn(centroAcciones, "alert").mockImplementation(() => undefined);
  vi.spyOn(vatGeography, "load").mockResolvedValue([{ id: 70, nombre: "Tolosa" }, { id: 71, nombre: "Ringuelet" }]);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT centro detalle in-page actions", () => {
  it("draws the buttons only for the permissions of the native predicates", async () => {
    setup();
    expect(await screen.findByText("Agregar sede")).toBeTruthy();
    expect(screen.getByText("Agregar contacto")).toBeTruthy();
    expect(rowButtons("Editar")).toBe(2);
    expect(rowButtons("Borrar")).toBe(2);
    cleanup();
    setup(detalle({ permisos: { ...permisosTodos, agregar_ubicacion: false, editar_contacto: false, eliminar_ubicacion: false }, modales: detalle().modales }));
    await screen.findByText("Agregar contacto");
    expect(screen.queryByText("Agregar sede")).toBeNull();
    expect(rowButtons("Editar")).toBe(1);
    expect(rowButtons("Borrar")).toBe(1);
    cleanup();
    setup(detalle({ permisos: { ...permisosTodos, editar_centro: false }, modales: null }));
    await screen.findByRole("heading", { level: 1, name: "CFP 401" });
    expect(screen.queryByText("Agregar contacto")).toBeNull();
    expect(rowButtons("Editar")).toBe(0);
  });

  it("adds a contact in the modal, saves it through the native view and reloads the page", async () => {
    setup();
    fireEvent.click(await screen.findByText("Agregar contacto"));
    const form = modal("modalContacto");
    expect(within(form).getByRole("heading", { name: "Agregar Contacto" }).tagName).toBe("H5");
    expect(form.className).toContain("vat-ui-modal");
    expect(form.querySelector("form#formContacto")).toBeTruthy();
    expect(within(form).getByText("Teléfono:").tagName).toBe("LABEL");
    webPost.mockResolvedValue(saved);
    fireEvent.change(form.querySelector("#id_nombre_contacto")!, { target: { value: "Ana Gómez" } });
    // the inline `oninput` of the digits-only widget runs as a filter
    fireEvent.change(form.querySelector("#id_documento")!, { target: { value: "30a111b" } });
    expect((form.querySelector("#id_documento") as HTMLInputElement).value).toBe("30111");
    fireEvent.click(form.querySelector("#id_es_principal")!);
    // the telephone is required: the HTML validation stops the submit like the native `reportValidity`
    fireEvent.submit(form.querySelector("form")!);
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.change(form.querySelector("#id_telefono_contacto")!, { target: { value: "221 555" } });
    fireEvent.submit(form.querySelector("form")!);
    await waitFor(() => expect(centroAcciones.reload).toHaveBeenCalledTimes(1));
    expect(webPost.mock.calls[0][0]).toBe("web/vat/institucion/contactos/nuevo/?centro=5");
    expect(bodyOf(0)).toEqual({ centro: "5", nombre_contacto: "Ana Gómez", documento: "30111", telefono_contacto: "221 555", es_principal: "on" });
    expect(document.getElementById("modalContacto")).toBeNull();
  });

  it("keeps the modal open on a rejected save: field errors, the native alert and the Guardar button back", async () => {
    setup();
    fireEvent.click(await screen.findByText("Agregar contacto"));
    const form = modal("modalContacto");
    fireEvent.change(form.querySelector("#id_telefono_contacto")!, { target: { value: "1" } });
    webPost.mockImplementation(() => rejected([field("telefono_contacto", { errors: ["Ingresá un teléfono válido."] })]));
    fireEvent.submit(form.querySelector("form")!);
    await waitFor(() => expect(centroAcciones.alert).toHaveBeenCalledWith("No se pudo guardar el contacto. Revisá los datos e intentá nuevamente."));
    const input = form.querySelector("#id_telefono_contacto")!;
    expect(input.className).toContain("is-invalid");
    expect(input.nextElementSibling?.className).toBe("invalid-feedback d-block");
    expect(input.nextElementSibling?.textContent).toBe("Ingresá un teléfono válido.");
    expect(within(form).getByRole("button", { name: "Guardar" })).toHaveProperty("disabled", false);
    expect(centroAcciones.reload).not.toHaveBeenCalled();
    // anything that is not a bound form is the generic message
    webPost.mockRejectedValue(new Error("down"));
    fireEvent.submit(form.querySelector("form")!);
    await waitFor(() => expect(centroAcciones.alert).toHaveBeenLastCalledWith("Error al guardar. Intente nuevamente."));
    expect(input.nextElementSibling?.className).not.toBe("invalid-feedback d-block");
    fireEvent.click(within(form).getByRole("button", { name: "Cancelar" }));
    expect(document.getElementById("modalContacto")).toBeNull();
  });

  it("takes the rejection text from the server answer and draws a Select2 error before its box, as the native script does", async () => {
    setup();
    fireEvent.click(await screen.findByText("Agregar contacto"));
    const form = modal("modalContacto");
    fireEvent.change(form.querySelector("#id_telefono_contacto")!, { target: { value: "1" } });
    webPost.mockImplementation(() => Promise.reject({ response: { status: 400, data: { editing: false, message: "Texto del servidor.", fields: [field("centro", { tag: "select", attrs: { class: "form-control select2" }, errors: ["Elegí un centro."] })], non_field_errors: [], urls: { list: "/vat/centros/" } } } }));
    fireEvent.submit(form.querySelector("form")!);
    await waitFor(() => expect(centroAcciones.alert).toHaveBeenCalledWith("Texto del servidor."));
    const select = form.querySelector("#id_centro")!;
    const feedback = select.closest("p")!.querySelector(".invalid-feedback")!;
    expect(feedback.textContent).toBe("Elegí un centro.");
    expect(select.className).toContain("is-invalid");
    // select, then the feedback, then the Select2 container: the native script inserts it `afterend` of the `<select>`
    expect(select.nextElementSibling).toBe(feedback);
    expect(feedback.nextElementSibling?.className).toContain("select2-container");
  });

  it("edits a contact from the fragment the native view draws and posts to the update endpoint", async () => {
    const url = "web/vat/centros-acciones/contactos/2/editar/";
    setup(detalle(), panel(), { [url]: { fields: [select2("centro", "Centro", [["5", "CFP 401"]], "5"), field("nombre_contacto", { label: "Nombre y apellido", value: "Ana Gómez" }), contactoFields()[3]] } });
    fireEvent.click((await buttons(/Editar/))[1]);
    await waitFor(() => expect(document.getElementById("modalContacto")).not.toBeNull());
    const form = modal("modalContacto");
    expect(webGet).toHaveBeenCalledWith(url, expect.anything());
    expect(within(form).getByRole("heading", { name: "Editar Contacto" })).toBeTruthy();
    expect((form.querySelector("#id_nombre_contacto") as HTMLInputElement).value).toBe("Ana Gómez");
    webPost.mockResolvedValue(saved);
    fireEvent.change(form.querySelector("#id_telefono_contacto")!, { target: { value: "55" } });
    fireEvent.submit(form.querySelector("form")!);
    await waitFor(() => expect(centroAcciones.reload).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe("web/vat/institucion/contactos/2/editar/");
  });

  it("tells the user when the edit form cannot be loaded", async () => {
    setup(detalle(), panel(), { "web/vat/centros-acciones/ubicaciones/1/editar/": new Error("down") });
    fireEvent.click((await buttons(/Editar/))[0]);
    await waitFor(() => expect(centroAcciones.alert).toHaveBeenCalledWith("Error al cargar el formulario de edición: Error al cargar la ubicación"));
    expect(document.getElementById("modalUbicacion")).toBeNull();
  });

  it("confirms before deleting and reloads whatever the answer was", async () => {
    setup();
    const confirm = vi.spyOn(vatNavigation, "confirm").mockReturnValue(false);
    const [borrarUbicacion, borrarContacto] = await buttons(/Borrar/);
    fireEvent.click(borrarContacto);
    expect(confirm).toHaveBeenLastCalledWith("¿Eliminar contacto?");
    expect(webPost).not.toHaveBeenCalled();
    confirm.mockReturnValue(true);
    webPost.mockRejectedValue(new Error("down"));
    fireEvent.click(borrarUbicacion);
    expect(confirm).toHaveBeenLastCalledWith("Eliminar ubicacion?");
    await waitFor(() => expect(centroAcciones.reload).toHaveBeenCalledTimes(1));
    expect(webPost.mock.calls[0][0]).toBe("web/vat/institucion/ubicaciones/1/eliminar/");
  });

  it("loads the localidades of the only departamento when the location modal opens and keeps the typed domicile", async () => {
    setup();
    fireEvent.click(await screen.findByText("Agregar sede"));
    const form = modal("modalUbicacion");
    expect(within(form).getByRole("heading", { name: "Agregar Ubicacion" })).toBeTruthy();
    await waitFor(() => expect(vatGeography.load).toHaveBeenCalledWith("/ajax/load-localidades/?municipio_id=7"));
    await waitFor(() => expect([...form.querySelectorAll("#id_localidad option")].map((o) => o.textContent)).toEqual(["", "Tolosa", "Ringuelet"]));
    expect((form.querySelector("#id_departamento") as HTMLSelectElement).value).toBe("7");
    fireEvent.change(form.querySelector("#id_domicilio")!, { target: { value: "7 123" } });
    webPost.mockResolvedValue(saved);
    fireEvent.submit(form.querySelector("form")!);
    await waitFor(() => expect(centroAcciones.reload).toHaveBeenCalled());
    expect(bodyOf(0)).toEqual({ centro: "5", departamento: "7", localidad: "", domicilio: "7 123" });
  });

  it("opens the course modal, picks a plan in the selector and saves the new course", async () => {
    setup();
    fireEvent.click(await screen.findByText("Agregar curso"));
    const form = modal("modalCurso");
    expect(within(form).getByRole("heading", { name: "Nuevo Curso" })).toBeTruthy();
    expect(within(form).getByRole("button", { name: "Guardar" }).id).toBe("cursoPrimarySubmitBtn");
    // the asterisk follows `field.field.required`, not the widget attribute (a select whose first option is not blank has none)
    expect([...form.querySelectorAll("label .text-danger")].length).toBe(3);
    expect(form.querySelector('label[for="id_estado"] .text-danger')).not.toBeNull();
    expect(form.querySelector('label[for="id_tipo"] .text-danger')).toBeNull();
    expect(document.getElementById("planCurricularSelectorSummary")?.textContent).toBe("No hay plan curricular seleccionado.");
    expect(document.getElementById("planCurricularSelectorButtonLabel")?.textContent).toBe("Seleccionar plan curricular");
    fireEvent.click(document.getElementById("openPlanCurricularSelector")!);
    const selector = modal("modalPlanCurricularSelector");
    expect(document.getElementById("modalCurso")).toBeNull();
    fireEvent.change(within(selector).getByPlaceholderText("Buscar por plan o normativa"), { target: { value: "res. 1" } });
    expect(selector.querySelectorAll("tbody tr.d-none").length).toBe(1);
    fireEvent.click(within(selector).getAllByRole("button", { name: "Seleccionar" })[0]);
    expect(document.getElementById("modalPlanCurricularSelector")).toBeNull();
    expect(document.getElementById("planCurricularSelectorSummary")?.textContent).toBe("Plan A");
    expect(document.getElementById("planEstudioSeleccionadoInfo")?.textContent).toBe("Plan curricular seleccionado: Plan A");
    expect(document.getElementById("planCurricularSelectorButtonLabel")?.textContent).toBe("Cambiar plan curricular");
    webPost.mockResolvedValue(saved);
    const callsBefore = panelCalls;
    fireEvent.change(document.getElementById("id_nombre")!, { target: { value: "Soldadura" } });
    fireEvent.submit(document.getElementById("formCurso")!);
    await waitFor(() => expect(panelCalls).toBe(callsBefore + 1));
    expect(webPost.mock.calls[0][0]).toBe("web/vat/centros-acciones/cursos/nuevo/?centro=5");
    expect(bodyOf(0)).toEqual({ plan_estudio: "30", nombre: "Soldadura", estado: "activo", observaciones: "" });
    expect(centroAcciones.reload).not.toHaveBeenCalled();
  });

  it("does not submit a course without a plan and shows the native course rejection", async () => {
    setup();
    fireEvent.click(await screen.findByText("Agregar curso"));
    fireEvent.change(document.getElementById("id_nombre")!, { target: { value: "Soldadura" } });
    fireEvent.submit(document.getElementById("formCurso")!);
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.change(document.getElementById("id_plan_estudio")!, { target: { value: "31" } });
    webPost.mockImplementation(() => rejected([field("nombre", { errors: ["Este campo es obligatorio."] })]));
    fireEvent.submit(document.getElementById("formCurso")!);
    await waitFor(() => expect(centroAcciones.alert).toHaveBeenCalledWith("No se pudo guardar el curso. Revisa los datos e intenta nuevamente."));
    expect(document.getElementById("id_nombre")?.nextElementSibling?.textContent).toBe("Este campo es obligatorio.");
  });

  it("edits a course with the values of its row and posts to the course update endpoint", async () => {
    setup();
    await waitFor(() => expect(document.querySelector(".btn-editar-curso")).not.toBeNull());
    fireEvent.click(document.querySelector(".btn-editar-curso")!);
    const form = modal("modalCurso");
    expect(within(form).getByRole("heading", { name: "Editar Curso" })).toBeTruthy();
    expect((document.getElementById("id_nombre") as HTMLInputElement).value).toBe("Electricidad");
    expect((document.getElementById("id_inscripcion_libre") as HTMLInputElement).checked).toBe(true);
    expect(document.querySelector("[data-voucher-counter-value=tipo]")?.textContent).toBe("1");
    expect(document.getElementById("planCurricularSelectorSummary")?.textContent).toBe("Plan A");
    webPost.mockResolvedValue(saved);
    fireEvent.submit(document.getElementById("formCurso")!);
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe("web/vat/centros-acciones/cursos/1/editar/");
    expect(bodyOf(0)).toMatchObject({ plan_estudio: "30", nombre: "Electricidad", tipo: "b", inscripcion_libre: "on", observaciones: "Nota" });
  });

  it("edits a commission: the waitlist capacity follows its toggle and the end date cannot precede the start", async () => {
    setup();
    await waitFor(() => expect(document.querySelector(".btn-editar-comision-curso")).not.toBeNull());
    fireEvent.click(document.querySelector(".btn-editar-comision-curso")!);
    const form = modal("modalComisionCurso");
    expect(within(form).getByRole("heading", { name: "Editar Comision de Curso" })).toBeTruthy();
    expect(document.getElementById("cursoSeleccionadoInfo")?.textContent).toBe("Curso seleccionado: Electricidad");
    const wrapper = form.querySelector("[data-waitlist-capacity-wrapper]")!;
    expect(wrapper.className).toContain("d-none");
    fireEvent.click(document.getElementById("id_acepta_lista_espera")!);
    expect(wrapper.className).not.toContain("d-none");
    expect(wrapper.querySelector("[data-waitlist-required-mark]")?.className).not.toContain("d-none");
    const fin = document.getElementById("id_fecha_fin") as HTMLInputElement;
    fireEvent.change(fin, { target: { value: "2026-02-01" } });
    expect(fin.validationMessage).toBe("La fecha de fin debe ser mayor o igual a la fecha de inicio.");
    fireEvent.submit(form.querySelector("form")!);
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.change(fin, { target: { value: "2026-07-01" } });
    fireEvent.change(document.getElementById("id_cupo_lista_espera")!, { target: { value: "5" } });
    webPost.mockResolvedValue(saved);
    const callsBefore = panelCalls;
    fireEvent.submit(form.querySelector("form")!);
    await waitFor(() => expect(panelCalls).toBe(callsBefore + 1));
    expect(webPost.mock.calls[0][0]).toBe("web/vat/comisiones-formularios/cursos/11/editar/");
    expect(bodyOf(0)).toMatchObject({ curso: "1", ubicacion: "9", cupo_total: "20", acepta_lista_espera: "on", cupo_lista_espera: "5", fecha_fin: "2026-07-01" });
  });
});
