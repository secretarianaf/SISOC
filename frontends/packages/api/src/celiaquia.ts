import type { AxiosInstance } from "axios";
import type {
  AccionResultado,
  AsignacionTecnico,
  AccionRevision,
  CatalogosRegistroErroneo,
  ComentarioLegajo,
  CupoMovimiento,
  DocumentoLegajo,
  Expediente,
  HistorialEstado,
  ImportacionResultado,
  LocalidadLookup,
  Legajo,
  MetricasCupo,
  MotivoPreview,
  OpcionCatalogo,
  ValidacionRenaper,
  Paginado,
  PagoExpediente,
  PagoNomina,
  PreviewExcel,
  ProcesamientoResultado,
  ProvinciaCupo,
  Reporte,
  UsuarioResumen,
  RegistroErroneo,
  ReprocesoResultado,
} from "./tipos";

/**
 * Endpoints de `api/celiaquia/`.
 *
 * Una funcion por operacion, sin estado: el cache y los reintentos los pone
 * TanStack Query en la app. Los nombres siguen a los del back para que sea
 * obvio a que endpoint corresponde cada uno.
 */
export const celiaquiaApi = (http: AxiosInstance) => ({
  expedientes: {
    listar: (params?: { estado?: string; numero_expediente?: string; page?: number }) =>
      http
        .get<Paginado<Expediente>>("expedientes/", { params })
        .then((r) => r.data),

    obtener: (id: number) =>
      http.get<Expediente>(`expedientes/${id}/`).then((r) => r.data),

    crear: (datos: {
      numero_expediente?: string;
      observaciones?: string;
      excel_masivo?: File | null;
    }) => {
      const form = new FormData();
      if (datos.numero_expediente)
        form.append("numero_expediente", datos.numero_expediente);
      if (datos.observaciones) form.append("observaciones", datos.observaciones);
      if (datos.excel_masivo) form.append("excel_masivo", datos.excel_masivo);
      return http.post<Expediente>("expedientes/", form).then((r) => r.data);
    },

    actualizar: (
      id: number,
      datos: { numero_expediente?: string; observaciones?: string },
    ) =>
      http
        .patch<Expediente>(`expedientes/${id}/`, datos)
        .then((r) => r.data),

    eliminar: (id: number) => http.delete(`expedientes/${id}/`),

    previewExcel: (archivo: File, limit?: number) => {
      const form = new FormData();
      form.append("excel_masivo", archivo);
      if (limit) form.append("limit", String(limit));
      return http
        .post<PreviewExcel>("expedientes/preview-excel/", form)
        .then((r) => r.data);
    },

    legajos: (id: number, params?: { page?: number }) =>
      http
        .get<Paginado<Legajo>>(`expedientes/${id}/legajos/`, { params })
        .then((r) => r.data),

    historialEstados: (id: number) =>
      http
        .get<HistorialEstado[]>(`expedientes/${id}/historial-estados/`)
        .then((r) => r.data),

    fueraDeCupo: (id: number) =>
      http.get<Legajo[]>(`expedientes/${id}/fuera-de-cupo/`).then((r) => r.data),

    registrosErroneos: (id: number) =>
      http
        .get<RegistroErroneo[]>(`expedientes/${id}/registros-erroneos/`)
        .then((r) => r.data),

    /**
     * Corrige una fila que no se pudo importar.
     *
     * Las claves de `datos` son las columnas del Excel, asi que el back recibe
     * el diccionario entero y valida con el mismo service que la pantalla
     * Django. Si la fila sigue invalida responde 400 con `invalid_fields`.
     */
    actualizarRegistroErroneo: (
      id: number,
      registroId: number,
      datos: Record<string, string>,
    ) =>
      http
        .post<AccionResultado>(
          `expedientes/${id}/registros-erroneos/${registroId}/actualizar/`,
          { datos },
        )
        .then((r) => r.data),

    /** Reintenta crear los legajos de todas las filas con error. */
    reprocesarRegistrosErroneos: (id: number) =>
      http
        .post<ReprocesoResultado>(
          `expedientes/${id}/registros-erroneos/reprocesar/`,
        )
        .then((r) => r.data),

    /**
     * Importa los legajos del Excel masivo ya cargado en el expediente.
     *
     * Devuelve los totales como JSON; la pantalla Django los manda por
     * `messages`, que no se pueden leer desde React.
     */
    importar: (id: number) =>
      http
        .post<ImportacionResultado>(`expedientes/${id}/importar/`)
        .then((r) => r.data),

    /** Excel vacio con las columnas que espera la importacion. */
    plantillaExcel: () =>
      http
        .get("expedientes/plantilla-excel/", { responseType: "blob" })
        .then((r) => r.data as Blob),

    /** Copia del Excel masivo vigente. Solo coordinacion y admin. */
    descargarExcelMasivo: (id: number) =>
      http
        .get(`expedientes/${id}/excel-masivo/`, { responseType: "blob" })
        .then((r) => r.data as Blob),

    /** Tecnicos asignables. Solo coordinacion y admin. */
    tecnicos: () =>
      http.get<UsuarioResumen[]>("expedientes/tecnicos/").then((r) => r.data),

    /** Sexos y nacionalidades, para los desplegables del formulario. */
    catalogos: () =>
      http
        .get<CatalogosRegistroErroneo>("expedientes/catalogos/")
        .then((r) => r.data),

    /**
     * Municipios que la correccion de este expediente va a aceptar.
     *
     * Van acotados a la provincia del expediente, no al pais: el validador de
     * la importacion rechaza los de otra provincia con "municipio N no
     * encontrado".
     */
    municipios: (id: number) =>
      http
        .get<OpcionCatalogo[]>(`expedientes/${id}/municipios/`)
        .then((r) => r.data),

    /**
     * Localidades que la correccion de este expediente va a aceptar.
     *
     * Acotadas a la provincia del expediente. Con `municipio` se filtra ademas
     * a ese municipio (campo del beneficiario); sin el devuelve toda la
     * provincia, que es lo que necesita `localidad_responsable`.
     */
    localidades: (id: number, params?: { municipio?: number }) =>
      http
        .get<LocalidadLookup[]>(`expedientes/${id}/localidades/`, { params })
        .then((r) => r.data),
    /** Descarta una fila sin importarla. */
    eliminarRegistroErroneo: (id: number, registroId: number) =>
      http
        .delete<AccionResultado>(
          `expedientes/${id}/registros-erroneos/${registroId}/`,
        )
        .then((r) => r.data),

    estructuraFamiliar: (id: number) =>
      http
        .get<Record<string, unknown>>(`expedientes/${id}/estructura-familiar/`)
        .then((r) => r.data),

    /**
     * Procesa el Excel masivo y crea los legajos.
     *
     * Devuelve el resumen con las filas **excluidas**: personas que ya estan en
     * el programa en otro expediente. No son registros erroneos (el Excel esta
     * bien), asi que no aparecen en esa grilla y hay que mostrarlas aparte.
     */
    procesar: (id: number) =>
      http
        .post<{ detail: string; resultado: ProcesamientoResultado }>(
          `expedientes/${id}/procesar/`,
        )
        .then((r) => r.data),

    confirmarEnvio: (id: number) =>
      http.post(`expedientes/${id}/confirmar-envio/`).then((r) => r.data),

    recepcionar: (id: number) =>
      http.post(`expedientes/${id}/recepcionar/`).then((r) => r.data),

    /** Asignaciones del expediente, activa e historicas. */
    asignaciones: (id: number) =>
      http
        .get<AsignacionTecnico[]>(`expedientes/${id}/asignaciones/`)
        .then((r) => r.data),

    asignarTecnico: (id: number, tecnico_id: number) =>
      http
        .post(`expedientes/${id}/asignar-tecnico/`, { tecnico_id })
        .then((r) => r.data),

    desasignarTecnico: (id: number) =>
      http.post(`expedientes/${id}/desasignar-tecnico/`).then((r) => r.data),

    subirCruce: (id: number, archivo: File) => {
      const form = new FormData();
      form.append("archivo", archivo);
      return http.post(`expedientes/${id}/cruce/`, form).then((r) => r.data);
    },

    /** Descargas: devuelven el blob para que la pantalla dispare el guardado. */
    nominaSintys: (id: number) =>
      http
        .get(`expedientes/${id}/nomina-sintys/`, { responseType: "blob" })
        .then((r) => r.data as Blob),

    padronFinal: (id: number) =>
      http
        .get(`expedientes/${id}/padron-final/`, { responseType: "blob" })
        .then((r) => r.data as Blob),
  },

  reporte: {
    /**
     * Reporte por provincia, con los mismos numeros que la pantalla Django.
     *
     * Las agregaciones las calcula el back: aca no se suma nada, porque las
     * reglas de persona unica y dupla viven en `reporte_service`.
     */
    obtener: (params?: {
      provincia?: number;
      fecha_desde?: string;
      fecha_hasta?: string;
      expediente_numero?: string;
      documento_persona?: string;
      revision_tecnico?: string;
      resultado_sintys?: string;
      estado_cupo?: string;
      page?: number;
    }) => http.get<Reporte>("reporte/", { params }).then((r) => r.data),
  },

  legajos: {
    listar: (params?: {
      expediente?: number;
      revision_tecnico?: string;
      estado_cupo?: string;
      page?: number;
    }) => http.get<Paginado<Legajo>>("legajos/", { params }).then((r) => r.data),

    documentos: (id: number) =>
      http.get<DocumentoLegajo[]>(`legajos/${id}/documentos/`).then((r) => r.data),

    /**
     * Historial de comentarios internos del legajo.
     *
     * Es del panel de Nacion: la provincia recibe 403 hasta que el comentario
     * se publica al subsanar o rechazar.
     */
    comentarios: (id: number) =>
      http
        .get<ComentarioLegajo[]>(`legajos/${id}/comentarios/`)
        .then((r) => r.data),

    /** Alta de un comentario tecnico estructurado (tipo + Si/No + observacion). */
    crearComentarioTecnico: (
      id: number,
      datos: {
        tipo_documento: string;
        tiene_observaciones: string;
        observacion_codigo?: string | null;
        observacion_libre?: string;
      },
    ) =>
      http
        .post<ComentarioLegajo>(`legajos/${id}/comentarios/tecnico/`, datos)
        .then((r) => r.data),

    /**
     * Consulta RENAPER y devuelve la comparacion contra los datos cargados.
     *
     * No guarda nada: el tecnico confirma despues con `guardarValidacionRenaper`.
     * Un error de negocio (sin documento, fallecido, sin match) vuelve como 400.
     */
    validarRenaper: (id: number) =>
      http
        .post<ValidacionRenaper>(`legajos/${id}/validar-renaper/`)
        .then((r) => r.data),

    /** Confirma el resultado: "1" acepta, "2" rechaza y libera cupo, "3" subsana. */
    guardarValidacionRenaper: (
      id: number,
      estado: "1" | "2" | "3",
      comentario?: string,
    ) =>
      http
        .post<AccionResultado>(`legajos/${id}/validacion-renaper/`, {
          estado,
          ...(comentario ? { comentario } : {}),
        })
        .then((r) => r.data),

    /** Motivo que se propondria al subsanar o rechazar, ya concatenado. */
    motivoPreview: (id: number) =>
      http
        .get<MotivoPreview>(`legajos/${id}/motivo-preview/`)
        .then((r) => r.data),

    /**
     * Pasa el legajo de SUBSANAR a SUBSANADO.
     *
     * Responder una subsanacion sube la evidencia pero **no cambia el estado
     * del legajo**: sin este paso sigue en SUBSANAR y la tecnica no puede
     * volver a aprobarlo ni rechazarlo.
     */
    confirmarSubsanacion: (id: number) =>
      http
        .post<Legajo>(`legajos/${id}/confirmar-subsanacion/`)
        .then((r) => r.data),

    /** La provincia adjunta evidencia nueva para la subsanacion activa. */
    responderSubsanacion: (
      id: number,
      archivos: File[],
      datos?: { descripcion?: string; observacion_id?: number },
    ) => {
      const form = new FormData();
      archivos.forEach((archivo) => form.append("archivos", archivo));
      if (datos?.descripcion) form.append("descripcion", datos.descripcion);
      if (datos?.observacion_id != null) {
        form.append("observacion_id", String(datos.observacion_id));
      }
      return http
        .post<AccionResultado>(`legajos/${id}/responder-subsanacion/`, form)
        .then((r) => r.data);
    },

    revisar: (
      id: number,
      datos: {
        accion: AccionRevision;
        texto_libre?: string;
        tipo_subsanacion?: string;
        observaciones?: { tipo: string; detalle: string }[];
      },
    ) => http.post(`legajos/${id}/revisar/`, datos).then((r) => r.data),

    /**
     * Sube un archivo al legajo, en el slot indicado (1, 2 o 3).
     *
     * Que slots pide cada legajo viene en `legajo.archivos`: depende del rol
     * (beneficiario, responsable o ambos). Sin `slot` el back lo pone en el
     * primero que este libre.
     */
    subirArchivo: (id: number, archivo: File, slot?: number) => {
      const form = new FormData();
      form.append("archivo", archivo);
      if (slot) form.append("slot", String(slot));
      return http
        .post<DocumentoLegajo[]>(`legajos/${id}/archivos/`, form)
        .then((r) => r.data);
    },
  },

  cupos: {
    listar: () =>
      http.get<Paginado<ProvinciaCupo>>("cupos/").then((r) => r.data),

    metricas: (id: number) =>
      http.get<MetricasCupo>(`cupos/${id}/metricas/`).then((r) => r.data),

    ocupados: (id: number) =>
      http.get<Legajo[]>(`cupos/${id}/ocupados/`).then((r) => r.data),

    suspendidos: (id: number) =>
      http.get<Legajo[]>(`cupos/${id}/suspendidos/`).then((r) => r.data),

    configurar: (provinciaId: number, total_asignado: number) =>
      http
        .post<ProvinciaCupo>(`cupos/provincia/${provinciaId}/`, {
          total_asignado,
        })
        .then((r) => r.data),

    baja: (legajoId: number, motivo = "") =>
      http.post(`cupos/legajos/${legajoId}/baja/`, { motivo }).then((r) => r.data),

    suspender: (legajoId: number, motivo = "") =>
      http
        .post(`cupos/legajos/${legajoId}/suspender/`, { motivo })
        .then((r) => r.data),

    reactivar: (legajoId: number, motivo = "") =>
      http
        .post(`cupos/legajos/${legajoId}/reactivar/`, { motivo })
        .then((r) => r.data),

    movimientos: (params?: { provincia?: number; expediente?: number }) =>
      http
        .get<Paginado<CupoMovimiento>>("cupos-movimientos/", { params })
        .then((r) => r.data),
  },

  pagos: {
    listar: (params?: { periodo?: string; estado?: string }) =>
      http.get<Paginado<PagoExpediente>>("pagos/", { params }).then((r) => r.data),

    obtener: (id: number) =>
      http.get<PagoExpediente>(`pagos/${id}/`).then((r) => r.data),

    crear: (provincia_id: number, periodo?: string) =>
      http
        .post<PagoExpediente>("pagos/", { provincia_id, periodo })
        .then((r) => r.data),

    nomina: (id: number) =>
      http.get<Paginado<PagoNomina>>(`pagos/${id}/nomina/`).then((r) => r.data),

    procesarRespuesta: (id: number, archivo: File) => {
      const form = new FormData();
      form.append("archivo", archivo);
      return http
        .post(`pagos/${id}/procesar-respuesta/`, form)
        .then((r) => r.data);
    },

    exportarNomina: (id: number) =>
      http
        .get(`pagos/${id}/exportar-nomina/`, { responseType: "blob" })
        .then((r) => r.data as Blob),
  },
});

export type CeliaquiaApi = ReturnType<typeof celiaquiaApi>;
