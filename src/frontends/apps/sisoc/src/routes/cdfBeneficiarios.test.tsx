import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { listNavigation } from "./cdfDataTable";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const columnas = (key: string) => ({
  list_key: key, endpoint: "/ajax/columnas-preferencias/", modal_id: `column-config-modal-${key}`, script_id: `column-config-data-${key}`,
  available: [{ key: "cuil", title: "CUIL", active: true, required: false, default: true }, { key: "dni", title: "DNI", active: true, required: false, default: true }],
  active: ["cuil", "dni"], defaults: ["cuil", "dni"],
});
const lista = (over: Record<string, unknown> = {}) => ({
  breadcrumb: [{ text: "Beneficiarios", url: "/centrodefamilia/beneficiarios/beneficiarios/" }, { text: "Listar", url: null }],
  filters_config: { fields: [{ name: "dni", label: "DNI", type: "number" }] },
  favorites: { section: "cdf_beneficiarios", url: "/ajax/filtros-favoritos/", detail_url_template: "/ajax/filtros-favoritos/0/" },
  columns: columnas("centrodefamilia_beneficiarios_list"),
  headers: [{ title: "CUIL", width: "10%", sortable: true, sort_key: "cuil" }, { title: "DNI", width: "9%", sortable: true, sort_key: "dni" }],
  results: [
    { id: 2, cells: ["20000000002", "40000002"], url: "/centrodefamilia/beneficiarios/beneficiarios/2/" },
    { id: 1, cells: ["20000000001", "40000003"], url: "/centrodefamilia/beneficiarios/beneficiarios/1/" },
  ],
  count: 12, page: 1, page_size: 10, pages: 2, has_next: true, has_previous: false, page_range: [1, 2], is_paginated: true,
  query_without_page: "", filters: { filters: "" }, messages: [],
  can_export: true,
  urls: {
    list: "/centrodefamilia/beneficiarios/beneficiarios/", reset: "/centrodefamilia/beneficiarios/beneficiarios/", add: "/centrodefamilia/beneficiarios/nuevo/",
    export: "/centrodefamilia/beneficiarios/beneficiarios/exportar/", export_available: "/api/web/cdf/beneficiarios/exportar/disponible/",
  },
  ...over,
});
const detalle = {
  id: 1, nombre_completo: "Ben, Sol", dni: "40000001", cuil: "20000000001", genero_display: "Femenino", fecha_nacimiento: "01/03/2012",
  correo_electronico: "No especificado", fecha_creado: "10/11/2026 09:30",
  responsable: { nombre_completo: "Resp, Ana", dni: "30000001", cuil: "27000000001", vinculo_display: "Padre/Madre", celular: "11-4000", url: "/centrodefamilia/beneficiarios/responsables/5/" },
  domicilio: { domicilio: "D", calle: "C 742", provincia: "BA", municipio: "None", localidad: "None", codigo_postal: "No especificado", barrio: "No especificado" },
  academico: { estudia: false, nivel_actual: null, maximo_nivel: "Primario incompleto", institucion: "No especificada" },
  actividad_preferida: ["Deportiva"], actividades_extracurriculares: true, actividades_detalle: [], messages: [],
};
const responsable = (vinculos: unknown[]) => ({
  id: 5, nombre_completo: "Resp, Ana", dni: "30000001", cuil: "27000000001", genero_display: "Femenino", fecha_nacimiento: "01/01/1980",
  celular: "No especificado", telefono_fijo: "No especificado", correo_electronico: "No especificado",
  domicilio: { calle: "C ", piso_vivienda: "No especificado", departamento_vivienda: "No especificado", barrio: "No especificado", provincia: "BA",
    municipio: "None", localidad: "None", codigo_postal: "No especificado", monoblock: "No especificado" },
  vinculos, messages: [],
});

