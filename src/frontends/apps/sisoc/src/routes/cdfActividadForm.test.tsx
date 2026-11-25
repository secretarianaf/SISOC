import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { actividadesLoader, timePicker } from "./cdfActividadForm";
import { navigation } from "./cdfFrame";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const CREATE = "web/cdf/centros/4/actividades/nueva/";
const EDIT = "web/cdf/actividades/9/editar/";
const campo = (name: string, label: string, over: Record<string, unknown> = {}) => ({
  name, label, required: true, disabled: false, widget: "number", help_text: "", value: "", attrs: {}, html: { class: "form-control" }, ...over,
});
const formulario = (over: Record<string, unknown> = {}) => ({
  centro: { id: 4, nombre: "CDF Cuatro", tipo: "adherido" },
  fields: [
    campo("categoria", "Categoría", { required: false, widget: "select", choices: [{ value: "", label: "Seleccione una categoría" }, { value: "3", label: "Deportes" }] }),
    campo("actividad", "Actividad", { widget: "select", html: {}, choices: [{ value: "", label: "---------" }] }),
    campo("cantidad_personas", "Cantidad Estimada de Participantes", { attrs: { min: "0" } }),
    campo("sexoact", "Actividad dirigida a...", { required: false, widget: "selectmultiple", value: [], html: { class: "select2 w-100" }, choices: [{ value: "1", label: "Mujer" }, { value: "2", label: "Varon" }] }),
    campo("dias", "Días", { required: false, widget: "selectmultiple", value: ["5"], html: { class: "select2 w-100" }, choices: [{ value: "5", label: "Lunes" }, { value: "6", label: "Martes" }] }),
    campo("horariosdesde", "Hora Desde", { widget: "text", value: "09:00:00", html: { class: "form-control timepicker", placeholder: "Seleccione una hora" } }),
    campo("horarioshasta", "Hora Hasta", { widget: "text", html: { class: "form-control timepicker", placeholder: "Seleccione una hora" } }),
    campo("precio", "PrecioActividad", { required: false }),
    campo("estado", "Estado", { widget: "select", value: "planificada", choices: [{ value: "planificada", label: "Planificada" }, { value: "en_curso", label: "En curso" }] }),
  ],
  errors: {}, non_field_errors: [], messages: [], ...over,
});

