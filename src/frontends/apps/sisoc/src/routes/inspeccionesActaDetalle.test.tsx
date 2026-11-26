import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { actaNavigation } from "./inspeccionesActaNavigation";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const NUMERO = "ACTA-2026-000001";
const PATH = `/inspecciones/actas/${NUMERO}/`;
const API = `/api/web/inspecciones/actas/${NUMERO}/`;
const session = {
  ...readyContext,
  navigation: [
    { id: "inicio", label: "Inicio", href: "/inicio/", children: [] },
    { id: "mi_cuenta", label: "Mi cuenta", href: "/mi-cuenta/", children: [] },
  ],
};
const acta = (over: Record<string, unknown> = {}, actaOver: Record<string, unknown> = {}) => ({
  layout: {
    breadcrumb: [{ text: "Inicio", url: "/inicio/" }, { text: "Inspecciones escolares", url: "/inspecciones/" }, { text: NUMERO, url: null }],
    display_name: "Gestora Sintética", role: "Coordinación sintética", initials: "GS",
  },
  acta: {
    numero: NUMERO, anulada: false, anulada_at: "", anulada_por: "", motivo_anulacion: "", notificacion_cargada: false, prueba: false,
    linea: "EP N° 12 · Turno tarde · cierre oficial 09/11/2026 15:00", pdf_url: null,
    anular_url: `${API}anular/`, prueba_url: `${API}prueba/`, ...actaOver,
  },
  resumen: { abierta: "Sí", resultado: "Parcial", motivo_parcial: "Corte de luz", personal: "20 / 24", aulas: "— / 8" },
  formulario_version: "v1",
  respuestas: [
    { codigo: "F00", pregunta: "Nombre", respuesta: "EP N° 12", notas: [] },
    { codigo: "F16", pregunta: "Observaciones", respuesta: "Línea 1\nLínea 2", notas: ["Motivo: lluvia"] },
  ],
  evidencia: [{ url: `/inspecciones/actas/${NUMERO}/imagenes/11111111-1111-4111-8111-111111111111/`, titulo: "Ingreso (F04)", descripcion: "Frente", alt: "Ingreso (F04): Frente", capturada: "10:00", subida: "" }],
  notificaciones: [
    { version: 2, cargada: "09/11/2026 16:00 · por Ana", notificada: "09/11/2026 15:30", receptor: "Rosa · Directora", condicion_firma: "Firmada", motivo: "", observaciones: "", motivo_correccion: "Foto borrosa", archivos: [{ url: `/inspecciones/actas/${NUMERO}/notificaciones/22222222-2222-4222-8222-222222222222/`, alt: "Notificación, página 1" }] },
    { version: 1, cargada: "09/11/2026 15:40 · por Ana", notificada: "09/11/2026 15:30", receptor: "—", condicion_firma: "Sin receptor", motivo: "Cerrado", observaciones: "", motivo_correccion: "", archivos: [] },
  ],
  inspector: { nombre: "Ana Prueba", usuario: "inspector.1", filas: [["Jornada", "09/11/2026 · turno tarde"], ["Inicio", "—"]] },
  institucion: { editar_url: "/inspecciones/?editar=4", carga_manual: false, filas: [["Cueanexo", "060123400"], ["Mail", "a@b.ar"]] },
  ubicacion: { fuente: "GPS", es_gps: true, filas: [["Coordenadas", "-34.6, -58.4"]], mapa_url: "https://www.openstreetmap.org/?mlat=-34.6&mlon=-58.4#map=18/-34.6/-58.4" },
  recepcion: { tipo: "excepcion", imagen_url: null, imagen_alt: "", filas: [["Excepción", "Se negó"], ["Motivo", "—"]] },
  historial: [{ hora: "09/11 15:00", codigo: "finalizada", texto: "Finalizada · Ana Prueba", motivo: "" }],
  messages: [],
  ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: session, status: 200 } : { data, status }));
}

