+++
key = "sisoc-base"
title = "SISOC base IA"
summary = "Resumen operativo del repo para arrancar tareas IA con menos lecturas y sin perder boundaries."
paths = ["AGENTS.md", "CLAUDE.md", "docs/indice.md", "docs/ia", "docs/operacion/codex_desktop.md", "src/scripts/ai", ".agents/skills", ".codex/environments/environment.toml"]
default = true
confidence = "alta"
validated_commit = "f4af8d293"
validated_at = "2026-10-20"
+++

# SISOC base IA

## Estado
- Revalidada manualmente contra `AGENTS.md`, `CLAUDE.md`, `docs/indice.md`, guias IA, skills y helpers de `src/scripts/ai/` (#2645).
- Pensada como fast-path para arrancar antes de abrir modulos de dominio.

## Proposito
- Partir siempre de `development` actualizado.
- La lectura inicial es minima y guiada por evidencia (`AGENTS.md`, "Contexto minimo").
- `docs/` es fuente de verdad operativa y cualquier decision reusable se registra en `docs/registro/`.

## Entry points y archivos clave
- `AGENTS.md`: fuente de verdad para agentes; `CLAUDE.md` y `.codex/rules.md` solo agregan lo especifico de cada herramienta.
- `docs/ia/CONTEXT_HYGIENE.md`: que guia leer segun la tarea y cuando ampliar.
- `docs/ia/AGENT_REPO_MAP.md`: mapa para ubicar codigo; no se lee entero al inicio.
- `.agents/skills/`: skills del repo (`cambio-guiado`, `registro-cambios`, `verticales-checklist`, `migracion-app-label`, UI); `.claude/skills/` es copia generada.
- `AGENTS.md` ("Responsabilidades del agente"): quien pide puede no saber programar; el agente responde por la calidad. CI: `quality_gate` (tests + 80% de cobertura del diff, label `excepcion-calidad`) y `zonas_sensibles` (label `requiere-revision-tecnica`).
- `src/scripts/ai/preflight.sh`: resumen operativo corto por task kind.
- `src/scripts/ai/context_memory.py`: resuelve memoria reusable y detecta si quedo vieja.

## Patrones y contratos utiles
- Codigo en `src/backends/` (kernel, `sisoc_core`, un directorio por vertical) y `src/frontends/`; imports Django sin prefijo `src.` (`import core`).
- Kernel no importa core/verticales; un servicio no importa otro.
- La logica de negocio vive preferentemente en `services/`; views nuevas class-based.
- Toda funcionalidad nueva incluye tests; bugfix con regresion cuando sea viable.
- Coexisten Django views y DRF; no asumir un unico boundary.
- Hay logging custom en `src/backends/config/settings.py` y `src/backends/kernel/core/utils.py`.
- Celery solo para PAS; el resto usa hilos o workers propios.

## Como validar rapido
- `bash src/scripts/ai/preflight.sh general`
- `python src/scripts/ai/context_memory.py preflight`
- `python src/scripts/ci/check_docs_paths.py --existencia <docs.md>`

## Cuando invalidar esta memoria
- Si cambian `AGENTS.md`, `CLAUDE.md`, `docs/ia/`, las skills, `docs/operacion/codex_desktop.md` o `src/scripts/ai/`.
- Si cambia el tooling obligatorio o el flujo de bootstrap.
