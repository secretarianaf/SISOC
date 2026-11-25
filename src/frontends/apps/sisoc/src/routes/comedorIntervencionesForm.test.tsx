import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { formValid, intervencionFormNavigation } from "./comedorIntervencionesForm";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const API = "web/comedores/intervenciones/";
const select = (id: string, label: string, options: [string, string][], value = "", extra: Record<string, unknown> = {}) => ({
  id, label, required: true, invalid: false, value, options: [{ value: "", label: "---------" }, ...options.map(([v, l]) => ({ value: v, label: l }))], ...extra,
});
const form = (over: Record<string, unknown> = {}, fields: Record<string, unknown> = {}) => ({
  comedor: { id: 3, nombre: "Comedor Sintético", url: "/comedores/3" }, admision_id: null,
  fields: {
    tipo_intervencion: select("id_tipo_intervencion", "Tipo de Intervención", [["1", "Visita"], ["2", "Llamada"]]),
    subintervencion: select("id_subintervencion", "Subtipo de Intervención", [], "", { required: false }),
    destinatario: select("id_destinatario", "Destinatario", [["7", "Titular"]]),
    forma_contacto: select("id_forma_contacto", "Forma de Contacto", [["4", "Presencial"]]),
    fecha: { id: "id_fecha", label: "Fecha", required: true, invalid: false, value: "13/11/2026", hidden_initial: "2026-11-13 11:06:47" },
    observaciones: { id: "id_observaciones", label: "Descripción", required: false, invalid: false, value: "" },
    tiene_documentacion: { id: "id_tiene_documentacion", label: "Documentación Adjunta", required: false, invalid: false, value: false },
    documentacion: { id: "id_documentacion", label: "Cargar Documentación" },
    ...fields,
  },
  messages: [], ...over,
});

function serve(body: unknown) {
  webGet.mockImplementation((url: string) => Promise.resolve(
    url === "web/session/" ? { data: readyContext, status: 200 }
      : url === `${API}subestados/` ? { data: [{ id: 11, text: "Inicial" }, { id: 12, text: "Seguimiento" }], status: 200 }
        : { data: body, status: 200 }));
}
function setup(url: string) {
  window.history.replaceState({}, "", url);
  return render(<App />);
}
const byId = (id: string) => document.getElementById(id) as HTMLInputElement & HTMLSelectElement;
const stepClasses = () => [byId("step-1").className, byId("step-2").className];

