import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { navigation } from "./cdfFrame";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const HEADERS = [
  { title: "Centro", sortable: true, sort_key: "centro" }, { title: "Actividad", sortable: true, sort_key: "actividad" },
  { title: "Días", sortable: true, sort_key: "dias" }, { title: "Horario Desde", sortable: true, sort_key: "horariosdesde" },
  { title: "Horario Hasta", sortable: true, sort_key: "horarioshasta" }, { title: "Estado", sortable: true, sort_key: "estado" },
];
const fila = (id: number, centro: string, actividad: string, dias: string[], over: Record<string, unknown> = {}) => ({
  id, centro, actividad, dias, dias_vacio: "core.Dia.None", horariosdesde: "09:00", horarioshasta: "10:30", estado_display: "En curso",
  urls: { detail: `/centrodefamilia/centros/actividades/${id}/detalle/` }, ...over,
});
const lista = (over: Record<string, unknown> = {}) => ({
  headers: HEADERS, messages: [],
  results: [fila(1, "Alfa", "Tenis", []), fila(2, "Zeta", "Ajedrez", ["Lunes", "Martes"], { horariosdesde: "08:00" }), fila(3, "Beta", "Yoga", ["Viernes"], { horariosdesde: "10:00" })],
  ...over,
});
const catalogo = (over: Record<string, unknown> = {}) => ({
  fields: [
    { name: "categoria", label: "Categoría", required: true, widget: "select", value: "", attrs: {}, html: { class: "form-control form-control-sm" },
      choices: [{ value: "", label: "---------" }, { value: "3", label: "Deportes" }] },
    { name: "nombre", label: "Nombre de la Actividad", required: true, widget: "text", value: "", attrs: { maxlength: "200" },
      html: { class: "form-control form-control-sm", placeholder: "Ej. Taller de oficio" } },
  ],
  errors: {}, non_field_errors: [], urls: { cancel: "/centrodefamilia/centros/" }, messages: [], ...over,
});

function serve(page: unknown, api: string) {
  webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
    : url === api ? Promise.resolve({ data: page, status: 200 }) : Promise.reject(new Error(url))));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const celdas = () => [...document.querySelectorAll("tbody tr")].map((tr) => tr.querySelector("td")?.textContent);

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CDF activity list route", () => {
  it("owns only the native list and catalog paths", () => {
    expect(findRoute("/centrodefamilia/actividades/")?.route.name).toBe("cdf-actividad-lista");
    expect(findRoute("/centrodefamilia/actividades/nueva/")?.params).toEqual({ catalogo: true });
    expect(findRoute("/centrodefamilia/actividades/x/")?.route.name).not.toBe("cdf-actividad-lista");
  });

  it("renders the table with the native empty title and buttons, the days text and the manager quirk", async () => {
    serve(lista(), "web/cdf/actividades/");
    setup("/centrodefamilia/actividades/");
    await screen.findByRole("table");
    await waitFor(() => expect(document.title).toBe("SISOC - Actividades"));
    expect(document.querySelector("h2.display-4")?.textContent).toBe("");
    expect(document.querySelector(".row.mt-3")?.children.length).toBe(0);
    expect([...document.querySelectorAll("thead th")].map((th) => th.textContent)).toEqual(["Centro ", "Actividad ", "Días ", "Horario Desde ", "Horario Hasta ", "Estado "]);
    const filas = [...document.querySelectorAll("tbody tr")].map((tr) => [...tr.querySelectorAll("td")].map((td) => td.textContent));
    expect(filas[0]).toEqual(["Alfa", "Tenis", "core.Dia.None", "09:00", "10:30", "En curso"]);
    expect(filas[1][2]).toBe("Lunes , Martes");
    expect(screen.getByRole("link", { name: "Ajedrez" }).getAttribute("href")).toBe("/centrodefamilia/centros/actividades/2/detalle/");
    expect(document.querySelector("td[data-dias='Lunes, Martes']")).toBeTruthy();
    expect(document.querySelector(".badge.badge-info")?.textContent).toBe("En curso");
  });

  it("forwards the page query (centro filter) to the API", async () => {
    serve(lista({ results: [] }), "web/cdf/actividades/?centro=4");
    setup("/centrodefamilia/actividades/?centro=4");
    expect(await screen.findByText("No hay actividades registradas.")).toBeTruthy();
    expect(document.querySelector("tbody td")?.getAttribute("colspan")).toBe("6");
  });

  it("sorts locally in three states like listSort.js and never calls the API again", async () => {
    serve(lista(), "web/cdf/actividades/");
    setup("/centrodefamilia/actividades/");
    await screen.findByRole("table");
    const cabecera = (name: string) => document.querySelector<HTMLElement>(`th[data-column=${name}]`)!;
    fireEvent.click(cabecera("centro"));
    expect(celdas()).toEqual(["Alfa", "Beta", "Zeta"]);
    expect(cabecera("centro").className).toContain("sort-asc");
    expect(cabecera("centro").querySelector("i")?.className).toContain("fa-sort-up");
    fireEvent.click(cabecera("centro"));
    expect(celdas()).toEqual(["Zeta", "Beta", "Alfa"]);
    fireEvent.click(cabecera("centro"));
    expect(cabecera("centro").className).not.toContain("sort-");
    expect(cabecera("centro").querySelector("i")?.className).toContain("fa-sort");
    fireEvent.click(cabecera("horariosdesde"));
    expect(celdas()).toEqual(["Zeta", "Alfa", "Beta"]);
    expect(webGet).toHaveBeenCalledTimes(2);
  });
});

