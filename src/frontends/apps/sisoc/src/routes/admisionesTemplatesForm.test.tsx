import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { templatesFormNavigation } from "./admisionesTemplatesForm";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const BASE = "/comedores/configuracion/templates/";
const API = "web/comedores/admisiones/plantillas-informe/crear/";
const nav = { templates: BASE, variables: `${BASE}variables/`, incidencias: `${BASE}incidencias/` };
const choice = (value: string, label: string) => ({ value, label });
const yesNo = [choice("", "---------"), choice("si", "Sí"), choice("no", "No")];
const form = (over: Record<string, unknown> = {}, values: Record<string, string> = {}) => ({
  fields: [
    { name: "nombre", required: true, value: "", max_length: 255 },
    { name: "descripcion", required: false, value: "" },
    { name: "tipo_admision", required: true, value: "incorporacion", choices: [choice("incorporacion", "Incorporación"), choice("renovacion", "Renovación")] },
    { name: "tipo_convenio", required: true, value: "", choices: [choice("", "Seleccione un tipo de convenio"), choice("3", "Asociación de hecho")] },
    { name: "es_ex_pnud", required: false, value: "", choices: yesNo },
    { name: "estado_convenio_pnud", required: false, value: "", choices: [choice("", "---------"), choice("vigente", "Vigente")] },
    { name: "tipo_renovacion", required: false, value: "", choices: [choice("", "---------"), choice("primera", "Primera renovación")] },
    { name: "estado_financiamiento", required: false, value: "", choices: [choice("", "---------"), choice("finalizado", "Finalizado")] },
    { name: "informe_complementario_modifica_prestaciones", required: false, value: "", choices: yesNo },
  ].map((f) => ({ ...f, value: values[f.name] ?? f.value })),
  errors: {}, non_field_errors: [], urls: { ...nav, cancelar: BASE }, messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
async function setup(data: unknown = form()) {
  serve(data);
  window.history.replaceState({}, "", `${BASE}crear/`);
  render(<App />);
  await screen.findByText("Definir una combinación");
}
const box = (label: string | RegExp) => screen.getByLabelText(label) as HTMLInputElement | HTMLSelectElement;

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => cleanup());

describe("Template create form (AD01.02)", () => {
  it("owns only the create URL, with its trailing slash", () => {
    expect(findRoute(`${BASE}crear/`)?.route.name).toBe("comedores-gestor-templates-form");
    for (const other of [`${BASE}crear`, `${BASE}crear/x/`, `${BASE}1/versiones/crear/`]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-gestor-templates-form");
    }
  });

  it("renders the native form, the help aside and the title", async () => {
    await setup();
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    await waitFor(() => expect(document.title).toContain("Crear template"));
    expect(await screen.findByRole("heading", { name: "Nueva plantilla lógica" }, { timeout: 4000 })).toBeTruthy();
    expect(await screen.findByRole("heading", { name: /Antes de crear/ }, { timeout: 4000 })).toBeTruthy();
    expect(screen.getByText(/Esta condición toma el tipo de convenio registrado/)).toBeTruthy();
    expect((box("Nombre") as HTMLInputElement).maxLength).toBe(255);
    expect(box("Nombre").required).toBe(true);
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe(BASE);
    expect(screen.getByRole("link", { name: "Gestor de templates", hidden: true })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Crear borrador" })).toBeTruthy();
  });

  it("shows the block of the chosen type, requires its fields and clears the PNUD state", async () => {
    await setup();
    const incorporacion = document.getElementById("condicionesIncorporacion")!;
    const renovacion = document.getElementById("condicionesRenovacion")!;
    const pnud = document.getElementById("estadoPnudContainer")!;
    expect([incorporacion.hidden, renovacion.hidden, pnud.hidden]).toEqual([false, true, true]);
    expect(box("¿Es Ex PNUD?").required).toBe(true);
    expect(box("Renovación que tramita").required).toBe(false);

    fireEvent.change(box("¿Es Ex PNUD?"), { target: { value: "si" } });
    expect(pnud.hidden).toBe(false);
    expect(box("Estado del convenio PNUD").required).toBe(true);
    fireEvent.change(box("Estado del convenio PNUD"), { target: { value: "vigente" } });
    fireEvent.change(box("¿Es Ex PNUD?"), { target: { value: "no" } });
    expect(pnud.hidden).toBe(true);
    expect(box("Estado del convenio PNUD").value).toBe("");

    fireEvent.change(box("Tipo de admisión"), { target: { value: "renovacion" } });
    expect([incorporacion.hidden, renovacion.hidden]).toEqual([true, false]);
    expect(box("¿Es Ex PNUD?").required).toBe(false);
    expect(box("Renovación que tramita").required).toBe(true);
    expect(box("Estado del financiamiento").required).toBe(true);
    expect(box(/Informe Técnico Complementario/).required).toBe(true);
  });

  it("posts the native fields once and follows the confirmed redirect", async () => {
    const assign = vi.spyOn(templatesFormNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: `${BASE}7/` } });
    await setup();
    fireEvent.change(box("Nombre"), { target: { value: "Plantilla nueva" } });
    fireEvent.change(box("Descripción"), { target: { value: "Detalle" } });
    fireEvent.change(box("Tipo de convenio"), { target: { value: "3" } });
    fireEvent.change(box("¿Es Ex PNUD?"), { target: { value: "si" } });
    fireEvent.change(box("Estado del convenio PNUD"), { target: { value: "vigente" } });
    fireEvent.submit(screen.getByRole("button", { name: "Crear borrador" }).closest("form")!);
    fireEvent.submit(screen.getByRole("button", { name: "Crear borrador" }).closest("form")!);

    await waitFor(() => expect(assign).toHaveBeenCalledWith(`${BASE}7/`));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0] as [string, URLSearchParams];
    expect(url).toBe(API);
    expect(Object.fromEntries(body)).toEqual({
      nombre: "Plantilla nueva", descripcion: "Detalle", tipo_admision: "incorporacion", tipo_convenio: "3", es_ex_pnud: "si",
      estado_convenio_pnud: "vigente", tipo_renovacion: "", estado_financiamiento: "", informe_complementario_modifica_prestaciones: "",
    });
  });

  it("shows the native errors of a rejected form, keeps the values and scrolls to the top", async () => {
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    webPost.mockRejectedValue({
      response: {
        status: 400,
        data: form({
          errors: { nombre: ["Este campo es requerido."], es_ex_pnud: ["Debe indicar si la admisión es Ex PNUD."] },
          non_field_errors: ["Ya existe un template para esta combinación."],
        }, { descripcion: "Detalle", tipo_convenio: "3" }),
      },
    });
    await setup();
    fireEvent.submit(screen.getByRole("button", { name: "Crear borrador" }).closest("form")!);

    expect(await screen.findByText("Este campo es requerido.")).toBeTruthy();
    expect(screen.getByText("Debe indicar si la admisión es Ex PNUD.")).toBeTruthy();
    expect(within(document.querySelector(".alert-danger") as HTMLElement).getByText("Ya existe un template para esta combinación.")).toBeTruthy();
    expect(box("Descripción").value).toBe("Detalle");
    expect(box("Tipo de convenio").value).toBe("3");
    expect(scroll).toHaveBeenCalledWith(0, 0);
    expect((screen.getByRole("button", { name: "Crear borrador" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("never resends after an unconfirmed result", async () => {
    webPost.mockRejectedValue(new Error("network"));
    await setup();
    const submit = () => fireEvent.submit(screen.getByRole("button", { name: "Crear borrador" }).closest("form")!);
    submit();

    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    submit();
    expect(webPost).toHaveBeenCalledTimes(1);
    expect((screen.getByRole("button", { name: "Crear borrador" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("rejects a payload without the nine native fields", async () => {
    serve({ ...form(), fields: [] });
    window.history.replaceState({}, "", `${BASE}crear/`);
    render(<App />);
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});
