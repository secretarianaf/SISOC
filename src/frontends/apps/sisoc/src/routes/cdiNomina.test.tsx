import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const URL_API = "web/cdi/centros/7/nomina/9/";
const ficha = (over: Record<string, unknown> = {}) => ({
  id: 9,
  label: "Ramírez, Sofía",
  centro: { id: 7, nombre: "CDI Girasoles", url: "/centrodeinfancia/7/nomina/" },
  editar_url: "/centrodeinfancia/7/nomina/9/editar/",
  sections: [
    { key: "registro", icon: "fa-clipboard-list", title: "Registro", subtitle: "Tipo de registro, fecha y referente del CDI", blocks: [
      { kind: "fields", spaced: false, items: [{ label: "Estado", value: "Activo" }, { label: "Código CDI", value: "—" }] },
    ] },
    { key: "cultura", icon: "fa-globe-americas", title: "Cultura e Identidad", subtitle: null, blocks: [
      { kind: "fields", spaced: true, items: [{ label: "Pueblo originario", value: "—" }] },
      { kind: "badges", spaced: true, label: "Grupos de pertenencia", tone: "warning", items: ["Migrante"] },
      { kind: "badges", spaced: false, label: "Lenguajes", tone: "info", items: ["Guaraní"] },
    ] },
    { key: "nutricion", icon: "fa-apple-alt", title: "Nutrición y Asistencia ANSES", subtitle: null, blocks: [
      { kind: "fields", spaced: true, items: [{ label: "Lactancia", value: "Exclusiva" }] },
      { kind: "rule" },
      { kind: "caption", text: "Asistencia ANSES" },
      { kind: "fields", spaced: false, items: [{ label: "AUH", value: "Sí" }] },
    ] },
    { key: "vacunacion", icon: "fa-syringe", title: "Vacunación NOMIVAC", subtitle: null, blocks: [
      { kind: "vaccines", rows: [{ vaccine: "BCG", doses: "1", date: "2023-03-05" }] },
    ] },
    { key: "observaciones", icon: "fa-comment-alt", title: "Observaciones", subtitle: null, blocks: [{ kind: "text", text: "Primera línea\nSegunda línea" }] },
  ],
  messages: [],
  ...over,
});

function serve(data: unknown, status = 200, sessionStatus = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(
    url === "web/session/" ? { data: sessionStatus === 200 ? readyContext : { detail: "x", state: "password_change_required", required_action_url: "/password/first-change/" }, status: sessionStatus }
      : { data, status },
  ));
}

