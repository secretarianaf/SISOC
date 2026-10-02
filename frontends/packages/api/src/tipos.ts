/**
 * Tipos de la API de Celiaquia.
 *
 * **No se escriben a mano.** Son alias de los componentes de
 * `openapi.d.ts`, que genera `openapi-typescript` desde
 * `packages/api/openapi.yaml`, que a su vez sale de drf-spectacular.
 * Ver `frontend_v2.md`, seccion 7 (Contrato).
 *
 * Regenerar despues de tocar un serializer del back:
 *
 *     npm run api:schema   # back -> openapi.yaml
 *     npm run api:types    # openapi.yaml -> openapi.d.ts
 *
 * Este archivo existe para darle nombres cortos a los componentes y para que
 * las pantallas no importen `components["schemas"][...]` por todos lados. Si un
 * tipo deja de existir en el schema, este archivo deja de compilar: esa es la
 * senal de que el contrato cambio.
 *
 * Los nombres de campo van en `snake_case`, tal como los devuelve el back: no
 * se convierten a camelCase.
 */

import type { components } from "./openapi";

type Schemas = components["schemas"];

/** Respuesta de `PageNumberPagination` de DRF. */
export type Paginado<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type EstadoExpediente = Schemas["EstadoExpediente"];
export type EstadoLegajo = Schemas["EstadoLegajo"];
export type Expediente = Schemas["Expediente"];
export type ExpedienteCreate = Schemas["ExpedienteCreate"];
export type Legajo = Schemas["Legajo"];
export type DocumentoLegajo = Schemas["DocumentoLegajo"];
export type ArchivoLegajo = Schemas["ArchivoLegajo"];
export type Reporte = Schemas["Reporte"];
export type ReporteCaso = Schemas["ReporteCaso"];
export type ProvinciaCupo = Schemas["ProvinciaCupo"];
export type FilaCupoProvincia = Schemas["FilaCupoProvincia"];
export type CupoMovimiento = Schemas["CupoMovimiento"];
export type PagoExpediente = Schemas["PagoExpediente"];
export type PagoNomina = Schemas["PagoNomina"];
export type RegistroErroneo = Schemas["RegistroErroneo"];
export type HistorialEstado = Schemas["ExpedienteEstadoHistorial"];
export type Subsanacion = Schemas["Subsanacion"];
export type AsignacionTecnico = Schemas["AsignacionTecnico"];
export type Organismo = Schemas["Organismo"];
export type TipoCruce = Schemas["TipoCruce"];
export type TipoDocumento = Schemas["TipoDocumento"];
export type UsuarioResumen = Schemas["UsuarioResumen"];
/** Lo que devuelve `preview-excel/`. `PreviewExcel` a secas es el request. */
export type PreviewExcel = Schemas["PreviewExcelResultado"];
export type AccionResultado = Schemas["AccionResultado"];
export type ReprocesoResultado = Schemas["ReprocesoResultado"];
export type ImportacionResultado = Schemas["ImportacionResultado"];
export type ExclusionImportacion = Schemas["ExclusionImportacion"];
export type ProcesamientoResultado = Schemas["ProcesamientoResultado"];
export type ComentarioLegajo = Schemas["ComentarioLegajo"];
export type MotivoPreview = Schemas["MotivoPreview"];
export type LocalidadLookup = Schemas["LocalidadLookup"];
export type OpcionCatalogo = Schemas["OpcionCatalogo"];
export type CatalogosRegistroErroneo = Schemas["CatalogosRegistroErroneo"];

/**
 * Respuesta de `validar-renaper`.
 *
 * No sale del schema: el back arma el payload a mano (los campos dependen de lo
 * que devuelva RENAPER para ese documento), asi que no hay serializer del que
 * generarlo. Es la unica excepcion a la regla de tipos generados.
 */
export type ValidacionRenaper = {
  success: boolean;
  datos_provincia: Record<string, string>;
  datos_renaper: Record<string, string>;
  datos_ejemplar: Record<string, string>;
  ciudadano_nombre: string;
  documento: string;
};

/* Enums: el back los publica como componentes propios. */
export type RevisionTecnico = Schemas["RevisionTecnicoEnum"];
export type EstadoCupo = Schemas["EstadoCupoEnum"];
export type ResultadoSintys = Schemas["ResultadoSintysEnum"];
export type AccionRevision = Schemas["AccionEnum"];
export type EstadoPago = Schemas["PagoExpedienteEstadoEnum"];
export type EstadoPagoNomina = Schemas["PagoNominaEstadoEnum"];
export type EstadoSubsanacion = Schemas["SubsanacionEstadoEnum"];

/* Cuerpos de las escrituras. */
export type AsignarTecnico = Schemas["AsignarTecnico"];
export type ConfigurarCupo = Schemas["ConfigurarCupo"];
export type CrearLegajos = Schemas["CrearLegajos"];
export type CrearPago = Schemas["CrearPago"];
export type RevisarLegajo = Schemas["RevisarLegajo"];
export type SolicitarSubsanacion = Schemas["SolicitarSubsanacion"];
export type SubirArchivoLegajo = Schemas["SubirArchivoLegajo"];
export type ObservacionSubsanacion = Schemas["ObservacionSubsanacion"];
export type Motivo = Schemas["Motivo"];

/**
 * Metricas de cupo que arma el front sumando la pagina de `ProvinciaCupo`.
 * No es un componente del schema: no existe endpoint que las devuelva.
 */
export type MetricasCupo = {
  total_asignado: number;
  usados: number;
  disponibles: number;
  fuera: number;
};
