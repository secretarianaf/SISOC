# Contexto de feature PR #2601 - feat(usuarios): secciones del ABM habilitadas por permiso

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2601
- Base: `main`
- Rama origen: `feat/usuarios-secciones-por-permiso`
- Autor: `Mkdir-arg`

## Contexto funcional

- ABM de usuarios multi-programa.

## Arquitectura tocada

- Se modifican templates, con posible impacto visual o de composición UI.
- Existen cambios de persistencia o migraciones que requieren revisión de datos.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: feature + seguridad (permisos).
- Área principal declarada: users.
- Impacto usuario declarado: los coordinadores y administradores de DataCalle dejan de ver las secciones de Comedores y de administración; los gestores CDI/SIMEPI dejan de ver Territorial y DataCalle. El resto de los perfiles no cambia.
- Riesgos / rollback: si a un perfil le falta una sección, se le agrega el permiso role_usuarios_seccion_* a su grupo. Rollback: revertir el PR y migrar users a 0054 (la reversa borra los permisos).

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: static/custom/js/user_mobile_access.js, tests/js/user_mobile_access.test.js, users/templates/user/user_form.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2601.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `AGENT_REPO_MAP.md`
- `CHANGELOG.md`
- `core/constants.py`
- `docs/contexto/features/pr-2601-feat-usuarios-secciones-del-abm-habilitadas-por-permiso.md`
- `docs/registro/decisiones/2026-09-29-usuarios-secciones-por-permiso.md`
- `docs/registro/prs/PR-2601.md`
- `docs/registro/releases/pending/2026-09-29-pr-2601.md`
- `static/custom/js/user_mobile_access.js`
- `tests/js/user_mobile_access.test.js`
- `tests/test_users_regressions.py`
- `tests/test_users_secciones_por_permiso.py`
- `users/bootstrap/groups_seed.py`
- `users/forms.py`
- `users/migrations/0055_usuarios_secciones_por_permiso.py`
- `users/secciones_usuario.py`
- `users/templates/user/user_form.html`
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
