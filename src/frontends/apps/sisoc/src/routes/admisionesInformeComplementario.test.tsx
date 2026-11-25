import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";
import { complementarioNative } from "./admisionesInformeComplementario";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const NATIVO = "/comedores/admision/informe_complementario/base/5/ver/";
const API = "web/comedores/admisiones/informes/complementario/base/5/";
const EDITOR = "/comedores/admision/3/tecnicos/editar/";
const campo = (identificador: string, nombre: string, valor: string) => ({ identificador, nombre, valor });
const datos = (over: Record<string, unknown> = {}) => ({
  id: 5, tipo: "base", comedor: "Comedor Sintético", origen_acompanamiento: false, observaciones_legales: "",
  grupos: [
    { titulo: "Datos de la Organización", tipo: "campos", campos: [campo("expediente_nro", "Expediente", "EX-1"), campo("nombre", "Nombre", "Org")] },
    { titulo: "Prestaciones Aprobadas", tipo: "matriz", identificador: "aprobadas", filas: [{ titulo: "Almuerzo", campos: [campo("aprobadas_almuerzo_lunes", "Almuerzo lunes", "10")] }] },
  ],
  campos_modificados: {}, urls: { volver: EDITOR, pagina: NATIVO, accion: NATIVO }, messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path = NATIVO) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  webPost.mockReset();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => cleanup());

describe("Complementary technical report route (AD02.02)", () => {
  it("owns only the native complementary page", () => {
    expect(findRoute(NATIVO)?.params).toEqual({ tipo: "base", id: "5" });
    for (const other of ["/comedores/admision/informe_tecnico/base/5/ver/", "/comedores/admision/informe_complementario/base/5/ver", "/comedores/admision/informe_complementario/base/5/editar/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-informe-complementario");
    }
  });

  it("renders the heading, breadcrumb, legal observations, groups, matrix and the form buttons", async () => {
    serve(datos({ observaciones_legales: "Corregir la dirección", campos_modificados: { Expediente: "EX-2" }, messages: [{ message: "Aviso", level: "info" }] }));
    setup();
    await screen.findByText("Datos de la Organización");
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Informe Complementario: Comedor Sintético"));
    expect(screen.getByRole("link", { name: "Comedor Sintético" }).getAttribute("href")).toBe(EDITOR);
    expect(screen.getByText("Corregir la dirección")).toBeTruthy();
    expect(screen.getByText("Aviso")).toBeTruthy();
    expect(screen.getByText("Valor modificado:")).toBeTruthy();
    expect(screen.getAllByLabelText("Modificar campo")).toHaveLength(2);
    expect(screen.getByLabelText("Modificar Almuerzo lunes")).toBeTruthy();
    expect(screen.getByText("Almuerzo")).toBeTruthy();
    expect((document.querySelector("form a.btn-secondary") as HTMLAnchorElement).getAttribute("href")).toBe(EDITOR);
    expect((document.querySelector("#check_expediente_nro") as HTMLInputElement).checked).toBe(true);
    expect((document.querySelector("#input_expediente_nro") as HTMLElement).style.display).toBe("block");
    expect((document.querySelector("#input_nombre") as HTMLElement).style.display).toBe("none");
  });

  it("checking a field shows its required input and unchecking hides and clears it", async () => {
    serve(datos());
    setup();
    await screen.findByText("Datos de la Organización");
    const casilla = document.querySelector("#check_nombre") as HTMLInputElement;
    const entrada = document.querySelector("#campo_nombre") as HTMLInputElement;
    fireEvent.click(casilla);
    expect((document.querySelector("#input_nombre") as HTMLElement).style.display).toBe("block");
    expect(entrada.required).toBe(true);
    fireEvent.change(entrada, { target: { value: "Nuevo" } });
    expect(entrada.value).toBe("Nuevo");
    fireEvent.click(casilla);
    expect(entrada.value).toBe("");
    expect(entrada.required).toBe(false);
    expect((document.querySelector("#input_nombre") as HTMLElement).style.display).toBe("none");
  });

  it("posts the typed values to the G1 action and opens the redirect it answers", async () => {
    serve(datos());
    const navegar = vi.spyOn(complementarioNative, "navigate").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { success: true, messages: [], redirect: EDITOR } });
    setup();
    await screen.findByText("Datos de la Organización");
    fireEvent.click(document.querySelector("#check_nombre")!);
    fireEvent.change(document.querySelector("#campo_nombre")!, { target: { value: "Nuevo" } });
    fireEvent.submit(screen.getByRole("button", { name: "Guardar y Enviar para Validación" }).closest("form")!);
    await waitFor(() => expect(navegar).toHaveBeenCalledWith(EDITOR));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, cuerpo] = webPost.mock.calls[0];
    expect(url).toBe(API);
    expect((cuerpo as { values: Record<string, string> }).values).toMatchObject({ Nombre: "Nuevo", Expediente: "" });
    navegar.mockRestore();
  });

  it("keeps ?origen=acompanamiento in the data and the action URLs, and a rejection opens its page", async () => {
    const origen = "?origen=acompanamiento";
    serve(datos({ origen_acompanamiento: true, urls: { volver: `${EDITOR}?admision_id=3`, pagina: NATIVO + origen, accion: NATIVO } }));
    const navegar = vi.spyOn(complementarioNative, "navigate").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 400, data: { success: false, messages: [{ message: "x", level: "error" }], redirect: NATIVO + origen } });
    setup(NATIVO + origen);
    await screen.findByText("Datos de la Organización");
    expect(webGet).toHaveBeenCalledWith(API + origen, expect.anything());
    expect((document.querySelector("form a.btn-secondary") as HTMLAnchorElement).getAttribute("href")).toBe(`${EDITOR}?admision_id=3`);
    fireEvent.submit(screen.getByRole("button", { name: "Guardar y Enviar para Validación" }).closest("form")!);
    await waitFor(() => expect(navegar).toHaveBeenCalledWith(NATIVO + origen));
    expect(webPost.mock.calls[0][0]).toBe(API + origen);
    navegar.mockRestore();
  });

  it("a 403 of the POST is the shared access screen and any other failure the error screen", async () => {
    serve(datos());
    const navegar = vi.spyOn(complementarioNative, "navigate").mockImplementation(() => undefined);
    webPost.mockResolvedValueOnce({ status: 403, data: {} });
    setup();
    await screen.findByText("Datos de la Organización");
    fireEvent.submit(screen.getByRole("button", { name: "Guardar y Enviar para Validación" }).closest("form")!);
    expect((await screen.findByRole("link", { name: "volver al inicio" })).getAttribute("href")).toBe("/inicio/");
    cleanup();
    webPost.mockResolvedValueOnce({ status: 500, data: {} });
    setup();
    await screen.findByText("Datos de la Organización");
    fireEvent.submit(screen.getByRole("button", { name: "Guardar y Enviar para Validación" }).closest("form")!);
    expect(await screen.findByText("No se pudo cargar la página.")).toBeTruthy();
    expect(navegar).not.toHaveBeenCalled();
    navegar.mockRestore();
  });

  it("a 403 from the API is the access screen", async () => {
    serve({ detail: "denied" }, 403);
    setup();
    expect((await screen.findByRole("link", { name: "volver al inicio" })).getAttribute("href")).toBe("/inicio/");
  });
});
