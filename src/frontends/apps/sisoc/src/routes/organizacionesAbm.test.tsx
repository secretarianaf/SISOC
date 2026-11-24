import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { FLASH_KEY, formValid, organizacionesNavigation } from "./organizacionesForm";
import { bajaValid } from "./organizacionesBaja";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/organizaciones/";
const field = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, label, type: "text", required: false, help: "", value: "", options: null, errors: [], attrs: {}, ...over,
});
const sel = (name: string, label: string, options: [string, string][], value = "") =>
  field(name, label, { type: "select", value, options: options.map(([v, l]) => ({ value: v, label: l })) });
function form(over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}) {
  const base = [
    field("nombre", "Nombre", { required: true, attrs: { maxlength: "255" } }),
    field("cuit", "Cuit", { attrs: { maxlength: "11" } }),
    sel("tipo_entidad", "Tipo entidad", [["", "---------"], ["1", "Asociación civil"], ["2", "Cooperativa"]]),
    sel("subtipo_entidad", "Subtipo entidad", []),
    field("telefono", "Telefono", { type: "number" }),
    field("email", "Email", { type: "email" }),
    sel("provincia", "Provincia", [["", "---------"], ["7", "Provincia sintética"]]),
    sel("municipio", "Municipio", []),
    sel("localidad", "Localidad", []),
    field("partido", "Partido"), field("domicilio", "Domicilio"),
    field("fecha_vencimiento", "Fecha de vencimiento", { type: "date" }),
    field("sin_vencimiento", "Sin vencimiento", { type: "checkbox", value: false }),
    field("programas", "Programas", { type: "multiple", value: [], options: [{ value: "1", label: "Alimentar Comunidad" }, { value: "2", label: "Abordaje Comunitario - Línea Secos" }] }),
    sel("region_abordaje", "Región", []), sel("subzona_abordaje", "Subzona", []),
    field("proyectos_lineas", "Proyectos", { type: "hidden", value: "[]" }),
    field("asignaciones_territoriales", "Asignaciones", { type: "hidden", value: "null" }),
    field("deleted_at", "Deleted at"), field("territoriales_abordaje_comunitario", "Territoriales", { type: "multiple", value: null, options: [] }),
    field("cuil_duplicado_confirmado", "", { type: "hidden" }), field("cuil_duplicado_confirmado_valor", "", { type: "hidden" }),
  ].map((f) => ({ ...f, ...(fieldOver[f.name] ?? {}) }));
  return {
    organizacion_id: null, fields: base, non_field_errors: [],
    data: { abordaje: [{ id: 2, nombre: "Abordaje Comunitario - Línea Secos" }], territoriales: [{ id: 5, nombre: "Tere Territorial" }], proyectos: [], inactivos: {} },
    subzonas: [], tipo_entidad_actual: null,
    urls: { cancel: "/organizaciones/listar", subtipos: "/api/web/comedores/organizaciones/subtipos/", cuil: "/api/web/comedores/organizaciones/cuil/" },
    ...over,
  };
}
const payload = (f = form()) => ({ form: f, messages: [] });

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const fetchMock = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.sessionStorage.clear();
  fetchMock.mockImplementation((url: string) => Promise.resolve({ json: () => Promise.resolve(url.includes("/cuil/") ? { organizaciones: [] } : []) }));
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("Organizaciones ABM routes", () => {
  it("owns the native create, edit and delete paths without trailing slash", () => {
    for (const path of ["/organizaciones/crear", "/organizaciones/editar/8", "/organizaciones/eliminar/8"]) expect(findRoute(path)?.route.name).toBe("comedores-organizaciones");
    for (const other of ["/organizaciones/crear/", "/organizaciones/editar/0", "/organizaciones/subtipos-entidad/ajax/", "/organizaciones/eliminar/x"]) expect(findRoute(other)?.route.name).not.toBe("comedores-organizaciones");
  });

  it("renders the native sections, saves one POST and keeps the Django message for the next screen", async () => {
    const assign = vi.spyOn(organizacionesNavigation, "assign").mockImplementation(() => undefined);
    serve(payload());
    webPost.mockResolvedValue({ status: 201, data: { redirect: "/organizaciones/detalle/9", messages: [{ message: "Listo", level: "success" }] } });
    setup("/organizaciones/crear");
    await screen.findByRole("heading", { level: 3, name: "Información Básica" });
    expect(webGet).toHaveBeenCalledWith(`${API}formulario/`, expect.anything());
    expect(["Información Básica", "Contacto", "Ubicación y Domicilio", "Vigencia", "Programas"].every((t) => screen.getByRole("heading", { level: 3, name: t }))).toBe(true);
    expect(document.getElementById("abordaje-card")!.className).toContain("d-none");
    expect(document.getElementById("completedSections")?.textContent).toBe("0");
    fireEvent.change(screen.getByLabelText(/^Nombre/), { target: { value: "Org <Nueva>" } });
    fireEvent.change(screen.getByLabelText("Provincia"), { target: { value: "7" } });
    fireEvent.click(screen.getByLabelText("Sin vencimiento"));
    fireEvent.click(screen.getByLabelText("Abordaje Comunitario - Línea Secos"));
    await waitFor(() => expect(document.getElementById("abordaje-card")!.className).not.toContain("d-none"));
    fireEvent.change(screen.getByLabelText("Nuevo código de proyecto"), { target: { value: "PRY-1" } });
    fireEvent.click(screen.getByRole("button", { name: /Agregar proyecto/ }));

    fireEvent.change(screen.getByLabelText("Agregar territorial al proyecto PRY-1"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar organización" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/organizaciones/detalle/9"));
    const [url, body] = webPost.mock.calls[0] as [string, URLSearchParams];
    expect(url).toBe(`${API}crear/`);
    expect(body.get("nombre")).toBe("Org <Nueva>");
    expect([...body.keys()]).not.toContain("deleted_at");
    expect([...body.keys()]).not.toContain("territoriales_abordaje_comunitario");
    expect([body.get("provincia"), body.get("sin_vencimiento"), body.getAll("programas")]).toEqual(["7", "on", ["2"]]);
    expect(JSON.parse(body.get("proyectos_lineas")!)).toEqual([{ codigo: "PRY-1", linea: 2 }]);
    expect(JSON.parse(body.get("asignaciones_territoriales")!)).toEqual([{ proyecto: "PRY-1", territorial: 5 }]);
    expect(JSON.parse(window.sessionStorage.getItem(FLASH_KEY)!)).toEqual([{ message: "Listo", level: "success" }]);
  });

  it("shows the Django errors verbatim on 400 and keeps what the user typed", async () => {
    serve(payload());
    const invalid = form({}, { cuit: { value: "123", errors: ["Ingresá un CUIT de 11 dígitos, solo con números y sin espacios."] }, nombre: { value: "Tipeado" } });
    invalid.non_field_errors = ["Error global"] as never;
    webPost.mockResolvedValue({ status: 400, data: { errors: {}, non_field_errors: ["Error global"], form: invalid } });
    setup("/organizaciones/crear");
    await screen.findByLabelText(/^Nombre/);
    fireEvent.change(screen.getByLabelText(/^Nombre/), { target: { value: "Tipeado" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar organización" }));
    expect(await screen.findByText("Ingresá un CUIT de 11 dígitos, solo con números y sin espacios.")).toBeTruthy();
    expect(screen.getByText("Error global")).toBeTruthy();
    expect((screen.getByLabelText(/^Nombre/) as HTMLInputElement).value).toBe("Tipeado");
    expect(screen.getByLabelText("Cuit").className).toContain("is-invalid");
  });

  it("asks to confirm a duplicated CUIT before saving", async () => {
    serve(payload());
    fetchMock.mockImplementation((url: string) => Promise.resolve({ json: () => Promise.resolve(url.includes("/cuil/")
      ? { organizaciones: [{ id: 3, nombre: "Dueña", tipo_entidad: "", subtipo_entidad: "", telefono: "", email: "", domicilio: "", provincia: "", municipio: "", localidad: "" }] } : []) }));
    webPost.mockResolvedValue({ status: 201, data: { redirect: "/organizaciones/detalle/9", messages: [] } });
    vi.spyOn(organizacionesNavigation, "assign").mockImplementation(() => undefined);
    setup("/organizaciones/crear");
    await screen.findByLabelText(/^Nombre/);
    fireEvent.change(screen.getByLabelText(/^Nombre/), { target: { value: "Org" } });
    fireEvent.change(screen.getByLabelText("Cuit"), { target: { value: "20111111112" } });
    expect(await screen.findByText("Dueña")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith("/api/web/comedores/organizaciones/cuil/?cuil=20111111112", expect.anything());
    const save = screen.getByRole("button", { name: "Guardar organización" }) as HTMLButtonElement;
    expect(save.disabled).toBe(true);
    fireEvent.click(screen.getByLabelText("Revisé la información y confirmo la creación del nuevo registro"));
    expect(save.disabled).toBe(false);
    fireEvent.click(save);
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    const body = webPost.mock.calls[0][1] as URLSearchParams;
    expect([body.get("cuil_duplicado_confirmado"), body.get("cuil_duplicado_confirmado_valor")]).toEqual(["on", "20111111112"]);
  });

  it("confirms a tipo de entidad change on edit before posting to the edit endpoint", async () => {
    serve(payload(form({ organizacion_id: 8, tipo_entidad_actual: 1, urls: { ...form().urls, cancel: "/organizaciones/detalle/8" } }, { tipo_entidad: { value: "1" }, nombre: { value: "Vieja" } })));
    webPost.mockResolvedValue({ status: 200, data: { redirect: "/organizaciones/detalle/8", messages: [] } });
    vi.spyOn(organizacionesNavigation, "assign").mockImplementation(() => undefined);
    setup("/organizaciones/editar/8");
    await screen.findByLabelText(/^Nombre/);
    expect(webGet).toHaveBeenCalledWith(`${API}8/formulario/`, expect.anything());
    fireEvent.change(screen.getByLabelText("Tipo entidad"), { target: { value: "2" } });
    expect(screen.getByText(/Al cambiar el Tipo de Entidad se reiniciará/).closest("#tipo-entidad-warning")!.className).not.toContain("d-none");
    fireEvent.click(screen.getByRole("button", { name: "Guardar organización" }));
    const modal = await screen.findByRole("dialog");
    expect(within(modal).getByRole("heading", { name: /Confirmar cambio de Tipo de Entidad/ })).toBeTruthy();
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.click(within(modal).getByRole("button", { name: "Confirmar cambio" }));
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe(`${API}8/editar/`);
  });

  it("validates the payloads", () => {
    expect(formValid(payload())).toBe(true);
    expect(formValid({ ...payload(), messages: [{ message: 1 }] })).toBe(false);
    expect(formValid(payload(form({ urls: { cancel: "https://evil.example/", subtipos: "/a/", cuil: "/b/" } })))).toBe(false);
    expect(bajaValid({ id: 1, nombre: "N", cascade_preview: null, motivo: null, urls: { cancel: "/a", list: "/b" }, messages: [] })).toBe(true);
    expect(bajaValid({ id: "1" })).toBe(false);
  });
});

describe("Organizaciones baja route", () => {
  const baja = (over: Record<string, unknown> = {}) => ({
    id: 8, nombre: "Para baja", motivo: null, urls: { cancel: "/organizaciones/detalle/8", list: "/organizaciones/listar" }, messages: [],
    cascade_preview: { total_afectados: 2, total_baja_logica: 2, desglose_por_modelo: [{ modelo: "Organización", cantidad: 1, modo: "baja_logica", ejemplos: ["Para baja"] }, { modelo: "Firmante", cantidad: 1, modo: "baja_logica", ejemplos: [] }] },
    ...over,
  });

  it("shows the cascade preview and deletes through the native view", async () => {
    const assign = vi.spyOn(organizacionesNavigation, "assign").mockImplementation(() => undefined);
    serve(baja());
    webPost.mockResolvedValue({ status: 200, data: { redirect: "/organizaciones/listar", messages: [{ message: "La organización Para baja fue dada de baja correctamente.", level: "success" }] } });
    setup("/organizaciones/eliminar/8");
    expect(await screen.findByText("PARA BAJA")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}8/baja/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Organizacion - Para baja"));
    expect(screen.getByText("Total de registros afectados:").parentElement?.textContent).toBe("Total de registros afectados: 2");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/organizaciones/detalle/8");
    expect(screen.getAllByRole("row").map((r) => r.textContent)).toContain("Firmante1Baja lógica-");
    fireEvent.click(screen.getByRole("button", { name: "Dar de baja Organización" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/organizaciones/listar"));
    expect(webPost.mock.calls[0][0]).toBe(`${API}8/baja/`);
    expect(JSON.parse(window.sessionStorage.getItem(FLASH_KEY)!)[0].message).toBe("La organización Para baja fue dada de baja correctamente.");
  });

  it("keeps the page and shows the native reason when the baja is blocked", async () => {
    const reason = "No se puede dar de baja la organización: tiene 1 proyecto(s) (PRY-9). Darla de baja borraría esos proyectos y sus datos.";
    serve(baja({ motivo: reason }));
    webPost.mockResolvedValue({ status: 409, data: { error: reason, messages: [{ message: reason, level: "error" }] } });
    const assign = vi.spyOn(organizacionesNavigation, "assign").mockImplementation(() => undefined);
    setup("/organizaciones/eliminar/8");
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja Organización" }));
    expect(await screen.findByText(reason)).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
  });
});
