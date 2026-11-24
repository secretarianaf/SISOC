import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { bajaValid, cursosNavigation, formValid, listValid } from "./comedorCursos";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/cursos-app-mobile/";
const BASE = "/comedores/configuracion/cursos-app-mobile/";
const curso = (over: Record<string, unknown> = {}) => ({
  id: 5, nombre: "Curso de cocina", programa: "PNUD", link: "https://cursos.example/cocina", orden: 2, es_recomendado: true, activo: true, tiene_imagen: false,
  urls: { editar: `${BASE}5/editar/`, eliminar: `${BASE}5/eliminar/` }, ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [curso(), curso({ id: 6, nombre: "Otro", es_recomendado: false, activo: false, tiene_imagen: true, urls: { editar: `${BASE}6/editar/`, eliminar: `${BASE}6/eliminar/` } })],
  page: { number: 1, count: 25, is_paginated: true, previous: null, next: 2, range: [1, 2], query_without_page: "" }, messages: [], urls: { crear: `${BASE}crear/` }, ...over,
});
const field = (name: string, label: string, type: string, over: Record<string, unknown> = {}) => ({
  name, label, type, html_required: false, errors: [], max_length: null, min: null, accept: null, value: type === "checkbox" ? false : "", ...over,
});
const fields = () => [
  field("nombre", "Nombre", "text", { html_required: true, max_length: 255 }),
  field("link", "Link", "url", { html_required: true, max_length: 500 }),
  field("imagen", "Imagen", "file", { accept: "image/*" }),
  field("descripcion", "Descripcion", "text", { max_length: 300 }),
  field("programa_objetivo", "Programa objetivo", "select", { html_required: true, choices: [{ value: "", label: "Seleccionar programa" }, { value: "pnud", label: "PNUD" }, { value: "ambos", label: "PNUD y Alimentar Comunidad" }] }),
  field("es_recomendado", "Es recomendado", "checkbox"),
  field("orden", "Orden", "number", { html_required: true, min: "0", value: "0" }),
  field("activo", "Activo", "checkbox", { value: true }),
];
const form = (over: Record<string, unknown> = {}) => ({ edit_mode: false, fields: fields(), non_field_errors: [], messages: [], urls: { list: BASE }, ...over });
const baja = (over: Record<string, unknown> = {}) => ({ nombre: "Curso de cocina", cancel_url: BASE, messages: [], ...over });

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
function setup(url: string) {
  window.history.replaceState({}, "", url);
  return render(<App />);
}
const el = (id: string) => document.getElementById(id) as HTMLInputElement;
/** The form is not `novalidate`: like the native page, the browser blocks a submit with required fields empty. */
const fillRequired = () => {
  fireEvent.change(el("id_nombre"), { target: { value: "Curso" } });
  fireEvent.change(el("id_link"), { target: { value: "https://cursos.example/c" } });
  fireEvent.change(el("id_programa_objetivo"), { target: { value: "pnud" } });
};

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Comedor course catalog", () => {
  it("owns the four native URLs (trailing slash) and validates its payloads", () => {
    for (const path of [BASE, `${BASE}crear/`, `${BASE}5/editar/`, `${BASE}5/eliminar/`]) {
      expect(findRoute(path)?.route.name, path).toBe("comedores-cursos-app-mobile");
    }
    expect(findRoute(`${BASE}5/`)?.route.name).not.toBe("comedores-cursos-app-mobile");
    expect(findRoute("/comedores/configuracion/cursos-app-mobile")?.route.name).not.toBe("comedores-cursos-app-mobile");
    expect(listValid(list())).toBe(true);
    expect(listValid(list({ results: [curso({ urls: { editar: "https://x.example", eliminar: "/e" } })] }))).toBe(false);
    expect(formValid(form())).toBe(true);
    expect(formValid(form({ fields: [field("x", "X", "radio")] }))).toBe(false);
    expect(formValid(form({ fields: [field("x", "X", "select")] }))).toBe(false);
    expect(bajaValid(baja())).toBe(true);
    expect(bajaValid(baja({ cancel_url: "https://x.example" }))).toBe(false);
  });

  it("renders the list like the template: breadcrumb, columns, rows, actions and pagination", async () => {
    serve(list({ messages: [{ message: "Curso para app mobile creado correctamente.", tags: "success" }] }));
    setup(`${BASE}?page=1&x=y`);
    expect(await screen.findByText("Curso de cocina")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}?page=1&x=y`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Cursos App Mobile"));
    expect(Array.from(document.querySelectorAll(".breadcrumb-item")).map((li) => li.textContent)).toEqual(["Cursos App Mobile", "Listar"]);
    expect(screen.getByRole("link", { name: /Agregar/ }).getAttribute("href")).toBe(`${BASE}crear/`);
    expect(Array.from(document.querySelectorAll("thead th")).map((th) => th.textContent)).toEqual(["Nombre", "Programa objetivo", "Link", "Orden", "Recomendado", "Estado", "Imagen", "Acciones"]);
    const rows = Array.from(document.querySelectorAll("tbody tr")).map((tr) => Array.from(tr.querySelectorAll("td")).map((td) => td.textContent));
    expect(rows).toEqual([
      ["Curso de cocina", "PNUD", "https://cursos.example/cocina", "2", "Sí", "Activo", "No", "Editar Eliminar"],
      ["Otro", "PNUD", "https://cursos.example/cocina", "2", "No", "Inactivo", "Sí", "Editar Eliminar"],
    ]);
    const link = document.querySelector("tbody a[target='_blank']") as HTMLAnchorElement;
    expect(link.rel).toBe("noreferrer");
    expect(Array.from(document.querySelectorAll("tbody .btn")).map((a) => a.getAttribute("href"))[1]).toBe(`${BASE}5/eliminar/`);
    expect(Array.from(document.querySelectorAll(".pagination .page-item")).map((li) => li.textContent)).toEqual(["Volver", "1", "2", "Continuar"]);
    expect(Array.from(document.querySelectorAll(".pagination a")).map((a) => a.getAttribute("href"))).toEqual(["#", "?page=1", "?page=2", "?page=2"]);
    expect(screen.getByText("Se encontraron 25 resultados")).toBeTruthy();
    expect(screen.getByText("Curso para app mobile creado correctamente.")).toBeTruthy();
  });

  it("renders the empty list row and no result count", async () => {
    serve(list({ results: [], page: { number: 1, count: 0, is_paginated: false, previous: null, next: null, range: [], query_without_page: "" } }));
    setup(BASE);
    expect(await screen.findByText("No hay cursos cargados.")).toBeTruthy();
    expect(document.querySelector("tbody td")?.getAttribute("colspan")).toBe("8");
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("renders the create form as `form.as_p` with the native controls", async () => {
    serve(form());
    setup(`${BASE}crear/`);
    expect(await screen.findByText("Crear curso")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}crear/`, expect.anything());
    expect(Array.from(document.querySelectorAll(".breadcrumb-item")).map((li) => li.textContent)).toEqual(["Cursos App Mobile", "Crear"]);
    expect(Array.from(document.querySelectorAll("form p label")).map((l) => l.textContent)).toEqual([
      "Nombre:", "Link:", "Imagen:", "Descripcion:", "Programa objetivo:", "Es recomendado:", "Orden:", "Activo:",
    ]);
    expect(el("id_link").type).toBe("url");
    expect(el("id_nombre").required).toBe(true);
    expect(el("id_nombre").maxLength).toBe(255);
    expect(el("id_imagen").accept).toBe("image/*");
    expect(el("id_orden").min).toBe("0");
    expect(el("id_activo").checked).toBe(true);
    expect(document.querySelector(".card-primary form")?.getAttribute("enctype")).toBe("multipart/form-data");
    expect(document.querySelector(".card-primary form")?.hasAttribute("novalidate")).toBe(false);
    expect(screen.getByRole("button", { name: "Guardar" })).toBeTruthy();
    expect(document.querySelector(".card-footer a.btn-outline-secondary")?.getAttribute("href")).toBe(BASE);
  });

  it("posts the native multipart fields once, with the chosen image, then follows the redirect", async () => {
    serve(form());
    const assign = vi.spyOn(cursosNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: BASE }, status: 200 });
    setup(`${BASE}crear/`);
    await screen.findByText("Crear curso");
    fireEvent.change(el("id_nombre"), { target: { value: "Curso nuevo" } });
    fireEvent.change(el("id_link"), { target: { value: "https://cursos.example/nuevo" } });
    fireEvent.change(el("id_programa_objetivo"), { target: { value: "ambos" } });
    fireEvent.click(el("id_es_recomendado"));
    fireEvent.change(el("id_orden"), { target: { value: "3" } });
    fireEvent.click(el("id_activo"));
    const imagen = new File(["png"], "curso.png", { type: "image/png" });
    fireEvent.change(el("id_imagen"), { target: { files: [imagen] } });
    const guardar = screen.getByRole("button", { name: "Guardar" });
    fireEvent.click(guardar);
    fireEvent.click(guardar);
    await waitFor(() => expect(assign).toHaveBeenCalledWith(BASE));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}crear/`);
    const sent = webPost.mock.calls[0][1] as FormData;
    expect(Array.from(sent.keys())).toEqual(["nombre", "link", "imagen", "descripcion", "programa_objetivo", "es_recomendado", "orden"]);
    expect(sent.get("nombre")).toBe("Curso nuevo");
    expect(sent.get("programa_objetivo")).toBe("ambos");
    expect(sent.get("es_recomendado")).toBe("on");
    expect(sent.get("orden")).toBe("3");
    expect((sent.get("imagen") as File).name).toBe("curso.png");
    expect(sent.has("activo")).toBe(false);
  });

  it("shows the as_p error lists before their paragraphs after a rejected POST and never navigates", async () => {
    serve(form());
    const assign = vi.spyOn(cursosNavigation, "assign").mockImplementation(() => undefined);
    const rejected = form({
      fields: fields().map((f) => (f.name === "nombre" ? { ...f, value: "Mantiene", errors: ["Este campo es requerido."] } : f)),
      messages: [{ message: "Revise el formulario.", tags: "warning" }],
    });
    webPost.mockResolvedValueOnce({ data: rejected, status: 400 });
    setup(`${BASE}crear/`);
    await screen.findByText("Crear curso");
    fillRequired();
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Este campo es requerido.")).toBeTruthy();
    const lista = document.getElementById("id_nombre_error") as HTMLElement;
    expect(lista.className).toBe("errorlist");
    expect(lista.nextElementSibling?.tagName).toBe("P");
    expect(el("id_nombre").getAttribute("aria-describedby")).toBe("id_nombre_error");
    expect(el("id_nombre").getAttribute("aria-invalid")).toBe("true");
    expect(el("id_nombre").value).toBe("Mantiene");
    expect(screen.getByText("Revise el formulario.")).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: "Guardar" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("renders the edit form and posts to the edit endpoint", async () => {
    serve(form({ edit_mode: true, fields: fields().map((f) => (f.name === "nombre" ? { ...f, value: "Existente" } : f)) }));
    const assign = vi.spyOn(cursosNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: BASE }, status: 200 });
    setup(`${BASE}5/editar/`);
    expect(await screen.findByText("Editar curso")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}5/editar/`, expect.anything());
    expect(Array.from(document.querySelectorAll(".breadcrumb-item")).map((li) => li.textContent)).toEqual(["Cursos App Mobile", "Editar"]);
    expect(el("id_nombre").value).toBe("Existente");
    fillRequired();
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(BASE));
    expect(webPost.mock.calls[0][0]).toBe(`${API}5/editar/`);
  });

  it("renders the delete confirmation and posts the native soft delete once", async () => {
    serve(baja());
    const assign = vi.spyOn(cursosNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: BASE }, status: 200 });
    setup(`${BASE}5/eliminar/`);
    expect(await screen.findByText("Eliminar curso", { selector: "h3" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}5/eliminar/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Eliminar curso"));
    expect(document.querySelector(".card-body p")?.textContent).toBe("¿Desea eliminar el curso Curso de cocina?");
    expect(document.querySelector(".card-footer a")?.getAttribute("href")).toBe(BASE);
    const eliminar = screen.getByRole("button", { name: "Eliminar" });
    fireEvent.click(eliminar);
    fireEvent.click(eliminar);
    await waitFor(() => expect(assign).toHaveBeenCalledWith(BASE));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}5/eliminar/`);
  });

  it("reports a forbidden delete and does not retry", async () => {
    serve(baja());
    webPost.mockResolvedValueOnce({ data: { detail: "Usted no tiene permiso para realizar esta acción." }, status: 403 });
    setup(`${BASE}5/eliminar/`);
    await screen.findByText("Eliminar curso", { selector: "h3" });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    expect(await screen.findByText("Usted no tiene permiso para realizar esta acción.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Eliminar" }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
  });
});
