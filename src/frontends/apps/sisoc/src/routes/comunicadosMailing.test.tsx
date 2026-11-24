import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { comunicadosMailingNavigation, formValid, jobValid } from "./comunicadosMailing";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/comunicados/mailing/";
const NATIVE = "/comunicados/mailing/";
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, label: name, help_text: `ayuda ${name}`, required: true, type: "text", accept: "", value: "", errors: [], ...over,
});
const form = (over: Record<string, unknown> = {}, fields = [
  field("asunto", { label: "Asunto" }), field("cuerpo", { label: "Cuerpo", type: "textarea" }),
  field("archivo", { label: "Archivo Excel", type: "file", accept: ".xlsx" }),
  field("archivos_adjuntos", { label: "Archivos adjuntos", type: "files", required: false }),
]) => ({
  form_title: "Envío de mailing masivo", fields, template_download_url: `${NATIVE}plantilla/`, gestion_url: "/comunicados/gestion/", recent_jobs: [], messages: [], ...over,
});
const job = (over: Record<string, unknown> = {}, jobOver: Record<string, unknown> = {}) => ({
  job: {
    id: 4, original_filename: "destinos.xlsx", requested_at: "12/11/2026 10:30", status: "failed", asunto: "Hola", cuerpo: "Texto\nlargo", resume_count: 1,
    total_rows: 3, processed_rows: 2, sent_rows: 1, rejected_rows: 1, last_successful: { mail: "ok@example.com", fila: 2 }, last_attempted: { mail: "", fila: null },
    last_error_message: "El mail 'x' no es valido.", last_error_at: "12/11/2026 10:31", attachments: [{ nombre_original: "a.pdf", url: "/media/a.pdf" }], ...jobOver,
  },
  rows: [{ fila: 2, status: "sent", mail_destino: "ok@example.com", attempts: 1, mensaje: "-" }, { fila: 3, status: "failed", mail_destino: "x", attempts: 1, mensaje: "Error" }],
  page: { number: 1, num_pages: 1, previous: null, next: null }, is_resume_available: true, resume_url: `${NATIVE}lotes/4/reanudar/`, refresh_url: `${NATIVE}lotes/4/`,
  upload_url: NATIVE, gestion_url: "/comunicados/gestion/", messages: [], ...over,
});

function serve(body: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
let assign: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  assign = vi.spyOn(comunicadosMailingNavigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); assign.mockRestore(); vi.restoreAllMocks(); });

