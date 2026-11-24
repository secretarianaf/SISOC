import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ExpedienteDetalleScreen } from "./ExpedienteDetalleScreen";
import type { Detalle, Legajo } from "./expedienteDetalle/types";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

const noLegajoActions: Legajo["actions"] = {
  editar: null, eliminar: null, subir_archivo: null, comentarios: "/celiaquia/expedientes/7/legajos/70/comentarios/",
  agregar_comentario: null, confirmar_subsanacion: null, responder_subsanacion: null, responder_renaper: null,
  validar_renaper: null, revisar: null, motivo_preview: null, corregir_evaluacion: null,
};

const legajo: Legajo = {
  id: 70, ciudadano_id: 700, nombre: "Ana", apellido: "Sintética", documento: "20111222333", rol: "beneficiario",
  tipo_legajo: "Beneficiario", es_responsable: false, es_doble_rol: false, es_hijo: false, icono: "menor",
  hijos_a_cargo: [], responsables: [], badges: [{ text: "Solo Beneficiario", tone: "success" }], hijos_texto: null, alertas: [],
  revision_tecnico: "PENDIENTE", estado_validacion_renaper: 0, estado: "Pendiente",
  documentos: [{ label: "Doc1", nombre: "DNI", cargado: false }], observacion: { titulo: null, texto: null, items: [] },
  subsanacion_motivo: "", renaper: { comentario: "", archivo_url: null, respuesta_label: null, pendiente: false, solicitud_label: "Subsanación solicitada" },
  archivos: [{ campo: "archivo2", label: "DNI", url: null }], subsanacion_activa: null, subsanaciones_historial: [],
  comentarios_visibles: false, actions: noLegajoActions,
};

function detalle(overrides: Partial<Detalle> = {}): Detalle {
  return {
    version: 1,
    expediente: { id: 7, numero: "EX-SYNTHETIC", estado: "ASIGNADO", estado_display: "Asignado", fecha_creacion: "2026-11-24T12:00:00Z", provincia: "Chaco", tecnicos: ["Técnica Uno"], documento_url: null, excel: null },
    roles: { tecnico: false, coordinador: false, provincial: false, admin: false },
    flags: {},
    actions: { editar: null, nomina_sintys: null, historial: false, familias: false, subir_cruce: null, reprocesar_cruce: null, padron_final: null, confirmar_envio: null, asignar_tecnico: null, reprocesar_errores: null },
    cupo: null, alertas: [], fuera_de_cupo: [], preview: null, preview_error: null,
    legajos_total: 1, legajos: [legajo],
    historial: { items: [], page: 1, num_pages: 1 },
    registros_erroneos: [], tecnicos: [], catalogos: null,
    comentarios: { catalogo: {}, tipos_documento: [] },
    complementaria: { accept: ".pdf", max_archivos: 3, max_mb: 5 },
    messages: [],
    ...overrides,
  };
}

const json = (body: unknown, status = 200) => ({ ok: status < 400, status, redirected: false, headers: new Headers({ "Content-Type": "application/json" }), json: async () => body });

it("loads the canonical projection with its query and never calls V2 APIs", async () => {
  window.history.replaceState({}, "", "/celiaquia/expedientes/7/?historial_page=2&preview_limit=10");
  const data = detalle({
    preview: { headers: ["apellido"], rows: [["Uno"]], limit: "10", options: [{ value: "5", label: "5" }, { value: "10", label: "10" }, { value: "all", label: "Todos" }], procesar: "/celiaquia/expedientes/7/procesar/" },
    actions: { ...detalle().actions, historial: true },
    historial: { items: [{ id: 1, fecha: null, estado_anterior: "Creado", estado_nuevo: "Asignado", usuario: "Coord", observaciones: "" }], page: 2, num_pages: 3 },
  });
  const fetcher = vi.fn().mockResolvedValue(json(data));
  vi.stubGlobal("fetch", fetcher);
  render(<ExpedienteDetalleScreen />);
  expect(await screen.findByRole("heading", { name: /Detalle del Expediente/ })).toBeTruthy();
  expect(fetcher.mock.calls[0][0]).toBe("/celiaquia/expedientes/7/?historial_page=2&preview_limit=10");
  expect(fetcher.mock.calls[0][1].headers.Accept).toBe("application/json");
  expect((screen.getByLabelText("Registros a leer del Excel") as HTMLSelectElement).value).toBe("10");
  fireEvent.click(screen.getByRole("button", { name: "Ver Historial" }));
  const next = screen.getByRole("link", { name: "Siguiente" });
  expect(next.getAttribute("href")).toBe("/celiaquia/expedientes/7/?historial_page=3&preview_limit=10");
  fireEvent.click(next);
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  expect(window.location.search).toBe("?historial_page=3&preview_limit=10");
  expect(fetcher.mock.calls[1][0]).toBe("/celiaquia/expedientes/7/?historial_page=3&preview_limit=10");
  expect(fetcher.mock.calls.every(([url]) => !String(url).includes("/api/"))).toBe(true);
});

