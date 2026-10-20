# AGENTS.md

Guia principal y fuente de verdad para IAs que trabajen en SISOC (Codex, Claude Code u otras). Mantener este archivo como mapa breve; los detalles viven en `docs/`. Cada regla vive en un solo lugar: las demas guias enlazan aca en vez de repetirla.

## Enfoque

- Trabajar con criterio senior en lo que toque hacer: implementacion, analisis, debugging, review, documentacion o descubrimiento.
- `docs/` es la fuente de verdad operativa: specs, ADRs, guias tecnicas y registros.
- Preferir soluciones simples, correctas, mantenibles y alineadas con los patrones reales del repo.
- Evitar sobreingenieria, refactors amplios, churn cosmetico y dependencias nuevas salvo necesidad clara.
- Si falta contexto critico, explicitar supuesto, impacto y seguir con la opcion mas segura.

## Antes de empezar

- Partir siempre de `development` actualizado (`git fetch origin` y rama nueva desde `origin/development`). No revertir cambios ajenos; si aparece conflicto con trabajo de otro, explicitarlo antes de seguir.

## Contexto minimo

No cargar contexto amplio por defecto. Leer:

1. `AGENTS.md`
2. `docs/indice.md`
3. memoria aplicable en `docs/contexto/memoria/` (o la cache local `.codex/cache/context-memory/`, ignorada por Git), si existe
4. archivo objetivo
5. tests del modulo o flujo afectado
6. una sola guia de `docs/ia/` segun la tarea (ver `docs/ia/CONTEXT_HYGIENE.md`)

`docs/ia/AGENT_REPO_MAP.md` se consulta para ubicar codigo, no se lee entero al inicio. Abrir mas docs, callers o settings solo con evidencia concreta.

## Implementacion

### Verticales independientes

Guia vigente y cuatro checklists: `docs/desarrollo/verticales_independientes.md`. La skill `verticales-checklist` la recorre paso a paso.

- Kernel no importa core/verticales; un servicio no importa otro, tampoco su `api.py`.
- Elegir dueño en `src/backends/` (kernel, `sisoc_core`, vertical o frontend); recursos y tests van junto a ese dueño.
- Usar contribuciones HTML, JSON o reenvio existentes para datos remotos, con permisos y fallback.
- Registrar prefijos en `src/backends/config/backends.json` y regenerar `src/backends/config/url_registry.json`.
- Resolver archivos por app o `__file__`, no por BASE_DIR + nombre de app.
- Cambio de app label: conservar tabla/content type con migraciones de estado (skill `migracion-app-label`).
- Comandos del grafo completo y collectstatic: migrador, no web de deploy.
- Revisar imports, runtime/imagen aislada, permisos, fallback y plan de deploy.

### Codigo

- El codigo vive en `src/backends/` (`config`, `kernel`, `sisoc_core` y un directorio por vertical) y `src/frontends/`. Ver el mapa de carpetas en `README.md`.
- Reutilizar patrones existentes; no inventar modelos, endpoints, permisos, settings o schemas sin evidencia en el repo o pedido explicito.
- La logica de negocio vive preferentemente en `services/` de la app; managers/querysets solo para reglas propias del acceso a datos. Views y templates no concentran reglas de dominio (ver `docs/ia/ARCHITECTURE.md`).
- Views nuevas: class-based views. Las function-based existentes se toleran y no se migran salvo pedido.
- Coexisten Django views y DRF (`api_views.py`, `api_serializers.py`).
- Hay logging custom en `src/backends/config/settings.py` y `src/backends/kernel/core/utils.py`.
- No mezclar feature, refactor amplio y formateo masivo.
- Mantener compatibilidad hacia atras salvo pedido explicito.
- Mejoras cercanas: proponerlas si ayudan, pero no implementarlas fuera de alcance sin aprobacion.
- Commits generados por IA: en espanol con el patron `<type>(<scope>): <subject>` (ver `docs/ia/CONTRIBUTING_AI.md`).

## Herramientas para agentes

- `src/scripts/ai/codex_task.ps1 <slug>`: crea branch, worktree y bootstrap desde `origin/development`.
- `src/scripts/ai/codex_run.ps1 validate`: validacion de cierre cuando aplique; para Python modificado, sumar `src/scripts/ai/codex_run.ps1 pylint <archivo.py>`.
- `src/scripts/ai/preflight.sh <tipo> [path]`: resumen corto del contexto.
- `python src/scripts/ai/context_memory.py preflight --target <path>`: resuelve memoria reutilizable y detecta si quedo vieja.
- `python src/scripts/ci/check_docs_paths.py --existencia <docs.md>`: rutas documentadas vigentes y existentes (CI lo corre sobre los Markdown del PR).
- Skills del repo: la fuente esta en `.agents/skills/` y `.claude/skills/` es una copia generada (ver `docs/ia/SKILLS.md`). Actuales: `registro-cambios`, `verticales-checklist`, `migracion-app-label`, `frontend-ui-ux`, `tema-verde-institucional`.

## Documentacion

- Registrar en `docs/registro/` cambios funcionales visibles, decisiones de arquitectura o diseno, temas de seguridad o permisos y trade-offs importantes (skill `registro-cambios`). Si el cambio es trivial y no necesita registro, decirlo en la entrega.
- Actualizar `docs/ia/AGENT_REPO_MAP.md` cuando cambie de forma relevante la estructura del repo, sus hotspots, comandos, validaciones, modulos, flujos o puntos de entrada. Es un mapa: el estado de cada PR o issue va en `docs/registro/`, no ahi.

## Validacion

Tooling real del repo (configuracion y comandos en `docs/ia/TESTING.md` y `docs/ia/STYLE_GUIDE.md`):
- Python: `black` (`pyproject.toml`)
- Lint Python: `pylint` + `pylint_django` (`.pylintrc`)
- Templates: `djlint` (`.djlintrc`)
- Tests: `pytest`, `pytest-django`, `pytest-xdist`

Tests:
- Toda funcionalidad nueva incluye tests; todo bugfix, un test de regresion cuando sea viable.
- Si no se agrega test, explicar por que en la entrega.

## Guias

- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/CONTRIBUTING_AI.md`
- `docs/ia/STYLE_GUIDE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/MODULAR_BOUNDARIES.md`
- `docs/ia/TESTING.md`
- `docs/ia/SECURITY_AI.md`
- `docs/ia/ERRORS_LOGGING.md`
- `docs/ia/SKILLS.md`
- `docs/ia/AGENT_REPO_MAP.md`
- `docs/registro/README.md`
