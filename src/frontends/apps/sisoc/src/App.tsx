import { useEffect, useId, useState, type ReactNode } from "react";
import { crearCliente, leerCookie } from "@sisoc/api";
import InsumosAccessError from "./InsumosAccessError";
import InsumosList from "./InsumosList";
import InsumosForm from "./InsumosForm";
import InsumosCategoriaForm from "./InsumosCategoriaForm";
import InsumosCategoriasList from "./InsumosCategoriasList";
import InsumosToast from "./InsumosToast";
import Login from "./Login";
import Account from "./Account";
import Groups from "./Groups";
import PasswordChange from "./PasswordChange";
import PendingSurvey from "./PendingSurvey";
import RequiredPasswordChange, { type RequiredPasswordPresentation } from "./RequiredPasswordChange";
import { safeInternalPath, validateInsumosStatus, type WebAccessState } from "./webAccess";
import "./shell.css";

type AccessState = WebAccessState;

type NavigationNode = {
  id: string;
  label: string;
  href: string | null;
  children: NavigationNode[];
};

type WebSessionContext = {
  user: {
    username: string;
    display_name: string;
    avatar_initial: string;
    role_label: string;
  } | null;
  access: { state: AccessState; required_action_url: string | null };
  navigation: NavigationNode[];
  capabilities: {
    insumos: {
      can_view: boolean;
      show_management: boolean;
      show_categories: boolean;
    };
  };
  footer_version_label: string;
};

type ReadyContext = WebSessionContext & {
  user: NonNullable<WebSessionContext["user"]>;
};

type LoadState =
  | { status: "loading" }
  | { status: "ready"; context: ReadyContext }
  | { status: "prerequisite"; context: WebSessionContext }
  | { status: "forbidden" }
  | { status: "error" };

const webClient = crearCliente("/api");
const ACCESS_STATES = new Set<AccessState>([
  "ready",
  "web_access_denied",
  "password_change_required",
  "profile_confirmation_required",
  "mandatory_survey_required",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object";
}

function internalPath(value: unknown): string | null {
  return safeInternalPath(value);
}

function isNavigationNode(value: unknown): value is NavigationNode {
  if (!value || typeof value !== "object") return false;
  const node = value as Record<string, unknown>;
  return (
    typeof node.id === "string" &&
    typeof node.label === "string" &&
    (node.href === null || internalPath(node.href) !== null) &&
    Array.isArray(node.children) &&
    node.children.every(isNavigationNode)
  );
}

function isWebSessionContext(value: unknown): value is WebSessionContext {
  if (!value || typeof value !== "object") return false;
  const context = value as Record<string, unknown>;
  const access = context.access as Record<string, unknown> | null;
  const user = context.user as Record<string, unknown> | null;
  const capabilities = context.capabilities as Record<string, unknown> | null;
  const insumos = capabilities?.insumos as Record<string, unknown> | null;
  if (
    !access ||
    !ACCESS_STATES.has(access.state as AccessState) ||
    (access.required_action_url !== null &&
      internalPath(access.required_action_url) === null) ||
    !Array.isArray(context.navigation) ||
    !context.navigation.every(isNavigationNode) ||
    typeof context.footer_version_label !== "string" ||
    !insumos ||
    typeof insumos.can_view !== "boolean" ||
    typeof insumos.show_management !== "boolean" ||
    typeof insumos.show_categories !== "boolean"
  ) {
    return false;
  }
  return (
    user === null ||
    (typeof user.username === "string" &&
      typeof user.display_name === "string" &&
      typeof user.avatar_initial === "string" &&
      typeof user.role_label === "string")
  );
}

function isCompleteReadyContext(
  context: WebSessionContext,
): context is ReadyContext {
  const requiredItems = new Set(context.navigation.map((item) => item.id));
  return (
    context.access.state === "ready" &&
    context.user !== null &&
    ["inicio", "legajos", "mi_cuenta"].every((id) => requiredItems.has(id))
  );
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

function loginPath(): string {
  const next = window.location.pathname + window.location.search;
  return `/login/?next=${encodeURIComponent(next)}`;
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
  };
  const src = localIcons[id];
  if (src) return <img src={src} alt="" />;
  const iconClass = iconClasses[id];
  if (iconClass) return <i className={`nav-icon ${iconClass}`} aria-hidden="true" />;
  return null;
}

const CATEGORY_LIST_PATH = "/v2/sisoc/insumos/categorias/";

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
  isNested = false,
  previewLinks = true,
  legacyOrder,
}: {
  item: NavigationNode;
  pathname: string;
  isMobile: boolean;
  onNavigate: () => void;
  isNested?: boolean;
  previewLinks?: boolean;
  legacyOrder?: number;
}) {
  const controlId = useId();
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});
  const isAccountItem = item.id === "mi_cuenta";
  const separatorClass = item.id === "comunicados" ? " sisoc-nav-comunicados" : "";
  const orderClass = legacyOrder === undefined ? " order-1" : "";
  const orderStyle = legacyOrder === undefined ? undefined : { order: legacyOrder };
  const localHref = projectedHref(item, previewLinks);
  const active = localHref !== null && (
    localHref === pathname ||
    (previewLinks && item.id === "insumos_listar" &&
      (pathname === "/v2/sisoc/insumos" ||
        pathname.startsWith("/v2/sisoc/insumos/")))
  );
  const descendantActive = item.children.some((child) =>
    containsActivePath(child, pathname, previewLinks),
  );
  const expanded = overrides[item.id] ?? descendantActive;
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
          className={`nav-link${isNested ? " nav-dot ms-2" : ""}${active ? " active" : ""}`}
          href={localHref ?? "/"}
          aria-current={active ? "page" : undefined}
          onClick={onNavigate}
        >
          <ShellIcon id={item.id} />
          <p>{item.label}</p>
        </a>
      </li>
    );
  }

  return (
    <li className={`nav-item nav-main-item${orderClass}${expanded ? " menu-open" : ""}${separatorClass}`} style={orderStyle}>
      <a
        className="nav-link"
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
        <ShellIcon id={item.id} />
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
            isNested
            previewLinks={previewLinks}
          />
        ))}
      </ul>
    </li>
  );
}

