// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import App from "./App";
import { get } from "./api";

vi.mock("./api", async (importOriginal) => ({
  ...await importOriginal<typeof import("./api")>(), get: vi.fn(),
}));

afterEach(() => { cleanup(); vi.resetAllMocks(); localStorage.clear(); });

function HistoryProbe() {
  const location = useLocation();
  const navigate = useNavigate();
  return <><output aria-label="URL actual">{location.pathname + location.search}</output><button onClick={() => navigate(-1)}>Atrás de prueba</button><button onClick={() => navigate(1)}>Adelante de prueba</button></>;
}

function show(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><App /><HistoryProbe /></MemoryRouter></QueryClientProvider>);
}

const session = { username: "Provincia", can_view_itinerarios: true, can_view_sedes: true, permissions: {}, can_export: false };

it("restores the full canonical itinerary query and page without using the V2 list", async () => {
  const filters = JSON.stringify({ logic: "AND", items: [{ field: "matricula_estimada", op: "gt", value: "50" }] });
  const query = new URLSearchParams({ busqueda: "Programa", buscar_por: "referente", estado: "borrador", provincia: "1", localidad: "Centro", fecha_desde: "2026-11-01", fecha_hasta: "2026-11-30", filters, page: "2" }).toString();
  vi.mocked(get).mockImplementation(async path => path === "/session/" ? session : { count: 0, results: [] });
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, headers: new Headers({ "Content-Type": "application/json" }), json: async () => ({
    count: 11, page: 2, pages: 2, page_size: 10,
    results: [{ id: 1, codigo: "IT-CANON-00", provincia: "Buenos Aires", estado: "borrador", estado_label: "Borrador", fecha_inicio: "2026-11-01", fecha_fin: "2026-11-30", referente: "Programa educativo" }],
    estados: [{ value: "borrador", label: "Borrador" }], provincias: [{ id: 1, nombre: "Buenos Aires" }], provincia_restringida: null,
    filters_config: { fields: [{ name: "matricula_estimada", label: "Matrícula estimada", type: "number" }], operators: { number: ["gt", "eq"] } },
  }) });
  vi.stubGlobal("fetch", fetchMock);
  try {
    show(`/ver-para-ser-libre/?${query}`);
    expect(await screen.findByText("IT-CANON-00")).toBeTruthy();
    expect(screen.getByRole("textbox", { name: "Buscar itinerarios" })).toHaveProperty("value", "Programa");
    expect(screen.getByRole("textbox", { name: "Localidad" })).toHaveProperty("value", "Centro");
    expect(screen.getByLabelText("Fecha desde")).toHaveProperty("value", "2026-11-01");
    expect(screen.getByLabelText("Fecha hasta")).toHaveProperty("value", "2026-11-30");
    expect(fetchMock).toHaveBeenCalledWith(`/ver-para-ser-libre/?${query}`, expect.objectContaining({ credentials: "same-origin", headers: { Accept: "application/json" } }));
    expect(vi.mocked(get).mock.calls.some(([path]) => path.startsWith("/itinerarios/?"))).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Página anterior" }));
    expect(screen.getByLabelText("URL actual").textContent).toContain("page=1");
    expect(screen.getByLabelText("URL actual").textContent).toContain("buscar_por=referente");
    fireEvent.click(screen.getByRole("button", { name: "Atrás de prueba" }));
    expect(screen.getByLabelText("URL actual").textContent).toContain("page=2");
    fireEvent.click(screen.getByRole("button", { name: "Limpiar filtros" }));
    expect(screen.getByLabelText("URL actual").textContent).toBe("/ver-para-ser-libre/");
    expect(screen.getByRole("textbox", { name: "Buscar itinerarios" })).toHaveProperty("value", "");
  } finally { vi.unstubAllGlobals(); }
});

