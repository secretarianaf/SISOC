import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "./App";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
  mensajeDeError: vi.fn(() => "Error de prueba"),
  SinPermiso: class SinPermiso extends Error {},
}));

const readyContext = {
  user: {
    username: "prueba.insumos",
    display_name: "Prueba Insumos Gestión",
    avatar_initial: "P",
    role_label: "Prueba local",
  },
  access: { state: "ready", required_action_url: null },
  navigation: [
    { id: "inicio", label: "Inicio", href: "/inicio/", children: [] },
    { id: "legajos", label: "Legajos", href: null, children: [] },
    { id: "comunicados", label: "Comunicados", href: "/comunicados/", children: [] },
    {
      id: "configuracion-comedores",
      label: "Configuración de Comedores",
      href: null,
      children: [
        { id: "insumos_listar", label: "Insumos", href: "/insumos/", children: [] },
      ],
    },
    { id: "mi_cuenta", label: "Mi cuenta", href: "/mi-cuenta/", children: [] },
  ],
  capabilities: {
    insumos: { can_view: true, show_management: true, show_categories: false },
  },
  footer_version_label: "Versión local de prueba",
};

function setViewport(isMobile: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      matches: isMobile && query.includes("max-width"),
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
    })),
  );
}

function setup(path = "/v2/sisoc/insumos/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.title = "SISOC - Insumos";
  setViewport(false);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("SISOC web shell", () => {
  it.each([
    ["/v2/sisoc/insumos", true],
    ["/v2/sisoc/insumos/", true],
    ["/v2/sisoc/insumos-ajeno", false],
    ["/v2/other/insumos", false],
  ])("preserves the Insumos navigation alias at %s without rewriting it", async (path, expected) => {
    webGet.mockImplementation((url: string) => Promise.resolve({ data:
      url === "web/session/" ? readyContext :
      url === "web/insumos/options/" ? { categories: [] } :
      { count: 0, page: 1, page_size: 20, pages: 1, filters: { busqueda: "", categoria: "" }, results: [] },
    }));
    setup(path as string);
    const navigation = await screen.findByRole("navigation", { name: /principal/i });
    const link = navigation.querySelector<HTMLAnchorElement>('a[href="/v2/sisoc/insumos/"]');
    expect(link).not.toBeNull();
    expect(link!.classList.contains("active")).toBe(expected);
    expect(link!.getAttribute("aria-current")).toBe(expected ? "page" : null);
    const parentControl = link!.closest("ul")!.previousElementSibling;
    expect(parentControl!.getAttribute("aria-expanded")).toBe(String(expected));
    expect(screen.queryByRole("link", { name: "Insumos" }) === link).toBe(expected);
    expect(window.location.pathname).toBe(path);
  });

  it("keeps the native separating space after the permission warning icon", async () => {
    webGet.mockResolvedValueOnce({ status: 403, data: { detail: "Forbidden" } });
    setup();
    const heading = await screen.findByRole("heading", { name: "¡Ups! Algo salió mal." });
    expect(heading.querySelector("i")?.nextSibling?.textContent?.startsWith(" ")).toBe(true);
  });

  it.each(["session", "form", "list"])("restores the outer title after unmounting a %s denial", async (kind) => {
    document.title = "Outer title";
    webGet.mockImplementation((url: string) => url === "web/session/" && kind !== "session"
      ? Promise.resolve({ data: readyContext })
      : Promise.resolve({ status: 403, data: { detail: "Forbidden" } }));
    const view = setup(kind === "list" ? "/v2/sisoc/insumos/" : "/v2/sisoc/insumos/crear/");
    await screen.findByRole("heading", { name: "¡Ups! Algo salió mal." });
    await waitFor(() => expect(document.title).toBe("SISOC - Error 403"));
    view.unmount();
    expect(document.title).toBe("Outer title");
  });

  it.each([
    ["/v2/sisoc/insumos/crear/", "SISOC - Nuevo insumo"],
    ["/v2/sisoc/insumos/9/editar/", "SISOC - Editar insumo"],
    ["/v2/sisoc/insumos/9/eliminar/", "SISOC - Eliminar insumo"],
    ["/v2/sisoc/insumos/", "SISOC - Insumos"],
  ])("matches the legacy document title at %s", async (path, title) => {
    webGet.mockImplementation((url: string) => Promise.resolve({ data:
      url === "web/session/" ? readyContext :
      url.endsWith("eliminar/") ? { id: 9, titulo: "Manual de prueba" } :
      url.endsWith("crear/") || url.endsWith("editar/") ? { initial: { programa: "", categoria: "", titulo: "", descripcion: "", activo: true }, options: { programa: [], categoria: [] }, current_file: null } :
      url === "web/insumos/options/" ? { categories: [] } :
      { count: 0, page: 1, page_size: 20, pages: 1, filters: { busqueda: "", categoria: "" }, results: [] },
    }));
    setup(path);
    await screen.findByRole("navigation", { name: "Navegación principal" });
    await waitFor(() => expect(document.title).toBe(title));
  });

  it("opens the React create route, keeps legacy active ancestry and returns with feedback", async () => {
    webGet.mockImplementation((url: string) => Promise.resolve({ data:
      url === "web/session/" ? readyContext :
      url === "web/insumos/crear/" ? { initial: { programa: "", categoria: "", titulo: "", descripcion: "", activo: true }, options: { programa: [], categoria: [] }, current_file: null } :
      url === "web/insumos/options/" ? { categories: [] } :
      { count: 0, page: 1, page_size: 20, pages: 1, filters: { busqueda: "", categoria: "" }, results: [] },
    }));
    webPost.mockResolvedValueOnce({ data: { ok: true, message: "Insumo creado correctamente.", redirect: "/insumos/" } });
    setup("/v2/sisoc/insumos/crear/");
    await screen.findByRole("heading", { name: "Nuevo insumo" });
    expect(document.title).toBe("SISOC - Nuevo insumo");
    expect(screen.getByRole("link", { name: "Insumos" }).className).toContain("active");
    expect(screen.getByRole("button", { name: "Configuración de Comedores" }).getAttribute("aria-expanded")).toBe("true");
    fireEvent.submit(screen.getByRole("button", { name: "Guardar insumo" }).closest("form")!);
    expect(await screen.findByText("Insumo creado correctamente.")).toBeDefined();
    expect(window.location.pathname).toBe("/v2/sisoc/insumos/");
    expect(await screen.findByRole("heading", { name: "Buscar insumos" })).toBeDefined();
    expect(document.title).toBe("SISOC - Insumos");
    webGet.mockReset();
  });
  it("waits for the cookie-authenticated context before rendering private navigation", async () => {
    let resolveContext!: (response: { data: typeof readyContext }) => void;
    webGet.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveContext = resolve;
      }),
    );
    setup();

    expect(screen.getByRole("status").textContent).toContain("Cargando");
    expect(screen.queryByText("Prueba Insumos Gestión")).toBeNull();
    expect(screen.queryByRole("navigation", { name: "Navegación principal" })).toBeNull();
    expect(webGet).toHaveBeenCalledWith("web/session/", expect.objectContaining({ signal: expect.any(AbortSignal) }));

    resolveContext({ data: readyContext });
    expect(await screen.findByRole("navigation", { name: "Navegación principal" })).toBeDefined();
  });

  it("renders the server-projected username, menu order, active ancestry, and footer", async () => {
    webGet.mockResolvedValueOnce({ data: readyContext });
    setup();

    expect(await screen.findByText("Prueba Insumos Gestión")).toBeDefined();
    expect(screen.getByLabelText("Inicial de usuario").textContent).toBe("P");
    const navigation = screen.getByRole("navigation", { name: "Navegación principal" });
    expect(navigation.textContent?.indexOf("Inicio")).toBeLessThan(
      navigation.textContent?.indexOf("Legajos") ?? -1,
    );
    expect(screen.getByRole("link", { name: "Insumos" }).getAttribute("href")).toBe(
      "/v2/sisoc/insumos/",
    );
    expect(screen.getByRole("button", { name: "Configuración de Comedores" }).getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByRole("button", { name: "Configuración de Comedores" }).closest("li")?.className).toContain("menu-open");
    const sidebar = screen.getByRole("complementary");
    expect(sidebar.className).toContain("app-sidebar");
    expect(sidebar.textContent?.indexOf("Mi cuenta")).toBeGreaterThan(
      sidebar.textContent?.indexOf("Inicio") ?? -1,
    );
    expect(screen.getByRole("link", { name: "Mi cuenta" }).closest("li")?.className).toContain("order-0");
    expect(screen.getByRole("link", { name: "Inicio" }).closest("li")?.className).toContain("order-1");
    expect(screen.getByRole("link", { name: "Insumos" }).className).toContain("nav-dot");
    expect(screen.getByRole("main").className).toContain("app-main");
    expect(screen.getByRole("contentinfo").className).toContain("app-footer");
    expect(screen.getByRole("link", { name: "Mi cuenta" }).querySelector("i")?.className).toContain(
      "fa-user-circle",
    );
    expect(screen.getByRole("link", { name: "Comunicados" }).querySelector("i")?.className).toContain(
      "bi-newspaper",
    );
    const logout = screen.getByRole("button", { name: "Cerrar sesión" }).closest("form");
    expect(logout?.getAttribute("method")).toBe("post");
    expect(logout?.getAttribute("action")).toBe("/logout/");
    expect(logout?.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")?.value).toBe(
      "synthetic-csrf-token",
    );
    expect(screen.getByText("Versión local de prueba")).toBeDefined();
  });

  it("keeps expandable navigation on the legacy link surface and supports keyboard activation", async () => {
    webGet.mockResolvedValueOnce({ data: readyContext });
    setup();

    const toggle = await screen.findByRole("button", { name: "Configuración de Comedores" });
    expect(toggle.tagName).toBe("A");
    expect(toggle.getAttribute("href")).toBe("#");
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(toggle.classList.contains("active")).toBe(false);

    fireEvent.keyDown(toggle, { key: "Enter" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    fireEvent.keyDown(toggle, { key: " " });
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
  });

  it("preserves the legacy separator and spacing before the account link", async () => {
    webGet.mockResolvedValueOnce({ data: readyContext });
    setup();

    const accountLink = await screen.findByRole("link", { name: "Mi cuenta" });
    const accountItem = accountLink.closest("li");
    expect(accountItem?.className).toContain("border-top");
    expect(accountItem?.className).toContain("pt-2");
  });

  it("keeps the legacy SVG sizing instead of the generic icon dimensions", async () => {
    webGet.mockResolvedValueOnce({ data: readyContext });
    setup();

    const home = await screen.findByRole("link", { name: "Inicio" });
    expect(home.querySelector("img")?.classList.contains("nav-icon")).toBe(false);
  });

  it("keeps the explicit legacy Comunicados separator on links and groups", async () => {
    for (const href of ["/comunicados/", null]) {
      webGet.mockResolvedValueOnce({ data: { ...readyContext, navigation: readyContext.navigation.map((item) => item.id === "comunicados" ? { ...item, href } : item) } });
      setup();
      const item = await screen.findByRole(href === null ? "button" : "link", { name: "Comunicados" });
      expect(item.closest("li")?.classList.contains("sisoc-nav-comunicados")).toBe(true);
      cleanup();
    }
  });

  it("preserves the rendered space between the back icon and its label", async () => {
    webGet.mockResolvedValueOnce({ data: readyContext });
    setup();

    const back = await screen.findByRole("link", { name: "Volver" });
    expect(back.textContent).toBe(" Volver");
  });

  it("withholds the private shell until legacy web prerequisites are complete", async () => {
    webGet.mockResolvedValueOnce({
      data: {
        ...readyContext,
        access: { state: "profile_confirmation_required", required_action_url: "/mi-cuenta/confirmar/" },
        navigation: [],
      },
    });
    setup();

    expect(await screen.findByRole("heading", { name: "Antes de continuar" })).toBeDefined();
    expect(screen.getByRole("link", { name: "Continuar en SISOC" }).getAttribute("href")).toBe(
      "/mi-cuenta/confirmar/",
    );
    expect(screen.queryByRole("navigation", { name: "Navegación principal" })).toBeNull();
    expect(screen.queryByText("Prueba Insumos Gestión")).toBeNull();
  });

  it("preserves structured prerequisite details on a session API 403 without granting the shell", async () => {
    webGet.mockResolvedValueOnce({
      status: 403,
      data: {
        ...readyContext,
        access: { state: "password_change_required", required_action_url: "/cambiar-clave/" },
      },
    });
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Antes de continuar" })).toBeDefined();
    expect(screen.getByRole("link", { name: "Continuar en SISOC" }).getAttribute("href")).toBe("/cambiar-clave/");
    expect(screen.queryByRole("navigation", { name: "Navegación principal" })).toBeNull();
    const config = webGet.mock.calls[0][1];
    expect(config.validateStatus(403)).toBe(true);
    expect(config.validateStatus(401)).toBe(false);
    expect(config.validateStatus(500)).toBe(false);
  });

  it("shows the static permission page for an unstructured session 403 instead of suggesting login", async () => {
    webGet.mockResolvedValueOnce({ status: 403, data: "<html>server-only content</html>" });
    render(<App />);

    expect(await screen.findByRole("heading", { name: "¡Ups! Algo salió mal." })).toBeDefined();
    await waitFor(() => expect(document.title).toBe("SISOC - Error 403"));
    expect(screen.queryByRole("link", { name: "Iniciar sesión" })).toBeNull();
    expect(screen.queryByText("server-only content")).toBeNull();
  });

  it("does not treat the Insumos view capability as authorization for the whole shell", async () => {
    webGet.mockResolvedValueOnce({
      data: {
        ...readyContext,
        capabilities: {
          insumos: { can_view: false, show_management: true, show_categories: false },
        },
      },
    });
    setup();

    expect(await screen.findByText("Prueba Insumos Gestión")).toBeDefined();
    expect(screen.getByRole("navigation", { name: "Navegación principal" })).toBeDefined();
  });

  it("fails closed for an external remediation URL and an unknown access state", async () => {
    webGet.mockResolvedValueOnce({
      data: {
        ...readyContext,
        access: { state: "password_change_required", required_action_url: "https://example.invalid/" },
        navigation: [],
      },
    });
    setup();
    expect(await screen.findByRole("alert")).toBeDefined();
    expect(screen.queryByRole("navigation", { name: "Navegación principal" })).toBeNull();

    cleanup();
    webGet.mockResolvedValueOnce({
      data: { ...readyContext, access: { state: "unknown", required_action_url: null } },
    });
    setup();
    expect(await screen.findByRole("alert")).toBeDefined();
    expect(screen.queryByText("Prueba Insumos Gestión")).toBeNull();
  });

  it("fails closed on 401 and malformed ready context without retrying", async () => {
    webGet.mockRejectedValueOnce({ response: { status: 401 } });
    setup();
    expect(await screen.findByRole("alert")).toBeDefined();
    expect((await screen.findByRole("link", { name: "Iniciar sesión" })).getAttribute("href")).toContain(
      "/login/?next=",
    );
    expect(screen.queryByRole("navigation", { name: "Navegación principal" })).toBeNull();
    expect(webGet).toHaveBeenCalledTimes(1);

    cleanup();
    webGet.mockResolvedValueOnce({ data: { ...readyContext, navigation: [] } });
    setup();
    expect(await screen.findByRole("alert")).toBeDefined();
    expect(screen.queryByText("Prueba Insumos Gestión")).toBeNull();
  });

  it("uses the legacy mobile scrim and dismisses the menu from it", async () => {
    setViewport(true);
    webGet.mockResolvedValueOnce({ data: readyContext });
    setup();

    const toggle = await screen.findByRole("button", { name: "Abrir menú" });
    expect(document.querySelector(".sidebar-overlay")).toBeNull();
    fireEvent.click(toggle);
    const dismiss = screen.getAllByRole("button", { name: "Cerrar menú" })[1];
    expect(dismiss.tagName).toBe("DIV");
    expect(dismiss.classList.contains("sidebar-overlay")).toBe(true);
    fireEvent.keyDown(dismiss, { key: "Enter" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(document.querySelector(".sidebar-overlay")).toBeNull();
    fireEvent.click(toggle);
    fireEvent.click(screen.getAllByRole("button", { name: "Cerrar menú" })[1]);
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
  });

  it("exposes an accessible mobile sidebar toggle", async () => {
    setViewport(true);
    webGet.mockResolvedValueOnce({ data: readyContext });
    setup();

    const toggle = await screen.findByRole("button", { name: "Abrir menú" });
    expect(toggle.className).toContain("d-lg-none");
    const brand = document.querySelector(".main-header .brand-image")?.closest(".brand-link");
    expect(brand?.className).toContain("d-none");
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(document.body.classList.contains("sidebar-collapse")).toBe(true);
    fireEvent.click(toggle);
    await waitFor(() => expect(toggle.getAttribute("aria-expanded")).toBe("true"));
    expect(brand?.className).toContain("d-flex");
    expect(brand?.className).not.toContain("d-none");
    expect(document.body.classList.contains("sidebar-open")).toBe(true);
    expect(document.body.classList.contains("sidebar-collapse")).toBe(false);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(document.body.classList.contains("sidebar-collapse")).toBe(true);
    cleanup();
    expect(document.body.classList.contains("sidebar-collapse")).toBe(false);
  });
});
