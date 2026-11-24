import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { buscadorValid } from "./vatBuscadorCiudadano";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/buscador-ciudadano/";
const ciudadano = (over: Record<string, unknown> = {}) => ({
  id: 3, iniciales: "AP", apellido: "Pérez", nombre: "Ana", tipo_documento: "DNI", documento: "30111222", cuil_cuit: "—", email: "ana@example.test", telefono: "—", ...over,
});
const fila = (over: Record<string, unknown> = {}) => ({
  fecha: "02/05/2026", unidad: "Electricidad", estado_curso: "Abierto", comision_codigo: "COM-001", comision_nombre: "Uno", comision_url: "/vat/comisiones/9/", periodo_inicio: "01/03/2026",
  periodo_fin: "01/06/2026", centro: "CFP 401", cue: "060144900", provincia: "Buenos Aires", localidad: "Tolosa", direccion: "7 123", estado: "inscripta", estado_label: "Inscripta",
  estado_comision: "Planificada", resultado: "", asistencia_pct: "50%", presentes: 1, total_sesiones: 2, origen: "Backoffice", ...over,
});
const RESUMEN = Object.fromEntries(["total", "en_curso", "pre_inscriptas", "en_espera", "completadas", "abandonadas", "rechazadas", "aprobadas", "desaprobadas", "sin_calificar", "presentes", "ausentes", "porcentaje_asistencia"].map((k) => [k, "1"]));
const data = (over: Record<string, unknown> = {}) => ({
  q: "", estado: "inicial", scope_is_national: true, candidatos: [], ciudadano: null, legajo_url: null, resumen: null, inscripciones: [], urls: { buscador: "/vat/buscador-ciudadano/" }, messages: [], ...over,
});
const resultado = (over: Record<string, unknown> = {}) => data({
  q: "30111222", estado: "resultado", ciudadano: ciudadano(), legajo_url: "/ciudadanos/ver/3/", resumen: { ...RESUMEN, porcentaje_asistencia: "50" }, inscripciones: [fila()], ...over,
});

