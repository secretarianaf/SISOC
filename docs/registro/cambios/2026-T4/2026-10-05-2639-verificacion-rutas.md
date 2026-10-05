# #2639 — Verificación de movimientos y descubrimiento de configuraciones

## Resultado y corrección

La verificación del 2026-10-05 encontró pérdidas de descubrimiento automático
al mover los archivos de entrada de las herramientas a `config/`:

- ESLint sin `--config` devolvía `Could not find config file`.
- Playwright sin `--config` recogía pruebas de Vitest y devolvía errores de
  imports y `No tests found`, en lugar de encontrar los tres escenarios E2E.

Se restituyeron `eslint.config.js`, `vitest.config.ts` y
`playwright.config.ts` a `src/frontends/`, junto con sus comandos habituales.
No se agregaron wrappers. `config/` conserva las opciones base de TypeScript,
referenciadas explícitamente por los tres `tsconfig.json`. Docker y los scripts
mantienen las ubicaciones nuevas documentadas en la decisión del 2026-10-05.

Archivos principales: `src/frontends/package.json`, las tres configuraciones,
`README.md`, `docs/ia/AGENT_REPO_MAP.md`, la guía de verticales y la decisión.

## Evidencia ejecutada

| Uso a conservar | Comprobación | Resultado |
|---|---|---|
| Descubrimiento ESLint | API `ESLint.calculateConfigForFile` sin override sobre `apps/vpsl/src/App.tsx`; se comprobó la regla React Hooks | OK |
| Lint y resolución TypeScript | `npm run lint`, `npm run typecheck` | OK; lint tiene dos advertencias en VPSL, sin errores |
| Proyectos/configuraciones de pruebas | `npm run test`, sin `--config` | 16 archivos, 88 pruebas pasaron |
| Playwright, servidor preview y directorio E2E | `PLAYWRIGHT_CHANNEL=chrome npm run test:e2e`, en Windows con Chrome instalado | 3 pasaron; API mockeada, no backend real |
| Script de contrato movido | `npm run api:check` | OK en Windows y Linux; no cambió el contrato |
| Runtime usado por Docker | Imagen `dev`, Node 22.14, sin red: lint, typecheck, 88 tests, contrato y listado Playwright | OK; 3 E2E descubiertos |
| Builds y COPY/contexto | `docker build --build-arg APP=<vpsl o celiaquia> --target prod -f docker/frontends/Dockerfile .` | Ambas imágenes construidas con el árbol final |
| Nginx y ubicación del dist | Contenedores temporales, sin red externa ni puertos publicados: `nginx -t` y GET por loopback | HTTP 200 en `/v2/vpsl/`, su ruta de formulario, `/v2/celiaquia/` y `/v2/celiaquia/expedientes/` |
| Compose dev/deploy | `docker compose config --format json`, inspección en memoria de contexto, Dockerfile y montajes frontend | OK; no se imprimieron variables del entorno |
| Scripts de operación/CI y transición de rutas | Pytest focalizado, sin conftest/Django/DB, con ejecutables falsos | 86 pasaron; incluye cuatro casos de avance/rollback entre estructuras |
| Scripts GitHub movidos | `node --test src/scripts/github/release_orchestrator.test.js src/scripts/github/sync_main_downstream.test.js` | 10 pasaron |
| Sintaxis y cálculo de raíz | `bash -n` sobre scripts `.sh`; parser PowerShell y `Get-CodexRepoRoot`; AST de Python | 32 Bash, helpers PowerShell y Python: OK |
| Referencias vigentes | `python src/scripts/ci/check_docs_paths.py` y búsqueda de rutas antiguas | 80 documentos, 0 referencias obsoletas; solo referencias intencionales a PWA externas y rollback legacy |
| Skills y diff | `python src/scripts/ai/sync_skills.py --check`, `git diff --check` | OK; lockfile sin cambios |

Las comprobaciones de Docker usaron tags locales `sisoc-issue2639/*:verify` y
contenedores con `--rm`; no se levantó el stack compartido ni se ejecutó deploy.

## Límites y reproducción

No se ejecutaron la suite Django completa, el grafo de migraciones ni un deploy
a QA: no son evidencia cubierta por estos tests unitarios y mocks. No se
ejecutaron scripts sobre datos reales. La prueba de grafo quedó deseleccionada
porque requiere configurar Django. El lint Python con Black no pudo correr:
el Python local devuelve `No module named black`. Para repetirlo con el runtime
del proyecto, usar `src/scripts/ai/codex_run.ps1 black-check <archivo.py>`.

La corrección preserva los archivos de entrada de descubrimiento automático;
las pruebas demuestran los consumidores ejecutados, no todos los comandos
externos o cron instalados fuera del repositorio. Esos comandos necesitan
actualizar `scripts/` a `src/scripts/` al incorporar el cambio.

Se usó `systematic-debugging` para reproducir las pérdidas antes de corregirlas
y diferenciar problemas del entorno (Chromium ausente) de rutas rotas. La skill
`code-review` se consultó, pero no se aplicó su flujo de comparación de commits
porque el alcance eran movimientos locales todavía sin commit. La skill
`playwright` se consultó; se conservaron las pruebas existentes del repo en
lugar de introducir otra CLI o nuevos escenarios.

Los scripts temporales de validación se retiraron. La revisión automática
rechazó la limpieza recursiva con `blocked by policy`, sin un motivo más
específico; quedaron carpetas de pytest en `tmp/`. Las imágenes locales de
verificación se conservan con los tags indicados. No se hizo commit ni push.
