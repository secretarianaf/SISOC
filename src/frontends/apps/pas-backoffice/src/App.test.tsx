import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import App from "./App";
import { descargarNomina, exportarPreliquidacionCsv, exportarSintys, exportarTokens, pasGet, pasPost, webGet } from "./api";

vi.mock("./api", () => ({ pasGet: vi.fn(), pasPost: vi.fn(), webGet: vi.fn(), exportarSintys: vi.fn(), exportarTokens: vi.fn(), importarSintys: vi.fn(),
  descargarNomina: vi.fn(), exportarPreliquidacionCsv: vi.fn(), statusPas: () => 403 }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

function mount(route = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[route]}><App /></MemoryRouter></QueryClientProvider>);
}
const ready = { user: { display_name: "Usuario de prueba" }, access: { state: "ready" } };
const liquidacionVacia = {
  periodo: "2026-11-01", puntos_control: [], descarga_habilitada: false, nomina_generada: false, fecha_cierre: "",
  titulares_a_acreditar: 0, titulares_bloqueados: 0, total_a_liquidar: "0.00", monto_mensual: "78000.00", filas: [], total_filas: 0,
};

it("navega hacia titulares dentro de React y consulta el padrón existente", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockImplementation(async (path) => path.startsWith("panel/") ? { persona: null } : { total_padron: 1, results: [{
    id: 10, apellidos: "Prueba", nombres: "Ana", dni: 1001, cuit: "", provincia: "", municipio: "", estado: { nombre: "Activo" },
  }], estados: [], previous: null, next: null, capabilities: { can_export_tokens: false } });
  mount();
  await screen.findByRole("heading", { name: "Titulares PAS" });
  expect(screen.getByRole("navigation", { name: "Circuitos PAS" })).toBeTruthy();
  const titular = await screen.findByRole("link", { name: /Prueba, Ana/ });
  expect(titular.getAttribute("href")).toMatch(/^\/titulares\/10/);
  fireEvent.click(titular);
  await screen.findByText("Sin titular seleccionado.");
  expect(vi.mocked(webGet)).toHaveBeenCalledWith("web/session/");
  expect(vi.mocked(pasGet)).toHaveBeenCalledWith("personas/?");
});

it("muestra la denegación de PAS sin exponer el padrón", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockRejectedValue(new Error());
  mount("/titulares");
  expect((await screen.findByRole("alert")).textContent).toContain("No tenés permiso");
  expect(screen.queryByRole("heading", { name: "Titulares PAS" })).toBeNull();
});

it("muestra el circuito y llama a la API existente de exportación con permiso", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue({
    can_change: true, circuito: { periodo_texto: "11/2026" },
    etapas: [{ numero: 1, nombre: "Exportación a SINTyS", completada: false }],
    renaper: { total: 0, fallecidas: 0, errores: 0 }, incompatibilidades: [],
  });
  mount("/cruces");
  await screen.findByRole("heading", { name: "Circuito Administrativo Mensual" });
  fireEvent.click(screen.getByRole("button", { name: "Exportar a SINTyS (VIAS)" }));
  await screen.findByText("Padrón exportado.");
  expect(exportarSintys).toHaveBeenCalledTimes(1);
});


it.each([
  ["/formacion", "Formación FCH"],
  ["/liquidacion", "Liquidación"],
  ["/dashboard", "Reporte PAS"],
  ["/informes", "Informes PAS"],
])("carga el destino %s del menú", async (ruta, titulo) => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue({
    total_padron: 0, personas: [], persona_seleccionada: null, resumen: null, formaciones: [], results: [], liquidacion: liquidacionVacia,
  });
  mount(ruta);
  await screen.findByRole("heading", { name: titulo });
  expect(screen.getByRole("navigation", { name: "Menú de PAS" })).toBeTruthy();
});

