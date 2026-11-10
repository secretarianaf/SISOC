import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import App from "../App";
import { duplasFormNavigation } from "./duplasForm";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const tecnicos = [
  { value: "4", label: "Prueba Ana - tecnico.0" },
  { value: "5", label: "Ejemplo Bruno - tecnico.1" },
  { value: "6", label: "Ficticia Carla - tecnico.2" },
];
const form = (over: Record<string, unknown> = {}) => ({
  title: "Editar Equipo técnico",
  fields: {
    nombre: { label: "Nombre", required: true, help_text: "", value: "Equipo E", max_length: 255 },
    estado: { label: "Estado", required: true, help_text: "", value: "Activo", choices: [{ value: "", label: "---------" }, { value: "Activo", label: "Activo" }, { value: "Inactivo", label: "Inactivo" }] },
    tecnico: { label: "Tecnico", required: true, help_text: "Un técnico puede integrarse en varias duplas.", value: ["5"], choices: tecnicos },
    abogado: { label: "Abogado", required: true, help_text: "", value: "8", choices: [{ value: "", label: "---------" }, { value: "8", label: "Legal Laura - abogado.0" }] },
  },
  errors: {},
  coordinador: "Clara Coordina",
  urls: { cancel: "/equipo-tecnico/" },
  messages: [],
  ...over,
});
const borrar = {
  id: 2, object_name: "EQUIPO TÉCNICO 02", title: "Dar de baja Equipo técnico", confirm_text: "Dar de baja Equipo técnico", cancel_text: "Cancelar",
  cascade_preview: { total_afectados: 1, total_baja_logica: 1, total_borrado_fisico: 0, desglose_por_modelo: [{ modelo: "Duplas", cantidad: 1, modo: "baja_logica", ejemplos: ["Equipo Técnico 02 (ID 2)"] }] },
  urls: { cancel: "/equipo-tecnico/" }, messages: [],
};

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const body = () => Object.fromEntries([...(webPost.mock.calls[0][1] as URLSearchParams).keys()].map((k) => [k, (webPost.mock.calls[0][1] as URLSearchParams).getAll(k)]));

