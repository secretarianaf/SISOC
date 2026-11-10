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

const LIST = "/montoprestacion/listar";
const session = {
  ...readyContext,
  navigation: [
    { id: "inicio", label: "Inicio", href: "/inicio/", children: [] },
    {
      id: "configuracion-comedores", label: "Configuración de Comedores", href: null, children: [
        { id: "montoprestacion_listar", label: "Monto de Prestaciones", href: LIST, children: [] },
        { id: "actividades_pnud", label: "Actividades PNUD", href: "/comedores/configuracion/actividades-pnud/", children: [] },
      ],
    },
    { id: "mi_cuenta", label: "Mi cuenta", href: "/mi-cuenta/", children: [] },
  ],
};
const monto = (id: number, extra: Record<string, unknown> = {}) => ({
  id, programa: "Alimentar Comunidad", desayuno_valor: "1025,50", almuerzo_valor: "None", merienda_valor: "0,00", cena_valor: "1234,75",
  usuario_creador: "gestion.montos", fecha_creacion: "09/11/2026 12:00", fecha_modificacion: "10/11/2026 11:00", ...extra,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [monto(1), monto(2, { programa: "Abordaje Comunitario" })],
  page: { number: 1, count: 12, is_paginated: true, previous: null, next: 2, range: [1, 2], query_without_page: "" },
  urls: { listar: LIST, crear: "/montoprestacion/crear" },
  messages: [],
  ...over,
});
const crumbs = (last: string) => [{ text: "Monto de Prestaciones", url: LIST }, { text: last, url: null }];
const back = { url: LIST, text: "Volver", type: "outline-light" };
const field = (name: string, label: string, value = "", required = false) => ({ name, label, required, value });
const form = (over: Record<string, unknown> = {}) => ({
  breadcrumb: crumbs("Crear Monto de Prestación"),
  back_button: back,
  fields: [
    { ...field("programa", "Programa", "", true), choices: [{ value: "", label: "---------" }, { value: "2", label: "Abordaje Comunitario" }, { value: "1", label: "Alimentar Comunidad" }] },
    field("desayuno_valor", "Valor desayuno"), field("almuerzo_valor", "Valor almuerzo"), field("merienda_valor", "Valor merienda"), field("cena_valor", "Valor cena", "3702.75"),
  ],
  errors: {},
  ...over,
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

describe("Montos de prestación route", () => {
  it("owns exactly the native montoprestacion URLs, without trailing slashes", () => {
    expect(findRoute("/montoprestacion/listar")?.params).toEqual({ mode: "listar" });
    expect(findRoute("/montoprestacion/crear")?.params).toEqual({ mode: "crear" });
    expect(findRoute("/montoprestacion/7/editar")?.params).toEqual({ mode: "editar", id: "7" });
    expect(findRoute("/montoprestacion/7/eliminar")?.params).toEqual({ mode: "eliminar", id: "7" });
    expect(findRoute("/montoprestacion/7/detalle")?.params).toEqual({ mode: "detalle", id: "7" });
    for (const other of ["/montoprestacion/listar/", "/montoprestacion/x/editar", "/montoprestacion/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-montos");
    }
  });

  it("lists the native rows, actions, pagination and the menu entry as active", async () => {
    serve(list({ messages: [{ message: "Monto de Prestación creada correctamente.", level: "success" }] }));
    setup(`${LIST}?page=1`);
    await screen.findByText("Abordaje Comunitario");
    expect(webGet).toHaveBeenCalledWith("web/session/", expect.anything());
    expect(webGet).toHaveBeenCalledWith("web/comedores/montos/?page=1", expect.anything());
    expect(document.title).toBe("SISOC - Prestaciones");
    expect(document.body.classList.contains("app-loaded")).toBe(true);
    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getAllByRole("cell").map((c) => c.textContent)).toEqual([
      "Alimentar Comunidad", "1025,50", "None", "0,00", "1234,75", "gestion.montos", "09/11/2026 12:00", "10/11/2026 11:00", "Ver Editar Eliminar",
    ]);
    expect(within(rows[1]).getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/montoprestacion/1/editar");
    expect(within(rows[1]).getByRole("link", { name: "Eliminar" }).getAttribute("href")).toBe("/montoprestacion/1/eliminar");
    expect(screen.getByRole("link", { name: "Agregar" }).getAttribute("href")).toBe("/montoprestacion/crear");
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?page=2");
    expect(screen.getByText("Se encontraron 12 resultados")).toBeTruthy();
    expect(screen.getByRole("status").textContent).toBe("Monto de Prestación creada correctamente.");
    expect(screen.getByRole("link", { name: "Monto de Prestaciones", current: "page" })).toBeTruthy();
  });

  it("shows the native empty row", async () => {
    serve(list({ results: [], page: { number: 1, count: 0, is_paginated: false, previous: null, next: null, range: [1], query_without_page: "" } }));
    setup(LIST);
    expect(await screen.findByText("No hay montos de prestaciones cargados.")).toBeTruthy();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
    expect(screen.queryByRole("link", { name: "Continuar" })).toBeNull();
  });

  it("renders the detail table and keeps the montos menu active", async () => {
    serve({ breadcrumb: crumbs("Detalle"), back_button: back, monto: monto(3) });
    setup("/montoprestacion/3/detalle");
    await screen.findByText("Detalle de Monto de Prestación");
    expect(webGet).toHaveBeenCalledWith("web/comedores/montos/3/", expect.anything());
    expect(document.title).toBe("SISOC - Monto de Prestación");
    expect(screen.getByRole("row", { name: "Valor almuerzo None" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Monto de Prestaciones", current: "page" })).toBeTruthy();
  });

  it("posts the create form as the native fields and follows the redirect", async () => {
    serve(form());
    webPost.mockResolvedValue({ data: { ok: true, redirect: LIST }, status: 200 });
    setup("/montoprestacion/crear");
    await screen.findByText("Datos de Monto de Prestación");
    expect(document.title).toBe("SISOC - Monto Prestación");
    expect(screen.getByRole("heading", { level: 3, name: "Monto de Prestación" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Programa*"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Valor desayuno"), { target: { value: "150.25" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(LIST));
    const [endpoint, body] = webPost.mock.calls[0];
    expect(endpoint).toBe("web/comedores/montos/crear/");
    expect((body as URLSearchParams).toString()).toBe("programa=2&desayuno_valor=150.25&almuerzo_valor=&merienda_valor=&cena_valor=3702.75");
  });

  it("re-renders the bound form with the native errors after a 400", async () => {
    serve(form());
    const invalid = form({
      errors: {
        __all__: [{ message: "Debe informar al menos un monto.", code: "" }],
        programa: [{ message: "Este campo es requerido.", code: "required" }],
      },
    });
    webPost.mockRejectedValue({ response: { status: 400, data: invalid } });
    setup("/montoprestacion/crear");
    await screen.findByText("Datos de Monto de Prestación");
    fireEvent.submit(screen.getByRole("button", { name: "Guardar" }).closest("form")!);
    expect(await screen.findByText("Debe informar al menos un monto.")).toBeTruthy();
    const select = screen.getByLabelText("Programa*");
    expect(select.className).toContain("is-invalid");
    expect(select.getAttribute("aria-describedby")).toBe("id_programa_error");
    expect(document.getElementById("error_1_id_programa")?.textContent).toBe("Este campo es requerido.");
    expect(assign).not.toHaveBeenCalled();
  });

  it("edits through its own endpoint", async () => {
    serve(form({ breadcrumb: crumbs("Editar Monto de Prestación") }));
    webPost.mockResolvedValue({ data: { ok: true, redirect: LIST }, status: 200 });
    setup("/montoprestacion/4/editar");
    await screen.findByText("Editar Monto de Prestación");
    expect((screen.getByLabelText("Valor cena") as HTMLInputElement).value).toBe("3702.75");
    fireEvent.change(screen.getByLabelText("Programa*"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(webPost).toHaveBeenCalledWith("web/comedores/montos/4/editar/", expect.any(URLSearchParams), expect.anything()));
  });

  it("confirms and deletes with the native texts", async () => {
    serve({
      breadcrumb: crumbs("Eliminar Monto de Prestación"), object_name: "ALIMENTAR COMUNIDAD",
      delete_message: "¿Desea eliminar este monto de prestación? Esta acción no se puede deshacer.", cancel_url: LIST,
    });
    webPost.mockResolvedValue({ data: { ok: true, redirect: LIST }, status: 200 });
    setup("/montoprestacion/5/eliminar");
    await screen.findByText("ALIMENTAR COMUNIDAD");
    expect(document.title).toBe("SISOC - Confirmar Eliminación");
    expect(screen.getByText(/¿Desea eliminar este monto de prestación\? Esta acción no se puede deshacer\./).textContent)
      .toBe("¿Desea eliminar este monto de prestación? Esta acción no se puede deshacer. ALIMENTAR COMUNIDAD?");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe(LIST);
    fireEvent.click(screen.getByRole("button", { name: "Dar de baja" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(LIST));
    expect(webPost).toHaveBeenCalledWith("web/comedores/montos/5/eliminar/", expect.any(URLSearchParams), expect.anything());
  });

  it("shows the access screen on a 403 and a load error on an unexpected shape", async () => {
    serve({ detail: "No tiene permisos." }, 403);
    setup(LIST);
    await waitFor(() => expect(document.title).toBe("SISOC - Error 403"));
    cleanup();
    serve({ results: "x" });
    setup(LIST);
    expect(await screen.findByRole("alert")).toBeTruthy();
  });

  it("keeps the native required program check before posting", async () => {
    serve(form());
    setup("/montoprestacion/crear");
    await screen.findByText("Datos de Monto de Prestación");
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await new Promise((r) => setTimeout(r, 50));
    expect(webPost).not.toHaveBeenCalled();
  });

  it("does not navigate when the write result cannot be confirmed", async () => {
    serve(form());
    webPost.mockRejectedValue({ response: { status: 502 } });
    setup("/montoprestacion/crear");
    await screen.findByText("Datos de Monto de Prestación");
    fireEvent.change(screen.getByLabelText("Programa*"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
  });
});