it("permite recorrer las cuatro pestañas de una ficha", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  const titular = { id: 10, nombres: "Ana", apellidos: "Prueba", dni: 1001, estado: { nombre: "Activo" } };
  vi.mocked(pasGet).mockImplementation(async (path) => path.startsWith("panel/") ? {
    persona: { ...titular, avisos: [] }, formaciones: [], ddjj: { seleccionada: null }, eventos_historial: [],
  } : { results: [titular], estados: [], capabilities: {}, previous: null, next: null, total_padron: 1 });
  mount("/titulares/10");
  expect(await screen.findByRole("heading", { name: "Datos del Titular" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Información Financiera" })).toBeTruthy();
  // Campos y orden de Figma: Identidad, Contacto y Domicilio; sin dato, guión largo.
  expect(screen.getAllByRole("term").map((item) => item.textContent)).toEqual([
    "DNI", "Fecha de nacimiento", "Teléfono", "Celular", "Email", "Provincia", "Municipio / Localidad", "Domicilio",
    "Asignación mensual", "CBU / Cuenta BNA", "Estado de cuenta",
  ]);
  expect(screen.getByText("1.001")).toBeTruthy();
  const tabs = ["Datos personales", "Capacitaciones FCH", "Declaración jurada", "Historial de datos"];
  for (const name of tabs) {
    const tab = await screen.findByRole("tab", { name });
    fireEvent.click(tab);
    expect(tab.getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("tabpanel").getAttribute("aria-labelledby")).toBe(tab.id);
  }
});

it("mantiene visible la tabla de Formación aunque el padrón esté vacío", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue({ personas: [], persona_seleccionada: null, resumen: null, formaciones: [] });
  mount("/formacion");
  expect(await screen.findByRole("table", { name: "Cursos registrados — Portal FCH" })).toBeTruthy();
  expect(screen.getByRole("columnheader", { name: "Constancia" })).toBeTruthy();
  expect(screen.getByText("Seleccioná un titular para ver sus cursos.")).toBeTruthy();
});

it("resume las incompatibilidades del período y conserva el DNI al abrir el padrón", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  const alerta = { titular: "Titular de prueba", dni: 990000001, categoria: "Supervivencia", detalle: "Control de prueba", fecha_deteccion: "", estado: "Pendiente" };
  vi.mocked(pasGet).mockResolvedValue({
    can_change: false, circuito: { periodo_texto: "11/2026" }, etapas: [],
    renaper: { total: 0, fallecidas: 0, errores: 0 }, incompatibilidades: [alerta],
  });
  mount("/cruces");
  // Supervivencia es la única fuente integrada: suma la alerta; el resto figura sin integrar.
  expect(await screen.findByText("1 alerta")).toBeTruthy();
  expect(screen.getByText("1 pendiente")).toBeTruthy();
  expect(screen.getAllByText("Sin integrar")).toHaveLength(3);
  expect(screen.getByRole("link", { name: "Gestionar a Titular de prueba" }).getAttribute("href")).toBe("/titulares?q=990000001");
});

it("muestra el contador de alertas de Cruces en su tarjeta de navegación", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  const alerta = { titular: "Titular de prueba", dni: 990000001, categoria: "Ingresos", detalle: "", fecha_deteccion: "", estado: "Pendiente" };
  vi.mocked(pasGet).mockResolvedValue({
    can_change: false, circuito: { periodo_texto: "11/2026" }, etapas: [],
    renaper: { total: 0, fallecidas: 0, errores: 0 }, incompatibilidades: [alerta, alerta],
  });
  mount("/cruces");
  const tarjeta = await screen.findByRole("link", { name: /Cruces y Novedades/ });
  expect(tarjeta.getAttribute("aria-current")).toBe("page");
  expect(await screen.findByLabelText("2 alertas")).toBeTruthy();
});

