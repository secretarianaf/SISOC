import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { legalValid, revisionValid } from "./admisionesLegales";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const VER = "/comedores/admisiones/legales/ver/5";
const REVISION = "/comedores/admisiones/legales/revisar-complementario/5";
const API = "web/comedores/admisiones/legales/5/";

type Over = Record<string, unknown>;
const field = (name: string, label: string, over: Over = {}) => ({
  name, label, kind: "text", required: true, value: "", help_text: "", errors: [], id: `id_${name}`, attrs: { class: "form-control", maxlength: "100" }, ...over,
});
const form = (fields: unknown[] = [], nonField: string[] = []) => ({ fields, non_field_errors: nonField });
const part = (name: string, label: string, value = "") => field(name, label, { value, attrs: { class: "form-control", autocomplete: "off", inputmode: "numeric", maxlength: "9" } });
const expediente = (over: Over = {}) => form([part("expediente_anio", "Año"), part("expediente_numero", "Número"), part("expediente_reparticion", "Repartición"), part("expediente_organismo", "Organismo", "MCH")], (over.non as string[]) ?? []);
const pv = () => form([part("pv_anio", "Año"), part("pv_numero", "Número"), part("pv_reparticion", "Repartición"), part("pv_organismo", "Organismo", "MCH")]);
const select = (name: string, label: string, choices: string[][], over: Over = {}) => field(name, label, { kind: "select", choices: choices.map(([value, text]) => ({ value, label: text })), attrs: {}, ...over });
const FORMS = {
  rectificar: form([field("observaciones", "Observaciones", { kind: "textarea", attrs: { class: "form-control", rows: "4", cols: "40", placeholder: "Detalle sus observaciones." } })]),
  numero_expediente: expediente(), primera_providencia: form([select("cantidad_espacios", "Cantidad de Espacios", [["", "---------"], ["hasta_5", "Hasta 5 Espacios"]])]),
  segunda_providencia: pv(), gde_pv_primera: pv(), gde_pv_segunda: pv(),
  intervencion_juridicos: form([
    select("intervencion_juridicos", "Intervención Jurídicos", [["", "---------"], ["validado", "Validado"], ["rechazado", "Rechazado"]]),
    select("rechazo_juridicos_motivo", "Motivo Rechazo Jurídicos", [["", "---------"], ["providencia", "Por providencia"], ["dictamen", "Por dictamen"]], { required: false }),
    select("dictamen_motivo", "Tipo de observación", [["", "---------"], ["observacion en informe técnico", "Observación en informe técnico"]], { required: false }),
  ]),
  if_proyecto_convenio: form([field("numero_if", "Número de IF de Proyecto de Convenio")]),
  convenio: form([field("numero_convenio", "Numero convenio"), field("archivo_convenio", "Archivo convenio", { kind: "file", attrs: { class: "form-control" } })]),
  reinicio_expediente: form([field("observaciones_reinicio_expediente", "Observaciones reinicio de expediente", { kind: "textarea", attrs: { rows: "10", cols: "40" } })]),
  solicitar_complementario: form([field("observaciones_informe_tecnico_complementario", "Observaciones informe técnico complementario", { kind: "textarea", attrs: { rows: "10", cols: "40" } })]),
};
const boton = (key: string, texto: string, modal: string | null, clase = "btn-primary", url: string | null = null) => ({ key, texto, modal, clase, url });
const legal = (over: Over = {}) => ({
  id: 5, titulo: { num_expediente: "EX-2026-000000001- -APN-DGD#MCH", archivada: false, rechazo: "", estado: "Enviado a Legales" },
  urls: { lista: "/comedores/admisiones/legales/listar", pagina: VER },
  botones: [boton("rectificar", "Rectificar", "modalRectificar", "btn-warning"), boton("agregar_expediente", "Agregar Número de expediente", "modalLegalesNumIF")],
  expediente: { estado: "Enviado a Legales", numero: "Sin información", proyecto: null, primera_providencia: null, segunda_providencia: null, intervencion: null, dictamen: null, disposicion: null, convenio: null },
  admision: { tipo: "Incorporación", tipo_convenio: "Convenio base", estado: "Rectificar", fecha: "01/10/2026", vencimiento_mandatos: "-", num_expediente: "Sin información", informe_pdf: "/media/informe.pdf", complementarios: [{ fecha: "02/10/2026", estado: "Borrador", pdf: null }], complementario_final: null },
  comedor: { id: 7, nombre: "Comedor Sintético", url: "/comedores/7", tipo: "Sin información", programa: "Sin información", organizacion: "Org Uno", ubicacion: "Chaco - Sin información - Sin información", calle: "Sin información Sin información - Piso: Sin información " },
  es_judicializado: false, tipo_admision: "Incorporación",
  documentos: [{ id: 1, nombre: "Estatuto", archivo_url: "/media/estatuto.pdf" }],
  historial_estados: { headers: [{ title: "Fecha", width: "25%" }, { title: "Estado anterior", width: "30%" }, { title: "Estado nuevo", width: "30%" }, { title: "Usuario", width: "15%" }], rows: [], page: { is_paginated: false, number: 1, count: 0, has_rows: false, previous: null, next: null, range: [], param: "historial_estados_page", query_without_page: "" } },
  forms: FORMS, messages: [], ...over,
});
const revision = (over: Over = {}) => ({ id: 5, comedor: "Comedor Sintético", urls: { legal: VER }, informe: { estado: "Enviado a Validación", creado_por: "tec1", fecha: "01/10/2026 10:00", campos: [{ campo: "plazo", value: "12" }] }, messages: [], ...over });

