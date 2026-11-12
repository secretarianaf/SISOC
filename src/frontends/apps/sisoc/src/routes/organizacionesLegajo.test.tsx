import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { legajoScripts, legajoValid } from "./organizacionesLegajo";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const SCRIPT = "/static/custom/js/organizacionesDocumentos.js";
const legajo = (over: Record<string, unknown> = {}) => ({
  title: "Organización: Ñandú <Sur>",
  html: '<div class="legajo-header"><h1>Ñandú &lt;Sur&gt;</h1><a href="/organizaciones/editar/8" class="btn">Editar</a></div>',
  scripts: [SCRIPT],
  messages: [],
  ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  legajoScripts.loaded.clear();
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Organizaciones legajo route", () => {
  it("owns only the native detail path of a numeric id", () => {
    expect(findRoute("/organizaciones/detalle/8")?.route.name).toBe("comedores-organizaciones");
    for (const other of ["/organizaciones/detalle/8/", "/organizaciones/detalle/0", "/organizaciones/detalle/x", "/organizaciones/editar/x"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-organizaciones");
    }
  });

  it("mounts the native fragment, keeps the query and runs the documentation initializers once", async () => {
    const load = vi.spyOn(legajoScripts, "load").mockResolvedValue();
    const init = vi.fn();
    const bind = vi.fn();
    Object.assign(window, { orgInitRectificarModal: init, orgInitDocumentoAdicional: init, orgBindDynamicHandlers: bind });
    serve(legajo({ messages: [{ message: "Se reinicio la documentacion del legajo porque cambio el Tipo de Entidad.", level: "warning" }] }));
    window.history.replaceState({}, "", "/organizaciones/detalle/8?programa=2&seccion=rendiciones");
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "Ñandú <Sur>" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/comedores/organizaciones/8/?programa=2&seccion=rendiciones", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Organización: Ñandú <Sur>"));
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/organizaciones/editar/8");
    await waitFor(() => expect(bind).toHaveBeenCalledTimes(1));
    expect(load).toHaveBeenCalledWith(SCRIPT);
    expect(init).toHaveBeenCalledTimes(2);
    expect(await screen.findByText("Se reinicio la documentacion del legajo porque cambio el Tipo de Entidad.")).toBeTruthy();
    for (const name of ["orgInitRectificarModal", "orgInitDocumentoAdicional", "orgBindDynamicHandlers"]) delete (window as unknown as Record<string, unknown>)[name];
  });

  it("injects each native script one time", async () => {
    const first = legajoScripts.load("/static/x.js");
    const second = legajoScripts.load("/static/x.js");
    expect(second).toBe(first);
    const tags = document.querySelectorAll('script[src="/static/x.js"]');
    expect(tags).toHaveLength(1);
    tags[0].dispatchEvent(new Event("load"));
    await first;
    tags[0].remove();
  });

  it("shows the access screen on 403, an error on 404 and on an invalid payload", async () => {
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    window.history.replaceState({}, "", "/organizaciones/detalle/8");
    render(<App />);
    await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
    expect(document.querySelector(".legajo-header")).toBeNull();
    cleanup();
    serve({ detail: "No encontrado." }, 404);
    render(<App />);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(legajoValid(legajo())).toBe(true);
    expect(legajoValid(legajo({ scripts: ["https://evil.example/x.js"] }))).toBe(false);
    expect(legajoValid(legajo({ html: 1 }))).toBe(false);
  });
});
