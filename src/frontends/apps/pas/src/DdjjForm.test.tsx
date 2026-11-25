import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DdjjForm from "./DdjjForm";
import type { DdjjPayload } from "./ddjj";
import { navigateTo, replaceWith } from "./navigation";

vi.mock("./navigation", () => ({ navigateTo: vi.fn(), replaceWith: vi.fn() }));

const PATH = "/pas/ddjj/formulario/00005a50-0000-4000-8000-000000000001";

function payload(overrides: Partial<DdjjPayload> = {}): DdjjPayload {
  return {
    values: {
      calle: "Calle 7",
      altura: "1234",
      provincia: "1",
      municipio: "2",
      correo_electronico: "persona@example.invalid",
      telefono_celular: "11 66 435632",
      embarazada: "",
      controles_embarazo_cumplidos: "",
      hijos_menores_a_cargo: "",
      vacunacion_cumplida: "",
      regularidad_escolar_acreditada: "",
      gastos_bajo_limite_smvm: "",
      no_accedio_mercado_cambios: "",
      acepto_declaracion: false,
    },
    existing: {
      calle: true,
      altura: true,
      provincia: true,
      municipio: true,
      correo_electronico: true,
      telefono_celular: true,
    },
    labels: {
      calle: "Calle",
      provincia: "Provincia",
      municipio: "Municipio",
      correo_electronico: "Correo electrónico",
      telefono_celular: "Teléfono celular",
      embarazada: "¿Estás embarazada?",
      acepto_declaracion:
        "Confirmo que estos datos son correctos y acepto recibir notificaciones del Programa por estos medios.",
    },
    empty_label: "---------",
    provinces: [
      { id: "1", label: "Buenos Aires" },
      { id: "2", label: "Córdoba" },
    ],
    municipalities: [
      { id: "1", label: "Avellaneda" },
      { id: "2", label: "La Plata" },
    ],
    urls: {
      municipalities: `${PATH}/municipios`,
      submit: `${PATH}/enviar`,
      confirmation: "/pas/ddjj/confirmacion",
    },
    ...overrides,
  };
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

let fetchMock: ReturnType<typeof vi.fn>;
let scrollMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn(async () => json(payload()));
  vi.stubGlobal("fetch", fetchMock);
  scrollMock = vi.fn();
  vi.stubGlobal("scrollTo", scrollMock);
  document.cookie = "csrftoken=synthetic-csrf";
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.mocked(navigateTo).mockReset();
  vi.mocked(replaceWith).mockReset();
});

async function renderForm() {
  const view = render(<DdjjForm pathname={PATH} />);
  await screen.findByText("Tus datos de contacto");
  return view;
}

const step = (index: number) =>
  document.querySelector<HTMLElement>(`[data-step-index="${index}"]`)!;
const radio = (name: string, visible: "Sí" | "No") =>
  [...document.querySelectorAll<HTMLInputElement>(`input[name="${name}"]`)].find(
    (input) => input.closest("label")!.textContent!.trim() === visible,
  )!;
const click = (id: string) => fireEvent.click(document.getElementById(id)!);

async function completeSteps(answers: Record<string, "Sí" | "No">) {
  click("ddjj-next");
  for (const [name, visible] of Object.entries(answers)) fireEvent.click(radio(name, visible));
  for (const target of [2, 3, 4]) {
    if (step(target).style.display === "block") click("ddjj-next");
  }
}

