import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { papeleraValid } from "./corePapelera";
import { corePapeleraNavigation, restaurarValid } from "./corePapeleraRestaurar";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const filter = (id: string, label: string, over: Record<string, unknown> = {}) => ({ id: `id_${id}`, label, value: "", attrs: { class: "form-control" }, ...over });
const lista = (over = {}) => ({
  filters: {
    model: filter("model", "Modelo", { attrs: { class: "form-select" }, choices: [{ value: "", label: "Todos los modelos" }, { value: "ciudadanos.Ciudadano", label: "Ciudadanos" }] }),
    q: filter("q", "Búsqueda", { attrs: { class: "form-control", type: "text", placeholder: "ID o texto" } }),
    deleted_by: filter("deleted_by", "Eliminado por", { attrs: { class: "form-control", type: "text", placeholder: "Usuario o nombre" } }),
    deleted_from: filter("deleted_from", "Desde", { attrs: { class: "form-control", type: "date" } }),
    deleted_to: filter("deleted_to", "Hasta", { attrs: { class: "form-control", type: "date" } }),
  },
  filter_errors: [], active_filters: [], selected_model_label: "Todos los modelos", show_all_models: true, deleted_count: 2,
  rows: [
    { id: 4, label: "Baja, Ana", model_label: "Ciudadano", deleted_at: "13/11/2026 09:05", deleted_by: "Quien Borra", restore_url: "/papelera/preview-restore/ciudadanos/ciudadano/4/?next=/papelera/" },
    { id: 5, label: "Otra", model_label: "Ciudadano", deleted_at: "12/11/2026 08:00", deleted_by: null, restore_url: "/papelera/preview-restore/ciudadanos/ciudadano/5/?next=/papelera/" },
  ],
  pagination: { num_pages: 1, number: 1, previous: null, next: null, querystring: "" },
  urls: { list: "/papelera/", home: "/inicio/" }, messages: [], ...over,
});
const previa = (over = {}) => ({
  id: 4, label: "Baja, Ana", model_identifier: "ciudadanos.ciudadano", total_afectados: 3,
  details: [{ label: "Id", value: "4" }, { label: "Nombre", value: "-" }],
  breakdown: [{ modelo: "Ciudadano", cantidad: 1, ejemplos: ["Baja, Ana"] }, { modelo: "Grupo familiar", cantidad: 2, ejemplos: [] }],
  restore_url: "/papelera/restore/ciudadanos/ciudadano/4/", back_url: "/papelera/?model=ciudadanos.Ciudadano", next_url: "/papelera/?page=2",
  urls: { home: "/inicio/", list: "/papelera/" }, messages: [], ...over,
});
const serve = (data: unknown, status = 200) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("papelera (T06.01)", () => {
  it("owns /papelera/ and the restore preview and validates the payloads", () => {
    expect(findRoute("/papelera/")?.route.name).toBe("core-papelera");
    expect(findRoute("/papelera/preview-restore/ciudadanos/ciudadano/4/")?.params).toEqual({ app: "ciudadanos", model: "ciudadano", pk: "4" });
    expect(findRoute("/papelera/restore/ciudadanos/ciudadano/4/")?.route.name).not.toBe("core-papelera-restaurar");
    expect(papeleraValid(lista())).toBe(true);
    expect(papeleraValid(lista({ rows: [{ id: "x" }] }))).toBe(false);
    expect(papeleraValid(lista({ urls: { list: "http://evil/", home: "/inicio/" } }))).toBe(false);
  });

  it("draws the native filters, rows and the combined-listing badges, asking with the page's query string", async () => {
    window.history.replaceState({}, "", "/papelera/?model=ciudadanos.Ciudadano&page=1");
    serve(lista({ messages: [{ message: "Restauración completada. Registros restaurados: 2.", level: "success" }] }));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Papelera Global" })).toBeTruthy();
    expect(webGet.mock.calls.map((c) => c[0])).toContain("web/core/papelera/?model=ciudadanos.Ciudadano&page=1");
    expect((screen.getByLabelText("Búsqueda:") as HTMLInputElement).placeholder).toBe("ID o texto");
    expect((screen.getByLabelText("Desde:") as HTMLInputElement).type).toBe("date");
    expect(screen.getByLabelText("Modelo:").className).toBe("form-select");
    expect(screen.getByText("Busca por ID o texto del registro eliminado.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Aplicar" }).getAttribute("type")).toBe("submit");
    expect(screen.getByRole("link", { name: "Limpiar" }).getAttribute("href")).toBe("/papelera/");
    expect(screen.getByText("Listado combinado")).toBeTruthy();
    expect(screen.getByText("Eliminados: 2")).toBeTruthy();
    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getByText("Quien Borra")).toBeTruthy();
    expect(within(rows[2]).getByText("-").className).toBe("text-muted");
    expect(within(rows[1]).getByRole("link", { name: "Restaurar" }).getAttribute("href")).toBe("/papelera/preview-restore/ciudadanos/ciudadano/4/?next=/papelera/");
    expect(screen.getByText("Restauración completada. Registros restaurados: 2.")).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Papelera"));
  });

  it("shows filter errors, the active-filter summary and the empty state", async () => {
    window.history.replaceState({}, "", "/papelera/");
    serve(lista({
      rows: [], deleted_count: 0, show_all_models: false, selected_model_label: "Ciudadanos",
      filter_errors: ["__all__: La fecha 'Desde' no puede ser posterior a la fecha 'Hasta'."],
      active_filters: [{ label: "Modelo", value: "Ciudadanos" }, { label: "Búsqueda", value: "ana" }],
    }));
    render(<App />);
    expect(await screen.findByText("No hay registros eliminados para este modelo.")).toBeTruthy();
    expect(screen.getByText("Ajustá los filtros o usá “Limpiar” para volver al listado completo.")).toBeTruthy();
    expect(screen.getByText("Modelo: Ciudadanos")).toBeTruthy();
    expect(screen.getByText("Búsqueda: ana")).toBeTruthy();
    expect(screen.getByText(/La fecha 'Desde' no puede ser posterior/)).toBeTruthy();
    expect(screen.queryByText("Listado combinado")).toBeNull();
  });

  it("paginates with the other parameters kept in each link", async () => {
    window.history.replaceState({}, "", "/papelera/?model=x&page=2");
    serve(lista({ pagination: { num_pages: 3, number: 2, previous: 1, next: 3, querystring: "model=x" } }));
    render(<App />);
    expect(await screen.findByText("Página 2 de 3")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Anterior" }).getAttribute("href")).toBe("?page=1&model=x");
    expect(screen.getByRole("link", { name: "Siguiente" }).getAttribute("href")).toBe("?page=3&model=x");
  });

  it("shows the access screen when the user is not a superuser (403)", async () => {
    window.history.replaceState({}, "", "/papelera/");
    serve({ detail: "No tiene permisos para esta acción." }, 403);
    render(<App />);
    await waitFor(() => expect(screen.queryByText("Cargando papelera…")).toBeNull());
    expect(screen.queryByRole("heading", { name: "Papelera Global" })).toBeNull();
  });
});

