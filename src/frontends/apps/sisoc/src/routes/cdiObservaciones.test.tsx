import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { navigation } from "./cdiFrame";
import { sameOriginTarget } from "./cdiObservaciones";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const centro = { id: 4, nombre: "CDI Sintético", url: "/centrodeinfancia/detalle/4" };
const form = (over: Record<string, unknown> = {}) => ({
  centro,
  field: { name: "observacion", label: "Observación", required: true, rows: 4, placeholder: "Describa la observación" },
  value: "", errors: {}, messages: [], ...over,
});
const detail = {
  id: 9, centro, observador: "Ana Operadora", fecha: "09/11/2026 07:30", observacion: "Texto sintético.",
  urls: { editar: "/centrodeinfancia/observacion/9/editar/", eliminar: "/centrodeinfancia/observacion/9/eliminar/" }, messages: [],
};
const confirm = {
  id: 9, centro, object_name: "OBSERVACIÓN 2026-11-09 - CDI SINTÉTICO", confirm_text: "Dar de baja", cancel_text: "Cancelar",
  cancel_url: "/centrodeinfancia/observacion/9/", messages: [],
  cascade_preview: { total_afectados: 1, total_baja_logica: 1, total_borrado_fisico: 0, desglose_por_modelo: [
    { modelo: "Observaciones Centro De Desarrollo Infantil", cantidad: 1, modo: "baja_logica", ejemplos: ["Observación 2026-11-09 - CDI Sintético (ID 9)"] },
  ] },
};

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}

