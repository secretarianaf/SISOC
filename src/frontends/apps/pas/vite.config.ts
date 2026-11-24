import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The public DDJJ keeps PAS's own stylesheet (/static/custom/css/pas_ddjj.css);
// the build is served by pas/ddjj_preview.py, which rewrites /v2/pas/assets/.
export default defineConfig({
  base: "/v2/pas/",
  plugins: [react()],
  test: {
    name: "pas",
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
