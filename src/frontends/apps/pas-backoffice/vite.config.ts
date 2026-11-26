import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/v2/pas/",
  plugins: [react()],
  test: { name: "pas-backoffice", include: ["src/**/*.test.{ts,tsx}"], environment: "jsdom" },
});