describe("restauración (T06.02)", () => {
  const url = "/papelera/preview-restore/ciudadanos/ciudadano/4/?next=%2Fpapelera%2F%3Fpage%3D2";

  it("validates the preview payload", () => {
    expect(restaurarValid(previa())).toBe(true);
    expect(restaurarValid(previa({ next_url: "http://evil/" }))).toBe(false);
    expect(restaurarValid(previa({ breakdown: [{ modelo: 1 }] }))).toBe(false);
  });

  it("draws the cascade preview and asks the API with the page's own query string", async () => {
    window.history.replaceState({}, "", url);
    serve(previa());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Confirmar restauración" })).toBeTruthy();
    expect(webGet.mock.calls.map((c) => c[0])).toContain("web/core/papelera/restaurar/ciudadanos/ciudadano/4/?next=%2Fpapelera%2F%3Fpage%3D2");
    expect(screen.getByText("Vista previa de restauración")).toBeTruthy();
    expect(screen.getByText("ID 4")).toBeTruthy();
    expect(screen.getByText("Total afectados:").parentElement?.textContent).toBe("Total afectados: 3");
    expect(screen.getByText("Modelo: ciudadanos.ciudadano")).toBeTruthy();
    expect(screen.getByText("Baja, Ana", { selector: "td" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Volver al listado" }).getAttribute("href")).toBe("/papelera/?model=ciudadanos.Ciudadano");
    expect(screen.getByRole("link", { name: "Papelera" }).getAttribute("href")).toBe("/papelera/?model=ciudadanos.Ciudadano");
    await waitFor(() => expect(document.title).toBe("SISOC - Confirmar Restauración"));
  });

  it("shows the empty breakdown message", async () => {
    window.history.replaceState({}, "", url);
    serve(previa({ breakdown: [] }));
    render(<App />);
    expect(await screen.findByText("No hay elementos a restaurar.")).toBeTruthy();
  });

  it("confirms once with confirmed=1 and the safe next, then follows the redirect", async () => {
    window.history.replaceState({}, "", url);
    serve(previa());
    const assign = vi.spyOn(corePapeleraNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/papelera/?page=2" }, status: 200 });
    render(<App />);
    const boton = await screen.findByRole("button", { name: "Restaurar en cascada" });
    fireEvent.click(boton);
    fireEvent.click(boton);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/papelera/?page=2"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/core/papelera/restaurar/ciudadanos/ciudadano/4/");
    const body = webPost.mock.calls[0][1] as URLSearchParams;
    expect(body.get("confirmed")).toBe("1");
    expect(body.get("next")).toBe("/papelera/?page=2");
  });

  it("omits next when the preview has none, and shows a refusal or an unconfirmed outcome without navigating", async () => {
    window.history.replaceState({}, "", "/papelera/preview-restore/ciudadanos/ciudadano/4/");
    serve(previa({ next_url: null }));
    const assign = vi.spyOn(corePapeleraNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValueOnce({ data: { detail: "No tiene permisos para esta acción." }, status: 403 });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Restaurar en cascada" }));
    expect((await screen.findByRole("alert")).textContent).toBe("No tiene permisos para esta acción.");
    expect((webPost.mock.calls[0][1] as URLSearchParams).has("next")).toBe(false);
    cleanup();
    webPost.mockRejectedValueOnce(new Error("network"));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Restaurar en cascada" }));
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudo confirmar el resultado");
    expect(assign).not.toHaveBeenCalled();
    expect(webPost).toHaveBeenCalledTimes(2);
  });
});