function setup(path = "/centrodeinfancia/7/nomina/9/ver/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => cleanup());

describe("CDI beneficiary detail route", () => {
  it("owns only the native detail path", () => {
    expect(findRoute("/centrodeinfancia/7/nomina/9/ver/")?.route.name).toBe("cdi-nomina");
    expect(findRoute("/centrodeinfancia/7/nomina/9/ver")?.route.name).toBe("business");
    expect(findRoute("/centrodeinfancia/7/nomina/0/ver/")?.route.name).toBe("business");
    // The edit screen belongs to cdiDestinatarioForm.
    expect(findRoute("/centrodeinfancia/7/nomina/9/editar/")?.route.name).toBe("cdi-destinatario-form");
  });

  it("loads the session and the API and draws the heading, crumb and edit link", async () => {
    serve(ficha());
    setup();
    await screen.findByRole("heading", { level: 3, name: "Registro" });
    expect(webGet).toHaveBeenCalledWith(URL_API, expect.anything());
    expect(webGet).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(document.title).toBe("SISOC - Destinatario — Ramírez, Sofía"));
    expect(screen.getByRole("heading", { level: 3, name: "Detalle de destinatario" })).toBeDefined();
    expect(screen.getByRole("link", { name: "CDI Girasoles — Nómina" }).getAttribute("href")).toBe("/centrodeinfancia/7/nomina/");
    expect(screen.getByText("Ramírez, Sofía", { selector: "li" }).className).toBe("breadcrumb-item active");
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe("/centrodeinfancia/7/nomina/9/editar/");
  });

  it("draws fields, badges, the rule, the vaccine table and the pre-line observations", async () => {
    serve(ficha());
    setup();
    const registro = (await screen.findByRole("heading", { name: "Registro" })).closest(".section-card") as HTMLElement;
    expect(within(registro).getByText("Tipo de registro, fecha y referente del CDI").className).toBe("section-subtitle");
    expect(within(registro).getByText("Estado").nextElementSibling?.textContent).toBe("Activo");
    expect(within(registro).getByText("Código CDI").nextElementSibling?.textContent).toBe("—");
    const cultura = screen.getByRole("heading", { name: "Cultura e Identidad" }).closest(".section-card") as HTMLElement;
    expect(cultura.querySelector(".row.g-3.mb-3")).not.toBeNull();
    expect(within(cultura).getByText("Migrante").className).toBe("badge");
    expect(within(cultura).getByText("Grupos de pertenencia").parentElement?.className).toBe("mb-3");
    expect(within(cultura).getByText("Lenguajes").parentElement?.className).toBe("");
    const nutricion = screen.getByRole("heading", { name: /Nutrición/ }).closest(".section-card") as HTMLElement;
    expect(nutricion.querySelector("hr")).not.toBeNull();
    expect(within(nutricion).getByText("Asistencia ANSES").className).toBe("small mb-2");
    const vacunas = screen.getByRole("table");
    expect(within(vacunas).getAllByRole("row").map((r) => r.textContent)).toEqual(["VacunaDosis recibidasFecha de última dosis", "BCG12023-03-05"]);
    const observaciones = screen.getByText(/Primera línea/);
    expect(observaciones.textContent).toBe("Primera línea\nSegunda línea");
    expect((observaciones as HTMLElement).style.whiteSpace).toBe("pre-line");
    expect(observaciones.closest(".section-card")?.className).toBe("section-card mb-4");
  });

  it("collapses a section with click, Enter and Space and keeps aria-expanded in sync", async () => {
    serve(ficha());
    setup();
    const header = (await screen.findByRole("button", { name: /Registro/ }));
    const body = document.getElementById("section-registro") as HTMLElement;
    expect(header.getAttribute("aria-expanded")).toBe("true");
    expect(header.tabIndex).toBe(0);
    expect(body.className).toBe("section-body collapse show");
    fireEvent.click(header);
    expect(header.getAttribute("aria-expanded")).toBe("false");
    expect(header.className).toBe("section-header collapsed");
    expect(body.className).toBe("section-body collapse");
    fireEvent.keyDown(header, { key: "Enter" });
    expect(header.getAttribute("aria-expanded")).toBe("true");
    fireEvent.keyDown(header, { key: " " });
    expect(header.getAttribute("aria-expanded")).toBe("false");
    fireEvent.keyDown(header, { key: "a" });
    expect(header.getAttribute("aria-expanded")).toBe("false");
  });

  it("omits the edit link and shows the empty vaccine notice", async () => {
    serve(ficha({
      editar_url: null,
      sections: [{ key: "vacunacion", icon: "fa-syringe", title: "Vacunación NOMIVAC", subtitle: null, blocks: [{ kind: "vaccines", rows: null }] }],
    }));
    setup();
    expect(await screen.findByText("Sin datos de vacunación cargados.")).toBeDefined();
    expect(screen.queryByRole("link", { name: "Editar" })).toBeNull();
  });

  it("shows pending messages and reports forbidden, not found and invalid payloads", async () => {
    serve(ficha({ messages: [{ message: "Listo.", level: "success" }] }));
    setup();
    expect(await screen.findByText("Listo.")).toBeDefined();
    cleanup();
    serve({ detail: "No tiene permiso." }, 403);
    setup();
    expect(await screen.findByText("¡Ups! Algo salió mal.")).toBeDefined();
    cleanup();
    serve({ detail: "No encontrado." }, 404);
    setup();
    expect(await screen.findByText("No se encontró la página.")).toBeDefined();
    cleanup();
    serve(ficha({ sections: [{ key: "x", icon: "i", title: "t", subtitle: null, blocks: [{ kind: "desconocido" }] }] }));
    setup();
    expect(await screen.findByText("No se pudo cargar la página.")).toBeDefined();
  });
});
