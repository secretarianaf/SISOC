import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import InsumosForm from "./InsumosForm";
import { SinPermiso } from "@sisoc/api";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get, post })),
  SinPermiso: class SinPermiso extends Error {},
}));

const metadata = {
  initial: { programa: "1", categoria: "11", titulo: "Manual sintético", descripcion: "Descripción", activo: true },
  options: {
    programa: [{ value: "", label: "---------" }, { value: "1", label: "Programa A" }, { value: "2", label: "Programa B" }],
    categoria: [{ value: "", label: "Sin categoría" }, { value: "11", label: "Categoría A", programa_id: "1" }, { value: "21", label: "Categoría B", programa_id: "2" }],
  },
  current_file: { name: "manual.pdf", download_url: "/insumos/7/descargar" },
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Insumos React mutation journey", () => {
  it.each(["crear", "editar"] as const)("clears the rejected new file without changing %s text values or resubmitting it", async (action) => {
    get.mockResolvedValueOnce({ data: { ...metadata, current_file: action === "editar" ? metadata.current_file : null } });
    post.mockRejectedValue({ response: { status: 400, data: { errors: { titulo: [{ message: "Este campo es obligatorio.", code: "required" }] } } } });
    const onComplete = vi.fn();
    render(<InsumosForm action={action} id={action === "editar" ? "7" : undefined} onComplete={onComplete} onCancel={vi.fn()} />);
    const upload = await screen.findByLabelText(/Archivo/);
    const selectedFile = new File(["synthetic"], "nuevo.pdf", { type: "application/pdf" });
    fireEvent.change(upload, { target: { files: [selectedFile] } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar insumo" }));
    await screen.findByText("Este campo es obligatorio.");
    expect(post).toHaveBeenCalledOnce();
    expect(post.mock.calls[0][1].get("archivo")).toBe(selectedFile);
    expect((screen.getByLabelText(/Título/) as HTMLInputElement).value).toBe("Manual sintético");
    if (action === "editar") expect(screen.getAllByRole("link", { name: "manual.pdf" })).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Guardar insumo" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect(post.mock.calls[1][1].has("archivo")).toBe(false);
    expect(onComplete).not.toHaveBeenCalled();
  });

  it.each(["crear", "editar"] as const)("returns to the page top after committed %s validation errors", async (action) => {
    get.mockResolvedValueOnce({ data: metadata });
    let reject!: (error: unknown) => void;
    post.mockReturnValueOnce(new Promise((_resolve, fail) => { reject = fail; }));
    const onComplete = vi.fn();
    render(<InsumosForm action={action} id={action === "editar" ? "7" : undefined} onComplete={onComplete} onCancel={vi.fn()} />);
    await screen.findByRole("button", { name: "Guardar insumo" });
    expect(window.scrollTo).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Guardar insumo" }));
    expect(window.scrollTo).not.toHaveBeenCalled();
    await act(async () => reject({ response: { status: 400, data: { errors: { titulo: [{ message: "Este campo es obligatorio.", code: "required" }] } } } }));
    expect(screen.getByText("Este campo es obligatorio.")).toBeDefined();
    expect(window.scrollTo).toHaveBeenCalledExactlyOnceWith({ top: 0, left: 0, behavior: "instant" });
    expect((screen.getByLabelText(/Título/) as HTMLInputElement).value).toBe("Manual sintético");
    expect(post).toHaveBeenCalledOnce();
    expect(onComplete).not.toHaveBeenCalled();
  });

  it("loads edit metadata and submits multipart without replacing the current file", async () => {
    get.mockResolvedValueOnce({ data: metadata });
    post.mockResolvedValueOnce({ data: { ok: true, message: "Insumo actualizado correctamente.", redirect: "/insumos/" } });
    const onComplete = vi.fn();
    render(<InsumosForm action="editar" id="7" onComplete={onComplete} onCancel={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Editar insumo" })).toBeDefined();
    const currentLinks = screen.getAllByRole("link", { name: "manual.pdf" });
    expect(currentLinks).toHaveLength(2);
    expect(currentLinks.every((link) => link.getAttribute("href") === "/insumos/7/descargar")).toBe(true);
    expect(screen.getByText("Actualmente")).toBeDefined();
    expect(document.querySelector('a[href^="/media/"]')).toBeNull();
    fireEvent.change(screen.getByLabelText(/Título/), { target: { value: "Manual actualizado" } });
    fireEvent.click(screen.getByLabelText("Activo"));
    fireEvent.click(screen.getByRole("button", { name: "Guardar insumo" }));
    await waitFor(() => expect(onComplete).toHaveBeenCalledWith("Insumo actualizado correctamente."));
    expect(get).toHaveBeenCalledWith("web/insumos/7/editar/", expect.objectContaining({ signal: expect.any(AbortSignal) }));
    const [url, body] = post.mock.calls[0];
    expect(url).toBe("web/insumos/7/editar/");
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("titulo")).toBe("Manual actualizado");
    expect(body.has("archivo")).toBe(false);
    expect(body.has("activo")).toBe(false);
  });

  it("withholds the previous record and ignores its late mutation after a route change", async () => {
    let finish!: (value: unknown) => void;
    get.mockResolvedValueOnce({ data: metadata }).mockReturnValueOnce(new Promise(() => {}));
    post.mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }));
    const onComplete = vi.fn();
    const view = render(<InsumosForm action="editar" id="7" onComplete={onComplete} onCancel={vi.fn()} />);
    await screen.findByRole("heading", { name: "Editar insumo" });
    fireEvent.click(screen.getByRole("button", { name: "Guardar insumo" }));
    view.rerender(<InsumosForm action="editar" id="8" onComplete={onComplete} onCancel={vi.fn()} />);
    expect(screen.queryByDisplayValue("Manual sintético")).toBeNull();
    finish({ data: { ok: true, message: "Respuesta anterior", redirect: "/insumos/" } });
    await waitFor(() => expect(screen.getByRole("status")).toBeDefined());
    expect(onComplete).not.toHaveBeenCalled();
  });

  it("loads a delete confirmation without mutating and cancels without POST", async () => {
    get.mockResolvedValueOnce({ data: { id: 7, titulo: "Manual sintético" } });
    const onCancel = vi.fn();
    render(<InsumosForm action="eliminar" id="7" onComplete={vi.fn()} onCancel={onCancel} />);
    await screen.findByRole("heading", { name: "Confirmar eliminación" });
    expect(screen.getByText("Manual sintético")).toBeDefined();
    expect(post).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("link", { name: "Cancelar" }));
    expect(onCancel).toHaveBeenCalledOnce();
    expect(post).not.toHaveBeenCalled();
  });

  it("creates with the selected file and filters categories when the program changes", async () => {
    get.mockResolvedValueOnce({ data: { ...metadata, current_file: null } });
    post.mockResolvedValueOnce({ data: { ok: true, message: "Insumo creado correctamente.", redirect: "/insumos/" } });
    const onComplete = vi.fn();
    render(<InsumosForm action="crear" onComplete={onComplete} onCancel={vi.fn()} />);
    const programa = await screen.findByLabelText(/Programa/);
    expect(screen.queryByRole("option", { name: "Categoría B" })).toBeNull();
    fireEvent.change(programa, { target: { value: "2" } });
    expect((screen.getByLabelText("Categoría") as HTMLSelectElement).value).toBe("");
    expect(screen.queryByRole("option", { name: "Categoría A" })).toBeNull();
    fireEvent.change(screen.getByLabelText("Categoría"), { target: { value: "21" } });
    const file = new File(["synthetic"], "nuevo.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText(/Archivo/), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar insumo" }));
    await waitFor(() => expect(onComplete).toHaveBeenCalledWith("Insumo creado correctamente."));
    const [url, body] = post.mock.calls[0];
    expect(url).toBe("web/insumos/crear/");
    expect(body.get("archivo")).toBe(file);
    expect(body.get("categoria")).toBe("21");
    expect(body.get("activo")).toBe("on");
  });

  it("shows server field errors without losing values or automatically resubmitting", async () => {
    get.mockResolvedValueOnce({ data: metadata });
    post.mockRejectedValueOnce({ response: { status: 400, data: { errors: { titulo: [{ message: "Este campo es obligatorio.", code: "required" }] } } } });
    render(<InsumosForm action="editar" id="7" onComplete={vi.fn()} onCancel={vi.fn()} />);
    await screen.findByRole("heading", { name: "Editar insumo" });
    fireEvent.click(screen.getByRole("button", { name: "Guardar insumo" }));
    await screen.findByText("Este campo es obligatorio.");
    expect(screen.getByText("Este campo es obligatorio.").tagName).toBe("STRONG");
    expect(screen.getByLabelText(/Título/).getAttribute("aria-invalid")).toBe("true");
    expect((screen.getByLabelText(/Título/) as HTMLInputElement).value).toBe("Manual sintético");
    expect(post).toHaveBeenCalledOnce();
    expect((screen.getByRole("button", { name: "Guardar insumo" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("prevents duplicate delete submissions and does not retry an unknown outcome", async () => {
    let reject!: (error: unknown) => void;
    get.mockResolvedValueOnce({ data: { id: 7, titulo: "Manual sintético" } });
    post.mockReturnValueOnce(new Promise((_resolve, fail) => { reject = fail; }));
    const onCancel = vi.fn();
    render(<InsumosForm action="eliminar" id="7" onComplete={vi.fn()} onCancel={onCancel} />);
    const button = await screen.findByRole("button", { name: "Eliminar" });
    const form = button.closest("form")!;
    fireEvent.submit(form);
    fireEvent.submit(form);
    fireEvent.click(screen.getByRole("link", { name: "Cancelar" }));
    expect(onCancel).not.toHaveBeenCalled();
    expect(post).toHaveBeenCalledExactlyOnceWith("web/insumos/7/eliminar/", undefined, expect.objectContaining({
      validateStatus: expect.any(Function),
    }));
    reject(new Error("Connection lost after send"));
    await screen.findByRole("alert");
    expect((button as HTMLButtonElement).disabled).toBe(true);
    fireEvent.submit(form);
    expect(post).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByRole("link", { name: "Cancelar" }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("completes delete only after an acknowledged server response", async () => {
    get.mockResolvedValueOnce({ data: { id: 7, titulo: "Manual sintético" } });
    post.mockResolvedValueOnce({ data: { ok: true, message: "Insumo eliminado correctamente.", redirect: "/insumos/" } });
    const onComplete = vi.fn();
    render(<InsumosForm action="eliminar" id="7" onComplete={onComplete} onCancel={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));
    await waitFor(() => expect(onComplete).toHaveBeenCalledWith("Insumo eliminado correctamente."));
  });

  it("fails closed on rejected access and on malformed external download metadata", async () => {
    get.mockRejectedValueOnce(new SinPermiso("No tiene permisos para esta operación."));
    const view = render(<InsumosForm action="editar" id="7" onComplete={vi.fn()} onCancel={vi.fn()} />);
    expect(await screen.findByRole("heading", { name: "¡Ups! Algo salió mal." })).toBeDefined();
    expect(screen.getByText(/No tiene permisos suficientes para realizar la acción/)).toBeDefined();
    expect(screen.queryByRole("button", { name: "Guardar insumo" })).toBeNull();
    view.unmount();
    get.mockResolvedValueOnce({ data: { ...metadata, current_file: { name: "manual.pdf", download_url: "https://example.invalid/file" } } });
    render(<InsumosForm action="editar" id="7" onComplete={vi.fn()} onCancel={vi.fn()} />);
    await screen.findByRole("alert");
    expect(screen.queryByRole("link", { name: "manual.pdf" })).toBeNull();
    expect(post).not.toHaveBeenCalled();
  });

  it("shows the source permission page after a mutation 403 without claiming success or retrying", async () => {
    get.mockResolvedValueOnce({ data: metadata });
    post.mockResolvedValueOnce({ status: 403, data: "<html>private server response</html>" });
    const onComplete = vi.fn();
    render(<InsumosForm action="editar" id="7" onComplete={onComplete} onCancel={vi.fn()} />);
    await screen.findByRole("heading", { name: "Editar insumo" });

    fireEvent.click(screen.getByRole("button", { name: "Guardar insumo" }));
    expect(await screen.findByRole("heading", { name: "¡Ups! Algo salió mal." })).toBeDefined();
    expect(screen.getByText(/No tiene permisos suficientes para realizar la acción/)).toBeDefined();
    expect(screen.queryByText("private server response")).toBeNull();
    expect(screen.queryByRole("button", { name: "Guardar insumo" })).toBeNull();
    expect(onComplete).not.toHaveBeenCalled();
    expect(post).toHaveBeenCalledOnce();
    expect(post).toHaveBeenCalledWith("web/insumos/7/editar/", expect.any(FormData), expect.objectContaining({
      validateStatus: expect.any(Function),
    }));
    const config = post.mock.calls[0][2];
    expect(config.validateStatus(403)).toBe(true);
    expect(config.validateStatus(401)).toBe(false);
    expect(config.validateStatus(500)).toBe(false);
  });

  it("preserves the prerequisite in a mutation 403 without reporting success or retrying", async () => {
    get.mockResolvedValueOnce({ data: metadata });
    post.mockResolvedValueOnce({
      status: 403,
      data: {
        detail: "Debe completar el requisito de acceso web.",
        state: "profile_confirmation_required",
        required_action_url: "/mi-cuenta/confirmar/",
      },
    });
    const onComplete = vi.fn();
    render(<InsumosForm action="editar" id="7" onComplete={onComplete} onCancel={vi.fn()} />);
    await screen.findByRole("heading", { name: "Editar insumo" });

    fireEvent.click(screen.getByRole("button", { name: "Guardar insumo" }));
    expect(await screen.findByRole("heading", { name: "Antes de continuar" })).toBeDefined();
    expect(screen.getByText("Necesitás confirmar tu perfil para continuar.")).toBeDefined();
    expect(screen.getByRole("link", { name: "Continuar en SISOC" }).getAttribute("href"))
      .toBe("/mi-cuenta/confirmar/");
    expect(screen.queryByRole("button", { name: "Guardar insumo" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "¡Ups! Algo salió mal." })).toBeNull();
    expect(onComplete).not.toHaveBeenCalled();
    expect(post).toHaveBeenCalledOnce();
  });

  it("ignores a prerequisite denial returned after the form was unmounted", async () => {
    get.mockResolvedValueOnce({ data: metadata });
    let resolvePost!: (value: { status: number; data: unknown }) => void;
    post.mockReturnValueOnce(new Promise((resolve) => { resolvePost = resolve; }));
    const onComplete = vi.fn();
    const view = render(<InsumosForm action="editar" id="7" onComplete={onComplete} onCancel={vi.fn()} />);
    await screen.findByRole("heading", { name: "Editar insumo" });

    fireEvent.click(screen.getByRole("button", { name: "Guardar insumo" }));
    view.unmount();
    await act(async () => resolvePost({
      status: 403,
      data: {
        detail: "Debe completar el requisito de acceso web.",
        state: "profile_confirmation_required",
        required_action_url: "/mi-cuenta/confirmar/",
      },
    }));

    expect(onComplete).not.toHaveBeenCalled();
    expect(post).toHaveBeenCalledOnce();
  });

  it("does not expose a download link when edit permission does not include view", async () => {
    get.mockResolvedValueOnce({ data: { ...metadata, current_file: { name: "manual.pdf", download_url: null } } });
    render(<InsumosForm action="editar" id="7" onComplete={vi.fn()} onCancel={vi.fn()} />);
    await screen.findByRole("heading", { name: "Editar insumo" });
    expect(screen.queryByRole("link", { name: "manual.pdf" })).toBeNull();
    expect(screen.getAllByText(/manual\.pdf/)).toHaveLength(2);
  });
});
