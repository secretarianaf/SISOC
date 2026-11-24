import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { pasPersonaFormRoute } from "./pasPersonaForm";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const options = (extra = {}) => ({
  provincias: [{ value: "1", label: "Provincia A" }], municipios: [{ value: "5", label: "Municipio A" }],
  estados: [{ value: "7", label: "Activo" }], generos: [{ value: "F", label: "Femenino" }],
  avisos_por_estado: { "7": [{ id: 11, text: "8301 - Alta" }] }, ...extra,
});
const edit = () => ({
  ...options({ estados: [], avisos_por_estado: {} }), id: 3,
  initial: { id_persona: "1", apellidos: "Apellido", nombres: "Nombre", dni: "30000001", cuit: "", genero: "", domicilio: "Calle 1", correo_electronico: "", telefono_celular: "", provincia: "1", municipio: "5" },
});

async function open(path: string, data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/"
    ? { data: readyContext, status: 200 } : { data, status }));
  window.history.replaceState({}, "", path);
  render(<App />);
  // jsdom does not fetch stylesheets: report them applied, as the browser would, until the page paints.
  const applyStyles = () => document.querySelectorAll('link[rel="stylesheet"]').forEach((l) => l.dispatchEvent(new Event("load")));
  if (status !== 200) {
    await waitFor(() => expect(document.querySelector('link[href$="comedorFormModerno.css"]')).toBeTruthy(), { timeout: 4000 }).catch(() => null);
    applyStyles();
    return;
  }
  await waitFor(() => { applyStyles(); expect(document.getElementById("pasForm")).toBeTruthy(); }, { timeout: 4000 });
}
const body = () => webPost.mock.calls[0][1] as URLSearchParams;
const type = (id: string, value: string) => fireEvent.change(document.getElementById(id)!, { target: { value } });
const submit = () => fireEvent.submit(document.getElementById("pasForm")!);

beforeEach(() => {
  vi.clearAllMocks();
  window.scrollTo = vi.fn();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => cleanup());

describe("pas/crear and pas/<pk>/editar", () => {
  it("owns exactly the two native paths", () => {
    expect(pasPersonaFormRoute.match("/pas/crear")).toEqual({ kind: "crear" });
    expect(pasPersonaFormRoute.match("/pas/12/editar")).toEqual({ kind: "editar", id: "12" });
    for (const other of ["/pas/crear/", "/pas/12", "/pas/x/editar", "/pas/12/eliminar", "/pas/listar"]) expect(pasPersonaFormRoute.match(other)).toBeNull();
  });

  it("prints the create form with the native texts, fields and sections", async () => {
    await open("/pas/crear", options());
    expect(document.title).toContain("PAS");
    expect(document.querySelector(".breadcrumb a")?.getAttribute("href")).toBe("/pas/listar");
    expect(document.querySelector(".breadcrumb .active")?.textContent).toBe("Crear");
    expect(screen.getByText("Crear registro PAS")).toBeTruthy();
    expect(screen.getByText("Datos principales de la persona titular")).toBeTruthy();
    expect(screen.getByText("Estado del titular")).toBeTruthy();
    expect([...document.querySelectorAll("#pasForm label")].map((l) => l.textContent)).toEqual([
      "IdPersona*", "Apellidos*", "Nombres*", "DNI*", "CUIT", "Género (RENAPER)", "Provincia*", "Municipio*",
      "Calle, número, piso y departamento", "Correo electrónico", "Teléfono celular", "Estado*", "Avisos*",
    ]);
    expect((document.getElementById("id_dni") as HTMLInputElement).type).toBe("number");
    expect(within(document.getElementById("pasForm")!).getByRole("link", { name: /Volver/ }).getAttribute("href")).toBe("/pas/listar");
    expect(screen.getByRole("button", { name: /Guardar registro/ }).className).toBe("btn btn-success");
    expect(screen.getByRole("link", { name: "Cancelar" })).toBeTruthy();
  });

  it("posts only the rendered fields, then shows the panel with the success message", async () => {
    await open("/pas/crear", options());
    webPost.mockResolvedValue({ status: 201, data: { id: 9, message: "Registro PAS creado correctamente." } });
    type("id_id_persona", "9001"); type("id_apellidos", "Pérez"); type("id_nombres", "Ana"); type("id_dni", "30111222");
    fireEvent.change(document.getElementById("id_provincia")!, { target: { value: "1" } });
    submit();
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    const [url] = webPost.mock.calls[0];
    expect(url).toBe("web/pas/personas/crear/");
    expect([...new Set([...body().keys()])].sort()).toEqual(["apellidos", "avisos", "cuit", "dni", "domicilio", "correo_electronico", "estado", "genero", "id_persona", "municipio", "nombres", "provincia", "telefono_celular"].filter((k) => k !== "avisos").sort());
    expect(body().get("apellidos")).toBe("Pérez");
    await waitFor(() => expect(window.location.pathname).toBe("/pas/panel-control/9"));
    expect(webGet.mock.calls.some(([u]) => u === "web/pas/panel/9/")).toBe(true);
  });

  it("shows the server rejections under their fields and keeps the typed values", async () => {
    await open("/pas/crear", options());
    webPost.mockResolvedValue({ status: 400, data: { errors: { dni: [{ message: "Ya existe un titular con este DNI.", code: "unique" }] } } });
    type("id_apellidos", "Pérez");
    submit();
    const error = await screen.findByText("Ya existe un titular con este DNI.");
    expect(error.closest(".invalid-feedback")?.id).toBe("id_dni_error");
    expect(document.getElementById("id_dni")!.className).toContain("is-invalid");
    expect((document.getElementById("id_apellidos") as HTMLInputElement).value).toBe("Pérez");
    expect(window.scrollTo).toHaveBeenCalled();
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("prints the edit form without the state section and posts to editar", async () => {
    await open("/pas/3/editar", edit());
    expect(await screen.findByText("Editar registro PAS")).toBeTruthy();
    expect(screen.queryByText("Estado del titular")).toBeNull();
    await waitFor(() => expect((document.getElementById("id_apellidos") as HTMLInputElement).value).toBe("Apellido"));
    const back = within(document.getElementById("pasForm")!).getByText(/Volver/).closest("a");
    expect(back?.getAttribute("href")).toBe("/pas/panel-control/3");
    expect(webGet.mock.calls.some(([u]) => u === "web/pas/personas/3/")).toBe(true);
    webPost.mockResolvedValue({ status: 200, data: { id: 3, message: "Registro PAS actualizado correctamente." } });
    submit();
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    expect(webPost.mock.calls[0][0]).toBe("web/pas/personas/3/editar/");
    expect(body().has("estado")).toBe(false);
    expect(body().get("municipio")).toBe("5");
  });

  it("never retries an answer it cannot confirm and shows the access screen on 403", async () => {
    await open("/pas/3/editar", edit());
    webPost.mockRejectedValue(new Error("timeout"));
    submit();
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo confirmar el resultado. Verificá el estado antes de reintentar.");
    expect(webPost).toHaveBeenCalledTimes(1);
    webPost.mockResolvedValue({ status: 403, data: { state: "forbidden" } });
    submit();
    await waitFor(() => expect(document.getElementById("pasForm")).toBeNull());
  });

  it("shows the access screen without the permission", async () => {
    await open("/pas/crear", { state: "forbidden" }, 403);
    await waitFor(() => expect(document.getElementById("pasForm")).toBeNull());
  });
});
