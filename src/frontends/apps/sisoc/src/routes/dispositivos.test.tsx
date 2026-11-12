import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { resetLeafletForTests } from "./dispositivosMapa";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const fila = (id: number) => ({
  id, nombre_institucion: `Dispositivo ${id}`, tipo_dispositivo_display: "Refugio", provincia: "Buenos Aires", municipio: "La Plata",
  urls: { detail: `/dispositivos/${id}/`, edit: `/dispositivos/${id}/editar`, delete: `/dispositivos/${id}/eliminar` },
});
const filtersConfig = { fields: [{ name: "nombre_institucion", label: "Institución", type: "text" }], operators: {} };
const favorites = { section: "dispositivos", url: "/ajax/filtros-favoritos/", detail_url_template: "/ajax/filtros-favoritos/0/" };
const lista = (over: Record<string, unknown> = {}) => ({
  count: 20, page: 1, page_size: 15, pages: 2, filters: { busqueda: "", filters: "" }, results: [fila(2), fila(1)],
  is_paginated: true, has_next: true, has_previous: false, page_range: [1, 2], query_prefix: "filters=x&",
  titulo: "Buscar Dispositivos", filters_config: filtersConfig, favorites, add_url: "/dispositivos/crear", map_url: "/dispositivos/mapa/?busqueda=x",
  urls: { list: "/dispositivos/", reset: "/dispositivos/" }, can_change: true, can_delete: false, messages: [],
  ...over,
});
const ficha = (over: Record<string, unknown> = {}) => ({
  id: 7, nombre_institucion: "Refugio Siete", meta: { tipo: "Refugio", provincia: "Buenos Aires", municipio: "La Plata", actualizado: "10/11/2026" },
  can_change: true, edit_url: "/dispositivos/7/editar",
  breadcrumb: [{ text: "Dispositivos", url: "/dispositivos/" }, { text: "Refugio Siete", url: null }],
  show_map: true, mapa_query: "Calle%201%2C%20La%20Plata",
  detalle_secciones: [
    { titulo: "Identificación del dispositivo", icono: "fas fa-building", items: [
      { label: "Nombre de la institución", value: "Refugio Siete", kind: "text", wide: false },
      { label: "Razón social", value: "-", kind: "text", wide: false },
      { label: "Días de atención", value: ["Lunes", "Martes"], kind: "list", wide: false },
      { label: "Horarios", value: [], kind: "list", wide: false },
    ] },
    { titulo: "Observaciones y documentación", icono: "fas fa-file-alt", items: [
      { label: "Observaciones adicionales", value: "Nota", kind: "text", wide: true },
      { label: "Documentación del dispositivo", value: { name: "acta.pdf", url: "/media/acta.pdf" }, kind: "file", wide: false },
      { label: "Documentación adicional 1", value: { name: "foto.PNG", url: "/media/foto.PNG" }, kind: "file", wide: false },
      { label: "Documentación adicional 2", value: null, kind: "file", wide: false },
    ] },
  ],
  messages: [{ message: "Dispositivo actualizado correctamente.", level: "success" }],
  ...over,
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

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
  resetLeafletForTests();
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  delete (window as unknown as { L?: unknown }).L;
  document.querySelectorAll("script[src*='leaflet']").forEach((s) => s.remove());
});

