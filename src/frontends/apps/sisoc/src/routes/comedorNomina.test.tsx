import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { comedorNominaNavigation, nominaValid } from "./comedorNomina";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const DIRECTA = "/comedores/7/nomina/";
const ADMISION = "/comedores/7/admision/3/nomina/";
const API = "web/comedores/comedores/";

const stats = {
  asistentes: "2", espera: "1", baja: "0", hombres: "1", mujeres: "1", no_binarios: "0", ninos: "1", adolescentes: "0",
  adultos: "1", adultos_mayores: "0", adulto_mayor_avanzado: "0",
};
const row = (id: number, estado: string, over: Record<string, unknown> = {}) => ({
  id, estado, ciudadano_id: id + 100, comunidad_indigena: false, situacion_calle: false, celiaquia: false,
  fecha: "05/11/2026", nombre: "Ana", apellido: "Gómez", documento: "30111222", sexo: "Femenino",
  estado_label: estado === "activo" ? "Activo" : "En espera", derivar_nombre: "Ana Gómez",
  urls: { ciudadano: `/ciudadanos/ver/${id + 100}`, cambiar_estado: `/comedores/nomina/${id}/cambiar-estado/`, derivar: `/comedores/nomina/${id}/derivar/`,
    borrar: `/comedores/7/nomina/${id}/eliminar/` },
  ...over,
});
const data = (over: Record<string, unknown> = {}) => ({
  comedor: { id: 7, nombre: "Comedor Norte", provincia: "Chaco", municipio: null },
  header: { inicio: "-", fin: "-", plazo: "-" }, stats, tabs: null, tab: "todas", dni: "", can_view_ciudadano: true,
  rows: [row(1, "activo", { comunidad_indigena: true, celiaquia: true }), row(2, "espera", { apellido: "Ruiz", nombre: "Beto" })],
  page: { has_other_pages: false, number: 1, num_pages: 1, count: 2, start: 1, end: 2, previous: null, next: null },
  estados: [["activo", "Activo"], ["espera", "En espera"], ["baja", "Baja"]], comedores_para_derivar: [{ id: 9, nombre: "Otro" }],
  urls: { comedores: "/comedores/listar", comedor: "/comedores/7", lista: DIRECTA, historial: null, crear: "/comedores/7/nomina/crear/" },
  messages: [], ...over,
});

function serve(payload: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: payload, status: 200 }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

let reload: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  reload = vi.spyOn(comedorNominaNavigation, "reload").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); reload.mockRestore(); });

