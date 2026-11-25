import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { detalleValid, listaValid } from "./rendicionFinal";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const LISTADO = "/rendicion_cuentas_final/listar/";
const DETALLE = "/comedores/7/rendicion_cuentas_final/";
const API_LISTA = "web/comedores/rendicion_cuentas_final/documentos/";
const API_DETALLE = "web/comedores/rendicion_cuentas_final/comedor/7/";
const fila = (over: Record<string, unknown> = {}) => ({
  id: 1, tipo_nombre: "Informe Dupla", comedor_nombre: "Comedor <Uno>", fecha_modificacion: "11/11/2026 10:30", estado: "En análisis",
  estado_slug: "en-analisis", archivo_url: "/media/rendicion_cuentas_final/a.pdf", accionable: true, ...over,
});
const lista = (over: Record<string, unknown> = {}) => ({
  count: 2, page: 1, page_size: null, pages: 1, has_previous: false, has_next: false, previous: null, next: null, range: [],
  filters: { busqueda: "" },
  results: [fila(), fila({ id: 2, comedor_nombre: "Otro", estado: "Validado", estado_slug: "validado", archivo_url: null, accionable: false, fecha_modificacion: null })],
  messages: [], ...over,
});
const doc = (over: Record<string, unknown> = {}) => ({
  id: 1, tipo_nombre: "Informe Dupla", estado: "En análisis", validador: "Dupla", observaciones: null, fecha_modificacion: "11/11/2026 10:30",
  archivo_url: "/media/rendicion_cuentas_final/a.pdf", editable: false, validable: true, eliminable: true, ...over,
});
const detalle = (over: Record<string, unknown> = {}) => ({
  rendicion: { id: 3, fisicamente_presentada: true }, comedor: { id: 7, nombre: "Comedor <Uno>" },
  urls: { comedores: "/comedores/", comedor: "/comedores/7" },
  documentos: [doc(), doc({ id: 2, tipo_nombre: "Informe Contable", estado: "Subsanar", validador: "Contable", observaciones: "Falta <firma>", archivo_url: null, editable: true, validable: false, eliminable: false, fecha_modificacion: null })],
  historial: [{ tipo_nombre: "Informe Dupla", accion: "Validar documento", usuario: "Ana", fecha: "11/11/2026 10:31" }],
  messages: [], ...over,
});

function serve(handler: (url: string) => unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: handler(url), status }));
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
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers(); });

