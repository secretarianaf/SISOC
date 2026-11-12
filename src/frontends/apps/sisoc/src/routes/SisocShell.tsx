/* eslint-disable react-refresh/only-export-components -- the native sidebar rules are shared with ClaroFrame. */
import { useEffect, useId, useState, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import InsumosToast from "../InsumosToast";
import { safeInternalPath } from "../webAccess";
import type { NavigationNode, ReadyContext, ShellRouteDefinition, ShellRouteParams } from "./types";

function internalPath(value: unknown): string | null {
  return safeInternalPath(value);
}

function useIsMobile(): boolean {
  const query = "(max-width: 991.98px)";
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia?.(query).matches ?? false,
  );
  useEffect(() => {
    const media = window.matchMedia?.(query);
    if (!media) return undefined;
    const update = () => setIsMobile(media.matches);
    media.addEventListener?.("change", update);
    return () => media.removeEventListener?.("change", update);
  }, []);
  return isMobile;
}

function ShellIcon({ id }: { id: string }) {
  const localIcons: Record<string, string> = {
    inicio: "/static/custom/img/iconos_sidebar/inicio.svg",
    legajos: "/static/custom/img/iconos_sidebar/legajos.svg",
    "configuracion-comedores": "/static/custom/img/iconos_sidebar/legajos.svg",
    tableros: "/static/custom/img/iconos_sidebar/tableros.svg",
    "administracion-sistema": "/static/custom/img/iconos_sidebar/administracion.svg",
  };
  const iconClasses: Record<string, string> = {
    comunicados: "bi bi-newspaper",
    mi_cuenta: "fas fa-user-circle",
    ocr_upload: "bi bi-file-text",
  };
  const src = localIcons[id];
  if (src) return <img src={src} alt="" />;
  const iconClass = iconClasses[id];
  if (iconClass) return <i className={`nav-icon ${iconClass}`} aria-hidden="true" />;
  return null;
}

// The legacy sidebar template places top-level items in this DOM (Tab) order and
// sets each visual position with an inline CSS order; the API lists them visually.
const LEGACY_SIDEBAR_ORDER: Record<string, number> = {
  inicio: 1,
  comunicados: 7,
  "administracion-sistema": 4,
  "configuracion-comedores": 5,
  ocr_upload: 6,
  tableros: 3,
  legajos: 2,
};
const LEGACY_SIDEBAR_DOM = Object.keys(LEGACY_SIDEBAR_ORDER);

// Unknown top-level items keep the server order instead of guessing a position.
function legacySidebarMenu(menu: NavigationNode[]): NavigationNode[] | null {
  if (!menu.every((item) => item.id in LEGACY_SIDEBAR_ORDER)) return null;
  return [...menu].sort((a, b) => LEGACY_SIDEBAR_DOM.indexOf(a.id) - LEGACY_SIDEBAR_DOM.indexOf(b.id));
}

