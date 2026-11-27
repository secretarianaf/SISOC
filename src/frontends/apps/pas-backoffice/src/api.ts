import { crearCliente, descargarBlob, SinPermiso } from "@sisoc/api";

const client = crearCliente("/api");

export function statusPas(error: unknown): number | undefined {
  if (error instanceof SinPermiso) return 403;
  return (error as { response?: { status?: number } } | null)?.response?.status;
}

export async function webGet<T>(path: string): Promise<T> {
  return (await client.get<T>(path)).data;
}

export type Titular = {
  id: number;
  apellidos: string;
  nombres: string;
  dni: number;
  cuit: string;
  provincia: string;
  municipio: string;
  estado: { nombre: string };
  /** Códigos de aviso; solo los trae el listado. */
  avisos?: number[];
  id_persona?: number;
  /** Chips del padrón: DDJJ sin completar y FCH bajo 100 puntos. */
  tag_ddjj?: boolean;
  tag_fch?: boolean;
};

export type Padron = {
  total_padron: number;
  page?: number;
  /** Páginas a mostrar, con "…" donde se saltean (paginador sin conteo). */
  page_range?: (number | "…")[];
  results: Titular[];
  estados: { nombre: string }[];
  previous: number | null;
  next: number | null;
  capabilities: { can_export_tokens: boolean; can_import?: boolean };
};

export type Curso = { curso: string; inicio: string; fin: string; puntos: string; estado: string; certificado_url?: string };

export type Ficha = {
  capabilities?: { can_change: boolean; can_delete?: boolean };
  cambio_estado?: { estados: { id: number; nombre: string }[]; avisos_por_estado: Record<string, { id: number; text: string }[]> };
  persona: (Omit<Titular, "avisos"> & { domicilio: string; correo_electronico: string; telefono_celular: string;
    fecha_creacion?: string; fecha_actualizacion?: string;
    avisos: { codigo: number; descripcion: string }[] }) | null;
  formaciones: Curso[];
  ddjj: {
    declaraciones: { id: number; version: number; presentada: string; es_ultima: boolean }[];
    seleccionada: { download_url: string; respuestas: { clave: string; etiqueta: string; respuesta: string }[] } | null;
  };
  eventos_historial: { tipo: string; fecha: string; estado?: string; version?: number; observacion?: string }[];
};

export type PuntoControl = { clave: string; titulo: string; estado: "ok" | "pendiente" | "sin_integrar"; detalle: string; bloquea: boolean };
export type FilaPreliquidacion = {
  id: number; titular: string; cuil: string; cbu: string; monto: string; fch: string | null;
  cruces_ok: boolean; ddjj_ok: boolean; habilitado: boolean; estado_final: string;
};
export type Liquidacion = {
  periodo: string;
  puntos_control: PuntoControl[];
  descarga_habilitada: boolean;
  nomina_generada: boolean;
  fecha_cierre: string;
  titulares_a_acreditar: number;
  titulares_bloqueados: number;
  total_a_liquidar: string;
  monto_mensual: string;
  filas: FilaPreliquidacion[];
  total_filas: number;
};
export type Area = { area: { title: string; subtitle: string }; total_padron: number; liquidacion?: Liquidacion; can_download?: boolean; can_export_csv?: boolean };
export type Formacion = Area & {
  personas: { id: number; apellidos: string; nombres: string; puntos_formacion: number; estado_formacion?: string }[];
  persona_seleccionada: { id: number; apellidos: string; nombres: string } | null;
  resumen: { titulo: string; detalle: string; puntos: number; objetivo: number; estado: string; dia_actual: number; duracion_dias: number; excedente: number;
    credito_inicial?: number; puntos_periodo?: number; semaforo?: "verde" | "amarillo" | "rojo"; bloquea_pago?: boolean; integrada?: boolean } | null;
  formaciones: Curso[];
  next_page: number | null;
};

