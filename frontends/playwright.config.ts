import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.e2e.ts",
  outputDir: process.env.PLAYWRIGHT_OUTPUT_DIR || "./test-results",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:4173",
    channel: process.env.PLAYWRIGHT_CHANNEL,
    headless: true,
  },
  webServer: process.env.PLAYWRIGHT_BASE_URL ? undefined : {
    command: "npm exec -w @sisoc/vpsl -- vite preview --host 127.0.0.1 --port 4173",
    url: "http://127.0.0.1:4173/v2/vpsl/",
    reuseExistingServer: false,
  },
});