// `includes/sidebar/opciones.html` opens branches and highlights entries when its
// route (`pagina_actual`) contains these markers, so subpages (crear/editar) keep
// their entry marked; the DTO only carries the tree.
type RouteRule = (route: string) => boolean;
const anyOf = (...markers: string[]): RouteRule => (route) => markers.some((marker) => route.includes(marker));
const never: RouteRule = () => false;
const NATIVE_GROUP_RULES: Record<string, { open: RouteRule; active?: RouteRule }> = {
  comunicados: { open: anyOf("comunicados"), active: anyOf("comunicados") },
  "administracion-sistema": { open: never },
  "configuracion-comedores": {
    open: anyOf("dupla", "equipo-tecnico", "montoprestacion", "cursos-app-mobile", "actividades-pnud", "insumos", "configuracion/templates"),
  },
  tableros: { open: anyOf("dashboard") },
  legajos: {
    open: anyOf("comedores", "admisiones", "acompanamiento", "rendicion_cuentas", "organizaciones", "centrodeinfancia",
      "ver-para-ser-libre", "pas/", "ciudadanos", "centros", "celiaquia", "expediente", "dispositivos", "datacalle", "inspecciones/"),
  },
  "historia-social-digital": { open: anyOf("ciudadanos"), active: anyOf("ciudadanos") },
  comedores: {
    open: anyOf("comedores", "admisiones", "acompanamiento", "rendicion_cuentas", "importarexpediente"),
    active: anyOf("comedores", "importarexpediente"),
  },
  "admision-comedores": { open: anyOf("admisiones") },
  organizaciones: { open: anyOf("organizaciones", "rendicioncuentasmensual"), active: anyOf("organizaciones", "rendicioncuentasmensual") },
  "centro-de-infancia": { open: anyOf("centrodeinfancia"), active: anyOf("centrodeinfancia") },
  "ver-para-ser-libres": { open: anyOf("ver-para-ser-libre"), active: anyOf("ver-para-ser-libre") },
  pas: { open: anyOf("pas/"), active: anyOf("pas/") },
  "situacion-de-calle": { open: anyOf("dispositivos", "datacalle"), active: anyOf("dispositivos", "datacalle") },
  "centro-de-familia": { open: anyOf("centros"), active: anyOf("centros") },
  inet: { open: anyOf("vat/"), active: anyOf("vat/") },
  "inet-catalogos": { open: anyOf("vat/modalidades-institucionales/", "vat/catalogos/") },
  "gestor-templates": { open: anyOf("configuracion/templates"), active: anyOf("configuracion/templates") },
  celiaquia: { open: never, active: never },
};
const NATIVE_LINK_RULES: Record<string, RouteRule> = {
  inicio: anyOf("inicio"),
  comunicados: (route) => route === "/comunicados/",
  comunicados_gestion: anyOf("comunicados/gestion"),
  usuarios: anyOf("usuarios", "password"),
  grupos: anyOf("grupos"),
  programa_listar: anyOf("programas/"),
  "audittrail:log_list": anyOf("auditoria/"),
  encuestas_listar: anyOf("encuestas"),
  papelera_list: anyOf("papelera/"),
  vat_voucher_parametria_list: anyOf("vat/vouchers/"),
  dupla_list: anyOf("dupla", "equipo-tecnico"),
  montoprestacion_listar: anyOf("montoprestacion"),
  cursos_app_mobile_list: anyOf("cursos-app-mobile"),
  actividades_pnud_list: anyOf("actividades-pnud"),
  insumos_listar: anyOf("insumos"),
  ocr_upload: anyOf("ocr/"),
  ciudadanos: anyOf("ciudadanos/listar"),
  ciudadanos_cola_revision: anyOf("ciudadanos/revision"),
  ciudadanos_importacion_masiva: anyOf("ciudadanos/importacion-masiva"),
  comedores: anyOf("comedores/listar"),
  admisiones_tecnicos_listar: anyOf("admisiones/tecnicos", "admisiones_tecnicos"),
  admisiones_legales_listar: anyOf("admisiones/legales", "admisiones_legales"),
  lista_comedores_acompanamiento: anyOf("acompanamiento"),
  importarexpedientes_list: anyOf("importarexpediente/listar"),
  organizaciones: anyOf("organizaciones/listar"),
  rendicioncuentasmensual_global_list: anyOf("rendicioncuentasmensual"),
  centrodeinfancia: anyOf("centrodeinfancia/listar"),
  centrodeinfancia_reportes: anyOf("centrodeinfancia/reportes"),
  vpsl_itinerario_list: anyOf("ver-para-ser-libre/"),
  vpsl_sede_list: anyOf("ver-para-ser-libre/sedes"),
  pas_persona_listar: anyOf("pas/listar"),
  pas_panel_control: anyOf("pas/panel-control"),
  pas_informe_listar: anyOf("pas/informes"),
  inspecciones_panel: anyOf("inspecciones/"),
  dispositivos_listar: anyOf("dispositivos/"),
  datacalle_relevamientos_listar: anyOf("datacalle/"),
  centro_list: anyOf("centros/"),
  beneficiarios_crear: anyOf("beneficiarios/nuevo"),
  beneficiarios_list: anyOf("beneficiarios/beneficiarios"),
  responsables_list: anyOf("beneficiarios/responsables"),
  vat_centro_list: anyOf("vat/centros/"),
  vat_reporte_inscripciones_asistencias: anyOf("vat/reportes/inscripciones-asistencias/"),
  vat_buscador_ciudadano: anyOf("vat/buscador-ciudadano/"),
  vat_modalidadcursada_list: anyOf("vat/catalogos/modalidades-cursado/"),
  vat_planversioncurricular_list: anyOf("vat/catalogos/planes-curriculares/"),
  gestor_templates_listar: (route) =>
    route.includes("configuracion/templates") && !route.includes("incidencias") && !route.includes("variables"),
  gestor_templates_variables_listar: anyOf("configuracion/templates/variables"),
  gestor_templates_incidencias_listar: anyOf("configuracion/templates/incidencias"),
  expediente_list: never,
  cupo_dashboard: never,
  reporter_provincias: never,
};
// The native Celiaquía branch uses plain `ms-2` leaves with their own icons.
const CELIAQUIA_LEAF_ICONS: Record<string, string> = {
  expediente_list: "fas fa-folder-open",
  cupo_dashboard: "fas fa-chart-bar",
  reporter_provincias: "fas fa-chart-pie",
};

