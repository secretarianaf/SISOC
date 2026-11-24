import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { coreProgramaFormNavigation, programaFormValid } from "./coreProgramaForm";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const field = (name: string, widget: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, widget, required: false, attrs: { class: "form-control" }, value: "", errors: [], ...over,
});
const form = (mode = "create", fields: unknown[] | null = null) => ({
  mode,
  fields: fields ?? [
    field("nombre", "text", { label: "Nombre", required: true, attrs: { class: "form-control", maxlength: "255" } }),
    field("estado", "checkbox", { label: "Estado", attrs: { class: "form-check-input" }, value: true }),
    field("observaciones", "text", { label: "Observaciones", attrs: { class: "form-control", maxlength: "500" } }),
    field("organismo", "select", { label: "Organismo", choices: [{ value: "", label: "---------" }, { value: "4", label: "Org Cuatro" }] }),
    field("descripcion", "textarea", { label: "Descripción", attrs: { class: "form-control", cols: "40", rows: "3" } }),
  ],
  urls: { list: "/programas/" }, messages: [],
});
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
const rejected = (data: unknown) => Object.assign(new Error("400"), { response: { status: 400, data } });

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.scrollTo = vi.fn();
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("formulario de programa (T05.02)", () => {
  it("owns /programas/crear/ and /programas/<pk>/editar/ and validates the form payload", () => {
    expect(findRoute("/programas/crear/")?.route.name).toBe("core-programa-form");
    expect(findRoute("/programas/3/editar/")?.params).toEqual({ id: "3" });
    expect(findRoute("/programas/3/editar")?.route.name).not.toBe("core-programa-form");
    expect(programaFormValid(form())).toBe(true);
    expect(programaFormValid({ ...form(), mode: "otro" })).toBe(false);
    expect(programaFormValid({ ...form(), fields: [{ name: 1 }] })).toBe(false);
  });

  it("draws the native create form: title, labels, widgets and buttons", async () => {
    window.history.replaceState({}, "", "/programas/crear/");
    serve(form());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Nuevo Programa" })).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Nuevo Programa"));
    const nombre = screen.getByLabelText("Nombre") as HTMLInputElement;
    expect(nombre.getAttribute("maxlength")).toBe("255");
    expect(nombre.required).toBe(true);
    expect((screen.getByLabelText("Estado") as HTMLInputElement).checked).toBe(true);
    expect(screen.getByLabelText("Descripción").tagName).toBe("TEXTAREA");
    expect(screen.getByRole("button", { name: "Crear" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/programas/");
  });

  it("posts only the rendered fields once and follows the redirect", async () => {
    window.history.replaceState({}, "", "/programas/crear/");
    serve(form());
    const assign = vi.spyOn(coreProgramaFormNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/programas/9/" }, status: 200 });
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Nombre"), { target: { value: "Nuevo" } });
    fireEvent.click(screen.getByLabelText("Estado"));
    fireEvent.change(screen.getByLabelText("Organismo"), { target: { value: "4" } });
    const button = screen.getByRole("button", { name: "Crear" });
    fireEvent.click(button);
    fireEvent.click(button);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/programas/9/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/core/programas/crear/");
    const body = webPost.mock.calls[0][1] as URLSearchParams;
    expect(Array.from(body.keys())).toEqual(["nombre", "observaciones", "organismo", "descripcion"]);
    expect(body.get("nombre")).toBe("Nuevo");
    expect(body.get("organismo")).toBe("4");
  });

  it("edits through the program's own endpoint and sends the checkbox as on", async () => {
    window.history.replaceState({}, "", "/programas/5/editar/");
    serve(form("edit"));
    const assign = vi.spyOn(coreProgramaFormNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/programas/5/" }, status: 200 });
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Editar Programa" })).toBeTruthy();
    expect(webGet.mock.calls.map((c) => c[0])).toContain("web/core/programas/5/editar/");
    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Editado" } });
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/programas/5/"));
    expect(webPost.mock.calls[0][0]).toBe("web/core/programas/5/editar/");
    expect((webPost.mock.calls[0][1] as URLSearchParams).get("estado")).toBe("on");
  });

  it("keeps the typed values, shows the field errors and goes back to the top after a rejected form", async () => {
    window.history.replaceState({}, "", "/programas/crear/");
    serve(form());
    const assign = vi.spyOn(coreProgramaFormNavigation, "assign").mockImplementation(() => {});
    const bound = form("create", [
      field("nombre", "text", { label: "Nombre", required: true, value: "Repetido", errors: ["Ya existe un Programa con este Nombre."], attrs: { class: "form-control", "aria-invalid": "true", "aria-describedby": "id_nombre_error" } }),
    ]);
    webPost.mockRejectedValue(rejected(bound));
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Nombre"), { target: { value: "Repetido" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect(await screen.findByText("Ya existe un Programa con este Nombre.")).toBeTruthy();
    expect(screen.getByText("Ya existe un Programa con este Nombre.").closest("ul")?.id).toBe("id_nombre_error");
    expect((screen.getByLabelText("Nombre") as HTMLInputElement).value).toBe("Repetido");
    expect(screen.getByLabelText("Nombre").getAttribute("aria-invalid")).toBe("true");
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
    expect(assign).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: "Crear" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("shows an unconfirmed outcome without navigating", async () => {
    window.history.replaceState({}, "", "/programas/crear/");
    serve(form());
    const assign = vi.spyOn(coreProgramaFormNavigation, "assign").mockImplementation(() => {});
    webPost.mockRejectedValue(new Error("network"));
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Nombre"), { target: { value: "X" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudo confirmar el resultado");
    expect(assign).not.toHaveBeenCalled();
  });
});
