/**
 * Behaviour of the inline script of `centrodeinfancia_form.html` (CDI centre create and edit) that does not
 * touch the DOM: the CUIT mask, the opening hours of the selected days and the cascading geography selects.
 * The route module owns the state; this file only holds the rules, so they can be tested alone.
 */
export type Hora = { apertura: string; cierre: string };
export type Horarios = Record<string, Hora>;
export type Choice = { value: string; label: string; decil?: string };

/** `formatCuit`: digits only, up to 11, as `NN-NNNNNNNN-N`. */
export function formatCuit(value: string): string {
  const digits = (value || "").replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 2) return digits;
  if (digits.length <= 10) return `${digits.slice(0, 2)}-${digits.slice(2)}`;
  return `${digits.slice(0, 2)}-${digits.slice(2, 10)}-${digits.slice(10)}`;
}

const VACIA: Hora = { apertura: "", cierre: "" };

/**
 * `refreshHorarioRows` + `copyFirstScheduleToOthers`: an unchecked day loses its hours (and its "touched"
 * mark); the first selected day that has an hour copies it into the empty fields of the other selected days
 * that nobody edited. `seleccionados` keeps the order of the days, like the check-boxes of the page.
 */
export function aplicarHorarios(
  dias: string[],
  seleccionados: string[],
  horarios: Horarios,
  tocados: Record<string, boolean>,
): { horarios: Horarios; tocados: Record<string, boolean> } {
  const siguienteHorarios: Horarios = { ...horarios };
  const siguienteTocados = { ...tocados };
  for (const dia of dias) {
    if (!seleccionados.includes(dia)) {
      siguienteHorarios[dia] = { ...VACIA };
      siguienteTocados[dia] = false;
    }
  }
  const primero = seleccionados
    .map((dia) => siguienteHorarios[dia] ?? VACIA)
    .find((hora) => hora.apertura || hora.cierre);
  if (primero) {
    for (const dia of seleccionados.slice(1)) {
      if (siguienteTocados[dia]) continue;
      const actual = siguienteHorarios[dia] ?? VACIA;
      siguienteHorarios[dia] = { apertura: actual.apertura || primero.apertura, cierre: actual.cierre || primero.cierre };
    }
  }
  return { horarios: siguienteHorarios, tocados: siguienteTocados };
}

export const PLACEHOLDER = { departamento: "Seleccione un departamento", municipio: "Seleccione un municipio", localidad: "Seleccione una localidad" } as const;

/** `ensurePlaceholder`: a select without an empty option gets one at the top. */
export function conPlaceholder(options: Choice[], label: string): Choice[] {
  return options.some((option) => option.value === "") ? options : [{ value: "", label }, ...options];
}

type Geo = { id: number | string; nombre?: string; nombre_region?: string; decil_ipi?: number | string | null };

/** `replaceOptions`: the empty option first, then each row (`decil_ipi` only when the row has it). */
export function opcionesDe(rows: unknown, label: string): Choice[] {
  const list = Array.isArray(rows) ? (rows as Geo[]) : [];
  return [
    { value: "", label },
    ...list.map((row) => ({
      value: String(row.id),
      label: row.nombre || row.nombre_region || "",
      ...(row.decil_ipi !== null && row.decil_ipi !== undefined ? { decil: String(row.decil_ipi) } : {}),
    })),
  ];
}

/** The selected value survives a reload of the options only when the new list has it. */
export const seleccion = (options: Choice[], value: string): string => (value && options.some((o) => o.value === value) ? value : "");

/** Same-origin JSON for the cascading selects (an answer that is not ok is an empty list); replaceable in tests. */
export const geography = {
  load: async (url: string): Promise<unknown> => {
    const response = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" });
    return response.ok ? response.json() : [];
  },
};