// Second-level entries carry no icon in the template, except this one.
const SECOND_LEVEL_ICONS: Record<string, string> = { vat_voucher_parametria_list: "bi bi-ticket-perforated" };

/** Native open state of a group, or `undefined` when the template has no route rule for it. */
export function nativeGroupOpen(id: string, pathname: string): boolean | undefined {
  return NATIVE_GROUP_RULES[id]?.open(pathname);
}

/** Native `active` class of a nested link or group anchor, or `undefined` without a rule. */
export function nativeActive(item: NavigationNode, pathname: string): boolean | undefined {
  if (item.href !== null) return NATIVE_LINK_RULES[item.id]?.(pathname);
  const rules = NATIVE_GROUP_RULES[item.id];
  return rules && (rules.active ?? never)(pathname);
}

/**
 * Markup of a nested sidebar entry (depth 2 and deeper) in `opciones.html`:
 * second-level entries are `nav-dot ms-2`, third-level links `ms-4` with a return
 * arrow, third-level groups an `ms-4` item, and fourth-level links `nav-dot ms-4`.
 */
export function nestedNavMarkup(item: NavigationNode, depth: number, parentId?: string): { item: string; link: string; icon: string | null } {
  if (parentId === "celiaquia" && item.href !== null) {
    return { item: "nav-item", link: "nav-link ms-2", icon: CELIAQUIA_LEAF_ICONS[item.id] ?? null };
  }
  if (depth <= 2) return { item: "nav-item", link: "nav-link nav-dot ms-2", icon: SECOND_LEVEL_ICONS[item.id] ?? null };
  if (depth === 3 && item.href === null) return { item: "nav-item ms-4", link: "nav-link", icon: "bi bi-arrow-return-right" };
  if (depth === 3) return { item: "nav-item", link: "nav-link ms-4", icon: "bi bi-arrow-return-right" };
  return { item: "nav-item", link: "nav-link nav-dot ms-4", icon: null };
}

// Identity frames render the legacy menu with its original public links.
function projectedHref(item: NavigationNode, previewLinks = true): string | null {
  if (previewLinks && item.id === "insumos_listar" && item.href === "/insumos/") {
    return "/v2/sisoc/insumos/";
  }
  return internalPath(item.href);
}

function containsActivePath(item: NavigationNode, pathname: string, previewLinks = true): boolean {
  return (
    projectedHref(item, previewLinks) === pathname ||
    (previewLinks && item.id === "insumos_listar" &&
      (pathname === "/v2/sisoc/insumos" ||
        pathname.startsWith("/v2/sisoc/insumos/"))) ||
    item.children.some((child) => containsActivePath(child, pathname, previewLinks))
  );
}

