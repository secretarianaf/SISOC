import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";
import { navigation } from "./userImport";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const BASE = "/comedores/configuracion/actividades-pnud/";
const session = {
  ...readyContext,
  navigation: [
    { id: "inicio", label: "Inicio", href: "/inicio/", children: [] },
    {
      id: "configuracion-comedores", label: "Configuración de Comedores", href: null, children: [
        { id: "actividades_pnud", label: "Actividades PNUD", href: BASE, children: [] },
      ],
    },
  ],
};
const page = { number: 1, count: 3, is_paginated: false, previous: null, next: null, range: [1], query_without_page: "estado=todas&" };
const list = (over: Record<string, unknown> = {}) => ({
  results: [
    { id: 1, categoria: "Cultura", actividad: "Teatro", activo: true },
    { id: 2, categoria: "Cultura", actividad: "Murga", activo: false },
  ],
  estado: "todas", q: "cul", can_manage: true, page, messages: [], ...over,
});
const values = { categoria: "", categoria_modo: "existente", categoria_existente: "", categoria_nueva: "", actividad: "", activo: true };
const form = (over: Record<string, unknown> = {}) => ({
  editar: false, values,
  categorias: [{ value: "", label: "Selecciona una categoria" }, { value: "Cultura", label: "Cultura" }, { value: "Deportes", label: "Deportes" }],
  actividad_max_length: 180, errors: {}, list_url: BASE, ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: session, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
let assign: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); assign.mockRestore(); });

