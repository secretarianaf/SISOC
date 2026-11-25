import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { comunicadosFormNavigation, formValid } from "./comunicadosForm";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/comunicados/";
const field = (value: string | boolean | string[], over: Record<string, unknown> = {}) => ({ value, required: false, hidden: false, errors: [], ...over });
const config = {
  comedores: {
    defaultField: "nombre",
    fields: [{ name: "nombre", label: "Nombre", type: "text" }, { name: "estado", label: "Estado", type: "choice", choices: [{ value: "a", label: "Activo" }] }],
    operators: { text: ["contains", "eq", "empty"], choice: ["eq", "ne"] },
  },
  organizaciones: { fields: [{ name: "nombre", label: "Nombre", type: "text" }], operators: { text: ["contains"] } },
};
const form = (over: Record<string, unknown> = {}, fields: Record<string, unknown> = {}) => ({
  title: "Crear Comunicado", is_edit: false, es_tecnico: false,
  fields: {
    tipo: field("interno", { required: true, choices: [{ value: "interno", label: "Comunicación Interna" }, { value: "externo", label: "Comunicación Externa" }] }),
    subtipo: field("", { choices: [{ value: "", label: "---------" }, { value: "institucional", label: "Institucional" }, { value: "comedores", label: "Comunicación a Comedores" }, { value: "organizaciones", label: "Comunicación a Organizaciones" }] }),
    fecha_vencimiento: field(""), destacado: field(false), para_todos_comedores: field(false), comedores: field([]), organizaciones: field([]),
    titulo: field("", { required: true, max_length: 255 }), cuerpo: field("", { required: true }), ...fields,
  },
  formset: { prefix: "adjuntos", has_forms: true, management: { TOTAL_FORMS: "1", INITIAL_FORMS: "0", MIN_NUM_FORMS: "0", MAX_NUM_FORMS: "1000" }, existing: [] },
  info: null, filters_config: config, seleccionados: { comedores: [{ id: 3, nombre: "Comedor tres" }], organizaciones: [] },
  max_adjunto_bytes: 10485760, extensiones: [".jpg", ".jpeg", ".pdf", ".png"], messages: [], ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
function setup(path = "/comunicados/crear/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const q = (sel: string) => document.querySelector(sel) as HTMLElement;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Comunicados create and edit form", () => {
  it("is owned by the comunicados module and validates its payload", () => {
    expect(findRoute("/comunicados/crear/")?.route.name).toBe("comedores-comunicados");
    expect(findRoute("/comunicados/editar/9/")?.route.name).toBe("comedores-comunicados");
    expect(findRoute("/comunicados/editar/x/")?.route.name).not.toBe("comedores-comunicados");
    expect(formValid(form())).toBe(true);
    expect(formValid({ ...form(), formset: {} })).toBe(false);
  });

  it("renders the native panels, helps and controls with the conditional visibility of comunicadosForm.js", async () => {
    serve(form());
    setup();
    await screen.findByText("Configuración");
    expect(webGet).toHaveBeenCalledWith(`${API}crear/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Crear Comunicado"));
    for (const t of ["Tipo de Comunicado", "Subtipo", "Vencimiento", "Marcar como Destacado", "Título", "Contenido", "Agregar archivos", "Cancelar", "Guardar Comunicado"]) {
      expect(screen.getAllByText(new RegExp(t)).length).toBeGreaterThan(0);
    }
    for (const t of ["Interna: SISOC · Externa: App móvil (PWA)", "Institucional: broadcast · Comedores: dirigido", "Opcional. Deja de mostrarse en esa fecha.",
      "Aparece fijado arriba de la lista.", "Se enviará a todos los comedores que tiene asignados.", "Puedes agregar múltiples archivos haciendo clic varias veces."]) {
      expect(screen.getByText(t)).toBeTruthy();
    }
    expect(q("#subtipo-options").className).toBe("option-item d-none");
    expect(q("#destacado-option").className).toBe("mt-3");
    expect(q("#comedores-options").className).toBe("editor-panel d-none");
    expect(q("#organizaciones-options").className).toBe("editor-panel d-none");
    expect((q("#id_titulo") as HTMLInputElement).maxLength).toBe(255);
    expect((q("#id_tipo") as HTMLSelectElement).required).toBe(true);
    expect(screen.queryByText("Información")).toBeNull();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/comunicados/gestion/");
    expect((q('input[name="adjuntos-TOTAL_FORMS"]') as HTMLInputElement).value).toBe("1");

    fireEvent.change(q("#id_tipo"), { target: { value: "externo" } });
    expect(q("#subtipo-options").className).toBe("option-item");
    expect(q("#destacado-option").className).toBe("mt-3 d-none");
    fireEvent.change(q("#id_subtipo"), { target: { value: "comedores" } });
    expect(q("#comedores-options").className).toBe("editor-panel");
    expect(q("#organizaciones-options").className).toBe("editor-panel d-none");
    fireEvent.click(q("#id_para_todos_comedores"));
    expect(q("#comedores-selector").className).toBe("d-none");
    fireEvent.change(q("#id_tipo"), { target: { value: "interno" } });
    expect((q("#id_subtipo") as HTMLSelectElement).value).toBe("");
    expect(q("#comedores-options").className).toBe("editor-panel d-none");
  });

  it("posts the native field names as multipart once and follows the confirmed redirect", async () => {
    serve(form());
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/comunicados/gestion/" }, status: 200 });
    const assign = vi.spyOn(comunicadosFormNavigation, "assign").mockImplementation(() => {});
    setup();
    await screen.findByText("Configuración");
    fireEvent.change(q("#id_tipo"), { target: { value: "externo" } });
    fireEvent.change(q("#id_subtipo"), { target: { value: "comedores" } });
    fireEvent.change(q("#id_titulo"), { target: { value: "Aviso" } });
    fireEvent.change(q("#id_cuerpo"), { target: { value: "Texto" } });
    const file = new File(["%PDF"], "guia.pdf", { type: "application/pdf" });
    fireEvent.change(q("#archivosInput"), { target: { files: [file] } });
    expect(q("#fileCount").textContent).toBe("1");
    expect(within(q("#filePreviewContainer")).getByText("guia.pdf")).toBeTruthy();
    const submit = screen.getByRole("button", { name: "Guardar Comunicado" });
    fireEvent.click(submit);
    fireEvent.click(submit);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comunicados/gestion/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0] as [string, FormData];
    expect(url).toBe(`${API}crear/`);
    expect([body.get("tipo"), body.get("subtipo"), body.get("titulo"), body.get("cuerpo"), body.get("comedores")]).toEqual(["externo", "comedores", "Aviso", "Texto", "3"]);
    expect([body.get("adjuntos-TOTAL_FORMS"), body.get("csrfmiddlewaretoken")]).toEqual(["1", "synthetic-csrf-token"]);
    expect((body.getAll("archivos_adjuntos") as File[]).map((f) => f.name)).toEqual(["guia.pdf"]);
    expect(body.has("destacado")).toBe(false);
  });

  it("shows the field errors of a 400 keeping the entered values, and an unconfirmed result is not resent", async () => {
    serve(form());
    const rejected = form({}, {
      titulo: field("Aviso", { required: true, max_length: 255, errors: ["Este campo es obligatorio."] }),
      cuerpo: field("", { required: true, errors: ["Este campo es obligatorio."] }),
    });
    webPost.mockResolvedValueOnce({ data: rejected, status: 400 });
    setup();
    await screen.findByText("Configuración");
    fireEvent.change(q("#id_titulo"), { target: { value: "Aviso" } });
    fireEvent.submit(q(".comunicado-editor form"));
    await waitFor(() => expect(document.querySelectorAll(".invalid-feedback.d-block")).toHaveLength(2));
    expect(document.querySelectorAll(".invalid-feedback.d-block")[0].textContent).toBe("Este campo es obligatorio.");
    expect((q("#id_titulo") as HTMLInputElement).value).toBe("Aviso");
    webPost.mockRejectedValueOnce(new Error("timeout"));
    fireEvent.submit(q(".comunicado-editor form"));
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo confirmar el resultado. Revise la gestión de comunicados antes de volver a guardar.");
    fireEvent.submit(q(".comunicado-editor form"));
    expect(webPost).toHaveBeenCalledTimes(2);
  });

  it("renders the edit form with the current attachments, the delete checkbox and the information panel", async () => {
    serve(form({
      title: "Editar Comunicado", is_edit: true,
      formset: {
        prefix: "adjuntos", has_forms: true, management: { TOTAL_FORMS: "2", INITIAL_FORMS: "1", MIN_NUM_FORMS: "0", MAX_NUM_FORMS: "1000" },
        existing: [{ nombre_original: "a.pdf", url: "/media/a.pdf", hidden: [{ name: "adjuntos-0-id", value: "5" }, { name: "adjuntos-0-comunicado", value: "9" }],
          delete: { name: "adjuntos-0-DELETE", id: "id_adjuntos-0-DELETE", checked: false } }],
      },
      info: { estado: "borrador", estado_label: "Borrador", fecha_creacion: "03/03/2026 09:00", creador: "Ana Pérez" },
    }, { titulo: field("Hola", { required: true }) }));
    setup("/comunicados/editar/9/");
    await screen.findByText("Archivos actuales");
    expect(webGet).toHaveBeenCalledWith(`${API}9/editar/`, expect.anything());
    expect((q("#id_titulo") as HTMLInputElement).value).toBe("Hola");
    expect(screen.getByRole("link", { name: "a.pdf" }).getAttribute("href")).toBe("/media/a.pdf");
    expect((q('input[name="adjuntos-0-id"]') as HTMLInputElement).value).toBe("5");
    expect((q("#id_adjuntos-0-DELETE") as HTMLInputElement).type).toBe("checkbox");
    expect(screen.getByText("Información")).toBeTruthy();
    expect(screen.getByText("Borrador").getAttribute("style")).toContain("rgba(156, 163, 175, 0.15)");
    expect(screen.getByText(/03\/03\/2026 09:00/)).toBeTruthy();
  });
});

describe("Comunicados recipients panel", () => {
  async function openComedores() {
    serve(form());
    setup();
    await screen.findByText("Configuración");
    fireEvent.change(q("#id_tipo"), { target: { value: "externo" } });
    fireEvent.change(q("#id_subtipo"), { target: { value: "comedores" } });
    return within(q("#comedores-options"));
  }
  const filters = () => JSON.parse(webGet.mock.calls.at(-1)?.[1].params.filters);

  it("starts with the previous selection and the hint, and the hidden CSV input follows it", async () => {
    const panel = await openComedores();
    expect(panel.getByText("Usá los filtros y presioná Buscar.")).toBeTruthy();
    expect(panel.getByText("Comedor tres")).toBeTruthy();
    expect(q("#comedores-options .destinatarios-seleccion label").textContent).toBe("Seleccionados (1) Quitar todos");
    expect((q('#comedores-options input[name="comedores"]') as HTMLInputElement).value).toBe("3");
    fireEvent.click(panel.getByText("Quitar todos"));
    expect(panel.getByText("No hay destinatarios seleccionados.")).toBeTruthy();
    expect((q('#comedores-options input[name="comedores"]') as HTMLInputElement).value).toBe("");
    expect((panel.getByLabelText("Quitar filtro").closest("button") as HTMLButtonElement).hidden).toBe(true);
  });

  it("searches with the combined filters, paginates the last search and adds or removes results", async () => {
    const panel = await openComedores();
    webGet.mockImplementation((_url: string, config: { params: { page?: number } }) => Promise.resolve({
      data: { results: [{ id: 8, nombre: "Comedor ocho", detalle: "Zona 1" }], total: 26, has_more: config.params.page === 1, page: config.params.page ?? 1, max_seleccion_masiva: 2000 }, status: 200,
    }));
    fireEvent.change(panel.getAllByLabelText("Valor a buscar")[0], { target: { value: " ocho " } });
    fireEvent.click(panel.getByRole("button", { name: "Buscar" }));
    expect(await panel.findByText("26 resultado(s) encontrado(s).")).toBeTruthy();
    expect(webGet.mock.calls.at(-1)?.[0]).toBe(`${API}destinatarios/comedores/buscar/`);
    expect(filters()).toEqual({ logic: "AND", items: [{ field: "nombre", op: "contains", value: "ocho" }] });
    expect(panel.getByText("Zona 1")).toBeTruthy();
    expect(panel.getByText("Página 1")).toBeTruthy();
    fireEvent.change(panel.getByLabelText("Filtrar por"), { target: { value: "estado" } });
    fireEvent.click(panel.getByRole("button", { name: "Siguiente" }));
    await panel.findByText("Página 2");
    expect(filters().items).toHaveLength(1);
    expect(webGet.mock.calls.at(-1)?.[1].params.page).toBe(2);
    fireEvent.click(panel.getByRole("button", { name: /Agregar$/ }));
    expect((q('#comedores-options input[name="comedores"]') as HTMLInputElement).value).toBe("3,8");
    fireEvent.click(panel.getByRole("button", { name: /Quitar$/ }));
    expect((q('#comedores-options input[name="comedores"]') as HTMLInputElement).value).toBe("3");
  });

  it("adds every result up to the cap, explains the cap and reports a failed search", async () => {
    const panel = await openComedores();
    webGet.mockResolvedValueOnce({ data: { results: [], total: 3, has_more: false, page: 1, max_seleccion_masiva: 2000 }, status: 200 });
    fireEvent.click(panel.getByRole("button", { name: "Buscar" }));
    await panel.findByText("3 resultado(s) encontrado(s).");
    webGet.mockResolvedValueOnce({ data: { results: [], total: 5000, truncado: true, max_seleccion_masiva: 2000 }, status: 200 });
    fireEvent.click(panel.getByRole("button", { name: "Agregar todos los resultados" }));
    await panel.findByText("Son 5000 resultados y el máximo para agregar de una vez es 2000. Afiná los filtros.");
    webGet.mockResolvedValueOnce({ data: { results: [{ id: 4, nombre: "Cuatro" }, { id: 6, nombre: "Seis" }], total: 2, truncado: false, max_seleccion_masiva: 2000 }, status: 200 });
    fireEvent.click(panel.getByRole("button", { name: "Agregar todos los resultados" }));
    await waitFor(() => expect((q('#comedores-options input[name="comedores"]') as HTMLInputElement).value).toBe("3,4,6"));
    webGet.mockRejectedValueOnce(new Error("HTTP 500"));
    fireEvent.click(panel.getByRole("button", { name: "Buscar" }));
    await panel.findByText("No se pudo completar la búsqueda. Intentá nuevamente.");
    fireEvent.click(panel.getByRole("button", { name: /Limpiar/ }));
    expect(panel.getByText("Usá los filtros y presioná Buscar.")).toBeTruthy();
  });
});
