import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { escuelasNavigation } from "./inspeccionesEscuelasNavigation";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "/api/web/inspecciones/";
const session = { ...readyContext, navigation: [{ id: "inicio", label: "Inicio", href: "/inicio/", children: [] }] };
const layout = (last: string | null) => ({
  breadcrumb: [{ text: "Inicio", url: "/inicio/" }, { text: "Inspecciones escolares", url: "/inspecciones/" }, { text: last ?? "Asignaciones", url: null }],
  display_name: "Gestora Sintética", role: "Coordinación sintética", initials: "GS",
});
const tabs = [
  { id: "tablero", label: "Tablero", url: "/inspecciones/tablero/" },
  { id: "escuelas", label: "Escuelas", url: "/inspecciones/" },
  { id: "asignaciones", label: "Asignaciones", url: "/inspecciones/asignaciones/" },
  { id: "actas", label: "Actas", url: "/inspecciones/actas/" },
];
const row = (id: number, extra: Record<string, unknown> = {}) => ({
  id, iniciales: "IA", inspector: { nombre: "Ines Aguirre", usuario: "iaguirre" },
  escuela: { nombre: "EP 12", cueanexo: "060123400", localidad: "San Justo", provincia: "Buenos Aires" },
  estado: "pendiente", estado_display: "Pendiente", actas: [], se_puede_quitar: true, quitar_url: `${API}asignaciones/${id}/quitar/`, ...extra,
});
const conActa = row(2, {
  estado: "finalizada", estado_display: "Finalizada", se_puede_quitar: false,
  actas: [{ numero: "ACTA-2026-000001", url: "/inspecciones/actas/ACTA-2026-000001/", anulada: true, prueba: true }],
});
const list = (over: Record<string, unknown> = {}) => ({
  layout: layout(null), tabs,
  filters: { fecha: "2026-11-11", inspector: null, escuela: null, provincia: "", estado: "", estado_acta: "" },
  day: { es_hoy: true, anterior: "/inspecciones/asignaciones/?fecha=2026-11-10", siguiente: "/inspecciones/asignaciones/?fecha=2026-11-12", hoy: "/inspecciones/asignaciones/?fecha=2026-11-11" },
  options: {
    provincias: [{ id: 1, nombre: "Buenos Aires" }],
    estados: [{ value: "", label: "Todos los estados" }, { value: "pendiente", label: "Pendiente" }],
    estados_acta: [{ value: "", label: "Todas las actas" }, { value: "validas", label: "Válidas" }],
    inspectores_url: `${API}inspectores/?alcance=programa`, escuelas_url: `${API}escuelas/buscar/`,
  },
  totales: { total: 7, pendiente: 4, en_curso: 1, finalizada: 2, inspectores: 3 },
  results: [row(1), conActa],
  page: { number: 1, count: 2, start_index: 1, end_index: 2, has_other_pages: false, previous: null, next: null, range: [1], query_without_page: "" },
  urls: { nueva: `${API}asignaciones/nueva/?fecha=2026-11-11`, importar: "/inspecciones/asignaciones/importar/" }, messages: [],
  ...over,
});
const field = (value = "", errors: string[] = []) => ({ value, errors });
const form = (over: Record<string, unknown> = {}) => ({
  layout: layout("Nueva asignación"), tabs, non_field_errors: [],
  fields: { fecha: field("2026-11-11"), inspector: field(), escuela: field() },
  inspector_inicial: null, escuela_inicial: null,
  options: { inspectores_url: `${API}inspectores/`, escuelas_url: `${API}escuelas/buscar/`, verificar_url: `${API}asignaciones/verificar/` },
  messages: [], ...over,
});

function serve(routes: Record<string, unknown>) {
  webGet.mockImplementation((url: string) => {
    if (url === "web/session/") return Promise.resolve({ data: session, status: 200 });
    const key = Object.keys(routes).find((k) => url.startsWith(k));
    return Promise.resolve(key ? { data: routes[key], status: 200 } : { data: {}, status: 404 });
  });
}

