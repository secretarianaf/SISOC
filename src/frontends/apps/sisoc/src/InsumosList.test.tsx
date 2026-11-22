import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import InsumosList from "./InsumosList";

const { webGet } = vi.hoisted(() => ({ webGet: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet })),
  mensajeDeError: vi.fn((error: { response?: { data?: { detail?: string } } }) =>
    error.response?.data?.detail ?? "Error de prueba",
  ),
  SinPermiso: class SinPermiso extends Error {},
}));

const options = { categories: [{ id: 4, nombre: "Manuales A" }] };
const page = {
  count: 25,
  page: 2,
  page_size: 20,
  pages: 2,
  filters: { busqueda: "Manual", categoria: "sin" },
  results: [
    {
      id: 9,
      titulo: "Manual de prueba 24",
      activo: false,
      categoria: "Sin categoría",
      fecha_carga: "26/10/2026 00:24",
      cargado_por: "Prueba Insumos Gestión",
      download_url: "/insumos/9/descargar",
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  window.history.replaceState({}, "", "/v2/sisoc/insumos/?busqueda=Manual&categoria=sin&page=2");
  webGet.mockImplementation((path: string) =>
    Promise.resolve({ data: path === "web/insumos/options/" ? options : page }),
  );
});

afterEach(() => {
  cleanup();
});

describe("Insumos list", () => {
  it("loads the legacy list-only stylesheet only while the list is mounted", async () => {
    const view = render(<InsumosList showManagement showCategories />);
    await screen.findByRole("table");
    const listStyles = document.querySelector('link[href="/static/custom/css/listModerno.css"]');
    expect(listStyles).not.toBeNull();
    expect(listStyles?.nextElementSibling?.getAttribute("href")).toBe("/static/custom/css/poncho_listados.css");
    view.unmount();
    expect(document.querySelector('link[href="/static/custom/css/listModerno.css"]')).toBeNull();
    expect(document.querySelector('link[href="/static/custom/css/poncho_listados.css"]')).toBeNull();
  });
  it("reflects horizontal scroll edges with the legacy two-pixel rounding margin", async () => {
    render(<InsumosList showManagement showCategories />);
    const table = await screen.findByRole("table");
    const container = table.parentElement;
    if (!container) throw new Error("Expected the scroll container");
    Object.defineProperties(container, {
      clientWidth: { configurable: true, value: 300 },
      scrollWidth: { configurable: true, value: 900 },
      scrollLeft: { configurable: true, writable: true, value: 0 },
    });

    fireEvent.resize(window);
    await waitFor(() => expect(container.classList.contains("poncho-scroll--der")).toBe(true));
    expect(container.classList.contains("poncho-scroll--izq")).toBe(false);
    expect(container.closest(".card-body")?.classList.contains("poncho-scroll")).toBe(true);
    container.scrollLeft = 100;
    fireEvent.scroll(container);
    expect(container.classList.contains("poncho-scroll--izq")).toBe(true);
    expect(container.classList.contains("poncho-scroll--der")).toBe(true);
    container.scrollLeft = 600;
    fireEvent.scroll(container);
    expect(container.classList.contains("poncho-scroll--der")).toBe(false);
    Object.defineProperty(container, "scrollWidth", { configurable: true, value: 301 });
    fireEvent.resize(window);
    expect(container.classList.contains("poncho-scroll--izq")).toBe(false);
    expect(container.classList.contains("poncho-scroll--der")).toBe(false);
  });

  it("places actions after search and category controls, matching the legacy search component", async () => {
    webGet.mockImplementation((path: string) =>
      Promise.resolve({ data: path === "web/insumos/options/" ? options : { ...page, count: 1, page: 1, pages: 1, filters: { busqueda: "", categoria: "" } } }),
    );
    window.history.replaceState({}, "", "/v2/sisoc/insumos/");
    render(<InsumosList showManagement showCategories />);

    await screen.findByText(page.results[0].titulo);
    const form = document.querySelector("#insumos-search-form")!;
    const actions = document.querySelector(".search-actions")!;
    const category = document.querySelector(".poncho-filtros-modulo")!;
    expect(form.compareDocumentPosition(actions) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(actions.compareDocumentPosition(category) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("does not render a result count for the legacy empty state", async () => {
    webGet.mockImplementation((path: string) =>
      Promise.resolve({ data: path === "web/insumos/options/" ? options : { ...page, count: 0, page: 1, pages: 0, filters: { busqueda: "", categoria: "" }, results: [] } }),
    );
    window.history.replaceState({}, "", "/v2/sisoc/insumos/");
    render(<InsumosList showManagement showCategories />);

    await screen.findByText("No se encontraron insumos");
    expect(screen.queryByText("Se encontraron 0 resultados")).toBeNull();
    expect(document.querySelector(".list-container > .mt-2")).not.toBeNull();
  });

  it("renders the server page and keeps download on the protected Django route", async () => {
    render(<InsumosList showManagement showCategories />);

    expect(await screen.findByRole("heading", { name: "Buscar insumos" })).toBeDefined();
    expect(screen.getByRole("searchbox", { name: "Buscar por título o descripción" })).toBeDefined();
    expect(screen.getByText("Manual de prueba 24")).toBeDefined();
    expect(screen.getByText("Manual de prueba 24").closest("td")?.textContent).toBe(
      "Manual de prueba 24 Inactivo",
    );
    expect(screen.getByText("Inactivo")).toBeDefined();
    expect(screen.getByText("26/10/2026 00:24")).toBeDefined();
    expect(screen.getAllByText("Sin categoría")).toHaveLength(2);
    expect(screen.getByText("Prueba Insumos Gestión")).toBeDefined();
    expect(screen.getByRole("link", { name: "Descargar" }).getAttribute("href")).toBe(
      "/insumos/9/descargar",
    );
    expect(screen.getByRole("link", { name: /Agregar insumo/ }).className).toContain("poncho-btn--cta");
    expect(screen.getByRole("link", { name: "Editar" }).getAttribute("href")).toBe(
      "/v2/sisoc/insumos/9/editar/",
    );
    expect(screen.getByRole("link", { name: "Eliminar" }).getAttribute("href")).toBe(
      "/v2/sisoc/insumos/9/eliminar/",
    );
    expect(screen.getByText("Se encontraron 25 resultados")).toBeDefined();
    expect(webGet).toHaveBeenCalledWith("web/insumos/options/", expect.any(Object));
    expect(webGet).toHaveBeenCalledWith(
      "web/insumos/",
      expect.objectContaining({ params: { busqueda: "Manual", categoria: "sin", page: "2" } }),
    );
  });

  it("submits trimmed search and category filters and resets them without a page number", async () => {
    window.history.replaceState({}, "", "/v2/sisoc/insumos/?page=4");
    render(<InsumosList showManagement={false} showCategories={false} />);

    await screen.findByText("Manual de prueba 24");
    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar por título o descripción" }), {
      target: { value: "  mapa  " },
    });
    fireEvent.change(screen.getByLabelText("Categoría"), { target: { value: "4" } });
    fireEvent.click(screen.getByRole("button", { name: "Buscar" }));

    await waitFor(() =>
      expect(window.location.search).toBe("?busqueda=mapa&categoria=4"),
    );
    await waitFor(() =>
      expect(webGet).toHaveBeenCalledWith(
        "web/insumos/",
        expect.objectContaining({ params: { busqueda: "mapa", categoria: "4" } }),
      ),
    );

    fireEvent.click(screen.getByRole("link", { name: "Resetear" }));
    await waitFor(() => expect(window.location.pathname + window.location.search).toBe("/v2/sisoc/insumos/"));
    await waitFor(() =>
      expect(webGet).toHaveBeenLastCalledWith(
        "web/insumos/",
        expect.objectContaining({ params: {} }),
      ),
    );
  });

  it("renders the legacy empty state without exposing pagination controls", async () => {
    webGet.mockImplementation((path: string) =>
      Promise.resolve({
        data:
          path === "web/insumos/options/"
            ? options
            : { ...page, count: 0, page: 1, pages: 0, results: [] },
      }),
    );
    render(<InsumosList showManagement={false} showCategories={false} />);

    expect(await screen.findByRole("heading", { name: "No se encontraron insumos" })).toBeDefined();
    expect(screen.getByText("No hay insumos que coincidan con los criterios de búsqueda.")).toBeDefined();
    expect(screen.queryByRole("link", { name: "Continuar" })).toBeNull();
  });

  it("keeps filters while navigating pages and does not expose management actions without capability", async () => {
    render(<InsumosList showManagement={false} showCategories={false} />);
    await screen.findByText("Manual de prueba 24");

    expect(screen.queryByRole("link", { name: "Editar" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Eliminar" })).toBeNull();
    const firstPage = screen.getByRole("link", { name: "1" });
    expect(firstPage.getAttribute("href")).toBe(
      "/v2/sisoc/insumos/?busqueda=Manual&categoria=sin&page=1",
    );
    fireEvent.click(firstPage);

    await waitFor(() =>
      expect(window.location.search).toBe("?busqueda=Manual&categoria=sin&page=1"),
    );
    await waitFor(() =>
      expect(webGet).toHaveBeenLastCalledWith(
        "web/insumos/",
        expect.objectContaining({ params: { busqueda: "Manual", categoria: "sin" } }),
      ),
    );
  });

  it("retains an inactive selected category in the request while matching the legacy blank option", async () => {
    window.history.replaceState({}, "", "/v2/sisoc/insumos/?categoria=999");
    render(<InsumosList showManagement={false} showCategories={false} />);

    await screen.findByText("Manual de prueba 24");
    expect((screen.getByLabelText("Categoría") as HTMLSelectElement).value).toBe("");
    expect(webGet).toHaveBeenCalledWith(
      "web/insumos/",
      expect.objectContaining({ params: { categoria: "999" } }),
    );
  });

  it("clears failed results and allows an explicit retry", async () => {
    webGet.mockImplementationOnce(() => Promise.resolve({ data: options }));
    webGet.mockRejectedValueOnce(new Error("offline"));
    render(<InsumosList showManagement={false} showCategories={false} />);

    expect(await screen.findByRole("alert")).toBeDefined();
    expect(screen.getByText("No se pudieron cargar los insumos.")).toBeDefined();
    expect(screen.queryByText("Manual de prueba 24")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Manual de prueba 24")).toBeDefined();
  });

  it("rejects a server-provided download URL that is not an internal path", async () => {
    const unsafePage = {
      ...page,
      results: [{ ...page.results[0], download_url: "https://example.invalid/file" }],
    };
    webGet.mockImplementation((path: string) =>
      Promise.resolve({ data: path === "web/insumos/options/" ? options : unsafePage }),
    );
    render(<InsumosList showManagement showCategories={false} />);

    expect(await screen.findByRole("alert")).toBeDefined();
    expect(screen.queryByRole("link", { name: "Descargar" })).toBeNull();
  });

  it("renders the source permission page for API 403 and hides list controls", async () => {
    webGet.mockImplementation((path: string) => Promise.resolve({
      status: path === "web/insumos/" ? 403 : 200,
      data: path === "web/insumos/" ? { detail: "No tiene permisos para esta acción." } : options,
    }));
    render(<InsumosList showManagement showCategories />);

    expect(await screen.findByRole("heading", { name: "¡Ups! Algo salió mal." })).toBeDefined();
    expect(screen.getByText(/No tiene permisos suficientes para realizar la acción/)).toBeDefined();
    expect(screen.getByRole("link", { name: "volver al inicio" }).getAttribute("href")).toBe("/inicio/");
    expect(screen.queryByText("No tiene permisos para esta acción.")).toBeNull();
    expect(screen.queryByRole("searchbox")).toBeNull();
    expect(screen.queryByRole("link", { name: "Agregar insumo" })).toBeNull();
    expect(webGet).toHaveBeenCalledWith("web/insumos/", expect.objectContaining({
      validateStatus: expect.any(Function),
    }));
    const config = webGet.mock.calls.find(([path]) => path === "web/insumos/")?.[1];
    expect(config.validateStatus(403)).toBe(true);
    expect(config.validateStatus(401)).toBe(false);
    expect(config.validateStatus(500)).toBe(false);
  });

  it("preserves the API prerequisite payload on a list 403 without exposing list actions", async () => {
    const access = {
      detail: "Debe completar el requisito de acceso web.",
      state: "password_change_required",
      required_action_url: "/password/first-change/",
    };
    webGet.mockImplementation((path: string) => Promise.resolve(path === "web/insumos/"
      ? { status: 403, data: access }
      : { status: 200, data: options }));
    render(<InsumosList showManagement showCategories />);

    expect(await screen.findByRole("heading", { name: "Antes de continuar" })).toBeDefined();
    expect(screen.getByText("Necesitás actualizar tu contraseña para continuar.")).toBeDefined();
    expect(screen.getByRole("link", { name: "Continuar en SISOC" }).getAttribute("href"))
      .toBe("/password/first-change/");
    expect(screen.queryByRole("searchbox")).toBeNull();
    expect(screen.queryByRole("link", { name: "Agregar insumo" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "¡Ups! Algo salió mal." })).toBeNull();
  });

  it("ignores a superseded response after the user changes the search", async () => {
    const pending: Array<(response: { data: unknown }) => void> = [];
    webGet.mockImplementation(
      () => new Promise((resolve) => pending.push(resolve as (response: { data: unknown }) => void)),
    );
    window.history.replaceState({}, "", "/v2/sisoc/insumos/");
    render(<InsumosList showManagement={false} showCategories={false} />);
    await waitFor(() => expect(pending).toHaveLength(2));

    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar por título o descripción" }), {
      target: { value: "nuevo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Buscar" }));
    await waitFor(() => expect(pending).toHaveLength(4));

    pending[2]({ data: options });
    pending[3]({
      data: {
        ...page,
        filters: { busqueda: "nuevo", categoria: "" },
        results: [{ ...page.results[0], titulo: "Resultado reciente" }],
      },
    });
    expect(await screen.findByText("Resultado reciente")).toBeDefined();

    pending[0]({ data: options });
    pending[1]({
      data: { ...page, results: [{ ...page.results[0], titulo: "Resultado obsoleto" }] },
    });
    await waitFor(() => expect(screen.queryByText("Resultado obsoleto")).toBeNull());
    expect(screen.getByText("Resultado reciente")).toBeDefined();
  });

  it("passes the special last-page value unchanged to the API", async () => {
    window.history.replaceState({}, "", "/v2/sisoc/insumos/?page=last");
    render(<InsumosList showManagement={false} showCategories={false} />);

    await screen.findByText("Manual de prueba 24");
    expect(webGet).toHaveBeenCalledWith(
      "web/insumos/",
      expect.objectContaining({ params: { page: "last" } }),
    );
  });

  it("passes invalid page input unchanged and displays the server 404 instead of page one", async () => {
    window.history.replaceState({}, "", "/v2/sisoc/insumos/?page=not-a-page");
    webGet.mockImplementation((path: string, config?: { params?: { page?: string } }) => {
      if (path === "web/insumos/options/") return Promise.resolve({ data: options });
      if (config?.params?.page === "not-a-page") {
        return Promise.reject({ response: { status: 404, data: { detail: "404 Not Found" } } });
      }
      return Promise.resolve({ data: page });
    });
    render(<InsumosList showManagement={false} showCategories={false} />);

    expect(await screen.findByText("404 Not Found")).toBeDefined();
    expect(webGet).toHaveBeenCalledWith(
      "web/insumos/",
      expect.objectContaining({ params: { page: "not-a-page" } }),
    );
    expect(screen.queryByText("Manual de prueba 24")).toBeNull();
  });

  it("selects the URL category when its asynchronous options arrive", async () => {
    window.history.replaceState({}, "", "/v2/sisoc/insumos/?categoria=4");
    let resolveOptions!: (response: { data: unknown }) => void;
    webGet.mockImplementation((path: string) =>
      path === "web/insumos/options/"
        ? new Promise((resolve) => {
            resolveOptions = resolve;
          })
        : Promise.resolve({ data: page }),
    );
    render(<InsumosList showManagement={false} showCategories={false} />);

    expect((screen.getByLabelText("Categoría") as HTMLSelectElement).value).toBe("");
    resolveOptions({ data: options });
    await waitFor(() =>
      expect((screen.getByLabelText("Categoría") as HTMLSelectElement).value).toBe("4"),
    );
  });
});
