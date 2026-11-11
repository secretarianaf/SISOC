import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { legacyIdentityFrame } from "../identityFrames";
import ClaroFrame from "./ClaroFrame";
import SisocShell from "./SisocShell";
import { readyContext, setViewport } from "./testFixtures";
import type { NavigationNode } from "./types";

vi.mock("@sisoc/api", () => ({
  crearCliente: vi.fn(() => ({ get: vi.fn() })),
  leerCookie: vi.fn(() => "synthetic-csrf-token"),
}));

const link = (id: string, label: string, href: string): NavigationNode => ({ id, label, href, children: [] });
const group = (id: string, label: string, children: NavigationNode[]): NavigationNode => ({ id, label, href: null, children });

// Projection of `includes/sidebar/opciones.html` as `build_web_navigation` returns it.
const navigation: NavigationNode[] = [
  link("inicio", "Inicio", "/inicio/"),
  group("legajos", "Legajos", [
    group("comedores", "Comedores", [
      link("comedores", "Ver Comedores", "/comedores/listar"),
      group("admision-comedores", "Admisión - Comedores", [
        link("admisiones_tecnicos_listar", "Técnicos", "/admisiones/tecnicos/listar"),
        link("admisiones_legales_listar", "Legales", "/admisiones/legales/listar"),
      ]),
    ]),
    group("centro-de-infancia", "Centro de Infancia", [
      link("centrodeinfancia", "Ver Centros de Infancia", "/centrodeinfancia/listar"),
      link("centrodeinfancia_reportes", "Reportes", "/centrodeinfancia/reportes/"),
    ]),
    link("inspecciones_panel", "Inspecciones escolares", "/inspecciones/"),
    group("celiaquia", "Celiaquía", [link("expediente_list", "Expedientes", "/celiaquia/expedientes/")]),
  ]),
  group("administracion-sistema", "Administración del sistema", [
    link("usuarios", "Usuarios", "/usuarios/"),
    link("vat_voucher_parametria_list", "Parametrías de Voucher", "/vat/vouchers/parametrias/"),
  ]),
  group("configuracion-comedores", "Configuración de Comedores", [
    link("montoprestacion_listar", "Monto de Prestaciones", "/comedores/montoprestacion/listar"),
    group("gestor-templates", "Gestor de templates", [
      link("gestor_templates_listar", "Templates", "/configuracion/templates/"),
      link("gestor_templates_variables_listar", "Variables documentales", "/configuracion/templates/variables/"),
    ]),
  ]),
  link("ocr_upload", "OCR", "/ocr/"),
  group("comunicados", "Comunicados", [link("comunicados", "Ver Comunicados", "/comunicados/")]),
  link("mi_cuenta", "Mi cuenta", "/mi-cuenta/"),
];

const anchor = (name: string) => screen.getByText(name, { selector: "p" }).closest("a") as HTMLAnchorElement;
const item = (name: string) => anchor(name).closest("li") as HTMLLIElement;

function renderShell(path: string, headerItems?: React.ReactNode, activePath?: string) {
  window.history.replaceState({}, "", path);
  return render(
    <SisocShell context={{ ...readyContext, navigation }} previewLinks={false} content={<p>Contenido</p>} headerItems={headerItems} activePath={activePath} />,
  );
}

function renderClaro(path: string) {
  window.history.replaceState({}, "", path);
  return render(
    <ClaroFrame
      title="Actas"
      user={{ display_name: "Prueba", avatar_initial: "P", role_label: "Rol" }}
      layout={{ breadcrumb: [], display_name: "Prueba", role: "", initials: "P" }}
      navigation={navigation}
      footerLabel="Versión"
    >
      <p>Contenido</p>
    </ClaroFrame>,
  );
}

