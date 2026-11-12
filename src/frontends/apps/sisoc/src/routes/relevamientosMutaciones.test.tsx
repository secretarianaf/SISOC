import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { bajaValid } from "./relevamientosBaja";
import { relevamientosNavigation, takeFlash } from "./relevamientosApi";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const LIST = "/comedores/7/relevamiento/listar";
const DETAIL = "/comedores/7/relevamiento/12";
const BAJA = "/comedores/7/relevamiento/12/eliminar";
const IF_API = "/api/web/comedores/relevamientos/7/relevamiento/numero-if/";
const caps = (over: Record<string, boolean> = {}) => ({ add_relevamiento: false, change_relevamiento: true, add_actacomplementaria: false, change_actacomplementaria: false, ...over });
const list = () => ({
  comedor: { id: 7, nombre: "Comedor <Uno>" }, encabezado: "Comedor <Uno> | Prov, Muni, Loc",
  relevamientos: [{ id: 12, fecha: "04/03/2026 15:07", estado: "Finalizado", estado_badge: "bg-success", numero_if: "IF-1", origen: "sisoc", sincronizado_gestionar: true, has_seguimiento: false, detalle_url: DETAIL, seguimientos: [] }],
  actas: [], seguimientos_pnud: [], opciones_alta: [], opciones_seguimiento: [], capabilities: caps(),
  urls: { listado: LIST, alta: "/comedores/ajax/7/relevamiento/", acta_crear: "/c/acta/crear", territoriales: "/comedores/7/territoriales/", territoriales_sincronizar: "/comedores/7/territoriales/sincronizar/", numero_if: IF_API }, messages: [],
});
const detail = () => ({
  relevamiento: { id: 12, comedor: { id: 7, nombre: "Comedor <Uno>" }, nombre_comedor: "Comedor <Uno>", fecha_visita: "04/03/2026 15:07", estado: "Finalizado", estado_visible: "Finalizado", estado_badge: "bg-success",
    estado_validacion: "", a_subsanar: false, esta_validado: false, sin_cargar: false, origen: "sisoc", sincronizado_gestionar: false, observaciones_coordinador: "", coordinador: null, fecha_revision_coordinador: null },
  timeline: [], secciones: [], titulos: [], seguimientos: [], adjuntos: [], pdf: { disponible: true, url: "/p/pdf", oficial: false, fecha_oficial: null },
  capabilities: { change_relevamiento: false, review_relevamiento: true, change_primerseguimiento: false, delete_primerseguimiento: false, view_logentry: false },
  urls: { listado: LIST, comedores: "/comedores/listar", comedor: "/comedores/7", alta: "/a/", eliminar: BAJA, revision: `${DETAIL}/revision`, revision_api: "/api/web/comedores/relevamientos/7/relevamiento/12/revision/",
    historial: "/h/", territoriales: "/t/", territoriales_sincronizar: "/t/s/" }, messages: [],
});
const preview = (over: Record<string, unknown> = {}) => ({ total_afectados: 3, total_baja_logica: 2, total_borrado_fisico: 1,
  desglose_por_modelo: [{ modelo: "Relevamiento", cantidad: 1, modo: "baja_logica", ejemplos: ["R <1>"] }, { modelo: "Archivo", cantidad: 2, modo: "borrado", ejemplos: [] }], ...over });
