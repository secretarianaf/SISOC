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
  { name: "tipo_envio", label: "Tipo de envio", required: true, help_text: "Seleccione el tipo de envio para descargar la plantilla correcta.", choices: [{ value: "standard", label: "Estandar" }, { value: "inet", label: "INET" }] },
  { name: "archivo", label: "Archivo Excel", required: true, help_text: "Cargue un archivo .xlsx.", accept: ".xlsx" },
];
const options = [
  { key: "standard", label: "Estandar", description: "Carga usuario y mail.", required_columns: ["usuario", "mail"] },
  { key: "inet", label: "INET", description: "Incluye el centro.", required_columns: ["usuario", "mail", "Nombre del Centro"] },
];
const recent = { id: 4, requested_at: "06/11/2026 17:02", status: "failed", send_type: "STANDARD", last_successful_username: "usuario0", last_successful_row: 2, last_error_message: "Fila 3: sin temporal.", detail_url: "/usuarios/credenciales-masivas/lotes/4/" };
const formData = (extra = {}) => ({ form_title: "Enviar credenciales masivas", fields, values: { tipo_envio: "standard" }, errors: {}, template_download_url: "/usuarios/credenciales-masivas/plantilla/", send_type_options: options, recent_jobs: [recent], messages: [], presentation, ...extra });
const job = { id: 9, original_filename: "credenciales.xlsx", requested_at: "06/11/2026 17:02", status: "failed", send_type: "INET", resume_count: 2, total_rows: 60, processed_rows: 3, sent_rows: 2, rejected_rows: 1, last_successful_username: "usuario1", last_successful_row: 3, last_attempted_username: "usuario2", last_attempted_row: 4, last_error_message: "Fila 4: sin temporal.", last_error_at: "06/11/2026 17:05" };
const rows = [{ id: 1, fila: 2, usuario: "usuario0", status: "sent", mail_destino: "", attempts: 1, mensaje: "Correo enviado." }, { id: 2, fila: 3, usuario: "", status: "failed", mail_destino: "d@example.invalid", attempts: 2, mensaje: "" }];
const detail = (extra = {}) => ({ job, rows, page: { number: 2, num_pages: 3, previous: 1, next: 3 }, is_resume_available: true, upload_url: "/usuarios/credenciales-masivas/", messages: [{ message: "El lote quedo pendiente para reanudarse desde la ultima fila fallida.", level: "success" }], presentation, ...extra });

let assign: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => {
  cleanup();
  assign.mockRestore();
  webGet.mockReset();
  webPost.mockReset();
});

async function openForm(data = formData()) {
  window.history.replaceState(null, "", "/usuarios/credenciales-masivas/");
  webGet.mockResolvedValue({ status: 200, data });
  render(<App />);
  return screen.findByRole("button", { name: "Crear lote" });
}

