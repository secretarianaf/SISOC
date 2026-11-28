import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { comedorConvenioNavigation, formatMonto, payloadValid, type ConvenioField } from "./comedorConvenio";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const PATH = "/comedores/7/convenio-pnud/";
const API = "web/comedores/comedores/7/convenio-pnud/";
const DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"];
const COMIDAS = ["desayuno", "almuerzo", "merienda", "merienda_reforzada", "cena"];

const field = (name: string, label: string, over: Partial<ConvenioField> = {}): ConvenioField => ({
  name, label, type: "number", required: false, help: "", value: "", monto: false, errors: [], attrs: { min: "0" }, ...over,
});
const montos = () => [
  field("nro_convenio", "Número de Convenio", { type: "text", value: "CV-1", attrs: { maxlength: "120" } }),
  field("monto_convenio_prestaciones_alimentarias", "Monto total del Convenio por Espacio - Prestaciones Alimentarias", { type: "text", monto: true, value: "1.235", attrs: { inputmode: "numeric" } }),
  field("monto_convenio_siph", "Monto total del Convenio por Espacio - Servicio Integral de Promoción Humana", { type: "text", monto: true, attrs: { inputmode: "numeric" } }),
];
const matriz = (reforzada: boolean) => DIAS.flatMap((d) => COMIDAS.filter((c) => reforzada || c !== "merienda_reforzada")
  .map((c) => field(`aprobadas_${c}_${d}`, `Aprobadas ${c} ${d}`, { required: true, value: "0" })));
const form = (variante: "resto" | "secos" | "tradicional", over: Record<string, unknown> = {}) => ({
  comedor_id: 7,
  prefill: { organizacion_solicitante: "Org Norte", codigo_proyecto: "PRY-7", estado_general: "Activo", subestado: "En ejecución", nombre_espacio: "Comedor Norte", id_externo: "EXT-1", domicilio_completo: "Sin información" },
  territoriales: [{ territorial: "Pérez, Ana (ana)", codigo: "PRY-7" }],
  es_linea_secos: variante === "secos", es_linea_tradicional: variante === "tradicional",
  fields: [
    ...montos(),
    ...(variante === "resto" ? [field("prestaciones_financiadas_mensuales", "Prestaciones financiadas mensuales")] : []),
    ...(variante === "tradicional" ? COMIDAS.map((c) => field(`prestaciones_financiadas_diarias_${c}`, `Prestaciones Financiadas Diarias - ${c}`)) : []),
    field("personas_conveniadas", "Personas Conveniadas"),
    ...(variante === "resto" ? [] : [field("personas_identidad_reservada", "Cantidad de personas con identidad reservada", { value: "2" })]),
    ...(variante === "tradicional" ? [] : [field("cantidad_modulos", "Cantidad de Módulos Mensuales")]),
    field("personas_declaradas_siph", "Total de personas declaradas en Servicio Integral de Promoción Humana"),
    ...(variante === "secos" ? [] : matriz(variante === "tradicional")),
  ],
  non_field_errors: [], urls: { ficha: "/comedores/7" }, ...over,
});
const payload = (variante: "resto" | "secos" | "tradicional" = "resto") => ({ form: form(variante), messages: [] });

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
let assign: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  assign = vi.spyOn(comedorConvenioNavigation, "assign").mockImplementation(() => undefined);
  window.history.replaceState({}, "", PATH);
});
afterEach(() => { cleanup(); assign.mockRestore(); });

