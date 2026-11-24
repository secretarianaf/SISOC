import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { comedorTarjetaNavigation, tarjetaValid, type TarjetaField } from "./comedorTarjeta";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const PATH = "/comedores/7/responsable-tarjeta/editar";
const API = "web/comedores/comedores/7/responsable-tarjeta/";
const SUR = { value: "1", label: "Sur" };
const NORTE = { value: "2", label: "Norte" };
const field = (name: string, label: string, over: Partial<TarjetaField> = {}): TarjetaField => ({
  name: `responsable_tarjeta_${name}`, label, type: "text", required: false, help: "", value: "", options: null, errors: [], attrs: {}, ...over,
});
const form = (over: Record<string, unknown> = {}, fields: TarjetaField[] = []) => ({
  comedor_id: 7,
  fields: [
    field("nombre", "Responsable tarjeta nombre", { attrs: { maxlength: "255" } }),
    field("mail", "Responsable tarjeta mail", { type: "email" }),
    field("dni", "Responsable tarjeta dni", { attrs: { maxlength: "20" } }),
    field("cuit", "Responsable tarjeta cuit", { attrs: { maxlength: "20" } }),
    field("telefono", "Responsable tarjeta telefono"),
    field("domicilio", "Responsable tarjeta domicilio"),
    field("provincia", "Responsable tarjeta provincia", { type: "select", options: [{ value: "", label: "---------" }, NORTE, SUR] }),
    field("municipio", "Responsable tarjeta municipio", { type: "select", options: [{ value: "", label: "---------" }] }),
    field("localidad", "Responsable tarjeta localidad", { type: "select", options: [{ value: "", label: "---------" }] }),
  ].map((f) => fields.find((o) => o.name === f.name) ?? f),
  non_field_errors: [], urls: { ficha: "/comedores/7", municipios: "/ajax/municipios/", localidades: "/ajax/localidades/" }, ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
let assign: ReturnType<typeof vi.spyOn>;
let load: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  assign = vi.spyOn(comedorTarjetaNavigation, "assign").mockImplementation(() => undefined);
  load = vi.spyOn(comedorTarjetaNavigation, "load").mockResolvedValue([]);
  window.history.replaceState({}, "", PATH);
});
afterEach(() => { cleanup(); assign.mockRestore(); load.mockRestore(); });

const pick = (label: string, option: string) => {
  const container = screen.getByLabelText(label).closest("[id^=div_]") as HTMLElement;
  fireEvent.mouseDown(container.querySelector(".select2-selection") as HTMLElement);
  fireEvent.click(screen.getByRole("option", { name: option }));
};

