import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { wizardValid } from "./vatComisionWizard";
import { vatNavigation } from "./vatShared";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/vat/comisiones-asistente/cursos/7/";
const MGMT = "comision_curso_asistente_json-current_step";
const field = (name: string, over: Record<string, unknown> = {}) => ({
  name, id: `id_${name}`, label: name, tag: "input", attrs: { class: "form-control sisoc-wizard-input", type: "text" }, value: "", choices: [], errors: [], help_text: "", ...over,
});
const base = (step: string) => ({
  step, steps: ["info", "horarios", "confirmacion"], management: { name: MGMT, value: step }, estado_label: "Planificada",
  curso: { nombre: "Electricidad básica", plan: "Plan A", codigo: "00000000007" }, urls: { cancel: "/vat/centros/2/#cursos" }, messages: [],
});
const infoFields = (over: Record<string, Record<string, unknown>> = {}) => [
  field("info-ubicacion", { tag: "select", attrs: { class: "form-select sisoc-wizard-input", "data-placeholder": "Selector" }, choices: [{ value: "", label: "---------" }, { value: "5", label: "Sede" }], value: "" }),
  field("info-cupo_total", { attrs: { class: "form-control sisoc-wizard-input", type: "number" }, value: "" }),
  field("info-estado", { tag: "select", attrs: { class: "form-select sisoc-wizard-input" }, choices: [{ value: "planificada", label: "Planificada" }], value: "planificada" }),
  field("info-fecha_inicio", { attrs: { class: "form-control sisoc-wizard-input", type: "date" } }),
  field("info-fecha_fin", { attrs: { class: "form-control sisoc-wizard-input", type: "date" } }),
  field("info-acepta_lista_espera", { attrs: { class: "form-check-input", type: "checkbox" }, value: false }),
  field("info-cupo_lista_espera", { attrs: { class: "form-control sisoc-wizard-input", type: "number" } }),
  field("info-observaciones", { tag: "textarea", attrs: { class: "form-control sisoc-wizard-input", rows: "3", cols: "40" } }),
].map((f) => ({ ...f, ...(over[f.name] ?? {}) }));
const info = (over: Record<string, Record<string, unknown>> = {}, extra: Record<string, unknown> = {}) => ({ ...base("info"), fields: infoFields(over), non_field_errors: [], ...extra });
const horario = (prefix: string, values: Record<string, string> = {}) => ({
  fields: [
    field(`${prefix}-dia_semana`, { tag: "select", attrs: { class: "form-select sisoc-wizard-input" }, choices: [{ value: "", label: "---------" }, { value: "1", label: "Lunes" }], value: values.dia ?? "" }),
    field(`${prefix}-hora_desde`, { attrs: { class: "form-control sisoc-wizard-input", type: "time" }, value: values.desde ?? "" }),
    field(`${prefix}-hora_hasta`, { attrs: { class: "form-control sisoc-wizard-input", type: "time" }, value: values.hasta ?? "" }),
    field(`${prefix}-vigente`, { tag: "select", attrs: { class: "form-select sisoc-wizard-input" }, choices: [{ value: "1", label: "Activo" }, { value: "0", label: "Inactivo" }], value: "1" }),
    field(`${prefix}-DELETE`, { attrs: { type: "checkbox" }, value: false }),
  ],
});
const horarios = (forms = [horario("horarios-0")], nonForm: string[] = []) => ({
  ...base("horarios"),
  formset: {
    prefix: "horarios", management: [["TOTAL_FORMS", String(forms.length)], ["INITIAL_FORMS", "0"], ["MIN_NUM_FORMS", "1"], ["MAX_NUM_FORMS", "1000"]].map(([n, value]) => ({ name: `horarios-${n}`, value })),
    forms, empty: horario("horarios-__prefix__"), non_form_errors: nonForm,
  },
});
const confirm = () => ({
  ...base("confirmacion"),
  resumen: { ubicacion: "Sede", periodo: "01/03/2027 - 30/04/2027", cupo: "20", horarios: [{ dia: "Lunes", horas: "18:00 a 20:00", duracion: "2 hs 0 minutos", estado: "Activo" }], total: "2 hs 0 minutos" },
});

