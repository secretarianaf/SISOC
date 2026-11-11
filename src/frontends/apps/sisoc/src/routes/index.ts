import { accountRoute } from "./account";
import { actividadesPnudRoute } from "./actividadesPnud";
import { businessRoute } from "./business";
import { categoriasRoute } from "./categorias";
import { cdiObservacionesRoute } from "./cdiObservaciones";
import { cdiReportesRoute } from "./cdiReportes";
import { cdfCentroFormRoute } from "./cdfCentroForm";
import { cdfCentrosRoute } from "./cdfCentros";
import { duplasRoute } from "./duplas";
import { duplasFormRoute } from "./duplasFormRoute";
import { groupsRoute } from "./groups";
import { inicioRoute } from "./inicio";
import { insumosRoute } from "./insumos";
import { inspeccionesActaDetalleRoute } from "./inspeccionesActaDetalle";
import { inspeccionesActasRoute } from "./inspeccionesActas";
import { loginRoute } from "./login";
import { montosRoute } from "./montos";
import { pasRoute } from "./pas";
import { passwordChangeRoute } from "./passwordChange";
import { passwordResetRoute } from "./passwordReset";
import { requiredPasswordRoute } from "./requiredPassword";
import { bulkCredentialsRoute } from "./bulkCredentials";
import { userImportRoute } from "./userImport";
import type { RouteDefinition, ShellRouteDefinition } from "./types";

export type { RouteDefinition, ShellRouteDefinition } from "./types";

/**
 * Pages inside the business shell, checked in order. `insumosRoute` matches
 * every path, so it must stay last.
 */
export const SHELL_ROUTES: ShellRouteDefinition[] = [categoriasRoute, insumosRoute];

/**
 * Top-level routes, checked in order; the first match renders. Identity routes
 * own their API bootstrap. `businessRoute` matches every path, so it must stay
 * last. To add a screen: create `routes/<unit>.tsx` (+ test) and register it here.
 */
export const ROUTES: RouteDefinition[] = [
  groupsRoute,
  inicioRoute,
  loginRoute,
  requiredPasswordRoute,
  accountRoute,
  passwordChangeRoute,
  passwordResetRoute,
  userImportRoute,
  bulkCredentialsRoute,
  inspeccionesActasRoute,
  inspeccionesActaDetalleRoute,
  cdiReportesRoute,
  cdiObservacionesRoute,
  cdfCentrosRoute,
  cdfCentroFormRoute,
  duplasRoute,
  duplasFormRoute,
  montosRoute,
  actividadesPnudRoute,
  pasRoute,
  businessRoute(SHELL_ROUTES),
];

export function findRoute(pathname: string, routes: readonly RouteDefinition[] = ROUTES) {
  for (const route of routes) {
    const params = route.match(pathname);
    if (params !== null) return { route, params };
  }
  return null;
}