function AccessMessage({ context }: { context: WebSessionContext }) {
  return <InsumosAccessError prerequisite={context.access} />;
}

function ErrorMessage() {
  return (
    <main className="sisoc-message" role="main">
      <section className="sisoc-message-card" role="alert">
        <h1>No se pudo verificar tu sesión</h1>
        <p>Volvé a ingresar para continuar en SISOC.</p>
        <a className="sisoc-action-link" href={loginPath()}>
          Iniciar sesión
        </a>
      </section>
    </main>
  );
}

function SisocShell({
  context,
  content,
  pageTitle,
  heading,
  overlays,
  previewLinks = true,
  breadcrumb,
  hideBack = false,
}: {
  context: Pick<ReadyContext, "user" | "navigation" | "footer_version_label"> & {
    capabilities?: ReadyContext["capabilities"];
  };
  content?: ReactNode;
  pageTitle?: string;
  heading?: string;
  overlays?: ReactNode;
  previewLinks?: boolean;
  breadcrumb?: ReactNode;
  hideBack?: boolean;
}) {
  const isMobile = useIsMobile();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [pathname, setPathname] = useState(() => window.location.pathname);
  // Native groups-list markup does not mark its Administration branch active.
  const navigationPath = !previewLinks && pathname === "/grupos/" ? "" : pathname;
  const [successMessage, setSuccessMessage] = useState("");
  // Category routes keep the exact public slashes of the source circuit.
  const categoryRoute = pathname.startsWith(CATEGORY_LIST_PATH);
  const formRoute = categoryRoute
    ? pathname.match(/^\/v2\/sisoc\/insumos\/categorias\/(?:(crear)|([0-9]+)\/(editar|eliminar))$/)
    : pathname.match(/^\/v2\/sisoc\/insumos\/(?:(crear)\/?|([0-9]+)\/(editar|eliminar)\/?)$/);
  const action = formRoute?.[1] === "crear" ? "crear" : formRoute?.[3] as "editar" | "eliminar" | undefined;
  useEffect(() => {
    const previousTitle = document.title;
    const title = categoryRoute
      ? action === "crear" ? "Nueva categoría" : action === "editar" ? "Editar categoría" : action === "eliminar" ? "Eliminar categoría" : "Categorías de insumos"
      : action === "crear" ? "Nuevo insumo" : action === "editar" ? "Editar insumo" : action === "eliminar" ? "Eliminar insumo" : "Insumos";
    document.title = `SISOC - ${pageTitle ?? title}`;
    return () => { document.title = previousTitle; };
  }, [action, categoryRoute, pageTitle]);
  const returnToList = (message = "") => {
    window.history.pushState({}, "", categoryRoute ? CATEGORY_LIST_PATH : "/v2/sisoc/insumos/");
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
                <a className="btn btn-secondary btn-sm sisoc-volver" href="/">
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
              <div className="row" />
            </div>
          </div>
          <div className="app-content">
            <div className="container-fluid">
              {successMessage && <InsumosToast key={successMessage} message={successMessage} />}
              {content ?? (categoryRoute ? (action
                ? <InsumosCategoriaForm key={pathname} action={action} id={formRoute?.[2]} onComplete={returnToList} onCancel={() => returnToList()} />
                : <InsumosCategoriasList key={pathname} />
              ) : action ? <InsumosForm key={pathname} action={action} id={formRoute?.[2]} onComplete={returnToList} onCancel={() => returnToList()} /> : <InsumosList
                showManagement={context.capabilities?.insumos.show_management ?? false}
                showCategories={context.capabilities?.insumos.show_categories ?? false}
              />)}
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

function BusinessApp() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();
    webClient
      .get<WebSessionContext>("web/session/", {
        signal: controller.signal,
        validateStatus: validateInsumosStatus,
      })
      .then(({ data, status }) => {
        if (!mounted) return;
        if (status === 403) {
          if (isWebSessionContext(data) && data.access.state !== "ready") {
            setState({ status: "prerequisite", context: data });
          } else {
            setState({ status: "forbidden" });
          }
        } else if (!isWebSessionContext(data)) {
          setState({ status: "error" });
        } else if (data.access.state !== "ready") {
          setState({ status: "prerequisite", context: data });
        } else if (isCompleteReadyContext(data)) {
          setState({ status: "ready", context: data });
        } else {
          setState({ status: "error" });
        }
      })
      .catch((error: unknown) => {
        if (!mounted) return;
        const status =
          isRecord(error) && isRecord(error.response) && typeof error.response.status === "number"
            ? error.response.status
            : undefined;
        setState({ status: status === 403 ? "forbidden" : "error" });
      });
    return () => {
      mounted = false;
      controller.abort();
    };
  }, []);

  if (state.status === "loading") {
    return (
      <main className="sisoc-message" role="status">
        Cargando SISOC…
      </main>
    );
  }
  if (state.status === "forbidden") return <InsumosAccessError />;
  if (state.status === "error") return <ErrorMessage />;
  if (state.status === "prerequisite") return <AccessMessage context={state.context} />;
  return <SisocShell context={state.context} />;
}

