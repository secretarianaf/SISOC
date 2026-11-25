import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { geography } from "./cdfCentroForm";
import { navigation } from "./cdfFrame";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const campo = (name: string, over: Record<string, unknown> = {}) => ({
  name, label: name[0].toUpperCase() + name.slice(1), required: false, disabled: false, widget: "text", help_text: "", value: "", attrs: {}, ...over,
});
const formulario = (over: Record<string, unknown> = {}) => ({
  fields: [
    campo("tipo", { required: true, widget: "select", choices: [{ value: "", label: "---------" }, { value: "faro", label: "faro" }, { value: "adherido", label: "Adherido" }] }),
    campo("nombre", { required: true, attrs: { maxlength: "200" } }),
    campo("provincia", { required: true, widget: "select", choices: [{ value: "", label: "---------" }, { value: "1", label: "Buenos Aires" }] }),
    campo("municipio", { widget: "select", choices: [{ value: "", label: "---------" }, { value: "5", label: "Inicial" }] }),
    campo("localidad", { widget: "select", choices: [{ value: "", label: "---------" }] }),
    campo("longitud", { widget: "number", attrs: { step: "0.000001" } }),
    campo("sitio_web", { widget: "url" }),
    campo("faro_asociado", { widget: "select", choices: [{ value: "", label: "---------" }, { value: "1", label: "Faro" }] }),
    campo("foto", { widget: "file", current: null }),
    campo("activo", { widget: "checkbox", value: true }),
  ],
  locked: [], errors: {}, non_field_errors: [],
  urls: { cancel: "", municipios: "/ajax/load-municipios/", localidades: "/ajax/load-localidades/", address_preview: "/ajax/ubicacion/previsualizar/" },
  messages: [],
  ...over,
});
const baja = {
  id: 7, nombre: "Centro Siete", confirm_text: "Dar de baja", cancel_text: "Cancelar",
  preview: { total_afectados: 3, total_baja_logica: 2, total_borrado_fisico: 1, desglose_por_modelo: [
    { modelo: "Centros", cantidad: 1, modo: "baja_logica", ejemplos: ["Centro Siete (ID 7)"] },
    { modelo: "Accesos Cdf", cantidad: 1, modo: "borrado_fisico", ejemplos: [] },
  ] },
  urls: { cancel: "/centrodefamilia/centros/7/" }, messages: [],
};

