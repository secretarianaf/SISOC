# Contexto de feature PR #2586 - chore(sync): integrar main en homologacion

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2586
- Base: `homologacion`
- Rama origen: `sync/main-a-homologacion-20260928`
- Autor: `dsocial118`

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
- Archivos visuales relevantes: .github/scripts/sync_main_downstream.js, .github/scripts/sync_main_downstream.test.js, comedores/templates/comedor/comedor_detail.html, datacalle/templates/datacalle/encuesta_detail.html, datacalle/templates/datacalle/relevamiento_detail.html, datacalle/templates/datacalle/relevamiento_form.html, datacalle/templates/datacalle/relevamiento_list.html, relevamientos/templates/acta_complementaria_detail.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2586.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `.github/scripts/sync_main_downstream.js`
- `.github/scripts/sync_main_downstream.test.js`
- `.github/workflows/deploy.yml`
- `.github/workflows/sync-main-downstream.yml`
- `AGENT_REPO_MAP.md`
- `CHANGELOG.md`
- `audittrail/constants.py`
- `comedores/api_views_territorial.py`
- `comedores/api_views_territorial_adjuntos.py`
- `comedores/api_views_territorial_pnud.py`
- `comedores/api_views_territorial_validaciones.py`
- `comedores/migrations/0062_imagencomedor_subido_por.py`
- `comedores/migrations/0063_merge_subido_por_responsable_tarjeta.py`
- `comedores/models.py`
- `comedores/templates/comedor/comedor_detail.html`
- `config/api_errors.py`
- `config/settings.py`
- `config/urls.py`
- `config/views.py`
- `datacalle/api_permissions.py`
- ... y 94 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
