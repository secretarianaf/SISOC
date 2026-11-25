import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { comisionDetalleValid } from "./vatComisionDetalle";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const CURSO = "/vat/cursos/comisiones/8/";
const API_CURSO = "web/vat/comisiones-detalle/cursos/8/";
const PERMISOS = {
  gestionar_comision: false, editar_comision: false, eliminar_comision: false, agregar_inscripcion: false, cambiar_inscripcion: false, eliminar_inscripcion: false,
  gestionar_asistencia: false, agregar_comision_horario: false, editar_comision_horario: false, eliminar_comision_horario: false, gestionar_lote_inscriptos: false,
  gestionar_resultados: false,
};
const inscripto = (id: number, over: Record<string, unknown> = {}) => ({
  id, apellido: `Apellido${id}`, nombre: `Nombre${id}`, documento: `DNI 3011${id}`, estado: "inscripta", estado_label: "Inscripta", detail_url: `/vat/inscripciones/${id}/`,
  busqueda: `apellido${id} nombre${id}`, tipo_alumno: "Sin Plan", es_alumno_vat: false, email: "—", telefono: "—", asistencia: null, delete_url: `/vat/inscripciones/${id}/eliminar/`, ...over,
});
const sesion = (id: number, over: Record<string, unknown> = {}) => ({
  id, numero: id, dia: "Lunes", fecha: "9 de marzo", desde: "09:00", hasta: "12:30", estado: "programada", presentes: "", ausentes: "", asistencia_url: `/vat/cursos/comisiones/sesiones/${id}/asistencia/`, ...over,
});
const horario = (id: number) => ({
  id, dia: "Lunes", dia_semana_id: 1, desde: "09:00", hasta: "12:30", duracion: "3 h 30 min", aula_espacio: "Aula 2", vigente: true,
  update_url: `/vat/cursos/comisiones/horarios/${id}/editar/`, delete_url: `/vat/cursos/comisiones/horarios/${id}/eliminar/`,
});
const data = (over: Record<string, unknown> = {}) => ({
  tipo: "curso", id: 8, codigo: "COM-8", nombre: "Comisión Ocho", titulo_tipo: "Comisión de Curso", subtitulo: "Electricidad básica", estado_label: "Planificada",
  acepta_lista_espera: false, ubicacion: "CFP 401 - Tolosa", fecha_inicio: "01/03/2026", fecha_fin: "—", cupo: "5", cupo_lista_espera: "—", cupo_ocupado: "2",
  clases_dictadas: "0", clases_pendientes: "1", metricas: [{ valor: "0%", label: "Asistencia general" }, { valor: "1", label: "Clases Totales" }],
  horarios: [horario(1)], sesiones: [sesion(1)], inscripciones: [inscripto(1), inscripto(2, { es_alumno_vat: true, tipo_alumno: "VAT", asistencia: "50" })], lista_espera: [],
  permisos: PERMISOS, urls: { eliminar: "/vat/cursos/comisiones/8/eliminar/", exportar_preinscriptos: null, exportar_inscriptos: null, horario_nuevo: "/vat/cursos/comisiones/horarios/nuevo/?comision_curso=8" },
  resultados: null, formularios: { rapida: null, profesor: null }, messages: [], ...over,
});

