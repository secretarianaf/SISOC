# Cambio: `/health/urls/` con el código de respuesta de cada URL sin parámetros

## Alcance

Se pidió una URL que muestre, para usar en PRD, si las URLs de SISOC responden
bien: solo GET, solo superusuarios, salteando las URLs con parámetros y las de
admin, logout, borrados, exportaciones y endpoints que solo aceptan POST;
respuesta en JSON con el código de cada URL y ejecución automática a las 6, 12
y 18.

Se implementó:

- `src/backends/kernel/core/services/health_urls.py`: toma las rutas de
  `src/backends/config/url_registry.json` (composición completa, verticales
  incluidas), filtra, hace un GET en proceso con la sesión del usuario técnico
  `sisoc-health-urls` (las rutas de verticales pasan por `core.backend_proxy`, como el tráfico
  real) y guarda el resultado en `LOG_DIR/health_urls.json` con escritura
  atómica.
- `src/backends/kernel/core/management/commands/chequear_urls.py`: corre el
  chequeo una vez, o con `--horarios` queda corriendo y chequea en esos
  horarios. Un fallo de una corrida queda en el JSON y no corta el worker.
- `src/backends/kernel/healthcheck/views.py` y `urls.py`: `GET /health/urls/`
  devuelve el último JSON.
- `src/backends/kernel/core/url_registry.py`: el registro ahora incluye las
  rutas sin nombre (`"name": ""`); los stubs de `reverse()` las ignoran.
  `url_registry.json` regenerado (255 rutas sin nombre nuevas).
- `docker/django/entrypoint.py` y `docker/compose/docker-compose.produccion.yml`:
  worker `health_urls_worker` (imagen del core) en HML/PRD. Variables nuevas en
  `.env.example`: `HEALTH_URLS_HORARIOS`.
- Guía operativa: `docs/operacion/instalacion.md`.

Las alternativas de ejecución (en el request, por lotes, cron del servidor,
Celery beat de PAS) y la elección del worker propio las propuso el agente y
las confirmó quien pidió el cambio. El request no alcanza: son unas 330 URLs
contra un timeout de Gunicorn de 30 s; Celery beat corre con la imagen de PAS,
que no conoce las demás URLs.

## Comportamiento

- `/health/urls/`: sin sesión redirige al login; un usuario no superusuario
  recibe 403; sin resultados todavía, 404 con un mensaje; si no, el JSON con
  `generado`, `duracion_s`, `resumen` (`chequeadas`, `por_status`,
  `ignoradas_solo_post`, `excluidas`, `salteadas_con_parametros`) y `urls`
  (`url`, `nombre`, `status`).
- `status` es el código real (200, 302, 404, 500, 504...). Los redirects no se
  siguen. Un 405 cuenta como "solo POST" y no se lista.
- Exclusiones por ruta o nombre: prefijo `admin/` y `logout`, `delete`,
  `eliminar`, `borrar`, `export`, `excel`, `xlsx`, `csv`, `descarg`. Las
  consultas a RENAPER sí se chequean.
- Endpoints que esperan parámetros por query o payload pueden responder 4xx
  sin estar rotos (por ejemplo, un ajax sin datos responde error de
  validación).
- Usuario técnico `sisoc-health-urls`: el chequeo lo crea la primera vez
  (superusuario, sin contraseña utilizable, no entra por el login) y en cada
  corrida deja su perfil con acceso web y sin cambio de contraseña ni
  confirmación de datos pendientes. Si está desactivado, el chequeo no corre y
  el JSON lo dice: es la forma de apagarlo. Es un alta de datos en PRD, sin
  migración.
- Control previo: si `inicio` no responde 200 para ese usuario (por ejemplo,
  por una encuesta obligatoria pendiente), no se recorren las URLs y el JSON
  muestra el error con el status y el destino del redirect. Evita un "todo
  302" que parezca sano.
- El chequeo crea una sesión de ese usuario y la borra al terminar.

## Verificación

- `pytest src/backends/kernel/tests/test_health_urls.py src/backends/kernel/tests/test_docker_entrypoint_unit.py src/backends/kernel/tests/test_servicios_backends.py src/backends/kernel/tests/test_legacy_redirects.py src/backends/kernel/tests/test_backend_proxy.py src/backends/kernel/tests/test_kernel_arranca_solo.py src/backends/kernel/tests/test_comedores_runtime.py src/backends/kernel/tests/test_ocr_runtime.py src/backends/kernel/tests/test_deploy_targets.py src/backends/kernel/tests/test_deploy_refresh_script.py src/backends/kernel/tests/test_deploy_workflow.py -n 4`
  (imagen local con SQLite): 174 passed, antes del cambio al usuario técnico.
- Después del usuario técnico y el control previo: `pytest src/backends/kernel/tests/test_health_urls.py src/backends/kernel/tests/test_docker_entrypoint_unit.py src/backends/kernel/tests/test_servicios_backends.py src/backends/kernel/tests/test_kernel_arranca_solo.py -n 4`: 66 passed.
- `black` y `pylint` sobre los Python tocados: el único aviso nuevo es
  `too-many-return-statements` en `main()` del entrypoint (ya estaba en 7/6;
  CI no corre pylint sobre `docker/`).
- No corrió: la suite completa ni el chequeo contra un entorno con datos y
  backends levantados. Falta la aceptación de quien pidió el
  cambio.
