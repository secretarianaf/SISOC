// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { inetClient, inetGet, type InetItem, type InetSession } from "@sisoc/api";
import App from "./App";

vi.mock("@sisoc/api", async (original) => ({ ...await original<typeof import("@sisoc/api")>(), inetGet: vi.fn(), inetClient: { post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
const item: InetItem = { id: 1, nombre: "CFP de prueba", cue: "060144900", provincia: "Buenos Aires", localidad: "Tolosa", estado: "Activo", centro_id: 1, curso_id: null, comision_id: null, fecha_inicio: null, fecha_fin: null, detalle: [{ label: "Domicilio", value: "Calle de prueba 123" }], puede_gestionar: true, puede_editar: true, puede_eliminar: true, comisiones_count: 0, inscriptos_count: 0, clases_count: 0, clases_realizadas: 0, asistencia_pct: null, documento: "", email: "", telefono: "", identidad_pendiente: false };
const session: InetSession = { username: "operador", nombre: "Operador de prueba", permissions: ["view_centro", "add_centro", "change_centro", "view_curso", "add_curso", "add_inscripcion"], puede_ver_planes: true };
const emptyPage = { count: 0, next: null, previous: null, results: [] };
function setup(path = "/v2/inet/centros/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></QueryClientProvider>);
}
beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false, addListener: vi.fn(), removeListener: vi.fn(), addEventListener: vi.fn(), removeEventListener: vi.fn() })));
  vi.mocked(inetGet).mockImplementation(async (path) => {
    if (path === "session/") return session;
    if (path.includes("filter-form/")) return { fields: [] };
    if (path.startsWith("centros/?")) return { ...emptyPage, count: 1, results: [item] };
    if (path === "centros/1/") return item;
    if (path.startsWith("centros/form/")) return { fields: [{ name: "nombre", label: "Denominación", kind: "text", required: true, disabled: false, help_text: "", value: "", options: [], remote_options: false }] };
    if (path === "sesiones/1/") return { ...item, nombre: "Clase 1", comision_id: 1, estado: "Programada" };
    if (path.includes("/asistencia/")) return { sesion_id: 1, fecha: "2026-10-05", filas: [{ inscripcion_id: 9, nombre: "Ana de prueba", documento: "Documento de prueba", presente: null, observaciones: "" }] };
    return emptyPage;
  });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("INET React", () => {
  it("abre el legajo desde el buscador con navegación React", async () => {
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Ver CFP de prueba" }, { timeout: 5000 }));
    expect(await screen.findByText("Calle de prueba 123")).toBeDefined();
    expect(screen.getByRole("tab", { name: /Ubicaciones/ })).toBeDefined();
  });
  it("muestra los errores de validación junto al campo y conserva el formulario", async () => {
    vi.mocked(inetClient.post).mockRejectedValue({ response: { status: 400, data: { campos: { nombre: ["La denominación no es válida."] } } } });
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Agregar CFP" }));
    fireEvent.change(await screen.findByLabelText("Denominación", { exact: false }), { target: { value: "Prueba" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(screen.getAllByText(/La denominación no es válida/).length).toBeGreaterThan(0));
    expect(screen.getByRole("dialog")).toBeDefined();
    expect(inetClient.post).toHaveBeenCalledWith("centros/", { campos: { nombre: "Prueba" } });
  });
  it("envía toda la nómina al guardar asistencia y convierte los no marcados a ausentes en el backend", async () => {
    vi.mocked(inetClient.put).mockResolvedValue({ data: undefined });
    setup("/v2/inet/sesiones/1/asistencia/");
    fireEvent.click(await screen.findByRole("checkbox", { name: "Presente Ana de prueba" }));
    fireEvent.click(screen.getByRole("button", { name: "Guardar asistencia" }));
    await waitFor(() => expect(inetClient.put).toHaveBeenCalledWith("sesiones/1/asistencia/", expect.objectContaining({ filas: [expect.objectContaining({ inscripcion_id: 9, presente: true })] })));
  });
  it("oculta planes curriculares cuando el actor no puede verlos", async () => {
    vi.mocked(inetGet).mockImplementation(async () => ({ ...session, puede_ver_planes: false }));
    setup("/v2/inet/planes/");
    expect(await screen.findByText("No tenés permiso para administrar planes curriculares.")).toBeDefined();
    expect(screen.queryByRole("link", { name: "Planes curriculares" })).toBeNull();
  });
  it("aplica la búsqueda sólo al agregar un filtro y permite quitarlo", async () => {
    setup();
    const input = await screen.findByRole("textbox", { name: "Valor del filtro Nombre" });
    fireEvent.change(input, { target: { value: "Electricidad" } });
    expect(vi.mocked(inetGet).mock.calls.some(([path]) => path.includes("nombre=Electricidad"))).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Agregar filtro" }));
    await waitFor(() => expect(vi.mocked(inetGet).mock.calls.some(([path]) => path.includes("nombre=Electricidad"))).toBe(true));
    expect(screen.getByRole("button", { name: "Nombre: Electricidad" })).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Limpiar filtros" }));
    expect(screen.queryByRole("button", { name: "Nombre: Electricidad" })).toBeNull();
  });

  it("no crea una comisión antes de confirmar el resumen", async () => {
    const fallback = vi.mocked(inetGet).getMockImplementation()!;
    const field = (name: string, label: string, kind: string, value: string, options: { value: string; label: string }[] = []) => ({ name, label, kind, value, options, required: true, disabled: false, help_text: "", remote_options: false });
    vi.mocked(inetGet).mockImplementation(async (path) => {
      if (path === "cursos/1/") return { ...item, nombre: "Electricidad" };
      if (path.startsWith("comisiones/form/")) return { fields: [field("ubicacion", "Ubicación", "select", "1", [{ value: "1", label: "Sede" }]), field("cupo_total", "Cupo", "number", "5"), field("fecha_inicio", "Inicio", "date", "2026-10-07"), field("fecha_fin", "Fin", "date", "2026-10-31")] };
      if (path === "horario-form/") return { fields: [field("dia_semana", "Día", "select", "", [{ value: "1", label: "Miércoles" }]), field("hora_desde", "Desde", "time", ""), field("hora_hasta", "Hasta", "time", "")] };
      return fallback(path);
    });
    vi.mocked(inetClient.post).mockResolvedValue({ data: { ...item, centro_id: 1 } });
    setup("/v2/inet/comisiones/nueva/?curso=1");
    fireEvent.mouseDown(await screen.findByLabelText("Día", { exact: false }));
    fireEvent.click(await screen.findByRole("option", { name: "Miércoles" }));
    fireEvent.change(screen.getByLabelText("Desde", { exact: false }), { target: { value: "09:00" } });
    fireEvent.change(screen.getByLabelText("Hasta", { exact: false }), { target: { value: "11:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear comisión" }));
    const dialog = await screen.findByRole("dialog", { name: "¿Crear la comisión?" });
    expect(inetClient.post).not.toHaveBeenCalled();
    expect(within(dialog).getByText(/Se van a generar 4 clases/)).toBeDefined();
    fireEvent.click(within(dialog).getByRole("button", { name: "Crear comisión" }));
    await waitFor(() => expect(inetClient.post).toHaveBeenCalledWith("comisiones/", expect.objectContaining({ horarios: [expect.objectContaining({ dia_semana: "1", hora_desde: "09:00", hora_hasta: "11:00" })] })));
  });

});
