import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { acompanamientosNavigation } from "./acompanamientosList";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const LISTA = "/acompanamientos/acompanamiento/";
const API = "web/comedores/acompanamientos/";
const columns = {
  list_key: "acompanamientos_comedores_list", endpoint: "/ajax/columnas-preferencias/", modal_id: "m", script_id: "s",
  available: [{ key: "id", title: "ID", active: true, required: false, default: true }], active: ["id"], defaults: ["id"],
};
const page = { is_paginated: true, number: 1, count: 11, has_rows: true, previous: null, next: 2, range: [1, 2], query_without_page: "ordering=-nombre&" };
const list = (over: Record<string, unknown> = {}) => ({
  filters_config: { fields: [{ name: "comedor_nombre", label: "Nombre del comedor", type: "text" }, { name: "estado", label: "Estado de la admisión", type: "choice", choices: [{ value: "iniciada", label: "Iniciada" }] }] },
  favorites: { section: "acompanamientos", url: "/ajax/filtros-favoritos/", detail_url_template: "/ajax/filtros-favoritos/0/" },
  urls: { list: LISTA, reset: LISTA, export: `${LISTA}exportar/` }, can_export: true, columns,
  headers: [{ title: "ID", sort_url: null, sort_direction: null }, { title: "Nombre", sort_url: "?ordering=nombre", sort_direction: "desc" }],
  results: [{ cells: [{ content: "1", data_attr: null, data_value: null }, { content: "Comedor Norte", data_attr: "nombre", data_value: "Comedor Norte" }],
    actions: [{ label: "Ver Acompañamiento", url: `${LISTA}1/detalle/?admision_id=2`, type: "primary" }] }],
  page, messages: [], ...over,
});
const HITOS = ["retiro_tarjeta", "habilitacion_tarjeta"].map((campo, i) => ({ campo, descripcion: campo, completado: i === 0, fecha: i === 0 ? "05/11/2026" : "—" }));
const ficha = (over: Record<string, unknown> = {}) => ({
  comedor: { id: 1, nombre: "Comedor Norte" }, admision_id: 2,
  convenios: [{ id: 2, label: "CONV-7", activa: true, seleccionada: true }, { id: 1, label: "Admisión #1", activa: false, seleccionada: false }],
  multiples_activos: false, informacion: null, prestaciones: { dias: [], por_dia: [], semanal: [] }, hitos: HITOS, puede_restaurar: true,
  urls: { detalle: `${LISTA}1/detalle/`, intervenciones: "/comedores/1/intervencion/ver?admision_id=2", expedientes: "/expedientespagos/1/", seguimiento: "/rendicioncuentasmensual/1/",
    informe_complementario: null, comedor: "/comedores/1", restaurar: `/api/${API}1/hitos/restaurar/` },
  messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
let assign: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  assign = vi.spyOn(acompanamientosNavigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); assign.mockRestore(); });

