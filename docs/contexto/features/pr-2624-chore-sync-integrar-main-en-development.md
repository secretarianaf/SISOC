# Contexto de feature PR #2624 - chore(sync): integrar main en development

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2624
- Base: `development`
- Rama origen: `automation/promote-homologacion-to-development`
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
- Archivos visuales relevantes: datacalle/templates/datacalle/encuesta_detail.html, datacalle/templates/datacalle/relevamiento_detail.html, kernel/users/templates/user/user_form.html, relevamientos/templates/acta_complementaria_detail.html, relevamientos/templates/primer_seguimiento_detail.html, relevamientos/templates/relevamiento_detail.html, relevamientos/templates/relevamiento_list.html, relevamientos/templates/seguimiento_pnud_detail.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2624.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `AGENT_REPO_MAP.md`
- `CHANGELOG.md`
- `comedores/api_views_territorial.py`
- `comedores/api_views_territorial_actas.py`
- `comedores/tests.py`
- `comedores/views/relevamientos.py`
- `datacalle/instrumento/README.md`
- `datacalle/instrumento/catalogos.json`
- `datacalle/instrumento/cuestionario.json`
- `datacalle/instrumento/diccionario-respuestas.json`
- `datacalle/models.py`
- `datacalle/services/__init__.py`
- `datacalle/services/encuestas.py`
- `datacalle/services/instrumento.py`
- `datacalle/templates/datacalle/encuesta_detail.html`
- `datacalle/templates/datacalle/relevamiento_detail.html`
- `datacalle/views.py`
- `docker-compose.deploy.yml`
- `docker-compose.yml`
- `docs/contexto/features/pr-2596-fix-acompanamiento-qa-28-9-popup-por-programa-acta-complementaria-bloqueo-de-re-revision-y-validacion-del-acta-h1-h5-h12-h16.md`
- ... y 87 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
