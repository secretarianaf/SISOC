import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { asistenciaValid } from "./comedorAsistenciaHistorial";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const HISTORIAL = "/comedores/7/admision/3/nomina/asistencia/";
const ENDPOINT = "web/comedores/comedores/7/admision/3/nomina/asistencia/";

const periodo = (iso: string, label: string, total: string, documento_url: string | null = null) => ({ label, iso, total, documento_url });
const asistente = (id: number, over: Record<string, unknown> = {}) => ({
  id, apellido: "Gómez", nombre: "Ana", documento: "30111222", genero: "Femenino", tomada_el: "26/10/2026 12:30", tomada_por: "tomadora",
  ciudadano_url: `/ciudadanos/ver/${id + 100}`, ...over,
});
const data = (over: Record<string, unknown> = {}) => ({
  comedor: { id: 7, nombre: "Comedor Norte" }, periodo: null, asistentes: [],
  periodos: [periodo("2026-10-01", "10/2026", "2", "/media/pwa/nomina_destinatarios/n.pdf"), periodo("2026-09-01", "09/2026", "1")],
  urls: { comedores: "/comedores/listar", comedor: "/comedores/7", nomina: "/comedores/7/admision/3/nomina/", historial: HISTORIAL },
  messages: [], ...over,
});

function serve(payload: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: payload, status: 200 }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => { vi.clearAllMocks(); setViewport(false); });
afterEach(() => cleanup());

describe("Comedor attendance history route (CO01)", () => {
  it("owns only the native history URL", () => {
    expect(findRoute(HISTORIAL)?.route.name).toBe("comedor-asistencia-historial");
    for (const other of ["/comedores/7/admision/3/nomina/", "/comedores/7/admision/3/nomina/asistencia", "/comedores/7/nomina/asistencia/", "/comedores/0/admision/3/nomina/asistencia/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedor-asistencia-historial");
    }
  });

  it("reads the endpoint and lists the months with the PDF link and the detail links", async () => {
    serve(data());
    setup(HISTORIAL);
    await screen.findByText("Periodo 10/2026");
    expect(webGet).toHaveBeenCalledWith(ENDPOINT, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Historial de asistencia - Comedor Norte"));
    expect(document.querySelector("h3")!.textContent).toBe("Historial de asistencia de Comedor Norte");
    expect(screen.getByRole("heading", { name: "Periodos de asistencia" })).toBeTruthy();
    const pdf = screen.getByRole("link", { name: "Descargar PDF" });
    expect(pdf.getAttribute("href")).toBe("/media/pwa/nomina_destinatarios/n.pdf");
    expect(pdf.getAttribute("target")).toBe("_blank");
    expect(pdf.hasAttribute("download")).toBe(true);
    expect(screen.getAllByRole("link", { name: /Descargar PDF/ })).toHaveLength(1);
    expect(screen.getAllByRole("link", { name: /Ver detalle/ }).map((a) => a.getAttribute("href"))).toEqual(["?periodo=2026-10-01", "?periodo=2026-09-01"]);
    expect(document.querySelectorAll(".nomina-period-count strong")[0].textContent).toBe("2");
    const crumbs = within(document.querySelector(".breadcrumb") as HTMLElement);
    expect(crumbs.getByRole("link", { name: "Nómina" }).getAttribute("href")).toBe("/comedores/7/admision/3/nomina/");
    expect(crumbs.getByText("Historial de asistencia").tagName).toBe("LI");
  });

  it("shows the empty list message", async () => {
    serve(data({ periodos: [] }));
    setup(HISTORIAL);
    await screen.findByText("No hay periodos con asistencia registrada.");
  });

  it("forwards the query and shows the attendees of the selected month", async () => {
    serve(data({ periodo: { label: "10/2026", total: "2" }, asistentes: [asistente(1), asistente(2, { apellido: "-", nombre: "-", ciudadano_url: null, genero: "-" })] }));
    setup(`${HISTORIAL}?periodo=2026-10-01`);
    await screen.findByText("2 asistentes registrados");
    expect(webGet).toHaveBeenCalledWith(`${ENDPOINT}?periodo=2026-10-01`, expect.anything());
    expect(screen.getByRole("heading", { name: "Periodo 10/2026" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver periodos" }).getAttribute("href")).toBe(HISTORIAL);
    expect(screen.getByRole("link", { name: "Gómez, Ana" }).getAttribute("href")).toBe("/ciudadanos/ver/101");
    expect([...document.querySelectorAll("thead th")].map((th) => th.textContent)).toEqual(["Apellido y nombre", "DNI", "Género", "Tomada el", "Tomada por"]);
    const cells = [...document.querySelectorAll("tbody tr")[0].querySelectorAll("td")].map((td) => td.textContent);
    expect(cells).toEqual(["Gómez, Ana", "30111222", "Femenino", "26/10/2026 12:30", "tomadora"]);
    expect(document.querySelectorAll("tbody tr")[1].querySelector("td")!.textContent).toBe("-");
    expect(screen.queryByRole("link", { name: /Descargar PDF/ })).toBeNull();
  });

  it("shows the empty attendee message of a selected month", async () => {
    serve(data({ periodo: { label: "10/2026", total: "0" } }));
    setup(`${HISTORIAL}?periodo=2026-10-01`);
    await screen.findByText("No hay asistentes registrados para este periodo.");
  });

  it("shows the access screen on 403 and an error on an invalid payload", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: { detail: "no" }, status: 403 }));
    setup(HISTORIAL);
    await waitFor(() => expect(screen.queryByText("Cargando historial de asistencia…")).toBeNull());
    expect(screen.queryByText("Periodos de asistencia")).toBeNull();
    cleanup();
    serve({ nope: true });
    setup(HISTORIAL);
    await screen.findByText("No se pudo cargar la página.");
  });

  it("validates the payload shape and refuses unsafe URLs", () => {
    expect(asistenciaValid(data())).toBe(true);
    expect(asistenciaValid(data({ periodos: [periodo("2026-10-01", "10/2026", "2", "javascript:alert(1)")] }))).toBe(false);
    expect(asistenciaValid(data({ periodos: [periodo("2026-10-01", "10/2026", "2", "https://files.example/n.pdf")] }))).toBe(true);
    expect(asistenciaValid(data({ asistentes: [asistente(1, { ciudadano_url: "//evil.test" })] }))).toBe(false);
    expect(asistenciaValid(data({ periodo: { label: 1, total: "2" } }))).toBe(false);
    expect(asistenciaValid(null)).toBe(false);
  });
});
