// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { ThemeProvider } from "@sisoc/ui";
import { api } from "./api";
import { ReportePage } from "./pages/ReportePage";
import { App } from "./App";
import type { Reporte } from "@sisoc/api";

vi.mock("./api", () => ({ api: { reporte: { obtener: vi.fn() } } }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

function Location() {
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  return <>
    <output aria-label="URL de prueba">{pathname + search}</output>
    <button type="button" onClick={() => navigate(-1)}>Volver en el historial de prueba</button>
  </>;
}

function show(path: string, pending = true) {
  if (pending) {
    vi.mocked(api.reporte.obtener).mockImplementation(() => new Promise(() => {}));
  }
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <ThemeProvider>
        <MemoryRouter initialEntries={[path]}>
          {path.startsWith("/reporter-provincias/") ? <App canonicalReport /> : <ReportePage />}
          <Location />
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

it("reabre un enlace canónico con sus filtros y la página guardada", async () => {
  show("/reporter-provincias/?provincia=3&revision_tecnico=APROBADO&page=2");
  await waitFor(() => expect(api.reporte.obtener).toHaveBeenCalledWith({
    provincia: 3, revision_tecnico: "APROBADO", page: 2,
  }));
});

it("conserva el estado de entrada histórico de la pantalla V2", async () => {
  show("/v2/celiaquia/reporte");
  await waitFor(() => expect(api.reporte.obtener).toHaveBeenCalledWith({
    provincia: undefined, page: 1,
  }));
});


const caso = {
  id: 1, ciudadano: "Ana Sol", expediente_id: 91, expediente_numero: "SINT-91",
  documento: "001", provincia: "Provincia de prueba", revision_tecnico: "APROBADO",
  resultado_sintys: "MATCH", estado_cupo: "DENTRO", archivos_ok: true,
  clasificacion: "", creado_en: null,
};

function report(page: number): Reporte {
  return {
    total_casos: 26, casos_documentos_ok: 2, casos_documentos_incompletos: 1,
    porcentaje_documentos_ok: 75, porcentaje_documentos_incompletos: 25,
    casos_con_comentarios: 0, metricas_principales: [], casos_por_instancia: {},
    resumen_validacion: [], resumen_sintys: [], resumen_cupo: [],
    clasificacion_aprobados: {}, tendencia_mensual: [], expedientes_por_provincia: [],
    casos: [caso, { ...caso, id: 2, ciudadano: "Eva Lago", documento: "002", expediente_id: 92 }],
    page, page_size: 12, detalle_desde: 1, detalle_hasta: 2,
    es_usuario_provincial: true, provincias: [], filtros_activos: [],
  };
}

it("busca solo en la página actual y conserva el enlace canónico de expediente", async () => {
  vi.mocked(api.reporte.obtener).mockResolvedValue(report(2));
  show("/reporter-provincias/?revision_tecnico=APROBADO&page=2", false);
  expect((await screen.findByRole("link", { name: "001" })).getAttribute("href")).toBe("/celiaquia/expedientes/91/");
  expect(screen.queryByRole("link", { name: "Cupos por provincia" })).toBeNull();
  const quick = screen.getByRole("searchbox", { name: "Buscar en esta página" });
  fireEvent.change(quick, { target: { value: "eva" } });
  expect(screen.getByRole("status", { name: "Resultados de la búsqueda rápida" }).textContent).toBe("1 registro visible en esta página");
  expect(screen.queryByText("Ana Sol")).toBeNull();
  expect(screen.getByText("Eva Lago")).toBeTruthy();
  expect(api.reporte.obtener).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText("URL de prueba").textContent).toContain("page=2");
});

it("aplica, pagina y limpia filtros en la misma URL canónica", async () => {
  vi.mocked(api.reporte.obtener).mockImplementation(async ({ page } = {}) => report(page ?? 1));
  show("/reporter-provincias/?page=2", false);
  fireEvent.change(await screen.findByRole("textbox", { name: "Expediente" }), { target: { value: "SINT 91" } });
  fireEvent.click(screen.getByRole("button", { name: "Aplicar" }));
  await waitFor(() => expect(screen.getByLabelText("URL de prueba").textContent).toBe("/reporter-provincias/?expediente_numero=SINT+91"));
  expect(api.reporte.obtener).toHaveBeenLastCalledWith({ expediente_numero: "SINT 91", provincia: undefined, page: 1 });
  fireEvent.click(await screen.findByRole("button", { name: /next|siguiente/i }));
  await waitFor(() => expect(screen.getByLabelText("URL de prueba").textContent).toBe("/reporter-provincias/?expediente_numero=SINT+91&page=2"));
  fireEvent.click(await screen.findByRole("button", { name: "Limpiar" }));
  await waitFor(() => expect(screen.getByLabelText("URL de prueba").textContent).toBe("/reporter-provincias/"));
});


it.each([
  ["Revisión aprobada", "revision_tecnico", "APROBADO"],
  ["SINTYS conciliado", "resultado_sintys", "MATCH"],
  ["Dentro de cupo", "estado_cupo", "DENTRO"],
])("aplica el filtro nativo del resumen %s y reinicia la página", async (label, key, value) => {
  vi.mocked(api.reporte.obtener).mockImplementation(async ({ page } = {}) => ({
    ...report(page ?? 1),
    resumen_validacion: [{ code: "APROBADO", label: "Revisión aprobada", count: 5, percentage: 20 }],
    resumen_sintys: [{ code: "MATCH", label: "SINTYS conciliado", count: 4, percentage: 16 }],
    resumen_cupo: [{ code: "DENTRO", label: "Dentro de cupo", count: 3, percentage: 12 }],
  }));
  show("/reporter-provincias/?page=2", false);
  fireEvent.change(await screen.findByRole("textbox", { name: "Expediente" }), { target: { value: "SINT 91" } });
  fireEvent.click(screen.getByRole("button", { name: label }));
  await waitFor(() => expect(api.reporte.obtener).toHaveBeenLastCalledWith({
    expediente_numero: "SINT 91", [key]: value, provincia: undefined, page: 1,
  }));
  expect(await screen.findByRole("button", { name: label, pressed: true })).toBeTruthy();
  expect(screen.getByLabelText("URL de prueba").textContent).not.toContain("page=");
  fireEvent.click(screen.getByRole("button", { name: "Volver en el historial de prueba" }));
  await waitFor(() => expect(screen.getByLabelText("URL de prueba").textContent).toBe("/reporter-provincias/?page=2"));
});

const ranking = [
  { provincia_id: 7, nombre: "Provincia visible", expedientes: 2, casos: 4, share: 20 },
  { provincia_id: null, nombre: "Sin provincia", expedientes: 1, casos: 2, share: 10 },
];

it.each([true, false])("respeta el alcance provincial (%s) en el ranking", async (provincial) => {
  vi.mocked(api.reporte.obtener).mockImplementation(async ({ page } = {}) => ({
    ...report(page ?? 1),
    es_usuario_provincial: provincial,
    expedientes_por_provincia: ranking,
    provincias: [{ id: 7, nombre: "Provincia visible" }],
  }));
  show("/reporter-provincias/?estado_cupo=DENTRO&page=2", false);
  await screen.findByText("Provincia visible");
  expect(screen.getByText("2 expedientes")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Sin provincia" })).toBeNull();
  const accion = screen.queryByRole("button", { name: "Provincia visible" });
  if (provincial) {
    expect(accion).toBeNull();
  } else {
    expect(accion).toBeTruthy();
    fireEvent.click(accion!);
    await waitFor(() => expect(api.reporte.obtener).toHaveBeenLastCalledWith({
      provincia: 7, estado_cupo: "DENTRO", page: 1,
    }));
  }
});

it("muestra el rol y marca Dupla solo en la fila indicada por Django", async () => {
  const respuesta = report(2);
  Object.assign(respuesta.casos[0], { clasificacion_label: "Menor de edad", clasificacion_tone: "warning", integra_dupla: true });
  Object.assign(respuesta.casos[1], { clasificacion_label: "Responsable", clasificacion_tone: "primary", integra_dupla: false });
  vi.mocked(api.reporte.obtener).mockResolvedValue(respuesta);
  show("/reporter-provincias/?page=2", false);
  const hijo = await screen.findByRole("row", { name: /Ana Sol/ });
  const responsable = screen.getByRole("row", { name: /Eva Lago/ });
  expect(within(hijo).getByText("Menor de edad")).toBeTruthy();
  expect(within(hijo).getByText("Dupla")).toBeTruthy();
  expect(within(responsable).getByText("Responsable")).toBeTruthy();
  expect(within(responsable).queryByText("Dupla")).toBeNull();
  fireEvent.change(screen.getByRole("searchbox", { name: "Buscar en esta página" }), { target: { value: "Dupla" } });
  expect(screen.queryByText("Eva Lago")).toBeNull();
  expect(screen.getByText("Ana Sol")).toBeTruthy();
});