beforeEach(() => setViewport(false));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe.each([
  ["SisocShell", renderShell],
  ["ClaroFrame", renderClaro],
])("%s nested navigation", (_name, renderFrame) => {
  it("draws a second-level group like the native nav-dot parent, opened and active by route prefix", () => {
    renderFrame("/centrodeinfancia/reportes/");
    expect(item("Legajos").className).toContain("menu-open");
    expect(item("Centro de Infancia").className.split(" ")).toEqual(expect.arrayContaining(["nav-item", "menu-open"]));
    expect(item("Centro de Infancia").className).not.toContain("nav-main-item");
    expect(anchor("Centro de Infancia").className).toBe("nav-link nav-dot ms-2 active");
    expect(anchor("Centro de Infancia").querySelector("i.nav-arrow.bi-chevron-right")).not.toBeNull();
    expect(item("Reportes").className).toBe("nav-item");
    expect(anchor("Reportes").className).toBe("nav-link ms-4 active");
    expect(anchor("Reportes").firstElementChild?.className).toBe("nav-icon bi bi-arrow-return-right");
    expect(anchor("Ver Centros de Infancia").className).toBe("nav-link ms-4");
  });

  it("opens the branch for any page of the prefix without marking a leaf", () => {
    renderFrame("/centrodeinfancia/observacion/1/");
    expect(item("Legajos").className).toContain("menu-open");
    expect(item("Centro de Infancia").className).toContain("menu-open");
    expect(anchor("Centro de Infancia").className).toBe("nav-link nav-dot ms-2 active");
    expect(anchor("Reportes").className).toBe("nav-link ms-4");
    expect(anchor("Ver Centros de Infancia").className).toBe("nav-link ms-4");
    expect(item("Comedores").className).not.toContain("menu-open");
    expect(anchor("Comedores").className).toBe("nav-link nav-dot ms-2");
  });

  it("draws a third-level group and its leaves like the native admission branch", () => {
    renderFrame("/admisiones/tecnicos/listar");
    expect(item("Comedores").className).toContain("menu-open");
    expect(anchor("Comedores").className).toBe("nav-link nav-dot ms-2");
    expect(item("Admisión - Comedores").className.split(" ")).toEqual(expect.arrayContaining(["nav-item", "ms-4", "menu-open"]));
    expect(anchor("Admisión - Comedores").className).toBe("nav-link");
    expect(anchor("Admisión - Comedores").firstElementChild?.className).toBe("nav-icon bi bi-arrow-return-right");
    expect(anchor("Técnicos").className).toBe("nav-link nav-dot ms-4 active");
    expect(anchor("Legales").className).toBe("nav-link nav-dot ms-4");
  });

  it("keeps the native Celiaquía exception: plain ms-2 leaves with their own icons, never opened", () => {
    renderFrame("/celiaquia/expedientes/");
    expect(item("Celiaquía").className).not.toContain("menu-open");
    expect(anchor("Celiaquía").className).toBe("nav-link nav-dot ms-2");
    expect(anchor("Expedientes").className).toBe("nav-link ms-2");
    expect(anchor("Expedientes").firstElementChild?.className).toBe("nav-icon fas fa-folder-open");
  });

  it("leaves second-level links unchanged", () => {
    renderFrame("/inspecciones/");
    expect(anchor("Inspecciones escolares").className).toBe("nav-link nav-dot ms-2 active");
    expect(anchor("Inspecciones escolares").querySelector("i")).toBeNull();
  });
});