beforeEach(() => { vi.clearAllMocks(); setViewport(false); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("Duplas form routes (DU01.02)", () => {
  it("owns only the native create, edit and delete paths", () => {
    expect(findRoute("/equipo-tecnico/crear/")?.route.name).toBe("duplas-form");
    expect(findRoute("/equipo-tecnico/3/editar/")?.route.name).toBe("duplas-form");
    expect(findRoute("/equipo-tecnico/3/eliminar/")?.route.name).toBe("duplas-form");
    for (const other of ["/equipo-tecnico/crear", "/equipo-tecnico/3/editar", "/equipo-tecnico/x/eliminar/", "/equipo-tecnico/3/"]) {
      expect(findRoute(other)?.route.name).not.toBe("duplas-form");
    }
  });

  it("renders the native form with the coordinator read-only and the chosen técnicos as chips", async () => {
    serve(form());
    setup("/equipo-tecnico/3/editar/");
    expect(await screen.findByRole("heading", { level: 2, name: "Editar Equipo técnico" }, { timeout: 5000 })).toBeDefined();
    expect(webGet).toHaveBeenCalledWith("web/comedores/duplas/3/editar/", expect.anything());
    expect(document.title).toBe("SISOC - Editar Equipo técnico");
    expect((document.getElementById("id_nombre") as HTMLInputElement).value).toBe("Equipo E");
    expect(document.querySelector("label[for=id_tecnico]")?.textContent).toBe("Tecnico*");
    expect([...document.querySelectorAll(".select2-selection__choice__display")].map((c) => c.textContent)).toEqual(["Ejemplo Bruno - tecnico.1"]);
    expect(screen.queryByLabelText(/Coordinador/)).toBeNull();
    expect(screen.getByRole("alert").textContent).toContain("Clara Coordina");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/equipo-tecnico/");
  });

  it("selects técnicos through the Select2 search and posts the native fields once", async () => {
    const assign = vi.spyOn(duplasFormNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/equipo-tecnico/" }, status: 200 });
    serve(form({ fields: { ...form().fields, tecnico: { ...form().fields.tecnico, value: [] } } }));
    setup("/equipo-tecnico/crear/");
    await screen.findByRole("heading", { level: 2 }, { timeout: 5000 });
    expect(webGet).toHaveBeenCalledWith("web/comedores/duplas/crear/", expect.anything());
    const search = document.querySelector<HTMLInputElement>("#div_id_tecnico .select2-search__field")!;
    expect(search.placeholder).toBe("Selecciona técnicos");
    fireEvent.change(search, { target: { value: "fíc" } });
    const options = within(document.getElementById("select2-id_tecnico-results")!).getAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual(["Ficticia Carla - tecnico.2"]);
    fireEvent.keyDown(search, { key: "Enter" });
    expect(document.getElementById("select2-id_tecnico-results")).toBeNull();
    fireEvent.change(search, { target: { value: "zzz" } });
    expect(screen.getByText("Sin resultados")).toBeDefined();
    fireEvent.keyDown(search, { key: "Escape" });
    fireEvent.change(document.getElementById("id_nombre")!, { target: { value: "Nuevo" } });
    await act(async () => { fireEvent.submit(document.getElementById("id_nombre")!.closest("form")!); });
    await act(async () => { fireEvent.submit(document.getElementById("id_nombre")!.closest("form")!); });
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/comedores/duplas/crear/");
    expect(body()).toEqual({ nombre: ["Nuevo"], estado: ["Activo"], abogado: ["8"], tecnico: ["6"] });
    expect(assign).toHaveBeenCalledWith("/equipo-tecnico/");
  });

  it("removes chips with the cross and with Backspace, leaving its text like Select2", async () => {
    serve(form({ fields: { ...form().fields, tecnico: { ...form().fields.tecnico, value: ["4", "6"] } } }));
    setup("/equipo-tecnico/3/editar/");
    await screen.findByRole("heading", { level: 2 }, { timeout: 5000 });
    const search = document.querySelector<HTMLInputElement>("#div_id_tecnico .select2-search__field")!;
    fireEvent.keyDown(search, { key: "Backspace" });
    expect(search.value).toBe("Ficticia Carla - tecnico.2");
    expect([...(document.getElementById("id_tecnico") as HTMLSelectElement).selectedOptions].map((o) => o.value)).toEqual(["4"]);
    fireEvent.click(screen.getByRole("button", { name: "Remove item" }));
    expect(document.querySelectorAll(".select2-selection__choice")).toHaveLength(0);
    expect(search.value).toBe("");
    expect(search.style.width).toBe("100%");
  });

  it("shows the server errors and general message of an invalid POST, without navigating", async () => {
    const assign = vi.spyOn(duplasFormNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({
      status: 400,
      data: form({
        errors: { nombre: [{ message: "Este campo es requerido.", code: "required" }] },
        fields: { ...form().fields, nombre: { ...form().fields.nombre, value: "" } },
        messages: [{ message: "Error al crear el Equipo técnico.", level: "error" }],
      }),
    });
    serve(form());
    setup("/equipo-tecnico/crear/");
    await screen.findByRole("heading", { level: 2 }, { timeout: 5000 });
    await act(async () => { fireEvent.submit(document.getElementById("id_nombre")!.closest("form")!); });
    expect(document.getElementById("id_nombre")?.className).toBe("textinput form-control is-invalid");
    expect(document.getElementById("id_nombre")?.getAttribute("aria-describedby")).toBe("id_nombre_error");
    expect(document.getElementById("error_1_id_nombre")?.textContent).toBe("Este campo es requerido.");
    expect(screen.getByText("Error al crear el Equipo técnico.")).toBeDefined();
    expect(assign).not.toHaveBeenCalled();
  });

  it("reports an unconfirmed outcome and never resubmits", async () => {
    webPost.mockRejectedValue(new Error("timeout"));
    serve(form());
    setup("/equipo-tecnico/3/editar/");
    await screen.findByRole("heading", { level: 2 }, { timeout: 5000 });
    await act(async () => { fireEvent.submit(document.getElementById("id_nombre")!.closest("form")!); });
    expect(screen.getByText(/No se pudo confirmar el resultado/)).toBeDefined();
    expect((screen.getByRole("button", { name: /Guardar/ }) as HTMLButtonElement).disabled).toBe(true);
    await act(async () => { fireEvent.submit(document.getElementById("id_nombre")!.closest("form")!); });
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("renders the delete confirmation with the cascade preview and soft deletes once", async () => {
    const assign = vi.spyOn(duplasFormNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/equipo-tecnico/" }, status: 200 });
    serve(borrar);
    setup("/equipo-tecnico/2/eliminar/");
    expect(await screen.findByRole("heading", { name: "Dar de baja Equipo técnico" }, { timeout: 5000 })).toBeDefined();
    expect(document.title).toBe("SISOC - Borrar Equipo técnico");
    expect(screen.getByText("EQUIPO TÉCNICO 02").className).toBe("font-weight-bold");
    expect(screen.getByText("Bajas lógicas: 1")).toBeDefined();
    expect(screen.queryByText(/Borrados físicos/)).toBeNull();
    expect([...document.querySelectorAll("tbody td")].map((td) => td.textContent)).toEqual(["Duplas", "1", "Baja lógica", "Equipo Técnico 02 (ID 2)"]);
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Dar de baja Equipo técnico" })); });
    expect(webPost).toHaveBeenCalledWith("web/comedores/duplas/2/eliminar/", expect.any(URLSearchParams), expect.anything());
    expect(assign).toHaveBeenCalledWith("/equipo-tecnico/");
  });

  it("turns a 403 on POST into the access message", async () => {
    webPost.mockResolvedValue({ status: 403, data: { detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" } });
    serve(borrar);
    setup("/equipo-tecnico/2/eliminar/");
    await screen.findByRole("heading", { name: "Dar de baja Equipo técnico" }, { timeout: 5000 });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Dar de baja Equipo técnico" })); });
    expect((await screen.findByRole("link", { name: "Continuar en SISOC" })).getAttribute("href")).toBe("/password/first-change/");
  });
});
