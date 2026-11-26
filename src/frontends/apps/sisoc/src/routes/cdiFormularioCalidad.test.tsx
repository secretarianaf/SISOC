import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { cdiFormularioCalidadRoute } from "./cdiFormularioCalidad";
import { readyContext } from "./testFixtures";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: () => ({ get, post }),
  leerCookie: () => "synthetic-csrf-token",
}));

const centro = { id: 7, nombre: "CDI Girasoles", url: "/centrodeinfancia/detalle/7" };
const base = "/centrodeinfancia/7/calidad/";

function renderRoute(path: string) {
  const params = cdiFormularioCalidadRoute.match(path);
  if (!params) throw new Error("Expected a matching route");
  return render(cdiFormularioCalidadRoute.render(params));
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

it("links from the canonical history to the draft and sent record", async () => {
  get.mockImplementation((path: string) => Promise.resolve({ data: path === "web/session/" ? readyContext : {
    centro, messages: [], cargar_url: base + "cargar/", borrador_modificado: "24/11/2026 10:00",
    rows: [{ id: 4, fecha_envio: "23/11/2026 11:00", enviado_por: "Ana", url: base + "4/" }],
    page: { number: 1, previous: null, next: 2 },
  } }));
  renderRoute(base);
  expect((await screen.findByRole("link", { name: "Continuar borrador" })).getAttribute("href")).toBe(base + "cargar/");
  expect(screen.getByRole("link", { name: "Ver formulario 4" }).getAttribute("href")).toBe(base + "4/");
  expect(screen.getByRole("link", { name: "Siguiente" }).getAttribute("href")).toBe("?page=2");
});

it("clears hidden answers and shows incomplete-send feedback without navigating away", async () => {
  const form = {
    centro, messages: [], codigo: "CDI-7", cartel: "Complete la encuesta.", errores: {},
    es_borrador_existente: false,
    secciones: [{ id: "info", titulo: "Información del centro", preguntas: [
      { numero: 1, texto: "Tenencia", subtitulo: "", nota: "", tipo: "radio", control: null,
        filas: [{ etiqueta: "", campo: { nombre: "p1", valor: "", opciones: [["1", "Propio"], ["2", "Otro"]] } }],
        especificar: { etiqueta: "Especifique", control: "p1", valor: "2", campo: { nombre: "p1_otro", valor: "", opciones: [] } }, error: null },
    ] }],
  };
  get.mockImplementation((path: string) => Promise.resolve({ data: path === "web/session/" ? readyContext : form }));
  post.mockResolvedValue({ status: 400, data: {
    ...form, es_borrador_existente: true, errores: { 1: "Ingrese el dato." },
    messages: [{ message: "Se guardó el avance como borrador.", level: "warning" }],
    secciones: [{ ...form.secciones[0], preguntas: [{ ...form.secciones[0].preguntas[0], error: "Ingrese el dato." }] }],
  } });
  renderRoute(base + "cargar/");
  fireEvent.click(await screen.findByLabelText("Otro"));
  fireEvent.change(screen.getByLabelText("Especifique"), { target: { value: "Alquilado" } });
  fireEvent.click(screen.getByLabelText("Propio"));
  expect(screen.queryByLabelText("Especifique")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
  await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
  const [url, body] = post.mock.calls[0];
  expect(url).toBe("web/cdi/centros/7/calidad/cargar/");
  expect(body.get("accion")).toBe("enviar");
  expect(body.get("p1")).toBe("1");
  expect(body.has("p1_otro")).toBe(false);
  expect(await screen.findByText("Ingrese el dato.")).toBeTruthy();
  expect(screen.getByText("continuando borrador guardado", { exact: false })).toBeTruthy();
});


it("blocks implicit keyboard and concurrent sends", async () => {
  const form = {
    centro, messages: [], codigo: "", cartel: "", errores: {}, es_borrador_existente: false,
    secciones: [{ id: "info", titulo: "Información", preguntas: [
      { numero: 1, texto: "Salas", nota: "", subtitulo: "", tipo: "numero", control: null, especificar: null, error: null,
        filas: [{ etiqueta: "", campo: { nombre: "p1", valor: "", opciones: [] } }] },
    ] }],
  };
  get.mockImplementation((path: string) => Promise.resolve({ data: path === "web/session/" ? readyContext : form }));
  let finish: (response: unknown) => void = () => {};
  post.mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  renderRoute(base + "cargar/");
  const number = await screen.findByRole("spinbutton", { name: "Salas" });
  expect(fireEvent.keyDown(number, { key: "Enter" })).toBe(false);
  expect(post).not.toHaveBeenCalled();
  const send = screen.getByRole("button", { name: "Enviar" }) as HTMLButtonElement;
  fireEvent.click(send);
  expect(send.disabled).toBe(true);
  fireEvent.click(send);
  expect(post).toHaveBeenCalledTimes(1);
  finish({ status: 500 });
  expect(await screen.findByText(/Verificá el historial/)).toBeTruthy();
});

it("does not swallow neighbouring or noncanonical paths", () => {
  expect(cdiFormularioCalidadRoute.match("/centrodeinfancia/7/formularios/4/")).toBeNull();
  expect(cdiFormularioCalidadRoute.match("/centrodeinfancia/7/calidad/4")).toBeNull();
  expect(cdiFormularioCalidadRoute.match(base + "4/")).toMatchObject({ screen: "detail", formId: "4" });
});
