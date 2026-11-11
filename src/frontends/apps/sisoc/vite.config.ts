import { defineConfig, type Plugin } from "vitest/config";
import react from "@vitejs/plugin-react";

function externalReactPreamble(): Plugin {
  const path = "/v2/sisoc/react-refresh-preamble.js";
  return {
    name: "sisoc-external-react-preamble",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use(path, (_request, response) => {
        response.setHeader("Content-Type", "application/javascript");
        response.end(react.preambleCode.replace("__BASE__", "/v2/sisoc/"));
      });
    },
    transformIndexHtml: {
      order: "post",
      handler(html) {
        return html.replace(
          /<script type="module">[\s\S]*?window\.\$RefreshReg\$[\s\S]*?<\/script>/,
          `<script type="module" src="${path}"></script>`,
        );
      },
    },
  };
}

export default defineConfig({
  base: "/v2/sisoc/",
  plugins: [react(), externalReactPreamble()],
  test: {
    name: "sisoc",
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./src/testSetup.ts"],
    testTimeout: 20000,
  },
  server: {
    host: "127.0.0.1",
    port: 5176,
    strictPort: true,
    hmr: { host: "127.0.0.1", clientPort: 5176 },
    proxy: {
      "/api/web": { target: "http://127.0.0.1:18885", changeOrigin: false },
      "/api/insumos": "http://127.0.0.1:18885",
      "/static/": "http://127.0.0.1:18885",
      "/v2/sisoc/static/": {
        target: "http://127.0.0.1:18885",
        changeOrigin: false,
        rewrite: (path) => path.replace(/^\/v2\/sisoc(?=\/static\/)/, ""),
      },
      "^/(?!v2/sisoc(?:/|$)|api(?:/|$)|static(?:/|$)|@vite(?:/|$)|@id(?:/|$)|@fs(?:/|$)).*": {
        target: "http://127.0.0.1:18885",
        changeOrigin: false,
      },
    },
  },
});
