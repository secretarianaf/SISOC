import type { InspOption } from "./InspSelect2";
import type { ClaroLayout } from "./ClaroFrame";
import type { InspMessage } from "./inspeccionesToasts";
import {
  apiPath, apiUrlValid, client, internal, layoutValid, messagesValid, optionValid, provinciasValid, tabsValid,
} from "./inspeccionesEscuelasApi";

/** Data contract, validation and POST of the Asignaciones tab web API (IN02). */
const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object";
const text = (v: unknown): v is string => typeof v === "string";

export type Tab = { id: string; label: string; url: string };
export type Choice = { value: string; label: string };
export type Row = {
  id: number; iniciales: string; inspector: { nombre: string; usuario: string };
  escuela: { nombre: string; cueanexo: string; localidad: string; provincia: string };
  estado: string; estado_display: string; actas: { numero: string; url: string; anulada: boolean; prueba: boolean }[];
  se_puede_quitar: boolean; quitar_url: string;
};
export type Page = {
  number: number; count: number; start_index: number; end_index: number; has_other_pages: boolean;
  previous: number | null; next: number | null; range: (number | "…")[]; query_without_page: string;
};
export type AsignacionesData = {
  layout: ClaroLayout; tabs: Tab[];
  filters: { fecha: string; inspector: InspOption | null; escuela: InspOption | null; provincia: string; estado: string; estado_acta: string };
  day: { es_hoy: boolean; anterior: string; siguiente: string; hoy: string };
  options: { provincias: { id: number; nombre: string }[]; estados: Choice[]; estados_acta: Choice[]; inspectores_url: string; escuelas_url: string };
  totales: { total: number; pendiente: number; en_curso: number; finalizada: number; inspectores: number };
  results: Row[]; page: Page; urls: { nueva: string; importar: string }; messages: InspMessage[];
};
export type Field = { value: string; errors: string[] };
export const FIELDS = ["fecha", "inspector", "escuela"] as const;
export type AsignacionFormData = {
  layout: ClaroLayout; tabs: Tab[]; non_field_errors: string[];
  fields: Record<(typeof FIELDS)[number], Field>;
  inspector_inicial: InspOption | null; escuela_inicial: InspOption | null;
  options: { inspectores_url: string; escuelas_url: string; verificar_url: string };
  messages: InspMessage[];
};

const choicesValid = (v: unknown) => Array.isArray(v) && v.every((c) => record(c) && text(c.value) && text(c.label));
const optionOrNull = (v: unknown) => v === null || optionValid(v);

function rowValid(r: unknown): r is Row {
  if (!record(r) || !record(r.inspector) || !record(r.escuela)) return false;
  return Number.isSafeInteger(r.id) && text(r.iniciales) && text(r.inspector.nombre) && text(r.inspector.usuario) &&
    ["nombre", "cueanexo", "localidad", "provincia"].every((k) => text((r.escuela as Record<string, unknown>)[k])) &&
    text(r.estado) && text(r.estado_display) && typeof r.se_puede_quitar === "boolean" && apiUrlValid(r.quitar_url) &&
    Array.isArray(r.actas) && r.actas.every((a) => record(a) && text(a.numero) && internal(a.url) && typeof a.anulada === "boolean" && typeof a.prueba === "boolean");
}

export function asignacionesValid(v: unknown): v is AsignacionesData {
  if (!record(v) || !record(v.filters) || !record(v.day) || !record(v.options) || !record(v.totales) || !record(v.page) || !record(v.urls)) return false;
  const p = v.page;
  const f = v.filters;
  return layoutValid(v.layout) && tabsValid(v.tabs) &&
    text(f.fecha) && optionOrNull(f.inspector) && optionOrNull(f.escuela) && text(f.provincia) && text(f.estado) && text(f.estado_acta) &&
    typeof v.day.es_hoy === "boolean" && internal(v.day.anterior) && internal(v.day.siguiente) && internal(v.day.hoy) &&
    provinciasValid(v.options.provincias) && choicesValid(v.options.estados) && choicesValid(v.options.estados_acta) &&
    apiUrlValid(v.options.inspectores_url) && apiUrlValid(v.options.escuelas_url) &&
    ["total", "pendiente", "en_curso", "finalizada", "inspectores"].every((k) => Number.isSafeInteger((v.totales as Record<string, unknown>)[k])) &&
    Array.isArray(v.results) && v.results.every(rowValid) &&
    ["number", "count", "start_index", "end_index"].every((k) => Number.isSafeInteger(p[k])) && typeof p.has_other_pages === "boolean" &&
    Array.isArray(p.range) && text(p.query_without_page) &&
    apiUrlValid(v.urls.nueva) && internal(v.urls.importar) && messagesValid(v.messages);
}

