import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { historialValid } from "./ciudadanoHistorial";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const campo = (name: string, label: string, over = {}) => ({ name, label, hidden: false, widget: "text", value: "", attrs: {}, ...over });
const fila = (over = {}) => ({
  id: 3, fecha_texto: "2026-11-13 09:11", actor_texto: "Proceso", actor_fallback: true, evento_texto: "Actualización", evento_clase: "bg-primary",
  continuacion: false, masiva: false, masiva_inicio: false, masiva_cantidad: 0, masiva_origen: "", con_diffs: true,
  cambios: [{ campo: "telefono", old: { empty: true, text: "" }, new: { empty: false, text: "<b>123</b>" } }], cambios_total: 1,
  detalle_url: "/auditoria/evento/3/?next=/auditoria/ciudadanos/ciudadano/7/", ...over,
});
const historial = (over = {}) => ({
  title: "Historial de la instancia", inicio_url: "/",
  fields: [
    campo("keyword", "Texto en cambios", { attrs: { placeholder: "campo, valor o fragmento", maxlength: "120" } }), campo("field_name", "Campo"), campo("batch_key", "Batch key"),
    campo("model", "Modelo", { hidden: true, value: "ciudadanos.ciudadano" }), campo("object_pk", "ID de instancia", { hidden: true, value: "7" }), campo("actor", "Usuario"),
    campo("action", "Evento", { widget: "select", choices: [{ value: "", label: "Todos los eventos" }, { value: "0", label: "Creación" }] }),
    campo("origin", "Origen", { widget: "select", choices: [{ value: "", label: "Todos los orígenes" }] }),
    campo("start_date", "Desde", { widget: "date", attrs: { max: "2026-11-13" } }), campo("end_date", "Hasta", { widget: "date", attrs: { max: "2026-11-13" } }),
  ],
  field_errors: [], non_field_errors: [], has_errors: false, puede_exportar: true, filtros_activos: [], filas: [fila()],
  paginacion: { is_paginated: false, number: 1, num_pages: 1, previous: false, next: false, querystring: "" }, messages: [], ...over,
});
const serve = (data: unknown) => webGet.mockImplementation((url: string) =>
  Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.history.replaceState({}, "", "/auditoria/ciudadanos/ciudadano/7/");
});
afterEach(() => cleanup());

