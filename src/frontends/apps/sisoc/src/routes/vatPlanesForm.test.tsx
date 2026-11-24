import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { planFormValid } from "./vatPlanesForm";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/catalogos/planes-curriculares/";
const BASE = "/vat/catalogos/planes-curriculares/";
const s2 = { class: "form-control select2", "data-width": "100%" };
const field = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label, tag: "input", help_text: "", value: "", choices: [], errors: [], disabled: false, required: false,
  attrs: { class: "form-control", type: "text" }, ...over,
});
const sel = (name: string, label: string, rows: [string, string][], over: Record<string, unknown> = {}) => field(name, label, {
  tag: "select", attrs: { class: "form-control" }, choices: [{ value: "", label: "---------" }, ...rows.map(([value, text]) => ({ value, label: text }))], ...over,
});
const select2 = (name: string, label: string, rows: [string, string][], over: Record<string, unknown> = {}) => sel(name, label, rows, {
  required: true, attrs: { ...s2, "data-placeholder": `Seleccionar ${name}...`, required: "required" }, ...over,
});
const fields = (over: Record<string, Record<string, unknown>> = {}, withProvincia = true) => [
  ...(withProvincia ? [select2("provincia", "Provincia", [["1", "Buenos Aires"]], { help_text: "El plan estará disponible para crear cursos." })] : []),
  field("nombre", "Nombre", { required: true, attrs: { class: "form-control", type: "text", required: "required", placeholder: "Nombre del plan curricular" } }),
  select2("sector", "Sector", [["3", "Industria"]]),
  select2("subsector", "Subsector", [["4", "Electricidad"]], { required: false }),
  select2("modalidad_cursada", "Modalidad", [["6", "Presencial"]]),
  sel("normativa_tipo", "Normativa - Tipo", [["Resolución", "Resolución"]]),
  field("normativa_numero", "Normativa - Número", { attrs: { class: "form-control", type: "text", inputmode: "numeric" } }),
  sel("normativa_anio", "Normativa - Año", [["2020", "2020"]]),
  field("horas_reloj", "Horas Reloj", { attrs: { class: "form-control", type: "number" } }),
  sel("nivel_requerido", "Nivel Requerido", [["sin_requisito", "Sin requisito"]]),
  sel("nivel_certifica", "Nivel que Certifica", [["nivel_1", "Certificado Nivel I"]]),
  field("activo", "Activo", { value: true, attrs: { class: "form-check-input", type: "checkbox" } }),
].map((f) => ({ ...f, ...(over[f.name] ?? {}) }));
const form = (over: Record<string, unknown> = {}) => ({
  editing: false, fields: fields(), non_field_errors: [], normativa_actual: "", page: { page_title: "Nuevo Plan de Estudio", submit_text: "Crear plan" },
  urls: { list: BASE, cancel: BASE }, messages: [], ...over,
});
const edit = (over: Record<string, unknown> = {}) => form({
  editing: true, fields: fields({ nombre: { value: "Electricista" }, sector: { value: "3" } }, false),
  page: { page_title: "Editar Plan de Estudio", submit_text: "Guardar cambios" }, urls: { list: BASE, cancel: `${BASE}5/` }, ...over,
});

