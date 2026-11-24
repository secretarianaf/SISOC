import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { detalleValid, rendicionDetalleNavigation, type RendicionDetalleData } from "./rendicionMensualDetalle";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const PREFIX = "/rendicioncuentasmensual/rendicioncuentasmensual";
const DETALLE = `${PREFIX}/detalle/5/`;
const API = "web/comedores/rendicioncuentasmensual/5/";

const archivo = (id: number, over: Record<string, unknown> = {}) => ({
  id, nombre: `doc-${id}`, estado: "presentado", badge: "pendiente", estado_text: "Presentado", observaciones: "", fecha: "11/11/2026 10:30",
  visualizado: false, visualizacion_title: "Por None el ", ver_url: `${PREFIX}/documento/${id}/ver/`, subsanaciones: [], ...over,
});
const capabilities = (over: Record<string, boolean> = {}) => ({
  puede_revisar_documentos: false, puede_solicitar_faltantes: false, puede_revision_territorial: false, puede_revision_auditoria: false, puede_auditoria: false,
  puede_regularizacion: false, puede_editar_datos: false, puede_gestionar_auditoria: false, mostrar_acciones_proceso: false, mostrar_documentacion_auditoria: false,
  puede_descargar_pdf: false, ...over,
});
const detalle = (over: Partial<RendicionDetalleData> = {}, rendicion: Record<string, unknown> = {}): RendicionDetalleData => ({
  rendicion: {
    id: 5, numero: "2", nombre: "Rendición marzo", proyecto: "P-77", organizacion: "Org <Norte>", convenio: "P01", linea_programatica: "Abordaje Comunitario - Linea Tradicional",
    mes_anio: "3 / 2026", periodo: "01/03/2026 - 31/03/2026", fecha_creacion: "01/03/2026 09:00", ultima_modificacion: "11/11/2026 10:30",
    comedores_relacionados: ["Comedor A", "Comedor B"], usuario_creador: "Ana Pérez", usuario_ultima_modificacion: "Sin dato", observaciones: "",
    etapa_proceso: "revision_documentacion", subestado_proceso: "en_curso", estado_proceso_display: "Revisión Territorial en curso", validada: "No",
    genera_acta: false, genera_acta_text: "Sin definir", resultado_auditoria: "", acta_auditoria_url: null, documento_regularizacion_url: null, ...rendicion,
  },
  capabilities: capabilities(),
  documentacion: [
    { codigo: "formulario_ii", label: "Formulario II - Resumen", required: true, historial_plano: false, solicitud_faltante: null, archivos: [archivo(11)] },
    { codigo: "otros", label: "Documentación Adicional", required: false, historial_plano: true, solicitud_faltante: { observaciones: "Subir extracto" },
      archivos: [archivo(21, { subsanaciones: [archivo(20, { estado_text: "Subsanado", observaciones: "Falta firma" })] })] },
    { codigo: "extracto_bancario", label: "Extracto Bancario", required: true, historial_plano: false, solicitud_faltante: null, archivos: [] },
  ],
  resumenes: [],
  urls: { volver: `${PREFIX}/listado/`, update: `${PREFIX}/editar/5/`, auditoria: `${PREFIX}/auditoria/5/`, pdf_solicitar: `${DETALLE}descargar-pdf/solicitar/`, pdf_estado: `${DETALLE}descargar-pdf/estado/` },
  messages: [],
  ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup() {
  window.history.replaceState({}, "", DETALLE);
  return render(<App />);
}
const json = (data: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(data), { status }));

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("Rendición mensual detail route", () => {
  it("owns only the native detail path with the repeated prefix", () => {
    expect(findRoute(DETALLE)?.route.name).toBe("comedores-rendicion-mensual-detalle");
    for (const other of [`${PREFIX}/detalle/5`, `${PREFIX}/detalle/x/`, `${PREFIX}/detalle/5/descargar-pdf/`, `${PREFIX}/5/`, "/rendicioncuentasmensual/detalle/5/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-rendicion-mensual-detalle");
    }
  });

  it("renders the native header, data card, badges and Volver", async () => {
    serve(detalle());
    setup();
    await screen.findByRole("heading", { level: 2, name: "Rendicion 2" });
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Detalle de Rendicion de Cuenta"));
    expect(document.getElementById("rendicion-estado-badge")?.className).toBe("badge-validacion pendiente");
    expect(screen.getByRole("link", { name: "Rendiciones" }).getAttribute("title")).toBe("Ver listado de rendiciones");
    expect(screen.getByRole("link", { name: "Volver" }).getAttribute("href")).toBe(`${PREFIX}/listado/`);
    for (const label of ["Nombre de rendición", "Proyecto", "Organizacion", "Convenio", "Linea Programatica", "Mes / Ano", "Periodo", "Fecha de creacion", "Ultima modificacion",
      "Comedores relacionados con el proyecto", "Usuario creador", "Usuario ultima modificacion"]) {
      expect(screen.getByText(label).tagName).toBe("SMALL");
    }
    expect(screen.getByText("Org <Norte>").tagName).toBe("STRONG");
    expect(screen.getByText("Comedor B").className).toBe("badge bg-light text-dark border");
    expect(screen.queryByText("Observaciones")).toBeNull();
    expect(screen.queryByText("Acciones del proceso")).toBeNull();
    expect(screen.queryByRole("link", { name: "Editar Datos de Rendición" })).toBeNull();
    expect(document.querySelector("#rendicion-download-action")?.children.length).toBe(0);
    expect(screen.getByText(/Cada documento presentado puede validarse/).textContent).not.toContain("Podés cambiar");
  });

  it("maps the finished and pending-corrections states and the warning", async () => {
    serve(detalle({}, { subestado_proceso: "pendiente_correcciones", observaciones: "Obs generales", comedores_relacionados: [] }));
    setup();
    await screen.findByText("La rendición tiene documentación pendiente de correcciones.");
    expect(document.getElementById("rendicion-estado-badge")?.className).toBe("badge-validacion no-validado");
    expect(screen.getByText("Sin comedores relacionados").tagName).toBe("STRONG");
    expect(screen.getByText("Obs generales").tagName).toBe("STRONG");
    cleanup();
    serve(detalle({}, { subestado_proceso: "finalizada" }));
    setup();
    await waitFor(() => expect(document.getElementById("rendicion-estado-badge")?.className).toBe("badge-validacion validado"));
  });

  it("draws the documentation table with categories, history and missing-document badges", async () => {
    serve(detalle());
    setup();
    await screen.findByText("Formulario II - Resumen");
    expect(screen.getAllByText("Obligatorio")[0].className).toBe("badge bg-warning text-dark");
    expect(screen.getByText("Opcional").className).toBe("badge bg-secondary");
    expect(screen.getAllByText("1 archivo")).toHaveLength(2);
    expect(screen.getByText("0 archivos")).toBeTruthy();
    expect(document.getElementById("solicitud-faltante-badge-otros")?.className).toBe("badge bg-danger");
    expect(document.getElementById("solicitud-faltante-badge-formulario_ii")?.className).toBe("badge bg-danger d-none");
    expect(document.getElementById("solicitud-faltante-observacion-otros")?.textContent).toBe("Observaciones: Subir extracto");
    expect(screen.getByText("No hay archivos cargados en esta categoria.").getAttribute("colspan")).toBe("5");
    const historico = screen.getByText("doc-20").closest("tr")!;
    expect(historico.className).toBe("documento-detail-row historial-documento-row");
    expect(within(historico).getByText("Subsanado").className).toBe("historial-documento-estado");
    expect(within(historico).getByText("Obs:").parentElement?.textContent).toBe("Obs: Falta firma");
    const principal = screen.getByText("doc-11").closest("tr")!;
    expect(within(principal).getByText("Presentado").className).toBe("badge-validacion pendiente");
    const ver = within(principal).getByRole("link", { name: "Ver" });
    expect(ver.getAttribute("href")).toBe(`${PREFIX}/documento/11/ver/`);
    expect(ver.getAttribute("target")).toBe("_blank");
    expect(within(principal).getByText("Sin visualizar").className).toBe("badge bg-secondary");
    expect(principal.querySelector("select")).toBeNull();
  });

  it("shows the viewed badge with its tooltip and the non-plain history badges", async () => {
    const data = detalle();
    data.documentacion[0].archivos = [archivo(11, { visualizado: true, visualizacion_title: "Por ana el 11/11/2026 10:30", observaciones: "Corregir",
      subsanaciones: [archivo(10, { badge: "pendiente", estado_text: "Subsanado", observaciones: "Vieja" })] })];
    serve(data);
    setup();
    expect((await screen.findByText("Visualizado")).getAttribute("title")).toBe("Por ana el 11/11/2026 10:30");
    const historico = screen.getByText("doc-10").closest("tr")!;
    expect(historico.className).toBe("documento-detail-row");
    expect(within(historico).getByText("Subsanado").className).toBe("badge-validacion pendiente");
    expect(document.getElementById("observaciones-display-10")?.textContent).toBe("Observaciones: Vieja");
    expect(document.getElementById("observaciones-display-11")?.textContent).toBe("Observaciones: Corregir");
  });

  it("shows the edit link, the audit management link and the stage forms with their CSRF token", async () => {
    serve(detalle({ capabilities: capabilities({ puede_editar_datos: true, mostrar_acciones_proceso: true, puede_revision_territorial: true, puede_gestionar_auditoria: true }) },
      { subestado_proceso: "pendiente" }));
    setup();
    expect((await screen.findByRole("link", { name: "Editar Datos de Rendición" })).getAttribute("href")).toBe(`${PREFIX}/editar/5/`);
    expect(screen.getByRole("link", { name: "Gestionar Auditoría" }).getAttribute("href")).toBe(`${PREFIX}/auditoria/5/`);
    const form = screen.getByRole("button", { name: "Iniciar revisión territorial" }).closest("form")!;
    expect(form.getAttribute("method")).toBe("post");
    expect(form.getAttribute("action")).toBeNull();
    expect(form.querySelector<HTMLInputElement>("[name=accion_proceso]")?.value).toBe("iniciar_revision_territorial");
    expect(form.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")?.value).toBe("synthetic-csrf-token");
    expect(screen.queryByRole("button", { name: "Finalizar revisión territorial" })).toBeNull();
  });

  it("offers each stage button for its own stage and state", async () => {
    serve(detalle({ capabilities: capabilities({ mostrar_acciones_proceso: true, puede_revision_auditoria: true }) }, { etapa_proceso: "revision_auditoria", subestado_proceso: "en_curso" }));
    setup();
    expect(await screen.findByRole("button", { name: "Finalizar revisión para Carga" })).toBeTruthy();
    cleanup();
    serve(detalle({ capabilities: capabilities({ mostrar_acciones_proceso: true, puede_regularizacion: true }) }, { etapa_proceso: "auditoria", subestado_proceso: "finalizada_con_observaciones" }));
    setup();
    expect(await screen.findByRole("button", { name: "Iniciar regularización" })).toBeTruthy();
    cleanup();
    serve(detalle({ capabilities: capabilities({ mostrar_acciones_proceso: true, puede_regularizacion: true }) }, { etapa_proceso: "regularizacion", subestado_proceso: "en_curso" }));
    setup();
    const finalizar = (await screen.findByRole("button", { name: "Finalizar regularización" })).closest("form")!;
    expect(finalizar.getAttribute("enctype")).toBe("multipart/form-data");
    expect(finalizar.querySelector<HTMLInputElement>("input[type=file]")?.name).toBe("documento_regularizacion");
    expect(screen.getByText("Acta Complementaria").tagName).toBe("LABEL");
  });

  it("shows the audit card with the acta links and the included rendiciones", async () => {
    serve(detalle({
      capabilities: capabilities({ mostrar_documentacion_auditoria: true }),
      resumenes: [{ id: 5, actual: true, titulo: "Rendición 2 · P01 · 01/03/2026 al 31/03/2026", documentos: [{ categoria: "Formulario II - Resumen", nombre: "doc-11", estado_text: "Validado", ver_url: `${PREFIX}/documento/11/ver/` }] }],
    }, { etapa_proceso: "auditoria", subestado_proceso: "finalizada_con_observaciones", validada: "Sí", genera_acta: true, genera_acta_text: "Sí",
      resultado_auditoria: "Auditoría finalizada con observaciones", acta_auditoria_url: "/media/acta.pdf", documento_regularizacion_url: "/media/compl.pdf" }));
    setup();
    await screen.findByRole("heading", { level: 5, name: "Auditoría" });
    expect(screen.getByText("Auditoría finalizada con observaciones").tagName).toBe("STRONG");
    expect(screen.getByRole("link", { name: "Acta de Auditoría" }).getAttribute("target")).toBe("_blank");
    expect(screen.getByRole("link", { name: "Acta Complementaria" }).getAttribute("href")).toBe("/media/compl.pdf");
    expect(screen.getByRole("heading", { level: 6, name: "Documentación de las rendiciones incluidas" })).toBeTruthy();
    expect(screen.getByText("Rendición 2 · P01 · 01/03/2026 al 31/03/2026").tagName).toBe("SUMMARY");
  });

  it("sends a missing-document request like the native script and updates the category", async () => {
    const fetchMock = vi.fn(() => json({ success: true, message: "Solicitud de documento faltante registrada.", solicitud: { categoria: "formulario_ii", observaciones: "<b>Falta</b>" } }));
    vi.stubGlobal("fetch", fetchMock);
    serve(detalle({ capabilities: capabilities({ puede_solicitar_faltantes: true }) }));
    setup();
    const form = (await screen.findAllByRole("button", { name: "Solicitar documento faltante" }))[0].closest("form")!;
    fireEvent.change(within(form).getByLabelText("Observaciones para documento faltante"), { target: { value: "<b>Falta</b>" } });
    fireEvent.submit(form);
    await waitFor(() => expect(document.getElementById("solicitud-faltante-badge-formulario_ii")?.className).toBe("badge bg-danger"));
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(window.location.href);
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>)["X-Requested-With"]).toBe("XMLHttpRequest");
    const body = init.body as FormData;
    expect([body.get("solicitar_categoria"), body.get("observaciones_faltante"), body.get("csrfmiddlewaretoken")]).toEqual(["formulario_ii", "<b>Falta</b>", "synthetic-csrf-token"]);
    expect(document.getElementById("solicitud-faltante-observacion-formulario_ii")?.textContent).toBe("Observaciones: <b>Falta</b>");
    expect(document.getElementById("solicitud-faltante-row-formulario_ii")?.className).toBe("documento-detail-row");
    expect(document.getElementById("revision-feedback")?.className).toBe("alert mb-3 alert-success");
    expect(document.getElementById("revision-feedback")?.textContent).toBe("Solicitud de documento faltante registrada.");
    expect((within(form).getByLabelText("Observaciones para documento faltante") as HTMLInputElement).value).toBe("");
  });

  it("shows the server message when the request is rejected", async () => {
    vi.stubGlobal("fetch", vi.fn(() => json({ success: false, message: "Ya existe una solicitud." }, 400)));
    serve(detalle({ capabilities: capabilities({ puede_solicitar_faltantes: true }) }));
    setup();
    const form = (await screen.findAllByRole("button", { name: "Solicitar documento faltante" }))[0].closest("form")!;
    fireEvent.change(within(form).getByLabelText("Observaciones para documento faltante"), { target: { value: "x" } });
    fireEvent.submit(form);
    await waitFor(() => expect(document.getElementById("revision-feedback")?.className).toBe("alert mb-3 alert-danger"));
    expect(document.getElementById("revision-feedback")?.textContent).toBe("Ya existe una solicitud.");
    expect(document.getElementById("solicitud-faltante-badge-formulario_ii")?.className).toBe("badge bg-danger d-none");
  });

  it("toggles the review controls like actualizarFilaRevision and saves through the native POST", async () => {
    const reload = vi.spyOn(rendicionDetalleNavigation, "reload").mockImplementation(() => undefined);
    const fetchMock = vi.fn(() => json({ success: true, message: "Selección guardada. Se confirmará al finalizar la revisión." }));
    vi.stubGlobal("fetch", fetchMock);
    serve(detalle({ capabilities: capabilities({ puede_revisar_documentos: true }) }));
    setup();
    await screen.findByText("Formulario II - Resumen");
    expect(screen.getByText(/Podés cambiar las selecciones guardadas hasta presionar Finalizar Revisión\./)).toBeTruthy();
    const select = document.querySelector<HTMLSelectElement>('select[data-documento-id="11"]')!;
    const inline = document.getElementById("guardar-revision-inline-11")!;
    const obsButton = document.getElementById("guardar-revision-observaciones-11")!;
    const row = document.getElementById("observaciones-row-11")!;
    const textarea = document.getElementById("observaciones-11") as HTMLTextAreaElement;
    expect(select.value).toBe("");
    expect([inline.className.includes("d-none"), obsButton.className.includes("d-none"), row.className.includes("d-none")]).toEqual([true, true, true]);
    expect(textarea.required).toBe(false);
    fireEvent.change(select, { target: { value: "subsanar" } });
    await waitFor(() => expect(row.className.includes("d-none")).toBe(false));
    expect(textarea.required).toBe(true);
    expect([inline.className.includes("d-none"), obsButton.className.includes("d-none")]).toEqual([true, false]);
    fireEvent.change(textarea, { target: { value: "  Falta la firma  " } });
    fireEvent.change(select, { target: { value: "validado" } });
    await waitFor(() => expect(inline.className.includes("d-none")).toBe(false));
    expect(textarea.value).toBe("");
    fireEvent.change(select, { target: { value: "subsanar" } });
    fireEvent.change(textarea, { target: { value: "  Falta la firma  " } });
    fireEvent.submit(document.getElementById("revision-documento-11")!);
    await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(window.location.href);
    const body = init.body as FormData;
    expect([body.get("documento_id"), body.get("estado"), body.get("observaciones"), body.get("csrfmiddlewaretoken")]).toEqual(["11", "subsanar", "Falta la firma", "synthetic-csrf-token"]);
    expect((init.headers as Record<string, string>)["X-Requested-With"]).toBe("XMLHttpRequest");
  });

  it("keeps the saved draft selected and the editor rows for a document already under review", async () => {
    const data = detalle({ capabilities: capabilities({ puede_revisar_documentos: true }) });
    data.documentacion[0].archivos = [archivo(11, { estado: "subsanar", badge: "no-validado", estado_text: "A Subsanar", observaciones: "Falta firma" })];
    serve(data);
    setup();
    await screen.findByText("doc-11");
    expect(document.querySelector<HTMLSelectElement>('select[data-documento-id="11"]')!.value).toBe("subsanar");
    expect((document.getElementById("observaciones-11") as HTMLTextAreaElement).value).toBe("Falta firma");
    expect(document.getElementById("observaciones-display-11")?.textContent).toBe("Observaciones: Falta firma");
    expect(document.getElementById("observaciones-row-11")?.className).toBe("documento-detail-row");
  });

  it("shows the server error and does not reload when saving a review fails", async () => {
    const reload = vi.spyOn(rendicionDetalleNavigation, "reload").mockImplementation(() => undefined);
    vi.stubGlobal("fetch", vi.fn(() => json({ success: false, message: "No tiene permisos para revisar documentos." }, 403)));
    serve(detalle({ capabilities: capabilities({ puede_revisar_documentos: true }) }));
    setup();
    await screen.findByText("doc-11");
    fireEvent.change(document.querySelector('select[data-documento-id="11"]')!, { target: { value: "validado" } });
    fireEvent.submit(document.getElementById("revision-documento-11")!);
    await waitFor(() => expect(document.getElementById("revision-feedback")?.textContent).toBe("No tiene permisos para revisar documentos."));
    expect(document.getElementById("revision-feedback")?.className).toBe("alert mb-3 alert-danger");
    expect(reload).not.toHaveBeenCalled();
  });

  it("requests the PDF, polls its state and downloads it through the native URL", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const assign = vi.spyOn(rendicionDetalleNavigation, "assign").mockImplementation(() => undefined);
    const answers = [{ estado: "pendiente" }, { estado: "procesando" }, { estado: "listo", url_descarga: "/media/rendicion.pdf" }];
    const fetchMock = vi.fn(() => json(answers.shift()));
    vi.stubGlobal("fetch", fetchMock);
    serve(detalle({ capabilities: capabilities({ puede_descargar_pdf: true }) }));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: /Generar descarga/ }));
    await waitFor(() => expect(screen.getByRole("status").textContent).toBe("Generando el PDF. Puede tardar unos minutos."));
    expect(screen.getByRole("button", { name: /Generando PDF/ }).hasAttribute("disabled")).toBe(true);
    await vi.advanceTimersByTimeAsync(3000);
    await vi.advanceTimersByTimeAsync(3000);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/media/rendicion.pdf"));
    expect(screen.getByRole("status").textContent).toBe("PDF listo. La descarga comienza en unos segundos.");
    expect((fetchMock.mock.calls[0] as unknown as [string, RequestInit])[0]).toBe(`${DETALLE}descargar-pdf/solicitar/`);
    expect((fetchMock.mock.calls[1] as unknown as [string])[0]).toBe(`${DETALLE}descargar-pdf/estado/`);
    vi.useRealTimers();
  });

  it("shows the PDF error message and re-enables the button", async () => {
    vi.stubGlobal("fetch", vi.fn(() => json({ mensaje: "Hay una descarga en curso." }, 409)));
    serve(detalle({ capabilities: capabilities({ puede_descargar_pdf: true }) }));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: /Generar descarga/ }));
    await waitFor(() => expect(screen.getByRole("status").textContent).toBe("Hay una descarga en curso."));
    expect(screen.getByRole("status").className).toContain("text-danger");
    expect(screen.getByRole("button", { name: /Generar descarga/ }).hasAttribute("disabled")).toBe(false);
  });

  it("reloads on returning from the document viewer unless a review is being edited", async () => {
    const reload = vi.spyOn(rendicionDetalleNavigation, "reload").mockImplementation(() => undefined);
    serve(detalle());
    setup();
    await screen.findByText("doc-11");
    fireEvent.click(screen.getAllByRole("link", { name: "Ver" })[0]);
    window.dispatchEvent(new Event("blur"));
    window.dispatchEvent(new Event("focus"));
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("shows the access screen on 403 and an error on an invalid payload", async () => {
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    setup();
    await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
    expect(screen.queryByRole("table")).toBeNull();
    cleanup();
    const bad = detalle();
    serve({ ...bad, documentacion: [{ ...bad.documentacion[0], archivos: [{ id: "1" }] }] });
    setup();
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(detalleValid(detalle())).toBe(true);
    expect(detalleValid(detalle({ urls: { ...detalle().urls, update: "https://evil.example/" } }))).toBe(false);
    expect(detalleValid({ ...detalle(), capabilities: { puede_editar_datos: true } })).toBe(false);
  });
});
