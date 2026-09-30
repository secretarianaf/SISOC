# Contexto de feature PR #2610 - refactor(kernel): mover core, users, iam, ciudadanos y audittrail a kernel/ (Ola 0 #1931/#2251)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2610
- Base: `development`
- Rama origen: `refactor/1931-kernel-estructura`
- Autor: `juanikitro`

## Contexto funcional

- No informado explícitamente; inferir desde el título del PR y el diff.

## Arquitectura tocada

- El PR toca lógica en `services/`, por lo que impacta reglas de negocio u orquestación.
- Hay cambios en capa API/DRF y conviene revisar contratos de request/response.
- Hay cambios en vistas web y puede existir impacto en permisos o renderizado.
- Se modifican templates, con posible impacto visual o de composición UI.
- Existen cambios de persistencia o migraciones que requieren revisión de datos.
- El alcance incluye automatización o tooling de CI/CD.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: No informado
- Área principal declarada: No informada
- Impacto usuario declarado: No informado
- Riesgos / rollback: No informado

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: kernel/ciudadanos/templates/ciudadanos/ciudadano_confirm_delete.html, kernel/ciudadanos/templates/ciudadanos/ciudadano_detail.html, kernel/ciudadanos/templates/ciudadanos/ciudadano_form.html, kernel/ciudadanos/templates/ciudadanos/ciudadano_list.html, kernel/ciudadanos/templates/ciudadanos/cola_revision.html, kernel/ciudadanos/templates/ciudadanos/grupofamiliar_confirm_delete.html, kernel/ciudadanos/templates/ciudadanos/grupofamiliar_form.html, kernel/ciudadanos/templates/ciudadanos/importacion_masiva_form.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2610.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `.github/workflows/architecture.yml`
- `.github/workflows/lint.yml`
- `.importlinter`
- `.pylintrc`
- `AGENTS.md`
- `AGENT_REPO_MAP.md`
- `CLAUDE.md`
- `config/__init__.py`
- `docs/contexto/features/pr-2610-refactor-kernel-mover-core-users-iam-ciudadanos-y-audittrail-a-kernel-ola-0-1931-2251.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/ERRORS_LOGGING.md`
- `docs/ia/SECURITY_AI.md`
- `docs/registro/cambios/2026-09-30-kernel-estructura.md`
- `docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md`
- `docs/registro/prs/PR-2610.md`
- `kernel/audittrail/__init__.py`
- `kernel/audittrail/api.py`
- `kernel/audittrail/apps.py`
- `kernel/audittrail/constants.py`
- `kernel/audittrail/context.py`
- ... y 284 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
