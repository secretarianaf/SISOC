import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";
import { fragmentNavigation } from "./pasPanel";
import { navigation } from "./userImport";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const session = {
  ...readyContext,
  navigation: [
    { id: "inicio", label: "Inicio", href: "/inicio/", children: [] },
    {
      id: "pas", label: "PAS", href: null, children: [
        { id: "pas_persona_listar", label: "Buscador PAS", href: "/pas/listar", children: [] },
        { id: "pas_panel_control", label: "Panel de Control", href: "/pas/panel-control", children: [] },
        { id: "pas_informe_listar", label: "Informes", href: "/pas/informes", children: [] },
      ],
    },
    { id: "mi_cuenta", label: "Mi cuenta", href: "/mi-cuenta/", children: [] },
  ],
};
const workflow = (active: string, persona?: number) => [
  ["panel", "01", "Panel de Control", "Titulares y ABM", persona ? `/pas/panel-control/${persona}` : "/pas/panel-control", "disponible"],
  ["formacion", "02", "Formación FCH", "Condicionalidad", persona ? `/pas/formacion?persona=${persona}` : "/pas/formacion", "disponible"],
  ["cruces", "03", "Cruces y Novedades", "Incompatibilidades", "/pas/cruces", "disponible"],
  ["mesa-ayuda", "04", "Mesa de Ayuda", "Reclamos y atención", "/pas/mesa-ayuda", "pendiente"],
  ["liquidacion", "05", "Liquidación", "Nómina de pago", "/pas/liquidacion", "pendiente"],
].map(([key, number, title, subtitle, url, source_status]) => ({ key, number, title, subtitle, url, source_status, active: key === active }));
const area = (key: string, title: string, extra: Record<string, unknown> = {}) => ({
  area: { key, number: "04", title, subtitle: "x" }, workflow: workflow(key), total_padron: 35, ...extra,
});
const persona = (id: number, extra: Record<string, unknown> = {}) => ({
  id, apellidos: `Apellido${id}`, nombres: `Nombre${id}`, puntos_formacion: 0, estado_formacion: "sin-formacion", ...extra,
});
const resumen = {
  puntos: 0, objetivo: 100, excedente: 0, cursos_completados: 0, total_cursos: 0, estado: "sin-formacion", titulo: "Sin formación",
  detalle: "La fuente de formación todavía no se encuentra integrada.", inicio_base: "01/01/2026", inicio_actual: "29/09/2026",
  fin_actual: "27/12/2026", duracion_dias: 90, dia_actual: 43,
};
const formacion = (extra: Record<string, unknown> = {}) => area("formacion", "Formación FCH", {
  query: "", estado_formacion: "todos", persona_solicitada_id: null, personas: [persona(1), persona(2)], has_next: false, next_page: null,
  persona_seleccionada: { id: 1, apellidos: "Apellido1", nombres: "Nombre1", dni: 30000001 }, resumen, formaciones: [], ...extra,
});
const row = (id: number, extra: Record<string, unknown> = {}) => ({
  id, apellidos: `Apellido${id}`, nombres: `Nombre${id}`, dni: 30000000 + id, id_persona: 7000 + id, cuit: `20-${id}-1`,
  provincia: "Buenos Aires", municipio: "La Matanza", estado: { nombre: "Activo", css_class: "pas-status-activo" }, avisos: [101], ...extra,
});
const listado = (extra: Record<string, unknown> = {}) => ({
  page: 1, page_size: 10, has_previous: false, has_next: true, previous: null, next: 2, is_paginated: true, page_range: [1, 2, "…"],
  count: null, query_prefix: "", total_padron: 35, query: "", estado_seleccionado: "", estados: [{ nombre: "Activo" }, { nombre: "Baja" }],
  capabilities: { can_import: true, can_export_tokens: true }, results: [row(1), row(2, { cuit: "", avisos: [] })], ...extra,
});
const titular = {
  id: 2, apellidos: "Apellido2", nombres: "Nombre2", dni: 30000002, id_persona: 7002, cuit: "", genero: "", provincia: "Buenos Aires",
  municipio: "La Matanza", domicilio: "", correo_electronico: "p@example.test", telefono_celular: "", estado: { id: 1, nombre: "Activo", css_class: "pas-status-activo" },
  avisos: [{ codigo: 101, descripcion: "Alta inicial" }], fecha_creacion: "01/11/2026 10:00", fecha_actualizacion: "02/11/2026 11:00",
  ddjj_vigente: { id: 9, download_url: "/pas/ddjj/9/descargar" },
};
const panel = (extra: Record<string, unknown> = {}) => ({
  persona: titular, workflow: workflow("panel", 2), query: "", estado_actual: "todos", estados_panel: [{ id: 1, nombre: "Activo" }, { id: 2, nombre: "Baja" }],
  personas_panel: [
    { id: 1, apellidos: "Apellido1", nombres: "Nombre1", cuit: "20-1-1", dni: 30000001, provincia: "", estado: { nombre: "Baja", css_class: "pas-status-baja" }, mostrar_tag_ddjj: true, mostrar_tag_fch: false },
    { id: 2, apellidos: "Apellido2", nombres: "Nombre2", cuit: "", dni: 30000002, provincia: "Buenos Aires", estado: { nombre: "Activo", css_class: "pas-status-activo" }, mostrar_tag_ddjj: false, mostrar_tag_fch: false },
  ],
  ddjj: {
    declaraciones: [{ id: 9, version: 2, presentada: "05/11/2026 10:00", es_ultima: true }, { id: 8, version: 1, presentada: "04/11/2026 10:00", es_ultima: false }],
    seleccionada: { id: 9, version: 2, presentada: "05/11/2026 10:00", download_url: "/pas/ddjj/9/descargar", respuestas: [{ clave: "domicilio", etiqueta: "Domicilio", respuesta: "Calle 1" }] },
    vigente_download_url: "/pas/ddjj/9/descargar",
  },
  formaciones: [],
  eventos_historial: [
    { tipo: "ddjj", fecha: "05/11/2026 10:00", fecha_iso: "2026-11-05T10:00:00-03:00", id: 9, version: 2 },
    { tipo: "estado", fecha: "01/11/2026 10:00", fecha_iso: "2026-11-01T10:00:00-03:00", estado: "Activo", avisos: [], usuario: null },
  ],
  capabilities: { can_change: true },
  cambio_estado: { estados: [{ id: 1, nombre: "Activo" }, { id: 2, nombre: "Baja" }], avisos_por_estado: { 1: [{ id: 11, text: "101 - Alta inicial" }] } },
  ...extra,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: session, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const appHeader = () => document.querySelector(".app-content-header > .container-fluid:last-child") as HTMLElement;
let assign: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); assign.mockRestore(); vi.unstubAllGlobals(); vi.useRealTimers(); });
// jsdom does not fetch stylesheets: report them applied, as the browser would.
const stylesLoaded = () => document.querySelectorAll('link[rel="stylesheet"]').forEach((l) => l.dispatchEvent(new Event("load")));

