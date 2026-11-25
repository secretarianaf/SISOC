import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { actaValid } from "./relevamientosActas";
import { relevamientosNavigation, takeFlash } from "./relevamientosApi";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const ACTA = "/comedores/7/acta-complementaria/5";
const caps = (over: Record<string, boolean> = {}) => ({ change_actacomplementaria: false, review_relevamiento: false, delete_actacomplementaria: false, ...over });
const acta = (over: Record<string, unknown> = {}, rev: Record<string, unknown> = {}) => ({
  acta: { id: 5, comedor: { id: 7, nombre: "Comedor <Uno>" }, fecha_hora: "4 Marzo 2026 12:07", tecnico: "Sin asignar", fecha_creacion: "5 Marzo 2026 10:00", observaciones: "Línea\ndos",
    estado: "Pendiente Revisión", estado_badge: "bg-warning text-dark", estado_validacion: "", a_subsanar: false, esta_validado: false, sin_cargar: false,
    observaciones_coordinador: "", coordinador: null, fecha_revision_coordinador: null, origen: "app", ...rev },
  prestaciones: [["Lunes", "Cena", "3", "-"]], adjuntos: [], capabilities: caps(),
  urls: { comedores: "/comedores/listar", comedor: "/comedores/7", listado: "/comedores/7/relevamiento/listar", editar: `${ACTA}/editar`, revision: `${ACTA}/revision`, eliminar: `${ACTA}/eliminar`, revision_api: "/api/web/comedores/relevamientos/7/actas/5/revision/", eliminar_api: "/api/web/comedores/relevamientos/7/actas/5/eliminar/" },
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
  window.sessionStorage.clear();
  vi.spyOn(relevamientosNavigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Actas complementarias route", () => {
  it("owns the detail path only", () => {
    expect(findRoute(ACTA)?.route.name).toBe("comedores-relevamientos-actas");
    for (const other of [`${ACTA}/`, `${ACTA}/editar`, "/comedores/7/acta-complementaria/crear", `${ACTA}/eliminar`, `${ACTA}/revision`]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-relevamientos-actas");
    }
  });

  it("renders the read-only detail with its heading, breadcrumb, summary and prestaciones", async () => {
    serve(acta());
    setup(ACTA);
    await screen.findByText("Resumen");
    expect(webGet).toHaveBeenCalledWith("web/comedores/relevamientos/7/actas/5/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Acta complementaria - Comedor: Comedor <Uno>"));
    expect(screen.getAllByRole("heading", { level: 3 })[0].textContent?.trim()).toBe("Comedor <Uno> | Acta complementaria extraordinaria | 4 Marzo 2026 12:07 App Pendiente Revisión");
    expect(screen.getByRole("link", { name: "Acompañamiento Territorial" }).getAttribute("href")).toBe("/comedores/7/relevamiento/listar");
    expect(screen.getByText("Acta complementaria", { selector: ".breadcrumb-item.active" })).toBeTruthy();
    expect(screen.getByText("Técnico", { exact: false }).querySelector("span")?.textContent).toBe("Sin asignar");
    expect(screen.getByText("Motivo / observaciones del cambio de prestación", { exact: false }).querySelector("span")?.innerHTML).toBe("Línea<br>dos");
    const card = screen.getByRole("heading", { level: 3, name: "Prestaciones" }).closest(".card")!;
    expect([...card.querySelectorAll("th")].map((t) => t.textContent)).toEqual(["Días", "Tipo", "Cantidad actual", "Cantidad en espera"]);
    for (const gone of ["Editar", "Revisar", "Eliminar"]) expect(screen.queryByText(gone)).toBeNull();
  });

  it("shows SISOC, the empty prestaciones and the default observation", async () => {
    serve(acta({ prestaciones: [] }, { origen: "sisoc", observaciones: "", fecha_hora: "Sin fecha", a_subsanar: true, estado_validacion: "A subsanar" }));
    setup(ACTA);
    await screen.findByText("El acta no tiene prestaciones cargadas.");
    expect(screen.getByText("SISOC", { selector: ".badge" }).className).toBe("badge bg-light text-dark ml-2");
    expect(screen.getByText("A subsanar", { selector: ".badge" })).toBeTruthy();
    expect(screen.getByText("Sin observaciones")).toBeTruthy();
  });

  it("offers the actions by capability and posts the review and the deletion natively", async () => {
    serve(acta({ capabilities: caps({ change_actacomplementaria: true, review_relevamiento: true, delete_actacomplementaria: true }) }, { observaciones_coordinador: "Corregir", coordinador: "rev", fecha_revision_coordinador: "6 Marzo 2026" }));
    setup(ACTA);
    await screen.findByText("Resumen");
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe(`${ACTA}/editar`);
    expect(screen.getByText("Observaciones del coordinador").parentElement?.textContent).toContain("(rev · 6 Marzo 2026)");
    fireEvent.click(screen.getByRole("button", { name: "Revisar" }));
    let dialog = await screen.findByRole("dialog");
    expect((dialog.querySelector("form") as HTMLFormElement).getAttribute("action")).toBe(`${ACTA}/revision`);
    expect(within(dialog).getByRole("combobox").getAttribute("id")).toBe("revision_acta_estado");
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Esta acción elimina el acta y sus prestaciones.")).toBeTruthy();
    const form = dialog.querySelector("form") as HTMLFormElement;
    expect([form.method, form.getAttribute("action")]).toEqual(["post", `${ACTA}/eliminar`]);
    expect((form.querySelector('[name="csrfmiddlewaretoken"]') as HTMLInputElement).value).toBe("synthetic-csrf-token");
  });

  it("hides the review button for a validated or unsent acta", async () => {
    serve(acta({ capabilities: caps({ review_relevamiento: true }) }, { esta_validado: true }));
    setup(ACTA);
    await screen.findByText("Resumen");
    expect(screen.queryByRole("button", { name: "Revisar" })).toBeNull();
  });

  it.each([403, 404])("answers %i with the existing screens", async (status) => {
    serve({ detail: "x" }, status);
    setup(ACTA);
    await waitFor(() => expect(document.querySelector("main")).toBeTruthy());
    expect(screen.queryByText("Resumen")).toBeNull();
  });

  it("rejects malformed payloads", () => {
    expect(actaValid(acta())).toBe(true);
    expect(actaValid(acta({ prestaciones: [["a", 1]] }))).toBe(false);
    expect(actaValid(acta({ urls: { ...acta().urls, eliminar: "javascript:alert(1)" } }))).toBe(false);
  });
});