describe("Comedor nómina read route (CO01)", () => {
  it("owns only the two native nómina URLs", () => {
    expect(findRoute(DIRECTA)?.route.name).toBe("comedor-nomina");
    expect(findRoute(ADMISION)?.route.name).toBe("comedor-nomina");
    for (const other of ["/comedores/7/nomina", "/comedores/7/nomina/crear/", "/comedores/7/admision/3/nomina/crear/", "/comedores/7/admision/3/nomina/asistencia/", "/comedores/0/nomina/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedor-nomina");
    }
  });

  it("reads the direct endpoint with the query and renders the native heading, metrics and rows", async () => {
    serve(data());
    setup(`${DIRECTA}?dni=3011`);
    await screen.findByText("Asistentes 2");
    expect(webGet).toHaveBeenCalledWith(`${API}7/nomina/?dni=3011`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Nómina – Comedor Norte"));
    expect(document.querySelector("h3")!.textContent).toBe("Nómina de Comedor Norte | Chaco , -");
    expect(screen.getByText("Lista de espera 1")).toBeTruthy();
    expect(screen.getByText("Adultos mayores + (+66) 0")).toBeTruthy();
    expect(screen.getAllByText("-")).toHaveLength(3);
    expect(screen.getByRole("link", { name: "Agregar persona" }).getAttribute("href")).toBe("/comedores/7/nomina/crear/");
    expect(screen.queryByRole("link", { name: "Historial de asistencia" })).toBeNull();
    expect(document.querySelector(".nomina-tabs")).toBeNull();
    expect([...document.querySelectorAll(".nomina-person-badge")].map((b) => b.textContent)).toEqual(["Comunidad indígena", "Celiaquía"]);
    expect(screen.getByRole("link", { name: "Gómez" }).getAttribute("href")).toBe("/ciudadanos/ver/101");
    expect(screen.getAllByRole("link", { name: /Borrar/ })[1].getAttribute("href")).toBe("/comedores/7/nomina/2/eliminar/");
  });

  it("reads the admission endpoint and shows the history link", async () => {
    serve(data({ urls: { comedores: "/comedores/listar", comedor: "/comedores/7", lista: ADMISION, historial: "/comedores/7/admision/3/nomina/asistencia/", crear: "/comedores/7/admision/3/nomina/crear/" } }));
    setup(ADMISION);
    await screen.findByText("Asistentes 2");
    expect(webGet).toHaveBeenCalledWith(`${API}7/admision/3/nomina/`, expect.anything());
    expect(screen.getByRole("link", { name: "Historial de asistencia" }).getAttribute("href")).toBe("/comedores/7/admision/3/nomina/asistencia/");
  });

  it("shows the PNUD tabs, keeps the DNI in their links and clears the search", async () => {
    serve(data({ tabs: [{ key: "alimentaria", label: "Alimentaria", active: false }, { key: "todas", label: "Todas", active: true }], tab: "todas", dni: "30 1/2" }));
    setup(`${DIRECTA}?tab=todas&dni=30%201/2`);
    await screen.findByText("Asistentes 2");
    expect(screen.getByRole("link", { name: "Alimentaria" }).getAttribute("href")).toBe("?tab=alimentaria&dni=30%201/2");
    expect(screen.getByRole("link", { name: "Todas" }).className).toContain("active");
    expect(screen.getByRole("link", { name: "Limpiar" }).getAttribute("href")).toBe(`${DIRECTA}?tab=todas`);
    expect(document.querySelector<HTMLInputElement>('input[name="tab"]')!.value).toBe("todas");
    expect((screen.getByPlaceholderText("Buscar por DNI") as HTMLInputElement).value).toBe("30 1/2");
  });

  it("paginates with the native buttons and keeps tab and DNI in the links", async () => {
    serve(data({ tabs: [], tab: "todas", dni: "3011", page: { has_other_pages: true, number: 2, num_pages: 3, count: 250, start: 101, end: 200, previous: 1, next: 3 } }));
    setup(`${DIRECTA}?page=2`);
    await screen.findByText("Mostrando 101-200 de 250");
    expect(screen.getByText("2 de 3")).toBeTruthy();
    const links = document.querySelectorAll<HTMLAnchorElement>(".nomina-page-btn");
    expect([...links].map((a) => a.getAttribute("href"))).toEqual(["?page=1&tab=todas&dni=3011", "?page=3&tab=todas&dni=3011"]);
  });

  it("disables the edges and shows the empty message", async () => {
    serve(data({ rows: [], page: { has_other_pages: true, number: 1, num_pages: 2, count: 101, start: 1, end: 100, previous: null, next: 2 } }));
    setup(DIRECTA);
    await screen.findByText("No hay registros en la nómina.");
    expect((document.querySelector("button.nomina-page-btn") as HTMLButtonElement).disabled).toBe(true);
  });

  it("opens one menu at a time, closes it outside and with Escape, and only offers Derivar to active rows", async () => {
    serve(data());
    setup(DIRECTA);
    await screen.findByText("Asistentes 2");
    const [accionesActivo, accionesEspera] = screen.getAllByRole("button", { name: "Acciones" });
    fireEvent.click(accionesActivo);
    const menu = accionesActivo.nextElementSibling as HTMLElement;
    expect(menu.className).toContain("show");
    expect(within(menu).getByText(/Derivar/)).toBeTruthy();
    fireEvent.click(accionesEspera);
    expect(menu.className).not.toContain("show");
    expect(within(accionesEspera.nextElementSibling as HTMLElement).queryByText(/Derivar/)).toBeNull();
    fireEvent.keyDown(document, { key: "Escape" });
    expect((accionesEspera.nextElementSibling as HTMLElement).className).not.toContain("show");
    fireEvent.click(screen.getAllByRole("button", { name: "Activo" })[0]);
    expect(screen.getAllByRole("link", { name: "En espera" })[0].className).not.toContain("active");
    fireEvent.click(document.body);
    expect(document.querySelector(".dropdown-menu.show")).toBeNull();
  });

  it("asks before following the native delete link and respects a refusal", async () => {
    serve(data());
    setup(DIRECTA);
    await screen.findByText("Asistentes 2");
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const link = screen.getAllByRole("link", { name: /Borrar/ })[0];
    expect(fireEvent.click(link)).toBe(false);
    expect(confirm).toHaveBeenCalledWith("¿Está seguro de eliminar este registro?");
    confirm.mockReturnValue(true);
    expect(fireEvent.click(link)).toBe(true);
    confirm.mockRestore();
  });

  it("hides the person link without the ciudadano permission", async () => {
    serve(data({ can_view_ciudadano: false }));
    setup(DIRECTA);
    await screen.findByText("Asistentes 2");
    expect(screen.queryByRole("link", { name: "Gómez" })).toBeNull();
    expect(screen.queryByText(/Ver detalles/)).toBeNull();
  });

  it("rejects payloads that do not match the contract", () => {
    expect(nominaValid(data())).toBe(true);
    expect(nominaValid(data({ urls: { ...data().urls, crear: "https://evil.example/" } }))).toBe(false);
    expect(nominaValid(data({ rows: [row(1, "otro")] }))).toBe(false);
    expect(nominaValid(data({ stats: { ...stats, espera: 1 } }))).toBe(false);
    expect(nominaValid(null)).toBe(false);
  });

  it("shows the access screen on a 403", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "no" }, status: 403 }));
    setup(DIRECTA);
    await waitFor(() => expect(screen.queryByText("Cargando nómina…")).toBeNull());
    expect(screen.queryByText("Asistentes 2")).toBeNull();
  });

  it("posts the chosen estado once and reloads on success", async () => {
    serve(data());
    webPost.mockResolvedValue({ data: { success: true, estado: "baja" }, status: 200 });
    setup(DIRECTA);
    await screen.findByText("Asistentes 2");
    fireEvent.click(screen.getAllByRole("button", { name: "Activo" })[0]);
    fireEvent.click(screen.getAllByRole("link", { name: "Baja" })[0]);
    await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe("web/comedores/comedores/nomina/1/cambiar-estado/");
    expect(body.toString()).toBe("estado=baja");
  });

  it("alerts the native messages when the state change fails", async () => {
    serve(data());
    const alert = vi.spyOn(window, "alert").mockImplementation(() => undefined);
    setup(DIRECTA);
    await screen.findByText("Asistentes 2");
    const choose = () => { fireEvent.click(screen.getAllByRole("button", { name: "Activo" })[0]); fireEvent.click(screen.getAllByRole("link", { name: "Baja" })[0]); };
    webPost.mockResolvedValueOnce({ data: { success: false, error: "Estado inválido." }, status: 400 });
    choose();
    await waitFor(() => expect(alert).toHaveBeenLastCalledWith("Error al cambiar el estado."));
    webPost.mockResolvedValueOnce({ data: { success: false, error: "Estado inválido." }, status: 200 });
    choose();
    await waitFor(() => expect(alert).toHaveBeenLastCalledWith("No se pudo cambiar el estado: Estado inválido."));
    webPost.mockResolvedValueOnce({ data: { success: false }, status: 200 });
    choose();
    await waitFor(() => expect(alert).toHaveBeenLastCalledWith("No se pudo cambiar el estado: error desconocido"));
    webPost.mockRejectedValueOnce(new Error(""));
    choose();
    await waitFor(() => expect(alert).toHaveBeenLastCalledWith("Ocurrió un error al cambiar el estado."));
    expect(reload).not.toHaveBeenCalled();
    alert.mockRestore();
  });

  async function openDerivar() {
    serve(data());
    setup(DIRECTA);
    await screen.findByText("Asistentes 2");
    fireEvent.click(screen.getAllByRole("button", { name: "Acciones" })[0]);
    fireEvent.click(screen.getByText(/Derivar/));
    return screen.findByRole("dialog");
  }

  it("opens the derive modal for the person and asks for a destination before posting", async () => {
    const dialog = await openDerivar();
    expect(within(dialog).getByText("Ana Gómez")).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirmar derivación" }));
    expect(within(dialog).getByText("Seleccioná un centro destino.").className).toContain("alert-warning");
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("posts the derivation once with destination and motive, then reloads", async () => {
    webPost.mockResolvedValue({ data: { success: true, message: "Derivación realizada correctamente." }, status: 200 });
    const dialog = await openDerivar();
    fireEvent.change(within(dialog).getByLabelText("Centro destino"), { target: { value: "9" } });
    fireEvent.change(within(dialog).getByLabelText(/Motivo/), { target: { value: "Se muda" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirmar derivación" }));
    await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe("web/comedores/comedores/nomina/1/derivar/");
    expect(body.toString()).toBe("centro_destino_id=9&motivo=Se+muda");
  });

  it("shows a rejected derivation in the alert and never retries it", async () => {
    webPost.mockResolvedValueOnce({ data: { success: false, message: "Centro destino inválido." }, status: 400 });
    const dialog = await openDerivar();
    fireEvent.change(within(dialog).getByLabelText("Centro destino"), { target: { value: "9" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirmar derivación" }));
    expect((await within(dialog).findByText("Centro destino inválido.")).className).toContain("alert-danger");
    expect(webPost).toHaveBeenCalledTimes(1);
    webPost.mockRejectedValueOnce(new Error("net"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirmar derivación" }));
    expect(await within(dialog).findByText("Error de conexión. Intentá nuevamente.")).toBeTruthy();
    expect(reload).not.toHaveBeenCalled();
  });
});
