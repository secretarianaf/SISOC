import { accountRoute } from "./account";
import { acompanamientosRoute } from "./acompanamientos";
import { actividadesPnudRoute } from "./actividadesPnud";
import { admisionesTemplatesRoute } from "./admisionesTemplates";
import { admisionesInformeDetalleRoute } from "./admisionesInformeDetalle";
import { businessRoute } from "./business";
import { categoriasRoute } from "./categorias";
import { cdiCentrosRoute } from "./cdiCentros";
import { cdiNominaRoute } from "./cdiNomina";
import { cdiObservacionesRoute } from "./cdiObservaciones";
import { cdiReportesRoute } from "./cdiReportes";
import { cdfBeneficiariosRoute } from "./cdfBeneficiarios";
import { cdfCentroFormRoute } from "./cdfCentroForm";
import { cdfCentrosRoute } from "./cdfCentros";
import { datacalleCasosRoute } from "./datacalleCasos";
import { datacalleRelevamientosRoute } from "./datacalleRelevamientos";
import { dispositivosRoute } from "./dispositivos";
import { cdfCentroUsuarioRoute } from "./cdfCentroUsuario";
import { duplasRoute } from "./duplas";
import { expedientesPagosRoute } from "./expedientesPagos";
import { rendicionFinalRoute } from "./rendicionFinal";
import { rendicionMensualRoute } from "./rendicionMensual";
import { comunicadosRoute } from "./comunicados";
import { organizacionConvenioRoute } from "./organizacionConvenio";
import { organizacionDocumentosRoute } from "./organizacionDocumentos";
import { organizacionFirmantesRoute } from "./organizacionFirmantes";
import { organizacionRendicionesRoute } from "./organizacionRendiciones";
import { organizacionesRoute } from "./organizaciones";
import { relevamientosRoute } from "./relevamientos";
import { relevamientosActasRoute } from "./relevamientosActas";
import { relevamientosFormsRoute } from "./relevamientosForms";
import { relevamientosSeguimientosRoute } from "./relevamientosSeguimientos";
import { duplasFormRoute } from "./duplasFormRoute";
import { groupsRoute } from "./groups";
import { inicioRoute } from "./inicio";
import { insumosRoute } from "./insumos";
import { inspeccionesActaDetalleRoute } from "./inspeccionesActaDetalle";
import { inspeccionesActasRoute } from "./inspeccionesActas";
import { inspeccionesAsignacionesRoute } from "./inspeccionesAsignaciones";
import { inspeccionesEscuelasRoute } from "./inspeccionesEscuelas";
import { inspeccionesTableroRoute } from "./inspeccionesTablero";
import { loginRoute } from "./login";
import { montosRoute } from "./montos";
import { ocrRoute } from "./ocr";
import { pasRoute } from "./pas";
import { pasInformesRoute } from "./pasInformes";
import { pasInformesGenerarRoute } from "./pasInformesGenerar";
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
  inspeccionesAsignacionesRoute,
  inspeccionesEscuelasRoute,
  inspeccionesTableroRoute,
  cdiReportesRoute,
  cdiObservacionesRoute,
  cdiCentrosRoute,
  cdiNominaRoute,
  cdfCentrosRoute,
  cdfCentroFormRoute,
  dispositivosRoute,
  cdfCentroUsuarioRoute,
  cdfBeneficiariosRoute,
  datacalleRelevamientosRoute,
  datacalleCasosRoute,
  duplasRoute,
  duplasFormRoute,
  montosRoute,
  actividadesPnudRoute,
  pasRoute,
  pasInformesRoute,
  pasInformesGenerarRoute,
  admisionesTemplatesRoute,
  admisionesInformeDetalleRoute,
  acompanamientosRoute,
  expedientesPagosRoute,
  rendicionMensualRoute,
  rendicionFinalRoute,
  comunicadosRoute,
  ocrRoute,
  organizacionesRoute,
  organizacionConvenioRoute,
  organizacionDocumentosRoute,
  organizacionFirmantesRoute,
  organizacionRendicionesRoute,
  relevamientosRoute,
  relevamientosSeguimientosRoute,
  relevamientosActasRoute,
  relevamientosFormsRoute,
  businessRoute(SHELL_ROUTES),
];

export function findRoute(pathname: string, routes: readonly RouteDefinition[] = ROUTES) {
  for (const route of routes) {
    const params = route.match(pathname);
    if (params !== null) return { route, params };
  }
  return null;
}
