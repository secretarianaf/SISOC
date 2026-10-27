// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ThemeProvider } from "@mui/material";
import { getTheme } from "@sisoc/ui";
import { get, postForm, type FormField } from "./api";
import { WorkflowForm } from "./Workflow";

vi.mock("./api", async (importOriginal) => ({
  ...await importOriginal<typeof import("./api")>(),
  get: vi.fn(),
  postForm: vi.fn(),
}));

afterEach(() => { cleanup(); vi.resetAllMocks(); });

function field(name: string, value: string, optional = false): FormField {
  return {
    name, label: name, value, type: "number", required: false, disabled: false,
    help: "", choices: [], min: "", max: "", step: "", graduacion_opcional: optional, file_url: "",
  };
}

function renderRegistro(optional: boolean, resultado = "entregado_dia") {
  vi.mocked(get).mockResolvedValue({
    kind: "registro-edit", back: "jornadas/1/", fields: [
      field("graduacion_izquierda", "", optional),
      field("graduacion_derecha", "", optional),
      { ...field("resultado", resultado), type: "select", choices: [
        { value: "no_requiere", label: "No requiere" },
        { value: "entregado_dia", label: "Entregado" },
        { value: "derivado", label: "Derivado" },
      ] },
    ],
  });
  render(<ThemeProvider theme={getTheme("light")}>
    <WorkflowForm kind="registro-edit" id={1} navigate={vi.fn()} />
  </ThemeProvider>);
}

describe("graduación de registros históricos", () => {
  it.each([true, false])("respeta la excepción histórica: %s", async (optional) => {
    renderRegistro(optional);
    const left = await screen.findByLabelText(/graduacion_izquierda/);
    expect((left as HTMLInputElement).required).toBe(!optional);
    expect((screen.getByLabelText(/graduacion_derecha/) as HTMLInputElement).required).toBe(!optional);
  });

  it("exige graduación al cambiar un registro que antes no requería lentes", async () => {
    renderRegistro(false, "no_requiere");
    const left = await screen.findByLabelText(/graduacion_izquierda/);
    expect((left as HTMLInputElement).required).toBe(false);
    fireEvent.mouseDown(screen.getByRole("combobox", { name: /resultado/ }));
    fireEvent.click(await screen.findByRole("option", { name: "Derivado" }));
    await waitFor(() => expect((left as HTMLInputElement).required).toBe(true));
  });
});

it("muestra las instrucciones de subsanación antes del formulario", async () => {
  vi.mocked(get).mockResolvedValue({ kind: "itinerario-subsanar", back: "itinerarios/1/", instrucciones: "Adjuntar carta firmada.", fields: [] });
  render(<ThemeProvider theme={getTheme("light")}><WorkflowForm kind="itinerario-subsanar" id={1} navigate={vi.fn()} /></ThemeProvider>);
  expect(await screen.findByText(/Adjuntar carta firmada/)).toBeTruthy();
});

describe("dirección de una jornada", () => {
  it.each([false, true])("conserva una dirección manual: %s", async (manual) => {
    vi.mocked(get).mockResolvedValue({
      kind: "jornada-edit", back: "jornadas/1/", fields: [
        { ...field("ubicacion_url", "https://www.google.com/maps?q=1,2"), type: "text" },
        { ...field("direccion", "Dirección previa"), type: "text" },
      ],
    });
    vi.mocked(postForm).mockResolvedValue({
      success: true, ubicacion_url: "https://www.google.com/maps?q=3,4",
      query: "3,4", direccion: "Dirección nueva",
    });
    render(<ThemeProvider theme={getTheme("light")}>
      <WorkflowForm kind="jornada-edit" id={1} navigate={vi.fn()} />
    </ThemeProvider>);
    const input = await screen.findByLabelText(/direccion/);
    if (manual) fireEvent.change(input, { target: { value: "Dirección manual" } });
    fireEvent.click(screen.getByRole("button", { name: "Verificar ubicación" }));
    await screen.findByText("Dirección encontrada: Dirección nueva");
    expect((input as HTMLInputElement).value).toBe(manual ? "Dirección manual" : "Dirección nueva");
  });
});

it("el pin actualiza los campos de la jornada sin modificar la dirección", async () => {
  vi.mocked(get).mockResolvedValue({ kind: "jornada-edit", back: "jornadas/1/", fields: [
    { ...field("direccion", "Dirección escrita"), type: "text" },
    { ...field("ubicacion_url", ""), type: "text", required: true },
    field("latitud", "-34"), field("longitud", "-58"),
  ] });
  const { container } = render(<ThemeProvider theme={getTheme("light")}><WorkflowForm kind="jornada-edit" id={1} navigate={vi.fn()} /></ThemeProvider>);
  await screen.findByLabelText(/latitud/);
  const root = container.querySelector<HTMLElement>("[data-pin-editor]")!;
  const lat = document.getElementById(root.dataset.latitudeField!) as HTMLInputElement;
  const lon = document.getElementById(root.dataset.longitudeField!) as HTMLInputElement;
  lat.value = "-34.123456"; lon.value = "-58.123456";
  fireEvent.input(lat);
  await waitFor(() => expect((screen.getByLabelText(/latitud/) as HTMLInputElement).value).toBe("-34.123456"));
  expect((screen.getByLabelText(/longitud/) as HTMLInputElement).value).toBe("-58.123456");
  expect((screen.getByLabelText(/direccion/) as HTMLInputElement).value).toBe("Dirección escrita");
  expect((screen.getByLabelText(/ubicacion_url/) as HTMLInputElement).required).toBe(false);
});

