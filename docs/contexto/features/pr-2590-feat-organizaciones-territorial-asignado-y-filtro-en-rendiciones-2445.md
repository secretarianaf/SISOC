# Contexto de feature PR #2590 - feat(organizaciones): territorial asignado y filtro en rendiciones (#2445)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2590
- Base: `development`
- Rama origen: `RCuentasTk_2445`
- Autor: `MariaNavarro90`

## Contexto funcional

- Asignar territoriales PNUD a las organizaciones de Abordaje Comunitario y poder filtrar las rendiciones de cuentas por territorial.

## Arquitectura tocada

- Hay cambios en vistas web y puede existir impacto en permisos o renderizado.
- Se modifican templates, con posible impacto visual o de composición UI.
- Existen cambios de persistencia o migraciones que requieren revisión de datos.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: Feature
- Área principal declarada: Organizaciones / Rendición de cuentas mensual
- Impacto usuario declarado: Los equipos pueden asignar uno o más territoriales PNUD a cada organización. En Rendiciones pueden filtrar y ver las rendiciones por territorial.
- Riesgos / rollback: Hasta que el #2444 cargue Profile.rol en el ambiente, el selector y el filtro no ofrecen opciones. No hay error, solo listas vacías. La migración es aditiva, solo crea la tabla intermedia. Rollback: revertir la PR y ejecutar migrate organizaciones 0021, que elimina la tabla y con ella las asignaciones que se hayan cargado.

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: organizaciones/templates/organizacion_detail.html, organizaciones/templates/organizacion_form.html, rendicioncuentasmensual/templates/components/rendicion_global_list_cell.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2590.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `docs/contexto/features/pr-2590-feat-organizaciones-territorial-asignado-y-filtro-en-rendiciones-2445.md`
- `docs/registro/cambios/2026-09-28-issue-2445-territorial-asignado-abordaje.md`
- `docs/registro/prs/PR-2590.md`
- `organizaciones/forms.py`
- `organizaciones/migrations/0022_issue_2445_territoriales_abordaje_comunitario.py`
- `organizaciones/models.py`
- `organizaciones/templates/organizacion_detail.html`
- `organizaciones/templates/organizacion_form.html`
- `organizaciones/views.py`
- `rendicioncuentasmensual/favorite_filters.py`
- `rendicioncuentasmensual/filter_config.py`
- `rendicioncuentasmensual/services.py`
- `rendicioncuentasmensual/templates/components/rendicion_global_list_cell.html`
- `rendicioncuentasmensual/views.py`
- `tests/test_issue_2445_territorial_abordaje_organizacion.py`
- `tests/test_issue_2445_territorial_filtro_rendiciones.py`
- `tests/test_rendicioncuentasmensual_views_unit.py`
- `users/services_territoriales.py`
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
