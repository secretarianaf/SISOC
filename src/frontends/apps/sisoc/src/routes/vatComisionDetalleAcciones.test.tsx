import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { comisionDetalleValid } from "./vatComisionDetalle";
import { comisionNav, errorMessage } from "./vatComisionDetalleAcciones";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const CURSO = "/vat/cursos/comisiones/8/";
const API = "web/vat/comisiones-detalle/cursos/8/";
const ALL = {
  gestionar_comision: true, editar_comision: true, eliminar_comision: true, agregar_inscripcion: true, cambiar_inscripcion: true, eliminar_inscripcion: true,
  gestionar_asistencia: true, agregar_comision_horario: true, editar_comision_horario: true, eliminar_comision_horario: true, gestionar_lote_inscriptos: true,
  gestionar_resultados: true,
};
const field = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label, tag: "input", attrs: { class: "form-control", type: "text" }, value: "", choices: [], errors: [], ...over,
});
const RAPIDA = [
  field("apellido", "Apellido"), field("nombre", "Nombre"),
  field("tipo_documento", "Tipo de documento", { tag: "select", attrs: { class: "form-control" }, value: "DNI", choices: [{ value: "DNI", label: "DNI" }, { value: "PASAPORTE", label: "Pasaporte" }] }),
  field("documento", "Documento"), field("fecha_nacimiento", "Fecha de Nacimiento", { attrs: { class: "form-control", type: "date" } }),
  field("sexo", "Sexo", { tag: "select", attrs: { class: "form-control" }, choices: [{ value: "", label: "---------" }, { value: "1", label: "Femenino" }] }),
];
const PROFESOR = [field("apellido", "Apellido", { attrs: { class: "form-control", type: "text", required: "required" } }), field("nombre", "Nombre"), field("documento", "Documento"), field("email", "Email", { attrs: { class: "form-control", type: "email" } })];
const inscripto = (id: number, over: Record<string, unknown> = {}) => ({
  id, apellido: `Apellido${id}`, nombre: `Nombre${id}`, documento: `DNI 3011${id}`, estado: "pre_inscripta", estado_label: "Pre-inscripta", detail_url: `/vat/inscripciones/${id}/`,
  busqueda: `apellido${id} nombre${id}`, tipo_alumno: "Sin Plan", es_alumno_vat: false, email: "—", telefono: "—", asistencia: null, delete_url: `/vat/inscripciones/${id}/eliminar/`, ...over,
});
const espera = (id: number) => ({ ...inscripto(id), estado: "en_espera", estado_label: "En Espera", fecha: "02/03/2026" });
const resultados = (over: Record<string, unknown> = {}) => ({
  aprobado: "aprobado", desaprobado: "desaprobado", resumen: { aprobados: "1", desaprobados: "0", sin_calificar: "1", inscriptos: "2" },
  alumnos: [{ id: 21, apellido: "Prueba", nombre: "Ana", documento: "DNI 30111222", resultado: "aprobado" }, { id: 22, apellido: "Ejemplo", nombre: "Beto", documento: "DNI 30111223", resultado: "" }],
  profesor_id: null, profesor_texto: "", fecha_fin: "2026-06-30", numero_acta: "", ...over,
});
const data = (over: Record<string, unknown> = {}) => ({
  tipo: "curso", id: 8, codigo: "COM-8", nombre: "Comisión Ocho", titulo_tipo: "Comisión de Curso", subtitulo: "Electricidad básica", estado_label: "Planificada",
  acepta_lista_espera: true, ubicacion: "CFP 401", fecha_inicio: "01/03/2026", fecha_fin: "30/06/2026", cupo: "5", cupo_lista_espera: "3", cupo_ocupado: "2",
  clases_dictadas: "0", clases_pendientes: "0", metricas: [], horarios: [], sesiones: [],
  inscripciones: [inscripto(1), inscripto(2, { estado: "inscripta", estado_label: "Inscripta" }), inscripto(3)], lista_espera: [espera(9)],
  permisos: ALL, urls: { eliminar: "/vat/cursos/comisiones/8/eliminar/", exportar_preinscriptos: null, exportar_inscriptos: null, horario_nuevo: "/x/" },
  resultados: resultados(), formularios: { rapida: RAPIDA, profesor: PROFESOR }, messages: [], ...over,
});