it("changing the Excel preview limit keeps it in the URL and back restores it", async () => {
  window.history.replaceState({}, "", "/celiaquia/expedientes/7/");
  const preview = { headers: ["apellido"], rows: [["Uno"]], limit: "all", options: [{ value: "5", label: "5" }, { value: "all", label: "Todos" }], procesar: null };
  const fetcher = vi.fn().mockResolvedValue(json(detalle({ preview })));
  vi.stubGlobal("fetch", fetcher);
  render(<ExpedienteDetalleScreen />);
  fireEvent.change(await screen.findByLabelText("Registros a leer del Excel"), { target: { value: "5" } });
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  expect(window.location.search).toBe("?preview_limit=5");
  window.history.replaceState({}, "", "/celiaquia/expedientes/7/");
  window.dispatchEvent(new PopStateEvent("popstate"));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
  expect(fetcher.mock.calls[2][0]).toBe("/celiaquia/expedientes/7/");
});

it("shows no action that the projection does not grant", async () => {
  window.history.replaceState({}, "", "/celiaquia/expedientes/7/");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(detalle())));
  render(<ExpedienteDetalleScreen />);
  fireEvent.click(await screen.findByRole("button", { name: "Ver detalle de Ana Sintética" }));
  for (const name of ["Aprobar", "Rechazar", "Subsanar", "Validar Renaper", "Corregir evaluación", "Confirmar Envío", "Editar Metadatos", "Descargar nómina Sintys", "Ver Historial", "Procesar Expediente"]) {
    expect(screen.queryByRole("button", { name })).toBeNull();
    expect(screen.queryByRole("link", { name })).toBeNull();
  }
  expect(screen.queryByRole("button", { name: /^Subir DNI/ })).toBeNull();
  expect(screen.getByText("Pendiente de carga")).toBeTruthy();
});

it("approves through the native revisar endpoint and then reloads the projection", async () => {
  window.history.replaceState({}, "", "/celiaquia/expedientes/7/");
  const granted = detalle({
    roles: { tecnico: true, coordinador: false, provincial: false, admin: false },
    legajos: [{ ...legajo, actions: { ...noLegajoActions, revisar: "/celiaquia/expedientes/7/legajos/70/revisar/", validar_renaper: "/celiaquia/expedientes/7/legajos/70/validar-renaper/", motivo_preview: "/celiaquia/expedientes/7/legajos/70/motivo-preview/" } }],
  });
  const fetcher = vi.fn()
    .mockResolvedValueOnce(json(granted))
    .mockResolvedValueOnce(json({ success: true, message: "Legajo aprobado." }))
    .mockResolvedValueOnce(json({ ...granted, legajos: [{ ...legajo, estado: "Aprobado", revision_tecnico: "APROBADO" }] }));
  vi.stubGlobal("fetch", fetcher);
  render(<ExpedienteDetalleScreen />);
  fireEvent.click(await screen.findByRole("button", { name: "Ver detalle de Ana Sintética" }));
  fireEvent.click(screen.getByRole("button", { name: "Aprobar" }));
  expect(await screen.findByText("Legajo aprobado.")).toBeTruthy();
  const [url, init] = fetcher.mock.calls[1];
  expect(url).toBe("/celiaquia/expedientes/7/legajos/70/revisar/");
  expect(init.method).toBe("POST");
  expect((init.body as FormData).get("accion")).toBe("APROBAR");
  expect(fetcher.mock.calls[2][0]).toBe("/celiaquia/expedientes/7/");
  expect(fetcher).toHaveBeenCalledTimes(3);
});

