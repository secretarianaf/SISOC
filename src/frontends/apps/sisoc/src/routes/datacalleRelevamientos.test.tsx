import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { navigation } from "./cdfFrame";
import { lookups } from "./datacalleRelevamientoForm";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const ID = "0b6d8f3e-1c2a-4f5b-9d7e-123456789abc";
const API = "web/dispositivos/datacalle/relevamientos/";
const fila = (n: number, over: Record<string, unknown> = {}) => ({
  id: `${ID.slice(0, -1)}${n}`, denominacion: `Operativo ${n}`, fase_display: "Espacio público", lugar: "Plaza", modalidad_papel: false,
  provincia: "Córdoba", zonas: "", fecha_inicio: "15/09/26", fecha_fin: "17/09/26", dias: 3, equipo: 2, estado: "planificado",
  estado_display: "Planificado", urls: { detail: `/datacalle/relevamientos/${ID}/`, edit: `/datacalle/relevamientos/${ID}/editar/` }, ...over,
});
const resumen = { total: 4, por_estado: [{ valor: "planificado", etiqueta: "Planificado", total: 3 }, { valor: "en_curso", etiqueta: "En curso", total: 0 }, { valor: "finalizado", etiqueta: "Finalizado", total: 1 }] };
const lista = (over: Record<string, unknown> = {}) => ({
  count: 16, page: 1, page_size: 15, pages: 2, filters: { busqueda: "plaza", estado: "finalizado", fase: "" },
  results: [fila(1, { modalidad_papel: true, zonas: "Centro, Alberdi" }), fila(2, { lugar: "", dias: 1, estado: "finalizado", estado_display: "Finalizado" })],
  is_paginated: true, has_next: true, has_previous: false, page_range: [1, 2], query_prefix: "estado=finalizado&", resumen,
  estados: [{ value: "planificado", label: "Planificado" }, { value: "en_curso", label: "En curso" }, { value: "finalizado", label: "Finalizado" }],
  fases: [{ value: "espacio_publico", label: "Espacio público" }, { value: "dispositivo_alojamiento", label: "Dispositivo de alojamiento" }],
  add_url: "/datacalle/relevamientos/crear/", can_change: true, messages: [], ...over,
});
const ficha = (over: Record<string, unknown> = {}) => ({
  id: ID, denominacion: "Operativo invierno", estado: "planificado", estado_display: "Planificado", provincia: "Córdoba", municipio: "Capital",
  zonas: "Centro", dias: 3, fase: "espacio_publico", fase_display: "Espacio público", lugar: "Plaza", localidades: ["Centro"],
  fecha_inicio: "15/09/2026", fecha_fin: "17/09/2026", modalidad_papel: true, creado_por: "Gestora Prueba",
  resumen_casos: { casos: 2, personas_observadas: 5, entrevistas: 1, sin_entrevista: 1, sin_entrevista_por_franja: 0 },
  equipo: [{ iniciales: "AC", nombre: "Ana Campo", dni: "30111222" }, { iniciales: "B", nombre: "beto", dni: "" }],
  observaciones: "Línea uno\nLínea dos", cierre: null,
  casos: [
    { id: "c1", codigo: "AB12", persona: "", lugar: "", sin_entrevista_por_franja: false, estado: "completa", estado_display: "Completa", es_formulario_menores: true, cargado: "16/09/26 10:51", url: "/datacalle/casos/c1/" },
    { id: "c2", codigo: "", persona: "Adulto", lugar: "Vereda", sin_entrevista_por_franja: true, estado: "rechazada", estado_display: "Rechazada", es_formulario_menores: false, cargado: "", url: "/datacalle/casos/c2/" },
  ],
  breadcrumb: [{ text: "Relevamientos", url: "/datacalle/relevamientos/" }, { text: "Operativo invierno", url: null }],
  can_change: true, can_close: true, can_delete: true,
  urls: { list: "/datacalle/relevamientos/", edit: `/datacalle/relevamientos/${ID}/editar/`, close: `/api/${API}${ID}/cerrar/`, delete: `/datacalle/relevamientos/${ID}/eliminar/` },
  messages: [], ...over,
});
const campo = (name: string, over: Record<string, unknown> = {}) => ({ name, label: name, required: false, disabled: false, widget: "text", help_text: "", value: "", attrs: {}, ...over });
const formulario = (over: Record<string, unknown> = {}) => ({
  titulo: "Planificar relevamiento",
  fields: [
    campo("denominacion", { label: "Denominación", required: true, help_text: "Nombre con el que el equipo identifica el operativo.", attrs: { maxlength: "255" } }),
    campo("provincia", { label: "Provincia", required: true, widget: "select", choices: [{ value: "", label: "---------" }, { value: "1", label: "Córdoba" }, { value: "2", label: "Salta" }] }),
    campo("municipio", { label: "Municipio", widget: "select", choices: [{ value: "", label: "---------" }] }),
    campo("localidades", { label: "Localidades / comunas", widget: "selectmultiple", value: [], choices: [] }),
    campo("fase", { label: "Fase", required: true, widget: "select", choices: [{ value: "", label: "---------" }, { value: "espacio_publico", label: "Espacio público" }, { value: "dispositivo_alojamiento", label: "Dispositivo de alojamiento" }] }),
    campo("area_operativa", { label: "Área operativa", help_text: "Lugar del operativo cuando la fase es espacio público." }),
    campo("dispositivo", { label: "Dispositivo", widget: "select", choices: [{ value: "", label: "---------" }] }),
    campo("fecha_inicio", { label: "Fecha de inicio", required: true, widget: "date" }),
    campo("fecha_fin", { label: "Fecha de fin", required: true, widget: "date" }),
    campo("modalidad_papel", { label: "Formato en papel", widget: "checkbox", value: false }),
    campo("equipo", { label: "Equipo", widget: "selectmultiple", value: [], choices: [] }),
    campo("observaciones", { label: "Observaciones", widget: "textarea", attrs: { cols: "40", rows: "3" } }),
  ],
  errors: {}, non_field_errors: [], can_add_dispositivo: true,
  urls: { cancel: "/datacalle/relevamientos/", add_dispositivo: "/dispositivos/crear", municipios: "/ajax/load-municipios/", localidades: "/ajax/load-localidades/",
    dispositivos: "/api/web/dispositivos/datacalle/opciones/dispositivos/", relevadores: "/api/web/dispositivos/datacalle/opciones/relevadores/" },
  messages: [], ...over,
});