function serve(data: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status: 200 }));
}
function setup(path = "/vat/cursos/7/comision/nueva/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}
const posted = (n = 0) => Object.fromEntries(webPost.mock.calls[n][1] as URLSearchParams);

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("VAT commission wizard route", () => {
  it("owns only the native wizard URL", () => {
    expect(findRoute("/vat/cursos/7/comision/nueva/")?.route.name).toBe("vat-comision-wizard");
    for (const other of ["/vat/cursos/7/comision/nueva", "/vat/cursos/x/comision/nueva/", "/vat/cursos/comisiones/nueva/", "/vat/cursos/7/"]) {
      expect(findRoute(other)?.route.name).not.toBe("vat-comision-wizard");
    }
  });

  it("validates the three step shapes and rejects a step that does not match", () => {
    expect(wizardValid(info())).toBe(true);
    expect(wizardValid(horarios())).toBe(true);
    expect(wizardValid(confirm())).toBe(true);
    expect(wizardValid({ ...info(), management: { name: MGMT, value: "horarios" } })).toBe(false);
    expect(wizardValid({ ...horarios(), formset: undefined })).toBe(false);
    expect(wizardValid({ ...confirm(), resumen: { ...confirm().resumen, total: 3 } })).toBe(false);
  });

  it("renders step 1 like the native page, with the waiting-list capacity hidden until it is on", async () => {
    serve(info());
    setup();
    expect(await screen.findByText("Nueva Comisión de curso")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    expect(screen.getByText("Planificada", { selector: ".sisoc-wizard-status" })).toBeTruthy();
    expect((screen.getByLabelText(/^Curso/) as HTMLInputElement).value).toBe("Electricidad básica");
    expect((screen.getByLabelText(/^Curso/) as HTMLInputElement).readOnly).toBe(true);
    expect(Array.from(document.querySelectorAll(".sisoc-wizard-step-label")).map((e) => e.textContent)).toEqual(["Información básica", "Horarios", "Confirmación"]);
    expect(document.querySelector(".sisoc-wizard-step.is-current")?.textContent).toContain("Información básica");
    expect((document.getElementById("wizard-cupo-espera-wrapper") as HTMLElement).hidden).toBe(true);
    fireEvent.click(screen.getByLabelText("Acepta lista de espera"));
    expect((document.getElementById("wizard-cupo-espera-wrapper") as HTMLElement).hidden).toBe(false);
    fireEvent.change(document.getElementById("id_info-cupo_lista_espera")!, { target: { value: "4" } });
    fireEvent.click(screen.getByLabelText("Acepta lista de espera"));
    expect((document.getElementById("id_info-cupo_lista_espera") as HTMLInputElement).value).toBe("");
    expect(screen.getByText("El cupo debe estar entre 5 y 100 estudiantes")).toBeTruthy();
    expect(screen.getAllByRole("link", { name: "Cancelar" }).map((a) => a.getAttribute("href"))).toEqual(["/vat/centros/2/#cursos", "/vat/centros/2/#cursos"]);
  });

  it("posts the step fields with the management field and shows the next step", async () => {
    serve(info());
    webPost.mockResolvedValue({ status: 200, data: horarios() });
    setup();
    await screen.findByText("Nueva Comisión de curso");
    fireEvent.change(document.getElementById("id_info-ubicacion")!, { target: { value: "5" } });
    fireEvent.change(document.getElementById("id_info-cupo_total")!, { target: { value: "20" } });
    fireEvent.click(screen.getByRole("button", { name: /Avanzar al paso siguiente/ }));
    expect(await screen.findByText("Horarios de clase")).toBeTruthy();
    expect(webPost.mock.calls[0][0]).toBe(API);
    expect(posted()).toEqual({
      [MGMT]: "info", "info-ubicacion": "5", "info-cupo_total": "20", "info-estado": "planificada", "info-fecha_inicio": "", "info-fecha_fin": "",
      "info-cupo_lista_espera": "", "info-observaciones": "",
    });
    expect(document.querySelector(".sisoc-wizard-step.is-done")?.textContent).toContain("Información básica");
  });

  it("shows the first error of a rejected step and keeps the typed values", async () => {
    serve(info());
    webPost.mockRejectedValue({ response: { status: 400, data: info({ "info-cupo_total": { value: "3", errors: ["Asegúrese de que este valor sea mayor o igual a 5.", "otro"] } }) } });
    setup();
    await screen.findByText("Nueva Comisión de curso");
    fireEvent.click(screen.getByRole("button", { name: /Avanzar al paso siguiente/ }));
    expect(await screen.findByText("Asegúrese de que este valor sea mayor o igual a 5.")).toBeTruthy();
    expect(screen.queryByText("otro")).toBeNull();
    expect((document.getElementById("id_info-cupo_total") as HTMLInputElement).value).toBe("3");
  });

  it("adds, clears and removes schedule blocks and computes the weekly total like the native script", async () => {
    serve(horarios([horario("horarios-0", { dia: "1", desde: "18:00:00", hasta: "20:00:00" })]));
    webPost.mockResolvedValue({ status: 200, data: confirm() });
    setup();
    await screen.findByText("Horarios de clase");
    expect(document.querySelector("[data-total-value]")?.textContent).toBe("2");
    expect(document.querySelector("[data-total-unit]")?.textContent).toBe("Horas");
    expect(document.querySelector("[data-total-semanal]")?.classList.contains("is-ok")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: /Agregar horario/ }));
    expect(screen.getByText("Horario 2")).toBeTruthy();
    fireEvent.change(document.getElementById("id_horarios-1-hora_desde")!, { target: { value: "10:00" } });
    fireEvent.change(document.getElementById("id_horarios-1-hora_hasta")!, { target: { value: "10:45" } });
    expect(document.querySelector("[data-total-value]")?.textContent).toBe("2 h 45");
    expect(document.querySelector("[data-total-unit]")?.textContent).toBe("min");
    fireEvent.click(document.querySelectorAll('[data-action="remove-horario"]')[1]);
    expect(document.querySelectorAll(".sisoc-wizard-horario:not([data-deleted])").length).toBe(1);
    expect(document.querySelector("[data-total-value]")?.textContent).toBe("2");
    fireEvent.click(document.querySelectorAll('[data-action="remove-horario"]')[0]);
    expect(document.querySelector("[data-total-value]")?.textContent).toBe("0");
    expect(document.querySelector("[data-total-unit]")?.textContent).toBe("Min");
    expect((document.getElementById("id_horarios-0-hora_desde") as HTMLInputElement).value).toBe("");
    fireEvent.click(screen.getByRole("button", { name: /Avanzar al paso siguiente/ }));
    await screen.findByText("Confirmación final");
    expect(posted()).toMatchObject({
      [MGMT]: "horarios", "horarios-TOTAL_FORMS": "2", "horarios-INITIAL_FORMS": "0", "horarios-MIN_NUM_FORMS": "1", "horarios-MAX_NUM_FORMS": "1000",
      "horarios-0-hora_desde": "", "horarios-0-vigente": "", "horarios-1-hora_desde": "10:00", "horarios-1-hora_hasta": "10:45", "horarios-1-DELETE": "on",
    });
    expect(posted()["horarios-0-DELETE"]).toBeUndefined();
  });

  it("shows the formset errors of a rejected schedule step as the native list", async () => {
    serve(horarios());
    webPost.mockRejectedValue({ response: { status: 400, data: horarios([horario("horarios-0")], ["El total semanal debe ser de al menos 2 horas."]) } });
    setup();
    await screen.findByText("Horarios de clase");
    fireEvent.click(screen.getByRole("button", { name: /Avanzar al paso siguiente/ }));
    const item = await screen.findByText("El total semanal debe ser de al menos 2 horas.");
    expect(item.closest("ul")?.className).toBe("errorlist nonform");
  });

  it("goes back without sending the edits of the step", async () => {
    serve(horarios());
    webPost.mockResolvedValue({ status: 200, data: info() });
    setup();
    await screen.findByText("Horarios de clase");
    fireEvent.change(document.getElementById("id_horarios-0-hora_desde")!, { target: { value: "09:00" } });
    fireEvent.click(screen.getByRole("button", { name: /Volver al paso anterior/ }));
    await screen.findByText("Información básica", { selector: "span" });
    expect(posted()).toEqual({ [MGMT]: "horarios", wizard_goto_step: "info" });
  });

  it("renders the summary and confirms, navigating to the redirect", async () => {
    serve(confirm());
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/vat/centros/2/?refresh=1#cursos" } });
    const assign = vi.spyOn(vatNavigation, "assign").mockImplementation(() => undefined);
    setup();
    expect(await screen.findByText("Confirmación final")).toBeTruthy();
    for (const t of ["Electricidad básica", "Plan A", "00000000007", "Sede", "01/03/2027 - 30/04/2027", "20", "Lunes", "18:00 a 20:00", "2 hs 0 minutos", "Activo"]) {
      expect(screen.getAllByText(t).length).toBeGreaterThan(0);
    }
    fireEvent.click(screen.getByRole("button", { name: /Confirmar y crear comisión/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/vat/centros/2/?refresh=1#cursos"));
    expect(posted()).toEqual({ [MGMT]: "confirmacion" });
  });

  it("reports an unconfirmed result without resending, and shows the access screen on 403", async () => {
    serve(confirm());
    webPost.mockRejectedValue(new Error("network"));
    setup();
    await screen.findByText("Confirmación final");
    fireEvent.click(screen.getByRole("button", { name: /Confirmar y crear comisión/ }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    cleanup();
    vi.clearAllMocks();
    serve(confirm());
    webPost.mockResolvedValue({ status: 403, data: { detail: "no" } });
    setup();
    await screen.findByText("Confirmación final");
    fireEvent.click(screen.getByRole("button", { name: /Confirmar y crear comisión/ }));
    await waitFor(() => expect(screen.queryByText("Confirmación final")).toBeNull());
  });
});
