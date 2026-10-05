# 2026-10-05 — Configuración de frontends y scripts dentro de src

## Contexto y alcance

Continuación de #2639 y de `2026-10-02-estructura-src-backends.md`.
El responsable pidió reducir la confusión entre los archivos de la raíz y
los de `src/frontends/`, delegó al agente la organización y definió que los
scripts también debían vivir dentro de `src/`.

## Decisión

Organización elegida por el agente dentro del alcance solicitado:

- `src/backends/`: código Django, con configuración del proyecto en `config/`.
- `src/frontends/`: un workspace npm del mismo repositorio, con `apps/`,
  `packages/`, `e2e/` y opciones base compartidas de TypeScript en `config/`.
- `package.json`, `package-lock.json`, `.npmrc`, `.nvmrc` y `tsconfig.json`
  junto con `eslint.config.js`, `vitest.config.ts` y `playwright.config.ts`
  permanecen en el workspace. Conservan la detección habitual de herramientas,
  editores y CI; no representan un repositorio Git independiente.
- Los `package.json`, `tsconfig.json` y `vite.config.ts` de cada app siguen
  junto a esa app porque describen su build, rutas y pruebas particulares.
- Un solo `.gitignore`, en la raíz, concentra los ignorados del repositorio.
- `docker/frontends/` concentra Dockerfile y plantilla de Nginx. Su
  `Dockerfile.dockerignore` limita el contexto de build al frontend, sus scripts
  y la plantilla; quedan excluidos dependencias, resultados, cachés y `.env`.
- `src/scripts/` concentra scripts de operación, infraestructura, CI,
  arquitectura, agentes, frontend y GitHub. Los fragmentos JavaScript de
  templates Django mantienen su ubicación con el código que los consume.

La raíz conserva entradas y configuración global. No se trasladan allí las
herramientas exclusivas de Node ni se agregan wrappers para las rutas anteriores.

## Alternativas y consecuencias

Centralizar también los manifiestos npm en la raíz facilitaría un único punto
de entrada, pero mezclaría herramientas Python y Node y aumentaría los archivos
sueltos. Mover todos los archivos a subcarpetas obligaría a configurar rutas
especiales para herramientas y editores. Se elige mantener los archivos de
descubrimiento en su ubicación convencional. La verificación mostró que mover
ESLint a `config/` rompe su detección automática (incluidos editores), y mover
Playwright hace que su CLI sin flags recoja pruebas de Vitest en lugar de los
E2E. Se mantienen también las entradas convencionales de Vitest. Los comandos
habituales siguen funcionando sin argumentos especiales.

Se actualizan las referencias vigentes, los cálculos de raíz de los scripts,
pytest y CI. Los registros históricos conservan sus rutas originales. Los
scripts de checkouts PWA externos conservan sus rutas propias. La clasificación
de deploy sigue excluyendo los scripts de GitHub y seleccionando todos los
fronts cuando cambia su imagen o sus herramientas compartidas.

El wrapper de deploy conserva la revisión previa y hace fast-forward al SHA
validado antes de buscar los scripts nuevos; el refresh recibe `--skip-pull`
porque el checkout ya fue actualizado. Para rollback resuelve los scripts y
healthchecks del árbol restaurado, que puede conservar la ubicación anterior.
Las pruebas usan ejecutables falsos y archivos temporales, sin ejecutar Git o
Docker reales. También se corrige la referencia pendiente al registro de
backends en ese wrapper (`src/backends/config/backends.json`).

El chequeo de contrato del frontend invoca con Node el CLI local de la
dependencia ya fijada, en lugar de `npx`, que no se ejecutaba con `execFileSync`
en Windows. No descarga herramientas durante el chequeo.

El cambio requiere coordinación con ramas abiertas y actualización de comandos
locales o cron externos que apunten a `scripts/`. No se modifican servidores,
datos, permisos ni dependencias. No se ejecuta un deploy como parte de este
ordenamiento local; la suite de CI, build de imágenes y aceptación en QA siguen
siendo evidencia necesaria antes de promoción.

Revisar esta decisión si las herramientas exigen nuevos archivos de entrada
o si los frontends pasan a repositorios independientes.