describe("bulk credentials form", () => {
  it("reads only its own transport and renders the native fields, send types and own history", async () => {
    await openForm();
    expect(webGet).toHaveBeenCalledTimes(1);
    expect(webGet).toHaveBeenCalledWith("web/users/bulk-credentials/", expect.any(Object));
    expect(document.title).toBe("SISOC - Credenciales masivas");
    expect(screen.getByRole("heading", { level: 3, name: "Enviar credenciales masivas" })).toBeTruthy();
    expect(document.querySelector(".breadcrumb .breadcrumb-item.active")?.textContent).toBe("Credenciales masivas");
    const select = document.getElementById("id_tipo_envio") as HTMLSelectElement;
    expect(select.className).toBe("form-control select form-select");
    expect(select.value).toBe("standard");
    expect([...select.options].map(o => o.textContent)).toEqual(["Estandar", "INET"]);
    expect((document.getElementById("id_archivo") as HTMLInputElement).accept).toBe(".xlsx");
    const inet = screen.getByText("INET", { selector: "strong" }).parentElement!;
    expect(inet.textContent).toBe("INET: Incluye el centro. Encabezados: usuario , mail , Nombre del Centro");
    expect(screen.getByText("Fallido").className).toBe("badge badge-danger");
    expect(screen.getByText("Fila 2").className).toBe("text-muted d-block");
    expect(screen.getByText("Fila 3: sin temporal.")).toBeTruthy();
    expect(screen.getByText("#4").childNodes).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Ver detalle" }).getAttribute("href")).toBe("/usuarios/credenciales-masivas/lotes/4/");
    expect(document.querySelector('link[rel="stylesheet"][href="/static/custom/css/hitos.css"]')).not.toBeNull();
  });

  it("keeps the template download as the native GET submission", async () => {
    await openForm();
    const download = screen.getByRole("button", { name: "Descargar plantilla" });
    expect(download.getAttribute("formaction")).toBe("/usuarios/credenciales-masivas/plantilla/");
    expect(download.getAttribute("formmethod")).toBe("get");
    expect(download.hasAttribute("formnovalidate")).toBe(true);
    const form = download.closest("form")!;
    const event = new SubmitEvent("submit", { bubbles: true, cancelable: true, submitter: download });
    form.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(false);
    expect(webPost).not.toHaveBeenCalled();
  });

  it("keeps the default Volver destination on the form, like the native page", async () => {
    await openForm();
    expect(document.querySelector(".sisoc-volver")?.getAttribute("href")).toBe("/");
  });

  it("shows the native empty-history notice", async () => {
    await openForm(formData({ recent_jobs: [] }));
    expect(screen.getByText("Todavia no hay lotes creados para credenciales masivas.")).toBeTruthy();
    expect(screen.queryByText("Ultimos lotes")).toBeNull();
  });

  it("enqueues once with the selected type and file, then opens the job detail", async () => {
    const submit = await openForm();
    const archivo = new File(["xlsx"], "credenciales.xlsx");
    fireEvent.change(document.getElementById("id_tipo_envio")!, { target: { value: "inet" } });
    fireEvent.change(document.getElementById("id_archivo")!, { target: { files: [archivo] } });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/usuarios/credenciales-masivas/lotes/31/" } });
    fireEvent.submit(submit.closest("form")!, { submitter: submit });
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/usuarios/credenciales-masivas/lotes/31/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [endpoint, body] = webPost.mock.calls[0];
    expect(endpoint).toBe("web/users/bulk-credentials/");
    expect((body as FormData).get("tipo_envio")).toBe("inet");
    expect((body as FormData).get("archivo")).toBe(archivo);
  });

  it("re-renders the bound form on a 400 and restarts keyboard navigation at the top", async () => {
    const submit = await openForm();
    webPost.mockRejectedValue({ response: { status: 400, data: formData({ values: { tipo_envio: "inet" }, errors: { archivo: [{ message: "Este campo es requerido.", code: "required" }] } }) } });
    submit.focus();
    fireEvent.click(submit);
    expect(await screen.findByText("Este campo es requerido.")).toBeTruthy();
    expect(document.getElementById("id_archivo")!.className).toBe("form-control is-invalid");
    expect((document.getElementById("id_tipo_envio") as HTMLSelectElement).value).toBe("inet");
    expect(assign).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(document.body);
  });

  it("reports an unconfirmed upload and never resubmits it", async () => {
    const submit = await openForm();
    webPost.mockRejectedValue(new Error("network"));
    fireEvent.click(submit);
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.click(submit);
    expect(webPost).toHaveBeenCalledTimes(1);
    expect((submit as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows the prerequisite instead of the form on a 403", async () => {
    window.history.replaceState(null, "", "/usuarios/credenciales-masivas/");
    webGet.mockResolvedValue({ status: 403, data: { detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" } });
    render(<App />);
    expect(await screen.findByText("Necesitás actualizar tu contraseña para continuar.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Crear lote" })).toBeNull();
  });
});

describe("bulk credentials job detail", () => {
  async function openDetail(data = detail(), search = "?page=2") {
    window.history.replaceState(null, "", `/usuarios/credenciales-masivas/lotes/9/${search}`);
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
    expect(webGet).toHaveBeenCalledWith("web/users/bulk-credentials/jobs/9/?page=2", expect.any(Object));
    expect(webPost).not.toHaveBeenCalled();
    expect(document.title).toBe("SISOC - Detalle de lote de credenciales");
  });

  it("goes back to the native volver_url of the job detail", async () => {
    await openDetail();
    expect(document.querySelector(".sisoc-volver")?.getAttribute("href")).toBe("/usuarios/credenciales-masivas/");
  });

  it("renders native counters, checkpoints, rows, pagination and actions", async () => {
    await openDetail();
    expect(screen.getByText("credenciales.xlsx | 06/11/2026 17:02").childNodes).toHaveLength(1);
    expect(screen.getByText("INET", { selector: "strong" })).toBeTruthy();
    expect(screen.getByText("Rechazadas").nextElementSibling?.textContent).toBe("1");
    expect(screen.getByText("usuario1").nextElementSibling?.textContent).toBe("Fila 3");
    expect(screen.getByText("usuario2").nextElementSibling?.textContent).toBe("Fila 4");
    expect(screen.getByText("Registrado el 06/11/2026 17:05").childNodes).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Actualizar estado" }).getAttribute("href")).toBe("/usuarios/credenciales-masivas/lotes/9/");
    expect(screen.getByRole("link", { name: "Anterior" }).getAttribute("href")).toBe("?page=1");
    expect(screen.getByRole("link", { name: "Siguiente" }).getAttribute("href")).toBe("?page=3");
    expect(screen.getAllByRole("row")[1].textContent).toBe("2usuario0 Enviada -1Correo enviado.");
    expect(screen.getAllByRole("row")[2].textContent).toBe("3- Fallida d@example.invalid2-");
    expect(screen.getByRole("link", { name: "Credenciales masivas" }).getAttribute("href")).toBe("/usuarios/credenciales-masivas/");
    expect(screen.getByText("El lote quedo pendiente para reanudarse desde la ultima fila fallida.")).toBeTruthy();
    expect(screen.queryByText(/Descargar CSV/)).toBeNull();
  });

  it("shows the native empty checkpoints, in-progress notice and hides resume", async () => {
    await openDetail(detail({ is_resume_available: false, rows: [], page: { number: 1, num_pages: 1, previous: null, next: null }, job: { ...job, status: "pending", last_successful_username: "", last_successful_row: null, last_attempted_username: "", last_attempted_row: null, last_error_message: "", last_error_at: "" } }), "");
    expect(screen.queryByRole("button", { name: "Reanudar" })).toBeNull();
    expect(screen.getByText("Todavia no hay envios exitosos.")).toBeTruthy();
    expect(screen.getByText("Todavia no se intento ninguna fila.")).toBeTruthy();
    expect((document.querySelector(".alert-info") as HTMLElement).firstChild?.textContent).toBe("El lote esta en curso fuera de la request web. Use ");
    expect(screen.getByText("Aun no hay filas procesadas para este lote.")).toBeTruthy();
    expect(screen.queryByRole("navigation", { name: "Paginacion de filas" })).toBeNull();
  });

  it("resumes with one POST and reloads the detail", async () => {
    await openDetail();
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/usuarios/credenciales-masivas/lotes/9/" } });
    fireEvent.click(screen.getByRole("button", { name: "Reanudar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/usuarios/credenciales-masivas/lotes/9/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/users/bulk-credentials/jobs/9/resume/");
  });

  it("does not retry an unconfirmed resume nor follow a foreign redirect", async () => {
    await openDetail();
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/usuarios/importar/lotes/9/" } });
    const button = screen.getByRole("button", { name: "Reanudar" });
    fireEvent.click(button);
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    fireEvent.click(button);
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(assign).not.toHaveBeenCalled();
    expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
  });
});