describe("DdjjForm", () => {
  it("loads its data from the canonical route and renders step 1 like the native page", async () => {
    await renderForm();

    expect(fetchMock).toHaveBeenCalledWith(`${PATH}/datos`, {
      credentials: "same-origin",
      redirect: "manual",
    });
    expect(screen.getByText("Paso 1 de 5")).toBeTruthy();
    expect(screen.getByText("20%")).toBeTruthy();
    expect(step(1).style.display).toBe("block");
    expect(step(2).style.display).toBe("none");
    expect((document.getElementById("id_calle") as HTMLInputElement).value).toBe("Calle 7");
    expect((document.getElementById("id_municipio") as HTMLSelectElement).value).toBe("2");
    expect(document.getElementById("id_calle")!.getAttribute("data-pas-existente")).toBe("true");
    expect(document.getElementById("ddjj-back")!.hidden).toBe(true);
    expect(document.getElementById("ddjj-submit")!.hidden).toBe(true);
    expect(document.getElementById("ddjj-next")!.textContent).toBe("Confirmar y continuar");
    expect(scrollMock).not.toHaveBeenCalled();
    const segments = document.querySelectorAll(".pas-ddjj-progress span");
    expect(segments[0].className).toBe("is-current");
    expect(segments[1].className).toBe("");
  });

  it("maps visible answers of the inverted questions to the native submitted values", async () => {
    await renderForm();
    const table: [string, "Sí" | "No", string][] = [
      ["gastos_bajo_limite_smvm", "Sí", "no"],
      ["gastos_bajo_limite_smvm", "No", "si"],
      ["no_accedio_mercado_cambios", "Sí", "no"],
      ["no_accedio_mercado_cambios", "No", "si"],
      ["embarazada", "Sí", "si"],
      ["hijos_menores_a_cargo", "No", "no"],
    ];
    for (const [name, visible, value] of table) {
      expect(radio(name, visible).value).toBe(value);
    }
    expect(step(4).querySelectorAll(".pas-ddjj-options-inverted")).toHaveLength(2);
  });

  it("requires an answer before continuing and shows conditional questions only for «Sí»", async () => {
    await renderForm();
    click("ddjj-next");
    expect(step(2).style.display).toBe("block");
    expect(scrollMock).toHaveBeenLastCalledWith({ top: 0, behavior: "smooth" });
    const report = vi.spyOn(HTMLInputElement.prototype, "reportValidity");
    click("ddjj-next");
    expect(report).toHaveBeenCalled();
    expect(step(2).style.display).toBe("block");

    const conditional = document.querySelector<HTMLElement>('[data-condition="embarazada"]')!;
    expect(conditional.hidden).toBe(true);
    expect(radio("controles_embarazo_cumplidos", "Sí").disabled).toBe(true);
    fireEvent.click(radio("embarazada", "Sí"));
    expect(conditional.hidden).toBe(false);
    expect(radio("controles_embarazo_cumplidos", "Sí").disabled).toBe(false);
    click("ddjj-next");
    expect(step(2).style.display).toBe("block");
    fireEvent.click(radio("controles_embarazo_cumplidos", "No"));
    click("ddjj-next");
    expect(step(3).style.display).toBe("block");
    expect(screen.getByText("Paso 3 de 5")).toBeTruthy();
    expect(document.getElementById("ddjj-next")!.textContent).toBe("Continuar");
    click("ddjj-back");
    expect(step(2).style.display).toBe("block");
    report.mockRestore();
  });

  it("reloads municipalities like the native script, including its fallbacks", async () => {
    await renderForm();
    let resolve: (value: Response) => void = () => undefined;
    fetchMock.mockImplementationOnce(() => new Promise<Response>((done) => (resolve = done)));
    const municipio = () => document.getElementById("id_municipio") as HTMLSelectElement;

    fireEvent.change(document.getElementById("id_provincia")!, { target: { value: "2" } });
    expect([...municipio().options].map((o) => o.text)).toEqual(["Cargando municipios..."]);
    const url = fetchMock.mock.calls.at(-1)![0] as URL;
    expect(url.pathname).toBe(`${PATH}/municipios`);
    expect(url.searchParams.get("provincia_id")).toBe("2");
    await act(async () => resolve(json([{ id: 9, nombre: "Río Cuarto" }])));
    expect([...municipio().options].map((o) => [o.value, o.text])).toEqual([
      ["", "Seleccioná un municipio"],
      ["9", "Río Cuarto"],
    ]);

    fetchMock.mockResolvedValueOnce(json({ detalle: "Invitacion no disponible." }, 410));
    fireEvent.change(document.getElementById("id_provincia")!, { target: { value: "1" } });
    await waitFor(() =>
      expect([...municipio().options].map((o) => o.text)).toEqual([
        "No se pudieron cargar los municipios",
      ]),
    );
    fetchMock.mockRejectedValueOnce(new TypeError("offline"));
    fireEvent.change(document.getElementById("id_provincia")!, { target: { value: "2" } });
    await waitFor(() =>
      expect([...municipio().options].map((o) => o.text)).toEqual([
        "No se pudieron cargar los municipios",
      ]),
    );
  });

  it("summarises visible answers and posts once with CSRF and the native fields", async () => {
    await renderForm();
    await completeSteps({
      embarazada: "No",
      hijos_menores_a_cargo: "Sí",
      vacunacion_cumplida: "Sí",
      regularidad_escolar_acreditada: "No",
      gastos_bajo_limite_smvm: "Sí",
      no_accedio_mercado_cambios: "No",
    });
    expect(screen.getByText("Paso 5 de 5")).toBeTruthy();
    const rows = [...document.querySelectorAll("#ddjj-summary > div")].map((row) => [
      row.querySelector("strong")!.textContent,
      row.querySelector("span")!.textContent,
    ]);
    expect(rows).toEqual([
      ["Domicilio", "Calle 7 1234"],
      ["Provincia", "Buenos Aires"],
      ["Municipio", "La Plata"],
      ["Embarazo", "No"],
      ["Menores de 18 años a cargo", "Sí"],
      ["Plan Nacional de Vacunación", "Sí"],
      ["Regularidad escolar", "No"],
      ["Gastos sobre 1 SMVM", "Sí"],
      ["Compra de divisas", "No"],
    ]);

    click("ddjj-submit");
    expect(document.getElementById("ddjj-confirm-modal")!.hidden).toBe(true);
    fireEvent.click(document.getElementById("id_acepto_declaracion")!);
    click("ddjj-submit");
    const modal = document.getElementById("ddjj-confirm-modal")!;
    expect(modal.hidden).toBe(false);
    expect(document.activeElement!.textContent).toBe("Atrás");

    fetchMock.mockResolvedValueOnce(json({ redirect: "/pas/ddjj/confirmacion" }));
    click("ddjj-confirm-send");
    click("ddjj-confirm-send");
    await waitFor(() => expect(navigateTo).toHaveBeenCalledWith("/pas/ddjj/confirmacion"));
    const posts = fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
    expect(posts).toHaveLength(1);
    const [url, init] = posts[0];
    expect(url).toBe(`${PATH}/enviar`);
    expect(init.headers["X-CSRFToken"]).toBe("synthetic-csrf");
    expect(init.redirect).toBe("manual");
    expect([...(init.body as URLSearchParams)]).toEqual([
      ["datos_mi_argentina_confirmados", "no"],
      ["calle", "Calle 7"],
      ["altura", "1234"],
      ["provincia", "1"],
      ["municipio", "2"],
      ["correo_electronico", "persona@example.invalid"],
      ["telefono_celular", "11 66 435632"],
      ["embarazada", "no"],
      ["hijos_menores_a_cargo", "si"],
      ["vacunacion_cumplida", "si"],
      ["regularidad_escolar_acreditada", "no"],
      ["gastos_bajo_limite_smvm", "no"],
      ["no_accedio_mercado_cambios", "si"],
      ["acepto_declaracion", "on"],
    ]);
  });

  it("shows server errors on the first failing step and restores answers as the native page", async () => {
    await renderForm();
    await completeSteps({
      embarazada: "No",
      hijos_menores_a_cargo: "No",
      gastos_bajo_limite_smvm: "Sí",
      no_accedio_mercado_cambios: "Sí",
    });
    fireEvent.click(document.getElementById("id_acepto_declaracion")!);
    click("ddjj-submit");
    const bound = payload();
    bound.values = {
      ...bound.values,
      calle: "",
      embarazada: "no",
      hijos_menores_a_cargo: "no",
      gastos_bajo_limite_smvm: "no",
      no_accedio_mercado_cambios: "no",
      acepto_declaracion: true,
    };
    bound.errors = { calle: ["Este dato es obligatorio."] };
    fetchMock.mockResolvedValueOnce(json(bound, 400));
    click("ddjj-confirm-send");

    await screen.findByText("Este dato es obligatorio.");
    expect(scrollMock).toHaveBeenLastCalledWith({ top: 0, behavior: "instant" });
    expect(step(1).style.display).toBe("block");
    expect(screen.getByText("Paso 1 de 5")).toBeTruthy();
    const calle = document.getElementById("id_calle")!;
    expect(calle.getAttribute("aria-invalid")).toBe("true");
    expect(calle.getAttribute("aria-describedby")).toBe("id_calle_error");
    expect(document.getElementById("ddjj-confirm-modal")!.hidden).toBe(true);
    expect((document.getElementById("id_acepto_declaracion") as HTMLInputElement).checked).toBe(true);
    // Native 400 re-render: the inverted answers come back on the opposite visible option.
    expect(radio("gastos_bajo_limite_smvm", "No").checked).toBe(true);
    expect(radio("gastos_bajo_limite_smvm", "No").value).toBe("si");
    expect(radio("no_accedio_mercado_cambios", "No").checked).toBe(true);
    expect(radio("embarazada", "No").checked).toBe(true);
    expect(navigateTo).not.toHaveBeenCalled();
  });

  it.each([
    ["an unavailable invitation", () => Promise.resolve(json({ detail: "x" }, 410))],
    ["a lost response", () => Promise.reject(new TypeError("network"))],
    ["a CSRF rejection", () => Promise.resolve(new Response("forbidden", { status: 403 }))],
  ])("returns to the canonical URL with a GET after %s, never replaying the POST", async (_, outcome) => {
    await renderForm();
    await completeSteps({
      embarazada: "No",
      hijos_menores_a_cargo: "No",
      gastos_bajo_limite_smvm: "No",
      no_accedio_mercado_cambios: "No",
    });
    fireEvent.click(document.getElementById("id_acepto_declaracion")!);
    click("ddjj-submit");
    fetchMock.mockImplementationOnce(outcome);
    click("ddjj-confirm-send");

    await waitFor(() => expect(navigateTo).toHaveBeenCalledWith(PATH));
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  });

  it.each([404, 410])("replaces the page with the canonical URL when data answers %s", async (status) => {
    fetchMock.mockResolvedValueOnce(json({ detail: "x" }, status));
    render(<DdjjForm pathname={PATH} />);
    await waitFor(() => expect(replaceWith).toHaveBeenCalledWith(PATH));
    expect(document.querySelector("#pas-ddjj-form")).toBeNull();
  });

  it("opens the legal terms focusing their close button and closes them", async () => {
    await renderForm();
    await completeSteps({
      embarazada: "No",
      hijos_menores_a_cargo: "No",
      gastos_bajo_limite_smvm: "No",
      no_accedio_mercado_cambios: "No",
    });
    click("ddjj-legal-open");
    const modal = document.getElementById("ddjj-legal-modal")!;
    expect(modal.hidden).toBe(false);
    expect(document.activeElement!.getAttribute("aria-label")).toBe("Cerrar");
    expect(modal.textContent).toContain("Programa de Acompañamiento Social (PAS).");
    fireEvent.click(document.activeElement!);
    expect(modal.hidden).toBe(true);
  });
});
