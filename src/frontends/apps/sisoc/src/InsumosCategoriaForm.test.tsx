import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import InsumosCategoriaForm from "./InsumosCategoriaForm";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get, post })),
  SinPermiso: class SinPermiso extends Error {},
}));
const metadata = {
  initial: { programa: "1", nombre: "Manuales", descripcion: "Guías", orden: "2", activo: true },
  options: { programa: [{ value: "", label: "---------" }, { value: "1", label: "Programa A" }] },
  current_file: null,
};
beforeEach(() => { vi.resetAllMocks(); vi.spyOn(window, "scrollTo").mockImplementation(() => {}); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("INS-B complete category form", () => {
  it.each(["crear", "editar"] as const)("posts %s as URL-encoded fields and fixed return", async (action) => {
    get.mockResolvedValue({ data: metadata });
    post.mockResolvedValue({ data: { ok: true, message: "Categoría guardada.", redirect: "/insumos/categorias/" } });
    const complete = vi.fn();
    render(<InsumosCategoriaForm action={action} id="4" onComplete={complete} onCancel={vi.fn()} />);
    await screen.findByRole("button", { name: "Guardar categoría" });
    fireEvent.change(screen.getByLabelText(/Nombre/), { target: { value: "Actualizada" } });
    fireEvent.click(screen.getByLabelText("Activa"));
    fireEvent.click(screen.getByRole("button", { name: "Guardar categoría" }));
    await waitFor(() => expect(complete).toHaveBeenCalledWith("Categoría guardada."));
    const [url, body] = post.mock.calls[0];
    expect(url).toBe(action === "crear" ? "web/insumos/categorias/crear/" : "web/insumos/categorias/4/editar/");
    expect(body).toBeInstanceOf(URLSearchParams);
    expect(body.get("nombre")).toBe("Actualizada");
    expect(body.get("orden")).toBe("2");
    expect(body.has("activo")).toBe(false);
    expect(body.has("archivo")).toBe(false);
  });

  it("keeps invalid values and field feedback without claiming success", async () => {
    get.mockResolvedValue({ data: metadata });
    post.mockRejectedValue({ response: { status: 400, data: { errors: { nombre: [{ message: "Ya existe una categoría con ese nombre en el programa.", code: "" }] } } } });
    const complete = vi.fn();
    render(<InsumosCategoriaForm action="crear" onComplete={complete} onCancel={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Guardar categoría" }));
    expect(await screen.findByText("Ya existe una categoría con ese nombre en el programa.")).toBeDefined();
    expect((screen.getByLabelText(/Nombre/) as HTMLInputElement).value).toBe("Manuales");
    expect(screen.getByLabelText(/Nombre/).getAttribute("aria-invalid")).toBe("true");
    expect(complete).not.toHaveBeenCalled();
    expect(window.scrollTo).toHaveBeenCalled();
  });

  it("explains SET_NULL and cancels deletion without submitting", async () => {
    get.mockResolvedValue({ data: { id: 4, nombre: "Manuales" } });
    const cancel = vi.fn();
    render(<InsumosCategoriaForm action="eliminar" id="4" onComplete={vi.fn()} onCancel={cancel} />);
    await screen.findByRole("button", { name: "Eliminar" });
    expect(screen.getByText(/Los insumos asociados quedarán como/)).toBeDefined();
    fireEvent.click(screen.getByRole("link", { name: "Cancelar" }));
    expect(cancel).toHaveBeenCalledOnce();
    expect(post).not.toHaveBeenCalled();
  });

  it("does not retry an uncertain delete or follow an unexpected redirect", async () => {
    get.mockResolvedValue({ data: { id: 4, nombre: "Manuales" } });
    post.mockResolvedValue({ data: { ok: true, message: "Borrada", redirect: "https://example.invalid/" } });
    const complete = vi.fn();
    render(<InsumosCategoriaForm action="eliminar" id="4" onComplete={complete} onCancel={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));
    await screen.findByText(/No se pudo confirmar el resultado/);
    expect((screen.getByRole("button", { name: "Eliminar" }) as HTMLButtonElement).disabled).toBe(true);
    expect(post).toHaveBeenCalledOnce();
    expect(complete).not.toHaveBeenCalled();
  });

  it("ignores old metadata and mutation completion after navigation", async () => {
    get.mockResolvedValueOnce({ data: metadata }).mockReturnValueOnce(new Promise(() => {}));
    let finish!: (value: unknown) => void;
    post.mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }));
    const complete = vi.fn();
    const view = render(<InsumosCategoriaForm action="editar" id="4" onComplete={complete} onCancel={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Guardar categoría" }));
    view.rerender(<InsumosCategoriaForm action="editar" id="5" onComplete={complete} onCancel={vi.fn()} />);
    expect(screen.queryByDisplayValue("Manuales")).toBeNull();
    await act(async () => finish({ data: { ok: true, message: "Guardada", redirect: "/insumos/categorias/" } }));
    expect(complete).not.toHaveBeenCalled();
  });

  it("renders the existing prerequisite error rather than a category form", async () => {
    get.mockResolvedValue({ status: 403, data: { detail: "Complete el requisito", state: "password_change_required", required_action_url: "/password/first-change/" } });
    render(<InsumosCategoriaForm action="crear" onComplete={vi.fn()} onCancel={vi.fn()} />);
    expect(await screen.findByRole("link", { name: /Continuar/ })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Guardar categoría" })).toBeNull();
  });
});
