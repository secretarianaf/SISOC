import { useQuery } from "@tanstack/react-query";
import { inetGet } from "@sisoc/api";

export const ROOT = "/v2/inet/";
export const resources = {
  centros: { title: "Centros de Formación Profesional", singular: "CFP", model: "centro" },
  cursos: { title: "Oferta educativa", singular: "curso", model: "curso" },
  comisiones: { title: "Comisiones", singular: "comisión", model: "comisioncurso" },
  horarios: { title: "Horarios", singular: "horario", model: "comisionhorario" },
  contactos: { title: "Contactos", singular: "contacto", model: "institucioncontacto" },
  ubicaciones: { title: "Ubicaciones", singular: "ubicación", model: "institucionubicacion" },
  planes: { title: "Planes curriculares", singular: "plan curricular", model: "planversioncurricular" },
  inscripciones: { title: "Inscriptos", singular: "inscripto", model: "inscripcion" },
  sesiones: { title: "Clases", singular: "clase", model: "asistenciasesion" },
} as const;
export type Resource = keyof typeof resources;
export function useInet<T>(path: string, enabled = true) {
  return useQuery({ queryKey: ["inet", path], queryFn: () => inetGet<T>(path), enabled });
}
export function queryString(values: Record<string, unknown>) {
  return new URLSearchParams(Object.entries(values).filter(([, value]) => value !== undefined && value !== null && value !== "").map(([key, value]) => [key, String(value)])).toString();
}
// Intl lanza RangeError con fechas inválidas: un valor vacío o mal formado no debe romper la pantalla.
function validDate(value: unknown) {
  if (typeof value !== "string" || !value) return undefined;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
}
export function formatDate(value: string | null | undefined) {
  const date = validDate(value);
  return date ? new Intl.DateTimeFormat("es-AR", { timeZone: "UTC", day: "2-digit", month: "2-digit", year: "numeric" }).format(date) : "—";
}
/** dd/mm, como en los resúmenes de período de Figma. */
export function shortDate(value: string | null | undefined) {
  return validDate(value) ? formatDate(value).slice(0, 5) : "—";
}
/** "Lunes 07/09/2026". */
export function weekdayDate(value: string | null | undefined) {
  const date = validDate(value);
  if (!date) return "—";
  const day = new Intl.DateTimeFormat("es-AR", { timeZone: "UTC", weekday: "long" }).format(date);
  return `${day.charAt(0).toUpperCase()}${day.slice(1)} ${formatDate(value)}`;
}

export function updateField(values: Record<string, unknown>, name: string, value: unknown) {
  const next = { ...values, [name]: value };
  const dependents: Record<string, string[]> = { provincia: ["municipio", "localidad"], municipio: ["localidad"], sector: ["subsector"] };
  for (const field of dependents[name] ?? []) next[field] = "";
  return next;
}

export function validationFields(error: unknown): Record<string, string> {
  const data = (error as { response?: { data?: Record<string, unknown> } })?.response?.data;
  return Object.fromEntries(Object.entries((data?.campos && typeof data.campos === "object" ? data.campos : data) ?? {}).map(([key, value]) => [key, Array.isArray(value) ? value.join(" ") : String(value)]));
}
