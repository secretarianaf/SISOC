import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { IntervencionesObservaciones as Tabs, NominaCard, RelacionesModales, type RelacionesModal, relacionesNavigation, relacionesValid } from "./comedorFichaRelaciones";
import { relacionesFixture } from "./comedorFichaFixtures";
import { tomarRechazo } from "./comedorFichaRechazo";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const fixture = relacionesFixture();
/** The tabs card and the modals, wired as the ficha page wires them. */
function IntervencionesObservaciones({ i, o }: { i: typeof fixture.intervenciones; o: typeof fixture.observaciones }) {
  const [modal, setModal] = useState<RelacionesModal>(null);
  return <><Tabs i={i} o={o} onModal={setModal} /><RelacionesModales i={i} o={o} modal={modal} close={() => setModal(null)} /></>;
}
let assign: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  vi.clearAllMocks();
  window.sessionStorage.clear();
  window.history.replaceState({}, "", "/comedores/7?admision_id=3&intervenciones_page=1&x=a b");
  assign = vi.spyOn(relacionesNavigation, "assign").mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); assign.mockRestore(); });

describe("Comedor ficha: nómina card", () => {
  it("validates the three keys", () => {
    expect(relacionesValid({ ...fixture })).toBe(true);
    expect(relacionesValid({ ...fixture, nomina: { ...fixture.nomina, ver: "https://evil.example/" } })).toBe(false);
    expect(relacionesValid({})).toBe(false);
  });

  it("draws the link, the pending notice, the native import form and the six boxes", () => {
    render(<NominaCard data={fixture.nomina} />);
    expect(screen.getByRole("link", { name: /Ver nómina/ }).getAttribute("href")).toBe("/comedores/7/admision/3/nomina/");
    expect(screen.getByText(/Nómina pendiente de presentación\./)).toBeTruthy();
    const form = document.querySelector("form")!;
    expect(form.getAttribute("method")).toBe("post");
    expect(form.getAttribute("action")).toBe("/comedores/7/admision/3/nomina/importar/");
    expect((form.querySelector("input[name=csrfmiddlewaretoken]") as HTMLInputElement).value).toBe("synthetic-csrf-token");
    expect([...document.querySelectorAll(".fs-2")].map((e) => e.textContent)).toEqual(["10", "4", "6", "2", "1", "0"]);
    expect(screen.getByText("Dados de baja")).toBeTruthy();
  });

  it("direct nómina shows the info notice and no import form or link", () => {
    render(<NominaCard data={{ ...fixture.nomina, ver: null, importar: null, pendiente: false, directa: true }} />);
    expect(screen.getByText(/Este comedor usa nómina directa/)).toBeTruthy();
    expect(document.querySelector("form")).toBeNull();
    expect(screen.queryByRole("link", { name: /Ver nómina/ })).toBeNull();
  });
});

