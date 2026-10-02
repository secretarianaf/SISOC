import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

/**
 * La app se sirve bajo /v2/celiaquia/: Django recibe esa ruta y la reenvia a
 * este servicio. El `base` tiene que coincidir o los assets con hash no
 * resuelven.
 *
 * En desarrollo el navegador entra por Django, pero el websocket de HMR
 * conecta directo al puerto de Vite, porque Django no reenvia websockets.
 */
export default defineConfig({
  base: "/v2/celiaquia/",
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    hmr: { protocol: "ws", host: "localhost", port: 5173 },
    proxy: {
      // Solo para levantar la app suelta contra el back local.
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
