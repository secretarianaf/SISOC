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
  VITE_SENTRY_REPLAYS?: string;
};

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
    release: entorno.VITE_SENTRY_RELEASE,
    // Datos de salud y sociales: nunca se adjunta PII por defecto.
    sendDefaultPii: false,
    integrations: replaysActivos
      ? [Sentry.replayIntegration({ maskAllText: true, blockAllMedia: true })]
      : [],
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: replaysActivos ? 1 : 0,
  });

  Sentry.setTag("frontend", `v2-${modulo}`);
}
