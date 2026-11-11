import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { navigation } from "./cdfFrame";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const fila = (id: number, over: Record<string, unknown> = {}) => ({
  id, nombre: `Centro ${id}`, tipo: "adherido", tipo_display: "Adherido", calle: "None", telefono: "011", celular: "15", activo: true,
  urls: { detail: `/centrodefamilia/centros/${id}/`, edit: `/centrodefamilia/centros/${id}/editar/`, delete: `/centrodefamilia/centros/${id}/eliminar/` },
  ...over,
});

const lista = (over: Record<string, unknown> = {}) => ({
  count: null, page: 1, page_size: 10, pages: null, has_next: true, has_previous: false, page_range: [1, 2, "..."],
  filters: { busqueda: "", filters: "" },
  results: [fila(12, { nombre: "Beta", activo: false }), fila(11, { nombre: "alfa", tipo: "faro", tipo_display: "faro" })],
  is_paginated: true, query_prefix: "filters=x&",
  filters_config: { fields: [{ name: "nombre", label: "Nombre", type: "text" }, { name: "activo", label: "Activo", type: "boolean" }], operators: {} },
  favorites: { section: "centrodefamilia_centros", url: "/ajax/filtros-favoritos/", detail_url_template: "/ajax/filtros-favoritos/0/" },
  can_add: true, can_delete: false,
  urls: { list: "/centrodefamilia/centros/", add: "/centrodefamilia/centros/nuevo/", actividad_create: "/centrodefamilia/actividades/nueva/", informecabal: "/centrodefamilia/informecabal/" },
  messages: [],
  ...over,
});

const pagina = (results: unknown[], over: Record<string, unknown> = {}) => ({ number: 1, pages: 1, page_range: [1], previous: null, next: null, results, ...over });

const ficha = (over: Record<string, unknown> = {}, centro: Record<string, unknown> = {}) => ({
  centro: {
    id: 7, nombre: "centro siete", tipo: "adherido", tipo_display: "Adherido", activo: true, codigo: "C-7", numero: "742",
    localidad: null, provincia: "Provincia Sintética", municipio: null, organizacion_asociada: null,
    correo: "c@example.com", sitio_web: null, link_redes: null, telefono: "011", celular: null, calle: "Calle Falsa",
    domicilio_actividad: "Dom", nombre_referente: "Rita", apellido_referente: "Ref", telefono_referente: null, correo_referente: "r@example.com",
    ...centro,
  },
  mapa: null,
  acciones: { editar_url: "/centrodefamilia/centros/7/editar/", agregar_actividad_url: "/centrodefamilia/centros/7/actividades/nueva/", agregar_adherido_url: null, generar_usuario_url: null },
  metricas: { categorias: 3, actividades: 2, inscriptos: 1, hombres: 1, mujeres: 0, mixtas: 0, interacciones: 1, centros_faro: null, total_recaudado: "150", asistentes: { total: 1, hombres: 1, mujeres: 0, espera: 4 } },
  actividades_curso: pagina([{ id: 1, actividad: "Fútbol", categoria: "Deportes", dias: ["Lunes", "Martes"], horariosdesde: "09:30", horarioshasta: "None", estado_display: "En curso", detalle_url: "/centrodefamilia/actividades/1/" }],
    { pages: 2, page_range: [1, 2], next: 2 }),
  actividades_otras: pagina([{ id: 9, centro: "Otro", actividad: "Canto", categoria: "Arte", estado_display: "Planificada", cantidad_personas: "5", dias: [], horariosdesde: "18:00", horarioshasta: "None", precio: null }]),
  search: { actividades_curso: "", actividades: "", todas_activa: false },
  links: { curso_prefix: "?search_actividades_curso=&page_actividades_curso=", todas_suffix: "&search_actividades=" },
  cabal: { ultimo: null, archivos: [] },
  adheridos: [], observaciones: [], puede_ver_usuarios: false,
  urls: { usuarios: "/api/web/cdf/centros/7/usuarios/" },
  messages: [],
  ...over,
});

