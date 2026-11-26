import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { editorNative, editorValid } from "./admisionesEditor";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const EDITOR = "/comedores/admisiones/tecnicos/editar/5";
const API = "web/comedores/admisiones/5/";
const field = (name: string, label: string, value = "", extra: Record<string, unknown> = {}) => ({
  name, label, kind: "text", required: true, value, help_text: "", max_length: null, errors: [], id: `id_${name}`, attrs: { class: "form-control" }, widget: "TextInput", ...extra,
});
const select = (name: string, label: string, value = "") => field(name, label, value, {
  kind: "select", widget: "Select", attrs: { class: "form-select" }, choices: [{ value: "", label: "---------" }, { value: "si", label: "Si" }, { value: "no", label: "No" }, { value: "vigente", label: "Vigente" }],
});
const doc = (over: Record<string, unknown> = {}) => ({
  id: "11", row_id: "3", documentacion_id: 3, archivo_id: 11, nombre: "Estatuto", obligatorio: true, organizacion: false, vencimiento: null, estado: "Documento adjunto",
  estado_valor: "Documento adjunto", estado_ui: { kind: "select", requires_observacion: false, border: "", options: [
    { value: "Documento adjunto", label: "Documento adjunto", selected: true, disabled: true }, { value: "A Validar Abogado", label: "A Validar Abogado", selected: false, disabled: false }] },
  archivo_url: "/media/estatuto.pdf", puede_eliminar: true, puede_adjuntar: false, gde: { kind: "plain" }, numero_gde: "", personalizado: false, observaciones: null, ...over,
});
const editor = (over: Record<string, unknown> = {}) => ({
  id: 5, vacio: false, banner: null,
  comedor: { id: 7, nombre: "Comedor Sintético", tipocomedor: "Sin información", programa: "Programa X", organizacion: "Org", provincia: "Chaco", municipio: "Resistencia", localidad: "Centro", calle: "Calle", numero: "12", piso: "Sin información", departamento: "" },
  urls: { listar: "/comedores/admisiones/tecnicos/listar", comedor: "/comedores/7", pagina: EDITOR, localidades: "/ajax/load_localidades/", agregar_documento: "/admision/5/documentacion/personalizada/agregar/", resync: "/admisiones/5/resync-convenio/" },
  botones: [{ clave: "mandar_a_legales", texto: "Derivar a legales", clase: "btn-primary", modal: "confirmarLegalesModal", url: null }, { clave: "ver_informe_tecnico", texto: "Ver Informe Técnico", clase: "btn-primary", modal: null, url: "/comedores/admision/informe_tecnico/base/9/ver/" }],
  resync: null, complementario_requerido: null, informe_a_subsanar: null, seleccion_convenio: null,
  admision: { tipo: "incorporacion", tipo_convenio: "Personería Jurídica", convenio_numero: 4, vigente_pwa: true, personas_conveniadas_nomina: null, tipo_display: "Incorporación", estado_proceso: "Convenio seleccionado",
    fecha: "01/10/2026", vencimiento_mandatos: "-", num_expediente: "EX-2026-000000001- -APN-DGD#MCH", enviado_legales: false, informe_estado: null, numero_if_tecnico: null, informe_gde: null, estado_legales: "", observaciones: "" },
  puede_editar_convenio_numero: true, mostrar_personas_conveniadas_nomina: false, puede_editar_personas_conveniadas_nomina: false, puede_editar_num_expediente: true,
  pdf: null, complementarios: [],
  validaciones: { editable: true, fields: [select("es_ex_pnud", "Es ex pnud", "no"), select("estado_convenio_pnud", "Estado convenio pnud", "")] },
  stats: { obligatorios_completos: 0, obligatorios_total: 1, aceptados: 0, a_validar_abogado: 0, rectificar: 0, pendientes: 0 },
  documentos: [doc()], documentos_personalizados: [], puede_agregar_documento: true,
  modales: { if_informe: [field("numero_if_tecnico", "Número IF Informe Técnico")], if_informe_archivo: { id: "id_archivo_informe_tecnico_GDE", label: "Archivo Informe Técnico (GDE)" },
    caratular: [field("expediente_anio", "Año"), field("expediente_numero", "Número"), field("expediente_reparticion", "Repartición"), field("expediente_organismo", "Organismo", "MCH")], informe_id: 9 },
  informe_embebido: null, messages: [], ...over,
});

