import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { navigation } from "./cdiFrame";
import { calcularEdad, progress } from "./cdiDestinatarioForm.behavior";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const VAC = ["bcg", "neumococo", "quintuple", "polio", "rotavirus", "meningococo", "antigripal", "hepatitis_a", "triple_viral", "varicela",
  "triple_bacteriana_celular", "triple_bacteriana_acelular", "sincicial_respiratorio", "fiebre_amarilla"];
const R = (p: string, cuit = true) => ["tipo_documentacion", "dni", "apellido", "nombre", "fecha_nacimiento", "cuit", ...(cuit ? ["sin_cuil"] : []), "sexo_registral",
  "nacionalidad", "relacion", "telefono", "pais_nacimiento", "nivel_educativo", "consentimiento"].map((n) => `${p}_${n}`);
const NAMES = [
  "estado", "tipo_registro", "fecha_registro", "trabajador_registra", "apellido", "nombre", "fecha_nacimiento", "edad_calculada", "edad_unidad", "sexo",
  "tipo_documentacion", "dni", "cuit_nino", "sin_cuil_nino", "pais_nacimiento", "nacionalidad", "sala", ...R("responsable_legal_1"), ...R("responsable_legal_2", false),
  "calle_domicilio", "altura_domicilio", "piso_domicilio", "departamento_domicilio", "tipo_barrio", "provincia_domicilio", "departamento", "decil_ipi",
  "municipio_domicilio", "localidad_domicilio", "convivientes", "pueblo_originario_cual", "necesito_interprete", "tiene_discapacidad", "posee_cud", "numero_cud",
  "recibe_apoyo_desarrollo", "cobertura_salud", "controles_sanitarios_ultimo_anio", "calendario_vacunacion_al_dia", "talla", "peso", "longitud_acostado",
  "perimetro_cefalico", "lactancia", "anses_auh", "anses_aue", "anses_acsi", "anses_acn", ...VAC.flatMap((v) => [`vacuna_${v}_dosis`, `vacuna_${v}_fecha`]), "observaciones",
];
const SELECTS: Record<string, [string, string][]> = {
  tiene_discapacidad: [["", "---------"], ["si", "Sí"], ["no", "No"]], posee_cud: [["", "---------"], ["true", "Sí"], ["false", "No"]],
  edad_unidad: [["", "---------"], ["meses", "Meses"], ["anios", "Años"]], provincia_domicilio: [["", "---------"], ["1", "Buenos Aires"]],
  departamento: [["", "---------"]], municipio_domicilio: [["", "---------"]], localidad_domicilio: [["", "---------"]],
  responsable_legal_1_relacion: [["", "---------"], ["madre", "Madre"]], responsable_legal_2_relacion: [["", "---------"], ["padre", "Padre"]],
  ...Object.fromEntries(VAC.map((v) => [`vacuna_${v}_dosis`, [["", "---------"], ["1_dosis", "1 dosis"]]])),
};
const field = (name: string, over: Record<string, unknown> = {}) => {
  const widget = name.endsWith("fecha_nacimiento") || name.endsWith("_fecha") || name === "fecha_registro" ? "date"
    : name === "observaciones" ? "textarea" : name.startsWith("sin_cuil") || name.endsWith("_sin_cuil") ? "checkbox" : SELECTS[name] ? "select" : "text";
  return {
    name, label: name, required: false, disabled: ["edad_calculada", "edad_unidad", "decil_ipi"].includes(name), widget, help_text: "", value: "", attrs: {}, renaper: false, errors: [],
    choices: SELECTS[name]?.map(([value, label]) => ({ value, label })) ?? null, ...(widget === "checkbox" ? { checked: false } : {}), ...over,
  };
};
const centro = { id: 4, nombre: "CDI Girasoles", url: "/centrodeinfancia/4/nomina/", nombre_visible: "CDI Girasoles", codigo_cdi: "—", provincia: "Mendoza", departamento: "—", municipio: "—", localidad: "—" };
const bloque = (b: string, over: Record<string, unknown> = {}) => ({
  bloque: b, url: `/centrodeinfancia/ajax/renaper/${b}/`, modo: "manual", campos: [], tipo_field: "", tipos_con_dni: ["dni_permanente"], verificado: false,
  permite_cambiar: true, opcional: false, token: "", ...over,
});
const group = (label: string, values: string[], checked: string[] = []) => ({
  label, required: false, errors: [], options: values.map((v, i) => ({ id: `id_${label}_${i}`, value: v, label: v, checked: checked.includes(v) })),
});
const page = (over: Record<string, unknown> = {}, fieldOver: Record<string, Record<string, unknown>> = {}) => ({
  is_edit: false, centro, search: { query: "1234", ciudadanos: [], no_resultados: true, renaper_precarga: false, renaper_prefill_token: null }, mostrar_formulario: true,
  selected: null, renaper_prefill_token: null, non_field_errors: [], fields: NAMES.map((n) => field(n, fieldOver[n])),
  multiples: {
    grupo_pertenencia: group("grupo_pertenencia", ["indigena", "ninguno"]), lenguajes: group("lenguajes", ["lsa"]),
    tipo_discapacidad: group("tipo_discapacidad", ["motora"]), alergias_alimentarias: group("alergias_alimentarias", ["tacc"]),
  },
  renaper: { nino: null, responsable_legal_1: bloque("responsable_legal_1"), responsable_legal_2: bloque("responsable_legal_2", { opcional: true, modo: "dni" }) },
  urls: { cancelar: centro.url, departamentos: "/ajax/deps/", municipios: "/ajax/munis/", localidades: "/ajax/locs/" }, messages: [], ...over,
});

