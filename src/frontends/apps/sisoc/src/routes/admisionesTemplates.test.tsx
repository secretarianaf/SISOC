import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const BASE = "/comedores/configuracion/templates/";
const API = "web/comedores/admisiones/plantillas-informe/";
const nav = { templates: BASE, variables: `${BASE}variables/`, incidencias: `${BASE}incidencias/` };
const page = (over: Record<string, unknown> = {}) => ({
  is_paginated: false, number: 1, count: 1, has_rows: true, previous: null, next: null, range: [1], query_without_page: "", ...over,
});
const choice = (value: string, label: string) => ({ value, label });
const list = (over: Record<string, unknown> = {}) => ({
  estado_filtro: "activa", busqueda: "",
  filtros: { tipo_admision: "", tipo_convenio: "", es_ex_pnud: "", estado_convenio_pnud: "", tipo_renovacion: "", estado_financiamiento: "", informe_complementario_modifica_prestaciones: "" },
  opciones: {
    tipos_admision: [choice("incorporacion", "Incorporación"), choice("renovacion", "Renovación")], tipos_convenio: [choice("1", "Personería Jurídica")],
    opciones_ex_pnud: [choice("si", "Sí")], estados_convenio_pnud: [choice("vigente", "Vigente")], tipos_renovacion: [choice("primera", "Primera renovación")],
    estados_financiamiento: [choice("finalizado", "Financiamiento finalizado")], opciones_informe_complementario: [choice("no", "No")],
  },
  results: [{
    id: 1, codigo: "IT-000001", nombre: "Incorporación Ex PNUD", descripcion: "Modelo sintético", combinacion: "Incorporación · Personería Jurídica · Ex PNUD: Sí · PNUD: Vigente",
    version_vigente: 1, estado: "activa", estado_display: "Activa", url: `${BASE}1/`,
  }],
  page: page(), urls: { ...nav, crear: `${BASE}crear/` }, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 1, codigo: "IT-000001", nombre: "Incorporación Ex PNUD", descripcion: "", estado: "activa", estado_display: "Activa",
  condiciones: [{ term: "Tipo de admisión", value: "Incorporación" }],
  borrador: { id: 2, numero: 2, modificado: "07/11/2026 10:30", urls: { editar: `${BASE}1/versiones/2/editar/`, publicar: `${BASE}1/versiones/2/publicar/`, descartar: `${BASE}1/versiones/2/descartar/` } },
  historial: [{ id: 1, numero: 1, estado: "publicada", estado_display: "Publicada", creado: "07/11/2026 10:30", publicado: null }],
  urls: { ...nav, version_crear: `${BASE}1/versiones/crear/`, inactivar: `${BASE}1/inactivar/` }, messages: [], ...over,
});
const variables = (over: Record<string, unknown> = {}) => ({
  estado_filtro: "activas", busqueda: "a b",
  results: [{ id: 4, categoria: "Informe", nombre: "Expediente", descripcion: "", token: "{{ informe.expediente }}", activo: true, alternar_url: `${BASE}variables/4/alternar/` }],
  urls: nav, messages: [], ...over,
});
const incidencias = (over: Record<string, unknown> = {}) => ({
  estado_filtro: "pendiente", busqueda: "", estados: [choice("pendiente", "Pendiente"), choice("resuelta", "Resuelta")],
  results: [{ id: 2, codigo: "INC-IT-000002", clave_condiciones: "incorporacion|convenio:2", cantidad_casos: 2, ultima_fecha: "07/11/2026 12:30", estado: "pendiente", estado_display: "Pendiente", url: `${BASE}incidencias/2/` }],
  page: page(), urls: nav, messages: [], ...over,
});
const incidencia = (over: Record<string, unknown> = {}) => ({
  id: 2, codigo: "INC-IT-000002", cantidad_casos: 1, primera_fecha: "07/11/2026 10:30", ultima_fecha: "07/11/2026 12:30", incidencia_anterior: null,
  clave_condiciones: "incorporacion|convenio:2", condiciones: [{ clave: "Tipo_Admision", descripcion: "Incorporación" }],
  form: [
    { name: "estado", label: "Estado", required: true, value: "en_analisis", choices: [choice("pendiente", "Pendiente"), choice("en_analisis", "En análisis")] },
    { name: "plantilla", label: "Plantilla", required: false, value: "", choices: [choice("", "---------")] },
    { name: "observaciones", label: "Observaciones", required: false, value: "Nota" },
  ],
  casos: [], urls: { ...nav, gestionar: `${BASE}incidencias/2/` }, messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const main = () => document.querySelector(".gestor-templates") as HTMLElement;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => cleanup());

describe("Template manager route (AD01.01)", () => {
  it("owns exactly the native query pages, with their trailing slashes", () => {
    expect(findRoute(BASE)?.params).toEqual({ page: "templates" });
    expect(findRoute(`${BASE}7/`)?.params).toEqual({ page: "detalle", id: "7" });
    expect(findRoute(`${BASE}variables/`)?.params).toEqual({ page: "variables" });
    expect(findRoute(`${BASE}incidencias/`)?.params).toEqual({ page: "incidencias" });
    expect(findRoute(`${BASE}incidencias/3/`)?.params).toEqual({ page: "incidencia", id: "3" });
    for (const other of ["/comedores/configuracion/templates", `${BASE}crear/`, `${BASE}7`, `${BASE}1/versiones/2/editar/`, `${BASE}1/versiones/2/previsualizar/`, `${BASE}variables/4/alternar/`]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-gestor-templates");
    }
  });

  it("renders the templates list with the query and native GET filters", async () => {
    serve(list({ messages: [{ message: "Plantilla inactivada correctamente.", level: "success" }] }));
    setup(`${BASE}?estado=todas`);
    await screen.findByText("Templates de informes técnicos");
    expect(webGet).toHaveBeenCalledWith(`${API}?estado=todas`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Gestor de templates"));
    const fila = within(main()).getByText("IT-000001").closest("tr")!;
    expect(within(fila).getByText("v1 publicada").classList.contains("gt-status--success")).toBe(true);
    expect(within(fila).getByRole("link", { name: "Gestionar" }).getAttribute("href")).toBe(`${BASE}1/`);
    expect(screen.getByText("Plantilla inactivada correctamente.")).toBeTruthy();
    const form = main().querySelector("form.gt-filters") as HTMLFormElement;
    expect(form.method).toBe("get");
    expect(screen.queryByText(/Se encontraron/)).toBeTruthy();
  });

  it("hides the other admission type's filters like the native script", async () => {
    serve(list());
    setup(BASE);
    await screen.findByText("Templates de informes técnicos");
    const grupo = (name: string) => main().querySelector(`[name="${name}"]`)!.closest("label")!;
    expect(grupo("es_ex_pnud").hidden).toBe(false);
    expect(grupo("tipo_renovacion").hidden).toBe(false);
    fireEvent.change(main().querySelector('[name="tipo_admision"]')!, { target: { value: "renovacion" } });
    expect(grupo("es_ex_pnud").hidden).toBe(true);
    expect(grupo("estado_convenio_pnud").hidden).toBe(true);
    expect(grupo("tipo_renovacion").hidden).toBe(false);
    expect(grupo("informe_complementario_modifica_prestaciones").hidden).toBe(false);
  });

  it("shows the native empty state without rows nor count", async () => {
    serve(list({ results: [], page: page({ count: 0, has_rows: false }) }));
    setup(BASE);
    expect(await screen.findByText("No hay templates para este filtro")).toBeTruthy();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("detail actions are native POST forms; discard asks the native confirmation", async () => {
    serve(detail());
    setup(`${BASE}1/`);
    await screen.findByText("Versión en preparación");
    await waitFor(() => expect(document.title).toBe("SISOC - IT-000001 · Gestor de templates"));
    expect(screen.queryByText("Crear nueva versión")).toBeNull();
    const publicar = screen.getByRole("button", { name: "Publicar versión" }).closest("form")!;
    expect(publicar.getAttribute("action")).toBe(`${BASE}1/versiones/2/publicar/`);
    expect(publicar.method).toBe("post");
    expect((publicar.querySelector('[name="csrfmiddlewaretoken"]') as HTMLInputElement).value).toBe("synthetic-csrf-token");
    expect(screen.getByRole("link", { name: "Continuar editando" }).getAttribute("href")).toBe(`${BASE}1/versiones/2/editar/`);
    const partida = screen.getByRole("button", { name: "Usar como punto de partida" }).closest("form")!;
    expect((partida.querySelector('[name="origen_version_id"]') as HTMLInputElement).value).toBe("1");
    expect(screen.getByText("—")).toBeTruthy();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const descartar = screen.getByRole("button", { name: "Descartar versión" }).closest("form")!;
    const evento = new Event("submit", { bubbles: true, cancelable: true });
    descartar.dispatchEvent(evento);
    expect(confirm).toHaveBeenCalledWith("¿Descartar la versión en preparación? Esta acción no se puede deshacer.");
    expect(evento.defaultPrevented).toBe(true);
    confirm.mockRestore();
  });

  it("an inactive template has no actions and the empty history", async () => {
    serve(detail({ estado: "inactiva", estado_display: "Inactiva", borrador: null, historial: [] }));
    setup(`${BASE}1/`);
    expect(await screen.findByText("No hay versiones publicadas todavía")).toBeTruthy();
    expect(screen.queryByText("Crear nueva versión")).toBeNull();
    expect(screen.queryByText("Inactivar template")).toBeNull();
    expect(screen.getByText("Configuración de condiciones y versiones de este template lógico.")).toBeTruthy();
  });

  it("variables toggle through the native form with next set to the current page", async () => {
    serve(variables());
    setup(`${BASE}variables/?estado=activas&q=a%20b`);
    await screen.findByText("Variables disponibles");
    const boton = screen.getByRole("button", { name: "Eliminar" });
    const form = boton.closest("form")!;
    expect(form.getAttribute("action")).toBe(`${BASE}variables/4/alternar/`);
    expect((form.querySelector('[name="next"]') as HTMLInputElement).value).toBe(`${BASE}variables/?estado=activas&q=a%20b`);
    expect(screen.getByRole("link", { name: "Eliminadas" }).getAttribute("href")).toBe(`${BASE}variables/?estado=inactivas&q=a%20b`);
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("incident list and detail keep the native form posting to the native URL", async () => {
    serve(incidencias());
    setup(`${BASE}incidencias/`);
    await screen.findByText("Configuraciones faltantes");
    expect(screen.getByRole("link", { name: "Todas" }).getAttribute("href")).toBe(`${BASE}incidencias/?estado=todas`);
    cleanup();
    serve(incidencia());
    setup(`${BASE}incidencias/2/`);
    await screen.findByText("Gestionar incidencia");
    await waitFor(() => expect(document.title).toBe("SISOC - INC-IT-000002 · Incidencias"));
    const form = screen.getByRole("button", { name: "Guardar gestión" }).closest("form")!;
    expect(form.getAttribute("action")).toBe(`${BASE}incidencias/2/`);
    expect((form.querySelector("#id_estado") as HTMLSelectElement).value).toBe("en_analisis");
    expect((form.querySelector("#id_observaciones") as HTMLTextAreaElement).value).toBe("Nota");
    expect(screen.getByText("No hay casos registrados")).toBeTruthy();
  });

  it("a 403 from the API is the access screen", async () => {
    serve({ detail: "denied" }, 403);
    setup(BASE);
    expect((await screen.findByRole("link", { name: "volver al inicio" })).getAttribute("href")).toBe("/inicio/");
    expect(screen.queryByText("Templates de informes técnicos")).toBeNull();
  });
});
