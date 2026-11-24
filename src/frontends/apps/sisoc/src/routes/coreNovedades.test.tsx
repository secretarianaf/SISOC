import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, waitFor, fireEvent, render, screen } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { novedadesValid } from "./coreNovedades";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const novedades = (over = {}) => ({
  current_version: "2026.02.03",
  versions: [
    { version: "2026.02.03", html: "<h3>Added</h3><ul><li>Feature <strong>A</strong></li></ul>" },
    { version: "2026.01.23", html: "<p>Bug B</p>" },
  ],
  error: false, urls: { architecture: "/arquitectura/", home: "/inicio/" }, messages: [], ...over,
});
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.history.replaceState({}, "", "/novedades/");
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("novedades (T02.01)", () => {
  it("owns only /novedades/ and validates the payload", () => {
    expect(findRoute("/novedades/")?.route.name).toBe("core-novedades");
    expect(findRoute("/novedades")?.route.name).not.toBe("core-novedades");
    expect(novedadesValid(novedades())).toBe(true);
    expect(novedadesValid(novedades({ versions: [{ version: 1 }] }))).toBe(false);
    expect(novedadesValid(novedades({ urls: { architecture: "http://evil/", home: "/inicio/" } }))).toBe(false);
  });

  it("draws the last update, the architecture link and the backend-parsed blocks", async () => {
    serve(novedades());
    render(<App />);
    expect(await screen.findByText(/Última actualización: 2026.02.03/)).toBeTruthy();
    const link = screen.getByRole("link", { name: /Ver arquitectura/ });
    expect(link.getAttribute("href")).toBe("/arquitectura/");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener");
    expect(screen.getByText("Versión SISOC 2026.02.03", { exact: false })).toBeTruthy();
    expect(screen.getByText("A").tagName).toBe("STRONG");
    expect(screen.getByRole("heading", { name: "Novedades del Sistema" })).toBeTruthy();
    expect(webGet.mock.calls.map((c) => c[0])).toContain("web/core/novedades/");
    // The native template defines no title block: the document title is just "SISOC -".
    await waitFor(() => expect(document.title).toBe("SISOC -"));
  });

  it("opens the first block and toggles each one with its Ver detalle button", async () => {
    serve(novedades());
    const { container } = render(<App />);
    await screen.findByText(/Última actualización/);
    const first = container.querySelector("#version-1") as HTMLElement;
    const second = container.querySelector("#version-2") as HTMLElement;
    expect(first.className).toBe("collapse show");
    expect(second.className).toBe("collapse");
    const [b1, b2] = screen.getAllByRole("button", { name: "Ver detalle" });
    expect(b1.getAttribute("aria-expanded")).toBe("true");
    expect(b2.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(b2);
    expect(second.className).toBe("collapse show");
    expect(b2.getAttribute("aria-expanded")).toBe("true");
    fireEvent.click(b1);
    expect(first.className).toBe("collapse");
  });

  it("shows the native error alert when the changelog could not be read", async () => {
    serve(novedades({ error: true, versions: [] }));
    render(<App />);
    expect(await screen.findByText("No fue posible obtener las novedades del sistema en este momento.")).toBeTruthy();
    expect(screen.getByText("Por favor, intente más tarde o contacte al administrador del sistema.")).toBeTruthy();
    expect(screen.queryByText(/Última actualización/)).toBeNull();
  });
});
