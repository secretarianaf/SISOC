import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within, act } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { DocumentosSection, documentosSectionValid, historialValid, type DocRow, type DocumentosSection as Section } from "./organizacionDocumentos";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/organizaciones/";
const file = (over: Record<string, unknown> = {}) => ({
  id: 70, state: "Documento adjunto", observations: "", url: "/media/a.pdf", expiry: null, gde: "", ...over,
});
const row = (over: Partial<DocRow> = {}): DocRow => ({
  row_id: 5, name: "Estatuto", mandatory: true, custom: false, document_id: 5, history_url: "/organizaciones/8/documentacion/5/historial/",
  can_validate: false, can_send: true, file: file() as DocRow["file"], ...over,
});
const section = (rows: DocRow[], over: Partial<Section> = {}): Section => ({
  kind: "documentos", organization_id: 8, category: "Organizacion con personeria juridica", can_validate: false, can_send: true, rows, ...over,
});
const ok = (r: DocRow) => ({ status: 200, data: { fila: r } });
const fail = (status: number, error: string) => ({ status, data: { error } });
const pdf = () => new File(["%PDF"], "a.pdf", { type: "application/pdf" });

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Organization documents table", () => {
  it("shows the catalog columns, a required marker, the history button and the pending state", () => {
    render(<DocumentosSection section={section([row({ file: null, history_url: null }), row({ row_id: 6, document_id: 6, name: "Acta", mandatory: false })])} />);
    expect(screen.getByRole("heading", { level: 5, name: "Documentación de la Organización" })).toBeTruthy();
    expect(screen.getByText("Organizacion con personeria juridica")).toBeTruthy();
    expect(screen.getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Documento", "Estado / validación", "Archivo", "Vencimiento / carga", "Número de GDE"]);
    expect(screen.getByText("Pendiente")).toBeTruthy();
    expect(screen.getByText("Sin archivo")).toBeTruthy();
    expect(screen.getByText("*")).toBeTruthy();
    expect(screen.getAllByRole("link", { name: "Historial" })).toHaveLength(1);
    expect(screen.getByRole("link", { name: /Ver Archivo/ }).getAttribute("href")).toBe("/media/a.pdf");
  });

  it("renders the empty row and hides the additional block without the send capacity", () => {
    render(<DocumentosSection section={section([], { can_send: false })} />);
    expect(screen.getByText("No hay documentación configurada.")).toBeTruthy();
    expect(screen.queryByText("Documentación Adicional")).toBeNull();
  });

  it("offers each role only its own state choices, or a badge", () => {
    const { unmount } = render(<DocumentosSection section={section([row({ file: file({ state: "Rectificar", observations: "Falta firma" }) as DocRow["file"] })])} />);
    const options = (select: HTMLElement) => within(select).getAllByRole("option").map((o) => `${o.textContent}${(o as HTMLOptionElement).disabled ? "!" : ""}`);
    expect(options(screen.getByRole("combobox"))).toEqual(["Rectificar!", "Documento adjunto", "A Validar Abogado"]);
    expect(screen.getByText("Falta firma")).toBeTruthy();
    unmount();
    render(<DocumentosSection section={section([row({ can_validate: true, can_send: false, file: file({ state: "A Validar Abogado" }) as DocRow["file"] })], { can_validate: true, can_send: false })} />);
    expect(options(screen.getByRole("combobox"))).toEqual(["A Validar Abogado", "Aceptado", "Rectificar"]);
    cleanup();
    render(<DocumentosSection section={section([row({ can_send: false, file: file({ state: "A Validar Abogado" }) as DocRow["file"] })])} />);
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(screen.getByText("A Validar Abogado").className).toContain("bg-primary");
  });

  it("uploads once with progress, replaces the row and shows the success toast", async () => {
    let report: ((e: { loaded: number; total: number }) => void) | undefined;
    let finish: (() => void) | undefined;
    webPost.mockImplementation((_url: string, _body: unknown, config: { onUploadProgress: typeof report }) => {
      report = config.onUploadProgress;
      return new Promise((resolve) => {
        finish = () => resolve(ok(row({ file: file({ id: 71, state: "Documento adjunto" }) as DocRow["file"] })));
      });
    });
    render(<DocumentosSection section={section([row({ file: null, history_url: null })])} />);
    fireEvent.change(document.getElementById("org-doc-file-5") as HTMLInputElement, { target: { files: [pdf()] } });
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    report?.({ loaded: 1, total: 4 });
    expect(await screen.findByText("25%")).toBeTruthy();
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(`${API}8/documentacion/5/subir/`);
    expect((body as FormData).get("archivo")).toBeInstanceOf(File);
    act(() => finish?.());
    expect(await screen.findByText("Documento cargado con éxito.")).toBeTruthy();
    expect(screen.getByRole("combobox")).toBeTruthy();
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("keeps the Django text on a refused upload and says network failed when it did", async () => {
    webPost.mockResolvedValueOnce(fail(400, "El archivo excede el tamaño máximo permitido de 20 MB."));
    render(<DocumentosSection section={section([row({ file: null, history_url: null })])} />);
    fireEvent.change(document.getElementById("org-doc-file-5") as HTMLInputElement, { target: { files: [pdf()] } });
    expect(await screen.findByText("El archivo excede el tamaño máximo permitido de 20 MB.")).toBeTruthy();
    webPost.mockRejectedValueOnce(new Error("network"));
    fireEvent.change(document.getElementById("org-doc-file-5") as HTMLInputElement, { target: { files: [pdf()] } });
    expect(await screen.findByText("Error de red al subir el documento.")).toBeTruthy();
    webPost.mockResolvedValueOnce(fail(500, ""));
    fireEvent.change(document.getElementById("org-doc-file-5") as HTMLInputElement, { target: { files: [pdf()] } });
    expect(await screen.findByText("No se pudo subir el archivo.")).toBeTruthy();
    expect(webPost).toHaveBeenCalledTimes(3);
  });

  it("changes the state of a technician's document and reverts on a native refusal", async () => {
    webPost.mockResolvedValueOnce(ok(row({ file: file({ state: "A Validar Abogado" }) as DocRow["file"] })));
    render(<DocumentosSection section={section([row()])} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "A Validar Abogado" } });
    expect(await screen.findByText("Estado actualizado con éxito.")).toBeTruthy();
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(`${API}documentacion/70/estado/`);
    expect([...(body as FormData).entries()]).toEqual([["estado", "A Validar Abogado"]]);
    cleanup();
    webPost.mockResolvedValueOnce(fail(403, "El documento no esta disponible para envio tecnico."));
    render(<DocumentosSection section={section([row()])} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "A Validar Abogado" } });
    expect(await screen.findByText("El documento no esta disponible para envio tecnico.")).toBeTruthy();
    expect((screen.getByRole("combobox") as HTMLSelectElement).value).toBe("Documento adjunto");
  });

  it("asks for observations before a lawyer rectifies, and cancel sends nothing", async () => {
    const lawyer = row({ can_validate: true, can_send: false, file: file({ state: "A Validar Abogado" }) as DocRow["file"] });
    webPost.mockResolvedValueOnce(ok({ ...lawyer, file: file({ state: "Rectificar", observations: "Falta el sello" }) as DocRow["file"] }));
    render(<DocumentosSection section={section([lawyer], { can_validate: true, can_send: false })} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "Rectificar" } });
    expect(screen.getByRole("heading", { name: "Observaciones obligatorias" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Guardar observaciones" }));
    expect(screen.getByText("Debe completar las observaciones.")).toBeTruthy();
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("heading", { name: "Observaciones obligatorias" })).toBeNull();
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "Rectificar" } });
    fireEvent.change(screen.getByLabelText("Detalle el motivo de la rectificacion"), { target: { value: "  Falta el sello " } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar observaciones" }));
    expect(await screen.findByText("Estado actualizado con éxito.")).toBeTruthy();
    expect([...(webPost.mock.calls[0][1] as FormData).entries()]).toEqual([["estado", "Rectificar"], ["observaciones", "Falta el sello"]]);
    expect(screen.getByText("Falta el sello")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Observaciones obligatorias" })).toBeNull();
  });

  it("edits the expiry inline: coloured date with its badge, save once, cancel and errors", async () => {
    const withExpiry = row({ file: file({ expiry: { date: "01/01/2000", iso: "2000-01-01", status: "vencido" } }) as DocRow["file"] });
    render(<DocumentosSection section={section([withExpiry])} />);
    expect(screen.getByText("01/01/2000").className).toContain("text-danger");
    expect(screen.getByText("Vencido")).toBeTruthy();
    fireEvent.click(screen.getByText("01/01/2000"));
    const input = document.querySelector("input.org-inline-input") as HTMLInputElement;
    expect(input.value).toBe("2000-01-01");
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(document.querySelector("input.org-inline-input")).toBeNull();
    webPost.mockResolvedValueOnce(fail(400, "Fecha de vencimiento invalida."));
    fireEvent.click(screen.getByText("01/01/2000"));
    fireEvent.change(document.querySelector("input.org-inline-input") as HTMLInputElement, { target: { value: "2031-02-03" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Fecha de vencimiento invalida.")).toBeTruthy();
    webPost.mockResolvedValueOnce(ok(row({ file: file({ expiry: { date: "03/02/2031", iso: "2031-02-03", status: "vigente" } }) as DocRow["file"] })));
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Vencimiento actualizado con éxito.")).toBeTruthy();
    expect(webPost.mock.calls.map((c) => c[0])).toEqual([`${API}documentacion/70/vencimiento/`, `${API}documentacion/70/vencimiento/`]);
    expect(screen.getByText("03/02/2031").className).toContain("text-success");
    expect(screen.getByText("Vigente")).toBeTruthy();
  });

  it("shows the GDE only on accepted documents, editable for the dupla and read-only otherwise", async () => {
    const accepted = row({ file: file({ state: "Aceptado", gde: "" }) as DocRow["file"] });
    webPost.mockResolvedValueOnce(ok({ ...accepted, file: file({ state: "Aceptado", gde: "GDE-9" }) as DocRow["file"] }));
    render(<DocumentosSection section={section([accepted])} />);
    fireEvent.click(screen.getByText("Sin número GDE"));
    fireEvent.change(screen.getByPlaceholderText("Ingrese número GDE"), { target: { value: " GDE-9 " } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Número GDE actualizado con éxito.")).toBeTruthy();
    expect([...(webPost.mock.calls[0][1] as FormData).entries()]).toEqual([["numero_gde", "GDE-9"]]);
    expect(webPost.mock.calls[0][0]).toBe(`${API}documentacion/70/numero-gde/`);
    expect(screen.getByText("GDE-9")).toBeTruthy();
    cleanup();
    render(<DocumentosSection section={section([row({ can_send: false, file: file({ state: "Aceptado", gde: "" }) as DocRow["file"] })])} />);
    expect(screen.queryByText("Sin número GDE")).toBeNull();
    expect(screen.getAllByText("-").length).toBeGreaterThan(0);
  });

  it("adds an additional document: a name is required first, then one multipart POST appends the row", async () => {
    webPost.mockResolvedValueOnce(ok(row({ row_id: "custom-90", name: "Extra", custom: true, document_id: null, history_url: null, file: file({ id: 90 }) as DocRow["file"] })));
    render(<DocumentosSection section={section([])} />);
    fireEvent.click(screen.getByRole("button", { name: /Agregar documento adicional/ }));
    expect(await screen.findByText("Debe indicar un nombre para el documento.")).toBeTruthy();
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Nombre del documento"), { target: { value: " Extra " } });
    fireEvent.change(screen.getByLabelText("Vencimiento (opcional)"), { target: { value: "2030-01-02" } });
    fireEvent.change(document.getElementById("nuevoDocOrgArchivo") as HTMLInputElement, { target: { files: [pdf()] } });
    expect(await screen.findByText("Documento adicional agregado con éxito.")).toBeTruthy();
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(`${API}8/documentacion/personalizada/`);
    expect([...(body as FormData).keys()]).toEqual(["nombre", "fecha_vencimiento", "archivo"]);
    expect((body as FormData).get("nombre")).toBe("Extra");
    expect(screen.getByText("Extra")).toBeTruthy();
    expect(screen.getByText("Adicional")).toBeTruthy();
    expect(screen.queryByText("No hay documentación configurada.")).toBeNull();
    expect((screen.getByLabelText("Nombre del documento") as HTMLInputElement).value).toBe("");
    expect(screen.queryByRole("button", { name: "Adjuntar" })).toBeNull();
  });

  it("validates the section payload", () => {
    expect(documentosSectionValid(section([row()]))).toBe(true);
    expect(documentosSectionValid({ ...section([]), rows: [{ name: 1 }] })).toBe(false);
  });
});

describe("Organization document history route", () => {
  const data = {
    organization: { id: 8, name: "Org <Sur>" }, document: { id: 5, name: "Estatuto" }, urls: { list: "/organizaciones/listar", legajo: "/organizaciones/detalle/8" },
    files: [
      { id: 2, created: "02/01/2026 10:00", state: "Rectificar", expiry: "-", observations: "Revisar", url: "/media/b.pdf" },
      { id: 1, created: "01/01/2026 09:00", state: "Aceptado", expiry: "01/01/2030", observations: "-", url: "/media/a.pdf" },
    ],
  };
  const serve = (payload: unknown, status = 200) =>
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: payload, status }));

  it("owns only the native history path with its trailing slash", () => {
    expect(findRoute("/organizaciones/8/documentacion/5/historial/")?.route.name).toBe("comedores-organizaciones-documentos");
    for (const other of ["/organizaciones/8/documentacion/5/historial", "/organizaciones/0/documentacion/5/historial/", "/organizaciones/8/documentacion/x/historial/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-organizaciones-documentos");
    }
  });

  it("renders the versions newest first with the native columns, badges and breadcrumb", async () => {
    serve(data);
    window.history.replaceState({}, "", "/organizaciones/8/documentacion/5/historial/");
    render(<App />);
    expect(await screen.findByRole("heading", { level: 3, name: "Estatuto" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}8/documentacion/5/historial/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Historial de documentacion"));
    expect(screen.getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Fecha de carga", "Estado", "Fecha de vencimiento", "Observaciones", "Archivo"]);
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows.map((r) => r.children[0].textContent)).toEqual(["02/01/2026 10:00", "01/01/2026 09:00"]);
    expect(screen.getByText("Rectificar").className).toContain("bg-danger");
    expect(screen.getByText("Aceptado").className).toContain("bg-success");
    expect(screen.getAllByRole("link", { name: "Ver archivo" })[1].getAttribute("href")).toBe("/media/a.pdf");
    expect(screen.getByRole("link", { name: "Org <Sur>" }).getAttribute("href")).toBe("/organizaciones/detalle/8");
    expect(screen.getByText("Historial", { selector: ".breadcrumb-item" })).toBeTruthy();
  });

  it("shows the empty text, the access screen on 403 and an error on 404", async () => {
    serve({ ...data, files: [] });
    window.history.replaceState({}, "", "/organizaciones/8/documentacion/5/historial/");
    render(<App />);
    expect(await screen.findByText("No hay documentos cargados.")).toBeTruthy();
    cleanup();
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    render(<App />);
    await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
    expect(screen.queryByText("Estatuto")).toBeNull();
    cleanup();
    serve({ detail: "No encontrado." }, 404);
    render(<App />);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(historialValid({ ...data, files: [{ id: 1 }] })).toBe(false);
  });
});
