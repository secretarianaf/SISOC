import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { ciudadanoFamiliarNavigation, familiarValid } from "./ciudadanoFamiliar";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const VINCULOS = [["", "---------"], ["HIJO/A", "Hijo/a"], ["OTRO", "Otro"]].map(([value, label]) => ({ value, label }));
const ESTADOS = [["", "---------"], ["bueno", "Bueno"]].map(([value, label]) => ({ value, label }));
const form = (over = {}) => ({
  ciudadano: { id: 7, texto: "Uno, Ana", volver_url: "/ciudadanos/ver/7" },
  campos: {
    ciudadano_2: { label: "Familiar", placeholder: "Buscar por documento (4+ dígitos)" },
    vinculo: { label: "Vinculo", options: VINCULOS }, estado_relacion: { label: "Estado relacion", options: ESTADOS },
    conviven: { label: "Conviven" }, cuidador_principal: { label: "Cuidador principal" }, observaciones: { label: "Observaciones" },
  },
  values: { ciudadano_2: "", vinculo: "", estado_relacion: "", conviven: false, cuidador_principal: false, observaciones: "" },
  errors: {}, messages: [], ...over,
});
const URL = "web/ciudadanos/7/familiares/nuevo/";
function serve(data: unknown, search: unknown = { results: [] }) {
  webGet.mockImplementation((url: string) => {
    if (url === "ciudadanos/buscar/") return Promise.resolve({ data: search, status: 200 });
    return Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 });
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.history.replaceState({}, "", "/ciudadanos/7/familiares/nuevo");
  window.scrollTo = vi.fn();
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const status = (id: string) => document.getElementById(`status-${id}`)?.textContent?.trim();

describe("agregar familiar", () => {
  it("owns only /ciudadanos/<pk>/familiares/nuevo and validates the payload", () => {
    expect(findRoute("/ciudadanos/7/familiares/nuevo")?.route.name).toBe("ciudadano-familiar-nuevo");
    expect(findRoute("/ciudadanos/7/familiares/nuevo/")?.route.name).not.toBe("ciudadano-familiar-nuevo");
    expect(familiarValid(form())).toBe(true);
    expect(familiarValid(form({ errors: { ciudadano_2: [1] } }))).toBe(false);
    expect(familiarValid({ ...form(), ciudadano: { id: 7, texto: "x", volver_url: "http://evil/" } })).toBe(false);
  });

  it("draws the native form: header, three sections, progress and actions", async () => {
    serve(form());
    render(<App />);
    expect(await screen.findByText("Agregar familiar para Uno, Ana")).toBeTruthy();
    expect(screen.getByText("0", { selector: "#completedSections" })).toBeTruthy();
    expect(screen.getAllByRole("link", { name: /Volver/ }).map((a) => a.getAttribute("href"))).toContain("/ciudadanos/ver/7");
    expect(screen.getByLabelText("Familiar").getAttribute("placeholder")).toBe("Buscar por documento (4+ dígitos)");
    expect(screen.getByLabelText("Vinculo")).toBeTruthy();
    expect(["familiar", "relacion", "notas"].map(status)).toEqual(["Sin completar", "Sin completar", "Sin completar"]);
    expect(document.querySelectorAll(".section-header[role=button][tabindex='0']").length).toBe(3);
  });

  it("collapses a section with a click or with Enter and Space", async () => {
    serve(form());
    render(<App />);
    await screen.findByText("Agregar familiar para Uno, Ana");
    const header = document.querySelector("[data-toggle-section=relacion]") as HTMLElement;
    const body = document.getElementById("section-relacion") as HTMLElement;
    fireEvent.click(header);
    expect(body.className).not.toContain("show");
    expect(header.className).toContain("collapsed");
    fireEvent.keyDown(header, { key: "Enter" });
    expect(body.className).toContain("show");
    fireEvent.keyDown(header, { key: " " });
    expect(body.className).not.toContain("show");
  });

  it("updates the section badges and the progress as the form is filled", async () => {
    serve(form());
    render(<App />);
    await screen.findByText("Agregar familiar para Uno, Ana");
    fireEvent.change(screen.getByLabelText("Vinculo"), { target: { value: "HIJO/A" } });
    expect(status("relacion")).toBe("Completa");
    fireEvent.change(screen.getByLabelText("Observaciones"), { target: { value: " " } });
    expect(status("notas")).toBe("Sin completar");
    fireEvent.change(screen.getByLabelText("Observaciones"), { target: { value: "Nota" } });
    expect(status("notas")).toBe("Completa");
    expect(screen.getByText("2", { selector: "#completedSections" })).toBeTruthy();
    expect((document.getElementById("progressBarFill") as HTMLElement).style.width).toBe("67%");
  });

  it("searches from 4 characters, lists the results and a click fills text and hidden id", async () => {
    serve(form(), { results: [{ id: 9, text: "Zeta, Zoe (DNI 30111223)" }] });
    render(<App />);
    const input = await screen.findByLabelText("Familiar");
    fireEvent.change(input, { target: { value: "301" } });
    expect(webGet).not.toHaveBeenCalledWith("ciudadanos/buscar/", expect.anything());
    fireEvent.change(input, { target: { value: "3011" } });
    fireEvent.click(await screen.findByText("Zeta, Zoe (DNI 30111223)"));
    expect(webGet).toHaveBeenCalledWith("ciudadanos/buscar/", { params: { q: "3011", exclude_id: 7 } });
    expect((input as HTMLInputElement).value).toBe("Zeta, Zoe (DNI 30111223)");
    expect((document.getElementById("id_ciudadano_2_id") as HTMLInputElement).value).toBe("9");
    expect(status("familiar")).toBe("Completa");
    expect(document.getElementById("ciudadano-suggestions")).toBeNull();
  });

  it("says when nothing was found and hides the list on an outside click", async () => {
    serve(form());
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Familiar"), { target: { value: "99999" } });
    expect(await screen.findByText("No se encontraron resultados")).toBeTruthy();
    fireEvent.click(document.body);
    expect(document.getElementById("ciudadano-suggestions")).toBeNull();
  });

  it("posts the native fields once and follows the redirect", async () => {
    serve(form(), { results: [{ id: 9, text: "Zeta, Zoe" }] });
    const assign = vi.spyOn(ciudadanoFamiliarNavigation, "assign").mockImplementation(() => {});
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/ciudadanos/ver/7" }, status: 200 });
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Familiar"), { target: { value: "Zeta" } });
    fireEvent.click(await screen.findByText("Zeta, Zoe"));
    fireEvent.change(screen.getByLabelText("Vinculo"), { target: { value: "HIJO/A" } });
    fireEvent.click(screen.getByLabelText("Conviven"));
    const guardar = screen.getByRole("button", { name: /Guardar familiar/ });
    fireEvent.click(guardar);
    fireEvent.click(guardar);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/ciudadanos/ver/7"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe(URL);
    expect(Object.fromEntries(body as URLSearchParams)).toEqual({ ciudadano_2_id: "9", ciudadano_2: "Zeta, Zoe", vinculo: "HIJO/A", estado_relacion: "", observaciones: "", conviven: "on" });
  });

  it("re-renders the bound form after a 400: errors, posted values, hidden id cleared, back to the top", async () => {
    serve(form());
    const bound = form({ errors: { ciudadano_2: ["Este campo es requerido."] }, values: { ...form().values, ciudadano_2: "", vinculo: "OTRO", observaciones: "x" } });
    webPost.mockRejectedValueOnce({ response: { status: 400, data: bound } });
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Vinculo"), { target: { value: "OTRO" } });
    fireEvent.click(screen.getByRole("button", { name: /Guardar familiar/ }));
    expect(await screen.findByText("Este campo es requerido.")).toBeTruthy();
    const input = screen.getByLabelText("Familiar");
    expect(input.getAttribute("aria-invalid")).toBe("true");
    expect(input.getAttribute("aria-describedby")).toBe("id_ciudadano_2_error");
    expect((screen.getByLabelText("Observaciones") as HTMLTextAreaElement).value).toBe("x");
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
    expect(screen.getByRole("button", { name: /Guardar familiar/ }).hasAttribute("disabled")).toBe(false);
  });

  it("reports a refusal or an unconfirmed outcome as a toast and lets the user retry", async () => {
    serve(form());
    webPost.mockResolvedValueOnce({ data: { detail: "Sin permiso" }, status: 403 });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /Guardar familiar/ }));
    expect(await screen.findByText("Sin permiso")).toBeTruthy();
    webPost.mockRejectedValueOnce(new Error("network"));
    fireEvent.click(screen.getByRole("button", { name: /Guardar familiar/ }));
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
  });

  it("Cancelar goes back in the history", async () => {
    serve(form());
    const back = vi.spyOn(ciudadanoFamiliarNavigation, "back").mockImplementation(() => {});
    render(<App />);
    await screen.findByText("Agregar familiar para Uno, Ana");
    fireEvent.click(screen.getAllByRole("button", { name: /Cancelar/ })[0]);
    fireEvent.click(screen.getAllByRole("link", { name: "Cancelar" })[0]);
    expect(back).toHaveBeenCalledTimes(2);
  });
});