function serve(data: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
}
async function open(path: string) {
  window.history.replaceState({}, "", path);
  render(<App />);
  await screen.findByRole("heading", { level: 1 });
}
const body = () => new URLSearchParams(webPost.mock.calls.at(-1)![1] as URLSearchParams);

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT curricular plan form route", () => {
  it("owns the create and edit paths only", () => {
    for (const path of [`${BASE}nuevo/`, `${BASE}5/editar/`]) expect(findRoute(path)?.route.name).toBe("vat-planes-form");
    for (const other of [`${BASE}nuevo`, `${BASE}5/`, `${BASE}5/eliminar/`, `${BASE}x/editar/`, BASE, "/vat/catalogos/sectores/nuevo/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-planes-form");
    }
  });

  it("validates the payload shape", () => {
    expect(planFormValid(form())).toBe(true);
    expect(planFormValid(edit())).toBe(true);
    expect(planFormValid(form({ fields: [...fields()].reverse() }))).toBe(true);
    expect(planFormValid(form({ fields: fields({}, false) }))).toBe(false);
    expect(planFormValid(edit({ fields: fields() }))).toBe(false);
    expect(planFormValid(form({ urls: { list: BASE, cancel: "https://x.test/" } }))).toBe(false);
    expect(planFormValid(form({ normativa_actual: 3 }))).toBe(false);
    expect(planFormValid({ ...form(), page: { page_title: "x" } })).toBe(false);
  });

  it("draws the native form: hero, panels, crispy fields, columns, help text and the actions", async () => {
    serve(form());
    await open(`${BASE}nuevo/`);
    expect(webGet).toHaveBeenCalledWith(`${API}nuevo/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nuevo Plan de Estudio"));
    expect(screen.getByRole("heading", { level: 1, name: "Nuevo Plan de Estudio" }).parentElement?.className).toBe("vp-hero");
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(expect.arrayContaining(["1. Clasificación Académica", "2. Datos del Plan"]));
    expect(document.querySelector("label[for=id_nombre] .asteriskField")?.textContent).toBe("*");
    expect(document.querySelector("#id_nombre")?.className).toBe("form-control textinput");
    expect(document.querySelector("#id_normativa_tipo")?.className).toBe("form-control select form-select");
    expect(document.querySelector("#id_sector")?.className).toBe("form-control select2 form-select select2-hidden-accessible");
    expect(document.querySelector("#div_id_provincia")?.parentElement?.className).toBe("col-md-12 vp-field");
    expect(document.querySelector("#div_id_sector")?.parentElement?.className).toBe("col-md-4 vp-field");
    expect(document.querySelector("#div_id_horas_reloj")?.parentElement?.className).toBe("col-md-2 vp-field");
    expect(document.querySelector("#div_id_nivel_requerido")?.parentElement?.className).toBe("col-md-3 vp-field");
    expect(screen.getByText("El plan estará disponible para crear cursos.")).toBeTruthy();
    expect(screen.getByText("Solo se edita el formato estructurado con tipo, número y año.")).toBeTruthy();
    expect(screen.queryByText("Normativa libre cargada en base:")).toBeNull();
    const activo = document.querySelector("#id_activo") as HTMLInputElement;
    expect([activo.type, activo.checked, activo.className]).toEqual(["checkbox", true, "form-check-input checkboxinput"]);
    expect(screen.getByRole("link", { name: /Cancelar/ }).getAttribute("href")).toBe(BASE);
    expect(screen.getByRole("button", { name: /Crear plan/ })).toBeTruthy();
  });

  it("draws the edit form without province, with the free normativa notice and the native button text", async () => {
    serve(edit({ normativa_actual: "Res. 1/2020" }));
    await open(`${BASE}5/editar/`);
    expect(webGet).toHaveBeenCalledWith(`${API}5/editar/`, expect.anything());
    expect(document.querySelector("#id_provincia")).toBeNull();
    expect((document.querySelector("#id_nombre") as HTMLInputElement).value).toBe("Electricista");
    expect(screen.getByText("Normativa libre cargada en base:").parentElement?.className).toBe("alert alert-secondary mb-3");
    expect(screen.getByRole("link", { name: /Cancelar/ }).getAttribute("href")).toBe(`${BASE}5/`);
    expect(screen.getByRole("button", { name: /Guardar cambios/ })).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Editar Plan de Estudio"));
  });

  it("posts only the template fields and follows the native redirect", async () => {
    serve(form());
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: `${BASE}7/` } });
    await open(`${BASE}nuevo/`);
    fireEvent.change(document.querySelector("#id_nombre")!, { target: { value: "Plan nuevo" } });
    fireEvent.change(document.querySelector("#id_horas_reloj")!, { target: { value: "80" } });
    fireEvent.click(document.querySelector("#id_activo")!);
    fireEvent.click(screen.getByRole("button", { name: /Crear plan/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(`${BASE}7/`));
    expect(webPost.mock.calls[0][0]).toBe(`${API}nuevo/`);
    const enviado = body();
    expect(enviado.get("nombre")).toBe("Plan nuevo");
    expect(enviado.get("horas_reloj")).toBe("80");
    expect(enviado.has("activo")).toBe(false);
    expect([...enviado.keys()].sort()).toEqual(["horas_reloj", "modalidad_cursada", "nivel_certifica", "nivel_requerido", "nombre", "normativa_anio", "normativa_numero", "normativa_tipo", "provincia", "sector", "subsector"]);
  });

  it("shows the bound form after a rejected POST with field and non-field errors", async () => {
    serve(form());
    const rechazo = form({
      fields: fields({ nombre: { value: "x", errors: ["Este campo es obligatorio."] }, normativa_numero: { errors: ["Ingrese el número de la normativa."] } }),
      non_field_errors: ["No se pudo guardar el plan."],
    });
    webPost.mockRejectedValue({ response: { status: 400, data: rechazo } });
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    await open(`${BASE}nuevo/`);
    fireEvent.click(screen.getByRole("button", { name: /Crear plan/ }));
    expect(await screen.findByText("Este campo es obligatorio.")).toBeTruthy();
    expect(screen.getByText("Ingrese el número de la normativa.")).toBeTruthy();
    expect(screen.getByText("No se pudo guardar el plan.").closest("ul")?.className).toBe("errorlist nonfield");
    expect(document.querySelector("#id_nombre")?.className).toContain("is-invalid");
    expect((document.querySelector("#id_nombre") as HTMLInputElement).value).toBe("x");
    expect(scroll).toHaveBeenCalledWith(0, 0);
  });

  it("keeps the locked fields of the provincial role locked and sends a single request per submit", async () => {
    serve(edit({ fields: fields({ sector: { value: "3", disabled: true, attrs: { ...s2, disabled: "disabled" } }, subsector: { disabled: true, attrs: { type: "hidden" }, tag: "input", choices: [], value: "4" },
      activo: { disabled: true, attrs: { type: "hidden" }, tag: "input", value: "on" } }, false) }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: `${BASE}5/` } });
    vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    await open(`${BASE}5/editar/`);
    expect((document.querySelector("#id_subsector") as HTMLInputElement).type).toBe("hidden");
    expect((document.querySelector("#id_subsector") as HTMLInputElement).disabled).toBe(true);
    expect((document.querySelector("#id_activo") as HTMLInputElement).type).toBe("hidden");
    expect(document.querySelector("#id_sector + .select2-container")?.className).toContain("select2-container--disabled");
    const boton = screen.getByRole("button", { name: /Guardar cambios/ });
    fireEvent.click(boton);
    fireEvent.click(boton);
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
  });

  it("shows the queued messages as dismissible alerts and says so when the result is not confirmed", async () => {
    serve(form({ messages: [{ message: "Plan de estudio creado correctamente.", level: "success" }] }));
    await open(`${BASE}nuevo/`);
    const alerta = document.querySelector(".alert.alert-success") as HTMLElement;
    expect(alerta.textContent).toContain("Plan de estudio creado correctamente.");
    expect(alerta.className).toBe("alert alert-success alert-dismissible fade show");
    fireEvent.click(alerta.querySelector("button.btn-close")!);
    expect(document.querySelector(".alert.alert-success")).toBeNull();
    webPost.mockRejectedValue({ response: { status: 500, data: {} } });
    fireEvent.click(screen.getByRole("button", { name: /Crear plan/ }));
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});
