import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { navigation } from "./cdiFrame";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

type Row = { id: number; nombre: string; dni: string; sala: string; presente: boolean | null; observaciones: string };
const row = (id: number, over: Partial<Row> = {}): Row => ({
  id, nombre: `Apellido${id}, Nombre${id}`, dni: String(40000000 + id), sala: id === 1 ? "Sala verde" : "-", presente: null, observaciones: "", ...over,
});
const payload = (rows: Row[] = [row(1), row(2, { presente: true, observaciones: "Llegó tarde" }), row(3, { presente: false })]) => ({
  centro: { id: 4, nombre: "CDI Girasoles" }, fecha: "2026-07-01", fecha_label: "01/07/2026", rows,
  totals: { presentes: rows.filter((r) => r.presente === true).length, ausentes: rows.filter((r) => r.presente === false).length, sin_marcar: rows.filter((r) => r.presente === null).length },
  messages: [],
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path = "/centrodeinfancia/4/nomina/asistencia/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const metric = (id: string) => document.getElementById(id)?.textContent;
const radios = (id: number) => Array.from(document.querySelectorAll<HTMLInputElement>(`input[name="presente_${id}"]`));
const ready = () => screen.findByRole("heading", { level: 1, name: "CDI Girasoles" });
const guardar = () => screen.getByRole("button", { name: /Guardar asistencia/ });

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("CDI nomina attendance route", () => {
  it("owns only the native path with its trailing slash", () => {
    expect(findRoute("/centrodeinfancia/4/nomina/asistencia/")?.route.name).toBe("cdi-nomina-asistencia");
    expect(findRoute("/centrodeinfancia/4/nomina/asistencia")?.route.name).toBe("business");
    expect(findRoute("/centrodeinfancia/4/nomina/asistencia/calendario/")?.route.name).toBe("business");
    expect(findRoute("/centrodeinfancia/0/nomina/asistencia/")?.route.name).toBe("business");
  });

  it("loads the date from the query, draws the rows, the counters and the saved marks", async () => {
    serve(payload());
    setup("/centrodeinfancia/4/nomina/asistencia/?fecha=2026-07-01");
    await ready();
    expect(webGet).toHaveBeenCalledWith("web/cdi/centros/4/nomina/asistencia/?fecha=2026-07-01", expect.anything());
    await waitFor(() => expect(document.title).toContain("Asistencia de nómina — CDI Girasoles"));
    expect(metric("asisMetricPresentes")).toBe("1");
    expect(metric("asisMetricAusentes")).toBe("1");
    expect(metric("asisMetricSinMarcar")).toBe("1");
    expect(radios(2).map((r) => r.checked)).toEqual([true, false]);
    expect(radios(3).map((r) => r.checked)).toEqual([false, true]);
    expect((screen.getByLabelText("Observaciones para Apellido2, Nombre2") as HTMLInputElement).value).toBe("Llegó tarde");
    expect(document.getElementById("asisConteo")?.textContent).toBe("Mostrando 1-3 de 3");
    expect(screen.getByText("Sala verde")).toBeDefined();
  });

  it("shows the empty state without a form when there is no active nomina", async () => {
    serve(payload([]));
    setup();
    expect(await screen.findByText("Sin nómina activa")).toBeDefined();
    expect(screen.getByText("Agregá personas activas a la nómina para poder tomar asistencia.")).toBeDefined();
    expect(document.getElementById("asisForm")).toBeNull();
    expect(screen.queryByRole("button", { name: /Guardar asistencia/ })).toBeNull();
  });

  it("recounts on change, toggles a chosen radio off and marks everyone", async () => {
    serve(payload([row(1), row(2), row(3)]));
    setup();
    await ready();
    fireEvent.click(radios(1)[0]);
    expect(metric("asisMetricPresentes")).toBe("1");
    expect(metric("asisMetricSinMarcar")).toBe("2");
    // Choosing the checked radio again cancels the click like the native script does (the browser decides the final checked state).
    fireEvent.pointerDown(radios(1)[0]);
    expect(fireEvent.click(radios(1)[0])).toBe(false);
    fireEvent.keyDown(radios(1)[0], { key: " " });
    expect(radios(1)[0].checked).toBe(false);
    expect(metric("asisMetricSinMarcar")).toBe("3");
    const todosPresentes = document.getElementById("asisMarcarPresentes") as HTMLInputElement;
    const todosAusentes = document.getElementById("asisMarcarAusentes") as HTMLInputElement;
    fireEvent.click(todosPresentes);
    expect(metric("asisMetricPresentes")).toBe("3");
    fireEvent.click(todosAusentes);
    expect(todosPresentes.checked).toBe(false);
    expect(metric("asisMetricAusentes")).toBe("3");
    expect(metric("asisMetricPresentes")).toBe("0");
    fireEvent.click(todosAusentes);
    expect(metric("asisMetricSinMarcar")).toBe("3");
  });

  it("pages the rows by 10 like the native script", async () => {
    serve(payload(Array.from({ length: 12 }, (_, n) => row(n + 1))));
    setup();
    await ready();
    const visible = () => Array.from(document.querySelectorAll(".asis-row")).filter((r) => !r.classList.contains("d-none")).length;
    expect(visible()).toBe(10);
    expect(document.getElementById("asisPager")?.textContent).toBe("1 de 2");
    expect((screen.getByRole("button", { name: "Página anterior" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Página siguiente" }));
    expect(visible()).toBe(2);
    expect(document.getElementById("asisConteo")?.textContent).toBe("Mostrando 11-12 de 12");
    expect((screen.getByRole("button", { name: "Página siguiente" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("posts the native urlencoded fields once and follows the native redirect", async () => {
    serve(payload());
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/centrodeinfancia/4/nomina/asistencia/?fecha=2026-07-01" }, status: 200 });
    setup();
    await ready();
    fireEvent.click(radios(1)[1]);
    fireEvent.change(screen.getByLabelText("Observaciones para Apellido1, Nombre1"), { target: { value: "Con fiebre" } });
    fireEvent.click(guardar());
    await waitFor(() => expect(navigation.assign).toHaveBeenCalledWith("/centrodeinfancia/4/nomina/asistencia/?fecha=2026-07-01"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0] as [string, URLSearchParams];
    expect(url).toBe("web/cdi/centros/4/nomina/asistencia/");
    expect(Array.from(body.entries())).toEqual([
      ["csrfmiddlewaretoken", "synthetic-csrf-token"], ["fecha", "2026-07-01"],
      ["presente_1", "0"], ["obs_1", "Con fiebre"],
      ["presente_2", "1"], ["obs_2", "Llegó tarde"],
      ["presente_3", "0"], ["obs_3", ""],
    ]);
  });

  it("reports an unconfirmed save without resubmitting", async () => {
    serve(payload());
    webPost.mockRejectedValueOnce(new Error("network"));
    setup();
    await ready();
    fireEvent.click(guardar());
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("No se pudo confirmar el resultado. Recargue la página antes de reintentar.");
    expect((guardar() as HTMLButtonElement).disabled).toBe(true);
    expect(navigation.assign).not.toHaveBeenCalled();
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("reads the month from the native calendar endpoint as the native script does", async () => {
    serve(payload());
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ dias: ["2026-07-01", "2026-07-15"] }) });
    vi.stubGlobal("fetch", fetchMock);
    setup();
    await ready();
    const dialog = document.getElementById("asisCalendarDialog") as HTMLElement;
    expect(dialog.hidden).toBe(true);
    fireEvent.click(document.getElementById("asisCalendarOpen") as HTMLElement);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/centrodeinfancia/4/nomina/asistencia/calendario/?mes=2026-07", { credentials: "same-origin" }));
    expect(dialog.hidden).toBe(false);
    await within(dialog).findByLabelText("2026-07-15, con asistencia registrada");
    expect(within(dialog).getByLabelText("2026-07-02")).toBeDefined();
    fireEvent.click(within(dialog).getByLabelText("2026-07-20"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Aplicar" }));
    expect(navigation.assign).toHaveBeenCalledWith("?fecha=2026-07-20");
    fireEvent.click(within(dialog).getByRole("button", { name: "Mes siguiente" }));
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith("/centrodeinfancia/4/nomina/asistencia/calendario/?mes=2026-08", { credentials: "same-origin" }));
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(dialog.hidden).toBe(true);
    expect(document.activeElement?.id).toBe("asisCalendarOpen");
  });

  it("leaves the month without marks when the native endpoint fails", async () => {
    serve(payload());
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, json: () => Promise.resolve({ detail: "x" }) }));
    setup();
    await ready();
    fireEvent.click(document.getElementById("asisCalendarOpen") as HTMLElement);
    const dialog = document.getElementById("asisCalendarDialog") as HTMLElement;
    await within(dialog).findByLabelText("2026-07-31");
    expect(dialog.querySelector(".has-attendance")).toBeNull();
  });
});
