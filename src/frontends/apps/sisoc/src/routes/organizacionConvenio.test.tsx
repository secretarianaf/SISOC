import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { FLASH_KEY, organizacionesNavigation } from "./organizacionesForm";
import { convenioValid, formatCents } from "./organizacionConvenio";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/organizaciones/proyectos/5/convenio/";
const field = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, label, type: "text", required: true, help: "", value: "", options: null, errors: [] as string[], attrs: {}, ...over,
});
const monto = (name: string, label: string, value = "") => field(name, label, { type: "number", value, attrs: { step: "0.01", min: "0", inputmode: "decimal" } });
function convenio(over: Record<string, unknown> = {}, tradicional = false) {
  const components = ["componente_alimentario", "componente_gastos_generales", "componente_siph", "componente_gasto_bancario", ...(tradicional ? ["imprevistos"] : [])];
  return {
    project: { id: 5, code: "P-1" },
    organization: { id: 8, name: "Org <Sur>", cuit: "20111111112", region: "Sin información", subzone: "Sin información" },
    line: tradicional ? "Abordaje comunitario - Línea Tradicional" : "Abordaje comunitario - Línea Secos",
    is_tradicional: tradicional, exists: false, summary: null, urls: { cancel: "/organizaciones/detalle/8?programa=3" }, messages: [],
    form: {
      fields: [field("numero", "Número de convenio", { attrs: { maxlength: "50" } }), field("fecha", "Fecha de convenio", { type: "date" }),
        field("meses", "Meses de convenio", { type: "number" }), monto("monto_total", "Monto total"),
        ...components.map((c) => monto(c, c)), ],
      components, non_field_errors: [],
    },
    ...over,
  };
}
function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
const open = () => { window.history.replaceState({}, "", "/organizaciones/proyectos/5/convenio/"); return render(<App />); };

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.sessionStorage.clear();
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Organization convenio route", () => {
  it("owns only the native path of a numeric project id, with its trailing slash", () => {
    expect(findRoute("/organizaciones/proyectos/5/convenio/")?.route.name).toBe("comedores-organizaciones-convenio");
    for (const other of ["/organizaciones/proyectos/5/convenio", "/organizaciones/proyectos/0/convenio/", "/organizaciones/proyectos/x/convenio/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-organizaciones-convenio");
    }
  });

  it("renders the native header, data and form of a new Secos convenio", async () => {
    serve(convenio());
    open();
    expect(await screen.findByRole("heading", { level: 5, name: "Cargar datos del Convenio" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Datos del Convenio"));
    expect(screen.getByText("Abordaje Comunitario")).toBeTruthy();
    expect(screen.getByText("Org <Sur>")).toBeTruthy();
    expect(screen.getAllByText("Sin información")).toHaveLength(2);
    expect(screen.getByText("Imprevistos no aplica: es solo para Línea Tradicional.")).toBeTruthy();
    expect(screen.queryByLabelText(/imprevistos/)).toBeNull();
    expect(document.getElementById("convenio-suma")?.textContent).toBe("$0");
    expect(document.getElementById("convenio-suma-aviso")?.className).toContain("d-none");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/organizaciones/detalle/8?programa=3");
  });

  it("shows Editar and the Tradicional imprevistos field for an existing convenio", async () => {
    serve(convenio({ exists: true, summary: { suma: "$950", total: "$1.000", diferencia: "$50", coincide: false } }, true));
    open();
    expect(await screen.findByRole("heading", { level: 5, name: "Editar datos del Convenio" })).toBeTruthy();
    expect(screen.getByLabelText(/imprevistos/)).toBeTruthy();
    expect(screen.queryByText("Imprevistos no aplica: es solo para Línea Tradicional.")).toBeNull();
    expect(document.getElementById("convenio-diferencia")?.textContent).toBe("$50");
    expect(document.getElementById("convenio-suma-aviso")?.className).not.toContain("d-none");
  });

  it("adds up cents like the native script and flips the hint", async () => {
    serve(convenio());
    open();
    await screen.findByRole("heading", { level: 5, name: "Cargar datos del Convenio" });
    const type = (name: RegExp | string, value: string) => fireEvent.change(screen.getByLabelText(typeof name === "string" ? new RegExp(`^${name}`) : name), { target: { value } });
    type(/^Monto total/, "1000");
    type("componente_alimentario", "400.5");
    expect(document.getElementById("convenio-suma")?.textContent).toBe("$400,50");
    expect(document.getElementById("convenio-diferencia")?.textContent).toBe("$599,50");
    expect(document.getElementById("convenio-suma-aviso")?.className).not.toContain("d-none");
    type("componente_gastos_generales", "599.5");
    expect(document.getElementById("convenio-suma")?.textContent).toBe("$1.000");
    expect(document.getElementById("convenio-suma-ok")?.className).not.toContain("d-none");
    expect(document.getElementById("convenio-suma-aviso")?.className).toContain("d-none");
    expect(formatCents(-123456)).toBe("-$1.234,56");
  });

  it("posts the fields once, keeps the Django messages for the legajo and navigates", async () => {
    serve(convenio());
    const go = vi.spyOn(organizacionesNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { redirect: "/organizaciones/detalle/8?programa=3", messages: [{ message: "Datos de convenio guardados.", level: "success" }] } });
    open();
    await screen.findByRole("heading", { level: 5, name: "Cargar datos del Convenio" });
    fireEvent.change(screen.getByLabelText(/^Número de convenio/), { target: { value: "CV-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(go).toHaveBeenCalledWith("/organizaciones/detalle/8?programa=3"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(API);
    expect((body as URLSearchParams).get("numero")).toBe("CV-1");
    expect((body as URLSearchParams).get("monto_total")).toBe("");
    expect(JSON.parse(window.sessionStorage.getItem(FLASH_KEY) ?? "[]")[0].message).toBe("Datos de convenio guardados.");
  });

  it("re-renders the bound form with the Django errors on 400", async () => {
    serve(convenio());
    const bound = convenio();
    bound.form.fields[0] = { ...bound.form.fields[0], errors: ["Este campo es requerido."] };
    webPost.mockResolvedValue({ status: 400, data: { errors: {}, ...bound } });
    open();
    await screen.findByRole("heading", { level: 5, name: "Cargar datos del Convenio" });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Este campo es requerido.")).toBeTruthy();
  });

  it("cannot render the 409 of a project without line: the native entry redirects before the page loads", async () => {
    serve({ error: "x", redirect: "/organizaciones/editar/8", messages: [{ message: "Asigná una línea al proyecto P-1 antes de cargar el convenio.", level: "error" }] }, 409);
    open();
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(convenioValid({ error: "x" })).toBe(false);
  });

  it("shows the access screen on 403 and an error on 404", async () => {
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    open();
    await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
    expect(screen.queryByRole("heading", { level: 5 })).toBeNull();
    cleanup();
    serve({ detail: "No encontrado." }, 404);
    open();
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(within(document.body).queryByText("Org <Sur>")).toBeNull();
  });
});