it("lista el padrón en el Buscador PAS y filtra por texto y estado", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue({
    total_padron: 1, page: 1, previous: null, next: null, estados: [{ nombre: "Activo" }],
    capabilities: { can_import: true, can_export_tokens: false },
    results: [{ id: 10, apellidos: "Prueba", nombres: "Ana", dni: 1001, id_persona: 77, cuit: "27-1001-3",
      provincia: "Salta", municipio: "Cafayate", estado: { nombre: "Activo" }, avisos: [1] }],
  });
  mount("/buscador");
  await screen.findByRole("heading", { name: "Buscador PAS" });
  expect(screen.queryByRole("navigation", { name: "Circuitos PAS" })).toBeNull();
  expect(await screen.findByText("DNI 1001 · IdPersona 77")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Abrir panel de control de Prueba, Ana" }).getAttribute("href")).toBe("/titulares/10");
  expect(screen.getByRole("link", { name: "Importar titulares" }).getAttribute("href")).toBe("/buscador/importar");
  expect(screen.getByRole("link", { name: "Nuevo titular" }).getAttribute("href")).toBe("/buscador/nuevo");
  expect(screen.queryByRole("button", { name: "Exportar tokens" })).toBeNull();
  fireEvent.change(screen.getByRole("searchbox", { name: "Buscar titular" }), { target: { value: "Ana" } });
  fireEvent.click(screen.getByRole("button", { name: "Buscar" }));
  await waitFor(() => expect(pasGet).toHaveBeenLastCalledWith("personas/?q=Ana"));
});

it("no expone el Buscador PAS sin permiso sobre el padrón", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockRejectedValue(new Error());
  mount("/buscador");
  expect((await screen.findByRole("alert")).textContent).toContain("No tenés permiso");
  expect(screen.queryByRole("table", { name: "Titulares PAS" })).toBeNull();
});

it("envía el alta por la API de titulares", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockImplementation(async (path) => path.startsWith("personas/opciones/")
    ? { estados: [], provincias: [], municipios: [], generos: [], avisos_por_estado: {} }
    : path.startsWith("panel/") ? { persona: null }
      : { results: [], estados: [], capabilities: {}, previous: null, next: null, total_padron: 0 });
  vi.mocked(pasPost).mockResolvedValue({ id: 10, message: "Creado" });
  mount("/titulares/nuevo");
  const nombre = await screen.findByRole("textbox", { name: "Nombres" });
  fireEvent.change(nombre, { target: { value: "Ejemplo" } });
  fireEvent.click(screen.getByRole("button", { name: /^Guardar$/ }));
  await waitFor(() => expect(pasPost).toHaveBeenCalledTimes(1));
  const [path, body] = vi.mocked(pasPost).mock.calls[0];
  expect(path).toBe("personas/crear/");
  expect(body?.get("nombres")).toBe("Ejemplo");
});

it("envía la vista previa de informes sin generar un CSV", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue({ estados: [], provincias: [], municipios: [], avisos: [] });
  vi.mocked(pasPost).mockResolvedValue({ total: 0, columns: [], rows: [] });
  mount("/informes/generar");
  await screen.findByRole("heading", { name: "Generar informe PAS" });
  fireEvent.click(screen.getByRole("button", { name: "Previsualizar" }));
  await screen.findByText("Resultados de la vista previa: 0");
  expect(pasPost).toHaveBeenCalledWith("informes/previsualizar/", expect.any(FormData));
});

it("importa titulares dentro del Buscador, envía el CSV y muestra sus errores de fila", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue({});
  vi.mocked(pasPost).mockResolvedValue({ resultado: { total: 2, creados: 1, duplicados: 0, errores: ["Fila 2 inválida"] } });
  mount("/buscador/importar");
  expect(await screen.findByRole("heading", { name: "Importar titulares" })).toBeTruthy();
  expect(screen.queryByRole("navigation", { name: "Circuitos PAS" })).toBeNull();
  expect(screen.getByRole("link", { name: "Volver al Buscador" }).getAttribute("href")).toBe("/buscador");
  const menu = screen.getByRole("navigation", { name: "Menú de PAS" });
  expect(within(menu).getByRole("link", { name: "Buscador PAS" }).getAttribute("aria-current")).toBe("page");
  expect(screen.getByText("Columnas obligatorias")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Ver reglas de importación" }));
  expect(screen.getByText(/el registro se omite y el padrón no cambia/)).toBeTruthy();
  const input = screen.getByLabelText("Archivo CSV");
  const archivo = new File(["a,b"], "titulares.csv", { type: "text/csv" });
  fireEvent.change(input, { target: { files: [archivo] } });
  expect(screen.getByText("titulares.csv")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Importar CSV" }));
  await screen.findByText("Fila 2 inválida");
  const [path, body] = vi.mocked(pasPost).mock.calls[0];
  expect(path).toBe("titulares/importar/");
  expect((body?.get("archivo") as File).name).toBe("titulares.csv");
});

it("agrupa las acciones del padrón en un menú contextual", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue({ results: [], estados: [], previous: null, next: null, total_padron: 0,
    capabilities: { can_import: true, can_export_tokens: true } });
  mount();
  const trigger = await screen.findByRole("button", { name: "Acciones del padrón" });
  expect(screen.queryByRole("menuitem", { name: "Nuevo titular" })).toBeNull();
  fireEvent.click(trigger);
  expect((await screen.findByRole("menuitem", { name: "Nuevo titular" })).getAttribute("href")).toBe("/titulares/nuevo");
  fireEvent.click(screen.getByRole("menuitem", { name: "Exportar tokens" }));
  await waitFor(() => expect(exportarTokens).toHaveBeenCalledTimes(1));
});

