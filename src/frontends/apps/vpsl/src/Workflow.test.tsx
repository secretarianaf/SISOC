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
    fireEvent.change(screen.getByLabelText(/resultado/), { target: { value: "derivado" } });
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