function serve(data: unknown) {
  webGet.mockImplementation((url: string) => (url === "web/session/" ? Promise.resolve({ data: readyContext, status: 200 }) : Promise.resolve({ data, status: 200 })));
}
const setup = (path = "/centrodeinfancia/4/nomina/crear/?query=1234") => {
  window.history.replaceState({}, "", path);
  return render(<App />);
};
const input = (name: string) => document.getElementById(`id_${name}`) as HTMLInputElement;
const type = (name: string, value: string) => fireEvent.change(input(name), { target: { value } });
const badge = (id: string) => document.getElementById(`status-${id}`) as HTMLElement;

beforeEach(() => {
  vi.clearAllMocks();
  setViewport(false);
  window.localStorage.clear();
  window.sessionStorage.clear();
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("behaviour script", () => {
  it("calculates the age in months under one year and in years after", () => {
    const hoy = new Date(2026, 9, 1);
    expect(calcularEdad("2026-03-10", hoy)).toEqual({ edad: "6", unidad: "meses" });
    expect(calcularEdad("2023-05-14", hoy)).toEqual({ edad: "3", unidad: "anios" });
    expect(calcularEdad("", hoy)).toEqual({ edad: "", unidad: null });
  });
  it("counts the sections like the native progress bar", () => {
    const { estados, completadas } = progress({ nombre: "A", apellido: "B", dni: "1", responsable_legal_2_nombre: "X" }, { grupo_pertenencia: ["ninguno"] });
    expect(estados.nino).toBe("complete");
    expect(estados.responsable2).toBe("incomplete");
    expect(estados.cultura).toBe("complete");
    expect(estados.vacunacion).toBe("empty");
    expect(completadas).toBe(2);
  });
});

describe("CDI destinatario form route", () => {
  it("owns only the native create and edit paths", () => {
    expect(findRoute("/centrodeinfancia/4/nomina/crear/")?.params).toEqual({ centro: "4", id: undefined });
    expect(findRoute("/centrodeinfancia/4/nomina/9/editar/")?.params).toEqual({ centro: "4", id: "9" });
    for (const other of ["/centrodeinfancia/4/nomina/crear", "/centrodeinfancia/4/nomina/9/ver/", "/centrodeinfancia/x/nomina/crear/"]) {
      expect(findRoute(other)?.route.name).not.toBe("cdi-destinatario-form");
    }
  });

  it("shows only the search until a ficha is chosen", async () => {
    serve(page({ mostrar_formulario: false, search: { query: "", ciudadanos: [{ id: 7, apellido: "Ramirez", nombre: "Sofia", documento: "44555666" }], no_resultados: false, renaper_precarga: false, renaper_prefill_token: null } }));
    setup("/centrodeinfancia/4/nomina/crear/");
    await screen.findByText("Buscar niño/a por DNI");
    expect(document.getElementById("destinatarioForm")).toBeNull();
    expect(screen.getByRole("link", { name: "Completar ficha" }).getAttribute("href")).toBe("?query=&ciudadano_id=7");
  });

  it("draws the ten sections with the progress bar, the age and the conditional rows", async () => {
    serve(page({}, { fecha_nacimiento: { value: "2023-05-14" }, nombre: { value: "Sofia" }, apellido: { value: "Ramirez" }, dni: { value: "44555666" } }));
    setup();
    await screen.findByText("Destinatario CDI");
    expect(document.querySelectorAll(".section-card").length).toBe(12);
    expect(badge("nino").textContent).toContain("Completada");
    expect(badge("registro").textContent).toContain("Sin completar");
    expect(input("edad_calculada").value).not.toBe("");
    // Nino, the optional responsable 2 (empty counts as complete) and the optional culture section.
    expect(document.getElementById("completedSections")?.textContent).toBe("3");
    expect(document.getElementById("bloque-discapacidad")?.classList.contains("d-none")).toBe(true);
    type("tiene_discapacidad", "si");
    expect(document.getElementById("bloque-discapacidad")?.classList.contains("d-none")).toBe(false);
    expect(document.getElementById("row-numero-cud")?.classList.contains("d-none")).toBe(true);
    type("posee_cud", "true");
    expect(document.getElementById("row-numero-cud")?.classList.contains("d-none")).toBe(false);
    expect(document.getElementById("row-pueblo-originario")?.classList.contains("d-none")).toBe(true);
    fireEvent.click(document.getElementById("id_grupo_pertenencia_0") as HTMLElement);
    expect(document.getElementById("row-pueblo-originario")?.classList.contains("d-none")).toBe(false);
    // "Tiene discapacidad" answered completes that section too.
    expect(document.getElementById("completedSections")?.textContent).toBe("4");
    expect(badge("cultura").textContent).toContain("Completada");
  });

  it("collapses a section with Enter and keeps aria-expanded in sync", async () => {
    serve(page());
    setup();
    await screen.findByText("Destinatario CDI");
    const header = document.querySelector("[data-toggle-section='registro']") as HTMLElement;
    expect(header.getAttribute("aria-expanded")).toBe("true");
    fireEvent.keyDown(header, { key: "Enter" });
    expect(header.getAttribute("aria-expanded")).toBe("false");
    expect(document.getElementById("section-registro")?.classList.contains("show")).toBe(false);
  });

  it("clears the CUIT with 'No posee CUIL' and unchecks it when a CUIT is typed", async () => {
    serve(page({}, { cuit_nino: { value: "20-44535030-4", required: true } }));
    setup();
    await screen.findByText("Destinatario CDI");
    fireEvent.click(input("sin_cuil_nino"));
    expect(input("cuit_nino").value).toBe("");
    expect(input("cuit_nino").readOnly).toBe(true);
    expect(input("cuit_nino").required).toBe(false);
    fireEvent.click(input("sin_cuil_nino"));
    type("cuit_nino", "20445350304");
    expect(input("sin_cuil_nino").checked).toBe(false);
    expect(input("cuit_nino").required).toBe(true);
  });

  it("starts the optional responsable 2 collapsed behind its add button", async () => {
    serve(page());
    setup();
    await screen.findByText("Destinatario CDI");
    const bloque2 = document.querySelector("[data-renaper-bloque='responsable_legal_2']") as HTMLElement;
    expect(bloque2.dataset.renaperModo).toBe("agregar");
    expect((input("responsable_legal_2_apellido").closest("[class*='col-']") as HTMLElement).hidden).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Agregar responsable 2" }));
    expect(bloque2.dataset.renaperModo).toBe("dni");
  });

  it("reloads the geography lists of a province already chosen and the decil of the department", async () => {
    vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve({
      ok: true,
      json: () => Promise.resolve(url.startsWith("/ajax/deps/") ? [{ id: 5, nombre: "Moreno", decil_ipi: 3 }] : url.startsWith("/ajax/munis/") ? [{ id: 8, nombre: "Moreno" }] : [{ id: 9, nombre: "Paso del Rey" }]),
    })));
    serve(page({}, { provincia_domicilio: { value: "1" }, departamento: { value: "5" }, municipio_domicilio: { value: "8" }, localidad_domicilio: { value: "9" } }));
    setup();
    await screen.findByText("Destinatario CDI");
    await waitFor(() => expect(input("decil_ipi").value).toBe("3"));
    expect(Array.from(input("municipio_domicilio").querySelectorAll("option")).map((o) => o.textContent)).toEqual(["Seleccionar municipio...", "Moreno"]);
    expect(input("localidad_domicilio").value).toBe("9");
  });

  it("posts once only what the template draws and goes to the nomina", async () => {
    const assign = vi.spyOn(navigation, "assign").mockImplementation(() => undefined);
    serve(page({ selected: { id: 7, apellido: "Ramirez", nombre: "Sofia", documento: "44555666" }, renaper_prefill_token: "tok" }, { apellido: { value: "Ramirez" } }));
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/centrodeinfancia/4/nomina/" } });
    setup("/centrodeinfancia/4/nomina/crear/?query=1234&ciudadano_id=7");
    await screen.findByText("Destinatario CDI");
    fireEvent.click(document.getElementById("id_grupo_pertenencia_1") as HTMLElement);
    const form = document.getElementById("destinatarioForm") as HTMLFormElement;
    fireEvent.submit(form);
    fireEvent.submit(form);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/centrodeinfancia/4/nomina/"));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, body] = webPost.mock.calls[0] as [string, URLSearchParams];
    expect(url).toBe("web/cdi/centros/4/nomina/crear/?query=1234&ciudadano_id=7");
    expect(body.get("csrfmiddlewaretoken")).toBe("synthetic-csrf-token");
    expect(body.get("ciudadano_id")).toBe("7");
    expect(body.get("renaper_prefill_token")).toBe("tok");
    expect(body.get("apellido")).toBe("Ramirez");
    expect(body.getAll("grupo_pertenencia")).toEqual(["ninguno"]);
    // Disabled fields and the child block (absent) are not sent.
    expect(body.has("edad_calculada")).toBe(false);
    expect(body.has("renaper_token_nino")).toBe(false);
    expect(body.has("renaper_token_responsable_legal_1")).toBe(true);
  });

  it("redraws the page with the server errors after a rejected save", async () => {
    serve(page());
    webPost.mockResolvedValue({ status: 400, data: page({ messages: [{ message: "Hay errores en la ficha de la nómina.", level: "warning" }] }, { apellido: { errors: [{ message: "Este campo es obligatorio.", code: "required" }] } }) });
    setup();
    await screen.findByText("Destinatario CDI");
    fireEvent.submit(document.getElementById("destinatarioForm") as HTMLFormElement);
    expect(await screen.findByText("Este campo es obligatorio.")).toBeTruthy();
    expect(input("apellido").classList.contains("is-invalid")).toBe(true);
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
    expect(await screen.findByText("Hay errores en la ficha de la nómina.")).toBeTruthy();
  });

  it("does not resubmit when the outcome is unknown", async () => {
    serve(page());
    webPost.mockRejectedValue(new Error("network"));
    setup();
    await screen.findByText("Destinatario CDI");
    fireEvent.submit(document.getElementById("destinatarioForm") as HTMLFormElement);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect((screen.getByRole("button", { name: /Agregar a nómina/ }) as HTMLButtonElement).disabled).toBe(true);
  });
});
