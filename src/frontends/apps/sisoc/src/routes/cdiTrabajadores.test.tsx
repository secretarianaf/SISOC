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

const URL_API = "web/cdi/centros/7/trabajadores/5/";
const ficha = (over: Record<string, unknown> = {}) => ({
  id: 5,
  label: "Gómez, Lucía",
  centro: { id: 7, nombre: "CDI Girasoles", url: "/centrodeinfancia/detalle/7" },
  editar_url: "/centrodeinfancia/7/trabajadores/5/editar/",
  eliminar_url: "/api/web/cdi/centros/7/trabajadores/5/eliminar/",
  sections: [
    { key: "institucion", icon: "fa-building", title: "Institución", subtitle: "Datos del CDI y fecha de carga", blocks: [
      { kind: "fields", spaced: false, items: [{ label: "Jurisdicción", value: "Mendoza" }, { label: "Código CDI", value: "—" }] },
    ] },
    { key: "formacion", icon: "fa-graduation-cap", title: "Formación y experiencia", subtitle: "Nivel educativo", blocks: [
      { kind: "fields", spaced: false, items: [{ label: "Nivel educativo", value: "—" }] },
      { kind: "badges", label: "Capacitaciones certificadas (últimos tres años)", tone: "warning", items: ["Primeros auxilios"], wrapper: "mt-3" },
    ] },
    { key: "discapacidad", icon: "fa-heartbeat", title: "Discapacidad", subtitle: "Condición, apoyos y CUD", blocks: [
      { kind: "fields", spaced: true, items: [{ label: "¿Tiene CUD?", value: "Sí" }] },
      { kind: "badges", label: "Tipo de discapacidad", tone: "danger", items: ["Visual"], wrapper: "" },
    ] },
  ],
  messages: [],
  ...over,
});

function serve(data: unknown, status = 200, sessionStatus = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(
    url === "web/session/" ? { data: sessionStatus === 200 ? readyContext : { detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, status: sessionStatus }
      : { data, status },
  ));
}

