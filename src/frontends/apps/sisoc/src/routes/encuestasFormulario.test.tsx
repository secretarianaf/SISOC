import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { formularioValid } from "./encuestasFormulario";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const campo = (value: string | boolean, over = {}) => ({ value, errors: [], invalid: false, describedby: "", ...over });
const fila = (over = {}) => ({
  orden: 1, texto: "¿Volverías?", bloque: "", max_caracteres: null, tipo: "si_no", obligatoria: true, opciones: [], pondera: true, puntaje_si: 3, puntaje_no: 1, condicion: null, ...over,
});
const page = (over: Record<string, unknown> = {}, fields: Record<string, unknown> = {}) => ({
  id: null, motivo_rechazo: null, non_field_errors: [],
  fields: {
    titulo: campo(""), descripcion: campo(""), es_anonima: campo(false), modalidad: campo("postergable"), es_recurrente: campo(false),
    intervalo_recordatorio_dias: campo("", { describedby: "id_intervalo_recordatorio_dias_helptext" }), duracion_ronda_dias: campo(""), intervalo_recurrencia_dias: campo(""), ...fields,
  },
  preguntas: [],
  tipos_pregunta: [["texto_corto", "Texto corto"], ["texto_largo", "Texto largo"], ["opcion_unica", "Opción única"], ["opcion_multiple", "Opción múltiple"], ["escala", "Escala"], ["si_no", "Sí/No"], ["numerico", "Numérico"], ["fecha", "Fecha"]],
  operadores_condicion: [["igual", "Igual a"], ["distinto", "Distinto de"]],
  tipos_con_opciones: "opcion_unica,opcion_multiple", tipos_ponderables: "si_no,opcion_unica,opcion_multiple,escala",
  urls: null, messages: [], ...over,
});
const editing = (preguntas: unknown[] = []) => page({ id: 7, urls: { exportar: "/encuestas/7/exportar/" }, preguntas }, {
  titulo: campo("Satisfacción"), duracion_ronda_dias: campo("7"), modalidad: campo("obligatoria"),
});
const serve = (data: unknown, status = 200) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
const assign = vi.fn();
const go = (path: string) => {
  window.history.replaceState({}, "", path);
  vi.stubGlobal("location", { ...window.location, assign, replace, pathname: path, search: "" });
};
const replace = vi.fn();

