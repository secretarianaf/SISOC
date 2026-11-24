import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { asistenciaValid } from "./vatAsistencia";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const CURSO = "/vat/cursos/comisiones/sesiones/8/asistencia/";
const API_CURSO = "web/vat/cursos/comisiones/sesiones/8/asistencia/";
const fila = (id: number, over: Record<string, unknown> = {}) => ({
  id, apellido: `Apellido${id}`, nombre: `Nombre${id}`, tipo_alumno: "Sin Plan", es_alumno_vat: false, presente: null, observaciones: "", ...over,
});
const data = (over: Record<string, unknown> = {}) => ({
  numero_sesion: 3, comision_label: "Comisión 12 - CFP 401", curso: "Electricidad básica - CFP 401", estado: "Planificada", dia: "Lunes 9 de marzo",
  horario: "09:00 a 12:30 hs", totales: { presentes: "0", ausentes: "0", sin_marcar: "2" }, filas: [fila(1), fila(2, { es_alumno_vat: true, tipo_alumno: "VAT" })], messages: [], ...over,
});

function serve(payload: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: payload, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const metrics = () => ["asisMetricPresentes", "asisMetricAusentes", "asisMetricSinMarcar"].map((id) => document.getElementById(id)?.textContent);
const radio = (value: string, row: number) => document.querySelectorAll<HTMLInputElement>(`input[type=radio][value="${value}"]`)[row];

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT asistencia route", () => {
  it("owns the course and the offer attendance paths only", () => {
    for (const path of [CURSO, "/vat/comisiones/sesiones/8/asistencia/"]) expect(findRoute(path)?.route.name).toBe("vat-asistencia");
    for (const other of ["/vat/cursos/comisiones/sesiones/8/asistencia", "/vat/comisiones/sesiones/x/asistencia/", "/vat/comisiones/8/", "/vat/cursos/sesiones/8/asistencia/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-asistencia");
    }
  });

  it("renders the native layout, the counters and the tour help", async () => {
    serve(data());
    setup(CURSO);
    expect(await screen.findByRole("heading", { level: 1, name: "Comisión 12 - CFP 401" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(API_CURSO, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Registro de asistencia — Clase #3"));
    expect(screen.getByText("Electricidad básica - CFP 401")).toBeTruthy();
    expect(screen.getByText("Planificada").className).toBe("asis-status-pill");
    expect(screen.getByText("Registro de asistencia clase #3")).toBeTruthy();
    expect(screen.getByText("Lunes 9 de marzo")).toBeTruthy();
    expect(screen.getByText("09:00 a 12:30 hs")).toBeTruthy();
    expect(metrics()).toEqual(["0", "0", "2"]);
    expect(screen.getByText("VAT").className).toBe("asis-chip-vat");
    expect(screen.getByText("Sin Plan").className).toBe("asis-tipo-sin-plan");
    expect(document.getElementById("asisConteo")?.textContent).toBe("Mostrando 1-2 de 2");
    expect(document.getElementById("asisPager")?.textContent).toBe("1 de 1");
    expect((document.getElementById("asisPrev") as HTMLButtonElement).disabled).toBe(true);
    expect((document.getElementById("asisNext") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole("button", { name: /Tour de ayuda/ })).toBeTruthy();
  });

  it("recounts the cards when a radio or a mark-all box changes, like the native script", async () => {
    serve(data());
    setup(CURSO);
    await screen.findByText("Registro de asistencia clase #3");
    fireEvent.click(radio("1", 0));
    expect(metrics()).toEqual(["1", "0", "1"]);
    fireEvent.click(radio("0", 1));
    expect(metrics()).toEqual(["1", "1", "0"]);
    fireEvent.click(document.getElementById("asisMarcarPresentes")!);
    expect(metrics()).toEqual(["2", "0", "0"]);
    expect(radio("1", 1).checked).toBe(true);
    fireEvent.click(document.getElementById("asisMarcarAusentes")!);
    expect(metrics()).toEqual(["0", "2", "0"]);
    expect((document.getElementById("asisMarcarPresentes") as HTMLInputElement).checked).toBe(false);
    fireEvent.click(document.getElementById("asisMarcarAusentes")!);
    expect(metrics()).toEqual(["0", "2", "0"]);
  });

  it("pages the rows ten at a time on the client and keeps the hidden rows in the form", async () => {
    serve(data({ filas: Array.from({ length: 12 }, (_, i) => fila(i + 1)), totales: { presentes: "0", ausentes: "0", sin_marcar: "12" } }));
    setup(CURSO);
    await screen.findByText("Registro de asistencia clase #3");
    const rows = () => Array.from(document.querySelectorAll("tr.asis-row")).map((r) => r.classList.contains("d-none"));
    expect(rows().filter((hidden) => !hidden)).toHaveLength(10);
    expect(document.getElementById("asisConteo")?.textContent).toBe("Mostrando 1-10 de 12");
    expect(document.getElementById("asisPager")?.textContent).toBe("1 de 2");
    fireEvent.click(document.getElementById("asisNext")!);
    expect(document.getElementById("asisConteo")?.textContent).toBe("Mostrando 11-12 de 12");
    expect(document.getElementById("asisPager")?.textContent).toBe("2 de 2");
    expect(rows().slice(0, 10).every(Boolean)).toBe(true);
    expect((document.getElementById("asisNext") as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(document.getElementById("asisPrev")!);
    expect(document.getElementById("asisPager")?.textContent).toBe("1 de 2");
    expect(document.querySelectorAll("input[type=radio][value='1']")).toHaveLength(12);
  });

  it("posts one pair of fields per marked row, with the notes, and navigates on success", async () => {
    serve(data({ filas: [fila(1, { presente: true, observaciones: "Con certificado" }), fila(2), fila(3, { presente: false })] }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/cursos/comisiones/5/" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup(CURSO);
    await screen.findByText("Registro de asistencia clase #3");
    fireEvent.click(radio("0", 0));
    fireEvent.click(screen.getByRole("button", { name: /Guardar Asistencia/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/cursos/comisiones/5/"));
    expect(webPost.mock.calls[0][0]).toBe(API_CURSO);
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams)).toEqual({
      obs_1: "Con certificado", presente_1: "0", obs_2: "", obs_3: "", presente_3: "0",
    });
  });

  it("reports an unconfirmed result and does not resend", async () => {
    serve(data());
    webPost.mockRejectedValue(new Error("network"));
    setup(CURSO);
    await screen.findByText("Registro de asistencia clase #3");
    fireEvent.click(screen.getByRole("button", { name: /Guardar Asistencia/ }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Guardar Asistencia/ }));
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("shows the empty state with the server counters, which are blank on the offer variant", async () => {
    serve(data({ filas: [], totales: { presentes: "", ausentes: "", sin_marcar: "" }, curso: "", estado: "" }));
    setup("/vat/comisiones/sesiones/8/asistencia/");
    expect(await screen.findByText("Sin inscriptos aceptados")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/vat/comisiones/sesiones/8/asistencia/", expect.anything());
    expect(screen.getByText("Aceptá inscripciones desde el detalle de la comisión para poder tomar asistencia.")).toBeTruthy();
    expect(metrics()).toEqual(["", "", ""]);
    expect(screen.queryByRole("button", { name: /Guardar Asistencia/ })).toBeNull();
  });

  it("shows queued messages as toasts", async () => {
    serve(data({ messages: [{ message: "Asistencia registrada exitosamente.", level: "success" }] }));
    setup(CURSO);
    expect(await screen.findByText("Asistencia registrada exitosamente.")).toBeTruthy();
  });

  it("validates the payload shape", () => {
    expect(asistenciaValid(data())).toBe(true);
    expect(asistenciaValid(data({ filas: [{ id: 1 }] }))).toBe(false);
    expect(asistenciaValid(data({ totales: { presentes: 1 } }))).toBe(false);
    expect(asistenciaValid({})).toBe(false);
  });

  it("keeps the first tab stops in the native order: all-present box, all-absent box, then each row", async () => {
    serve(data());
    setup(CURSO);
    await screen.findByText("Registro de asistencia clase #3");
    const form = document.getElementById("asisForm") as HTMLFormElement;
    const order = Array.from(form.querySelectorAll("input:not([type=hidden]),button")).map((e) => (e as HTMLElement).id || (e as HTMLInputElement).name || e.textContent);
    expect(order.slice(0, 3)).toEqual(["asisMarcarPresentes", "asisMarcarAusentes", "presente_1"]);
    expect(within(form).getAllByRole("radio")).toHaveLength(4);
  });
});
