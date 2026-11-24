import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import {
  pdfNavigation, RendicionesFiltro, RendicionesTable, rendicionesFiltroValid, rendicionesSectionValid, rendicionValid,
  type RendicionesFiltroSection, type RendicionesSection,
} from "./organizacionRendiciones";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const detail = (over: Record<string, unknown> = {}) => ({
  id: 9, number: 7, organization: { id: 8, name: "Org <Sur>" }, project_code: "P-1", convenio: "C-7", number_text: "7", period: "01/01/2026 al 31/03/2026",
  process: "Carga — En curso", territorial: "Sí", territorial_date: "01/04/2026 12:30", audit: "Sí", audit_date: "02/04/2026 00:05", validated: "No", validated_date: "-",
  audited: "No", audited_date: "-", audit_record_url: "/media/acta.pdf", regularized: "No", regularized_date: "-", complementary_record_url: null,
  can_view_rendicion: true, can_download_pdf: true,
  urls: { rendicion: "/rendicioncuentasmensual/detalle/9", pdf_request: "/rendicioncuentasmensual/detalle/9/descargar-pdf/solicitar/", pdf_status: "/rendicioncuentasmensual/detalle/9/descargar-pdf/estado/" },
  ...over,
});
function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
const open = () => { window.history.replaceState({}, "", "/organizaciones/8/rendiciones/9/detalle/"); return render(<App />); };
const json = (body: unknown, ok = true) => Promise.resolve({ ok, json: () => Promise.resolve(body) } as Response);

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); });

