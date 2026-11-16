import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { informeNative } from "./admisionesInformeDetalle";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
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
  webPost.mockReset();
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

  const generado = () => informe({ estado: "Docx generado", puede_cambiar_estado: false, archivos: { docx_descargar: "/media/b.docx", docx_editado_ver: null, pdf_final: null, borrador: { kind: "docx_final", url: "/media/b.docx" } } });

  it("the upload modal posts the DOCX to the G1 action and opens the redirect it answers", async () => {
    serve(generado());
    const navegar = vi.spyOn(informeNative, "navigate").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { success: true, messages: [], redirect: NATIVO } });
    setup();
    expect((await screen.findByRole("link", { name: /Descargar DOCX/ })).getAttribute("href")).toBe("/media/b.docx");
    expect(screen.getByRole("link", { name: /DOCX Final/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Subir DOCX Editado/ }));
    const boton = screen.getByRole("button", { name: "Subir Archivo" }) as HTMLButtonElement;
    expect(boton.name).toBe("subir_docx");
    const entrada = document.querySelector("#docx_editado") as HTMLInputElement;
    expect(entrada.required).toBe(true);
    const archivo = new File(["PK"], "editado.docx");
    fireEvent.change(entrada, { target: { files: [archivo] } });
    fireEvent.submit(boton.closest("form")!);
    await waitFor(() => expect(navegar).toHaveBeenCalledWith(NATIVO));
    expect(webPost).toHaveBeenCalledTimes(1);
    const [url, cuerpo] = webPost.mock.calls[0];
    expect(url).toBe("web/comedores/admisiones/informes/base/5/docx-editado/");
    expect((cuerpo as FormData).get("docx_editado")).toBe(archivo);
    navegar.mockRestore();
  });

  it("a rejected upload still opens the page where the error message waits, and a 403 is the shared access screen", async () => {
    serve(generado());
    const navegar = vi.spyOn(informeNative, "navigate").mockImplementation(() => undefined);
    webPost.mockResolvedValueOnce({ status: 400, data: { success: false, messages: [{ message: "x", level: "error" }], redirect: NATIVO } });
    setup();
    fireEvent.click(await screen.findByRole("button", { name: /Subir DOCX Editado/ }));
    fireEvent.submit(screen.getByRole("button", { name: "Subir Archivo" }).closest("form")!);
    await waitFor(() => expect(navegar).toHaveBeenCalledWith(NATIVO));
    expect(navegar).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(document, { key: "Escape" });
    webPost.mockResolvedValueOnce({ status: 403, data: { success: false, messages: [] } });
    fireEvent.click(screen.getByRole("button", { name: /Subir DOCX Editado/ }));
    fireEvent.submit(screen.getByRole("button", { name: "Subir Archivo" }).closest("form")!);
    expect((await screen.findByRole("link", { name: "volver al inicio" })).getAttribute("href")).toBe("/inicio/");
    expect(navegar).toHaveBeenCalledTimes(1);
    navegar.mockRestore();
  });

  it("a server failure of the review is the error screen", async () => {
    serve(informe());
    webPost.mockResolvedValueOnce({ status: 500, data: {} });
    setup();
    fireEvent.click(await screen.findByText("Cambiar estado"));
    fireEvent.change(screen.getByLabelText("Nuevo estado"), { target: { value: "Validado" } });
    fireEvent.submit(screen.getByRole("button", { name: "Guardar" }).closest("form")!);
    expect(await screen.findByText("No se pudo cargar la página.")).toBeTruthy();
  });

  it("the status modal needs a checked field and observations to fix, like the native script, and posts the review", async () => {
    serve(informe());
    const navegar = vi.spyOn(informeNative, "navigate").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { success: true, messages: [], redirect: "/comedores/admision/3/tecnicos/editar/" } });
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
    fireEvent.submit(form);
    expect(await screen.findByText("Debe completar el campo de observaciones.")).toBeTruthy();
    expect(webPost).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Observaciones"), { target: { value: " Corregir " } });
    fireEvent.submit(form);
    await waitFor(() => expect(navegar).toHaveBeenCalledWith("/comedores/admision/3/tecnicos/editar/"));
    expect(webPost).toHaveBeenCalledWith("web/comedores/admisiones/informes/base/5/revision/",
      { estado: "A subsanar", observacion: " Corregir ", campos_a_subsanar: ["Localidad"] }, expect.anything());
    navegar.mockRestore();
  });

  it("validating posts only the state", async () => {
    serve(informe());
    const navegar = vi.spyOn(informeNative, "navigate").mockImplementation(() => undefined);
    webPost.mockResolvedValue({ status: 200, data: { success: true, messages: [], redirect: "/comedores/admision/3/tecnicos/editar/" } });
    setup();
    fireEvent.click(await screen.findByText("Cambiar estado"));
    fireEvent.change(screen.getByLabelText("Nuevo estado"), { target: { value: "Validado" } });
    fireEvent.submit(screen.getByRole("button", { name: "Guardar" }).closest("form")!);
    await waitFor(() => expect(navegar).toHaveBeenCalled());
    expect(webPost).toHaveBeenCalledWith("web/comedores/admisiones/informes/base/5/revision/", { estado: "Validado" }, expect.anything());
    navegar.mockRestore();
  });

  it("a 403 from the API is the access screen", async () => {
    serve({ detail: "denied" }, 403);
    setup();
    expect((await screen.findByRole("link", { name: "volver al inicio" })).getAttribute("href")).toBe("/inicio/");
  });
});