function NavigationItem({
  item,
  pathname,
  isMobile,
  onNavigate,
  depth = 1,
  parentId,
  previewLinks = true,
  legacyOrder,
}: {
  item: NavigationNode;
  pathname: string;
  isMobile: boolean;
  onNavigate: () => void;
  depth?: number;
  parentId?: string;
  previewLinks?: boolean;
  legacyOrder?: number;
}) {
  const controlId = useId();
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});
  const isNested = depth > 1;
  const isAccountItem = item.id === "mi_cuenta";
  const separatorClass = item.id === "comunicados" ? " sisoc-nav-comunicados" : "";
  const orderClass = legacyOrder === undefined ? " order-1" : "";
  const orderStyle = legacyOrder === undefined ? undefined : { order: legacyOrder };
  const nested = isNested ? nestedNavMarkup(item, depth, parentId) : null;
  const localHref = projectedHref(item, previewLinks);
  const exactActive = localHref !== null && (
    localHref === pathname ||
    (previewLinks && item.id === "insumos_listar" &&
      (pathname === "/v2/sisoc/insumos" ||
        pathname.startsWith("/v2/sisoc/insumos/")))
  );
  // Route rules describe native pages; the /v2/ preview keeps exact matching.
  const nativeRules = !previewLinks;
  const active = (nativeRules ? nativeActive(item, pathname) : undefined) ?? exactActive;
  const descendantActive = item.children.some((child) =>
    containsActivePath(child, pathname, previewLinks),
  );
  const expanded = overrides[item.id] ?? (nativeRules ? nativeGroupOpen(item.id, pathname) : undefined) ?? descendantActive;
  const toggleExpanded = () =>
    setOverrides((current) => ({ ...current, [item.id]: !expanded }));

  if (item.href !== null) {
    return (
      <li
        className={`nav-item${isNested || isAccountItem ? "" : ` nav-main-item${orderClass}`}${
          isAccountItem ? " order-0 border-top pt-2" : ""
        }${separatorClass}`}
        style={isNested || isAccountItem ? undefined : orderStyle}
      >
        <a
          className={`${nested ? nested.link : "nav-link"}${active ? " active" : ""}`}
          href={localHref ?? "/"}
          aria-current={active ? "page" : undefined}
          onClick={onNavigate}
        >
          {nested ? nested.icon && <i className={`nav-icon ${nested.icon}`} aria-hidden="true" /> : <ShellIcon id={item.id} />}
          <p>{item.label}</p>
        </a>
      </li>
    );
  }

  const groupActive = nativeRules && depth <= 2 && nativeActive(item, pathname) === true;
  return (
    <li
      className={`${nested ? nested.item : `nav-item nav-main-item${orderClass}`}${expanded ? " menu-open" : ""}${nested ? "" : separatorClass}`}
      style={nested ? undefined : orderStyle}
    >
      <a
        className={`${nested ? nested.link : "nav-link"}${groupActive ? " active" : ""}`}
        href="#"
        role="button"
        aria-expanded={expanded}
        aria-controls={controlId}
        onClick={(event) => {
          event.preventDefault();
          toggleExpanded();
        }}
        onKeyDown={(event) => {
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          toggleExpanded();
        }}
      >
        {nested ? nested.icon && <i className={`nav-icon ${nested.icon}`} aria-hidden="true" /> : <ShellIcon id={item.id} />}
        <p>{item.label}</p>
        <i className="nav-arrow bi bi-chevron-right" aria-hidden="true" />
      </a>
      <ul
        className="nav nav-treeview"
        id={controlId}
        hidden={!expanded}
      >
        {item.children.map((child) => (
          <NavigationItem
            key={child.id}
            item={child}
            pathname={pathname}
            isMobile={isMobile}
            onNavigate={onNavigate}
            depth={depth + 1}
            parentId={item.id}
            previewLinks={previewLinks}
          />
        ))}
      </ul>
    </li>
  );
}

// First shell route whose matcher accepts the current in-shell pathname.
function resolveShellRoute(
  routes: readonly ShellRouteDefinition[],
  pathname: string,
): { route: ShellRouteDefinition; params: ShellRouteParams } | null {
  for (const route of routes) {
    const params = route.match(pathname);
    if (params !== null) return { route, params };
  }
  return null;
}