describe("Organization rendición detail route", () => {
  it("owns only the native path with its trailing slash", () => {
    expect(findRoute("/organizaciones/8/rendiciones/9/detalle/")?.route.name).toBe("comedores-organizaciones-rendiciones");
    for (const other of ["/organizaciones/8/rendiciones/9/detalle", "/organizaciones/0/rendiciones/9/detalle/", "/organizaciones/8/rendiciones/x/detalle/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-organizaciones-rendiciones");
    }
  });

  it("renders every native field in order, the go-to link and the file links", async () => {
    serve(detail());
    open();
    expect(await screen.findByRole("heading", { level: 4, name: "Rendición 7" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/comedores/organizaciones/8/rendiciones/9/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Detalle de Rendición"));
    expect(screen.getByText("Org <Sur>")).toBeTruthy();
    const labels = [...document.querySelectorAll(".card-body small.text-muted")].map((e) => e.textContent);
    expect(labels).toEqual(["Código de Proyecto", "Convenio", "Número de Rendición", "Período", "Estado del proceso", "Validación Territorial", "Fecha de Validación Territorial",
      "Validación Auditoría", "Fecha de Validación Auditoría", "Validación", "Fecha de Validación", "PDF Rendición", "Auditada", "Fecha de Auditada", "PDF Acta de Auditoría",
      "Regularización de Rendición", "Fecha de Regularización", "Acta Complementaria"]);
    expect(screen.getByText("Carga — En curso")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ir a Rendición" }).getAttribute("href")).toBe("/rendicioncuentasmensual/detalle/9");
    expect(screen.getAllByRole("link", { name: "Ver archivo" })).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Ver archivo" }).getAttribute("href")).toBe("/media/acta.pdf");
  });

  it("hides the go-to link and the download without their capabilities", async () => {
    serve(detail({ can_view_rendicion: false, can_download_pdf: false }));
    open();
    await screen.findByRole("heading", { level: 4, name: "Rendición 7" });
    expect(screen.queryByRole("link", { name: "Ir a Rendición" })).toBeNull();
    expect(screen.queryByRole("button", { name: /Descargar/ })).toBeNull();
  });

  it("requests the PDF once, polls the job and starts the download when it is ready", async () => {
    serve(detail());
    const go = vi.spyOn(pdfNavigation, "assign").mockImplementation(() => undefined);
    const fetchMock = vi.fn()
      .mockImplementationOnce(() => json({ estado: "pendiente" }))
      .mockImplementationOnce(() => json({ estado: "procesando" }))
      .mockImplementationOnce(() => json({ estado: "listo", url_descarga: "/media/rendicion.pdf" }));
    vi.stubGlobal("fetch", fetchMock);
    open();
    await screen.findByRole("heading", { level: 4, name: "Rendición 7" });
    vi.useFakeTimers({ shouldAdvanceTime: true });
    fireEvent.click(screen.getByRole("button", { name: /Descargar/ }));
    expect(await screen.findByText("Generando el PDF. Puede tardar unos minutos.")).toBeTruthy();
    expect((document.querySelector(".js-pdf-descarga-form button") as HTMLButtonElement).disabled).toBe(true);
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    await waitFor(() => expect(go).toHaveBeenCalledWith("/media/rendicion.pdf"));
    expect(screen.getByText("PDF listo. La descarga comienza en unos segundos.")).toBeTruthy();
    const [first, second] = fetchMock.mock.calls;
    expect(first[0]).toBe("/rendicioncuentasmensual/detalle/9/descargar-pdf/solicitar/");
    expect(first[1].method).toBe("POST");
    expect(first[1].headers["X-Requested-With"]).toBe("XMLHttpRequest");
    expect(first[1].headers["X-CSRFToken"]).toBe("synthetic-csrf-token");
    expect(second[0]).toBe("/rendicioncuentasmensual/detalle/9/descargar-pdf/estado/");
    expect(fetchMock.mock.calls.filter((c) => c[1]?.method === "POST")).toHaveLength(1);
  });

  it("shows the job's own message on error and the generic one when the answer is not JSON", async () => {
    serve(detail());
    const fetchMock = vi.fn()
      .mockImplementationOnce(() => json({ estado: "error", mensaje: "La rendición no está lista." }, false))
      .mockImplementationOnce(() => Promise.resolve({ ok: false, json: () => Promise.reject(new Error("html")) } as Response));
    vi.stubGlobal("fetch", fetchMock);
    open();
    await screen.findByRole("heading", { level: 4, name: "Rendición 7" });
    fireEvent.click(screen.getByRole("button", { name: /Descargar/ }));
    expect(await screen.findByText("La rendición no está lista.")).toBeTruthy();
    expect(screen.getByRole("status").className).toContain("text-danger");
    expect((screen.getByRole("button", { name: /Descargar/ }) as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: /Descargar/ }));
    expect(await screen.findByText("No se pudo generar el PDF.")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("gives up after the maximum wait", async () => {
    serve(detail());
    vi.stubGlobal("fetch", vi.fn(() => json({ estado: "procesando" })));
    open();
    await screen.findByRole("heading", { level: 4, name: "Rendición 7" });
    vi.useFakeTimers({ shouldAdvanceTime: true });
    fireEvent.click(screen.getByRole("button", { name: /Descargar/ }));
    await screen.findByText("Generando el PDF. Puede tardar unos minutos.");
    await act(async () => { await vi.advanceTimersByTimeAsync(15 * 60 * 1000 + 6000); });
    expect(await screen.findByText("La generación del PDF tardó demasiado. Intentá nuevamente.")).toBeTruthy();
  });

  it("shows the access screen on 403, an error on 404 and rejects malformed payloads", async () => {
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    open();
    await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
    expect(screen.queryByRole("heading", { level: 4 })).toBeNull();
    cleanup();
    serve({ detail: "No encontrado." }, 404);
    open();
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(rendicionValid(detail())).toBe(true);
    expect(rendicionValid(detail({ urls: { rendicion: "https://evil.example/", pdf_request: "/a", pdf_status: "/b" } }))).toBe(false);
  });
});

describe("Rendiciones legajo sections", () => {
  const row = (over: Record<string, unknown> = {}) => ({
    id: 1, line: "secos", line_label: "Secos", project: "S-1", convenio: "C-1", number: "1", period: "Marzo 2026", territorial: true, audit: false, validated: false, audited: true,
    url: "/organizaciones/8/rendiciones/1/detalle/", ...over,
  });
  const table = (over: Partial<RendicionesSection> = {}): RendicionesSection => ({ kind: "rendiciones", show_line: false, rows: [row()], ...over } as RendicionesSection);

  it("renders the table with ticks, dashes and the detail link", () => {
    render(<RendicionesTable section={table()} />);
    expect(screen.getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Conv.", "N° de Rend.", "Período", "Validación Territorial", "Revisión para Carga", "Validación", "Auditada", "Detalle"]);
    expect(screen.getAllByRole("cell").map((c) => c.textContent)).toEqual(["C-1", "1", "Marzo 2026", "✔", "-", "-", "✔", "Ver"]);
    expect(screen.getByRole("link", { name: "Ver" }).getAttribute("href")).toBe("/organizaciones/8/rendiciones/1/detalle/");
  });

  it("adds the line and project columns, with a badge or the no-line marker", () => {
    render(<RendicionesTable section={table({ show_line: true, rows: [row(), row({ id: 2, line: null, line_label: null, project: "-" })] })} />);
    expect(screen.getAllByRole("columnheader").map((c) => c.textContent).slice(0, 3)).toEqual(["Línea", "Proyecto", "Conv."]);
    expect(screen.getByText("Secos").className).toContain("badge-linea-secos");
    expect(screen.getByText("Sin línea").className).toContain("badge-pendiente");
  });

  it("filters through a GET form only when there is more than one code", () => {
    const section = (over: Partial<RendicionesFiltroSection>): RendicionesFiltroSection => ({ kind: "rendiciones_filtro", codes: ["S-1", "S-2"], selected: "S-2", program_id: 3, ...over });
    const { container, unmount } = render(<RendicionesFiltro section={section({})} />);
    expect(container.querySelector("form")?.getAttribute("method")).toBe("get");
    expect((container.querySelector("input[name=programa]") as HTMLInputElement).value).toBe("3");
    expect((container.querySelector("input[name=seccion]") as HTMLInputElement).value).toBe("rendiciones");
    expect((screen.getByLabelText("Código de Proyecto") as HTMLSelectElement).value).toBe("S-2");
    expect(screen.getByRole("option", { name: "Todos los proyectos" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Filtrar" })).toBeTruthy();
    unmount();
    const sinPrograma = render(<RendicionesFiltro section={section({ program_id: null })} />);
    expect(sinPrograma.container.querySelector("input[name=programa]")).toBeNull();
    sinPrograma.unmount();
    const uno = render(<RendicionesFiltro section={section({ codes: ["S-1"] })} />);
    expect(uno.container.querySelector("form")).toBeNull();
    expect(screen.getByText("S-1")).toBeTruthy();
    uno.unmount();
    expect(render(<RendicionesFiltro section={section({ codes: [] })} />).container.textContent).toBe("");
  });

  it("validates the section payloads", () => {
    expect(rendicionesSectionValid(table())).toBe(true);
    expect(rendicionesSectionValid({ ...table(), rows: [{ id: 1 }] })).toBe(false);
    expect(rendicionesFiltroValid({ kind: "rendiciones_filtro", codes: ["a"], selected: "", program_id: null })).toBe(true);
    expect(rendicionesFiltroValid({ kind: "rendiciones_filtro", codes: [1], selected: "" })).toBe(false);
  });
});