describe("CDF activity catalog route", () => {
  it("renders the native card with the plain fields and the cancel link", async () => {
    serve(catalogo(), "web/cdf/actividades/nueva/");
    setup("/centrodefamilia/actividades/nueva/");
    await screen.findByText("Nueva Actividad", { selector: ".card-header" });
    await waitFor(() => expect(document.title).toBe("SISOC - Nueva Actividad"));
    expect(document.querySelector("#id_categoria")?.className).toBe("form-control form-control-sm");
    expect(document.querySelector<HTMLInputElement>("#id_nombre")?.placeholder).toBe("Ej. Taller de oficio");
    expect(document.querySelector<HTMLInputElement>("#id_nombre")?.getAttribute("maxlength")).toBe("200");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/centrodefamilia/centros/");
    expect(document.querySelector("button.btn-outline-success")?.textContent).toBe("Guardar");
  });

  it("posts once with the CSRF token and follows the native redirect", async () => {
    serve(catalogo(), "web/cdf/actividades/nueva/");
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { url: "/centrodefamilia/centros/" } });
    setup("/centrodefamilia/actividades/nueva/");
    const boton = await screen.findByRole("button", { name: "Guardar" });
    fireEvent.change(document.querySelector("#id_categoria") as HTMLSelectElement, { target: { value: "3" } });
    fireEvent.change(document.querySelector("#id_nombre") as HTMLInputElement, { target: { value: "Natacion" } });
    fireEvent.click(boton);
    fireEvent.click(boton);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodefamilia/centros/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe("web/cdf/actividades/nueva/");
    expect((body as FormData).get("categoria")).toBe("3");
    expect((body as FormData).get("nombre")).toBe("Natacion");
    expect((body as FormData).get("csrfmiddlewaretoken")).toBe("synthetic-csrf-token");
  });

  it("shows the field errors of a 400 as the native error lists and keeps the values", async () => {
    serve(catalogo(), "web/cdf/actividades/nueva/");
    webPost.mockResolvedValueOnce({ status: 400, data: catalogo({
      fields: catalogo().fields.map((f) => (f.name === "nombre" ? { ...f, value: "Solo" } : f)),
      errors: { categoria: [{ message: "Este campo es requerido.", code: "required" }] }, non_field_errors: ["Aviso general"],
    }) });
    setup("/centrodefamilia/actividades/nueva/");
    await screen.findByRole("button", { name: "Guardar" });
    fireEvent.change(document.querySelector("#id_nombre") as HTMLInputElement, { target: { value: "Solo" } });
    fireEvent.change(document.querySelector("#id_categoria") as HTMLSelectElement, { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(document.querySelector(".mb-3 ul.errorlist li")?.textContent).toBe("Este campo es requerido."));
    expect(document.querySelector("ul.errorlist.nonfield li")?.textContent).toBe("Aviso general");
    expect((document.querySelector("#id_nombre") as HTMLInputElement).value).toBe("Solo");
    expect((screen.getByRole("button", { name: "Guardar" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("does not repeat an uncertain save", async () => {
    serve(catalogo(), "web/cdf/actividades/nueva/");
    webPost.mockRejectedValue(Object.assign(new Error("timeout"), { response: { status: 504 } }));
    setup("/centrodefamilia/actividades/nueva/");
    const boton = await screen.findByRole("button", { name: "Guardar" });
    fireEvent.change(document.querySelector("#id_categoria") as HTMLSelectElement, { target: { value: "3" } });
    fireEvent.change(document.querySelector("#id_nombre") as HTMLInputElement, { target: { value: "X" } });
    fireEvent.click(boton);
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe(
      "No se pudo confirmar el resultado. Verificá el estado antes de reintentar."));
    expect(webPost).toHaveBeenCalledTimes(1);
  });
});
