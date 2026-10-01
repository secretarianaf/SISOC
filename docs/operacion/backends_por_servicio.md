# Backends por vertical: cómo corren, se despliegan y se agregan

Guía operativa del ADR `docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md`.
Primer backend: Dispositivos, que incluye Datacalle (#2309).

## Topología

```
Nginx del host ──► django (SISOC core, imagen sisoc/core:<sha>)
                     │  rutas propias del core
                     └─► proxy por prefijo (core/backend_proxy.py)
                           └─► backend_dispositivos (imagen sisoc/backend-dispositivos:<sha>)
                                 /dispositivos/, /datacalle/, /api/datacalle/
```

- **Ruteo.** El core recibe todo el tráfico. Antes de reenviar ya corrió su
  middleware: sesión, autenticación, contraseña inicial, datos personales y
  encuesta obligatoria. El backend autentica con la misma sesión (misma DB y
  `SECRET_KEY`) y valida CSRF por su cuenta.
- **Datos compartidos.** Una sola DB, `media/` como volumen compartido y
  `static_root/`, que recolecta el core y el backend lee en modo solo lectura.
- **Si el backend se cae,** el core responde 503 en sus prefijos y el resto de
  SISOC sigue funcionando.

## Configuración

- **`config/backends.json`** es la fuente única. Por cada backend declara sus
  apps, prefijos de URL, URLconf, origen en la red de Compose y servicios de
  Compose. De ahí leen los settings, el proxy y el deploy.
- **Settings por proceso:**
  - `config.settings`: core, sin las apps de los backends.
  - `<vertical>_runtime.settings`: el kernel más las apps del backend.
  - `config.settings_all`: todo en un proceso; lo usan los tests, el
    desarrollo local y el migrador.
- **Nombres de URL entre servicios.** `config/url_registry.json` permite que
  `{% url %}`, `redirect()` y `LOGIN_URL` resuelvan nombres de otro servicio.
  Cada proceso agrega rutas solo-`reverse()` para los nombres que no tiene.
  Si cambiás URLs, regenerálo:

  ```bash
  docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings_all django python manage.py generar_registro_urls
  ```

  `tests/test_servicios_backends.py` falla si quedó desactualizado.
- **Menú lateral.** Los ítems que aporta una app del core, como los tableros
  de `dashboard`, se registran en `core.services.sidebar_items`. En un backend
  sin esa app, el ítem no aparece.

## Deploy

`scripts/operacion/deploy_refresh.sh` decide el plan con
`scripts/operacion/deploy_targets.py`, comparando el SHA que corre hoy con el
nuevo:

| Cambio | Plan |
| --- | --- |
| Solo `backends/<x>/**` | **Selectivo:** construye ese backend y el migrador, migra, y recrea solo ese servicio (`up --no-deps`). |
| Solo `frontends/apps/<x>/**` | **Selectivo:** solo `front_<x>`. |
| Solo docs, tests o `.github/` | **Ninguno:** no se reinicia nada. |
| Cualquier otra cosa (kernel, core, config, templates, static, requirements, docker, compose, `CHANGELOG.md`) | **Completo:** construye todo, baja el stack, migra y levanta. |

- **Migraciones.** El servicio `migrator` (`docker compose --profile migrate
  run --rm migrator`) aplica todo el grafo con `config.settings_all`. Los
  servicios web no migran sus apps de backend.
- **El backend no carga el grafo de migraciones.** `makemigrations` o
  `migrate` con el settings de un backend fallan con `NodeNotFoundError`, y es
  lo esperado: las migraciones del kernel dependen de apps del core. Gunicorn
  y las vistas no usan el grafo. Para migrar, usar siempre el migrador.
- **Rollback.** `deploy_verified.sh` vuelve al SHA anterior y recrea los
  mismos servicios que tocó el deploy fallido. Las migraciones no se revierten
  solas.
- **Imágenes.** Cada imagen se etiqueta con el SHA (`SISOC_RELEASE_SHA`). En
  deploy no se monta el checkout: actualizarlo no cambia lo que corre hasta
  reconstruir el servicio.

## Agregar un backend

1. **Código:** `git mv <app> backends/<vertical>/<app>`. Los imports no
   cambian.
2. **Runtime:** crear `backends/<vertical>/<vertical>_runtime/` con
   `settings.py` y `urls.py`, copiando el de Dispositivos. El `urls.py` debe
   exponer `backend_urlpatterns`.
3. **Registro y settings:** sumar la entrada en `config/backends.json`, sacar
   las apps de `CORE_APPS` en `config/settings.py` y agregar la carpeta a
   `pythonpath` en `pytest.ini`.
4. **Compose:** sumar el servicio en `docker-compose.deploy.yml`, copiando
   `backend_dispositivos`.
5. **URLs:** si el vertical no tenía prefijo propio, agregarlo y dejar
   redirects 301 desde las URLs viejas, **solo por compatibilidad**.
6. **Registro de URLs:** regenerar `config/url_registry.json`.
7. **Verificación:** que pasen `tests/test_servicios_backends.py`,
   `tests/test_kernel_arranca_solo.py` y el job `service_images` de CI.
