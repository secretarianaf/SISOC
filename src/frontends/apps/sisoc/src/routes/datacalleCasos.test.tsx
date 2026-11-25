import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const ID = "0b6d8f3e-1c2a-4f5b-9d7e-123456789abc";
const caso = (over: Record<string, unknown> = {}) => ({
  id: ID, titulo: "Caso AB12", estado: "completa", estado_display: "Completa", origen_display: "App", relevador: "Ana Campo",
  fecha_inicio: "16/09/2026 10:05", variante_etiqueta: "Formulario de menores", es_formulario_menores: true, sin_entrevista_por_franja: false,
  persona_entrevistada_etiqueta: "", respuestas: [
    { titulo: "Identificación", items: [{ etiqueta: "Nombre del encuestador", valor: "Ana", historico: false }, { etiqueta: "Otros asentamientos", valor: "", historico: true }] },
    { titulo: "Otros datos", items: [{ etiqueta: "claveDesconocida", valor: "valor crudo", historico: false }] },
  ],
  breadcrumb: [{ text: "Relevamientos", url: "/datacalle/relevamientos/" }, { text: "Operativo invierno", url: `/datacalle/relevamientos/${ID}/` }, { text: "AB12", url: null }],
  messages: [], ...over,
});
const textOf = (el: Element | null) => (el?.textContent ?? "").replace(/\s+/g, " ").trim();

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => {
    if (url === "web/session/") return Promise.resolve({ data: readyContext, status: 200 });
    if (url === `web/dispositivos/datacalle/casos/${ID}/`) return Promise.resolve({ data, status });
    return Promise.reject(new Error(`unexpected ${url}`));
  });
  window.history.replaceState({}, "", `/datacalle/casos/${ID}/`);
  return render(<App />);
}

beforeEach(() => { vi.clearAllMocks(); document.title = "SISOC"; setViewport(false); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("DataCalle case ficha", () => {
  it("owns only the native case path", () => {
    expect(findRoute(`/datacalle/casos/${ID}/`)?.route.name).toBe("datacalle-casos");
    for (const path of [`/datacalle/casos/${ID}`, `/datacalle/casos/${ID.toUpperCase()}/`, "/datacalle/casos/12/"]) {
      expect(findRoute(path)?.route.name, path).not.toBe("datacalle-casos");
    }
  });

  it("renders the native ficha with the minors notice and the answers", async () => {
    serve(caso());

    await waitFor(() => expect(textOf(screen.getByRole("heading", { level: 1 }))).toBe("Caso AB12"));
    await waitFor(() => expect(document.title).toContain("Caso AB12"));
    expect(textOf(document.querySelector(".dc-header__meta"))).toBe("Completa · App · Ana Campo ·16/09/2026 10:05 · Formulario de menores");
    expect(document.querySelector(".dc-chip--finalizado")).not.toBeNull();
    expect(textOf(screen.getByText(/Formulario de menores \(14 a 17 años\)/))).toBe(
      "Formulario de menores (14 a 17 años): se relevan el código de identificación y los vínculos, el documento, el nivel educativo, dónde duerme esta noche y desde cuándo está en situación de calle. Las demás preguntas del papel general no se le preguntan: no son datos faltantes.");
    expect(screen.getByText("pregunta retirada")).not.toBeNull();
    expect(screen.getByText("valor crudo")).not.toBeNull();
    expect([...document.querySelectorAll(".dc-dato__valor--vacio")].map((e) => e.textContent)).toEqual(["—"]);
    expect([...document.querySelectorAll(".breadcrumb-item")].map((e) => e.textContent)).toEqual(["Relevamientos", "Operativo invierno", "AB12"]);
  });

  it("shows the age-band notice, the empty state and no optional meta", async () => {
    serve(caso({ estado: "rechazada", estado_display: "Rechazada", relevador: null, fecha_inicio: "", variante_etiqueta: "", es_formulario_menores: false,
      sin_entrevista_por_franja: true, persona_entrevistada_etiqueta: "6 a 13 años · Varón", respuestas: [] }));

    await waitFor(() => expect(screen.getByText("El caso no trae respuestas")).not.toBeNull());
    expect(screen.getByText("Llegó desde la app sin contenido en el instrumento.")).not.toBeNull();
    expect(textOf(screen.getByText(/Por su franja etaria/))).toBe(
      "Por su franja etaria no correspondía entrevistarla: fue observada y cuenta en el grupo (6 a 13 años · Varón).");
    expect(textOf(document.querySelector(".dc-header__meta"))).toBe("Rechazada · App");
    expect(document.querySelector(".dc-chip--planificado")).not.toBeNull();
    expect(screen.queryByText(/Formulario de menores \(14/)).toBeNull();
  });

  it("shows the not-found page for a case out of scope", async () => {
    serve({ detail: "No encontrado." }, 404);
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("No se encontró la página."));
  });
});
