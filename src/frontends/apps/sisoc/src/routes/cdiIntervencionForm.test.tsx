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

const html = (value = "", error = "") =>
  `<p><label for="id_observaciones">Observaciones:</label>${error}<textarea name="observaciones" id="id_observaciones">${value}</textarea></p>` +
  `<p><label for="id_documentacion">Documentación:</label><input type="file" name="documentacion" id="id_documentacion"></p>`;
const payload = (over: Record<string, unknown> = {}) => ({ volver_url: "/centrodeinfancia/detalle/4", form_html: html(), messages: [], ...over });

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path = "/centrodeinfancia/intervencion/crear/4") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
  vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CDI intervention form route", () => {
  it("owns only the native create and edit paths", () => {
    expect(findRoute("/centrodeinfancia/intervencion/crear/4")?.params).toEqual({ mode: "create", centro: "4" });
    expect(findRoute("/centrodeinfancia/intervencion/editar/4/7")?.params).toEqual({ mode: "edit", centro: "4", id: "7" });
    for (const other of ["/centrodeinfancia/intervencion/crear/4/", "/centrodeinfancia/intervencion/editar/4/7/", "/centrodeinfancia/intervencion/crear/0", "/centrodeinfancia/intervencion/editar/4"]) {
      expect(findRoute(other)?.route.name).toBe("business");
    }
  });

  it("draws the native card with the server markup, Guardar and Volver", async () => {
    serve(payload());
    setup();
    await screen.findByLabelText("Observaciones:");
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/4/intervenciones/crear/", expect.anything());
    expect(screen.getByRole("button", { name: "Guardar" })).toBeDefined();
    expect(document.querySelector("form a.btn-secondary")?.getAttribute("href")).toBe("/centrodeinfancia/detalle/4");
    expect(document.querySelector("form a.btn-secondary")?.closest("form")?.getAttribute("enctype")).toBe("multipart/form-data");
  });

  it("loads the edit endpoint", async () => {
    serve(payload());
    setup("/centrodeinfancia/intervencion/editar/4/7");
    await screen.findByLabelText("Observaciones:");
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/4/intervenciones/7/editar/", expect.anything());
  });

  it("posts once as multipart with the token and follows the native redirect", async () => {
    serve(payload());
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/centrodeinfancia/detalle/4" }, status: 200 });
    setup();
    fireEvent.change(await screen.findByLabelText("Observaciones:"), { target: { value: "Nota" } });
    const button = screen.getByRole("button", { name: "Guardar" });
    fireEvent.click(button);
    fireEvent.click(button);
    await waitFor(() => expect(navigation.assign).toHaveBeenCalledWith("/centrodeinfancia/detalle/4"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/cdi/centros/4/intervenciones/crear/");
    const body = webPost.mock.calls[0][1] as FormData;
    expect(body.get("observaciones")).toBe("Nota");
    expect(body.get("csrfmiddlewaretoken")).toBe("synthetic-csrf-token");
    expect(body.has("documentacion")).toBe(true);
  });

  it("redraws a rejected form with its errors, scrolls to the top and allows a new try", async () => {
    serve(payload());
    webPost.mockResolvedValue({ data: payload({ form_html: html("Mal", '<ul class="errorlist"><li>Campo inválido.</li></ul>') }), status: 400 });
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Guardar" }));
    await screen.findByText("Campo inválido.");
    expect((screen.getByLabelText("Observaciones:") as HTMLTextAreaElement).value).toBe("Mal");
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
    expect(screen.getByRole("button", { name: "Guardar" }).hasAttribute("disabled")).toBe(false);
    expect(navigation.assign).not.toHaveBeenCalled();
  });

  it("reports an uncertain result without retrying and keeps a forbidden answer as access error", async () => {
    serve(payload());
    webPost.mockRejectedValueOnce(new Error("network"));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Guardar" }));
    await screen.findByRole("alert");
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Guardar" }).hasAttribute("disabled")).toBe(true);
    cleanup();
    serve(payload());
    webPost.mockResolvedValueOnce({ data: { detail: "No tiene permisos para esta acción." }, status: 403 });
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Guardar" })).toBeNull());
  });

  it("shows the page error for an invalid payload and the not found page for a 404", async () => {
    serve({ volver_url: "//evil", form_html: "", messages: [] });
    setup();
    await screen.findByText("No se pudo cargar la página.");
    cleanup();
    serve({ detail: "No encontrado." }, 404);
    setup("/centrodeinfancia/intervencion/editar/4/9");
    await screen.findByText("No se encontró la página.");
  });
});