it("surfaces a native rejection and does not reload", async () => {
  window.history.replaceState({}, "", "/celiaquia/expedientes/7/");
  const data = detalle({ roles: { tecnico: false, coordinador: false, provincial: true, admin: false }, actions: { ...detalle().actions, confirmar_envio: "/celiaquia/expedientes/7/confirmar/" } });
  const fetcher = vi.fn().mockResolvedValueOnce(json(data)).mockResolvedValueOnce(json({ success: false, error: "Hay legajos sin archivos." }, 400));
  vi.stubGlobal("fetch", fetcher);
  render(<ExpedienteDetalleScreen />);
  fireEvent.click(await screen.findByRole("button", { name: "Confirmar Envío" }));
  expect(await screen.findByText("Hay legajos sin archivos.")).toBeTruthy();
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it("renders pending Django messages and a 404 as an error", async () => {
  window.history.replaceState({}, "", "/celiaquia/expedientes/7/");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(detalle({ messages: [{ level: "success", text: "Expediente actualizado." }] }))));
  render(<ExpedienteDetalleScreen />);
  expect(await screen.findByText("Expediente actualizado.")).toBeTruthy();
  cleanup();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({}, 404)));
  render(<ExpedienteDetalleScreen />);
  expect(await screen.findByText("No se encontró el recurso solicitado.")).toBeTruthy();
});

it("rejects with the motives the native preview offers and requires a motive", async () => {
  window.history.replaceState({}, "", "/celiaquia/expedientes/7/");
  const actions = { ...noLegajoActions, revisar: "/celiaquia/expedientes/7/legajos/70/revisar/", motivo_preview: "/celiaquia/expedientes/7/legajos/70/motivo-preview/" };
  const data = detalle({ legajos: [{ ...legajo, actions }] });
  const fetcher = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
    if (url.endsWith("/motivo-preview/")) return json({ success: true, tiene_observaciones: true, opciones: [{ id: 5, etiqueta: "DNI ilegible", pendiente: true }, { id: 6, etiqueta: "Falta biopsia", pendiente: false }] });
    if (init?.method === "POST") return json({ success: true });
    return json(data);
  });
  vi.stubGlobal("fetch", fetcher);
  render(<ExpedienteDetalleScreen />);
  fireEvent.click(await screen.findByRole("button", { name: "Ver detalle de Ana Sintética" }));
  fireEvent.click(screen.getByRole("button", { name: "Rechazar" }));
  const pending = await screen.findByRole("checkbox", { name: "DNI ilegible" });
  expect((pending as HTMLInputElement).checked).toBe(true);
  fireEvent.click(pending);
  fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));
  expect(await screen.findByText("Seleccioná al menos un motivo o completá la información complementaria.")).toBeTruthy();
  expect(fetcher.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  fireEvent.click(screen.getByRole("checkbox", { name: /Falta biopsia/ }));
  fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));
  await screen.findByText("Legajo rechazado.");
  const post = fetcher.mock.calls.find(([, init]) => init?.method === "POST")!;
  expect(post[0]).toBe("/celiaquia/expedientes/7/legajos/70/revisar/");
  expect((post[1].body as FormData).get("accion")).toBe("RECHAZAR");
  expect((post[1].body as FormData).getAll("observaciones_ids")).toEqual(["6"]);
});

const registro = (id: number, apellido: string) => ({
  id, fila: id, datos_raw: { apellido, nombre: "Uno", documento: "20111222333", sexo: "F" }, datos: {},
  mensaje_error: "Falta municipio", invalid_fields: ["municipio"], responsable_requerido: false,
  nacionalidad_id: "", municipio_id: "", actualizar_url: `/celiaquia/expedientes/7/registros-erroneos/${id}/actualizar/`,
  eliminar_url: `/celiaquia/expedientes/7/registros-erroneos/${id}/eliminar/`,
});
const catalogos = {
  sexos: [{ id: 1, label: "Femenino" }, { id: 2, label: "Masculino" }], nacionalidades: [{ id: 10, label: "Argentina" }],
  nacionalidad_argentina_id: "10", municipios: [{ id: 20, label: "Resistencia" }], localidades: [{ id: 30, label: "Centro", municipio_id: 20, municipio: "Resistencia" }],
};
const posts = (fetcher: ReturnType<typeof vi.fn>) => fetcher.mock.calls.filter(([, init]) => init?.method === "POST");

