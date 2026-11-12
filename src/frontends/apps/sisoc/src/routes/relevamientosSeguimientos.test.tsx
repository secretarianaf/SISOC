import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { pnudValid, seguimientoValid } from "./relevamientosSeguimientos";
import { relevamientosNavigation, takeFlash } from "./relevamientosApi";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const SEG = "/comedores/7/relevamiento/12/seguimiento/3/";
const ALIAS = "/comedores/7/relevamiento/12/primer-seguimiento/";
const PNUD = "/comedores/7/seguimiento-pnud/9";
const review = (over: Record<string, unknown> = {}) => ({
  estado: "Finalizado", estado_badge: "bg-success", estado_validacion: "", a_subsanar: false, esta_validado: false, sin_cargar: false,
  observaciones_coordinador: "", coordinador: null, fecha_revision_coordinador: null, origen: "sisoc", ...over,
});
const caps = (over: Record<string, boolean> = {}) => ({ change_primerseguimiento: false, review_relevamiento: false, delete_primerseguimiento: false, ...over });
const seguimiento = (over: Record<string, unknown> = {}, rev: Record<string, unknown> = {}) => ({
  seguimiento: { id: 3, tipo_display: "Primer seguimiento", numero_orden: 1, fecha_hora: "4 Marzo 2026 12:07", sincronizado_gestionar: false, gestionar_id: "Sin asignar", tecnico: "Téc <1>", referente: "Sin asignar",
    motivo_diferencia_aprobado_declarado: "", ...review(rev) },
  relevamiento: { id: 12, fecha_visita: "Sin información" }, comedor: { id: 7, nombre: "Comedor <Uno>" },
  instancias: [{ id: 3, numero_orden: 1, tipo_display: "Primer seguimiento", detalle_url: SEG }, { id: 4, numero_orden: 2, tipo_display: "Seguimiento Posterior", detalle_url: "/comedores/7/relevamiento/12/seguimiento/4/" }],
  bloques: [{ key: "cierre", label: "Cierre", campos: [{ label: "Comentarios finales", value: "listo", es_imagen: false },
    { label: "Firma entrevistado", value: [{ t: "img", a: { src: "/media/firma.png", alt: "Firma entrevistado", class: "img-fluid my-1 rounded object-fit-contain" }, c: [] }], es_imagen: true }] }],
  es_primer: true, prestaciones: [["Lunes", "Almuerzo", "5", "-", "-"]], receta_items: [["Arroz", "-", "2"]], adjuntos: [],
  pdf: { url: null, fecha_oficial: null }, capabilities: caps(),
  urls: { comedores: "/comedores/listar", comedor: "/comedores/7", relevamiento: "/comedores/7/relevamiento/12", editar: `${SEG}editar`, revision: `${SEG}revision`, revision_api: "/api/web/comedores/relevamientos/7/relevamiento/12/seguimientos/3/revision/" }, messages: [], ...over,
});
const pnud = (over: Record<string, unknown> = {}) => ({
  seguimiento: { id: 9, formulario: "siph", formulario_display: "FORM-SIPH", fecha_hora: "Sin fecha", tecnico: "Sin técnico", fecha_creacion: "5 Marzo 2026 10:00", ...review({ estado: "Pendiente Revisión", estado_badge: "bg-warning text-dark", origen: "app" }) },
  comedor: { id: 7, nombre: "Comedor <Uno>" }, encabezado_formulario: { linea: "Línea Tradicional", titulo: "Seguimiento SIPH" },
  secciones: [{ titulo: "Funcionamiento", filas: [{ etiqueta: "Estado", tipo: "texto", valor: "Cerrado\nhoy" }, { etiqueta: "Fotos", tipo: "imagen", valor: "/media/f.png" },
    { etiqueta: "Personas", tipo: "tabla", columnas: ["Nombre", "Edad"], filas: [["Ana", "30"]] }] }],
  adjuntos: [], pdf_url: `${PNUD}/pdf`, capabilities: { review_relevamiento: false },
  urls: { comedores: "/comedores/listar", comedor: "/comedores/7", listado: "/comedores/7/relevamiento/listar", revision: `${PNUD}/revision`, revision_api: "/api/web/comedores/relevamientos/7/pnud/9/revision/" }, messages: [], ...over,
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
  window.sessionStorage.clear();
  vi.spyOn(relevamientosNavigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Seguimientos route", () => {
  it("owns the instance, alias and PNUD paths only", () => {
    for (const p of [SEG, ALIAS, PNUD]) expect(findRoute(p)?.route.name).toBe("comedores-relevamientos-seguimientos");
    for (const other of ["/comedores/7/relevamiento/12/seguimiento/3", "/comedores/7/relevamiento/12/seguimiento/3/editar", "/comedores/7/relevamiento/12/seguimiento/3/pdf",
      "/comedores/7/relevamiento/12/primer-seguimiento/eliminar", "/comedores/7/seguimiento-pnud/9/pdf", "/comedores/7/seguimiento-pnud/9/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-relevamientos-seguimientos");
    }
  });

  it("renders the instance read-only with its heading, breadcrumb, cycle, tables and legend", async () => {
    serve(seguimiento());
    setup(SEG);
    await screen.findByText("Resumen");
    expect(webGet).toHaveBeenCalledWith("web/comedores/relevamientos/7/relevamiento/12/seguimientos/3/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Primer seguimiento - Comedor: Comedor <Uno>"));
    expect(screen.getAllByRole("heading", { level: 3 })[0].textContent).toBe("Comedor <Uno> | Primer seguimiento #1 | 4 Marzo 2026 12:07 | Finalizado Pendiente sincronización");
    expect(screen.getByRole("link", { name: "Acompañamiento Territorial Sin información" }).getAttribute("href")).toBe("/comedores/7/relevamiento/12");
    expect(screen.getByText("Primer seguimiento", { selector: ".breadcrumb-item.active" })).toBeTruthy();
    const group = screen.getByRole("group", { name: "Instancias del ciclo" });
    expect(within(group).getAllByRole("link").map((a) => [a.textContent, a.className])).toEqual([["#1 Primer seguimiento", "btn btn-sm btn-info"], ["#2 Seguimiento Posterior", "btn btn-sm btn-outline-info"]]);
    expect(screen.getByText("El PDF se genera cuando el territorial lo envía desde Gestionar.")).toBeTruthy();
    for (const gone of ["Editar", "Revisar", "Descargar PDF"]) expect(screen.queryByText(gone)).toBeNull();
    expect(screen.getByText("ID GESTIONAR", { exact: false }).querySelector("span")?.textContent).toBe("Sin asignar");
    expect(screen.queryByText("Motivo de la diferencia entre lo aprobado y lo declarado")).toBeNull();
    expect(screen.getByRole("heading", { level: 3, name: "Cierre" })).toBeTruthy();
    expect(screen.getByAltText("Firma entrevistado").getAttribute("src")).toBe("/media/firma.png");
    const prestaciones = screen.getByRole("heading", { level: 3, name: "Prestaciones" }).closest(".card")!;
    expect([...prestaciones.querySelectorAll("th")].map((t) => t.textContent)).toEqual(["Días", "Tipo", "AP", "DE presencial", "DE vianda"]);
    expect([...screen.getByRole("heading", { level: 3, name: "Items de receta del menú" }).closest(".card")!.querySelectorAll("th")].map((t) => t.textContent)).toEqual(["Ingrediente", "Unidad de medida", "Cantidad"]);
  });

  it("uses the primero endpoint for the alias and shows the empty blocks message", async () => {
    serve(seguimiento({ bloques: [], instancias: [], es_primer: false, prestaciones: [["Martes", "-", "1", "2", "-", "-"]] }));
    setup(ALIAS);
    await screen.findByText("Todavía no se cargaron bloques para este seguimiento.");
    expect(webGet).toHaveBeenCalledWith("web/comedores/relevamientos/7/relevamiento/12/seguimientos/primero/", expect.anything());
    expect(screen.queryByRole("group", { name: "Instancias del ciclo" })).toBeNull();
    expect([...screen.getByRole("heading", { level: 3, name: "Prestaciones" }).closest(".card")!.querySelectorAll("th")].map((t) => t.textContent)).toContain("AP vianda");
  });

  it("shows the badges, the PDF link, the actions and posts the review natively", async () => {
    serve(seguimiento({ pdf: { url: `${SEG}pdf`, fecha_oficial: "01/01/2026 10:00" }, capabilities: caps({ change_primerseguimiento: true, review_relevamiento: true }) },
      { origen: "app", a_subsanar: true, estado_validacion: "A subsanar", observaciones_coordinador: "Corregir\nfoto", coordinador: "rev", fecha_revision_coordinador: "5 Marzo 2026" }));
    setup(SEG);
    await screen.findByText("Resumen");
    expect(screen.getAllByRole("heading", { level: 3 })[0].textContent).toContain("A subsanar App Pendiente sincronización");
    expect(screen.getByRole("link", { name: "Descargar PDF" }).getAttribute("title")).toBe("Formato oficial de Gestionar, enviado el 01/01/2026 10:00");
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe(`${SEG}editar`);
    expect(screen.getByText("Observaciones del coordinador").parentElement?.className).toContain("alert-danger");
    fireEvent.click(screen.getByRole("button", { name: "Revisar" }));
    const dialog = await screen.findByRole("dialog");
    const form = dialog.querySelector("form") as HTMLFormElement;
    expect([form.method, form.getAttribute("action")]).toEqual(["post", `${SEG}revision`]);
    expect((form.querySelector('[name="csrfmiddlewaretoken"]') as HTMLInputElement).value).toBe("synthetic-csrf-token");
    expect((dialog.querySelector("textarea") as HTMLTextAreaElement).value).toBe("Corregir\nfoto");
    expect(within(dialog).getByRole("button", { name: "Guardar revisión" }).className).toContain("btn-warning");
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("hides the review button for a validated seguimiento", async () => {
    serve(seguimiento({ capabilities: caps({ review_relevamiento: true }) }, { esta_validado: true }));
    setup(SEG);
    await screen.findByText("Resumen");
    expect(screen.queryByRole("button", { name: "Revisar" })).toBeNull();
  });

  it("renders the PNUD detail with SIPH PDF, sections, tables, image and the empty message", async () => {
    serve(pnud());
    setup(PNUD);
    await screen.findByText("Resumen");
    expect(webGet).toHaveBeenCalledWith("web/comedores/relevamientos/7/pnud/9/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Seguimiento PNUD - Comedor: Comedor <Uno>"));
    expect(screen.getAllByRole("heading", { level: 3 })[0].textContent).toBe("Comedor <Uno> | FORM-SIPH | Sin fecha Pendiente Revisión App");
    expect(screen.getByRole("link", { name: "Descargar PDF" }).className).toBe("btn btn-outline-secondary");
    expect(screen.getByText("Cargado el", { exact: false }).querySelector("span")?.textContent).toBe("5 Marzo 2026 10:00");
    expect(screen.getByText("Línea Tradicional").className).toBe("fw-bold");
    expect(screen.getByRole("heading", { level: 3, name: "Funcionamiento" })).toBeTruthy();
    expect(screen.getByText("Estado").nextElementSibling?.innerHTML).toBe("Cerrado<br>hoy");
    expect(screen.getByAltText("Fotos").getAttribute("style")).toContain("max-width: 240px");
    expect(screen.getByText("Ana")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Acompañamiento Territorial" }).getAttribute("href")).toBe("/comedores/7/relevamiento/listar");
  });

  it("omits the PNUD PDF link for other forms and shows the empty message", async () => {
    serve(pnud({ pdf_url: null, secciones: [], encabezado_formulario: { linea: "", titulo: "" } }));
    setup(PNUD);
    await screen.findByText("El seguimiento no tiene respuestas cargadas.");
    expect(screen.queryByRole("link", { name: "Descargar PDF" })).toBeNull();
    expect(screen.queryByText("Línea Tradicional")).toBeNull();
  });

  it.each([403, 404])("answers %i with the existing screens", async (status) => {
    serve({ detail: "x" }, status);
    setup(SEG);
    await waitFor(() => expect(document.querySelector("main")).toBeTruthy());
    expect(screen.queryByText("Resumen")).toBeNull();
  });

  it("rejects malformed payloads", () => {
    expect(seguimientoValid(seguimiento())).toBe(true);
    expect(seguimientoValid(seguimiento({ prestaciones: [[1]] }))).toBe(false);
    expect(seguimientoValid(seguimiento({ urls: { ...seguimiento().urls, editar: "https://evil.example/" } }))).toBe(false);
    expect(pnudValid(pnud())).toBe(true);
    expect(pnudValid(pnud({ pdf_url: 3 }))).toBe(false);
  });
});

describe("Seguimiento and PNUD reviews through the API", () => {
  it("posts the seguimiento review to its API and flashes the message", async () => {
    serve(seguimiento({ capabilities: caps({ review_relevamiento: true }) }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, message: "Seguimiento validado correctamente.", redirect: SEG } });
    setup(SEG);
    fireEvent.click(await screen.findByRole("button", { name: "Revisar" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByRole("combobox"), { target: { value: "A subsanar" } });
    fireEvent.change(dialog.querySelector("textarea") as HTMLTextAreaElement, { target: { value: "Corregir" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Guardar revisión" }));
    await waitFor(() => expect(relevamientosNavigation.assign).toHaveBeenCalledWith(SEG));
    const [url, body] = webPost.mock.calls[0] as [string, URLSearchParams];
    expect(url).toBe("web/comedores/relevamientos/7/relevamiento/12/seguimientos/3/revision/");
    expect([body.get("estado_validacion"), body.get("observaciones_coordinador")]).toEqual(["A subsanar", "Corregir"]);
    expect(takeFlash()).toEqual([{ message: "Seguimiento validado correctamente.", level: "success" }]);
  });

  it("posts the PNUD review to its API and shows a 400 as a toast", async () => {
    serve(pnud({ capabilities: { review_relevamiento: true } }));
    webPost.mockResolvedValue({ status: 400, data: { errors: { __all__: [{ message: "Para devolver el seguimiento debe indicar qué corregir.", code: "invalid" }] } } });
    setup(PNUD);
    fireEvent.click(await screen.findByRole("button", { name: "Revisar" }));
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Guardar revisión" }));
    await screen.findByText("Para devolver el seguimiento debe indicar qué corregir.");
    expect(webPost.mock.calls[0][0]).toBe("web/comedores/relevamientos/7/pnud/9/revision/");
    expect(relevamientosNavigation.assign).not.toHaveBeenCalled();
  });
});