export default function SisocShell({
  context,
  content,
  pageTitle,
  heading,
  overlays,
  previewLinks = true,
  breadcrumb,
  hideBack = false,
  backHref = "/",
  routes = [],
  headerItems,
  appHeader,
  activePath,
}: {
  context: Pick<ReadyContext, "user" | "navigation" | "footer_version_label"> & {
    capabilities?: ReadyContext["capabilities"];
  };
  content?: ReactNode;
  pageTitle?: string;
  heading?: ReactNode;
  overlays?: ReactNode;
  previewLinks?: boolean;
  breadcrumb?: ReactNode;
  hideBack?: boolean;
  /** Native `volver_url` of the page; the legacy back button defaults to `/`. */
  backHref?: string;
  /** In-shell pages used when no explicit `content` is given (business shell only). */
  routes?: readonly ShellRouteDefinition[];
  /** Page-specific `nav-item`s that `includes/header.html` places before the logout item. */
  headerItems?: ReactNode;
  /** `{% block app-header %}` of `includes/main.html`: replaces its default empty row. */
  appHeader?: ReactNode;
  /** Path the menu rules evaluate instead of the current one (a page that marks its list entry). */
  activePath?: string;
}) {
  const isMobile = useIsMobile();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [pathname, setPathname] = useState(() => window.location.pathname);
  // Native groups-list markup does not mark its Administration branch active.
  const navigationPath = activePath ?? (!previewLinks && pathname === "/grupos/" ? "" : pathname);
  const [successMessage, setSuccessMessage] = useState("");
  const shellRoute = resolveShellRoute(routes, pathname);
  const routeTitle = shellRoute?.route.title(shellRoute.params);
  useEffect(() => {
    const previousTitle = document.title;
    document.title = `SISOC - ${pageTitle ?? routeTitle}`;
    return () => { document.title = previousTitle; };
  }, [routeTitle, pageTitle]);
  const returnToList = (message = "") => {
    window.history.pushState({}, "", shellRoute?.route.listPath ?? "/v2/sisoc/insumos/");
    setPathname(window.location.pathname);
    setSuccessMessage(message);
  };
  useEffect(() => {
    const sync = () => { setPathname(window.location.pathname); setSuccessMessage(""); };
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  const account = context.navigation.find((item) => item.id === "mi_cuenta");
  const serverMenu = context.navigation.filter((item) => item.id !== "mi_cuenta");
  const legacyMenu = legacySidebarMenu(serverMenu);
  const menu = legacyMenu ?? serverMenu;
  const closeOnNavigate = () => {
    if (isMobile) setMobileOpen(false);
  };

  useEffect(() => {
    if (!isMobile || !mobileOpen) return undefined;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [isMobile, mobileOpen]);

  useEffect(() => {
    const hadCollapsedSidebar = document.body.classList.contains("sidebar-collapse");
    document.body.classList.toggle("sidebar-open", isMobile && mobileOpen);
    document.body.classList.toggle("sidebar-collapse", isMobile && !mobileOpen);
    return () => {
      document.body.classList.remove("sidebar-open");
      document.body.classList.toggle("sidebar-collapse", hadCollapsedSidebar);
    };
  }, [isMobile, mobileOpen]);

  return (
    <>
      <header className="main-header">
        <nav className="navbar d-flex flex-wrap align-items-center justify-content-between gap-2">
          <div className="d-flex align-items-center gap-2">
            <button
              className="btn btn-link d-inline-flex d-lg-none p-0 text-white"
              type="button"
              data-lte-toggle="sidebar"
              aria-label={mobileOpen ? "Cerrar menú" : "Abrir menú"}
              aria-controls="sisoc-navigation"
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((open) => !open)}
            >
              <i className="bi bi-list fs-2" aria-hidden="true" />
            </button>
            <a className="brand-link d-flex align-items-center" href="/inicio/" aria-label="Inicio de SISOC">
              <span className="brand-text fw-light">
                <img className="brand-image" src="/static/custom/img/logoBlanco.png" alt="SISOC" />
              </span>
            </a>
          </div>
        <ul className="nav-links mb-0 d-flex align-items-center flex-wrap">
          {headerItems}
          <li className="nav-item circle-btn">
            <form className="d-inline" method="post" action="/logout/">
              <input
                type="hidden"
                name="csrfmiddlewaretoken"
                value={leerCookie("csrftoken") ?? ""}
              />
              <button className="nav-link nav-link-rounded border-0 bg-transparent" type="submit" aria-label="Cerrar sesión">
                <img src="/static/custom/img/iconos_navbar/exit.svg" alt="Salir" />
              </button>
            </form>
          </li>
        </ul>
        </nav>
      </header>

      <div className="app-wrapper">
        {isMobile && mobileOpen && (
          <div
            className="sidebar-overlay"
            role="button"
            tabIndex={0}
            aria-label="Cerrar menú"
            onClick={() => setMobileOpen(false)}
            onKeyDown={(event) => {
              if (event.key !== "Enter" && event.key !== " ") return;
              event.preventDefault();
              setMobileOpen(false);
            }}
          />
        )}
        <aside
          className="app-sidebar shadow"
          id="sisoc-navigation"
          aria-label="Menú lateral"
          aria-hidden={isMobile && !mobileOpen}
          data-open={mobileOpen}
        >
          <div className="sidebar-wrapper">
            <nav aria-label="Navegación principal">
              <ul
                className="nav sidebar-menu flex-column"
                data-lte-toggle="treeview"
                role="menu"
                data-accordion="false"
              >
                <li className="nav-item user-info mb-2 mt-2 order-first">
                  <div className="user-panel d-flex align-items-center p-3 sisoc-user-panel">
                    <div className="user-avatar me-3">
                      <div
                        className="avatar-circle d-flex align-items-center justify-content-center bg-primary text-white rounded-circle"
                        aria-label="Inicial de usuario"
                      >
                        {context.user.avatar_initial}
                      </div>
                    </div>
                    <div className="info flex-grow-1">
                      <p className="mb-1 text-white fw-bold">{context.user.display_name}</p>
                      <p className="mb-0 text-white-50 small">{context.user.role_label}</p>
                    </div>
                  </div>
                </li>
              {menu.map((item) => (
                <NavigationItem
                  key={item.id}
                  item={item}
                  pathname={navigationPath}
                  isMobile={isMobile}
                  onNavigate={closeOnNavigate}
                  previewLinks={previewLinks}
                  legacyOrder={legacyMenu ? LEGACY_SIDEBAR_ORDER[item.id] : undefined}
                />
              ))}
                {account && (
                  <NavigationItem
                    item={account}
                    pathname={navigationPath}
                    isMobile={isMobile}
                    onNavigate={closeOnNavigate}
                    previewLinks={previewLinks}
                  />
                )}
            </ul>
          </nav>
          </div>
        </aside>

        <main className="app-main">
          <div className="app-content-header">
            <div className="container-fluid">
          {!hideBack && <div className="d-print-none">
                <a className="btn btn-secondary btn-sm sisoc-volver" href={backHref}>
                  <i className="fas fa-arrow-left" aria-hidden="true" />{" "}
                  <span>Volver</span>
                </a>
              </div>}
              <div className="row">
                <div className="col-sm-9">
                  <h3 className="mb-0">{heading}</h3>
                </div>
                <div className="col-sm-3">
                  <ol className="breadcrumb float-sm-end">{breadcrumb}</ol>
                </div>
              </div>
            </div>
            <div className="container-fluid">
              {appHeader ?? <div className="row" />}
            </div>
          </div>
          <div className="app-content">
            <div className="container-fluid">
              {successMessage && <InsumosToast key={successMessage} message={successMessage} />}
              {content ?? shellRoute?.route.render({
                pathname,
                params: shellRoute.params,
                capabilities: context.capabilities,
                returnToList,
              })}
            </div>
          </div>
        </main>

        <footer className="app-footer">
          <div className="footer-content">
            <img
              className="footer-logo img-fluid sisoc-footer-logo"
              src="/static/custom/img/Presidencia_footer.svg"
              alt="Presidencia Logo"
            />
            <a
              className="footer-secondary-link"
              href="/novedades/"
              aria-label={context.footer_version_label}
            >
              <i className="bi bi-clock-fill" aria-hidden="true" />
              <span>{context.footer_version_label}</span>
            </a>
          </div>
        </footer>
        {overlays}
      </div>
    </>
  );
}