it("restores canonical Sedes filters and page from the URL without using the V2 list", async () => {
  const filters = JSON.stringify({ logic: "AND", items: [{ field: "localidad", op: "eq", value: "Centro" }] });
  const search = new URLSearchParams({ busqueda: "educativa", filters, page: "2" }).toString();
  vi.mocked(get).mockImplementation(async path => path === "/session/" ? session : { count: 0, results: [] });
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, headers: new Headers({ "Content-Type": "application/json" }), json: async () => ({
    count: 16, page: 2, pages: 2, page_size: 15, results: [{ id: 16, nombre: "Escuela 16", localidad: "Centro", jurisdiccion: "Buenos Aires", cueanexo: "16" }],
    filters_config: { fields: [{ name: "localidad", label: "Localidad", type: "text" }], operators: { text: ["eq", "contains"] } },
  }) });
  vi.stubGlobal("fetch", fetchMock);
  try {
    show(`/ver-para-ser-libre/sedes/?${search}`);
    expect(await screen.findByText("Escuela 16")).toBeTruthy();
    expect(screen.getByRole("textbox", { name: "Buscar sede" })).toHaveProperty("value", "educativa");
    expect(screen.getByRole("textbox", { name: "Valor del filtro 1" })).toHaveProperty("value", "Centro");
    expect(fetchMock).toHaveBeenCalledWith(`/ver-para-ser-libre/sedes/?${search}`, expect.objectContaining({ headers: { Accept: "application/json" }, credentials: "same-origin" }));
    expect(vi.mocked(get).mock.calls.some(([path]) => path.startsWith("/sedes/?"))).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Página anterior" }));
    expect(screen.getByLabelText("URL actual").textContent).toContain("page=1");
    expect(screen.getByLabelText("URL actual").textContent).toContain("busqueda=educativa");
    fireEvent.click(screen.getByRole("button", { name: "Atrás de prueba" }));
    expect(screen.getByLabelText("URL actual").textContent).toContain("page=2");
    fireEvent.click(screen.getByRole("button", { name: "Limpiar filtros" }));
    expect(await screen.findByRole("textbox", { name: "Buscar sede" })).toHaveProperty("value", "");
    expect(screen.getByLabelText("URL actual").textContent).toBe("/ver-para-ser-libre/sedes/");
    fireEvent.click(screen.getByRole("button", { name: "Atrás de prueba" }));
    expect(screen.getByRole("textbox", { name: "Buscar sede" })).toHaveProperty("value", "educativa");
    fireEvent.click(screen.getByRole("button", { name: "Adelante de prueba" }));
    expect(screen.getByRole("textbox", { name: "Buscar sede" })).toHaveProperty("value", "");
  } finally { vi.unstubAllGlobals(); }
});

it("keeps the V2 Sedes search and detail links on the existing API and URL contract", async () => {
  vi.mocked(get).mockImplementation(async path => path === "/session/" ? session : {
    count: 1, next: null, previous: null,
    results: [{ id: 7, nombre: "Sede previa", localidad: "Centro", jurisdiccion: "Buenos Aires", cueanexo: "7" }],
  });
  show("/v2/vpsl/sedes/");
  await screen.findByText("Sede previa");
  fireEvent.change(screen.getByRole("textbox", { name: "Buscar sede" }), { target: { value: "Centro" } });
  fireEvent.click(screen.getByRole("button", { name: "Buscar" }));
  expect(get).toHaveBeenCalledWith("/sedes/?page=1&q=Centro");
  expect(screen.queryByRole("button", { name: "Agregar filtro" })).toBeNull();
  fireEvent.click(await screen.findByRole("button", { name: "Ver sede" }));
  expect(screen.getByLabelText("URL actual").textContent).toBe("/v2/vpsl/sedes/7/");
});

it.each(["light", "dark"])("presenta subsanación y cartas en modo %s", async (mode) => {
  localStorage.setItem("app.theme", mode);
  vi.mocked(get).mockImplementation(async (path) => path === "/session/" ? session : {
    id: 1, codigo: "VPSL-1", provincia: "Buenos Aires", estado: "en_subsanacion", estado_label: "En subsanación",
    fecha_inicio: "2026-10-01", fecha_fin: "2026-10-03", referente: "Ana", referente_telefono: "123456",
    referente_email: "ana@example.com", subsanacion_observaciones: "Reemplazar la carta sin firma.",
    carta_archivo_url: "/media/carta.pdf", carta_archivo_estado: "subsanar", jornadas: [],
  });
  show("/v2/vpsl/itinerarios/1/");
  expect(await screen.findByText(/Reemplazar la carta sin firma/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "Ver carta adjunta" }).getAttribute("href")).toBe("/media/carta.pdf");
  expect(screen.getByText("ana@example.com")).toBeTruthy();
});