export type Cruces = {
  can_change: boolean;
  circuito: { periodo_texto: string; periodo?: string };
  etapas: { numero: number; nombre: string; completada: boolean; fecha_texto: string; integracion_pendiente: boolean }[];
  renaper: { total: number; fallecidas: number; errores: number };
  incompatibilidades: {
    id?: number; persona_id?: number; titular: string; dni: number; categoria: string; origen?: string; detalle: string;
    fecha_deteccion: string; estado: string; estado_actual?: string; cambio_propuesto?: string | null;
  }[];
  cambio_estado?: NonNullable<Ficha["cambio_estado"]>;
  importacion_sintys?: ResumenSintys | null;
};

export type ResumenSintys = { total: number; compatibles: number; alertas: number; sin_cambios: number; ya_gestionadas: number; errores: string[] };

export type Informe = {
  id: number;
  numero: string;
  creado: string;
  total_personas: number;
  download_url: string | null;
};

export function pasGet<T>(path: string): Promise<T> {
  return webGet<T>(`web/pas/${path}`);
}


export async function pasPost<T>(path: string, body?: FormData): Promise<T> {
  return (await client.post<T>(`web/pas/${path}`, body)).data;
}

export async function generarInforme(body: FormData) {
  try {
    const response = await client.post<Blob>("web/pas/informes/generar/", body, { responseType: "blob" });
    const id = String(response.headers["x-pas-informe-id"] ?? "");
    const disposition = String(response.headers["content-disposition"] ?? "");
    const filename = /filename="?([^";]+)"?/i.exec(disposition)?.[1] ?? "informe-pas.csv";
    descargarBlob(response.data, filename);
    return /^[0-9]+$/.test(id) ? id : null;
  } catch (error) {
    const result = (error as { response?: { status?: number; data?: unknown } }).response;
    if (result?.status === 400 && result.data instanceof Blob) result.data = JSON.parse(await result.data.text());
    throw error;
  }
}

export async function exportarSintys() {
  const response = await client.post<Blob>("web/pas/cruces/exportar-sintys/", undefined, { responseType: "blob" });
  const disposition = String(response.headers["content-disposition"] ?? "");
  const filename = /filename="?([^";]+)"?/i.exec(disposition)?.[1] ?? "padron-sintys.xlsx";
  descargarBlob(response.data, filename);
}

/**
 * Tokens vigentes de DDJJ: la vista nativa `pas_tokens_exportar`, con su
 * permiso. Se baja como blob para que la descarga no dependa de que el
 * navegador resuelva un link a un adjunto y para poder avisar si falla.
 */
export async function exportarTokens() {
  const response = await client.get<Blob>("/pas/ddjj/tokens/exportar", { baseURL: "", responseType: "blob" });
  const disposition = String(response.headers["content-disposition"] ?? "");
  const filename = /filename="?([^";]+)"?/i.exec(disposition)?.[1] ?? "pas_tokens_ddjj_vigentes.xlsx";
  descargarBlob(response.data, filename);
}

export async function importarSintys(archivo: File) {
  const body = new FormData();
  body.append("archivo", archivo);
  return (await client.post<{ message: string; resumen: ResumenSintys }>("web/pas/cruces/importar-sintys/", body)).data;
}

/**
 * Nómina de pago BNA (TXT). Si un punto de control la bloquea, el backend
 * responde 409 con los motivos: se leen del blob para poder mostrarlos.
 */
export async function descargarNomina() {
  try {
    const response = await client.post<Blob>("web/pas/liquidacion/descargar-nomina/", undefined, { responseType: "blob" });
    const disposition = String(response.headers["content-disposition"] ?? "");
    const filename = /filename="?([^";]+)"?/i.exec(disposition)?.[1] ?? "nomina_pago_pas_bna.xlsx";
    descargarBlob(response.data, filename);
  } catch (error) {
    const result = (error as { response?: { data?: unknown } }).response;
    if (result?.data instanceof Blob) result.data = JSON.parse(await result.data.text());
    throw error;
  }
}

/** CSV de la preliquidación completa del período (todas las filas). */
export async function exportarPreliquidacionCsv() {
  const response = await client.get<Blob>("web/pas/liquidacion/preliquidacion-csv/", { responseType: "blob" });
  const disposition = String(response.headers["content-disposition"] ?? "");
  const filename = /filename="?([^";]+)"?/i.exec(disposition)?.[1] ?? "preliquidacion_pas.csv";
  descargarBlob(response.data, filename);
}
