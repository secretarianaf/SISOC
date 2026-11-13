import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { nominaListaNavigation } from "./cdiNominaLista";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const row = (id: number, over: Record<string, unknown> = {}) => ({
  id, estado: "activo", sala_filtro: "Sala 1", fecha: "01/10/2026", nombre: `Ramírez${id}, Sofía`, ciudadano_url: `/ciudadanos/ver/${id}`,
  dni: "30111222", sexo: "Femenino", edad: "3", sala: "Sala 1", derivar_nombre: `Sofía Ramírez${id}`,
  urls: { ver: `/centrodeinfancia/7/nomina/${id}/ver/`, editar: `/centrodeinfancia/7/nomina/${id}/editar/`, borrar: `/centrodeinfancia/7/nomina/${id}/eliminar/` },
  ...over,
});
const range = (num: string, pct: string, zero = false) => ({ num, pct, width: Number(pct), zero });
const lista = (over: Record<string, unknown> = {}) => ({
  centro: { id: 7, nombre: "CDI Girasoles", url: "/centrodeinfancia/detalle/7", codigo_cdi: "CDI-7", ubicacion: "Godoy Cruz, Mendoza" },
  stats: { asistentes: "3", hombres: "1", mujeres: "2", x: "0", menores: "1", espera: "1" },
  rangos: {
    ninos: range("1", "100"), adolescentes: range("0", "0", true), adultos: range("0", "0", true),
    adultos_mayores: range("0", "0", true), adulto_mayor_avanzado: range("0", "0", true),
  },
  rows: [row(1), row(2, { estado: "pendiente", sala_filtro: "Sala 2", sala: "Sala 2", nombre: "Pérez, Juan" }), row(3, { estado: "baja", sala_filtro: "", sala: "-" })],
  page: { has_other_pages: false, number: 1, num_pages: 1, count: 3, start: 1, end: 3, previous: null, next: null },
  centros_para_derivar: [{ id: 8, nombre: "CDI Destino" }, { id: 9, nombre: "CDI Otro" }],
  urls: { lista: "/centrodeinfancia/listar", crear: "/centrodeinfancia/7/nomina/crear/" },
  messages: [],
  ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}

function setup(path = "/centrodeinfancia/7/nomina/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

const tableRows = () => within(document.getElementById("tablaNomina") as HTMLElement).getAllByRole("row").slice(1);
const visible = () => tableRows().filter((r) => !r.hidden).map((r) => r.getAttribute("data-estado"));

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
  setViewport(false);
  vi.spyOn(nominaListaNavigation, "reload").mockImplementation(() => undefined);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CDI nómina list route", () => {
  it("owns only the native list path", () => {
    expect(findRoute("/centrodeinfancia/7/nomina/")?.route.name).toBe("cdi-nomina-lista");
    for (const other of ["/centrodeinfancia/7/nomina", "/centrodeinfancia/0/nomina/", "/centrodeinfancia/7/nomina/formulario/", "/centrodeinfancia/7/nomina/asistencia/"]) {
      expect(findRoute(other)?.route.name).toBe("business");
    }
  });

  it("loads session and page, keeps the page query and draws hero, metrics and rows", async () => {
    serve(lista());
    setup("/centrodeinfancia/7/nomina/?page=1");
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/7/nomina/?page=1", expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nómina – CDI Girasoles"));
    expect(screen.getByText("Centro de Desarrollo Infantil · Nómina")).toBeDefined();
    expect(screen.getByText("N° CDI-7")).toBeDefined();
    expect(Array.from(document.querySelectorAll(".cdi-stat-card")).map((c) => c.textContent)).toEqual([
      "3Asistentes", "1Hombres", "2Mujeres", "0Género X", "1Menores de edad", "1Lista de espera",
    ]);
    const crumbs = Array.from(document.querySelectorAll(".breadcrumb-item")).map((c) => c.textContent);
    expect(crumbs).toEqual(["Centros de Desarrollo Infantil", "CDI Girasoles", "Nómina"]);
    expect(screen.getByRole("link", { name: "Agregar persona" }).getAttribute("href")).toBe("/centrodeinfancia/7/nomina/crear/");
    const [activa, pendiente, baja] = tableRows();
    expect(activa.textContent).toBe("01/10/2026Ramírez1, Sofía30111222Femenino3Sala 1ActivoVer Editar Derivar Borrar");
    expect(within(activa).getByRole("link", { name: "Ramírez1, Sofía" }).getAttribute("href")).toBe("/ciudadanos/ver/1");
    expect(within(activa).getByRole("link", { name: "Ver" }).getAttribute("href")).toBe("/centrodeinfancia/7/nomina/1/ver/");
    expect(within(pendiente).getByText("Pendiente").className).toBe("cdf-pill cdf-pill--gold");
    expect(within(pendiente).queryByRole("button", { name: "Derivar" })).toBeNull();
    expect(within(baja).getByText("Baja").className).toBe("cdf-pill cdf-pill--muted");
    expect(within(baja).queryByRole("button", { name: "Derivar" })).toBeNull();
    expect(screen.queryByText(/Mostrando/)).toBeNull();
  });

  it("shows the empty row and omits the code pill without a code", async () => {
    serve(lista({ rows: [], centro: { ...lista().centro, codigo_cdi: "" } }));
    setup();
    expect(await screen.findByText("No hay registros en la nómina.")).toBeDefined();
    expect(screen.queryByText(/^N° /)).toBeNull();
  });

  it("toggles the detailed statistics and remembers it like nomina_detail.js", async () => {
    serve(lista());
    setup();
    const toggle = await screen.findByRole("button", { name: "Ver estadísticas detalladas" });
    const body = document.getElementById("detailedStatsContent") as HTMLElement;
    expect(body.style.display).toBe("none");
    expect(body.querySelectorAll(".cdi-dist-row.is-zero").length).toBe(4);
    expect((body.querySelector(".cdi-dist-fill") as HTMLElement).style.width).toBe("100%");
    fireEvent.click(toggle);
    expect(body.style.display).toBe("block");
    expect(toggle.textContent).toContain("Ocultar estadísticas detalladas");
    expect(toggle.querySelector("i")?.className).toContain("rotated");
    expect(window.localStorage.getItem("nominaDetailsExpanded")).toBe("true");
    cleanup();
    serve(lista());
    setup();
    await screen.findByRole("button", { name: "Ocultar estadísticas detalladas" });
    expect((document.getElementById("detailedStatsContent") as HTMLElement).style.display).toBe("block");
  });

  it("filters the current page by text, state and room like the native script", async () => {
    serve(lista());
    setup();
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    expect(Array.from((document.getElementById("nominaFiltroSala") as HTMLSelectElement).options).map((o) => o.value)).toEqual(["", "Sala 1", "Sala 2"]);
    fireEvent.change(screen.getByLabelText("Filtrar por estado"), { target: { value: "pendiente" } });
    expect(visible()).toEqual(["pendiente"]);
    fireEvent.change(screen.getByLabelText("Filtrar por estado"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Filtrar por sala"), { target: { value: "Sala 1" } });
    expect(visible()).toEqual(["activo"]);
    fireEvent.change(screen.getByLabelText("Filtrar por sala"), { target: { value: "" } });
    fireEvent.change(screen.getByPlaceholderText("Buscar en nómina…"), { target: { value: "  PÉREZ " } });
    expect(visible()).toEqual(["pendiente"]);
    // The native filter reads the whole row text, action labels included.
    fireEvent.change(screen.getByPlaceholderText("Buscar en nómina…"), { target: { value: "derivar" } });
    expect(visible()).toEqual(["activo"]);
    fireEvent.change(screen.getByPlaceholderText("Buscar en nómina…"), { target: { value: "" } });
    expect(visible()).toEqual(["activo", "pendiente", "baja"]);
  });

  it("draws the native pagination with disabled ends", async () => {
    serve(lista({ page: { has_other_pages: true, number: 1, num_pages: 2, count: 103, start: 1, end: 100, previous: null, next: 2 } }));
    setup();
    expect(await screen.findByText("Mostrando 1-100 de 103")).toBeDefined();
    expect(screen.getByRole("link", { name: "Página siguiente" }).getAttribute("href")).toBe("?page=2");
    expect(screen.getByText("Anterior").getAttribute("aria-disabled")).toBe("true");
    expect(screen.getByText("Anterior").getAttribute("tabindex")).toBe("-1");
    expect(screen.getByText("1 de 2")).toBeDefined();
  });

  it("asks for confirmation before following Borrar", async () => {
    serve(lista());
    setup();
    await screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const link = within(tableRows()[0]).getByRole("link", { name: "Borrar" });
    expect(link.getAttribute("href")).toBe("/centrodeinfancia/7/nomina/1/eliminar/");
    expect(fireEvent.click(link)).toBe(false);
    expect(confirm).toHaveBeenCalledWith("¿Está seguro de eliminar este registro?");
    confirm.mockReturnValue(true);
    expect(fireEvent.click(link)).toBe(true);
  });
});

