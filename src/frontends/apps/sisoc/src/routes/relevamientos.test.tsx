import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { detailValid, listValid } from "./relevamientos";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const LIST = "/comedores/7/relevamiento/listar";
const DETAIL = "/comedores/7/relevamiento/12";
const caps = (over: Record<string, boolean> = {}) => ({ add_relevamiento: false, change_relevamiento: false, add_actacomplementaria: false, change_actacomplementaria: false, ...over });
const seg = { id: 3, fecha: "Sin fecha", estado: "Pendiente", estado_badge: "bg-secondary", tipo: "Seguimiento Posterior", numero_orden: 2, origen: "app", sincronizado_gestionar: false, detalle_url: "/comedores/7/relevamiento/12/seguimiento/3" };
const list = (over: Record<string, unknown> = {}) => ({
  comedor: { id: 7, nombre: "Comedor <Uno>" }, encabezado: "Comedor <Uno> | Prov, Muni, Loc",
  relevamientos: [{ id: 12, fecha: "04/03/2026 15:07", estado: "Finalizado", estado_badge: "bg-success", numero_if: "IF-1", origen: "sisoc", sincronizado_gestionar: true, has_seguimiento: true, detalle_url: "/comedores/7/relevamiento/12", seguimientos: [seg] }],
  actas: [{ id: 5, fecha_hora: "Sin fecha", tecnico: "Sin técnico", origen: "sisoc", prestaciones_count: 1, estado: "Finalizado", estado_badge: "bg-success", a_subsanar: false, detalle_url: "/comedores/7/acta/5", editar_url: "/comedores/7/acta/5/editar" }],
  seguimientos_pnud: [{ id: 9, formulario_display: "FORM-SIPH", fecha_hora: "Sin fecha", tecnico: "Sin técnico", origen: "app", estado: "Pendiente Revisión", estado_badge: "bg-warning text-dark", a_subsanar: true, detalle_url: "/comedores/7/pnud/9" }],
  opciones_alta: [{ value: "inicial", label: "Relevamiento inicial" }], opciones_seguimiento: [{ value: "posterior", label: "Seguimiento posterior" }],
  capabilities: caps(), urls: { listado: LIST, alta: "/comedores/ajax/7/relevamiento/", acta_crear: "/comedores/7/acta/crear", territoriales: "/comedores/7/territoriales/", territoriales_sincronizar: "/comedores/7/territoriales/sincronizar/", numero_if: "/comedores/7/numero-if/" },
  messages: [], ...over,
});
type N = string | { t: string; a: Record<string, string>; c: N[] };
const el = (t: string, cls: string, ...c: N[]): N => ({ t, a: cls ? { class: cls } : {}, c });
const card = (titulo: string, ...body: N[]) => el("div", "card", el("div", "card-header", el("h3", "card-title font-weight-bold mr-3 pt-1", titulo),
  el("div", "card-tools", { t: "button", a: { type: "button", class: "btn btn-tool", "data-card-widget": "collapse" }, c: [el("i", "fas fa-minus")] })), el("div", "card-body card-comments p-0 pb-1", ...body));
const value = (label: string, v: string, cls = "username fw-bold fs-5") => el("div", "nav nav-pills row my-3", el("div", "nav-item col-4 d-flex",
  el("div", "comment-text comment-text d-flex flex-column text-sm", label, el("span", cls, v))));
