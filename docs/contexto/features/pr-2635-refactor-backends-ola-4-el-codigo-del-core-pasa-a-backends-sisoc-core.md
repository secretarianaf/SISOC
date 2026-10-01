# Contexto de feature PR #2635 - refactor(backends): ola 4, el código del core pasa a backends/sisoc_core

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2635
- Base: `development`
- Rama origen: `feat/2309-backends-ola4`
- Autor: `juanikitro`

## Contexto funcional

- No informado explícitamente; inferir desde el título del PR y el diff.

## Arquitectura tocada

- El PR toca lógica en `services/`, por lo que impacta reglas de negocio u orquestación.
- Hay cambios en capa API/DRF y conviene revisar contratos de request/response.
- Hay cambios en vistas web y puede existir impacto en permisos o renderizado.
- Se modifican templates, con posible impacto visual o de composición UI.
- Existen cambios de persistencia o migraciones que requieren revisión de datos.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: No informado
- Área principal declarada: No informada
- Impacto usuario declarado: No informado
- Riesgos / rollback: No informado

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: backends/sisoc_core/acompanamientos/templates/acompanamientos/partials/comedor_rows.html, backends/sisoc_core/acompanamientos/templates/acompañamiento_detail.html, backends/sisoc_core/acompanamientos/templates/hitos/hito_row.html, backends/sisoc_core/acompanamientos/templates/lista_comedores.html, backends/sisoc_core/admisiones/templates/admisiones/admisiones_detalle.html, backends/sisoc_core/admisiones/templates/admisiones/admisiones_legales_detalle.html, backends/sisoc_core/admisiones/templates/admisiones/admisiones_legales_list.html, backends/sisoc_core/admisiones/templates/admisiones/admisiones_tecnicos_form.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2635.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `.gitleaksignore`
- `.pylintrc`
- `AGENT_REPO_MAP.md`
- `CLAUDE.md`
- `backends/sisoc_core/acompanamientos/acompanamiento_service.py`
- `backends/sisoc_core/acompanamientos/admin.py`
- `backends/sisoc_core/acompanamientos/apps.py`
- `backends/sisoc_core/acompanamientos/favorite_filters.py`
- `backends/sisoc_core/acompanamientos/fixtures/hitos.json`
- `backends/sisoc_core/acompanamientos/forms.py`
- `backends/sisoc_core/acompanamientos/migrations/0001_squashed_0008.py`
- `backends/sisoc_core/acompanamientos/migrations/__init__.py`
- `backends/sisoc_core/acompanamientos/models/acompanamiento.py`
- `backends/sisoc_core/acompanamientos/models/hitos.py`
- `backends/sisoc_core/acompanamientos/services/__init__.py`
- `backends/sisoc_core/acompanamientos/services/filter_config.py`
- `backends/sisoc_core/acompanamientos/templates/acompanamientos/partials/comedor_rows.html`
- `backends/sisoc_core/acompanamientos/templates/acompañamiento_detail.html`
- `backends/sisoc_core/acompanamientos/templates/hitos/hito_row.html`
- `backends/sisoc_core/acompanamientos/templates/lista_comedores.html`
- ... y 836 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
