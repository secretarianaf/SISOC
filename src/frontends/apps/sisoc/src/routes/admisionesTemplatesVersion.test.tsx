import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { editorAssets, versionFormNavigation } from "./admisionesTemplatesVersion";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const BASE = "/comedores/configuracion/templates/";
const URL = `${BASE}1/versiones/2/editar/`;
const API = "web/comedores/admisiones/plantillas-informe/1/versiones/2/";
const nav = { templates: BASE, variables: `${BASE}variables/`, incidencias: `${BASE}incidencias/` };
const data = (over: Record<string, unknown> = {}) => ({
  version: { id: 2, numero: 3 }, plantilla: { id: 1, codigo: "IT-000001", nombre: "Incorporación" },
  contenido_html: { label: "Contenido del template", value: "<p>Hola</p>", errors: [], placeholder: "Escribí el contenido HTML" },
  observaciones: { label: "Observaciones de la versión", value: "Nota", errors: [], placeholder: "" },
  non_field_errors: [],
  variables: [
    { categoria: "Comedor", nombre: "Nombre", codigo: "comedor.nombre", token: "{{ comedor.nombre }}" },
    { categoria: "Informe", nombre: "Fecha", codigo: "informe.fecha", token: "{{ informe.fecha }}" },
    { categoria: "Informe", nombre: "Expediente", codigo: "informe.expediente", token: "{{ informe.expediente }}" },
  ],
  urls: { ...nav, detalle: `${BASE}1/`, previsualizar: `${BASE}1/versiones/2/previsualizar/` }, messages: [], ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
async function setup(body: unknown = data()) {
  serve(body);
  window.history.replaceState({}, "", URL);
  render(<App />);
  await screen.findByText("Editar contenido del template");
}
const submit = () => fireEvent.submit(screen.getByRole("button", { name: "Guardar borrador" }).closest("form")!);

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(editorAssets, "load").mockResolvedValue();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => cleanup());

describe("Template version editor (AD01.02)", () => {
  it("owns only the editor URL of a version", () => {
    expect(findRoute(URL)?.route.name).toBe("comedores-gestor-templates-version");
    for (const other of [`${BASE}1/versiones/2/editar`, `${BASE}1/versiones/2/previsualizar/`, `${BASE}1/versiones/crear/`]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-gestor-templates-version");
    }
  });

  it("renders the native editor contract, loads the editor assets and groups the variables", async () => {
    await setup();
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    expect(editorAssets.load).toHaveBeenCalled();
    expect(document.title).toContain("Editar versión");
    expect(screen.getByText("IT-000001 · Versión 3")).toBeTruthy();
    const source = document.querySelector("[data-template-editor-source]") as HTMLTextAreaElement;
    expect(source.value).toBe("<p>Hola</p>");
    expect(document.querySelectorAll("[data-categoria-variable]").length).toBe(2);
    expect(document.querySelectorAll("[data-template-variable]").length).toBe(3);
    expect(document.getElementById("buscar-variable-template")).toBeTruthy();
    expect(document.querySelector("details.gt-editor-panel--content")?.hasAttribute("open")).toBe(true);
    const preview = screen.getByRole("button", { name: "Descargar vista previa" }).closest("form")!;
    expect([preview.getAttribute("method"), preview.getAttribute("action"), preview.getAttribute("target")]).toEqual(["get", `${BASE}1/versiones/2/previsualizar/`, "_blank"]);
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe(`${BASE}1/`);
  });

  it("shows the empty catalogue text", async () => {
    await setup(data({ variables: [] }));
    expect(screen.getByText("No hay variables activas en el catálogo.")).toBeTruthy();
  });

  it("posts only the two native fields once and follows the redirect", async () => {
    const assign = vi.spyOn(versionFormNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: `${BASE}1/` } });
    await setup();
    submit(); submit();
    await waitFor(() => expect(assign).toHaveBeenCalledWith(`${BASE}1/`));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0] as [string, URLSearchParams];
    expect(url).toBe(API);
    expect(Object.fromEntries(body)).toEqual({ contenido_html: "<p>Hola</p>", observaciones: "Nota" });
  });

  it("shows the native errors of a rejected save with the returned values", async () => {
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    webPost.mockRejectedValue({ response: { status: 400, data: data({ non_field_errors: ["Solo se pueden editar versiones en borrador."], contenido_html: { label: "Contenido del template", value: "<p>Otro</p>", errors: [], placeholder: "" } }) } });
    await setup();
    submit();
    expect(await screen.findByText("Solo se pueden editar versiones en borrador.")).toBeTruthy();
    expect((document.querySelector("[data-template-editor-source]") as HTMLTextAreaElement).value).toBe("<p>Otro</p>");
    expect(scroll).toHaveBeenCalledWith(0, 0);
  });

  it("never resends after an unconfirmed result", async () => {
    webPost.mockRejectedValue(new Error("network"));
    await setup();
    submit();
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    submit();
    expect(webPost).toHaveBeenCalledTimes(1);
  });
});
