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

const URL_API = "web/cdf/actividades/9/";
const persona = (id: number, over: Record<string, unknown> = {}, urls: Record<string, string> = {}) => ({
  id, apellido: `Ape${id}`, nombre: `Nom${id}`, documento: `3011${id}`, sexo: "Mujer", fecha_registro: "12/11/2026",
  urls: { ciudadano: `/ciudadanos/ver/${id}/`, ...urls }, ...over,
});
const pagina = (over: Record<string, unknown> = {}) => ({
  actividad: {
    id: 9, nombre: "Futbol", categoria: "Deportes", estado_display: "En curso", horariosdesde: "09:00", horarioshasta: "10:30",
    cantidad_personas: "2", sexos: ["Mujer", "Varon"], dias: ["Lunes", "Martes"], precio_total: "3000",
  },
  centro: { id: 4, nombre: "CDF Cuatro" },
  participantes: [persona(1, {}, { delete: "/centrodefamilia/centros/4/actividades/9/participantes/1/eliminar/" })],
  lista_espera: [persona(2, {}, { promover: "/centrodefamilia/centros/4/actividades/9/lista-espera/2/promover/" })],
  promo_error: false, puede_tomar_asistencia: true,
  urls: {
    centro_list: "/centrodefamilia/centros/", centro_detail: "/centrodefamilia/centros/4/", edit: "/centrodefamilia/centros/actividades/9/editar/",
    create_participante: "/centrodefamilia/centros/4/actividades/9/participantes/crear/", asistencia: "/centrodefamilia/centros/actividades/9/asistencia/",
  },
  messages: [], ...over,
});