const rows = () => Array.from(document.querySelectorAll<HTMLElement>(".pregunta-row"));
const numeros = () => rows().map((r) => r.querySelector(".pregunta-numero")?.textContent);
const sent = (call = 0) => {
  const body = webPost.mock.calls[call][1] as URLSearchParams;
  return { body, preguntas: JSON.parse(body.get("preguntas_json") ?? "null") };
};

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  window.history.replaceState({}, "", "/encuestas/crear/");
  setViewport(false);
  vi.stubGlobal("location", { ...window.location, assign, replace, pathname: "/encuestas/crear/", search: "" });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("formulario de alta y edicion de encuestas", () => {
  it("owns the create and edit paths and validates the payload", () => {
    expect(findRoute("/encuestas/crear/")?.route.name).toBe("encuestas-formulario");
    expect(findRoute("/encuestas/7/editar/")?.route.name).toBe("encuestas-formulario");
    expect(formularioValid(page())).toBe(true);
    expect(formularioValid(editing([fila()]))).toBe(true);
    expect(formularioValid(page({ id: "7" }))).toBe(false);
    expect(formularioValid(page({ preguntas: ["x"] }))).toBe(false);
    expect(formularioValid(page({ fields: {} }))).toBe(false);
    expect(formularioValid(page({ urls: { exportar: "https://externo.test/x" } }))).toBe(false);
  });

  it("draws the create form as the native page, without the export menu", async () => {
    serve(page());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Generar encuesta", level: 2 })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/encuestas/crear/", expect.anything());
    await waitFor(() => expect(document.title).toContain("Generar encuesta"));
    expect(screen.queryByRole("button", { name: /Exportar JSON/ })).toBeNull();
    expect((screen.getByLabelText(/Título/) as HTMLInputElement).maxLength).toBe(200);
    expect((screen.getByLabelText("Modalidad de respuesta") as HTMLSelectElement).value).toBe("postergable");
    expect(screen.getByText("Todavía no agregaste preguntas.").classList.contains("d-none")).toBe(false);
    expect(document.getElementById("preguntas-cantidad")?.textContent).toBe("0");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/encuestas/");
    expect((document.getElementById("id_intervalo_recordatorio_dias") as HTMLInputElement).required).toBe(true);
  });

  it("shows the reminder and recurrence fields only when they apply", async () => {
    serve(page());
    render(<App />);
    const modalidad = (await screen.findByLabelText("Modalidad de respuesta")) as HTMLSelectElement;
    const recordatorio = document.getElementById("id_intervalo_recordatorio_dias") as HTMLInputElement;
    const recurrencia = document.getElementById("recurrencia-field") as HTMLElement;
    expect(recurrencia.style.display).toBe("none");
    fireEvent.click(screen.getByLabelText("Recurrente"));
    expect(recurrencia.style.display).toBe("");
    fireEvent.change(modalidad, { target: { value: "obligatoria" } });
    expect((document.getElementById("recordatorio-field") as HTMLElement).style.display).toBe("none");
    expect(recordatorio.disabled).toBe(true);
    fireEvent.change(modalidad, { target: { value: "postergable" } });
    expect(recordatorio.disabled).toBe(false);
  });

  it("opens the export menu on edit with the two native links", async () => {
    go("/encuestas/7/editar/");
    serve(editing());
    render(<App />);
    const toggle = await screen.findByRole("button", { name: /Exportar JSON/ });
    expect(webGet).toHaveBeenCalledWith("web/encuestas/7/editar/", expect.anything());
    expect(screen.getByRole("heading", { name: "Editar encuesta", level: 2 })).toBeTruthy();
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(document.querySelector(".dropdown-menu")?.classList.contains("show")).toBe(true);
    expect(screen.getByText("Solo encuesta").closest("a")?.getAttribute("href")).toBe("/encuestas/7/exportar/");
    expect(screen.getByText("Con segmentación").closest("a")?.getAttribute("href")).toBe("/encuestas/7/exportar/?incluir_segmentacion=1");
    fireEvent.keyDown(toggle, { key: "Escape" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
  });

  it("follows the native redirect of a pending survey", async () => {
    go("/encuestas/7/editar/");
    serve({ redirect: "/encuestas/7/revision/" });
    render(<App />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/encuestas/7/revision/"));
  });

  it("adds questions with the native defaults and per-type controls", async () => {
    serve(page());
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Agregar pregunta/ }));
    expect(numeros()).toEqual(["Pregunta 1"]);
    expect(document.getElementById("preguntas-cantidad")?.textContent).toBe("1");
    const row = rows()[0];
    const tipo = row.querySelector(".pregunta-tipo") as HTMLSelectElement;
    expect(tipo.value).toBe("texto_corto");
    expect(row.querySelector(".pregunta-max-caracteres-wrap")?.classList.contains("d-none")).toBe(false);
    expect(row.querySelector(".pregunta-opciones-wrap")?.classList.contains("d-none")).toBe(true);
    expect(row.querySelector(".pregunta-pondera-wrap")?.classList.contains("d-none")).toBe(true);
    expect(row.querySelector(".pregunta-condicion-wrap")?.classList.contains("d-none")).toBe(true);
    fireEvent.change(tipo, { target: { value: "opcion_unica" } });
    expect(row.querySelector(".pregunta-opciones-wrap")?.classList.contains("d-none")).toBe(false);
    expect(row.querySelector(".pregunta-pondera-wrap")?.classList.contains("d-none")).toBe(false);
    fireEvent.change(row.querySelector(".pregunta-opciones") as HTMLTextAreaElement, { target: { value: "Bueno\n Malo \n\n" } });
    fireEvent.click(row.querySelector(".pregunta-pondera") as HTMLInputElement);
    const puntajes = row.querySelectorAll<HTMLInputElement>(".puntaje-opcion-input");
    expect(Array.from(row.querySelectorAll(".puntaje-opcion-texto")).map((e) => e.textContent)).toEqual(["Bueno", "Malo"]);
    fireEvent.change(puntajes[1], { target: { value: "4" } });
    fireEvent.change(tipo, { target: { value: "escala" } });
    expect(row.querySelector(".pregunta-puntaje-escala-nota")?.classList.contains("d-none")).toBe(false);
    fireEvent.change(tipo, { target: { value: "numerico" } });
    expect((row.querySelector(".pregunta-pondera") as HTMLInputElement).checked).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: /Agregar pregunta/ }));
    expect(rows()[1].querySelector(".pregunta-condicion-wrap")?.classList.contains("d-none")).toBe(false);
    expect(Array.from(rows()[1].querySelectorAll(".pregunta-condicion-referencia option")).map((o) => o.textContent)).toEqual(["(siempre visible)", "Pregunta 1"]);
  });

  it("uses a fixed value list for conditions on Yes/No and option questions", async () => {
    serve(page());
    render(<App />);
    const add = await screen.findByRole("button", { name: /Agregar pregunta/ });
    fireEvent.click(add);
    fireEvent.click(add);
    const [primera, segunda] = rows();
    fireEvent.change(primera.querySelector(".pregunta-texto") as HTMLInputElement, { target: { value: "¿Conforme?" } });
    fireEvent.change(primera.querySelector(".pregunta-tipo") as HTMLSelectElement, { target: { value: "si_no" } });
    const ref = segunda.querySelector(".pregunta-condicion-referencia") as HTMLSelectElement;
    expect(Array.from(ref.options).map((o) => o.textContent)).toEqual(["(siempre visible)", "¿Conforme?"]);
    const select = segunda.querySelector(".pregunta-condicion-valor-select") as HTMLSelectElement;
    const libre = segunda.querySelector(".pregunta-condicion-valor") as HTMLInputElement;
    fireEvent.change(libre, { target: { value: "no" } });
    fireEvent.change(ref, { target: { value: ref.options[1].value } });
    expect(select.classList.contains("d-none")).toBe(false);
    expect(libre.classList.contains("d-none")).toBe(true);
    expect(Array.from(select.options).map((o) => [o.value, o.textContent])).toEqual([["si", "Sí"], ["no", "No"]]);
    expect(select.value).toBe("no");
    fireEvent.change(primera.querySelector(".pregunta-tipo") as HTMLSelectElement, { target: { value: "opcion_unica" } });
    fireEvent.change(primera.querySelector(".pregunta-opciones") as HTMLTextAreaElement, { target: { value: "Bueno\nMalo" } });
    expect(Array.from(select.options).map((o) => o.value)).toEqual(["Bueno", "Malo"]);
    expect(select.value).toBe("Bueno");
    fireEvent.change(primera.querySelector(".pregunta-tipo") as HTMLSelectElement, { target: { value: "texto_corto" } });
    expect(select.classList.contains("d-none")).toBe(true);
    expect(libre.classList.contains("d-none")).toBe(false);
  });

  it("reorders with the arrow keys, announces it and refuses to break a dependency", async () => {
    go("/encuestas/7/editar/");
    serve(editing([
      fila({ texto: "Uno" }),
      fila({ orden: 2, texto: "Dos", tipo: "texto_corto", pondera: false, condicion: { orden: 1, operador: "igual", valor: "no" } }),
      fila({ orden: 3, texto: "Tres", tipo: "texto_corto", pondera: false }),
    ]));
    render(<App />);
    await screen.findByRole("heading", { name: "Editar encuesta", level: 2 });
    const textos = () => rows().map((r) => (r.querySelector(".pregunta-texto") as HTMLInputElement).value);
    expect(textos()).toEqual(["Uno", "Dos", "Tres"]);
    fireEvent.keyDown(rows()[1].querySelector(".pregunta-arrastrar") as HTMLElement, { key: "ArrowUp" });
    expect(textos()).toEqual(["Uno", "Dos", "Tres"]);
    expect(screen.getByText("No se puede mover: una pregunta condicional debe quedar después de la pregunta de la que depende.")).toBeTruthy();
    fireEvent.keyDown(rows()[2].querySelector(".pregunta-arrastrar") as HTMLElement, { key: "ArrowUp" });
    expect(textos()).toEqual(["Uno", "Tres", "Dos"]);
    expect(screen.getByText("Pregunta movida a la posición 2. Guardá la encuesta para conservar el orden.")).toBeTruthy();
    expect((rows()[2].querySelector(".pregunta-condicion-referencia") as HTMLSelectElement).selectedOptions[0].textContent).toBe("Uno");
    fireEvent.keyDown(rows()[0].querySelector(".pregunta-arrastrar") as HTMLElement, { key: "ArrowUp" });
    expect(textos()).toEqual(["Uno", "Tres", "Dos"]);
  });

  it("reorders by dragging a card onto another and marks the target while dragging", async () => {
    go("/encuestas/7/editar/");
    serve(editing([fila({ texto: "Uno" }), fila({ orden: 2, texto: "Dos" }), fila({ orden: 3, texto: "Tres" })]));
    render(<App />);
    await screen.findByRole("heading", { name: "Editar encuesta", level: 2 });
    const dataTransfer = { setData: vi.fn(), setDragImage: vi.fn(), effectAllowed: "", dropEffect: "" };
    const textos = () => rows().map((r) => (r.querySelector(".pregunta-texto") as HTMLInputElement).value);
    fireEvent.dragStart(rows()[0].querySelector(".pregunta-arrastrar") as HTMLElement, { dataTransfer });
    expect(dataTransfer.setData).toHaveBeenCalledWith("text/plain", "Pregunta 1");
    fireEvent.dragOver(rows()[2], { dataTransfer });
    expect(rows()[2].classList.contains("pregunta-destino-despues")).toBe(true);
    fireEvent.drop(rows()[2], { dataTransfer });
    expect(textos()).toEqual(["Dos", "Tres", "Uno"]);
    expect(rows().some((r) => r.className.includes("pregunta-destino"))).toBe(false);
    fireEvent.dragEnd(rows()[2].querySelector(".pregunta-arrastrar") as HTMLElement);
    expect(rows().some((r) => r.classList.contains("pregunta-arrastrando"))).toBe(false);
  });

  it("confirms before removing a question and warns about dependents", async () => {
    go("/encuestas/7/editar/");
    serve(editing([
      fila({ texto: "Uno" }),
      fila({ orden: 2, texto: "Dos", tipo: "texto_corto", pondera: false, condicion: { orden: 1, operador: "igual", valor: "si" } }),
    ]));
    render(<App />);
    await screen.findByRole("heading", { name: "Editar encuesta", level: 2 });
    fireEvent.click(within(rows()[0]).getByRole("button", { name: /Quitar/ }));
    const modal = document.getElementById("quitar-pregunta-modal") as HTMLElement;
    expect(within(modal).getByText("¿Quitar la pregunta 1? Se eliminarán su texto, opciones y configuración. El cambio se aplicará al guardar la encuesta. Las preguntas que dependen de esta quedarán siempre visibles.")).toBeTruthy();
    await waitFor(() => expect(document.activeElement).toBe(document.getElementById("cancelar-quitar-pregunta")));
    fireEvent.click(within(modal).getByRole("button", { name: "Cancelar" }));
    expect(document.getElementById("quitar-pregunta-modal")).toBeNull();
    expect(rows().length).toBe(2);
    await waitFor(() => expect(document.activeElement).toBe(within(rows()[0]).getByRole("button", { name: /Quitar/ })));
    fireEvent.click(within(rows()[0]).getByRole("button", { name: /Quitar/ }));
    fireEvent.click(screen.getByRole("button", { name: "Quitar pregunta" }));
    expect(rows().length).toBe(1);
    expect(numeros()).toEqual(["Pregunta 1"]);
    expect((rows()[0].querySelector(".pregunta-condicion-referencia") as HTMLSelectElement).value).toBe("");
    await waitFor(() => expect(document.activeElement).toBe(rows()[0].querySelector(".pregunta-arrastrar")));
  });

  it("posts the form fields and the serialised questions, then follows the native redirect", async () => {
    serve(page());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/encuestas/", messages: [] } });
    render(<App />);
    fireEvent.change(await screen.findByLabelText(/Título/), { target: { value: "  Satisfacción " } });
    fireEvent.change(screen.getByLabelText("Duración de la ronda (días)"), { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Intervalo de recordatorio (días)"), { target: { value: "3" } });
    fireEvent.click(screen.getByLabelText("Anónima"));
    const add = screen.getByRole("button", { name: /Agregar pregunta/ });
    fireEvent.click(add);
    fireEvent.click(add);
    const [primera, segunda] = rows();
    fireEvent.change(primera.querySelector(".pregunta-texto") as HTMLInputElement, { target: { value: " ¿Volverías? " } });
    fireEvent.change(primera.querySelector(".pregunta-tipo") as HTMLSelectElement, { target: { value: "si_no" } });
    fireEvent.click(primera.querySelector(".pregunta-pondera") as HTMLInputElement);
    fireEvent.change(primera.querySelector(".pregunta-puntaje-si") as HTMLInputElement, { target: { value: "3" } });
    fireEvent.change(segunda.querySelector(".pregunta-texto") as HTMLInputElement, { target: { value: "¿Por qué?" } });
    fireEvent.click(segunda.querySelector(".pregunta-obligatoria") as HTMLInputElement);
    fireEvent.change(segunda.querySelector(".pregunta-bloque") as HTMLInputElement, { target: { value: " Cierre " } });
    fireEvent.change(segunda.querySelector(".pregunta-max-caracteres") as HTMLInputElement, { target: { value: "200" } });
    const ref = segunda.querySelector(".pregunta-condicion-referencia") as HTMLSelectElement;
    fireEvent.change(ref, { target: { value: ref.options[1].value } });
    fireEvent.change(segunda.querySelector(".pregunta-condicion-valor-select") as HTMLSelectElement, { target: { value: "no" } });
    fireEvent.click(screen.getByRole("button", { name: /Guardar encuesta/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    expect(webPost.mock.calls[0][0]).toBe("web/encuestas/crear/");
    const { body, preguntas } = sent();
    expect(Object.fromEntries(body.entries())).toEqual({
      titulo: "  Satisfacción ", descripcion: "", es_anonima: "on", modalidad: "postergable", intervalo_recordatorio_dias: "3", duracion_ronda_dias: "7",
      intervalo_recurrencia_dias: "", preguntas_json: JSON.stringify(preguntas),
    });
    expect(preguntas).toEqual([
      { orden: 1, texto: "¿Volverías?", bloque: "", max_caracteres: null, tipo: "si_no", obligatoria: true, opciones: [], pondera: true, puntaje_si: 3, puntaje_no: 0, condicion: null },
      { orden: 2, texto: "¿Por qué?", bloque: "Cierre", max_caracteres: 200, tipo: "texto_corto", obligatoria: false, opciones: [], pondera: false, puntaje_si: 0, puntaje_no: 0,
        condicion: { orden: 1, operador: "igual", valor: "no" } },
    ]);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/encuestas/"));
  });

  it("leaves the disabled reminder interval out of the post, as the browser does", async () => {
    go("/encuestas/7/editar/");
    serve(editing());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/encuestas/", messages: [] } });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Guardar encuesta/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    expect(webPost.mock.calls[0][0]).toBe("web/encuestas/7/editar/");
    expect(sent().body.has("intervalo_recordatorio_dias")).toBe(false);
    expect(sent().body.get("modalidad")).toBe("obligatoria");
  });

  it("redraws the native 400: errors, kept values and questions, and back to the top", async () => {
    serve(page());
    webPost.mockResolvedValue({
      status: 400,
      data: page({ non_field_errors: ["Pregunta 1: las preguntas de opción requieren al menos dos opciones."], preguntas: [fila({ texto: "Devuelta" })] },
        { titulo: campo("", { errors: ["Este campo es requerido."], invalid: true, describedby: "id_titulo_error" }), duracion_ronda_dias: campo("7") }),
    });
    const scroll = vi.fn();
    vi.stubGlobal("scrollTo", scroll);
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Guardar encuesta/ }));
    expect(await screen.findByText("Este campo es requerido.")).toBeTruthy();
    expect(screen.getByText("Pregunta 1: las preguntas de opción requieren al menos dos opciones.").closest("ul")?.className).toBe("errorlist nonfield");
    const titulo = screen.getByLabelText(/Título/);
    expect(titulo.getAttribute("aria-invalid")).toBe("true");
    expect(titulo.getAttribute("aria-describedby")).toBe("id_titulo_error");
    expect((screen.getByLabelText("Duración de la ronda (días)") as HTMLInputElement).value).toBe("7");
    expect((rows()[0].querySelector(".pregunta-texto") as HTMLInputElement).value).toBe("Devuelta");
    expect(scroll).toHaveBeenCalledWith(0, 0);
    expect(assign).not.toHaveBeenCalled();
  });

  it("shows the queued messages and the rejection reason of a returned draft", async () => {
    go("/encuestas/7/editar/");
    serve({ ...editing(), messages: [{ message: "Aviso previo", level: "warning" }], motivo_rechazo: { texto: "Falta\ncontexto", usuario: "Alicia", fecha: "01/10/2026 09:30", estado: "borrador" } });
    render(<App />);
    expect(await screen.findByText("Cambios solicitados")).toBeTruthy();
    expect(screen.getByText("Alicia · 01/10/2026 09:30")).toBeTruthy();
    expect(screen.getByText("Corregí la encuesta, guardá los cambios y volvé a solicitar la publicación desde el listado.")).toBeTruthy();
    expect(await screen.findByText("Aviso previo")).toBeTruthy();
  });

  it("reports an uncertain outcome without retrying", async () => {
    serve(page());
    webPost.mockRejectedValue(new Error("network"));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Guardar encuesta/ }));
    expect(await screen.findByText("No se pudo completar la operación.")).toBeTruthy();
    expect(webPost).toHaveBeenCalledTimes(1);
  });
});
