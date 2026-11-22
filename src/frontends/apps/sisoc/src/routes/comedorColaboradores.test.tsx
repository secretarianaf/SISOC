import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { colaboradoresNavigation, dataValid } from "./comedorColaboradores";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/colaboradores/comedor/";
const comedor = { id: 3, nombre: "Comedor Sintético", url: "/comedores/3" };
const scalar = (label: string, value = "", over: Record<string, unknown> = {}) => ({ label, required: false, html_required: false, value, max_length: null, ...over });
const fields = (over: Record<string, unknown> = {}) => ({
  genero: { ...scalar("Genero", "ND", { required: true }), choices: [{ value: "V", label: "Varón" }, { value: "ND", label: "No declara" }] },
  codigo_telefono: scalar("Codigo telefono", "", { max_length: 10 }),
  numero_telefono: scalar("Numero telefono", "", { max_length: 20 }),
  fecha_alta: scalar("Fecha alta", "2026-11-13", { required: true, html_required: true }),
  fecha_baja: scalar("Fecha baja"),
  actividades: { label: "Actividades", required: true, choices: [{ value: "1", label: " - Cocina", checked: false }, { value: "2", label: " - Limpieza", checked: false }] },
  ...over,
});
const preview = { apellido: "Gómez", nombre: "Ana", dni: "30999111", prefijo_cuil: "27", cuil_cuit: "27309991114", sufijo_cuil: "4", sexo: "Femenino", fecha_nacimiento: "01/01/2000", edad: "26" };
const data = (over: Record<string, unknown> = {}) => ({
  comedor, edit_mode: false, query: "30999111", preview, source: "sisoc", existing: false, not_found: false,
  hidden: { name: "ciudadano_id", value: "77" }, form: { fields: fields(), errors: {} }, messages: [], urls: { comedor: "/comedores/3" }, ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
function setup(url: string) {
  window.history.replaceState({}, "", url);
  return render(<App />);
}
const posted = () => Array.from((webPost.mock.calls[0][1] as URLSearchParams).entries());

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Comedor collaborators", () => {
  it("owns the two native URLs (trailing slash) and validates its payload", () => {
    for (const path of ["/comedores/3/colaboradores/crear/", "/comedores/3/colaboradores/8/editar/"]) {
      expect(findRoute(path)?.route.name, path).toBe("comedores-colaboradores");
    }
    expect(findRoute("/comedores/3/colaboradores/crear")?.route.name).not.toBe("comedores-colaboradores");
    expect(findRoute("/comedores/3/colaboradores/8/eliminar/")?.route.name).not.toBe("comedores-colaboradores");
    expect(dataValid(data())).toBe(true);
    expect(dataValid(data({ form: null, preview: null, source: null }))).toBe(true);
    expect(dataValid(data({ hidden: { name: "otro", value: "1" } }))).toBe(false);
    expect(dataValid(data({ urls: { comedor: "https://x.example" } }))).toBe(false);
    expect(dataValid(data({ form: { fields: fields({ genero: null }), errors: {} } }))).toBe(false);
  });

  it("renders only the search when nothing was searched and keeps the native GET form", async () => {
    serve(data({ query: "", preview: null, source: null, form: null }));
    setup("/comedores/3/colaboradores/crear/");
    expect(await screen.findByText("Agregar colaborador del espacio")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}3/crear/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Agregar colaborador"));
    expect(Array.from(document.querySelectorAll(".breadcrumb-item")).map((li) => li.textContent)).toEqual(["Comedor", "Agregar colaborador"]);
    const form = document.querySelector("form.form-inline") as HTMLFormElement;
    expect(form.getAttribute("method")).toBe("get");
    expect((document.getElementById("busqueda-dni") as HTMLInputElement).name).toBe("query");
    expect(screen.getByRole("button", { name: "Buscar" })).toBeTruthy();
    expect(document.querySelector(".container form[method='post']")).toBeNull();
  });

  it("forwards the search to the API and shows the found citizen with the form", async () => {
    serve(data());
    setup("/comedores/3/colaboradores/crear/?query=30999111");
    expect(await screen.findByText("Ciudadano encontrado en SISOC")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}3/crear/?query=30999111`, expect.anything());
    expect(Array.from(document.querySelectorAll(".col-md-4.mb-2")).map((c) => c.textContent)).toEqual([
      "Apellido: Gómez", "Nombre: Ana", "DNI: 30999111", "Prefijo CUIL: 27", "CUIT/CUIL: 27309991114", "Sufijo CUIL: 4", "Sexo: Femenino", "Fecha de nacimiento: 01/01/2000", "Edad: 26",
    ]);
    expect((document.getElementById("busqueda-dni") as HTMLInputElement).value).toBe("30999111");
    expect(document.querySelector('label[for="id_genero"]')?.textContent).toBe("Genero*");
    expect(document.querySelector('label[for="id_fecha_baja"]')?.textContent).toBe("Fecha baja");
    expect((document.getElementById("id_genero") as HTMLSelectElement).required).toBe(false);
    expect((document.getElementById("id_fecha_alta") as HTMLInputElement).required).toBe(true);
    expect(Array.from(document.querySelectorAll(".form-check-label")).map((l) => l.textContent)).toEqual([" - Cocina", " - Limpieza"]);
    expect(screen.getByRole("button", { name: "Guardar colaborador" })).toBeTruthy();
  });

  it("shows the RENAPER header, the existing-collaboration warning and the not-found notice", async () => {
    serve(data({ source: "renaper", hidden: { name: "dni", value: "30999111" } }));
    setup("/comedores/3/colaboradores/crear/?query=30999111");
    expect(await screen.findByText("Datos obtenidos desde RENAPER")).toBeTruthy();
    cleanup();
    serve(data({ existing: true, form: null }));
    setup("/comedores/3/colaboradores/crear/?ciudadano_id=77");
    expect(await screen.findByText("La persona ya se encuentra registrada como colaborador de este espacio.")).toBeTruthy();
    expect(document.querySelector(".container form[method='post']")).toBeNull();
    cleanup();
    serve(data({ preview: null, source: null, form: null, not_found: true }));
    setup("/comedores/3/colaboradores/crear/?query=30111222");
    expect(await screen.findByText("No se encontraron datos para el DNI ingresado.")).toBeTruthy();
  });

  it("renders dismissible flash messages with their native tags", async () => {
    serve(data({ preview: null, source: null, form: null, query: "123", messages: [{ message: "Ingrese un DNI numérico válido para realizar la búsqueda.", tags: "warning" }] }));
    setup("/comedores/3/colaboradores/crear/?query=123");
    await screen.findAllByText(/Ingrese un DNI numérico válido/);
    // The inline alert of the template plus the toastr toast the base template adds.
    expect(screen.getAllByText(/Ingrese un DNI numérico válido/)).toHaveLength(2);
    const alert = document.querySelector(".container .alert") as HTMLElement;
    expect(alert.className).toBe("alert alert-warning alert-dismissible fade show");
    fireEvent.click(alert.querySelector("button.btn-close")!);
    expect(document.querySelector(".container .alert")).toBeNull();
  });

  it("posts the native fields once with the citizen id, then follows the native redirect", async () => {
    serve(data());
    const assign = vi.spyOn(colaboradoresNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/comedores/3" }, status: 200 });
    setup("/comedores/3/colaboradores/crear/?query=30999111");
    await screen.findByText("Ciudadano encontrado en SISOC");
    fireEvent.change(document.getElementById("id_genero")!, { target: { value: "V" } });
    fireEvent.change(document.getElementById("id_codigo_telefono")!, { target: { value: "11" } });
    fireEvent.change(document.getElementById("id_numero_telefono")!, { target: { value: "5551234" } });
    fireEvent.click(document.getElementById("id_actividades_0")!);
    fireEvent.click(document.getElementById("id_actividades_1")!);
    fireEvent.click(document.getElementById("id_actividades_0")!);
    const guardar = screen.getByRole("button", { name: "Guardar colaborador" });
    fireEvent.click(guardar);
    fireEvent.click(guardar);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/3"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}3/crear/`);
    expect(posted()).toEqual([
      ["ciudadano_id", "77"], ["genero", "V"], ["codigo_telefono", "11"], ["numero_telefono", "5551234"], ["fecha_alta", "2026-11-13"], ["fecha_baja", ""], ["actividades", "2"],
    ]);
    expect(screen.getByRole("button", { name: /Guardando/ })).toBeTruthy();
  });

  it("shows the native field errors and messages after a rejected POST and never navigates", async () => {
    serve(data());
    const assign = vi.spyOn(colaboradoresNavigation, "assign").mockImplementation(() => undefined);
    const rejected = data({
      query: "",
      form: { fields: fields({ genero: { ...scalar("Genero", "V", { required: true }), choices: [{ value: "V", label: "Varón" }] } }), errors: { actividades: [{ message: "Este campo es requerido.", code: "required" }], fecha_alta: [{ message: "Este campo es requerido.", code: "required" }] } },
      messages: [{ message: "Errores en el formulario del colaborador.", tags: "warning" }],
    });
    webPost.mockResolvedValueOnce({ data: rejected, status: 400 });
    setup("/comedores/3/colaboradores/crear/?query=30999111");
    await screen.findByText("Ciudadano encontrado en SISOC");
    fireEvent.click(screen.getByRole("button", { name: "Guardar colaborador" }));
    expect((await screen.findAllByText("Errores en el formulario del colaborador.")).length).toBe(2);
    expect(screen.getAllByText("Este campo es requerido.")).toHaveLength(2);
    expect(document.getElementById("id_fecha_alta")!.className).toContain("is-invalid");
    expect(document.getElementById("id_fecha_alta")!.getAttribute("aria-describedby")).toBe("id_fecha_alta_error");
    expect(document.getElementById("id_actividades_1")!.className).toContain("is-invalid");
    expect(document.getElementById("id_actividades_1")!.closest(".form-check")!.querySelector("#id_actividades_error")).toBeTruthy();
    expect((document.getElementById("id_genero") as HTMLSelectElement).value).toBe("V");
    // The native page reloads from the POST: its search box is the posted one (empty), not the old query.
    expect((document.getElementById("busqueda-dni") as HTMLInputElement).value).toBe("");
    expect(assign).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: "Guardar colaborador" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("renders the edit page with the associated citizen and posts the hidden citizen id", async () => {
    serve(data({
      edit_mode: true, source: "edicion", query: "", hidden: { name: "ciudadano_id", value: "77" },
      form: { fields: fields({ codigo_telefono: scalar("Codigo telefono", "11", { max_length: 10 }), actividades: { label: "Actividades", required: true, choices: [{ value: "1", label: " - Cocina", checked: true }, { value: "2", label: " - Limpieza", checked: false }] } }), errors: {} },
    }));
    const assign = vi.spyOn(colaboradoresNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/comedores/3" }, status: 200 });
    setup("/comedores/3/colaboradores/8/editar/");
    expect(await screen.findByText("Editar colaborador del espacio")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}3/8/editar/`, expect.anything());
    expect(screen.getByText("Ciudadano asociado")).toBeTruthy();
    expect(Array.from(document.querySelectorAll(".breadcrumb-item")).map((li) => li.textContent)).toEqual(["Comedor", "Editar colaborador"]);
    expect(document.getElementById("busqueda-dni")).toBeNull();
    expect((document.getElementById("id_codigo_telefono") as HTMLInputElement).value).toBe("11");
    expect((document.getElementById("id_actividades_0") as HTMLInputElement).checked).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/3"));
    expect(webPost.mock.calls[0][0]).toBe(`${API}3/8/editar/`);
    expect(posted()[0]).toEqual(["ciudadano_id", "77"]);
    expect(posted().filter(([k]) => k === "actividades")).toEqual([["actividades", "1"]]);
  });

  it("reports a forbidden post and does not retry", async () => {
    serve(data());
    webPost.mockResolvedValueOnce({ data: { detail: "Usted no tiene permiso para realizar esta acción." }, status: 403 });
    setup("/comedores/3/colaboradores/crear/?query=30999111");
    await screen.findByText("Ciudadano encontrado en SISOC");
    fireEvent.click(screen.getByRole("button", { name: "Guardar colaborador" }));
    expect(await screen.findByText("Usted no tiene permiso para realizar esta acción.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Guardar colaborador" }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
  });
});
