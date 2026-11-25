import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { navigation } from "./cdfFrame";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const urls = { list: "/centrodefamilia/informecabal/", preview: "/centrodefamilia/informecabal/preview/", process: "/centrodefamilia/informecabal/process/", reprocess: "/centrodefamilia/informecabal/reprocess/" };
const archivo = (id: number, nombre: string, fecha: string, orden: string, usuario: string, total: number, validas: number) => ({
  id, nombre_original: nombre, fecha_subida: fecha, fecha_orden: orden, usuario, total_filas: total, total_validas: validas, total_invalidas: total - validas,
  urls: { detail: `/centrodefamilia/informecabal/${id}/` },
});
const lista = (over: Record<string, unknown> = {}) => ({
  page: 1, has_previous: false, has_next: true, previous_page: null, next_page: 2,
  results: [archivo(3, "b.xlsx", "05/10/2026 10:00", "2026-10-05 10:00", "ana", 10, 7), archivo(2, "a.xlsx", "04/10/2026 09:30", "2026-10-04 09:30", "zoe", 4, 4)],
  alerts: [], urls, messages: [], ...over,
});
const registro = (n: number, over: Record<string, unknown> = {}) => ({
  numero: n, nro_comercio: `NC${n}`, razon_social: `Razon ${n}`, importe: "1234,50", fecha_trx: "05/10/2026", moneda_origen: "ARS", importe_pesos: "1234,50",
  pago_aceptado: true, impactado: true, urls: { detail: `/centrodefamilia/informecabal/registro/5/?registro=${n + 10}` }, ...over,
});