describe("Dispositivos list and legajo", () => {
  it("owns only the native list, legajo and map paths", () => {
    expect(findRoute("/dispositivos/")?.route.name).toBe("dispositivos");
    expect(findRoute("/dispositivos/7/")?.params).toEqual({ id: "7" });
    expect(findRoute("/dispositivos/mapa/")?.params).toEqual({ mapa: true });
    for (const other of ["/dispositivos", "/dispositivos/crear", "/dispositivos/7/editar", "/dispositivos/07/", "/dispositivos/7/ubicacion/"]) {
      expect(findRoute(other)?.route.name).not.toBe("dispositivos");
    }
  });

  it("loads the list with the same query and renders the native table and actions", async () => {
    serve({ "web/dispositivos/listado/?busqueda=x": { data: lista() } });
    setup("/dispositivos/?busqueda=x");
    await screen.findByRole("heading", { name: "Buscar Dispositivos" });
    await waitFor(() => expect(document.title).toBe("SISOC - Dispositivos"));
    const tabla = document.querySelector("table.table-comedor-moderno") as HTMLElement;
    expect(within(tabla).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Institución", "Tipo", "Provincia", "Municipio", "Acciones"]);
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas.map((r) => r.querySelector("td")?.textContent)).toEqual(["Dispositivo 2", "Dispositivo 1"]);
    const mapa = within(filas[0]).getByRole("link", { name: "Ver en mapa" });
    expect(mapa.getAttribute("href")).toBe("/dispositivos/mapa/?busqueda=x&dispositivo=2");
    expect(mapa.getAttribute("title")).toBe("Ver ubicación en el mapa");
    expect(within(filas[0]).getByRole("link", { name: "Ver detalle" }).getAttribute("href")).toBe("/dispositivos/2/");
    expect(within(filas[0]).getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/dispositivos/2/editar");
    expect(within(filas[0]).queryByRole("link", { name: "Eliminar" })).toBeNull();
    expect(screen.getByRole("link", { name: "Mapa de dispositivos" }).getAttribute("href")).toBe("/dispositivos/mapa/?busqueda=x");
    expect(screen.getByRole("link", { name: "Agregar dispositivo" }).getAttribute("href")).toBe("/dispositivos/crear");
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("href")).toBe("/dispositivos/");
    const paginacion = document.querySelector("ul.pagination") as HTMLElement;
    expect(within(paginacion).getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?filters=x&page=2");
    expect(within(paginacion).getByRole("link", { name: "Volver" }).getAttribute("href")).toBe("#");
    expect(within(paginacion).getByRole("link", { name: "1" }).closest("li")?.className).toBe("page-item active");
    expect(screen.getByText("Se encontraron 20 resultados")).toBeTruthy();
  });

  it("shows the native empty state and hides actions without permissions", async () => {
    serve({ "web/dispositivos/listado/": { data: lista({ results: [], count: 0, is_paginated: false, add_url: null, map_url: null, can_change: false }) } });
    setup("/dispositivos/");
    await screen.findByText("No se encontraron dispositivos");
    expect(screen.getByText("No hay dispositivos que coincidan con los criterios de búsqueda.")).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Agregar dispositivo" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Mapa de dispositivos" })).toBeNull();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
    expect(document.querySelector(".pagination")).toBeNull();
  });

  it("renders the forbidden screen and the not found state from the API", async () => {
    serve({ "web/dispositivos/listado/": { data: { detail: "x" }, status: 403 } });
    setup("/dispositivos/");
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Buscar Dispositivos" })).toBeNull());
    await waitFor(() => expect(webGet).toHaveBeenCalledTimes(2));
    cleanup();
    serve({ "web/dispositivos/9/": { data: { detail: "No encontrado." }, status: 404 } });
    setup("/dispositivos/9/");
    expect(await screen.findByText("No se encontró la página.")).toBeTruthy();
  });

  it("renders the legajo sections, chips, files, map and the edit button", async () => {
    serve({ "web/dispositivos/7/": { data: ficha() } });
    setup("/dispositivos/7/");
    await screen.findByRole("heading", { level: 1, name: "Refugio Siete" });
    await waitFor(() => expect(document.title).toBe("SISOC - Refugio Siete"));
    expect(document.querySelector(".detail-page-meta")?.textContent).toBe("Refugio · Buenos Aires · La Plata · Actualizado el 10/11/2026");
    expect(screen.getByRole("link", { name: "Dispositivos" }).getAttribute("href")).toBe("/dispositivos/");
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/dispositivos/7/editar");
    expect(screen.getByTitle("Ubicación del dispositivo").getAttribute("src")).toBe("https://www.google.com/maps?q=Calle%201%2C%20La%20Plata&output=embed");
    expect(screen.getByText("Dispositivo actualizado correctamente.")).toBeTruthy();
    const acordeon = document.querySelector(".accordion-horizontal") as HTMLElement;
    const headers = within(acordeon).getAllByRole("button");
    expect(headers.map((h) => h.textContent)).toEqual(["Identificación del dispositivo", "Observaciones y documentación"]);
    expect(headers[0].className).toBe("accordion-header h5 accordion-header--informacion");
    expect(headers.map((h) => h.getAttribute("aria-expanded"))).toEqual(["true", "false"]);
    fireEvent.click(headers[1]);
    await waitFor(() => expect(headers.map((h) => h.getAttribute("aria-expanded"))).toEqual(["false", "true"]));
    expect(acordeon.style.height).toBe("400px");
    const panel = headers[1].closest(".accordion-panel") as HTMLElement;
    expect(panel.style.width).toBe("calc(100% - 60px)");
    await waitFor(() => expect(document.querySelector(".accordion-shell")?.className).toBe("accordion-shell"));
    const tarjetas = document.querySelectorAll(".section-card");
    expect(tarjetas).toHaveLength(2);
    const primera = tarjetas[0] as HTMLElement;
    expect(within(primera).getAllByText("—").map((e) => e.className.trim())).toEqual(["detail-item-value empty", "detail-item-value empty"]);
    expect(within(primera).getAllByText(/Lunes|Martes/).map((e) => e.className)).toEqual(["chip", "chip"]);
    const segunda = tarjetas[1] as HTMLElement;
    expect(within(segunda).getByText("Nota").parentElement?.className).toBe("col-md-12");
    const docs = within(segunda).getAllByRole("link");
    expect(docs.map((d) => [d.getAttribute("href"), d.getAttribute("title"), d.getAttribute("target")])).toEqual([
      ["/media/acta.pdf", "Documentación del dispositivo", "_blank"], ["/media/foto.PNG", "Documentación adicional 1", "_blank"],
    ]);
    expect(docs[0].querySelector(".doc-card-icon")?.className).toContain("fa-file-pdf pdf");
    expect(docs[1].querySelector(".doc-card-icon")?.className).toContain("fa-file-image img");
    // Native quirk: the block header only opens when the first item of the section is a file.
    expect(within(segunda).queryByText("Archivos adjuntos")).toBeNull();
    expect(segunda.querySelector(".doc-cards-grid")).toBeNull();
  });

  it("omits the map and the edit button without their permissions and stacks panels on mobile", async () => {
    vi.stubGlobal("innerWidth", 390);
    serve({ "web/dispositivos/7/": { data: ficha({ show_map: false, mapa_query: null, can_change: false, meta: { tipo: null, provincia: "Buenos Aires", municipio: null, actualizado: null } }) } });
    setup("/dispositivos/7/");
    await screen.findByRole("heading", { level: 1, name: "Refugio Siete" });
    expect(screen.queryByTitle("Ubicación del dispositivo")).toBeNull();
    expect(screen.queryByRole("link", { name: "Editar" })).toBeNull();
    expect(document.querySelector(".detail-page-meta")?.textContent).toBe(" · Buenos Aires");
    const acordeon = document.querySelector(".accordion-horizontal") as HTMLElement;
    expect(acordeon.style.height).toBe("auto");
    expect((acordeon.querySelector(".accordion-panel") as HTMLElement).style.width).toBe("100%");
  });
});

