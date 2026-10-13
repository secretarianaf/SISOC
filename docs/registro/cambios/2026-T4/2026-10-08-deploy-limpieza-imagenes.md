# Limpieza de imágenes en el deploy automático

## Problema

Con la modularización, cada deploy construye unas diez imágenes `sisoc/*`
(core, backends, migrador y fronts) etiquetadas con el SHA y no borra las
anteriores. El disco se llena con cada deploy: el deploy de HML del
2026-10-08 falló por `No space left on device`. La única limpieza era manual
(`src/scripts/infra/cleanup_prod_disk.sh`).

## Cambio

`src/scripts/operacion/deploy_verified.sh`, después de verificar el deploy
(migraciones y salud), borra las imágenes `sisoc/*` que no usa ningún
contenedor (aunque esté detenido) y que no son de la revisión desplegada ni de
la anterior. También borra la cache de build de más de 3 días.

- Si el deploy falla, no limpia: el rollback puede usar esas imágenes.
- Si la limpieza falla, el deploy queda verificado igual y se avisa con un
  warning en el log y en el Summary.
- No toca volúmenes, contenedores ni imágenes que no sean `sisoc/*`.

Guía: `docs/operacion/deploy_automatizado.md`, sección "Limpieza de imágenes".

## Validación

`src/backends/kernel/tests/test_deploy_script_paths.py` cubre:

- deploy verificado: borra solo la imagen sobrante;
- deploy fallido: no limpia;
- limpieza fallida: el deploy termina en 0 con aviso.

Los casos fallan con el script anterior y pasan con el nuevo.

## A revisar en los servidores

`src/scripts/crontab` todavía declara `docker system prune -af --filter
"until=24h" --volumes`. Ese comando borra volúmenes sin uso. Si sigue
instalado en algún servidor, conviene sacarlo: esta limpieza lo reemplaza.
