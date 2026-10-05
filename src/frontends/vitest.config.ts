import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

/**
 * Un proyecto por workspace, para que cada app corra con su propia config.
 *
 * Hace falta porque las dos apps declaran el entorno distinto y ninguna de las
 * dos esta mal: vpsl lo pone por archivo (`// @vitest-environment jsdom`) y
 * celiaquia en `apps/celiaquia/vite.config.ts`, que ademas trae `setupFiles`.
 * Corriendo todo bajo una sola config, la de celiaquia se ignora y sus tests
 * se caen con `document is not defined`.
 */
export default defineConfig({
  plugins: [react()],
  test: {
    projects: [
      // Los paquetes compartidos no tienen config propia.
      {
        extends: true,
        test: { name: "packages", include: ["packages/**/*.test.{ts,tsx}"] },
      },
      "apps/vpsl",
      "apps/celiaquia",
    ],
  },
});