it("autosaves an erroneous record after a 500 ms pause with the native JSON body and never retries a failure", async () => {
  window.history.replaceState({}, "", "/celiaquia/expedientes/7/");
  const data = detalle({ registros_erroneos: [registro(1, "Pérez")], catalogos });
  let saves = 0;
  const fetcher = vi.fn().mockImplementation(async (_url: string, init?: RequestInit) => {
    if (init?.method !== "POST") return json(data);
    saves += 1;
    return saves === 1 ? json({ success: true, message: "Registro actualizado correctamente." }) : json({ success: false, error: "Ocurrió un error interno al actualizar el registro." }, 500);
  });
  vi.stubGlobal("fetch", fetcher);
  render(<ExpedienteDetalleScreen />);
  fireEvent.click(await screen.findByRole("button", { name: "Editar" }));
  expect(screen.getByText(/Los campos se guardan automáticamente al cambiar/)).toBeTruthy();
  const apellido = screen.getByLabelText("Apellido *") as HTMLInputElement;
  fireEvent.input(apellido, { target: { value: "Pére" } });
  fireEvent.input(apellido, { target: { value: " Pérez Gómez " } });
  expect(posts(fetcher)).toHaveLength(0);
  await waitFor(() => expect(posts(fetcher)).toHaveLength(1), { timeout: 1500 });
  const [url, init] = posts(fetcher)[0];
  expect(url).toBe("/celiaquia/expedientes/7/registros-erroneos/1/actualizar/");
  expect(init.headers["Content-Type"]).toBe("application/json");
  const body = JSON.parse(init.body as string);
  expect(body.apellido).toBe("Pérez Gómez");
  expect(body.sexo).toBe("1");
  expect(await screen.findByText("Cambios guardados.")).toBeTruthy();
  fireEvent.input(apellido, { target: { value: "Gómez" } });
  expect(await screen.findByText("Error: Ocurrió un error interno al actualizar el registro.", undefined, { timeout: 1500 })).toBeTruthy();
  await new Promise((resolve) => setTimeout(resolve, 700));
  expect(posts(fetcher)).toHaveLength(2);
  expect((screen.getByLabelText("Apellido *") as HTMLInputElement).value).toBe("Gómez");
  // Collapsing and reopening keeps the unsaved edit.
  fireEvent.click(screen.getByRole("button", { name: "Editar" }));
  fireEvent.click(screen.getByRole("button", { name: "Editar" }));
  expect((screen.getByLabelText("Apellido *") as HTMLInputElement).value).toBe("Gómez");
  expect(fetcher).toHaveBeenCalledTimes(3);
});

it("Reprocesar Todos saves every erroneous record first and warns about the ones still invalid", async () => {
  window.history.replaceState({}, "", "/celiaquia/expedientes/7/");
  const data = detalle({ registros_erroneos: [registro(1, "Pérez"), registro(2, "López")], catalogos, actions: { ...detalle().actions, reprocesar_errores: "/celiaquia/expedientes/7/registros-erroneos/reprocesar/" } });
  const fetcher = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
    if (init?.method !== "POST") return json(data);
    if (url.includes("/2/actualizar/")) return json({ success: false, saved_partial: true, error: "CUIL inválido", invalid_fields: ["documento"] }, 400);
    if (url.includes("/1/actualizar/")) return json({ success: false, error: "Ocurrió un error interno al actualizar el registro." }, 500);
    return json({ success: true, creados: 1, errores: 1, excluidos: 0, registros_restantes: 1 });
  });
  vi.stubGlobal("fetch", fetcher);
  vi.spyOn(window, "confirm").mockReturnValue(true);
  render(<ExpedienteDetalleScreen />);
  fireEvent.click(await screen.findByRole("button", { name: "Reprocesar Todos" }));
  expect(await screen.findByText(/Se guardaron 1 registros antes de reprocesar y 1 siguen con errores de validacion\./)).toBeTruthy();
  expect(screen.getByText(/Se creó 1 legajo correctamente\. 1 registro aún tienen errores\./)).toBeTruthy();
  expect(posts(fetcher).map(([url]) => url)).toEqual([
    "/celiaquia/expedientes/7/registros-erroneos/1/actualizar/",
    "/celiaquia/expedientes/7/registros-erroneos/2/actualizar/",
    "/celiaquia/expedientes/7/registros-erroneos/reprocesar/",
  ]);
  expect(JSON.parse(posts(fetcher)[1][1].body as string).apellido).toBe("López");
});

