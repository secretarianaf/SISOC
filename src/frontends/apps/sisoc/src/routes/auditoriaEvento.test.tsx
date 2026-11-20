import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { eventoValid } from "./auditoriaEvento";
import { historialValid } from "./ciudadanoHistorial";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const evento = (over = {}) => ({
  id: 9, inicio_url: "/", volver_url: "/auditoria/?page=2", fecha_texto: "2026-11-13 09:11:05", actor_texto: "Proceso", actor_fallback: true,
  actor_secundario: "cron", modelo_texto: "ciudadanos.ciudadano", instancia_texto: "#7", evento_texto: "Actualización", evento_clase: "bg-primary",
  con_diffs: true, aviso_masivo: "", origen_texto: "Web", batch_key: "", ip_texto: "-", es_eliminacion: false,
  cambios: [
    { campo: "telefono", old: { empty: true, text: "", preview: null }, new: { empty: false, text: "<b>123</b>", preview: null } },
    { campo: "notas", old: { empty: false, text: "x".repeat(200), preview: "x".repeat(179) + "…" }, new: { empty: false, text: "ok", preview: null } },
  ],
  ...over,
});
const campo = (name: string, label: string, over = {}) => ({ name, label, hidden: false, widget: "text", value: "", attrs: {}, ...over });
const fila = (over = {}) => ({
  id: 3, fecha_texto: "2026-11-13 09:11", actor_texto: "Aldo", actor_fallback: false, evento_texto: "Creación", evento_clase: "bg-success",
  continuacion: false, masiva: false, masiva_inicio: false, masiva_cantidad: 0, masiva_origen: "", con_diffs: true, cambios: [], cambios_total: 0,
  detalle_url: "/auditoria/evento/3/?next=/auditoria/", modelo_texto: "ciudadanos.ciudadano", instancia_texto: "#7", ...over,
});
const listado = (over = {}) => ({
  title: "Auditoría de cambios", inicio_url: "/",
  fields: [campo("keyword", "Texto en cambios"), campo("model", "Modelo"), campo("object_pk", "ID de instancia")],
  field_errors: [], non_field_errors: [], has_errors: false, puede_exportar: false, filtros_activos: [], filas: [fila()],
  paginacion: { is_paginated: false, number: 1, num_pages: 1, previous: false, next: false, querystring: "" }, messages: [], ...over,
});
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => cleanup());

describe("detalle de un evento de auditoria", () => {
  it("owns /auditoria/evento/<id>/ and validates the payload", () => {
    expect(findRoute("/auditoria/evento/9/")?.route.name).toBe("auditoria-evento");
    expect(findRoute("/auditoria/")?.route.name).toBe("auditoria-listado");
    expect(eventoValid(evento())).toBe(true);
    expect(eventoValid(evento({ volver_url: "http://evil/" }))).toBe(false);
    expect(eventoValid(evento({ cambios: [{ campo: "a", old: { empty: true, text: "" }, new: { empty: true, text: "", preview: null } }] }))).toBe(false);
  });

  it("draws the fields, escapes values and keeps the long ones in a details", async () => {
    window.history.replaceState({}, "", "/auditoria/evento/9/?next=/auditoria/%3Fpage%3D2");
    serve(evento());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Detalle de auditoría" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/auditoria/evento/9/?next=/auditoria/%3Fpage%3D2", expect.anything());
    expect(screen.getByText("Evento #9")).toBeTruthy();
    expect(screen.getByText("Actualización").className).toContain("bg-primary");
    expect(screen.getByText("Proceso").className).toBe("text-muted");
    expect(screen.getByText("cron").className).toBe("text-muted d-block");
    expect(screen.getByText("<b>123</b>")).toBeTruthy();
    expect(document.querySelector("tbody em")?.textContent).toBe("No cargado");
    expect(document.querySelectorAll("details").length).toBe(1);
    expect(document.querySelector("summary")?.textContent).toBe("x".repeat(179) + "…");
    expect(document.querySelector(".card-title .badge")?.textContent).toBe("2");
    const crumb = [...document.querySelectorAll(".breadcrumb li")].map((li) => [li.textContent, li.querySelector("a")?.getAttribute("href") ?? null]);
    expect(crumb).toEqual([["Inicio", "/"], ["Auditoría", "/auditoria/?page=2"], ["Evento 9", null]]);
  });

  it("shows the bulk notice, the batch key and the empty state of a deletion", async () => {
    window.history.replaceState({}, "", "/auditoria/evento/9/");
    serve(evento({ con_diffs: false, cambios: [], es_eliminacion: true, evento_texto: "Eliminación", evento_clase: "bg-danger",
      aviso_masivo: "Evento asociado a acción masiva (lote)", batch_key: "lote-1" }));
    render(<App />);
    expect(await screen.findByText("Sin diffs registrados para este evento.")).toBeTruthy();
    expect(screen.getByText("Las eliminaciones o eventos automáticos pueden no incluir detalle de cambios.")).toBeTruthy();
    expect(screen.getByText("Evento asociado a acción masiva (lote)")).toBeTruthy();
    expect(screen.getByText("Batch key: lote-1")).toBeTruthy();
    expect(screen.getAllByText("Sin diffs").length).toBe(2);
  });
});

describe("listado global de auditoria", () => {
  it("draws the model and instance columns, no changes column, every filter visible", async () => {
    window.history.replaceState({}, "", "/auditoria/?action=0");
    serve(listado());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Auditoría de cambios" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/auditoria/listado/?action=0", expect.anything());
    expect(historialValid(listado())).toBe(true);
    expect([...document.querySelectorAll("thead th")].map((th) => th.textContent)).toEqual(["Fecha", "Usuario", "Modelo", "Instancia", "Evento", ""]);
    expect(screen.getByText("ciudadanos.ciudadano")).toBeTruthy();
    expect(screen.getByText("#7")).toBeTruthy();
    expect((document.getElementById("id_model") as HTMLInputElement).type).toBe("text");
    expect(screen.queryByRole("button", { name: "Exportar CSV" })).toBeNull();
  });

  it("uses a six column empty state", async () => {
    window.history.replaceState({}, "", "/auditoria/");
    serve(listado({ filas: [] }));
    render(<App />);
    await screen.findByText("No hay eventos para los filtros seleccionados.");
    expect(document.querySelector("tbody td")?.getAttribute("colspan")).toBe("6");
  });
});
