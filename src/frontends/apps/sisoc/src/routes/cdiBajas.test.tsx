import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { navigation } from "./cdiFrame";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const preview = {
  total_afectados: 2, total_baja_logica: 2, total_borrado_fisico: 0,
  desglose_por_modelo: [{ modelo: "Nomina Centro Infancia", cantidad: 1, modo: "baja_logica", ejemplos: ["Paz, Sofía (ID 7)"] }],
};
const centro = {
  id: 4, title: "Eliminar Centro de Desarrollo Infantil", object_name: "CDI SINTÉTICO", cascade_preview: preview,
  confirm_text: "Dar de baja", cancel_text: "Cancelar", cancel_url: "/centrodeinfancia/listar", messages: [],
};
const nomina = {
  id: 7, title: "Eliminar registro de nómina", object_name: "PAZ, SOFÍA", cascade_preview: null,
  confirm_text: "Dar de baja", cancel_text: "Cancelar", cancel_url: "/centrodeinfancia/4/nomina/", messages: [],
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
});

describe("CDI soft-delete confirmations route", () => {
  it("owns only the two native confirmation paths", () => {
    expect(findRoute("/centrodeinfancia/eliminar/4")?.params).toEqual({ kind: "centro", endpoint: "web/cdi/centros/4/eliminar/" });
    expect(findRoute("/centrodeinfancia/4/nomina/7/eliminar/")?.params).toEqual({ kind: "nomina", endpoint: "web/cdi/centros/4/nomina/7/eliminar/" });
    for (const other of ["/centrodeinfancia/eliminar/4/", "/centrodeinfancia/eliminar/x", "/centrodeinfancia/4/nomina/7/eliminar", "/centrodeinfancia/4/nomina/7/ver/"]) {
      expect(findRoute(other)?.route.name).not.toBe("cdi-bajas");
    }
  });

  it("renders the native centre confirmation with its cascade preview and cancel target", async () => {
    serve(centro);
    setup("/centrodeinfancia/eliminar/4");
    expect(await screen.findByText("CDI SINTÉTICO")).toBeDefined();
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/4/eliminar/", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Eliminar Centro de Desarrollo Infantil"));
    expect(screen.getByText(/baja lógica en cascada del registro/)).toBeDefined();
    expect(screen.getByText("Bajas lógicas: 2")).toBeDefined();
    const row = within(screen.getByRole("table")).getAllByRole("row")[1];
    expect(row.textContent).toBe("Nomina Centro Infancia1Baja lógicaPaz, Sofía (ID 7)");
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/centrodeinfancia/listar");
    const csrf = document.querySelector('input[name="csrfmiddlewaretoken"]') as HTMLInputElement;
    expect(csrf.value).toBe("synthetic-csrf-token");
  });

  it("posts the nómina soft delete once and follows the native redirect", async () => {
    serve(nomina);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/centrodeinfancia/4/nomina/" }, status: 200 });
    setup("/centrodeinfancia/4/nomina/7/eliminar/");
    expect(await screen.findByText("PAZ, SOFÍA")).toBeDefined();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.getByRole("link", { name: "Cancelar" }).getAttribute("href")).toBe("/centrodeinfancia/4/nomina/");
    fireEvent.click(screen.getByRole("button", { name: "Dar de baja" }));
    await waitFor(() => expect(navigation.assign).toHaveBeenCalledWith("/centrodeinfancia/4/nomina/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/cdi/centros/4/nomina/7/eliminar/");
    expect((webPost.mock.calls[0][1] as URLSearchParams).toString()).toBe("");
  });

  it("shows the native rejection instead of deleting", async () => {
    serve(centro);
    webPost.mockResolvedValue({ data: { detail: "El rol Auditoría tiene acceso de solo lectura." }, status: 403 });
    setup("/centrodeinfancia/eliminar/4");
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Dar de baja" })).toBeNull());
    expect(navigation.assign).not.toHaveBeenCalled();
  });

  it("reports an unconfirmed outcome without retrying", async () => {
    serve(centro);
    webPost.mockRejectedValueOnce(new Error("network"));
    setup("/centrodeinfancia/eliminar/4");
    fireEvent.click(await screen.findByRole("button", { name: "Dar de baja" }));
    expect(await screen.findByRole("alert")).toBeDefined();
    expect((screen.getByRole("button", { name: "Dar de baja" }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(navigation.assign).not.toHaveBeenCalled();
  });

  it("reports an out-of-scope object as not found", async () => {
    serve({ detail: "No encontrado." }, 404);
    setup("/centrodeinfancia/4/nomina/99/eliminar/");
    expect(await screen.findByText("No se encontró la página.")).toBeDefined();
    expect(screen.queryByRole("button", { name: "Dar de baja" })).toBeNull();
  });
});