describe.each([
  ["SisocShell", renderShell],
  ["ClaroFrame", renderClaro],
])("%s route-fragment rules of the large menu", (_name, renderFrame) => {
  it("keeps the configuration branch open and its entry marked on a subpage", () => {
    renderFrame("/comedores/montoprestacion/crear");
    expect(item("Configuración de Comedores").className).toContain("menu-open");
    expect(anchor("Monto de Prestaciones").className).toBe("nav-link nav-dot ms-2 active");
    expect(item("Legajos").className).toContain("menu-open");
  });

  it("draws the nested templates group with ms-4 leaves and the template's exclusions", () => {
    renderFrame("/configuracion/templates/variables/");
    expect(item("Gestor de templates").className).toContain("menu-open");
    expect(anchor("Gestor de templates").className).toBe("nav-link nav-dot ms-2 active");
    expect(anchor("Variables documentales").className).toBe("nav-link ms-4 active");
    expect(anchor("Templates").className).toBe("nav-link ms-4");
  });

  it("never opens the administration branch and uses the native second-level icons", () => {
    renderFrame("/usuarios/");
    expect(item("Administración del sistema").className).not.toContain("menu-open");
    expect(anchor("Usuarios").className).toBe("nav-link nav-dot ms-2 active");
    expect(anchor("Parametrías de Voucher").firstElementChild?.className).toBe("nav-icon bi bi-ticket-perforated");
    expect(anchor("Ver Comunicados").querySelector("i")).toBeNull();
    expect(anchor("OCR").firstElementChild?.className).toBe("nav-icon bi bi-file-text");
  });

  it("marks the communications group only on its routes", () => {
    renderFrame("/comunicados/");
    expect(item("Comunicados").className).toContain("menu-open");
    expect(anchor("Comunicados").className).toBe("nav-link active");
    expect(anchor("Ver Comunicados").className).toBe("nav-link nav-dot ms-2 active");
  });
});

describe("SisocShell activePath", () => {
  it("evaluates the menu rules on the given path instead of the current one", () => {
    renderShell("/otra/pagina/", undefined, "/centrodeinfancia/reportes/");
    expect(anchor("Reportes").className).toBe("nav-link ms-4 active");
    expect(item("Configuración de Comedores").className).not.toContain("menu-open");
  });
});

describe("legacyIdentityFrame activePath", () => {
  it("forwards the path the menu rules evaluate", () => {
    window.history.replaceState({}, "", "/otra/pagina/");
    const presentation = { user: readyContext.user, legacy_frame_navigation: navigation, footer_version_label: "Versión" };
    render(legacyIdentityFrame(<p>Contenido</p>, presentation as never, "Título", "Título", undefined, undefined, false, "/", "/comedores/montoprestacion/crear"));
    expect(anchor("Monto de Prestaciones").className).toBe("nav-link nav-dot ms-2 active");
    expect(item("Configuración de Comedores").className).toContain("menu-open");
  });
});

describe("SisocShell header items", () => {
  it("renders the given items before the logout item of the native header list", () => {
    renderShell("/centrodeinfancia/reportes/", <li className="nav-item"><a href="/x/">Extra</a></li>);
    const extra = screen.getByRole("link", { name: "Extra" }).closest("li") as HTMLLIElement;
    const list = document.querySelector("header.main-header ul.nav-links") as HTMLUListElement;
    expect(list.firstElementChild).toBe(extra);
    expect(extra.nextElementSibling?.querySelector("form[action='/logout/']")).not.toBeNull();
  });

  it("renders only the logout item without header items", () => {
    renderShell("/inicio/");
    const list = document.querySelector("header.main-header ul.nav-links") as HTMLUListElement;
    expect(list.children).toHaveLength(1);
  });
});

describe("SisocShell app-header block", () => {
  const block = () => document.querySelector(".app-content-header > .container-fluid:last-child") as HTMLElement;

  it("keeps the template default, one empty row, without an app header", () => {
    renderShell("/inicio/");
    expect(block().innerHTML).toBe('<div class="row"></div>');
  });

  it("replaces the default row with the given app header, as `{% block app-header %}` does", () => {
    window.history.replaceState({}, "", "/inicio/");
    render(<SisocShell context={{ ...readyContext, navigation }} previewLinks={false} content={<p>Contenido</p>} appHeader={<div className="pas-top-actions"><a href="/pas/listar">Buscador PAS</a></div>} />);
    expect(block().innerHTML).toBe('<div class="pas-top-actions"><a href="/pas/listar">Buscador PAS</a></div>');
  });
});