describe("Comedor convenio PNUD route (CO07.03)", () => {
  it("owns only the native convenio URL", () => {
    expect(findRoute(PATH)?.route.name).toBe("comedores-convenio-pnud");
    for (const other of ["/comedores/7/convenio-pnud", "/comedores/7/", "/comedores/7/editar"]) expect(findRoute(other)?.route.name).not.toBe("comedores-convenio-pnud");
  });

  it("validates the payload and formats a monto like convenio_pnud.js", () => {
    expect(payloadValid(payload())).toBe(true);
    expect(payloadValid({ form: { ...form("resto"), urls: { ficha: "https://externo.example/" } }, messages: [] })).toBe(false);
    expect(formatMonto("100000000")).toBe("100.000.000");
    expect(formatMonto("1.000")).toBe("1.000");
    expect(formatMonto("1000,5")).toBe("1000,5");
    expect(formatMonto("12.34")).toBe("12.34");
  });

  it("shows the prefill, territoriales and the resto layout with the matrix without Merienda Reforzada", async () => {
    serve(payload());
    render(<App />);
    expect(await screen.findByText("Datos del Convenio", { selector: ".section-title" })).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Datos del Convenio"));
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    expect(screen.getByText("Organización solicitante").parentElement?.textContent).toBe("Organización solicitanteOrg Norte");
    expect(screen.getByText("Pérez, Ana (ana) — Código de Proyecto: PRY-7")).toBeTruthy();
    expect(screen.getByText("Prestaciones por convenio", { selector: ".section-title" })).toBeTruthy();
    expect([...document.querySelectorAll("thead th")].map((c) => c.textContent)).toEqual(["Día", "Desayuno", "Almuerzo", "Merienda", "Cena"]);
    expect(document.querySelectorAll("tbody input").length).toBe(28);
    expect((screen.getByLabelText("Monto total del Convenio por Espacio - Prestaciones Alimentarias") as HTMLInputElement).value).toBe("1.235");
    expect(screen.getByLabelText("Prestaciones financiadas mensuales")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Guardar convenio" })).toBeTruthy();
  });

  it("secos has no matrix and tradicional adds the daily prestaciones and Merienda Reforzada", async () => {
    serve(payload("secos"));
    const first = render(<App />);
    expect(await screen.findByText("Datos del Convenio", { selector: ".section-title" })).toBeTruthy();
    expect(screen.queryByText("Prestaciones por convenio", { selector: ".section-title" })).toBeNull();
    expect(screen.queryByLabelText("Prestaciones financiadas mensuales")).toBeNull();
    first.unmount();
    serve(payload("tradicional"));
    render(<App />);
    await waitFor(() => expect([...document.querySelectorAll("thead th")].map((c) => c.textContent)).toEqual(["Día", "Desayuno", "Almuerzo", "Merienda", "Merienda Reforzada", "Cena"]));
    expect(document.querySelectorAll("tbody input").length).toBe(35);
    expect(screen.getByLabelText("Prestaciones Financiadas Diarias - desayuno")).toBeTruthy();
    expect(screen.queryByLabelText("Cantidad de Módulos Mensuales")).toBeNull();
  });

  it("identidad reservada is editable and posted in secos and tradicional, absent in the rest (#2917)", async () => {
    serve(payload());
    const resto = render(<App />);
    expect(await screen.findByLabelText("Personas Conveniadas")).toBeTruthy();
    expect(screen.queryByLabelText("Cantidad de personas con identidad reservada")).toBeNull();
    expect(screen.queryByText(/Se descuenta de las Personas Conveniadas/)).toBeNull();
    resto.unmount();
    for (const variante of ["secos", "tradicional"] as const) {
      serve(payload(variante));
      webPost.mockResolvedValue({ status: 200, data: { redirect: "/comedores/7" } });
      const vista = render(<App />);
      const campo = (await screen.findByLabelText("Cantidad de personas con identidad reservada")) as HTMLInputElement;
      expect(campo.value).toBe("2");
      expect(screen.getByText(/Se descuenta de las Personas Conveniadas/)).toBeTruthy();
      fireEvent.change(campo, { target: { value: "5" } });
      fireEvent.click(screen.getByRole("button", { name: "Guardar convenio" }));
      await waitFor(() => expect(webPost).toHaveBeenCalled());
      expect((webPost.mock.calls.at(-1)![1] as URLSearchParams).get("personas_identidad_reservada")).toBe("5");
      vista.unmount();
      webPost.mockClear();
    }
  });

  it("formats the monto on blur and posts only the variant's fields", async () => {
    serve(payload());
    webPost.mockResolvedValue({ status: 200, data: { redirect: "/comedores/7" } });
    render(<App />);
    const monto = (await screen.findByLabelText("Monto total del Convenio por Espacio - Prestaciones Alimentarias")) as HTMLInputElement;
    fireEvent.change(monto, { target: { value: "100000000" } });
    fireEvent.blur(monto);
    expect(monto.value).toBe("100.000.000");
    fireEvent.change(screen.getByLabelText("Personas Conveniadas"), { target: { value: "30" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar convenio" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/7"));
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(API);
    const posted = body as URLSearchParams;
    expect([...posted.keys()].sort()).toEqual(form("resto").fields.map((f) => f.name).sort());
    expect(posted.get("monto_convenio_prestaciones_alimentarias")).toBe("100.000.000");
    expect(posted.get("personas_conveniadas")).toBe("30");
    expect(posted.has("prestaciones_financiadas_diarias_cena")).toBe(false);
  });

  it("a rejected POST shows the native errors, keeps the typed values and does not navigate", async () => {
    serve(payload());
    const rechazado = form("resto");
    rechazado.fields[1] = { ...rechazado.fields[1], value: "1000,5", errors: ["Ingresá un monto sin decimales, por ejemplo 100.000.000."] };
    const celda = rechazado.fields.findIndex((f) => f.name === "aprobadas_cena_lunes");
    rechazado.fields[celda] = { ...rechazado.fields[celda], errors: ["Asegúrese de que este valor es mayor o igual a 0."] };
    webPost.mockRejectedValue({ response: { status: 400 } });
    webPost.mockResolvedValueOnce({ status: 400, data: { errors: {}, non_field_errors: [], form: rechazado } });
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Guardar convenio" }));
    expect(await screen.findByText("Ingresá un monto sin decimales, por ejemplo 100.000.000.")).toBeTruthy();
    expect((screen.getByLabelText("Monto total del Convenio por Espacio - Prestaciones Alimentarias") as HTMLInputElement).value).toBe("1000,5");
    expect(screen.getByText("Ingresá un monto sin decimales, por ejemplo 100.000.000.").className).toBe("invalid-feedback d-block");
    expect(document.querySelector(".errorlist li")?.textContent).toBe("Asegúrese de que este valor es mayor o igual a 0.");
    expect(assign).not.toHaveBeenCalled();
    expect(scroll).toHaveBeenCalledWith(0, 0);
    scroll.mockRestore();
  });

  it("keeps an invalid monto as typed and blocks non-numeric keys in the quantity fields like convenio_pnud.js", async () => {
    serve(payload());
    render(<App />);
    const monto = (await screen.findByLabelText("Monto total del Convenio por Espacio - Prestaciones Alimentarias")) as HTMLInputElement;
    fireEvent.change(monto, { target: { value: "1000,5" } });
    fireEvent.blur(monto);
    expect(monto.value).toBe("1000,5");
    const personas = screen.getByLabelText("Personas Conveniadas");
    expect(fireEvent.keyDown(personas, { key: "e" })).toBe(false);
    expect(fireEvent.keyDown(personas, { key: "7" })).toBe(true);
  });

  it("the native refusal redirect (not PNUD/Abordaje) leaves for the ficha", async () => {
    serve({ redirect: "/comedores/7" });
    render(<App />);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/7"));
  });

  it("an uncertain POST asks to reload and disables saving", async () => {
    serve(payload());
    webPost.mockRejectedValue(new Error("network"));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Guardar convenio" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Guardar convenio" }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(assign).not.toHaveBeenCalled();
  });

  it("shows the access screen on a 403", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "Usted no tiene permiso para realizar esta acción." }, status: 403 }));
    render(<App />);
    await waitFor(() => expect(screen.queryByText("Datos del Convenio", { selector: ".section-title" })).toBeNull());
    expect(webPost).not.toHaveBeenCalled();
  });
});
