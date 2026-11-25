import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { segmentacionValid } from "./encuestasSegmentacion";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const page = (over = {}) => ({
  id: 7, titulo: "Satisfacción 2026", disponible_pwa: false, tipo: "", grupos: [
    { id: 1, name: "Equipo Norte", selected: false }, { id: 2, name: "Equipo Sur", selected: false }, { id: 3, name: "Técnicos", selected: false },
  ],
  destinatarios: [], usuarios: [], urls: { plantilla: "/encuestas/7/segmentacion/plantilla/" }, messages: [], ...over,
});
const API = "web/encuestas/7/segmentacion/";
let current: unknown;
const serve = (data: unknown) => {
  current = data;
  webGet.mockImplementation((url: string) =>
    Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: current, status: 200 }));
};
const radio = (name: RegExp) => screen.getByRole("radio", { name }) as HTMLInputElement;
const sent = (n = 0) => webPost.mock.calls[n] as [string, FormData | URLSearchParams, unknown];

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  window.history.replaceState({}, "", "/encuestas/7/segmentacion/");
  setViewport(false);
});
afterEach(() => cleanup());

describe("segmentacion de una encuesta", () => {
  it("owns /encuestas/<id>/segmentacion/ and validates the payload", () => {
    expect(findRoute("/encuestas/7/segmentacion/")?.route.name).toBe("encuestas-segmentacion");
    expect(findRoute("/encuestas/7/segmentacion/plantilla/")?.route.name).not.toBe("encuestas-segmentacion");
    expect(segmentacionValid(page())).toBe(true);
    expect(segmentacionValid(page({ urls: { plantilla: "http://evil/" } }))).toBe(false);
    expect(segmentacionValid(page({ grupos: [{ id: "x", name: "a", selected: false }] }))).toBe(false);
    expect(segmentacionValid(page({ messages: [{ message: "a", level: "fatal" }] }))).toBe(false);
  });

  it("draws the native form with 'todos' checked when there is no segmentation", async () => {
    serve(page());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Segmentación" })).toBeTruthy();
    await waitFor(() => expect(document.title).toContain("Segmentación: Satisfacción 2026"));
    await waitFor(() => expect(radio(/Todos los usuarios logueados/).checked).toBe(true));
    expect(radio(/Listado de documentos/).checked).toBe(false);
    expect((document.getElementById("grupos-field") as HTMLFieldSetElement).hidden).toBe(true);
    expect((document.getElementById("listado-archivo-field") as HTMLElement).style.display).toBe("none");
    expect((document.getElementById("archivo_listado") as HTMLInputElement).disabled).toBe(true);
    expect(screen.queryByText("Agregar destinatario")).toBeNull();
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
  });

  it("follows the radios: the file field, the template link and the column help", async () => {
    serve(page({ tipo: "listado_documentos" }));
    render(<App />);
    await screen.findByRole("heading", { name: "Segmentación" });
    const link = () => document.getElementById("descargar-plantilla") as HTMLAnchorElement;
    expect(link().getAttribute("href")).toBe("/encuestas/7/segmentacion/plantilla/?tipo=listado_documentos");
    expect(document.getElementById("archivo-columnas")?.textContent).toBe("Columnas requeridas: tipo_documento, numero_documento.");
    expect(document.getElementById("usuarios-ayuda")?.hidden).toBe(true);
    fireEvent.click(radio(/Listado de IDs de usuarios/));
    expect(link().getAttribute("href")).toBe("/encuestas/7/segmentacion/plantilla/?tipo=listado_usuarios");
    expect(document.getElementById("archivo-columnas")?.textContent).toBe("Columna requerida: usuario_id.");
    expect(document.getElementById("usuarios-ayuda")?.hidden).toBe(false);
    fireEvent.click(radio(/Grupos de usuarios/));
    expect((document.getElementById("grupos-field") as HTMLFieldSetElement).disabled).toBe(false);
    expect((document.getElementById("listado-archivo-field") as HTMLElement).style.display).toBe("none");
  });

  it("counts, lists, filters and removes groups with the native focus rule", async () => {
    serve(page({ tipo: "grupos", grupos: [{ id: 1, name: "Equipo Norte", selected: true }, { id: 2, name: "Equipo Sur", selected: false }, { id: 3, name: "Técnicos", selected: true }] }));
    render(<App />);
    await screen.findByRole("heading", { name: "Segmentación" });
    expect(document.getElementById("grupos-contador")?.textContent).toBe("2 grupos seleccionados");
    expect(document.getElementById("grupos-seleccionados-vacio")?.hidden).toBe(true);
    fireEvent.click(screen.getByRole("checkbox", { name: "Equipo Sur" }));
    expect(document.getElementById("grupos-contador")?.textContent).toBe("3 grupos seleccionados");
    fireEvent.change(screen.getByLabelText("Buscar grupo"), { target: { value: "técn" } });
    expect(screen.getByText("Equipo Sur", { selector: "label span" }).closest("label")?.className).toContain("d-none");
    expect(screen.getByText("Técnicos", { selector: "label span" }).closest("label")?.className).not.toContain("d-none");
    fireEvent.change(screen.getByLabelText("Buscar grupo"), { target: { value: "zzz" } });
    expect(document.getElementById("grupos-sin-resultados")?.hidden).toBe(false);
    fireEvent.change(screen.getByLabelText("Buscar grupo"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Quitar grupo Equipo Norte" }));
    expect(document.getElementById("grupos-contador")?.textContent).toBe("2 grupos seleccionados");
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole("button", { name: "Quitar grupo Equipo Sur" })));
    fireEvent.click(screen.getByRole("button", { name: "Quitar grupo Equipo Sur" }));
    fireEvent.click(screen.getByRole("button", { name: "Quitar grupo Técnicos" }));
    expect(document.getElementById("grupos-contador")?.textContent).toBe("0 grupos seleccionados");
    expect(document.getElementById("grupos-seleccionados-vacio")?.hidden).toBe(false);
    await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText("Buscar grupo")));
  });

  it("posts only what the native form submits, shows the verbatim message and reads the page again", async () => {
    serve(page());
    webPost.mockImplementation(() => {
      serve(page({ tipo: "grupos", disponible_pwa: true, grupos: [{ id: 1, name: "Equipo Norte", selected: true }, { id: 2, name: "Equipo Sur", selected: false }, { id: 3, name: "Técnicos", selected: false }] }));
      return Promise.resolve({ status: 200, data: { ok: true, redirect: "/encuestas/7/segmentacion/", messages: [{ message: "Segmentación actualizada correctamente.", level: "success" }] } });
    });
    render(<App />);
    await screen.findByRole("heading", { name: "Segmentación" });
    fireEvent.click(screen.getByRole("checkbox", { name: /Disponible en la PWA/ }));
    fireEvent.click(radio(/Grupos de usuarios/));
    fireEvent.click(screen.getByRole("checkbox", { name: "Equipo Norte" }));
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    const [url, body] = sent();
    expect(url).toBe(`${API}tipo/`);
    const form = body as FormData;
    expect(form.get("tipo")).toBe("grupos");
    expect(form.get("disponibilidad_pwa_presente")).toBe("1");
    expect(form.get("disponible_pwa")).toBe("on");
    expect(form.getAll("grupos")).toEqual(["1"]);
    expect(form.has("archivo_listado")).toBe(false);
    expect(await screen.findByText("Segmentación actualizada correctamente.")).toBeTruthy();
    await waitFor(() => expect(radio(/Grupos de usuarios/).checked).toBe(true));
    expect(webGet.mock.calls.filter(([u]) => u === API).length).toBe(2);
    expect(document.getElementById("grupos-contador")?.textContent).toBe("1 grupo seleccionado");
  });

  it("leaves the file field out unless the type takes a list", async () => {
    serve(page({ tipo: "listado_documentos" }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/x/", messages: [] } });
    render(<App />);
    await screen.findByRole("heading", { name: "Segmentación" });
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    const form = sent()[1] as FormData;
    expect(form.get("tipo")).toBe("listado_documentos");
    expect(form.has("grupos")).toBe(false);
    expect(form.has("disponible_pwa")).toBe(false);
  });

  it("adds a document recipient, lists it, and removes it through its own endpoint", async () => {
    serve(page({ tipo: "listado_documentos", destinatarios: [{ id: 11, tipo_label: "DNI", numero_documento: "30111222" }] }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/x/", messages: [{ message: "Destinatario eliminado correctamente.", level: "success" }] } });
    render(<App />);
    await screen.findByRole("heading", { name: "Segmentación" });
    expect(screen.getByText("30111222")).toBeTruthy();
    expect(document.querySelector(".count-badge b")?.textContent?.trim()).toBe("1");
    fireEvent.change(screen.getByLabelText("Tipo"), { target: { value: "cuit" } });
    fireEvent.change(screen.getByLabelText("Número"), { target: { value: "20301112229" } });
    fireEvent.click(screen.getByRole("button", { name: /Agregar/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    expect(sent(0)[0]).toBe(`${API}agregar/`);
    expect(Object.fromEntries((sent(0)[1] as URLSearchParams).entries())).toEqual({ tipo_documento: "cuit", numero_documento: "20301112229" });
    await screen.findByText("Destinatario eliminado correctamente.");
    fireEvent.click(await screen.findByRole("button", { name: /Quitar/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(2));
    expect(sent(1)[0]).toBe(`${API}11/quitar/`);
    expect(String(sent(1)[1])).toBe("");
  });

  it("lists user recipients by id with their name and asks for a user id", async () => {
    serve(page({ tipo: "listado_usuarios", usuarios: [{ id: 5, username: "dora", full_name: "Dora Sur" }, { id: 6, username: "sin.nombre", full_name: "" }] }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/x/", messages: [] } });
    render(<App />);
    await screen.findByRole("heading", { name: "Segmentación" });
    expect(screen.getByText("ID 5")).toBeTruthy();
    expect(document.querySelectorAll(".destinatario-numero")[0].textContent).toBe("dora · Dora Sur");
    expect(document.querySelectorAll(".destinatario-numero")[1].textContent).toBe("sin.nombre");
    const field = screen.getByLabelText("ID de usuario en SISOC") as HTMLInputElement;
    expect(field.required).toBe(true);
    fireEvent.change(field, { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: /Agregar/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalled());
    expect(Object.fromEntries((sent()[1] as URLSearchParams).entries())).toEqual({ usuario_id: "9" });
  });

  it("shows the native error message and keeps the data when the service rejects", async () => {
    serve(page({ tipo: "listado_documentos" }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/x/", messages: [{ message: "El número de documento debe ser numérico.", level: "error" }] } });
    render(<App />);
    await screen.findByRole("heading", { name: "Segmentación" });
    fireEvent.change(screen.getByLabelText("Número"), { target: { value: "abc" } });
    fireEvent.click(screen.getByRole("button", { name: /Agregar/ }));
    const toast = await screen.findByText("El número de documento debe ser numérico.");
    expect(toast.closest(".toast")?.className).toContain("toast-error");
    expect(radio(/Listado de documentos/).checked).toBe(true);
    expect(within(document.body).queryByText("abc")).toBeNull();
  });

  it("shows a generic error when the request fails and lets the user retry", async () => {
    serve(page());
    webPost.mockRejectedValueOnce(new Error("network")).mockResolvedValue({ status: 200, data: { ok: true, redirect: "/x/", messages: [] } });
    render(<App />);
    await screen.findByRole("heading", { name: "Segmentación" });
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    expect(await screen.findByText("No se pudo completar la operación.")).toBeTruthy();
    await waitFor(() => expect((screen.getByRole("button", { name: /Guardar/ }) as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(2));
  });

  it("follows the native redirect of an approval-pending survey", async () => {
    serve({ redirect: "/encuestas/7/revision/" });
    const replace = vi.fn();
    vi.stubGlobal("location", { ...window.location, replace, pathname: "/encuestas/7/segmentacion/", search: "" });
    render(<App />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/encuestas/7/revision/"));
    vi.unstubAllGlobals();
  });

  it("shows the access screen on 403", async () => {
    webGet.mockImplementation((url: string) =>
      Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "No tiene permisos para esta acción." }, status: 403 }));
    render(<App />);
    expect(await screen.findByText(/permiso/i)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Guardar/ })).toBeNull();
  });
});
