import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { navigation } from "./userImport";
import { setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
  mensajeDeError: vi.fn(() => "Error de prueba"),
  SinPermiso: class SinPermiso extends Error {},
}));

const presentation = { user: { username: "synthetic", display_name: "Ana", avatar_initial: "A", role_label: "-" }, footer_version_label: "Versiones", legacy_frame_navigation: [] };
const fields = [
  { name: "archivo", label: "Archivo Excel", required: true, help_text: "Archivo .xlsx con columnas.", accept: ".xlsx" },
  { name: "enviar_credenciales", label: "Enviar credenciales por email", required: false, help_text: "Si esta marcado." },
  { name: "es_pwa", label: "Usuarios de la PWA", required: false, help_text: "Usuarios de la app movil (PWA)." },
];
const formData = (extra = {}) => ({ fields, initial: { enviar_credenciales: true, es_pwa: false }, errors: {}, template_download_url: "/usuarios/importar/plantilla/", recent_jobs: [{ id: 4, requested_at: "06/11/2026 10:00", status: "completed_with_errors", created_rows: 2, skipped_rows: 1, failed_rows: 1, detail_url: "/usuarios/importar/lotes/4/" }], messages: [], presentation, ...extra });
const job = { id: 9, original_filename: "usuarios.xlsx", requested_at: "06/11/2026 10:00", status: "failed", send_credentials: true, resume_count: 1, total_rows: 60, processed_rows: 3, created_rows: 1, skipped_rows: 1, failed_rows: 1, last_error_message: "Fila 4: rol inexistente.", last_error_at: "06/11/2026 10:05" };
const rows = [{ id: 1, fila: 2, nombre: "Ana", apellido: "Prueba", email: "", status: "created", attempts: 1, mensaje: "" }, { id: 2, fila: 3, nombre: "Luis", apellido: "Prueba", email: "l@example.invalid", status: "failed", attempts: 2, mensaje: "Rol inexistente." }];
const detail = (extra = {}) => ({ job, rows, page: { number: 2, num_pages: 3, previous: 1, next: 3 }, status_filter: "failed", is_resume_available: true, csv_url: "/usuarios/importar/lotes/9/descargar-csv/", upload_url: "/usuarios/importar/", messages: [{ message: "El lote quedo pendiente para reanudarse desde la ultima fila fallida.", level: "success" }], presentation, ...extra });

let assign: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  assign.mockRestore();
  webGet.mockReset();
  webPost.mockReset();
});

async function openForm(data = formData()) {
  window.history.replaceState(null, "", "/usuarios/importar/");
  webGet.mockResolvedValue({ status: 200, data });
  render(<App />);
  return screen.findByRole("button", { name: "Crear lote" });
}