describe("Comedor ficha: intervenciones and observaciones tabs", () => {
  it("tables, convenio buttons, badges and the pager keep the native markup", () => {
    render(<IntervencionesObservaciones i={fixture.intervenciones} o={fixture.observaciones} />);
    expect(screen.getAllByRole("columnheader").slice(0, 7).map((h) => h.textContent)).toEqual(["Fecha", "Intervención", "Sub intervención", "Doc. adjunta", "Destinatario", "Usuario creador", "Acciones"]);
    expect(screen.getByRole("link", { name: "C-1" }).className).toBe("btn btn-sm btn-primary");
    expect(screen.getByRole("link", { name: /Admisión #4/ }).getAttribute("href")).toBe("?admision_id=4#intervenciones-tab");
    expect(screen.getByText("Cerrada").className).toBe("badge bg-secondary ms-1");
    expect(screen.getByText("No").className).toBe("badge bg-secondary");
    const acciones = document.querySelector("tbody tr td:last-child")!;
    expect(acciones.textContent).toBe("Ver Eliminar");
    const siguiente = screen.getAllByRole("link", { name: "Continuar" })[0];
    expect(siguiente.getAttribute("href")).toBe("?admision_id=3&x=a+b&intervenciones_page=2");
    expect(screen.getByText("Se encontraron 12 resultados")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Volver" }).parentElement!.className).toBe("page-item disabled");
  });

  it("the tabs switch the panes", () => {
    render(<IntervencionesObservaciones i={fixture.intervenciones} o={fixture.observaciones} />);
    expect(document.getElementById("observaciones-pane")!.className).toBe("tab-pane fade");
    fireEvent.click(screen.getByRole("tab", { name: "Observaciones" }));
    expect(document.getElementById("observaciones-pane")!.className).toBe("tab-pane fade show active");
    expect(document.getElementById("intervenciones-pane")!.className).toBe("tab-pane fade");
    expect(screen.getByRole("tab", { name: "Observaciones" }).getAttribute("aria-selected")).toBe("true");
  });

  it("an empty table shows no result count, as the template (an empty page is falsy)", () => {
    render(<IntervencionesObservaciones i={{ ...fixture.intervenciones, filas: [], paginacion: null, resultados: 0 }} o={fixture.observaciones} />);
    expect(screen.queryByText("Se encontraron 0 resultados")).toBeNull();
    expect(screen.getByText("Se encontraron 1 resultados")).toBeTruthy();
  });

  it("empty tables show the native messages", () => {
    render(<IntervencionesObservaciones i={{ ...fixture.intervenciones, filas: [], paginacion: null, resultados: 0 }} o={{ ...fixture.observaciones, filas: [], resultados: 0 }} />);
    expect(screen.getByText("Aún no se han registrado intervenciones.")).toBeTruthy();
    expect(screen.getByText("Sin observaciones registradas.")).toBeTruthy();
  });

  it("the intervention modal loads subtypes, validates the date, posts the multipart form and navigates", async () => {
    webGet.mockResolvedValue({ data: [{ id: 8, text: "Ingreso" }] });
    webPost.mockResolvedValue({ status: 200, data: { ok: true, redirect: "/comedores/7?admision_id=3" } });
    render(<IntervencionesObservaciones i={fixture.intervenciones} o={fixture.observaciones} />);
    fireEvent.click(screen.getByRole("button", { name: "Agregar intervención" }));
    const modal = await screen.findByRole("dialog");
    expect(within(modal).getByText("Nueva intervención", { selector: "h5" })).toBeTruthy();
    fireEvent.change(document.getElementById("id_tipo_intervencion")!, { target: { value: "1" } });
    await waitFor(() => expect(within(modal).getByRole("option", { name: "Ingreso" })).toBeTruthy());
    expect(webGet.mock.calls[0][0]).toBe("web/comedores/intervenciones/subestados/");
    expect(document.getElementById("documentacion-field-modal")!.className).toBe("col-12 d-none");
    fireEvent.click(document.getElementById("id_tiene_documentacion")!);
    expect(document.getElementById("documentacion-field-modal")!.className).toBe("col-12");

    fireEvent.change(document.getElementById("id_fecha")!, { target: { value: "1999-01-01" } });
    expect(screen.getByText("El año de la fecha debe estar entre 2000 y 2100.")).toBeTruthy();
    fireEvent.submit(document.getElementById("intervencionModalForm")!);
    expect(webPost).not.toHaveBeenCalled();

    fireEvent.change(document.getElementById("id_fecha")!, { target: { value: "2026-03-05" } });
    fireEvent.submit(document.getElementById("intervencionModalForm")!);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/7?admision_id=3"));
    expect(webPost.mock.calls[0][0]).toBe("web/comedores/intervenciones/comedor/7/crear/");
    const body = webPost.mock.calls[0][1] as FormData;
    expect(body.get("next")).toBe("/comedores/7?admision_id=3");
    expect(body.get("admision_id")).toBe("3");
  });

  it("a rejected intervention goes to the create page with the 400 payload, as the native page re-renders the form", async () => {
    const payload = { comedor: { id: 7 }, fields: { fecha: { invalid: true } } };
    webPost.mockResolvedValue({ status: 400, data: payload });
    render(<IntervencionesObservaciones i={fixture.intervenciones} o={fixture.observaciones} />);
    fireEvent.click(screen.getByRole("button", { name: "Agregar intervención" }));
    await screen.findByRole("dialog");
    fireEvent.submit(document.getElementById("intervencionModalForm")!);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/intervencion/crear/7"));
    expect(tomarRechazo("web/comedores/intervenciones/comedor/7/crear/", (v): v is typeof payload => !!v)).toEqual(payload);
  });

  it("a rejected observation goes to its create page with the 400 payload", async () => {
    const payload = { value: "", errors: { observacion: [{ message: "Este campo es obligatorio." }] } };
    webPost.mockResolvedValue({ status: 400, data: payload });
    render(<IntervencionesObservaciones i={fixture.intervenciones} o={fixture.observaciones} />);
    fireEvent.click(screen.getByRole("tab", { name: "Observaciones" }));
    fireEvent.click(screen.getByRole("button", { name: "Agregar observación" }));
    await screen.findByRole("dialog");
    fireEvent.submit(document.getElementById("observacionModalForm")!);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/7/observacion/crear"));
    expect(webPost.mock.calls[0][2].validateStatus(400)).toBe(true);
    expect(tomarRechazo("web/comedores/observaciones/comedor/7/crear/", (v): v is typeof payload => !!v)).toEqual(payload);
  });

  it("a 403 (or a 400 without payload) keeps the modal open with a toast and never navigates", async () => {
    webPost.mockResolvedValue({ status: 403, data: { detail: "no" } });
    render(<IntervencionesObservaciones i={fixture.intervenciones} o={fixture.observaciones} />);
    fireEvent.click(screen.getByRole("button", { name: "Agregar intervención" }));
    await screen.findByRole("dialog");
    fireEvent.submit(document.getElementById("intervencionModalForm")!);
    expect(await screen.findByText(/No se pudo guardar la intervención/)).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("the modals leave the body as Bootstrap does and the Tab wrap skips the hidden inputs", async () => {
    render(<IntervencionesObservaciones i={fixture.intervenciones} o={fixture.observaciones} />);
    fireEvent.click(screen.getByRole("tab", { name: "Observaciones" }));
    fireEvent.click(screen.getByRole("button", { name: "Agregar observación" }));
    const dialog = await screen.findByRole("dialog");
    expect(document.body.style.overflow).toBe("hidden");
    expect(document.body.style.paddingRight).toBe("0px");
    const guardar = within(dialog).getByRole("button", { name: "Guardar observación" });
    guardar.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: "Close" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(document.body.style.overflow).toBe("");
  });

  it("the observation modal posts and navigates; a failure shows a toast", async () => {
    webPost.mockResolvedValueOnce({ status: 200, data: { ok: true, redirect: "/comedores/7" } });
    render(<IntervencionesObservaciones i={fixture.intervenciones} o={fixture.observaciones} />);
    fireEvent.click(screen.getByRole("tab", { name: "Observaciones" }));
    fireEvent.click(screen.getByRole("button", { name: "Agregar observación" }));
    await screen.findByRole("dialog");
    expect((document.getElementById("id_observacion") as HTMLTextAreaElement).placeholder).toBe("Describa la observación");
    fireEvent.submit(document.getElementById("observacionModalForm")!);
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/comedores/7"));
    expect(webPost.mock.calls[0][0]).toBe("web/comedores/observaciones/comedor/7/crear/");
  });

  it("a network failure on the observation modal shows a toast", async () => {
    webPost.mockRejectedValueOnce(new Error("network"));
    render(<IntervencionesObservaciones i={fixture.intervenciones} o={fixture.observaciones} />);
    fireEvent.click(screen.getByRole("tab", { name: "Observaciones" }));
    fireEvent.click(screen.getByRole("button", { name: "Agregar observación" }));
    await screen.findByRole("dialog");
    fireEvent.submit(document.getElementById("observacionModalForm")!);
    expect(await screen.findByText(/No se pudo guardar la observación/)).toBeTruthy();
    expect(assign).not.toHaveBeenCalled();
  });
});