it("carga localidades de la provincia y descarta respuestas anteriores", async () => {
  const fields = [
    { ...field("provincia", ""), label: "Provincia", type: "select", choices: [{ value: "", label: "Elegir" }, { value: "1", label: "Provincia A" }, { value: "2", label: "Provincia B" }] },
    { ...field("localidad", ""), label: "Localidad", type: "select", choices: [] },
    { ...field("domicilio", ""), type: "text" },
  ];
  const initial = { kind: "sede-create", back: "sedes/", fields };
  let finishA!: (data: typeof initial) => void;
  let finishB!: (data: typeof initial) => void;
  vi.mocked(get).mockImplementation((path) => {
    if (path.includes("provincia=1")) return new Promise(resolve => { finishA = resolve; });
    if (path.includes("provincia=2")) return new Promise(resolve => { finishB = resolve; });
    return Promise.resolve(initial);
  });
  render(<ThemeProvider theme={getTheme("light")}><WorkflowForm kind="sede-create" id={0} navigate={vi.fn()} /></ThemeProvider>);
  const province = await screen.findByRole("combobox", { name: /Provincia/ });
  expect(screen.getByText("Elegí primero una provincia.")).toBeTruthy();
  expect(screen.getByRole("combobox", { name: /Localidad/ }).getAttribute("aria-disabled")).toBe("true");
  fireEvent.change(screen.getByLabelText(/domicilio/), { target: { value: "Domicilio conservado" } });
  fireEvent.mouseDown(province);
  fireEvent.click(await screen.findByRole("option", { name: "Provincia A" }));
  await waitFor(() => expect(finishA).toBeDefined());
  expect(screen.getByText("Cargando localidades…")).toBeTruthy();
  fireEvent.mouseDown(province);
  fireEvent.click(await screen.findByRole("option", { name: "Provincia B" }));
  await waitFor(() => expect(finishB).toBeDefined());
  finishB({ ...initial, fields: fields.map(f => f.name === "localidad" ? { ...f, choices: [{ value: "Ciudad B", label: "Ciudad B" }] } : f) });
  await screen.findByText("Elegí una localidad de la provincia.");
  finishA({ ...initial, fields: fields.map(f => f.name === "localidad" ? { ...f, choices: [{ value: "Ciudad A", label: "Ciudad A" }] } : f) });
  fireEvent.mouseDown(screen.getByRole("combobox", { name: /Localidad/ }));
  fireEvent.click(await screen.findByRole("option", { name: "Ciudad B" }));
  expect(screen.queryByRole("option", { name: "Ciudad A" })).toBeNull();
  expect((screen.getByLabelText(/domicilio/) as HTMLInputElement).value).toBe("Domicilio conservado");
});

it("agrupa la ubicación de sede con domicilio antes de provincia, localidad y mapa", async () => {
  vi.mocked(get).mockResolvedValue({ kind: "sede-create", back: "sedes/", fields: [
    { ...field("telefono", ""), type: "text" },
    { ...field("localidad", ""), type: "select" },
    field("longitud", ""),
    { ...field("provincia", ""), type: "select" },
    { ...field("nombre", ""), type: "text" },
    field("latitud", ""),
    { ...field("domicilio", ""), type: "text" },
  ] });
  render(<ThemeProvider theme={getTheme("light")}><WorkflowForm kind="sede-create" id={0} navigate={vi.fn()} /></ThemeProvider>);
  const location = await screen.findByRole("region", { name: "Ubicación" });
  const names = [...location.querySelectorAll<HTMLInputElement>("input[name]")].map(input => input.name).filter(name => name !== "csrfmiddlewaretoken");
  expect(names).toEqual(["domicilio", "provincia", "localidad", "latitud", "longitud"]);
  expect(location.querySelector("[data-pin-editor]")).toBeTruthy();
  expect(screen.getByRole("region", { name: "Contacto" }).querySelector("input[name=telefono]")).toBeTruthy();
  expect(screen.getByRole("region", { name: "Datos de la sede" }).querySelector("input[name=nombre]")).toBeTruthy();
});

it("habilita verificar ubicación de jornada con dirección y localidad sin enlace", async () => {
  vi.mocked(get).mockResolvedValue({ kind: "jornada-create", back: "itinerarios/1/", provincia_ubicacion: "Ciudad Autónoma de Buenos Aires", fields: [
    { ...field("direccion", ""), type: "text" },
    { ...field("localidad", ""), type: "select", choices: [{ value: "101", label: "Ciudad Autónoma de Buenos Aires" }] },
    { ...field("ubicacion_url", ""), type: "text" },
    field("latitud", ""), field("longitud", ""),
  ] });
  const { container } = render(<ThemeProvider theme={getTheme("light")}><WorkflowForm kind="jornada-create" id={1} navigate={vi.fn()} /></ThemeProvider>);
  const verify = await screen.findByRole("button", { name: "Verificar ubicación" });
  expect((verify as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText(/direccion/), { target: { value: "Domicilio de prueba 123" } });
  fireEvent.mouseDown(screen.getByRole("combobox", { name: /localidad/ }));
  fireEvent.click(await screen.findByRole("option", { name: "Ciudad Autónoma de Buenos Aires" }));
  expect((verify as HTMLButtonElement).disabled).toBe(false);
  const root = container.querySelector<HTMLElement>("[data-pin-editor]")!;
  const preview = vi.fn();
  root.addEventListener("pin:preview", preview);
  fireEvent.click(verify);
  expect(preview).toHaveBeenCalledOnce();
  expect(postForm).not.toHaveBeenCalled();
  const address = root.dataset.addressFields!.split(",").map(id => (document.getElementById(id) as HTMLInputElement).value);
  expect(address).toEqual(["Domicilio de prueba 123", "Ciudad Autónoma de Buenos Aires", "Ciudad Autónoma de Buenos Aires"]);
});