type Extra = Record<string, (config?: { params?: Record<string, string> }) => unknown>;
function serve(payload: unknown, extra: Extra = {}) {
  webGet.mockImplementation((url: string, config?: { params?: Record<string, string> }) => {
    if (url === "web/session/") return Promise.resolve({ data: readyContext, status: 200 });
    if (url in extra) return Promise.resolve({ data: extra[url](config), status: 200 });
    return Promise.resolve({ data: payload, status: 200 });
  });
}
async function open(path: string, payload = data(), extra: Extra = {}) {
  serve(payload, extra);
  window.history.replaceState({}, "", path);
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: "Comisión Ocho" });
}
const byId = (id: string) => document.getElementById(id) as HTMLElement;
// Role queries compute styles for the whole page (the native stylesheet is large): inside the modals plain lookups keep the tests fast.
const button = (root: HTMLElement, name: string) => Array.from(root.querySelectorAll("button")).find((b) => b.textContent === name) as HTMLElement;
const text = (id: string) => byId(id).textContent;
const redirect = (url: string) => webPost.mockResolvedValue({ data: { ok: true, redirect: url }, status: 200 });
const body = (call = 0) => Object.fromEntries((webPost.mock.calls[call][1] as URLSearchParams).entries());

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  window.history.replaceState({}, "", "/");
  setViewport(false);
  vi.spyOn(comisionNav, "assign").mockImplementation(() => undefined);
  vi.spyOn(comisionNav, "reload").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("comisión detalle: admit or reject from the wait list", () => {
  it("posts the new state to the U3 endpoint of the variant and follows the native redirect", async () => {
    await open(`${CURSO}#espera`);
    redirect(CURSO);
    fireEvent.click(within(document.getElementById("esperaTablaBody") as HTMLElement).getByRole("button", { name: /Admitir/ }));
    await waitFor(() => expect(comisionNav.assign).toHaveBeenCalledWith(CURSO));
    expect(webPost.mock.calls[0][0]).toBe("web/vat/inscripciones-persona/cursos/9/cambiar-estado/");
    expect(body()).toEqual({ estado: "inscripta" });
    fireEvent.click(within(byId("esperaTablaBody")).getByRole("button", { name: /Rechazar/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(2));
    expect(body(1)).toEqual({ estado: "rechazada" });
    expect(within(byId("esperaTablaBody")).getByRole("button", { name: /Admitir/ }).getAttribute("title")).toBe("Admitir desde la lista de espera");
  });

  it("uses the offer endpoint and shows the uncertain outcome without a redirect", async () => {
    await open("/vat/comisiones/8/#espera", data({ tipo: "oferta", acepta_lista_espera: false }));
    webPost.mockResolvedValue({ data: {}, status: 200 });
    fireEvent.click(within(byId("esperaTablaBody")).getByRole("button", { name: /Admitir/ }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(webPost.mock.calls[0][0]).toBe("web/vat/inscripciones-persona/9/cambiar-estado/");
    expect(comisionNav.assign).not.toHaveBeenCalled();
  });

  it("has no actions column without the change permission", async () => {
    await open(`${CURSO}#espera`, data({ permisos: { ...ALL, cambiar_inscripcion: false } }));
    expect(Array.from(document.querySelectorAll("#esperaTabla thead th")).map((e) => e.textContent)).toEqual(["Apellido", "Nombre", "Documento", "Fecha", "Estado"]);
    expect(document.querySelectorAll("#esperaTablaBody button")).toHaveLength(0);
  });
});

describe("comisión detalle: batch accept/reject", () => {
  const checks = () => Array.from(document.querySelectorAll<HTMLInputElement>(".ci-lote-check"));

  it("counts the selection, selects what the filter shows and clears it when the filter changes", async () => {
    await open(`${CURSO}#inscriptos`);
    expect(text("inscriptosLoteConteo")).toBe("0 seleccionados");
    expect((byId("inscriptosLoteAceptar") as HTMLButtonElement).disabled).toBe(true);
    expect((byId("inscriptosLoteRechazar") as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(checks()[0]);
    expect(text("inscriptosLoteConteo")).toBe("1 seleccionado");
    expect((byId("inscriptosLoteAceptar") as HTMLButtonElement).disabled).toBe(false);
    expect((byId("inscriptosLoteTodos") as HTMLInputElement).indeterminate).toBe(true);
    fireEvent.click(byId("inscriptosLoteTodos"));
    expect(text("inscriptosLoteConteo")).toBe("3 seleccionados");
    expect((byId("inscriptosLoteTodos") as HTMLInputElement).checked).toBe(true);
    fireEvent.change(byId("inscriptosBuscador"), { target: { value: "apellido2" } });
    expect(text("inscriptosLoteConteo")).toBe("0 seleccionados");
    fireEvent.click(byId("inscriptosLoteTodos"));
    expect(text("inscriptosLoteConteo")).toBe("1 seleccionado");
    expect(checks().filter((c) => c.checked).map((c) => c.value)).toEqual(["2"]);
  });

  it("confirms with the native texts and posts the selected ids, then returns to the tab", async () => {
    await open(`${CURSO}#inscriptos`);
    fireEvent.click(checks()[0]);
    fireEvent.click(checks()[1]);
    fireEvent.click(byId("inscriptosLoteAceptar"));
    const modal = byId("modalInscriptosLote");
    expect(within(modal).getByText("Confirmar acción")).toBeTruthy();
    expect(text("inscriptosLoteResumen")).toBe("¿Confirmás aceptar 2 inscripciones?");
    expect(text("inscriptosLoteDetalle")).toBe("1 cambian de estado; 1 ya estaban en ese estado y no se modifican.");
    redirect(`${CURSO}#inscriptos`);
    fireEvent.click(byId("inscriptosLoteConfirmar"));
    expect(byId("inscriptosLoteConfirmar").textContent).toBe("Procesando...");
    await waitFor(() => expect(comisionNav.reload).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe("web/vat/inscripciones-persona/cursos/comisiones/8/cambiar-estado-lote/");
    const params = webPost.mock.calls[0][1] as URLSearchParams;
    expect(params.get("estado")).toBe("inscripta");
    expect(params.getAll("inscripciones")).toEqual(["1", "2"]);
    expect(window.location.hash).toBe("#inscriptos");
  });

  it("words the reject confirmation in the singular and closes with Escape or Cancelar", async () => {
    await open(`${CURSO}#inscriptos`);
    fireEvent.click(checks()[0]);
    fireEvent.click(byId("inscriptosLoteRechazar"));
    expect(text("inscriptosLoteResumen")).toBe("¿Confirmás rechazar 1 inscripción?");
    expect(text("inscriptosLoteDetalle")).toBe("");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(document.getElementById("modalInscriptosLote")).toBeNull();
    fireEvent.click(byId("inscriptosLoteRechazar"));
    fireEvent.click(within(byId("modalInscriptosLote")).getByRole("button", { name: "Cancelar" }));
    expect(document.getElementById("modalInscriptosLote")).toBeNull();
    expect(webPost).not.toHaveBeenCalled();
  });

  it("has no selection column or batch buttons without the batch permission", async () => {
    await open(`${CURSO}#inscriptos`, data({ permisos: { ...ALL, gestionar_lote_inscriptos: false } }));
    expect(document.getElementById("inscriptosLoteTodos")).toBeNull();
    expect(document.getElementById("inscriptosLoteAceptar")).toBeNull();
    expect(document.querySelector("#inscriptosTabla form")).toBeNull();
  });
});

describe("comisión detalle: quick enrolment", () => {
  const openModal = async (payload = data(), path = `${CURSO}#inscriptos`) => {
    await open(path, payload);
    fireEvent.click(screen.getByRole("button", { name: /Agregar inscripto/ }));
    return byId("modalInscripcionRapida");
  };
  const search = (value: string, extra: Extra = {}) => {
    serve(data(), extra);
    fireEvent.change(byId("inscripcionDocumentoSearch"), { target: { value } });
    fireEvent.click(byId("inscripcionBuscarBtn"));
  };

  it("opens with the native structure and validates the document before searching", async () => {
    const modal = await openModal();
    expect(within(modal).getByText("Inscribir ciudadano")).toBeTruthy();
    expect(modal.className).toBe("modal fade ci-modal show d-block");
    expect(byId("inscripcionDocumentoSearch").getAttribute("placeholder")).toBe("Ingrese DNI (mín. 7 dígitos)");
    fireEvent.click(byId("inscripcionBuscarBtn"));
    expect(text("inscripcionRapidaAlert")).toBe("Ingrese un documento numérico de al menos 7 dígitos.");
    expect(byId("inscripcionRapidaAlert").className).toBe("alert alert-warning");
    fireEvent.change(byId("inscripcionTipoDocumentoSearch"), { target: { value: "PASAPORTE" } });
    expect(byId("inscripcionDocumentoSearch").getAttribute("placeholder")).toBe("Ingrese pasaporte (6 a 15 caracteres)");
    expect(byId("inscripcionRapidaAlert").className).toBe("alert d-none");
    fireEvent.change(byId("inscripcionDocumentoSearch"), { target: { value: "ab" } });
    fireEvent.click(byId("inscripcionBuscarBtn"));
    expect(text("inscripcionRapidaAlert")).toBe("Ingrese un pasaporte de 6 a 15 caracteres alfanuméricos.");
    expect(webGet).not.toHaveBeenCalledWith("ciudadanos/buscar/", expect.anything());
  });

  it("selects a found citizen and enrols it with the observations", async () => {
    await openModal();
    search("30111222", { "ciudadanos/buscar/": () => ({ results: [{ id: 77, text: "Prueba, Ana - DNI 30111222" }] }) });
    fireEvent.click(await screen.findByText("Prueba, Ana - DNI 30111222"));
    expect(text("inscripcionSelectedCitizen")).toBe("Ciudadano seleccionado: Prueba, Ana - DNI 30111222");
    expect(webGet).toHaveBeenCalledWith("ciudadanos/buscar/", { params: { q: "30111222", tipo_documento: "DNI" } });
    fireEvent.change(byId("inscripcionObservaciones"), { target: { value: "Llegó por mostrador" } });
    webPost.mockResolvedValue({ data: { ok: true, message: "Inscripción creada para Ana Prueba.", inscripcion_id: 5, estado: "inscripta" }, status: 200 });
    fireEvent.click(button(byId("modalInscripcionRapida"), "Inscribir"));
    await waitFor(() => expect(comisionNav.reload).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe("web/vat/inscripciones-persona/cursos/rapida-comision/");
    expect(body()).toMatchObject({ comision: "8", ciudadano_id: "77", observaciones: "Llegó por mostrador", tipo_documento: "DNI" });
  });

  it("offers the short form with the searched document when nobody matches and shows the server errors", async () => {
    await openModal();
    fireEvent.change(byId("inscripcionTipoDocumentoSearch"), { target: { value: "PASAPORTE" } });
    search("ab12cd34", { "ciudadanos/buscar/": () => ({ results: [] }) });
    await waitFor(() => expect(byId("inscripcionNoResults").className).toBe("alert alert-info mb-3"));
    expect(byId("inscripcionQuickCitizenSection").className).toBe("border rounded-3 p-3");
    expect((byId("id_documento") as HTMLInputElement).value).toBe("AB12CD34");
    expect((byId("id_tipo_documento") as HTMLSelectElement).value).toBe("PASAPORTE");
    expect(webGet).toHaveBeenCalledWith("ciudadanos/buscar/", { params: { q: "AB12CD34", tipo_documento: "PASAPORTE" } });
    fireEvent.change(byId("id_apellido"), { target: { value: "Nueva" } });
    webPost.mockResolvedValue({ data: { ok: false, message: "Errores en el formulario de ciudadano.", errors: { nombre: ["Este campo es obligatorio."], fecha_nacimiento: ["Fecha inválida."] } }, status: 400 });
    fireEvent.click(button(byId("modalInscripcionRapida"), "Inscribir"));
    await waitFor(() => expect(text("inscripcionRapidaAlert")).toBe("Este campo es obligatorio. Fecha inválida."));
    expect(byId("inscripcionRapidaAlert").className).toBe("alert alert-danger");
    expect(comisionNav.reload).not.toHaveBeenCalled();
    expect(body()).toMatchObject({ apellido: "Nueva", documento: "AB12CD34", ciudadano_id: "" });
    expect(button(byId("modalInscripcionRapida"), "Inscribir")).toBeTruthy();
  });

  it("shows the message of a rejected enrolment and the search failure, and uses the offer endpoint", async () => {
    await openModal(data({ tipo: "oferta", acepta_lista_espera: false, resultados: null, formularios: { rapida: RAPIDA, profesor: null }, permisos: { ...ALL, gestionar_resultados: false } }), "/vat/comisiones/8/#inscriptos");
    search("30111222", { "ciudadanos/buscar/": () => { throw new Error("down"); } });
    await waitFor(() => expect(text("inscripcionRapidaAlert")).toBe("No se pudo buscar ciudadanos en este momento."));
    search("30111222", { "ciudadanos/buscar/": () => ({ results: [{ id: 5, text: "Otro" }] }) });
    fireEvent.click(await screen.findByText("Otro"));
    webPost.mockResolvedValue({ data: { ok: false, message: "La comisión está cerrada." }, status: 400 });
    fireEvent.click(button(byId("modalInscripcionRapida"), "Inscribir"));
    await waitFor(() => expect(text("inscripcionRapidaAlert")).toBe("La comisión está cerrada."));
    expect(webPost.mock.calls[0][0]).toBe("web/vat/inscripciones-persona/rapida-comision/");
    webPost.mockRejectedValue(new Error("network"));
    fireEvent.click(button(byId("modalInscripcionRapida"), "Inscribir"));
    await waitFor(() => expect(text("inscripcionRapidaAlert")).toBe("No se pudo completar la inscripción."));
  });

  it("closes with the close button, Cancelar or the backdrop", async () => {
    const modal = await openModal();
    fireEvent.click(within(modal).getByRole("button", { name: "Close" }));
    expect(document.getElementById("modalInscripcionRapida")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Agregar inscripto/ }));
    fireEvent.click(byId("modalInscripcionRapida"));
    expect(document.getElementById("modalInscripcionRapida")).toBeNull();
  });
});

describe("comisión detalle: results of the acta", () => {
  const row = (id: number) => document.querySelector(`[data-inscripcion="${id}"]`) as HTMLElement;
  const summary = () => ["aprobados", "desaprobados", "sin_calificar", "inscriptos"].map((k) => document.querySelector(`[data-resumen="${k}"]`)?.textContent);

  it("renders the tab, the summary and the acta fields as the native template", async () => {
    await open(`${CURSO}#resultados`);
    expect(within(screen.getByRole("tablist", { name: "Secciones de la comisión" })).getByRole("button", { name: "Resultados" })).toBeTruthy();
    expect(Array.from(document.querySelectorAll(".sisoc-side-tabs--right .sisoc-side-tab")).map((e) => e.textContent).at(-1)).toBe("Resultados (2)");
    expect(summary()).toEqual(["1", "0", "1", "2"]);
    expect((byId("actaFechaFin") as HTMLInputElement).value).toBe("2026-06-30");
    expect(byId("profesorChip").className).toBe("ci-prof-chip d-none");
    expect(text("resultadosConteo")).toBe("Mostrando 2 de 2");
    expect(row(21).querySelector("[data-resultado-pill]")?.className).toBe("ci-pill ci-pill-green");
    expect(row(22).querySelector("[data-resultado-pill]")?.textContent).toBe("Sin calificar");
    expect((row(21).querySelector("[data-resultado-input]") as HTMLInputElement).name).toBe("resultado_21");
  });

  it("marks students, recounts and filters like the page script", async () => {
    await open(`${CURSO}#resultados`);
    fireEvent.click(within(row(22)).getByRole("button", { name: /Desaprobar/ }));
    expect(summary()).toEqual(["1", "1", "0", "2"]);
    expect(row(22).getAttribute("data-resultado")).toBe("desaprobado");
    expect(row(22).querySelector("[data-resultado-pill]")?.className).toBe("ci-pill ci-pill-red");
    fireEvent.click(screen.getByRole("button", { name: "A calificar" }));
    expect(text("resultadosConteo")).toBe("Mostrando 0 de 2");
    expect(document.querySelector("[data-sin-resultados-row]")?.classList.contains("d-none")).toBe(false);
    expect(screen.getByRole("button", { name: "A calificar" }).className).toBe("ci-filtro-btn is-active");
    fireEvent.click(within(row(22)).getByRole("button", { name: /Aprobar/ }));
    fireEvent.click(screen.getByRole("button", { name: "Finalizados" }));
    expect(text("resultadosConteo")).toBe("Mostrando 2 de 2");
    expect(row(21).classList.contains("d-none")).toBe(false);
  });

  it("asks for the teacher and the end date before saving", async () => {
    await open(`${CURSO}#resultados`);
    fireEvent.click(screen.getByRole("button", { name: /Guardar resultados/ }));
    expect(text("resultadosAlert")).toBe("Seleccioná el profesor a cargo para guardar el acta.");
    expect(byId("resultadosAlert").className).toBe("alert alert-danger");
    fireEvent.click(within(row(22)).getByRole("button", { name: /Aprobar/ }));
    expect(byId("resultadosAlert").className).toBe("alert d-none");
    expect(webPost).not.toHaveBeenCalled();
  });

  it("searches teachers, selects one, requires the end date and saves through the native endpoint", async () => {
    await open(`${CURSO}#resultados`, data(), { [`${API}profesores/buscar/`]: (config) => ({ results: config?.params?.q === "dora" ? [{ id: 5, text: "Docente, Dora — DNI 20111222 — dora@example.com" }] : [] }) });
    fireEvent.change(byId("profesorBuscador"), { target: { value: "d" } });
    expect(webGet).not.toHaveBeenCalledWith(`${API}profesores/buscar/`, expect.anything());
    fireEvent.change(byId("profesorBuscador"), { target: { value: "zz" } });
    fireEvent.keyDown(byId("profesorBuscador"), { key: "Enter" });
    expect(await screen.findByText('Sin coincidencias. Usá "Agregar profesor".')).toBeTruthy();
    fireEvent.change(byId("profesorBuscador"), { target: { value: "dora" } });
    fireEvent.keyDown(byId("profesorBuscador"), { key: "Enter" });
    fireEvent.click(await screen.findByText(/Docente, Dora — DNI 20111222/, { selector: "#profesorResultados button" }));
    expect(text("profesorChipTexto")).toBe("Docente, Dora — DNI 20111222 — dora@example.com");
    expect(byId("profesorChip").className).toBe("ci-prof-chip");
    expect((byId("profesorId") as HTMLInputElement).value).toBe("5");
    expect((byId("profesorBuscador") as HTMLInputElement).value).toBe("");
    fireEvent.change(byId("actaFechaFin"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: /Guardar resultados/ }));
    expect(text("resultadosAlert")).toBe("Indicá la fecha de fin para guardar el acta.");
    fireEvent.change(byId("actaFechaFin"), { target: { value: "2026-07-15" } });
    fireEvent.change(byId("actaNumero"), { target: { value: "0245/2026" } });
    redirect(`${CURSO}#resultados`);
    fireEvent.click(screen.getByRole("button", { name: /Guardar resultados/ }));
    await waitFor(() => expect(comisionNav.reload).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe(`${API}resultados/`);
    expect(body()).toEqual({ profesor: "5", fecha_fin: "2026-07-15", numero_acta: "0245/2026", resultado_21: "aprobado", resultado_22: "" });
    fireEvent.click(byId("profesorChipQuitar"));
    expect((byId("profesorId") as HTMLInputElement).value).toBe("");
    expect(byId("profesorChip").className).toBe("ci-prof-chip d-none");
  });

  it("starts with the saved teacher and reloads on Cancelar", async () => {
    await open(`${CURSO}#resultados`, data({ resultados: resultados({ profesor_id: 5, profesor_texto: "Docente, Dora — DNI 20111222 — dora@example.com", numero_acta: "0245/2026" }) }));
    expect(byId("profesorChip").className).toBe("ci-prof-chip");
    expect((byId("actaNumero") as HTMLInputElement).value).toBe("0245/2026");
    fireEvent.click(byId("resultadosCancelar"));
    expect(comisionNav.reload).toHaveBeenCalled();
    expect(window.location.hash).toBe("#resultados");
  });

  it("creates a teacher in the modal and selects it, or shows the server errors", async () => {
    await open(`${CURSO}#resultados`);
    fireEvent.click(screen.getByRole("button", { name: /Agregar profesor/ }));
    const modal = byId("modalProfesorNuevo");
    expect(within(modal).getByText("El alta es directa: no se valida la identidad contra RENAPER.")).toBeTruthy();
    expect(Array.from(modal.querySelectorAll("label")).map((l) => l.textContent)).toEqual(["Apellido *", "Nombre ", "Documento ", "Email "]);
    fireEvent.change(byId("id_apellido"), { target: { value: "Docente" } });
    webPost.mockResolvedValue({ data: { ok: false, message: "No se pudo dar de alta al profesor. Revisá los datos.", errors: { documento: ["Ya existe."] } }, status: 400 });
    fireEvent.click(button(modal, "Guardar profesor"));
    await waitFor(() => expect(text("profesorNuevoAlert")).toBe("Ya existe."));
    webPost.mockResolvedValue({ data: { ok: true, profesor: { id: 9, text: "Docente, Dora — DNI 1 — d@example.com" } }, status: 200 });
    fireEvent.click(button(modal, "Guardar profesor"));
    await waitFor(() => expect(document.getElementById("modalProfesorNuevo")).toBeNull());
    expect(webPost.mock.calls[1][0]).toBe(`${API}profesores/nuevo/`);
    expect(body(1)).toMatchObject({ apellido: "Docente" });
    expect(text("profesorChipTexto")).toBe("Docente, Dora — DNI 1 — d@example.com");
  });

  it("has no tab for the offer variant or without the results permission", async () => {
    await open(`${CURSO}#resultados`, data({ resultados: null, formularios: { rapida: RAPIDA, profesor: null }, permisos: { ...ALL, gestionar_resultados: false } }));
    expect(document.querySelector('[data-sisoc-panel="resultados"]')).toBeNull();
    expect(screen.queryByRole("button", { name: "Resultados" })).toBeNull();
  });
});

describe("comisión detalle: helpers and payload", () => {
  it("builds the native error message: the message, then the joined field errors, then the fallback", () => {
    expect(errorMessage({ message: "Listo" }, "x")).toBe("Listo");
    expect(errorMessage({ errors: { a: ["Uno."], b: ["Dos.", "Tres."] } }, "x")).toBe("Uno. Dos. Tres.");
    expect(errorMessage(null, "x")).toBe("x");
    expect(errorMessage({ errors: {} }, "x")).toBe("x");
  });

  it("validates the form fields of the payload", () => {
    expect(comisionDetalleValid(data())).toBe(true);
    expect(comisionDetalleValid(data({ formularios: { rapida: [{ name: "x" }], profesor: null } }))).toBe(false);
    expect(comisionDetalleValid(data({ formularios: null }))).toBe(false);
    expect(comisionDetalleValid(data({ resultados: { aprobado: "aprobado" } }))).toBe(false);
  });
});