type Hit = { data: unknown; status?: number };
function serve(routes: Record<string, Hit>) {
  webGet.mockImplementation((url: string) => {
    if (url === "web/session/") return Promise.resolve({ data: readyContext, status: 200 });
    const hit = routes[url];
    return hit ? Promise.resolve({ data: hit.data, status: hit.status ?? 200 }) : Promise.reject(new Error(`unexpected ${url}`));
  });
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const has = (el: Element | null) => expect(el).not.toBeNull();
const textOf = (el: Element | null) => (el?.textContent ?? "").replace(/\s+/g, " ").trim();
const attr = (el: Element | null, name: string) => el?.getAttribute(name);
const shown = (id: string) => (document.getElementById(id) as HTMLElement).style.display !== "none";
const assign = () => vi.spyOn(navigation, "assign").mockImplementation(() => undefined);

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("DataCalle operativos", () => {
  it("owns only the native operativo paths", () => {
    for (const path of ["/datacalle/relevamientos/", "/datacalle/relevamientos/crear/", `/datacalle/relevamientos/${ID}/`,
      `/datacalle/relevamientos/${ID}/editar/`, `/datacalle/relevamientos/${ID}/eliminar/`]) {
      expect(findRoute(path)?.route.name, path).toBe("datacalle-relevamientos");
    }
    for (const path of ["/datacalle/relevamientos", `/datacalle/relevamientos/${ID.toUpperCase()}/`, "/datacalle/relevamientos/12/",
      `/datacalle/relevamientos/${ID}/cerrar/`, `/datacalle/casos/${ID}/`]) {
      expect(findRoute(path)?.route.name, path).not.toBe("datacalle-relevamientos");
    }
  });

  it("renders the native list with its literal texts, summary and links", async () => {
    serve({ [`${API}?busqueda=plaza&estado=finalizado`]: { data: lista() } });
    setup("/datacalle/relevamientos/?busqueda=plaza&estado=finalizado");

    await waitFor(() => expect(textOf(screen.getByRole("heading", { level: 1 }))).toContain("Relevamientos DataCalle"));
    await waitFor(() => expect(document.title).toContain("Relevamientos DataCalle"));
    has(screen.getByText("Operativos de situación de calle"));
    has(screen.getByText("Le llegan como tarea al equipo en SISOC - Mobile"));
    expect(attr(screen.getByRole("link", { name: /Planificar relevamiento/ }), "href")).toBe("/datacalle/relevamientos/crear/");
    const stats = [...document.querySelectorAll(".dc-stat")].map((s) => s.textContent?.replace(/\s+/g, " ").trim());
    expect(stats).toEqual(["4 Total", "3 Planificado", "0 En curso", "1 Finalizado"]);
    expect((screen.getByPlaceholderText("Buscar por denominación, área, provincia, localidad, encuestador o DNI") as HTMLInputElement).value).toBe("plaza");
    const [estado, fase] = screen.getAllByRole("combobox") as HTMLSelectElement[];
    expect(estado.value).toBe("finalizado");
    expect(estado.options[0].text).toBe("Todos los estados");
    expect(fase.options[0].text).toBe("Ambos tipos de operativo");
    expect(attr(screen.getByRole("button", { name: /Filtrar/ }), "type")).toBe("submit");
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Operativo", "Jurisdicción", "Fechas", "Equipo", "Estado", "Acciones"]);
    const [primera, segunda] = screen.getAllByRole("row").slice(1);
    expect(primera.textContent?.replace(/\s+/g, " ")).toContain("Espacio público · Plaza · papel");
    has(within(primera).getByText("Centro, Alberdi"));
    has(within(primera).getByText("15/09/26 → 17/09/26"));
    has(within(primera).getByText("3 días"));
    has(within(segunda).getByText("1 día"));
    has(within(segunda).getByText("—"));
    expect(["dc-chip", "dc-chip--finalizado"].every((c) => (within(segunda).getByText("Finalizado"))?.classList.contains(c))).toBe(true);
    expect(attr(within(primera).getByRole("link", { name: /Ver/ }), "title")).toBe("Ver detalles");
    has(within(primera).getByRole("link", { name: /Editar/ }));
    expect(attr(screen.getByRole("link", { name: "Continuar" }), "href")).toBe("?estado=finalizado&page=2");
    has(screen.getByText("Se encontraron 16 resultados"));
  });

  it("hides the plan and edit actions without permission and shows the empty state", async () => {
    serve({ [API]: { data: lista({ results: [], count: 0, pages: 1, is_paginated: false, has_next: false, add_url: null, can_change: false }) } });
    setup("/datacalle/relevamientos/");

    await waitFor(() => has(screen.getByText("Todavía no hay operativos")));
    has(screen.getByText("Planificá uno para que le aparezca como tarea al equipo en la app."));
    expect(screen.queryByText(/Planificar relevamiento/)).toBeNull();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("renders the native ficha with every section", async () => {
    serve({ [`${API}${ID}/`]: { data: ficha() } });
    setup(`/datacalle/relevamientos/${ID}/`);

    await waitFor(() => expect(textOf(screen.getByRole("heading", { level: 1 }))).toContain("Operativo invierno"));
    await waitFor(() => expect(document.title).toContain("Operativo invierno"));
    for (const t of ["Dónde se releva", "Cuándo", "Equipo asignado", "Observaciones", "Cierre en campo", "Casos relevados", "se cargan desde la app",
      "Área operativa", "Período planificado", "Formato en papel", "Planificado por", "Gestora Prueba", "Sí", "2 entrevistadores", "DNI 30111222",
      "Todavía sin cerrar", "Menores (14 a 17)", "Sin entrevista (edad)", "Sin entrevista por edad", "Personas observadas"]) {
      expect(screen.getAllByText(t).length, t).toBeGreaterThan(0);
    }
    has(screen.getByText("El equipo cierra el operativo desde la app y ahí llegan el punto GPS y la observación del asentamiento."));
    expect(textOf(document.querySelector(".dc-seccion .dc-dato__valor .dc-chip--zona"))).toContain("Centro");
    expect(textOf(document.querySelectorAll(".dc-persona__avatar")[0])).toContain("AC");
    expect(screen.getByText(/Línea uno/).innerHTML).toBe("Línea uno<br>Línea dos");
    expect(attr(screen.getByRole("link", { name: /Editar/ }), "href")).toBe(`/datacalle/relevamientos/${ID}/editar/`);
    has(screen.getByRole("button", { name: /Cerrar relevamiento/ }));
    expect(attr(screen.getByRole("link", { name: /Eliminar/ }), "href")).toBe(`/datacalle/relevamientos/${ID}/eliminar/`);
    const casos = within(screen.getByText("AB12").closest("tbody")!).getAllByRole("row");
    expect(casos[1].textContent).toContain("—");
    expect(attr(within(casos[0]).getByRole("link", { name: /Ver/ }), "href")).toBe("/datacalle/casos/c1/");
    expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toEqual(expect.arrayContaining(["Relevamientos", "Operativo invierno"]));
  });

  it("shows the closed ficha, the empty team and cases, and hides actions by permission", async () => {
    serve({ [`${API}${ID}/`]: { data: ficha({
      estado: "finalizado", estado_display: "Finalizado", equipo: [], casos: [], observaciones: "", localidades: [], creado_por: null, lugar: "",
      cierre: { fecha: "20/09/2026 18:30", por: "Beto Ruiz", gps: null, observacion_asentamiento: ["Ranchada", "Colchones"], otra_observacion: "" },
      can_change: false, can_close: false, can_delete: false, messages: [{ message: "El relevamiento quedó cerrado.", level: "success" }],
    }) } });
    setup(`/datacalle/relevamientos/${ID}/`);

    await waitFor(() => has(screen.getByText("Sin equipo asignado: nadie va a ver este operativo en la app.")));
    has(screen.getByText("Todavía no llegaron casos"));
    has(screen.getByText("Aparecen acá a medida que el equipo sincroniza desde la app."));
    has(screen.getByText("0 entrevistadores"));
    expect(screen.getByText(/20\/09\/2026 18:30/).textContent?.replace(/\s+/g, " ").trim()).toBe("20/09/2026 18:30 por Beto Ruiz");
    has(screen.getByText("Ranchada, Colchones"));
    has(screen.getByText("El relevamiento quedó cerrado."));
    expect(screen.queryByText("Observaciones")).toBeNull();
    expect(screen.queryByRole("button", { name: /Cerrar relevamiento/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /Editar/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /Eliminar/ })).toBeNull();
    expect([...document.querySelectorAll(".dc-dato__valor--vacio")].map((e) => e.textContent?.trim())).toEqual(["—", "—", "—", "Sin equipo asignado: nadie va a ver este operativo en la app.", "—"]);
  });

  it("closes once and goes to the ficha the native redirect points to", async () => {
    serve({ [`${API}${ID}/`]: { data: ficha() } });
    webPost.mockReturnValue(new Promise(() => undefined));
    setup(`/datacalle/relevamientos/${ID}/`);
    const boton = await screen.findByRole("button", { name: /Cerrar relevamiento/ });
    fireEvent.click(boton);
    fireEvent.click(boton);

    await waitFor(() => expect((boton as HTMLButtonElement).disabled).toBe(true));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}${ID}/cerrar/`);
    expect((webPost.mock.calls[0][1] as FormData).get("csrfmiddlewaretoken")).toBe("synthetic-csrf-token");
  });

  it("navigates with the queued message after the close and reloads the ficha when it is uncertain", async () => {
    const go = assign();
    serve({ [`${API}${ID}/`]: { data: ficha() } });
    webPost.mockResolvedValueOnce({ status: 200, data: { cerrado_ahora: true, message: "El relevamiento quedó cerrado.", level: "success", url: `/datacalle/relevamientos/${ID}/` } });
    setup(`/datacalle/relevamientos/${ID}/`);
    fireEvent.click(await screen.findByRole("button", { name: /Cerrar relevamiento/ }));
    await waitFor(() => expect(go).toHaveBeenCalledWith(`/datacalle/relevamientos/${ID}/`));
    cleanup();

    go.mockClear();
    webPost.mockRejectedValueOnce(Object.assign(new Error("timeout"), { response: { status: 504, data: { uncertain: true } } }));
    setup(`/datacalle/relevamientos/${ID}/`);
    fireEvent.click(await screen.findByRole("button", { name: /Cerrar relevamiento/ }));
    await waitFor(() => expect(go).toHaveBeenCalledWith(`/datacalle/relevamientos/${ID}/`));
    expect(webPost).toHaveBeenCalledTimes(2);
  });

  it("confirms the soft delete with the native texts and goes to the list", async () => {
    const go = assign();
    serve({ [`${API}${ID}/eliminar/`]: { data: { id: ID, denominacion: "Operativo invierno", urls: { cancel: `/datacalle/relevamientos/${ID}/` }, messages: [] } } });
    webPost.mockResolvedValue({ status: 200, data: { url: "/datacalle/relevamientos/" } });
    setup(`/datacalle/relevamientos/${ID}/eliminar/`);

    await waitFor(() => has(screen.getByText("Confirmar eliminación")));
    await waitFor(() => expect(document.title).toContain("Eliminar relevamiento"));
    expect(screen.getByText(/¿Seguro que desea eliminar el relevamiento/).textContent?.replace(/\s+/g, " ").trim())
      .toBe("¿Seguro que desea eliminar el relevamiento Operativo invierno?");
    expect(screen.getByText(/Se da de baja de forma lógica/).textContent?.trim())
      .toBe("Se da de baja de forma lógica: deja de verse como tarea en la app y queda recuperable desde la papelera.");
    expect(attr(screen.getByRole("link", { name: "Cancelar" }), "href")).toBe(`/datacalle/relevamientos/${ID}/`);
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));

    await waitFor(() => expect(go).toHaveBeenCalledWith("/datacalle/relevamientos/"));
    expect(webPost.mock.calls[0][0]).toBe(`${API}${ID}/eliminar/`);
  });
});

describe("DataCalle operativo form", () => {
  it("renders the native create form with its literal texts", async () => {
    serve({ [`${API}formulario/`]: { data: formulario() } });
    setup("/datacalle/relevamientos/crear/");

    await waitFor(() => expect(textOf(screen.getByRole("heading", { level: 1 }))).toContain("Planificar relevamiento"));
    await waitFor(() => expect(document.title).toContain("Planificar relevamiento"));
    for (const t of ["El operativo le llega como tarea a los entrevistadores del equipo", "Identificación", "Dónde se releva", "Cuándo", "Equipo",
      "La fase define si el lugar es un área del espacio público o un dispositivo de alojamiento.", "Puede durar un día o varios.",
      "Sólo los entrevistadores elegidos ven el operativo en la app.", "Nombre con el que el equipo identifica el operativo."]) {
      expect(screen.getAllByText(t).length, t).toBeGreaterThan(0);
    }
    expect(attr(screen.getByRole("button", { name: /Guardar/ }), "type")).toBe("submit");
    expect(attr(screen.getByRole("link", { name: "Cancelar" }), "href")).toBe("/datacalle/relevamientos/");
    expect(shown("campo-area-operativa")).toBe(false);
    expect(shown("campo-dispositivo")).toBe(false);
    expect(attr(screen.getByRole("link", { name: "Dar de alta un dispositivo", hidden: true }), "target")).toBe("_blank");
    expect(textOf(document.getElementById("select2-id_provincia-container"))).toContain("---------");
    expect(attr(document.getElementById("id_provincia"), "tabindex")).toBe("-1");
    expect(attr(document.querySelector("#div_id_provincia .select2-selection"), "tabindex")).toBe("0");
    has(document.querySelector("#div_id_denominacion .asteriskField"));
    expect(document.querySelector("#div_id_area_operativa .asteriskField")).toBeNull();
  });

  it("shows the place field of the phase and validates it before posting", async () => {
    serve({ [`${API}formulario/`]: { data: formulario({ fields: formulario().fields.map((f) => (f.name === "fase" ? { ...f, value: "espacio_publico" } : f)) }) } });
    setup("/datacalle/relevamientos/crear/");
    await screen.findByText("Planificar relevamiento");

    expect(shown("campo-area-operativa")).toBe(true);
    has(document.querySelector("#div_id_area_operativa .asteriskField"));
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    await waitFor(() => expect(["dc-error-inline"].every((c) => (screen.getByText("Indicá el área operativa del espacio público."))?.classList.contains(c))).toBe(true));
    expect(["is-invalid"].every((c) => (document.getElementById("id_area_operativa"))?.classList.contains(c))).toBe(true);
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.input(document.getElementById("id_area_operativa")!, { target: { value: "Plaza" } });
    await waitFor(() => expect(screen.queryByText("Indicá el área operativa del espacio público.")).toBeNull());

    fireEvent.mouseDown(document.querySelector("#div_id_fase .select2-selection")!);
    fireEvent.click(await screen.findByRole("option", { name: "Dispositivo de alojamiento" }));
    await waitFor(() => expect(shown("campo-dispositivo")).toBe(true));
    expect(shown("campo-area-operativa")).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    await waitFor(() => has(screen.getByText("Elegí el dispositivo de alojamiento.")));
    expect(webPost).not.toHaveBeenCalled();
  });

  it("reloads municipalities, devices and team from the chosen province", async () => {
    serve({ [`${API}formulario/`]: { data: formulario() } });
    const load = vi.spyOn(lookups, "load").mockImplementation((url: string) => Promise.resolve(
      url.startsWith("/ajax/load-municipios/") ? [{ id: 7, nombre: "Capital" }]
        : url.startsWith("/ajax/load-localidades/") ? [{ id: 9, nombre: "Centro" }]
          : url.includes("opciones/dispositivos") ? [{ id: 3, nombre: "Refugio" }] : [{ id: 5, nombre: "Ana Campo (30111222)" }]));
    setup("/datacalle/relevamientos/crear/");
    await screen.findByText("Planificar relevamiento");

    fireEvent.mouseDown(document.querySelector("#div_id_provincia .select2-selection")!);
    fireEvent.click(await screen.findByRole("option", { name: "Córdoba" }));

    await waitFor(() => expect([...(document.getElementById("id_municipio") as HTMLSelectElement).options].map((o) => o.text)).toEqual(["Seleccionar municipio...", "Capital"]));
    expect(load.mock.calls.map((c) => c[0])).toEqual([
      "/ajax/load-municipios/?provincia_id=1",
      "/api/web/dispositivos/datacalle/opciones/dispositivos/?provincia_id=1",
      "/api/web/dispositivos/datacalle/opciones/relevadores/?provincia_id=1",
    ]);
    await waitFor(() => expect([...(document.getElementById("id_dispositivo") as HTMLSelectElement).options].map((o) => o.text)).toEqual(["Seleccionar dispositivo...", "Refugio"]));
    await waitFor(() => expect([...(document.getElementById("id_equipo") as HTMLSelectElement).options].map((o) => o.text)).toEqual(["Ana Campo (30111222)"]));

    fireEvent.mouseDown(document.querySelector("#div_id_municipio .select2-selection")!);
    fireEvent.click(await screen.findByRole("option", { name: "Capital" }));
    await waitFor(() => expect([...(document.getElementById("id_localidades") as HTMLSelectElement).options].map((o) => o.text)).toEqual(["Centro"]));
    expect(load).toHaveBeenLastCalledWith("/ajax/load-localidades/?municipio_id=7");
  });

  it("keeps a single province disabled", async () => {
    serve({ [`${API}formulario/`]: { data: formulario({ fields: formulario().fields.map((f) => (f.name === "provincia"
      ? { ...f, disabled: true, value: "1", help_text: "Tu alcance territorial es esta provincia." } : f)) }) } });
    setup("/datacalle/relevamientos/crear/");

    await waitFor(() => has(screen.getByText("Tu alcance territorial es esta provincia.")));
    expect((document.getElementById("id_provincia") as HTMLButtonElement).disabled).toBe(true);
    expect(["select2-container--disabled"].every((c) => (document.querySelector("#div_id_provincia .select2-container"))?.classList.contains(c))).toBe(true);
    expect(textOf(document.getElementById("select2-id_provincia-container"))).toContain("Córdoba");
    fireEvent.mouseDown(document.querySelector("#div_id_provincia .select2-selection")!);
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("saves once, renders the bound form on 400 and never retries an uncertain save", async () => {
    const go = assign();
    serve({ [`${API}${ID}/formulario/`]: { data: formulario({ titulo: "Editar relevamiento", fields: formulario().fields.map((f) => (f.name === "denominacion" ? { ...f, value: "Viejo" } : f)) }) } });
    webPost.mockResolvedValueOnce({ status: 400, data: formulario({
      titulo: "Editar relevamiento",
      errors: { equipo: [{ message: "Elegí al menos un entrevistador para el equipo.", code: "invalid" }], fecha_fin: [{ message: "La fecha de fin no puede ser anterior a la de inicio.", code: "invalid" }] },
    }) });
    setup(`/datacalle/relevamientos/${ID}/editar/`);
    await screen.findByText("Editar relevamiento");
    expect((screen.getByLabelText(/Denominación/) as HTMLInputElement).value).toBe("Viejo");

    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    await waitFor(() => has(screen.getByText("Elegí al menos un entrevistador para el equipo.")));
    expect(attr(screen.getByText("La fecha de fin no puede ser anterior a la de inicio.").closest(".invalid-feedback"), "id")).toBe("id_fecha_fin_error");
    expect(["is-invalid"].every((c) => (document.getElementById("id_fecha_fin"))?.classList.contains(c))).toBe(true);
    expect(["is-invalid"].every((c) => (document.getElementById("id_equipo"))?.classList.contains(c))).toBe(true);
    expect(webPost.mock.calls[0][0]).toBe(`${API}${ID}/editar/`);
    expect((webPost.mock.calls[0][1] as FormData).get("denominacion")).toBe("Viejo");

    webPost.mockResolvedValueOnce({ status: 200, data: { id: ID, url: `/datacalle/relevamientos/${ID}/` } });
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    await waitFor(() => expect(go).toHaveBeenCalledWith(`/datacalle/relevamientos/${ID}/`));

    webPost.mockRejectedValueOnce(Object.assign(new Error("timeout"), { response: { status: 504, data: { uncertain: true } } }));
    cleanup();
    setup(`/datacalle/relevamientos/${ID}/editar/`);
    await screen.findByText("Editar relevamiento");
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    await waitFor(() => expect(textOf(screen.getByRole("alert"))).toContain("No se pudo confirmar el resultado."));
    expect((screen.getByRole("button", { name: /Guardar/ }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(3);
  });
});
