# `kernel/users` queda como identidad y permisos; gestión de usuarios en `usuarios`

Parte de las épicas #1931, #2251 y #2309. ADR:
`docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md` (puntos 9 y 13).

## Por qué

Los backends por vertical instalan el kernel. `users` declaraba modelos con
FKs a `comedores`, `organizaciones` y `duplas`, que son los accesos PWA. Por
eso ningún backend podía arrancar sin el cluster de Comedores.

## Qué cambió

- **Accesos PWA a `pwa`:** `AccesoComedorPWA`, `AccesoOrganizacionPWA`,
  `AuditAccesoComedorPWA` y `CoordinadorEquipoTecnicoPWA`, con sus admins.
  - Mantienen las tablas `users_*` (`Meta.db_table`) y los nombres de
    índices, constraints y tablas M2M.
  - Migraciones solo de estado: `pwa.0025_accesos_pwa_desde_users` y
    `users.0057_accesos_pwa_a_pwa`. No hay DDL ni copia de datos.
  - Los content types `users.*` de esos modelos pasan a `pwa`, así que los
    permisos de grupos y el historial de auditoría apuntan al mismo
    registro. Si ya existieran en ambas apps, la migración falla a propósito,
    para resolverlo a mano.
- **Lógica PWA:** `users.services_pwa` pasa a `pwa.services.accesos` y
  `users.pwa_comedores` a `pwa.services.capacidades_comedores`.
- **Nueva app `usuarios` (core):** pantallas, formularios, importación masiva,
  credenciales masivas, API de login de las PWAs (`/api/users/`) y los
  comandos `process_bulk_credentials_jobs` y `process_user_import_jobs`.
  Las URLs, los nombres de URL, los templates y los comandos de los workers
  no cambian.
- **Reset de contraseña PWA:** sale de `users.services_auth` y pasa a
  `usuarios.services_password_reset_pwa`.
- **`core.views`:** importa `historial` de forma diferida, porque el footer
  carga ese módulo en todos los servicios.
- **import-linter:** el kernel (`core`, `users`, `ciudadanos`) no puede
  importar `usuarios`.

## Sin cambios

Comportamiento funcional, URLs, permisos, datos y esquema de la DB.

## Riesgos y verificación

- La migración corre en el deploy de QA. Antes de promover a HML o PRD,
  verificar que los content types quedaron en `pwa` y que los grupos con
  permisos PWA los conservan.
- Los PRs abiertos que tocan `users/forms.py`, `users/views.py`,
  `users/services_pwa.py`, etc. tienen que actualizarse desde `development`.
  Git sigue los renombres.
