import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { listValid } from "./admisionesListas";
import { admisionesNative, detalleValid } from "./admisionesDetalle";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const TECNICOS = "/comedores/admisiones/tecnicos/listar";
const LEGALES = "/comedores/admisiones/legales/listar";
const headers = ["ID Comedor", "Tipo", "Nombre", "Organización", "N° Expediente", "N° Convenio", "Provincia", "Equipo técnico", "Estado", "Última Modificación"]
  .map((title) => ({ title, sort_url: title === "Nombre" ? "?order_by=nombre&direction=asc" : null, sort_direction: null }));
const cell = (content: string, extra: Record<string, unknown> = {}) => ({ content, data_attr: null, data_value: null, link_url: null, link_class: null, link_title: null, ...extra });
const lista = (over: Record<string, unknown> = {}) => ({
  title: "Admisiones - Equipos técnicos",
  breadcrumb: [{ text: "", url: "admisiones_tecnicos_listar", active: false }, { text: "", url: null, active: true }],
  filters_config: { fields: [{ name: "comedor_nombre", label: "Nombre del comedor", type: "text" }] },
  favorites: { section: "admisiones_tecnicos", url: "/filtros-favoritos/", detail_url_template: "/filtros-favoritos/0/" },
  urls: { list: TECNICOS, reset: TECNICOS },
  columns: { list_key: "admisiones_tecnicos_list", endpoint: "/columnas/", modal_id: "columnConfigModal", script_id: "column-config-json", available: [], active: [], defaults: [] },
  headers,
  results: [{
    cells: [cell("7"), cell("Incorporación"), cell("Comedor Sintético", { data_attr: "nombre", data_value: "Comedor Sintético", link_url: "/comedores/7", link_class: "font-weight-bold link-handler", link_title: "Ver detalles" }),
      cell("Org"), cell("EX-1"), cell("3°"), cell("Chaco"), cell("-"), cell("Iniciado"), cell("01/11/2026")],
    actions: [{ label: "Ver", badge: "Rectificar", url: "/comedores/admisiones/tecnicos/editar/5", type: "warning" }],
  }],
  page: { is_paginated: false, number: 1, count: 1, has_rows: true, previous: null, next: null, range: [1], query_without_page: "" },
  messages: [], ...over,
});