export function asignacionFormValid(v: unknown): v is AsignacionFormData {
  if (!record(v) || !record(v.fields) || !record(v.options)) return false;
  const f = v.fields;
  return layoutValid(v.layout) && tabsValid(v.tabs) && Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) &&
    FIELDS.every((k) => record(f[k]) && text(f[k].value) && Array.isArray(f[k].errors) && (f[k].errors as unknown[]).every(text)) &&
    optionOrNull(v.inspector_inicial) && optionOrNull(v.escuela_inicial) &&
    apiUrlValid(v.options.inspectores_url) && apiUrlValid(v.options.escuelas_url) && apiUrlValid(v.options.verificar_url) && messagesValid(v.messages);
}

export type Outcome =
  | { kind: "json"; mensaje: string; otra: boolean }
  | { kind: "redirect"; to: string }
  | { kind: "invalid"; data: AsignacionFormData }
  | { kind: "forbidden"; data: unknown }
  | { kind: "uncertain" };

const accepted = (status: number) => (status >= 200 && status < 300) || status === 400 || status === 403;

/** POST once (modal: with `X-Requested-With`, like `panel.js`); never retried. */
export async function postAsignacion(endpoint: string, body: URLSearchParams, modal: boolean): Promise<Outcome> {
  try {
    const { data, status } = await client.post(apiPath(endpoint), body, {
      validateStatus: accepted, headers: modal ? { "X-Requested-With": "XMLHttpRequest" } : {},
    });
    if (status === 403) return { kind: "forbidden", data };
    if (status === 400) return asignacionFormValid(data) ? { kind: "invalid", data } : { kind: "uncertain" };
    if (record(data) && data.ok === true && internal(data.redirect)) return { kind: "redirect", to: data.redirect as string };
    if (record(data) && data.ok === true && text(data.mensaje) && typeof data.otra === "boolean") {
      return { kind: "json", mensaje: data.mensaje, otra: data.otra };
    }
  } catch {
    // Network error or timeout after sending: the result is unknown.
  }
  return { kind: "uncertain" };
}

export type RemoveOutcome = { kind: "redirect"; to: string } | { kind: "forbidden"; data: unknown } | { kind: "uncertain" };

/** POST of the removal («Quitar»), once; a lost response is reported, never retried. */
export async function quitarAsignacion(endpoint: string): Promise<RemoveOutcome> {
  try {
    const { data, status } = await client.post(apiPath(endpoint), new URLSearchParams(), { validateStatus: accepted });
    if (status === 403) return { kind: "forbidden", data };
    if (status === 200 && record(data) && data.ok === true && internal(data.redirect)) return { kind: "redirect", to: data.redirect as string };
  } catch {
    // Network error or timeout after sending: the result is unknown.
  }
  return { kind: "uncertain" };
}

/** `panel.js` «otra visita» notice: same text, failures leave the notice as it was. */
export async function verificarAsignacion(url: string, values: { fecha: string; inspector: string; escuela: string }): Promise<string | null | undefined> {
  const query = new URLSearchParams({ fecha: values.fecha, inspector: values.inspector, escuela: values.escuela });
  try {
    const { data } = await client.get(`${apiPath(url)}?${query.toString()}`);
    if (!record(data) || !Array.isArray(data.otras) || !data.otras.every(text)) return undefined;
    if (!data.otras.length) return null;
    if (!text(data.escuela)) return undefined;
    return `${data.escuela} ya está asignada en esta jornada a ${data.otras.join(", ")}. Podés asignarla igual: cuenta como otra visita y no reemplaza la anterior.`;
  } catch {
    return undefined;
  }
}
