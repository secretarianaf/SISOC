import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { expedientesNavigation } from "./expedientesPagosList";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const BASE = "/expedientespagos/expedientespagos/";
const API = "web/comedores/expedientespagos/";
const columns = {
  list_key: "expedientes_pagos_list", endpoint: "/ajax/columnas-preferencias/",
  modal_id: "column-config-modal-expedientes_pagos_list", script_id: "column-config-data-expedientes_pagos_list",
  available: [{ key: "mes_pago", title: "Mes de Pago", active: true, required: false, default: true }],
};
const HEADERS = ["Mes de Pago", "Año", "Expediente de Pago", "Expediente del Convenio", "Total", "Fecha de creación"];
const list = (over: Record<string, unknown> = {}) => ({
  comedor_id: 7, can_create: true, create_url: `${BASE}7/nuevo/`, breadcrumb_url: "/acompanamientos/acompanamiento/7/detalle/",
  columns, headers: HEADERS,
  results: [{ id: 3, cells: ["setiembre", "2026", "EP<1>", "EC-1", "$1.235", "11/11/2026"], detail_url: `${BASE}3/detalle/` }],
  messages: [], ...over,
});
const DETAIL_KEYS = [
  "expediente_pago", "expediente_convenio", "mes_pago", "mes_convenio", "ano", "organizacion_creacion", "anexo",
  "total_prestaciones", "gastos_accesorios", "total", "numero_orden_pago", "fecha_creacion", "fecha_pago_al_banco",
  "fecha_acreditacion", "observaciones",
  ...["desayuno", "almuerzo", "merienda", "cena"].flatMap((c) => [`prestaciones_mensuales_${c}`, `monto_mensual_${c}`]),
];
const detail = (over: Record<string, string> = {}) => ({
  id: 3, comedor_id: 7,
  expediente: { ...Object.fromEntries(DETAIL_KEYS.map((k) => [k, "-"])), total: "$2.000", observaciones: "", monto_mensual_cena: "$100", ...over },
  list_url: `${BASE}7/`, update_url: `${BASE}3/editar/`, delete_url: `${BASE}3/eliminar/`, messages: [],
});
const NAMES = [
  "expediente_pago", "expediente_convenio", "anexo", "if_cantidad_de_prestaciones", "if_pagado", "total_prestaciones",
  "gastos_accesorios", "total", "mes_pago", "ano", "organizacion_creacion", "numero_orden_pago", "fecha_pago_al_banco",
  "fecha_acreditacion", "observaciones",
  ...["desayuno", "almuerzo", "merienda", "cena"].map((c) => `prestaciones_mensuales_${c}`),
  ...["desayuno", "almuerzo", "merienda", "cena"].map((c) => `monto_mensual_${c}`),
];
const typeOf = (n: string) => (n.startsWith("fecha") ? "date" : n === "observaciones" ? "textarea"
  : /total|gastos|monto|prestaciones_mensuales/.test(n) ? "number" : "text");
const fields = (values: Record<string, string> = {}, errors: Record<string, string[]> = {}) => NAMES.map((name) => ({
  name, label: name === "expediente_convenio" ? "Expediente del Convenio" : name === "ano" ? "Año" : name,
  type: typeOf(name), required: name === "expediente_convenio", max_length: name === "ano" ? "4" : null,
  step: name.startsWith("monto") || name === "total" ? "0.01" : null, value: values[name] ?? "", errors: errors[name] ?? [],
}));
const form = (over: Record<string, unknown> = {}) => ({ comedor_id: 7, fields: fields(), cancel_url: `${BASE}7/`, ...over });

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
let assign: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  assign = vi.spyOn(expedientesNavigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); assign.mockRestore(); });

