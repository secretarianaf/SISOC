import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "./App";
import { readyContext, setViewport } from "./routes/testFixtures";

const { webGet, webPost } = vi.hoisted(() => ({ webGet: vi.fn(), webPost: vi.fn() }));
vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: webGet, post: webPost })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
  mensajeDeError: vi.fn(() => "Error de prueba"),
  SinPermiso: class SinPermiso extends Error {},
}));

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

  it.each([
    ["/", "web/login/"],
    ["/login/", "web/login/"],
    ["/password/first-change/", "web/password/first-change/"],
    ["/mi-cuenta/", "web/account/"],
    ["/mi-cuenta/confirmar/", "web/account/confirm/"],
    ["/password_change/", "web/password/change/"],
    ["/password_change/done/", "web/password/change/"],
    ["/inicio/", "web/surveys/pending/"],
  ])("loads only its identity operation at %s", async (path, endpoint) => {
    webGet.mockReturnValue(new Promise(() => {}));
    setup(path);
    await waitFor(() => expect(webGet.mock.calls.some(([url]) => String(url).startsWith(endpoint))).toBe(true));
    expect(webGet.mock.calls.some(([url]) => url === "web/session/")).toBe(false);
    expect(webGet.mock.calls.some(([url]) => String(url).startsWith("web/insumos/"))).toBe(false);
  });


  it("keeps the native separating space after the permission warning icon", async () => {
    webGet.mockResolvedValueOnce({ status: 403, data: { detail: "Forbidden" } });
    setup();
    const heading = await screen.findByRole("heading", { name: "¡Ups! Algo salió mal." });
    expect(heading.querySelector("i")?.nextSibling?.textContent?.startsWith(" ")).toBe(true);
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
    expect(screen.getByRole("link", { name: "Inicio" }).closest("li")?.style.order).toBe("1");
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

  it("keeps the legacy sidebar tab order while CSS order preserves the visual order", async () => {
    const top = (id: string, label: string, href: string | null = null) => ({ id, label, href, children: [] });
    webGet.mockResolvedValueOnce({ data: { ...readyContext, navigation: [
      top("inicio", "Inicio", "/inicio/"), top("legajos", "Legajos"), top("tableros", "Tableros"),
      top("administracion-sistema", "Administración del sistema"), top("configuracion-comedores", "Configuración de Comedores"),
      top("ocr_upload", "OCR", "/ocr/"), top("comunicados", "Comunicados"), top("mi_cuenta", "Mi cuenta", "/mi-cuenta/"),
    ] } });
    setup();
    await screen.findByRole("link", { name: "Inicio" });
    const items = [...document.querySelectorAll<HTMLLIElement>(".sidebar-menu > li.nav-item:not(.user-info)")];
    expect(items.map((item) => item.textContent)).toEqual([
      "Inicio", "Comunicados", "Administración del sistema", "Configuración de Comedores", "OCR", "Tableros", "Legajos", "Mi cuenta",
    ]);
    expect(items.map((item) => item.style.order)).toEqual(["1", "7", "4", "5", "6", "3", "2", ""]);
    expect(items.some((item) => item.classList.contains("order-1"))).toBe(false);
  });

  it("links the footer version to the legacy changelog route", async () => {
    webGet.mockResolvedValueOnce({ data: readyContext });
    setup();
    const version = await screen.findByRole("link", { name: "Versión local de prueba" });
    expect(version.getAttribute("href")).toBe("/novedades/");
  });

  it("keeps the server menu order when a top-level item has no legacy position", async () => {
    webGet.mockResolvedValueOnce({ data: { ...readyContext, navigation: [
      readyContext.navigation[0], { id: "nuevo", label: "Nuevo", href: "/nuevo/", children: [] }, ...readyContext.navigation.slice(1),
    ] } });
    setup();
    await screen.findByRole("link", { name: "Nuevo" });
    const items = [...document.querySelectorAll<HTMLLIElement>(".sidebar-menu > li.nav-main-item")];
    expect(items.map((item) => item.textContent)).toEqual(["Inicio", "Nuevo", "Legajos", "Comunicados", "Configuración de ComedoresInsumos"]);
    expect(items.every((item) => item.classList.contains("order-1") && item.style.order === "")).toBe(true);
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

  it("points the back link to the native default destination", async () => {
    webGet.mockResolvedValueOnce({ data: readyContext });
    setup();

    const back = await screen.findByRole("link", { name: "Volver" });
    expect(back.getAttribute("href")).toBe("/");
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
    const brand = document.querySelector<HTMLAnchorElement>(".main-header .brand-image")?.closest<HTMLAnchorElement>(".brand-link");
    expect(brand?.className).toBe("brand-link d-flex align-items-center");
    brand?.focus();
    expect(document.activeElement).toBe(brand);
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    await waitFor(() => expect(document.body.classList.contains("sidebar-collapse")).toBe(true));
    fireEvent.click(toggle);
    await waitFor(() => expect(toggle.getAttribute("aria-expanded")).toBe("true"));
    expect(brand?.className).toBe("brand-link d-flex align-items-center");
    await waitFor(() => expect(document.body.classList.contains("sidebar-open")).toBe(true));
    await waitFor(() => expect(document.body.classList.contains("sidebar-collapse")).toBe(false));
    fireEvent.keyDown(document, { key: "Escape" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    await waitFor(() => expect(document.body.classList.contains("sidebar-collapse")).toBe(true));
    cleanup();
    expect(document.body.classList.contains("sidebar-collapse")).toBe(false);
  });



});