describe("Acompañamientos route (AC01)", () => {
  it("owns the native list and ficha URLs with their trailing slash", () => {
    expect(findRoute(LISTA)?.params).toEqual({ page: "list" });
    expect(findRoute(`${LISTA}7/detalle/`)?.params).toEqual({ page: "detail", id: "7" });
    for (const other of ["/acompanamientos/acompanamiento", `${LISTA}7/detalle`, `${LISTA}exportar/`, `${LISTA}ajax/`, "/acompanamientos/comedor/7/restaurar-hito/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-acompanamientos");
    }
  });

  it("list: server ordering header, actions, pages and the native CSV GET", async () => {
    serve(list());
    setup(`${LISTA}?ordering=-nombre`);
    await screen.findByText("Comedores en Acompañamiento");
    expect(webGet).toHaveBeenCalledWith(`${API}?ordering=-nombre`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Comedores en Acompañamiento"));
    const nombre = screen.getByRole("link", { name: "Nombre" });
    expect(nombre.getAttribute("href")).toBe("?ordering=nombre");
    expect(nombre.querySelector("i")!.className).toBe("fas fa-sort-down");
    expect(screen.getByRole("link", { name: "Ver Acompañamiento" }).getAttribute("href")).toBe(`${LISTA}1/detalle/?admision_id=2`);
    expect(screen.getByText("Comedor Norte").getAttribute("data-nombre")).toBe("Comedor Norte");
    expect(screen.getByRole("link", { name: "2" }).getAttribute("href")).toBe("?ordering=-nombre&page=2");
    expect(screen.queryByText("Agregar")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Exportar búsqueda/ }));
    expect(assign).toHaveBeenCalledWith(`${LISTA}exportar/?ordering=-nombre`);
  });

  it("list: a choice filter shows its select and serializes the native filters JSON", async () => {
    serve(list({ results: [], page: { ...page, is_paginated: false, count: 0, has_rows: false }, can_export: false }));
    setup(LISTA);
    expect(await screen.findByText("No se encontraron comedores.")).toBeTruthy();
    expect(screen.queryByText(/Se encontraron \d/)).toBeNull();
    expect(screen.queryByRole("button", { name: /Exportar/ })).toBeNull();
    const campo = document.querySelector('[data-rol="campo"]') as HTMLSelectElement;
    fireEvent.change(campo, { target: { value: "estado" } });
    const valor = document.querySelector('[data-rol="valor-select"]') as HTMLSelectElement;
    expect(valor.hidden).toBe(false);
    fireEvent.change(valor, { target: { value: "iniciada" } });
    const form = document.getElementById("filters-form") as HTMLFormElement;
    form.addEventListener("submit", (e) => e.preventDefault());
    fireEvent.submit(form);
    expect((document.getElementById("filters-input") as HTMLInputElement).value).toBe(JSON.stringify({ logic: "AND", items: [{ field: "estado", op: "eq", value: "iniciada" }] }));
  });

  it("ficha: agreements, counters, header and the restore form state", async () => {
    serve(ficha());
    setup(`${LISTA}1/detalle/`);
    await screen.findByText("Listado de Hitos");
    await waitFor(() => expect(document.title).toBe("SISOC - Acompañamiento"));
    const block = document.querySelector(".app-content-header > .container-fluid:last-child")!;
    expect(block.innerHTML).toBe('<div class="row"><div class="col-12"><h2 class="mb-0">Comedor Norte</h2></div></div>');
    expect(document.querySelector(".app-content span[hidden]")).toBeNull();
    expect(screen.getByRole("link", { name: /CONV-7/ }).className).toContain("btn-primary");
    expect(screen.getByText("Cerrada")).toBeTruthy();
    expect(document.getElementById("completados-count")!.textContent).toBe("1");
    expect(document.getElementById("pendientes-count")!.textContent).toBe("1");
    expect(document.getElementById("total-count")!.textContent).toBe("2");
    const botones = document.querySelectorAll<HTMLButtonElement>("button.btn-restaurar");
    expect([botones[0].disabled, botones[1].disabled]).toEqual([false, true]);
    expect(screen.getByText("No hay información relevante disponible")).toBeTruthy();
    expect(screen.getByText("No hay prestaciones disponibles")).toBeTruthy();
  });

  it("ficha: restore posts the shown agreement and navigates to the redirect", async () => {
    serve(ficha());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, message: { level: "success", text: "ok" }, redirect: `${LISTA}1/detalle/?admision_id=2` } });
    setup(`${LISTA}1/detalle/`);
    fireEvent.click((await screen.findAllByRole("button", { name: /Restaurar/ }))[0]);
    await waitFor(() => expect(assign).toHaveBeenCalledWith(`${LISTA}1/detalle/?admision_id=2`));
    const [endpoint, body] = webPost.mock.calls[0];
    expect(endpoint).toBe(`${API}1/hitos/restaurar/`);
    expect(String(body)).toBe("campo=retiro_tarjeta&admision_id=2");
  });

  it("ficha: 409 shows the native text; 504 is uncertain and not retried", async () => {
    serve(ficha());
    webPost.mockResolvedValueOnce({ status: 409, data: { ok: false, message: { level: "error", text: "No se encontraron hitos para el convenio seleccionado." }, redirect: "/x/" } });
    setup(`${LISTA}1/detalle/`);
    fireEvent.click((await screen.findAllByRole("button", { name: /Restaurar/ }))[0]);
    expect(await screen.findByText("No se encontraron hitos para el convenio seleccionado.")).toBeTruthy();
    webPost.mockRejectedValueOnce({ response: { status: 504, data: { uncertain: true } } });
    fireEvent.click(screen.getAllByRole("button", { name: /Restaurar/ })[0]);
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    fireEvent.click(screen.getAllByRole("button", { name: /Restaurar/ })[0]);
    expect(webPost).toHaveBeenCalledTimes(2);
    expect(assign).not.toHaveBeenCalled();
  });

  it("ficha without milestones nor a technician shows the native empty block", async () => {
    serve(ficha({ hitos: null, puede_restaurar: false, convenios: [], admision_id: null }));
    setup(`${LISTA}3/detalle/`);
    expect(await screen.findByText("No hay información de hitos disponible")).toBeTruthy();
    expect(document.querySelector('[name="admision_id"]')).toBeNull();
  });
});