function serve(page: unknown, api = CREATE) {
  webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
    : url === api ? Promise.resolve({ data: page, status: 200 }) : Promise.reject(new Error(url))));
}
function setup(path = "/centrodefamilia/centros/4/actividades/nueva/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const input = (id: string) => document.getElementById(id) as HTMLInputElement;

let destroy: ReturnType<typeof vi.fn>;
let attach: ReturnType<typeof vi.fn>;
beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  destroy = vi.fn();
  attach = vi.fn(() => ({ destroy }));
  vi.spyOn(timePicker, "load").mockResolvedValue(attach as never);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CDF centre activity form route", () => {
  it("owns only the native create and edit paths", () => {
    expect(findRoute("/centrodefamilia/centros/4/actividades/nueva/")?.params).toEqual({ centro: "4" });
    expect(findRoute("/centrodefamilia/centros/actividades/9/editar/")?.params).toEqual({ id: "9" });
    expect(findRoute("/centrodefamilia/centros/actividades/9/editar/")?.route.name).toBe("cdf-actividad-form");
    expect(findRoute("/centrodefamilia/centros/4/actividades/")?.route.name).not.toBe("cdf-actividad-form");
  });

  it("renders the crispy fields with the native classes, no title and no cancel button", async () => {
    serve(formulario());
    setup();
    await screen.findByRole("button", { name: "Guardar" });
    await waitFor(() => expect(document.title).toBe("SISOC - Nueva Actividad"));
    expect(document.querySelector(".card h2")).toBeNull();
    expect(screen.queryByRole("link", { name: "Cancelar" })).toBeNull();
    expect(document.querySelector("label[for=id_cantidad_personas]")?.textContent).toBe("Cantidad Estimada de Participantes*");
    expect(input("id_cantidad_personas").getAttribute("min")).toBe("0");
    expect(input("id_horariosdesde").placeholder).toBe("Seleccione una hora");
    expect(input("id_horariosdesde").value).toBe("09:00:00");
    expect(input("id_categoria").className).toContain("form-control");
    expect(input("id_categoria").closest("form")?.getAttribute("enctype")).toBe("multipart/form-data");
    expect(document.querySelectorAll("select[multiple]").length).toBe(2);
    expect(document.querySelector(".select2-selection__choice")?.textContent).toContain("Lunes");
  });

  it("attaches the 24 h time pickers to both hour inputs and destroys them on leaving", async () => {
    serve(formulario());
    setup();
    await screen.findByRole("button", { name: "Guardar" });
    await waitFor(() => expect(attach).toHaveBeenCalledTimes(2));
    expect(attach.mock.calls.map((c) => (c[0] as HTMLElement).id)).toEqual(["id_horariosdesde", "id_horarioshasta"]);
    expect(attach.mock.calls[0][1]).toEqual({ enableTime: true, noCalendar: true, dateFormat: "H:i", time_24hr: true });
    cleanup();
    expect(destroy).toHaveBeenCalledTimes(2);
  });

  it("reloads the dependent activities when the category changes like centro_familia_categoria.js", async () => {
    serve(formulario());
    const load = vi.spyOn(actividadesLoader, "load").mockResolvedValue([{ id: 7, nombre: "Futbol" }]);
    setup();
    await screen.findByRole("button", { name: "Guardar" });
    fireEvent.change(input("id_categoria"), { target: { value: "3" } });
    expect(load).toHaveBeenCalledWith("/ajax/actividades/?categoria_id=3");
    expect([...(input("id_actividad") as unknown as HTMLSelectElement).options].map((o) => o.textContent)).toEqual(["Cargando..."]);
    await waitFor(() => expect([...(input("id_actividad") as unknown as HTMLSelectElement).options].map((o) => o.textContent)).toEqual(["Seleccione una actividad", "Futbol"]));
    expect(webGet).toHaveBeenCalledTimes(2);
  });

  it("posts once with every native field (including the multiple selects) and follows the redirect", async () => {
    serve(formulario());
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    vi.spyOn(actividadesLoader, "load").mockResolvedValue([{ id: 7, nombre: "Futbol" }]);
    webPost.mockResolvedValue({ status: 200, data: { url: "/centrodefamilia/centros/4/", message: "La actividad fue creada correctamente.", level: "success" } });
    setup();
    await screen.findByRole("button", { name: "Guardar" });
    fireEvent.change(input("id_categoria"), { target: { value: "3" } });
    await waitFor(() => expect((input("id_actividad") as unknown as HTMLSelectElement).options.length).toBe(2));
    fireEvent.change(input("id_actividad"), { target: { value: "7" } });
    fireEvent.change(input("id_cantidad_personas"), { target: { value: "12" } });
    fireEvent.change(input("id_horarioshasta"), { target: { value: "10:30" } });
    const boton = screen.getByRole("button", { name: "Guardar" });
    fireEvent.click(boton);
    fireEvent.click(boton);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodefamilia/centros/4/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    const data = body as FormData;
    expect(url).toBe(CREATE);
    expect(data.get("csrfmiddlewaretoken")).toBe("synthetic-csrf-token");
    expect([data.get("categoria"), data.get("actividad"), data.get("cantidad_personas")]).toEqual(["3", "7", "12"]);
    expect(data.getAll("dias")).toEqual(["5"]);
    expect([data.get("horariosdesde"), data.get("horarioshasta"), data.get("estado")]).toEqual(["09:00:00", "10:30", "planificada"]);
  });

  it("shows the errors of a 400, the crispy non-field block and keeps the typed values", async () => {
    serve(formulario());
    webPost.mockResolvedValueOnce({ status: 400, data: formulario({
      fields: formulario().fields.map((f) => (f.name === "cantidad_personas" ? { ...f, value: "-3" } : f)),
      errors: { cantidad_personas: [{ message: "Asegúrese de que este valor es mayor o igual a 0.", code: "min_value" }] },
      non_field_errors: ["Un centro de tipo FARO no debe tener un precio asignado."],
    }) });
    setup();
    await screen.findByRole("button", { name: "Guardar" });
    fireEvent.change(input("id_cantidad_personas"), { target: { value: "3" } });
    fireEvent.change(input("id_horarioshasta"), { target: { value: "10:30" } });
    const actividad = input("id_actividad") as unknown as HTMLSelectElement;
    actividad.required = false;
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(document.getElementById("error_1_id_cantidad_personas")?.textContent).toBe("Asegúrese de que este valor es mayor o igual a 0."));
    expect(input("id_cantidad_personas").className).toContain("is-invalid");
    expect(input("id_cantidad_personas").value).toBe("-3");
    expect(document.querySelector(".alert-block.alert-danger li")?.textContent).toBe("Un centro de tipo FARO no debe tener un precio asignado.");
    expect((screen.getByRole("button", { name: "Guardar" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("renders the hidden price of a FARO centre as a hidden input", async () => {
    serve(formulario({ fields: formulario().fields.map((f) => (f.name === "precio" ? { ...f, widget: "hidden", required: false } : f)) }));
    setup();
    await screen.findByRole("button", { name: "Guardar" });
    expect(input("id_precio").type).toBe("hidden");
    expect(document.getElementById("div_id_precio")).toBeNull();
  });

  it("loads the current values for the edit path and posts to the edit endpoint", async () => {
    serve(formulario(), EDIT);
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { url: "/centrodefamilia/centros/4/", message: "La actividad fue actualizada correctamente.", level: "success" } });
    setup("/centrodefamilia/centros/actividades/9/editar/");
    await screen.findByRole("button", { name: "Guardar" });
    expect(webGet).toHaveBeenCalledWith(EDIT, expect.anything());
    fireEvent.change(input("id_cantidad_personas"), { target: { value: "20" } });
    fireEvent.change(input("id_horarioshasta"), { target: { value: "11:00" } });
    (input("id_actividad") as unknown as HTMLSelectElement).required = false;
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(assign).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe(EDIT);
  });

  it("does not repeat an uncertain save", async () => {
    serve(formulario());
    webPost.mockRejectedValue(Object.assign(new Error("timeout"), { response: { status: 504 } }));
    setup();
    await screen.findByRole("button", { name: "Guardar" });
    fireEvent.change(input("id_cantidad_personas"), { target: { value: "1" } });
    fireEvent.change(input("id_horarioshasta"), { target: { value: "10:30" } });
    (input("id_actividad") as unknown as HTMLSelectElement).required = false;
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe(
      "No se pudo confirmar el resultado. Verificá el estado antes de reintentar."));
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("renders the queued messages as the native dismissible alerts", async () => {
    serve(formulario({ messages: [{ message: "Aviso previo", level: "warning" }] }));
    setup();
    const alerta = (await screen.findAllByText("Aviso previo")).map((e) => e.closest(".alert")).find(Boolean) as HTMLElement;
    expect(alerta.className).toBe("alert alert-warning alert-dismissible fade show");
    expect(alerta.querySelector("i.fa-exclamation-circle")).toBeTruthy();
    fireEvent.click(alerta.querySelector("button.btn-close") as HTMLElement);
    expect(document.querySelector(".alert-warning")).toBeNull();
  });
});
