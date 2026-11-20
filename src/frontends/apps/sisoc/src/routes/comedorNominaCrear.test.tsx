import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { nominaCrearNavigation, nominaCrearValid } from "./comedorNominaCrear";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/nomina-crear/3/";
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, required: false, kind: "input", attrs: { type: "text", class: "textinput form-control" },
  help_text: "", errors: [], value: "", ...over,
});
const select = (name: string, choices: [string, string][], over: Record<string, unknown> = {}) =>
  field(name, { kind: "select", attrs: { class: "select form-select" }, choices: choices.map(([value, label]) => ({ value, label })), ...over });
const yesNo = (name: string) => select(name, [["", "---------"], ["Si", "Si"], ["No", "No"]]);
const payload = (over: Record<string, unknown> = {}) => ({
  comedor: { id: 3, nombre: "Comedor Sintético", url: "/comedores/3" }, query: "", cupo: null, has_activities: false, ciudadanos: [],
  show_form: false, renaper: false, mode: "con_dni",
  form_ciudadano: { fields: [field("apellido", { required: true, label: "Apellido" }), field("nombre", { required: true, label: "Nombre" })], non_field_errors: [] },
  form_sin_dni: { fields: [field("apellido", { required: true, label: "Apellido" }), select("motivo_sin_dni", [["", "---------"], ["otro", "Otro"]], { label: "Motivo sin dni" })], non_field_errors: [] },
  form_extra: { fields: [select("estado", [["activo", "Activo"], ["espera", "En espera"]], { required: true, label: "Estado" }), field("observaciones", { kind: "textarea", label: "Observaciones" })], non_field_errors: [] },
  modal_fields: [yesNo("modal-pertenece_comunidad_indigena"), yesNo("modal-en_situacion_de_calle"), yesNo("modal-persona_con_celiaquia")],
  estados: [{ value: "activo", label: "Activo" }, { value: "espera", label: "En espera" }], pnud: false, actividades: [], messages: [], ...over,
});
const persona = (over: Record<string, unknown> = {}) => ({
  id: 7, apellido: "Gómez", nombre: "Ana", documento: "30111222", tipo_registro: "ESTANDAR", revision: false,
  comunidad_indigena: "Si", situacion_calle: "", celiaquia: "", ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
function setup(url = "/comedores/3/nomina/crear/") {
  window.history.replaceState({}, "", url);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  // jsdom has no scrollIntoView; the creation card scrolls to itself in a frame callback.
  Element.prototype.scrollIntoView = vi.fn();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Comedor nómina crear", () => {
  it("owns the two native URLs (trailing slash) and validates its payload", () => {
    expect(findRoute("/comedores/3/nomina/crear/")?.route.name).toBe("comedor-nomina-crear");
    expect(findRoute("/comedores/3/admision/5/nomina/crear/")?.route.name).toBe("comedor-nomina-crear");
    expect(findRoute("/comedores/3/nomina/crear")?.route.name).not.toBe("comedor-nomina-crear");
    expect(findRoute("/comedores/3/nomina/")?.route.name).not.toBe("comedor-nomina-crear");
    expect(nominaCrearValid(payload())).toBe(true);
    expect(nominaCrearValid(payload({ comedor: { id: 3, nombre: "x", url: "https://x.example" } }))).toBe(false);
    expect(nominaCrearValid(payload({ ciudadanos: [{ id: "x" }] }))).toBe(false);
  });

  it("reads the search from the URL and renders the matches with the creation card hidden", async () => {
    serve(payload({ query: "301", ciudadanos: [persona(), persona({ id: 8, revision: true, tipo_registro: "SIN_DNI" })] }));
    setup("/comedores/3/nomina/crear/?query=301");
    expect(await screen.findByRole("heading", { name: "Agregar a Nómina" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}?query=301`, expect.anything());
    expect((screen.getByPlaceholderText("Ingrese DNI (mín 4 dígitos)") as HTMLInputElement).value).toBe("301");
    expect(screen.getAllByRole("button", { name: "Agregar" })).toHaveLength(1);
    expect((screen.getByRole("button", { name: "Revisión pendiente" }) as HTMLButtonElement).disabled).toBe(true);
    expect(document.getElementById("card-creacion-ciudadano")?.classList.contains("d-none")).toBe(true);
  });

  it("toggles the creation card and mode like the native script", async () => {
    serve(payload());
    setup();
    await screen.findByRole("heading", { name: "Agregar a Nómina" });
    const sinDni = document.getElementById("formulario-sin-dni") as HTMLElement;
    expect((sinDni.querySelector("input[name=apellido]") as HTMLInputElement).disabled).toBe(true);
    fireEvent.click(document.getElementById("btn-sin-dni") as HTMLElement);
    await waitFor(() => expect(document.getElementById("card-creacion-ciudadano")?.classList.contains("d-none")).toBe(false));
    expect(document.getElementById("titulo-creacion-ciudadano")?.textContent).toBe("Crear Ciudadano sin DNI");
    expect((sinDni.querySelector("input[name=apellido]") as HTMLInputElement).disabled).toBe(false);
    expect((document.getElementById("formulario-con-dni")?.querySelector("input[name=apellido]") as HTMLInputElement).disabled).toBe(true);
  });

  it("validates the estado of the modal and posts only the enabled controls once confirmed", async () => {
    serve(payload({ ciudadanos: [persona()] }));
    const assign = vi.spyOn(nominaCrearNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/comedores/3/nomina/" }, status: 200 });
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Agregar" }));
    expect((await screen.findByText("Ciudadano seleccionado: Gómez, Ana")).textContent).toBeTruthy();
    const modal = document.getElementById("form-nomina") as HTMLFormElement;
    fireEvent.submit(modal);
    expect(webPost).not.toHaveBeenCalled();
    expect(modal.classList.contains("was-validated")).toBe(true);
    expect((document.getElementById("estado") as HTMLSelectElement).classList.contains("is-invalid")).toBe(true);
    fireEvent.change(document.getElementById("estado") as HTMLSelectElement, { target: { value: "activo" } });
    fireEvent.submit(modal);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/3/nomina/"));
    const body = webPost.mock.calls[0][1] as URLSearchParams;
    expect(body.get("ciudadano_id")).toBe("7");
    expect(body.get("estado")).toBe("activo");
    expect(body.get("modal-pertenece_comunidad_indigena")).toBe("Si");
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("replaces the page with the bound forms after a rejected POST and keeps the native message", async () => {
    serve(payload());
    const rejected = payload({
      show_form: true, messages: [{ message: "Revise los datos marcados en el formulario.", tags: "warning" }],
      form_ciudadano: { fields: [field("apellido", { required: true, label: "Apellido", errors: ["Este campo es requerido."], attrs: { class: "textinput form-control is-invalid" } })], non_field_errors: [] },
    });
    webPost.mockResolvedValue({ data: rejected, status: 400 });
    setup();
    await screen.findByRole("heading", { name: "Agregar a Nómina" });
    const conDni = document.getElementById("formulario-con-dni") as HTMLElement;
    fireEvent.submit(conDni.querySelector("form") as HTMLFormElement);
    // The native page shows the message inline and as a toast.
    expect((await screen.findAllByText("Revise los datos marcados en el formulario.")).length).toBeGreaterThanOrEqual(1);
    expect(document.querySelector(".alert-warning")?.textContent).toContain("Revise los datos marcados");
    expect(screen.getByText("Este campo es requerido.")).toBeTruthy();
    expect(document.getElementById("card-creacion-ciudadano")?.classList.contains("d-none")).toBe(false);
  });

  it("reports an uncertain result without retrying", async () => {
    serve(payload());
    const assign = vi.spyOn(nominaCrearNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockRejectedValue(new Error("network"));
    setup();
    await screen.findByRole("heading", { name: "Agregar a Nómina" });
    fireEvent.submit((document.getElementById("formulario-con-dni") as HTMLElement).querySelector("form") as HTMLFormElement);
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudo confirmar el resultado");
    expect(assign).not.toHaveBeenCalled();
    expect(webPost).toHaveBeenCalledTimes(1);
  });
});
