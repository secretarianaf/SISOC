import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { jobValid, uploadValid } from "./ocr";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const upload = (over: Record<string, unknown> = {}) => ({
  max_file_size_mb: 20, allowed_extensions: ["jpeg", "jpg", "pdf", "png"],
  options: [
    { name: "opt_preprocess", label: "Preprocesado de imagen", help_text: "Limpieza con OpenCV antes del OCR. Apagarlo degrada en escaneos.", initial: true },
    { name: "opt_pdf_text_layer", label: "Usar capa de texto del PDF", help_text: "Aprovecha el texto digital.", initial: true },
    { name: "opt_auto_orient", label: "Auto-corregir orientación", help_text: "Detecta y endereza páginas rotadas.", initial: true },
  ],
  recent_jobs: [{ id: 3, requested_at: "10/11/2026 09:30", status: "completed_with_errors", processed_documents: 1, total_documents: 2, detail_url: "/ocr/3/" }],
  messages: [], ...over,
});
const doc = (over: Record<string, unknown> = {}) => ({
  id: 1, original_filename: "a.pdf", status: "completed", page_count: 2, file_size_label: "2,0 KB", extracted_text: "Hola <b>mundo</b>",
  error_message: "", processed_at: "10/11/2026 09:31:02", download_url: "/ocr/documentos/1/descargar/", ...over,
});
const job = (over: Record<string, unknown> = {}) => ({
  id: 3, requested_at: "10/11/2026 09:30", status: "completed_with_errors", total_documents: 3, processed_documents: 2, failed_documents: 1,
  last_error_message: "Fallo parcial", options: { preprocess: false, pdf_text_layer: true, auto_orient: true },
  documents: [doc(), doc({ id: 2, original_filename: "b.png", status: "no_text", page_count: null, extracted_text: "", download_url: null, error_message: "En blanco" }),
    doc({ id: 3, original_filename: "c.png", status: "failed", extracted_text: "", download_url: null, error_message: "", processed_at: "" })],
  upload_url: "/ocr/", messages: [{ message: "Lote OCR #3 creado con 3 archivo(s). El procesamiento se ejecuta en segundo plano.", level: "success" }], ...over,
});

function serve(data: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("OCR route", () => {
  it("owns the upload and batch detail paths only", () => {
    expect(findRoute("/ocr/")?.route.name).toBe("ocr");
    expect(findRoute("/ocr/7/")?.route.name).toBe("ocr");
    expect(findRoute("/ocr/documentos/7/descargar/")?.route.name).not.toBe("ocr");
    expect(uploadValid(upload())).toBe(true);
    expect(uploadValid({ ...upload(), recent_jobs: [{}] })).toBe(false);
    expect(jobValid(job())).toBe(true);
    expect(jobValid({ ...job(), documents: [{}] })).toBe(false);
  });

  it("renders the upload screen texts, selection count and recent batches", async () => {
    serve(upload());
    setup("/ocr/");
    expect(await screen.findByText("Extracción de texto (OCR)")).toBeTruthy();
    expect(screen.getByText("Tamaño máximo por archivo: 20 MB.")).toBeTruthy();
    expect(screen.getByText("Puede seleccionar varios archivos a la vez.")).toBeTruthy();
    expect(screen.getByText("Completado con errores")).toBeTruthy();
    expect(screen.getByText("1/2")).toBeTruthy();
    expect(screen.getByText("Ver detalle").getAttribute("href")).toBe("/ocr/3/");
    const input = document.getElementById("id_archivos") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["a"], "a.png"), new File(["b"], "b.png")] } });
    expect(await screen.findByText("2 archivos seleccionados")).toBeTruthy();
  });

  it("shows the empty list text", async () => {
    serve(upload({ recent_jobs: [] }));
    setup("/ocr/");
    expect(await screen.findByText("Todavía no hay lotes OCR creados.")).toBeTruthy();
  });

  it("posts the files with only the enabled options and shows server errors", async () => {
    serve(upload());
    webPost.mockResolvedValue({ status: 400, data: { errors: { archivos: ["Debe seleccionar al menos un archivo."] } } });
    setup("/ocr/");
    fireEvent.click(await screen.findByLabelText("Preprocesado de imagen"));
    fireEvent.click(screen.getByText("Procesar archivos"));
    expect(await screen.findByText("Debe seleccionar al menos un archivo.")).toBeTruthy();
    const [url, body] = webPost.mock.calls[0] as [string, FormData];
    expect(url).toBe("web/ocr/lotes/");
    expect([...body.keys()].sort()).toEqual(["opt_auto_orient", "opt_pdf_text_layer"]);
  });

  it("explains an unreadable answer without retrying", async () => {
    serve(upload());
    webPost.mockRejectedValue(new Error("timeout"));
    setup("/ocr/");
    fireEvent.click(await screen.findByText("Procesar archivos"));
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("renders the batch detail with per-state texts and download only where offered", async () => {
    serve(job());
    setup("/ocr/3/");
    expect(await screen.findByText("Lote OCR #3")).toBeTruthy();
    expect(screen.getByText("Preprocesado: OFF")).toBeTruthy();
    expect(screen.getByText("Capa de texto PDF: ON")).toBeTruthy();
    expect(screen.getByText("Fallo parcial")).toBeTruthy();
    expect(screen.getByText("No se pudo extraer texto legible del archivo.")).toBeTruthy();
    expect(screen.getByText("En blanco")).toBeTruthy();
    expect(screen.getByText("Error desconocido al procesar el archivo.", { exact: false })).toBeTruthy();
    expect(screen.getAllByText("2 páginas")).toHaveLength(2);
    expect(screen.getAllByText("Descargar .txt")).toHaveLength(1);
    expect(screen.getByText("Descargar .txt").getAttribute("href")).toBe("/ocr/documentos/1/descargar/");
    expect(screen.getByText("Lote OCR #3 creado con 3 archivo(s). El procesamiento se ejecuta en segundo plano.")).toBeTruthy();
  });

  it("toggles the text preview and reports a failed copy", async () => {
    serve(job());
    const writeText = vi.fn().mockRejectedValue(new Error("denied"));
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    const alert = vi.spyOn(window, "alert").mockImplementation(() => undefined);
    setup("/ocr/3/");
    fireEvent.click(await screen.findByText("Ver texto completo"));
    expect(await screen.findByText("Colapsar texto")).toBeTruthy();
    fireEvent.click(screen.getByText("Copiar"));
    await waitFor(() => expect(alert).toHaveBeenCalledWith("No se pudo copiar el texto. Selecciónelo manualmente."));
  });

  it("shows the pending state", async () => {
    serve(job({ status: "pending", failed_documents: 0, last_error_message: "", messages: [], documents: [doc({ status: "pending", extracted_text: "", download_url: null })] }));
    setup("/ocr/3/");
    expect(await screen.findByText("Esperando procesamiento...")).toBeTruthy();
    expect(screen.getAllByText("Pendiente")).toHaveLength(2);
  });

  it("shows the no documents text", async () => {
    serve(job({ documents: [], messages: [] }));
    setup("/ocr/3/");
    expect(await screen.findByText("Todavía no hay documentos en este lote.")).toBeTruthy();
  });
});
