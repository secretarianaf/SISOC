import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";

/**
 * Config compartida por las dos apps del monorepo.
 *
 * De VPSL: los ignores de `.npm-cache` y del `generated.ts` (es generado,
 * lintearlo no aporta) y los globals de node, que usan sus configs de Vite.
 * De Celiaquia: las reglas de react-hooks y react-refresh.
 */
export default tseslint.config(
  {
    ignores: [
      "**/dist/**",
      "**/node_modules/**",
      ".npm-cache/**",
      // Generados desde el contrato OpenAPI.
      "packages/api/src/generated.ts",
      "packages/api/src/openapi.d.ts",
    ],
  },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser, ...globals.node },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/no-non-null-assertion": "off",
    },
  },
  {
    // react-refresh solo tiene sentido en las apps: son las que hacen HMR.
    files: ["apps/*/src/**/*.{ts,tsx}"],
    rules: {
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
    },
  },
);