describe("Rendición final route", () => {
  it("owns only the native detail and list paths", () => {
    expect(findRoute(LISTADO)?.route.name).toBe("comedores-rendicion-final");
    expect(findRoute(DETALLE)?.route.name).toBe("comedores-rendicion-final");
    for (const other of ["/rendicion_cuentas_final/listar", "/comedores/7/rendicion_cuentas_final", "/comedores/x/rendicion_cuentas_final/", "/rendicion_cuentas_final/ajax/", "/comedores/7/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-rendicion-final");
    }
  });

  it("validates the payloads", () => {
    expect(detalleValid(detalle())).toBe(true);
    expect(detalleValid({ ...detalle(), historial: [{}] })).toBe(false);
    expect(listaValid(lista())).toBe(true);
    expect(listaValid({ ...lista(), results: [{ id: "x" }] })).toBe(false);
  });

  it("renders the list rows with the native columns, states and disabled buttons", async () => {
    serve(() => lista());
    setup(LISTADO);
    await screen.findByText("Comedor <Uno>");
    expect(webGet).toHaveBeenCalledWith(API_LISTA, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Espacios Comunitarios"));
    expect(screen.getByRole("heading", { level: 2, name: "Buscar Documento" })).toBeTruthy();
    const input = screen.getByRole("searchbox", { name: "Ingresar comedor o tipo de documento." }) as HTMLInputElement;
    expect(input.placeholder).toBe("Buscar por comedor o tipo de documento");
    expect(input.title).toBe("Ingresar comedor o tipo de documento.");
    expect(screen.getByRole("button", { name: "Buscar" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("href")).toBe(LISTADO);
    const rows = screen.getAllByRole("row");
    expect(within(rows[0]).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Nombre", "Comedor", "Fecha de modificacion", "Estado", "Acciones", "Validar", "Subsanar"]);
    expect(rows[1].className).toBe("documento-row estado-en-analisis");
    expect(within(rows[1]).getAllByRole("cell").slice(0, 4).map((c) => c.textContent)).toEqual(["Informe Dupla", "Comedor <Uno>", "11/11/2026 10:30", "En análisis"]);
    const visualizar = within(rows[1]).getByRole("link", { name: "Visualizar" });
    expect(visualizar.getAttribute("href")).toBe("/media/rendicion_cuentas_final/a.pdf");
    expect(visualizar.getAttribute("target")).toBe("_blank");
    expect(within(rows[2]).getByRole("button", { name: "Visualizar" }).hasAttribute("disabled")).toBe(true);
    expect(within(rows[2]).getAllByRole("cell")[2].textContent).toBe("-");
    expect(within(rows[1]).getByRole("button", { name: "Validar" }).className).toContain("btn-warning");
    expect(within(rows[2]).getByRole("button", { name: "Validar" }).className).toContain("btn-secondary");
    expect(document.getElementById("ajax-results-count")?.textContent).toBe("");
    expect(document.querySelector(".pagination")).toBeNull();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("shows the native empty row", async () => {
    serve(() => lista({ count: 0, results: [] }));
    setup(LISTADO);
    const empty = await screen.findByText("No se encontraron documentos.");
    expect(empty.getAttribute("colspan")).toBe("7");
  });

  it("searches with a 300 ms debounce, shows the counter and paginates through the API", async () => {
    const paginada = (over: Record<string, unknown>) => lista({ page_size: 25, pages: 2, range: [1, 2], count: 30, ...over });
    serve((url) => {
      if (url.includes("page=2")) return paginada({ page: 2, has_previous: true, previous: 1, results: [fila({ id: 9, tipo_nombre: "Pagina dos" })] });
      return url.includes("busqueda=") ? paginada({ has_next: true, next: 2 }) : lista();
    });
    setup(LISTADO);
    await screen.findByText("Comedor <Uno>");
    vi.useFakeTimers();
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "alfa" } });
    expect(webGet).not.toHaveBeenCalledWith(expect.stringContaining("busqueda=alfa"), expect.anything());
    await vi.advanceTimersByTimeAsync(300);
    expect(webGet).toHaveBeenCalledWith(`${API_LISTA}?busqueda=alfa`, expect.anything());
    vi.useRealTimers();
    await screen.findByText("30 resultado(s) encontrado(s)");
    expect(screen.getByText("Se encontraron 30 resultados")).toBeTruthy();
    fireEvent.click(screen.getByRole("link", { name: "Continuar" }));
    await screen.findByText("Pagina dos");
    expect(webGet).toHaveBeenCalledWith(`${API_LISTA}?busqueda=alfa&page=2`, expect.anything());
    fireEvent.keyDown(screen.getByRole("searchbox"), { key: "Escape" });
    await waitFor(() => expect(webGet).toHaveBeenCalledWith(`${API_LISTA}?busqueda=`, expect.anything()));
    expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe("");
    await waitFor(() => expect(document.getElementById("ajax-results-count")?.textContent).toBe(""));
  });

  it("the magnifier searches at once and an error shows the native message", async () => {
    serve((url) => (url.includes("busqueda=") ? "broken" : lista()));
    setup(LISTADO);
    await screen.findByText("Comedor <Uno>");
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Buscar" }));
    await screen.findByText("Error al cargar los datos. Intente nuevamente.");
  });

  it("runs the search of a prefilled query once on load", async () => {
    serve(() => lista());
    setup(`${LISTADO}?busqueda=beta`);
    await screen.findByText("Comedor <Uno>");
    await waitFor(() => expect(webGet).toHaveBeenCalledWith(`${API_LISTA}?busqueda=beta`, expect.anything()));
    expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe("beta");
  });

  it("renders the detail tables, breadcrumb, switch state and history", async () => {
    serve(() => detalle());
    setup(DETALLE);
    await screen.findByText("Historial de Documentos");
    expect(webGet).toHaveBeenCalledWith(API_DETALLE, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Rendicion de Cuentas Final"));
    expect(screen.getByRole("heading", { level: 3, name: "Rendicion de Cuentas Final" })).toBeTruthy();
    const crumbs = [...document.querySelectorAll(".breadcrumb .breadcrumb-item")];
    expect(crumbs.map((c) => c.textContent)).toEqual(["Espacios Comunitarios", "", "Rendicion de Cuentas Final"]);
    expect(crumbs[0].querySelector("a")?.getAttribute("href")).toBe("/comedores/");
    expect(crumbs[1].querySelector("a")?.getAttribute("href")).toBe("/comedores/7");
    expect(crumbs[2].className).toBe("breadcrumb-item active");
    expect(screen.getByRole("button", { name: "Añadir documento personalizado" })).toBeTruthy();
    expect((screen.getByLabelText("Revisión físicamente presentada") as HTMLInputElement).checked).toBe(true);
    const [head, ...rows] = [...document.querySelectorAll("table")[0].querySelectorAll("tr")];
    expect([...head.querySelectorAll("th")].map((c) => c.textContent)).toEqual(["Tipo de Documento", "Estado", "Validador", "Observaciones", "Última Modificación", "", "", "", ""]);
    expect([...rows[0].querySelectorAll("td")].slice(0, 5).map((c) => c.textContent)).toEqual(["Informe Dupla", "En análisis", "Dupla", "-", "11/11/2026 10:30"]);
    expect(within(rows[1] as HTMLElement).getByRole("button", { name: "Adjuntar" }).className).toContain("btn-success");
    expect(within(rows[0] as HTMLElement).getByRole("button", { name: "Validar" }).className).toContain("btn-warning");
    expect([...document.querySelectorAll("table")[1].querySelectorAll("tbody td")].map((c) => c.textContent)).toEqual(["Informe Dupla", "Validar documento", "Ana", "11/11/2026 10:31"]);
  });

  it("shows the empty history and a missing object", async () => {
    serve(() => detalle({ historial: [] }));
    setup(DETALLE);
    expect((await screen.findByText("No hay registros aun.")).getAttribute("colspan")).toBe("4");
    cleanup();
    serve(() => detalle({ historial: [{ tipo_nombre: null, accion: "X", usuario: "", fecha: null }] }));
    setup(DETALLE);
    expect((await screen.findByText("No disponible")).className).toBe("text-muted");
  });

  it("opens the observations modal as plain text and closes it with Escape and the button", async () => {
    serve(() => detalle());
    setup(DETALLE);
    fireEvent.click(await screen.findByRole("link", { name: "Ver" }));
    const dialog = await screen.findByRole("dialog", { name: "Observaciones del documento Informe Contable" });
    expect(within(dialog).getByText("Falta <firma>")).toBeTruthy();
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    fireEvent.click(screen.getByRole("link", { name: "Ver" }));
    const again = await screen.findByRole("dialog");
    fireEvent.click(within(again).getAllByRole("button", { name: "Cerrar" })[1]);
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("shows the access screen on 403 and the load error otherwise", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "no" }, status: 403 }));
    setup(LISTADO);
    await waitFor(() => expect(screen.queryByText("Cargando documentos…")).toBeNull());
    expect(screen.queryByRole("table")).toBeNull();
    cleanup();
    serve(() => "broken");
    setup(DETALLE);
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar la página.");
  });

  describe("actions", () => {
    const ok = (message: string) => webPost.mockResolvedValue({ status: 200, data: { ok: true, message } });
    const confirmWith = (answer: boolean) => vi.spyOn(window, "confirm").mockReturnValue(answer);
    const fileOf = (name: string) => new File(["x"], name, { type: "application/pdf" });
    const row = (n: number) => screen.getAllByRole("row")[n];

    it("validates from the list after the native confirm, shows the message and reloads with a GET", async () => {
      serve(() => lista());
      ok("Documento validado correctamente.");
      const confirm = confirmWith(true);
      setup(LISTADO);
      await screen.findByText("Comedor <Uno>");
      const gets = webGet.mock.calls.length;
      fireEvent.click(within(row(1)).getByRole("button", { name: "Validar" }));
      await screen.findByText("Documento validado correctamente.");
      expect(confirm).toHaveBeenCalledWith("¿Estás seguro de que querés validar este documento?");
      expect(webPost).toHaveBeenCalledTimes(1);
      expect(webPost.mock.calls[0][0]).toBe("web/comedores/rendicion_cuentas_final/documentos/1/validar/");
      await waitFor(() => expect(webGet.mock.calls.length).toBeGreaterThan(gets));
    });

    it("does not send when the confirm is cancelled and sends once on a double click", async () => {
      serve(() => lista());
      ok("Documento validado correctamente.");
      const confirm = confirmWith(false);
      setup(LISTADO);
      await screen.findByText("Comedor <Uno>");
      const boton = within(row(1)).getByRole("button", { name: "Validar" });
      fireEvent.click(boton);
      expect(webPost).not.toHaveBeenCalled();
      confirm.mockReturnValue(true);
      fireEvent.click(boton);
      fireEvent.click(boton);
      await screen.findByText("Documento validado correctamente.");
      expect(webPost).toHaveBeenCalledTimes(1);
    });

    it("reports an unconfirmed outcome without resending", async () => {
      serve(() => lista());
      webPost.mockResolvedValue({ status: 504, data: { uncertain: true } });
      confirmWith(true);
      setup(LISTADO);
      await screen.findByText("Comedor <Uno>");
      fireEvent.click(within(row(1)).getByRole("button", { name: "Validar" }));
      await screen.findByText("No se pudo confirmar el resultado.");
      expect(webPost).toHaveBeenCalledTimes(1);
    });

    it("subsanar opens the native modal with an empty required textarea and sends the observation", async () => {
      serve(() => lista());
      ok("Documento enviado a subsanar correctamente.");
      setup(LISTADO);
      await screen.findByText("Comedor <Uno>");
      fireEvent.click(within(row(1)).getByRole("button", { name: "Subsanar" }));
      const dialog = await screen.findByRole("dialog", { name: "Subsanar Documento" });
      const area = within(dialog).getByLabelText("Observación") as HTMLTextAreaElement;
      expect([area.value, area.maxLength, area.required]).toEqual(["", 150, true]);
      expect(document.activeElement).toBe(dialog);
      fireEvent.change(area, { target: { value: "Falta firma" } });
      fireEvent.click(within(dialog).getByRole("button", { name: "Enviar a Subsanar" }));
      await screen.findByText("Documento enviado a subsanar correctamente.");
      const [url, body] = webPost.mock.calls[0];
      expect(url).toBe("web/comedores/rendicion_cuentas_final/documentos/1/subsanar/");
      expect((body as FormData).get("observacion")).toBe("Falta firma");
      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    });

    it("subsanar closes with Escape and Cancelar without sending", async () => {
      serve(() => lista());
      setup(LISTADO);
      await screen.findByText("Comedor <Uno>");
      const abrir = () => fireEvent.click(within(row(1)).getByRole("button", { name: "Subsanar" }));
      abrir();
      await screen.findByRole("dialog");
      fireEvent.keyDown(document, { key: "Escape" });
      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
      abrir();
      fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Cancelar" }));
      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
      expect(webPost).not.toHaveBeenCalled();
    });

    it("detail: validar, eliminar and the switch post to the native-equivalent endpoints", async () => {
      serve(() => detalle());
      ok("Hecho.");
      confirmWith(true);
      setup(DETALLE);
      await screen.findByText("Historial de Documentos");
      fireEvent.click(screen.getAllByRole("button", { name: "Validar" }).find((b) => !b.hasAttribute("disabled"))!);
      await screen.findByText("Hecho.");
      expect(webPost.mock.calls[0][0]).toBe("web/comedores/rendicion_cuentas_final/documentos/1/validar/");
      fireEvent.click(document.querySelector<HTMLButtonElement>("button.bi-trash:not([disabled])")!);
      await waitFor(() => expect(webPost).toHaveBeenCalledTimes(2));
      expect(webPost.mock.calls[1][0]).toBe("web/comedores/rendicion_cuentas_final/documentos/1/eliminar/");
      await waitFor(() => expect(screen.getByLabelText("Revisión físicamente presentada").hasAttribute("disabled")).toBe(false));
      fireEvent.click(screen.getByLabelText("Revisión físicamente presentada"));
      await waitFor(() => expect(webPost).toHaveBeenCalledTimes(3));
      expect(webPost.mock.calls[2][0]).toBe("web/comedores/rendicion_cuentas_final/3/fisicamente_presentada/");
    });

    it("detail: adjuntar sends the chosen file with the document id", async () => {
      serve(() => detalle());
      ok("Archivo adjuntado correctamente.");
      confirmWith(true);
      setup(DETALLE);
      await screen.findAllByRole("button", { name: "Adjuntar" });
      fireEvent.click(screen.getAllByRole("button", { name: "Adjuntar" }).find((b) => !b.hasAttribute("disabled"))!);
      const dialog = await screen.findByRole("dialog", { name: "Adjuntar archivo" });
      expect(within(dialog).getByText("Documento: Informe Contable")).toBeTruthy();
      fireEvent.change(within(dialog).getByLabelText("Archivo"), { target: { files: [fileOf("c.pdf")] } });
      fireEvent.submit(dialog.querySelector("form")!);
      await screen.findByText("Archivo adjuntado correctamente.");
      const [url, body] = webPost.mock.calls[0];
      expect(url).toBe("web/comedores/rendicion_cuentas_final/documentos/adjuntar/");
      expect((body as FormData).get("documento_id")).toBe("2");
      expect(((body as FormData).get("archivo") as File).name).toBe("c.pdf");
    });

    it("detail: crear sends the name and the optional file", async () => {
      serve(() => detalle());
      ok("");
      confirmWith(true);
      setup(DETALLE);
      fireEvent.click(await screen.findByRole("button", { name: "Añadir documento personalizado" }));
      const dialog = await screen.findByRole("dialog", { name: "Nuevo Documento Personalizado" });
      fireEvent.change(within(dialog).getByLabelText("Nombre del documento"), { target: { value: "Acta" } });
      fireEvent.click(within(dialog).getByRole("button", { name: "Crear" }));
      await waitFor(() => expect(webPost).toHaveBeenCalledTimes(1));
      const [url, body] = webPost.mock.calls[0];
      expect(url).toBe("web/comedores/rendicion_cuentas_final/3/crear/");
      expect((body as FormData).get("nombre")).toBe("Acta");
      expect((body as FormData).has("archivo")).toBe(false);
    });

    it("a native-style 400 and a 403 show their message", async () => {
      serve(() => lista());
      webPost.mockResolvedValue({ status: 400, data: { ok: false, message: "No se seleccionó ningún archivo." } });
      confirmWith(true);
      setup(LISTADO);
      await screen.findByText("Comedor <Uno>");
      fireEvent.click(within(row(1)).getByRole("button", { name: "Validar" }));
      await screen.findByText("No se seleccionó ningún archivo.");
      webPost.mockResolvedValue({ status: 403, data: { detail: "Sin permiso" } });
      await waitFor(() => expect(within(row(1)).getByRole("button", { name: "Validar" }).hasAttribute("disabled")).toBe(false));
      fireEvent.click(within(row(1)).getByRole("button", { name: "Validar" }));
      await screen.findByText("Sin permiso");
    });
  });
});