function serve(page: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: page, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const reply = (status: number, data: unknown) => webPost.mockResolvedValueOnce({ status, data });
const lastBody = () => webPost.mock.calls.at(-1)![1] as URLSearchParams | FormData;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => cleanup());

describe("Legal admision detail route (AD03.03)", () => {
  it("owns the native legal detail and review pages without a trailing slash", () => {
    expect(findRoute(VER)?.params).toEqual({ page: "ver", id: "5" });
    expect(findRoute(REVISION)?.params).toEqual({ page: "revision", id: "5" });
    for (const other of [`${VER}/`, "/comedores/admisiones/legales/listar", "/comedores/admisiones/tecnicos/editar/5"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-admisiones-legales");
    }
  });

  it("renders the heading, the cards, the buttons and the empty history like the template", async () => {
    serve(legal());
    setup(`${VER}?historial_estados_page=2`);
    await screen.findByText("Estado expediente:");
    expect(webGet).toHaveBeenCalledWith(`${API}?historial_estados_page=2`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Expediente: EX-2026-000000001- -APN-DGD#MCH"));
    expect(screen.getByRole("button", { name: "Rectificar" }).className).toBe("btn btn-warning mr-1");
    expect(screen.getByRole("button", { name: "Agregar Número de expediente" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Comedor Sintético" }).getAttribute("href")).toBe("/comedores/7");
    expect(screen.getByRole("link", { name: "Ver Archivo" }).getAttribute("href")).toBe("/media/estatuto.pdf");
    expect(screen.getByText("02/10/2026 - Borrador")).toBeTruthy();
    expect(screen.getByText("No hay cambios de estado registrados")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Expedientes" }).getAttribute("href")).toBe("/comedores/admisiones/legales/listar");
  });

  it("shows the archived heading and the link of the review button", async () => {
    serve(legal({
      titulo: { num_expediente: "EX-1", archivada: true, rechazo: "Por providencia", estado: "Archivado" },
      botones: [boton("revisar_informe_complementario", "Revisar Informe Complementario", null, "btn-info", REVISION)],
    }));
    setup(VER);
    expect(await screen.findByText("Rechazado: Por providencia / Enviado a Archivo")).toBeTruthy();
    const enlace = screen.getByRole("link", { name: "Revisar Informe Complementario" });
    expect(enlace.getAttribute("href")).toBe(REVISION);
    expect(enlace.className).toBe("btn btn-info mr-1");
  });

  it("posts a modal to its action endpoint, then rereads the page and shows the native message", async () => {
    serve(legal());
    setup(VER);
    fireEvent.click(await screen.findByRole("button", { name: "Rectificar" }));
    const modal = await screen.findByRole("dialog");
    fireEvent.change(within(modal).getByLabelText("Observaciones:"), { target: { value: "Falta nota" } });
    serve(legal({ botones: [], messages: [] }));
    reply(200, { messages: [{ message: "Enviado a rectificar con éxito.", level: "success" }], estado_legales: "A Rectificar", botones: [] });
    fireEvent.click(within(modal).getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText("Enviado a rectificar con éxito.")).toBeTruthy();
    expect(webPost.mock.calls[0][0]).toBe(`${API}acciones/rectificar/`);
    expect((lastBody() as URLSearchParams).get("observaciones")).toBe("Falta nota");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(screen.queryByRole("button", { name: "Rectificar" })).toBeNull();
  });

  it("keeps the modal open with the field errors of a 400 and changes nothing else", async () => {
    serve(legal());
    setup(VER);
    fireEvent.click(await screen.findByRole("button", { name: "Agregar Número de expediente" }));
    const modal = await screen.findByRole("dialog");
    expect(modal.querySelectorAll(".expediente-estructurado-grid .input-group").length).toBe(3);
    fireEvent.change(modal.querySelector("#id_expediente_anio")!, { target: { value: "20" } });
    const rejected = expediente({ non: ["El expediente ya pertenece a la admisión #9; comedor: C; organización: O; tipo: Incorporación."] });
    (rejected.fields[0] as { errors: string[]; value: string }).errors = ["Asegúrese de que este valor tenga al menos 4 caracteres."];
    (rejected.fields[0] as { value: string }).value = "20";
    reply(400, { form: "numero_expediente", modal: "modalLegalesNumIF", ...rejected });
    fireEvent.click(within(modal).getByRole("button", { name: "Guardar" }));
    expect(await within(modal).findByText("Asegúrese de que este valor tenga al menos 4 caracteres.")).toBeTruthy();
    expect(within(modal).getByText(/El expediente ya pertenece/)).toBeTruthy();
    expect((modal.querySelector("#id_expediente_anio") as HTMLInputElement).value).toBe("20");
    expect(screen.getByRole("dialog")).toBe(modal);
    expect(webGet).toHaveBeenCalledTimes(2);
  });

  it("shows the Jurídicos motivos only while rejected and requires the one it needs", async () => {
    serve(legal({ botones: [boton("intervencion_juridicos", "Intervención Jurídicos", "modalIntervencionJuridicos")] }));
    setup(VER);
    fireEvent.click(await screen.findByRole("button", { name: "Intervención Jurídicos" }));
    const modal = await screen.findByRole("dialog");
    const motivo = modal.querySelector("#id_rechazo_juridicos_motivo") as HTMLSelectElement;
    const dictamen = modal.querySelector("#id_dictamen_motivo") as HTMLSelectElement;
    expect(modal.querySelector<HTMLElement>("#motivoRechazoField")!.style.display).toBe("none");
    fireEvent.change(modal.querySelector("#id_intervencion_juridicos")!, { target: { value: "rechazado" } });
    expect(modal.querySelector<HTMLElement>("#motivoRechazoField")!.style.display).toBe("block");
    expect(motivo.required).toBe(true);
    expect(dictamen.required).toBe(false);
    fireEvent.change(motivo, { target: { value: "dictamen" } });
    expect(modal.querySelector<HTMLElement>("#motivoDictamenField")!.style.display).toBe("block");
    expect(dictamen.required).toBe(true);
  });

  it("sends the agreement file as multipart and the PV parts as the structured fields", async () => {
    serve(legal({ botones: [boton("convenio", "Convenio", "modalConvenio"), boton("gde_pv_primera", "Cargar número de GDE PV", "modalGDEPVPrimera")] }));
    setup(VER);
    fireEvent.click(await screen.findByRole("button", { name: "Convenio" }));
    let modal = await screen.findByRole("dialog");
    fireEvent.change(modal.querySelector("#id_numero_convenio")!, { target: { value: "55" } });
    const archivo = new File(["pdf"], "convenio.pdf", { type: "application/pdf" });
    fireEvent.change(modal.querySelector("#id_archivo_convenio")!, { target: { files: [archivo] } });
    reply(200, { messages: [], estado_legales: "Acompañamiento Pendiente", botones: [] });
    // jsdom does not keep the files of a synthetic change event, so its `required` check would block the click.
    fireEvent.submit(modal.querySelector("form")!);
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    const body = lastBody() as FormData;
    expect(webPost.mock.calls[0][0]).toBe(`${API}acciones/convenio/`);
    expect(body.get("numero_convenio")).toBe("55");
    expect(body.get("archivo_convenio")).toBeInstanceOf(File);
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());

    fireEvent.click(await screen.findByRole("button", { name: "Cargar número de GDE PV" }));
    modal = await screen.findByRole("dialog");
    expect(modal.querySelectorAll(".input-group").length).toBe(3);
    fireEvent.change(modal.querySelector("#id_pv_anio")!, { target: { value: "2026" } });
    reply(409, { messages: [{ message: "No se puede cargar el GDE PV: el expediente está en estado 'X'.", level: "error" }], estado_legales: "X", botones: [] });
    fireEvent.click(within(modal).getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText(/No se puede cargar el GDE PV/)).toBeTruthy();
    expect(webPost.mock.calls[1][0]).toBe(`${API}acciones/gde-pv-primera/`);
    expect((lastBody() as URLSearchParams).get("pv_anio")).toBe("2026");
  });

  it("generates the first providence with the judicial fields only for judicialized comedores", async () => {
    serve(legal({ botones: [boton("primera_providencia", "Generar Primera Providencia", "modalPrimeraProvidencia")] }));
    setup(VER);
    fireEvent.click(await screen.findByRole("button", { name: "Generar Primera Providencia" }));
    const modal = await screen.findByRole("dialog");
    expect(within(modal).getByDisplayValue("Primera Providencia")).toBeTruthy();
    expect(within(modal).getByDisplayValue("No")).toBeTruthy();
    expect(modal.querySelector("#id_caratula_causa")).toBeNull();
  });

  it("validates the envelopes", () => {
    expect(legalValid(legal())).toBe(true);
    expect(legalValid({ ...legal(), forms: { ...FORMS, convenio: { fields: [{ name: "x" }], non_field_errors: [] } } })).toBe(false);
    expect(legalValid({ ...legal(), urls: { lista: "https://evil.example", pagina: VER } })).toBe(false);
    expect(legalValid({ ...legal(), documentos: [{ id: "1", nombre: "x", archivo_url: null }] })).toBe(false);
    expect(revisionValid(revision())).toBe(true);
    expect(revisionValid({ ...revision(), informe: { estado: "x" } })).toBe(false);
  });
});

describe("Complementary report review (AD03.03)", () => {
  it("shows the changes and asks for observations only when rectifying", async () => {
    serve(revision());
    setup(REVISION);
    await screen.findByText("Cambios Realizados por el Técnico");
    expect(webGet).toHaveBeenCalledWith(`${API}complementario/revision/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Revisar Informe Complementario: Comedor Sintético"));
    expect(screen.getByText("plazo")).toBeTruthy();
    const observaciones = document.getElementById("observaciones_complementario") as HTMLTextAreaElement;
    expect(document.getElementById("observaciones-group")!.style.display).toBe("none");
    fireEvent.click(document.getElementById("rectificar")!);
    expect(document.getElementById("observaciones-group")!.style.display).toBe("block");
    expect(observaciones.required).toBe(true);
    fireEvent.change(observaciones, { target: { value: "Corregir" } });
    fireEvent.click(document.getElementById("validar")!);
    expect(observaciones.required).toBe(false);
    expect(observaciones.value).toBe("");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe(VER);
  });

  it("posts the decision to the native review endpoint", async () => {
    serve(revision());
    reply(200, { redirect: VER, estado_legales: "Informe Complementario Solicitado" });
    setup(REVISION);
    fireEvent.click(await screen.findByLabelText(/Rectificar - Solicitar/));
    fireEvent.change(document.getElementById("observaciones_complementario")!, { target: { value: "Corregir" } });
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe(`${API}complementario/revision/`);
    const body = lastBody() as URLSearchParams;
    expect(body.get("accion_complementario")).toBe("rectificar");
    expect(body.get("observaciones_complementario")).toBe("Corregir");
  });

  it("explains that there is nothing to review", async () => {
    serve(revision({ informe: null }));
    setup(REVISION);
    expect(await screen.findByText(/No se encontró un informe complementario pendiente de revisión/)).toBeTruthy();
  });
});