it("pagina registros y presenta evidencias y actas del cierre", async () => {
  vi.mocked(get).mockImplementation(async (path) => {
    if (path === "/session/") return session;
    if (path.includes("/registros/")) return {
      count: 26, next: path.includes("page=1") ? "page=2" : null, previous: path.includes("page=2") ? "page=1" : null,
      results: [{ id: path.includes("page=2") ? 2 : 1, dni: path.includes("page=2") ? "22222222" : "11111111", nombre: "Ana", apellido: "Perez", numero_acta: "1", resultado: "No requiere", graduacion_izquierda: "", graduacion_derecha: "" }],
    };
    if (path.includes("/laboratorio/")) return { count: 0, results: [], next: null, previous: null };
    return {
      id: 1, itinerario_id: 1, fecha: "2026-10-01", sede: "Escuela", estado: "habilitada", estado_label: "Habilitada",
      checklist: [{ item: "electricidad", descripcion: "Electricidad", cumple: true, evidencia_url: "/media/evidencia.pdf", historial: [] }],
      cierre: { responsable: "Ana", consistente: true, atenciones: 2, lentes: 0, casos: 0, acta_adjunta_url: "/media/acta.pdf", historial: [] },
    };
  });
  show("/v2/vpsl/jornadas/1/");
  await screen.findByText("11111111");
  expect(screen.getByRole("link", { name: "Ver evidencia" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "Descargar acta de cierre" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Página siguiente" }));
  expect(await screen.findByText("22222222")).toBeTruthy();
  expect(screen.queryByText("11111111")).toBeNull();
});

it("abre y navega un itinerario por sus URLs canónicas, sin volver a /v2", async () => {
  vi.mocked(get).mockImplementation(async (path) => {
    if (path === "/session/") return { ...session, permissions: { change_itinerariovpsl: true } };
    if (path === "/itinerarios/1/") return {
      id: 1, codigo: "VPSL-1", provincia: "Buenos Aires", estado: "en_subsanacion", estado_label: "En subsanación",
      subsanacion_observaciones: "Reemplazar carta.", fecha_inicio: "2026-10-01", fecha_fin: "2026-10-03", jornadas: [],
    };
    if (path.startsWith("/forms/")) return { fields: [], back: "itinerarios/1/" };
    return { results: [], count: 0 };
  });
  show("/ver-para-ser-libre/1/");
  expect(await screen.findByText(/Reemplazar carta/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Subsanar" }));
  expect(await screen.findByRole("heading", { name: "Subsanar itinerario" })).toBeTruthy();
  expect(get).toHaveBeenCalledWith("/forms/itinerario-subsanar/1/");
  expect(screen.getAllByRole("link", { name: "Sedes" })[0].getAttribute("href")).toBe("/ver-para-ser-libre/sedes/");
});

it("confirma una baja en su ruta canónica y conserva su retorno", async () => {
  vi.mocked(get).mockImplementation(async (path) => {
    if (path === "/session/") return session;
    if (path === "/actions/eliminar-jornada/8/") return {
      preview: { total_afectados: 2, total_borrado_fisico: 0, desglose_por_modelo: [] },
      back: "/ver-para-ser-libre/1/",
    };
    if (path === "/itinerarios/1/") return {
      id: 1, codigo: "VPSL-1", provincia: "Buenos Aires", estado: "borrador", jornadas: [],
    };
    return { results: [], count: 0 };
  });
  show("/ver-para-ser-libre/jornadas/8/eliminar/");
  expect(await screen.findByText(/afecta 2 elementos/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(await screen.findByText(/VPSL-1/)).toBeTruthy();
  expect(get).toHaveBeenCalledWith("/itinerarios/1/");
});

it("muestra la jornada canónica con su permiso propio, sin exigir ver itinerarios", async () => {
  vi.mocked(get).mockImplementation(async (path) => {
    if (path === "/session/") return { ...session, can_view_itinerarios: false, permissions: { view_jornadavpsl: true } };
    if (path === "/jornadas/8/") return {
      id: 8, itinerario_id: 1, fecha: "2026-10-01", sede: "Escuela inclusiva", estado: "habilitada",
    };
    return { results: [], count: 0 };
  });
  show("/ver-para-ser-libre/jornadas/8/");
  expect(await screen.findByText(/Escuela inclusiva/)).toBeTruthy();
});
