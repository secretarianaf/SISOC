import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { detailValid, intervencionesNavigation, listValid } from "./comedorIntervenciones";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/intervenciones/";
const fila = (over: Record<string, unknown> = {}) => ({
  id: 5, fecha: "01/10/2026", tipo_intervencion: "Visita", subintervencion: "None", destinatario: "Titular", forma_contacto: "Presencial",
  tiene_documentacion: false, url: "/intervencion/detalle/5/", url_eliminar: null, ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  comedor: { id: 3, nombre: "Comedor Sintético", url: "/comedores/3" }, admision_id: null, admisiones: [],
  filtros: { fecha: "", tipo_intervencion: "", destinatario: "" },
  tipos_intervencion: [{ id: 1, nombre: "Visita" }, { id: 2, nombre: "Llamada" }],
  destinatarios: [{ id: 7, nombre: "Titular" }],
  results: [fila()], urls: { agregar: "/comedores/intervencion/crear/3", volver: "/comedores/3" }, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 5, fecha: "01/10/2026 23:30", tipo_intervencion: "Visita", subintervencion: "None", forma_contacto: "Presencial", observaciones: "None",
  documentacion: null, puede_eliminar_archivo: false, messages: [], ...over,
});

function serve(body: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status }));
}
function setup(url: string) {
  window.history.replaceState({}, "", url);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Comedor interventions list", () => {
  it("owns the native URLs and validates its payload", () => {
    expect(findRoute("/comedores/intervencion/ver/3")?.route.name).toBe("comedores-intervenciones");
    expect(findRoute("/intervencion/detalle/5/")?.route.name).toBe("comedores-intervenciones");
    expect(findRoute("/comedores/intervencion/ver/3/")?.route.name).not.toBe("comedores-intervenciones");
    expect(findRoute("/comedores/intervencion/ver/x")?.route.name).not.toBe("comedores-intervenciones");
    expect(listValid(list())).toBe(true);
    expect(listValid(list({ admision_id: "1" }))).toBe(false);
    expect(listValid(list({ results: [fila({ url: "https://externo.example" })] }))).toBe(false);
    expect(detailValid(detail())).toBe(true);
    expect(detailValid(detail({ documentacion: { name: "a" } }))).toBe(false);
  });

  it("renders the native table, filters and the empty cell the nested td leaves", async () => {
    serve(list({
      admision_id: 9, admisiones: [{ id: 9, convenio: "CONV-1", activa: true }, { id: 4, convenio: null, activa: false }],
      filtros: { fecha: "2026-10-01", tipo_intervencion: "2", destinatario: "7" },
      results: [fila({ url_eliminar: "/comedores/intervencion/borrar/3/5/", tiene_documentacion: true })],
      messages: [{ message: "Intervención dada de baja correctamente.", level: "success" }],
    }));
    setup("/comedores/intervencion/ver/3?admision_id=9&fecha=2026-10-01");
    expect(await screen.findByText("Historial de Intervenciones")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}comedor/3/?admision_id=9&fecha=2026-10-01`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Intervenciones"));
    expect(screen.getByText("Intervención dada de baja correctamente.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "CONV-1" }).className).toBe("btn btn-sm btn-primary");
    const cerrada = screen.getByRole("link", { name: /Admisión #4/ });
    expect(cerrada.className).toBe("btn btn-sm btn-outline-secondary");
    expect(cerrada.textContent).toBe("Admisión #4 Cerrada");
    expect(screen.getByRole("link", { name: "Agregar Intervención" }).getAttribute("href")).toBe("/comedores/intervencion/crear/3?admision_id=9");
    expect(document.querySelector<HTMLInputElement>('input[name="admision_id"]')?.value).toBe("9");
    expect(document.querySelector<HTMLInputElement>('input[name="fecha"]')?.value).toBe("2026-10-01");
    expect(document.querySelector<HTMLSelectElement>('select[name="tipo_intervencion"]')?.value).toBe("2");
    expect(document.querySelector<HTMLSelectElement>('select[name="destinatario"]')?.value).toBe("7");
    const filas = document.querySelectorAll("tbody tr");
    expect(filas).toHaveLength(1);
    const celdas = Array.from(filas[0].querySelectorAll("td")).map((td) => td.textContent);
    expect(celdas).toEqual(["01/10/2026", "Visita", "None", "Titular", "Presencial", "Sí", "", "Ver Eliminar"]);
    expect(within(filas[0] as HTMLElement).getByRole("link", { name: "Eliminar" }).getAttribute("href")).toBe("/comedores/intervencion/borrar/3/5/");
    expect(document.querySelector('form#filtros-form')?.getAttribute("method")).toBe("get");
  });

  it("shows the empty message and no delete link for a plain reader", async () => {
    serve(list({ results: [] }));
    setup("/comedores/intervencion/ver/3");
    expect(await screen.findByText("Aún no se han registrado intervenciones")).toBeTruthy();
    expect(document.querySelector("table")).toBeNull();
    expect(screen.queryByText("Convenio:")).toBeNull();
    expect(webGet).toHaveBeenCalledWith(`${API}comedor/3/`, expect.anything());
  });

  it("clears the filters keeping the admission, like the native script", async () => {
    serve(list({ admision_id: 9, admisiones: [{ id: 9, convenio: null, activa: true }] }));
    setup("/comedores/intervencion/ver/3?admision_id=9");
    fireEvent.click(await screen.findByRole("button", { name: "Limpiar" }));
    expect(window.location.href).toContain("?admision_id=9");
  });

  it("shows the access screen for a 403 and an error for an invalid payload", async () => {
    serve({ detail: "x" }, 403);
    setup("/comedores/intervencion/ver/3");
    await waitFor(() => expect(document.querySelector("main, .content-wrapper, body")?.textContent).not.toContain("Historial"));
    cleanup();
    serve({ results: "x" });
    setup("/comedores/intervencion/ver/3");
    expect(await screen.findByText("No se pudo cargar la página.")).toBeTruthy();
  });
});

describe("Comedor intervention detail", () => {
  it("renders the native card rows, the missing values and no file controls without a file", async () => {
    serve(detail());
    setup("/intervencion/detalle/5/");
    expect(await screen.findByText("Detalle de Intervención")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}5/`, expect.anything());
    const filas = Array.from(document.querySelectorAll("tbody tr")).map((tr) => Array.from(tr.children).map((c) => c.textContent));
    expect(filas).toEqual([
      ["Fecha y hora", "01/10/2026 23:30"],
      ["Tipo de intervención", "Visita"],
      ["Subtipo de intervención", "None"],
      ["Forma de contacto", "Presencial"],
      ["Descripción", "None"],
      ["Documentación adjunta", "No hay documentación adjunta."],
    ]);
  });

  it("downloads the file and hides the removal button from non-superusers", async () => {
    serve(detail({ documentacion: { name: "documentacion/acta.txt", url: "/media/documentacion/acta.txt" } }));
    setup("/intervencion/detalle/5/");
    const link = await screen.findByRole("link", { name: "Descargar" });
    expect(link.getAttribute("href")).toBe("/media/documentacion/acta.txt");
    expect(link.hasAttribute("download")).toBe(true);
    expect(screen.getByText("documentacion/acta.txt")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Eliminar" })).toBeNull();
  });

  it("confirms in the modal, posts once and follows the native redirect", async () => {
    serve(detail({ documentacion: { name: "a.txt", url: "/media/a.txt" }, puede_eliminar_archivo: true }));
    const assign = vi.spyOn(intervencionesNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/intervencion/detalle/5/" }, status: 200 });
    setup("/intervencion/detalle/5/");
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));
    expect(await screen.findByText("¿Estás seguro de que deseas eliminar el archivo adjunto?")).toBeTruthy();
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByText("Confirmar eliminación")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    const dialog = await screen.findByRole("dialog");
    const confirm = within(dialog).getByRole("button", { name: "Eliminar" });
    fireEvent.click(confirm);
    fireEvent.click(confirm);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/intervencion/detalle/5/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}5/documentacion/eliminar/`);
  });

  it("keeps the page and reports a forbidden or unconfirmed removal", async () => {
    serve(detail({ documentacion: { name: "a.txt", url: "/media/a.txt" }, puede_eliminar_archivo: true }));
    const assign = vi.spyOn(intervencionesNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValueOnce({ data: { detail: "No tiene permisos." }, status: 403 });
    setup("/intervencion/detalle/5/");
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Eliminar" }));
    expect(await screen.findByText("No tiene permisos.")).toBeTruthy();
    webPost.mockRejectedValueOnce(new Error("network"));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Eliminar" }));
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
  });
});
