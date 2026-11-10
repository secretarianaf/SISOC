import { useEffect, useLayoutEffect, useState, type CSSProperties, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { safeInternalPath } from "../webAccess";
import type { NavigationNode } from "./types";

/**
 * Light layout of `includes/base_claro.html` (Inspecciones): dark sidebar with
 * the logo, white header with breadcrumb and user, light content. It is not the
 * dark business shell: the native page loads a different stylesheet list, so
 * the frame swaps it while mounted, exactly in the native order.
 */
const CLARO_STYLESHEETS = [
  "https://fonts.googleapis.com/css?family=Source+Sans+Pro:300,400,400i,700&display=fallback",
  "https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap",
  "https://cdn.jsdelivr.net/npm/charts.css/dist/charts.min.css",
  "https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.css",
  "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css",
  "https://cdn.jsdelivr.net/npm/flag-icon-css@3.5.0/css/flag-icon.min.css",
  "https://cdnjs.cloudflare.com/ajax/libs/toastr.js/latest/toastr.min.css",
  "https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css",
  "https://cdn.jsdelivr.net/npm/bs-stepper@1.7.0/dist/css/bs-stepper.min.css",
  "https://cdn.datatables.net/1.11.5/css/dataTables.bootstrap4.min.css",
  "https://cdn.datatables.net/responsive/2.2.9/css/responsive.bootstrap4.min.css",
  "https://cdn.datatables.net/buttons/2.2.3/css/buttons.bootstrap4.min.css",
  "https://cdnjs.cloudflare.com/ajax/libs/tempusdominus-bootstrap-4/5.39.0/css/tempusdominus-bootstrap-4.min.css",
  "https://cdn.jsdelivr.net/npm/daterangepicker/daterangepicker.css",
  "https://cdnjs.cloudflare.com/ajax/libs/toastr.js/latest/toastr.min.css",
  "https://cdnjs.cloudflare.com/ajax/libs/icheck-bootstrap/3.0.1/icheck-bootstrap.min.css",
  "https://cdn.jsdelivr.net/npm/@fontsource/source-sans-3@5.0.12/index.css",
  "/static/dist/css/adminlte.css",
  "https://cdn.jsdelivr.net/npm/overlayscrollbars@2.3.0/styles/overlayscrollbars.min.css",
  "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.min.css",
  "https://cdn.jsdelivr.net/npm/apexcharts@3.37.1/dist/apexcharts.css",
  "https://cdn.jsdelivr.net/npm/jsvectormap@1.5.3/dist/css/jsvectormap.min.css",
  "/static/custom/css/poncho.css",
  "/static/custom/css/utils.css",
  "/static/custom/css/main.css?v=20260821-2",
  "/static/custom/css/select2_theme.css",
  "/static/custom/css/hitos.css",
  "https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Roboto+Mono&display=swap",
  "/static/custom/css/layout_claro.css",
  "/static/inspecciones/css/panel.css",
];

const OVERLAY_VIEWPORT: CSSProperties = {
  marginRight: "-16px", marginBottom: "-16px", marginLeft: "0px", top: "-8px", right: "auto", left: "-8px",
  width: "calc(100% + 16px)", padding: "8px", overflowX: "scroll",
};

const BODY_CLASS = "layout-fixed sidebar-expand-lg sidebar-mini bg-body-tertiary insp-cuerpo";

export type ClaroUser = { display_name: string; avatar_initial: string; role_label: string };
export type ClaroLayout = {
  breadcrumb: { text: string; url: string | null }[];
  display_name: string;
  role: string;
  initials: string;
};

// Physical (Tab) order of `includes/sidebar/opciones.html`; CSS `order` sets the visual one.
const SIDEBAR_DOM = ["inicio", "comunicados", "administracion-sistema", "configuracion-comedores", "ocr_upload", "tableros", "legajos"];
const SIDEBAR_ORDER: Record<string, number> = {
  inicio: 1, legajos: 2, tableros: 3, "administracion-sistema": 4, "configuracion-comedores": 5, ocr_upload: 6, comunicados: 7,
};
const ICON_IMAGES: Record<string, string> = {
  inicio: "/static/custom/img/iconos_sidebar/inicio.svg",
  legajos: "/static/custom/img/iconos_sidebar/legajos.svg",
  "configuracion-comedores": "/static/custom/img/iconos_sidebar/legajos.svg",
  tableros: "/static/custom/img/iconos_sidebar/tableros.svg",
  "administracion-sistema": "/static/custom/img/iconos_sidebar/administracion.svg",
};
const ICON_CLASSES: Record<string, string> = { comunicados: "bi bi-newspaper", mi_cuenta: "fas fa-user-circle" };

function Icon({ id }: { id: string }) {
  if (ICON_IMAGES[id]) return <img src={ICON_IMAGES[id]} alt="" />;
  if (ICON_CLASSES[id]) return <i className={`nav-icon ${ICON_CLASSES[id]}`} />;
  return null;
}

// The native page marks the link whose path contains the current route ("inspecciones/").
function isActive(href: string | null, pathname: string): boolean {
  const local = safeInternalPath(href);
  return local !== null && local !== "/" && pathname.startsWith(local);
}

function hasActive(item: NavigationNode, pathname: string): boolean {
  return isActive(item.href, pathname) || item.children.some((child) => hasActive(child, pathname));
}

// AdminLTE hides open treeviews (inline `display: none`) while the mobile sidebar is collapsed.
function SidebarItem({ item, pathname, nested = false, hideTree = false }: { item: NavigationNode; pathname: string; nested?: boolean; hideTree?: boolean }) {
  const [open, setOpen] = useState(() => hasActive(item, pathname));
  const order = SIDEBAR_ORDER[item.id];
  const style: CSSProperties | undefined = nested || order === undefined ? undefined
    : item.id === "comunicados" ? { order, borderBottom: "1px solid var(--sidebar-border-color)" } : { order };
  const liClass = nested ? "nav-item" : "nav-item nav-main-item";
  if (item.href !== null) {
    return (
      <li className={liClass} style={style}>
        <a href={safeInternalPath(item.href) ?? "/"} className={`nav-link${nested ? " nav-dot ms-2" : ""}${isActive(item.href, pathname) ? " active" : ""}`}>
          {!nested && <Icon id={item.id} />}
          <p>{item.label}</p>
        </a>
      </li>
    );
  }
  return (
    <li className={`${liClass}${open ? " menu-open" : ""}`} style={style}>
      <a href="#" className="nav-link" aria-expanded={open} onClick={(event) => { event.preventDefault(); setOpen(!open); }}>
        {!nested && <Icon id={item.id} />}
        <p>{item.label}</p>
        <i className="nav-arrow bi bi-chevron-right" />
      </a>
      <ul className="nav nav-treeview" style={hideTree && open ? { display: "none" } : undefined}>
        {item.children.map((child) => <SidebarItem key={`${child.id}:${child.label}`} item={child} pathname={pathname} nested hideTree={hideTree} />)}
      </ul>
    </li>
  );
}

function sidebarOrder(menu: NavigationNode[]): NavigationNode[] {
  const rank = (item: NavigationNode) => { const i = SIDEBAR_DOM.indexOf(item.id); return i === -1 ? SIDEBAR_DOM.length : i; };
  return [...menu].sort((a, b) => rank(a) - rank(b));
}

function useIsMobile(): boolean {
  const query = "(max-width: 991.98px)";
  const [isMobile, setIsMobile] = useState(() => window.matchMedia?.(query).matches ?? false);
  useEffect(() => {
    const media = window.matchMedia?.(query);
    if (!media) return undefined;
    const update = () => setIsMobile(media.matches);
    media.addEventListener?.("change", update);
    return () => media.removeEventListener?.("change", update);
  }, []);
  return isMobile;
}

export default function ClaroFrame({ title, user, layout, navigation, footerLabel, children }: {
  title: string;
  user: ClaroUser;
  layout: ClaroLayout;
  navigation: NavigationNode[];
  footerLabel: string;
  children: ReactNode;
}) {
  const pathname = window.location.pathname;
  const isMobile = useIsMobile();
  const [mobileOpen, setMobileOpen] = useState(false);

  useLayoutEffect(() => {
    const html = document.documentElement;
    const oldTheme = html.getAttribute("data-bs-theme");
    const oldBody = document.body.className;
    const oldTitle = document.title;
    const previous = [...document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]')].map((link) => ({ link, disabled: link.disabled }));
    for (const { link } of previous) link.disabled = true;
    const added = CLARO_STYLESHEETS.map((href) => {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      link.dataset.claroFrame = "";
      document.head.appendChild(link);
      return link;
    });
    const root = document.getElementById("root");
    root?.style.setProperty("display", "contents");
    html.setAttribute("data-bs-theme", "light");
    document.title = `SISOC - ${title}`;
    return () => {
      for (const link of added) link.remove();
      for (const { link, disabled } of previous) link.disabled = disabled;
      root?.style.removeProperty("display");
      if (oldTheme === null) html.removeAttribute("data-bs-theme"); else html.setAttribute("data-bs-theme", oldTheme);
      document.body.className = oldBody;
      document.title = oldTitle;
    };
  }, [title]);

  // AdminLTE marks the body `app-loaded` and collapses the sidebar below lg.
  useLayoutEffect(() => {
    document.body.className = `${BODY_CLASS}${isMobile ? (mobileOpen ? " sidebar-open" : " sidebar-collapse") : ""} app-loaded`;
  }, [isMobile, mobileOpen]);

  useEffect(() => {
    if (!isMobile || !mobileOpen) return undefined;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") setMobileOpen(false); };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [isMobile, mobileOpen]);

  const account = navigation.find((item) => item.id === "mi_cuenta");
  const menu = sidebarOrder(navigation.filter((item) => item.id !== "mi_cuenta"));
  const last = layout.breadcrumb.length - 1;
  return (
    <div className="app-wrapper">
      <aside className="app-sidebar shadow" data-bs-theme="dark">
        <div className="sidebar-brand">
          <a href="/inicio/" className="brand-link" aria-label="Inicio de SISOC">
            <img src="/static/custom/img/logoBlanco.png" alt="SISOC" className="brand-image" />
          </a>
        </div>
        {/* OverlayScrollbars (AdminLTE) wraps the menu in a viewport: the menu keeps its content
            height, so `mt-auto` on "Mi cuenta" does not push the other items down. */}
        <div className="sidebar-wrapper" data-overlayscrollbars="host">
          <div data-overlayscrollbars-viewport="scrollbarHidden" style={OVERLAY_VIEWPORT}>
          <nav>
            <ul className="nav sidebar-menu flex-column" data-lte-toggle="treeview" role="menu" data-accordion="false">
              <li className="nav-item user-info mb-2 mt-2">
                <div className="user-panel d-flex align-items-center p-3">
                  <div className="user-avatar me-3">
                    <div className="avatar-circle d-flex align-items-center justify-content-center bg-primary text-white rounded-circle" style={{ width: "45px", height: "45px", fontSize: "16px", fontWeight: 600 }}>
                      {user.avatar_initial}
                    </div>
                  </div>
                  <div className="info flex-grow-1">
                    <p className="mb-1 text-white fw-bold">{user.display_name}</p>
                    <p className="mb-0 text-white-50 small">{user.role_label}</p>
                  </div>
                </div>
              </li>
              {menu.map((item) => <SidebarItem key={item.id} item={item} pathname={pathname} hideTree={isMobile && !mobileOpen} />)}
              {account && (
                <li className="nav-item mt-auto border-top pt-2">
                  <a href={safeInternalPath(account.href) ?? "/"} className={`nav-link${isActive(account.href, pathname) ? " active" : ""}`}>
                    <Icon id="mi_cuenta" />
                    <p>{account.label}</p>
                  </a>
                </li>
              )}
            </ul>
          </nav>
          </div>
        </div>
      </aside>
      <header className="app-header insp-cabecera">
        <button className="insp-cabecera-menu d-lg-none" type="button" data-lte-toggle="sidebar" aria-label="Abrir menú" aria-expanded={mobileOpen} onClick={() => setMobileOpen(!mobileOpen)}>
          <i className="bi bi-list" aria-hidden="true" />
        </button>
        <nav className="insp-migas" aria-label="Ubicación">
          <ol>
            {layout.breadcrumb.map((item, index) => (
              <li key={`${index}:${item.text}`}>
                {/* The native whitespace after the "/" separator renders as a space. */}
                {" "}
                {item.url && index !== last ? <a href={safeInternalPath(item.url) ?? "/"}>{item.text}</a> : <strong aria-current="page">{item.text}</strong>}
                {" "}
              </li>
            ))}
          </ol>
        </nav>
        <div className="insp-cabecera-usuario">
          <span className="insp-cabecera-nombre">{layout.display_name}</span>
          {layout.role && <>{" "}<span className="insp-cabecera-rol">{layout.role}</span></>}
          {" "}<span className="insp-avatar insp-avatar-grande" aria-hidden="true">{layout.initials}</span>
          {" "}<form method="post" action="/logout/" className="d-inline">
            <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
            <button type="submit" className="insp-cabecera-salir" aria-label="Cerrar sesión">
              <i className="bi bi-box-arrow-right" aria-hidden="true" />
            </button>
          </form>
        </div>
      </header>
      <main className="app-main insp-main">
        <div className="insp-contenido">{children}</div>
      </main>
      <footer className="app-footer">
        <div className="footer-content">
          <img src="/static/custom/img/Presidencia_footer.svg" alt="Presidencia Logo" className="footer-logo img-fluid" />
          <a href="/novedades/" className="footer-secondary-link" aria-label={footerLabel}>
            <i className="bi bi-clock-fill" />
            <span>{footerLabel}</span>
          </a>
        </div>
      </footer>
      <aside className="control-sidebar control-sidebar-dark" />
    </div>
  );
}