it("avisa si la exportación de tokens falla en el Buscador PAS", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue({ results: [], estados: [], previous: null, next: null, total_padron: 0,
    capabilities: { can_import: false, can_export_tokens: true } });
  vi.mocked(exportarTokens).mockRejectedValue(new Error("403"));
  mount("/buscador");
  fireEvent.click(await screen.findByRole("button", { name: "Exportar tokens" }));
  expect((await screen.findByRole("alert")).textContent).toContain("No se pudieron exportar los tokens");
});

const alertaSintys = {
  id: 7, persona_id: 10, titular: "Juarez, Alfredo", dni: 16012217, categoria: "Ingresos", origen: "SINTyS", detalle: "PENSION NO CONTRIBUTIVA",
  fecha_deteccion: "25/11/2026 10:00", estado: "Pendiente", estado_actual: "Activo", cambio_propuesto: "Suspendido (10 - INCOMPATIBLE)",
};
const crucesConAlerta = {
  can_change: true, circuito: { periodo_texto: "11/2026" }, etapas: [], renaper: { total: 0, fallecidas: 0, errores: 0 },
  incompatibilidades: [alertaSintys], importacion_sintys: { total: 2, compatibles: 1, alertas: 1, sin_cambios: 0, ya_gestionadas: 0,
    errores: ["Línea 3: titular no encontrado (ID 4, DNI 1004)."] },
  cambio_estado: { estados: [{ id: 1, nombre: "Activo" }, { id: 2, nombre: "Suspendido" }], avisos_por_estado: { "2": [{ id: 10, text: "10 - INCOMPATIBLE" }] } },
};

it("confirma una alerta SINTyS desde el botón Gestionar", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue(crucesConAlerta);
  vi.mocked(pasPost).mockResolvedValue({ message: "Alerta confirmada. El estado del titular quedó actualizado." });
  vi.spyOn(window, "confirm").mockReturnValue(true);
  mount("/cruces");
  expect(await screen.findByText("Activo → Suspendido (10 - INCOMPATIBLE)")).toBeTruthy();
  expect(screen.getByText(/Línea 3: titular no encontrado/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Gestionar a Juarez, Alfredo" }));
  fireEvent.click(await screen.findByRole("menuitem", { name: "Confirmar" }));
  await screen.findByText("Alerta confirmada. El estado del titular quedó actualizado.");
  expect(window.confirm).toHaveBeenCalledWith("¿Confirmar la alerta de Juarez, Alfredo y pasar a Suspendido (10 - INCOMPATIBLE)?");
  expect(pasPost).toHaveBeenCalledWith("cruces/incompatibilidades/7/confirmar/");
});

it("modifica una alerta con el cambio de estado y pide confirmación", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue(crucesConAlerta);
  vi.mocked(pasPost).mockResolvedValue({ message: "ok" });
  const confirmar = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValue(true);
  mount("/cruces");
  fireEvent.click(await screen.findByRole("button", { name: "Gestionar a Juarez, Alfredo" }));
  fireEvent.click(await screen.findByRole("menuitem", { name: "Modificar" }));
  const dialogo = await screen.findByRole("dialog", { name: "Modificar estado de Juarez, Alfredo" });
  fireEvent.mouseDown(within(dialogo).getByRole("combobox", { name: "Estado" }));
  fireEvent.click(await screen.findByRole("option", { name: "Suspendido" }));
  fireEvent.click(within(dialogo).getByRole("checkbox", { name: "10 - INCOMPATIBLE" }));
  fireEvent.click(within(dialogo).getByRole("button", { name: "Guardar cambio" }));
  expect(pasPost).not.toHaveBeenCalled();
  fireEvent.click(within(dialogo).getByRole("button", { name: "Guardar cambio" }));
  await waitFor(() => expect(pasPost).toHaveBeenCalledTimes(1));
  expect(confirmar).toHaveBeenLastCalledWith("¿Confirmar el cambio de estado de Juarez, Alfredo? La alerta quedará confirmada.");
  const [ruta, cuerpo] = vi.mocked(pasPost).mock.calls[0];
  expect(ruta).toBe("cruces/incompatibilidades/7/modificar/");
  expect((cuerpo as FormData).get("estado")).toBe("2");
  expect((cuerpo as FormData).getAll("avisos")).toEqual(["10"]);
});

