import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { detailValid, listValid } from "./comunicados";
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
  can_manage: false, permisos: { editar: false, publicar: false, archivar: false, eliminar: false }, messages: [], ...over,
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
  it("owns the list and the detail paths only", () => {
    expect(findRoute("/comunicados/")?.route.name).toBe("comedores-comunicados");
    expect(findRoute("/comunicados/ver/12/")?.route.name).toBe("comedores-comunicados");
    for (const other of ["/comunicados", "/comunicados/gestion/", "/comunicados/crear/", "/comunicados/ver/x/", "/comunicados/editar/3/",
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