function serve(data: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
}
function setup() {
  window.history.replaceState({}, "", EDITOR);
  return render(<App />);
}
const ok = (messages: unknown[] = []) => Promise.resolve({ status: 200, data: { success: true, messages } });

beforeEach(() => {
  vi.clearAllMocks();
  webGet.mockReset();
  webPost.mockReset();
  document.title = "SISOC";
  setViewport(false);
  vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Technical admision editor (AD03.02)", () => {
  it("owns the native editor URL without a trailing slash", () => {
    expect(findRoute(EDITOR)?.params).toEqual({ page: "editor", id: "5" });
    expect(findRoute(`${EDITOR}/`)?.route.name).not.toBe("comedores-admisiones-seguimiento");
  });

  it("renders the cards, the buttons and the documents table of the native template", async () => {
    serve(editor({ banner: "RECHAZADO: Falta de documentación" }));
    setup();
    await screen.findByText("Documentos requeridos");
    expect(webGet).toHaveBeenCalledWith(`${API}`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Admision: Comedor Sintético"));
    expect(screen.getByText("RECHAZADO: Falta de documentación").className).toContain("bg-danger");
    expect(screen.getByRole("button", { name: "Derivar a legales" }).className).toBe("btn btn-primary mr-1");
    expect(screen.getByRole("link", { name: "Ver Informe Técnico" }).getAttribute("href")).toBe("/comedores/admision/informe_tecnico/base/9/ver/");
    expect(screen.getByText("Programa X")).toBeTruthy();
    expect(screen.getByText("Personería Jurídica")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver Archivo" }).getAttribute("href")).toBe("/media/estatuto.pdf");
    expect(screen.getByText("Documentación adicional")).toBeTruthy();
    expect(screen.queryByText("Informe Técnico Complementario Requerido")).toBeNull();
  });

  it("rejects a malformed envelope", () => {
    expect(editorValid(editor())).toBe(true);
    expect(editorValid({ ...editor(), documentos: [{ nombre: "x" }] })).toBe(false);
    expect(editorValid({ ...editor(), urls: { ...editor().urls, listar: "https://evil.example" } })).toBe(false);
  });

  it("derives to legal through the action endpoint and reloads with the native message", async () => {
    serve(editor());
    webPost.mockImplementationOnce(() => ok([{ message: "La admisión fue enviada a legales correctamente.", level: "success" }]));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Derivar a legales" }));
    const modal = await screen.findByRole("dialog");
    expect(within(modal).getByText("¿Estás seguro que queres derivar a Legales")).toBeTruthy();
    fireEvent.click(within(modal).getByRole("button", { name: "Confirmar" }));
    await waitFor(() => expect(webPost).toHaveBeenCalledWith("web/comedores/admisiones/5/acciones/derivar-legales/", {}, expect.anything()));
    expect(await screen.findByText("La admisión fue enviada a legales correctamente.")).toBeTruthy();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(webGet).toHaveBeenCalledWith(`${API}?r=1`, expect.anything()));
  });

  it("keeps a rejected action's message, reloads and resets the view", async () => {
    serve(editor());
    webPost.mockImplementationOnce(() => Promise.resolve({ status: 400, data: { success: false, messages: [{ message: "La admisión ya estaba marcada como enviada a legales.", level: "error" }] } }));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Derivar a legales" }));
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Confirmar" }));
    expect(await screen.findByText("La admisión ya estaba marcada como enviada a legales.")).toBeTruthy();
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
  });

  it("saves the cover and keeps the modal open with the field errors when the form is invalid", async () => {
    serve(editor({ botones: [{ clave: "caratular_expediente", texto: "Caratular expediente", clase: "btn-primary", modal: "caratularExpediente", url: null }] }));
    const invalid = { status: 400, data: { success: false, messages: [], non_field_errors: [], fields: [
      field("expediente_anio", "Año", "20", { errors: ["Asegúrese de que este valor tenga al menos 4 caracteres (tiene 2)."] }),
      field("expediente_numero", "Número"), field("expediente_reparticion", "Repartición"), field("expediente_organismo", "Organismo", "MCH")] } };
    webPost.mockImplementationOnce(() => Promise.resolve(invalid)).mockImplementationOnce(() => ok([{ message: "Caratulación del expediente guardado correctamente.", level: "success" }]));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Caratular expediente" }));
    const modal = await screen.findByRole("dialog");
    fireEvent.change(modal.querySelector("#id_expediente_anio")!, { target: { value: "20" } });
    fireEvent.change(modal.querySelector("#id_expediente_numero")!, { target: { value: "123456789" } });
    fireEvent.change(modal.querySelector("#id_expediente_reparticion")!, { target: { value: "DGD" } });
    fireEvent.click(within(modal).getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Asegúrese de que este valor tenga al menos 4 caracteres (tiene 2).")).toBeTruthy();
    expect(screen.getByRole("dialog")).toBeTruthy();
    const body = webPost.mock.calls[0][1] as Record<string, string>;
    expect(body).toEqual({ expediente_anio: "20", expediente_numero: "123456789", expediente_reparticion: "DGD", expediente_organismo: "MCH" });
    fireEvent.change(screen.getByRole("dialog").querySelector("#id_expediente_anio")!, { target: { value: "2026" } });
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Caratulación del expediente guardado correctamente.")).toBeTruthy();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("uploads the technical report number as multipart and the final DOCX through its action", async () => {
    serve(editor({ botones: [
      { clave: "if_informe_tecnico", texto: "Cargar Informe Técnico -GDE", clase: "btn-primary", modal: "modalIFInformeTecnico", url: null },
      { clave: "revisar_informe_tecnico", texto: "Revisar Informe Técnico", clase: "btn-warning", modal: "modalRevisarInformeTecnico", url: null }],
    pdf: { archivo: null, docx: "/media/i.docx", docx_editado: null } }));
    webPost.mockImplementation(() => ok([{ message: "Hecho.", level: "success" }]));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Cargar Informe Técnico -GDE" }));
    const modal = await screen.findByRole("dialog");
    const numero = within(modal).getByRole<HTMLInputElement>("textbox", { name: /Número IF Informe Técnico/ });
    fireEvent.change(numero, { target: { value: "IF-2026-12345678-APN-TEST" } });
    expect(numero.value).toBe("IF-2026-12345678-APN-TEST");
    const archivo = new File(["informe sintético"], "informe.pdf", { type: "application/pdf" });
    fireEvent.change(modal.querySelector("input[type=file]")!, { target: { files: [archivo] } });
    expect((modal.querySelector("input[type=file]") as HTMLInputElement).required).toBe(true);
    fireEvent.submit(modal.querySelector("form")!);
    await waitFor(() => expect(webPost).toHaveBeenCalledWith("web/comedores/admisiones/5/acciones/if-informe-tecnico/", expect.any(FormData), expect.anything()));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    const body = webPost.mock.calls[0][1] as FormData;
    expect(body.get("numero_if_tecnico")).toBe("IF-2026-12345678-APN-TEST");
    expect(body.get("archivo_informe_tecnico_GDE")).toBeInstanceOf(File);
    fireEvent.click(screen.getByRole("button", { name: "Revisar Informe Técnico" }));
    expect(within(await screen.findByRole("dialog")).getByRole("link", { name: /Descargar DOCX/ }).getAttribute("href")).toBe("/media/i.docx");
    fireEvent.click(screen.getByRole("button", { name: /Subir DOCX Informe técnico Final/ }));
    const upload = await screen.findByRole("dialog");
    expect((upload.querySelector("input[name=informe_id]") as HTMLInputElement).value).toBe("9");
    fireEvent.submit(upload.querySelector("form")!);
    await waitFor(() => expect(webPost).toHaveBeenLastCalledWith("web/comedores/admisiones/5/acciones/subir-docx-final/", expect.any(FormData), expect.anything()));
  });

  it("posts the template validations and hides the PNUD state until it applies", async () => {
    serve(editor());
    webPost.mockImplementationOnce(() => ok([{ message: "Validaciones de templates guardadas correctamente.", level: "success" }]));
    setup();
    const container = (await screen.findByText("Estado convenio pnud", { selector: "label" })).closest("#estadoConvenioPnudEdicionContainer")!;
    expect(container.className).toContain("d-none");
    fireEvent.change(document.getElementById("id_es_ex_pnud")!, { target: { value: "si" } });
    expect(container.className).not.toContain("d-none");
    fireEvent.change(document.getElementById("id_estado_convenio_pnud")!, { target: { value: "vigente" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar validaciones" }));
    await waitFor(() => expect(webPost).toHaveBeenCalledWith("web/comedores/admisiones/5/acciones/validaciones-template/", { es_ex_pnud: "si", estado_convenio_pnud: "vigente" }, expect.anything()));
    expect(await screen.findByText("Validaciones de templates guardadas correctamente.")).toBeTruthy();
  });

  it("shows the read-only validations without the form when the user cannot edit them", async () => {
    serve(editor({ validaciones: { editable: false, valores: [["¿Es Ex PNUD?", "No"], ["Estado del convenio PNUD", "No aplica"]] } }));
    setup();
    expect(await screen.findByText("No aplica")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Guardar validaciones" })).toBeNull();
  });

  it("asks for the agreement type with the native fields and confirms it through the action", async () => {
    serve(editor({ seleccion_convenio: { tipo_entidad: "Personería Jurídica", tipo_convenio: "Personería Jurídica", precargado: true, tipo: "incorporacion" }, validaciones: null,
      admision: { ...editor().admision, tipo_convenio: "" } }));
    webPost.mockImplementationOnce(() => ok([{ message: "Tipo de convenio precargado desde la organización.", level: "success" }]));
    setup();
    const modal = await screen.findByRole("dialog");
    expect(within(modal).getByText("Selección de Convenio", { selector: "h5" })).toBeTruthy();
    expect(within(modal).getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/comedores/admisiones/tecnicos/listar");
    expect(document.getElementById("estadoConvenioPnudInicialContainer")).toBeNull();
    fireEvent.change(document.getElementById("esExPnudInicial")!, { target: { value: "si" } });
    expect(document.getElementById("estadoConvenioPnudInicialContainer")).not.toBeNull();
    fireEvent.change(document.getElementById("estadoConvenioPnudInicial")!, { target: { value: "vigente" } });
    fireEvent.click(within(modal).getByRole("button", { name: "Continuar" }));
    await waitFor(() => expect(webPost).toHaveBeenCalledWith("web/comedores/admisiones/5/acciones/confirmar-tipo-convenio/", { es_ex_pnud: "si", estado_convenio_pnud: "vigente" }, expect.anything()));
  });

  it("changes a document state through the native endpoint and asks the observation to rectify", async () => {
    const abogado = doc({ estado: "A Validar Abogado", estado_valor: "A Validar Abogado", estado_ui: { kind: "select", requires_observacion: true, border: "border border-2 border-primary", options: [
      { value: "A Validar Abogado", label: "A Validar Abogado", selected: true, disabled: false }, { value: "Aceptado", label: "Aceptado", selected: false, disabled: false }, { value: "Rectificar", label: "Rectificar", selected: false, disabled: false }] } });
    serve(editor({ documentos: [abogado] }));
    const post = vi.spyOn(editorNative, "post").mockResolvedValue({ success: true });
    setup();
    await screen.findByText("Documentos requeridos");
    const estado = document.querySelector("#estado-11 select")!;
    fireEvent.change(estado, { target: { value: "Rectificar" } });
    const modal = await screen.findByRole("dialog");
    fireEvent.click(within(modal).getByRole("button", { name: "Guardar observaciones" }));
    expect(within(modal).getByText("Debe completar las observaciones.")).toBeTruthy();
    fireEvent.change(modal.querySelector("textarea")!, { target: { value: "Falta firma" } });
    fireEvent.click(within(modal).getByRole("button", { name: "Guardar observaciones" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/ajax/actualizar-estado/", { estado: "Rectificar", documento_id: "11", admision_id: "5", observacion: "Falta firma" }));
    expect(await screen.findByText("Estado actualizado con éxito.")).toBeTruthy();
    fireEvent.change(estado, { target: { value: "Aceptado" } });
    await waitFor(() => expect(post).toHaveBeenLastCalledWith("/ajax/actualizar-estado/", { estado: "Aceptado", documento_id: "11", admision_id: "5" }));
  });

  it("alerts the native error of a rejected state change and keeps the control", async () => {
    serve(editor());
    const post = vi.spyOn(editorNative, "post").mockResolvedValue({ success: false, error: "Sin permisos para modificar esta admision." });
    const alert = vi.spyOn(editorNative, "alert").mockImplementation(() => undefined);
    setup();
    await screen.findByText("Documentos requeridos");
    const estado = document.querySelector("#estado-11 select") as HTMLSelectElement;
    fireEvent.change(estado, { target: { value: "A Validar Abogado" } });
    await waitFor(() => expect(alert).toHaveBeenCalledWith("Error: Sin permisos para modificar esta admision."));
    expect(post).toHaveBeenCalledTimes(1);
    expect(estado.value).toBe("Documento adjunto");
  });

  it("edits the GDE number of an accepted document", async () => {
    serve(editor({ documentos: [doc({ estado: "Aceptado", estado_ui: { kind: "badge", badge: "bg-success" }, gde: { kind: "editable", value: null } })] }));
    const post = vi.spyOn(editorNative, "post").mockResolvedValueOnce({ success: false, error: "No tiene permisos para editar este documento.", valor_anterior: "" }).mockResolvedValueOnce({ success: true });
    const alert = vi.spyOn(editorNative, "alert").mockImplementation(() => undefined);
    setup();
    fireEvent.click((await screen.findByTitle("Agregar número GDE")).parentElement!);
    const input = document.getElementById("gde-input-11") as HTMLInputElement;
    fireEvent.change(input, { target: { value: " IF-9 " } });
    fireEvent.click(within(document.getElementById("gde-edit-11")!).getByTitle("Guardar"));
    await waitFor(() => expect(alert).toHaveBeenCalledWith("Error: No tiene permisos para editar este documento."));
    expect(post).toHaveBeenLastCalledWith("/ajax/actualizar-numero-gde/", { documento_id: "11", numero_gde: "IF-9" });
    fireEvent.click(within(document.getElementById("gde-edit-11")!).getByTitle("Guardar"));
    expect(await screen.findByText("Número GDE actualizado con éxito.")).toBeTruthy();
  });

  it("edits the agreement number and the PWA switch through the native endpoints", async () => {
    serve(editor());
    const post = vi.spyOn(editorNative, "post").mockResolvedValueOnce({ success: true, convenio_numero: 9 }).mockResolvedValueOnce({ success: false, error: "No tiene permisos para editar esta admision." });
    const alert = vi.spyOn(editorNative, "alert").mockImplementation(() => undefined);
    setup();
    fireEvent.click((await screen.findByTitle("Editar numero de convenio")).parentElement!);
    fireEvent.change(document.getElementById("convenio-numero-input")!, { target: { value: "9" } });
    fireEvent.click(within(document.getElementById("convenio-numero-edit")!).getByTitle("Guardar"));
    expect(await screen.findByText("Numero de convenio actualizado con exito.")).toBeTruthy();
    expect(post).toHaveBeenCalledWith("/ajax/actualizar-convenio-numero/", { admision_id: "5", convenio_numero: "9" });
    const toggle = screen.getByRole("switch") as HTMLInputElement;
    fireEvent.click(toggle);
    await waitFor(() => expect(alert).toHaveBeenCalledWith("Error: No tiene permisos para editar esta admision."));
    expect(toggle.checked).toBe(true);
  });

  it("edits the expediente number from the structured modal and validates the parts first", async () => {
    serve(editor());
    const post = vi.spyOn(editorNative, "post").mockResolvedValue({ success: true, num_expediente: "EX-2026-000000002- -APN-DGD#MCH" });
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Editar" }));
    const modal = await screen.findByRole("dialog");
    expect((document.getElementById("num-expediente-numero") as HTMLInputElement).value).toBe("000000001");
    fireEvent.change(document.getElementById("num-expediente-anio")!, { target: { value: "20" } });
    fireEvent.click(within(modal).getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Complete el año (4 dígitos), número (9 dígitos), repartición y organismo.")).toBeTruthy();
    expect(post).not.toHaveBeenCalled();
    fireEvent.change(document.getElementById("num-expediente-anio")!, { target: { value: "2026" } });
    fireEvent.change(document.getElementById("num-expediente-numero")!, { target: { value: "000000002" } });
    fireEvent.click(within(modal).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/ajax/actualizar-num-expediente/", { admision_id: "5", num_expediente: "EX-2026-000000002- -APN-DGD#MCH" }));
    expect(await screen.findByText("Número de expediente actualizado con éxito.")).toBeTruthy();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("uploads and deletes files through the native endpoints and reloads", async () => {
    serve(editor({ documentos: [doc({ archivo_id: null, archivo_url: null, puede_adjuntar: true, puede_eliminar: false, estado: "Pendiente", estado_valor: "Pendiente", estado_ui: { kind: "badge", badge: "bg-secondary" } }), doc({ id: "12", row_id: "4", documentacion_id: 4, archivo_id: 12, nombre: "Acta" })] }));
    const upload = vi.spyOn(editorNative, "upload").mockResolvedValue({ status: 200, body: JSON.stringify({ success: true }) });
    const remove = vi.spyOn(editorNative, "remove").mockResolvedValue({ success: true });
    setup();
    await screen.findByText("Documentos requeridos");
    fireEvent.change(document.getElementById("file-3")!, { target: { files: [new File(["x"], "e.pdf")] } });
    await waitFor(() => expect(upload).toHaveBeenCalledWith("/api/web/comedores/admisiones/5/documentacion/3/subir/", expect.any(FormData), expect.any(Function)));
    await waitFor(() => expect(webGet).toHaveBeenCalledWith(`${API}?r=1`, expect.anything()));
    fireEvent.change(screen.getByPlaceholderText("Nombre del documento adicional"), { target: { value: "Nota" } });
    fireEvent.change(document.getElementById("nuevoDocumentoArchivo")!, { target: { files: [new File(["x"], "n.pdf")] } });
    await waitFor(() => expect(upload).toHaveBeenCalledWith("/admision/5/documentacion/personalizada/agregar/", expect.any(FormData), expect.any(Function)));
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    const modal = await screen.findByRole("dialog");
    expect(within(modal).getByText("¿Seguro que quiere eliminar el siguiente archivo?")).toBeTruthy();
    fireEvent.click(within(modal).getByRole("button", { name: "Eliminar" }));
    await waitFor(() => expect(remove).toHaveBeenCalledWith("/api/web/comedores/admisiones/5/documentacion/4/eliminar/?archivo_id=12"));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("alerts when the additional document has no name", async () => {
    serve(editor());
    const alert = vi.spyOn(editorNative, "alert").mockImplementation(() => undefined);
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Adjuntar" }));
    expect(alert).toHaveBeenCalledWith("Por favor, escriba un nombre antes de adjuntar un archivo.");
  });

  it("forces the resync choice and confirms it through the native endpoint", async () => {
    serve(editor({ resync: { desincronizada: true, documentacion_desactualizada: false, solo_datos_organizacion: false, tipo_entidad_actual: "Asociación de Hecho", tipo_entidad_snapshot: "Personería Jurídica", documentos_modificados: ["Estatuto"], datos_modificados: [] } }));
    const post = vi.spyOn(editorNative, "post").mockResolvedValue({ success: true, redirect: EDITOR });
    const navigate = vi.spyOn(editorNative, "navigate").mockImplementation(() => undefined);
    setup();
    const modal = await screen.findByRole("dialog");
    expect(within(modal).getByText("El tipo de convenio fue actualizado desde el Legajo de la Organización", { selector: "h5" })).toBeTruthy();
    expect(within(modal).getByText("Asociación de Hecho")).toBeTruthy();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect((within(modal).getByRole("button", { name: "Aplicar" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(document.getElementById("accionResyncConvenio")!, { target: { value: "continuar" } });
    fireEvent.click(within(modal).getByRole("button", { name: "Aplicar" }));
    expect(within(modal).getByText(/Continuará gestionando la Admisión con la información ya procesada/)).toBeTruthy();
    fireEvent.click(within(modal).getByRole("button", { name: "Confirmar" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/admisiones/5/resync-convenio/", { accion: "continuar" }, { "X-Requested-With": "XMLHttpRequest" }));
    expect(navigate).toHaveBeenCalledWith(EDITOR);
  });

  it("draws the legal alerts and the rectify card from the native flags", async () => {
    serve(editor({ complementario_requerido: { observaciones: "Falta el informe" }, informe_a_subsanar: "Corregir CUIT", admision: { ...editor().admision, estado_legales: "A Rectificar", observaciones: "Rectificar X" } }));
    setup();
    expect(await screen.findByText("Falta el informe")).toBeTruthy();
    expect(screen.getByText("Corregir CUIT")).toBeTruthy();
    expect(screen.getByText("Rectificar X")).toBeTruthy();
    expect(screen.getByText("A Rectificar", { selector: "h2" })).toBeTruthy();
  });

  const embebido = (over: Record<string, unknown> = {}) => ({
    tipo: "base", admision_id: 5, informe_id: null, estado: "", comedor: "Comedor Sintético", permite_no_corresponde: false,
    fields: [field("nombre_organizacion", "Nombre de la organización", "Org", { required: false })], antecedentes: [], non_field_errors: [], campos_a_subsanar: [], observacion: "",
    publicacion: { plantilla: null, error: null, configuracion_faltante: false, detalle_copiable: "" },
    urls: { volver: EDITOR, previsualizar: null, reportar_faltante: "/comedores/admisiones/5/templates/reportar-faltante/", localidades: "/ajax/load_localidades/" },
    caratula: { num_expediente: null, borrador: false, fields: [
      field("caratula-expediente_anio", "Año"), field("caratula-expediente_numero", "Número"), field("caratula-expediente_reparticion", "Repartición"), field("caratula-expediente_organismo", "Organismo", "MCH")] },
    messages: [], ...over,
  });

  it("draws the embedded report and cover form and saves a draft through its action", async () => {
    serve(editor({ informe_embebido: embebido() }));
    webPost.mockImplementationOnce(() => ok([{ message: "Informe técnico guardado correctamente.", level: "success" }]));
    setup();
    expect(await screen.findByText("Informe Técnico y Carátula del Expediente")).toBeTruthy();
    expect(screen.getByText("Carátula del Expediente")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Guardar Borrador/ }).getAttribute("formnovalidate")).not.toBeNull();
    fireEvent.change(document.getElementById("id_nombre_organizacion")!, { target: { value: "Nueva Org" } });
    fireEvent.click(screen.getByText("Carátula del Expediente"));
    for (const [name, value] of [["anio", "2026"], ["numero", "123456789"], ["reparticion", "DGD"]]) fireEvent.change(document.getElementById(`id_caratula-expediente_${name}`)!, { target: { value } });
    fireEvent.click(screen.getByRole("button", { name: /Guardar Borrador/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalledWith("web/comedores/admisiones/5/acciones/informe-caratula/", expect.objectContaining({ action: "draft" }), expect.anything()));
    const values = (webPost.mock.calls[0][1] as { values: Record<string, unknown> }).values;
    expect(values.nombre_organizacion).toBe("Nueva Org");
    expect(values["caratula-expediente_anio"]).toBe("2026");
    expect(await screen.findByText("Informe técnico guardado correctamente.")).toBeTruthy();
    await waitFor(() => expect(webGet).toHaveBeenCalledWith(`${API}?r=1`, expect.anything()));
  });

  it("keeps the form and shows the field errors of a rejected final submit", async () => {
    serve(editor({ informe_embebido: embebido() }));
    webPost.mockImplementationOnce(() => Promise.resolve({ status: 400, data: { success: false, messages: [{ message: "No se pudo guardar el informe. Verificá que los campos obligatorios estén completos.", level: "error" }],
      non_field_errors: [], fields: [field("nombre_organizacion", "Nombre de la organización", "Org", { errors: ["Este campo es obligatorio."] })],
      caratula_fields: [field("caratula-expediente_anio", "Año", "", { errors: ["Año inválido."] }), field("caratula-expediente_numero", "Número"), field("caratula-expediente_reparticion", "Repartición"), field("caratula-expediente_organismo", "Organismo", "MCH")] } }));
    setup();
    await screen.findByText("Informe Técnico y Carátula del Expediente");
    for (const [name, value] of [["anio", "2026"], ["numero", "123456789"], ["reparticion", "DGD"]]) fireEvent.change(document.getElementById(`id_caratula-expediente_${name}`)!, { target: { value } });
    fireEvent.click(screen.getByRole("button", { name: /Finalizar/ }));
    expect(await screen.findByText("Este campo es obligatorio.")).toBeTruthy();
    expect(screen.getByText("Año inválido.")).toBeTruthy();
    expect(screen.getByText("No se pudo guardar el informe. Verificá que los campos obligatorios estén completos.")).toBeTruthy();
    expect(webGet).not.toHaveBeenCalledWith(`${API}?r=1`, expect.anything());
  });

  it("shows the caratulated expediente instead of the cover fields", async () => {
    serve(editor({ informe_embebido: embebido({ caratula: { num_expediente: "EX-2026-000000001- -APN-DGD#MCH", borrador: false, fields: null } }) }));
    setup();
    expect(await screen.findByText("Expediente caratulado:")).toBeTruthy();
    expect(screen.getByText("Para modificarlo usá la edición del número de expediente en la ficha de la admisión.")).toBeTruthy();
  });
});
