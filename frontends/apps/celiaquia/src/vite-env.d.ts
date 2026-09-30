/// <reference types="vite/client" />

/**
 * Variables de entorno del build. Toda `VITE_*` queda en el bundle: es publica
 * por definicion y nunca lleva secretos (`frontend_v2.md`, seccion 8).
 */
interface ImportMetaEnv {
  /** DSN de Sentry. Vacio en local: sin el, no se inicializa. */
  readonly VITE_SENTRY_DSN?: string;
  /** Igual al `environment` del back del entorno. */
  readonly VITE_SENTRY_ENVIRONMENT?: string;
  /** SHA del commit desplegado. */
  readonly VITE_SENTRY_RELEASE?: string;
  /** "true" solo si el back del entorno tiene replays activos. */
  readonly VITE_SENTRY_REPLAYS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
