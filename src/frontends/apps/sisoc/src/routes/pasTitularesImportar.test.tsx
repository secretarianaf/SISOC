import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import { findRoute } from "./index";
import { readyContext, setViewport } from "./testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const page = {
  breadcrumb: [{ text: "PAS", url: "/pas/listar" }, { text: "Importar titulares", url: null }],
  archivo: { label: "Archivo CSV", accept: ".csv" },
};

function serve(data: unknown = page, status = 200) {
  webGet.mockImplementation((url: string) => Promise.resolve(url === "web/session/"
    ? { data: readyContext, status: 200 } : { data, status }));
}
async function open() {
  window.history.replaceState({}, "", "/pas/titulares/importar");
  render(<App />);
  return screen.findByRole("heading", { level: 1, name: "Importar titulares" });
}
const choose = (name = "titulares.csv") => {
  const file = new File(["Apellidos;Nombres\n"], name, { type: "text/csv" });
  fireEvent.change(document.getElementById("id_archivo")!, { target: { files: [file] } });
  return file;
};
const submit = () => fireEvent.submit(document.getElementById("id_archivo")!.closest("form")!);

beforeEach(() => {
  vi.clearAllMocks();
  document.body.className = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary dark-mode";
  setViewport(false);
  window.scrollTo = vi.fn();
});
afterEach(() => cleanup());

describe("PAS titulares import", () => {
  it("owns exactly the native URL", () => {
    expect(findRoute("/pas/titulares/importar")?.route.name).toBe("pas-titulares-importar");
    for (const other of ["/pas/titulares/importar/", "/pas/titulares", "/pas/crear", "/pas/ddjj/tokens/exportar"]) {
      expect(findRoute(other)?.route.name).not.toBe("pas-titulares-importar");
    }
  });

  it("prints the native header, explanation, field and button", async () => {
    serve();
    await open();
    await waitFor(() => expect(document.title).toContain("Importar titulares PAS"));
    expect(screen.getByText("Programa de Acompañamiento Social").className).toBe("pas-eyebrow");
    expect(screen.getByText("Carga incremental")).toBeTruthy();
    expect(screen.getByRole("heading", { level: 2, name: "Archivo CSV" })).toBeTruthy();
    const explanation = document.querySelector(".pas-search-panel > p")!;
    expect(explanation.textContent).toContain("Columnas obligatorias: Apellidos/Apellido, Nombres/Nombre, DNI, CUIT, Provincia y Municipio.");
    expect(explanation.textContent).toContain("UltimoEstadoPas, se asigna el estado Activo.");
    const input = screen.getByLabelText("Archivo CSV") as HTMLInputElement;
    expect(input.accept).toBe(".csv");
    expect(input.required).toBe(true);
    expect(input.className).toBe("form-control");
    expect(screen.getByRole("button", { name: "Importar titulares" }).className).toBe("btn btn-primary");
    expect(document.querySelector(".breadcrumb-item.active")?.textContent).toBe("Importar titulares");
    expect(document.querySelector('.breadcrumb a[href="/pas/listar"]')?.textContent).toBe("PAS");
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("posts the multipart file and prints the summary with the error list and a fresh form", async () => {
    serve();
    webPost.mockResolvedValue({
      status: 200,
      data: { resultado: { total: 3, creados: 1, duplicados: 1, errores: ["Fila 4: DNI y CUIT deben contener números."] } },
    });
    await open();
    const file = choose();
    submit();
    const summary = await screen.findByRole("status");
    expect(summary.textContent).toBe("Procesados: 3 · Nuevos: 1 · Duplicados omitidos: 1 · Errores: 1");
    expect(summary.className).toBe("alert alert-info mt-4");
    expect(document.querySelector("ul.alert.alert-warning li")?.textContent).toBe("Fila 4: DNI y CUIT deben contener números.");
    const [url, body] = webPost.mock.calls[0];
    expect(url).toBe("web/pas/titulares/importar/");
    expect((body as FormData).get("archivo")).toBe(file);
    expect((document.getElementById("id_archivo") as HTMLInputElement).files).toHaveLength(0);
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("omits the warning list when no row failed", async () => {
    serve();
    webPost.mockResolvedValue({ status: 200, data: { resultado: { total: 1, creados: 1, duplicados: 0, errores: [] } } });
    await open();
    choose();
    submit();
    await screen.findByRole("status");
    expect(document.querySelector("ul.alert-warning")).toBeNull();
  });

  it("shows the exact rejection under the field and drops a previous summary", async () => {
    serve();
    webPost.mockResolvedValueOnce({ status: 200, data: { resultado: { total: 1, creados: 1, duplicados: 0, errores: [] } } });
    webPost.mockResolvedValueOnce({ status: 400, data: { errors: { archivo: ["Faltan columnas obligatorias: DNI, CUIT."] } } });
    await open();
    choose();
    submit();
    await screen.findByRole("status");
    choose();
    submit();
    const error = await screen.findByText("Faltan columnas obligatorias: DNI, CUIT.");
    expect(error.className).toBe("text-danger mt-2");
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("does not post without a file and ignores a second submit while one runs", async () => {
    serve();
    let release: (value: unknown) => void = () => undefined;
    webPost.mockReturnValue(new Promise((resolve) => { release = resolve; }));
    await open();
    submit();
    expect(webPost).not.toHaveBeenCalled();
    choose();
    submit();
    submit();
    expect(webPost).toHaveBeenCalledTimes(1);
    expect((screen.getByRole("button", { name: "Importar titulares" }) as HTMLButtonElement).disabled).toBe(true);
    release({ status: 200, data: { resultado: { total: 0, creados: 0, duplicados: 0, errores: [] } } });
    await screen.findByRole("status");
  });

  it("reports an unconfirmed result without retrying", async () => {
    serve();
    webPost.mockRejectedValue(new Error("timeout"));
    await open();
    choose();
    submit();
    expect((await screen.findByRole("alert")).textContent).toBe("No se pudo confirmar el resultado. Verificá el estado antes de reintentar.");
    expect(webPost).toHaveBeenCalledTimes(1);
  });

  it("shows the access screen when the read or the post is forbidden", async () => {
    serve({ detail: "denied" }, 403);
    window.history.replaceState({}, "", "/pas/titulares/importar");
    render(<App />);
    await waitFor(() => expect(screen.queryByText("Cargando importación…")).toBeNull());
    expect(screen.queryByLabelText("Archivo CSV")).toBeNull();
    cleanup();

    serve();
    webPost.mockResolvedValue({ status: 403, data: { detail: "denied" } });
    await open();
    choose();
    submit();
    await waitFor(() => expect(screen.queryByLabelText("Archivo CSV")).toBeNull());
    expect(screen.queryByRole("status")).toBeNull();
  });
});
