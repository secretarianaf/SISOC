import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { dispositivoEliminarNavigation } from "./dispositivoEliminar";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const datos = (over: Record<string, unknown> = {}) => ({
  id: 7, nombre_institucion: "Refugio Siete", cancel_url: "/dispositivos/7/", messages: [], ...over,
});

function serve(page: { data: unknown; status?: number }) {
  webGet.mockImplementation((url: string) => {
    if (url === "web/session/") return Promise.resolve({ data: readyContext, status: 200 });
    if (url === "web/dispositivos/7/eliminar/") return Promise.resolve({ data: page.data, status: page.status ?? 200 });
    return Promise.reject(new Error(`unexpected ${url}`));
  });
}
function setup(path = "/dispositivos/7/eliminar") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("Dispositivo delete confirmation", () => {
  it("owns only the canonical delete path", () => {
    expect(findRoute("/dispositivos/7/eliminar")?.route.name).toBe("dispositivo-eliminar");
    expect(findRoute("/dispositivos/7/eliminar")?.params).toEqual({ id: "7" });
    for (const other of ["/dispositivos/7/eliminar/", "/dispositivos/07/eliminar", "/dispositivos/eliminar", "/dispositivos/7/"]) {
      expect(findRoute(other)?.route.name).not.toBe("dispositivo-eliminar");
    }
  });

  it("renders the native confirmation with the projected data", async () => {
    serve({ data: datos() });
    setup();
    await screen.findByRole("heading", { name: "Confirmar eliminación" });
    await waitFor(() => expect(document.title).toBe("SISOC - Eliminar dispositivo"));
    const pregunta = screen.getByText(/¿Seguro que desea eliminar el dispositivo/);
    expect(pregunta.querySelector("strong")?.textContent).toBe("Refugio Siete");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/dispositivos/7/");
    expect(webGet).toHaveBeenCalledWith("web/dispositivos/7/eliminar/", expect.anything());
  });

  it("submits the native POST once to the canonical URL with the CSRF token", async () => {
    const submit = vi.spyOn(dispositivoEliminarNavigation, "submit").mockImplementation(() => undefined);
    serve({ data: datos() });
    setup();
    const boton = await screen.findByRole("button", { name: "Eliminar" });
    fireEvent.click(boton);
    fireEvent.click(boton);

    expect(submit).toHaveBeenCalledTimes(1);
    const form = submit.mock.calls[0][0];
    expect(form.method).toBe("post");
    expect(new URL(form.action).pathname).toBe("/dispositivos/7/eliminar");
    expect(new FormData(form).get("csrfmiddlewaretoken")).toBe("synthetic-csrf-token");
    expect((boton as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).not.toHaveBeenCalled();
  });

  it("shows the native denial without data and never retries the read", async () => {
    serve({ data: { detail: "No tiene permiso." }, status: 403 });
    setup();
    await waitFor(() => expect(screen.queryByText("Cargando…")).toBeNull());
    expect(screen.queryByRole("button", { name: "Eliminar" })).toBeNull();
    expect(screen.queryByText("Refugio Siete")).toBeNull();
    expect(webGet.mock.calls.filter(([url]) => url === "web/dispositivos/7/eliminar/")).toHaveLength(1);
  });

  it("reports a missing or out-of-scope device as not found", async () => {
    serve({ data: { detail: "No encontrado." }, status: 404 });
    setup();
    expect(await screen.findByText("No se encontró la página.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Eliminar" })).toBeNull();
  });
});
