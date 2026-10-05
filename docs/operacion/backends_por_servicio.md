# Backends por vertical: cómo corren, se despliegan y se agregan

Guía operativa del ADR `docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md`.

Para desarrollar y revisar cambios, usar `docs/desarrollo/verticales_independientes.md`.

| Backend | Apps | Prefijos |
| --- | --- | --- |
| `dispositivos` | dispositivos, datacalle | `/dispositivos/`, `/datacalle/`, `/api/datacalle/` |
| `vpsl` | ver_para_ser_libre | `/ver-para-ser-libre/`, `/api/vpsl/` (el front React sigue en `/v2/vpsl/`) |
| `pas` | pas (más Celery: `celery_pas_worker`, `celery_beat`) | `/pas/`, `/media/pas/` |
| `vat` | VAT | `/vat/`, `/api/vat/`, `/api/schema/VAT/`, `/api/docs/VAT/`, `/api/redoc/VAT/` |
| `celiaquia` | celiaquia | `/celiaquia/`, `/reporter-provincias/`, `/api/celiaquia/` |
| `cdi` | centrodeinfancia, ticketera | `/centrodeinfancia/`, `/simepi/`, `/api/ticketera/` |
| `cdf` | centrodefamilia | `/centrodefamilia/`, `/api/centrodefamilia/` |

**El core** corre las apps de `src/backends/sisoc_core/`: el cluster de Comedores
(comedores, admisiones, relevamientos, intervenciones, rendiciones, etc.) y
los servicios propios del core (dashboard, comunicados, encuestas, OCR, PWA,
usuarios). No es un backend detrás del proxy: es el proceso que recibe el
tráfico. Por eso no figura en `src/backends/config/backends.json`. Un cambio solo en
`src/backends/sisoc_core/**` recrea solo los servicios del core (ver Deploy).

**Datos maestros en el kernel.** `organizaciones` (Organizacion, roles,
avales) y `catalogo_intervenciones` (tipos, subtipos, destinatarios y
contactos) viven en `src/backends/kernel/`, porque los usan CDI, CDF y el core. Las
pantallas de organizaciones y el modelo `Firmante`, que se relaciona con
comedores, quedan en el core (`gestion_organizaciones`). Las tablas no
cambiaron de nombre.

**URLs viejas de CDF.** `/centros/`, `/actividades/`, `/ajax/actividades/`,
`/informecabal/` y `/beneficiarios/` redirigen a `/centrodefamilia/...`
(`core.legacy_redirects`). Esas redirecciones existen solo por compatibilidad
con enlaces guardados: no hay que usarlas en código nuevo.

## Topología

```
Nginx del host ──► django (SISOC core, imagen sisoc/core:<sha>)
                     │  rutas propias del core
                     └─► proxy por prefijo (src/backends/kernel/core/backend_proxy.py)
                           └─► backend_dispositivos (imagen sisoc/backend-dispositivos:<sha>)
                                 /dispositivos/, /datacalle/, /api/datacalle/
```

- **Ruteo.** El core recibe todo el tráfico. Antes de reenviar ya corrió su
  middleware: sesión, autenticación, contraseña inicial, datos personales y
  encuesta obligatoria. El backend autentica con la misma sesión (misma DB y
  `SECRET_KEY`) y valida CSRF por su cuenta.
- **Datos compartidos.** Una sola DB, `media/` como volumen compartido y
  `static_root/`, que recolecta el migrador y los servicios web leen en modo solo lectura.
- **Si el backend se cae,** el core responde 503 en sus prefijos y el resto de
  SISOC sigue funcionando.

## Configuración

- **`src/backends/config/backends.json`** es la fuente única. Por cada backend declara sus
  apps, prefijos de URL, URLconf, origen en la red de Compose y servicios de
  Compose. De ahí leen los settings, el proxy y el deploy.
- **Settings por proceso:**
  - `config.settings`: core, sin las apps de los backends.
  - `<vertical>_runtime.settings`: el kernel más las apps del backend.
  - `config.settings_all`: todo en un proceso; lo usan los tests, el
    desarrollo local y el migrador.
- **Nombres de URL entre servicios.** `src/backends/config/url_registry.json` permite que
  `{% url %}`, `redirect()` y `LOGIN_URL` resuelvan nombres de otro servicio.
  Cada proceso agrega rutas solo-`reverse()` para los nombres que no tiene.
  Si cambiás URLs, regenerálo:

  ```bash
  docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings_all django python manage.py generar_registro_urls
  ```

  `src/backends/kernel/tests/test_servicios_backends.py` falla si quedó desactualizado.
- **Menú lateral.** Los ítems que aporta una app del core, como los tableros
  de `dashboard`, se registran en `core.services.sidebar_items`. En un backend
  sin esa app, el ítem no aparece. La regla de menú "solo VAT" vive en el
  kernel (`iam.roles_vat`), así que se aplica en todos lados.
- **Filtros favoritos.** El endpoint lo sirve el core. Si la sección pertenece
  a un backend (`favorite_sections`), el core reenvía el pedido a ese backend.
- **Ciudadano 360.** Las secciones de VAT, Celiaquía y CDF (sección y monto) son contribuciones
  renderizadas (`ciudadanos.detail_contributions`): el template de la sección
  vive en el vertical. Si el vertical corre en otro backend
  (`ciudadano_contributions`), el core pide el fragmento ya renderizado con la
  sesión del usuario. Si no responde, la sección queda vacía y el resto del
  detalle se muestra igual.
