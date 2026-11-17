import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { navigation } from "./cdiFrame";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const centro = { id: 4, nombre: "CDI Sintético", url: "/centrodeinfancia/detalle/4" };
const detail = (over: Record<string, unknown> = {}) => ({
  id: 7, centro, fecha: "13/11/2026 16:29", tipo_intervencion: "Visita", subintervencion: "None", destinatario: "Centro",
  forma_contacto: "Presencial", observaciones: "Texto sintético.", messages: [],
  documentacion: { name: "documentacion/acta.pdf", descargar: "/api/web/cdi/intervenciones/7/documentacion/", eliminar: "/api/web/cdi/intervenciones/7/documentacion/eliminar/" },
  ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup() {
  window.history.replaceState({}, "", "/centrodeinfancia/intervencion/detalle/7/");
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

describe("CDI intervention detail route", () => {
  it("owns only the native detail path", () => {
    expect(findRoute("/centrodeinfancia/intervencion/detalle/7/")?.params).toEqual({ id: "7" });
    for (const other of ["/centrodeinfancia/intervencion/detalle/7", "/centrodeinfancia/intervencion/detalle/x/"]) {
      expect(findRoute(other)?.route.name).toBe("business");
    }
  });

  it("renders the native table and the authenticated download link", async () => {
    serve(detail());
    setup();
    expect(await screen.findByRole("heading", { name: "Detalle de Intervención" })).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("SISOC - Detalle de Intervención - Centro de Desarrollo Infantil"));
    expect(webGet).toHaveBeenCalledWith("web/cdi/intervenciones/7/", expect.anything());
    const rows = screen.getAllByRole("row").map((row) => Array.from(row.querySelectorAll("th,td")).map((c) => c.textContent));
    expect(rows).toEqual([
      ["Centro", "CDI Sintético"], ["Fecha y hora", "13/11/2026 16:29"], ["Tipo de intervención", "Visita"], ["Sub-intervención", "None"],
      ["Destinatario", "Centro"], ["Forma de contacto", "Presencial"], ["Observaciones", "Texto sintético."],
      ["Documentación adjunta", "documentacion/acta.pdfDescargarEliminar"],
    ]);
    const link = screen.getByRole("link", { name: "Descargar" });
    expect(link.getAttribute("href")).toBe("/api/web/cdi/intervenciones/7/documentacion/");
    expect(link.hasAttribute("download")).toBe(true);
    expect(screen.getByRole("link", { name: "CDI Sintético" }).getAttribute("href")).toBe("/centrodeinfancia/detalle/4");
  });

  it("shows the empty text and no delete button without a document or without delete rights", async () => {
    serve(detail({ documentacion: null }));
    setup();
    expect(await screen.findByText("No hay documentación adjunta.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Eliminar" })).toBeNull();
    cleanup();
    serve(detail({ documentacion: { name: "documentacion/acta.pdf", descargar: "/api/web/cdi/intervenciones/7/documentacion/", eliminar: null } }));
    setup();
    expect(await screen.findByRole("link", { name: "Descargar" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Eliminar" })).toBeNull();
  });

  it("confirms in the modal, posts once and follows the native redirect", async () => {
    serve(detail());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/centrodeinfancia/detalle/4" } });
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));
    expect(await screen.findByText("¿Está seguro de que desea eliminar la documentación adjunta?")).toBeTruthy();
    expect(webPost).not.toHaveBeenCalled();
    const confirm = document.getElementById("btn-confirmar-eliminar-documentacion") as HTMLButtonElement;
    fireEvent.click(confirm);
    fireEvent.click(confirm);
    await waitFor(() => expect(navigation.assign).toHaveBeenCalledWith("/centrodeinfancia/detalle/4"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe("/api/web/cdi/intervenciones/7/documentacion/eliminar/");
    expect((body as URLSearchParams).toString()).toBe("csrfmiddlewaretoken=synthetic-csrf-token");
  });

  it("cancels without writing", async () => {
    serve(detail());
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));
    fireEvent.click(await screen.findByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByText("¿Está seguro de que desea eliminar la documentación adjunta?")).toBeNull());
    expect(webPost).not.toHaveBeenCalled();
  });

  it("reports an unconfirmed outcome without resubmitting and keeps the page", async () => {
    serve(detail());
    webPost.mockRejectedValue(new Error("network"));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));
    fireEvent.click(document.getElementById("btn-confirmar-eliminar-documentacion") as HTMLButtonElement);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(navigation.assign).not.toHaveBeenCalled();
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("shows the access error on 403 and the not-found page on 404", async () => {
    serve({ detail: "No tiene permisos." }, 403);
    setup();
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Detalle de Intervención" })).toBeNull());
    cleanup();
    serve({ detail: "No encontrado." }, 404);
    setup();
    expect(await screen.findByText("No se encontró la página.")).toBeTruthy();
  });
});