function serve(routes: Record<string, { data: unknown; status?: number }>, sessionStatus = 200) {
  webGet.mockImplementation((url: string) => {
    if (url === "web/session/") {
      return Promise.resolve(sessionStatus === 200 ? { data: readyContext, status: 200 }
        : { data: { detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, status: sessionStatus });
    }
    const hit = routes[url];
    return hit ? Promise.resolve({ data: hit.data, status: hit.status ?? 200 }) : Promise.reject(new Error(`unexpected ${url}`));
  });
}

function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("CDF centres route", () => {
  it("owns only the native list and detail paths", () => {
    expect(findRoute("/centrodefamilia/centros/")?.route.name).toBe("cdf-centros");
    expect(findRoute("/centrodefamilia/centros/7/")?.params).toEqual({ id: "7" });
    for (const other of ["/centrodefamilia/centros", "/centrodefamilia/centros/nuevo/", "/centrodefamilia/centros/7/editar/", "/centrodefamilia/centros/07/"]) {
      expect(findRoute(other)?.route.name).not.toBe("cdf-centros");
    }
  });

  it("loads the session and the list with the same query and renders the native list", async () => {
    serve({ "web/cdf/centros/?page=1": { data: lista() } });
    setup("/centrodefamilia/centros/?page=1");
    await screen.findByRole("heading", { name: "Buscar Centro" });
    expect(webGet).toHaveBeenCalledTimes(2);
    expect(document.title).toBe("SISOC - Centros de Familia");
    expect(screen.getByRole("link", { name: "Centro de Familia" }).getAttribute("href")).toBe("/centrodefamilia/centros/");
    const rows = within(document.getElementById("centros-table-body") as HTMLElement).getAllByRole("row");
    expect(rows.map((r) => r.querySelector("td")?.textContent)).toEqual(["Beta", "alfa"]);
    expect(rows[0].textContent).toContain("None");
    expect(rows[0].textContent).toContain("011 / 15");
    expect(within(rows[0]).getByText("Inactivo").className).toBe("badge badge-danger");
    expect(within(rows[1]).getByText("faro")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Agregar" }).getAttribute("href")).toBe("/centrodefamilia/centros/nuevo/");
    expect(screen.getByRole("link", { name: "Agregar Actividad" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Procesar Informe Cabal" }).id).toBe("btn-cabal");
    expect(screen.queryByRole("button", { name: /Eliminar/ })).toBeNull();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?filters=x&page=2");
    const paginacion = document.querySelector("#pagination-container ul") as HTMLElement;
    expect(within(paginacion).getByRole("link", { name: "Volver" }).getAttribute("href")).toBe("#");
    expect(screen.getByRole("link", { name: "..." }).closest("li")?.className).toBe("page-item disabled");
  });

  it("hides the SSE buttons without can_add and keeps Agregar like the native search bar", async () => {
    serve({ "web/cdf/centros/": { data: lista({ can_add: false, is_paginated: false, results: [] }) } });
    setup("/centrodefamilia/centros/");
    await screen.findByText("No se encontraron centros.");
    expect(screen.getByRole("link", { name: "Agregar" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Agregar Actividad" })).toBeNull();
    expect(document.querySelector("#pagination-container ul")).toBeNull();
  });

  it("deletes through the native POST form only after the native confirmation", async () => {
    serve({ "web/cdf/centros/": { data: lista({ can_delete: true }) } });
    setup("/centrodefamilia/centros/");
    const botones = await screen.findAllByRole("button", { name: /Eliminar/ });
    const form = botones[0].closest("form") as HTMLFormElement;
    expect(form.getAttribute("method")).toBe("post");
    expect(form.getAttribute("action")).toBe("/centrodefamilia/centros/12/eliminar/");
    expect((form.querySelector("input[name=csrfmiddlewaretoken]") as HTMLInputElement).value).toBe("synthetic-csrf-token");
    const confirm = vi.spyOn(navigation, "confirm").mockReturnValue(false);
    const submit = vi.fn((e: Event) => e.preventDefault());
    form.addEventListener("submit", submit);
    fireEvent.click(botones[0]);
    expect(confirm).toHaveBeenCalledWith("¿Estás seguro de que deseas eliminar este centro? Esta acción no se puede deshacer.");
    expect(submit).not.toHaveBeenCalled();
    confirm.mockReturnValue(true);
    fireEvent.click(botones[0]);
    expect(submit).toHaveBeenCalledTimes(1);
  });

  it("sorts only the visible rows like listSort (asc, desc, then keeps the order)", async () => {
    serve({ "web/cdf/centros/": { data: lista() } });
    setup("/centrodefamilia/centros/");
    const header = await screen.findByRole("columnheader", { name: /Nombre/ });
    const names = () => within(document.getElementById("centros-table-body") as HTMLElement).getAllByRole("row").map((r) => r.querySelector("td")?.textContent);
    fireEvent.click(header);
    expect(names()).toEqual(["alfa", "Beta"]);
    expect(header.className).toBe("sortable sort-asc");
    fireEvent.click(header);
    expect(names()).toEqual(["Beta", "alfa"]);
    fireEvent.click(header);
    expect(names()).toEqual(["Beta", "alfa"]);
    expect(header.className).toBe("sortable ");
  });

  it("serializes the boolean filter as the native advanced filters do", async () => {
    serve({ "web/cdf/centros/": { data: lista() } });
    setup("/centrodefamilia/centros/");
    const campo = await screen.findByLabelText("Buscar por");
    fireEvent.change(campo, { target: { value: "activo" } });
    const valores = screen.getAllByLabelText("Valor a buscar");
    const select = valores.find((v) => v.tagName === "SELECT") as HTMLSelectElement;
    expect([...select.options].map((o) => o.textContent)).toEqual(["Sí", "No"]);
    fireEvent.change(select, { target: { value: "false" } });
    const form = document.getElementById("filters-form") as HTMLFormElement;
    form.addEventListener("submit", (e) => e.preventDefault());
    fireEvent.submit(form);
    expect((document.getElementById("filters-input") as HTMLInputElement).value).toBe(
      JSON.stringify({ logic: "AND", items: [{ field: "activo", op: "eq", value: "false" }] }),
    );
  });

  it("renders the ficha from the projected context and never asks for credentials without the panel", async () => {
    serve({ "web/cdf/centros/7/": { data: ficha() } });
    setup("/centrodefamilia/centros/7/");
    await screen.findByRole("heading", { level: 1 });
    expect(document.title).toBe("SISOC - centro siete");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Centro siete Adherido Activo");
    expect(screen.getByText("$150")).toBeTruthy();
    expect(screen.getByText("1 hombres · 0 mujeres")).toBeTruthy();
    expect(screen.getByText("—, Provincia Sintética")).toBeTruthy();
    expect(screen.getByText("Sin mapa disponible")).toBeTruthy();
    expect(screen.getByText("Sin informes vinculados")).toBeTruthy();
    expect(screen.getByText("Lunes , Martes")).toBeTruthy();
    expect(screen.getByText("09:30 - None")).toBeTruthy();
    expect(screen.queryByRole("link", { name: /Agregar Adherido/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /Generar usuario/ })).toBeNull();
    expect(screen.getByRole("link", { name: "2" }).getAttribute("href")).toBe("?search_actividades_curso=&page_actividades_curso=2#actividades-curso-container");
    expect(screen.getByRole("tab", { name: "En curso" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.queryByText("Usuarios del centro")).toBeNull();
    expect(webGet).toHaveBeenCalledTimes(2);
  });

  it("opens the Todas tab when the native query asks for it and shows the activity modal", async () => {
    serve({ "web/cdf/centros/7/?page_act=1": { data: ficha({ search: { actividades_curso: "", actividades: "", todas_activa: true } }) } });
    setup("/centrodefamilia/centros/7/?page_act=1");
    const tab = await screen.findByRole("tab", { name: "Todas las actividades" });
    expect(tab.getAttribute("aria-selected")).toBe("true");
    expect(document.getElementById("pane-act-todas")?.className).toBe("tab-pane fade show active");
    fireEvent.click(screen.getByRole("button", { name: "Detalles" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("Canto – Otro")).toBeTruthy();
    expect(within(dialog).getByText("Gratuita")).toBeTruthy();
    expect(within(dialog).getByText("No especificado")).toBeTruthy();
    expect(document.body.classList.contains("modal-open")).toBe(true);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("reloads the page on every search input like centrodefamilia.js", async () => {
    serve({ "web/cdf/centros/7/?page=3&page_act=2": { data: ficha() } });
    setup("/centrodefamilia/centros/7/?page=3&page_act=2");
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    const curso = (await screen.findAllByPlaceholderText("Buscar actividad…"))[0];
    fireEvent.input(curso, { target: { value: "fu" } });
    expect(assign).toHaveBeenLastCalledWith("http://localhost:3000/centrodefamilia/centros/7/?page_act=2&search_actividades_curso=fu");
    fireEvent.input(screen.getAllByPlaceholderText("Buscar actividad…")[1], { target: { value: "x" } });
    expect(assign).toHaveBeenLastCalledWith("http://localhost:3000/centrodefamilia/centros/7/?page=3&search_actividades=x");
  });

  it("loads the CR1 panel once from its own endpoint and keeps it out of the URL", async () => {
    serve({
      "web/cdf/centros/7/": { data: ficha({ puede_ver_usuarios: true }) },
      "web/cdf/centros/7/usuarios/": { data: { results: [
        { username: "ref.uno", nombre_completo: null, email: "r@example.com", activo: true, contrasena_temporal: "Temp-1" },
        { username: "ref.dos", nombre_completo: "Dos", email: null, activo: false, contrasena_temporal: null },
      ] } },
    });
    setup("/centrodefamilia/centros/7/");
    expect(await screen.findByText("Temp-1")).toBeTruthy();
    expect(screen.getByText("Ya cambiada")).toBeTruthy();
    expect(screen.getByText("Baja")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/cdf/centros/7/usuarios/", expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(webGet).toHaveBeenCalledTimes(3);
    expect(window.location.href).not.toContain("Temp-1");
  });

  it("shows FARO actions and an empty adheridos tab", async () => {
    serve({ "web/cdf/centros/7/": { data: ficha({
      acciones: { editar_url: "/centrodefamilia/centros/7/editar/", agregar_actividad_url: "/a/", agregar_adherido_url: "/centrodefamilia/centros/nuevo/?faro=7", generar_usuario_url: "/centrodefamilia/centros/7/generar-usuario/" },
      metricas: { ...ficha().metricas, total_recaudado: null },
    }, { tipo: "faro", tipo_display: "faro" }) } });
    setup("/centrodefamilia/centros/7/");
    expect((await screen.findByRole("link", { name: "Agregar Adherido" })).getAttribute("href")).toBe("/centrodefamilia/centros/nuevo/?faro=7");
    expect(screen.getByRole("link", { name: "Generar usuario" })).toBeTruthy();
    expect(screen.getByText("Centros Adheridos")).toBeTruthy();
    expect(screen.queryByText("Monto Recaudado")).toBeNull();
    expect(screen.getByRole("tab", { name: "Centros adheridos" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByText("No hay centros adheridos.")).toBeTruthy();
  });

  it("maps 403, 404, a pending requirement and a malformed payload to their states", async () => {
    serve({ "web/cdf/centros/7/": { data: { detail: "x" }, status: 403 } });
    const first = setup("/centrodefamilia/centros/7/");
    await waitFor(() => expect(webGet).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
    first.unmount();
    serve({ "web/cdf/centros/7/": { data: { detail: "x" }, status: 404 } });
    const second = setup("/centrodefamilia/centros/7/");
    expect(await screen.findByText("No se encontró la página.")).toBeTruthy();
    second.unmount();
    serve({ "web/cdf/centros/": { data: { ...lista(), count: "x" } } });
    setup("/centrodefamilia/centros/");
    expect(await screen.findByText("No se pudo cargar la página.")).toBeTruthy();
  });

  it("rejects a map source outside Google Maps", async () => {
    serve({ "web/cdf/centros/7/": { data: ficha({ mapa: "https://evil.example/x" }) } });
    setup("/centrodefamilia/centros/7/");
    expect(await screen.findByText("No se pudo cargar la página.")).toBeTruthy();
  });
});