describe("Actividades PNUD route", () => {
  it("owns the native catalog URLs with their trailing slashes", () => {
    expect(findRoute(BASE)?.params).toEqual({ mode: "list" });
    expect(findRoute(`${BASE}crear/`)?.params).toEqual({ mode: "crear" });
    expect(findRoute(`${BASE}4/editar/`)?.params).toEqual({ mode: "editar", id: "4" });
    expect(findRoute(`${BASE}4/baja/`)?.params).toEqual({ mode: "baja", id: "4" });
    for (const other of ["/comedores/configuracion/actividades-pnud", `${BASE}crear`, `${BASE}4/eliminar/`]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-actividades-pnud");
    }
  });

  it("lists with the search bar, estado filter and manage actions", async () => {
    serve(list({ messages: [{ message: "La actividad PNUD ya se encontraba inactiva.", level: "info" }] }));
    setup(`${BASE}?estado=todas&q=cul`);
    await screen.findByText("Teatro");
    expect(webGet).toHaveBeenCalledWith("web/comedores/actividades-pnud/?estado=todas&q=cul", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Actividades PNUD"));
    expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe("cul");
    expect(screen.getByRole("link", { name: "Todas" }).className).toBe("btn btn-primary");
    expect(screen.getByRole("link", { name: "Activas" }).getAttribute("href")).toBe(`${BASE}?estado=activa&q=cul`);
    expect((document.querySelector('input[name="estado"]') as HTMLInputElement).getAttribute("form")).toBe("simple-search-form");
    const [, teatro, murga] = screen.getAllByRole("row");
    expect(within(teatro).getByRole("link", { name: "Dar de baja" }).getAttribute("href")).toBe(`${BASE}1/baja/`);
    expect(within(murga).queryByRole("link", { name: "Dar de baja" })).toBeNull();
    expect(within(murga).getByText("Inactivo").className).toContain("actividades-pnud-status--inactive");
    expect(screen.getByRole("link", { name: "Agregar" }).getAttribute("href")).toBe(`${BASE}crear/`);
    expect(screen.getByText("Se encontraron 3 resultados")).toBeTruthy();
    expect(screen.getByRole("status").textContent).toBe("La actividad PNUD ya se encontraba inactiva.");
    expect(screen.getByRole("link", { name: "Actividades PNUD", current: "page" })).toBeTruthy();
  });

  it("shows a dash and no add button to read-only users, and no count line when empty", async () => {
    serve(list({ can_manage: false }));
    setup(BASE);
    await screen.findByText("Teatro");
    expect(screen.queryByRole("link", { name: "Agregar" })).toBeNull();
    expect(screen.getAllByText("-")).toHaveLength(2);
    cleanup();
    serve(list({ results: [], page: { ...page, count: 0 } }));
    setup(BASE);
    expect(await screen.findByText("No hay actividades cargadas.")).toBeTruthy();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("switches the category mode like the inline script and posts the native fields", async () => {
    serve(form());
    webPost.mockResolvedValue({ data: { ok: true, redirect: BASE }, status: 200 });
    setup(`${BASE}crear/`);
    await screen.findByText("Crear actividad");
    const nueva = screen.getByRole("button", { name: "Crear nueva" });
    fireEvent.change(screen.getByLabelText("Categoria existente"), { target: { value: "Cultura" } });
    fireEvent.click(nueva);
    expect(nueva.className).toBe("btn btn-sm btn-primary");
    expect((document.querySelector('[data-categoria-mode-field="existente"]') as HTMLElement).hidden).toBe(true);
    expect((screen.getByLabelText("Categoria existente") as HTMLSelectElement).value).toBe("");
    fireEvent.change(screen.getByLabelText("Nueva categoria"), { target: { value: "Salud" } });
    fireEvent.change(screen.getByLabelText("Actividad"), { target: { value: "Charla" } });
    fireEvent.click(screen.getByLabelText("Activo"));
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(BASE));
    const [endpoint, body] = webPost.mock.calls[0];
    expect(endpoint).toBe("web/comedores/actividades-pnud/crear/");
    expect((body as URLSearchParams).toString()).toBe("categoria=&categoria_modo=nueva&categoria_existente=&categoria_nueva=Salud&actividad=Charla");
  });

  it("re-renders the bound form with the native errors", async () => {
    serve(form());
    webPost.mockRejectedValue({ response: { status: 400, data: form({
      values: { ...values, categoria_modo: "nueva", actividad: "  " },
      errors: { actividad: [{ message: "Este campo es requerido.", code: "required" }], categoria_nueva: [{ message: "La categoria es obligatoria.", code: "" }] },
    }) } });
    setup(`${BASE}crear/`);
    await screen.findByText("Crear actividad");
    fireEvent.change(screen.getByLabelText("Actividad"), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Este campo es requerido.")).toBeTruthy();
    expect(document.getElementById("id_actividad_error")?.className).toBe("errorlist");
    expect(screen.getByLabelText("Nueva categoria").getAttribute("aria-invalid")).toBe("true");
    // The template never prints the category error of the mode fields.
    expect(screen.queryByText("La categoria es obligatoria.")).toBeNull();
    expect(screen.getByRole("button", { name: "Crear nueva" }).className).toBe("btn btn-sm btn-primary");
    expect(assign).not.toHaveBeenCalled();
  });

  it("edits with the current category selected", async () => {
    serve(form({ editar: true, values: { ...values, categoria: "Cultura", categoria_existente: "Cultura", actividad: "Murga", activo: false } }));
    setup(`${BASE}2/editar/`);
    await screen.findByText("Editar actividad");
    expect(webGet).toHaveBeenCalledWith("web/comedores/actividades-pnud/2/editar/", expect.anything());
    expect((screen.getByLabelText("Categoria existente") as HTMLSelectElement).value).toBe("Cultura");
    expect((screen.getByLabelText("Activo") as HTMLInputElement).checked).toBe(false);
    expect(screen.getByText("Editar", { selector: ".breadcrumb-item" })).toBeTruthy();
  });

  it("confirms the deactivation and posts it", async () => {
    serve({ categoria: "Cultura", actividad: "Teatro", cancel_url: BASE });
    webPost.mockResolvedValue({ data: { ok: true, redirect: BASE }, status: 200 });
    setup(`${BASE}1/baja/`);
    await screen.findByText("Cultura - Teatro");
    await waitFor(() => expect(document.title).toBe("SISOC - Dar de baja actividad PNUD"));
    expect(screen.getByText(/Se marcará como inactiva la actividad/).textContent).toBe("Se marcará como inactiva la actividad Cultura - Teatro.");
    fireEvent.click(screen.getByRole("button", { name: "Dar de baja" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(BASE));
    expect(webPost).toHaveBeenCalledWith("web/comedores/actividades-pnud/1/baja/", expect.any(URLSearchParams), expect.anything());
  });

  it("shows the access screen on a 403", async () => {
    serve({ detail: "No tiene permisos." }, 403);
    setup(`${BASE}crear/`);
    await waitFor(() => expect(document.title).toBe("SISOC - Error 403"));
    expect(webPost).not.toHaveBeenCalled();
  });
});
