import { vi } from "vitest";

// Shared synthetic web-session fixture for App and route tests.
export const readyContext = {
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

export function setViewport(isMobile: boolean) {
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
