import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const workflow = ["panel", "formacion", "cruces", "mesa-ayuda", "liquidacion"].map((key, i) => ({
  key, number: `0${i + 1}`, title: key, subtitle: key, url: `/pas/${key}`, active: i === 0, source_status: "disponible",
}));
const persona = (estado = "Activo") => ({
  id: 2, apellidos: "Apellido2", nombres: "Nombre2", dni: 30000002, id_persona: 7002, cuit: "", genero: "", provincia: "Buenos Aires",
  municipio: "La Matanza", domicilio: "", correo_electronico: "", telefono_celular: "", estado: { id: 1, nombre: estado, css_class: "pas-status-activo" },
  avisos: [], fecha_creacion: "01/11/2026 10:00", fecha_actualizacion: "02/11/2026 11:00", ddjj_vigente: null,
});
const panel = (estado = "Activo") => ({
  persona: persona(estado), workflow, query: "", estado_actual: "todos", estados_panel: [], personas_panel: [],
  ddjj: { declaraciones: [], seleccionada: null, vigente_download_url: null }, formaciones: [], eventos_historial: [],
  capabilities: { can_change: true },
  cambio_estado: {
    estados: [{ id: 1, nombre: "Activo" }, { id: 2, nombre: "Baja" }],
    avisos_por_estado: { 1: [{ id: 11, text: "101 - Alta inicial" }, { id: 12, text: "102 - Revisión" }], 2: [{ id: 12, text: "102 - Revisión" }, { id: 21, text: "201 - Fallecido" }] },
  },
});

function serve(...pages: unknown[]) {
  const queue = [...pages];
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/"
    ? { data: readyContext, status: 200 } : { data: queue.length > 1 ? queue.shift() : queue[0], status: 200 }));
}
async function openModal() {
  window.history.replaceState({}, "", "/pas/panel-control/2?q=Ap&estado_actual=1");
  render(<App />);
  const trigger = await screen.findByRole("button", { name: "Cambiar estado" });
  fireEvent.click(trigger);
  return { trigger, dialog: await screen.findByRole("dialog") };
}
function choose(id: string, label: string) {
  fireEvent.mouseDown(document.querySelector(`#${id} + .select2 .select2-selection`)!);
  fireEvent.click(screen.getByRole("option", { name: label }));
}

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => cleanup());

describe("PAS06.03 Cambiar estado", () => {
  it("opens the Bootstrap modal with the native texts, backdrop and focus", async () => {
    serve(panel());
    const { dialog } = await openModal();
    expect(dialog.id).toBe("cambiarEstadoModal");
    expect(dialog.className).toBe("modal fade show");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(document.activeElement).toBe(dialog);
    expect(document.body.classList.contains("modal-open")).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
    expect(document.querySelector("body > .modal-backdrop.fade.show")).toBeTruthy();
    expect(within(dialog).getByRole("heading", { name: "Cambiar estado PAS" })).toBeTruthy();
    expect(within(dialog).getByText("Estado actual:").textContent).toBe("Estado actual: Activo");
    expect(within(dialog).getByText("Seleccione una opcion")).toBeTruthy();
    expect(within(dialog).getByPlaceholderText("Seleccione avisos")).toBeTruthy();
    expect(within(dialog).getByRole("button", { name: "Cerrar" })).toBeTruthy();
    expect([...(document.getElementById("id_estado") as HTMLSelectElement).options].map((o) => o.textContent)).toEqual(["Seleccione un estado", "Activo", "Baja"]);
    expect((document.getElementById("id_avisos") as HTMLSelectElement).options).toHaveLength(0);
  });

  it("closes with Escape, Cancelar and the cross and gives the focus back", async () => {
    serve(panel());
    const { trigger, dialog } = await openModal();
    fireEvent.keyDown(dialog, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(document.activeElement).toBe(trigger);
    expect(document.body.classList.contains("modal-open")).toBe(false);
    expect(document.querySelector(".modal-backdrop")).toBeNull();
    expect(document.getElementById("cambiarEstadoModal")?.getAttribute("aria-hidden")).toBe("true");
    for (const name of ["Cancelar", "Cerrar"]) {
      fireEvent.click(trigger);
      fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name }));
      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    }
  });

  it("keeps the focus inside the open modal", async () => {
    serve(panel());
    const { dialog } = await openModal();
    document.querySelector<HTMLAnchorElement>('a[href="/pas/listar"]')!.focus();
    expect(dialog.contains(document.activeElement)).toBe(true);
  });

  it("filters the notices by state and posts the change, then reloads the panel with the message", async () => {
    serve(panel(), panel("Baja"));
    webPost.mockResolvedValue({ data: { message: "Estado PAS actualizado correctamente.", persona: {} }, status: 200 });
    const { dialog } = await openModal();
    choose("id_estado", "Activo");
    choose("id_avisos", "102 - Revisión");
    expect(within(dialog).getByTitle("102 - Revisión")).toBeTruthy();
    choose("id_estado", "Baja");
    // `populateAvisos` keeps a notice the new state also offers.
    expect(within(dialog).getByTitle("102 - Revisión")).toBeTruthy();
    choose("id_avisos", "201 - Fallecido");
    fireEvent.click(within(dialog).getByRole("button", { name: "Guardar cambio" }));
    await screen.findByText("Estado PAS actualizado correctamente.");
    const [endpoint, body] = webPost.mock.calls[0];
    expect(endpoint).toBe("web/pas/personas/2/cambiar-estado/");
    expect((body as URLSearchParams).toString()).toBe("estado=2&avisos=12&avisos=21");
    expect(window.location.pathname + window.location.search).toBe("/pas/panel-control/2");
    expect(webGet).toHaveBeenLastCalledWith("web/pas/panel/2/", expect.anything());
    expect(await screen.findByText("Apellido2, Nombre2 · DNI 30000002")).toBeTruthy();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.querySelector(".toast-success")?.textContent).toBe("Estado PAS actualizado correctamente.");
  });

  it("shows every form error as an error toast after a 400", async () => {
    serve(panel());
    webPost.mockRejectedValue({ response: { status: 400, data: { errors: {}, messages: ["Este campo es requerido.", "Este campo es requerido."] } } });
    const { dialog } = await openModal();
    fireEvent.submit(within(dialog).getByRole("button", { name: "Guardar cambio" }).closest("form")!);
    await waitFor(() => expect(document.querySelectorAll(".toast-error")).toHaveLength(2));
    expect([...document.querySelectorAll(".toast-error")].map((t) => t.textContent)).toEqual(["Este campo es requerido.", "Este campo es requerido."]);
    expect(window.location.pathname + window.location.search).toBe("/pas/panel-control/2");
  });

  it("does not retry an unconfirmed result: it reloads the panel and says so", async () => {
    serve(panel());
    webPost.mockRejectedValue({ response: { status: 504, data: { uncertain: true } } });
    const { dialog } = await openModal();
    fireEvent.submit(within(dialog).getByRole("button", { name: "Guardar cambio" }).closest("form")!);
    expect(await screen.findByText("No se pudo confirmar el resultado. Verificá el estado antes de reintentar.")).toBeTruthy();
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("shows the access screen when the POST is forbidden", async () => {
    serve(panel());
    webPost.mockResolvedValue({ data: { detail: "x" }, status: 403 });
    const { dialog } = await openModal();
    fireEvent.submit(within(dialog).getByRole("button", { name: "Guardar cambio" }).closest("form")!);
    await waitFor(() => expect(document.title).toBe("SISOC - Error 403"));
  });
});
