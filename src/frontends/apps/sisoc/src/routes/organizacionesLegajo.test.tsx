import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { legajoValid } from "./organizacionesLegajo";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const datos = (over: Record<string, unknown> = {}) => ({
  edit_url: "/organizaciones/editar/8", name: "Ñandú <Sur>", cuit: "20111111112", tipo: "Asociación civil", subtipo: "Mutual", phone: "1140000000", email: "a@b.org",
  programs: ["Alimentar comunidad", "Abordaje comunitario - Línea Secos"], comedores_count: 2, provincia: "Prov", municipio: "-", localidad: "-", partido: "-", domicilio: "Mitre 1",
  expiry: { text: "31/01/2999", state: "vigente" }, created: "01/10/2026 09:30", ...over,
});
const header = (over: Record<string, unknown> = {}) => ({
  name: "Ñandú <Sur>", cuit: "20111111112", tipo: "Asociación civil", subtipo: "Mutual", history_url: "/audit/x/", edit_url: "/organizaciones/editar/8", delete_url: "/organizaciones/eliminar/8", ...over,
});
const legajo = (over: Record<string, unknown> = {}) => ({
  title: "Organización: Ñandú <Sur>", css: ".legajo-header{color:red}", header: header(), selector: { kind: "none" }, datos: datos(), blocks: [], messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
const open = (path = "/organizaciones/detalle/8") => { window.history.replaceState({}, "", path); return render(<App />); };

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Organizaciones legajo route", () => {
  it("owns only the native detail path of a numeric id", () => {
    expect(findRoute("/organizaciones/detalle/8")?.route.name).toBe("comedores-organizaciones");
    for (const other of ["/organizaciones/detalle/8/", "/organizaciones/detalle/0", "/organizaciones/detalle/x", "/organizaciones/editar/x"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-organizaciones");
    }
  });

  it("draws the header, the data card and the native styles, keeping the query", async () => {
    serve(legajo({ messages: [{ message: "Se reinicio la documentacion del legajo porque cambio el Tipo de Entidad.", level: "warning" }] }));
    open("/organizaciones/detalle/8?programa=2&seccion=rendiciones");
    expect(await screen.findByRole("heading", { level: 1, name: "Ñandú <Sur>" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/comedores/organizaciones/8/?programa=2&seccion=rendiciones", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Organización: Ñandú <Sur>"));
    expect(document.querySelector("style")?.textContent).toContain(".legajo-header{color:red}");
    expect(document.querySelector(".subtitle")?.textContent).toBe("CUIT: 20111111112 | Asociación civil - Mutual");
    expect(screen.getAllByRole("link").filter((a) => ["Historial", "Editar", "Eliminar"].includes(a.textContent ?? "")).map((a) => a.getAttribute("href")))
      .toEqual(["/audit/x/", "/organizaciones/editar/8", "/organizaciones/eliminar/8"]);
    expect(screen.getByRole("link", { name: "Editar datos de la organización" }).getAttribute("href")).toBe("/organizaciones/editar/8");
    expect(screen.getByText("Programas:").nextElementSibling?.textContent).toBe("Alimentar comunidad · Abordaje comunitario - Línea Secos");
    expect(screen.getByText("Comedores asociados:").nextElementSibling?.textContent).toBe("2 en total");
    expect(screen.getByText(/Vigente/).className).toContain("badge-status vigente");
    expect(await screen.findByText("Se reinicio la documentacion del legajo porque cambio el Tipo de Entidad.")).toBeTruthy();
  });

  it("hides the management and history controls and shows the expired badge and the default chip", async () => {
    serve(legajo({
      header: header({ history_url: null, edit_url: null, delete_url: null, subtipo: null }),
      datos: datos({ edit_url: null, programs: [], expiry: { text: "01/02/2000", state: "vencido" } }),
    }));
    open();
    expect(await screen.findByRole("heading", { level: 1 })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Editar" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Historial" })).toBeNull();
    expect(document.querySelector(".subtitle")?.textContent).toBe("CUIT: 20111111112 | Asociación civil");
    expect(screen.getByText("Sin programas", { selector: ".chip-legajo" })).toBeTruthy();
    expect(screen.getByText("Programas:").nextElementSibling?.textContent).toBe("Sin programas");
    expect(screen.getByText(/Vencido/).className).toContain("vencido");
  });

  it("draws the program selector as a switch and the strip with the tabs", async () => {
    serve(legajo({
      selector: { kind: "switch", items: [{ id: 1, name: "Alimentar", color: "alco", active: false, url: "?programa=1" }, { id: 2, name: "Secos", color: "secos", active: true, url: "?programa=2" }] },
      blocks: [
        { kind: "franja", color: "secos", label: "Abordaje Comunitario", name: "Secos", summary: "1 espacio · 2 proyectos" },
        { kind: "tabs", color: "secos", items: [{ label: "Información del programa", url: "?programa=2&seccion=info", active: true }, { label: "Rendiciones Presentadas (3)", url: "?programa=2&seccion=rendiciones", active: false }] },
      ],
    }));
    open();
    const nav = await screen.findByRole("navigation", { name: "Programa del legajo" });
    expect(within(nav).getByRole("link", { name: "Secos" }).getAttribute("aria-current")).toBe("page");
    expect(within(nav).getByRole("link", { name: "Secos" }).className).toBe("activo color-secos");
    expect(within(nav).getByRole("link", { name: "Alimentar" }).getAttribute("href")).toBe("?programa=1");
    expect(document.querySelector(".franja-programa.color-secos")?.textContent).toBe("Abordaje Comunitario Secos 1 espacio · 2 proyectos");
    const tabs = screen.getByRole("navigation", { name: "Secciones del programa" });
    expect(within(tabs).getByRole("link", { name: "Información del programa" }).getAttribute("aria-current")).toBe("page");
    expect(within(tabs).getByRole("link", { name: "Rendiciones Presentadas (3)" }).getAttribute("href")).toBe("?programa=2&seccion=rendiciones");
  });

  it("draws a single-program chip, the no-program notice and the abordaje notice", async () => {
    serve(legajo({
      selector: { kind: "chip", name: "Secos", color: "secos" },
      blocks: [{ kind: "sin_programas", edit_url: "/organizaciones/editar/8#section-programas" }, { kind: "aviso_abordaje" }],
    }));
    open();
    expect(await screen.findByText("Secos", { selector: ".chip-legajo" })).toBeTruthy();
    expect(screen.getByText("Sin programas asignados")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Cargar programas" }).getAttribute("href")).toBe("/organizaciones/editar/8#section-programas");
    expect(screen.getByText(/La organización tiene datos de Abordaje Comunitario/)).toBeTruthy();
  });

  it("draws the rendiciones cards with their filter, table and empty text", async () => {
    const row = { id: 5, line: null, line_label: null, project: "P-1", convenio: "CV", number: "1", period: "01/2026", territorial: true, audit: false, validated: true, audited: false, url: "/organizaciones/8/rendiciones/5/" };
    serve(legajo({
      blocks: [
        { kind: "rendiciones_generales", total: 0, filter: { kind: "rendiciones_filtro", codes: ["P-1", "P-2"], selected: "", program_id: null }, table: null },
        { kind: "rendiciones_programa", color: "secos", title: "Rendiciones Presentadas · Secos", total: 1, filter: { kind: "rendiciones_filtro", codes: [], selected: "", program_id: 2 },
          table: { kind: "rendiciones", show_line: false, rows: [row] } },
        { kind: "rendiciones_otras", total: 1, table: { kind: "rendiciones", show_line: true, rows: [row] } },
      ],
    }));
    open();
    expect(await screen.findByText("No hay rendiciones presentadas para la selección actual.")).toBeTruthy();
    expect(screen.getByRole("combobox", { name: "Código de Proyecto" })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 5, name: "Rendiciones Presentadas · Secos 1 Total" })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 5, name: "Rendiciones de otras líneas 1 Total" })).toBeTruthy();
    expect(screen.getByText("Su línea no está entre los programas de la organización. Se muestran acá para que no queden ocultas.")).toBeTruthy();
    expect(screen.getAllByRole("link", { name: "Ver" })).toHaveLength(2);
  });

  it("draws the projects-without-line notice with its singular and plural forms", async () => {
    const block = (count: number, codes: string[], edit: string | null) => ({ kind: "aviso_sin_linea", count, plural: count === 1 ? "" : "s", plural_n: count === 1 ? "" : "n", plural_s: count === 1 ? "" : "s", codes, edit_url: edit });
    serve(legajo({ blocks: [block(2, ["A-1", "B-2"], "/organizaciones/editar/8#abordaje-card")] }));
    open();
    expect(await screen.findByText("2 proyectos sin línea")).toBeTruthy();
    expect(document.querySelector(".aviso-legajo")?.textContent).toContain("no aparecen en las líneas de la organización: no tienen línea o su línea no está cargada en la organización. Asignales una: A-1 B-2");
    expect(screen.getByRole("link", { name: "Asignar línea" }).getAttribute("href")).toBe("/organizaciones/editar/8#abordaje-card");
    cleanup();
    serve(legajo({ blocks: [block(1, ["A-1"], null)] }));
    open();
    expect(await screen.findByText("1 proyecto sin línea")).toBeTruthy();
    expect(document.querySelector(".aviso-legajo")?.textContent).toContain("no aparece en las líneas de la organización: no tiene línea o su línea no está cargada en la organización. Asignale una: A-1");
    expect(screen.queryByRole("link", { name: "Asignar línea" })).toBeNull();
  });

  it("draws every legajo section in order, and the sin-programa group with its own sections", async () => {
    serve(legajo({
      blocks: [
        { kind: "avales", can_manage: false, add_url: null, rows: [] },
        { kind: "region", can_manage: false, edit_url: null, has_data: true, region: "R", subzona: "S", territorials: [] },
        { kind: "proyectos", title: "Proyectos", color: "otro", can_manage: false, edit_url: null, total: 0, rows: [] },
        { kind: "convenios", program: "Línea Secos", color: "secos", is_tradicional: false, can_manage: false, rows: [] },
        { kind: "firmantes", title: "Firmantes · Secos", color: "secos", show_program: false, can_manage: false, add_url: null, rows: [] },
        { kind: "comedores", title: "Comedores Asociados · Secos", color: "secos", show_code: false, show_program: false, total: 0, rows: [] },
        { kind: "documentos", organization_id: 8, category: "Tipo documental", can_validate: false, can_send: false, rows: [] },
        { kind: "sin_programa", sections: [{ kind: "firmantes", title: "Firmantes", color: "sin", show_program: true, can_manage: false, add_url: null, rows: [] }, { kind: "desconocida" }] },
        { kind: "desconocida" },
      ],
    }));
    open();
    await screen.findByText("No hay documentación configurada.");
    const titles = Array.from(document.querySelectorAll(".px-4 h5")).map((h) => h.textContent?.replace(/\s+/g, " ").trim());
    expect(titles).toEqual([
      "Datos de la Organización Común a todos los programas", "Avales", "Datos de Región", "Proyectos 0 Total", "Datos de Convenio · Línea Secos", "Firmantes · Secos",
      "Comedores Asociados · Secos 0 Total", "Documentación de la Organización", "Sin programa asignado Visible en cualquier programa", "Firmantes",
    ]);
    expect(screen.getByText(/Editalos para asignarles uno\./)).toBeTruthy();
  });

  it("shows the access screen on 403, an error on 404 and rejects malformed payloads", async () => {
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    open();
    await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
    expect(document.querySelector(".legajo-header")).toBeNull();
    cleanup();
    serve({ detail: "No encontrado." }, 404);
    render(<App />);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(legajoValid(legajo())).toBe(true);
    expect(legajoValid({ ...legajo(), header: { ...header(), edit_url: "https://evil.example/" } })).toBe(false);
    expect(legajoValid({ ...legajo(), selector: { kind: "switch", items: "x" } })).toBe(false);
    expect(legajoValid({ ...legajo(), datos: datos({ expiry: { text: "x", state: "otro" } }) })).toBe(false);
    expect(legajoValid({ ...legajo(), messages: [{ message: "x", level: "otro" }] })).toBe(false);
    expect(legajoValid({ ...legajo(), blocks: [{}] })).toBe(false);
  });
});
