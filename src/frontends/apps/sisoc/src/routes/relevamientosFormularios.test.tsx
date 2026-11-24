import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { actaFormValid, seguimientoFormValid } from "./relevamientosForms";
import { relevamientosNavigation, takeFlash } from "./relevamientosApi";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const EDITAR = "/comedores/7/relevamiento/12/seguimiento/3/editar";
const DETALLE = "/comedores/7/relevamiento/12/seguimiento/3/";
const API_SEG = "web/comedores/relevamientos/7/relevamiento/12/seguimientos/3/editar/";

type N = string | { t: string; a: Record<string, string>; c: N[] };
const el = (t: string, a: Record<string, string>, ...c: N[]): N => ({ t, a, c });
const input = (name: string, value: string, type = "text") => el("input", { type, name, id: `id_${name}`, class: "form-control", value });
const select = (name: string, options: [string, string][], selected: string) =>
  el("select", { name, id: `id_${name}`, class: "form-select" }, ...options.map(([v, l]) => el("option", v === selected ? { value: v, selected: "" } : { value: v }, l)));
const field = (name: string, label: string, nodes: N[], extra: Record<string, unknown> = {}) => ({ name, label, id: `id_${name}`, hidden: false, help_text: "", errors: [] as string[], nodes, ...extra });
const hidden = (name: string, value: string) => field(name, "", [el("input", { type: "hidden", name, id: `id_${name}`, value })], { hidden: true });
const management = (total: number, initial: number) => [hidden("prestaciones-TOTAL_FORMS", String(total)), hidden("prestaciones-INITIAL_FORMS", String(initial)), hidden("prestaciones-MIN_NUM_FORMS", "0"), hidden("prestaciones-MAX_NUM_FORMS", "1000")];
const seguimientoForm = (over: Record<string, unknown> = {}) => ({
  seguimiento: { id: 3, tipo_display: "Primer seguimiento", numero_orden: 1 }, relevamiento: { id: 12, fecha_visita: "Sin información" }, comedor: { id: 7, nombre: "Comedor <Uno>" },
  root: { fields: [
    field("seg-fecha_hora", "Fecha hora", [input("seg-fecha_hora", "2026-03-04T12:07", "datetime-local")]),
    field("seg-estado", "Estado", [select("seg-estado", [["Asignado", "Asignado"], ["Completo", "Completo"]], "Completo")]),
    field("seg-tecnico", "Tecnico", [input("seg-tecnico", "Téc <1>")], { help_text: "Quién cargó" }),
  ], non_field_errors: [] },
  bloques: [
    { key: "funcionamiento", label: "Funcionamiento", existe: true, form: { fields: [field("funcionamiento-funcionamiento", "Funcionamiento", [input("funcionamiento-funcionamiento", "Cerrado")]),
      field("funcionamiento-abierto", "Abierto", [el("input", { type: "checkbox", name: "funcionamiento-abierto", id: "id_ab", value: "on", checked: "" })]),
      field("funcionamiento-notas", "Notas", [el("textarea", { name: "funcionamiento-notas", id: "id_notas", rows: "4" }, "línea 1\nlínea 2")])], non_field_errors: [] } },
    { key: "menu", label: "Menú", existe: false, form: { fields: [field("menu-cambios", "Cambios", [select("menu-cambios", [["unknown", "Desconocido"], ["true", "Sí"], ["false", "No"]], "unknown")])], non_field_errors: [] } },
  ],
  prestaciones: { management: management(2, 1), forms: [
    { hidden: [hidden("prestaciones-0-id", "4")], fields: ["dias_prestacion", "tipo_prestacion", "ap_presencial", "ap_vianda", "ap_total", "de_presencial", "de_vianda", "DELETE"].map((n) =>
      field(`prestaciones-0-${n}`, n, [n === "DELETE" ? el("input", { type: "checkbox", name: `prestaciones-0-${n}`, id: `id_p0_${n}` }) : input(`prestaciones-0-${n}`, n === "dias_prestacion" ? "Lunes" : "")])) },
    { hidden: [], fields: ["dias_prestacion", "tipo_prestacion", "ap_presencial", "ap_vianda", "ap_total", "de_presencial", "de_vianda", "DELETE"].map((n) =>
      field(`prestaciones-1-${n}`, n, [n === "DELETE" ? el("input", { type: "checkbox", name: `prestaciones-1-${n}`, id: `id_p1_${n}` }) : input(`prestaciones-1-${n}`, "")])) },
  ], non_form_errors: [] },
  urls: { comedores: "/comedores/listar", comedor: "/comedores/7", relevamiento: "/comedores/7/relevamiento/12", detalle: DETALLE }, messages: [], ...over,
});
const actaForm = (over: Record<string, unknown> = {}) => ({
  acta_id: null, comedor: { id: 7, nombre: "Comedor <Uno>" },
  form: { fields: [
    field("acta-fecha_hora", "Fecha hora", [input("acta-fecha_hora", "", "datetime-local")]),
    field("acta-tecnico", "Técnico territorial", [select("acta-tecnico", [["", "---------"], ["9", "tec9"]], "")], { help_text: "Si se deja vacío queda registrado el usuario que carga el acta." }),
    field("acta-observaciones", "Observaciones", [el("textarea", { name: "acta-observaciones", id: "id_obs", rows: "4" })]),
  ], non_field_errors: [] },
  prestaciones: { management: management(1, 0), forms: [{ hidden: [], fields: ["dias_prestacion", "tipo_prestacion", "cantidad_actual", "cantidad_espera", "DELETE"].map((n) =>
    field(`prestaciones-0-${n}`, n, [n === "DELETE" ? el("input", { type: "checkbox", name: `prestaciones-0-${n}`, id: `id_a0_${n}` }) : input(`prestaciones-0-${n}`, "")])) }], non_form_errors: [] },
  urls: { comedores: "/comedores/listar", comedor: "/comedores/7", listado: "/comedores/7/relevamiento/listar" }, messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const posted = () => webPost.mock.calls[0] as [string, URLSearchParams];

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.sessionStorage.clear();
  vi.spyOn(relevamientosNavigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Seguimiento edit form", () => {
  it("owns the edit, create and acta edit paths only", () => {
    for (const p of [EDITAR, "/comedores/7/acta-complementaria/crear", "/comedores/7/acta-complementaria/5/editar"]) expect(findRoute(p)?.route.name).toBe("comedores-relevamientos-formularios");
    for (const other of [`${EDITAR}/`, "/comedores/7/relevamiento/12/seguimiento/3/eliminar", "/comedores/7/acta-complementaria/5", "/comedores/7/acta-complementaria/crear/", "/comedores/7/relevamiento/12/editar"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-relevamientos-formularios");
    }
  });

  it("renders the native form: heading, breadcrumb, cards, widgets with their server values and the table", async () => {
    serve(seguimientoForm());
    setup(EDITAR);
    await screen.findByText("Datos de la instancia");
    expect(webGet).toHaveBeenCalledWith(API_SEG, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Editar primer seguimiento - Comedor: Comedor <Uno>"));
    expect(screen.getAllByRole("heading", { level: 3 })[0].textContent).toBe("Comedor <Uno> | Editar primer seguimiento #1");
    expect(screen.getByRole("link", { name: "Primer seguimiento" }).getAttribute("href")).toBe(DETALLE);
    expect(screen.getByText("Editar", { selector: ".breadcrumb-item.active" })).toBeTruthy();
    expect((document.querySelector('[name="seg-fecha_hora"]') as HTMLInputElement).value).toBe("2026-03-04T12:07");
    expect((document.querySelector('[name="seg-estado"]') as HTMLSelectElement).value).toBe("Completo");
    expect((document.querySelector('[name="funcionamiento-abierto"]') as HTMLInputElement).checked).toBe(true);
    expect((document.querySelector('[name="funcionamiento-notas"]') as HTMLTextAreaElement).value).toBe("línea 1\nlínea 2");
    expect((document.querySelector('[name="menu-cambios"]') as HTMLSelectElement).value).toBe("unknown");
    expect(screen.getByText("Quién cargó").className).toBe("form-text text-muted");
    const menu = document.getElementById("bloque-menu")!;
    expect(within(menu).getByText("Sin cargar").getAttribute("title")).toBe("Se crea solo si se completa algún campo");
    expect(document.getElementById("bloque-funcionamiento")!.querySelector(".badge")).toBeNull();
    const tabla = document.getElementById("bloque-prestaciones")!;
    expect([...tabla.querySelectorAll("th")].map((t) => t.textContent)).toEqual(["Días", "Tipo", "AP presencial", "AP vianda", "AP total", "DE presencial", "DE vianda", "Eliminar"]);
    expect(tabla.querySelectorAll("tbody tr")).toHaveLength(2);
    expect(within(tabla).getByText("La última fila vacía permite agregar una prestación. Guarde y vuelva a editar para agregar más.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe(DETALLE);
  });

  it("submits the native names, flashes the message and goes to the detail", async () => {
    serve(seguimientoForm());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, message: "Seguimiento actualizado correctamente.", redirect: DETALLE } });
    setup(EDITAR);
    await screen.findByText("Datos de la instancia");
    fireEvent.change(document.querySelector('[name="seg-estado"]') as HTMLSelectElement, { target: { value: "Asignado" } });
    fireEvent.change(document.querySelector('[name="menu-cambios"]') as HTMLSelectElement, { target: { value: "true" } });
    fireEvent.click(document.querySelector('[name="prestaciones-0-DELETE"]') as HTMLInputElement);
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(relevamientosNavigation.assign).toHaveBeenCalledWith(DETALLE));
    const [url, body] = posted();
    expect(url).toBe(API_SEG);
    expect([body.get("seg-estado"), body.get("seg-tecnico"), body.get("seg-fecha_hora")]).toEqual(["Asignado", "Téc <1>", "2026-03-04T12:07"]);
    expect([body.get("funcionamiento-abierto"), body.get("menu-cambios"), body.get("prestaciones-0-DELETE"), body.get("prestaciones-1-DELETE")]).toEqual(["on", "true", "on", null]);
    expect([body.get("prestaciones-TOTAL_FORMS"), body.get("prestaciones-INITIAL_FORMS"), body.get("prestaciones-0-id")]).toEqual(["2", "1", "4"]);
    expect(body.get("csrfmiddlewaretoken")).toBe("synthetic-csrf-token");
    expect(takeFlash()).toEqual([{ message: "Seguimiento actualizado correctamente.", level: "success" }]);
  });

  it("re-renders the bound form with its errors on a 400 and keeps the toast", async () => {
    serve(seguimientoForm());
    const invalido = seguimientoForm();
    invalido.root.fields[1].errors = ["Escoja una opción válida."];
    invalido.prestaciones.forms[0].fields[4].errors = ["Asegúrese de que este valor sea mayor o igual a 0."];
    webPost.mockResolvedValue({ status: 400, data: { detail: "Revise los campos marcados en rojo.", ...invalido } });
    setup(EDITAR);
    await screen.findByText("Datos de la instancia");
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await screen.findByText("Escoja una opción válida.");
    expect(screen.getByText("Escoja una opción válida.").className).toBe("text-danger small");
    expect(screen.getByText("Asegúrese de que este valor sea mayor o igual a 0.")).toBeTruthy();
    expect((await screen.findAllByText("Revise los campos marcados en rojo.")).length).toBeGreaterThan(0);
    expect(relevamientosNavigation.assign).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: "Guardar" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("never resends an uncertain answer", async () => {
    serve(seguimientoForm());
    webPost.mockResolvedValue({ status: 504, data: { uncertain: true } });
    setup(EDITAR);
    await screen.findByText("Datos de la instancia");
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    const alerta = await screen.findByRole("alert");
    expect(alerta.textContent).toContain("No se pudo confirmar el resultado.");
    expect((screen.getByRole("button", { name: "Guardar" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(within(alerta).getByRole("button", { name: "Recargar" }));
    expect(relevamientosNavigation.assign).toHaveBeenCalledWith(EDITAR);
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it.each([403, 404])("answers %i with the existing screens", async (status) => {
    serve({ detail: "x" }, status);
    setup(EDITAR);
    await waitFor(() => expect(document.querySelector("main")).toBeTruthy());
    expect(screen.queryByText("Datos de la instancia")).toBeNull();
  });
});

describe("Acta form", () => {
  it("renders the new acta form with the native copy and column classes", async () => {
    serve(actaForm());
    setup("/comedores/7/acta-complementaria/crear");
    await screen.findByText("Datos del acta");
    expect(webGet).toHaveBeenCalledWith("web/comedores/relevamientos/7/actas/crear/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nueva acta complementaria - Comedor: Comedor <Uno>"));
    expect(screen.getAllByRole("heading", { level: 3 })[0].textContent).toBe("Comedor <Uno> | Nueva acta complementaria extraordinaria");
    expect(screen.getByText("Registra, fuera del ciclo de visitas, un cambio en la prestación del comedor.")).toBeTruthy();
    expect(screen.getByText("Observaciones").parentElement?.className).toBe("col-12 mb-3");
    expect(screen.getByText("Técnico territorial").parentElement?.className).toBe("col-md-6 mb-3");
    expect(screen.getByText("Si se deja vacío queda registrado el usuario que carga el acta.")).toBeTruthy();
    expect([...document.getElementById("bloque-prestaciones")!.querySelectorAll("th")].map((t) => t.textContent)).toEqual(["Días", "Tipo", "Cantidad actual", "Cantidad en espera", "Eliminar"]);
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/comedores/7/relevamiento/listar");
    expect(screen.getByRole("link", { name: "Acompañamiento Territorial" }).getAttribute("href")).toBe("/comedores/7/relevamiento/listar");
  });

  it("creates through the API and edits through the edit endpoint", async () => {
    serve(actaForm());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, message: "Acta complementaria guardada correctamente.", redirect: "/comedores/7/acta-complementaria/5" } });
    setup("/comedores/7/acta-complementaria/crear");
    await screen.findByText("Datos del acta");
    fireEvent.change(document.querySelector('[name="acta-tecnico"]') as HTMLSelectElement, { target: { value: "9" } });
    fireEvent.change(document.querySelector('[name="acta-observaciones"]') as HTMLTextAreaElement, { target: { value: "Cambio\ndos" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(relevamientosNavigation.assign).toHaveBeenCalledWith("/comedores/7/acta-complementaria/5"));
    const [url, body] = posted();
    expect(url).toBe("web/comedores/relevamientos/7/actas/crear/");
    expect([body.get("acta-tecnico"), body.get("acta-observaciones"), body.get("prestaciones-TOTAL_FORMS")]).toEqual(["9", "Cambio\ndos", "1"]);
    cleanup();
    vi.clearAllMocks();
    serve(actaForm({ acta_id: 5 }));
    webPost.mockResolvedValue({ status: 504, data: { uncertain: true } });
    setup("/comedores/7/acta-complementaria/5/editar");
    await screen.findByText("Datos del acta");
    expect(webGet).toHaveBeenCalledWith("web/comedores/relevamientos/7/actas/5/editar/", expect.anything());
    expect(screen.getAllByRole("heading", { level: 3 })[0].textContent).toBe("Comedor <Uno> | Editar acta complementaria extraordinaria");
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await screen.findByRole("alert");
    expect(posted()[0]).toBe("web/comedores/relevamientos/7/actas/5/editar/");
  });

  it("shows a rejected technician and quantity as field errors", async () => {
    serve(actaForm());
    const malo = actaForm();
    malo.form.fields[1].errors = ["Escoja una opción válida."];
    malo.prestaciones.forms[0].fields[2].errors = ["Introduzca un número entero."];
    webPost.mockResolvedValue({ status: 400, data: { detail: "Revise los campos marcados en rojo.", ...malo } });
    setup("/comedores/7/acta-complementaria/crear");
    await screen.findByText("Datos del acta");
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await screen.findByText("Escoja una opción válida.");
    expect(screen.getByText("Introduzca un número entero.")).toBeTruthy();
  });

  it("rejects malformed payloads", () => {
    expect(seguimientoFormValid(seguimientoForm())).toBe(true);
    expect(seguimientoFormValid(seguimientoForm({ urls: { comedores: "/a", comedor: "/b", relevamiento: "/c", detalle: "https://evil.example/" } }))).toBe(false);
    expect(seguimientoFormValid(seguimientoForm({ bloques: [{ key: "x", label: "X", existe: true, form: { fields: [{ name: 1 }], non_field_errors: [] } }] }))).toBe(false);
    expect(actaFormValid(actaForm())).toBe(true);
    expect(actaFormValid(actaForm({ acta_id: "5" }))).toBe(false);
  });
});
