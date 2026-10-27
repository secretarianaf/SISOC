# 2026-10-22 — Permiso propio para el mapa de dispositivos (#2759)

Issue: https://github.com/secretarianaf/SISOC/issues/2759

## Comportamiento

El mapa de dispositivos (#2676) usaba el mismo permiso que el listado (`dispositivos.view_dispositivo`), así que todo usuario con acceso al listado veía el mapa. Se agrega el permiso `dispositivos.ver_mapa_dispositivo` ("Puede ver el mapa de dispositivos").

- `/dispositivos/mapa/` y `/dispositivos/<pk>/ubicacion/` exigen `view_dispositivo` **y** `ver_mapa_dispositivo` (`permissions_all_required`). Sin cualquiera de los dos responden 403.
- En el listado, el botón **Mapa de dispositivos** y la acción **Ver en mapa** de cada fila solo aparecen con `ver_mapa_dispositivo`.
- El listado, el detalle y el alcance territorial no cambian.

## Decisión de despliegue

El permiso no se asigna a ningún grupo: al desplegar, solo los superusuarios conservan el acceso al mapa y un administrador debe asignarlo a los grupos o usuarios que correspondan desde el admin (`dispositivos | dispositivo | Puede ver el mapa de dispositivos`). Es el efecto buscado por el issue.

Se implementó como hotfix desde `main` y se integra por `homologacion`, sin pasar por `development`.

## Migración y reversión

`dispositivos/0007_alter_dispositivo_options.py` solo cambia `Meta.permissions` (sin cambios de esquema); Django crea el permiso en `post_migrate`. Si el código nuevo se sirve antes de migrar, el mapa queda inaccesible para no superusuarios (falla cerrado). Para revertir, quitar el código y revertir la migración a `0006`.
