import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const NATIVO = "/comedores/admision/informe_tecnico/base/5/ver/";
const API = "web/comedores/admisiones/informes/base/5/";
const informe = (over: Record<string, unknown> = {}) => ({
  id: 5, tipo: "base", estado: "Iniciado", comedor: "Comedor Sintético", observaciones_subsanacion: "",
  campos: [{ nombre: "Fecha de pedido", valor: "01/11/2026" }, { nombre: "Localidad", valor: "Centro" }],
  archivos: { docx_descargar: null, docx_editado_ver: null, pdf_final: null, borrador: null },
  puede_cambiar_estado: true, puede_subsanar: true,
  urls: { admision: "/comedores/admision/3/tecnicos/editar/", accion: NATIVO }, messages: [], ...over,
});

function serve(data: unknown, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/" ? { data: readyContext, status: 200 } : { data, status }));
}
function setup(path = NATIVO) {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC";
  setViewport(false);
});
afterEach(() => cleanup());

describe("Technical report detail route (AD02.01)", () => {
  it("owns only the native detail page", () => {
    expect(findRoute(NATIVO)?.params).toEqual({ tipo: "base", id: "5" });
    expect(findRoute("/comedores/admision/informe_tecnico/juridico/9/ver/")?.params).toEqual({ tipo: "juridico", id: "9" });
    for (const other of ["/comedores/admision/informe_tecnico/base/5/editar/", "/comedores/admision/informe_tecnico/base/5/ver", "/comedores/admision/informe_complementario/base/5/ver/"]) {
      expect(findRoute(other)?.route.name).not.toBe("comedores-informe-tecnico-detalle");
    }
  });

  it("renders the heading, breadcrumb, observations and every field with its checkbox", async () => {
    serve(informe({ observaciones_subsanacion: "Revisar fechas", messages: [{ message: "DOCX enviado a validar correctamente.", level: "success" }] }));
    setup();
    await screen.findByText("Fecha de pedido");
    expect(webGet).toHaveBeenCalledWith(API, expect.anything());
    await waitFor(() => expect(document.title).toBe("SISOC - Informe Técnico: Comedor Sintético"));
    expect(screen.getByText("Informe Técnico: Comedor Sintético - Estado: Iniciado")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Comedor Sintético" }).getAttribute("href")).toBe("/comedores/admision/3/tecnicos/editar/");
    expect(screen.getByText("Revisar fechas")).toBeTruthy();
    expect(screen.getByText("DOCX enviado a validar correctamente.")).toBeTruthy();
    expect(screen.getAllByLabelText("Subsanar")).toHaveLength(2);
    expect(screen.getByText("01/11/2026")).toBeTruthy();
  });

  it("a validated report shows the final PDF and neither review nor checkboxes", async () => {
    serve(informe({ estado: "Validado", puede_cambiar_estado: false, puede_subsanar: false, archivos: { docx_descargar: null, docx_editado_ver: null, pdf_final: "/media/final.pdf", borrador: null } }));
    setup();
    expect((await screen.findByRole("link", { name: /PDF Final/ })).getAttribute("href")).toBe("/media/final.pdf");
    expect(screen.queryByText("Cambiar estado")).toBeNull();
    expect(screen.queryByLabelText("Subsanar")).toBeNull();
  });

  it("the upload modal posts the DOCX to the native URL", async () => {
    serve(informe({ estado: "Docx generado", puede_cambiar_estado: false, archivos: { docx_descargar: "/media/b.docx", docx_editado_ver: null, pdf_final: null, borrador: { kind: "docx_final", url: "/media/b.docx" } } }));
    setup();
    expect((await screen.findByRole("link", { name: /Descargar DOCX/ })).getAttribute("href")).toBe("/media/b.docx");
    expect(screen.getByRole("link", { name: /DOCX Final/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Subir DOCX Editado/ }));
    const form = screen.getByRole("button", { name: "Subir Archivo" }).closest("form")!;
    expect(form.method).toBe("post");
    expect(form.enctype).toBe("multipart/form-data");
    expect(form.getAttribute("action")).toBe(NATIVO);
    expect((form.querySelector('[name="csrfmiddlewaretoken"]') as HTMLInputElement).value).toBe("synthetic-csrf-token");
    expect((form.querySelector("#docx_editado") as HTMLInputElement).required).toBe(true);
    expect((screen.getByRole("button", { name: "Subir Archivo" }) as HTMLButtonElement).name).toBe("subir_docx");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("button", { name: "Subir Archivo" })).toBeNull();
  });

  it("the status modal needs a checked field and observations to fix, like the native script", async () => {
    serve(informe());
    setup();
    await screen.findByText("Fecha de pedido");
    fireEvent.click(screen.getByText("Cambiar estado"));
    const guardar = screen.getByRole("button", { name: "Guardar" }) as HTMLButtonElement;
    fireEvent.change(screen.getByLabelText("Nuevo estado"), { target: { value: "A subsanar" } });
    expect(screen.getByText("Debe marcar al menos un campo para subsanar.")).toBeTruthy();
    expect(guardar.disabled).toBe(true);
    fireEvent.click(screen.getAllByLabelText("Subsanar")[1]);
    expect(guardar.disabled).toBe(false);
    expect(screen.getByLabelText("Observaciones")).toBeTruthy();
    const form = guardar.closest("form")!;
    expect(form.getAttribute("action")).toBe(NATIVO);
    expect((form.querySelector('[name="campos_a_subsanar"]') as HTMLInputElement).value).toBe("Localidad");
    const evento = new Event("submit", { bubbles: true, cancelable: true });
    form.dispatchEvent(evento);
    expect(evento.defaultPrevented).toBe(true);
    expect(await screen.findByText("Debe completar el campo de observaciones.")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Observaciones"), { target: { value: " Corregir " } });
    const valido = new Event("submit", { bubbles: true, cancelable: true });
    form.dispatchEvent(valido);
    expect(valido.defaultPrevented).toBe(false);
  });

  it("a 403 from the API is the access screen", async () => {
    serve({ detail: "denied" }, 403);
    setup();
    expect((await screen.findByRole("link", { name: "volver al inicio" })).getAttribute("href")).toBe("/inicio/");
  });
});