function serve(initial: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: initial, status: 200 }));
}
function setup() {
  window.history.replaceState({}, "", "/vat/buscador-ciudadano/");
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  webPost.mockReset();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT buscador por ciudadano route", () => {
  it("owns its path only", () => {
    expect(findRoute("/vat/buscador-ciudadano/")?.route.name).toBe("vat-buscador-ciudadano");
    expect(findRoute("/vat/buscador-ciudadano")?.route.name).not.toBe("vat-buscador-ciudadano");
  });

  it("renders the initial state with the search form and the breadcrumb", async () => {
    serve(data());
    setup();
    expect(await screen.findByText("Ingresá un documento para comenzar")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - VAT - Buscador por Ciudadano"));
    expect(screen.getByRole("heading", { level: 1, name: "Buscador por Ciudadano" })).toBeTruthy();
    expect(document.querySelector(".breadcrumb a")?.getAttribute("href")).toBe("/vat/centros/");
    expect(screen.queryByRole("link", { name: /Limpiar/ })).toBeNull();
    expect(screen.queryByText(/dentro de tu alcance de acceso. Este listado/)).toBeNull();
  });

  it("searches through the API, shows the trajectory and the scope note, and keeps the downloads native", async () => {
    serve(data());
    webPost.mockResolvedValue({ status: 200, data: resultado({ scope_is_national: false }) });
    setup();
    await screen.findByText("Ingresá un documento para comenzar");
    fireEvent.change(screen.getByLabelText(/DNI o CUIL/), { target: { value: " 30111222 " } });
    fireEvent.click(screen.getByRole("button", { name: /Buscar/ }));
    expect(await screen.findByText("Pérez, Ana")).toBeTruthy();
    expect(Object.fromEntries(webPost.mock.calls[0][1] as URLSearchParams)).toEqual({ q: "30111222" });
    expect(webPost.mock.calls[0][0]).toBe(API);
    expect(screen.getByText(/Estás viendo únicamente las inscripciones/)).toBeTruthy();
    expect(screen.getByRole("link", { name: /Ver legajo/ }).getAttribute("href")).toBe("/ciudadanos/ver/3/");
    expect(screen.getByRole("link", { name: /Limpiar/ }).getAttribute("href")).toBe("/vat/buscador-ciudadano/");
    expect(screen.getByText("50%", { selector: ".busc-kpi__n" })).toBeTruthy();
    const celdas = [...document.querySelectorAll(".busc-tbl tbody td")];
    expect(celdas[0].textContent).toBe("02/05/2026");
    expect(celdas[2].querySelector("a")?.getAttribute("href")).toBe("/vat/comisiones/9/");
    expect(celdas[8].textContent).toContain("1 de 2 sesiones");
    expect(celdas[7].textContent).toBe("Sin calificar");
    const exportar = [...document.querySelectorAll("form.busc-inline-form")].map((f) => Object.fromEntries(new FormData(f as HTMLFormElement)));
    expect(exportar.map((e) => [e.export, e.q, e.ciudadano_id])).toEqual([["csv", "30111222", "3"], ["xlsx", "30111222", "3"]]);
  });

  it("lets the user pick a candidate and posts the chosen id", async () => {
    serve(data());
    webPost
      .mockResolvedValueOnce({ status: 200, data: data({
        q: "20301112223", estado: "candidatos",
        candidatos: [{ ciudadano: ciudadano(), total_inscripciones: 1 }, { ciudadano: ciudadano({ id: 4, apellido: "Duplicado", nombre: "Dora", iniciales: "DD" }), total_inscripciones: 2 }],
      }) })
      .mockResolvedValueOnce({ status: 200, data: resultado({ ciudadano: ciudadano({ id: 4, apellido: "Duplicado", nombre: "Dora" }) }) });
    setup();
    await screen.findByText("Ingresá un documento para comenzar");
    fireEvent.change(screen.getByLabelText(/DNI o CUIL/), { target: { value: "20301112223" } });
    fireEvent.click(screen.getByRole("button", { name: /Buscar/ }));
    expect(await screen.findByText("Se encontraron 2 ciudadanos con ese número en distintos tipos de documento. Elegí cuál querés consultar.")).toBeTruthy();
    expect(screen.getByText(/1 inscripción INET/)).toBeTruthy();
    expect(screen.getByText(/2 inscripciónes INET/)).toBeTruthy();
    fireEvent.click(screen.getAllByRole("button", { name: /Ver trayectoria/ })[1]);
    expect(await screen.findByText("Duplicado, Dora")).toBeTruthy();
    expect(Object.fromEntries(webPost.mock.calls[1][1] as URLSearchParams)).toEqual({ q: "20301112223", ciudadano_id: "4" });
  });

  it("shows the not-found and empty-trajectory states", async () => {
    serve(data());
    webPost.mockResolvedValueOnce({ status: 200, data: data({ q: "1", estado: "no_encontrado" }) })
      .mockResolvedValueOnce({ status: 200, data: resultado({ inscripciones: [] }) });
    setup();
    await screen.findByText("Ingresá un documento para comenzar");
    fireEvent.click(screen.getByRole("button", { name: /Buscar/ }));
    expect(await screen.findByText("No se encontró un ciudadano con ese documento")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Buscar/ }));
    expect(await screen.findByText("El ciudadano no registra inscripciones en INET")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "CSV" })).toBeNull();
  });

  it("reports an unconfirmed search", async () => {
    serve(data());
    webPost.mockRejectedValue(new Error("network"));
    setup();
    await screen.findByText("Ingresá un documento para comenzar");
    fireEvent.click(screen.getByRole("button", { name: /Buscar/ }));
    expect(await screen.findByRole("alert")).toBeTruthy();
  });

  it("validates the payload shapes", () => {
    expect(buscadorValid(data())).toBe(true);
    expect(buscadorValid(resultado())).toBe(true);
    expect(buscadorValid(resultado({ resumen: { total: "1" } }))).toBe(false);
    expect(buscadorValid(data({ estado: "otro" }))).toBe(false);
  });
});
