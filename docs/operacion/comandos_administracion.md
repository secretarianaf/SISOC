# Management commands relevantes

## Core
- `load_fixtures`: carga fixtures en modo upsert (no borra) y acepta
  `--force`/`--overwrite` para reaplicar las entradas existentes. Tras
  recorrer los archivos, reintenta sólo los registros fallidos para resolver
  FKs hacia fixtures posteriores, incluso si un archivo quedó parcialmente
  cargado. Detiene los reintentos si no hay progreso y reporta los errores
  restantes; no cambia el criterio inicial de tablas vacías ni fuerza cargas.
  Luego sincroniza el catálogo de intervenciones y el territorio del fixture. La
  sincronización territorial es create-only: resuelve claves naturales
  normalizadas, conserva filas ya presentes —incluidas las creadas
  orgánicamente— y reporta las filas que no pudo incorporar por integridad.
  El comando no descarga BAHRA; la actualización del fixture se prepara antes
  con `src/scripts/actualizar_territorio_desde_bahra.py` y admite `--dry-run`.
  Evidencia: `src/backends/kernel/core/management/commands/load_fixtures.py`,
  `src/backends/kernel/core/services/territorio_sync.py` y
  `docs/registro/cambios/2026-T3/2026-07-17-bajada-bahra-territorio.md`.
- `generate_webp_images`: genera WebP para ImageFields con opciones de filtro, calidad y estadísticas. Evidencia: src/backends/kernel/core/management/commands/generate_webp_images.py:1-111.
- `debug_queries`: ejecuta depuración de queries para vistas (todas o Ciudadanos). Evidencia: src/backends/kernel/core/management/commands/debug_queries.py:1-33.
- `run_benchmarks`: ejecuta benchmarks reproducibles en una DB efímera, serializa resultados JSON y compara contra baseline versionado; soporta `--rebuild-baseline`. Evidencia: src/backends/kernel/core/management/commands/run_benchmarks.py:1-176.

## Admisiones
- `corregir_expedientes_issue_2272`: preflight, aplicación transaccional (`--apply`) y verificación posterior (`--verify`) de la corrección versionada de expedientes. Requiere una ventana sin escrituras y un manifiesto previamente aprobado; el runbook de HML/PRD está en `docs/operacion/correccion_expedientes_issue_2272.md`. Evidencia: `src/backends/comedores/admisiones/management/commands/corregir_expedientes_issue_2272.py`.

## Users
- `create_groups`: crea grupos predeterminados y sincroniza permisos bootstrap segun la semilla declarativa de IAM (`src/backends/kernel/users/bootstrap/groups_seed.py`). Evidencia: `src/backends/kernel/users/management/commands/create_groups.py`.
- `sync_group_permissions_from_registry`: sincroniza permisos Django por grupo para grupos ya existentes. Util post-migracion en staging/prod. Evidencia: `src/backends/kernel/users/management/commands/sync_group_permissions_from_registry.py`.
- `create_test_users`: genera usuarios de prueba cuando `DEBUG=True`. Evidencia: `src/backends/kernel/users/management/commands/create_test_users.py`.
- `import_users_from_csv`: crea/actualiza usuarios replicando grupos desde un usuario de referencia. Evidencia: `src/backends/kernel/users/management/commands/import_users_from_csv.py`.
- `assign_provincia_to_test_user`: asigna `provincia_id=1` al usuario `ProvinciaCeliaquia`. Evidencia: `src/backends/kernel/users/management/commands/assign_provincia_to_test_user.py`.

## Relevamientos
- `import_relevamientos`: importa relevamientos desde CSV respetando signals/validaciones. Evidencia: `src/backends/comedores/relevamientos/management/commands/import_relevamientos.py`.
- `delete_relevamientos`: elimina IDs en lotes disparando `pre_delete`/`post_delete`. Evidencia: `src/backends/comedores/relevamientos/management/commands/delete_relevamientos.py`.