describe("historial de la instancia", () => {
  it("owns /auditoria/<app>/<model>/<pk>/ only and validates the payload", () => {
    expect(findRoute("/auditoria/ciudadanos/ciudadano/7/")?.route.name).toBe("auditoria-historial-instancia");
    expect(findRoute("/auditoria/evento/3/")?.route.name).not.toBe("auditoria-historial-instancia");
    expect(historialValid(historial())).toBe(true);
    expect(historialValid(historial({ inicio_url: "http://evil/" }))).toBe(false);
    expect(historialValid(historial({ filas: [fila({ detalle_url: "http://evil/" })] }))).toBe(false);
    expect(historialValid({ ...historial(), paginacion: { is_paginated: true } })).toBe(false);
  });

  it("draws the filters, the hidden instance fields, the events and the export buttons", async () => {
    serve(historial());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Historial de la instancia" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/auditoria/ciudadanos/ciudadano/7/", expect.anything());
    expect(screen.getByLabelText("Texto en cambios:").getAttribute("placeholder")).toBe("campo, valor o fragmento");
    expect(screen.getByText("Busca texto dentro de los diffs del evento.")).toBeTruthy();
    expect((document.getElementById("id_model") as HTMLInputElement).value).toBe("ciudadanos.ciudadano");
    expect((document.getElementById("id_object_pk") as HTMLInputElement).type).toBe("hidden");
    expect(screen.getByRole("button", { name: "Exportar CSV" }).getAttribute("value")).toBe("csv");
    expect(screen.getByRole("button", { name: "Exportar JSON" }).getAttribute("name")).toBe("export");
    expect(screen.getByRole("link", { name: "Limpiar" }).getAttribute("href")).toBe(".");
    const row = screen.getByRole("link", { name: "Ver" }).closest("tr") as HTMLElement;
    expect(within(row).getByText("Actualización").className).toContain("bg-primary");
    expect(within(row).getByText("Proceso").className).toBe("text-muted");
    expect(row.textContent).toContain("telefono: No cargado → <b>123</b>");
    expect(row.querySelector("em")?.textContent).toBe("No cargado");
    expect(screen.getByRole("link", { name: "Ver" }).getAttribute("href")).toBe("/auditoria/evento/3/?next=/auditoria/ciudadanos/ciudadano/7/");
  });

  it("hides the export buttons without the export permission and shows the empty state", async () => {
    serve(historial({ puede_exportar: false, filas: [] }));
    render(<App />);
    await screen.findByRole("heading", { name: "Historial de la instancia" });
    expect(screen.queryByRole("button", { name: "Exportar CSV" })).toBeNull();
    expect(screen.getByText("No hay eventos para los filtros seleccionados.")).toBeTruthy();
    expect(screen.getByText("Ajustá los filtros o usá “Limpiar” para volver al listado completo.")).toBeTruthy();
  });

  it("lists every change of a row and still shows the counter, like the native template", async () => {
    const c = (campo: string) => ({ campo, old: { empty: true, text: "" }, new: { empty: false, text: "1" } });
    serve(historial({ filas: [fila({ cambios: [c("a"), c("b"), c("c")], cambios_total: 3 })] }));
    render(<App />);
    expect(await screen.findByText("+ 1 más")).toBeTruthy();
    expect(screen.getByText("c")).toBeTruthy();
  });

  it("shows bulk markers, the diffless badge and the extra changes counter", async () => {
    serve(historial({ filas: [
      fila({ id: 4, masiva: true, masiva_inicio: true, masiva_cantidad: 3, masiva_origen: "batch_key", cambios_total: 5 }),
      fila({ id: 5, masiva: true, continuacion: true, con_diffs: false, cambios: [], cambios_total: 0 }),
    ] }));
    render(<App />);
    expect(await screen.findByText("Acción masiva x3")).toBeTruthy();
    expect(screen.getByText("Agrupado por batch_key")).toBeTruthy();
    expect(screen.getByText("+ 3 más")).toBeTruthy();
    expect(screen.getByText("Mismo lote")).toBeTruthy();
    expect(screen.getByText("Sin diffs")).toBeTruthy();
    expect(screen.getByText("Sin diffs registrados")).toBeTruthy();
    expect(document.querySelectorAll("tr.table-light").length).toBe(1);
  });

  it("shows the active filters and the form errors", async () => {
    serve(historial({
      has_errors: true, field_errors: [{ label: "Hasta", message: "La fecha 'Hasta' no puede ser anterior a 'Desde'." }], non_field_errors: ["Rango inválido"],
      filtros_activos: [{ label: "Evento", value: "0" }],
    }));
    render(<App />);
    expect(await screen.findByText("Hasta: La fecha 'Hasta' no puede ser anterior a 'Desde'.")).toBeTruthy();
    expect(screen.getByText("Rango inválido")).toBeTruthy();
    expect(screen.getByText("Filtros activos:")).toBeTruthy();
    expect(screen.getByText("Evento: 0")).toBeTruthy();
  });

  it("paginates with the links of the native footer and keeps the query", async () => {
    window.history.replaceState({}, "", "/auditoria/ciudadanos/ciudadano/7/?page=2&action=0");
    serve(historial({ paginacion: { is_paginated: true, number: 2, num_pages: 3, previous: true, next: true, querystring: "action=0" } }));
    render(<App />);
    expect(await screen.findByText("Página 2 de 3")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith("web/auditoria/ciudadanos/ciudadano/7/?page=2&action=0", expect.anything());
    const links = [...document.querySelectorAll(".pagination a")].map((a) => [a.textContent, a.getAttribute("href")]);
    expect(links).toEqual([["«", "?page=1&action=0"], ["‹", "?page=1&action=0"], ["›", "?page=3&action=0"], ["»", "?page=3&action=0"]]);
  });
});