function serve(routes: Record<string, unknown>) {
  webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
    : url in routes ? Promise.resolve({ data: routes[url], status: 200 }) : Promise.reject(new Error(url))));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const display = (name: string) => (document.getElementById(`div_id_${name}`) as HTMLElement).style.display;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  vi.spyOn(document.head, "appendChild").mockImplementation((node) => node);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("CDF centre form and delete routes", () => {
  it("owns only the native create, edit and delete paths", () => {
    expect(findRoute("/centrodefamilia/centros/nuevo/")?.params).toEqual({ action: "nuevo" });
    expect(findRoute("/centrodefamilia/centros/7/editar/")?.params).toEqual({ id: "7", action: "editar" });
    expect(findRoute("/centrodefamilia/centros/7/eliminar/")?.params).toEqual({ id: "7", action: "eliminar" });
    expect(findRoute("/centrodefamilia/centros/7/")?.route.name).toBe("cdf-centros");
    expect(findRoute("/centrodefamilia/centros/7/generar-usuario/")?.route.name).not.toBe("cdf-centro-form");
  });

  it("renders the crispy fields and shows the groups of each tipo like centro_form.js", async () => {
    serve({ "web/cdf/centros/options/": formulario() });
    setup("/centrodefamilia/centros/nuevo/");
    await screen.findByLabelText(/Tipo/);
    await waitFor(() => expect(document.title).toBe("SISOC - Nuevo Centro"));
    expect(document.querySelector("label[for=id_nombre]")?.className).toBe("form-label requiredField");
    expect((document.getElementById("id_nombre") as HTMLInputElement).className).toBe("textinput form-control");
    expect(document.getElementById("id_nombre")?.getAttribute("maxlength")).toBe("200");
    expect(display("tipo")).toBe("block");
    expect(display("nombre")).toBe("none");
    expect((document.querySelector("[data-centro-location-editor]") as HTMLElement).hidden).toBe(true);
    fireEvent.change(document.getElementById("id_tipo") as HTMLSelectElement, { target: { value: "faro" } });
    expect(display("nombre")).toBe("block");
    expect(display("faro_asociado")).toBe("none");
    expect(display("sitio_web")).toBe("none");
    expect((document.querySelector("[data-centro-location-editor]") as HTMLElement).hidden).toBe(false);
    fireEvent.change(document.getElementById("id_tipo") as HTMLSelectElement, { target: { value: "adherido" } });
    expect(display("faro_asociado")).toBe("block");
    const cancelar = screen.getByText("Cancelar");
    expect(cancelar.tagName).toBe("A");
    expect(cancelar.getAttribute("href")).toBe("");
  });

  it("reloads municipios on province change and localidades only for loaded municipios", async () => {
    serve({ "web/cdf/centros/options/": formulario() });
    const load = vi.spyOn(geography, "load").mockImplementation((url: string) =>
      Promise.resolve(url.includes("municipios") ? [{ id: 9, nombre: "La Matanza" }] : [{ id: 3, nombre: "San Justo" }]));
    setup("/centrodefamilia/centros/nuevo/");
    await screen.findByLabelText(/Tipo/);
    fireEvent.change(document.getElementById("id_tipo") as HTMLSelectElement, { target: { value: "faro" } });
    fireEvent.change(document.getElementById("id_municipio") as HTMLSelectElement, { target: { value: "5" } });
    expect(load).not.toHaveBeenCalled();
    fireEvent.change(document.getElementById("id_provincia") as HTMLSelectElement, { target: { value: "1" } });
    expect(load).toHaveBeenCalledWith("/ajax/load-municipios/?provincia_id=1");
    await screen.findByRole("option", { name: "La Matanza" });
    expect(screen.getAllByRole("option", { name: "Seleccionar localidad..." })).toHaveLength(1);
    fireEvent.change(document.getElementById("id_municipio") as HTMLSelectElement, { target: { value: "9" } });
    expect(load).toHaveBeenLastCalledWith("/ajax/load-localidades/?municipio_id=9");
    expect(await screen.findByRole("option", { name: "San Justo" })).toBeTruthy();
  });

  it("posts the form to the API, keeps ?faro= and returns to the native URL", async () => {
    serve({ "web/cdf/centros/options/?faro=1": formulario() });
    webPost.mockResolvedValue({ status: 201, data: { id: 3, message: "Centro creado exitosamente.", redirect: "list", url: "/centrodefamilia/centros/" } });
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    setup("/centrodefamilia/centros/nuevo/?faro=1");
    fireEvent.submit((await screen.findByRole("button", { name: "Guardar" })).closest("form") as HTMLFormElement);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodefamilia/centros/"));
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe("web/cdf/centros/crear/?faro=1");
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get("activo")).toBe("on");
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("shows the bound errors of a 400 and the non-field message", async () => {
    serve({ "web/cdf/centros/7/editar/": formulario() });
    webPost.mockResolvedValue({ status: 400, data: formulario({
      errors: { nombre: [{ message: "Este campo es obligatorio.", code: "required" }] },
      non_field_errors: ["Debe asociar un Centro FARO activo si el centro es ADHERIDO."],
    }) });
    setup("/centrodefamilia/centros/7/editar/");
    fireEvent.submit((await screen.findByRole("button", { name: "Guardar" })).closest("form") as HTMLFormElement);
    expect(await screen.findByText("Debe asociar un Centro FARO activo si el centro es ADHERIDO.")).toBeTruthy();
    expect(screen.getByText("Este campo es obligatorio.").closest("span")?.id).toBe("error_1_id_nombre");
    expect(document.getElementById("id_nombre")?.className).toBe("textinput form-control is-invalid");
    expect(webPost.mock.calls[0][0]).toBe("web/cdf/centros/7/editar/");
  });

  it("never retries an uncertain save", async () => {
    serve({ "web/cdf/centros/7/editar/": formulario() });
    webPost.mockRejectedValue(Object.assign(new Error("timeout"), { response: { status: 504, data: { uncertain: true } } }));
    setup("/centrodefamilia/centros/7/editar/");
    fireEvent.submit((await screen.findByRole("button", { name: "Guardar" })).closest("form") as HTMLFormElement);
    expect(await screen.findByText("No se pudo confirmar el resultado. Verificá el estado antes de reintentar.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Guardar" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.submit(screen.getByRole("button", { name: "Guardar" }).closest("form") as HTMLFormElement);
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("renders the cascade preview and soft deletes through the API", async () => {
    serve({ "web/cdf/centros/7/eliminar/": baja });
    webPost.mockResolvedValue({ status: 200, data: { message: "Centro dado de baja correctamente.", redirect: "list", url: "/centrodefamilia/centros/" } });
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    setup("/centrodefamilia/centros/7/eliminar/");
    expect(await screen.findByText("CENTRO SIETE")).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Confirmar Eliminación"));
    expect(screen.getByText("Bajas lógicas: 2")).toBeTruthy();
    expect(screen.getByText("Borrado físico técnico")).toBeTruthy();
    expect(screen.getByText("-")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/centrodefamilia/centros/7/");
    fireEvent.click(screen.getByRole("button", { name: "Dar de baja" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodefamilia/centros/"));
    expect(webPost.mock.calls[0][0]).toBe("web/cdf/centros/7/eliminar/");
  });
});
