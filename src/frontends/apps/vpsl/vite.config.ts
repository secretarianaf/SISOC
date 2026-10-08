import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

// Keep Fast Refresh compatible with Django script-src without unsafe-inline.
function externalReactPreamble(): Plugin {
  const path = "/v2/vpsl/react-refresh-preamble.js";
  return {
    name: "vpsl-external-react-preamble",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use(path, (_request, response) => {
        response.setHeader("Content-Type", "application/javascript");
        response.end(react.preambleCode.replace("__BASE__", "/v2/vpsl/"));
      });
    },
    transformIndexHtml: {
      order: "post",
      handler(html) {
        return html.replace(/<script type="module">[\s\S]*?window\.\$RefreshReg\$[\s\S]*?<\/script>/, `<script type="module" src="${path}"></script>`);
      },
    },
  };
}

export default defineConfig({
  base: "/v2/vpsl/",
  plugins: [react(), externalReactPreamble()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/@sentry/")) return "sentry";
          if (id.includes("node_modules/@mui/") || id.includes("node_modules/@emotion/")) return "mui";
          if (id.includes("node_modules/react") || id.includes("node_modules/scheduler/")) return "react";
          if (id.includes("node_modules/@tanstack/")) return "query";
          return undefined;
        },
      },
    },
  },
  server: {
    host: "0.0.0.0",
    hmr: { host: "localhost", clientPort: 5173 },
    proxy: { "/api/vpsl": "http://django:8000" },
  },
});