describe("Comunicados mailing route", () => {
  it("owns the two native paths ahead of the comunicados module and validates its payloads", () => {
    expect(findRoute(NATIVE)?.route.name).toBe("comedores-comunicados-mailing");
    expect(findRoute(`${NATIVE}lotes/4/`)?.params).toEqual({ pk: "4" });
    for (const other of [`${NATIVE}plantilla/`, `${NATIVE}lotes/4/reanudar/`, `${NATIVE}lotes/x/`]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-comunicados-mailing");
    }
    expect(formValid(form())).toBe(true);
    expect(formValid(form({ fields: [] }))).toBe(false);
    expect(jobValid(job())).toBe(true);
    expect(jobValid(job({ page: { number: "1" } }))).toBe(false);
  });

  it("renders the form with its help texts, the empty batches notice and the native buttons", async () => {
    serve(form());
    setup(NATIVE);
    expect(await screen.findByRole("heading", { name: "Envío de mailing masivo" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    expect(screen.getByText("ayuda archivo")).toBeTruthy();
    expect(screen.getByText("Todavía no hay lotes creados para mailing masivo.")).toBeTruthy();
    const template = screen.getByRole("button", { name: "Descargar plantilla" }) as HTMLButtonElement;
    expect(template.getAttribute("formaction")).toBe(`${NATIVE}plantilla/`);
    expect(screen.getAllByRole("link", { name: "Volver" }).some((l) => l.className.includes("btn-secondary") && l.getAttribute("href") === "/comunicados/gestion/")).toBe(true);
    expect(document.querySelector('input[name="archivos_adjuntos"]')?.hasAttribute("multiple")).toBe(true);
  });

  it("lists the own recent batches with their badges", async () => {
    serve(form({ recent_jobs: [
      { id: 7, requested_at: "01/11/2026 09:00", status: "completed", asunto_corto: "Hola", last_successful_mail: "a@b.com", last_successful_row: 5, last_error_message: "", detail_url: `${NATIVE}lotes/7/` },
      { id: 6, requested_at: "01/11/2026 08:00", status: "weird", asunto_corto: "X", last_successful_mail: "", last_successful_row: null, last_error_message: "Falló", detail_url: `${NATIVE}lotes/6/` },
    ] }));
    setup(NATIVE);
    expect(await screen.findByText("Completado")).toBeTruthy();
    expect(screen.getByText("Pendiente")).toBeTruthy();
    expect(screen.getByText("Fila 5")).toBeTruthy();
    expect(screen.getAllByRole("link", { name: "Ver detalle" })[0].getAttribute("href")).toBe(`${NATIVE}lotes/7/`);
  });

  it("posts the multipart form once and follows the native redirect", async () => {
    serve(form());
    webPost.mockResolvedValue({ data: { ok: true, redirect: `${NATIVE}lotes/9/` }, status: 200 });
    setup(NATIVE);
    await screen.findByText("Archivo Excel");
    const send = screen.getByRole("button", { name: "Crear lote de mailing" });
    const element = document.querySelector("form[enctype=\"multipart/form-data\"]") as HTMLFormElement;
    fireEvent.submit(element);
    await waitFor(() => expect(assign).toHaveBeenCalledWith(`${NATIVE}lotes/9/`));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(API);
    expect(webPost.mock.calls[0][1]).toBeInstanceOf(FormData);
    expect((send as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows a rejected upload with its field errors and keeps the typed text", async () => {
    serve(form());
    const rejected = form({}, [
      field("asunto", { label: "Asunto", value: "Mi asunto" }), field("cuerpo", { label: "Cuerpo", type: "textarea" }),
      field("archivo", { label: "Archivo Excel", type: "file", errors: ["El archivo debe incluir una columna llamada 'mail'."] }),
      field("archivos_adjuntos", { label: "Archivos adjuntos", type: "files", required: false }),
    ]);
    webPost.mockResolvedValue({ data: rejected, status: 400 });
    setup(NATIVE);
    await screen.findByText("Archivo Excel");
    fireEvent.submit(document.querySelector("form[enctype=\"multipart/form-data\"]") as HTMLFormElement);
    expect(await screen.findByText("El archivo debe incluir una columna llamada 'mail'.")).toBeTruthy();
    expect((screen.getByLabelText(/Asunto/) as HTMLInputElement).value).toBe("Mi asunto");
    expect(document.getElementById("id_archivo")?.className).toContain("is-invalid");
    expect(assign).not.toHaveBeenCalled();
  });

  it("does not resend after an uncertain upload", async () => {
    serve(form());
    webPost.mockRejectedValue({ response: { status: 504, data: { uncertain: true } } });
    setup(NATIVE);
    await screen.findByText("Archivo Excel");
    fireEvent.submit(document.querySelector("form[enctype=\"multipart/form-data\"]") as HTMLFormElement);
    expect(await screen.findByText("No se pudo confirmar el resultado. Revise los últimos lotes antes de volver a cargar el archivo.")).toBeTruthy();
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(assign).not.toHaveBeenCalled();
  });

  it("renders the batch detail with its literal texts", async () => {
    serve(job());
    setup(`${NATIVE}lotes/4/`);
    expect((await screen.findAllByText("Lote #4")).length).toBe(2);
    expect(webGet).toHaveBeenCalledWith(`${API}jobs/4/`, expect.anything());
    for (const t of ["Filas totales", "Filas procesadas", "Enviadas", "Rechazadas", "Último mail enviado correctamente", "Último mail intentado", "Todavía no se intentó ninguna fila.",
      "Cuerpo del mensaje", "Archivos adjuntos", "Causa del error", "Enviado", "Fallido"]) expect(screen.getAllByText(t).length).toBeGreaterThan(0);
    expect(screen.getByText("Registrado el 12/11/2026 10:31")).toBeTruthy();
    expect(screen.getByRole("link", { name: "a.pdf" }).getAttribute("href")).toBe("/media/a.pdf");
    expect(screen.getByRole("link", { name: "Actualizar estado" }).getAttribute("href")).toBe(`${NATIVE}lotes/4/`);
    expect(screen.queryByText(/El lote está en curso/)).toBeNull();
  });

  it("shows the in-progress notice and no resume button for a pending batch", async () => {
    serve(job({ is_resume_available: false }, { status: "pending", last_error_message: "", last_error_at: null, attachments: [] }));
    setup(`${NATIVE}lotes/4/`);
    expect(await screen.findByText(/El lote está en curso fuera de la request web/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Reanudar" })).toBeNull();
    expect(screen.queryByText("Archivos adjuntos")).toBeNull();
  });

  it("pages the rows only when there is more than one page", async () => {
    serve(job({ page: { number: 2, num_pages: 3, previous: 1, next: 3 } }));
    setup(`${NATIVE}lotes/4/?page=2`);
    expect(await screen.findByText("Página 2 de 3")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}jobs/4/?page=2`, expect.anything());
    expect(screen.getByRole("link", { name: "Anterior" }).getAttribute("href")).toBe("?page=1");
    expect(screen.getByRole("link", { name: "Siguiente" }).getAttribute("href")).toBe("?page=3");
  });

  it("resumes once and follows the redirect; an uncertain result is not resent", async () => {
    serve(job());
    webPost.mockResolvedValueOnce({ data: { ok: true, redirect: `${NATIVE}lotes/4/` }, status: 200 });
    setup(`${NATIVE}lotes/4/`);
    const button = await screen.findByRole("button", { name: "Reanudar" });
    fireEvent.click(button);
    fireEvent.click(button);
    await waitFor(() => expect(assign).toHaveBeenCalledWith(`${NATIVE}lotes/4/`));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}jobs/4/resume/`);
  });

  it("says the resume result is uncertain without resending", async () => {
    serve(job());
    webPost.mockRejectedValue({ response: { status: 504, data: { uncertain: true } } });
    setup(`${NATIVE}lotes/4/`);
    fireEvent.click(await screen.findByRole("button", { name: "Reanudar" }));
    expect(await screen.findByText("No se pudo confirmar el resultado. Use Actualizar estado.")).toBeTruthy();
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("shows the access screen on 403", async () => {
    serve({ detail: "x" }, 403);
    setup(NATIVE);
    await waitFor(() => expect(screen.queryByText("Cargando mailing…")).toBeNull());
    expect(screen.queryByText("Envío de mailing masivo")).toBeNull();
  });
});
