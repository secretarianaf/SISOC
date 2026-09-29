import type { AxiosInstance } from "axios";
import type {
  AccionRevision,
  CupoMovimiento,
  DocumentoLegajo,
  Expediente,
  HistorialEstado,
  Legajo,
  MetricasCupo,
  Paginado,
  PagoExpediente,
  PagoNomina,
  PreviewExcel,
  ProvinciaCupo,
  RegistroErroneo,
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

    estructuraFamiliar: (id: number) =>
      http
        .get<Record<string, unknown>>(`expedientes/${id}/estructura-familiar/`)
        .then((r) => r.data),

    procesar: (id: number) =>
      http.post(`expedientes/${id}/procesar/`).then((r) => r.data),

    confirmarEnvio: (id: number) =>
      http.post(`expedientes/${id}/confirmar-envio/`).then((r) => r.data),

    recepcionar: (id: number) =>
      http.post(`expedientes/${id}/recepcionar/`).then((r) => r.data),

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

  legajos: {
    listar: (params?: {
      expediente?: number;
      revision_tecnico?: string;
      estado_cupo?: string;
      page?: number;
    }) => http.get<Paginado<Legajo>>("legajos/", { params }).then((r) => r.data),

    documentos: (id: number) =>
      http.get<DocumentoLegajo[]>(`legajos/${id}/documentos/`).then((r) => r.data),

    revisar: (
      id: number,
      datos: {
        accion: AccionRevision;
        texto_libre?: string;
        tipo_subsanacion?: string;
        observaciones?: { tipo: string; detalle: string }[];
      },
    ) => http.post(`legajos/${id}/revisar/`, datos).then((r) => r.data),

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
