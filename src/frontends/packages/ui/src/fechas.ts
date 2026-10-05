/**
 * Formato de fechas del front v2.
 *
 * `frontend_v2.md` (sección 7) dice que el back manda ISO 8601 y el front
 * formatea para mostrar en es-AR. El problema es que `toLocaleDateString("es-AR")`
 * devuelve `1/10/2026` y `5/6/2000`: sin ceros y de ancho variable, que en una
 * tabla queda desprolijo y se lee peor.
 *
 * Acá se fija **DD/MM/YYYY** con ceros, que es el formato que usan los Excel de
 * Celiaquía y el que muestran las pantallas Django.
 *
 * Todo esto es presentación: lo que viaja a la API sigue siendo lo que
 * declara el contrato.
 */

const dosDigitos = (n: number) => String(n).padStart(2, "0");

/** Convierte lo que venga a Date, o null si no es una fecha usable. */
const aFecha = (valor: string | Date | null | undefined): Date | null => {
  if (!valor) return null;
  const fecha = valor instanceof Date ? valor : new Date(valor);
  return Number.isNaN(fecha.getTime()) ? null : fecha;
};

/**
 * `DD/MM/YYYY`. Devuelve `vacio` si el valor no es una fecha.
 *
 * El default es un guion y no una cadena vacía para que una celda sin fecha se
 * distinga de una que no cargó.
 */
export function formatearFecha(
  valor: string | Date | null | undefined,
  vacio = "—",
): string {
  const fecha = aFecha(valor);
  if (!fecha) return vacio;
  return `${dosDigitos(fecha.getDate())}/${dosDigitos(
    fecha.getMonth() + 1,
  )}/${fecha.getFullYear()}`;
}

/** `DD/MM/YYYY HH:mm`. Para historiales, donde la hora distingue dos eventos. */
export function formatearFechaHora(
  valor: string | Date | null | undefined,
  vacio = "—",
): string {
  const fecha = aFecha(valor);
  if (!fecha) return vacio;
  return `${formatearFecha(fecha)} ${dosDigitos(fecha.getHours())}:${dosDigitos(
    fecha.getMinutes(),
  )}`;
}

/**
 * Normaliza a `DD/MM/YYYY` un valor crudo de Excel, para editarlo.
 *
 * Los registros erróneos traen la fecha tal como vino del archivo:
 * `2000-06-25 00:00:00`, `2000-06-25` o ya `25/06/2000`. Mostrar el timestamp
 * crudo en un formulario es ilegible.
 *
 * Si no se reconoce el valor se devuelve **tal cual**: puede ser justamente el
 * dato mal cargado que el usuario tiene que corregir, y pisarlo le ocultaría
 * qué vino en el archivo.
 */
export function normalizarFechaEditable(valor: string): string {
  const texto = (valor ?? "").trim();
  if (!texto) return "";

  const yaEsDdMmAaaa = /^\d{2}\/\d{2}\/\d{4}$/.test(texto);
  if (yaEsDdMmAaaa) return texto;

  // `YYYY-MM-DD` con hora opcional. No se usa `new Date()` a propósito: con
  // una fecha sin zona la interpreta como UTC y puede correr un día.
  const iso = texto.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T].*)?$/);
  if (iso) {
    const [, anio, mes, dia] = iso;
    return `${dia}/${mes}/${anio}`;
  }

  return texto;
}