function serve(routes: Record<string, unknown>) {
  webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
    : url in routes ? Promise.resolve({ data: routes[url], status: 200 }) : Promise.reject(new Error(url))));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CDF beneficiaries and responsables routes", () => {
  it("owns the native list, detail and preinscription paths", () => {
    expect(findRoute("/centrodefamilia/beneficiarios/beneficiarios/")?.params).toEqual({ screen: "beneficiarios" });
    expect(findRoute("/centrodefamilia/beneficiarios/beneficiarios/7/")?.params).toEqual({ screen: "beneficiarios", id: "7" });
    expect(findRoute("/centrodefamilia/beneficiarios/responsables/")?.params).toEqual({ screen: "responsables" });
    expect(findRoute("/centrodefamilia/beneficiarios/responsables/3/")?.params).toEqual({ screen: "responsables", id: "3" });
    expect(findRoute("/centrodefamilia/beneficiarios/nuevo/")?.params).toEqual({ screen: "nuevo" });
    expect(findRoute("/centrodefamilia/beneficiarios/beneficiarios/exportar/")?.route.name).not.toBe("cdf-beneficiarios");
  });

  it("renders the exact list with count, actions and native links", async () => {
    serve({ "web/cdf/beneficiarios/": lista() });
    setup("/centrodefamilia/beneficiarios/beneficiarios/");
    await screen.findByText("Listado de Preinscriptos");
    await waitFor(() => expect(document.title).toBe("SISOC - Listado de Preinscriptos"));
    expect(screen.getByRole("heading", { name: "Preinscriptos" })).toBeTruthy();
    expect(screen.getByText("Buscar Beneficiario")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Crear un nuevo Preinscripto/ }).getAttribute("href")).toBe("/centrodefamilia/beneficiarios/nuevo/");
    expect(screen.getByText("Se encontraron 12 resultados")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Siguiente" }).getAttribute("href")).toBe("?page=2");
    expect(screen.getByRole("link", { name: "Anterior" }).getAttribute("href")).toBe("#");
    expect(screen.getAllByRole("link", { name: "Ver" })[0].getAttribute("href")).toBe("/centrodefamilia/beneficiarios/beneficiarios/2/");
    expect((document.querySelector("th[data-column=cuil]") as HTMLElement).style.width).toBe("10%");
    expect(screen.getByRole("button", { name: /Exportar búsqueda/ }).getAttribute("title")).toBe("Descargar listado actual en CSV");
  });

  it("warns without navigating when the CSV would be empty", async () => {
    const assign = vi.spyOn(listNavigation, "assign").mockImplementation(() => undefined);
    serve({ "web/cdf/beneficiarios/": lista(), "web/cdf/beneficiarios/exportar/disponible/": { exists: false, message: "No hay beneficiarios para exportar con el filtro aplicado." } });
    setup("/centrodefamilia/beneficiarios/beneficiarios/");
    fireEvent.click(await screen.findByRole("button", { name: /Exportar búsqueda/ }));
    await screen.findByText("No hay beneficiarios para exportar con el filtro aplicado.");
    expect(assign).not.toHaveBeenCalled();
  });

  it("navigates to the native CSV with the active local sort", async () => {
    const assign = vi.spyOn(listNavigation, "assign").mockImplementation(() => undefined);
    serve({ "web/cdf/beneficiarios/": lista(), "web/cdf/beneficiarios/exportar/disponible/": { exists: true, message: "" } });
    setup("/centrodefamilia/beneficiarios/beneficiarios/");
    const dni = await screen.findByText("DNI", { selector: "th" });
    fireEvent.click(dni);
    fireEvent.click(dni);
    expect(document.querySelector("tbody tr td")?.textContent).toBe("20000000001");
    fireEvent.click(screen.getByRole("button", { name: /Exportar búsqueda/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodefamilia/beneficiarios/beneficiarios/exportar/?sort=dni&direction=desc"));
  });

  it("hides the export button without the export permission and shows the empty text", async () => {
    serve({ "web/cdf/beneficiarios/": lista({ can_export: false, results: [], count: 0, is_paginated: false }) });
    setup("/centrodefamilia/beneficiarios/beneficiarios/");
    await screen.findByText("No hay beneficiarios disponibles.");
    expect(screen.queryByRole("button", { name: /Exportar búsqueda/ })).toBeNull();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("renders the NoCount responsables list without total nor add button", async () => {
    serve({ "web/cdf/responsables/": lista({
      breadcrumb: [{ text: "Responsables", url: "/centrodefamilia/beneficiarios/responsables/" }, { text: "Listar", url: null }],
      columns: columnas("centrodefamilia_responsables_list"), count: null, pages: null, page_range: [1, 2, "..."],
      urls: { list: "/centrodefamilia/beneficiarios/responsables/", reset: "/centrodefamilia/beneficiarios/responsables/" },
    }) });
    setup("/centrodefamilia/beneficiarios/responsables/");
    await screen.findByText("Listado de Responsables");
    await waitFor(() => expect(document.title).toBe("SISOC - Listado de responsables"));
    expect(screen.getByText("Buscar Responsable")).toBeTruthy();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
    expect(screen.queryByRole("link", { name: /Agregar|Crear/ })).toBeNull();
    expect(screen.getByText("...")).toBeTruthy();
  });

  it("renders the beneficiary detail cards", async () => {
    serve({ "web/cdf/beneficiarios/1/": detalle });
    setup("/centrodefamilia/beneficiarios/beneficiarios/1/");
    await screen.findByRole("heading", { name: "Ben, Sol" });
    await waitFor(() => expect(document.title).toBe("SISOC - Detalle del Preinscripto"));
    expect(screen.getByText("Información Personal")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver detalle" }).getAttribute("href")).toBe("/centrodefamilia/beneficiarios/responsables/5/");
    expect(screen.getByText("11-4000")).toBeTruthy();
    expect(screen.getByText("No estudiando")).toBeTruthy();
    expect(screen.queryByText("Nivel Actual")).toBeNull();
    expect(screen.getByText("Deportiva").className).toBe("cdf-pill cdf-pill--teal");
    expect(screen.getByText("Sí, pero sin detalles especificados")).toBeTruthy();
  });

  it("renders the responsable detail with its beneficiaries or the empty state", async () => {
    serve({
      "web/cdf/responsables/5/": responsable([{ beneficiario_id: 1, cuil: "20000000001", apellido_nombre: "Ben, Sol", dni: "40000001", genero_display: "Femenino",
        fecha_nacimiento: "01/03/2012", vinculo_display: "Tutor/Tutora", fecha_creado: "10/11/2026 09:30", url: "/centrodefamilia/beneficiarios/beneficiarios/1/" }]),
      "web/cdf/responsables/6/": responsable([]),
    });
    const view = setup("/centrodefamilia/beneficiarios/responsables/5/");
    await screen.findByText("1 preinscripto(s) a cargo");
    expect(screen.getByText("Tutor/Tutora")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver" }).getAttribute("href")).toBe("/centrodefamilia/beneficiarios/beneficiarios/1/");
    view.unmount();
    setup("/centrodefamilia/beneficiarios/responsables/6/");
    await screen.findByText("Sin preinscriptos asignados");
    expect(screen.getByText("Este responsable no tiene preinscriptos a cargo.")).toBeTruthy();
  });

  it("keeps the API 403 and 404", async () => {
    webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
      : Promise.resolve({ data: { detail: "x" }, status: 404 })));
    setup("/centrodefamilia/beneficiarios/beneficiarios/99/");
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("No se encontró la página."));
  });
});
