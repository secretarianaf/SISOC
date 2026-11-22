import { crearCliente } from "@sisoc/api";
import { safeInternalPath } from "../webAccess";
import type { InspOption } from "./InspSelect2";
import type { ClaroLayout } from "./ClaroFrame";
import type { InspMessage } from "./inspeccionesToasts";

/** Data contract, validation and POST of the Escuelas tab web API (IN05). */
export type Field = { value: string; errors: string[] };
export const FIELDS = ["provincia", "localidad", "cueanexo", "cp", "nombre", "domicilio", "telefono", "mail"] as const;
export type EscuelaFormData = {
  layout: ClaroLayout;
  tabs: { id: string; label: string; url: string }[];
  totales: Totales;
  editar: boolean;
  aviso: { motivos: string; localidad_original: string } | null;
  non_field_errors: string[];
  fields: Record<(typeof FIELDS)[number], Field>;
  localidad_inicial: InspOption | null;
  duplicada_url: string | null;
  options: { provincias: { id: number; nombre: string }[]; localidades_url: string };
  messages: InspMessage[];
};
export type Totales = { escuelas: number; escuelas_a_revisar: number; jornada: string; asignaciones_hoy: number; actas_hoy: number };

export const client = crearCliente("/api");
const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object";
const text = (v: unknown): v is string => typeof v === "string";
export const internal = (v: unknown) => text(v) && safeInternalPath(v) === v;
const API_PREFIX = "/api/web/inspecciones/";
export const apiPath = (url: string) => url.slice("/api/".length);
export const apiUrlValid = (v: unknown) => internal(v) && (v as string).startsWith(API_PREFIX);

export function layoutValid(l: unknown): l is ClaroLayout {
  return record(l) && Array.isArray(l.breadcrumb) && l.breadcrumb.every((b) => record(b) && text(b.text) && (b.url === null || internal(b.url))) &&
    text(l.display_name) && text(l.role) && text(l.initials);
}
export function tabsValid(v: unknown) {
  return Array.isArray(v) && v.every((t) => record(t) && text(t.id) && text(t.label) && internal(t.url));
}
export function totalesValid(v: unknown): v is Totales {
  return record(v) && ["escuelas", "escuelas_a_revisar", "asignaciones_hoy", "actas_hoy"].every((k) => Number.isSafeInteger(v[k])) && text(v.jornada);
}
export function messagesValid(v: unknown): v is InspMessage[] {
  return Array.isArray(v) && v.every((m) => record(m) && text(m.message) && ["success", "error", "warning", "info"].includes(m.level as string));
}
export function optionValid(v: unknown): v is InspOption {
  return record(v) && Number.isSafeInteger(v.id) && text(v.text);
}
export function provinciasValid(v: unknown) {
  return Array.isArray(v) && v.every((p) => record(p) && Number.isSafeInteger(p.id) && text(p.nombre));
}
export function escuelaFormValid(v: unknown): v is EscuelaFormData {
  if (!record(v) || !record(v.fields) || !record(v.options)) return false;
  const f = v.fields;
  return layoutValid(v.layout) && tabsValid(v.tabs) && totalesValid(v.totales) && typeof v.editar === "boolean" &&
    (v.aviso === null || (record(v.aviso) && text(v.aviso.motivos) && text(v.aviso.localidad_original))) &&
    Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) &&
    FIELDS.every((k) => record(f[k]) && text(f[k].value) && Array.isArray(f[k].errors) && (f[k].errors as unknown[]).every(text)) &&
    (v.localidad_inicial === null || optionValid(v.localidad_inicial)) && (v.duplicada_url === null || internal(v.duplicada_url)) &&
    provinciasValid(v.options.provincias) && apiUrlValid(v.options.localidades_url) && messagesValid(v.messages);
}

export type Outcome =
  | { kind: "json"; ok: true; mensaje: string; otra: boolean }
  | { kind: "redirect"; to: string }
  | { kind: "invalid"; data: EscuelaFormData }
  | { kind: "forbidden"; data: unknown }
  | { kind: "uncertain" };

const accepted = (status: number) => (status >= 200 && status < 300) || status === 400 || status === 403;

/** POST once (modal: with `X-Requested-With`, like `panel.js`); never retried. */
export async function postEscuela(endpoint: string, body: URLSearchParams, modal: boolean): Promise<Outcome> {
  try {
    const { data, status } = await client.post(apiPath(endpoint), body, {
      validateStatus: accepted, headers: modal ? { "X-Requested-With": "XMLHttpRequest" } : {},
    });
    if (status === 403) return { kind: "forbidden", data };
    if (status === 400) return escuelaFormValid(data) ? { kind: "invalid", data } : { kind: "uncertain" };
    if (record(data) && data.ok === true && internal(data.redirect)) return { kind: "redirect", to: data.redirect as string };
    if (record(data) && data.ok === true && text(data.mensaje) && typeof data.otra === "boolean") {
      return { kind: "json", ok: true, mensaje: data.mensaje, otra: data.otra };
    }
  } catch {
    // Network error or timeout after sending: the result is unknown.
  }
  return { kind: "uncertain" };
}
