import type { ClaroLayout } from "./ClaroFrame";
import type { InspMessage } from "./inspeccionesToasts";
import { apiUrlValid, layoutValid, messagesValid, tabsValid } from "./inspeccionesEscuelasApi";

/** Data contract of the Tablero tab web API (IN03): the shell and the polled data. */
const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object";
const text = (v: unknown): v is string => typeof v === "string";
const int = (v: unknown): v is number => Number.isSafeInteger(v);
const list = (v: unknown): v is unknown[] => Array.isArray(v);

export const FILTER_KEYS = ["fecha", "provincia", "localidad", "inspector", "turno", "notificacion"] as const;
export type Filters = Record<(typeof FILTER_KEYS)[number], string>;
export type TableroShell = {
  layout: ClaroLayout; tabs: { id: string; label: string; url: string }[]; filters: Filters;
  options: {
    provincias: { id: number; nombre: string }[]; inspectores: { id: number; nombre: string }[];
    turnos: { valor: string; etiqueta: string }[]; notificaciones: { valor: string; etiqueta: string }[];
  };
  intervalo_ms: number; urls: { datos: string; exportar: string; descargar: string }; messages: InspMessage[];
};

export type Categoria = { valor: string; etiqueta: string; cantidad: number };
export type Indice = { previsto: number; presente: number; computables: number; colegios: number; excluidas: number; porcentaje: number | null };
export type Serie = { total: number; denominador: number; categorias: Categoria[] };
export type Punto = { numero: string; url: string | null; escuela: string; cueanexo: string; turno: string; inspector: string; resultado: string; lat: number; lng: number; constatada: boolean };
export type Ultima = {
  numero: string; url: string | null; escuela: string; turno: string; inspector: string; hora: string; provincia: string;
  firma: { tipo: string; etiqueta: string }; notificacion: { estado: string; etiqueta: string };
};
export type TableroDatos = {
  indicadores: {
    escuelas_unicas: number; actas_validas: number; escuelas_con_mas_de_una_visita: number;
    inspectores: { con_actividad: number; habilitados: number; sin_actividad: number };
    borradores_en_curso: number; notificacion_pendiente: number; notificacion_cargada: number;
  };
  turnos: Categoria[]; resultados: Categoria[]; ausentismo: Indice; aulas: Indice;
  presencia: { personal: Serie; estudiantes: Serie };
  mapa: { puntos: Punto[]; con_gps: number; sin_coordenadas: number; manual: number; sin_ubicacion: number };
  ultimas: Ultima[]; opciones: { localidades: { id: number; nombre: string }[] };
};

const idName = (v: unknown) => list(v) && v.every((o) => record(o) && int(o.id) && text(o.nombre));
const valueLabel = (v: unknown) => list(v) && v.every((o) => record(o) && text(o.valor) && text(o.etiqueta));

export function shellValid(v: unknown): v is TableroShell {
  if (!record(v) || !record(v.filters) || !record(v.options) || !record(v.urls)) return false;
  const o = v.options;
  return layoutValid(v.layout) && tabsValid(v.tabs) && FILTER_KEYS.every((k) => text((v.filters as Record<string, unknown>)[k])) &&
    idName(o.provincias) && idName(o.inspectores) && valueLabel(o.turnos) && valueLabel(o.notificaciones) &&
    int(v.intervalo_ms) && v.intervalo_ms > 0 && ["datos", "exportar", "descargar"].every((k) => apiUrlValid((v.urls as Record<string, unknown>)[k])) &&
    messagesValid(v.messages);
}

const categorias = (v: unknown) => list(v) && v.every((c) => record(c) && text(c.valor) && text(c.etiqueta) && int(c.cantidad));
const indice = (v: unknown) => record(v) && ["previsto", "presente", "computables", "colegios", "excluidas"].every((k) => int(v[k]));
const percent = (v: unknown) => record(v) && (v.porcentaje === null || typeof v.porcentaje === "number");
const serie = (v: unknown) => record(v) && int(v.total) && int(v.denominador) && categorias(v.categorias);
const urlOrNull = (v: unknown) => v === null || text(v);

export function datosValid(v: unknown): v is TableroDatos {
  if (!record(v) || !record(v.indicadores) || !record(v.presencia) || !record(v.mapa) || !record(v.opciones)) return false;
  const i = v.indicadores;
  const m = v.mapa;
  return ["escuelas_unicas", "actas_validas", "escuelas_con_mas_de_una_visita", "borradores_en_curso", "notificacion_pendiente", "notificacion_cargada"].every((k) => int(i[k])) &&
    record(i.inspectores) && ["con_actividad", "habilitados", "sin_actividad"].every((k) => int((i.inspectores as Record<string, unknown>)[k])) &&
    categorias(v.turnos) && categorias(v.resultados) && indice(v.ausentismo) && indice(v.aulas) &&
    serie(v.presencia.personal) && serie(v.presencia.estudiantes) &&
    ["con_gps", "sin_coordenadas", "manual", "sin_ubicacion"].every((k) => int(m[k])) &&
    list(m.puntos) && m.puntos.every((p) => record(p) && text(p.numero) && urlOrNull(p.url) && ["escuela", "cueanexo", "turno", "inspector", "resultado"].every((k) => text(p[k])) &&
      typeof p.lat === "number" && typeof p.lng === "number" && typeof p.constatada === "boolean") &&
    list(v.ultimas) && v.ultimas.every((a) => record(a) && text(a.numero) && urlOrNull(a.url) && ["escuela", "turno", "inspector", "hora", "provincia"].every((k) => text(a[k])) &&
      record(a.firma) && text(a.firma.tipo) && text(a.firma.etiqueta) && record(a.notificacion) && text(a.notificacion.estado) && text(a.notificacion.etiqueta)) &&
    idName(v.opciones.localidades) && percent(v.ausentismo) && percent(v.aulas);
}