// --- Map ---------------------------------------------------------------------

const device = (id: number, over: Record<string, unknown> = {}) => ({
  id, name: `Dispositivo ${id}`, type: "Refugio", province_id: 1, province: "Buenos Aires", representative: "Ana", phone: "221 1",
  address: `Calle ${id} 100, La Plata, Buenos Aires`, detail_url: `/dispositivos/${id}/`, location_url: `/api/web/dispositivos/${id}/ubicacion/`,
  location: null, municipio: "La Plata", street: `Calle ${id} 100`, ...over,
});
const mapa = (devices: unknown[], over: Record<string, unknown> = {}) => ({
  titulo: "Buscar Dispositivos", devices, provinces: [{ id: 1, nombre: "Buenos Aires" }], filters_config: filtersConfig, favorites,
  location_filters: [], initial_device: "", urls: { list: "/dispositivos/mapa/", reset: "/dispositivos/mapa/" }, messages: [], ...over,
});

function fakeLeaflet() {
  const markers: { title: string; popup: HTMLElement | null; open: number }[] = [];
  const layers = new Set<unknown>();
  const map = { setView: vi.fn(() => map), fitBounds: vi.fn(), on: vi.fn(), closePopup: vi.fn(), remove: vi.fn() };
  const group = {
    addTo: () => group, getLayers: () => [...layers], getBounds: () => "bounds",
    hasLayer: (l: unknown) => layers.has(l), addLayer: (l: unknown) => layers.add(l), removeLayer: (l: unknown) => layers.delete(l),
  };
  const L = {
    map: vi.fn(() => map), tileLayer: vi.fn(() => ({ addTo: vi.fn() })), featureGroup: () => group, divIcon: vi.fn(() => "icon"),
    marker: vi.fn((_c: unknown, o: { title: string }) => {
      const entry = { title: o.title, popup: null as HTMLElement | null, open: 0 };
      markers.push(entry);
      const marker = {
        getLatLng: () => _c, openPopup: () => { entry.open += 1; }, on: vi.fn(),
        bindPopup: (e: HTMLElement) => { entry.popup = e; return marker; },
        addTo: () => { layers.add(marker); return marker; },
      };
      return marker;
    }),
  };
  (window as unknown as { L: unknown }).L = L;
  return { L, map, markers, layers };
}