describe("PAS back-office routes", () => {
  it("owns exactly the native PAS URLs it migrates", () => {
    expect(findRoute("/pas/listar")?.params).toEqual({ page: "listar" });
    expect(findRoute("/pas/panel-control")?.params).toEqual({ page: "panel" });
    expect(findRoute("/pas/panel-control/7")?.params).toEqual({ page: "panel", id: "7" });
    expect(findRoute("/pas/7")?.params).toEqual({ page: "panel", id: "7" });
    expect(findRoute("/pas/formacion")?.params).toEqual({ page: "area", area: "formacion" });
    expect(findRoute("/pas/mesa-ayuda")?.params).toEqual({ page: "area", area: "mesa-ayuda" });
    expect(findRoute("/pas/liquidacion")?.params).toEqual({ page: "area", area: "liquidacion" });
    for (const other of ["/pas/listar/", "/pas/7/editar", "/pas/cruces", "/pas/informes", "/pas/ddjj/confirmacion", "/pas/panel-control/x", "/pas/crear"]) {
      expect(findRoute(other)?.route.name).not.toBe("pas-backoffice");
    }
  });
});

describe("Buscador PAS", () => {
  it("renders the native rows, buttons, pager and header action", async () => {
    serve(listado({ query_prefix: "busqueda=Ap&q=Ap&" , query: "Ap" }));
    setup("/pas/listar?q=Ap");
    await screen.findByText("Apellido1, Nombre1");
    expect(webGet).toHaveBeenCalledWith("web/pas/personas/?q=Ap", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Buscador PAS"));
    expect(within(appHeader()).getByRole("link", { name: "Informes" }).getAttribute("href")).toBe("/pas/informes");
    // `{% block app-header %}` replaces the template's empty row instead of following it.
    expect([...appHeader().children].map((c) => c.className)).toEqual(["pas-top-actions"]);
    expect(screen.getByRole("link", { name: "Importar titulares" }).getAttribute("title")).toBe("Importar titulares desde CSV");
    expect(screen.getByRole("link", { name: "Exportar tokens" }).getAttribute("href")).toBe("/pas/ddjj/tokens/exportar");
    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getAllByRole("cell").map((c) => c.textContent)).toEqual([
      "Apellido1, Nombre1DNI 30000001 · IdPersona 7001", "20-1-1", "Buenos Aires La Matanza", "Activo", "101", "",
    ]);
    expect(within(rows[2]).getAllByRole("cell")[1].textContent).toBe("-");
    expect(within(rows[2]).getAllByRole("cell")[4].textContent).toBe("Sin avisos");
    expect(within(rows[1]).getByTitle("Abrir panel de control de Nombre1 Apellido1").getAttribute("href")).toBe("/pas/panel-control/1");
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?busqueda=Ap&q=Ap&page=2");
    expect(screen.getByRole("link", { name: "2" }).getAttribute("href")).toBe("?busqueda=Ap&q=Ap&page=2");
    expect(screen.getByText("Padrón actual: 35 titulares")).toBeTruthy();
    expect(screen.getByTitle("Limpiar búsqueda").getAttribute("href")).toBe("/pas/listar");
    expect((screen.getByPlaceholderText("Buscar por nombre, CUIT, DNI o IdPersona") as HTMLInputElement).value).toBe("Ap");
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
    expect(screen.getByRole("link", { name: "Buscador PAS", current: "page" })).toBeTruthy();
  });

  it("hides buttons without each permission and shows the empty row", async () => {
    serve(listado({ capabilities: { can_import: false, can_export_tokens: false }, results: [], total_padron: 1, is_paginated: false }));
    setup("/pas/listar");
    expect(await screen.findByText("Sin titulares para los criterios seleccionados")).toBeTruthy();
    expect(screen.queryByText("Importar titulares")).toBeNull();
    expect(screen.queryByText("Exportar tokens")).toBeNull();
    expect(screen.queryByTitle("Limpiar búsqueda")).toBeNull();
    expect(screen.queryByRole("link", { name: "Continuar" })).toBeNull();
    expect(screen.getByText("Padrón actual: 1 titular")).toBeTruthy();
  });

  it("shows the access screen on a 403 and a load error on an unexpected shape", async () => {
    serve({ detail: "x" }, 403);
    setup("/pas/listar");
    await waitFor(() => expect(document.title).toBe("SISOC - Error 403"));
    cleanup();
    serve({ results: "x" });
    setup("/pas/listar");
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});

describe("Panel de Control PAS", () => {
  it("renders the titular, side list, actions and data tab", async () => {
    serve(panel({ query: "Ap ñ/", estado_actual: "1" }));
    setup("/pas/panel-control/2?q=Ap");
    await screen.findByText("Apellido2, Nombre2 · DNI 30000002");
    expect(webGet).toHaveBeenCalledWith("web/pas/panel/2/?q=Ap", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Panel de Control · PAS"));
    const header = within(appHeader());
    expect(header.getByRole("link", { name: "Buscador PAS" }).getAttribute("href")).toBe("/pas/listar");
    expect(header.getByRole("button", { name: "Cambiar estado" })).toBeTruthy();
    expect(header.getByRole("link", { name: "Editar datos personales" }).getAttribute("href")).toBe("/pas/2/editar");
    const people = screen.getByRole("complementary", { name: "Titulares PAS" });
    const links = within(people).getAllByRole("link").filter((a) => a.classList.contains("pas-person-mini"));
    expect(links.map((a) => a.getAttribute("href"))).toEqual([
      "/pas/panel-control/1?q=Ap%20%C3%B1/&estado_actual=1", "/pas/panel-control/2?q=Ap%20%C3%B1/&estado_actual=1",
    ]);
    expect(links[1].className).toContain("is-active");
    expect(within(links[0]).getByTitle("Declaración jurada pendiente").textContent).toBe("DDJJ");
    expect(within(links[0]).getByText("Sin provincia")).toBeTruthy();
    expect(within(links[1]).getByText("DNI 30000002")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Activo" }).className).toBe("is-active");
    expect(screen.getByRole("button", { name: "Todos" }).className).toBe("");
    expect(screen.getByText("CUIT no informado")).toBeTruthy();
    expect(screen.getByText("101 · Alta inicial")).toBeTruthy();
    const datos = screen.getByRole("tabpanel", { name: "Datos personales" });
    expect(within(datos).getByText("Domicilio").nextElementSibling?.textContent).toBe("Sin dato");
    expect(within(datos).getByRole("link", { name: "Descargar última" }).getAttribute("href")).toBe("/pas/ddjj/9/descargar");
    expect(within(datos).getByText("Alta del registro").nextElementSibling?.textContent).toBe("01/11/2026 10:00");
    const workflowLinks = within(screen.getByRole("navigation", { name: "Circuito PAS" })).getAllByRole("link");
    expect(workflowLinks.map((a) => a.getAttribute("href"))[1]).toBe("/pas/formacion?persona=2");
    expect(workflowLinks[0].className).toBe("pas-workflow-card is-active");
    expect(workflowLinks[3].querySelector('[title="Integración pendiente"]')).toBeTruthy();
  });

  it("switches tabs like Bootstrap 5.3: click, arrows and roving tabindex", async () => {
    serve(panel());
    setup("/pas/panel-control/2");
    const datos = await screen.findByRole("tab", { name: "Datos personales" });
    const ddjj = screen.getByRole("tab", { name: "Declaración Jurada" });
    expect(datos.getAttribute("tabindex")).toBeNull();
    expect(ddjj.getAttribute("tabindex")).toBe("-1");
    fireEvent.click(screen.getByRole("tab", { name: "Historial de estados" }));
    const historial = document.getElementById("historial-panel")!;
    expect(historial.className).toBe("tab-pane fade show active");
    expect(within(historial).getByText("Declaración Jurada · Versión 2")).toBeTruthy();
    expect(within(historial).getByRole("link", { name: "Ver presentación" }).getAttribute("href")).toBe("?ddjj=9#ddjj-panel");
    expect(within(historial).getByText("Sistema")).toBeTruthy();
    expect(within(historial).getByText("Sin avisos")).toBeTruthy();
    fireEvent.keyDown(screen.getByRole("tab", { name: "Historial de estados" }), { key: "ArrowRight" });
    expect(screen.getByRole("tab", { name: "Datos personales" }).getAttribute("aria-selected")).toBe("true");
    expect(document.activeElement).toBe(screen.getByRole("tab", { name: "Datos personales" }));
    fireEvent.keyDown(document.activeElement!, { key: "ArrowLeft" });
    expect(screen.getByRole("tab", { name: "Historial de estados" }).getAttribute("aria-selected")).toBe("true");
    fireEvent.click(screen.getByRole("tab", { name: "Capacitación FCH" }));
    expect(screen.getByText("Sin formación registrada en SISOC")).toBeTruthy();
  });

  it("opens the DDJJ tab from the hash and navigates when the version changes", async () => {
    serve(panel());
    setup("/pas/panel-control/2?ddjj=9#ddjj-panel");
    const replace = vi.spyOn(fragmentNavigation, "replace").mockImplementation(() => undefined);
    const tab = await screen.findByRole("tab", { name: "Declaración Jurada" });
    expect(tab.getAttribute("aria-selected")).toBe("true");
    stylesLoaded();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("#ddjj-panel"));
    const select = screen.getByLabelText("Presentación consultada") as HTMLSelectElement;
    expect([...select.options].map((o) => [o.value, o.textContent])).toEqual([
      ["?ddjj=9#ddjj-panel", "Versión 2 · 05/11/2026 10:00 · Última"],
      ["?ddjj=8#ddjj-panel", "Versión 1 · 04/11/2026 10:00"],
    ]);
    expect(screen.getByRole("link", { name: "Descargar PDF" }).getAttribute("href")).toBe("/pas/ddjj/9/descargar");
    expect(within(document.getElementById("ddjj-panel")!).getByText("Domicilio").nextElementSibling?.textContent).toBe("Calle 1");
    fireEvent.change(select, { target: { value: "?ddjj=8#ddjj-panel" } });
    expect(assign).toHaveBeenCalledWith("?ddjj=8#ddjj-panel");
    expect(document.body.innerHTML).not.toContain("media/pas");
  });

  it("renders the empty padron, the empty DDJJ tab and hides actions without change", async () => {
    serve(panel({ ddjj: { declaraciones: [], seleccionada: null, vigente_download_url: null }, capabilities: { can_change: false }, persona: { ...titular, ddjj_vigente: null } }));
    setup("/pas/2");
    await screen.findByText("Apellido2, Nombre2 · DNI 30000002");
    expect(webGet).toHaveBeenCalledWith("web/pas/panel/2/", expect.anything());
    expect(screen.queryByRole("button", { name: "Cambiar estado" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Editar datos personales" })).toBeNull();
    expect(screen.getByText("Sin Declaraciones Juradas presentadas")).toBeTruthy();
    const datos = screen.getByRole("tabpanel", { name: "Datos personales" });
    expect(within(datos).getByText("Declaración Jurada").nextElementSibling?.textContent).toBe("No");
    cleanup();
    serve(panel({ persona: null, personas_panel: [] }));
    setup("/pas/panel-control");
    expect(await screen.findByText("No hay titulares PAS registrados")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/pas/panel/", expect.anything());
    expect(screen.getByText("Consulta integral de titulares PAS")).toBeTruthy();
    expect(screen.queryByRole("tab")).toBeNull();
  });
});

describe("PAS areas", () => {
  it("renders Formación with filters, links and the summary", async () => {
    serve(formacion({ query: " a/b ", estado_formacion: "sin-formacion" }));
    setup("/pas/formacion?q=%20a/b%20&estado_formacion=sin-formacion");
    await screen.findByText("Semáforo de validación de formación");
    expect(webGet).toHaveBeenCalledWith("web/pas/areas/formacion/?q=%20a/b%20&estado_formacion=sin-formacion", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Formación FCH · PAS"));
    expect(within(appHeader()).getByRole("link", { name: "Buscador PAS" })).toBeTruthy();
    expect(screen.getByText("Fuente de formación pendiente")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sin formación" }).className).toBe("is-active");
    expect((screen.getByLabelText("Buscar titular") as HTMLInputElement).value).toBe(" a/b ");
    const links = document.querySelectorAll("#pas-formacion-personas-items a");
    expect([...links].map((a) => [a.getAttribute("href"), a.className])).toEqual([
      ["?persona=1&q=%20a/b%20&estado_formacion=sin-formacion", "is-active pas-formation-person-link"],
      ["?persona=2&q=%20a/b%20&estado_formacion=sin-formacion", " pas-formation-person-link"],
    ]);
    expect(links[0].textContent).toBe("Apellido1, Nombre10 pts");
    expect(screen.getByText("Apellido1, Nombre1 · DNI 30000001")).toBeTruthy();
    expect(screen.getByText(/Períodos de 90 días corridos desde/).textContent).toBe("Períodos de 90 días corridos desde 01/01/2026");
    expect(screen.getByText("/ 90 · inició 29/09/2026")).toBeTruthy();
    expect(screen.getByText("La fuente de formación todavía no está integrada")).toBeTruthy();
    expect(document.getElementById("pas-formacion-scroll-status")?.textContent).toBe("");
  });

  it("shows the empty selection when the filter leaves no titular", async () => {
    serve(formacion({ personas: [], persona_seleccionada: null, resumen: null, estado_formacion: "cumplido" }));
    setup("/pas/formacion?estado_formacion=cumplido");
    expect(await screen.findByText("No hay un titular seleccionado")).toBeTruthy();
    expect(screen.getByText("Ajustá los filtros para consultar su formación.")).toBeTruthy();
    expect(screen.getByText("Sin titulares para los filtros elegidos")).toBeTruthy();
  });

  it("loads the next pages on the sentinel like pas_formacion.js", async () => {
    let fire: () => void = () => undefined;
    const disconnect = vi.fn();
    let observed = false;
    vi.stubGlobal("IntersectionObserver", class {
      constructor(callback: (entries: { isIntersecting: boolean }[]) => void) { observed = true; fire = () => callback([{ isIntersecting: true }]); }
      observe() { return undefined; }
      disconnect() { disconnect(); }
    });
    const pages = [
      { personas: [persona(3)], has_next: true, next_page: 3, query: "x", estado_formacion: "todos", persona_seleccionada_id: 7 },
    ];
    webGet.mockImplementation((url: string) => {
      if (url === "web/session/") return Promise.resolve({ data: session, status: 200 });
      if (url.startsWith("web/pas/formacion/personas/")) {
        const page = pages.shift();
        return page ? Promise.resolve({ data: page, status: 200 }) : Promise.reject(new Error("down"));
      }
      return Promise.resolve({ data: formacion({ query: " x", persona_solicitada_id: 7, has_next: true, next_page: 2 }), status: 200 });
    });
    setup("/pas/formacion?persona=7&q=%20x");
    await screen.findByText("Desplazate para cargar más titulares");
    fire();
    expect(webGet).toHaveBeenCalledTimes(2);
    stylesLoaded();
    await waitFor(() => expect(observed).toBe(true));
    fire();
    await screen.findByText("Apellido3, Nombre3");
    expect(webGet).toHaveBeenCalledWith("web/pas/formacion/personas/?page=2&q=+x&estado_formacion=todos&persona=7");
    expect(document.querySelector('#pas-formacion-personas-items a[href^="?persona=3"]')?.getAttribute("href")).toBe("?persona=3&q=x&estado_formacion=todos");
    expect(screen.getByText("Desplazate para cargar más titulares")).toBeTruthy();
    fire();
    expect(await screen.findByText("No se pudieron cargar más titulares.")).toBeTruthy();
  });

  it("asks the GET again at 00:00:05 of the next day", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "Date"] });
    vi.setSystemTime(new Date(2026, 10, 10, 23, 59, 0));
    serve(formacion());
    setup("/pas/formacion");
    await vi.waitFor(() => expect(webGet).toHaveBeenCalledTimes(2));
    vi.advanceTimersByTime(66_000);
    await vi.waitFor(() => expect(webGet).toHaveBeenCalledTimes(4));
    vi.useRealTimers();
  });

  it("renders Mesa de Ayuda and Liquidación", async () => {
    serve(area("mesa-ayuda", "Mesa de Ayuda"));
    setup("/pas/mesa-ayuda");
    expect(await screen.findByText("Sin tickets vinculados")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/pas/areas/mesa-ayuda/", expect.anything());
    expect(screen.getByText("Integración pendiente")).toBeTruthy();
    expect(screen.getByText("La identificación, conversación, adjuntos y estados dependerán de la API de Mesa de Ayuda.")).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Mesa de Ayuda · PAS"));
    cleanup();
    serve(area("liquidacion", "Liquidación"));
    setup("/pas/liquidacion");
    expect(await screen.findByText("Liquidación bloqueada")).toBeTruthy();
    expect(screen.getByText("Padrón PAS").nextElementSibling?.textContent).toBe("35");
    expect(screen.getByText("No iniciada")).toBeTruthy();
    expect(screen.getByText("Faltan reglas confirmadas de FCH, DDJJ, incompatibilidades y el formato definitivo de nómina.")).toBeTruthy();
  });
});