function setup(path = PATH) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "";
  document.body.removeAttribute("style");
  setViewport(false);
  vi.spyOn(actaNavigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("Inspecciones acta detail route", () => {
  it("owns only the native detail path", () => {
    expect(findRoute(PATH)?.route.name).toBe("inspecciones-acta-detalle");
    expect(findRoute(`/inspecciones/actas/${NUMERO}`)?.route.name).not.toBe("inspecciones-acta-detalle");
    expect(findRoute(`${PATH}pdf/`)?.route.name).not.toBe("inspecciones-acta-detalle");
    expect(findRoute("/inspecciones/actas/")?.route.name).toBe("inspecciones-actas");
  });

  it("loads the session and the acta API and prints the native page", async () => {
    serve(acta());
    setup();
    expect(await screen.findByRole("heading", { level: 1, name: NUMERO })).toBeTruthy();
    expect(webGet.mock.calls.map(([url]) => url)).toEqual(["web/session/", `web/inspecciones/actas/${NUMERO}/`]);
    await waitFor(() => expect(document.title).toBe("SISOC - Inspecciones escolares"));
    expect(screen.getByText("EP N° 12 · Turno tarde · cierre oficial 09/11/2026 15:00")).toBeTruthy();
    expect(screen.getByText("Finalizada").className).toBe("insp-badge insp-badge-ok");
    expect(screen.getByText("Excepción de firma")).toBeTruthy();
    expect(screen.getByText("Notificación pendiente")).toBeTruthy();
    expect(screen.queryByText("Prueba")).toBeNull();
    expect(screen.getByText("PDF pendiente").getAttribute("aria-disabled")).toBe("true");
    expect(screen.getByRole("link", { name: "Ver en el mapa" }).getAttribute("rel")).toBe("noopener noreferrer");
    expect(screen.getByText("Motivo: Corte de luz")).toBeTruthy();
    const celda = screen.getByText("Motivo: lluvia").parentElement as HTMLElement;
    expect(celda.innerHTML).toBe('Línea 1<br>Línea 2 <span class="insp-nota">Motivo: lluvia</span>');
    expect(screen.getByRole("img", { name: "Ingreso (F04): Frente" }).getAttribute("src")).toContain("/imagenes/");
    expect(screen.getByText("Tomada 10:00")).toBeTruthy();
    expect(screen.getByText("Versión anterior (v1)")).toBeTruthy();
    expect(screen.getByText("060123400").className).toBe("insp-mono");
    expect(screen.getByText("a@b.ar").className).toBe("text-break");
    expect(screen.getByRole("link", { name: "Editar institución" }).getAttribute("href")).toBe("/inspecciones/?editar=4");
    expect(screen.getByText("Finalizada · Ana Prueba")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Marcar como prueba" })).toBeTruthy();
  });

  it("shows the annulment notice, the test badge and hides the actions of an annulled acta", async () => {
    serve(acta({}, { anulada: true, anulada_at: "09/11/2026 18:00", anulada_por: "Coordina Cion", motivo_anulacion: "Escuela equivocada", prueba: true, pdf_url: `${PATH}pdf/` }));
    setup();
    const aviso = await screen.findByRole("alert");
    expect(aviso.textContent?.replace(/\s+/g, " ").trim()).toBe(
      "Acta anulada el 09/11/2026 18:00 por Coordina Cion . Motivo: Escuela equivocada Conserva su número y su contenido, pero no cuenta en los indicadores.",
    );
    expect(screen.getByText("Prueba").className).toBe("insp-badge insp-badge-neutro");
    expect(screen.queryByRole("button", { name: "Anular acta" })).toBeNull();
    expect(screen.queryByRole("button", { name: /prueba/ })).toBeNull();
    expect(screen.getByRole("link", { name: "Descargar PDF" }).getAttribute("href")).toBe(`${PATH}pdf/`);
  });

  it("shows queued messages as toasts", async () => {
    serve(acta({ messages: [{ message: `Acta ${NUMERO} anulada.`, level: "success" }] }));
    setup();
    const toast = await screen.findByText(`Acta ${NUMERO} anulada.`);
    const box = toast.closest(".toast") as HTMLElement;
    expect([box.className, box.style.display, box.getAttribute("aria-live")]).toEqual(["toast toast-success", "block", "polite"]);
    expect(toast.closest("#toast-container")?.className).toBe("toast-bottom-right");
  });

  it("opens the annul modal with focus, traps Tab, closes on Escape and returns focus", async () => {
    serve(acta());
    setup();
    const trigger = await screen.findByRole("button", { name: "Anular acta" });
    fireEvent.click(trigger);
    const dialog = screen.getByRole("dialog", { name: `Anular ${NUMERO}` });
    expect(document.activeElement).toBe(dialog);
    expect(document.body.classList.contains("modal-open")).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
    const textarea = within(dialog).getByLabelText(/Motivo/) as HTMLTextAreaElement;
    expect([textarea.minLength, textarea.required, textarea.name]).toEqual([10, true, "motivo"]);
    const submit = within(dialog).getByRole("button", { name: "Anular acta" });
    submit.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: "Cerrar" }));
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.body.classList.contains("modal-open")).toBe(false);
    expect(document.activeElement).toBe(trigger);
    expect(webPost).not.toHaveBeenCalled();
  });

  it("posts the annulment once to the API and follows the native redirect", async () => {
    serve(acta());
    let resolve: (value: unknown) => void = () => undefined;
    webPost.mockReturnValue(new Promise((ok) => { resolve = ok; }));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Anular acta" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText(/Motivo/), { target: { value: "Escuela equivocada" } });
    const form = dialog.querySelector("form") as HTMLFormElement;
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(`web/inspecciones/actas/${NUMERO}/anular/`);
    expect(Object.fromEntries(body as URLSearchParams)).toEqual({ csrfmiddlewaretoken: "synthetic-csrf-token", next: PATH, motivo: "Escuela equivocada" });
    resolve({ data: { ok: true, redirect: PATH }, status: 200 });
    await waitFor(() => expect(actaNavigation.assign).toHaveBeenCalledWith(PATH));
  });

  it("posts the test mark with the native fields and refuses an external redirect", async () => {
    serve(acta({}, { prueba: true }));
    webPost.mockResolvedValue({ data: { ok: true, redirect: "https://ejemplo.com/" }, status: 200 });
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Quitar marca de prueba" }));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(`web/inspecciones/actas/${NUMERO}/prueba/`);
    expect(Object.fromEntries(body as URLSearchParams)).toEqual({ csrfmiddlewaretoken: "synthetic-csrf-token", next: PATH, es_prueba: "0" });
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    expect(actaNavigation.assign).not.toHaveBeenCalled();
  });

  it("shows the access error on a 403 and an error on an invalid payload", async () => {
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    setup();
    await waitFor(() => expect(screen.queryByText("Cargando acta…")).toBeNull());
    expect(screen.queryByRole("heading", { level: 1, name: NUMERO })).toBeNull();
    cleanup();
    serve(acta({ ubicacion: { fuente: "GPS", es_gps: true, filas: [], mapa_url: "javascript:alert(1)" } }));
    setup();
    expect(await screen.findByText("No se pudo cargar el acta.")).toBeTruthy();
  });
});
