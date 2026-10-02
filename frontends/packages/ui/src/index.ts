/**
 * Superficie publica de @sisoc/ui.
 *
 * Conviven las dos apps del monorepo: VPSL usa `getTheme` y `V2Layout`;
 * Celiaquia usa `buildTheme`, su propio AppShell y los componentes de abajo.
 * No hay colision de nombres, asi que se exportan los dos conjuntos.
 */

// --- VPSL ------------------------------------------------------------------
export { brand, getTheme } from "./theme";
export { V2Layout } from "./layout";
export type { V2Module } from "./layout";

// --- Celiaquia -------------------------------------------------------------
export { buildTheme } from "./theme.celiaquia";
export { severidad } from "./theme.celiaquia";
export { ThemeProvider, useColorMode } from "./ThemeProvider";

export { AppShell } from "./layout/AppShell";
export type { AppShellProps } from "./layout/AppShell";
export { Header } from "./layout/Header";
export { Footer } from "./layout/Footer";
export { Sidebar, SIDEBAR_WIDTH } from "./layout/Sidebar";
export type { NavNode, NavSection } from "./layout/Sidebar";

export { default as Stack } from "./components/Stack";
export { default as PageHeader } from "./components/PageHeader";
export type { Crumb } from "./components/PageHeader";
export { default as SectionCard } from "./components/SectionCard";
export { default as StatCard } from "./components/StatCard";
export { default as SearchField } from "./components/SearchField";
export { default as FilterChipGroup } from "./components/FilterChipGroup";
export { default as NavigationCard } from "./components/NavigationCard";
export {
  default as StateChip,
  toneExpediente,
  toneRevision,
  toneSintys,
  toneCupo,
  toneMovimiento,
} from "./components/StateChip";
export type { StateTone } from "./components/StateChip";
export {
  formatearFecha,
  formatearFechaHora,
  normalizarFechaEditable,
} from "./fechas";
