# Contexto de feature PR #2585 - fix(rendiciones): renombrar Monto rendido a Monto auditado (#2545)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2585
- Base: `development`
- Rama origen: `RCuentasTk_2545`
- Autor: `MariaNavarro90`

## Contexto funcional

- No informado explícitamente; inferir desde el título del PR y el diff.

## Arquitectura tocada

- Se modifican templates, con posible impacto visual o de composición UI.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: No informado
- Área principal declarada: No informada
- Impacto usuario declarado: No informado
- Riesgos / rollback: No informado

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: organizaciones/templates/organizacion_detail.html, organizaciones/templates/organizacion_rendicion_detail.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2585.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `docs/registro/cambios/2026-09-28-issue-2545-monto-auditado.md`
- `organizaciones/templates/organizacion_detail.html`
- `organizaciones/templates/organizacion_rendicion_detail.html`
- `organizaciones/tests.py`
- `rendicioncuentasmensual/forms.py`
- `tests/test_rendicioncuentasmensual_acta_auditoria.py`
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
