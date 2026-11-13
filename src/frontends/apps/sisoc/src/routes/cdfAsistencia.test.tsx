import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { navigation } from "./cdfFrame";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const URL_API = "web/cdf/actividades/9/asistencia/";
const fila = (id: number, presente: boolean | null) => ({ id, apellido: `Ape${id}`, nombre: `Nom${id}`, documento: `3011${id}`, presente });
const pagina = (over: Record<string, unknown> = {}) => ({
  actividad: { id: 9, nombre: "Futbol", categoria: "Deportes", estado_display: "En curso", horariosdesde: "09:00", horarioshasta: "10:30" },
  centro: { id: 4, nombre: "CDF Cuatro" }, fecha: "2026-10-01", fecha_display: "01/10/2026", fecha_error: null, ya_tomada: true,
  totales: { presentes: 1, ausentes: 1, sin_marcar: 1 },
  filas: [fila(1, true), fila(2, false), fila(3, null)],
  urls: { centro_list: "/centrodefamilia/centros/", centro_detail: "/centrodefamilia/centros/4/", detalle: "/centrodefamilia/centros/actividades/9/detalle/" },
  messages: [], ...over,
});

function serve(page: unknown, api = URL_API) {
  webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
    : url === api ? Promise.resolve({ data: page, status: 200 }) : Promise.reject(new Error(url))));
}
function setup(search = "") {
  window.history.replaceState({}, "", `/centrodefamilia/centros/actividades/9/asistencia/${search}`);
  return render(<App />);
}
const metric = (id: string) => document.getElementById(id)?.textContent;
const radio = (id: number, value: string) => document.querySelector<HTMLInputElement>(`input[name=presente_${id}][value="${value}"]`)!;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CDF attendance route", () => {
  it("owns only the native sheet path", () => {
    expect(findRoute("/centrodefamilia/centros/actividades/9/asistencia/")?.route.name).toBe("cdf-asistencia");
    expect(findRoute("/centrodefamilia/centros/actividades/9/asistencia/")?.params).toEqual({ id: "9" });
    expect(findRoute("/centrodefamilia/centros/actividades/9/detalle/")?.route.name).not.toBe("cdf-asistencia");
    expect(findRoute("/centrodefamilia/centros/actividades/0/asistencia/")?.route.name).not.toBe("cdf-asistencia");
  });

  it("renders the sheet with the native texts, marks and server metrics", async () => {
    serve(pagina());
    setup();
    await screen.findByRole("heading", { name: "Asistencia — Futbol" });
    await waitFor(() => expect(document.title).toBe("SISOC - Toma de Asistencia"));
    expect(document.querySelector(".cdf-hero-sub")?.textContent).toBe("CDF Cuatro Deportes 09:00 - 10:30");
    expect((document.getElementById("fechaAsistencia") as HTMLInputElement).value).toBe("2026-10-01");
    expect(document.querySelector("form.cdf-actions")?.getAttribute("method")).toBe("get");
    expect(document.querySelector(".cdf-alert--info")?.textContent).toBe("Ya existe asistencia registrada para el 01/10/2026. Al guardar se actualizarán los registros.");
    expect(document.querySelector(".cdf-card-head span")?.textContent).toBe("Planilla del 01/10/2026");
    expect([metric("asisMetricPresentes"), metric("asisMetricAusentes"), metric("asisMetricSinMarcar")]).toEqual(["1", "1", "1"]);
    expect(radio(1, "1").checked).toBe(true);
    expect(radio(2, "0").checked).toBe(true);
    expect(radio(3, "1").checked || radio(3, "0").checked).toBe(false);
    expect(screen.getByText("Ape1, Nom1")).toBeTruthy();
    expect(document.querySelector(".breadcrumb")?.textContent).toBe("Centro de FamiliaActividadesDetalleAsistencia");
    expect(webGet).toHaveBeenCalledWith(URL_API, expect.anything());
  });

  it("updates the metrics with each individual mark and the two bulk checkboxes like the native script", async () => {
    serve(pagina());
    setup();
    await screen.findByRole("button", { name: /Guardar Asistencia/ });
    fireEvent.click(radio(3, "1"));
    expect([metric("asisMetricPresentes"), metric("asisMetricAusentes"), metric("asisMetricSinMarcar")]).toEqual(["2", "1", "0"]);
    const todosPresentes = document.getElementById("asisMarcarPresentes") as HTMLInputElement;
    const todosAusentes = document.getElementById("asisMarcarAusentes") as HTMLInputElement;
    fireEvent.click(todosAusentes);
    expect([metric("asisMetricPresentes"), metric("asisMetricAusentes")]).toEqual(["0", "3"]);
    fireEvent.click(todosPresentes);
    expect(todosAusentes.checked).toBe(false);
    expect([metric("asisMetricPresentes"), metric("asisMetricAusentes")]).toEqual(["3", "0"]);
    // Unchecking the bulk box does not clear the radios.
    fireEvent.click(todosPresentes);
    expect(todosPresentes.checked).toBe(false);
    expect(metric("asisMetricPresentes")).toBe("3");
    // A manual change moves the metrics but leaves the bulk boxes alone.
    fireEvent.click(radio(1, "0"));
    expect([metric("asisMetricPresentes"), metric("asisMetricAusentes")]).toEqual(["2", "1"]);
  });

  it("posts the checked radios once and follows the native redirect", async () => {
    serve(pagina());
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { url: "/centrodefamilia/centros/actividades/9/asistencia/?fecha=2026-10-01", message: "Asistencia del 01/10/2026 registrada para 3 participante(s).", level: "success" } });
    setup();
    const guardar = await screen.findByRole("button", { name: /Guardar Asistencia/ });
    fireEvent.click(guardar);
    fireEvent.click(guardar);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodefamilia/centros/actividades/9/asistencia/?fecha=2026-10-01"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(URL_API);
    const data = body as FormData;
    expect(data.get("csrfmiddlewaretoken")).toBe("synthetic-csrf-token");
    expect(data.get("fecha")).toBe("2026-10-01");
    expect(data.get("presente_1")).toBe("1");
    expect(data.get("presente_2")).toBe("0");
    // The unmarked one sends nothing: the server turns it into absent.
    expect(data.has("presente_3")).toBe(false);
  });

  it("shows the date warning and the empty state without enrolled participants", async () => {
    serve(pagina({ filas: [], ya_tomada: false, totales: { presentes: 0, ausentes: 0, sin_marcar: 0 }, fecha_error: "La fecha indicada no es válida." }), `${URL_API}?fecha=xx`);
    setup("?fecha=xx");
    await screen.findByText("No hay participantes inscritos");
    expect(document.querySelector(".cdf-alert--warning")?.textContent).toBe("La fecha indicada no es válida. Se muestra la planilla de hoy.");
    expect(document.querySelector(".cdf-alert--info")).toBeNull();
    expect(screen.queryByRole("button", { name: /Guardar Asistencia/ })).toBeNull();
  });

  it("never repeats an uncertain save", async () => {
    serve(pagina());
    webPost.mockRejectedValue(Object.assign(new Error("timeout"), { response: { status: 504 } }));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: /Guardar Asistencia/ }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe(
      "No se pudo confirmar el resultado. Verificá el estado antes de reintentar."));
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("keeps the 403 of the attendance rule and the 404 of a missing activity", async () => {
    webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
      : Promise.resolve({ data: { detail: "x" }, status: 404 })));
    setup();
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("No se encontró la página."));
    cleanup();
    webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
      : Promise.resolve({ data: { detail: "x" }, status: 403 })));
    setup();
    await waitFor(() => expect(document.body.textContent).toContain("403"));
    expect(webPost).not.toHaveBeenCalled();
  });
});