const baja = (over: Record<string, unknown> = {}) => ({ id: 12, nombre: "Comedor <Uno> - 2026-03-04", comedor: { id: 7, nombre: "Comedor <Uno>" }, fecha_visita: "04/03/2026 15:07",
  cascade_preview: preview(), confirm_text: "Dar de baja", cancel_text: "Cancelar", cancel_url: DETAIL, urls: { comedores: "/comedores/listar" }, messages: [], ...over });

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
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.sessionStorage.clear();
  vi.spyOn(relevamientosNavigation, "assign").mockImplementation(() => undefined);
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true, meta: { fuente: "cache_provincia", total: 0 }, territoriales: [] }) })));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("Relevamientos mutations", () => {
  it("saves the Numero de IF through the API without navigating and shows the toast", async () => {
    serve(list());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, message: "Número de IF actualizado correctamente.", redirect: LIST, numero_if: "IF-2" } });
    setup(LIST);
    fireEvent.click(await screen.findByRole("button", { name: "Actualizar IF" }));
    const input = document.querySelector('input[name="numero_if"]') as HTMLInputElement;
    fireEvent.change(input, { target: { value: "IF-2" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await screen.findByText("Número de IF actualizado correctamente.");
    const [url, body] = webPost.mock.calls[0] as [string, URLSearchParams];
    expect(url).toBe("web/comedores/relevamientos/7/relevamiento/numero-if/");
    expect([body.get("relevamiento_id"), body.get("numero_if")]).toEqual(["12", "IF-2"]);
    expect(screen.getByText("Número de IF:").nextElementSibling?.textContent).toBe("IF-2");
    expect(document.querySelector('input[name="numero_if"]')).toBeNull();
    expect(relevamientosNavigation.assign).not.toHaveBeenCalled();
  });

  it("shows the literal error of a rejected Numero de IF and keeps the form", async () => {
    serve(list());
    webPost.mockResolvedValue({ status: 403, data: { detail: "No tiene permisos para editar el Número de IF." } });
    setup(LIST);
    fireEvent.click(await screen.findByRole("button", { name: "Actualizar IF" }));
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await screen.findByText("No tiene permisos para editar el Número de IF.");
    expect(document.querySelector('input[name="numero_if"]')).toBeTruthy();
    webPost.mockResolvedValue({ status: 400, data: { errors: { numero_if: [{ message: "Asegúrese de que este valor tenga como máximo 255 caracteres.", code: "max_length" }] } } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await screen.findByText("Asegúrese de que este valor tenga como máximo 255 caracteres.");
  });

  it("never resubmits after an uncertain answer and offers a reload", async () => {
    serve(list());
    webPost.mockResolvedValue({ status: 504, data: { uncertain: true } });
    setup(LIST);
    fireEvent.click(await screen.findByRole("button", { name: "Actualizar IF" }));
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("No se pudo confirmar el resultado.");
    expect((screen.getByRole("button", { name: "Guardar" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(within(alert).getByRole("button", { name: "Recargar" }));
    expect(relevamientosNavigation.assign).toHaveBeenCalledWith(LIST);
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("reviews through the API, flashes the message and goes to the detail", async () => {
    serve(detail());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, message: "Acompañamiento Territorial validado correctamente.", redirect: DETAIL } });
    setup(DETAIL);
    fireEvent.click(await screen.findByRole("button", { name: "Revisar" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByRole("combobox"), { target: { value: "Validado" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Guardar revisión" }));
    await waitFor(() => expect(relevamientosNavigation.assign).toHaveBeenCalledWith(DETAIL));
    const [url, body] = webPost.mock.calls[0] as [string, URLSearchParams];
    expect(url).toBe("web/comedores/relevamientos/7/relevamiento/12/revision/");
    expect([body.get("estado_validacion"), body.get("observaciones_coordinador")]).toEqual(["Validado", ""]);
    expect(takeFlash()).toEqual([{ message: "Acompañamiento Territorial validado correctamente.", level: "success" }]);
  });

  it("shows a review rejection as a toast and closes the modal", async () => {
    serve(detail());
    webPost.mockResolvedValue({ status: 400, data: { errors: { __all__: [{ message: "Para devolver el acompañamiento territorial debe indicar qué corregir.", code: "invalid" }] } } });
    setup(DETAIL);
    fireEvent.click(await screen.findByRole("button", { name: "Revisar" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByRole("combobox"), { target: { value: "A subsanar" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Guardar revisión" }));
    await screen.findByText("Para devolver el acompañamiento territorial debe indicar qué corregir.");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(relevamientosNavigation.assign).not.toHaveBeenCalled();
  });

  it("shows a flashed message on the next screen once", async () => {
    window.sessionStorage.setItem("sisoc.relevamientos.flash", JSON.stringify([{ message: "Hecho", level: "success" }]));
    serve(detail());
    setup(DETAIL);
    await screen.findByText("Hecho");
    expect(takeFlash()).toEqual([]);
  });
});

describe("Relevamiento baja page", () => {
  it("owns the eliminar path and leaves crear and editar native", () => {
    expect(findRoute(BAJA)?.route.name).toBe("comedores-relevamientos");
    for (const other of ["/comedores/7/relevamiento/crear", "/comedores/7/relevamiento/12/editar", `${BAJA}/`, "/comedores/7/relevamiento/12/pdf", "/comedores/7/relevamiento/12/revision"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-relevamientos");
    }
  });

  it("renders the native confirmation with the cascade preview", async () => {
    serve(baja());
    setup(BAJA);
    await screen.findByText("Atención!", { exact: false });
    expect(webGet).toHaveBeenCalledWith("web/comedores/relevamientos/7/relevamiento/12/eliminar/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Acompañamiento Territorial - 12"));
    expect(screen.getByText("COMEDOR <UNO> - 2026-03-04")).toBeTruthy();
    expect(screen.getByText("Total de registros afectados:").parentElement?.textContent).toContain("3");
    expect(screen.getByText("Bajas lógicas: 2")).toBeTruthy();
    expect(screen.getByText("Borrados físicos técnicos: 1")).toBeTruthy();
    expect([...document.querySelectorAll("thead th")].map((t) => t.textContent)).toEqual(["Modelo", "Cantidad", "Acción", "Ejemplos"]);
    expect([...document.querySelectorAll("tbody tr")].map((r) => [...r.querySelectorAll("td")].map((c) => c.textContent))).toEqual([["Relevamiento", "1", "Baja lógica", "R <1>"], ["Archivo", "2", "Borrado físico técnico", "-"]]);
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe(DETAIL);
    expect(screen.getByRole("link", { name: "Acompañamiento Territorial 04/03/2026 15:07" }).getAttribute("href")).toBe(DETAIL);
    expect(screen.getByText("Eliminar", { selector: ".breadcrumb-item" })).toBeTruthy();
  });

  it("posts the baja once and follows the native redirect", async () => {
    serve(baja({ cascade_preview: null }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, message: "Acompañamiento Territorial dado de baja correctamente.", redirect: "/comedores/7" } });
    setup(BAJA);
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    await waitFor(() => expect(relevamientosNavigation.assign).toHaveBeenCalledWith("/comedores/7"));
    expect(webPost.mock.calls[0][0]).toBe("web/comedores/relevamientos/7/relevamiento/12/eliminar/");
    expect(document.querySelector("table")).toBeNull();
  });

  it("keeps the page on an error and never resubmits an uncertain baja", async () => {
    serve(baja());
    webPost.mockResolvedValueOnce({ status: 404, data: { detail: "No encontrado." } });
    setup(BAJA);
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    await screen.findByText("No encontrado.");
    webPost.mockResolvedValueOnce({ status: 504, data: { uncertain: true } });
    fireEvent.click(screen.getByRole("button", { name: "Dar de baja" }));
    await screen.findByText("No se pudo confirmar el resultado.", { exact: false });
    expect((screen.getByRole("button", { name: "Dar de baja" }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(2);
  });

  it.each([403, 404])("answers %i with the existing screens", async (status) => {
    serve({ detail: "x" }, status);
    setup(BAJA);
    await waitFor(() => expect(document.querySelector("main")).toBeTruthy());
    expect(screen.queryByText("Atención!", { exact: false })).toBeNull();
  });

  it("rejects malformed payloads", () => {
    expect(bajaValid(baja())).toBe(true);
    expect(bajaValid(baja({ cancel_url: "https://evil.example/" }))).toBe(false);
    expect(bajaValid(baja({ cascade_preview: { total_afectados: 1, desglose_por_modelo: [{ modelo: 1 }] } }))).toBe(false);
  });
});

describe("Seguimiento and acta actions through the API", () => {
  const seg = { id: 3, numero_orden: 2, tipo: "Seguimiento Posterior", fecha: "Sin fecha", estado: "Pendiente", estado_badge: "bg-secondary", estado_validacion: "", a_subsanar: false, origen: "app", sincronizado_gestionar: false,
    detalle_url: "/comedores/7/relevamiento/12/seguimiento/3/", editar_url: "/comedores/7/relevamiento/12/seguimiento/3/editar", eliminar_url: "/comedores/7/relevamiento/12/seguimiento/3/eliminar",
    eliminar_api: "/api/web/comedores/relevamientos/7/relevamiento/12/seguimientos/3/eliminar/" };

  it("deletes a seguimiento from the cycle table through the API and flashes the message", async () => {
    const base = detail();
    serve({ ...base, seguimientos: [seg], capabilities: { ...base.capabilities, delete_primerseguimiento: true } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, message: "Seguimiento eliminado correctamente.", redirect: DETAIL } });
    setup(DETAIL);
    fireEvent.click((await screen.findAllByRole("button", { name: "Eliminar" })).find((b) => b.className.includes("btn-sm")) as HTMLElement);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Eliminar seguimiento posterior #2")).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("button", { name: "Eliminar" }));
    await waitFor(() => expect(relevamientosNavigation.assign).toHaveBeenCalledWith(DETAIL));
    expect(webPost.mock.calls[0][0]).toBe("web/comedores/relevamientos/7/relevamiento/12/seguimientos/3/eliminar/");
    expect(takeFlash()).toEqual([{ message: "Seguimiento eliminado correctamente.", level: "success" }]);
  });

  it("keeps the cycle table and shows the error when the baja is rejected", async () => {
    const base = detail();
    serve({ ...base, seguimientos: [seg], capabilities: { ...base.capabilities, delete_primerseguimiento: true } });
    webPost.mockResolvedValue({ status: 404, data: { detail: "No encontrado." } });
    setup(DETAIL);
    fireEvent.click((await screen.findAllByRole("button", { name: "Eliminar" })).find((b) => b.className.includes("btn-sm")) as HTMLElement);
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Eliminar" }));
    await screen.findByText("No encontrado.");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(screen.getByText("Ciclo de seguimiento")).toBeTruthy();
    expect(relevamientosNavigation.assign).not.toHaveBeenCalled();
  });
});
