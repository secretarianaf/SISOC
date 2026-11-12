import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { comunicadosNavigation, detailValid, gestionValid, listValid } from "./comunicados";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/comunicados/";
const card = (over: Record<string, unknown> = {}) => ({
  id: 4, titulo: "Aviso <importante>", cuerpo_resumen: "Texto breve …", destacado: false, fecha_publicacion: "04/03/2026 15:07",
  creador: "Ana Pérez", adjuntos_count: 0, detail_url: "/comunicados/ver/4/", ...over,
});
const page = (over: Record<string, unknown> = {}) => ({
  is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "", ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [card()], page: page(), filtro_titulo: "", can_manage: false, gestion_url: null, messages: [], ...over,
});
const detail = (over: Record<string, unknown> = {}) => ({
  id: 4, titulo: "Aviso <importante>", cuerpo: "Uno\nlinea\n\nDos", estado: "publicado", estado_label: "Publicado", destacado: false,
  fecha_publicacion: "04/03/2026 15:07", fecha_vencimiento: "", esta_vencido: false, creador: "Ana Pérez", adjuntos: [],
  can_manage: false, fecha_creacion: "03/03/2026 09:00", modificado_por: "",
  permisos: { editar: false, publicar: false, archivar: false, eliminar: false }, messages: [], ...over,
});
const acciones = (over: Record<string, unknown> = {}) => ({ editar: false, publicar: false, archivar: false, destacado: false, ...over });
const fila = (over: Record<string, unknown> = {}) => ({
  id: 7, titulo: "Aviso largo de prueba", titulo_corto: "Aviso largo …", tipo: "interno", estado: "borrador", esta_vencido: false, destacado: false,
  fecha_creacion: "03/03/2026", fecha_publicacion: "", creador: "Ana Pérez", acciones: acciones(), ...over,
});
const gestion = (over: Record<string, unknown> = {}) => ({
  results: [fila()], page: page(), filtros: { titulo: "", estado: "", tipo: "" },
  flags: { can_create: false, is_admin: false, es_tecnico: false }, mailing_url: null, messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Comunicados published route", () => {
  it("owns the list, the gestion list and the detail paths only", () => {
    expect(findRoute("/comunicados/")?.route.name).toBe("comedores-comunicados");
    expect(findRoute("/comunicados/gestion/")?.route.name).toBe("comedores-comunicados");
    expect(findRoute("/comunicados/ver/12/")?.route.name).toBe("comedores-comunicados");
    for (const other of ["/comunicados", "/comunicados/gestion", "/comunicados/crear/", "/comunicados/ver/x/", "/comunicados/editar/3/",
      "/comunicados/mailing/", "/api/comunicados/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-comunicados");
    }
  });

  it("renders the search bar and the cards from the API", async () => {
    serve(list({ results: [card({ destacado: true, adjuntos_count: 2 }), card({ id: 5, titulo: "Otro", detail_url: "/comunicados/ver/5/" })], filtro_titulo: "avi" }));
    setup("/comunicados/?titulo=avi");
    await screen.findByText("Otro");
    expect(webGet).toHaveBeenCalledWith(`${API}?titulo=avi`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Comunicados"));
    expect(screen.getByRole("heading", { level: 3, name: "Comunicados" })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 2, name: "Buscar comunicado" })).toBeTruthy();
    const search = screen.getByRole("searchbox", { name: "Buscar por título." }) as HTMLInputElement;
    expect([search.name, search.placeholder, search.value, search.title]).toEqual(["titulo", "Buscar por título...", "avi", "Buscar por título."]);
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("href")).toBe("/comunicados/");
    expect(screen.queryByRole("link", { name: "Gestionar" })).toBeNull();
    const cards = [...document.querySelectorAll<HTMLElement>(".comunicado-card")];
    expect(cards).toHaveLength(2);
    expect(within(cards[0]).getByText("Destacado")).toBeTruthy();
    expect(cards[0].style.borderLeft).toBe("4px solid rgb(231, 186, 97)");
    expect(within(cards[0]).getByText(/2 adjunto\(s\)/)).toBeTruthy();
    expect(within(cards[0]).getByRole("link", { name: "Aviso <importante>" }).getAttribute("href")).toBe("/comunicados/ver/4/");
    expect(within(cards[0]).getByRole("link", { name: "Leer más" }).className).toBe("btn btn-sm btn-outline-primary");
    expect(cards[0].querySelector(".comunicado-meta")?.textContent).toBe(" 04/03/2026 15:07  Ana Pérez  2 adjunto(s) ");
    expect(within(cards[1]).queryByText("Destacado")).toBeNull();
    expect(within(cards[1]).queryByText(/adjunto/)).toBeNull();
    expect(cards[1].getAttribute("style")).toBeNull();
    expect(within(cards[1]).getByText("Texto breve …")).toBeTruthy();
    expect(document.querySelector(".pagination")).toBeNull();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("shows the gestion button for managers, the empty card and the pagination", async () => {
    serve(list({ results: [], can_manage: true, gestion_url: "/comunicados/gestion/",
      page: page({ is_paginated: true, number: 2, num_pages: 2, count: 21, previous: 1, range: [1, 2], query_without_page: "titulo=a&" }) }));
    setup("/comunicados/?titulo=a&page=2");
    expect(await screen.findByText("No hay comunicados publicados.")).toBeTruthy();
    const gestionar = screen.getByRole("link", { name: "Gestionar" });
    expect([gestionar.getAttribute("href"), gestionar.title, gestionar.className]).toEqual(["/comunicados/gestion/", "Gestionar comunicados", "poncho-btn poncho-btn--neutro"]);
    expect(screen.getAllByRole("link", { name: "Volver" }).map((a) => a.getAttribute("href"))).toContain("?titulo=a&page=1");
    expect(screen.getByRole("link", { name: "Continuar" }).closest("li")?.className).toBe("page-item disabled");
    expect(screen.getByText("Se encontraron 21 resultados")).toBeTruthy();
  });

  it("renders the reader detail with linebreaks, dates and attachments", async () => {
    serve(detail({ destacado: true, fecha_vencimiento: "06/03/2026 10:00", esta_vencido: true,
      adjuntos: [{ id: 9, nombre_original: "guia.pdf", url: "/media/comunicados/guia.pdf" }] }));
    setup("/comunicados/ver/4/");
    expect(await screen.findByRole("heading", { level: 4, name: "Aviso <importante>" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}4/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Aviso <importante>"));
    expect(screen.getByRole("heading", { level: 3, name: "Comunicado" })).toBeTruthy();
    expect(screen.getByText("Comunicado Destacado").className).toBe("card-header bg-warning text-dark");
    expect(document.querySelector(".card")?.className).toBe("card border-warning");
    expect(screen.getByText("Publicado").className).toBe("badge bg-success");
    expect(screen.getByText(/Publicado: 04\/03\/2026 15:07/)).toBeTruthy();
    expect(screen.getByText(/Vence: 06\/03\/2026 10:00/)).toBeTruthy();
    expect(screen.getByText("Vencido").className).toBe("badge bg-danger");
    expect(document.querySelector(".comunicado-contenido")?.innerHTML).toBe("<p>Uno<br>linea</p>\n\n<p>Dos</p>");
    expect(screen.getByText("Archivos Adjuntos")).toBeTruthy();
    const adjunto = screen.getByRole("link", { name: "guia.pdf" });
    expect([adjunto.getAttribute("href"), adjunto.getAttribute("target")]).toEqual(["/media/comunicados/guia.pdf", "_blank"]);
    expect(document.querySelector(".card-footer")).toBeNull();
  });

  it("hides the optional detail parts", async () => {
    serve(detail({ fecha_publicacion: "", estado: "borrador", estado_label: "Borrador" }));
    setup("/comunicados/ver/4/");
    await screen.findByRole("heading", { level: 4, name: "Aviso <importante>" });
    expect(screen.queryByText("Comunicado Destacado")).toBeNull();
    expect(screen.queryByText(/Publicado:/)).toBeNull();
    expect(screen.queryByText(/Vence:/)).toBeNull();
    expect(screen.queryByText("Archivos Adjuntos")).toBeNull();
    expect(screen.getByText("Borrador").className).toBe("badge bg-secondary");
    expect(document.querySelector(".card")?.className).toBe("card ");
  });

  it("shows the access screen on 403 and an error on a bad payload or network failure", async () => {
    serve({ detail: "No tiene permisos." }, 403);
    setup("/comunicados/");
    await waitFor(() => expect(document.title).toBe("SISOC - Error 403"));
    expect(document.querySelector(".comunicado-card")).toBeNull();
    cleanup();
    serve({ detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, 403);
    setup("/comunicados/ver/4/");
    await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
    expect(document.querySelector(".comunicado-contenido")).toBeNull();
    cleanup();
    serve(list({ results: [card({ detail_url: "https://evil.example/" })] }));
    setup("/comunicados/");
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar la página.");
    cleanup();
    webGet.mockRejectedValue(new Error("network"));
    setup("/comunicados/ver/4/");
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar la página.");
    expect(listValid(list())).toBe(true);
    expect(detailValid(detail())).toBe(true);
    expect(detailValid(detail({ permisos: { editar: "x" } }))).toBe(false);
  });
});

describe("Comunicados management route (CM02.01)", () => {
  it("renders the table, filters, badges and the row actions from the API", async () => {
    const all = acciones({ editar: true, publicar: true });
    serve(gestion({
      results: [
        fila({ acciones: all }),
        fila({ id: 8, estado: "publicado", destacado: true, fecha_publicacion: "05/03/2026", acciones: acciones({ archivar: true, destacado: true }) }),
        fila({ id: 9, estado: "publicado", tipo: "externo", esta_vencido: true, acciones: acciones({ archivar: true }) }),
        fila({ id: 10, estado: "publicado", acciones: acciones({ destacado: true }) }),
        fila({ id: 11, estado: "archivado" }),
      ],
      filtros: { titulo: "avi", estado: "publicado", tipo: "interno" },
      flags: { can_create: true, is_admin: true, es_tecnico: false }, mailing_url: "/comunicados/mailing/",
    }));
    setup("/comunicados/gestion/?titulo=avi&estado=publicado");
    await screen.findByText("Comunicados", { selector: "h5" });
    expect(webGet).toHaveBeenCalledWith(`${API}gestion/?titulo=avi&estado=publicado`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Gestión de Comunicados"));
    expect(screen.getByRole("heading", { level: 3, name: "Gestión de Comunicados" })).toBeTruthy();
    expect((screen.getByRole("searchbox", { name: "Buscar por título." }) as HTMLInputElement).placeholder).toBe("Buscar comunicado...");
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("href")).toBe("/comunicados/gestion/");
    expect(screen.getByRole("link", { name: /Nuevo/ }).getAttribute("href")).toBe("/comunicados/crear/");
    expect(screen.getByRole("link", { name: "Mailing masivo" }).getAttribute("href")).toBe("/comunicados/mailing/");
    expect((screen.getByLabelText("Estado") as HTMLSelectElement).value).toBe("publicado");
    expect((screen.getByLabelText("Tipo") as HTMLSelectElement).value).toBe("interno");
    expect(screen.getByRole("link", { name: "Limpiar búsqueda" }).getAttribute("href")).toBe("?estado=publicado&tipo=interno");
    expect(screen.getByRole("link", { name: /Ver Vista Pública/ }).getAttribute("href")).toBe("/comunicados/");
    const rows = [...document.querySelectorAll<HTMLElement>("tbody tr")];
    const titles = (row: HTMLElement) => [...row.querySelectorAll(".btn-group a, .btn-group button")].map((e) => e.getAttribute("title"));
    expect(rows).toHaveLength(5);
    expect(within(rows[0]).getByText("Borrador").className).toBe("badge bg-secondary");
    expect(within(rows[0]).getByText("Interno").className).toBe("badge bg-info");
    expect(within(rows[0]).getByRole("link", { name: "Aviso largo …" }).getAttribute("href")).toBe("/comunicados/ver/7/");
    expect(within(rows[0]).getByText("-").className).toBe("text-muted");
    expect(titles(rows[0])).toEqual(["Ver", "Editar", "Publicar"]);
    expect(within(rows[0]).getByTitle("Editar").getAttribute("href")).toBe("/comunicados/editar/7/");
    expect(rows[1].querySelector(".fa-star.text-warning")).not.toBeNull();
    expect(titles(rows[1])).toEqual(["Ver", "Archivar", "Quitar destacado"]);
    expect(within(rows[1]).getByText("05/03/2026")).toBeTruthy();
    expect(within(rows[2]).getByText("Vencido").className).toBe("badge bg-danger");
    expect(within(rows[2]).getByText("Externo").className).toBe("badge bg-warning text-dark");
    expect(titles(rows[3])).toEqual(["Ver", "Marcar como destacado"]);
    expect(within(rows[4]).getByText("Archivado").className).toBe("badge bg-dark");
    expect(titles(rows[4])).toEqual(["Ver"]);
    const form = rows[0].querySelector("form") as HTMLFormElement;
    expect([form.method, form.getAttribute("action")]).toEqual(["post", "/comunicados/publicar/7/"]);
    expect((form.elements.namedItem("csrfmiddlewaretoken") as HTMLInputElement).value).toBe("synthetic-csrf-token");
  });

  it("asks before publishing or archiving", async () => {
    serve(gestion({ results: [fila({ acciones: acciones({ publicar: true }) }), fila({ id: 8, estado: "publicado", acciones: acciones({ archivar: true }) })] }));
    setup("/comunicados/gestion/");
    const publicar = await screen.findByTitle("Publicar");
    const confirm = vi.spyOn(comunicadosNavigation, "confirm").mockReturnValueOnce(false);
    expect(fireEvent.click(publicar)).toBe(false);
    expect(confirm).toHaveBeenLastCalledWith("¿Publicar este comunicado?");
    confirm.mockReturnValueOnce(true);
    const archivar = screen.getByTitle("Archivar");
    archivar.closest("form")?.addEventListener("submit", (e) => e.preventDefault());
    expect(fireEvent.click(archivar)).toBe(true);
    expect(confirm).toHaveBeenLastCalledWith("¿Archivar este comunicado?");
  });

  it("submits the search form when a module select changes and hides tipo for technicians", async () => {
    serve(gestion({ results: [], flags: { can_create: false, is_admin: false, es_tecnico: true } }));
    setup("/comunicados/gestion/");
    expect(await screen.findByText("No hay comunicados.")).toBeTruthy();
    expect(screen.queryByLabelText("Tipo")).toBeNull();
    expect(screen.queryByRole("link", { name: /Nuevo/ })).toBeNull();
    expect(screen.queryByRole("link", { name: "Mailing masivo" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Limpiar búsqueda" })).toBeNull();
    const submit = vi.spyOn(comunicadosNavigation, "submit").mockImplementation(() => undefined);
    const select = screen.getByLabelText("Estado") as HTMLSelectElement;
    expect(select.getAttribute("form")).toBe("simple-search-form");
    fireEvent.change(select, { target: { value: "archivado" } });
    expect(submit).toHaveBeenCalledTimes(1);
  });

  it("shows the count, the pagination, the 403 and the bad payload screens", async () => {
    serve(gestion({ page: page({ is_paginated: true, number: 1, num_pages: 2, count: 21, next: 2, range: [1, 2], query_without_page: "estado=borrador&" }) }));
    setup("/comunicados/gestion/");
    expect(await screen.findByText("(21)")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?estado=borrador&page=2");
    cleanup();
    serve({ detail: "No tiene permisos para gestionar comunicados." }, 403);
    setup("/comunicados/gestion/");
    await waitFor(() => expect(document.title).toBe("SISOC - Error 403"));
    cleanup();
    serve(gestion({ mailing_url: "https://evil.example/" }));
    setup("/comunicados/gestion/");
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar la página.");
    expect(gestionValid(gestion())).toBe(true);
    expect(gestionValid(gestion({ results: [fila({ acciones: { editar: 1 } })] }))).toBe(false);
  });

  it("renders the manager footer of the detail by state and permission", async () => {
    const todos = { editar: true, publicar: true, archivar: true, eliminar: true };
    serve(detail({ estado: "borrador", estado_label: "Borrador", can_manage: true, permisos: todos, modificado_por: "editor" }));
    setup("/comunicados/ver/4/");
    await screen.findByRole("heading", { level: 4, name: "Aviso <importante>" });
    const footer = document.querySelector(".card-footer") as HTMLElement;
    expect(footer.querySelector("small")?.textContent).toBe("Creado: 03/03/2026 09:00 | Modificado por: editor");
    expect([...footer.querySelectorAll("a, button")].map((e) => e.textContent?.trim())).toEqual(["Editar", "Publicar", "Eliminar"]);
    expect(within(footer).getByRole("link", { name: "Eliminar" }).getAttribute("href")).toBe("/comunicados/eliminar/4/");
    expect((footer.querySelector("form") as HTMLFormElement).getAttribute("action")).toBe("/comunicados/publicar/4/");
    cleanup();
    serve(detail({ can_manage: true, permisos: todos }));
    setup("/comunicados/ver/4/");
    await screen.findByRole("heading", { level: 4, name: "Aviso <importante>" });
    const pub = document.querySelector(".card-footer") as HTMLElement;
    expect(pub.querySelector("small")?.textContent).toBe("Creado: 03/03/2026 09:00");
    expect([...pub.querySelectorAll("a, button")].map((e) => e.textContent?.trim())).toEqual(["Archivar"]);
    expect((pub.querySelector("form") as HTMLFormElement).getAttribute("action")).toBe("/comunicados/archivar/4/");
    cleanup();
    serve(detail({ can_manage: true, permisos: { editar: false, publicar: false, archivar: false, eliminar: false } }));
    setup("/comunicados/ver/4/");
    await screen.findByRole("heading", { level: 4, name: "Aviso <importante>" });
    expect(document.querySelector(".card-footer")).toBeNull();
  });
});
