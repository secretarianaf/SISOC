# Contexto de feature PR #2626 - refactor(users): kernel solo con identidad; gestión de usuarios a usuarios y accesos PWA a pwa (Ola 1a #2309)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2626
- Base: `development`
- Rama origen: `refactor/1931-kernel-sin-fks-dominio`
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
- Archivos visuales relevantes: usuarios/templates/group/group_form.html, usuarios/templates/group/group_list.html, usuarios/templates/registration/login.html, usuarios/templates/user/_mi_cuenta_campos.html, usuarios/templates/user/_mi_cuenta_submit_js.html, usuarios/templates/user/bulk_credentials_form.html, usuarios/templates/user/bulk_credentials_job_detail.html, usuarios/templates/user/confirmar_datos.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2626.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `.importlinter`
- `AGENT_REPO_MAP.md`
- `centrodeinfancia/models.py`
- `comedores/api_serializers.py`
- `comedores/api_views.py`
- `comedores/api_views_territorial.py`
- `comedores/management/commands/sincronizar_accesos_pwa_organizaciones.py`
- `comedores/pwa_capabilities.py`
- `comedores/pwa_user_import.py`
- `comedores/signals.py`
- `comedores/views_territorial.py`
- `config/settings.py`
- `config/urls.py`
- `docs/contexto/features/pr-2626-refactor-users-kernel-solo-con-identidad-gestion-de-usuarios-a-usuarios-y-accesos-pwa-a-pwa-ola-1a-2309.md`
- `docs/registro/cambios/2026-10-01-users-identidad-y-usuarios-core.md`
- `docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md`
- `docs/registro/prs/PR-2626.md`
- `kernel/core/views.py`
- `kernel/users/admin.py`
- `kernel/users/migrations/0058_accesos_pwa_a_pwa.py`
- ... y 105 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