async function pick(id: string, label: string) {
  const box = document.querySelector<HTMLElement>(`#${id} + .select2 .select2-selection`)!;
  fireEvent.mouseDown(box);
  fireEvent.click(await screen.findByRole("option", { name: label }));
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Comedor intervention form", () => {
  it("owns the native create and edit URLs and validates its payload", () => {
    expect(findRoute("/comedores/intervencion/crear/3")?.route.name).toBe("comedores-intervenciones");
    expect(findRoute("/comedores/intervencion/editar/5/3")?.route.name).toBe("comedores-intervenciones");
    expect(findRoute("/comedores/intervencion/crear/3/")?.route.name).not.toBe("comedores-intervenciones");
    expect(formValid(form())).toBe(true);
    expect(formValid(form({ admision_id: "1" }))).toBe(false);
    expect(formValid(form({}, { fecha: { id: "id_fecha" } }))).toBe(false);
  });

  it("renders the wizard at step 1 with the native labels, hidden inputs and the progress bar", async () => {
    serve(form({ admision_id: 9 }));
    setup("/comedores/intervencion/crear/3?admision_id=9");
    expect(await screen.findByText("Nueva Intervención")).toBeTruthy();
    expect(webGet).toHaveBeenCalledWith(`${API}comedor/3/crear/?admision_id=9`, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Agregar Intervención"));
    expect(stepClasses()).toEqual(["step-container", "step-container d-none"]);
    expect(document.querySelector("#current-step")?.textContent).toBe("1");
    expect((document.querySelector("#progressBarFill") as HTMLElement).style.width).toBe("50%");
    expect(document.querySelector<HTMLInputElement>('input[name="admision_id"]')?.value).toBe("9");
    expect(document.querySelector<HTMLInputElement>('input[name="csrfmiddlewaretoken"]')?.value).toBe("synthetic-csrf-token");
    expect(document.querySelector('label[for="id_tipo_intervencion"]')?.textContent).toBe("Tipo de Intervención *");
    expect(document.querySelector('label[for="id_subintervencion"]')?.textContent).toBe("Subtipo de Intervención");
    expect(document.querySelector(".select2-selection__placeholder")?.textContent).toBe("Seleccione un tipo de intervención");
    expect(byId("id_fecha").getAttribute("min")).toBe("2000-01-01");
    expect(document.querySelector('input[name="initial-fecha"]')?.getAttribute("value")).toBe("2026-11-13 11:06:47");
    expect(byId("documentacion-field").className).toBe("row d-none");
  });

  it("validates step 1 like the template script and moves between steps", async () => {
    serve(form());
    setup("/comedores/intervencion/crear/3");
    fireEvent.click(await screen.findByRole("button", { name: /Siguiente/ }));
    expect(stepClasses()[0]).toBe("step-container");
    expect(byId("id_tipo_intervencion").className).toContain("is-invalid");
    expect(byId("id_destinatario").className).toContain("is-invalid");
    await pick("id_tipo_intervencion", "Visita");
    fireEvent.change(byId("id_destinatario"), { target: { value: "7" } });
    fireEvent.click(screen.getByRole("button", { name: /Siguiente/ }));
    expect(stepClasses()).toEqual(["step-container d-none", "step-container"]);
    expect(document.querySelector("#current-step")?.textContent).toBe("2");
    expect((document.querySelector("#progressBarFill") as HTMLElement).style.width).toBe("100%");
    fireEvent.click(screen.getByRole("button", { name: /Anterior/ }));
    expect(stepClasses()).toEqual(["step-container", "step-container d-none"]);
  });

  it("loads the subtypes of the chosen type, resets them on change and shows the file row on demand", async () => {
    serve(form());
    setup("/comedores/intervencion/crear/3");
    await screen.findByText("Nueva Intervención");
    await pick("id_tipo_intervencion", "Visita");
    await waitFor(() => expect(webGet).toHaveBeenCalledWith(`${API}subestados/`, { params: { id: "1" } }));
    await waitFor(() => expect(Array.from(byId("id_subintervencion").options).map((o) => o.text)).toEqual(["Seleccione una opción", "Inicial", "Seguimiento"]));
    await pick("id_subintervencion", "Seguimiento");
    expect(byId("id_subintervencion").value).toBe("12");
    await pick("id_tipo_intervencion", "Llamada");
    await waitFor(() => expect(byId("id_subintervencion").value).toBe(""));
    fireEvent.click(byId("id_tiene_documentacion"));
    expect(byId("documentacion-field").className).toBe("row");
    fireEvent.click(byId("id_tiene_documentacion"));
    expect(byId("documentacion-field").className).toBe("row d-none");
  });

  it("keeps the native edit quirks: reloads the subtypes dropping the selection and ignores the localized date", async () => {
    serve(form({}, {
      tipo_intervencion: select("id_tipo_intervencion", "Tipo de Intervención", [["1", "Visita"]], "1"),
      subintervencion: select("id_subintervencion", "Subtipo de Intervención", [["12", "Seguimiento"]], "12", { required: false }),
      observaciones: { id: "id_observaciones", label: "Descripción", required: false, invalid: false, value: "Original" },
    }));
    setup("/comedores/intervencion/editar/5/3");
    await screen.findByText("Nueva Intervención");
    expect(webGet).toHaveBeenCalledWith(`${API}5/editar/3/`, expect.anything());
    await waitFor(() => expect(webGet).toHaveBeenCalledWith(`${API}subestados/`, { params: { id: "1" } }));
    await waitFor(() => expect(byId("id_subintervencion").options.length).toBe(3));
    expect(byId("id_subintervencion").value).toBe("");
    expect(byId("id_tipo_intervencion").value).toBe("1");
    expect(byId("id_fecha").value).toBe("");
    expect((byId("id_observaciones") as unknown as HTMLTextAreaElement).value).toBe("Original");
  });

  it("blocks the submit for a date outside 2000-2100 and clears the message when fixed", async () => {
    serve(form());
    setup("/comedores/intervencion/crear/3");
    await screen.findByText("Nueva Intervención");
    fireEvent.change(byId("id_fecha"), { target: { value: "1999-06-15" } });
    expect(byId("fecha-error").textContent).toBe("El año de la fecha debe ser mayor o igual a 2000.");
    expect(byId("fecha-error").style.display).toBe("block");
    expect(byId("id_fecha").className).toContain("is-invalid");
    fireEvent.submit(byId("intervencionForm"));
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.change(byId("id_fecha"), { target: { value: "2101-06-15" } });
    expect(byId("fecha-error").textContent).toBe("El año de la fecha debe ser menor o igual a 2100.");
    fireEvent.change(byId("id_fecha"), { target: { value: "2026-06-15" } });
    expect(byId("fecha-error").style.display).toBe("none");
    expect(byId("id_fecha").className).not.toContain("is-invalid");
  });

  it("posts the multipart form once and follows the native redirect, local or same site only", async () => {
    serve(form({ admision_id: 9 }));
    const assign = vi.spyOn(intervencionFormNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ data: { ok: true, redirect: "/comedores/intervencion/ver/3?admision_id=9" }, status: 200 });
    setup("/comedores/intervencion/crear/3?admision_id=9&next=/comedores/3");
    await screen.findByText("Nueva Intervención");
    await pick("id_tipo_intervencion", "Visita");
    fireEvent.change(byId("id_destinatario"), { target: { value: "7" } });
    fireEvent.change(byId("id_forma_contacto"), { target: { value: "4" } });
    fireEvent.change(byId("id_fecha"), { target: { value: "2026-10-01" } });
    fireEvent.change(byId("id_observaciones"), { target: { value: "Texto" } });
    fireEvent.submit(byId("intervencionForm"));
    fireEvent.submit(byId("intervencionForm"));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/intervencion/ver/3?admision_id=9"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(webPost.mock.calls[0][0]).toBe(`${API}comedor/3/crear/?admision_id=9&next=/comedores/3`);
    const body = webPost.mock.calls[0][1] as FormData;
    expect(Object.fromEntries(Array.from(body.entries()).filter(([k]) => k !== "documentacion"))).toMatchObject({
      csrfmiddlewaretoken: "synthetic-csrf-token", admision_id: "9", tipo_intervencion: "1", subintervencion: "", destinatario: "7",
      fecha: "2026-10-01", forma_contacto: "4", observaciones: "Texto", "initial-fecha": "2026-11-13 11:06:47",
    });
    expect(body.has("tiene_documentacion")).toBe(false);
  });

  it("re-renders the bound form at step 1 after a rejected POST and never navigates", async () => {
    serve(form());
    const assign = vi.spyOn(intervencionFormNavigation, "assign").mockImplementation(() => undefined);
    const rejected = form({}, {
      tipo_intervencion: select("id_tipo_intervencion", "Tipo de Intervención", [["1", "Visita"]], "1"),
      destinatario: select("id_destinatario", "Destinatario", [["7", "Titular"]], "", { invalid: true }),
      observaciones: { id: "id_observaciones", label: "Descripción", required: false, invalid: false, value: "No se pierde" },
    });
    webPost.mockResolvedValueOnce({ data: rejected, status: 400 });
    setup("/comedores/intervencion/crear/3");
    await screen.findByText("Nueva Intervención");
    fireEvent.click(screen.getByRole("button", { name: /Siguiente/ }));
    byId("id_tipo_intervencion");
    fireEvent.submit(byId("intervencionForm"));
    await waitFor(() => expect(byId("id_destinatario").getAttribute("aria-invalid")).toBe("true"));
    expect(byId("id_destinatario").getAttribute("aria-describedby")).toBe("id_destinatario_error");
    expect(stepClasses()).toEqual(["step-container", "step-container d-none"]);
    expect((byId("id_observaciones") as unknown as HTMLTextAreaElement).value).toBe("No se pierde");
    expect(assign).not.toHaveBeenCalled();
  });

  it("reports an unconfirmed or forbidden post and does not resubmit on its own", async () => {
    serve(form());
    const assign = vi.spyOn(intervencionFormNavigation, "assign").mockImplementation(() => undefined);
    webPost.mockRejectedValueOnce(new Error("network"));
    setup("/comedores/intervencion/crear/3");
    await screen.findByText("Nueva Intervención");
    fireEvent.submit(byId("intervencionForm"));
    expect(await screen.findByText(/No se pudo confirmar el resultado/)).toBeTruthy();
    webPost.mockResolvedValueOnce({ data: { detail: "No tiene permisos." }, status: 403 });
    fireEvent.submit(byId("intervencionForm"));
    expect(webPost).toHaveBeenCalledTimes(1);
    expect(assign).not.toHaveBeenCalled();
    expect(within(byId("step-2")).getByRole("alert")).toBeTruthy();
  });
});
