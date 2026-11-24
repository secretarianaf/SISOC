/**
 * The behaviour script of `destinatario_form.html` (`static/custom/js/destinatarioForm.js`) as pure
 * functions over the form values: section progress, age from the birth date and the geography lists.
 */
export type Values = Record<string, string>;
export type Multi = Record<string, string[]>;
export type Estado = "complete" | "incomplete" | "empty";

export const SECCIONES = ["registro", "nino", "responsable1", "responsable2", "domicilio", "cultura", "discapacidad", "salud", "nutricion", "vacunacion"] as const;
export type Seccion = (typeof SECCIONES)[number];

export const VACUNAS = [
  "bcg", "neumococo", "quintuple", "polio", "rotavirus", "meningococo", "antigripal", "hepatitis_a", "triple_viral", "varicela",
  "triple_bacteriana_celular", "triple_bacteriana_acelular", "sincicial_respiratorio", "fiebre_amarilla",
];

const R = (prefix: string) => [
  "tipo_documentacion", "dni", "apellido", "nombre", "fecha_nacimiento", "cuit", "sin_cuil", "sexo_registral", "nacionalidad", "relacion",
  "telefono", "pais_nacimiento", "nivel_educativo", "consentimiento",
].map((n) => `${prefix}_${n}`);

/** Names of the fields (and check-box groups) each section card holds: what `hasSectionData` scans. */
export const CAMPOS_DE: Record<Seccion, { fields: string[]; groups: string[] }> = {
  registro: { fields: ["estado", "tipo_registro", "fecha_registro", "trabajador_registra"], groups: [] },
  nino: {
    fields: ["apellido", "nombre", "fecha_nacimiento", "edad_calculada", "edad_unidad", "sexo", "tipo_documentacion", "dni", "cuit_nino", "sin_cuil_nino", "pais_nacimiento", "nacionalidad", "sala"],
    groups: [],
  },
  responsable1: { fields: R("responsable_legal_1"), groups: [] },
  responsable2: { fields: R("responsable_legal_2").filter((n) => n !== "responsable_legal_2_sin_cuil"), groups: [] },
  domicilio: {
    fields: ["calle_domicilio", "altura_domicilio", "piso_domicilio", "departamento_domicilio", "tipo_barrio", "provincia_domicilio", "departamento", "decil_ipi", "municipio_domicilio", "localidad_domicilio", "convivientes"],
    groups: [],
  },
  cultura: { fields: ["pueblo_originario_cual", "necesito_interprete"], groups: ["grupo_pertenencia", "lenguajes"] },
  discapacidad: { fields: ["tiene_discapacidad", "posee_cud", "numero_cud", "recibe_apoyo_desarrollo"], groups: ["tipo_discapacidad"] },
  salud: { fields: ["cobertura_salud", "controles_sanitarios_ultimo_anio", "calendario_vacunacion_al_dia", "talla", "peso", "longitud_acostado", "perimetro_cefalico"], groups: [] },
  nutricion: { fields: ["lactancia", "anses_auh", "anses_aue", "anses_acsi", "anses_acn"], groups: ["alergias_alimentarias"] },
  vacunacion: { fields: VACUNAS.flatMap((v) => [`vacuna_${v}_dosis`, `vacuna_${v}_fecha`]), groups: [] },
};
/** Fields rendered as check boxes: they only count when checked. */
const CASILLAS = new Set(["sin_cuil_nino", "responsable_legal_1_sin_cuil"]);

export function hasSectionData(id: Seccion, values: Values, multi: Multi): boolean {
  const { fields, groups } = CAMPOS_DE[id];
  if (fields.some((n) => !CASILLAS.has(n) && (values[n] ?? "").trim() !== "")) return true;
  if (fields.some((n) => CASILLAS.has(n) && values[n])) return true;
  return groups.some((g) => (multi[g] ?? []).length > 0);
}

/** `checkSection*`: is the section complete. */
export function sectionComplete(id: Seccion, values: Values, multi: Multi): boolean {
  const v = (n: string) => (values[n] ?? "").trim();
  switch (id) {
    case "registro": return v("tipo_registro") !== "" || v("fecha_registro") !== "";
    case "nino": return v("nombre") !== "" && v("apellido") !== "" && v("dni") !== "";
    case "responsable1": return v("responsable_legal_1_relacion") !== "" && v("responsable_legal_1_apellido") !== "";
    case "responsable2": return !hasSectionData("responsable2", values, multi) || (v("responsable_legal_2_relacion") !== "" && v("responsable_legal_2_apellido") !== "");
    case "domicilio": return v("calle_domicilio") !== "" || v("localidad_domicilio") !== "";
    case "cultura": return true;
    case "discapacidad": return v("tiene_discapacidad") !== "";
    case "salud": return v("cobertura_salud") !== "";
    case "nutricion": return v("lactancia") !== "" || v("diagnostico_peso") !== "";
    case "vacunacion": return VACUNAS.some((c) => v(`vacuna_${c}_dosis`) !== "");
  }
}

export function progress(values: Values, multi: Multi): { estados: Record<Seccion, Estado>; completadas: number } {
  const estados = {} as Record<Seccion, Estado>;
  let completadas = 0;
  SECCIONES.forEach((id) => {
    if (sectionComplete(id, values, multi)) { estados[id] = "complete"; completadas += 1; }
    else estados[id] = hasSectionData(id, values, multi) ? "incomplete" : "empty";
  });
  return { estados, completadas };
}

/** `calcular` of the age script: years, or months under one year; `null` keeps the unit untouched. */
export function calcularEdad(value: string, hoy: Date = new Date()): { edad: string; unidad: "meses" | "anios" | null } {
  if (!value) return { edad: "", unidad: null };
  const nac = new Date(`${value}T00:00:00`);
  if (Number.isNaN(nac.getTime())) return { edad: "", unidad: null };
  let anios = hoy.getFullYear() - nac.getFullYear();
  const mes = hoy.getMonth() - nac.getMonth();
  if (mes < 0 || (mes === 0 && hoy.getDate() < nac.getDate())) anios -= 1;
  if (anios < 1) {
    let meses = (hoy.getFullYear() - nac.getFullYear()) * 12 + (hoy.getMonth() - nac.getMonth());
    if (hoy.getDate() < nac.getDate()) meses -= 1;
    return { edad: String(meses >= 0 ? meses : 0), unidad: "meses" };
  }
  return { edad: String(anios), unidad: "anios" };
}

export type GeoItem = { id: number | string; nombre?: string; nombre_region?: string; decil_ipi?: number | null };
export type GeoOption = { value: string; label: string; decil: string };

/** `loadOptions` / `loadDepartamentos`: the same Ajax lists the native script reads. */
export async function cargarLista(url: string): Promise<GeoItem[]> {
  const response = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return (await response.json()) as GeoItem[];
}

export function aOpciones(items: GeoItem[], vacio: string): GeoOption[] {
  return [{ value: "", label: vacio, decil: "" }, ...items.map((i) => ({ value: String(i.id), label: i.nombre || i.nombre_region || "", decil: i.decil_ipi == null ? "" : String(i.decil_ipi) }))];
}

export const SIN_ALCANCE = "No hay municipios disponibles para su jurisdicción.";
export const VACIO = { departamento: "Seleccionar departamento...", municipio: "Seleccionar municipio...", localidad: "Seleccionar localidad..." };
