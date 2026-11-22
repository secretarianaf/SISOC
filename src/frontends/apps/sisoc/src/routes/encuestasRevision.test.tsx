import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { revisionValid } from "./encuestasRevision";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const pregunta = (over = {}) => ({
  numero: 1, tipo: "opcion_unica", tipo_label: "Opción única", obligatoria: true, texto: "¿Cómo calificás?", condicion: null, pondera: true, puntaje_si: null, puntaje_no: null,
  opciones: [{ texto: "Bueno", puntaje: 5 }, { texto: "Malo", puntaje: 1 }], ...over,
});
const page = (over = {}) => ({
  id: 7, titulo: "Satisfacción", version: 2, estado: "pendiente_aprobacion", estado_label: "Pendiente de aprobación", creador: "Ana Gestora", motivo_rechazo: null,
  descripcion: "Primera línea\nSegunda línea", modalidad: "Obligatoria", es_anonima: false, disponible_pwa: true, duracion_ronda_dias: 7, es_recurrente: false,
  intervalo_recurrencia_dias: null, intervalo_recordatorio_dias: 0,
  segmentacion: { tipo: "listado_documentos", label: "Listado de documentos", destinatarios: ["DNI: 30111222"], usuarios: [], grupos: [] },
  preguntas: [pregunta(), pregunta({ numero: 2, tipo: "si_no", tipo_label: "Sí/No", texto: "¿Volverías?", puntaje_si: 3, puntaje_no: 1, opciones: [] }),
    pregunta({ numero: 3, tipo: "texto_largo", tipo_label: "Texto largo", obligatoria: false, texto: "Comentarios", pondera: false, opciones: [], condicion: "Se muestra si «¿Volverías?» igual a «no»." })],
  solicitada_por: "Ana Gestora", fecha_solicitud: "01/10/2026 09:30", puede_aprobar: true, messages: [], ...over,
});
const serve = (data: unknown, status = 200) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
const assign = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  window.history.replaceState({}, "", "/encuestas/7/revision/");
  setViewport(false);
  vi.stubGlobal("location", { ...window.location, assign, replace: vi.fn(), pathname: "/encuestas/7/revision/", search: "" });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("revision de una solicitud de publicacion", () => {
  it("owns /encuestas/<id>/revision/ and validates the payload", () => {
    expect(findRoute("/encuestas/7/revision/")?.route.name).toBe("encuestas-revision");
    expect(revisionValid(page())).toBe(true);
    expect(revisionValid(page({ segmentacion: null }))).toBe(true);
    expect(revisionValid(page({ version: "2" }))).toBe(false);
    expect(revisionValid(page({ preguntas: [pregunta({ opciones: [{ texto: 1 }] })] }))).toBe(false);
  });

  it("draws the data, the recipients and the questions as the native page", async () => {
    serve(page());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Satisfacción", level: 1 })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/encuestas/7/revision/", expect.anything());
    await waitFor(() => expect(document.title).toContain("Revisar encuesta"));
    expect(screen.getByText("Versión 2 · Creada por Ana Gestora")).toBeTruthy();
    expect(screen.getByText("PWA de Espacios Comunitarios: Habilitada")).toBeTruthy();
    expect(screen.getByText("Una única ronda")).toBeTruthy();
    expect(screen.queryByText("Recordatorio")).toBeNull();
    expect(screen.getByText("Ver 1 destinatario")).toBeTruthy();
    expect(screen.getByText("DNI: 30111222")).toBeTruthy();
    expect(screen.getByText("Preguntas (3)")).toBeTruthy();
    expect(screen.getByText("Pregunta 1 · Opción única · Obligatoria")).toBeTruthy();
    expect(screen.getByText("Pregunta 3 · Texto largo · Opcional")).toBeTruthy();
    expect(screen.getByText("Se muestra si «¿Volverías?» igual a «no».")).toBeTruthy();
    expect(screen.getAllByText("· 5 puntos").length).toBe(1);
    expect(screen.getByText("· 3 puntos")).toBeTruthy();
    expect(screen.getByText("El usuario completará su respuesta al recibir la encuesta.")).toBeTruthy();
    expect(screen.getByText("Solicitada por").nextElementSibling?.textContent).toBe("Ana Gestora");
    expect(screen.getByRole("link", { name: "Encuestas" }).getAttribute("href")).toBe("/encuestas/");
  });

  it("approves through its endpoint and follows the native redirect", async () => {
    serve(page());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/encuestas/", messages: [] } });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Aprobar y publicar/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    expect(webPost.mock.calls[0][0]).toBe("web/encuestas/7/aprobar/");
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/encuestas/"));
  });

  it("opens the modal, posts the reason and navigates on success", async () => {
    serve(page());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/encuestas/", messages: [] } });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Rechazar solicitud/ }));
    const area = (await screen.findByLabelText(/Motivo del rechazo/)) as HTMLTextAreaElement;
    expect(area.required).toBe(true);
    expect(area.maxLength).toBe(2000);
    await waitFor(() => expect(document.activeElement).toBe(area));
    fireEvent.change(area, { target: { value: "Revisar las opciones" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar rechazo" }));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    expect(webPost.mock.calls[0][0]).toBe("web/encuestas/7/rechazar/");
    expect(Object.fromEntries((webPost.mock.calls[0][1] as URLSearchParams).entries())).toEqual({ motivo: "Revisar las opciones" });
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/encuestas/"));
  });

  it("keeps the modal open with the error and the typed text on the native 400", async () => {
    serve(page());
    webPost.mockResolvedValue({ status: 400, data: { errors: { motivo: [{ message: "Indicá qué debe corregir el gestor.", code: "required" }] } } });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Rechazar solicitud/ }));
    fireEvent.change(await screen.findByLabelText(/Motivo del rechazo/), { target: { value: "  " } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar rechazo" }));
    expect(await screen.findByText("Indicá qué debe corregir el gestor.")).toBeTruthy();
    expect(document.querySelector("#motivo-rechazo-error ul.errorlist")).toBeTruthy();
    expect((screen.getByLabelText(/Motivo del rechazo/) as HTMLTextAreaElement).value).toBe("  ");
    expect(assign).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByLabelText(/Motivo del rechazo/)).toBeNull();
  });

  it("says so and allows a retry when the request fails", async () => {
    serve(page());
    webPost.mockRejectedValueOnce(new Error("network"));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Aprobar y publicar/ }));
    expect(await screen.findByText("No se pudo completar la operación.")).toBeTruthy();
    await waitFor(() => expect((screen.getByRole("button", { name: /Aprobar y publicar/ }) as HTMLButtonElement).disabled).toBe(false));
  });

  it("shows no decision buttons to an editor and a note for a survey that is not pending", async () => {
    serve(page({ puede_aprobar: false }));
    const { unmount } = render(<App />);
    expect(await screen.findByText("Un administrador de encuestas debe aprobar o rechazar la solicitud.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Aprobar y publicar/ })).toBeNull();
    unmount();
    serve(page({ estado: "borrador", estado_label: "Borrador", motivo_rechazo: { texto: "Falta contexto\ny ejemplos", usuario: "Alicia", fecha: "02/10/2026 10:00" } }));
    render(<App />);
    expect(await screen.findByText("Esta encuesta no tiene una solicitud pendiente de aprobación.")).toBeTruthy();
    expect(screen.getByText("Cambios solicitados")).toBeTruthy();
    expect(screen.getByText("Alicia · 02/10/2026 10:00")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Rechazar solicitud/ })).toBeNull();
  });

  it("draws the groups, the users and the all-users segmentation", async () => {
    serve(page({ segmentacion: { tipo: "grupos", label: "Grupos", destinatarios: [], usuarios: [], grupos: ["Equipo Norte"] }, preguntas: [] }));
    const { unmount } = render(<App />);
    expect(await screen.findByText("Equipo Norte")).toBeTruthy();
    expect(screen.getByText("La encuesta todavía no tiene preguntas.")).toBeTruthy();
    unmount();
    serve(page({ segmentacion: { tipo: "listado_usuarios", label: "Usuarios", destinatarios: [], usuarios: [{ id: 5, username: "dora", full_name: "Dora Sur" }], grupos: [] } }));
    const second = render(<App />);
    expect(await screen.findByText("ID 5: dora · Dora Sur")).toBeTruthy();
    second.unmount();
    serve(page({ segmentacion: { tipo: "todos_los_usuarios", label: "Todos", destinatarios: [], usuarios: [], grupos: [] } }));
    render(<App />);
    expect(await screen.findByText("La encuesta estará disponible para todos los usuarios que inicien sesión.")).toBeTruthy();
  });

  it("shows the access screen on 403", async () => {
    serve({ detail: "No tiene permisos para esta acción." }, 403);
    render(<App />);
    expect(await screen.findByText(/permiso/i)).toBeTruthy();
    expect(screen.queryByText("Revisión de publicación")).toBeNull();
  });
});