it("shows the native simulated progress counter while Procesar runs and keeps the success alert for a reload", async () => {
  window.history.replaceState({}, "", "/celiaquia/expedientes/7/");
  window.localStorage.clear();
  const preview = { headers: ["apellido"], rows: [["Uno"], ["Dos"], ["Tres"]], limit: "all", options: [{ value: "all", label: "Todos" }], procesar: "/celiaquia/expedientes/7/procesar/" };
  const data = detalle({ preview });
  let finish: (value: unknown) => void = () => undefined;
  const fetcher = vi.fn().mockImplementation(async (_url: string, init?: RequestInit) => {
    if (init?.method !== "POST") return json(data);
    return new Promise((resolve) => { finish = resolve; });
  });
  vi.stubGlobal("fetch", fetcher);
  render(<ExpedienteDetalleScreen />);
  fireEvent.click(await screen.findByRole("button", { name: "Procesar Expediente" }));
  expect(screen.getByRole("button", { name: /Procesando 0 \/ 3 registros\.\.\./ })).toBeTruthy();
  expect(await screen.findByRole("button", { name: /Procesando 3 \/ 3 registros\.\.\./ }, { timeout: 1500 })).toBeTruthy();
  finish(json({ success: true, creados: 3, errores: 0, alerta_resumen: "Se crearon 3 legajos." }));
  expect(await screen.findByText("¡Listo! Se crearon 3 legajos.")).toBeTruthy();
  expect(screen.getByRole("button", { name: /Completado 3 \/ 3 registros/ })).toBeTruthy();
  const stored = JSON.parse(window.localStorage.getItem("expediente-detail-timed-alert:7") ?? "null");
  expect(stored).toMatchObject({ kind: "success", message: "Se crearon 3 legajos." });
  expect(stored.expiresAt).toBeGreaterThan(Date.now() + 100000);
  expect(posts(fetcher)).toHaveLength(1);
});

it("restores an unexpired timed success alert after a reload and drops an expired one", async () => {
  window.history.replaceState({}, "", "/celiaquia/expedientes/7/");
  window.localStorage.setItem("expediente-detail-timed-alert:7", JSON.stringify({ kind: "success", message: "Se crearon 2 legajos.", expiresAt: Date.now() + 60000 }));
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(detalle())));
  render(<ExpedienteDetalleScreen />);
  expect(await screen.findByText("Se crearon 2 legajos.")).toBeTruthy();
  cleanup();
  window.localStorage.setItem("expediente-detail-timed-alert:7", JSON.stringify({ kind: "success", message: "Vieja alerta.", expiresAt: Date.now() - 1 }));
  render(<ExpedienteDetalleScreen />);
  await screen.findByRole("heading", { name: /Detalle del Expediente/ });
  expect(screen.queryByText("Vieja alerta.")).toBeNull();
  expect(window.localStorage.getItem("expediente-detail-timed-alert:7")).toBeNull();
});

it("filters the técnico list with an accessible search box before assigning", async () => {
  window.history.replaceState({}, "", "/celiaquia/expedientes/7/");
  const data = detalle({ actions: { ...detalle().actions, asignar_tecnico: "/celiaquia/expedientes/7/asignar-tecnico/" }, tecnicos: [{ id: 1, name: "Ana Álvarez" }, { id: 2, name: "Bruno Díaz" }, { id: 3, name: "Carla Díez" }] });
  const fetcher = vi.fn().mockImplementation(async (_url: string, init?: RequestInit) => (init?.method === "POST" ? json({ success: true }) : json(data)));
  vi.stubGlobal("fetch", fetcher);
  render(<ExpedienteDetalleScreen />);
  const filtro = await screen.findByRole("searchbox", { name: "Buscar Técnico" });
  const select = screen.getByRole("combobox", { name: /Seleccionar Técnico/ }) as HTMLSelectElement;
  expect(select.options).toHaveLength(3);
  fireEvent.change(filtro, { target: { value: "diez" } });
  expect(Array.from(select.options).map((o) => o.text)).toEqual(["Ana Álvarez", "Carla Díez"]);
  fireEvent.keyDown(filtro, { key: "Enter" });
  expect(select.value).toBe("3");
  expect(document.activeElement).toBe(select);
  fireEvent.click(screen.getByRole("button", { name: "Asignar" }));
  await waitFor(() => expect(posts(fetcher)).toHaveLength(1));
  expect((posts(fetcher)[0][1].body as FormData).get("tecnico_id")).toBe("3");
});
