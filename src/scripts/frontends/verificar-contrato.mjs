/**
 * Verifica que los tipos TS versionados coincidan con `openapi.yaml`.
 *
 * `frontend_v2.md` (seccion 7) pide que CI falle si los tipos no coinciden con
 * el schema. La otra mitad del chequeo — que el schema versionado coincida con
 * el que genera el back — necesita Django, asi que vive en el workflow.
 *
 * Regenera los tipos en un archivo temporal y los compara con el commiteado.
 * No toca `packages/api/src/openapi.d.ts`.
 *
 *   node src/scripts/frontends/verificar-contrato.mjs
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = resolve(fileURLToPath(new URL(".", import.meta.url)), "../../frontends");
const contratos = [["openapi.celiaquia.yaml", "openapi.d.ts"], ["openapi.inet.yaml", "inet.generated.ts"]];

const temporal = mkdtempSync(join(tmpdir(), "sisoc-contrato-"));
const generado = join(temporal, "openapi.d.ts");

try {
  for (const [schemaName, typeName] of contratos) {
    const schema = join(raiz, "packages/api", schemaName);
    const versionado = join(raiz, "packages/api/src", typeName);
    execFileSync(
      process.execPath,
      [join(raiz, "node_modules/openapi-typescript/bin/cli.js"), schema, "-o", generado],
      { cwd: raiz, stdio: "pipe" },
    );

    const esperado = readFileSync(generado, "utf8");
    const actual = readFileSync(versionado, "utf8");

    if (esperado.replace(/\r\n/g, "\n") !== actual.replace(/\r\n/g, "\n")) {
      console.error(
        [
          `Los tipos versionados no coinciden con ${schemaName}.`,
          "",
          "Regeneralos y commiteá el resultado:",
          `  npm run ${schemaName.includes("inet") ? "inet:types" : "api:types"} --prefix src/frontends`,
        ].join("\n"),
      );
      process.exit(1);
    }

    console.log(`Contrato OK: ${schemaName}.`);
  }
} finally {
  rmSync(temporal, { recursive: true, force: true });
}