describe("CDI nómina derivation modal", () => {
  async function open() {
    serve(lista());
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Derivar" }));
    return screen.findByRole("dialog");
  }

  it("opens with the person, the scoped centres and an empty form, and closes without a request", async () => {
    const dialog = await open();
    expect(within(dialog).getByText("Derivar persona", { selector: "h5" })).toBeDefined();
    expect(within(dialog).getByText("Sofía Ramírez1").tagName).toBe("STRONG");
    expect(Array.from((within(dialog).getByLabelText("Centro destino") as HTMLSelectElement).options).map((o) => o.textContent))
      .toEqual(["-- Seleccionar centro --", "CDI Destino", "CDI Otro"]);
    expect(document.getElementById("derivarMensaje")?.className).toBe("alert d-none");
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(webPost).not.toHaveBeenCalled();
  });

  it("warns without a destination and sends nothing", async () => {
    const dialog = await open();
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirmar derivación" }));
    const alert = document.getElementById("derivarMensaje") as HTMLElement;
    expect(alert.className).toBe("alert alert-warning");
    expect(alert.textContent).toBe("Seleccioná un centro destino.");
    expect(webPost).not.toHaveBeenCalled();
  });

  it("posts the URL-encoded destination and the untrimmed reason once, then reloads", async () => {
    let resolve: (value: unknown) => void = () => undefined;
    webPost.mockReturnValue(new Promise((r) => { resolve = r; }));
    const dialog = await open();
    fireEvent.change(within(dialog).getByLabelText("Centro destino"), { target: { value: "9" } });
    fireEvent.change(within(dialog).getByLabelText(/Motivo/), { target: { value: "  Mudanza  " } });
    const confirm = within(dialog).getByRole("button", { name: "Confirmar derivación" });
    fireEvent.click(confirm);
    fireEvent.click(confirm);
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe("web/cdi/nomina/1/derivar/");
    expect((body as URLSearchParams).toString()).toBe("centro_destino_id=9&motivo=++Mudanza++");
    expect((confirm as HTMLButtonElement).disabled).toBe(true);
    resolve({ data: { success: true, message: "Derivación realizada correctamente." }, status: 200 });
    await waitFor(() => expect(nominaListaNavigation.reload).toHaveBeenCalledTimes(1));
  });

  it("shows the server message of a rejected derivation and allows another attempt", async () => {
    webPost.mockResolvedValue({ data: { success: false, message: "Solo se pueden derivar personas con estado Activo." }, status: 400 });
    const dialog = await open();
    fireEvent.change(within(dialog).getByLabelText("Centro destino"), { target: { value: "8" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirmar derivación" }));
    await waitFor(() => expect(document.getElementById("derivarMensaje")?.textContent).toBe("Solo se pueden derivar personas con estado Activo."));
    expect(document.getElementById("derivarMensaje")?.className).toBe("alert alert-danger");
    expect((within(dialog).getByRole("button", { name: "Confirmar derivación" }) as HTMLButtonElement).disabled).toBe(false);
    expect(nominaListaNavigation.reload).not.toHaveBeenCalled();
  });

  it("falls back to the native generic messages for a body without message or a failed request", async () => {
    webPost.mockResolvedValueOnce({ data: { detail: "No tiene permisos para esta acción." }, status: 403 });
    const dialog = await open();
    fireEvent.change(within(dialog).getByLabelText("Centro destino"), { target: { value: "8" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirmar derivación" }));
    await waitFor(() => expect(document.getElementById("derivarMensaje")?.textContent).toBe("Error al derivar."));
    webPost.mockRejectedValueOnce(new Error("network"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirmar derivación" }));
    await waitFor(() => expect(document.getElementById("derivarMensaje")?.textContent).toBe("Error de conexión. Intentá nuevamente."));
    webPost.mockResolvedValueOnce({ data: "<html></html>", status: 502 });
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirmar derivación" }));
    await waitFor(() => expect(webPost).toHaveBeenCalledTimes(3));
    await waitFor(() => expect(document.getElementById("derivarMensaje")?.textContent).toBe("Error de conexión. Intentá nuevamente."));
  });

  it("traps Tab inside the open modal and closes with Escape", async () => {
    const dialog = await open();
    const confirm = within(dialog).getByRole("button", { name: "Confirmar derivación" });
    confirm.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: "Cerrar" }));
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("pulls focus back into the modal when it lands outside, like Bootstrap's focus trap", async () => {
    const dialog = await open();
    const outside = screen.getByRole("link", { name: "Agregar persona" });
    outside.focus();
    expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: "Cerrar" }));
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    outside.focus();
    expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: "Confirmar derivación" }));
  });
});

describe("CDI nómina list states", () => {
  it("shows pending messages and reports forbidden, not found and invalid payloads", async () => {
    serve(lista({ messages: [{ message: "Ficha creada y agregada a la nómina.", level: "success" }] }));
    setup();
    expect(await screen.findByText("Ficha creada y agregada a la nómina.")).toBeDefined();
    cleanup();
    serve({ detail: "No tiene permiso." }, 403);
    setup();
    expect(await screen.findByText("¡Ups! Algo salió mal.")).toBeDefined();
    cleanup();
    serve({ detail: "No encontrado." }, 404);
    setup();
    expect(await screen.findByText("No se encontró la página.")).toBeDefined();
    cleanup();
    serve(lista({ rows: [{ id: "x" }] }));
    setup();
    expect(await screen.findByText("No se pudo cargar la página.")).toBeDefined();
  });
});
