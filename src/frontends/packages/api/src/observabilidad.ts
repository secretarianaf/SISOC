/**
 * Sentry del front v2 (`frontend_v2.md`, seccion 11).
 *
 * Usa el **mismo proyecto que el back**. Lo que exige el documento:
 *
 * - `environment` igual que el del back del entorno.
 * - `release` = SHA del commit.
 * - tag `frontend=v2-<modulo>`.
 * - `sendDefaultPii: false`, porque son datos de salud y sociales.
 * - Replays solo si el back los tiene activos, siempre con `maskAllText` y
 *   `blockAllMedia`.
 *
 * Sin DSN no hace nada: en local no se manda telemetria y no hay que configurar
 * nada para levantar el front.
 */
import * as Sentry from "@sentry/react";

export type OpcionesObservabilidad = {
  /** Nombre del modulo, para el tag `frontend=v2-<modulo>`. */
  modulo: string;
};

/**
 * Toda `VITE_*` es publica por definicion (queda en el bundle): aca no va
 * ningun secreto. El DSN de Sentry es publico por diseño.
 */
type EntornoVite = {
  VITE_SENTRY_DSN?: string;
  VITE_SENTRY_ENVIRONMENT?: string;
  VITE_SENTRY_RELEASE?: string;
  /** El que pasan el Dockerfile y los compose como build arg. */
  VITE_RELEASE_SHA?: string;
  VITE_SENTRY_REPLAYS?: string;
};

/**
 * La URL sin query string. Los filtros viajan en la query (el reporte filtra
 * por `documento_persona`) y Sentry guarda la URL completa de cada request.
 */
const sinQuery = (url: unknown) =>
  typeof url === "string" ? url.split("?")[0] : url;

export function iniciarObservabilidad(
  { modulo }: OpcionesObservabilidad,
  entorno: EntornoVite,
): void {
  const dsn = entorno.VITE_SENTRY_DSN;
  if (!dsn) return;

  const replaysActivos = entorno.VITE_SENTRY_REPLAYS === "true";

  Sentry.init({
    dsn,
    environment: entorno.VITE_SENTRY_ENVIRONMENT || "development",
    release: entorno.VITE_SENTRY_RELEASE || entorno.VITE_RELEASE_SHA,
    // Datos de salud y sociales: nunca se adjunta PII por defecto.
    sendDefaultPii: false,
    integrations: replaysActivos
      ? [Sentry.replayIntegration({ maskAllText: true, blockAllMedia: true })]
      : [],
    beforeBreadcrumb: (breadcrumb) => {
      const data = breadcrumb.data;
      if (data && "url" in data) data.url = sinQuery(data.url);
      if (data && "to" in data) data.to = sinQuery(data.to);
      if (data && "from" in data) data.from = sinQuery(data.from);
      return breadcrumb;
    },
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: replaysActivos ? 1 : 0,
  });

  Sentry.setTag("frontend", `v2-${modulo}`);
}
