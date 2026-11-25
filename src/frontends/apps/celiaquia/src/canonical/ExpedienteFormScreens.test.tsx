// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ExpedienteEditarScreen, ExpedienteNuevoScreen } from "./ExpedienteFormScreens";

const URLS = {
  preview: "/celiaquia/expedientes/preview_excel/",
  plantilla: "/celiaquia/expedientes/plantilla_excel/",
  localidades: "/celiaquia/expedientes/localidades_lookup/",
  cancel: "/celiaquia/expedientes/",
};

function projection(overrides: Record<string, unknown> = {}) {
  return {
    version: 1, mode: "create", title: "Crear Expediente", expediente: null,
    fields: {
      numero_expediente: { label: "Número Expediente", required: false, max_length: 100, value: "" },
      observaciones: { label: "Observaciones", required: false, value: "" },
      excel_masivo: { label: "Archivo Excel", required: true, accept: ".xlsx", max_bytes: 5 * 1024 * 1024, current: null },
    },
    urls: URLS, preview_max_limit: 5000,
    provincias: [{ id: 6, nombre: "Buenos Aires" }],
    ...overrides,
  };
}

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const xlsx = (name = "carga.xlsx", size = 10) => new File([new Uint8Array(size)], name, { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  document.cookie = "csrftoken=token-sintetico";
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

async function showNew(navigate = vi.fn()) {
  fetchMock.mockResolvedValueOnce(json(projection()));
  render(<ExpedienteNuevoScreen params={{}} navigate={navigate} />);
  await screen.findByRole("heading", { name: "Crear Expediente" });
  return navigate;
}

function pickFile(file: File) {
  fireEvent.change(screen.getByLabelText(/Archivo Excel/), { target: { files: [file] } });
}

it("loads the canonical projection and renders the native fields and links", async () => {
  await showNew();
  expect(fetchMock).toHaveBeenCalledWith("/celiaquia/expedientes/nuevo/", expect.objectContaining({ headers: { Accept: "application/json" } }));
  expect(screen.getByLabelText("Número Expediente")).toHaveAttribute("maxLength", "100");
  expect(screen.getByLabelText("Observaciones").tagName).toBe("TEXTAREA");
  const file = screen.getByLabelText(/Archivo Excel/);
  expect(file).toHaveAttribute("accept", ".xlsx");
  expect(file).toBeRequired();
  expect(screen.getByRole("link", { name: "Descargar plantilla" })).toHaveAttribute("href", URLS.plantilla);
  expect(screen.getByRole("link", { name: "Cancelar" })).toHaveAttribute("href", URLS.cancel);
});

it("rejects a non-xlsx or oversized file on the client without sending it", async () => {
  await showNew();
  pickFile(xlsx("viejo.xls"));
  fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
  expect(await screen.findByText("Solo se permiten archivos .xlsx.")).toBeInTheDocument();
  pickFile(xlsx("grande.xlsx", 5 * 1024 * 1024 + 1));
  expect(await screen.findByText("El archivo supera el tamaño máximo de 5 MB.")).toBeInTheDocument();
  expect(screen.getByLabelText(/Archivo Excel/)).toHaveAttribute("aria-invalid", "true");
  fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("submits the native form as JSON once and navigates to the returned redirect", async () => {
  const navigate = await showNew();
  let resolve!: (value: Response) => void;
  fetchMock.mockReturnValueOnce(new Promise<Response>((done) => { resolve = done; }));
  fireEvent.change(screen.getByLabelText("Número Expediente"), { target: { value: "EX-1" } });
  pickFile(xlsx());
  fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
  await waitFor(() => expect(screen.getByRole("button", { name: /Guardando/ })).toBeDisabled());
  const [url, init] = fetchMock.mock.calls[1];
  expect(url).toBe("/celiaquia/expedientes/nuevo/");
  expect(init.method).toBe("POST");
  expect(init.headers).toMatchObject({ Accept: "application/json", "X-CSRFToken": "token-sintetico" });
  const body = init.body as FormData;
  expect(body.get("numero_expediente")).toBe("EX-1");
  expect((body.get("excel_masivo") as File).name).toBe("carga.xlsx");
  resolve(json({ ok: true, redirect: "/celiaquia/expedientes/41/" }));
  await waitFor(() => expect(navigate).toHaveBeenCalledWith("/celiaquia/expedientes/41/"));
});

it("shows server field and form errors linked to their inputs", async () => {
  const navigate = await showNew();
  fetchMock.mockResolvedValueOnce(json({ ok: false, errors: { excel_masivo: ["Extensión no permitida."], __all__: ["Error general."] } }, 400));
  pickFile(xlsx());
  fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
  const fieldError = await screen.findByText("Extensión no permitida.");
  const input = screen.getByLabelText(/Archivo Excel/);
  expect(input.getAttribute("aria-describedby")).toContain(fieldError.id);
  expect(input).toHaveAttribute("aria-invalid", "true");
  expect(screen.getByRole("alert")).toHaveTextContent("Error general.");
  expect(screen.getByRole("button", { name: "Guardar" })).toBeEnabled();
  expect(navigate).not.toHaveBeenCalled();
});

it("never retries after a transport failure and blocks resubmission", async () => {
  const navigate = await showNew();
  fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
  pickFile(xlsx());
  fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
  expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Guardar" })).toBeDisabled();
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(navigate).not.toHaveBeenCalled();
});

it("previews the selected Excel with the chosen row limit", async () => {
  await showNew();
  fireEvent.click(screen.getByRole("button", { name: "Previsualizar Excel" }));
  expect(await screen.findByText("Primero seleccioná un archivo Excel.")).toBeInTheDocument();
  pickFile(xlsx());
  fireEvent.change(screen.getByLabelText("Filas a previsualizar"), { target: { value: "50" } });
  fetchMock.mockResolvedValueOnce(json({ headers: ["apellido", "nombre"], rows: [{ apellido: "<b>Sol</b>", nombre: "Ana" }], total_rows: 120, shown_rows: 1 }));
  fireEvent.click(screen.getByRole("button", { name: "Previsualizar Excel" }));
  const table = await screen.findByRole("table", { name: "Vista previa del Excel" });
  expect(within(table).getByText("<b>Sol</b>")).toBeInTheDocument();
  expect(screen.getByText("Mostrando 1 de 120 filas.")).toBeInTheDocument();
  const [url, init] = fetchMock.mock.calls[1];
  expect(url).toBe(URLS.preview);
  expect((init.body as FormData).get("limit")).toBe("50");
  // Preview never posts to the canonical form URL.
  expect(fetchMock.mock.calls.filter(([target, options]) => target === "/celiaquia/expedientes/nuevo/" && options?.method === "POST")).toHaveLength(0);
});

it("reports preview errors with the native message", async () => {
  await showNew();
  pickFile(xlsx());
  fetchMock.mockResolvedValueOnce(json({ error: "Faltan columnas." }, 400));
  fireEvent.click(screen.getByRole("button", { name: "Previsualizar Excel" }));
  expect(await screen.findByText("Error al previsualizar: Faltan columnas.")).toBeInTheDocument();
});

it("searches localidades and filters them by text", async () => {
  await showNew();
  fetchMock.mockResolvedValueOnce(json([
    { provincia_id: 6, provincia_nombre: "Buenos Aires", municipio_id: 1, municipio_nombre: "La Plata", localidad_id: 10, localidad_nombre: "Tolosa" },
    { provincia_id: 6, provincia_nombre: "Buenos Aires", municipio_id: 2, municipio_nombre: "Quilmes", localidad_id: 20, localidad_nombre: "Bernal" },
  ]));
  fireEvent.click(screen.getByRole("button", { name: "Buscar localidades" }));
  const dialog = await screen.findByRole("dialog", { name: "Buscar Localidades" });
  await within(dialog).findByRole("cell", { name: "10 - Tolosa" });
  expect(fetchMock).toHaveBeenLastCalledWith(`${URLS.localidades}?`, expect.anything());
  fireEvent.change(within(dialog).getByLabelText("Buscar"), { target: { value: "bernal" } });
  expect(within(dialog).queryByRole("cell", { name: "10 - Tolosa" })).not.toBeInTheDocument();
  expect(within(dialog).getByRole("cell", { name: "20 - Bernal" })).toBeInTheDocument();
  fetchMock.mockResolvedValueOnce(json([]));
  fireEvent.change(within(dialog).getByLabelText("Provincia"), { target: { value: "6" } });
  await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith(`${URLS.localidades}?provincia=6`, expect.anything()));
  fireEvent.keyDown(dialog, { key: "Escape" });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Buscar localidades" })).toHaveFocus();
});

it("edits an expediente showing the current Excel without requiring a new one", async () => {
  fetchMock.mockResolvedValueOnce(json(projection({
    mode: "edit", title: "Editar Expediente", expediente: { id: 7, numero: "EX-7" },
    fields: {
      numero_expediente: { label: "Número Expediente", required: false, max_length: 100, value: "EX-7" },
      observaciones: { label: "Observaciones", required: false, value: "nota" },
      excel_masivo: { label: "Archivo Excel", required: true, accept: ".xlsx", max_bytes: 5242880, current: { name: "celiaquia/original.xlsx", url: "/media/celiaquia/original.xlsx" } },
    },
    provincias: [],
  })));
  const navigate = vi.fn();
  render(<ExpedienteEditarScreen params={{ pk: "7" }} navigate={navigate} />);
  await screen.findByRole("heading", { name: "Editar Expediente" });
  expect(fetchMock.mock.calls[0][0]).toBe("/celiaquia/expedientes/7/editar/");
  expect(screen.getByLabelText("Número Expediente")).toHaveValue("EX-7");
  expect(screen.getByLabelText("Observaciones")).toHaveValue("nota");
  expect(screen.getByRole("link", { name: "celiaquia/original.xlsx" })).toHaveAttribute("href", "/media/celiaquia/original.xlsx");
  expect(screen.getByLabelText(/Archivo Excel/)).not.toBeRequired();
  fetchMock.mockResolvedValueOnce(json({ ok: true, redirect: "/celiaquia/expedientes/7/" }));
  fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
  await waitFor(() => expect(navigate).toHaveBeenCalledWith("/celiaquia/expedientes/7/"));
  expect(fetchMock.mock.calls[1][0]).toBe("/celiaquia/expedientes/7/editar/");
});

it("shows a load error for a denied or incompatible projection", async () => {
  fetchMock.mockResolvedValueOnce(new Response("", { status: 403 }));
  render(<ExpedienteNuevoScreen params={{}} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("No tiene permiso para ver esta pantalla.");
  cleanup();
  fetchMock.mockResolvedValueOnce(json({ ...projection(), version: 2 }));
  render(<ExpedienteNuevoScreen params={{}} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("no es compatible");
});
