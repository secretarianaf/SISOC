import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { FLASH_KEY, organizacionesNavigation } from "./organizacionesForm";
import { bajaValid, FirmantesSection, firmantesSectionValid, formularioValid, type FirmantesSection as Section } from "./organizacionFirmantes";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/organizaciones/";
const field = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, label, type: "text", required: false, help: "", value: "", options: null, errors: [] as string[], attrs: {}, ...over,
});
const roles = [{ value: "", label: "---------" }, { value: "1", label: "Presidente" }, { value: "2", label: "Tesorero" }];
function formulario(over: Record<string, unknown> = {}, title = "Datos de Firmantes") {
  return {
    title, organization_id: 8, allow_another: true, urls: { back: "/organizaciones/detalle/8" }, messages: [], non_field_errors: [] as string[],
    fields: [field("nombre", "Nombre", { required: true, attrs: { maxlength: "255" } }), field("rol", "Rol", { type: "select", options: roles }),
      field("cuit", "Cuit", { type: "number" }), field("programa", "Programa", { type: "select", options: [{ value: "", label: "---------" }] })],
    ...over,
  };
}
function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
const open = (path: string) => { window.history.replaceState({}, "", path); return render(<App />); };

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.sessionStorage.clear();
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Firmantes and avales routes", () => {
  it("owns only the six native paths, without trailing slash", () => {
    for (const path of ["firmante/crear/8", "firmante/editar/8", "firmante/eliminar/8", "aval/crear/8", "aval/editar/8", "aval/eliminar/8"]) {
      expect(findRoute(`/organizaciones/${path}`)?.route.name).toBe("comedores-organizaciones-firmantes");
    }
    for (const other of ["/organizaciones/firmante/crear/8/", "/organizaciones/firmante/crear/0", "/organizaciones/firmante/otro/8", "/organizaciones/avales/crear/8"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-organizaciones-firmantes");
    }
  });

  it("renders the alta like the native page: back bar with its empty submit anchor, card, hidden id and both buttons", async () => {
    serve(formulario());
    open("/organizaciones/firmante/crear/8");
    expect(await screen.findByRole("heading", { level: 2, name: "Datos de Firmantes" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}8/firmantes/formulario/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Organizaciones"));
    expect(document.querySelector("a.btn-outline-light")?.textContent?.trim()).toBe("Volver");
    expect(document.querySelector("a.btn-outline-light")?.getAttribute("href")).toBe("/organizaciones/detalle/8");
    expect(document.querySelector(".btn-group a.btn-submit")?.getAttribute("href")).toBe("");
    expect((document.querySelector("input[name=organizacion_id]") as HTMLInputElement).value).toBe("8");
    expect(within(screen.getByLabelText(/^Rol/)).getAllByRole("option").map((o) => o.textContent)).toEqual(["---------", "Presidente", "Tesorero"]);
    expect(screen.getByRole("button", { name: "Guardar" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Guardar y agregar otro" })).toBeTruthy();
  });

  it("posts the alta once with the body organization, then navigates and keeps no message", async () => {
    serve(formulario());
    const go = vi.spyOn(organizacionesNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 201, data: { redirect: "/organizaciones/detalle/8", otro: false, messages: [] } });
    open("/organizaciones/firmante/crear/8");
    await screen.findByRole("heading", { level: 2, name: "Datos de Firmantes" });
    fireEvent.change(screen.getByLabelText(/^Nombre/), { target: { value: "Ana" } });
    fireEvent.change(screen.getByLabelText(/^Rol/), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(go).toHaveBeenCalledWith("/organizaciones/detalle/8"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(`${API}8/firmantes/`);
    expect([...(body as URLSearchParams).entries()]).toEqual([["organizacion_id", "8"], ["nombre", "Ana"], ["rol", "1"], ["cuit", ""], ["programa", ""]]);
    expect(window.sessionStorage.getItem(FLASH_KEY)).toBeNull();
  });

  it("sends guardar_otro only from its own button", async () => {
    serve(formulario());
    vi.spyOn(organizacionesNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 201, data: { redirect: "/organizaciones/firmante/crear/8", otro: true, messages: [] } });
    open("/organizaciones/firmante/crear/8");
    await screen.findByRole("heading", { level: 2, name: "Datos de Firmantes" });
    fireEvent.change(screen.getByLabelText(/^Nombre/), { target: { value: "Ana" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar y agregar otro" }));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    expect((webPost.mock.calls[0][1] as URLSearchParams).get("guardar_otro")).toBe("true");
  });

  it("shows the Django errors of a 400 on the bound fields and keeps the typed values", async () => {
    serve(formulario());
    const bound = formulario({}, "Datos de Firmantes");
    bound.fields[0] = { ...bound.fields[0], value: "Ana" };
    bound.fields[1] = { ...bound.fields[1], value: "1", errors: ["Ya existe un firmante con ese rol para esta organización."] };
    webPost.mockResolvedValue({ status: 400, data: { errors: {}, form: bound, messages: [{ message: "Falta el id de la organización.", level: "error" }] } });
    open("/organizaciones/firmante/crear/8");
    await screen.findByRole("heading", { level: 2, name: "Datos de Firmantes" });
    fireEvent.change(screen.getByLabelText(/^Nombre/), { target: { value: "Ana" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Ya existe un firmante con ese rol para esta organización.")).toBeTruthy();
    expect((screen.getByLabelText(/^Nombre/) as HTMLInputElement).value).toBe("Ana");
    expect(screen.getByText("Falta el id de la organización.")).toBeTruthy();
  });

  it("renders the edición without the top bar nor the second button, and the aval card title", async () => {
    serve(formulario({ allow_another: false, organization_id: null, urls: { back: null } }, "Datos de Avales"));
    open("/organizaciones/aval/editar/3");
    expect(await screen.findByRole("heading", { level: 2, name: "Datos de Avales" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}avales/3/formulario/`, expect.anything());
    expect(document.querySelector("a.btn-outline-light")).toBeNull();
    expect(document.querySelector("a.btn-submit")).toBeNull();
    expect(screen.queryByRole("button", { name: "Guardar y agregar otro" })).toBeNull();
    expect(document.querySelector("input[name=organizacion_id]")).toBeNull();
    const go = vi.spyOn(organizacionesNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { redirect: "/organizaciones/detalle/8", otro: false, messages: [] } });
    fireEvent.change(screen.getByLabelText(/^Nombre/), { target: { value: "Beto" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(go).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe(`${API}avales/3/`);
    expect((webPost.mock.calls[0][1] as URLSearchParams).has("organizacion_id")).toBe(false);
  });

  it("confirms the baja with the cascade preview and navigates with the native message", async () => {
    serve({
      id: 4, title: "Atención!", message: "¿Está seguro que desea dar de baja al firmante Ana", urls: { cancel: "/organizaciones/detalle/8" }, messages: [],
      cascade_preview: { total_afectados: 1, total_baja_logica: 1, desglose_por_modelo: [{ modelo: "Firmantes", cantidad: 1, modo: "baja_logica", ejemplos: ["Ana (Firmante 1) (ID 4)"] }] },
    });
    const go = vi.spyOn(organizacionesNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { redirect: "/organizaciones/detalle/8", messages: [{ message: "Firmante dado de baja correctamente.", level: "success" }] } });
    open("/organizaciones/firmante/eliminar/4");
    expect(await screen.findByRole("heading", { level: 3, name: /Atención!/ })).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Confirmar Eliminación"));
    expect(screen.getByText(/¿Está seguro que desea dar de baja al firmante Ana/)).toBeTruthy();
    expect(screen.getByText("Total de registros afectados:")).toBeTruthy();
    expect(screen.getByText("Ana (Firmante 1) (ID 4)")).toBeTruthy();
    expect(document.querySelector(".breadcrumb-item.active")?.textContent).toBe("");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/organizaciones/detalle/8");
    fireEvent.click(screen.getByRole("button", { name: "Dar de baja" }));
    await waitFor(() => expect(go).toHaveBeenCalledWith("/organizaciones/detalle/8"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}firmantes/4/baja/`);
    expect(JSON.parse(window.sessionStorage.getItem(FLASH_KEY) ?? "[]")[0].message).toBe("Firmante dado de baja correctamente.");
  });

  it("shows the access screen on 403, an error on 404 and rejects malformed payloads", async () => {
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    open("/organizaciones/firmante/crear/8");
    await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
    expect(screen.queryByRole("heading", { level: 2 })).toBeNull();
    cleanup();
    serve({ detail: "No encontrado." }, 404);
    open("/organizaciones/aval/eliminar/4");
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(formularioValid({ ...formulario(), fields: "x" })).toBe(false);
    expect(bajaValid({ id: 1 })).toBe(false);
  });
});

describe("Firmantes legajo section", () => {
  const rows = [
    { id: 1, name: "Ana", role: "Presidente", cuit: "20111111112", program: null, edit_url: "/organizaciones/firmante/editar/1", delete_url: "/organizaciones/firmante/eliminar/1" },
    { id: 2, name: "Beto", role: null, cuit: "-", program: "Otro", edit_url: "/organizaciones/firmante/editar/2", delete_url: "/organizaciones/firmante/eliminar/2" },
  ];
  const section = (over: Partial<Section> = {}): Section => ({ kind: "firmantes", title: "Firmantes · Línea Secos", color: "secos", show_program: false, can_manage: true, add_url: "/organizaciones/firmante/crear/8", rows, ...over });

  it("renders the program table with its actions and the add button", () => {
    render(<FirmantesSection section={section()} />);
    expect(screen.getByRole("heading", { level: 5, name: "Firmantes · Línea Secos" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Agregar Firmante/ }).getAttribute("href")).toBe("/organizaciones/firmante/crear/8");
    expect(screen.getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Nombre", "Rol", "CUIT", "Acciones"]);
    expect(screen.getByText("Presidente").className).toContain("badge-gold");
    expect(screen.getByRole("link", { name: "Editar firmante Ana" }).getAttribute("href")).toBe("/organizaciones/firmante/editar/1");
    expect(screen.getByRole("link", { name: "Eliminar firmante Beto" }).getAttribute("href")).toBe("/organizaciones/firmante/eliminar/2");
  });

  it("adds the program column of the sin-programa block and hides the management without the permission", () => {
    render(<FirmantesSection section={section({ show_program: true, can_manage: false, add_url: null })} />);
    expect(screen.getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Nombre", "Rol", "CUIT", "Programa"]);
    expect(screen.getByText("Sin programa").className).toContain("badge-pendiente");
    expect(screen.getByText("Otro (no cargado en la organización)").className).toContain("badge-gris");
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("shows the empty text and validates the payload", () => {
    render(<FirmantesSection section={section({ rows: [] })} />);
    expect(screen.getByText("No hay firmantes registrados.")).toBeTruthy();
    expect(firmantesSectionValid(section())).toBe(true);
    expect(firmantesSectionValid({ ...section(), add_url: "https://evil.example/" })).toBe(false);
  });
});