it("muestra puntos de control, preliquidación y los motivos del bloqueo de la nómina", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue({
    total_padron: 2, can_download: true, liquidacion: {
      ...liquidacionVacia, descarga_habilitada: true, titulares_a_acreditar: 1, titulares_bloqueados: 1, total_a_liquidar: "78000.00", total_filas: 2,
      puntos_control: [{ clave: "suspensiones", titulo: "PC 1 Consolidación de suspensiones", estado: "ok", detalle: "Cruces confirmados.", bloquea: false },
        { clave: "formacion", titulo: "PC 3 Validación de condicionalidad FCH", estado: "sin_integrar", detalle: "FCH sin integrar.", bloquea: false }],
      filas: [
        { id: 1, titular: "Perez, Ana", cuil: "27-1", cbu: "", monto: "78000.00", fch: null, cruces_ok: true, ddjj_ok: true, habilitado: true, estado_final: "Habilitado" },
        { id: 2, titular: "Gomez, Luis", cuil: "20-2", cbu: "", monto: "0.00", fch: null, cruces_ok: true, ddjj_ok: false, habilitado: false, estado_final: "Bloqueado: Sin DDJJ" },
      ],
    },
  });
  vi.mocked(descargarNomina).mockRejectedValue({ response: { status: 409, data: { motivos: ["Hay 2 alertas de incompatibilidad sin gestionar."] } } });
  vi.spyOn(window, "confirm").mockReturnValue(true);
  mount("/liquidacion");
  expect(await screen.findByText("PC 1 Consolidación de suspensiones · OK")).toBeTruthy();
  expect(screen.getByText("PC 3 Validación de condicionalidad FCH · Sin integrar")).toBeTruthy();
  expect(screen.getByText("Bloqueado: Sin DDJJ")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Perez, Ana" }).getAttribute("href")).toBe("/titulares/1");
  fireEvent.click(screen.getByRole("button", { name: "Descargar nómina de pago" }));
  expect(await screen.findByText("Hay 2 alertas de incompatibilidad sin gestionar.")).toBeTruthy();
  expect(descargarNomina).toHaveBeenCalledTimes(1);
});

it("deshabilita la descarga de la nómina sin permiso", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue({ total_padron: 0, can_download: false, liquidacion: { ...liquidacionVacia, descarga_habilitada: true } });
  mount("/liquidacion");
  const boton = await screen.findByRole("button", { name: "Descargar nómina de pago" });
  expect((boton as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText("Sin titulares para liquidar.")).toBeTruthy();
});