function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "";
  document.body.removeAttribute("style");
  setViewport(false);
  vi.spyOn(escuelasNavigation, "assign").mockImplementation(() => undefined);
  vi.spyOn(escuelasNavigation, "reload").mockImplementation(() => undefined);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("Inspecciones asignaciones routes", () => {
  it("owns the native list and form paths only", () => {
    expect(findRoute("/inspecciones/asignaciones/")?.params).toEqual({ form: false });
    expect(findRoute("/inspecciones/asignaciones/nueva/")?.params).toEqual({ form: true });
    expect(findRoute("/inspecciones/asignaciones/importar/")?.route.name).not.toBe("inspecciones-asignaciones");
    expect(findRoute("/inspecciones/asignaciones/5/quitar/")?.route.name).not.toBe("inspecciones-asignaciones");
  });

  it("renders the day from the API with the server totals and the native query", async () => {
    serve({ "web/inspecciones/asignaciones/": list() });
    setup("/inspecciones/asignaciones/?estado=pendiente&fecha=2026-11-11");
    expect(await screen.findByText("Asignaciones de la jornada")).toBeTruthy();
    expect(webGet.mock.calls.map(([url]) => url)).toEqual(["web/session/", "web/inspecciones/asignaciones/?estado=pendiente&fecha=2026-11-11"]);
    // Totals are the server's (7), not the two rows on the page.
    expect(screen.getByText("Asignaciones de la jornada").nextElementSibling?.textContent).toBe("7");
    expect(screen.getByText("Pendientes").nextElementSibling?.textContent).toBe("4");
    expect(screen.getByText("En curso (borrador)").nextElementSibling?.textContent).toBe("1");
    expect(screen.getByText("Finalizadas").getAttribute("title")).toBe("Sin actas anuladas ni de prueba");
    expect(screen.getByRole("link", { name: "Asignaciones" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByText("Mostrando 1–2 de 2 · 3 inspectores")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Día anterior" }).getAttribute("href")).toBe("/inspecciones/asignaciones/?fecha=2026-11-10");
    expect(screen.getByRole("link", { name: "Hoy" }).className).toBe("btn btn-outline-secondary disabled");
    expect((document.getElementById("filtro-fecha") as HTMLInputElement).value).toBe("2026-11-11");
    expect(screen.getByText("Pendiente", { selector: "span.insp-badge" }).className).toBe("insp-badge insp-badge-alerta");
    expect(screen.getByText("Anulada").className).toBe("insp-badge insp-badge-error");
    expect(screen.getByText("Prueba").className).toBe("insp-badge insp-badge-neutro");
    expect(screen.getByRole("link", { name: "ACTA-2026-000001" }).getAttribute("href")).toBe("/inspecciones/actas/ACTA-2026-000001/");
    expect(screen.getAllByText("No se puede quitar: ya tiene acta")).toHaveLength(1);
    expect(document.querySelector(".insp-boton-icono.deshabilitado")?.getAttribute("title")).toBe("No se puede quitar: ya tiene acta");
    expect(screen.getAllByRole("button", { name: /Quitar asignación de EP 12/ })).toHaveLength(1);
  });

  it("shows the empty state of the day and no footer", async () => {
    serve({ "web/inspecciones/asignaciones/": list({ results: [], page: { number: 1, count: 0, start_index: 0, end_index: 0, has_other_pages: false, previous: null, next: null, range: [], query_without_page: "" } }) });
    setup("/inspecciones/asignaciones/");
    expect(await screen.findByText("No hay asignaciones")).toBeTruthy();
    expect(screen.getByText(/No hay asignaciones para esta jornada con los filtros elegidos\./)).toBeTruthy();
    expect(document.querySelector(".insp-seccion-pie")).toBeNull();
  });

  it("auto-submits the filters on change like panel.js", async () => {
    serve({ "web/inspecciones/asignaciones/": list() });
    setup("/inspecciones/asignaciones/");
    await screen.findByText("Asignaciones de la jornada");
    const formulario = document.querySelector("form.insp-filtros") as HTMLFormElement;
    const seen: Record<string, string>[] = [];
    formulario.requestSubmit = () => { seen.push(Object.fromEntries(new FormData(formulario) as unknown as Iterable<[string, string]>)); };
    await waitFor(() => {
      fireEvent.change(document.getElementById("filtro-estado") as HTMLSelectElement, { target: { value: "pendiente" } });
      expect(seen.length).toBeGreaterThan(0);
    });
    expect(seen[0]).toEqual({ fecha: "2026-11-11", inspector: "", escuela: "", provincia: "", estado: "pendiente", estado_acta: "" });
  });

  it("opens the assignment modal, posts with X-Requested-With and reloads after saving", async () => {
    serve({ "web/inspecciones/asignaciones/nueva/": form({ inspector_inicial: { id: 3, text: "Ines Aguirre" }, escuela_inicial: { id: 4, text: "EP 12" } }), "web/inspecciones/asignaciones/verificar/": { otras: [] }, "web/inspecciones/asignaciones/": list() });
    webPost.mockResolvedValue({ data: { ok: true, mensaje: "Se asignó EP 12 a Ines Aguirre para el 11/11/2026.", otra: false }, status: 200 });
    setup("/inspecciones/asignaciones/");
    fireEvent.click(await screen.findByRole("button", { name: "Nueva asignación" }));
    const dialog = await screen.findByRole("dialog");
    await waitFor(() => expect(document.activeElement?.id).toBe("id_fecha"));
    expect(webGet).toHaveBeenCalledWith("web/inspecciones/asignaciones/nueva/?fecha=2026-11-11", expect.objectContaining({ headers: { "X-Requested-With": "XMLHttpRequest" } }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Asignar" }));
    await waitFor(() => expect(escuelasNavigation.reload).toHaveBeenCalled());
    const [url, body, config] = webPost.mock.calls[0];
    expect(url).toBe("web/inspecciones/asignaciones/nueva/");
    const sent = body as URLSearchParams;
    expect([sent.get("fecha"), sent.get("inspector"), sent.get("escuela"), sent.has("otra")]).toEqual(["2026-11-11", "3", "4", false]);
    expect(config.headers).toEqual({ "X-Requested-With": "XMLHttpRequest" });
  });

  it("shows the native errors, keeps the values and «otra» reloads the form keeping the day", async () => {
    serve({ "web/inspecciones/asignaciones/nueva/": form(), "web/inspecciones/asignaciones/verificar/": { otras: [] }, "web/inspecciones/asignaciones/": list() });
    webPost.mockResolvedValueOnce({ data: form({ non_field_errors: ["Esa escuela ya está asignada a ese inspector en esa jornada."], fields: { fecha: field("2026-11-15"), inspector: field("3"), escuela: field("4", ["Elegí una escuela de la lista."]) }, inspector_inicial: { id: 3, text: "Ines Aguirre" } }), status: 400 });
    webPost.mockResolvedValueOnce({ data: { ok: true, mensaje: "Se asignó EP 12 a Ines Aguirre para el 15/11/2026.", otra: true }, status: 200 });
    setup("/inspecciones/asignaciones/");
    fireEvent.click(await screen.findByRole("button", { name: "Nueva asignación" }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByLabelText(/Jornada/);
    fireEvent.click(within(dialog).getByRole("button", { name: "Asignar y cargar otra" }));
    expect((await within(dialog).findByText("Esa escuela ya está asignada a ese inspector en esa jornada.")).className).toBe("alert alert-danger");
    expect((within(dialog).getByText("Elegí una escuela de la lista.")).className).toBe("invalid-feedback d-block");
    expect((within(dialog).getByLabelText(/Jornada/) as HTMLInputElement).value).toBe("2026-11-15");
    expect(document.getElementById("select2-id_inspector-container")?.textContent).toBe("Ines Aguirre");
    fireEvent.click(within(dialog).getByRole("button", { name: "Asignar y cargar otra" }));
    expect(await within(dialog).findByText("Se asignó EP 12 a Ines Aguirre para el 15/11/2026.")).toBeTruthy();
    expect((webPost.mock.calls[1][1] as URLSearchParams).get("otra")).toBe("1");
    // The next form is loaded at the saved day (`panel.js` otraConFecha).
    const loads = webGet.mock.calls.map(([url]) => url).filter((url: string) => url.startsWith("web/inspecciones/asignaciones/nueva/"));
    expect(loads.at(-1)).toBe("web/inspecciones/asignaciones/nueva/?fecha=2026-11-15");
    expect(escuelasNavigation.reload).not.toHaveBeenCalled();
  });

  it("asks the server about another visit and shows its notice", async () => {
    serve({
      "web/inspecciones/asignaciones/nueva/": form({ fields: { fecha: field("2026-11-11"), inspector: field("3"), escuela: field("4") }, inspector_inicial: { id: 3, text: "Ines Aguirre" }, escuela_inicial: { id: 4, text: "EP 12" } }),
      "web/inspecciones/asignaciones/verificar/": { escuela: "EP 12", otras: ["Juan Perez", "Ana Gomez"] },
    });
    setup("/inspecciones/asignaciones/nueva/");
    const aviso = await screen.findByText("EP 12 ya está asignada en esta jornada a Juan Perez, Ana Gomez. Podés asignarla igual: cuenta como otra visita y no reemplaza la anterior.");
    expect(aviso.className).toBe("insp-aviso insp-aviso-ambar");
    expect(aviso.getAttribute("role")).toBe("status");
    expect(webGet).toHaveBeenCalledWith("web/inspecciones/asignaciones/verificar/?fecha=2026-11-11&inspector=3&escuela=4");
  });

  it("posts the page form without X-Requested-With and follows the native redirect", async () => {
    serve({ "web/inspecciones/asignaciones/nueva/": form({ messages: [{ message: "Se asignó EP 12 a Ines Aguirre para el 10/11/2026.", level: "success" }] }), "web/inspecciones/asignaciones/verificar/": { otras: [] } });
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/inspecciones/asignaciones/?fecha=2026-11-11" }, status: 200 });
    setup("/inspecciones/asignaciones/nueva/?fecha=2026-11-11");
    expect(await screen.findByText("Se asignó EP 12 a Ines Aguirre para el 10/11/2026.")).toBeTruthy();
    expect(document.querySelector(".insp-dialogo form")).toBeTruthy();
    expect(webGet.mock.calls[1]).toEqual(["web/inspecciones/asignaciones/nueva/?fecha=2026-11-11", expect.not.objectContaining({ headers: expect.anything() })]);
    fireEvent.click(screen.getByRole("button", { name: "Asignar" }));
    await waitFor(() => expect(escuelasNavigation.assign).toHaveBeenCalledWith("/inspecciones/asignaciones/?fecha=2026-11-11"));
    expect(webPost.mock.calls[0][0]).toBe("web/inspecciones/asignaciones/nueva/");
    expect(webPost.mock.calls[0][2].headers).toEqual({});
  });

  it("removes an assignment only after confirming and returns to the day", async () => {
    serve({ "web/inspecciones/asignaciones/": list() });
    const confirmar = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/inspecciones/asignaciones/?fecha=2026-11-11" }, status: 200 });
    setup("/inspecciones/asignaciones/");
    const boton = await screen.findByRole("button", { name: "Quitar asignación de EP 12" });
    fireEvent.click(boton);
    expect(confirmar).toHaveBeenLastCalledWith("¿Quitar la asignación de EP 12 a Ines Aguirre?");
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.click(boton);
    await waitFor(() => expect(escuelasNavigation.assign).toHaveBeenCalledWith("/inspecciones/asignaciones/?fecha=2026-11-11"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/inspecciones/asignaciones/1/quitar/");
  });

  it("reports a lost removal response without retrying it", async () => {
    serve({ "web/inspecciones/asignaciones/": list() });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    webPost.mockRejectedValue(new Error("network"));
    setup("/inspecciones/asignaciones/");
    fireEvent.click(await screen.findByRole("button", { name: "Quitar asignación de EP 12" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByText(/No se pudo confirmar el resultado\./)).toBeTruthy();
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(escuelasNavigation.assign).not.toHaveBeenCalled();
  });

  it("opens the import modal for asignaciones as a native multipart form", async () => {
    serve({ "web/inspecciones/asignaciones/": list() });
    setup("/inspecciones/asignaciones/");
    fireEvent.click(await screen.findByRole("button", { name: "Importar Excel/CSV" }));
    const dialog = await screen.findByRole("dialog", { name: "Importar asignaciones" });
    const formulario = dialog.querySelector("form") as HTMLFormElement;
    expect([formulario.method, formulario.enctype, formulario.getAttribute("action")]).toEqual(["post", "multipart/form-data", "/inspecciones/asignaciones/importar/"]);
    expect(within(dialog).getByLabelText("Archivo Excel (.xlsx) o CSV").id).toBe("id_archivo_asignaciones");
    expect(within(dialog).getByText("fecha").tagName).toBe("STRONG");
  });

  it("sends a 403 of the API to the access screen", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: session, status: 200 } : { data: { detail: "x" }, status: 403 }));
    setup("/inspecciones/asignaciones/");
    await waitFor(() => expect(screen.queryByText("Cargando asignaciones…")).toBeNull());
    expect(screen.queryByText("Asignaciones de la jornada")).toBeNull();
  });
});
