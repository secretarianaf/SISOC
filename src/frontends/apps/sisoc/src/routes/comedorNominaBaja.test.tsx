import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { bajaNavigation } from "./comedorIntervencionesBaja";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const DIRECTA_URL = "/comedores/3/nomina/9/eliminar/";
const ADMISION_URL = "/comedores/3/admision/4/nomina/9/eliminar/";
const DIRECTA_API = "web/comedores/comedores/3/nomina/9/eliminar/";
const ADMISION_API = "web/comedores/comedores/3/admision/4/nomina/9/eliminar/";
const data = (over: Record<string, unknown> = {}) => ({
  id: 9, object_name: "GÓMEZ, ANA - ACTIVO", confirm_text: "Dar de baja", cancel_text: "Cancelar",
  cancel_url: "/comedores/3/nomina/", messages: [], breadcrumb: { etiqueta: "Gómez, Ana - Activo", url: "/comedores/9" },
  cascade_preview: {
    total_afectados: 1, total_baja_logica: 1, total_borrado_fisico: 0,
    desglose_por_modelo: [{ modelo: "Nómina", cantidad: 1, modo: "baja_logica", ejemplos: ["Gómez, Ana - Activo"] }],
  },
  ...over,
});

function serve(body: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status }));
}
function setup(url = DIRECTA_URL) {
  window.history.replaceState({}, "", url);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Comedor nómina soft-delete confirmations", () => {
  it("owns both canonical URLs and nothing around them", () => {
    expect(findRoute(DIRECTA_URL)?.route.name).toBe("comedor-nomina-baja");
    expect(findRoute(ADMISION_URL)?.route.name).toBe("comedor-nomina-baja");
    expect(findRoute("/comedores/3/nomina/9/eliminar")?.route.name).not.toBe("comedor-nomina-baja");
    expect(findRoute("/comedores/3/nomina/")?.route.name).toBe("comedor-nomina");
  });

  it("renders the native direct confirmation with its preview, breadcrumb and cancel target", async () => {
    serve(data());
    setup();
    expect(await screen.findByText("Atención!")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(DIRECTA_API, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Acciones"));
    expect(document.querySelector(".error-content p")?.textContent).toBe("¿Estás seguro que deseas realizar una baja lógica en cascada del registro GÓMEZ, ANA - ACTIVO?");
    expect(document.querySelector(".alert-info")?.textContent).toBe("Total de registros afectados: 1Bajas lógicas: 1");
    expect(Array.from(document.querySelectorAll("tbody tr")).map((tr) => tr.textContent)).toEqual(["Nómina1Baja lógicaGómez, Ana - Activo"]);
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/comedores/3/nomina/");
    expect(Array.from(document.querySelectorAll(".breadcrumb-item")).map((li) => li.textContent)).toEqual(["Admisiones", "Gómez, Ana - Activo", "Detalle"]);
    expect(screen.getByRole("link", { name: "Gómez, Ana - Activo" }).getAttribute("href")).toBe("/comedores/9");
    expect((document.querySelector("input[name=csrfmiddlewaretoken]") as HTMLInputElement).value).toBe("synthetic-csrf-token");
  });

  it("reads the admission confirmation from its own endpoint and cancels to the admission nómina", async () => {
    serve(data({ cancel_url: "/comedores/3/admision/4/nomina/", cascade_preview: null }));
    setup(ADMISION_URL);
    expect(await screen.findByText("Atención!")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(ADMISION_API, expect.anything());
    expect(document.querySelector(".alert-info")).toBeNull();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/comedores/3/admision/4/nomina/");
  });

  it("posts once with the CSRF form to the native view and follows its redirect", async () => {
    serve(data());
    const assign = vi.spyOn(bajaNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/comedores/3/admision/4/nomina/" }, status: 200 });
    setup(ADMISION_URL);
    const confirm = await screen.findByRole("button", { name: "Dar de baja" });
    fireEvent.click(confirm);
    fireEvent.click(confirm);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/3/admision/4/nomina/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(ADMISION_API);
  });

  it("shows the native denial or an unconfirmed notice, never navigates and never retries", async () => {
    serve(data());
    const assign = vi.spyOn(bajaNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValueOnce({ data: { detail: "Usted no tiene permiso para realizar esta acción." }, status: 403 });
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    expect(await screen.findByText("Usted no tiene permiso para realizar esta acción.")).toBeTruthy();
    cleanup();
    serve(data());
    webPost.mockRejectedValueOnce(new Error("network"));
    setup();
    const confirm = await screen.findByRole("button", { name: "Dar de baja" });
    fireEvent.click(confirm);
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    fireEvent.click(confirm);
    expect(webPost).toHaveBeenCalledTimes(2);
    expect(assign).not.toHaveBeenCalled();
  });

  it("shows no confirmation data when the native lookup denies the read", async () => {
    serve({ detail: "No encontrado." }, 404);
    setup();
    expect(await screen.findByText("No se pudo cargar la página.")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(DIRECTA_API, expect.anything());
    expect(screen.queryByRole("button", { name: "Dar de baja" })).toBeNull();
    expect(screen.queryByText("Atención!")).toBeNull();
  });
});