function serve(payload: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: payload, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const panel = (name: string) => document.querySelector(`[data-sisoc-panel="${name}"]`) as HTMLElement;
const active = () => Array.from(document.querySelectorAll(".sisoc-info-panel.is-active")).map((e) => e.getAttribute("data-sisoc-panel"));
const hiddenTabs = (side: string) => Array.from(document.querySelectorAll(`.sisoc-side-tabs--${side} .sisoc-side-tab`)).filter((e) => e.hasAttribute("hidden")).map((e) => e.getAttribute("data-sisoc-tab-target"));

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  window.history.replaceState({}, "", "/");
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT comisión detalle route", () => {
  it("owns the offer and the course detail paths only", () => {
    for (const path of [CURSO, "/vat/comisiones/8/"]) expect(findRoute(path)?.route.name).toBe("vat-comision-detalle");
    for (const other of ["/vat/cursos/comisiones/8", "/vat/comisiones/x/", "/vat/comisiones/horarios/", "/vat/comisiones/sesiones/8/asistencia/", "/vat/cursos/comisiones/8/eliminar/", "/vat/cursos/comisiones/nueva/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-comision-detalle");
    }
  });

  it("renders the native layout: title, tabs, global metrics and the general panel", async () => {
    serve(data());
    setup(CURSO);
    expect(await screen.findByRole("heading", { level: 1, name: "Comisión Ocho" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(API_CURSO, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - COM-8 — Comisión de Curso"));
    expect(screen.getByText("Planificada").className).toBe("sisoc-status-pill");
    expect(screen.getByText("COM-8").className).toBe("sisoc-cue-text");
    expect(screen.getByText("Electricidad básica")).toBeTruthy();
    const rail = within(screen.getByRole("tablist", { name: "Secciones de la comisión" })).getAllByRole("button").map((b) => b.textContent);
    expect(rail).toEqual(["Información", "Inscriptos", "Clases", "Horarios"]);
    expect(Array.from(document.querySelectorAll("#sisocMetricGridGlobal .sisoc-metric-card")).map((e) => e.textContent)).toEqual(["0%Asistencia general", "1Clases Totales"]);
    expect(active()).toEqual(["general"]);
    expect(within(panel("general")).getByText("CFP 401 - Tolosa")).toBeTruthy();
    expect(within(panel("general")).getByText("3 h 30 min")).toBeTruthy();
    expect(hiddenTabs("left")).toEqual(["inscriptos", "sesiones", "horarios"]);
    expect(hiddenTabs("right")).toEqual(["general"]);
    const side = Array.from(document.querySelectorAll(".sisoc-side-tabs--right .sisoc-side-tab")).map((e) => e.textContent);
    expect(side).toEqual(["Información", "Inscriptos (2)", "Sesiones (1)", "Horarios (1)"]);
    expect(document.querySelector(".sisoc-page-top .sisoc-header-actions")?.children).toHaveLength(0);
  });

  it("switches tabs by click and by the URL hash, hiding the global metrics where the page does", async () => {
    serve(data());
    window.history.replaceState({}, "", `${CURSO}#sesiones`);
    render(<App />);
    await screen.findByRole("heading", { level: 1, name: "Comisión Ocho" });
    expect(active()).toEqual(["sesiones"]);
    expect((document.getElementById("sisocMetricGridGlobal") as HTMLElement).style.display).toBe("none");
    fireEvent.click(screen.getByRole("button", { name: "Horarios" }));
    expect(active()).toEqual(["horarios"]);
    expect((document.getElementById("sisocMetricGridGlobal") as HTMLElement).style.display).toBe("");
    expect(document.querySelectorAll(".sisoc-tab-chip.is-active")).toHaveLength(1);
    expect(document.querySelectorAll('.sisoc-side-tab.is-active[data-sisoc-tab-target="horarios"]')).toHaveLength(2);
    window.location.hash = "#nada";
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    await waitFor(() => expect(active()).toEqual(["general"]));
  });

  it("filters the inscriptos by name and paginates ten at a time, like the native script", async () => {
    const inscripciones = Array.from({ length: 12 }, (_, i) => inscripto(i + 1));
    serve(data({ inscripciones }));
    setup(`${CURSO}#inscriptos`);
    await screen.findByRole("heading", { level: 1, name: "Comisión Ocho" });
    const rows = () => Array.from(document.querySelectorAll("#inscriptosTablaBody .ci-tbl-row"));
    const visible = () => rows().filter((r) => !r.classList.contains("d-none")).length;
    expect(visible()).toBe(10);
    expect(document.getElementById("inscriptosConteo")?.textContent).toBe("Mostrando 1-10 de 12");
    expect(document.getElementById("inscriptosPager")?.textContent).toBe("1 de 2");
    expect((document.getElementById("inscriptosPrev") as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(document.getElementById("inscriptosNext") as HTMLElement);
    expect(visible()).toBe(2);
    expect(document.getElementById("inscriptosConteo")?.textContent).toBe("Mostrando 11-12 de 12");
    expect((document.getElementById("inscriptosNext") as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(document.getElementById("inscriptosBuscador") as HTMLElement, { target: { value: " APELLIDO12 " } });
    expect(visible()).toBe(1);
    expect(document.getElementById("inscriptosPager")?.textContent).toBe("1 de 1");
    expect(document.querySelector("[data-no-results-row]")?.classList.contains("d-none")).toBe(true);
    fireEvent.change(document.getElementById("inscriptosBuscador") as HTMLElement, { target: { value: "zzz" } });
    expect(visible()).toBe(0);
    expect(document.getElementById("inscriptosConteo")?.textContent).toBe("Mostrando 0-0 de 0");
    expect(document.querySelector("[data-no-results-row]")?.classList.contains("d-none")).toBe(false);
  });

  it("prints the inscriptos with the native pills, links and dashes", async () => {
    serve(data());
    setup(`${CURSO}#inscriptos`);
    await screen.findByRole("heading", { level: 1, name: "Comisión Ocho" });
    const table = panel("inscriptos");
    expect(within(table).getByRole("link", { name: "Apellido1" }).getAttribute("href")).toBe("/vat/inscripciones/1/");
    expect(within(table).getByText("VAT").className).toBe("ci-pill ci-pill-teal");
    expect(within(table).getAllByText("Sin Plan")[0].className).toBe("ci-pill ci-pill-gray");
    expect(within(table).getAllByText("Inscripta")[0].className).toBe("ci-pill ci-pill-green");
    expect(within(table).getByText("50%")).toBeTruthy();
    expect(within(table).getAllByText("—").length).toBeGreaterThan(0);
    expect(Array.from(table.querySelectorAll("thead th")).map((e) => e.textContent)).toEqual(["Apellido", "Nombre", "Documento", "Tipo de alumno", "Estado", "Email", "Teléfono", "Asistencia"]);
  });

  it("shows the empty rows the native template has", async () => {
    serve(data({ inscripciones: [], sesiones: [], horarios: [] }));
    setup(CURSO);
    await screen.findByRole("heading", { level: 1, name: "Comisión Ocho" });
    expect(screen.getByText("Sin inscriptos aún. Inscribí ciudadanos a esta comisión para verlos aquí.")).toBeTruthy();
    expect(screen.getByText("Sin clases generadas. Agregá un horario para generar las clases automáticamente.")).toBeTruthy();
    expect(screen.getByText("Sin horarios cargados. Agregá un horario para esta comisión.")).toBeTruthy();
    expect(within(panel("general")).getByText("Sin horarios cargados")).toBeTruthy();
    expect(document.getElementById("inscriptosConteo")?.textContent).toBe("Mostrando 0-0 de 0");
    expect(document.getElementById("sesionesPager")?.textContent).toBe("1 de 1");
  });

  it("shows the wait list tab when the commission accepts it or has people waiting", async () => {
    serve(data({ acepta_lista_espera: true, cupo_lista_espera: "3", lista_espera: [{ ...inscripto(9), fecha: "02/03/2026", estado: "en_espera", estado_label: "En espera" }] }));
    setup(`${CURSO}#espera`);
    await screen.findByRole("heading", { level: 1, name: "Comisión Ocho" });
    expect(active()).toEqual(["espera"]);
    expect(Array.from(panel("espera").querySelectorAll(".sisoc-metric-card")).map((e) => e.textContent)).toEqual(["3Cupo de espera", "1En espera"]);
    expect(within(panel("espera")).getByText("02/03/2026")).toBeTruthy();
    expect(panel("espera").querySelector("tbody .ci-pill")?.className).toBe("ci-pill ci-pill-yellow");
    expect(within(screen.getByRole("tablist", { name: "Secciones de la comisión" })).getByRole("button", { name: "Lista de espera" })).toBeTruthy();
  });

  it("lists the classes, with the counters only for the completed ones and the attendance links for managers", async () => {
    serve(data({ sesiones: [sesion(1, { estado: "realizada", presentes: "2", ausentes: "1" }), sesion(2), sesion(3, { estado: "cancelada" })], permisos: { ...PERMISOS, gestionar_asistencia: true } }));
    setup(`${CURSO}#sesiones`);
    await screen.findByRole("heading", { level: 1, name: "Comisión Ocho" });
    const rows = Array.from(panel("sesiones").querySelectorAll("tbody tr")).map((r) => Array.from(r.querySelectorAll("td")).map((c) => c.textContent));
    expect(rows).toEqual([
      ["Clase 1", "Lunes", "9 de marzo", "09:00 hs", "12:30 hs", "Completada", "2", "1", "Ver"],
      ["Clase 2", "Lunes", "9 de marzo", "09:00 hs", "12:30 hs", "Pendiente", "—", "—", "Asistencia"],
      ["Clase 3", "Lunes", "9 de marzo", "09:00 hs", "12:30 hs", "Cancelada", "—", "—", "Asistencia"],
    ]);
    expect(within(panel("sesiones")).getByRole("link", { name: "Ver" }).getAttribute("href")).toBe("/vat/cursos/comisiones/sesiones/1/asistencia/");
    expect(within(panel("sesiones")).getByRole("link", { name: "Ver" }).className).toBe("sisoc-btn sisoc-btn--edit");
  });

  it("keeps the offer variant blanks and has no commission metrics", async () => {
    serve(data({ tipo: "oferta", metricas: [], clases_dictadas: "", clases_pendientes: "", titulo_tipo: "Comisión", sesiones: [sesion(1, { estado: "realizada" })] }));
    setup("/vat/comisiones/8/#sesiones");
    await screen.findByRole("heading", { level: 1, name: "Comisión Ocho" });
    expect(webGet).toHaveBeenCalledWith("web/vat/comisiones-detalle/8/", expect.anything());
    expect(document.querySelectorAll("#sisocMetricGridGlobal .sisoc-metric-card")).toHaveLength(0);
    expect(Array.from(panel("sesiones").querySelectorAll(".sisoc-metric-card")).map((e) => e.textContent)).toEqual(["1Clases totales", "Clases completadas", "Clases pendientes"]);
  });

  it("links the actions that have no API in this screen to their native pages", async () => {
    const permisos = { ...PERMISOS, eliminar_comision: true, eliminar_inscripcion: true, cambiar_inscripcion: true, agregar_comision_horario: true, editar_comision_horario: true, eliminar_comision_horario: true };
    serve(data({ permisos, urls: { eliminar: "/vat/cursos/comisiones/8/eliminar/", exportar_preinscriptos: "/vat/cursos/comisiones/8/descargar-nomina-preinscriptos/", exportar_inscriptos: "/vat/cursos/comisiones/8/descargar-nomina-inscriptos/", horario_nuevo: "/vat/cursos/comisiones/horarios/nuevo/?comision_curso=8" } }));
    setup(CURSO);
    await screen.findByRole("heading", { level: 1, name: "Comisión Ocho" });
    const link = (name: string | RegExp) => screen.getByRole("link", { name, hidden: true });
    expect(link("Eliminar").getAttribute("href")).toBe("/vat/cursos/comisiones/8/eliminar/");
    expect(link("Descargar preinscriptos").getAttribute("href")).toBe("/vat/cursos/comisiones/8/descargar-nomina-preinscriptos/");
    expect(link("Descargar inscriptos").getAttribute("href")).toBe("/vat/cursos/comisiones/8/descargar-nomina-inscriptos/");
    expect(screen.getAllByRole("link", { name: /Borrar/, hidden: true }).map((a) => a.getAttribute("href"))).toEqual(["/vat/inscripciones/1/eliminar/", "/vat/inscripciones/2/eliminar/"]);
    expect(link("Eliminar horario Lunes 09:00 a 12:30").getAttribute("href")).toBe("/vat/cursos/comisiones/horarios/1/eliminar/");
    expect(link("Agregar").getAttribute("href")).toBe("/vat/cursos/comisiones/horarios/nuevo/?comision_curso=8");
    expect(link("Editar horario Lunes 09:00 a 12:30").getAttribute("href")).toBe("/vat/cursos/comisiones/horarios/1/editar/");
    expect(document.querySelector(".sisoc-centro-page form")).toBeNull();
  });

  it("shows queued messages as toasts", async () => {
    serve(data({ messages: [{ message: "Comisión creada exitosamente.", level: "success" }] }));
    setup(CURSO);
    expect(await screen.findByText("Comisión creada exitosamente.")).toBeTruthy();
  });

  it("validates the payload shape", () => {
    expect(comisionDetalleValid(data())).toBe(true);
    expect(comisionDetalleValid(data({ tipo: "otro" }))).toBe(false);
    expect(comisionDetalleValid(data({ inscripciones: [{ id: 1 }] }))).toBe(false);
    expect(comisionDetalleValid(data({ permisos: { gestionar_comision: true } }))).toBe(false);
    expect(comisionDetalleValid(data({ urls: { eliminar: "https://evil.test/", exportar_preinscriptos: null, exportar_inscriptos: null, horario_nuevo: "/x/" } }))).toBe(false);
    expect(comisionDetalleValid({})).toBe(false);
  });
});