describe("Comedor responsable de tarjeta route (CO07.03)", () => {
  it("owns only the native URL", () => {
    expect(findRoute(PATH)?.route.name).toBe("comedores-responsable-tarjeta");
    for (const other of [`${PATH}/`, "/comedores/7/editar", "/comedores/7/responsable-tarjeta"]) expect(findRoute(other)?.route.name).not.toBe("comedores-responsable-tarjeta");
  });

  it("validates the nine fields in template order", () => {
    expect(tarjetaValid({ ...form() })).toBe(true);
    expect(tarjetaValid({ ...form(), fields: form().fields.slice(1) })).toBe(false);
    expect(tarjetaValid({ ...form(), urls: { ficha: "https://externo.example/", municipios: "/a", localidades: "/b" } })).toBe(false);
  });

  it("renders the native card with its fields, Guardar and Cancelar", async () => {
    serve({ form: form() });
    render(<App />);
    expect(await screen.findByText("Responsable de la Tarjeta")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    const labels = [...document.querySelectorAll("#responsableTarjetaForm label")].map((l) => l.textContent);
    expect(labels).toEqual(["Responsable tarjeta nombre", "Responsable tarjeta mail", "Responsable tarjeta dni", "Responsable tarjeta cuit", "Responsable tarjeta telefono",
      "Responsable tarjeta domicilio", "Responsable tarjeta provincia", "Responsable tarjeta municipio", "Responsable tarjeta localidad"]);
    expect(screen.getByRole("button", { name: "Guardar" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/comedores/7");
    expect((screen.getByLabelText("Responsable tarjeta nombre") as HTMLInputElement).maxLength).toBe(255);
    expect((screen.getByLabelText("Responsable tarjeta mail") as HTMLInputElement).type).toBe("email");
  });

  it("choosing a provincia clears and reloads the municipios, then the localidades", async () => {
    serve({ form: form() });
    load.mockImplementation((url: string) => Promise.resolve(url.startsWith("/ajax/municipios/") ? [{ id: 11, nombre: "Municipio Sur" }] : [{ id: 21, nombre: "Localidad Sur" }]));
    render(<App />);
    await screen.findByText("Responsable de la Tarjeta");
    pick("Responsable tarjeta provincia", "Sur");
    await waitFor(() => expect(load).toHaveBeenCalledWith("/ajax/municipios/?provincia_id=1"));
    await waitFor(() => expect(document.querySelector("#responsable-tarjeta-municipio-loader")?.className).toContain("d-none"));
    pick("Responsable tarjeta municipio", "Municipio Sur");
    await waitFor(() => expect(load).toHaveBeenCalledWith("/ajax/localidades/?municipio_id=11"));
    await waitFor(() => expect(document.querySelector("#responsable-tarjeta-localidad-loader")?.className).toContain("d-none"));
    pick("Responsable tarjeta localidad", "Localidad Sur");
    expect((document.getElementById("id_responsable_tarjeta_localidad") as HTMLSelectElement).value).toBe("21");
  });

  it("posts the nine fields as typed and follows the redirect to the ficha", async () => {
    serve({ form: form() });
    webPost.mockResolvedValue({ status: 200, data: { redirect: "/comedores/7" } });
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Responsable tarjeta nombre"), { target: { value: "Ana Pérez" } });
    fireEvent.change(screen.getByLabelText("Responsable tarjeta mail"), { target: { value: "ana@example.org" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/7"));
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(API);
    const posted = body as URLSearchParams;
    expect([...posted.keys()]).toEqual(form().fields.map((f) => f.name));
    expect(posted.get("responsable_tarjeta_nombre")).toBe("Ana Pérez");
    expect(posted.get("responsable_tarjeta_mail")).toBe("ana@example.org");
    expect(posted.get("responsable_tarjeta_provincia")).toBe("");
  });

  it("a rejected POST shows the native errors and the options the server rebuilt", async () => {
    serve({ form: form() });
    const rechazado = form({}, [
      field("mail", "Responsable tarjeta mail", { type: "email", value: "no-es-un-mail", errors: ["Introduzca una dirección de correo electrónico válida."] }),
      field("provincia", "Responsable tarjeta provincia", { type: "select", value: "1", options: [{ value: "", label: "---------" }, NORTE, SUR] }),
      field("municipio", "Responsable tarjeta municipio", { type: "select", options: [{ value: "", label: "---------" }, { value: "11", label: "Municipio Sur" }] }),
    ]);
    webPost.mockResolvedValue({ status: 400, data: { errors: {}, non_field_errors: [], form: rechazado } });
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Introduzca una dirección de correo electrónico válida.")).toBeTruthy();
    expect((screen.getByLabelText("Responsable tarjeta mail") as HTMLInputElement).value).toBe("no-es-un-mail");
    expect(screen.getByLabelText("Responsable tarjeta mail").className).toContain("is-invalid");
    expect((document.getElementById("id_responsable_tarjeta_provincia") as HTMLSelectElement).value).toBe("1");
    expect([...(document.getElementById("id_responsable_tarjeta_municipio") as HTMLSelectElement).options].map((o) => o.label)).toContain("Municipio Sur");
    expect(assign).not.toHaveBeenCalled();
    expect(scroll).toHaveBeenCalledWith(0, 0);
    scroll.mockRestore();
  });

  it("an uncertain POST asks to reload and disables saving", async () => {
    serve({ form: form() });
    webPost.mockRejectedValue(new Error("network"));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Guardar" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Guardar" }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(assign).not.toHaveBeenCalled();
  });

  it("shows the access screen on a 403", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "Usted no tiene permiso para realizar esta acción." }, status: 403 }));
    render(<App />);
    await waitFor(() => expect(screen.queryByText("Responsable de la Tarjeta")).toBeNull());
    expect(webPost).not.toHaveBeenCalled();
  });
});
