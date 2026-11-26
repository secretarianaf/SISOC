import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { ciudadanoColaRevisionNavigation, colaValid } from "./ciudadanoColaRevision";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const fila = (id: number, over = {}) => ({
  id, nombre_texto: `Apellido${id}, Nombre${id}`, identificador: `INT-${id}`, documento: "30111222", tipo_registro: "SIN_DNI",
  motivo: { texto: "Otro", descripcion: "Sin papeles" }, provincia: "Chaco", estado_revision: "PENDIENTE", editar_url: `/ciudadanos/editar/${id}`, ...over,
});
const cola = (over = {}) => ({
  total_pendientes: 2, total_filtrado: 2, estado: "pendiente",
  estados: [{ value: "pendiente", label: "Revisión Pendiente" }, { value: "descartada", label: "Solicitudes descartadas" }, { value: "aprobada", label: "Solicitudes aprobadas" }],
  filas: [fila(1), fila(2, { tipo_registro: "DNI_NO_VALIDADO_RENAPER", motivo: { texto: "Errores en la transcripción de datos manuales", descripcion: null } })],
  paginacion: { paginated: false, number: 1, previous: null, next: null, range: [], count: null }, cola_url: "/ciudadanos/revision/", messages: [], ...over,
});
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.history.replaceState({}, "", "/ciudadanos/revision/");
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("cola de revisión de identidad", () => {
  it("owns only /ciudadanos/revision/ and validates the payload", () => {
    expect(findRoute("/ciudadanos/revision/")?.route.name).toBe("ciudadano-cola-revision");
    expect(findRoute("/ciudadanos/revision")?.route.name).not.toBe("ciudadano-cola-revision");
    expect(colaValid(cola())).toBe(true);
    expect(colaValid(cola({ cola_url: "http://evil/" }))).toBe(false);
    expect(colaValid(cola({ paginacion: { paginated: true, number: 1, previous: "x", next: null, range: [], count: 1 } }))).toBe(false);
  });

  it("draws the counters, the filter, the rows and the pending actions", async () => {
    serve(cola());
    render(<App />);
    expect(await screen.findByText("Revisión manual")).toBeTruthy();
    expect(screen.getByText("2 ciudadanos requieren revisión manual.")).toBeTruthy();
    expect(screen.getByText("2 resultados")).toBeTruthy();
    expect(screen.getByText("Apellido1, Nombre1")).toBeTruthy();
    expect(screen.getByText("Sin DNI")).toBeTruthy();
    expect(screen.getByText("RENAPER no validado")).toBeTruthy();
    expect(screen.getByText("Sin papeles")).toBeTruthy();
    expect(screen.getAllByRole("link", { name: /Editar/ }).map((a) => a.getAttribute("href"))).toEqual(["/ciudadanos/editar/1", "/ciudadanos/editar/2"]);
    expect(screen.getAllByRole("button", { name: /Revisado/ }).length).toBe(2);
    expect(screen.getAllByRole("button", { name: /Descartar/ }).length).toBe(2);
    expect((screen.getByLabelText("Estado") as HTMLSelectElement).value).toBe("pendiente");
  });

  it("uses the singular and the resolved states without actions", async () => {
    serve(cola({
      total_pendientes: 1, total_filtrado: 1, estado: "aprobada",
      filas: [fila(3, { estado_revision: "APROBADA" }), fila(4, { estado_revision: "DESCARTADA", tipo_registro: "ESTANDAR" })],
    }));
    render(<App />);
    expect(await screen.findByText("1 ciudadano requiere revisión manual.")).toBeTruthy();
    expect(screen.getByText("1 resultado")).toBeTruthy();
    expect(screen.getByText("Aprobado")).toBeTruthy();
    expect(screen.getByText("Descartado")).toBeTruthy();
    expect(screen.getByText("Estándar")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Revisado/ })).toBeNull();
  });

  it("says so when the filter has no citizens", async () => {
    serve(cola({ filas: [], total_filtrado: 0 }));
    render(<App />);
    expect(await screen.findByText("No hay ciudadanos para el filtro seleccionado.")).toBeTruthy();
    expect(screen.getByText("0 resultados")).toBeTruthy();
  });

  it("keeps the filter in the pagination links", async () => {
    window.history.replaceState({}, "", "/ciudadanos/revision/?estado=descartada&page=2");
    serve(cola({ estado: "descartada", paginacion: { paginated: true, number: 2, previous: 1, next: 3, range: [1, 2, 3], count: 60 } }));
    render(<App />);
    expect(await screen.findByText("Se encontraron 60 resultados")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/ciudadanos/revision/?estado=descartada&page=2", expect.anything());
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?estado=descartada&page=3");
    expect(screen.getAllByRole("link", { name: "Volver" }).map((a) => a.getAttribute("href"))).toContain("?estado=descartada&page=1");
  });

  it("asks for the confirmation, posts once with the native next and follows the redirect", async () => {
    serve(cola());
    const assign = vi.spyOn(ciudadanoColaRevisionNavigation, "assign").mockImplementation(() => {});
    const confirmar = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValue(true);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/ciudadanos/revision/?estado=pendiente" }, status: 200 });
    render(<App />);
    const [primero] = await screen.findAllByRole("button", { name: /Descartar/ });
    fireEvent.click(primero);
    expect(confirmar).toHaveBeenLastCalledWith("¿Descartar esta solicitud?");
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.click(primero);
    fireEvent.click(primero);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/ciudadanos/revision/?estado=pendiente"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/ciudadanos/1/descartar-revision/");
    expect((webPost.mock.calls[0][1] as URLSearchParams).get("next")).toBe("/ciudadanos/revision/?estado=pendiente");
  });

  it("marks one as reviewed through its own endpoint and shows a refusal without navigating", async () => {
    serve(cola());
    const assign = vi.spyOn(ciudadanoColaRevisionNavigation, "assign").mockImplementation(() => {});
    vi.spyOn(window, "confirm").mockReturnValue(true);
    webPost.mockResolvedValueOnce({ data: { detail: "Sin permiso" }, status: 403 });
    webPost.mockRejectedValueOnce(new Error("network"));
    render(<App />);
    const [primero, segundo] = await screen.findAllByRole("button", { name: /Revisado/ });
    fireEvent.click(primero);
    expect((await screen.findByRole("alert")).textContent).toBe("Sin permiso");
    expect(webPost.mock.calls[0][0]).toBe("web/ciudadanos/1/marcar-revisado/");
    fireEvent.click(segundo);
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("No se pudo confirmar el resultado"));
    expect(webPost.mock.calls[1][0]).toBe("web/ciudadanos/2/marcar-revisado/");
    expect(assign).not.toHaveBeenCalled();
  });
});
