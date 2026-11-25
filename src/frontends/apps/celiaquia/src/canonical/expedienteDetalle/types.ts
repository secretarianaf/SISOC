/** Shape of the private JSON projection served by `canonical_expediente_detail.py`. */

export type Tone = "info" | "warning" | "success" | "danger" | "error" | "debug";

export type Archivo = {
  id: number; nombre: string; url: string | null; origen: string; origen_codigo: string;
  observacion: string | null; descripcion: string; creado_en: string | null; usuario: string | null;
};

export type Subsanacion = {
  id: number; estado: string; estado_display: string;
  solicitada_por: string | null; solicitada_en: string | null;
  respondida_por: string | null; respondida_en: string | null;
  observaciones: { id: number; tipo: string; detalle: string }[];
  archivos: Archivo[];
};

export type SubsanacionActiva = Subsanacion & {
  archivos_de_nacion: Archivo[];
  archivos_de_provincia: Archivo[];
  observaciones_opciones: { id: number; label: string }[];
};

export type LegajoActions = {
  editar: string | null; eliminar: string | null; subir_archivo: string | null;
  comentarios: string; agregar_comentario: string | null; confirmar_subsanacion: string | null;
  responder_subsanacion: string | null; responder_renaper: string | null;
  validar_renaper: string | null; revisar: string | null; motivo_preview: string | null;
  corregir_evaluacion: string | null;
};

export type Persona = { id: number; nombre: string; apellido: string; documento: string };

export type Legajo = {
  id: number; ciudadano_id: number; nombre: string; apellido: string; documento: string;
  rol: string; tipo_legajo: string; es_responsable: boolean; es_doble_rol: boolean; es_hijo: boolean;
  icono: "familia" | "adulto" | "menor";
  hijos_a_cargo: Persona[]; responsables: string[];
  badges: { text: string; tone: string }[]; hijos_texto: string | null; alertas: string[];
  revision_tecnico: string; estado_validacion_renaper: number | null; estado: string;
  documentos: { label: string; nombre: string; cargado: boolean }[];
  observacion: { titulo: string | null; texto: string | null; items: string[] };
  subsanacion_motivo: string;
  renaper: { comentario: string; archivo_url: string | null; respuesta_label: string | null; pendiente: boolean; solicitud_label: string };
  archivos: { campo: string; label: string; url: string | null }[];
  subsanacion_activa: SubsanacionActiva | null;
  subsanaciones_historial: Subsanacion[];
  comentarios_visibles: boolean;
  actions: LegajoActions;
};

export type Registro = {
  id: number; fila: number; datos_raw: Record<string, string>; datos: Record<string, string>;
  mensaje_error: string; invalid_fields: string[]; responsable_requerido: boolean;
  nacionalidad_id: string; municipio_id: string; actualizar_url: string; eliminar_url: string;
};

export type Opcion = { id: number; label: string };

export type Catalogos = {
  sexos: Opcion[]; nacionalidades: Opcion[]; nacionalidad_argentina_id: string;
  municipios: Opcion[]; localidades: (Opcion & { municipio_id: number; municipio: string })[];
};

export type ObservacionCatalogo = { codigo: string; texto: string; libre?: boolean };

export type Detalle = {
  version: number;
  expediente: {
    id: number; numero: string; estado: string; estado_display: string; fecha_creacion: string | null;
    provincia: string; tecnicos: string[]; documento_url: string | null;
    excel: null | {
      nombre: string; url: string; audit: boolean; cargado_por: string | null; cargado_en: string | null;
      procesado_por: string | null; procesado_en: string | null;
    };
  };
  roles: { tecnico: boolean; coordinador: boolean; provincial: boolean; admin: boolean };
  flags: Record<string, boolean>;
  actions: {
    editar: string | null; nomina_sintys: string | null; historial: boolean; familias: boolean;
    subir_cruce: string | null; reprocesar_cruce: string | null; padron_final: string | null;
    confirmar_envio: string | null; asignar_tecnico: string | null; reprocesar_errores: string | null;
  };
  cupo: null | { total_asignado: number; usados: number; disponibles: number; fuera: number };
  alertas: { style: string; text: string }[];
  fuera_de_cupo: { id: number; documento: string; nombre: string; apellido: string }[];
  preview: null | {
    headers: string[]; rows: string[][]; limit: string;
    options: { value: string; label: string }[]; procesar: string | null;
  };
  preview_error: string | null;
  legajos_total: number;
  legajos: Legajo[];
  historial: {
    items: { id: number; fecha: string | null; estado_anterior: string; estado_nuevo: string; usuario: string | null; observaciones: string }[];
    page: number; num_pages: number;
  };
  registros_erroneos: Registro[];
  tecnicos: { id: number; name: string }[];
  catalogos: Catalogos | null;
  comentarios: { catalogo: Record<string, ObservacionCatalogo[]>; tipos_documento: { value: string; label: string }[] };
  complementaria: { accept: string; max_archivos: number; max_mb: number };
  messages: { level: string; text: string }[];
};

export type Notice = { tone: Tone; text: string };