const tree = (): N[] => [
  el("div", "row relevamiento-container", el("div", "col-3", card("Acompañamiento Territorial", value("Territorial", "Sin información"))),
    el("div", "col-4", card("Información", value("Nombre", "Comedor <Uno>"))), el("div", "col-5", card("Datos del referente del Comedor/Merendero", value("Función", "Sin información")))),
  el("div", "relevamiento-container", card("Observacion", value("Observacion", "-", "username text-wrap"))),
];
const titulos = ["Acompañamiento Territorial", "Información", "Datos del referente del Comedor/Merendero", "Observacion"];
const detail = (over: Record<string, unknown> = {}, rel: Record<string, unknown> = {}) => ({
  relevamiento: { id: 12, comedor: { id: 7, nombre: "Comedor <Uno>" }, nombre_comedor: "Comedor <Uno>", fecha_visita: "04/03/2026 15:07", estado: "Visita pendiente", estado_visible: "Pendiente", estado_badge: "bg-secondary",
    estado_validacion: "", a_subsanar: false, esta_validado: false, sin_cargar: false, origen: "app", sincronizado_gestionar: true, observaciones_coordinador: "", coordinador: null, fecha_revision_coordinador: null, ...rel },
  timeline: [{ id: 12, step: 1, fecha: "04/03/26", estado: "Pendiente", card_class: "active", status_class: "pendiente" }],
  secciones: tree(), titulos,
  seguimientos: [{ id: 3, numero_orden: 2, tipo: "Seguimiento Posterior", fecha: "Sin fecha", estado: "Pendiente", estado_badge: "bg-secondary", estado_validacion: "", a_subsanar: false, origen: "app", sincronizado_gestionar: false,
    detalle_url: "/comedores/7/relevamiento/12/seguimiento/3", editar_url: "/comedores/7/relevamiento/12/seguimiento/3/editar", eliminar_url: "/comedores/7/relevamiento/12/seguimiento/3/eliminar", eliminar_api: "/api/web/comedores/relevamientos/7/relevamiento/12/seguimientos/3/eliminar/" }],
  adjuntos: [], pdf: { disponible: false, url: "/comedores/7/relevamiento/12/pdf", oficial: false, fecha_oficial: null },
  capabilities: { change_relevamiento: false, review_relevamiento: false, change_primerseguimiento: false, delete_primerseguimiento: false, view_logentry: false },
  urls: { listado: LIST, comedores: "/comedores/listar", comedor: "/comedores/7", alta: "/comedores/ajax/7/relevamiento/", eliminar: "/comedores/7/relevamiento/12/eliminar", revision: "/comedores/7/relevamiento/12/revision", revision_api: "/comedores/7/relevamiento/12/revision/",
    historial: "/audittrail/relevamientos/relevamiento/12/", territoriales: "/comedores/7/territoriales/", territoriales_sincronizar: "/comedores/7/territoriales/sincronizar/" },
  messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true, meta: { fuente: "cache_provincia", total: 1 }, territoriales: [{ gestionar_uid: "u1", nombre: "Ana Pérez" }] }) })));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("Relevamientos route", () => {
  it("owns the list and detail paths only", () => {
    expect(findRoute(LIST)?.route.name).toBe("comedores-relevamientos");
    expect(findRoute(DETAIL)?.route.name).toBe("comedores-relevamientos");
    for (const other of ["/comedores/7/relevamiento/listar/", "/comedores/x/relevamiento/listar", "/comedores/7/relevamiento/12/pdf", "/comedores/7/relevamiento/crear",
      "/comedores/7/relevamiento/12/editar", "/comedores/7/relevamiento/12/seguimiento/3"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-relevamientos");
    }
  });

  it("renders the three cards read-only, with the native texts and links", async () => {
    serve(list());
    setup(LIST);
    await screen.findByText("12 - 04/03/2026 15:07");
    expect(webGet).toHaveBeenCalledWith("web/comedores/relevamientos/7/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Acompañamiento Territorial - Comedor: Comedor <Uno>"));
    expect(screen.getAllByRole("heading", { level: 3 })[0].textContent).toContain("Comedor <Uno> | Prov, Muni, Loc");
    expect(["Acompañamiento Territorial", "Actas complementarias extraordinarias", "Seguimientos PNUD"].map((t) => screen.getAllByRole("heading", { level: 3, name: t }).length)).toEqual([1, 1, 1]);
    expect(screen.getByRole("link", { name: "12 - 04/03/2026 15:07" }).getAttribute("href")).toBe("/comedores/7/relevamiento/12");
    expect(screen.getByRole("link", { name: "3 - Sin fecha" }).getAttribute("href")).toBe("/comedores/7/relevamiento/12/seguimiento/3");
    expect(screen.getByText("Seguimiento Posterior #2")).toBeTruthy();
    expect(screen.getByText("Número de IF:").nextElementSibling?.textContent).toBe("IF-1");
    expect(screen.getByText("1 prestación")).toBeTruthy();
    expect(screen.getByRole("link", { name: "5 - Sin fecha" })).toBeTruthy();
    expect(screen.getByText("A subsanar")).toBeTruthy();
    for (const name of ["Agregar", "Actualizar IF", "Editar"]) {
      expect(screen.queryByRole("button", { name })).toBeNull();
      expect(screen.queryByRole("link", { name })).toBeNull();
    }
  });

  it("shows the empty messages and an empty relevamientos block", async () => {
    serve(list({ relevamientos: [], actas: [], seguimientos_pnud: [] }));
    setup(LIST);
    await screen.findByText("No hay actas complementarias cargadas para este comedor.");
    expect(screen.getByText("No hay seguimientos PNUD cargados para este comedor.")).toBeTruthy();
  });

  it("offers the buttons by capability and posts the modals natively", async () => {
    serve(list({ capabilities: caps({ add_relevamiento: true, change_relevamiento: true, add_actacomplementaria: true, change_actacomplementaria: true }) }));
    setup(LIST);
    await screen.findByText("12 - 04/03/2026 15:07");
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/comedores/7/acta/5/editar");
    expect(screen.getByRole("link", { name: "Agregar" }).getAttribute("href")).toBe("/comedores/7/acta/crear");
    fireEvent.click(screen.getAllByRole("button", { name: "Agregar" })[0]);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Nuevo acompañamiento territorial")).toBeTruthy();
    const form = dialog.querySelector("form") as HTMLFormElement;
    expect(form.getAttribute("action")).toBe("/comedores/ajax/7/relevamiento/");
    expect(form.method).toBe("post");
    expect((form.querySelector('[name="csrfmiddlewaretoken"]') as HTMLInputElement).value).toBe("synthetic-csrf-token");
    fireEvent.click(within(dialog).getByRole("button", { name: "Crear acompañamiento territorial" }));
    expect((await screen.findByText("Seleccioná un territorial de la lista antes de crear el relevamiento.")).className).toBe("toast toast-error");
    const input = within(dialog).getByPlaceholderText("Escribí el nombre del territorial");
    fireEvent.change(input, { target: { value: "ana perez" } });
    await waitFor(() => expect(within(dialog).getByRole("button", { name: "Ana Pérez" })).toBeTruthy());
    fireEvent.click(within(dialog).getByRole("button", { name: "Crear acompañamiento territorial" }));
    expect((form.querySelector('[name="territorial"]') as HTMLInputElement).value).toBe(JSON.stringify({ gestionar_uid: "u1", nombre: "Ana Pérez" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    fireEvent.click(screen.getAllByRole("button", { name: "Agregar" })[1]);
    const seguimiento = await screen.findByRole("dialog");
    expect((seguimiento.querySelector('[name="relevamiento_id"]') as HTMLInputElement).value).toBe("12");
    expect(within(seguimiento).getByText("Crear seguimiento")).toBeTruthy();
  });

  it("opens and cancels the inline Numero de IF form", async () => {
    serve(list({ capabilities: caps({ change_relevamiento: true }) }));
    setup(LIST);
    fireEvent.click(await screen.findByRole("button", { name: "Actualizar IF" }));
    const input = document.querySelector('input[name="numero_if"]') as HTMLInputElement;
    expect(input.value).toBe("IF-1");
    expect((input.form as HTMLFormElement).querySelector('[name="relevamiento_id"]')).toHaveProperty("value", "12");
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(document.querySelector('input[name="numero_if"]')).toBeNull();
  });

  it("renders the detail header, sections and cycle, read-only", async () => {
    serve(detail());
    setup(DETAIL);
    await screen.findByText("Ciclo de seguimiento");
    expect(webGet).toHaveBeenCalledWith("web/comedores/relevamientos/7/relevamiento/12/", expect.anything());
    expect(screen.getAllByRole("heading", { level: 3 })[0].textContent).toBe("Comedor <Uno> | Acompañamiento Territorial | 04/03/2026 15:07 | Pendiente Sincronizado con GESTIONAR App");
    expect(screen.getByRole("link", { name: "Comedores" }).getAttribute("href")).toBe("/comedores/listar");
    expect(screen.getByRole("link", { name: "Comedor <Uno>" }).getAttribute("href")).toBe("/comedores/7");
    expect(["Inicio de Ejecución", "Final de Ejecución", "Plazo de Ejecución"].every((t) => screen.getByText(t).nextElementSibling?.textContent === "-")).toBe(true);
    expect(screen.getByRole("link", { name: "Eliminar" }).getAttribute("href")).toBe("/comedores/7/relevamiento/12/eliminar");
    for (const gone of ["Reasignar territorial", "Revisar", "Historial", "Descargar PDF"]) expect(screen.queryByText(gone)).toBeNull();
    expect(screen.getByRole("link", { name: "Ver seguimientos" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver" }).getAttribute("href")).toBe("/comedores/7/relevamiento/12/seguimiento/3");
    expect(screen.getByText("1 instancia")).toBeTruthy();
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent).slice(1)).toEqual(
      titulos);
    const observacion = screen.getByText("-", { selector: "span.username" });
    expect(observacion.className).toBe("username text-wrap");
    expect(screen.getByText("Comedor <Uno>", { selector: "span.username" }).className).toBe("username fw-bold fs-5");
    const body = screen.getByRole("heading", { level: 3, name: "Información" }).closest(".card")!.querySelector(".card-body") as HTMLElement;
    fireEvent.click(screen.getByRole("heading", { level: 3, name: "Información" }).closest(".card")!.querySelector("button.btn-tool") as HTMLElement);
    expect(body.style.display).toBe("none");
    expect(screen.getByRole("heading", { level: 3, name: "Información" }).closest(".card")!.querySelector("i")!.className).toContain("fa-plus");
  });

  it("shows the actions by capability and opens the review, assign and delete modals", async () => {
    serve(detail({ capabilities: { change_relevamiento: true, review_relevamiento: true, change_primerseguimiento: true, delete_primerseguimiento: true, view_logentry: true } },
      { observaciones_coordinador: "Corregir\nfoto", a_subsanar: true, coordinador: "rev", fecha_revision_coordinador: "05/03/2026" }));
    setup(DETAIL);
    await screen.findByText("Ciclo de seguimiento");
    expect(screen.getByText("Observaciones del coordinador").parentElement?.className).toContain("alert-danger");
    expect(screen.getByRole("link", { name: "Historial" }).getAttribute("href")).toBe("/audittrail/relevamientos/relevamiento/12/");
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/comedores/7/relevamiento/12/seguimiento/3/editar");
    fireEvent.click(screen.getByRole("button", { name: "Revisar" }));
    let dialog = await screen.findByRole("dialog");
    expect((dialog.querySelector("form") as HTMLFormElement).getAttribute("action")).toBe("/comedores/7/relevamiento/12/revision");
    expect(within(dialog).getByText("Revisión del coordinador")).toBeTruthy();
    expect((dialog.querySelector("textarea") as HTMLTextAreaElement).value).toBe("Corregir\nfoto");
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    fireEvent.click(screen.getByRole("button", { name: "Reasignar territorial" }));
    dialog = await screen.findByRole("dialog");
    await waitFor(() => expect(within(dialog).getByRole("option", { name: "Ana Pérez" })).toBeTruthy());
    expect((dialog.querySelector('[name="relevamiento_id"]') as HTMLInputElement).value).toBe("12");
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    fireEvent.click(screen.getAllByRole("button", { name: "Eliminar" })[0]);
    dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Eliminar seguimiento posterior #2")).toBeTruthy();
    expect((dialog.querySelector("form") as HTMLFormElement).getAttribute("action")).toBe("/comedores/7/relevamiento/12/seguimiento/3/eliminar");
  });

  it("shows the territorial status line and forces a sync like the native script", async () => {
    serve(list({ capabilities: caps({ add_relevamiento: true }) }));
    setup(LIST);
    fireEvent.click(await screen.findAllByRole("button", { name: "Agregar" }).then((b) => b[0]));
    const dialog = await screen.findByRole("dialog");
    await waitFor(() => expect(within(dialog).getByText("1 territoriales (desde cache rápido)")).toBeTruthy());
    expect(fetch).toHaveBeenCalledWith("/comedores/7/territoriales/", expect.objectContaining({ headers: expect.objectContaining({ "X-Requested-With": "XMLHttpRequest" }) }));
    fireEvent.click(within(dialog).getByTitle("Sincronizar con GESTIONAR"));
    expect(fetch).toHaveBeenLastCalledWith("/comedores/7/territoriales/sincronizar/", expect.objectContaining({ method: "POST", headers: expect.objectContaining({ "X-CSRFToken": "synthetic-csrf-token" }) }));
    await screen.findByText("Territoriales sincronizados correctamente");
  });

  it("reports a territorial load failure in the status line", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: false, status: 500, statusText: "Boom", json: () => Promise.resolve({}) })));
    serve(list({ capabilities: caps({ add_relevamiento: true }) }));
    setup(LIST);
    fireEvent.click((await screen.findAllByRole("button", { name: "Agregar" }))[0]);
    const dialog = await screen.findByRole("dialog");
    await waitFor(() => expect(within(dialog).getByText("Error: HTTP 500: Boom")).toBeTruthy());
    await screen.findByText("Error cargando territoriales: HTTP 500: Boom");
  });

  it("auto-advances the photo carousel every 5 s and pauses on hover", async () => {
    const slide = (n: number): N => el("div", "carousel-item", { t: "img", a: { src: `/media/${n}.jpg`, alt: `Foto ${n}`, class: "d-block w-100" }, c: [] });
    const carouselNode: N = { t: "div", a: { id: "carouselExample", class: "carousel slide" }, c: [el("div", "carousel-inner", slide(1), slide(2))] };
    serve(detail({ secciones: [el("div", "relevamiento-container", card("Fotos", carouselNode))], titulos: ["Fotos"] }));
    setup(DETAIL);
    await screen.findByText("Ciclo de seguimiento");
    vi.useFakeTimers();
    const carousel = () => document.getElementById("carouselExample") as HTMLElement;
    // Re-arm the interval under the fake clock.
    fireEvent.mouseEnter(carousel());
    fireEvent.mouseLeave(carousel());
    const active = () => document.querySelector(".carousel-item.active img")?.getAttribute("alt");
    expect(active()).toBe("Foto 1");
    act(() => { vi.advanceTimersByTime(5000); });
    expect(active()).toBe("Foto 2");
    fireEvent.mouseEnter(carousel());
    act(() => { vi.advanceTimersByTime(20000); });
    expect(active()).toBe("Foto 2");
    fireEvent.mouseLeave(carousel());
    act(() => { vi.advanceTimersByTime(5000); });
    expect(active()).toBe("Foto 1");
    vi.useRealTimers();
  });

  it("offers the PDF only when finalized", async () => {
    serve(detail({ pdf: { disponible: true, url: "/comedores/7/relevamiento/12/pdf", oficial: true, fecha_oficial: "01/01/2026 10:00" } }, { estado: "Finalizado" }));
    setup(DETAIL);
    await screen.findByText("Ciclo de seguimiento");
    expect(screen.getByRole("link", { name: "Descargar PDF" }).getAttribute("href")).toBe("/comedores/7/relevamiento/12/pdf");
    expect(screen.getByText("Formato oficial de Gestionar")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Reasignar territorial" })).toBeNull();
  });

  it.each([403, 404])("answers %i with the existing screens", async (status) => {
    serve({ detail: "x" }, status);
    setup(LIST);
    await waitFor(() => expect(document.querySelector("main")).toBeTruthy());
    expect(screen.queryByRole("heading", { level: 3, name: "Seguimientos PNUD" })).toBeNull();
  });

  it("rejects malformed payloads", () => {
    expect(listValid(list())).toBe(true);
    expect(listValid(list({ actas: [{ id: "x" }] }))).toBe(false);
    expect(listValid(list({ urls: { ...list().urls, alta: "https://evil.example/" } }))).toBe(false);
    expect(detailValid(detail())).toBe(true);
    expect(detailValid(detail({ pdf: null }))).toBe(false);
  });
});
