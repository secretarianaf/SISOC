import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { actividadesNavigation, dataValid } from "./comedorActividades";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/actividades-espacio/comedor/";
const comedor = { id: 3, nombre: "Comedor Sintético", url: "/comedores/3" };
const blankRow = { values: { dia_actividad: "", hora_inicio: "", hora_fin: "" }, errors: {} };
const data = (over: Record<string, unknown> = {}) => ({
  comedor, edit_mode: false,
  fields: {
    categoria: { label: "Categoría", required: false, value: "", errors: [], options: [{ value: "", label: "Seleccionar" }, { value: "Cocina", label: "Cocina" }, { value: "Deporte", label: "Deporte" }] },
    catalogo_actividad: { label: "Actividad", required: true, value: "", errors: [] },
    vigencia_actividad_meses: { label: "Vigencia en meses", required: false, value: "", errors: [], min: "0" },
    responsable_actividad: { label: "Responsable", required: false, value: "", errors: [], max_length: 255 },
  },
  non_field_errors: [],
  activity_options: [{ id: 11, categoria: "Cocina", actividad: "Taller de cocina" }, { id: 12, categoria: "Cocina", actividad: "Panadería" }, { id: 21, categoria: "Deporte", actividad: "Futbol" }],
  days: [{ id: 1, nombre: "Lunes" }, { id: 2, nombre: "Martes" }],
  rows: [blankRow], messages: [], urls: { comedor: "/comedores/3", volver: "/comedores/3#legajo-actividades-pnud" }, ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data: body, status: 200 }));
}
function setup(url: string) {
  window.history.replaceState({}, "", url);
  return render(<App />);
}
const el = (id: string) => document.getElementById(id) as HTMLInputElement;
const posted = () => Array.from((webPost.mock.calls[0][1] as URLSearchParams).entries());

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Comedor activities", () => {
  it("owns the two native URLs (trailing slash) and validates its payload", () => {
    for (const path of ["/comedores/3/actividades/crear/", "/comedores/3/actividades/8/editar/"]) {
      expect(findRoute(path)?.route.name, path).toBe("comedores-actividades");
    }
    expect(findRoute("/comedores/3/actividades/crear")?.route.name).not.toBe("comedores-actividades");
    expect(dataValid(data())).toBe(true);
    expect(dataValid(data({ rows: [] }))).toBe(false);
    expect(dataValid(data({ urls: { comedor: "/c", volver: "https://x.example" } }))).toBe(false);
    expect(dataValid(data({ days: [{ id: "x", nombre: "Lunes" }] }))).toBe(false);
  });

  it("renders the create page like the template: heading, breadcrumb, fields and one empty schedule row", async () => {
    serve(data());
    setup("/comedores/3/actividades/crear/");
    expect(await screen.findByText("Agregar actividad del espacio")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}3/crear/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Agregar actividad"));
    expect(Array.from(document.querySelectorAll(".breadcrumb-item")).map((li) => li.textContent)).toEqual(["Comedor", "Agregar actividad"]);
    expect(document.querySelector(".card-header")?.textContent).toBe("Comedor Sintético");
    expect(document.querySelector('label[for="id_categoria"]')?.textContent).toBe("Categoría");
    expect(document.querySelector('label[for="id_catalogo_actividad"]')?.textContent).toBe("Actividad*");
    expect(el("id_catalogo_actividad").disabled).toBe(true);
    expect(document.querySelectorAll(".schedule-row")).toHaveLength(1);
    expect((document.querySelector(".remove-schedule-row") as HTMLButtonElement).disabled).toBe(true);
    expect(document.querySelector(".card-footer a.btn-outline-secondary")?.getAttribute("href")).toBe("/comedores/3#legajo-actividades-pnud");
    expect(screen.getByRole("button", { name: "Guardar actividad" })).toBeTruthy();
  });

  it("filters the activities by category like the template script and clears the choice on change", async () => {
    serve(data());
    setup("/comedores/3/actividades/crear/");
    await screen.findByText("Agregar actividad del espacio");
    fireEvent.change(el("id_categoria"), { target: { value: "Cocina" } });
    expect(el("id_catalogo_actividad").disabled).toBe(false);
    expect(Array.from(el("id_catalogo_actividad").querySelectorAll("option")).map((o) => o.textContent)).toEqual(["Seleccionar", "Taller de cocina", "Panadería"]);
    fireEvent.change(el("id_catalogo_actividad"), { target: { value: "12" } });
    expect(el("id_catalogo_actividad").value).toBe("12");
    fireEvent.change(el("id_categoria"), { target: { value: "Deporte" } });
    expect(el("id_catalogo_actividad").value).toBe("");
    expect(Array.from(el("id_catalogo_actividad").querySelectorAll("option")).map((o) => o.textContent)).toEqual(["Seleccionar", "Futbol"]);
    fireEvent.change(el("id_categoria"), { target: { value: "" } });
    expect(el("id_catalogo_actividad").disabled).toBe(true);
  });

  it("adds and removes schedule rows, keeping at least one", async () => {
    serve(data());
    setup("/comedores/3/actividades/crear/");
    await screen.findByText("Agregar actividad del espacio");
    fireEvent.click(screen.getByRole("button", { name: /Agregar horario/ }));
    fireEvent.click(screen.getByRole("button", { name: /Agregar horario/ }));
    expect(document.querySelectorAll(".schedule-row")).toHaveLength(3);
    expect(Array.from(document.querySelectorAll<HTMLButtonElement>(".remove-schedule-row")).every((b) => !b.disabled)).toBe(true);
    fireEvent.change(document.querySelectorAll<HTMLInputElement>('input[name="schedule_hora_inicio"]')[1], { target: { value: "10:00" } });
    fireEvent.click(document.querySelectorAll<HTMLButtonElement>(".remove-schedule-row")[0]);
    expect(document.querySelectorAll(".schedule-row")).toHaveLength(2);
    expect(document.querySelectorAll<HTMLInputElement>('input[name="schedule_hora_inicio"]')[0].value).toBe("10:00");
    fireEvent.click(document.querySelectorAll<HTMLButtonElement>(".remove-schedule-row")[0]);
    expect((document.querySelector(".remove-schedule-row") as HTMLButtonElement).disabled).toBe(true);
  });

  it("posts the native repeated schedule fields once and follows the redirect", async () => {
    serve(data());
    const assign = vi.spyOn(actividadesNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/comedores/3#legajo-actividades-pnud" }, status: 200 });
    setup("/comedores/3/actividades/crear/");
    await screen.findByText("Agregar actividad del espacio");
    fireEvent.change(el("id_categoria"), { target: { value: "Cocina" } });
    fireEvent.change(el("id_catalogo_actividad"), { target: { value: "11" } });
    fireEvent.change(el("id_vigencia_actividad_meses"), { target: { value: "6" } });
    fireEvent.change(el("id_responsable_actividad"), { target: { value: "Luis" } });
    fireEvent.click(screen.getByRole("button", { name: /Agregar horario/ }));
    const dias = document.querySelectorAll<HTMLSelectElement>('select[name="schedule_dia_actividad"]');
    const inicio = document.querySelectorAll<HTMLInputElement>('input[name="schedule_hora_inicio"]');
    const fin = document.querySelectorAll<HTMLInputElement>('input[name="schedule_hora_fin"]');
    fireEvent.change(dias[0], { target: { value: "1" } }); fireEvent.change(inicio[0], { target: { value: "09:00" } }); fireEvent.change(fin[0], { target: { value: "10:00" } });
    fireEvent.change(dias[1], { target: { value: "2" } }); fireEvent.change(inicio[1], { target: { value: "14:00" } }); fireEvent.change(fin[1], { target: { value: "15:30" } });
    const guardar = screen.getByRole("button", { name: "Guardar actividad" });
    fireEvent.click(guardar);
    fireEvent.click(guardar);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/3#legajo-actividades-pnud"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}3/crear/`);
    expect(posted()).toEqual([
      ["categoria", "Cocina"], ["catalogo_actividad", "11"], ["vigencia_actividad_meses", "6"],
      ["schedule_dia_actividad", "1"], ["schedule_dia_actividad", "2"], ["schedule_hora_inicio", "09:00"], ["schedule_hora_inicio", "14:00"],
      ["schedule_hora_fin", "10:00"], ["schedule_hora_fin", "15:30"], ["responsable_actividad", "Luis"],
    ]);
  });

  it("shows field, row and form errors plus the messages after a rejected POST and never navigates", async () => {
    serve(data());
    const assign = vi.spyOn(actividadesNavigation, "assign").mockImplementation(() => undefined);
    const rejected = data({
      fields: { ...data().fields, catalogo_actividad: { label: "Actividad", required: true, value: "", errors: ["Este campo es requerido."] }, responsable_actividad: { label: "Responsable", required: false, value: "Luis", errors: [], max_length: 255 } },
      non_field_errors: ["Completa todos los dias y horarios con formato HH:MM."],
      rows: [{ values: { dia_actividad: "1", hora_inicio: "xx", hora_fin: "11:00" }, errors: { hora_inicio: "Hora inicio debe tener formato HH:MM." } }],
      messages: [{ message: "Revise el formulario.", tags: "warning" }],
    });
    webPost.mockResolvedValueOnce({ data: rejected, status: 400 });
    setup("/comedores/3/actividades/crear/");
    await screen.findByText("Agregar actividad del espacio");
    fireEvent.click(screen.getByRole("button", { name: "Guardar actividad" }));
    expect(await screen.findByText("Completa todos los dias y horarios con formato HH:MM.")).toBeTruthy();
    expect(document.querySelector(".alert-danger ul.errorlist.nonfield li")?.textContent).toBe("Completa todos los dias y horarios con formato HH:MM.");
    expect(screen.getByText("Este campo es requerido.")).toBeTruthy();
    expect(el("id_catalogo_actividad").className).toContain("is-invalid");
    expect(el("id_catalogo_actividad").getAttribute("aria-describedby")).toBe("id_catalogo_actividad_error");
    expect(document.querySelector(".schedule-row .invalid-feedback.d-block")?.textContent).toBe("Hora inicio debe tener formato HH:MM.");
    expect(el("id_responsable_actividad").value).toBe("Luis");
    expect(screen.getAllByText("Revise el formulario.")).toHaveLength(2);
    expect(assign).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: "Guardar actividad" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("renders the edit page with the stored row and the category-bound activity, and posts to the edit endpoint", async () => {
    serve(data({
      edit_mode: true,
      fields: {
        ...data().fields,
        categoria: { ...data().fields.categoria, value: "Cocina" },
        catalogo_actividad: { label: "Actividad", required: true, value: "12", errors: [] },
        vigencia_actividad_meses: { label: "Vigencia en meses", required: false, value: "3", errors: [], min: "0" },
      },
      rows: [{ values: { dia_actividad: "2", hora_inicio: "08:30", hora_fin: "10:00" }, errors: {} }],
    }));
    const assign = vi.spyOn(actividadesNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/comedores/3#legajo-actividades-pnud" }, status: 200 });
    setup("/comedores/3/actividades/8/editar/");
    expect(await screen.findByText("Editar actividad del espacio")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}3/8/editar/`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Editar actividad"));
    expect(el("id_catalogo_actividad").value).toBe("12");
    expect(el("id_vigencia_actividad_meses").value).toBe("3");
    expect(document.querySelector<HTMLSelectElement>('select[name="schedule_dia_actividad"]')!.value).toBe("2");
    fireEvent.click(screen.getByRole("button", { name: "Actualizar actividad" }));
    await waitFor(() => expect(assign).toHaveBeenCalled());
    expect(webPost.mock.calls[0][0]).toBe(`${API}3/8/editar/`);
    expect(posted().filter(([k]) => k === "schedule_hora_inicio")).toEqual([["schedule_hora_inicio", "08:30"]]);
  });

  it("drops a server-rendered activity that does not belong to the category, like the script", async () => {
    serve(data({ fields: { ...data().fields, categoria: { ...data().fields.categoria, value: "Deporte" }, catalogo_actividad: { label: "Actividad", required: true, value: "11", errors: [] } } }));
    setup("/comedores/3/actividades/crear/");
    await screen.findByText("Agregar actividad del espacio");
    expect(el("id_catalogo_actividad").value).toBe("");
  });

  it("reports a forbidden post and does not retry", async () => {
    serve(data());
    webPost.mockResolvedValueOnce({ data: { detail: "Usted no tiene permiso para realizar esta acción." }, status: 403 });
    setup("/comedores/3/actividades/crear/");
    await screen.findByText("Agregar actividad del espacio");
    fireEvent.click(screen.getByRole("button", { name: "Guardar actividad" }));
    expect(await screen.findByText("Usted no tiene permiso para realizar esta acción.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Guardar actividad" }) as HTMLButtonElement).disabled).toBe(true);
    expect(webPost).toHaveBeenCalledTimes(1);
  });
});