function serve(endpoint: string, page: unknown) {
  webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
    : url === endpoint ? Promise.resolve({ data: page, status: 200 }) : Promise.reject(new Error(url))));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const reply = (body: unknown, status = 200, json = true) => ({
  ok: status >= 200 && status < 300, status,
  headers: { get: () => (json ? "application/json" : "text/html") },
  json: async () => { if (!json) throw new Error("not json"); return body; },
  text: async () => String(body),
});
const calls = () => (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls as [string, RequestInit][];
const column = (index: number) => Array.from(document.querySelectorAll("table.projects tbody tr")).map((row) => row.querySelectorAll("td")[index]?.textContent);

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  vi.stubGlobal("fetch", vi.fn());
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("CDF Informe Cabal routes", () => {
  it("owns only the four native screens, never the AJAX endpoints", () => {
    for (const [path, params] of [
      ["/centrodefamilia/informecabal/", { kind: "list" }],
      ["/centrodefamilia/informecabal/7/", { kind: "archivo", id: "7" }],
      ["/centrodefamilia/informecabal/registro/7/", { kind: "registro", id: "7" }],
      ["/centrodefamilia/centros/4/informecabal/7/", { kind: "centro", centro: "4", id: "7" }],
    ] as const) {
      expect(findRoute(path)?.route.name).toBe("cdf-informecabal");
      expect(findRoute(path)?.params).toEqual(params);
    }
    for (const path of ["/centrodefamilia/informecabal/preview/", "/centrodefamilia/informecabal/process/", "/centrodefamilia/informecabal/reprocess/",
      "/centrodefamilia/informecabal/0/", "/centrodefamilia/centros/4/"]) {
      expect(findRoute(path)?.route.name).not.toBe("cdf-informecabal");
    }
  });

  it("renders the history like the native list, with inline alerts, pagination links and the local sort", async () => {
    serve("web/cdf/informecabal/", lista({ alerts: [{ message: "Informe CABAL procesado correctamente.", tags: "success" }] }));
    setup("/centrodefamilia/informecabal/");
    await screen.findByRole("heading", { name: "Historial de Archivos CABAL" });
    await waitFor(() => expect(document.title).toBe("SISOC - Informe Cabal - Historial"));
    expect(document.querySelector(".alert.alert-success.fade.show")?.textContent).toBe("Informe CABAL procesado correctamente.");
    expect(Array.from(document.querySelectorAll("thead th")).map((th) => th.textContent?.trim())).toEqual(["Archivo", "Fecha", "Usuario", "Total", "Válidas", "Inválidas", "Acciones"]);
    expect(column(0)).toEqual(["b.xlsx", "a.xlsx"]);
    expect(column(1)).toEqual(["05/10/2026 10:00", "04/10/2026 09:30"]);
    expect(document.querySelector<HTMLAnchorElement>("a.btn-info")?.getAttribute("href")).toBe("/centrodefamilia/informecabal/3/");
    expect(document.querySelector<HTMLAnchorElement>(".pagination a.page-link")?.getAttribute("href")).toBe("?page=2");
    expect(document.querySelector(".pagination li.disabled")?.textContent).toBe("Anterior");
    expect(document.querySelector(".pagination li.active")?.textContent).toBe("1");
    expect(webGet).toHaveBeenCalledWith("web/cdf/informecabal/", expect.anything());
    // Header click sorts the rows of the page: ascending, descending, then it stays as is (listSort.js).
    const usuario = document.querySelector<HTMLElement>('th[data-column="usuario"]')!;
    fireEvent.click(usuario);
    expect(column(2)).toEqual(["ana", "zoe"]);
    expect(usuario.className).toBe("sortable sort-asc");
    expect(usuario.querySelector("i")?.className).toBe("fas sort-icon fa-sort-up");
    fireEvent.click(usuario);
    expect(column(2)).toEqual(["zoe", "ana"]);
    fireEvent.click(document.querySelector<HTMLElement>('th[data-column="total"]')!);
    expect(column(3)).toEqual(["4", "10"]);
    fireEvent.click(usuario);
    fireEvent.click(usuario);
    fireEvent.click(usuario);
    expect(usuario.className).toBe("sortable");
    expect(usuario.querySelector("i")?.className).toBe("fas sort-icon fa-sort");
  });

  it("shows the empty row and the page query", async () => {
    serve("web/cdf/informecabal/?page=2", lista({ results: [], page: 2, has_previous: true, has_next: false, previous_page: 1, next_page: null }));
    setup("/centrodefamilia/informecabal/?page=2");
    await screen.findByText("Sin archivos procesados aún.");
    expect(document.querySelector(".pagination a.page-link")?.getAttribute("href")).toBe("?page=1");
    expect(document.querySelectorAll(".pagination li.disabled")).toHaveLength(1);
  });

  it("previews a chosen file page by page and processes it once, reloading like the native script", async () => {
    serve("web/cdf/informecabal/", lista());
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(reply({
      ok: true, total: 30, not_matching: [2, 5],
      rows: [{ fila: 1, no_coincidente: false, data: { NroComercio: "N1", RazonSocial: "R1", Importe: 10, FechaTRX: "2026-10-01", MonedaOrigen: "ARS", ImportePesos: 10, MotivoRechazo: 0 } },
        { fila: 2, no_coincidente: true, data: { NroComercio: "<b>x</b>" } }],
    }));
    setup("/centrodefamilia/informecabal/");
    fireEvent.click(await screen.findByRole("button", { name: "Procesar nuevo archivo" }));
    expect(document.querySelector("#modalCabal .modal-title")?.textContent).toBe("Procesar nuevo archivo CABAL");
    expect(document.querySelector("#preview-table tbody")?.textContent).toBe("Sin datos");
    expect((document.getElementById("btn-procesar") as HTMLButtonElement).disabled).toBe(true);
    expect((document.getElementById("btn-prev") as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(document.getElementById("fileCabal")!, { target: { files: [new File(["x"], "nuevo.xlsx")] } });
    await waitFor(() => expect(document.querySelectorAll("#preview-table tbody tr")).toHaveLength(2));
    const [url, init] = calls()[0];
    expect(url).toBe(urls.preview);
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("same-origin");
    expect(init.headers).toEqual({ "X-CSRFToken": "synthetic-csrf-token" });
    expect((init.body as FormData).get("page")).toBe("1");
    expect((init.body as FormData).get("file")).toBeInstanceOf(File);
    expect(document.querySelector("#preview-table tbody tr")?.textContent).toBe("1N1R110" + "2026-10-01ARS100");
    expect(document.querySelectorAll("#preview-table tbody tr")[1].className).toBe("table-warning");
    // Cell values are text, never markup.
    expect(document.querySelectorAll("#preview-table tbody tr")[1].textContent).toContain("<b>x</b>");
    expect(document.querySelector("#alert-zone .alert-warning")?.textContent).toBe("Registros no coincidentes: (2, 5)");
    expect(document.getElementById("page-indicator")?.textContent).toBe("1");
    expect((document.getElementById("btn-next") as HTMLButtonElement).disabled).toBe(false);
    expect((document.getElementById("btn-procesar") as HTMLButtonElement).disabled).toBe(false);

    fetchMock.mockResolvedValueOnce(reply({ ok: true, total: 30, not_matching: [], rows: [{ fila: 26, data: {} }] }));
    fireEvent.click(document.getElementById("btn-next")!);
    await waitFor(() => expect(document.getElementById("page-indicator")?.textContent).toBe("2"));
    await waitFor(() => expect((calls()[1][1].body as FormData).get("page")).toBe("2"));
    await waitFor(() => expect(document.querySelector("#alert-zone .alert")).toBeNull());
    expect((document.getElementById("btn-next") as HTMLButtonElement).disabled).toBe(true);

    fetchMock.mockResolvedValueOnce(reply({ ok: true, archivo_id: 9, total: 30, validas: 28, invalidas: 2, not_matching: [] }));
    const procesar = document.getElementById("btn-procesar") as HTMLButtonElement;
    await waitFor(() => expect(procesar.disabled).toBe(false));
    fireEvent.click(procesar);
    fireEvent.click(procesar);
    await waitFor(() => expect(document.querySelector("#alert-zone .alert-success")?.textContent).toBe("Archivo procesado. Total: 30, Válidas: 28, Inválidas: 2"));
    const process = calls().filter(([target]) => target === urls.process);
    expect(process).toHaveLength(1);
    expect((process[0][1].body as FormData).get("force")).toBe("false");
    expect(procesar.disabled).toBe(true);
    await waitFor(() => expect(assign).toHaveBeenCalledWith(window.location.href), { timeout: 2000 });
  });

  it("clears the preview on an error answer and on a non-JSON answer", async () => {
    serve("web/cdf/informecabal/", lista());
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    setup("/centrodefamilia/informecabal/");
    fireEvent.click(await screen.findByRole("button", { name: "Procesar nuevo archivo" }));
    const input = document.getElementById("fileCabal")!;
    fetchMock.mockResolvedValueOnce(reply({ ok: false, error: "El archivo no tiene el formato esperado o está dañado." }, 400));
    fireEvent.change(input, { target: { files: [new File(["x"], "mal.xlsx")] } });
    await screen.findByText("El archivo no tiene el formato esperado o está dañado.");
    expect(document.querySelector("#alert-zone .alert-danger")).not.toBeNull();
    expect(document.querySelector("#preview-table tbody")?.textContent).toBe("Sin datos");
    expect((document.getElementById("btn-procesar") as HTMLButtonElement).disabled).toBe(true);
    fetchMock.mockResolvedValueOnce(reply("No se envió archivo.", 400, false));
    fireEvent.change(input, { target: { files: [new File(["x"], "otro.xlsx")] } });
    await screen.findByText("Error inesperado al previsualizar");
  });

  it("asks before forcing a duplicate name and shows the processing errors", async () => {
    serve("web/cdf/informecabal/", lista());
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    const confirm = vi.spyOn(navigation, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    setup("/centrodefamilia/informecabal/");
    fireEvent.click(await screen.findByRole("button", { name: "Procesar nuevo archivo" }));
    fetchMock.mockResolvedValueOnce(reply({ ok: true, total: 1, not_matching: [], rows: [{ fila: 1, data: {} }] }));
    fireEvent.change(document.getElementById("fileCabal")!, { target: { files: [new File(["x"], "dup.xlsx")] } });
    const procesar = document.getElementById("btn-procesar") as HTMLButtonElement;
    await waitFor(() => expect(procesar.disabled).toBe(false));

    fetchMock.mockResolvedValueOnce(reply({ ok: false, duplicate_name: true }, 409));
    fireEvent.click(procesar);
    await waitFor(() => expect(confirm).toHaveBeenCalledWith("Ya se subió un archivo con este nombre. ¿Desea proseguir?"));
    await waitFor(() => expect(procesar.disabled).toBe(false));
    expect(calls().filter(([target]) => target === urls.process)).toHaveLength(1);

    fetchMock.mockResolvedValueOnce(reply({ ok: false, duplicate_name: true }, 409));
    fetchMock.mockResolvedValueOnce(reply({ ok: false, error: "Error inesperado al procesar." }, 500));
    fireEvent.click(procesar);
    await screen.findByText("Error inesperado al procesar.");
    const process = calls().filter(([target]) => target === urls.process);
    expect(process).toHaveLength(3);
    expect((process[2][1].body as FormData).get("force")).toBe("true");
    expect(procesar.disabled).toBe(false);
  });

  it("closes the modals with Cancelar, the cross and Escape", async () => {
    serve("web/cdf/informecabal/", lista());
    setup("/centrodefamilia/informecabal/");
    const abrir = await screen.findByRole("button", { name: "Procesar nuevo archivo" });
    fireEvent.click(abrir);
    fireEvent.click(document.getElementById("btn-cancelar")!);
    expect(document.getElementById("modalCabal")).toBeNull();
    fireEvent.click(abrir);
    fireEvent.click(document.querySelector("#modalCabal .close")!);
    expect(document.getElementById("modalCabal")).toBeNull();
    fireEvent.click(abrir);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(document.getElementById("modalCabal")).toBeNull();
    expect(document.body.classList.contains("modal-open")).toBe(false);
  });

  it("reprocesses by centre code with the native messages", async () => {
    serve("web/cdf/informecabal/", lista());
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    setup("/centrodefamilia/informecabal/");
    const abrir = await screen.findByRole("button", { name: "Reprocesar rechazados" });
    expect(document.getElementById("reprocess-result")?.className).toBe("mt-2 d-none alert");
    fireEvent.click(abrir);
    expect(document.querySelector("#modalReprocesarCentro .modal-title")?.textContent).toBe("Reprocesar centro");
    expect(document.getElementById("codigoCentro")?.getAttribute("placeholder")).toBe("Ej: FARO-001");
    await waitFor(() => expect(document.activeElement?.id).toBe("codigoCentro"));
    fireEvent.click(document.getElementById("btnConfirmReprocesar")!);
    expect(document.getElementById("reprocess-result")?.textContent).toBe("Debés ingresar un código de centro.");
    expect(document.getElementById("reprocess-result")?.className).toBe("mt-2 alert alert-danger");
    // The error re-renders the page: the focus stays on the code input, as the native script leaves it.
    expect(document.activeElement?.id).toBe("codigoCentro");
    expect(fetchMock).not.toHaveBeenCalled();

    fetchMock.mockResolvedValueOnce(reply({ ok: false, error: "No se pudo reprocesar el centro. Revise los datos e intente nuevamente." }, 400));
    fireEvent.change(document.getElementById("codigoCentro")!, { target: { value: " FARO-001 " } });
    fireEvent.click(document.getElementById("btnConfirmReprocesar")!);
    await waitFor(() => expect(document.getElementById("reprocess-result")?.textContent).toBe("Error: No se pudo reprocesar el centro. Revise los datos e intente nuevamente."));
    const [url, init] = calls()[0];
    expect(url).toBe(urls.reprocess);
    expect(init.headers).toEqual({ "X-CSRFToken": "synthetic-csrf-token", "Content-Type": "application/x-www-form-urlencoded" });
    expect(init.body).toBe("codigo=FARO-001");
    expect(document.getElementById("modalReprocesarCentro")).not.toBeNull();

    fetchMock.mockResolvedValueOnce(reply({ ok: true, procesados: 3, impactados: 2, por_archivo: { 7: 2, 8: 1 } }));
    fireEvent.click(document.getElementById("btnConfirmReprocesar")!);
    await waitFor(() => expect(document.getElementById("reprocess-result")?.textContent).toBe("OK. Procesados: 3 | Impactados: 2 | por archivo: 7:2, 8:1"));
    expect(document.getElementById("reprocess-result")?.className).toBe("mt-2 alert alert-success");
    expect(document.getElementById("modalReprocesarCentro")).toBeNull();
  });

  it("reports a non-JSON and a network failure of the reprocess", async () => {
    serve("web/cdf/informecabal/", lista());
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    setup("/centrodefamilia/informecabal/");
    fireEvent.click(await screen.findByRole("button", { name: "Reprocesar rechazados" }));
    fireEvent.change(document.getElementById("codigoCentro")!, { target: { value: "X1" } });
    fetchMock.mockResolvedValueOnce(reply("<html>boom</html>", 502, false));
    fireEvent.click(document.getElementById("btnConfirmReprocesar")!);
    await waitFor(() => expect(document.getElementById("reprocess-result")?.textContent).toBe("Error: Respuesta no JSON (status 502). <html>boom</html>"));
    fetchMock.mockRejectedValueOnce(new Error("offline"));
    fireEvent.click(document.getElementById("btnConfirmReprocesar")!);
    await waitFor(() => expect(document.getElementById("reprocess-result")?.textContent).toBe("Error de red: offline"));
    expect((document.getElementById("btnConfirmReprocesar") as HTMLButtonElement).disabled).toBe(false);
  });
});

describe("CDF Informe Cabal detail screens", () => {
  it("renders the file detail with its badges, counters and the empty state", async () => {
    const data = {
      archivo: { id: 5, nombre_original: "informe.xlsx", fecha_subida: "05/10/2026 10:00", usuario: "ana", total_filas: 3, total_validas: 2, total_invalidas: 1 },
      registros: [registro(1), registro(2, { pago_aceptado: false, impactado: false })], urls: { list: "/centrodefamilia/informecabal/" }, messages: [],
    };
    serve("web/cdf/informecabal/5/", data);
    setup("/centrodefamilia/informecabal/5/");
    await screen.findByText("Detalle del Archivo");
    await waitFor(() => expect(document.title).toBe("SISOC - Detalle Archivo CABAL"));
    expect(document.querySelector(".mb-3 a.btn-secondary.btn-sm")?.textContent).toBe("← Volver");
    expect(Array.from(document.querySelectorAll("dt")).map((e) => e.textContent)).toEqual(["Nombre Original", "Fecha de Subida", "Usuario", "Total Filas", "Válidas (Impactadas)", "Inválidas (Rechazadas)"]);
    expect(Array.from(document.querySelectorAll("dd")).map((e) => e.textContent)).toEqual(["informe.xlsx", "05/10/2026 10:00", "ana", "3", "2", "1"]);
    expect(document.querySelector("dd.text-success")?.textContent).toBe("2");
    expect(document.querySelector("dd.text-danger")?.textContent).toBe("1");
    const rows = document.querySelectorAll("tbody tr");
    expect(rows[0].textContent).toBe("1NC1Razon 11234,5005/10/2026ARS1234,50Pago aceptadoImpactado");
    expect(rows[1].textContent).toBe("2NC2Razon 21234,5005/10/2026ARS1234,50Pago no aceptadoRechazado");
    expect(rows[1].querySelectorAll(".badge-danger")).toHaveLength(2);
    expect(screen.getByRole("link", { name: "Ver registro 1" }).getAttribute("href"))
      .toBe("/centrodefamilia/informecabal/registro/5/?registro=11");
    expect(screen.getByRole("link", { name: "Ver registro 2" }).getAttribute("href"))
      .toBe("/centrodefamilia/informecabal/registro/5/?registro=12");
  });

  it("shows the empty file state", async () => {
    serve("web/cdf/informecabal/5/", {
      archivo: { id: 5, nombre_original: "x.xlsx", fecha_subida: "05/10/2026 10:00", usuario: "ana", total_filas: 0, total_validas: 0, total_invalidas: 0 },
      registros: [], urls: { list: "/centrodefamilia/informecabal/" }, messages: [],
    });
    setup("/centrodefamilia/informecabal/5/");
    await screen.findByText("No hay registros asociados a este archivo.");
  });

  it("renders the native registro page with its empty values", async () => {
    serve("web/cdf/informecabal/registro/5/", { messages: [] });
    setup("/centrodefamilia/informecabal/registro/5/");
    await screen.findByRole("heading", { name: "Detalle de Registro CABAL #" });
    await waitFor(() => expect(document.title).toBe("SISOC - Detalle Registro CABAL"));
    expect(Array.from(document.querySelectorAll("dt")).map((e) => e.textContent)).toEqual(["Centro", "NroComercio", "RazonSocial", "FechaTRX", "Importe", "ImportePesos", "MonedaOrigen", "MotivoRechazo", "Desc Motivo Rechazo", "No coincidente", "Fila (Excel)"]);
    expect(Array.from(document.querySelectorAll("dd")).map((e) => e.textContent)).toEqual(["—", "", "", "", "", "", "", "", "", "No", ""]);
  });

  it("requests the selected registro and renders its Centro and No coincidente", async () => {
    const source = {
      id: 12, centro: "—", nro_comercio: "NC2", razon_social: "Razon 2", fecha_trx: "05/10/2026",
      importe: "1234,50", importe_pesos: "1234,50", moneda_origen: "ARS", motivo_rechazo: "05",
      desc_motivo_rechazo: "Rechazado", no_coincidente: "Sí", fila_numero: "7",
    };
    serve("web/cdf/informecabal/registro/5/?registro=12", {
      registro: source, urls: { archivo: "/centrodefamilia/informecabal/5/" }, messages: [],
    });
    setup("/centrodefamilia/informecabal/registro/5/?registro=12");
    await screen.findByRole("heading", { name: "Detalle de Registro CABAL #12" });
    expect(screen.getByText("Centro").nextElementSibling?.textContent).toBe("—");
    expect(screen.getByText("No coincidente").nextElementSibling?.textContent).toBe("Sí");
    expect(screen.getByText("NroComercio").nextElementSibling?.textContent).toBe("NC2");
    expect(screen.getByRole("link", { name: "← Volver al archivo" }).getAttribute("href"))
      .toBe("/centrodefamilia/informecabal/5/");
  });

  it("renders the per-centre page with pager and the empty alert", async () => {
    const base = {
      centro: { id: 4, nombre: "CDF Cuatro" }, count: 51, page: 1, num_pages: 2, has_previous: false, has_next: true, previous_page: null, next_page: 2, messages: [],
      results: [{ numero: 1, nro_comercio: "NC1", razon_social: "Razon 1", importe: "$1234,50", fecha_trx: "05/10/2026", pago_aceptado: true },
        { numero: 2, nro_comercio: "NC2", razon_social: "Razon 2", importe: "$5,00", fecha_trx: "06/10/2026", pago_aceptado: false }],
    };
    serve("web/cdf/centros/4/informecabal/5/", base);
    setup("/centrodefamilia/centros/4/informecabal/5/");
    await screen.findByText("Registros CABAL para CDF Cuatro");
    await waitFor(() => expect(document.title).toBe("SISOC - Archivos CABAL - CDF Cuatro"));
    const rows = document.querySelectorAll("tbody tr");
    expect(rows[0].textContent).toBe("1NC1Razon 1$1234,5005/10/2026Pago aceptado");
    expect(rows[1].querySelector("td.text-danger.font-weight-bold")?.textContent).toBe("Pago no aceptado");
    expect(document.querySelector(".mt-3")?.textContent).toBe("51 registros encontrados.");
    expect(document.querySelector(".card-body .mt-2")?.textContent).toBe("Página 1 de 2 Siguiente");
    expect(document.querySelector<HTMLAnchorElement>(".card-body .mt-2 a")?.getAttribute("href")).toBe("?page=2");
    cleanup();
    serve("web/cdf/centros/4/informecabal/5/?page=2", { ...base, page: 2, has_previous: true, has_next: false, previous_page: 1, next_page: null });
    setup("/centrodefamilia/centros/4/informecabal/5/?page=2");
    await screen.findByText("Anterior");
    expect(document.querySelector(".card-body .mt-2")?.textContent).toBe("Anterior Página 2 de 2");
    cleanup();
    serve("web/cdf/centros/4/informecabal/5/", { ...base, results: [], count: 0, has_next: false, next_page: null, num_pages: 1 });
    setup("/centrodefamilia/centros/4/informecabal/5/");
    await screen.findByText("No hay registros CABAL para este centro.");
    expect(document.querySelector(".alert-info")).not.toBeNull();
  });

  it("answers a missing record and a malformed payload like the other CDF screens", async () => {
    webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 }) : Promise.resolve({ data: {}, status: 404 })));
    setup("/centrodefamilia/informecabal/99/");
    await screen.findByText("No se encontró la página.");
    cleanup();
    serve("web/cdf/informecabal/", { page: "x" });
    setup("/centrodefamilia/informecabal/");
    await screen.findByText("No se pudo cargar la página.");
  });
});