## Comedores
- `import_comedores_excel`: alta masiva desde Excel con normalizacion de estados. Evidencia: `src/backends/comedores/comedores/management/commands/import_comedores_excel.py`.
- `validar_comedores_csv`: marca comedores listados en CSV como `Validado` y los lleva a `Activo / En ejecucion`; soporta `--dry-run`. Evidencia: `src/backends/comedores/comedores/management/commands/validar_comedores_csv.py`.
- `update_programa_estado_comedores`: actualiza programa y estado general desde CSV por `comedor_id`, con override de programa/actividad/proceso/detalle y `--dry-run`. Evidencia: `src/backends/comedores/comedores/management/commands/update_programa_estado_comedores.py`.
- `update_estados_comedores`: aplica estados desde CSV a historial. Evidencia: `src/backends/comedores/comedores/management/commands/update_estados_comedores.py`.
- `update_estados_comedores_from_names`: crea historial de estados a partir de CSV con nombres (`Estado General`, `Subestado`, `Motivo`) y `comedor_id`; soporta `--dry-run`. Evidencia: `src/backends/comedores/comedores/management/commands/update_estados_comedores_from_names.py`.
- `reset_validaciones`: resetea validaciones de comedores a Pendiente. Evidencia: `src/backends/comedores/comedores/management/commands/reset_validaciones.py`.
- `update_comedores_dupla`: asigna duplas a comedores desde CSV, opcionalmente creando admisiones. Evidencia: `src/backends/comedores/comedores/management/commands/update_comedores_dupla.py`.
- `sync_comedores_gestionar`: sincroniza payload completo de comedores contra GESTIONAR (`Add`/`Update`, multithread). Evidencia: `src/backends/comedores/comedores/management/commands/sync_comedores_gestionar.py`.
- `sincronizar_accesos_pwa_organizaciones`: previsualiza y reconcilia la totalidad de accesos PWA derivados de organizaciones. Sin flags es un dry-run de sólo lectura; `--apply` persiste por organización y `--organizacion ID` limita el alcance (repetible). Ejecutar primero `python manage.py sincronizar_accesos_pwa_organizaciones` y revisar totales antes de repetir con `--apply`. Evidencia: `src/backends/comedores/comedores/management/commands/sincronizar_accesos_pwa_organizaciones.py`.
- `sync_territoriales_cache`: sincroniza cache de territoriales, con opciones de stats, force y cleanup. Evidencia: `src/backends/comedores/comedores/management/commands/sync_territoriales_cache.py`.

## Rendiciones
- `seed_rendicion_stage_examples`: crea escenarios QA idempotentes para las
  cuatro etapas de rendiciones. Requiere `--comedor-id`, solicita la contraseña
  de forma interactiva y no tiene credenciales predeterminadas. Usar solo en
  QA/local; crea usuarios, grupos y rendiciones en el comedor indicado.
  Evidencia: `src/backends/comedores/rendicioncuentasmensual/management/commands/seed_rendicion_stage_examples.py`.

## Centro de familia
- `cargar_legajos`: crea ciudadanos/participantes desde Excel. Evidencia: `src/backends/cdf/centrodefamilia/management/commands/cargar_legajos.py`.
- `reprocess_cabal`: reprocesa registros CABAL rechazados con confirmacion interactiva. Evidencia: `src/backends/cdf/centrodefamilia/management/commands/reprocess_cabal.py`.

## Centro de infancia (CDI)
- `mover_documentacion_cdi`: mueve los archivos de intervenciones CDI de `media/documentacion/` a `media/cdi/documentacion/` y actualiza el nombre guardado en cada fila (solo filas de CDI; los archivos de Comedores no se tocan). Dry-run por defecto; `--aplicar` ejecuta. Es idempotente y reanudable, informa los archivos faltantes sin fallar y borra el archivo viejo solo después de actualizar la fila, de comparar el SHA-256 de origen y destino y de comprobar que ninguna fila CDI ni de Comedores lo usa. Tiene que correr donde estén instaladas todas las apps (el migrador / `settings_all`): en un runtime sin Comedores (p. ej. `backend_cdi`) mueve y actualiza las filas pero no borra los viejos y los informa como `PENDIENTE`. Evidencia: `src/backends/cdi/centrodeinfancia/management/commands/mover_documentacion_cdi.py`.

### Ejecución automática en el deploy
`src/scripts/operacion/deploy_refresh.sh` corre `mover_documentacion_cdi --aplicar` en el migrador (`docker compose --profile migrate run --rm -T migrator python manage.py mover_documentacion_cdi --aplicar`) **en cada deploy que despliega servicios**, justo después de las migraciones y antes de reaplicar permisos y levantar los servicios, en QA, HML y producción. Corre también en un deploy selectivo sin migraciones (por eso el migrador se construye siempre) y no corre si el plan es `ninguno`. Como el comando es idempotente, los deploys siguientes no mueven nada: solo hacen la pasada de reconciliación (una consulta sobre las filas ya movidas y un chequeo de existencia por fila).

