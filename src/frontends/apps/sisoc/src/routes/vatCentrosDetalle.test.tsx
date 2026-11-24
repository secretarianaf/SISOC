import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { centroDetalleValid } from "./vatCentrosDetalle";
import { panelValid } from "./vatCentrosDetalleCursos";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const URL_DETALLE = "/vat/centros/5/";
const API_DETALLE = "web/vat/centros-detalle/5/";
const API_PANEL = "web/vat/centros-detalle/5/cursos/";
const permisos = { editar_centro: false, agregar_ubicacion: false, editar_ubicacion: false, eliminar_ubicacion: false, agregar_contacto: false, editar_contacto: false, eliminar_contacto: false };
const acciones = (base: string, id: number) => ({
  form: `/api/web/vat/centros-acciones/${base}/${id}/editar/`, guardar: `/api/web/vat/institucion/${base}/${id}/editar/`, eliminar: `/api/web/vat/institucion/${base}/${id}/eliminar/`,
});
const detalle = (over: Record<string, unknown> = {}) => ({
  id: 5, nombre: "CFP 401", codigo: "060144900", activo: true, mostrar_datos_administrativos: true, tipo_gestion: "Estatal", domicilio: "Calle 7 1234",
  telefono: "221 555 0101", celular: "-", correo: "cfp@example.com", mapa: "https://maps.google.com/maps?q=x&output=embed",
  referente: { nombre: "Lia Paz", telefono: "221 555 0202", dni: "30111222", correo: "lia@example.com", usuarios: ["Ana Gómez", "jperez"] },
  ubicaciones: [{ id: 1, nombre: "Sede principal", caracteristica: "Sede principal", localidad: "Tolosa", domicilio: "7 123", urls: acciones("ubicaciones", 1) }],
  contactos: [{ id: 2, nombre: "Ana Gómez", documento: "30111222", rol: "Dirección", principal: true, telefono: "221 555 0202", urls: acciones("contactos", 2) }],
  permisos, urls: { cursos: `/api/${API_PANEL}` }, modales: null, messages: [], ...over,
});
const curso = (id: number, nombre: string, comisiones: number) => ({
  id, nombre, plan: `Plan ${nombre}`, comisiones, edicion: null, urls: { detalle: `/vat/cursos/${id}/`, comision_nueva: null, eliminar: null },
});
const comision = (id: number, cursoId: number, cursoNombre: string, codigo: string) => ({
  id, curso_id: cursoId, curso_nombre: cursoNombre, codigo, nombre: `Turno ${codigo}`, codigo_o_nombre: codigo, ubicacion: "Sede", fecha_inicio: "01/03/2026",
  fecha_fin: "30/06/2026", cupo: "20", estado: "activa", edicion: null, urls: { detalle: `/vat/cursos/comisiones/${id}/`, eliminar: null },
});
const panel = (over: Record<string, unknown> = {}) => ({
  cursos: [curso(1, "Electricidad", 2), curso(2, "Soldadura", 0)],
  comisiones: [comision(11, 1, "Electricidad", "COM-1"), comision(12, 1, "Electricidad", "COM-2")],
  modales: null, permisos: { gestionar: false, agregar_curso: false, editar_curso: false, editar_comision: false }, ...over,
});

