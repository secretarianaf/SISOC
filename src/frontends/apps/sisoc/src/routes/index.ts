import { accountRoute } from "./account";
import { acompanamientosRoute } from "./acompanamientos";
import { comedoresRoute } from "./comedores";
import { comedorBajaRoute } from "./comedorBaja";
import { comedorFichaRoute } from "./comedorFicha";
import { comedorFormRoute } from "./comedorForm";
import { comedorConvenioRoute } from "./comedorConvenio";
import { comedorTarjetaRoute } from "./comedorTarjeta";
import { comedorNominaRoute } from "./comedorNomina";
import { comedorAsistenciaHistorialRoute } from "./comedorAsistenciaHistorial";
import { comedorCertificacionesRoute } from "./comedorCertificaciones";
import { comedorTransaccionesRoute } from "./comedorTransacciones";
import { actividadesPnudRoute } from "./actividadesPnud";
import { admisionesTemplatesRoute } from "./admisionesTemplates";
import { admisionesInformeDetalleRoute } from "./admisionesInformeDetalle";
import { admisionesInformeEditorRoute } from "./admisionesInformeEditor";
import { admisionesLegalesRoute } from "./admisionesLegales";
import { admisionesSeguimientoRoute } from "./admisionesSeguimiento";
import { businessRoute } from "./business";
import { categoriasRoute } from "./categorias";
import { coreArquitecturaRoute } from "./coreArquitectura";
import { coreNovedadesRoute } from "./coreNovedades";
import { corePapeleraRoute } from "./corePapelera";
import { corePapeleraRestaurarRoute } from "./corePapeleraRestaurar";
import { coreProgramaBajaRoute } from "./coreProgramaBaja";
import { coreProgramaFormRoute } from "./coreProgramaForm";
import { coreProgramasRoute } from "./coreProgramas";
import { ciudadano360Route } from "./ciudadano360";
import { ciudadanoBajaRoute } from "./ciudadanoBaja";
import { ciudadanoFamiliarRoute } from "./ciudadanoFamiliar";
import { ciudadanoFormRoute } from "./ciudadanoForm";
import { auditoriaEventoRoute } from "./auditoriaEvento";
import { auditoriaListadoRoute, ciudadanoHistorialRoute } from "./ciudadanoHistorial";
import { cdiCentroDetalleRoute } from "./cdiCentroDetalle";
import { cdiCentroFormRoute } from "./cdiCentroForm";
import { cdiDocumentacionRoute } from "./cdiDocumentacion";
import { cdiCentrosRoute } from "./cdiCentros";
import { cdiNominaRoute } from "./cdiNomina";
import { cdiNominaListaRoute } from "./cdiNominaLista";
import { cdiObservacionesRoute } from "./cdiObservaciones";
import { cdiTrabajadorRoute } from "./cdiTrabajadores";
import { cdiTrabajadorFormRoute } from "./cdiTrabajadoresForm";
import { cdiFormulariosListaRoute, cdiFormularioDetalleRoute } from "./cdiFormularios";
import { cdiFormularioFormRoute } from "./cdiFormulariosForm";
import { comedorIntervencionesRoute } from "./comedorIntervenciones";
import { comedorObservacionesRoute } from "./comedorObservaciones";
import { comedorColaboradoresRoute } from "./comedorColaboradores";
import { comedorActividadesRoute } from "./comedorActividades";
import { comedorCursosRoute } from "./comedorCursos";
import { cdiReportesRoute } from "./cdiReportes";
import { cdfActividadFormRoute } from "./cdfActividadForm";
import { cdfActividadListRoute } from "./cdfActividadList";
import { cdfActividadRoute } from "./cdfActividades";
import { cdfAsistenciaRoute } from "./cdfAsistencia";
import { cdiDestinatarioFormRoute } from "./cdiDestinatarioForm";
import { cdiUsuariosGenerarRoute } from "./cdiUsuariosGenerar";
import { cdfBeneficiariosRoute } from "./cdfBeneficiarios";
import { cdfParticipantesRoute } from "./cdfParticipantes";
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
import { pasCrucesRoute } from "./pasCruces";
import { pasInformesGenerarRoute } from "./pasInformesGenerar";
import { passwordChangeRoute } from "./passwordChange";
import { passwordResetRoute } from "./passwordReset";
import { requiredPasswordRoute } from "./requiredPassword";
import { bulkCredentialsRoute } from "./bulkCredentials";
import { userImportRoute } from "./userImport";
import { usuariosRoute } from "./usuarios";
import { vatAsistenciaRoute } from "./vatAsistencia";
import { vatInscripcionOfertaRoute } from "./vatInscripcionOferta";
import { vatInscripcionOfertaFormRoute } from "./vatInscripcionOfertaForm";
import { vatEvaluacionesRoute } from "./vatEvaluaciones";
import { vatEvaluacionesFormRoute } from "./vatEvaluacionesForm";
import { vatParametriaDetalleRoute } from "./vatParametriaDetalle";
import { vatReporteRoute } from "./vatReporte";
import { vatResultadosRoute } from "./vatResultados";
import { vatResultadosFormRoute } from "./vatResultadosForm";
import { vatVouchersFormRoute } from "./vatVouchersForm";
import { vatVouchersRoute } from "./vatVouchers";
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
  usuariosRoute,
  bulkCredentialsRoute,
  inspeccionesActasRoute,
  inspeccionesActaDetalleRoute,
  inspeccionesAsignacionesRoute,
  inspeccionesEscuelasRoute,
  inspeccionesTableroRoute,
  cdiReportesRoute,
  cdiObservacionesRoute,
  cdiCentrosRoute,
  cdiCentroDetalleRoute,
  cdiCentroFormRoute,
  cdiNominaRoute,
  cdiNominaListaRoute,
  cdiDocumentacionRoute,
  cdiTrabajadorRoute,
  cdiTrabajadorFormRoute,
  cdiFormulariosListaRoute,
  cdiFormularioDetalleRoute,
  cdiFormularioFormRoute,
  cdiUsuariosGenerarRoute,
  cdiDestinatarioFormRoute,
  cdfCentrosRoute,
  cdfCentroFormRoute,
  dispositivosRoute,
  cdfCentroUsuarioRoute,
  cdfBeneficiariosRoute,
  cdfActividadRoute,
  cdfActividadListRoute,
  cdfActividadFormRoute,
  cdfAsistenciaRoute,
  cdfParticipantesRoute,
  datacalleRelevamientosRoute,
  datacalleCasosRoute,
  duplasRoute,
  duplasFormRoute,
  montosRoute,
  actividadesPnudRoute,
  pasRoute,
  pasCrucesRoute,
  pasInformesRoute,
  pasInformesGenerarRoute,
  admisionesTemplatesRoute,
  admisionesInformeDetalleRoute,
  admisionesInformeEditorRoute,
  admisionesSeguimientoRoute,
  admisionesLegalesRoute,
  acompanamientosRoute,
  comedoresRoute,
  comedorBajaRoute,
  comedorFichaRoute,
  comedorFormRoute,
  comedorConvenioRoute,
  comedorTarjetaRoute,
  comedorNominaRoute,
  comedorAsistenciaHistorialRoute,
  comedorCertificacionesRoute,
  comedorTransaccionesRoute,
  expedientesPagosRoute,
  rendicionMensualRoute,
  rendicionFinalRoute,
  comunicadosRoute,
  comedorIntervencionesRoute,
  comedorObservacionesRoute,
  comedorColaboradoresRoute,
  comedorActividadesRoute,
  comedorCursosRoute,
  vatVouchersRoute,
  vatEvaluacionesRoute,
  vatEvaluacionesFormRoute,
  vatResultadosRoute,
  vatResultadosFormRoute,
  vatReporteRoute,
  vatVouchersFormRoute,
  vatParametriaDetalleRoute,
  vatAsistenciaRoute,
  vatInscripcionOfertaRoute,
  vatInscripcionOfertaFormRoute,
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
  ciudadano360Route,
  ciudadanoBajaRoute,
  ciudadanoFamiliarRoute,
  ciudadanoFormRoute,
  ciudadanoHistorialRoute,
  auditoriaListadoRoute,
  auditoriaEventoRoute,
  coreNovedadesRoute,
  coreArquitecturaRoute,
  coreProgramasRoute,
  coreProgramaFormRoute,
  coreProgramaBajaRoute,
  corePapeleraRoute,
  corePapeleraRestaurarRoute,
  businessRoute(SHELL_ROUTES),
];

export function findRoute(pathname: string, routes: readonly RouteDefinition[] = ROUTES) {
  for (const route of routes) {
    const params = route.match(pathname);
    if (params !== null) return { route, params };
  }
  return null;
}
