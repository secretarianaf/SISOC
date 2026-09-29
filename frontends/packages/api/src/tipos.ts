/**
 * Tipos de la API de Celiaquia.
 *
 * **Provisorios.** `frontend_v2.md` manda generarlos con `openapi-typescript`
 * desde `packages/api/openapi.yaml`, que a su vez sale de drf-spectacular. Hasta
 * que ese paso este en CI, estos estan escritos a mano siguiendo los
 * serializers de `celiaquia/api_serializers.py`.
 *
 * Los nombres de campo van en `snake_case`, tal como los devuelve el back: no
 * se convierten a camelCase.
 */

/** Respuesta de `PageNumberPagination` de DRF. */
export type Paginado<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type EstadoExpedienteNombre =
  | "CREADO"
  | "EN_ESPERA"
  | "CONFIRMACION_DE_ENVIO"
  | "RECEPCIONADO"
  | "ASIGNADO"
  | "PROCESO_DE_CRUCE"
  | "CRUCE_FINALIZADO";

export type EstadoExpediente = {
  id: number;
  nombre: string;
  display_name?: string;
};

export type Expediente = {
  id: number;
  numero_expediente: string | null;
  observaciones: string;
  fecha_creacion: string;
  estado: EstadoExpediente | null;
  provincia: string | null;
  legajos_total: number | null;
};

export type RevisionTecnico =
  | "PENDIENTE"
  | "APROBADO"
  | "RECHAZADO"
  | "SUBSANAR"
  | "SUBSANADO";

export type EstadoCupo = "DENTRO" | "FUERA" | "NO_EVAL" | "SIN_ASIGNAR";

export type Legajo = {
  id: number;
  expediente: number;
  nombre: string | null;
  apellido: string | null;
  documento: string | null;
  revision_tecnico: RevisionTecnico;
  resultado_sintys: string | null;
  estado_cupo: EstadoCupo;
  es_titular_activo: boolean;
  subsanacion_motivo: string | null;
  creado_en: string;
};

export type DocumentoLegajo = {
  id: number;
  nombre: string;
  cargado: boolean;
};

export type ProvinciaCupo = {
  id: number;
  provincia: number;
  provincia_nombre: string | null;
  total_asignado: number | null;
  usados: number | null;
};

export type MetricasCupo = {
  total_asignado: number;
  usados: number;
  disponibles: number;
  fuera: number;
};

export type CupoMovimiento = {
  id: number;
  provincia: number;
  expediente: number | null;
  tipo: string;
  delta: number | null;
  motivo: string | null;
  usuario: string | null;
  creado_en: string;
};

export type PagoExpediente = {
  id: number;
  provincia: number;
  periodo: string;
  estado: string;
  total_candidatos: number;
  total_validados: number;
  total_excluidos: number;
  creado_en: string;
};

export type PagoNomina = {
  id: number;
  documento: string;
  nombre: string;
  apellido: string;
  estado: string;
  observacion: string;
};

export type RegistroErroneo = {
  id: number;
  expediente: number;
  fila_excel: number;
  datos_raw: Record<string, string>;
  campo_error: string;
  mensaje_error: string;
  procesado: boolean;
  creado_en: string;
};

export type HistorialEstado = {
  id: number;
  fecha: string;
  estado_anterior: string | null;
  estado_nuevo: string | null;
  usuario: string | null;
  observaciones: string | null;
};

export type AccionRevision = "APROBAR" | "RECHAZAR" | "SUBSANAR" | "ELIMINAR";

export type PreviewExcel = {
  headers: string[];
  rows: Record<string, string>[];
};