function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("CDI observations route", () => {
  it("owns only the four native observation paths", () => {
    expect(findRoute("/centrodeinfancia/4/observacion/crear/")?.params).toEqual({ mode: "create", centro: "4" });
    expect(findRoute("/centrodeinfancia/observacion/9/")?.params).toEqual({ mode: "detail", id: "9" });
    expect(findRoute("/centrodeinfancia/observacion/9/editar/")?.params).toEqual({ mode: "edit", id: "9" });
    expect(findRoute("/centrodeinfancia/observacion/9/eliminar/")?.params).toEqual({ mode: "delete", id: "9" });
    for (const other of ["/centrodeinfancia/observacion/9", "/centrodeinfancia/observacion/x/", "/centrodeinfancia/4/observacion/crear", "/centrodeinfancia/detalle/4"]) {
      expect(findRoute(other)?.route.name).toBe("business");
    }
  });

  it("renders the native create form and keeps next in the API query", async () => {
    serve(form());
    setup("/centrodeinfancia/4/observacion/crear/?next=/centrodeinfancia/detalle/4");
    const textarea = (await screen.findByLabelText(/Observación/)) as HTMLTextAreaElement;
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/4/observaciones/crear/?next=/centrodeinfancia/detalle/4", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Observación - Centro de Desarrollo Infantil"));
    expect(textarea.getAttribute("placeholder")).toBe("Describa la observación");
    expect(textarea.getAttribute("rows")).toBe("4");
    expect(textarea.className).toBe("form-control textarea");
    expect(textarea.required).toBe(true);
    expect(screen.getByRole("link", { name: "CDI Sintético" }).getAttribute("href")).toBe("/centrodeinfancia/detalle/4");
    expect(screen.getByText("Agregar observación al centro:", { exact: false }).tagName).toBe("H3");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("data-history-back")).toBe("true");
  });

  it("posts URL-encoded once and follows the native redirect", async () => {
    serve(form());
    let resolve: (v: unknown) => void = () => undefined;
    webPost.mockReturnValue(new Promise((r) => { resolve = r; }));
    setup("/centrodeinfancia/4/observacion/crear/?next=/centrodeinfancia/detalle/4");
    fireEvent.change(await screen.findByLabelText(/Observación/), { target: { value: "Visita." } });
    const button = screen.getByRole("button", { name: "Confirmar" });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(webPost).toHaveBeenCalledTimes(1);
    const [endpoint, body] = webPost.mock.calls[0];
    expect(endpoint).toBe("web/cdi/centros/4/observaciones/crear/?next=/centrodeinfancia/detalle/4");
    expect((body as URLSearchParams).toString()).toBe("observacion=Visita.");
    resolve({ data: { ok: true, redirect: "/centrodeinfancia/detalle/4" }, status: 200 });
    await waitFor(() => expect(navigation.assign).toHaveBeenCalledWith("/centrodeinfancia/detalle/4"));
  });

  it("shows the native field error and keeps the value", async () => {
    serve(form());
    webPost.mockResolvedValue({ data: form({ errors: { observacion: [{ message: "Este campo es requerido.", code: "required" }] } }), status: 400 });
    setup("/centrodeinfancia/4/observacion/crear/");
    // An empty textarea is blocked by the browser like the native `required`; submit the form directly.
    fireEvent.submit((await screen.findByRole("button", { name: "Confirmar" })).closest("form") as HTMLFormElement);
    const error = await screen.findByText("Este campo es requerido.");
    expect(error.closest("p")?.id).toBe("error_1_id_observacion");
    const textarea = screen.getByLabelText(/Observación/);
    expect(textarea.className).toBe("form-control textarea is-invalid");
    expect(textarea.getAttribute("aria-describedby")).toBe("id_observacion_error");
    expect(navigation.assign).not.toHaveBeenCalled();
  });

  it("shows the 403 page for the auditor veto and an uncertain result without retrying", async () => {
    serve(form());
    webPost.mockResolvedValueOnce({ data: { detail: "El rol Auditoría tiene acceso de solo lectura." }, status: 403 });
    setup("/centrodeinfancia/4/observacion/crear/");
    fireEvent.change(await screen.findByLabelText(/Observación/), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));
    expect(await screen.findByText("¡Ups! Algo salió mal.")).toBeDefined();
    cleanup();
    webPost.mockClear();
    serve(form());
    webPost.mockRejectedValueOnce(new Error("network"));
    setup("/centrodeinfancia/4/observacion/crear/");
    fireEvent.change(await screen.findByLabelText(/Observación/), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));
    expect(await screen.findByRole("alert")).toBeDefined();
    expect((screen.getByRole("button", { name: "Confirmar" }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("refuses a redirect to another origin", async () => {
    expect(sameOriginTarget("https://ejemplo.invalid/x")).toBeNull();
    expect(sameOriginTarget(`${window.location.origin}/centrodeinfancia/detalle/4`)).toBe("/centrodeinfancia/detalle/4");
    expect(sameOriginTarget("//ejemplo.invalid/x")).toBeNull();
    serve(form());
    webPost.mockResolvedValue({ data: { ok: true, redirect: "https://ejemplo.invalid/" }, status: 200 });
    setup("/centrodeinfancia/4/observacion/crear/");
    fireEvent.change(await screen.findByLabelText(/Observación/), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));
    expect(await screen.findByRole("alert")).toBeDefined();
    expect(navigation.assign).not.toHaveBeenCalled();
  });

  it("edits with the stored value on the edit endpoint", async () => {
    serve(form({ value: "Texto original." }));
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/centrodeinfancia/observacion/9/" }, status: 200 });
    setup("/centrodeinfancia/observacion/9/editar/");
    const textarea = (await screen.findByLabelText(/Observación/)) as HTMLTextAreaElement;
    expect(webGet).toHaveBeenCalledWith("web/cdi/observaciones/9/editar/", expect.anything());
    expect(textarea.value).toBe("Texto original.");
    fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));
    await waitFor(() => expect(navigation.assign).toHaveBeenCalledWith("/centrodeinfancia/observacion/9/"));
    expect(webPost.mock.calls[0][0]).toBe("web/cdi/observaciones/9/editar/");
  });

  it("renders the native detail card", async () => {
    serve(detail);
    setup("/centrodeinfancia/observacion/9/");
    expect(await screen.findByRole("heading", { name: "Observación 9" })).toBeDefined();
    await waitFor(() => expect(document.title).toBe("SISOC - Observación - CDI Sintético"));
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/centrodeinfancia/observacion/9/editar/");
    expect(screen.getByRole("link", { name: "Eliminar" }).className).toBe("btn btn-danger");
    expect(screen.getByText("Observador:").parentElement?.textContent).toBe("Observador: Ana Operadora");
    expect(screen.getByText("Fecha y hora:").parentElement?.textContent).toBe("Fecha y hora: 09/11/2026 07:30");
    expect(webGet).toHaveBeenCalledWith("web/cdi/observaciones/9/", expect.anything());
  });

  it("confirms the soft delete and goes to the native centre page", async () => {
    serve(confirm);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/centrodeinfancia/detalle/4" }, status: 200 });
    setup("/centrodeinfancia/observacion/9/eliminar/");
    expect(await screen.findByText("OBSERVACIÓN 2026-11-09 - CDI SINTÉTICO")).toBeDefined();
    expect(screen.getByText("Bajas lógicas: 1")).toBeDefined();
    expect(screen.queryByText(/Borrados físicos/)).toBeNull();
    const row = within(screen.getByRole("table")).getAllByRole("row")[1];
    expect(row.textContent).toBe("Observaciones Centro De Desarrollo Infantil1Baja lógicaObservación 2026-11-09 - CDI Sintético (ID 9)");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/centrodeinfancia/observacion/9/");
    fireEvent.click(screen.getByRole("button", { name: "Dar de baja" }));
    await waitFor(() => expect(navigation.assign).toHaveBeenCalledWith("/centrodeinfancia/detalle/4"));
    expect(webPost.mock.calls[0][0]).toBe("web/cdi/observaciones/9/eliminar/");
    expect((webPost.mock.calls[0][1] as URLSearchParams).toString()).toBe("");
  });

  it("reports a missing observation and a pending requirement", async () => {
    serve({ detail: "No encontrado." }, 404);
    setup("/centrodeinfancia/observacion/99/");
    expect(await screen.findByText("No se encontró la página.")).toBeDefined();
    cleanup();
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    setup("/centrodeinfancia/observacion/9/");
    expect(await screen.findByText("Necesitás actualizar tu contraseña para continuar.")).toBeDefined();
  });
});