- Un error del comando (excepción o exit distinto de 0) **detiene el deploy** antes de levantar los servicios; la próxima corrida retoma donde quedó.
- `CONFLICTO`, `PENDIENTE`, `FALTANTE`, `OMITIDO` y `EN USO` **no** fallan el deploy: el script los repite al final con el prefijo `[REVISAR-CDI]` en el log del deploy para que una persona los revise y resuelva a mano (ver los pasos de abajo).
- El deploy **no hace backup** de `media/` ni de la base antes de migrar; el respaldo lo gestiona Infra (`docs/operacion/infraestructura.md`). El movimiento copia, verifica tamaño y SHA-256, actualiza la fila y recién entonces borra el original; no hay otro respaldo. Confirmar el respaldo vigente antes de promover.
- Nginx no se toca desde el deploy: el cierre de `/media/cdi/` (`docs/operacion/nginx/sisoc-produccion.conf`) sigue requiriendo `nginx -t` y reload manual en cada entorno, después de verificar que no quedan `MOVER`.

Los pasos manuales de abajo quedan solo para verificar el resultado y para revertir o resolver conflictos.

### Pasos en producción (CDI-F2)
Orden obligatorio: el movimiento tiene que correr **antes** de que Nginx cierre `/media/cdi/`, o en la misma ventana. Mientras haya filas con `documentacion/...` el archivo sigue accesible por la API autenticada (que lee el almacenamiento, no la URL); lo único que deja de funcionar al cerrar Nginx son los enlaces directos a `/media/cdi/`, que ya no usa ninguna pantalla.

1. Respaldar `media/documentacion/` y `media/cdi/` (o confirmar el respaldo vigente) y la tabla de intervenciones CDI.
2. Desplegar la versión con la migración `0055_documentacion_intervencion_prefijo_cdi` (solo cambia `upload_to`; no toca datos) y reiniciar `backend_cdi`.
3. Verificar en el migrador (grafo completo, no en `backend_cdi`) con un dry-run: `docker compose --profile migrate run --rm -T migrator python manage.py mover_documentacion_cdi`. Después del deploy automático debería no quedar nada para `MOVER`. Revisar la lista `MOVER`, los `LIMPIAR` (filas ya movidas cuyo archivo viejo sigue existiendo), los `FALTANTE` (filas cuyo archivo ya no existe; no se tocan) y los `CONFLICTO` (el destino existe con otro contenido; resolver a mano: no se cambia nada y se conservan ambos archivos).
4. Solo si hace falta repetir o resolver a mano, aplicar en el migrador: `docker compose --profile migrate run --rm -T migrator python manage.py mover_documentacion_cdi --aplicar` (el deploy ya lo corre solo). Repetirlo debe dar `movidos=0`. Si la corrida se corta, volver a correrla: es idempotente y retoma donde quedó. Una pasada de reconciliación inicial borra el archivo viejo de las filas que ya habían sido actualizadas (nombre `cdi/documentacion/<pk>_<nombre>`) pero cuyo borrado se cortó (`LIMPIADO`), solo si el contenido coincide y nadie más lo usa. Revisar las líneas `CONFLICTO` (un nombre que no entra en el campo, un error al actualizar la fila o un destino con otro contenido) y resolverlas a mano, y las `PENDIENTE` (no se pudo comprobar Comedores): repetir el comando en el migrador / `settings_all`. Cada archivo viejo termina en una de tres salidas: `LIMPIADO` (borrado), `EN USO` (otra fila CDI o de Comedores aún lo usa; se conserva) o `PENDIENTE` (no se pudo comprobar). El resumen incluye `limpiados`, `en_uso` y `pendientes`.
5. Verificar una intervención con documento: descarga por `/api/web/cdi/intervenciones/<id>/documentacion/` con un usuario con permiso.
6. Agregar a Nginx `location ^~ /media/cdi/ { return 404; }` (ver `docs/operacion/nginx/sisoc-produccion.conf`), `nginx -t` y reload. No tocar `/media/documentacion/`: Comedores lo sigue usando.
7. Comprobar que `https://<host>/media/cdi/documentacion/<archivo>` responde 404.

Reversa: no hay comando inverso. Si hiciera falta, restaurar `media/documentacion/` desde el respaldo del paso 1 y revertir los nombres de las filas desde el respaldo de la tabla.

## Celiaquia
- `migrar_comentarios`: migra comentarios legados de expedientes al historial; soporta `--dry-run`. Evidencia: `src/backends/celiaquia/celiaquia/management/commands/migrar_comentarios.py`.

## Auditoria
- `purge_auditlog`: borra registros de auditlog mas antiguos que N dias (soporta `--dry-run`). Evidencia: `src/backends/kernel/audittrail/management/commands/purge_auditlog.py`.

## PAS

- `sincronizar_supervivencia_pas`: solicita una corrida mensual en Celery; admite `--fecha` y `--reanudar ID`. Ver `docs/implementaciones/pas_control_mensual_celery.md`.

## Nota
- Los comandos `test_*` presentes en algunas apps se consideran utilitarios de desarrollo/regresion y no forman parte del inventario operativo principal.