function setup(path = "/centrodeinfancia/7/trabajadores/5/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("CDI worker detail route", () => {
  it("owns only the native detail path", () => {
    expect(findRoute("/centrodeinfancia/7/trabajadores/5/")?.route.name).toBe("cdi-trabajador");
    expect(findRoute("/centrodeinfancia/7/trabajadores/5")?.route.name).toBe("business");
    expect(findRoute("/centrodeinfancia/7/trabajadores/0/")?.route.name).toBe("business");
    expect(findRoute("/centrodeinfancia/7/trabajadores/5/editar/")?.route.name).not.toBe("cdi-trabajador");
    expect(findRoute("/centrodeinfancia/7/trabajadores/asistencia/")?.route.name).not.toBe("cdi-trabajador");
  });

  it("loads the session and the API and draws heading, crumb and the edit and delete controls", async () => {
    serve(ficha());
    setup();
    await screen.findByRole("heading", { level: 3, name: "Institución" });
    expect(webGet).toHaveBeenCalledWith(URL_API, expect.anything());
    expect(webGet).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(document.title).toBe("SISOC - Trabajador — Gómez, Lucía"));
    expect(screen.getByRole("heading", { level: 3, name: "Detalle de trabajador" })).toBeDefined();
    expect(screen.getByRole("link", { name: "CDI Girasoles" }).getAttribute("href")).toBe("/centrodeinfancia/detalle/7");
    expect(screen.getByText("Gómez, Lucía", { selector: "li" }).className).toBe("breadcrumb-item active");
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/centrodeinfancia/7/trabajadores/5/editar/");
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeDefined();
  });

  it("draws fields and badge lists with the native wrapper classes and the last card spacing", async () => {
    serve(ficha());
    setup();
    const institucion = (await screen.findByRole("heading", { name: "Institución" })).closest(".section-card") as HTMLElement;
    expect(within(institucion).getByText("Datos del CDI y fecha de carga").className).toBe("section-subtitle");
    expect(within(institucion).getByText("Jurisdicción").nextElementSibling?.textContent).toBe("Mendoza");
    expect(within(institucion).getByText("Código CDI").nextElementSibling?.textContent).toBe("—");
    const formacion = screen.getByRole("heading", { name: "Formación y experiencia" }).closest(".section-card") as HTMLElement;
    const caps = within(formacion).getByText("Capacitaciones certificadas (últimos tres años)").parentElement as HTMLElement;
    expect(caps.className).toBe("mt-3");
    expect(within(caps).getByText("Primeros auxilios").className).toBe("badge");
    const discapacidad = screen.getByRole("heading", { name: "Discapacidad" }).closest(".section-card") as HTMLElement;
    expect(discapacidad.className).toBe("section-card mb-4");
    expect(institucion.className).toBe("section-card");
    expect(discapacidad.querySelector(".row")?.className).toBe("row g-3 mb-3");
    expect((within(discapacidad).getByText("Visual").parentElement?.parentElement as HTMLElement).hasAttribute("class")).toBe(false);
  });

  it("hides the controls the actor does not have", async () => {
    serve(ficha({ editar_url: null, eliminar_url: null }));
    setup();
    await screen.findByRole("heading", { name: "Institución" });
    expect(screen.queryByRole("link", { name: "Editar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Eliminar" })).toBeNull();
  });

  it("collapses a section with the mouse and with Enter and Space like the native script", async () => {
    serve(ficha());
    setup();
    const header = (await screen.findByRole("heading", { name: "Institución" })).closest(".section-header") as HTMLElement;
    expect(header.getAttribute("role")).toBe("button");
    expect(header.getAttribute("tabindex")).toBe("0");
    expect(header.getAttribute("aria-expanded")).toBe("true");
    const body = document.getElementById("section-institucion") as HTMLElement;
    fireEvent.click(header);
    expect(header.getAttribute("aria-expanded")).toBe("false");
    expect(header.className).toBe("section-header collapsed");
    expect(body.className).toBe("section-body collapse");
    fireEvent.keyDown(header, { key: "Enter" });
    expect(header.getAttribute("aria-expanded")).toBe("true");
    fireEvent.keyDown(header, { key: " " });
    expect(header.getAttribute("aria-expanded")).toBe("false");
  });

  it("opens the delete modal in place, closes it with Cancelar, the cross and Escape without writing", async () => {
    serve(ficha());
    setup();
    await screen.findByRole("heading", { name: "Institución" });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    const modal = document.getElementById("modalEliminarTrabajador") as HTMLElement;
    expect(modal.className).toBe("modal fade show d-block");
    expect(within(modal).getByText("¿Está seguro de eliminar a", { exact: false }).textContent).toBe("¿Está seguro de eliminar a Gómez, Lucía?");
    fireEvent.click(within(modal).getByRole("button", { name: "Cancelar" }));
    expect(document.getElementById("modalEliminarTrabajador")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    fireEvent.click(screen.getByRole("button", { name: "Cerrar" }));
    expect(document.getElementById("modalEliminarTrabajador")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    fireEvent.keyDown(document, { key: "Escape" });
    expect(document.getElementById("modalEliminarTrabajador")).toBeNull();
    expect(webPost).not.toHaveBeenCalled();
  });

  it("posts the delete once and follows the native redirect", async () => {
    serve(ficha());
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/centrodeinfancia/detalle/7" }, status: 200 });
    setup();
    await screen.findByRole("heading", { name: "Institución" });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    const form = (document.getElementById("modalEliminarTrabajador") as HTMLElement).querySelector("form") as HTMLFormElement;
    fireEvent.submit(form);
    fireEvent.submit(form);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodeinfancia/detalle/7"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe("web/cdi/centros/7/trabajadores/5/eliminar/");
  });

  it("announces a rejected delete, keeps the page and does not retry", async () => {
    serve(ficha());
    const alert = vi.spyOn(window, "alert").mockImplementation(() => undefined);
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { detail: "No tiene permisos para esta acción." }, status: 403 });
    setup();
    await screen.findByRole("heading", { name: "Institución" });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    fireEvent.submit((document.getElementById("modalEliminarTrabajador") as HTMLElement).querySelector("form") as HTMLFormElement);
    await waitFor(() => expect(alert).toHaveBeenCalledWith("No tiene permisos para esta acción."));
    expect(assign).not.toHaveBeenCalled();
    expect(webPost).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(within(document.getElementById("modalEliminarTrabajador") as HTMLElement).getByRole("button", { name: "Eliminar" }).hasAttribute("disabled")).toBe(false));
  });

  it("announces a connection failure on the delete", async () => {
    serve(ficha());
    const alert = vi.spyOn(window, "alert").mockImplementation(() => undefined);
    webPost.mockRejectedValue(new Error("network"));
    setup();
    await screen.findByRole("heading", { name: "Institución" });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    fireEvent.submit((document.getElementById("modalEliminarTrabajador") as HTMLElement).querySelector("form") as HTMLFormElement);
    await waitFor(() => expect(alert).toHaveBeenCalledWith("Error de conexión. Intentá nuevamente."));
  });

  it("shows the not found, forbidden and invalid payload states", async () => {
    serve({}, 404);
    setup();
    expect((await screen.findByRole("alert")).textContent).toBe("No se encontró la página.");
    cleanup();
    serve(ficha({ sections: [{ key: 1 }] }));
    setup();
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar la página.");
    cleanup();
    serve({ detail: "x" }, 403);
    setup();
    await waitFor(() => expect(screen.queryByText("Cargando…")).toBeNull());
    expect(screen.queryByRole("heading", { name: "Institución" })).toBeNull();
  });
});
