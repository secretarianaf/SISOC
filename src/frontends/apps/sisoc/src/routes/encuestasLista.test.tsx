import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { listaValid } from "./encuestasLista";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const fila = (over = {}) => ({
  id: 4, titulo: "Satisfacción", version: 2, fecha_creacion: "01/10/2026", estado: "borrador", estado_label: "Borrador", tiene_motivo_rechazo: false,
  modalidad: "Obligatoria", es_anonima: false, creador: "Ana Gestora", ...over,
});
const page = (over = {}) => ({
  filters_config: { fields: [{ name: "titulo", label: "Título", type: "text" }, { name: "estado", label: "Estado", type: "choice", choices: [{ value: "borrador", label: "Borrador" }] }], defaultField: "titulo" },
  favorites: { section: "", url: "/filtros-favoritos/", detail_url_template: "/filtros-favoritos/0/" },
  urls: { list: "/encuestas/", add: "/encuestas/crear/", importar: "/encuestas/importar/" },
  puede_gestionar: true, puede_aprobar: false, puede_editar: true, puede_ver_resultados: true, pendientes_aprobacion: 0, pendientes_url: "/encuestas/?filters=x",
  results: [fila()], page: { is_paginated: false, number: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "" }, messages: [], ...over,
});
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
const assign = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  window.history.replaceState({}, "", "/encuestas/");
  setViewport(false);
  vi.stubGlobal("location", { ...window.location, assign, replace: vi.fn(), pathname: "/encuestas/", search: "" });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("listado de encuestas", () => {
  it("owns /encuestas/ only and validates the payload", () => {
    expect(findRoute("/encuestas/")?.route.name).toBe("encuestas-lista");
    expect(findRoute("/encuestas/7/resultados/")?.route.name).not.toBe("encuestas-lista");
    expect(listaValid(page())).toBe(true);
    expect(listaValid(page({ urls: { list: "/encuestas/", add: "http://evil/", importar: "/x/" } }))).toBe(false);
    expect(listaValid(page({ results: [fila({ version: "2" })] }))).toBe(false);
    expect(listaValid(page({ filters_config: { fields: [] } }))).toBe(false);
  });

  it("draws the search bar, the table and the native actions for a manager", async () => {
    serve(page({ results: [fila(), fila({ id: 5, estado: "pendiente_aprobacion", estado_label: "Pendiente de aprobación", titulo: "Pendiente", es_anonima: true }), fila({ id: 6, titulo: "Rechazada", tiene_motivo_rechazo: true })] }));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Encuestas" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/encuestas/lista/", expect.anything());
    expect(screen.getByRole("heading", { name: "Buscar encuestas" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("href")).toBe("/encuestas/");
    expect(screen.getByRole("link", { name: /Crear encuesta/ }).getAttribute("href")).toBe("/encuestas/crear/");
    expect(screen.getByRole("button", { name: /Importar/ })).toBeTruthy();
    expect(screen.getAllByText("Versión 2 · 01/10/2026", { selector: ".encuesta-meta" }).length).toBe(3);
    expect(screen.getAllByRole("link", { name: /Editar/ })[0].getAttribute("href")).toBe("/encuestas/4/editar/");
    expect(screen.getAllByRole("link", { name: /Segmentación/ })[0].getAttribute("href")).toBe("/encuestas/4/segmentacion/");
    expect(screen.getAllByRole("link", { name: /Resultados/ }).length).toBe(3);
    expect(screen.getByRole("link", { name: /Revisar solicitud/ }).getAttribute("href")).toBe("/encuestas/5/revision/");
    expect(screen.getAllByRole("button", { name: /Solicitar publicación/ }).length).toBe(2);
    expect(screen.getByText("Anónima")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Ver motivo del rechazo/ }).getAttribute("href")).toBe("/encuestas/6/editar/");
    expect(screen.queryByText("Solicitudes de publicación")).toBeNull();
    expect(screen.getByText("Se encontraron 1 resultados")).toBeTruthy();
  });

  it("hides what the permissions do not give: no management buttons, approval tray when approving", async () => {
    serve(page({ puede_gestionar: false, puede_editar: false, puede_aprobar: true, pendientes_aprobacion: 1, puede_ver_resultados: false,
      results: [fila({ id: 5, estado: "pendiente_aprobacion", estado_label: "Pendiente de aprobación" })] }));
    render(<App />);
    await screen.findByRole("heading", { name: "Encuestas" });
    expect(screen.queryByRole("button", { name: /Importar/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /Crear encuesta/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /Editar/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /Resultados/ })).toBeNull();
    expect(screen.getByRole("link", { name: /Revisar solicitud/ })).toBeTruthy();
    expect(screen.getByText("1 pendiente de aprobación. Revisá el contenido antes de publicar.")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Ver pendientes/ }).getAttribute("href")).toBe("/encuestas/?filters=x");
  });

  it("shows the empty state and the paginator with the query kept", async () => {
    serve(page({ results: [], page: { is_paginated: true, number: 2, count: 41, previous: 1, next: 3, range: [1, 2, 3], query_without_page: "filters=abc&" } }));
    render(<App />);
    expect(await screen.findByText("No se encontraron encuestas")).toBeTruthy();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
    expect(screen.getByText("No hay encuestas que coincidan con los criterios de búsqueda.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?filters=abc&page=3");
    expect(within(document.querySelector(".pagination") as HTMLElement).getByRole("link", { name: "Volver" }).getAttribute("href")).toBe("?filters=abc&page=1");
  });

  it("requests a publication through its endpoint and follows the native redirect", async () => {
    serve(page());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/encuestas/" } });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Solicitar publicación/ }));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    expect(webPost.mock.calls[0][0]).toBe("web/encuestas/4/publicar/");
    expect(String(webPost.mock.calls[0][1])).toBe("");
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/encuestas/"));
  });

  it("shows the queued native message as a toast when the page loads", async () => {
    serve(page({ messages: [{ message: "Publicación solicitada. La encuesta está pendiente de aprobación.", level: "success" }] }));
    render(<App />);
    expect(await screen.findByText("Publicación solicitada. La encuesta está pendiente de aprobación.")).toBeTruthy();
  });

  it("keeps the button usable and says so when the publication request fails", async () => {
    serve(page());
    webPost.mockRejectedValue(new Error("network"));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Solicitar publicación/ }));
    expect(await screen.findByText("No se pudo completar la operación.")).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
    await waitFor(() => expect((screen.getByRole("button", { name: /Solicitar publicación/ }) as HTMLButtonElement).disabled).toBe(false));
  });

  it("imports the chosen file with the native field and shows the spinner while it runs", async () => {
    serve(page());
    let finish: (v: unknown) => void = () => undefined;
    webPost.mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    render(<App />);
    await screen.findByRole("heading", { name: "Encuestas" });
    const input = document.getElementById("archivo-encuesta") as HTMLInputElement;
    expect(input.getAttribute("accept")).toBe(".json,application/json");
    const click = vi.spyOn(input, "click");
    fireEvent.click(screen.getByRole("button", { name: /Importar/ }));
    expect(click).toHaveBeenCalled();
    const file = new File(['{"a":1}'], "encuesta.json", { type: "application/json" });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
    expect(webPost.mock.calls[0][0]).toBe("web/encuestas/importar/?mensajes=en-cola");
    expect((webPost.mock.calls[0][1] as FormData).get("archivo")).toBeTruthy();
    const button = screen.getByRole("button", { name: /Importando/ }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.getAttribute("aria-busy")).toBe("true");
    finish({ status: 200, data: { ok: true, redirect: "/encuestas/" } });
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/encuestas/"));
  });

  it("follows the native redirect of a legacy search link", async () => {
    serve({ redirect: "/encuestas/?filters=%7B%7D" });
    const replace = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign, replace, pathname: "/encuestas/", search: "?busqueda=x" });
    render(<App />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/encuestas/?filters=%7B%7D"));
  });

  it("shows the access screen on 403", async () => {
    webGet.mockImplementation((url: string) =>
      Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "No tiene permisos para esta acción." }, status: 403 }));
    render(<App />);
    expect(await screen.findByText(/permiso/i)).toBeTruthy();
    expect(screen.queryByText("Buscar encuestas")).toBeNull();
  });
});
