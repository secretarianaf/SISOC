import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "/api/web/inspecciones/tablero/";
const session = { ...readyContext, navigation: [{ id: "inicio", label: "Inicio", href: "/inicio/", children: [] }] };
const tabs = [
  { id: "tablero", label: "Tablero", url: "/inspecciones/tablero/" },
  { id: "escuelas", label: "Escuelas", url: "/inspecciones/" },
  { id: "asignaciones", label: "Asignaciones", url: "/inspecciones/asignaciones/" },
  { id: "actas", label: "Actas", url: "/inspecciones/actas/" },
];
const shell = (over: Record<string, unknown> = {}) => ({
  layout: { breadcrumb: [{ text: "Inicio", url: "/inicio/" }, { text: "Inspecciones escolares", url: "/inspecciones/" }, { text: "Tablero", url: null }], display_name: "Gestora Sintética", role: "Coordinación sintética", initials: "GS" },
  tabs, filters: { fecha: "2026-11-11", provincia: "", localidad: "", inspector: "", turno: "", notificacion: "" },
  options: {
    provincias: [{ id: 1, nombre: "Buenos Aires" }, { id: 2, nombre: "Córdoba" }], inspectores: [{ id: 7, nombre: "Ines Aguirre" }],
    turnos: [{ valor: "manana", etiqueta: "Mañana" }, { valor: "tarde", etiqueta: "Tarde" }], notificaciones: [{ valor: "pendiente", etiqueta: "Pendiente" }, { valor: "cargada", etiqueta: "Cargada" }],
  },
  intervalo_ms: 5000, urls: { datos: `${API}datos/`, exportar: `${API}exportar.csv`, descargar: `${API}descargar-actas/` }, messages: [], ...over,
});
const cat = (valor: string, etiqueta: string, cantidad: number) => ({ valor, etiqueta, cantidad });
const acta = (n: number, extra: Record<string, unknown> = {}) => ({
  numero: `ACTA-2026-00000${n}`, url: `/inspecciones/actas/ACTA-2026-00000${n}/`, escuela: `Escuela ${n}`, cueanexo: "060123400", turno: "Tarde", inspector: "Ines Aguirre", resultado: "Constatado",
  hora: "15:0" + n, provincia: "Buenos Aires", firma: { tipo: "excepcion", etiqueta: "Sin firma: Negativa" }, notificacion: { estado: "pendiente", etiqueta: "Pendiente" }, ...extra,
});
const datos = (over: Record<string, unknown> = {}) => ({
  indicadores: { escuelas_unicas: 1234, actas_validas: 1500, escuelas_con_mas_de_una_visita: 3, inspectores: { con_actividad: 4, habilitados: 6, sin_actividad: 2 }, borradores_en_curso: 5, notificacion_pendiente: 7, notificacion_cargada: 9 },
  turnos: [cat("manana", "Mañana", 10), cat("tarde", "Tarde", 5)],
  resultados: [cat("constatado", "Constatado", 3), cat("cerrada", "Cerrada", 1)],
  ausentismo: { previsto: 100, presente: 80, computables: 4, colegios: 3, excluidas: 1, porcentaje: 20 },
  aulas: { previsto: 40, presente: 30, computables: 4, colegios: 3, excluidas: 0, porcentaje: 75 },
  presencia: { personal: { total: 5, denominador: 4, categorias: [cat("si", "Sí", 3), cat("no", "No", 1)] }, estudiantes: { total: 5, denominador: 5, categorias: [cat("si", "Sí", 5)] } },
  mapa: { puntos: [], con_gps: 0, sin_coordenadas: 2, manual: 1, sin_ubicacion: 1 },
  ultimas: [acta(1), acta(2, { firma: { tipo: "firma", etiqueta: "Firmada" }, notificacion: { estado: "cargada", etiqueta: "Cargada" }, url: null })],
  opciones: { localidades: [{ id: 9, nombre: "San Justo · La Matanza" }] }, ...over,
});