// Identity pages reuse the legacy frame from their own presentation DTO, never business capabilities.
function legacyIdentityFrame(
  content: ReactNode,
  presentation: RequiredPasswordPresentation,
  pageTitle: string,
  heading = pageTitle,
  overlays?: ReactNode,
  breadcrumb?: ReactNode,
  hideBack = false,
) {
  return <SisocShell
    context={{ user: presentation.user, navigation: presentation.legacy_frame_navigation, footer_version_label: presentation.footer_version_label }}
    content={content}
    pageTitle={pageTitle}
    heading={heading}
    overlays={overlays}
    breadcrumb={breadcrumb}
    hideBack={hideBack}
    previewLinks={false}
  />;
}

function requiredPasswordFrame(content: ReactNode, presentation: RequiredPasswordPresentation) {
  return legacyIdentityFrame(content, presentation, "Cambio obligatorio de contraseña", "Actualizar contraseña");
}

function accountFrame(content: ReactNode, presentation: RequiredPasswordPresentation, overlays?: ReactNode) {
  return legacyIdentityFrame(content, presentation, "Mi cuenta", "Mi cuenta", overlays);
}

function confirmationFrame(content: ReactNode, presentation: RequiredPasswordPresentation, overlays?: ReactNode) {
  return legacyIdentityFrame(content, presentation, "Confirma tus datos personales", "Confirma tus datos personales", overlays);
}

// Public identity paths own their API bootstrap; every other path keeps the business shell.
export default function App() {
  const groupEdit = window.location.pathname.match(/^\/grupos\/editar\/([0-9]+)\/$/);
  if (window.location.pathname === "/grupos/" || window.location.pathname === "/grupos/crear/" || groupEdit) {
    const mode = groupEdit ? "edit" : window.location.pathname === "/grupos/crear/" ? "create" : "list";
    return <Groups
      mode={mode}
      id={groupEdit?.[1]}
      renderFrame={(content, presentation, title, breadcrumb) =>
        legacyIdentityFrame(content, presentation, mode === "list" ? title : "Grupos", title, undefined, breadcrumb)}
    />;
  }
  if (window.location.pathname === "/inicio/") {
    // The source home has no back button and an empty heading row.
    return <PendingSurvey renderFrame={(content, presentation, overlays) =>
      legacyIdentityFrame(content, presentation, "", "", overlays, undefined, true)} />;
  }
  if (window.location.pathname === "/" || window.location.pathname === "/login/") {
    return <Login />;
  }
  if (window.location.pathname === "/password/first-change/") {
    return <RequiredPasswordChange renderFrame={requiredPasswordFrame} />;
  }
  if (window.location.pathname === "/mi-cuenta/") {
    return <Account mode="account" renderFrame={accountFrame} />;
  }
  if (window.location.pathname === "/mi-cuenta/confirmar/") {
    return <Account mode="confirm" renderFrame={confirmationFrame} />;
  }
  // The voluntary form and its done page keep the installed admin template frame.
  if (window.location.pathname === "/password_change/") {
    return <PasswordChange mode="form" />;
  }
  if (window.location.pathname === "/password_change/done/") {
    return <PasswordChange mode="done" />;
  }
  return <BusinessApp />;
}