describe("Expedientes de pago route", () => {
  it("owns the five native paths with their trailing slashes", () => {
    expect(findRoute(`${BASE}7/`)?.params).toEqual({ mode: "list", id: "7" });
    expect(findRoute(`${BASE}3/detalle/`)?.params).toEqual({ mode: "detail", id: "3" });
    expect(findRoute(`${BASE}7/nuevo/`)?.params).toEqual({ mode: "create", id: "7" });
    expect(findRoute(`${BASE}3/editar/`)?.params).toEqual({ mode: "edit", id: "3" });
    expect(findRoute(`${BASE}3/eliminar/`)?.params).toEqual({ mode: "delete", id: "3" });
    for (const other of [`${BASE}7`, `${BASE}x/`, "/expedientespagos/7/", `${BASE}3/detalle`]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-expedientes-pagos");
    }
  });

  it("lists the native cells as text, the create button and the column control", async () => {
    serve(list());
    setup(`${BASE}7/?page=1`);
    await screen.findByText("EP<1>");
    expect(webGet).toHaveBeenCalledWith(`${API}comedores/7/?page=1`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Listado de Expedientes de pagos"));
    expect(screen.getByRole("heading", { level: 1, name: "Listado de Expedientes de Pagos" })).toBeTruthy();
    const rows = screen.getAllByRole("row");
    expect(within(rows[0]).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([...HEADERS, "Acciones"]);
    expect(within(rows[1]).getAllByRole("cell").map((c) => c.textContent)).toEqual(["setiembre", "2026", "EP<1>", "EC-1", "$1.235", "11/11/2026", " Ver"]);
    expect(within(rows[1]).getByRole("link", { name: "Ver" }).getAttribute("href")).toBe(`${BASE}3/detalle/`);
    expect(screen.getByRole("link", { name: "Nuevo Expediente de Pago" }).getAttribute("href")).toBe(`${BASE}7/nuevo/`);
    expect(screen.getByRole("link", { name: "Expedientes de pagos" }).getAttribute("href")).toBe("/acompanamientos/acompanamiento/7/detalle/");
    fireEvent.click(screen.getByRole("button", { name: "Configurar columnas" }));
    expect(await screen.findByRole("dialog", { name: "Columnas visibles" })).toBeTruthy();
  });

  it("hides the create button without the codes and shows the native empty row", async () => {
    serve(list({ can_create: false, results: [] }));
    setup(`${BASE}9/`);
    expect(await screen.findByText("No hay expedientes de pagos registrados para este comedor.")).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Nuevo Expediente de Pago" })).toBeNull();
  });

  it("renders the stored amounts, the actions menu and observations only when present", async () => {
    serve(detail({ observaciones: "Pagado" }));
    setup(`${BASE}3/detalle/`);
    await screen.findByText("Información del Expediente");
    await waitFor(() => expect(document.title).toBe("SISOC - Expediente de Pago"));
    expect(screen.getByText("Observaciones")).toBeTruthy();
    expect(screen.getAllByText("$2.000")).toHaveLength(2);
    const toggle = screen.getByRole("button", { name: "Acciones" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(toggle);
    await waitFor(() => expect(toggle.getAttribute("aria-expanded")).toBe("true"));
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe(`${BASE}3/editar/`);
    expect(screen.getByRole("link", { name: "Eliminar" }).className).toContain("text-danger");
    const cena = screen.getByRole("row", { name: /Cena/ });
    expect(within(cena).getAllByRole("cell").map((c) => c.textContent)).toEqual(["Cena", "-", "$100"]);
    cleanup();
    serve(detail());
    setup(`${BASE}3/detalle/`);
    await screen.findByText("Información del Expediente");
    expect(screen.queryByText("Observaciones")).toBeNull();
  });

  it("posts the 23 rendered fields once and follows the native redirect", async () => {
    serve(form());
    let release: (v: unknown) => void = () => undefined;
    webPost.mockReturnValue(new Promise((r) => { release = r; }));
    setup(`${BASE}7/nuevo/`);
    await screen.findByRole("heading", { level: 1, name: "Crear Expediente de Pago" });
    await waitFor(() => expect(document.title).toBe("SISOC - Crear Expediente de Pago"));
    expect(screen.getByLabelText("Año").getAttribute("maxlength")).toBe("4");
    fireEvent.change(screen.getByLabelText("Expediente del Convenio*"), { target: { value: "EC-9" } });
    const formElement = screen.getByRole("button", { name: "Guardar" }).closest("form")!;
    fireEvent.submit(formElement);
    fireEvent.submit(formElement);
    release({ data: { ok: true, redirect: `${BASE}7/` }, status: 200 });
    await waitFor(() => expect(assign).toHaveBeenCalledWith(`${BASE}7/`));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [endpoint, body] = webPost.mock.calls[0];
    expect(endpoint).toBe(`${API}comedores/7/crear/`);
    const sent = body as URLSearchParams;
    expect([...sent.keys()]).toEqual(NAMES);
    expect(sent.get("expediente_convenio")).toBe("EC-9");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe(`${BASE}7/`);
  });

  it("resets the create form after a 400, like the native empty re-render", async () => {
    serve(form());
    webPost.mockRejectedValue({ response: { status: 400, data: form({ errors: { ano: [{ message: "x" }] }, reset_form: true }) } });
    setup(`${BASE}7/nuevo/`);
    const convenio = await screen.findByLabelText("Expediente del Convenio*");
    fireEvent.change(convenio, { target: { value: "EC-9" } });
    fireEvent.submit(convenio.closest("form")!);
    await waitFor(() => expect((screen.getByLabelText("Expediente del Convenio*") as HTMLInputElement).value).toBe(""));
    expect(document.querySelector(".invalid-feedback")).toBeNull();
    expect(document.activeElement).toBe(document.body);
    expect(assign).not.toHaveBeenCalled();
  });

  it("paints the edit errors returned with the bound form", async () => {
    serve(form({ fields: fields({ ano: "2026" }) }));
    webPost.mockRejectedValue({ response: { status: 400, data: form({ fields: fields({ ano: "20261" }, { ano: ["Asegúrese de que este valor tenga como máximo 4 caracteres (tiene 5)."] }) }) } });
    setup(`${BASE}3/editar/`);
    const ano = await screen.findByLabelText("Año");
    expect((ano as HTMLInputElement).value).toBe("2026");
    expect(screen.getByRole("heading", { level: 1, name: "Editar Expediente de Pago" })).toBeTruthy();
    fireEvent.submit(ano.closest("form")!);
    await waitFor(() => expect(document.getElementById("error_1_id_ano")?.textContent).toBe("Asegúrese de que este valor tenga como máximo 4 caracteres (tiene 5)."));
    const bound = screen.getByLabelText("Año") as HTMLInputElement;
    expect(bound.value).toBe("20261");
    expect(bound.className).toContain("is-invalid");
    expect(bound.getAttribute("aria-describedby")).toBe("id_ano_error");
    expect(webPost).toHaveBeenCalledWith(`${API}3/editar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("confirms the logical delete with the native texts and follows the redirect", async () => {
    serve({
      id: 3, expediente_pago: "EP-1", breadcrumb_label: "ep-1", message: "¿Estás seguro que deseas dar de baja lógica el expediente",
      cascade_preview: { total_afectados: 1, total_baja_logica: 1, total_borrado_fisico: 0, desglose_por_modelo: [{ modelo: "Expedientes De Pago", cantidad: 1, modo: "baja_logica", ejemplos: ["ExpedientePago object (3) (ID 3)"] }] },
      cancel_url: `${BASE}3/detalle/`,
    });
    webPost.mockResolvedValue({ data: { ok: true, message: "Expediente dado de baja correctamente.", redirect: "/acompanamientos/acompanamiento/" }, status: 200 });
    setup(`${BASE}3/eliminar/`);
    await screen.findByText("Dar de baja Expediente");
    await waitFor(() => expect(document.title).toBe("SISOC - Acciones"));
    expect(screen.getByText(/dar de baja lógica el expediente/).textContent).toBe("¿Estás seguro que deseas dar de baja lógica el expediente EP-1?");
    expect(screen.getByText("Total de registros afectados:")).toBeTruthy();
    expect(screen.getByText("Baja lógica")).toBeTruthy();
    expect(screen.getByRole("link", { name: "ep-1" }).getAttribute("href")).toBe(`${BASE}3/detalle/`);
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe(`${BASE}3/detalle/`);
    fireEvent.click(screen.getByRole("button", { name: "Dar de baja" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/acompanamientos/acompanamiento/"));
    expect(webPost).toHaveBeenCalledWith(`${API}3/eliminar/`, expect.any(URLSearchParams), expect.anything());
  });

  it("reports an unconfirmed write without resending", async () => {
    serve(form());
    webPost.mockRejectedValue({ response: { status: 504, data: { uncertain: true } } });
    setup(`${BASE}3/editar/`);
    const convenio = await screen.findByLabelText("Expediente del Convenio*");
    fireEvent.change(convenio, { target: { value: "EC" } });
    fireEvent.submit(convenio.closest("form")!);
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    fireEvent.submit(convenio.closest("form")!);
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    expect(assign).not.toHaveBeenCalled();
  });

  it("shows the access screen on a 403 and a load error on network failure or bad shape", async () => {
    serve({ detail: "No tiene permisos." }, 403);
    setup(`${BASE}3/editar/`);
    await waitFor(() => expect(document.title).toBe("SISOC - Error 403"));
    cleanup();
    serve({ results: "x" });
    setup(`${BASE}7/`);
    expect(await screen.findByRole("alert")).toBeTruthy();
    cleanup();
    webGet.mockRejectedValue(new Error("network"));
    setup(`${BASE}3/detalle/`);
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar la página.");
  });
});
