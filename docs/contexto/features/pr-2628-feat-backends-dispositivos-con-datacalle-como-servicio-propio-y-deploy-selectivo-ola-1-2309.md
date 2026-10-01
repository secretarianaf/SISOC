# Contexto de feature PR #2628 - feat(backends): Dispositivos (con Datacalle) como servicio propio y deploy selectivo (Ola 1 #2309)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2628
- Base: `development`
- Rama origen: `feat/2309-backend-dispositivos`
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
- Archivos visuales relevantes: backends/dispositivos/datacalle/templates/datacalle/encuesta_detail.html, backends/dispositivos/datacalle/templates/datacalle/relevamiento_confirm_delete.html, backends/dispositivos/datacalle/templates/datacalle/relevamiento_detail.html, backends/dispositivos/datacalle/templates/datacalle/relevamiento_form.html, backends/dispositivos/datacalle/templates/datacalle/relevamiento_list.html, backends/dispositivos/dispositivos/templates/dispositivos_confirm_delete.html, backends/dispositivos/dispositivos/templates/dispositivos_detail.html, backends/dispositivos/dispositivos/templates/dispositivos_form.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2628.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `.github/workflows/architecture.yml`
- `.github/workflows/lint.yml`
- `.github/workflows/tests.yml`
- `.importlinter`
- `.pylintrc`
- `backends/dispositivos/datacalle/__init__.py`
- `backends/dispositivos/datacalle/api_permissions.py`
- `backends/dispositivos/datacalle/api_serializers.py`
- `backends/dispositivos/datacalle/api_urls.py`
- `backends/dispositivos/datacalle/api_views.py`
- `backends/dispositivos/datacalle/apps.py`
- `backends/dispositivos/datacalle/forms.py`
- `backends/dispositivos/datacalle/instrumento/README.md`
- `backends/dispositivos/datacalle/instrumento/catalogos.json`
- `backends/dispositivos/datacalle/instrumento/cuestionario.json`
- `backends/dispositivos/datacalle/instrumento/diccionario-respuestas.json`
- `backends/dispositivos/datacalle/migrations/0001_initial.py`
- `backends/dispositivos/datacalle/migrations/0002_relevamiento_localidades.py`
- `backends/dispositivos/datacalle/migrations/0003_encuesta.py`
- `backends/dispositivos/datacalle/migrations/0004_encuesta_datacalle_e_relevam_c0184c_idx_and_more.py`
- ... y 99 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
