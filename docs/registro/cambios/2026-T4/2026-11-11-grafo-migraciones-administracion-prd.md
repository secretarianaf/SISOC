# Corrección operativa: comandos administrativos y grafo de migraciones en PRD

## Alcance

El grafo desplegado no estaba roto: los comandos se ejecutaban en la imagen
parcial del core. Se corrige la receta de administración en
`docs/operacion/backends_por_servicio.md`, fijando la imagen del migrador a
la versión del core activo y evitando su arranque con efectos de escritura.
No se modifica código, dependencias, settings, migraciones ni datos.

Se investigaron estos errores reportados al ejecutar comandos en `django`:

```text
Migration users.0041_bootstrap_simepi_cdi_groups dependencies reference nonexistent parent node ('centrodeinfancia', '0035_migrar_pueblo_originario_legacy')
Migration users.0029_bootstrap_cdi_referente_centro_group_squashed_0030_profile_territorial_scope dependencies reference nonexistent parent node ('centrodeinfancia', '0029_accesocdi_accesocdi_uniq_acceso_cdi_user_centro')
```

## Causa y comportamiento

La revisión de producción fue `3ab3d849f956682cc7e396816d3c3cee86bb5366`.
El checkout estaba limpio y el core usaba `sisoc/core:<esa revisión>`, sin
bind mount de código. `docker/django/Dockerfile` elimina los verticales al
construir core; `config.settings` no instala `centrodeinfancia`.
`MIGRATION_MODULES` estaba vacío. Los archivos CDI existían en el checkout,
pero no en la imagen core, por diseño.

Se reprodujo `NodeNotFoundError` con `MigrationLoader(None)` en el core
(en esa ejecución, `users.0049` referenciaba `comedores.0056`). El nodo que
aparece primero puede variar: no demuestra que falte solo una migración.
En `sisoc/migrator:<esa misma revisión>`, `config.settings_all` cargó 348
nodos y ambos padres CDI reportados estaban presentes.

La receta anterior no fijaba `SISOC_RELEASE_SHA`; en la sesión de diagnóstico
resolvía `sisoc/migrator:local`. La receta corregida obtiene la revisión de
la imagen activa y rechaza etiquetas que no sean un SHA completo.

## Por qué el deploy no falló

Se verificaron los registros históricos del artefacto real, no solo el
workflow vigente:

- [Deploy de producción](https://github.com/secretarianaf/SISOC/actions/runs/42242814018),
  job `deploy-produccion` / `127977191542`: exitoso. Construyó el migrador de
  esa revisión y registró `No migrations to apply` durante despliegue y
  verificación. `src/scripts/operacion/deploy_verified.sh` y
  `.github/workflows/deploy.yml` verifican migraciones mediante el migrador.
- [CI de esa revisión](https://github.com/secretarianaf/SISOC/actions/runs/42242813753),
  job `migrations_check` / `127977189620`: exitoso, `No changes detected`.
  `docker-compose.yml` usa `config.settings_all`, aunque llama `django` al
  servicio. Job `service_images` / `127977189483`: exitoso; ejecuta `check`
  en core y detección de migraciones en el migrador completo.

El deploy comprobó la composición correcta. Ejecutar después un comando que
necesita todo el grafo dentro de core no reproduce esa validación.

## Verificación en producción (2026-11-11)

Todas las operaciones de Django fueron de lectura; los contenedores efímeros
del migrador se eliminaron con `--rm` y no se inició su preparación normal.

| Comprobación | Resultado observado |
| --- | --- |
| Identidad core | Imagen `sha256:174f0d0bf0a53aaef61a432e02d1faa236c6023631e97415a85c175994bcb1e3` |
| Identidad migrador | Imagen `sha256:bf6f6df9b7e93a659cc00c9ab56497f8e55e7aba94dd43377d5e2bf7e5d60ca4` |
| `MigrationLoader(None)` en migrador | 348 nodos; ambos padres CDI presentes |
| `makemigrations --check --dry-run` en migrador | `No changes detected`, salida 0 |
| `migrate --plan` en migrador | `No planned migration operations`, salida 0 |
| Prechequeo de `createsuperuser` | `command.check_migrations()` exitoso; no se llamó a `handle()` |
| `/health/` interno de core | HTTP 200; contenedor healthy, cero reinicios |
| Logs de core, últimos diez minutos del diagnóstico | Cero marcadores `ERROR`/`[error]` y cero tracebacks |
| Checkout y core después de las consultas | Revisión original; checkout limpio |

Advertencia observada y no corregida: `models.W036` para
`admisiones.Admision`; MySQL no implementa constraints únicos condicionales.
No produjo error del grafo ni se cambió el esquema para silenciarla.

No se ejecutó `migrate` sin `--plan`, `--fake`, creación de usuarios,
fixtures ni preparación de DB. No se reconstruyó ni reinició producción.
No se afirma aceptación humana ni verificación funcional de pantallas.
No hay RED/GREEN de código: el cambio es documental; la regresión operativa
se comprueba con las consultas reales anteriores y la receta corregida.

## Diagnóstico inicial y continuación

No hace falta desplegar una nueva imagen para este hallazgo. Cambiar el grafo
o instalar verticales en core ampliaría el alcance sin reparar una falla real.
Se preservaron la revisión, las imágenes y los servicios activos.

Rollback de runtime: no aplica, porque no hubo cambio de runtime ni de DB.
Rollback de documentación: revertir únicamente esta corrección del runbook
y este registro; no tocar contenedores, datos ni historial de migraciones.
La publicación documental y sus checks son distintos del deploy histórico;
no deben presentarse como una nueva release desplegada.

## Prevención ejecutable solicitada posteriormente

La corrección documental anterior no evitaba repetir el comando incorrecto.
Se agrega `src/scripts/operacion/manage_deploy.py`: selecciona automáticamente
la revisión inmutable del core activo y sus Compose efectivos, exige que exista
el migrador de esa misma revisión y ejecuta los argumentos Django en él con
`config.settings_all`, `--no-deps`, `--pull never` y `--entrypoint python`.
No ejecuta la preparación de DB. La entrada interactiva y el código de salida
se conservan; no se agregan dependencias, settings ni permisos.

`manage.py` rechaza los comandos estándar que necesitan el grafo completo si
recibe settings parciales o faltan los verticales en disco. Informa el comando
correcto y termina con código 2 antes de inicializar Django. La ayuda y los
comandos ajenos al grafo mantienen su comportamiento. No se altera ninguna
dependencia de migración ni se desactiva su verificación.

Regresión: `src/backends/kernel/tests/test_manage_deploy.py`, sin DB. RED:
faltaba la herramienta y el comando parcial terminaba en traceback. GREEN:
selección de imagen, preservación de argumentos y salida, rechazo sin ejecución
ante imagen ausente/no versionada, ayuda sin Docker y rechazo de contexto
parcial sin traceback. Los tests locales no sustituyen los probes reales de PRD.

Esta continuación requiere desplegar la entrada administrativa y su guard;
el diagnóstico inicial de no modificar el grafo sigue vigente. La revisión,
comprobaciones posteriores y rollback se registran al completar el despliegue.