function serve(page: unknown, api = URL_API) {
  webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
    : url === api ? Promise.resolve({ data: page, status: 200 }) : Promise.reject(new Error(url))));
}
function setup(path = "/centrodefamilia/centros/actividades/9/detalle/") {
  const [pathname, search = ""] = path.split("?");
  window.history.replaceState({}, "", `${pathname}${search ? `?${search}` : ""}`);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CDF activity ficha route", () => {
  it("owns only the native ficha path", () => {
    expect(findRoute("/centrodefamilia/centros/actividades/9/detalle/")?.route.name).toBe("cdf-actividad");
    expect(findRoute("/centrodefamilia/centros/actividades/9/detalle/")?.params).toEqual({ id: "9" });
    expect(findRoute("/centrodefamilia/centros/actividades/9/editar/")?.route.name).not.toBe("cdf-actividad");
    expect(findRoute("/centrodefamilia/centros/actividades/0/detalle/")?.route.name).not.toBe("cdf-actividad");
  });

  it("renders the hero, actions, info grid and both tables with the native texts", async () => {
    serve(pagina());
    setup();
    await screen.findByRole("heading", { name: "Futbol" });
    await waitFor(() => expect(document.title).toBe("SISOC - Detalle Actividad"));
    expect(document.querySelector(".cdf-hero-sub")?.textContent).toBe("CDF Cuatro Deportes 09:00 - 10:30");
    expect(document.querySelector(".cdf-pill--teal")?.textContent).toBe("En curso");
    expect([...document.querySelectorAll(".cdf-actions a")].map((a) => [a.textContent, a.getAttribute("href")])).toEqual([
      ["Editar", "/centrodefamilia/centros/actividades/9/editar/"],
      ["Agregar Participante", "/centrodefamilia/centros/4/actividades/9/participantes/crear/"],
      ["Tomar Asistencia", "/centrodefamilia/centros/actividades/9/asistencia/"],
    ]);
    expect([...document.querySelectorAll(".cdf-info-item")].map((i) => i.textContent)).toEqual([
      "CentroCDF Cuatro", "CategoríaDeportes", "Cupo2", "Dirigido aMujer , Varon", "DíasLunes , Martes", "Horario09:00 - 10:30", "Costo total$3000",
    ]);
    expect(screen.getByRole("link", { name: "Ape1, Nom1" }).getAttribute("href")).toBe("/ciudadanos/ver/1/");
    expect(screen.getByRole("link", { name: "Dar de baja" }).getAttribute("href")).toBe("/centrodefamilia/centros/4/actividades/9/participantes/1/eliminar/");
    expect(document.querySelector("#lista-espera")?.textContent).toContain("Ape2, Nom2");
    expect(screen.getByRole("button", { name: "Promover" })).toBeTruthy();
    expect(document.querySelector(".breadcrumb")?.textContent).toBe("Centro de FamiliaActividadesDetalle");
  });

  it("shows the native empty states, hides attendance without permission and keeps the fallbacks", async () => {
    serve(pagina({
      participantes: [], lista_espera: [], puede_tomar_asistencia: false,
      actividad: { ...pagina().actividad, sexos: [], dias: [] },
    }));
    setup();
    await screen.findByText("No hay participantes inscritos aún");
    expect(screen.getByText("Sin lista de espera")).toBeTruthy();
    expect(screen.getByText("Todos los sexos")).toBeTruthy();
    expect(screen.getByText("No asignado")).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Tomar Asistencia" })).toBeNull();
  });

  it("posts one promotion with the CSRF token and follows the native redirect", async () => {
    serve(pagina());
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { url: "/centrodefamilia/centros/actividades/9/detalle/", message: "Participante promovido a inscrito correctamente.", level: "success", promo_error: false } });
    setup();
    const boton = await screen.findByRole("button", { name: "Promover" });
    fireEvent.click(boton);
    fireEvent.click(boton);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodefamilia/centros/actividades/9/detalle/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe("web/cdf/centros/4/actividades/9/lista-espera/2/promover/");
    expect((body as FormData).get("csrfmiddlewaretoken")).toBe("synthetic-csrf-token");
  });

  it("never repeats an uncertain promotion and says so", async () => {
    serve(pagina());
    webPost.mockRejectedValue(Object.assign(new Error("timeout"), { response: { status: 504 } }));
    setup();
    fireEvent.click(await screen.findByRole("button", { name: "Promover" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe(
      "No se pudo confirmar el resultado. Verificá el estado antes de reintentar."));
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("opens the no-room modal for promo_error and closes it with the button, the cross and Escape", async () => {
    serve(pagina({ promo_error: true }), `${URL_API}?promo_error=1`);
    setup("/centrodefamilia/centros/actividades/9/detalle/?promo_error=1");
    const modal = await screen.findByRole("dialog", { hidden: true });
    expect(modal.querySelector(".modal-title")?.textContent).toBe("Cupo Máximo Alcanzado");
    expect(modal.querySelector(".modal-body")?.textContent).toBe("No hay cupo disponible para promover a un participante de la lista de espera.");
    expect(modal.querySelector(".modal-dialog")?.className).toBe("modal-dialog modal-dialog-centered modal-sm");
    const [cruz, pie] = screen.getAllByRole("button", { name: "Cerrar" });
    expect(cruz.className).toBe("btn-close btn-close-white");
    fireEvent.click(pie);
    await waitFor(() => expect(document.querySelector("#promoErrorModal")).toBeNull());
    expect(document.querySelector(".modal-backdrop")).toBeNull();
  });

  it("closes the modal with Escape", async () => {
    serve(pagina({ promo_error: true }), `${URL_API}?promo_error=1`);
    setup("/centrodefamilia/centros/actividades/9/detalle/?promo_error=1");
    await screen.findByRole("dialog", { hidden: true });
    await waitFor(() => {
      fireEvent.keyDown(document, { key: "Escape" });
      expect(document.querySelector("#promoErrorModal")).toBeNull();
    });
  });

  it("shows the queued flash message as a toast at the end of the body", async () => {
    serve(pagina({ messages: [{ message: "Participante dado de baja correctamente.", level: "success" }] }));
    setup();
    const toast = await screen.findByText("Participante dado de baja correctamente.");
    expect(toast.closest("#toast-container")?.parentElement).toBe(document.body);
  });

  it("keeps the 403 and 404 of the API", async () => {
    webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 })
      : Promise.resolve({ data: { detail: "x" }, status: 404 })));
    setup();
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("No se encontró la página."));
  });
});
