import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { FichaPage } from "./comedorFicha";
import { admisionNavigation } from "./comedorFichaAdmision";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/comedores/7/admision/";
const marcas = (labels: string[]) => labels.map((label) => ({ label, marcado: false }));
const ficha = (over: Record<string, unknown> = {}) => ({
  id: 7, nombre: "Comedor Norte", messages: [],
  header: {
    validar: false, convenio_pnud: null, actividades: null, acompanamiento_territorial: null, historial: null, convenios: [],
    acciones: { editar: "/comedores/7/editar", responsable_tarjeta: null, eliminar: "/comedores/7/eliminar", equipo_tecnico: null, comenzar_admision: true },
  },
  titulo: { conformidad_pendiente: null, nombre: "Comedor Norte", validacion: "Pendiente", programa: "Sin programa", etiqueta_estado: "Activo", es_caritas: false, inicio_ejecucion: null, plazo_ejecucion: "-" },
  acordeon: {
    ubicacion: { mapa: { tipo: "vacio", src: null }, datos: [] },
    responsables: { foto: { url: "/static/custom/img/default.png", webp: null, default: true }, hay_organizacion: false, items: [], firmantes: [], avales: [] },
    prestaciones: { colaboradores: "-", dias_por_semana: "-", prestaciones_mensuales: "-", monto_mensual: "-", dias: ["Lunes"], filas: [{ comida: "Desayuno", valores: ["-"] }] },
    relevamientos: { titulo: "Acompañamiento Territorial", pnud: false, donaciones: marcas(["Particulares"]), servicio: marcas(["Vianda"]), espacio: marcas(["Propio"]), actividades_anexo: [] },
  },
  ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
let assign: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  window.history.replaceState({}, "", "/comedores/7");
  assign = vi.spyOn(admisionNavigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); assign.mockRestore(); });

async function openModal() {
  fireEvent.click(await screen.findByRole("button", { name: /Acciones/ }));
  fireEvent.click(screen.getByRole("button", { name: /Comenzar Admisión/ }));
  return screen.findByRole("dialog");
}
const choose = (value: string) => {
  fireEvent.change(document.getElementById("admisionID")!, { target: { value } });
  fireEvent.submit(document.querySelector("#modalAdmision form")!);
};

describe("Comedor ficha: Comenzar Admisión", () => {
  it("shows the queued native messages of the ficha", async () => {
    serve(ficha({ messages: [{ message: "Se creó una nueva admisión de tipo 'Incorporación' correctamente.", level: "success" }] }));
    render(<FichaPage id="7" />);
    expect(await screen.findByText(/Se creó una nueva admisión/)).toBeTruthy();
  });

  it("the menu item opens the native modal with its two types", async () => {
    serve(ficha());
    render(<FichaPage id="7" />);
    const dialog = await openModal();
    expect(dialog.textContent).toContain("Seleccione el tipo de Admisión");
    const select = document.getElementById("admisionID") as HTMLSelectElement;
    expect([...select.options].map((o) => [o.value, o.textContent])).toEqual([["", "-- Seleccione --"], ["incorporacion", "Incorporación"], ["renovacion", "Renovación"]]);
    expect(select.required).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(webPost).not.toHaveBeenCalled();
  });

  it("the menu item is absent when the API says the comedor cannot start an admission", async () => {
    const body = ficha();
    body.header.acciones.comenzar_admision = false;
    serve(body);
    render(<FichaPage id="7" />);
    fireEvent.click(await screen.findByRole("button", { name: /Acciones/ }));
    expect(screen.queryByRole("button", { name: /Comenzar Admisión/ })).toBeNull();
  });

  it("posts the chosen type and goes to the ficha that shows the message", async () => {
    serve(ficha());
    webPost.mockResolvedValue({ status: 201, data: { created: true, redirect: "/comedores/7", message: { level: "success", text: "ok" } } });
    render(<FichaPage id="7" />);
    await openModal();
    choose("renovacion");
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/7"));
    const [endpoint, body] = webPost.mock.calls[0];
    expect(endpoint).toBe(API);
    expect(String(body)).toBe("admision=renovacion");
  });

  it("a refused admission also goes to the ficha (the native flow redirects with the message)", async () => {
    serve(ficha());
    webPost.mockResolvedValue({ status: 200, data: { created: false, redirect: "/comedores/7", message: { level: "warning", text: "Ya existe" } } });
    render(<FichaPage id="7" />);
    await openModal();
    choose("incorporacion");
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/7"));
  });

  it("an uncertain outcome keeps the modal, shows the notice and is not retried", async () => {
    serve(ficha());
    webPost.mockRejectedValue({ response: { status: 504, data: { uncertain: true } } });
    render(<FichaPage id="7" />);
    await openModal();
    choose("incorporacion");
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(assign).not.toHaveBeenCalled();
  });

  it("a 403 shows the API detail and stays", async () => {
    serve(ficha());
    webPost.mockResolvedValue({ status: 403, data: { detail: "Usted no tiene permiso para realizar esta acción." } });
    render(<FichaPage id="7" />);
    await openModal();
    choose("incorporacion");
    expect(await screen.findByText("Usted no tiene permiso para realizar esta acción.")).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
  });

  it("Escape closes the modal", async () => {
    serve(ficha());
    render(<FichaPage id="7" />);
    await openModal();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