it("muestra los chips DDJJ y FCH en el padrón y mantiene al titular al pasar a Formación", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  const titular = { id: 10, nombres: "Ana", apellidos: "Prueba", dni: 1001, cuit: "", provincia: "Salta", municipio: "", estado: { nombre: "Activo" } };
  vi.mocked(pasGet).mockImplementation(async (path) => path.startsWith("panel/") ? {
    persona: { ...titular, avisos: [] }, formaciones: [], ddjj: { seleccionada: null }, eventos_historial: [],
  } : { results: [{ ...titular, tag_ddjj: true, tag_fch: true }, { ...titular, id: 11, nombres: "Bea", tag_ddjj: false, tag_fch: false }],
    estados: [], capabilities: {}, previous: null, next: null, total_padron: 2 });
  mount("/titulares/10");
  expect(await screen.findByLabelText("DDJJ sin completar")).toBeTruthy();
  expect(screen.getAllByLabelText("Formación FCH bajo 100 puntos")).toHaveLength(1);
  const formacion = within(screen.getByRole("navigation", { name: "Circuitos PAS" })).getByRole("link", { name: /Formación FCH/ });
  expect(formacion.getAttribute("href")).toBe("/formacion?persona=10");
});

it("muestra en el historial el detalle de la alerta confirmada", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  const titular = { id: 10, nombres: "Ana", apellidos: "Prueba", dni: 1001, estado: { nombre: "Suspendido" } };
  vi.mocked(pasGet).mockImplementation(async (path) => path.startsWith("panel/") ? {
    persona: { ...titular, avisos: [] }, formaciones: [], ddjj: { seleccionada: null },
    eventos_historial: [{ tipo: "estado", fecha: "25/11/2026 10:00", estado: "Suspendido", observacion: "SINTyS · Ingresos: MAYOR DE 65 AÑOS + JUBILACION / PENSION" }],
  } : { results: [titular], estados: [], capabilities: {}, previous: null, next: null, total_padron: 1 });
  mount("/titulares/10");
  fireEvent.click(await screen.findByRole("tab", { name: "Historial de datos" }));
  expect(screen.getByText("SINTyS · Ingresos: MAYOR DE 65 AÑOS + JUBILACION / PENSION")).toBeTruthy();
});

it("deja Justicia y Migraciones pendientes y pone en curso el procesamiento de alertas", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  const etapa = (numero: number, nombre: string, completada: boolean, integracion_pendiente = false) =>
    ({ numero, nombre, completada, fecha_texto: completada ? "25/11/2026 10:00" : "", integracion_pendiente });
  vi.mocked(pasGet).mockResolvedValue({
    can_change: false, circuito: { periodo_texto: "11/2026" }, renaper: { total: 0, fallecidas: 0, errores: 0 }, incompatibilidades: [],
    etapas: [etapa(1, "Exportación a SINTyS (VIAS)", true), etapa(2, "Importación retorno SINTyS", true), etapa(3, "Cruce FTP Justicia", false, true),
      etapa(4, "Cruce Migraciones", false, true), etapa(5, "Procesamiento de alertas", false), etapa(6, "Cierre del circuito mensual", false)],
  });
  mount("/cruces");
  const pasos = await screen.findByRole("list", { name: "Pasos del circuito mensual" });
  const items = within(pasos).getAllByRole("listitem");
  expect(items[4].getAttribute("aria-current")).toBe("step");
  expect(within(items[4]).getByText("En curso")).toBeTruthy();
  expect(within(items[2]).getByText("Pendiente")).toBeTruthy();
  expect(within(items[3]).getByText("Pendiente")).toBeTruthy();
  expect(screen.queryByText("Integración pendiente")).toBeNull();
});

