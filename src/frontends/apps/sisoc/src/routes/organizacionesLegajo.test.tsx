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
  sections: [],
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

  it("mounts each React section in its placeholder, keeping the native HTML around it", async () => {
    serve(legajo({
      html: '<h1>Legajo</h1><div data-legajo-seccion="0"></div><p id="after">Después</p>',
      sections: [{
        kind: "convenios", program: "Línea Secos", color: "secos", is_tradicional: false, can_manage: true,
        rows: [
          { project: { id: 5, code: "P-1" }, url: "/organizaciones/proyectos/5/convenio/", summary: { suma: "$950", total: "$1.000", diferencia: "$50", coincide: false },
            convenio: { number: "CV-1", date: "15/01/2026", months: 12, total: "$1.000", imprevistos: "-", components: [{ label: "Componente SIPH", amount: "$150" }] } },
          { project: { id: 6, code: "P-2" }, url: "/organizaciones/proyectos/6/convenio/", summary: null, convenio: null },
        ],
      }],
    }));
    window.history.replaceState({}, "", "/organizaciones/detalle/8");
    render(<App />);
    expect(await screen.findByRole("heading", { level: 5, name: "Datos de Convenio · Línea Secos" })).toBeTruthy();
    const host = document.querySelector("[data-legajo-seccion='0']");
    expect(host?.querySelector("h5")).toBeTruthy();
    expect(host?.nextElementSibling?.id).toBe("after");
    expect(screen.getByText("Revisar montos")).toBeTruthy();
    expect(screen.getByText("Sin cargar")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Editar convenio" }).getAttribute("href")).toBe("/organizaciones/proyectos/5/convenio/");
    expect(screen.getByRole("link", { name: "Cargar convenio" }).getAttribute("href")).toBe("/organizaciones/proyectos/6/convenio/");
    expect(screen.getByText("Imprevistos no aplica: es solo para Línea Tradicional.")).toBeTruthy();
  });

  it("mounts the avales table in its placeholder", async () => {
    serve(legajo({
      html: '<div data-legajo-seccion="0"></div><p id="after">Después</p>',
      sections: [{ kind: "avales", can_manage: true, add_url: "/organizaciones/aval/crear/8", rows: [{ id: 3, name: "Beto", cuit: "-", edit_url: "/organizaciones/aval/editar/3", delete_url: "/organizaciones/aval/eliminar/3" }] }],
    }));
    window.history.replaceState({}, "", "/organizaciones/detalle/8");
    render(<App />);
    expect(await screen.findByRole("heading", { level: 5, name: "Avales" })).toBeTruthy();
    expect(document.querySelector("[data-legajo-seccion='0']")?.nextElementSibling?.id).toBe("after");
    expect((document.querySelector("[data-legajo-seccion='0']") as HTMLElement).style.display).toBe("contents");
    expect(screen.getByRole("link", { name: "Editar aval" }).getAttribute("href")).toBe("/organizaciones/aval/editar/3");
  });

  it("mounts the región section in its placeholder", async () => {
    serve(legajo({
      html: '<div data-legajo-seccion="0"></div><p id="after">Después</p>',
      sections: [{ kind: "region", can_manage: false, edit_url: null, has_data: true, region: "R", subzona: "S", territorials: [] }],
    }));
    window.history.replaceState({}, "", "/organizaciones/detalle/8");
    render(<App />);
    expect(await screen.findByRole("heading", { level: 5, name: "Datos de Región" })).toBeTruthy();
    expect(document.querySelector("[data-legajo-seccion='0']")?.nextElementSibling?.id).toBe("after");
  });

  it("mounts the documents section next to the convenios one, each in its own placeholder", async () => {
    serve(legajo({
      html: '<div data-legajo-seccion="0"></div><hr id="mid"><div data-legajo-seccion="1"></div>',
      sections: [
        { kind: "documentos", organization_id: 8, category: "Tipo documental", can_validate: false, can_send: false, rows: [] },
        { kind: "convenios", program: "Línea Secos", color: "secos", is_tradicional: false, can_manage: false, rows: [] },
        { kind: "desconocida" },
      ],
    }));
    window.history.replaceState({}, "", "/organizaciones/detalle/8");
    render(<App />);
    expect(await screen.findByText("No hay documentación configurada.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Agregar documento adicional/ })).toBeNull();
    expect(document.querySelector("[data-legajo-seccion='0'] #documentacion")).toBeTruthy();
    expect(document.querySelector("[data-legajo-seccion='1'] .card-secos")).toBeTruthy();
    expect(screen.getByText("No hay proyectos en esta línea.")).toBeTruthy();
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