function respond(statuses: Record<string, { status: number; body: unknown }>) {
  const fetchMock = vi.fn((url: string) => {
    const hit = statuses[url];
    if (!hit) return Promise.reject(new Error("network"));
    return Promise.resolve({ ok: hit.status === 200, json: () => Promise.resolve(hit.body) });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("Dispositivos map", () => {
  it("reports the native failure text and keeps the table when Leaflet does not load", async () => {
    serve({ "web/dispositivos/mapa/": { data: mapa([device(1), device(2)]) } });
    setup("/dispositivos/mapa/");
    await screen.findByRole("heading", { name: "Mapa de dispositivos" });
    await waitFor(() => expect(document.getElementById("map-status")?.textContent).toBe("2 dispositivos para cargar."));
    const script = await waitFor(() => {
      const found = document.querySelector("script[src*='leaflet']") as HTMLScriptElement | null;
      expect(found).not.toBeNull();
      return found as HTMLScriptElement;
    });
    expect(script.integrity).toBe("sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH");
    act(() => { script.dispatchEvent(new Event("error")); });
    await waitFor(() => expect(document.getElementById("map-status")?.textContent).toBe("No se pudo cargar el mapa. Consultá las direcciones en la tabla."));
    expect(document.getElementById("map-filter-count")?.textContent).toBe("2 dispositivos en el listado.");
    expect(screen.getByRole("button", { name: /Ver todos/ }).hasAttribute("disabled")).toBe(true);
    expect(document.querySelectorAll("#map-devices-table tbody tr:not([hidden])")).toHaveLength(2);
    expect(document.getElementById("location-status-1")?.textContent).toBe("Pendiente");
    expect(screen.getByText("Dispositivos (2)")).toBeTruthy();
  });

  it("uses saved locations first, looks the rest up in order and stops after unavailable", async () => {
    const { markers, map } = fakeLeaflet();
    const fetchMock = respond({
      "/api/web/dispositivos/2/ubicacion/": { status: 200, body: { status: "ambiguous" } },
      "/api/web/dispositivos/3/ubicacion/": { status: 503, body: { status: "unavailable" } },
    });
    serve({ "web/dispositivos/mapa/": { data: mapa([device(2), device(3), device(4), device(1, { location: { status: "located", lat: -34, lon: -58 } })]) } });
    setup("/dispositivos/mapa/");
    await waitFor(() => expect(document.getElementById("map-status")?.textContent).toBe(
      "1 ubicados · 1 guardados · 3 sin ubicar · 4/4 revisados. No se pudo consultar el servicio de ubicación. Volvé a intentar recargando la página."));
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual(["/api/web/dispositivos/2/ubicacion/", "/api/web/dispositivos/3/ubicacion/"]);
    expect(["1", "2", "3", "4"].map((id) => document.getElementById(`location-status-${id}`)?.textContent))
      .toEqual(["Ubicado", "Dirección ambigua", "Servicio no disponible", "Servicio no disponible"]);
    expect(markers.map((m) => m.title)).toEqual(["Dispositivo 1"]);
    expect([...(markers[0].popup as HTMLElement).children].map((e) => e.textContent)).toEqual([
      "Dispositivo 1", "Calle 1 100, La Plata, Buenos Aires", "Refugio", "Representante: Ana", "Teléfono: 221 1", "Ver detalle"]);
    const boton = document.querySelector('[data-map-focus="1"]') as HTMLButtonElement;
    expect(boton.disabled).toBe(false);
    expect(boton.title).toBe("Ver Dispositivo 1 en el mapa");
    expect((document.querySelector('[data-map-focus="2"]') as HTMLButtonElement).title).toBe("Dirección ambigua");
    expect(screen.getByRole("button", { name: /Ver todos/ }).hasAttribute("disabled")).toBe(false);
    expect(document.getElementById("map-filter-count")?.textContent).toBe("Mostrando 1–4 de 4 dispositivos");
    expect(map.fitBounds).toHaveBeenCalled();
    fireEvent.click(boton);
    await waitFor(() => expect(document.getElementById("map-device-1")?.className).toBe("table-active"));
    expect(map.setView).toHaveBeenLastCalledWith([-34, -58], 16);
    expect(markers[0].open).toBe(1);
  });

  it("applies the location-state filters on the client and paginates by 15", async () => {
    fakeLeaflet();
    respond({});
    const located = { status: "located", lat: -34, lon: -58 };
    const devices = Array.from({ length: 17 }, (_, i) => device(i + 1, { location: i < 16 ? located : { status: "not_found" } }));
    serve({ "web/dispositivos/mapa/": { data: mapa(devices, { location_filters: [{ field: "estado_ubicacion", op: "eq", value: "located" }], initial_device: 16 }) } });
    setup("/dispositivos/mapa/");
    await waitFor(() => expect(document.getElementById("map-status")?.textContent).toBe("16 ubicados · 17 guardados · 1 sin ubicar · 17/17 revisados"));
    // The initial device is on page 2: its page is shown and its row selected.
    await waitFor(() => expect(document.getElementById("map-device-16")?.className).toBe("table-active"));
    expect(document.getElementById("map-filter-count")?.textContent).toBe("Mostrando 16–16 de 16 dispositivos");
    expect(document.getElementById("map-device-17")?.hidden).toBe(true);
    const nav = document.getElementById("map-pagination") as HTMLElement;
    expect(nav.hidden).toBe(false);
    expect(within(nav).getAllByRole("button").map((b) => b.textContent)).toEqual(["Volver", "1", "2", "Continuar"]);
    fireEvent.click(within(nav).getByRole("button", { name: "1" }));
    await waitFor(() => expect(document.getElementById("map-filter-count")?.textContent).toBe("Mostrando 1–15 de 16 dispositivos"));
    expect(document.querySelectorAll("#map-devices-table tbody tr[data-device-id]:not([hidden])")).toHaveLength(15);
  });

  it("shows the client empty row when no device matches the state filter", async () => {
    fakeLeaflet();
    respond({});
    serve({ "web/dispositivos/mapa/": { data: mapa([device(1, { location: { status: "not_found" } })], { location_filters: [{ field: "estado_ubicacion", op: "eq", value: "located" }] }) } });
    setup("/dispositivos/mapa/");
    await waitFor(() => expect(document.getElementById("map-filter-count")?.textContent).toBe("No se encontraron dispositivos"));
    expect(document.getElementById("map-filter-empty")?.hidden).toBe(false);
    expect(screen.getByText("No hay dispositivos que coincidan con la provincia y el estado seleccionados.")).toBeTruthy();
  });

  it("explains an empty server result", async () => {
    fakeLeaflet();
    respond({});
    serve({ "web/dispositivos/mapa/": { data: mapa([]) } });
    setup("/dispositivos/mapa/");
    await waitFor(() => expect(document.getElementById("map-status")?.textContent).toBe("No hay dispositivos para mostrar con los filtros seleccionados."));
    expect(screen.getByText("No hay dispositivos que coincidan con los criterios de búsqueda.")).toBeTruthy();
    expect(document.getElementById("map-filter-empty")).toBeNull();
  });
});