- **Métricas del dashboard de CDF.** Si `centrodefamilia` no está instalada en
  el core, el dashboard las pide a `/centrodefamilia/metricas-dashboard/`. Si
  el backend no responde, muestra las métricas en cero.
- **Celery** solo lo usa PAS: el worker y el beat corren con la imagen y el
  settings del backend de PAS. El deploy selectivo de PAS los recrea
  (`extra_services`).

## Deploy

`src/scripts/operacion/deploy_refresh.sh` decide el plan con
`src/scripts/operacion/deploy_targets.py`, comparando el SHA que corre hoy con el
nuevo:

| Cambio | Plan |
| --- | --- |
| Solo `src/backends/<x>/**` | **Selectivo:** construye ese backend y el migrador, migra, y recrea solo ese servicio (`up --no-deps`). |
| Solo `src/backends/sisoc_core/**` | **Selectivo:** construye la imagen del core y el migrador, migra, y recrea solo los servicios con imagen `sisoc/core` del entorno (en QA, `django` y `ocr_worker`; en PRD, además los workers de importación, credenciales y mailing). Los backends no se reinician. Si no se pueden resolver esos servicios, hace un deploy completo. |
| Solo `src/frontends/apps/<x>/**` | **Selectivo:** solo `front_<x>`. |
| Solo docs/Markdown salvo CHANGELOG, `.github/`, `src/scripts/github/`, `src/backends/<dueño>/tests/` o `src/frontends/e2e/` | **Ninguno:** no se reinicia nada. Los tests dentro de una app siguen la regla del dueño. |
| Compartidos de `src/frontends/` (paquetes, config, lockfile) | **Selectivo:** todos los fronts; sin migrador. |
| `docker/frontends/` o `src/scripts/frontends/` | **Selectivo:** todos los fronts; sin migrador. |
| Otros scripts de `src/scripts/` | **Completo:** el selector no exceptúa esas rutas. |
| Cualquier otra cosa (kernel, config, recursos compartidos, requirements, docker, compose, `CHANGELOG.md`) | **Completo:** construye todo, baja el stack, migra y levanta. |

- **Migraciones.** El servicio `migrator` (`docker compose --profile migrate
  run --rm migrator`) aplica todo el grafo con `config.settings_all`. Los
  servicios web no migran sus apps de backend.
- **El backend no carga el grafo de migraciones.** `makemigrations` o
  `migrate` con el settings de un backend fallan con `NodeNotFoundError`, y es
  lo esperado: las migraciones del kernel dependen de apps del core. Gunicorn
  y las vistas no usan el grafo. Para migrar, usar siempre el migrador.
- **Comandos de administración que leen migraciones** (`createsuperuser`,
  `migrate`, `showmigrations`) se corren en el migrador, porque el core
  tampoco tiene el grafo completo:

  ```bash
  docker compose --project-directory . -f docker/compose/docker-compose.deploy.yml --profile migrate run --rm migrator python manage.py createsuperuser
  ```

  En deploy, la web no prepara la DB (`SISOC_PREPARAR_DB=false`). El migrador
  (rol `migrator` del entrypoint) aplica migraciones, fixtures,
  `create_test_users` y `create_groups`.
- **Rollback.** `deploy_verified.sh` vuelve al SHA anterior y recrea los
  mismos servicios que tocó el deploy fallido. Las migraciones no se revierten
  solas.
- **Imágenes.** Cada imagen se etiqueta con el SHA (`SISOC_RELEASE_SHA`). En
  deploy no se monta el checkout: actualizarlo no cambia lo que corre hasta
  reconstruir el servicio.

## Agregar un backend

1. **Código:** `git mv <app> src/backends/<vertical>/<app>`. Los imports no
   cambian.
2. **Runtime:** crear `src/backends/<vertical>/<vertical>_runtime/` con
   `settings.py` (`aplicar(globals(), "<vertical>")`, de
   `src/backends/config/backend_settings.py`) y `urls.py`, que define `backend_urlpatterns`
   y usa `urlpatterns_de_backend` (`src/backends/config/backend_urls.py`).
3. **Registro y settings:** sumar la entrada en `src/backends/config/backends.json`, sacar
   las apps de `CORE_APPS` en `src/backends/config/settings.py` y agregar la carpeta a
   `pythonpath` en `pytest.ini`.
4. **Compose:** sumar el servicio en `docker/compose/docker-compose.deploy.yml`, copiando
   `backend_dispositivos`.
5. **URLs:** si el vertical no tenía prefijo propio, agregarlo y dejar
   redirects 301 desde las URLs viejas, **solo por compatibilidad**.
6. **Registro de URLs:** regenerar `src/backends/config/url_registry.json`.
7. **Contribuciones a páginas del core:** si el vertical aporta secciones de
   favoritos o de Ciudadano 360, declararlas en `favorite_sections` o
   `ciudadano_contributions`. Las de Ciudadano 360 tienen que ser
   renderizadas, con template propio.
8. **Verificación:** que pasen `src/backends/kernel/tests/test_servicios_backends.py` (cada backend
   recorre sus rutas sin argumentos en su propio proceso),
   `src/backends/kernel/tests/test_kernel_arranca_solo.py` y el job `service_images` de CI.
