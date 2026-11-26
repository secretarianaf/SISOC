import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { parametriaListValid, voucherDetailValid, voucherListValid } from "./vatVouchers";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/vouchers/";
const page = (over: Record<string, unknown> = {}) => ({
  is_paginated: false, number: 1, num_pages: 1, count: 1, previous: null, next: null, range: [1], query_without_page: "", ...over,
});
const row = (over: Record<string, unknown> = {}) => ({
  id: 3, ciudadano: "Ana Prueba", documento: "30000001", programa: "Programa Sintético", disponible: 8, inicial: 10, vencimiento: "01/03/2027",
  estado: "activo", estado_label: "Activo", detail_url: "/vat/vouchers/3/", ...over,
});
const list = (over: Record<string, unknown> = {}) => ({
  results: [row()], page: page(), busqueda: "", urls: { list: "/vat/vouchers/", create: "/vat/vouchers/asignar/" }, messages: [], ...over,
});
const campos = [
  { name: "cantidad", id: "id_cantidad", label: "Cantidad a recargar", required: true, tag: "input", min: 1, choices: [] },
  { name: "motivo", id: "id_motivo", label: "Motivo", required: true, tag: "select", min: null,
    choices: [{ value: "automatica", label: "Recarga Automática" }, { value: "manual", label: "Recarga Manual" }] },
];
const detail = (over: Record<string, unknown> = {}) => ({
  id: 3, ciudadano: "Ana Prueba", documento: "30000001", programa: "Programa Sintético", estado: "activo", estado_label: "Activo",
  disponible: 8, inicial: 10, porcentaje: "80", asignado_por: "—", fecha_asignacion: "01/02/2026", vencimiento: "01/03/2027", dias_para_vencer: 30,
  usos: [{ fecha: "02/02/2026", oferta: "Oferta <A>", cantidad: 2 }],
  recargas: [{ fecha: "03/02/2026", motivo: "manual", por: "Gestora", cantidad: 5 }],
  logs: [{ tipo_evento: "asignacion", fecha: "01/02/2026 09:00" }],
  acciones: { recargar: true, cancelar: true, recargar_url: "/vat/vouchers/3/recargar/", cancelar_url: "/vat/vouchers/3/cancelar/", campos },
  messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path: string) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT vouchers route", () => {
  it("owns the list, the parametrías list and the detail paths only", () => {
    for (const path of ["/vat/vouchers/", "/vat/vouchers/parametrias/", "/vat/vouchers/12/"]) {
      expect(findRoute(path)?.route.name).toBe("vat-vouchers");
    }
    for (const other of ["/vat/vouchers", "/vat/vouchers/asignar/", "/vat/vouchers/asignar-masivo/", "/vat/vouchers/12/recargar/",
      "/vat/vouchers/12/cancelar/", "/vat/vouchers/parametrias/nueva/", "/vat/vouchers/parametrias/4/", "/api/web/vat/vouchers/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-vouchers");
    }
  });

  it("renders the search bar, the table and the badges of the list", async () => {
    serve(list({ results: [row(), row({ id: 4, ciudadano: "Beto Prueba", estado: "vencido", estado_label: "Vencido", detail_url: "/vat/vouchers/4/" }),
      row({ id: 5, ciudadano: "Carla Prueba", estado: "agotado", estado_label: "Agotado" }), row({ id: 6, ciudadano: "Dana", estado: "cancelado", estado_label: "Cancelado" })], busqueda: "Prueba" }));
    setup("/vat/vouchers/?busqueda=Prueba");
    await screen.findByText("Beto Prueba");
    expect(webGet).toHaveBeenCalledWith(`${API}?busqueda=Prueba`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Vouchers"));
    expect(screen.getByRole("heading", { level: 2, name: "Buscar Voucher" })).toBeTruthy();
    const search = screen.getByRole("searchbox", { name: "Buscar por nombre o DNI" }) as HTMLInputElement;
    expect([search.name, search.placeholder, search.value]).toEqual(["busqueda", "Buscar por nombre o DNI", "Prueba"]);
    expect(screen.getByRole("link", { name: "Resetear" }).getAttribute("href")).toBe("/vat/vouchers/");
    expect(screen.getByRole("link", { name: "Asignar" }).getAttribute("href")).toBe("/vat/vouchers/asignar/");
    const headers = [...document.querySelectorAll("thead th")].map((th) => th.textContent?.trim());
    expect(headers).toEqual(["Ciudadano", "DNI", "Programa", "Créditos", "Vencimiento", "Estado", "Acciones"]);
    const first = document.querySelectorAll("tbody tr")[0];
    expect(first.querySelectorAll("td")[3].textContent).toBe("8 / 10");
    expect(first.querySelector(".badge-validacion.validado")?.textContent).toBe(" Activo");
    expect(document.querySelectorAll("tbody .badge-validacion.no-validado")).toHaveLength(1);
    expect(document.querySelectorAll("tbody .badge-validacion.pendiente")).toHaveLength(1);
    expect(screen.getByText("Cancelado").closest("span")?.getAttribute("style")).toContain("background: rgb(75, 85, 99)");
    expect(within(first as HTMLElement).getByRole("link", { name: "Ver" }).getAttribute("href")).toBe("/vat/vouchers/3/");
    expect(screen.getByText("Se encontraron 1 resultados")).toBeTruthy();
  });

  it("sorts the visible rows by ciudadano and shows the empty message", async () => {
    serve(list({ results: [row({ id: 4, ciudadano: "Zeta" }), row({ id: 3, ciudadano: "Álvaro" })], page: page({ count: 2 }) }));
    setup("/vat/vouchers/");
    await screen.findByText("Zeta");
    const header = document.querySelector("th.sortable") as HTMLElement;
    const names = () => [...document.querySelectorAll("tbody tr td:first-child")].map((td) => td.textContent);
    fireEvent.click(header);
    expect(names()).toEqual(["Álvaro", "Zeta"]);
    expect(header.className).toBe("sortable sort-asc");
    fireEvent.click(header);
    expect(names()).toEqual(["Zeta", "Álvaro"]);
    cleanup();
    serve(list({ results: [], page: page({ count: 0 }) }));
    setup("/vat/vouchers/");
    expect(await screen.findByText("No se encontraron vouchers")).toBeTruthy();
    expect(screen.getByText("No hay vouchers registrados.")).toBeTruthy();
    expect(screen.queryByText(/Se encontraron/)).toBeNull();
  });

  it("keeps the other query parameters in the pagination links", async () => {
    serve(list({ page: page({ is_paginated: true, number: 1, num_pages: 2, count: 21, next: 2, range: [1, 2], query_without_page: "estado=activo&" }) }));
    setup("/vat/vouchers/?estado=activo");
    await screen.findByText("Ana Prueba");
    expect(screen.getByRole("link", { name: "Continuar" }).getAttribute("href")).toBe("?estado=activo&page=2");
    expect(screen.getAllByRole("link", { name: "Volver" }).some((a) => a.closest("li")?.className === "page-item disabled")).toBe(true);
  });

  it("renders the parametrías list", async () => {
    serve({ results: [{ id: 9, nombre: "Parametría A", programa: "Programa", cantidad_inicial: 8, vencimiento: "01/03/2027", activa: false, vouchers: 4, detail_url: "/vat/vouchers/parametrias/9/" }],
      page: page(), busqueda: "", urls: { list: "/vat/vouchers/parametrias/", create: "/vat/vouchers/parametrias/nueva/" }, messages: [] });
    setup("/vat/vouchers/parametrias/");
    await screen.findByText("Parametría A");
    expect(webGet).toHaveBeenCalledWith(`${API}parametrias/`, expect.anything());
    expect(screen.getByRole("heading", { level: 2, name: "Buscar Parametría" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Agregar" }).getAttribute("href")).toBe("/vat/vouchers/parametrias/nueva/");
    expect(screen.getByRole("link", { name: "Parametría A" }).getAttribute("title")).toBe("Ver detalles");
    expect(document.querySelector(".badge-validacion.no-validado")?.textContent).toBe(" Inactiva");
    expect(document.querySelectorAll("tbody td")[5].textContent).toBe("4");
  });

  it("renders the detail with credits, history and the native action forms", async () => {
    serve(detail());
    setup("/vat/vouchers/3/");
    expect(await screen.findByRole("heading", { level: 4, name: "Ana Prueba" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}3/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Voucher — Ana Prueba"));
    expect(screen.getByRole("heading", { level: 3, name: "Detalle de Voucher" })).toBeTruthy();
    expect(screen.getByText(/DNI 30000001 · Programa Sintético/)).toBeTruthy();
    expect(screen.getByText("Activo").className).toBe("badge fs-6 bg-success");
    expect(screen.getByText("8").className).toBe("display-5 fw-bold text-success");
    expect(document.querySelector(".progress-bar")?.className).toBe("progress-bar bg-warning");
    expect((document.querySelector(".progress-bar") as HTMLElement).style.width).toBe("80%");
    expect(screen.getByText("30 días").className).toBe("text-success");
    expect(screen.getByText("-2").className).toBe("text-end fw-semibold text-danger");
    expect(screen.getByText("+5").className).toBe("text-end fw-semibold text-success");
    expect(screen.getByText("Oferta <A>")).toBeTruthy();
    const recarga = document.querySelector('form[action="/vat/vouchers/3/recargar/"]') as HTMLFormElement;
    expect(recarga.method).toBe("post");
    expect((recarga.querySelector('[name="csrfmiddlewaretoken"]') as HTMLInputElement).value).toBe("synthetic-csrf-token");
    const cantidad = recarga.querySelector('[name="cantidad"]') as HTMLInputElement;
    expect([cantidad.type, cantidad.min, cantidad.required, cantidad.className]).toEqual(["number", "1", true, "form-control"]);
    expect([...recarga.querySelectorAll("option")].map((o) => o.value)).toEqual(["automatica", "manual"]);
    expect(screen.getByRole("button", { name: "Recargar" }).className).toBe("btn btn-sm btn-success w-100");
  });

  it("asks before cancelling and only submits when confirmed", async () => {
    serve(detail());
    setup("/vat/vouchers/3/");
    await screen.findByRole("heading", { level: 4, name: "Ana Prueba" });
    const confirm = vi.spyOn(vatNavigation, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    const form = document.querySelector('form[action="/vat/vouchers/3/cancelar/"]') as HTMLFormElement;
    expect(fireEvent.submit(form)).toBe(false);
    expect(fireEvent.submit(form)).toBe(true);
    expect(confirm).toHaveBeenCalledWith("¿Cancelar este voucher?");
  });

  it("hides the credit actions and shows the overdue and empty states", async () => {
    serve(detail({
      estado: "vencido", estado_label: "Vencido", disponible: 0, dias_para_vencer: -2, usos: [], recargas: [], logs: [],
      acciones: { recargar: false, cancelar: false, recargar_url: "/x/", cancelar_url: "/y/", campos },
    }));
    setup("/vat/vouchers/3/");
    await screen.findByRole("heading", { level: 4, name: "Ana Prueba" });
    expect(document.querySelector("main form, .content form, form[action^=\"/vat/\"]")).toBeNull();
    expect(screen.getByText("Vencido", { selector: "span.text-danger" })).toBeTruthy();
    expect(document.querySelector(".display-5")?.className).toBe("display-5 fw-bold text-danger");
    expect(document.querySelector(".progress-bar")?.className).toBe("progress-bar bg-danger");
    for (const empty of ["Sin usos registrados.", "Sin recargas registradas.", "Sin eventos registrados."]) expect(screen.getByText(empty)).toBeTruthy();
  });

  it("shows the pending native message as a toast", async () => {
    serve(detail({ messages: [{ message: "Voucher cancelado correctamente.", level: "success" }] }));
    setup("/vat/vouchers/3/");
    expect(await screen.findByText("Voucher cancelado correctamente.")).toBeTruthy();
  });

  it("shows an error on a malformed payload", async () => {
    serve({ results: "nope" });
    setup("/vat/vouchers/");
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo cargar la página.");
  });

  it("validates the payload shapes", () => {
    expect(voucherListValid(list())).toBe(true);
    expect(voucherListValid(list({ results: [row({ detail_url: "https://x.test/" })] }))).toBe(false);
    expect(parametriaListValid(list())).toBe(false);
    expect(voucherDetailValid(detail())).toBe(true);
    expect(voucherDetailValid(detail({ dias_para_vencer: "30" }))).toBe(false);
    expect(voucherDetailValid(detail({ acciones: null }))).toBe(false);
  });
});