describe("Acta actions through the API", () => {
  const all = () => acta({ capabilities: caps({ review_relevamiento: true, delete_actacomplementaria: true }) });

  it("reviews through the API, flashes the message and goes to the detail", async () => {
    serve(all());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, message: "Acta complementaria validada correctamente.", redirect: ACTA } });
    setup(ACTA);
    fireEvent.click(await screen.findByRole("button", { name: "Revisar" }));
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Guardar revisión" }));
    await waitFor(() => expect(relevamientosNavigation.assign).toHaveBeenCalledWith(ACTA));
    const [url, body] = webPost.mock.calls[0] as [string, URLSearchParams];
    expect(url).toBe("web/comedores/relevamientos/7/actas/5/revision/");
    expect([body.get("estado_validacion"), body.get("observaciones_coordinador")]).toEqual(["Validado", ""]);
    expect(takeFlash()).toEqual([{ message: "Acta complementaria validada correctamente.", level: "success" }]);
  });

  it("shows a review rejection as a toast and keeps the page", async () => {
    serve(all());
    webPost.mockResolvedValue({ status: 409, data: { detail: "El acta complementaria ya está validada: no admite otra revisión." } });
    setup(ACTA);
    fireEvent.click(await screen.findByRole("button", { name: "Revisar" }));
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Guardar revisión" }));
    await screen.findByText("El acta complementaria ya está validada: no admite otra revisión.");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(relevamientosNavigation.assign).not.toHaveBeenCalled();
  });

  it("deletes through the API to the list and never resends a lost answer", async () => {
    serve(all());
    webPost.mockResolvedValueOnce({ status: 504, data: { uncertain: true } });
    setup(ACTA);
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));
    let dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Eliminar" }));
    await screen.findByText("No se pudo confirmar el resultado.", { exact: false });
    expect((within(dialog).getByRole("button", { name: "Eliminar" }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/comedores/relevamientos/7/actas/5/eliminar/");
    cleanup();
    vi.clearAllMocks();
    serve(all());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, message: "Acta complementaria eliminada correctamente.", redirect: "/comedores/7/relevamiento/listar" } });
    setup(ACTA);
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));
    dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Eliminar" }));
    await waitFor(() => expect(relevamientosNavigation.assign).toHaveBeenCalledWith("/comedores/7/relevamiento/listar"));
    expect(takeFlash()).toEqual([{ message: "Acta complementaria eliminada correctamente.", level: "success" }]);
  });
});