const DETALLE = "/comedores/7/admision/5/detalle/";
const detalle = (over: Record<string, unknown> = {}) => ({
  id: 5, activa: true, comedor: { id: 7, nombre: "Comedor Sintético" }, urls: { comedores: "/comedores/", comedor: "/comedores/7", pagina: DETALLE },
  puede_forzar_cierre: true,
  admision: { creado: "01/10/2026", tipo: "Incorporación", tipo_convenio: "-", convenio_numero: 4, vigente_pwa: true, estado_actual: "Iniciado", fecha_estado: "-", estado_legales: "-",
    enviado_legales: false, enviado_acompaniamiento: false, num_expediente: "EX-1", fecha_cierre: null, motivo_cierre: "-" },
  puede_editar_convenio_numero: false, puede_editar_num_expediente: false, num_expediente_bloqueo: "",
  dupla: { nombre: "Dupla Uno", estado: "Activo", abogado: "Ana Abogada", tecnicos: ["Tomás Técnico", "Tina Técnica"] },
  documentos: [{ nombre: "Estatuto", obligatorio: true, estado: "Aceptado", numero_gde: "-", archivo_url: "/media/estatuto.pdf" }], documentos_personalizados: [],
  informe_tecnico: null, informe_enlaces: null, informe_gde: null, complementarios: [],
  historial_estados: { headers: ["Fecha", "Estado nuevo", "Estado anterior", "Usuario"], rows: [], page: { is_paginated: false, number: 1, count: 0, has_rows: false, previous: null, next: null, range: [], param: "historial_estados_page", query_without_page: "" } },
  acompanamiento: { expediente: "-", disposicion: "-", if_relevamiento: "-", vencimiento: "-", codigo_proyecto: "-", if_asociados: "-", dias: [], prestaciones_por_dia: [], totales: [] },
  expedientes_pagos: [], rendiciones_mensuales: [], rendicion_final: null, messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => cleanup());

describe("Admision lists route (AD03.01)", () => {
  it("owns only the two native list pages, without a trailing slash", () => {
    expect(findRoute(TECNICOS)?.params).toEqual({ page: "tecnicos" });
    expect(findRoute(LEGALES)?.params).toEqual({ page: "legales" });
    for (const other of [`${TECNICOS}/`, "/comedores/admisiones/tecnicos/editar/5/", "/comedores/admisiones/legales/ver/5"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-admisiones-seguimiento");
    }
  });

  it("renders the technical list with the name link, the badge and the native action", async () => {
    serve(lista());
    setup(`${TECNICOS}?page=1`);
    await screen.findByText("Admisiones - Equipos técnicos");
    expect(webGet).toHaveBeenCalledWith("web/comedores/admisiones/tecnicos/?page=1", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Admisiones"));
    expect(screen.getByRole("link", { name: "Comedor Sintético" }).getAttribute("href")).toBe("/comedores/7");
    const ver = screen.getByTitle("Ver");
    expect(ver.getAttribute("href")).toBe("/comedores/admisiones/tecnicos/editar/5");
    expect(ver.className).toBe("btn btn-warning position-relative");
    expect(within(ver).getByText("Rectificar").className).toContain("bg-danger");
    expect(screen.getByRole("link", { name: "Nombre" }).getAttribute("href")).toBe("?order_by=nombre&direction=asc");
  });

  it("renders the legal list and its empty message", async () => {
    serve(lista({ title: "Expedientes - Legales", results: [], page: { is_paginated: false, number: 1, count: 0, has_rows: false, previous: null, next: null, range: [], query_without_page: "" } }));
    setup(LEGALES);
    await screen.findByText("Expedientes - Legales");
    expect(webGet).toHaveBeenCalledWith("web/comedores/admisiones/legales/", expect.anything());
    expect(screen.getByText("No hay expedientes registrados.")).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Comedores - Expedientes"));
  });

  it("keeps the 403 and malformed envelopes out of the page", async () => {
    expect(listValid({})).toBe(false);
    expect(listValid({ ...lista(), results: [{ cells: [cell("x", { link_url: "https://evil.example" })], actions: [] }] })).toBe(false);
    expect(listValid(lista())).toBe(true);
    serve({}, 200);
    setup(TECNICOS);
    expect(await screen.findByRole("alert")).toBeTruthy();
  });

  it("owns the native detail page and keeps its trailing slash", () => {
    expect(findRoute(DETALLE)?.params).toEqual({ page: "detalle", comedor: "7", id: "5" });
    expect(findRoute("/comedores/7/admision/5/detalle")?.route.name).not.toBe("comedores-admisiones-seguimiento");
  });

  it("renders the admision, the dupla, the document table and the empty sections", async () => {
    serve(detalle({ messages: [{ message: "La admisión ha sido cerrada forzadamente.", level: "success" }] }));
    setup(DETALLE);
    await screen.findByText("Dupla Uno");
    expect(webGet).toHaveBeenCalledWith("web/comedores/admisiones/7/5/detalle/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Admision 5"));
    expect(screen.getByText("Activa").className).toBe("badge bg-success");
    expect(screen.getByText("Tomás Técnico, Tina Técnica")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Descargar" }).getAttribute("href")).toBe("/media/estatuto.pdf");
    expect(screen.getByText("No se registran informes tecnicos cargados.")).toBeTruthy();
    expect(screen.getByText("No se registran cambios de estado.")).toBeTruthy();
    expect(screen.getByText("Todavia no se genero una rendicion de cuenta final para este comedor.")).toBeTruthy();
    expect(screen.getByText("La admisión ha sido cerrada forzadamente.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Comedor Sintético" }).getAttribute("href")).toBe("/comedores/7");
  });

  it("posts the forced closure to the native URL with the CSRF token and the reason field", async () => {
    serve(detalle());
    setup(DETALLE);
    fireEvent.click(await screen.findByRole("button", { name: /Forzar Cierre/ }));
    const modal = await screen.findByRole("dialog");
    const form = modal.querySelector("form")!;
    expect(form.getAttribute("method")).toBe("post");
    expect(form.getAttribute("action")).toBe(DETALLE);
    expect((form.querySelector("[name=csrfmiddlewaretoken]") as HTMLInputElement).value).toBe("synthetic-csrf-token");
    expect((form.querySelector("textarea[name=motivo_forzar_cierre]") as HTMLTextAreaElement).required).toBe(true);
    expect(within(modal).getByRole("button", { name: "Confirmar Cierre" }).getAttribute("name")).toBe("forzar_cierre");
    fireEvent.click(within(modal).getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("closed admisions show the badge, the closing data and no close button", async () => {
    serve(detalle({ activa: false, puede_forzar_cierre: false, admision: { ...detalle().admision, fecha_cierre: "02/10/2026", motivo_cierre: "Cierre de prueba" } }));
    setup(DETALLE);
    await screen.findByText("Cierre de prueba");
    expect(screen.getByText("Cerrada").className).toBe("badge bg-danger");
    expect(screen.queryByRole("button", { name: /Forzar Cierre/ })).toBeNull();
    expect(screen.queryByPlaceholderText("Nombre del archivo adicional")).toBeNull();
  });

  it("rejects a malformed detail envelope", () => {
    expect(detalleValid(detalle())).toBe(true);
    expect(detalleValid({ ...detalle(), documentos: [{ nombre: "x" }] })).toBe(false);
    expect(detalleValid({ ...detalle(), urls: { comedores: "https://evil.example", comedor: "/c", pagina: "/p" } })).toBe(false);
  });

  it("edits the agreement number through the native endpoint and shows the native toasts", async () => {
    serve(detalle({ puede_editar_convenio_numero: true }));
    const post = vi.spyOn(admisionesNative, "post").mockResolvedValueOnce({ success: false, error: "El numero de convenio no puede ser negativo." })
      .mockResolvedValueOnce({ success: true, convenio_numero: 9 });
    setup(DETALLE);
    fireEvent.click((await screen.findByTitle("Editar numero de convenio")).parentElement!);
    const input = document.getElementById("convenio-numero-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "-1" } });
    fireEvent.click(screen.getByTitle("Guardar"));
    expect(await screen.findByText("El numero de convenio no puede ser negativo.")).toBeTruthy();
    expect(post).toHaveBeenLastCalledWith("/ajax/actualizar-convenio-numero/", { admision_id: "5", convenio_numero: "-1" });
    expect(document.getElementById("convenio-numero-input")).not.toBeNull();
    fireEvent.change(input, { target: { value: "9" } });
    fireEvent.click(screen.getByTitle("Guardar"));
    expect(await screen.findByText("Numero de convenio actualizado con exito.")).toBeTruthy();
    expect(screen.getByText("9").className).toBe("text-success fw-bold");
    expect(document.getElementById("convenio-numero-input")).toBeNull();
    post.mockRestore();
  });

  it("toggles Vigente PWA and reverts it when the native view rejects", async () => {
    serve(detalle({ puede_editar_convenio_numero: true }));
    const post = vi.spyOn(admisionesNative, "post").mockResolvedValueOnce({ success: false, error: "No tiene permisos para editar esta admision." });
    const alert = vi.spyOn(admisionesNative, "alert").mockImplementation(() => undefined);
    setup(DETALLE);
    const toggle = (await screen.findByRole("switch")) as HTMLInputElement;
    fireEvent.click(toggle);
    await waitFor(() => expect(alert).toHaveBeenCalledWith("Error: No tiene permisos para editar esta admision."));
    expect(post).toHaveBeenCalledWith("/ajax/actualizar-vigente-pwa/", { admision_id: "5", vigente_pwa: "0" });
    expect(toggle.checked).toBe(true);
    post.mockRestore(); alert.mockRestore();
  });

  it("uploads an additional file to the native page URL and reloads, or alerts without a name", async () => {
    serve(detalle());
    const upload = vi.spyOn(admisionesNative, "upload").mockResolvedValue(200);
    const reload = vi.spyOn(admisionesNative, "reload").mockImplementation(() => undefined);
    const alert = vi.spyOn(admisionesNative, "alert").mockImplementation(() => undefined);
    setup(DETALLE);
    const file = new File(["x"], "n.pdf");
    const input = (await screen.findByPlaceholderText("Nombre del archivo adicional")) as HTMLInputElement;
    fireEvent.change(document.getElementById("nuevoArchivoFile")!, { target: { files: [file] } });
    expect(alert).toHaveBeenCalledWith("Por favor ingrese un nombre para el archivo");
    expect(upload).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: "Nota extra" } });
    fireEvent.change(document.getElementById("nuevoArchivoFile")!, { target: { files: [file] } });
    await waitFor(() => expect(reload).toHaveBeenCalled());
    const [url, form] = upload.mock.calls[0];
    expect(url).toBe(DETALLE);
    expect((form as FormData).get("nombre")).toBe("Nota extra");
    expect((form as FormData).get("archivo")).toBeInstanceOf(File);
    upload.mockRestore(); reload.mockRestore(); alert.mockRestore();
  });
});
