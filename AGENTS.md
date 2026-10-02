# AGENTS.md

Guia principal para IAs que trabajen en SISOC. Mantener este archivo como mapa breve; los detalles viven en `docs/`.

## Enfoque

- Trabajar con criterio senior en lo que toque hacer: implementacion, analisis, debugging, review, documentacion o descubrimiento.
- `docs/` es la fuente de verdad operativa: specs, ADRs, guias tecnicas y registros.
- Preferir soluciones simples, correctas, mantenibles y alineadas con los patrones reales del repo.
- Evitar sobreingenieria, refactors amplios, churn cosmetico y dependencias nuevas salvo necesidad clara.
- Si falta contexto critico, explicitar supuesto, impacto y seguir con la opcion mas segura.

## Contexto minimo

No cargar contexto amplio por defecto. Leer:

1. `AGENTS.md`
2. `docs/indice.md`
3. memoria aplicable en `docs/contexto/memoria/` o `.codex/cache/context-memory/`
4. archivo objetivo
5. tests del modulo o flujo afectado
6. una sola guia de `docs/ia/` segun la tarea

Para crear un modulo de dominio nuevo, agregar una dependencia interdominio o
preparar una extraccion, leer antes de disenar
`docs/ia/MODULAR_BOUNDARIES.md`.

Usar `docs/ia/CONTEXT_HYGIENE.md` para decidir si hace falta ampliar. Abrir mas docs, callers o settings solo con evidencia concreta.

## Implementacion

- Reutilizar patrones existentes; no inventar modelos, endpoints, permisos o schemas sin evidencia en el repo o pedido explicito.
- No mezclar feature, refactor amplio y formateo masivo.
- Mantener compatibilidad hacia atras salvo pedido explicito.
- Mejoras cercanas: proponerlas si ayudan, pero no implementarlas fuera de alcance sin aprobacion.
- Commits generados por IA: en espanol con el patron `<type>(<scope>): <subject>` (ver `docs/ia/CONTRIBUTING_AI.md`).
- La logica de negocio vive preferentemente en `services/`.
- Coexisten Django views y DRF.
- Hay logging custom en `src/backends/config/settings.py` y `src/backends/kernel/core/utils.py`.
- El codigo vive en `src/backends/` (`config`, `kernel` y un directorio por vertical) y `src/frontends/`. Ver el mapa de carpetas en `README.md`.

## Herramientas para agentes

- `scripts/ai/codex_task.ps1 <slug>`: crea branch, worktree y bootstrap desde `origin/development`.
- `scripts/ai/codex_run.ps1 validate`: validacion de cierre cuando aplique; para Python modificado, sumar `scripts/ai/codex_run.ps1 pylint <archivo.py>`.
- `scripts/ai/preflight.sh <tipo> [path]`: resumen corto del contexto.
- `python scripts/ai/context_memory.py preflight --target <path>`: resuelve memoria reutilizable y detecta si quedo vieja.
- Skills del repo: la fuente esta en `.agents/skills/` y `.claude/skills/` es una copia generada (ver `docs/ia/SKILLS.md`).

## Documentacion

Registrar en `docs/registro/` cambios funcionales visibles, decisiones de arquitectura o diseno, temas de seguridad o permisos y trade-offs importantes. Si el cambio es trivial y no necesita registro, decirlo en la entrega.
- Actualizar `docs/ia/AGENT_REPO_MAP.md` en cualquier cambio que altere de forma relevante la estructura del repo, sus hotspots de navegacion, comandos operativos, validaciones, modulos, flujos, puntos de entrada o advertencias utiles para futuros agentes y desarrolladores.

## Validacion

Tooling real del repo:
- Python: `black`
- Lint Python: `pylint` + `pylint_django`
- Templates: `djlint`
- Tests: `pytest`, `pytest-django`, `pytest-xdist`

Si el cambio modifica comportamiento, agregar o actualizar tests cercanos cuando aporte cobertura real.

## Guias

- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/CONTRIBUTING_AI.md`
- `docs/ia/STYLE_GUIDE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/MODULAR_BOUNDARIES.md`
- `docs/ia/TESTING.md`
- `docs/ia/SECURITY_AI.md`
- `docs/ia/ERRORS_LOGGING.md`
- `docs/registro/README.md`
