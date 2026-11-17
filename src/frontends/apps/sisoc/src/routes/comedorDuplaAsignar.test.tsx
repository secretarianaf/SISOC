import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { duplaAsignarNavigation, duplaAsignarValid } from "./comedorDuplaAsignar";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/asignar-dupla/3/";
const payload = (over: Record<string, unknown> = {}) => ({
  comedor: { id: 3, nombre: "Comedor Sintético", url: "/comedores/3" },
  dupla_actual_id: 11,
  duplas: [
    { id: 11, nombre: "Dupla Alfa", coordinador: "Gómez Luis", tecnicos: "Pérez Ana", abogado: "Soto Eva" },
    { id: 12, nombre: "Dupla Beta", coordinador: "Sin asignar", tecnicos: "—", abogado: "—" },
  ],
  urls: { comedores: "/comedores/listar" }, messages: [], ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
function setup() {
  window.history.replaceState({}, "", "/comedores/dupla/asignar/3");
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Comedor dupla assignment", () => {
  it("owns the native URL (no trailing slash) and validates its payload", () => {
    expect(findRoute("/comedores/dupla/asignar/3")?.route.name).toBe("comedores-dupla-asignar");
    expect(findRoute("/comedores/dupla/asignar/3/")?.route.name).not.toBe("comedores-dupla-asignar");
    expect(findRoute("/comedores/dupla/asignar/x")?.route.name).not.toBe("comedores-dupla-asignar");
    expect(duplaAsignarValid(payload())).toBe(true);
    expect(duplaAsignarValid(payload({ urls: { comedores: "https://x.example" } }))).toBe(false);
    expect(duplaAsignarValid(payload({ duplas: [{ id: "a" }] }))).toBe(false);
  });

  it("renders the table like the native page and filters by name on keyup", async () => {
    serve(payload());
    setup();
    expect(await screen.findByRole("heading", { name: "Asignar Equipo Técnico" })).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    expect(document.title).toContain("Espacio Comunitario: Comedor Sintético");
    expect(screen.getAllByRole("button", { name: "Asignar" })).toHaveLength(2);
    expect(document.querySelectorAll("i.bi-check-circle-fill")).toHaveLength(1);
    const filter = screen.getByPlaceholderText("Filtrar por nombre de equipo técnico...") as HTMLInputElement;
    filter.value = "beta";
    fireEvent.keyUp(filter);
    await waitFor(() => expect((screen.getByText("Dupla Alfa").closest("tr") as HTMLElement).style.display).toBe("none"));
    expect((screen.getByText("Dupla Beta").closest("tr") as HTMLElement).style.display).toBe("");
  });

  it("shows the native empty row when no team is active", async () => {
    serve(payload({ duplas: [], dupla_actual_id: null }));
    setup();
    expect(await screen.findByText("No hay equipos técnicos activos disponibles.")).toBeTruthy();
  });

  it("posts the chosen dupla only after the confirmation and follows the redirect", async () => {
    serve(payload());
    const assign = vi.spyOn(duplaAsignarNavigation, "assign").mockImplementation(() => undefined);
    const confirm = vi.spyOn(duplaAsignarNavigation, "confirm").mockReturnValueOnce(false).mockReturnValue(true);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/comedores/3" }, status: 200 });
    setup();
    const buttons = await screen.findAllByRole("button", { name: "Asignar" });
    fireEvent.click(buttons[1]);
    expect(confirm).toHaveBeenCalledWith("¿Estás seguro de que deseas asignar esta dupla?");
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.click(buttons[1]);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/3"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(API);
    expect((webPost.mock.calls[0][1] as URLSearchParams).get("dupla_id")).toBe("12");
  });

  it("reports an uncertain result and does not retry or navigate", async () => {
    serve(payload());
    const assign = vi.spyOn(duplaAsignarNavigation, "assign").mockImplementation(() => undefined);
    vi.spyOn(duplaAsignarNavigation, "confirm").mockReturnValue(true);
    webPost.mockRejectedValue(new Error("network"));
    setup();
    fireEvent.click((await screen.findAllByRole("button", { name: "Asignar" }))[0]);
    expect((await screen.findByRole("alert")).textContent).toContain("No se pudo confirmar el resultado");
    expect(assign).not.toHaveBeenCalled();
    expect(webPost).toHaveBeenCalledTimes(1);
  });
});
