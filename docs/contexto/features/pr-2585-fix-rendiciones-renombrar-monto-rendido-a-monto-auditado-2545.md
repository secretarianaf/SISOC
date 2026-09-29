# Contexto de feature PR #2585 - fix(rendiciones): renombrar Monto rendido a Monto auditado (#2545)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2585
- Base: `development`
- Rama origen: `RCuentasTk_2545`
- Autor: `MariaNavarro90`

## Contexto funcional

- Rendición de cuentas mensual. Nombre del monto que se registra al cerrar la etapa Auditoría.

## Arquitectura tocada

- Se modifican templates, con posible impacto visual o de composición UI.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: Cambio de texto (UI)
- Área principal declarada: Rendición de cuentas mensual / Organizaciones
- Impacto usuario declarado: Cambia el nombre visible del campo. No cambian datos, validaciones ni la PWA.
- Riesgos / rollback: Riesgo mínimo, solo cambian textos. El rollback es revertir la PR, sin migraciones.

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: organizaciones/templates/organizacion_rendicion_detail.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2585.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `docs/contexto/features/pr-2585-fix-rendiciones-renombrar-monto-rendido-a-monto-auditado-2545.md`
- `docs/registro/cambios/2026-09-28-issue-2545-monto-auditado.md`
- `docs/registro/prs/PR-2585.md`
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
