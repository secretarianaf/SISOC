# Contexto de feature PR #2591 - feat(users): cargar roles territoriales PNUD en Profile.rol (#2444)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2591
- Base: `development`
- Rama origen: `RCuentasTk_2444`
- Autor: `MariaNavarro90`

## Contexto funcional

- Registrar el rol TERRITORIAL PNUD / RESPONSABLE TERRITORIAL PNUD de los usuarios territoriales, necesario para asignarlos a organizaciones de Abordaje Comunitario (#2445).

## Arquitectura tocada

- Existen cambios de persistencia o migraciones que requieren revisión de datos.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: Datos (data migration)
- Área principal declarada: Usuarios
- Impacto usuario declarado: Sin cambios visibles por sí sola. Con la #2445, estos usuarios pasan a estar disponibles como territoriales asignables a organizaciones.
- Riesgos / rollback: Riesgo bajo: solo cambia un campo descriptivo que no otorga permisos. Usernames no encontrados: si la salida muestra alguno, hay que confirmar con el área si el usuario tiene otro username o todavía no fue creado. La migración no falla por eso. Rollback: la reversa no modifica datos. Para restaurar valores, usar el detalle de valor anterior de la salida del deploy, por eso conviene conservarla. Numeración: si otra rama agrega antes una users.0056, hay que crear una migración de merge (makemigrations --merge).

## Design system y UI

- Sin cambios visibles de UI o design system detectados en el diff.

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2591.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `docs/registro/cambios/2026-09-28-issue-2444-roles-territoriales-pnud.md`
- `tests/test_issue_2444_roles_territoriales_migration.py`
- `users/migrations/0056_issue_2444_roles_territoriales_pnud.py`
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
