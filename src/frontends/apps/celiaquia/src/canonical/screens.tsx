import type { ComponentType } from "react";
import { CuposScreen, CupoProvinciaScreen } from "./CuposScreens";
import { PagosScreen, PagoDetalleScreen } from "./PagosScreens";
import { TableroScreen } from "./TableroScreen";
import { ExpedienteNuevoScreen, ExpedienteEditarScreen } from "./ExpedienteFormScreens";
import { ExpedienteDetalleScreen } from "./ExpedienteDetalleScreen";

export type CanonicalParams = Record<string, string>;
type Screen = { pattern: RegExp; component: ComponentType<{ params: CanonicalParams }> };

/**
 * Canonical Django URLs served by the React shell. Each entry needs its
 * `sisoc-celiaquia-<screen>` marker in index.html; without it Django keeps
 * answering with the native template.
 */
const SCREENS: Screen[] = [
  { pattern: /^\/celiaquia\/expedientes\/nuevo\/$/, component: ExpedienteNuevoScreen },
  { pattern: /^\/celiaquia\/expedientes\/(?<pk>\d+)\/editar\/$/, component: ExpedienteEditarScreen },
  { pattern: /^\/celiaquia\/expedientes\/(?<pk>\d+)\/$/, component: ExpedienteDetalleScreen },
  { pattern: /^\/celiaquia\/cupos\/$/, component: CuposScreen },
  { pattern: /^\/celiaquia\/cupos\/provincia\/(?<provinciaId>\d+)\/$/, component: CupoProvinciaScreen },
  { pattern: /^\/celiaquia\/tablero\/$/, component: TableroScreen },
  { pattern: /^\/celiaquia\/pagos\/provincia\/(?<provinciaId>\d+)\/$/, component: PagosScreen },
  { pattern: /^\/celiaquia\/pagos\/expediente\/(?<pagoId>\d+)\/$/, component: PagoDetalleScreen },
];

export function matchCanonicalScreen(pathname: string) {
  for (const screen of SCREENS) {
    const match = screen.pattern.exec(pathname);
    if (match) return { Component: screen.component, params: { ...(match.groups ?? {}) } };
  }
  return null;
}
