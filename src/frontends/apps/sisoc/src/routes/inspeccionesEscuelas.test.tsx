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
  breadcrumb: last ? [{ text: "Inicio", url: "/inicio/" }, { text: "Inspecciones escolares", url: "/inspecciones/" }, { text: last, url: null }]
    : [{ text: "Inicio", url: "/inicio/" }, { text: "Inspecciones escolares", url: null }],
  display_name: "Gestora Sintética", role: "Coordinación sintética", initials: "GS",
});
const tabs = [
  { id: "tablero", label: "Tablero", url: "/inspecciones/tablero/" },
  { id: "escuelas", label: "Escuelas", url: "/inspecciones/" },
  { id: "asignaciones", label: "Asignaciones", url: "/inspecciones/asignaciones/" },
  { id: "actas", label: "Actas", url: "/inspecciones/actas/" },
];
const totales = { escuelas: 2, escuelas_a_revisar: 1, jornada: "11/11", asignaciones_hoy: 0, actas_hoy: 3 };
const options = { provincias: [{ id: 1, nombre: "Buenos Aires" }, { id: 2, nombre: "Córdoba" }], localidades_url: `${API}localidades/` };
const row = (id: number, extra: Record<string, unknown> = {}) => ({
  id, cueanexo: "060123400", nombre: "EP 12", provincia: "Buenos Aires",
  localidad: { vinculada: true, texto: "San Justo", distrito: "La Matanza", aviso: "" },
  domicilio: "Av. Perón 3245", cp: "B1754ABC", telefono: "—", mail: "—", mail_invalido: false, form_url: `${API}escuelas/${id}/editar/`, ...extra,
});
const panel = (over: Record<string, unknown> = {}) => ({
  layout: layout(null), tabs, totales,
  filters: { q: "", provincia: "", localidad: null }, options,
  a_revisar: { activo: false, contador: 1, url: "?a_revisar=1" },
  results: [row(4), row(5, { localidad: { vinculada: false, texto: "San Jose", distrito: "", aviso: "localidad repetida" }, mail: "roto@", mail_invalido: true })],
  page: { number: 1, count: 2, start_index: 1, end_index: 2, has_other_pages: false, previous: null, next: null, range: [1], query_without_page: "" },
  urls: { nueva: `${API}escuelas/nueva/`, importar: "/inspecciones/escuelas/importar/" }, editar_url: null, messages: [],
  ...over,
});
const field = (value = "", errors: string[] = []) => ({ value, errors });
const form = (over: Record<string, unknown> = {}) => ({
  layout: layout("Nueva escuela"), tabs, totales, editar: false, aviso: null, non_field_errors: [],
  fields: { provincia: field(), localidad: field(), cueanexo: field(), cp: field(), nombre: field(), domicilio: field(), telefono: field(), mail: field() },
  localidad_inicial: null, duplicada_url: null, options, messages: [], ...over,
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

describe("Inspecciones escuelas routes", () => {
  it("owns the native panel and form paths only", () => {
    expect(findRoute("/inspecciones/")?.params).toEqual({ form: "panel", pk: null });
    expect(findRoute("/inspecciones/escuelas/nueva/")?.params).toEqual({ form: "nueva", pk: null });
    expect(findRoute("/inspecciones/escuelas/7/editar/")?.params).toEqual({ form: "editar", pk: 7 });
    expect(findRoute("/inspecciones")?.route.name).not.toBe("inspecciones-escuelas");
    expect(findRoute("/inspecciones/escuelas/0/editar/")?.route.name).not.toBe("inspecciones-escuelas");
    expect(findRoute("/inspecciones/actas/")?.route.name).toBe("inspecciones-actas");
  });

  it("renders the panel from the API with the native query", async () => {
    serve({ "web/inspecciones/escuelas/": panel() });
    setup("/inspecciones/?q=EP");
    expect(await screen.findByText("Escuelas en el catálogo")).toBeTruthy();
    expect(webGet.mock.calls.map(([url]) => url)).toEqual(["web/session/", "web/inspecciones/escuelas/?q=EP"]);
    await waitFor(() => expect(document.title).toBe("SISOC - Inspecciones escolares"));
    expect(screen.getByText("Escuelas con datos a revisar").parentElement?.className).toBe("insp-kpi insp-kpi-alerta");
    expect(screen.getByText("Asignaciones de hoy (11/11)")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Escuelas" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByText("La Matanza").className).toBe("insp-detalle");
    expect(screen.getByText("localidad repetida").className).toBe("insp-badge insp-badge-alerta");
    expect(screen.getByText("mail inválido")).toBeTruthy();
    expect(screen.getByRole("link", { name: /A revisar · 1/ }).getAttribute("href")).toBe("?a_revisar=1");
    const localidad = document.getElementById("filtro-localidad") as HTMLSelectElement;
    expect(localidad.disabled).toBe(true);
    expect(screen.getByText("Elegí provincia")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Editar EP 12" })).toHaveLength(2);
  });

  it("empties and enables the locality before the province auto-submits", async () => {
    serve({ "web/inspecciones/escuelas/": panel({ filters: { q: "", provincia: "1", localidad: { id: 9, text: "San Justo · La Matanza" } } }) });
    setup("/inspecciones/?provincia=1&localidad=9");
    await waitFor(() => expect(document.getElementById("select2-filtro-localidad-container")?.textContent).toBe("San Justo · La Matanza"));
    const formulario = document.querySelector("form.insp-filtros") as HTMLFormElement;
    const seen: Record<string, string>[] = [];
    formulario.requestSubmit = () => { seen.push(Object.fromEntries(new FormData(formulario) as unknown as Iterable<[string, string]>)); };
    // The auto-submit listener is attached in a passive effect: re-send until it listens.
    await waitFor(() => {
      fireEvent.change(document.getElementById("filtro-provincia") as HTMLSelectElement, { target: { value: "" } });
      expect(seen.length).toBeGreaterThan(0);
    });
    expect(seen).toEqual([{ q: "", provincia: "" }]);
    fireEvent.change(document.getElementById("filtro-provincia") as HTMLSelectElement, { target: { value: "2" } });
    expect(seen[1]).toEqual({ q: "", provincia: "2", localidad: "" });
  });

  it("opens the school modal, posts with X-Requested-With and reloads after saving", async () => {
    serve({ "web/inspecciones/escuelas/nueva/": form(), "web/inspecciones/escuelas/": panel() });
    webPost.mockResolvedValue({ data: { ok: true, mensaje: "Se agregó la escuela EP 1 (060123499).", otra: false }, status: 200 });
    setup("/inspecciones/");
    fireEvent.click(await screen.findByRole("button", { name: "Nueva escuela" }));
    const dialog = await screen.findByRole("dialog");
    await waitFor(() => expect(document.activeElement?.id).toBe("id_provincia"));
    await waitFor(() => expect(document.body.classList.contains("modal-open")).toBe(true));
    expect(webGet).toHaveBeenCalledWith("web/inspecciones/escuelas/nueva/", expect.objectContaining({ headers: { "X-Requested-With": "XMLHttpRequest" } }));
    fireEvent.change(within(dialog).getByLabelText(/Nombre/), { target: { value: "EP 1" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Guardar escuela" }));
    await waitFor(() => expect(escuelasNavigation.reload).toHaveBeenCalled());
    const [url, body, config] = webPost.mock.calls[0];
    expect(url).toBe("web/inspecciones/escuelas/nueva/");
    expect((body as URLSearchParams).get("nombre")).toBe("EP 1");
    expect((body as URLSearchParams).has("otra")).toBe(false);
    expect(config.headers).toEqual({ "X-Requested-With": "XMLHttpRequest" });
  });

  it("shows errors and the duplicate link, then «otra» reloads an empty form with the notice", async () => {
    serve({ "web/inspecciones/escuelas/nueva/": form(), "web/inspecciones/escuelas/": panel() });
    webPost.mockResolvedValueOnce({ data: form({ fields: { ...form().fields, cueanexo: field("060123400", ["Ya existe: EP 12 (San Justo)."]) }, duplicada_url: "/inspecciones/?editar=4" }), status: 400 });
    webPost.mockResolvedValueOnce({ data: { ok: true, mensaje: "Se agregó la escuela EP 1 (060123499).", otra: true }, status: 200 });
    setup("/inspecciones/");
    fireEvent.click(await screen.findByRole("button", { name: "Nueva escuela" }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByLabelText(/Cueanexo/);
    fireEvent.click(within(dialog).getByRole("button", { name: "Guardar y cargar otra" }));
    const error = await within(dialog).findByText("Ya existe: EP 12 (San Justo).");
    expect(error.className).toBe("invalid-feedback d-block");
    expect(within(error).getByRole("link", { name: "Abrir para editar" }).getAttribute("href")).toBe("/inspecciones/?editar=4");
    expect((within(dialog).getByLabelText(/Cueanexo/) as HTMLInputElement).getAttribute("aria-invalid")).toBe("true");
    fireEvent.click(within(dialog).getByRole("button", { name: "Guardar y cargar otra" }));
    expect(await within(dialog).findByText("Se agregó la escuela EP 1 (060123499).")).toBeTruthy();
    expect((webPost.mock.calls[1][1] as URLSearchParams).get("otra")).toBe("1");
    expect(escuelasNavigation.reload).not.toHaveBeenCalled();
  });

  it("opens the edit modal from ?editar and closes it with Escape", async () => {
    serve({ "web/inspecciones/escuelas/4/editar/": form({ editar: true, aviso: { motivos: "Localidad repetida", localidad_original: "San Jose" } }), "web/inspecciones/escuelas/": panel({ editar_url: `${API}escuelas/4/editar/` }) });
    setup("/inspecciones/?editar=4");
    const dialog = await screen.findByRole("dialog");
    const aviso = await within(dialog).findByRole("status");
    await waitFor(() => expect(document.body.className).toMatch(/modal-open app-loaded$/));
    expect(aviso.textContent).toBe("Datos a revisar: Localidad repetida. Localidad del archivo: San Jose. Al guardar con una localidad de la lista y un mail válido se quita la marca.");
    expect(within(dialog).queryByRole("button", { name: "Guardar y cargar otra" })).toBeNull();
    fireEvent.keyDown(document.activeElement as HTMLElement, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(document.body.classList.contains("modal-open")).toBe(false));
  });

  it("posts the page form without X-Requested-With and follows the native redirect", async () => {
    serve({ "web/inspecciones/escuelas/nueva/": form({ messages: [{ message: "Se agregó la escuela EP 1 (060123499).", level: "success" }] }) });
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/inspecciones/?q=060123498" }, status: 200 });
    setup("/inspecciones/escuelas/nueva/");
    expect(await screen.findByText("Se agregó la escuela EP 1 (060123499).")).toBeTruthy();
    expect(document.querySelector(".insp-dialogo form")).toBeTruthy();
    expect(webGet.mock.calls[1]).toEqual(["web/inspecciones/escuelas/nueva/", expect.not.objectContaining({ headers: expect.anything() })]);
    fireEvent.click(screen.getByRole("button", { name: "Guardar escuela" }));
    await waitFor(() => expect(escuelasNavigation.assign).toHaveBeenCalledWith("/inspecciones/?q=060123498"));
    expect(webPost.mock.calls[0][2].headers).toEqual({});
  });

  it("opens the import modal as a native multipart form", async () => {
    serve({ "web/inspecciones/escuelas/": panel() });
    setup("/inspecciones/");
    const trigger = await screen.findByRole("button", { name: "Importar Excel/CSV" });
    fireEvent.click(trigger);
    const dialog = await screen.findByRole("dialog", { name: "Importar escuelas" });
    const formulario = dialog.querySelector("form") as HTMLFormElement;
    expect([formulario.method, formulario.enctype, formulario.getAttribute("action")]).toEqual(["post", "multipart/form-data", "/inspecciones/escuelas/importar/"]);
    await waitFor(() => expect(document.activeElement).toBe(dialog));
    fireEvent.keyDown(dialog, { key: "Escape" });
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });
});