describe("user import form", () => {
  it("reads only its own transport and renders the native fields, initials and own history", async () => {
    await openForm();
    expect(webGet).toHaveBeenCalledTimes(1);
    expect(webGet).toHaveBeenCalledWith("web/users/import/", expect.any(Object));
    expect(document.title).toBe("SISOC - Gestor masivo de usuarios");
    expect(document.querySelector(".breadcrumb .breadcrumb-item.active")?.textContent).toBe("Gestor masivo");
    const file = document.getElementById("id_archivo") as HTMLInputElement;
    expect(file.type).toBe("file");
    expect(file.accept).toBe(".xlsx");
    expect((document.getElementById("id_enviar_credenciales") as HTMLInputElement).checked).toBe(true);
    expect((document.getElementById("id_es_pwa") as HTMLInputElement).checked).toBe(false);
    expect(screen.getByRole("link", { name: "Descargar plantilla" }).getAttribute("href")).toBe("/usuarios/importar/plantilla/");
    expect(screen.getByText("Completado con errores").className).toBe("badge badge-warning");
    expect(screen.getByRole("link", { name: "Ver detalle" }).getAttribute("href")).toBe("/usuarios/importar/lotes/4/");
    expect(screen.getByText("#4").childNodes).toHaveLength(1);
    expect(document.querySelector('link[rel="stylesheet"][href="/static/custom/css/hitos.css"]')).not.toBeNull();
  });

  it("shows the native empty-history notice", async () => {
    await openForm(formData({ recent_jobs: [] }));
    expect(screen.getByText("Todavia no hay lotes de importacion creados.")).toBeTruthy();
    expect(screen.queryByText("Ultimos lotes")).toBeNull();
  });

  it("enqueues once with the file and checked options, then opens the job detail", async () => {
    const submit = await openForm();
    const archivo = new File(["xlsx"], "usuarios.xlsx");
    fireEvent.change(document.getElementById("id_archivo")!, { target: { files: [archivo] } });
    fireEvent.click(document.getElementById("id_es_pwa")!);
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/usuarios/importar/lotes/31/" } });
    fireEvent.click(submit);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/usuarios/importar/lotes/31/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [endpoint, body] = webPost.mock.calls[0];
    expect(endpoint).toBe("web/users/import/");
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get("archivo")).toBe(archivo);
    expect((body as FormData).get("enviar_credenciales")).toBe("on");
    expect((body as FormData).get("es_pwa")).toBe("on");
  });

  it("re-renders the bound form on a 400 without navigating", async () => {
    const submit = await openForm();
    fireEvent.click(document.getElementById("id_enviar_credenciales")!);
    webPost.mockRejectedValue({ response: { status: 400, data: formData({ initial: { enviar_credenciales: false, es_pwa: false }, errors: { archivo: [{ message: "Este campo es requerido.", code: "required" }] } }) } });
    submit.focus();
    fireEvent.click(submit);
    expect(await screen.findByText("Este campo es requerido.")).toBeTruthy();
    const file = document.getElementById("id_archivo")!;
    expect(file.className).toBe("form-control is-invalid");
    expect(file.getAttribute("aria-describedby")).toBe("id_archivo_helptext id_archivo_error");
    expect((document.getElementById("id_enviar_credenciales") as HTMLInputElement).checked).toBe(false);
    expect(assign).not.toHaveBeenCalled();
    expect((submit as HTMLButtonElement).disabled).toBe(false);
    // Like the native page reload, keyboard navigation restarts at the top of the document.
    expect(document.activeElement).toBe(document.body);
    expect(document.body.hasAttribute("tabindex")).toBe(false);
  });

  it("reports an unconfirmed upload and never resubmits it", async () => {
    const submit = await openForm();
    webPost.mockRejectedValue(new Error("network"));
    fireEvent.click(submit);
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.click(submit);
    expect(webPost).toHaveBeenCalledTimes(1);
    expect((submit as HTMLButtonElement).disabled).toBe(true);
    expect(assign).not.toHaveBeenCalled();
  });

  it("shows the prerequisite instead of the form on a 403", async () => {
    window.history.replaceState(null, "", "/usuarios/importar/");
    webGet.mockResolvedValue({ status: 403, data: { detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" } });
    render(<App />);
    expect(await screen.findByText("Necesitás actualizar tu contraseña para continuar.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Crear lote" })).toBeNull();
  });
});

describe("user import job detail", () => {
  async function openDetail(data = detail(), search = "?estado=failed&page=2") {
    window.history.replaceState(null, "", `/usuarios/importar/lotes/9/${search}`);
    webGet.mockResolvedValue({ status: 200, data });
    render(<App />);
    await screen.findByText("Lote #9", { selector: "h3" });
  }

  it("reads the status once with the page query and never polls", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await openDetail();
    await vi.advanceTimersByTimeAsync(10 * 60 * 1000);
    vi.useRealTimers();
    expect(webGet).toHaveBeenCalledTimes(1);
    expect(webGet).toHaveBeenCalledWith("web/users/import/jobs/9/?estado=failed&page=2", expect.any(Object));
    expect(webPost).not.toHaveBeenCalled();
    expect(document.title).toBe("SISOC - Detalle de lote de importacion");
  });

  it("renders native counters, rows, filters, pagination and actions", async () => {
    await openDetail();
    expect(screen.getByText("usuarios.xlsx | 06/11/2026 10:00")).toBeTruthy();
    expect(screen.getByText("Fila 4: rol inexistente.")).toBeTruthy();
    expect(screen.getByText("Registrado el 06/11/2026 10:05").childNodes).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Actualizar estado" }).getAttribute("href")).toBe("/usuarios/importar/lotes/9/");
    expect(screen.getByRole("link", { name: "Descargar CSV" }).getAttribute("href")).toBe("/usuarios/importar/lotes/9/descargar-csv/");
    expect(screen.getByRole("link", { name: "Fallidos" }).className).toBe("btn btn-sm btn-danger");
    expect(screen.getByRole("link", { name: "Todos" }).className).toBe("btn btn-sm btn-outline-secondary");
    expect(screen.getByRole("link", { name: "Anterior" }).getAttribute("href")).toBe("?estado=failed&page=1");
    expect(screen.getByRole("link", { name: "Siguiente" }).getAttribute("href")).toBe("?estado=failed&page=3");
    expect(screen.getByText("Pagina 2 de 3")).toBeTruthy();
    expect(screen.getByText("Pagina 2 de 3").childNodes).toHaveLength(1);
    expect(screen.getAllByRole("row")[1].textContent).toBe("2Ana Prueba- Creado 1-");
    expect(screen.getByText("El lote quedo pendiente para reanudarse desde la ultima fila fallida.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Gestor masivo" }).getAttribute("href")).toBe("/usuarios/importar/");
  });

  it("keeps the native text runs and the native page stylesheet", async () => {
    await openDetail(detail({ job: { ...job, status: "pending", last_error_message: "", last_error_at: "" } }));
    expect(document.querySelector('link[rel="stylesheet"][href="/static/custom/css/hitos.css"]')).not.toBeNull();
    const heading = screen.getByRole("heading", { level: 3, name: "Lote #9" });
    expect(heading.childNodes).toHaveLength(1);
    expect(screen.getByText("usuarios.xlsx | 06/11/2026 10:00").childNodes).toHaveLength(1);
    expect(screen.getByText("Si", { exact: false, selector: "strong" }).textContent).toBe("Si ");
    const notice = document.querySelector(".alert-info") as HTMLElement;
    expect(notice.firstChild?.textContent).toBe("El lote esta en curso fuera de la request web. Use ");
    expect(screen.getAllByRole("row")[1].querySelector("td:nth-child(2)")?.childNodes).toHaveLength(1);
  });

  it("hides resume, CSV and pagination when the source does", async () => {
    await openDetail(detail({ is_resume_available: false, csv_url: null, page: { number: 1, num_pages: 1, previous: null, next: null }, job: { ...job, status: "processing", last_error_message: "", last_error_at: "" } }), "");
    expect(screen.queryByRole("button", { name: "Reanudar" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Descargar CSV" })).toBeNull();
    expect(screen.queryByRole("navigation", { name: "Paginacion de filas" })).toBeNull();
    expect(screen.getByText(/El lote esta en curso fuera de la request web/)).toBeTruthy();
  });

  it("resumes with one POST and reloads the detail", async () => {
    await openDetail();
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/usuarios/importar/lotes/9/" } });
    fireEvent.click(screen.getByRole("button", { name: "Reanudar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/usuarios/importar/lotes/9/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/users/import/jobs/9/resume/");
    expect(String(webPost.mock.calls[0][1])).toBe("");
  });

  it("does not retry an unconfirmed resume nor follow a foreign redirect", async () => {
    await openDetail();
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "https://example.invalid/" } });
    const button = screen.getByRole("button", { name: "Reanudar" });
    fireEvent.click(button);
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    fireEvent.click(button);
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(assign).not.toHaveBeenCalled();
    expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
  });
});