type Reply = { data: unknown; status: number } | Error;
function serve(shellData: unknown, replies: Reply[] | ((query: string) => Reply)) {
  const calls: string[] = [];
  webGet.mockImplementation((url: string, config?: Record<string, unknown>) => {
    if (url === "web/session/") return Promise.resolve({ data: session, status: 200 });
    if (url.startsWith("web/inspecciones/tablero/datos/")) {
      calls.push(url);
      const next = typeof replies === "function" ? replies(url) : (replies[Math.min(calls.length - 1, replies.length - 1)]);
      expect(config).toEqual(expect.objectContaining({ headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" } }));
      return next instanceof Error ? Promise.reject(next) : Promise.resolve(next);
    }
    return Promise.resolve({ data: shellData, status: 200 });
  });
  return calls;
}
const ok = (over: Record<string, unknown> = {}): Reply => ({ data: datos(over), status: 200 });
const flush = () => act(async () => { await vi.advanceTimersByTimeAsync(0); });
const advance = (ms: number) => act(async () => { await vi.advanceTimersByTimeAsync(ms); });
async function setup(path = "/inspecciones/tablero/") {
  window.history.replaceState({}, "", path);
  const view = render(<App />);
  await flush();
  await flush();
  return view;
}
const text = (selector: string) => document.querySelector(selector)?.textContent;
const state = () => document.querySelector("[data-tablero-vivo]")?.getAttribute("data-estado");

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval", "Date"] });
  vi.setSystemTime(new Date("2026-11-11T18:00:00Z"));
  document.body.className = "";
  document.body.removeAttribute("style");
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Inspecciones tablero route", () => {
  it("owns only the native tablero path", () => {
    expect(findRoute("/inspecciones/tablero/")?.route.name).toBe("inspecciones-tablero");
    expect(findRoute("/inspecciones/tablero/datos/")?.route.name).not.toBe("inspecciones-tablero");
    expect(findRoute("/inspecciones/tablero/exportar.csv")?.route.name).not.toBe("inspecciones-tablero");
    expect(findRoute("/inspecciones/tablero/descargar-actas/")?.route.name).not.toBe("inspecciones-tablero");
  });

  it("shows the template placeholders until the first read, then the server figures", async () => {
    let resolve: (reply: Reply) => void = () => undefined;
    webGet.mockImplementation((url: string) => {
      if (url === "web/session/") return Promise.resolve({ data: session, status: 200 });
      if (url.startsWith("web/inspecciones/tablero/datos/")) return new Promise((r) => { resolve = r; });
      return Promise.resolve({ data: shell({ filters: { fecha: "2026-11-11", provincia: "", localidad: "", inspector: "", turno: "tarde", notificacion: "" } }), status: 200 });
    });
    await setup("/inspecciones/tablero/?turno=tarde");
    expect(webGet.mock.calls[1][0]).toBe("web/inspecciones/tablero/?turno=tarde");
    expect(document.title).toBe("SISOC - Tablero · Inspecciones escolares");
    expect(text("[data-tablero-estado]")).toBe("Conectando…");
    expect(text('[data-kpi="actas_validas"]')).toBe("–");
    expect(text("[data-tablero-ultimas]")).toBe("Cargando…");
    expect(text("[data-indice=\"ausentismo-descripcion\"]")).toBe("–");
    expect(screen.getByRole("link", { name: "Tablero" }).getAttribute("aria-current")).toBe("page");
    expect(text(".insp-tablero-vivo-intervalo")).toBe("· se actualiza cada 5 s");
    await act(async () => { resolve({ data: datos(), status: 200 }); await vi.advanceTimersByTimeAsync(0); });
    expect(state()).toBe("vivo");
    expect(text("[data-tablero-estado]")).toBe("En vivo");
    expect(text('[data-kpi="escuelas_unicas"]')).toBe("1.234");
    expect(text('[data-kpi="actas_validas"]')).toBe("1.500");
    expect(text('[data-kpi="inspectores_habilitados"]')).toBe("6");
    expect(text("[data-indice=\"ausentismo-porcentaje\"]")).toBe("20,0 %");
    expect(text("[data-indice=\"ausentismo-fraccion\"]")).toBe("20 / 100");
    expect(text("[data-indice=\"ausentismo-fraccion-etiqueta\"]")).toBe("ausentes / previstos");
    expect(text("[data-indice=\"ausentismo-descripcion\"]")).toBe("Personal ausente sobre el previsto · 3 colegios · 4 de 5 actas computables");
    expect(text("[data-indice=\"aulas-fraccion\"]")).toBe("30 / 40");
    expect(text("[data-indice=\"aulas-excluidas\"]")).toBe("0 excluidas");
    expect(document.querySelector('[data-indice="ausentismo-aviso-exceso"]')?.className).toContain("d-none");
    expect(text("[data-tablero-sin-gps]")).toBe("2 actas sin ubicación GPS, fuera del mapa (1 con ubicación manual · 1 sin ubicación)");
    expect(text("[data-tablero-presencia-total=\"personal\"]")).toBe("(4)");
    expect(text("[data-tablero-presencia-denominador]")).toBe("Base: 4 actas con la pregunta respondida (personal) y 5 (estudiantes), de 5. «No constatado» y «Sin dato» se cuentan aparte: no son cero.");
    const turnos = Array.from(document.querySelectorAll<HTMLElement>("[data-tablero-turnos] .insp-barra-relleno")).map((n) => n.style.width);
    expect(turnos).toEqual(["100%", "50%"]);
    expect(document.querySelector("[data-tablero-resultados] .insp-segmentos")?.getAttribute("aria-label")).toBe("3 Constatado, 1 Cerrada");
    expect(Array.from(document.querySelectorAll("[data-tablero-resultados-leyenda] li")).map((n) => n.textContent)).toEqual(["Constatado · 3", "Cerrada · 1"]);
    const filas = document.querySelectorAll("[data-tablero-ultimas] tr");
    expect(filas).toHaveLength(2);
    expect(within(filas[0] as HTMLElement).getByRole("link", { name: "ACTA-2026-000001" }).getAttribute("href")).toBe("/inspecciones/actas/ACTA-2026-000001/");
    expect(filas[0].querySelector(".insp-tablero-badge-nueva")).toBeNull();
    expect(filas[1].querySelector("a")).toBeNull();
    expect(filas[1].querySelector(".insp-tablero-badge-ok")?.textContent).toBe("Firmada");
    expect(screen.getByRole("link", { name: "Descargar actas completas" }).getAttribute("href")).toBe(`${API}descargar-actas/?fecha=2026-11-11&turno=tarde`);
  });

  it("polls every interval, reports a lost connection with the last good time and recovers", async () => {
    const calls = serve(shell(), [ok(), new Error("network"), ok({ indicadores: { ...datos().indicadores, actas_validas: 1501 } })]);
    await setup();
    expect(calls).toHaveLength(1);
    expect(state()).toBe("vivo");
    await advance(2000);
    expect(text("[data-tablero-hace]")).toBe("· actualizado hace 2 s");
    await advance(3000);
    expect(calls).toHaveLength(2);
    expect(state()).toBe("desconectado");
    expect(text("[data-tablero-estado]")).toBe("Sin conexión");
    const alerta = screen.getByRole("alert", { name: "" });
    expect(alerta.className).toBe("insp-aviso insp-aviso-rojo");
    expect(alerta.textContent).toMatch(/^Sin conexión con el servidor\. Los datos son de las \d\d:\d\d:\d\d \(última consulta correcta\)\. Se reintenta cada 5 s\.$/);
    // The figures of the last good read stay on screen.
    expect(text('[data-kpi="actas_validas"]')).toBe("1.500");
    await advance(5000);
    expect(calls).toHaveLength(3);
    expect(state()).toBe("vivo");
    expect(text('[data-kpi="actas_validas"]')).toBe("1.501");
    expect(document.querySelector("[data-tablero-desconexion]")?.className).toContain("d-none");
  });

  it("says nothing loaded yet when the first read fails and tells an expired session apart", async () => {
    serve(shell(), [new Error("network"), { data: { detail: "x" }, status: 401 }]);
    await setup();
    expect(text("[data-tablero-desconexion-texto]")).toBe("Todavía no se pudo cargar el tablero. Se reintenta cada 5 s.");
    await advance(5000);
    expect(text("[data-tablero-desconexion-texto]")).toBe("La sesión venció o ya no tiene permiso. Recargá la página para volver a ingresar.");
    expect(text("[data-tablero-ultimas]")).toBe("Cargando…");
  });

  it("treats a malformed or a 500 response as no connection, never as figures", async () => {
    serve(shell(), [{ data: { indicadores: {} }, status: 200 }, { data: datos(), status: 500 }]);
    await setup();
    expect(state()).toBe("desconectado");
    await advance(5000);
    expect(state()).toBe("desconectado");
    expect(text('[data-kpi="actas_validas"]')).toBe("–");
  });

  it("reads again with the chosen filters, keeps the locality only with a province and updates the links", async () => {
    const calls = serve(shell(), (url) => (url.includes("provincia=1")
      ? ok({ opciones: { localidades: [{ id: 9, nombre: "San Justo · La Matanza" }] } }) : ok()));
    await setup();
    fireEvent.change(document.getElementById("tablero-turno") as HTMLSelectElement, { target: { value: "tarde" } });
    expect(text("[data-tablero-estado]")).toBe("Actualizando…");
    await flush();
    expect(calls.at(-1)).toBe("web/inspecciones/tablero/datos/?fecha=2026-11-11&turno=tarde");
    expect(window.location.search).toBe("?fecha=2026-11-11&turno=tarde");
    expect(screen.getByRole("link", { name: "Exportar CSV (filtros aplicados)" }).getAttribute("href")).toBe(`${API}exportar.csv?fecha=2026-11-11&turno=tarde`);
    expect(screen.getByRole("link", { name: "Descargar actas completas" }).getAttribute("href")).toBe(`${API}descargar-actas/?fecha=2026-11-11&turno=tarde`);
    const localidad = document.getElementById("tablero-localidad") as HTMLSelectElement;
    expect(localidad.disabled).toBe(true);
    fireEvent.change(document.getElementById("tablero-provincia") as HTMLSelectElement, { target: { value: "1" } });
    await flush();
    expect(localidad.disabled).toBe(false);
    expect(Array.from(localidad.options).map((o) => o.text)).toEqual(["Localidad", "San Justo · La Matanza"]);
    fireEvent.change(localidad, { target: { value: "9" } });
    await flush();
    expect(calls.at(-1)).toBe("web/inspecciones/tablero/datos/?fecha=2026-11-11&provincia=1&localidad=9&turno=tarde");
    // The province changes: the locality is emptied before the next read.
    fireEvent.change(document.getElementById("tablero-provincia") as HTMLSelectElement, { target: { value: "2" } });
    await flush();
    expect(calls.at(-1)).toBe("web/inspecciones/tablero/datos/?fecha=2026-11-11&provincia=2&turno=tarde");
    fireEvent.change(document.getElementById("tablero-provincia") as HTMLSelectElement, { target: { value: "" } });
    await flush();
    expect(calls.at(-1)).toBe("web/inspecciones/tablero/datos/?fecha=2026-11-11&turno=tarde");
    expect((document.getElementById("tablero-localidad") as HTMLSelectElement).disabled).toBe(true);
  });

  it("keeps a chosen locality that no longer has actas as «Localidad elegida (sin actas)»", async () => {
    serve(shell({ filters: { fecha: "2026-11-11", provincia: "1", localidad: "55", inspector: "", turno: "", notificacion: "" } }), [ok()]);
    await setup("/inspecciones/tablero/?provincia=1&localidad=55");
    const localidad = document.getElementById("tablero-localidad") as HTMLSelectElement;
    expect(Array.from(localidad.options).map((o) => o.text)).toEqual(["Localidad", "San Justo · La Matanza", "Localidad elegida (sin actas)"]);
    expect(localidad.value).toBe("55");
  });

  it("pauses while the tab is hidden and reads again when it returns", async () => {
    const calls = serve(shell(), [ok()]);
    await setup();
    Object.defineProperty(document, "hidden", { configurable: true, get: () => true });
    act(() => { document.dispatchEvent(new Event("visibilitychange")); });
    expect(text("[data-tablero-estado]")).toBe("En pausa (pestaña oculta)");
    await advance(15000);
    expect(calls).toHaveLength(1);
    Object.defineProperty(document, "hidden", { configurable: true, get: () => false });
    act(() => { document.dispatchEvent(new Event("visibilitychange")); });
    expect(text("[data-tablero-estado]")).toBe("Actualizando…");
    await flush();
    expect(calls).toHaveLength(2);
    expect(state()).toBe("vivo");
  });

  it("marks an acta that arrives after the first read as new for eight seconds", async () => {
    serve(shell(), [ok(), ok({ ultimas: [acta(3), acta(1)] })]);
    await setup();
    expect(document.querySelector(".insp-tablero-badge-nueva")).toBeNull();
    await advance(5000);
    const nueva = document.querySelector("tr.insp-tablero-nueva");
    expect(nueva?.textContent).toContain("ACTA-2026-000003");
    expect(nueva?.querySelector(".insp-tablero-badge-nueva")?.textContent).toBe("nueva");
    expect(document.querySelectorAll(".insp-tablero-badge-nueva")).toHaveLength(1);
    await advance(8000);
    expect(document.querySelector(".insp-tablero-badge-nueva")).toBeNull();
  });

  it("flags more people present than expected and an empty list", async () => {
    serve(shell(), [ok({ ausentismo: { previsto: 10, presente: 12, computables: 1, colegios: 1, excluidas: 0, porcentaje: -20 }, ultimas: [], aulas: { previsto: 0, presente: 0, computables: 0, colegios: 0, excluidas: 2, porcentaje: null } })]);
    await setup();
    expect(document.querySelector('[data-indice="ausentismo-aviso-exceso"]')?.className).toBe("insp-aviso insp-aviso-ambar");
    expect(text("[data-indice=\"ausentismo-fraccion\"]")).toBe("12 / 10");
    expect(text("[data-indice=\"ausentismo-fraccion-etiqueta\"]")).toBe("presentes / previstos");
    expect(text("[data-indice=\"aulas-porcentaje\"]")).toBe("Sin datos computables");
    expect(text("[data-indice=\"aulas-descripcion\"]")).toBe("Aulas funcionando sobre las previstas · 0 colegios · 0 de 2 actas computables");
    expect(text("[data-tablero-ultimas]")).toBe("Sin actas con estos filtros.");
  });

  it("says so when the map libraries cannot be loaded", async () => {
    serve(shell(), [ok()]);
    await setup();
    const script = document.querySelector<HTMLScriptElement>('script[src*="leaflet@1.9.4"]');
    expect(script?.getAttribute("integrity")).toBe("sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=");
    expect(script?.getAttribute("crossorigin")).toBe("anonymous");
    await act(async () => { script?.dispatchEvent(new Event("error")); await vi.advanceTimersByTimeAsync(0); });
    expect(text("[data-tablero-mapa]")).toBe("No se pudo cargar el mapa.");
    expect(document.querySelector('link[href*="leaflet@1.9.4"]')?.getAttribute("integrity")).toBe("sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=");
  });

  it("draws the GPS points on the map, clusters by verification and renders popup text as text", async () => {
    const fitBounds = vi.fn();
    const addLayers = vi.fn();
    let options: Record<string, unknown> = {};
    const layer = { clearLayers: vi.fn(), addLayers, getBounds: vi.fn(() => "bounds") };
    const map = {
      attributionControl: { setPrefix: vi.fn() }, fitBounds, setMinZoom: vi.fn(), getZoom: vi.fn(() => 5), addLayer: vi.fn(), on: vi.fn(), remove: vi.fn(),
      scrollWheelZoom: { enable: vi.fn(), disable: vi.fn() },
    };
    const markers: { options: Record<string, unknown>; popup?: () => HTMLElement }[] = [];
    (window as unknown as { L: unknown }).L = {
      latLngBounds: () => ({ pad: () => "limits" }), map: vi.fn(() => map), tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
      markerClusterGroup: vi.fn((o: Record<string, unknown>) => { options = o; return layer; }),
      circleMarker: vi.fn((_latlng: number[], o: Record<string, unknown>) => { const m: (typeof markers)[number] = { options: o }; markers.push(m); return Object.assign(m, { bindPopup: (f: () => HTMLElement) => { m.popup = f; } }); }),
      divIcon: vi.fn((o: unknown) => o), point: vi.fn((x: number, y: number) => [x, y]),
    };
    const punto = (n: number, constatada: boolean, extra: Record<string, unknown> = {}) => ({ numero: `ACTA-2026-00000${n}`, url: `/inspecciones/actas/ACTA-2026-00000${n}/`, escuela: `Escuela ${n}`, cueanexo: "060123400", turno: "Tarde", inspector: "Ines Aguirre", resultado: "Constatado", lat: -34.6, lng: -58.5, constatada, ...extra });
    const puntos = [punto(1, true), punto(2, false, { escuela: "<img src=x onerror=alert(1)>", url: null })];
    const calls = serve(shell(), () => ok({ mapa: { puntos: [...puntos], con_gps: 2, sin_coordenadas: 0, manual: 0, sin_ubicacion: 0 } }));
    await setup();
    expect(calls).toHaveLength(1);
    expect(fitBounds).toHaveBeenCalledWith([[-55.1, -73.6], [-21.7, -53.6]]);
    expect(addLayers).toHaveBeenCalledTimes(1);
    expect(markers.map((m) => [m.options.fillColor, m.options.constatada])).toEqual([["#3b8681", true], ["#c26a00", false]]);
    expect(text("[data-tablero-sin-gps]")).toBe("Todas las actas tienen ubicación GPS");
    const popup = markers[1].popup?.() as HTMLElement;
    expect(popup.querySelector("strong")?.textContent).toBe("<img src=x onerror=alert(1)>");
    expect(popup.querySelector("img")).toBeNull();
    expect(Array.from(popup.querySelectorAll("dt")).map((n) => n.textContent)).toEqual(["Cueanexo", "Turno", "Inspector", "Acta", "Resultado"]);
    expect(popup.querySelector("span.insp-tablero-numero")?.textContent).toBe("ACTA-2026-000002");
    expect((markers[0].popup?.() as HTMLElement).querySelector("a")?.getAttribute("href")).toBe("/inspecciones/actas/ACTA-2026-000001/");
    const icon = (verified: boolean[]) => (options.iconCreateFunction as (g: unknown) => { className: string; iconSize: number[] })({ getAllChildMarkers: () => verified.map((constatada) => ({ options: { constatada } })) });
    expect(icon([true, true]).className).toBe("insp-tablero-grupo");
    expect(icon([true, false]).className).toBe("insp-tablero-grupo insp-tablero-grupo-mixto");
    expect(icon([false]).className).toBe("insp-tablero-grupo insp-tablero-grupo-sin-constatacion");
    expect(icon(Array(120).fill(true)).iconSize).toEqual([48, 48]);
    // Filtering by territory fits the map to the points of the answer.
    fireEvent.change(document.getElementById("tablero-provincia") as HTMLSelectElement, { target: { value: "1" } });
    await flush();
    expect(fitBounds).toHaveBeenLastCalledWith("bounds", { padding: [30, 30], maxZoom: 13 });
    // The refit waits for the new answer: a poll without a change of filters does not move the map.
    const fits = fitBounds.mock.calls.length;
    await advance(5000);
    expect(fitBounds.mock.calls.length).toBe(fits);
    delete (window as unknown as { L?: unknown }).L;
  });

  it("shows the queued messages of the shell (a download with nothing to download) as toasts", async () => {
    serve(shell({ messages: [{ message: "No hay actas completas para descargar con estos filtros.", level: "warning" }] }), [ok()]);
    await setup();
    expect(screen.getByText("No hay actas completas para descargar con estos filtros.").closest(".toast")?.className).toBe("toast toast-warning");
  });

  it("sends a 403 of the shell to the access screen", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: session, status: 200 } : { data: { detail: "x" }, status: 403 }));
    await setup();
    expect(document.querySelector("[data-tablero-vivo]")).toBeNull();
    expect(document.querySelector("#insp-tablero")).toBeNull();
  });
});
