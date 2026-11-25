import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, waitFor, render, screen } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { arquitecturaValid } from "./coreArquitectura";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const datos = (over = {}) => ({ grafo_disponible: true, generado: "13/11/2026 10:00", urls: { data: "/arquitectura/grafo.json", back: "/novedades/" }, ...over });
const serve = (data: unknown, status = 200) => webGet.mockResolvedValue({ data, status });

let shell: HTMLLinkElement;
beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC - Shell";
  document.body.className = "layout-fixed dark-mode";
  document.documentElement.setAttribute("data-bs-theme", "dark");
  shell = document.createElement("link");
  shell.rel = "stylesheet"; shell.href = "/static/dist/css/adminlte.css";
  document.head.appendChild(shell);
  window.history.replaceState({}, "", "/arquitectura/");
});
afterEach(() => { cleanup(); shell.remove(); vi.restoreAllMocks(); });

describe("arquitectura (T03.01)", () => {
  it("owns only /arquitectura/ (the graph JSON stays native) and validates the payload", () => {
    expect(findRoute("/arquitectura/")?.route.name).toBe("core-arquitectura");
    expect(findRoute("/arquitectura/grafo.json")?.route.name).not.toBe("core-arquitectura");
    expect(arquitecturaValid(datos())).toBe(true);
    expect(arquitecturaValid(datos({ urls: { data: "http://evil/", back: "/novedades/" } }))).toBe(false);
    expect(arquitecturaValid(datos({ generado: 3 }))).toBe(false);
  });

  it("mounts the viewer container as a body child, loads the existing assets and restores the shell on leave", async () => {
    serve(datos());
    const { unmount } = render(<App />);
    await vi.waitFor(() => expect(document.getElementById("mapa")).not.toBeNull());
    const mapa = document.getElementById("mapa") as HTMLElement;
    expect(mapa.parentElement).toBe(document.body);
    expect(mapa.getAttribute("data-grafo")).toBe("/arquitectura/grafo.json");
    expect(mapa.getAttribute("data-volver")).toBe("/novedades/");
    expect(webGet.mock.calls[0][0]).toBe("web/core/arquitectura/");
    await waitFor(() => expect(document.title).toBe("Arquitectura de SISOC"));
    expect(document.body.className).toBe("");
    expect(document.documentElement.hasAttribute("data-bs-theme")).toBe(false);
    expect(shell.hasAttribute("disabled")).toBe(true);
    expect(document.head.querySelector('link[href="/static/arquitectura/mapa.css"]')).not.toBeNull();
    expect(document.body.querySelector('script[src="/static/arquitectura/mapa.js"]')).not.toBeNull();
    expect(document.head.querySelector('link[href^="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans"]')).not.toBeNull();
    unmount();
    expect(shell.hasAttribute("disabled")).toBe(false);
    await waitFor(() => expect(document.title).toBe("SISOC - Shell"));
    expect(document.body.className).toBe("layout-fixed dark-mode");
    expect(document.documentElement.getAttribute("data-bs-theme")).toBe("dark");
    expect(document.getElementById("mapa")).toBeNull();
    expect(document.head.querySelector('link[href="/static/arquitectura/mapa.css"]')).toBeNull();
    expect(document.body.querySelector("script[src]")).toBeNull();
  });

  it("explains that the graph has not been generated and offers the way back", async () => {
    serve(datos({ grafo_disponible: false, generado: null }));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "El mapa de arquitectura todavía no fue generado" })).toBeTruthy();
    expect(screen.getByText("python manage.py generar_mapa_arquitectura")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Volver a Novedades" }).getAttribute("href")).toBe("/novedades/");
    expect(document.getElementById("mapa")).toBeNull();
    expect(document.head.querySelector('link[href="/static/arquitectura/mapa.css"]')).toBeNull();
  });

  it("shows the access screen on 403 and the error screen on a malformed payload", async () => {
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    render(<App />);
    expect((await screen.findByRole("heading", { level: 1 })).textContent).toBe("Antes de continuar");
    cleanup();
    serve({ nope: true });
    render(<App />);
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar la página.");
  });
});