function setup(data: unknown, panelData: unknown = panel()) {
  webGet.mockImplementation((url: string) => {
    if (url === "web/session/") return Promise.resolve({ data: readyContext, status: 200 });
    if (url === API_PANEL) return panelData instanceof Error ? Promise.reject(panelData) : Promise.resolve({ data: panelData, status: 200 });
    return Promise.resolve({ data, status: 200 });
  });
  window.history.replaceState({}, "", URL_DETALLE);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT centro detalle route", () => {
  it("owns its path only", () => {
    expect(findRoute(URL_DETALLE)?.route.name).toBe("vat-centros-detalle");
    for (const other of ["/vat/centros/5", "/vat/centros/x/", "/vat/centros/5/eliminar/", "/vat/centros/5/generar-usuario/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-centros-detalle");
    }
  });

  it("validates the payloads strictly", () => {
    expect(centroDetalleValid(detalle())).toBe(true);
    expect(centroDetalleValid(detalle({ mapa: 3 }))).toBe(false);
    expect(centroDetalleValid(detalle({ urls: { cursos: "https://evil.example/" } }))).toBe(false);
    expect(centroDetalleValid(detalle({ permisos: {} }))).toBe(false);
    expect(panelValid(panel())).toBe(true);
    expect(panelValid(panel({ cursos: [{ ...curso(1, "x", 0), urls: { detalle: "javascript:1", comision_nueva: null, eliminar: null } }] }))).toBe(false);
  });

  it("renders the information, the referente and moves through the side tabs like the native page", async () => {
    setup(detalle());
    expect(await screen.findByRole("heading", { level: 1, name: "CFP 401" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(API_DETALLE, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - CFP 401"));
    expect(screen.getByText("CUE 060144900")).toBeTruthy();
    expect(screen.getByText("Activo").className).toBe("sisoc-status-pill");
    expect(screen.getByText("#060144900")).toBeTruthy();
    expect(screen.getByText("Estatal")).toBeTruthy();
    expect(screen.getByRole("link", { name: "cfp@example.com" }).getAttribute("href")).toBe("mailto:cfp@example.com");
    expect(document.querySelector("iframe[title='Mapa del centro']")?.getAttribute("src")).toContain("maps.google.com");
    expect(document.querySelector(".sisoc-referente-item:nth-child(3) .sisoc-referente-copy div")?.textContent).toContain("Ana Gómez");
    // only the first tab is on the left; the other two wait on the right
    const left = document.querySelector(".sisoc-side-tabs--left")!;
    const right = document.querySelector(".sisoc-side-tabs--right")!;
    expect([...left.querySelectorAll("button")].map((b) => b.hidden)).toEqual([false, true, true]);
    expect([...right.querySelectorAll("button")].map((b) => b.hidden)).toEqual([true, false, false]);
    fireEvent.click(within(right as HTMLElement).getByText("Contactos adicionales"));
    expect([...left.querySelectorAll("button")].map((b) => b.hidden)).toEqual([false, false, false]);
    expect(left.querySelector(".is-active")?.textContent).toBe("Contactos adicionales");
    expect(document.querySelector("[data-sisoc-panel=contactos]")?.className).toContain("is-active");
    expect(document.querySelector("[data-sisoc-panel=general]")?.className).not.toContain("is-active");
    expect(screen.getByText("Dirección")).toBeTruthy();
    expect(screen.getByText("Sí")).toBeTruthy();
    // without the permissions of the native predicates no action button is drawn
    expect(screen.queryByText("Agregar sede")).toBeNull();
    expect(screen.queryByText("Editar")).toBeNull();
  });

  it("hides the administrative data, the map and the users of a centro that has none", async () => {
    setup(detalle({ mostrar_datos_administrativos: false, mapa: null, activo: false, referente: { nombre: "-", telefono: "-", dni: "-", correo: "-", usuarios: [] }, ubicaciones: [], contactos: [] }));
    expect(await screen.findByText("Sin datos suficientes para mostrar el mapa")).toBeTruthy();
    expect(screen.queryByText("Sector de gestión")).toBeNull();
    expect(screen.getByText("Inactivo").className).toContain("is-inactive");
    fireEvent.click(within(document.querySelector(".sisoc-side-tabs--right") as HTMLElement).getByText("Ubicaciones adicionales"));
    expect(screen.getByText("No hay ubicaciones registradas para este centro.")).toBeTruthy();
  });

  it("loads the courses panel, filters, locks a course row and paginates like the page script", async () => {
    const cursos = Array.from({ length: 7 }, (_, i) => curso(i + 1, `Curso ${i + 1}`, i === 0 ? 1 : 0));
    setup(detalle(), panel({ cursos, comisiones: [comision(11, 1, "Curso 1", "COM-1"), comision(12, 2, "Curso 2", "COM-2")] }));
    expect(screen.queryByText("Oferta educativa 2026")).toBeNull();
    expect(await screen.findByText("Oferta educativa 2026")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(API_PANEL);
    const visible = (table: string) => [...document.querySelectorAll(`#${table} tbody tr`)].filter((r) => !r.classList.contains("d-none")).length;
    expect(visible("tablaCursosCentro")).toBe(5);
    expect(document.getElementById("cursosFilterSummary")?.textContent).toBe("Mostrando 1-5 de 7");
    expect(document.querySelectorAll("#cursosPagination button").length).toBe(2);
    fireEvent.click(document.querySelectorAll("#cursosPagination button")[1]);
    expect(document.getElementById("cursosFilterSummary")?.textContent).toBe("Mostrando 6-7 de 7");
    fireEvent.change(document.getElementById("cursosFilterSearch")!, { target: { value: "curso 3" } });
    expect(document.getElementById("cursosFilterSummary")?.textContent).toBe("Mostrando 1-1 de 1");
    fireEvent.change(document.getElementById("cursosFilterSearch")!, { target: { value: "zzz" } });
    expect(document.getElementById("cursosFilterSummary")?.textContent).toBe("Mostrando 0 de 0");
    expect(document.getElementById("cursosTableEmptyState")?.className).not.toContain("d-none");
    fireEvent.change(document.getElementById("cursosFilterSearch")!, { target: { value: "" } });
    fireEvent.change(document.getElementById("cursosFilterEstado")!, { target: { value: "con_comision" } });
    expect(document.getElementById("cursosFilterSummary")?.textContent).toBe("Mostrando 1-1 de 1");
    fireEvent.change(document.getElementById("cursosFilterEstado")!, { target: { value: "" } });
    // a click on a course row locks the commissions of that course; Escape releases it
    const row = screen.getByLabelText("Seleccionar curso Curso 2 para filtrar comisiones");
    fireEvent.click(row);
    expect(row.className).toContain("curso-row-selected");
    expect(row.getAttribute("aria-pressed")).toBe("true");
    expect(document.getElementById("comisionesCursoHint")?.textContent).toBe("Mostrando comisiones de: Curso 2 (1)");
    expect(visible("tablaComisionesCursoCentro")).toBe(1);
    fireEvent.keyDown(row, { key: "Escape" });
    expect(document.getElementById("comisionesCursoHint")?.textContent).toBe("Comisiones vinculadas a cursos del centro.");
    expect(visible("tablaComisionesCursoCentro")).toBe(2);
    expect(screen.getAllByRole("link", { name: /Ver/ })[0].getAttribute("href")).toBe("/vat/cursos/1/");
  });

  it("keeps the rows static when one of the tables is empty, as the page script does", async () => {
    setup(detalle(), panel({ comisiones: [] }));
    expect(await screen.findByText("No hay comisiones de curso para este centro.")).toBeTruthy();
    expect(document.getElementById("cursosFilterSummary")?.textContent).toBe("Mostrando 1-2 de 2");
    expect(document.querySelectorAll("#tablaCursosCentro tbody tr.d-none").length).toBe(0);
    expect(document.querySelector("select#comisionesFilterCurso")).toBeTruthy();
  });

  it("shows the error card and retries the load", async () => {
    let calls = 0;
    webGet.mockImplementation((url: string) => {
      if (url === "web/session/") return Promise.resolve({ data: readyContext, status: 200 });
      if (url === API_PANEL) return ++calls === 1 ? Promise.reject(new Error("down")) : Promise.resolve({ data: panel(), status: 200 });
      return Promise.resolve({ data: detalle(), status: 200 });
    });
    window.history.replaceState({}, "", URL_DETALLE);
    render(<App />);
    expect(await screen.findByText("No se pudo cargar la sección de cursos.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Oferta educativa 2026")).toBeTruthy();
    expect(calls).toBe(2);
  });
});
