/** Contract of /pas/ddjj/formulario/<token>/datos and /enviar (src/backends/pas/pas/web_ddjj.py). */

export type Option = { id: string; label: string };

export type TextField =
  | "calle"
  | "altura"
  | "provincia"
  | "municipio"
  | "correo_electronico"
  | "telefono_celular";

export type AnswerField =
  | "embarazada"
  | "controles_embarazo_cumplidos"
  | "hijos_menores_a_cargo"
  | "vacunacion_cumplida"
  | "regularidad_escolar_acreditada"
  | "gastos_bajo_limite_smvm"
  | "no_accedio_mercado_cambios";

export type FormValues = Record<TextField | AnswerField, string> & {
  acepto_declaracion: boolean;
};

export type DdjjPayload = {
  values: FormValues;
  existing: Record<TextField, boolean>;
  labels: Record<
    Exclude<TextField, "altura"> | "embarazada" | "acepto_declaracion",
    string
  >;
  empty_label: string;
  provinces: Option[];
  municipalities: Option[];
  urls: { municipalities: string; submit: string; confirmation: string };
  errors?: Record<string, string[]>;
};

export const TEXT_FIELDS: TextField[] = [
  "calle",
  "altura",
  "provincia",
  "municipio",
  "correo_electronico",
  "telefono_celular",
];

export const ANSWER_FIELDS: AnswerField[] = [
  "embarazada",
  "controles_embarazo_cumplidos",
  "hijos_menores_a_cargo",
  "vacunacion_cumplida",
  "regularidad_escolar_acreditada",
  "gastos_bajo_limite_smvm",
  "no_accedio_mercado_cambios",
];

/**
 * The visible questions are the negation of these field names, so the native
 * script (pas_ddjj.js) swaps the radio values: visible «Sí» submits "no".
 */
export const INVERTED_FIELDS: AnswerField[] = [
  "gastos_bajo_limite_smvm",
  "no_accedio_mercado_cambios",
];

/** Step (0-based) whose `.errorlist` the native page opens first after a 400. */
export const FIELD_STEP: Record<string, number> = {
  calle: 0,
  altura: 0,
  provincia: 0,
  municipio: 0,
  correo_electronico: 0,
  telefono_celular: 0,
  embarazada: 1,
  controles_embarazo_cumplidos: 1,
  hijos_menores_a_cargo: 2,
  vacunacion_cumplida: 2,
  regularidad_escolar_acreditada: 2,
  gastos_bajo_limite_smvm: 3,
  no_accedio_mercado_cambios: 3,
  acepto_declaracion: 4,
};

export const flip = (value: string) =>
  value === "si" ? "no" : value === "no" ? "si" : value;

/** Value a radio input submits for its visible option ("si" → «Sí», "no" → «No»). */
export const submittedValue = (field: AnswerField, visible: "si" | "no") =>
  INVERTED_FIELDS.includes(field) ? flip(visible) : visible;

/**
 * Answers shown again after a native HTTP 400. Django checks the input whose
 * original value equals the posted value and pas_ddjj.js swaps the values
 * afterwards, so an inverted answer comes back with the opposite visible
 * option. Reproduced on purpose for visual/functional parity; see the record
 * 2026-11-06-2806-react-ddjj-publica.md (pending product decision).
 */
export function answersAfterServerError(values: FormValues) {
  const answers = {} as Record<AnswerField, string>;
  for (const field of ANSWER_FIELDS) {
    answers[field] = INVERTED_FIELDS.includes(field)
      ? flip(values[field])
      : values[field];
  }
  return answers;
}

export function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  const item = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  return item ? decodeURIComponent(item.slice(prefix.length)) : null;
}

export type SubmitOutcome =
  | { kind: "confirmed"; redirect: string }
  | { kind: "invalid"; payload: DdjjPayload }
  | { kind: "reload" };

/**
 * Single POST attempt. Anything other than success or a validation error
 * (unavailable invitation, restricted session, network loss) returns "reload":
 * the caller goes back to the canonical URL with a GET, never a POST replay.
 */
export async function submitDeclaration(
  url: string,
  body: URLSearchParams,
): Promise<SubmitOutcome> {
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      redirect: "manual",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "X-CSRFToken": readCookie("csrftoken") ?? "",
      },
      body,
    });
  } catch {
    return { kind: "reload" };
  }
  try {
    if (response.status === 200) {
      const data = (await response.json()) as { redirect?: unknown };
      if (typeof data.redirect === "string") {
        return { kind: "confirmed", redirect: data.redirect };
      }
    }
    if (response.status === 400) {
      return { kind: "invalid", payload: (await response.json()) as DdjjPayload };
    }
  } catch {
    return { kind: "reload" };
  }
  return { kind: "reload" };
}

export async function loadDeclaration(
  url: string,
): Promise<DdjjPayload | "reload" | "error"> {
  try {
    const response = await fetch(url, {
      credentials: "same-origin",
      redirect: "manual",
    });
    if (response.status === 200) return (await response.json()) as DdjjPayload;
    if ([404, 410].includes(response.status) || response.type === "opaqueredirect") {
      return "reload";
    }
  } catch {
    return "error";
  }
  return "error";
}
