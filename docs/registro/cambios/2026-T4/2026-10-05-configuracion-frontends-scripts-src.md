# Scripts en src y organización del frontend (#2639)

Decisión: `docs/registro/decisiones/2026-10-05-configuracion-frontends-scripts-src.md`.
El alcance publicado incluye esta continuación de #2639 y la guía de #2638,
por instrucción explícita del responsable. Los commits separan scripts/CI,
frontend e imagen, y documentación/verificador.

## Cambio y compatibilidad

- Scripts de operación, agentes, CI, arquitectura y GitHub en `src/scripts/`;
  los consumidores y cálculos de raíz se actualizan, sin wrappers de rutas viejas.
- El frontend conserva ESLint, Vitest y Playwright en el workspace para que las
  herramientas los descubran. Las opciones base de TypeScript van en `config/`;
  Dockerfile/Nginx pasan a `docker/frontends/` y el script de contrato a
  `src/scripts/frontends/`. El contexto Docker se limita con Dockerfile.dockerignore.
- Deploy actualiza el checkout por fast-forward antes de resolver los scripts
  nuevos. Rollback resuelve scripts/healthchecks según la revisión restaurada,
  admitiendo la ubicación anterior. Se preserva el SHA previo para esa reversa.
- Selector: scripts de GitHub no despliegan; imagen y scripts compartidos de
  frontend seleccionan todos los fronts; scripts de CI no exceptuados y el
  conjunto completo de este cambio requieren deploy completo.
- Sin nuevas dependencias, cambios de schema, permisos, datos ni acciones sobre
  servidores. Los comandos/cron externos que usen scripts/ necesitan revisión.

## Evidencia ejecutada

- 86 pruebas focalizadas de scripts/CI/deploy simulado, 1 deselected (grafo de
  migraciones que requiere composición Django). Usan mocks/archivos temporales;
  no equivalen a probar Git/Docker/DB reales. Comando:
  `python -m pytest -c tmp/pytest_paths.ini --noconftest -p no:cacheprovider src/backends/kernel/tests/test_deploy_targets.py src/backends/kernel/tests/test_pr_lint_tools_unit.py src/backends/kernel/tests/test_pr_doc_automation_unit.py src/backends/kernel/tests/test_context_memory_unit.py src/backends/kernel/tests/test_sync_skills.py src/backends/kernel/tests/test_deploy_pwas.py src/backends/kernel/tests/test_pwa_nginx.py src/backends/kernel/tests/test_deploy_workflow.py src/backends/kernel/tests/test_deploy_script_paths.py -q -k 'not grafo_de_migraciones'`.
  Configuración temporal usada: `[pytest]`, `pythonpath = .. ../src`, `addopts =`.
  No se versiona tmp/; para repetir, usar la configuración oficial del entorno
  aislado preparado o materializar esa configuración temporal.
- `node --test src/scripts/github/release_orchestrator.test.js src/scripts/github/sync_main_downstream.test.js`:
  10 passed.
- Sintaxis Python de los scripts, encoding de los grupos staged y
  `git diff --check`: sin errores.
- `python src/scripts/ci/check_docs_paths.py`: 80 documentos, cero hallazgos
  en el alcance declarado; `python src/scripts/ai/sync_skills.py --check`: OK.
- `node src/scripts/frontends/verificar-contrato.mjs`: contrato OK, sin
  regenerar archivos versionados ni descargar herramientas.
- Descubrimiento de configuración ESLint y archivos Vitest: OK; Playwright
  `--list`: 3 tests en un archivo. No se ejecutaron esos tests de navegador.

## Pendiente antes de incorporar/promover

CI del HEAD publicado: lint oficial/imports, tests completos pertinentes,
migraciones y service_images. Construir/probar imágenes y transición de
deploy/rollback en QA autorizada, comprobar comandos/cron externos y aceptación
del flujo frontend y de la guía. El descubrimiento de configuración no prueba
el build ni el comportamiento del navegador. No se ejecuta deploy aquí.