it("Cursos PAS: el sidebar lo ubica en Administración con el Buscador PAS y sin los grupos de SISOC", async () => {
  vi.mocked(webGet).mockResolvedValue({ ...ready, navigation: [{ id: "tableros", label: "Tableros", href: null, children: [] }] });
  vi.mocked(pasGet).mockResolvedValue({ titulo: "Cursos PAS", subtitulo: "Administración" });
  mount("/cursos");
  expect(await screen.findByRole("heading", { name: "Cursos PAS" })).toBeTruthy();
  expect(vi.mocked(pasGet)).toHaveBeenCalledWith("cursos/");
  const menu = screen.getByRole("navigation", { name: "Menú de PAS" });
  const administracion = within(menu).getByRole("button", { name: "Administración" });
  const grupo = document.getElementById(administracion.getAttribute("aria-controls") ?? "") as HTMLElement;
  expect(within(grupo).getByRole("link", { name: "Buscador PAS" }).getAttribute("href")).toBe("/buscador");
  expect(within(grupo).queryByRole("link", { name: "Panel de control" })).toBeNull();
  expect(within(document.getElementById("pas-submenu") as HTMLElement).getByRole("link", { name: "Panel de control" }).getAttribute("href")).toBe("/");
  expect(within(grupo).getByRole("link", { name: "Cursos PAS" }).getAttribute("aria-current")).toBe("page");
  expect(within(menu).queryByText("Tableros")).toBeNull();
});

it("da de alta un titular dentro del Buscador y vuelve filtrado por su DNI", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockImplementation(async (path) => path.startsWith("personas/opciones/")
    ? { estados: [], provincias: [], municipios: [], generos: [], avisos_por_estado: {} }
    : { results: [], estados: [], capabilities: {}, previous: null, next: null, total_padron: 0 });
  vi.mocked(pasPost).mockResolvedValue({ id: 10, message: "Creado" });
  mount("/buscador/nuevo");
  expect(await screen.findByRole("heading", { name: "Nuevo titular PAS" })).toBeTruthy();
  const menu = screen.getByRole("navigation", { name: "Menú de PAS" });
  expect(within(menu).getByRole("link", { name: "Buscador PAS" }).getAttribute("aria-current")).toBe("page");
  expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/buscador");
  fireEvent.change(screen.getByRole("textbox", { name: "DNI" }), { target: { value: "40111222" } });
  fireEvent.click(screen.getByRole("button", { name: /^Guardar$/ }));
  await waitFor(() => expect(pasGet).toHaveBeenCalledWith("personas/?q=40111222"));
});

it("exporta la preliquidación a CSV desde el encabezado de la tabla", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  const fila = { id: 1, titular: "Perez, Ana", cuil: "27-1", cbu: "", monto: "78000.00", fch: null, cruces_ok: true, ddjj_ok: true, habilitado: true, estado_final: "Habilitado" };
  vi.mocked(pasGet).mockResolvedValue({ total_padron: 1, can_download: false, can_export_csv: true,
    liquidacion: { ...liquidacionVacia, filas: [fila], total_filas: 1 } });
  vi.mocked(exportarPreliquidacionCsv).mockResolvedValue(undefined);
  mount("/liquidacion");
  const boton = await screen.findByRole("button", { name: "Exportar CSV" });
  fireEvent.click(boton);
  await waitFor(() => expect(exportarPreliquidacionCsv).toHaveBeenCalledTimes(1));
});

it("deshabilita el CSV de preliquidación sin el permiso de exportación", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue({ total_padron: 1, can_export_csv: false, liquidacion: { ...liquidacionVacia, total_filas: 1 } });
  mount("/liquidacion");
  expect(((await screen.findByRole("button", { name: "Exportar CSV" })) as HTMLButtonElement).disabled).toBe(true);
});

it("muestra los cursos FCH solo como Inscripto o Aprobado con sus colores", async () => {
  vi.mocked(webGet).mockResolvedValue(ready);
  vi.mocked(pasGet).mockResolvedValue({ personas: [], persona_seleccionada: { id: 1, apellidos: "Prueba", nombres: "Ana" }, resumen: null, formaciones: [
    { curso: "Herramientas Digitales", inicio: "01/01/2025", fin: "15/01/2025", puntos: "30", estado: "Aprobado" },
    { curso: "Emprendimiento y Economía Social", inicio: "16/01/2025", fin: "", puntos: "", estado: "Inscripto" },
  ] });
  mount("/formacion");
  const aprobado = await screen.findByText("Aprobado");
  expect(aprobado.closest(".MuiChip-root")?.className).toContain("MuiChip-colorSuccess");
  expect(screen.getByText("Inscripto").closest(".MuiChip-root")?.className).toContain("MuiChip-colorInfo");
});
