# Contexto de feature PR #2584 - fix(territorial): errores HTTP de la API territorial detectados por la auditoría de la app

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2584
- Base: `main`
- Rama origen: `fix/territorial-errores-http`
- Autor: `Mkdir-arg`

## Contexto funcional

- No informado explícitamente; inferir desde el título del PR y el diff.

## Arquitectura tocada

- Hay cambios en capa API/DRF y conviene revisar contratos de request/response.
- Hay cambios en vistas web y puede existir impacto en permisos o renderizado.
- Existen cambios de persistencia o migraciones que requieren revisión de datos.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: No informado
- Área principal declarada: No informada
- Impacto usuario declarado: No informado
- Riesgos / rollback: No informado

## Design system y UI

- Sin cambios visibles de UI o design system detectados en el diff.

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2584.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `CHANGELOG.md`
- `comedores/api_views_territorial.py`
- `comedores/api_views_territorial_adjuntos.py`
- `comedores/api_views_territorial_validaciones.py`
- `comedores/migrations/0062_imagencomedor_subido_por.py`
- `comedores/models.py`
- `config/api_errors.py`
- `config/settings.py`
- `config/urls.py`
- `config/views.py`
- `docs/contexto/features/pr-2584-fix-territorial-errores-http-de-la-api-territorial-detectados-por-la-auditoria-de-la-app.md`
- `docs/registro/prs/PR-2584.md`
- `docs/registro/releases/pending/2026-09-30-pr-2584.md`
- `relevamientos/serializer.py`
- `relevamientos/service.py`
- `relevamientos/views/api_views.py`
- `tests/test_territorial_api.py`
- `tests/test_territorial_errores_http.py`
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
