# docs/ia/AGENT_REPO_MAP.md

Orientación estable del repositorio `SISOC` para agentes de IA y desarrolladores.

Para ubicar código, usar CodeGraph primero (herramienta MCP `codegraph_explore` o
el CLI `codegraph`) y `grep` como respaldo. Este mapa solo da orientación que cambia
poco: no es una bitácora. El estado de cada PR, issue o corte vive en
`docs/registro/`. No hace falta actualizarlo en cada PR; solo cuando cambie la
estructura descrita acá.

## Stack

- Backend: Python 3.11, Django 5.2 LTS y Django REST Framework (`requirements/base.txt`).
  Pantallas server-side con templates Django y APIs DRF conviviendo.
- Front v2: React 19 + Vite + MUI en el workspace npm `src/frontends/`. La raíz del
  repo no tiene `package.json`.
- Base de datos: MySQL 8.4 (`docker-compose.yml`).
- Runtime: Docker Compose. Celery con Redis para PAS y Comedores
  (`docker/compose/docker-compose.celery.yml`, `src/backends/config/celery.py`).
- Calidad: black, pylint, djlint, pytest e import-linter (`.importlinter`).

## Cómo se corre localmente

Seguir `README.md` y `docs/operacion/instalacion.md`. En resumen: copiar
`.env.example` a `.env` y correr `docker compose up`. Los comandos de tests, lint y
migraciones están en `AGENTS.md` (sección Comandos).

En local todo corre en un solo proceso con `config.settings_all` (core más todos
los backends). `pytest.ini` usa la misma composición.

## Estructura del monorepo

```text
src/
|-- backends/
|   |-- config/       # proyecto Django: settings, urls, registro de backends
|   |-- kernel/       # código común + templates/, static/ y tests/ compartidos
|   |-- sisoc_core/   # apps del core: usuarios, dashboard, encuestas, insumos
|   `-- <vertical>/   # un backend por vertical, con su <vertical>_runtime/
|-- frontends/        # apps/, packages/, e2e/ del front v2
`-- scripts/          # helpers de IA, CI, operación, arquitectura y frontend
docs/                 # documentación operativa y de arquitectura (índice: docs/indice.md)
docker/               # imágenes y overrides de Compose (docker/compose/)
requirements/         # dependencias Python
```

Los imports no llevan el prefijo de carpeta (`import core`, `import comedores`):
`src/backends/config/__init__.py` agrega `src/backends/kernel/` y cada vertical al
`sys.path`. Decisión: `docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md`.

## Dueños de código

Cada backend vertical está registrado en `src/backends/config/backends.json` (apps,
prefijos de URL, servicio y workers). El core no figura ahí: es el proceso que
recibe el tráfico y atiende a los backends por proxy.

### Kernel y core

| Dueño | Ruta | Propósito |
| --- | --- | --- |
| Configuración | `src/backends/config/` | settings, URLconfs, middlewares, registro de backends y de URLs |
| Kernel | `src/backends/kernel/` | código común: `core`, `users`, `iam`, `ciudadanos`, `organizaciones`, `audittrail`, `catalogo_intervenciones`, `healthcheck`, `sentry` |
| Core | `src/backends/sisoc_core/` | `usuarios` (gestión de usuarios y login PWA), `dashboard`, `encuestas`, `insumos` |

### Verticales

| Vertical | Ruta | Apps | Servicio |
| --- | --- | --- | --- |
| Comedores | `src/backends/comedores/` | comedores, gestion_organizaciones, duplas, admisiones, intervenciones, historial, acompanamientos, expedientespagos, relevamientos, rendicioncuentasfinal, rendicioncuentasmensual, importarexpediente, comunicados, pwa | `backend_comedores` |
| CDI | `src/backends/cdi/` | centrodeinfancia, ticketera | `backend_cdi` |
| CDF | `src/backends/cdf/` | centrodefamilia | `backend_cdf` |
| Celiaquía | `src/backends/celiaquia/` | celiaquia | `backend_celiaquia` |
| Dispositivos | `src/backends/dispositivos/` | dispositivos, datacalle | `backend_dispositivos` |
| Inspecciones | `src/backends/inspecciones/` | inspecciones | `backend_inspecciones` |
| OCR | `src/backends/ocr/` | ocr | `backend_ocr` |
| PAS | `src/backends/pas/` | pas | `backend_pas` |
| VAT | `src/backends/vat/` | VAT | `backend_vat` |
| VPSL | `src/backends/vpsl/` | ver_para_ser_libre | `backend_vpsl` |

Tabla de prefijos de URL por backend: `docs/operacion/backends_por_servicio.md`.
Reglas entre servicios y checklist de cambios: `AGENTS.md` ("Verticales
independientes") y `docs/desarrollo/verticales_independientes.md`.

### Front v2

| Ruta | Propósito |
| --- | --- |
| `src/frontends/apps/sisoc/` | pantallas React migradas del core y los verticales |
| `src/frontends/apps/vpsl/` | Ver Para Ser Libres (`/v2/vpsl/`) |
| `src/frontends/apps/inet/` | INET (`/v2/inet/`) |
| `src/frontends/apps/celiaquia/` | Celiaquía (`/v2/celiaquia/`) |
| `src/frontends/apps/pas/` | formulario público de DDJJ de PAS (`/v2/pas/`) |
| `src/frontends/packages/ui/` | componentes y tema compartidos (`@sisoc/ui`) |
| `src/frontends/packages/api/` | cliente HTTP compartido (`@sisoc/api`) |
| `src/frontends/e2e/` | pruebas end-to-end con Playwright |

Guía del front v2: `docs/implementaciones/frontend_v2.md`.

## Puntos de entrada

| Pieza | Ruta | Notas |
| --- | --- | --- |
| Arranque Django | `manage.py` | elige el módulo de settings |
| Settings del core | `src/backends/config/settings.py` | apps, middleware, DRF, CSP, `FRONTEND_V2_UPSTREAMS` |
| Settings locales completos | `src/backends/config/settings_all.py` | core más todos los backends en un proceso |
| Settings por backend | `src/backends/config/backend_settings.py` y `src/backends/<vertical>/<vertical>_runtime/` | cada servicio vertical arma su settings y su URLconf |
| URLs del core | `src/backends/config/urls.py` | router del core y docs OpenAPI (`/api/schema/`, `/api/docs/`) |
| URLs completas | `src/backends/config/urls_all.py` | composición usada con `settings_all` |
| Proxy a backends | `src/backends/kernel/core/backend_proxy.py` | reenvía cada prefijo al servicio dueño |
| Front v2 | `src/backends/kernel/core/v2_frontend.py` | sirve `/v2/<modulo>/` con sesión Django |
| Registro de URLs | `src/backends/config/url_registry.json` | nombres de URL entre servicios para `reverse()` |
| Celery | `src/backends/config/celery.py` | app compartida, colas `pas` y `comedores` |
| Contenedores | `docker/django/entrypoint.py` | migraciones, roles de servicio y arranque del servidor |

### Registro de URLs entre servicios

El core y cada backend corren con su propio URLconf, pero sus templates hacen
`reverse()` de nombres del otro servicio. `url_registry.json` guarda esos nombres
para la composición completa, y cada servicio agrega los que no define como stubs
(ver `src/backends/kernel/core/url_registry.py`). Si se agrega o cambia una URL,
regenerarlo con `python manage.py generar_registro_urls` usando `settings_all`. Un
test de CI verifica que esté al día.

## Contexto operativo

### Servicios y roles de contenedor

La misma imagen cumple distintos roles según `DJANGO_SERVICE_ROLE`
(`docker/django/entrypoint.py`):

- `web` (por defecto): sirve HTTP. Usa `runserver` en desarrollo y Gunicorn en
  entornos de deploy.
- `migrator`: corre migraciones, fixtures y grupos, y termina. En deploy es el único
  que migra, porque el core sin los backends no puede cargar el grafo completo de
  migraciones.
- Workers: `bulk_credentials_worker`, `ciudadanos_import_worker`, `mailing_worker`,
  `user_import_worker`, `ocr_worker`, `encuestas_worker` y `health_urls_worker`.
- Celery (Compose aparte): `celery_pas_worker`, `celery_comedores_worker` y
  `celery_beat`.

En local, `docker-compose.yml` levanta `mysql`, `django`, los fronts (`front_*`),
`ocr_worker` y `encuestas_worker`. Los fronts no publican puertos: Django entrega
`/v2/<modulo>/` al navegador. En deploy, `docker/compose/docker-compose.deploy.yml`
define un `backend_<vertical>` por servicio y el `migrator`;
`docker/compose/docker-compose.produccion.yml` agrega los workers.

Cada imagen copia solo su código: la del core no trae los verticales y la de un
backend trae solo su carpeta. Un import de otro vertical que funciona en local con
`settings_all` puede fallar en deploy.

### Variables de entorno

- `.env.example` es el catálogo de variables. Cada servidor tiene su propio `.env`;
  no hay archivos `.env` por entorno versionados. No tocar `.env*` salvo pedido
  explícito.
- `ENVIRONMENT=dev` no se comporta como QA o PRD: hay toggles distintos por entorno.
- `RUN_MAKEMIGRATIONS_ON_START` vale `true` por defecto en dev y puede ocultar
  migraciones faltantes. Revisar siempre el diff de migraciones.
- `DJANGO_SETTINGS_MODULE` decide la composición: `config.settings_all` en local y
  tests; settings por servicio en deploy.

### Zonas sensibles

- `src/backends/config/settings.py`, `src/backends/config/urls.py` y
  `docker/django/entrypoint.py`: afectan a todos los servicios.
- `src/backends/kernel/users/bootstrap/groups_seed.py`: permisos globales.
- `src/backends/sisoc_core/encuestas/middleware.py`: middleware global que puede
  bloquear la navegación de cualquier usuario con una encuesta obligatoria.
- `src/backends/kernel/templates/` y `src/backends/kernel/static/custom/`: UI y JS
  compartidos. Mucho JS depende de IDs y clases exactas del HTML.
- `signals.py`, `tasks.py` y management commands: side effects poco visibles, como
  syncs con GESTIONAR o RENAPER.
- `migrations/` existentes: no editarlas para ordenar.

## Patrones del código

- La lógica de negocio va en `services/` cuando la app lo tiene. Conviven apps
  legacy con lógica en `views.py` o `models.py`.
- Entre dominios se usan contratos Python acotados (`<app>/api.py`) y registros
  (por ejemplo, filtros favoritos o contribuciones a Ciudadano 360), no imports
  directos de modelos. Reglas: `docs/ia/MODULAR_BOUNDARIES.md` y `.importlinter`.
- RENAPER se consulta solo mediante `core.services.renaper`.
- JS y CSS propios: compartidos en `src/backends/kernel/static/custom/`; los de un
  solo vertical en `<app>/static/custom/`, con la misma ruta pública.
- Tests: transversales en `src/backends/kernel/tests/`, de cada vertical en
  `src/backends/<vertical>/tests/` o cerca del módulo.

## Documentación según la tarea

| Tarea | Leer primero |
| --- | --- |
| Arquitectura y límites | `docs/ia/ARCHITECTURE.md`, `docs/ia/MODULAR_BOUNDARIES.md` |
| Cambio que cruza servicios | `docs/desarrollo/verticales_independientes.md`, `docs/operacion/backends_por_servicio.md` |
| Tests | `docs/ia/TESTING.md` |
| Permisos o seguridad | `docs/ia/SECURITY_AI.md` |
| Logging y errores | `docs/ia/ERRORS_LOGGING.md` |
| Estilo y templates | `docs/ia/STYLE_GUIDE.md` |
| Front v2 | `docs/implementaciones/frontend_v2.md` |
| PWA | `docs/implementaciones/pwa_backend.md`, `docs/operacion/deploy_pwas.md` |
| Deploy e infraestructura | `docs/operacion/deploy_automatizado.md`, `docs/operacion/infraestructura.md`, `docs/infra/QA_OPERATIONS.md` |
| Mapa visual de arquitectura | `docs/arquitectura/mapa_sisoc.html` (generado por `src/scripts/arquitectura/generar_mapa.py`) |

## Mantenimiento

Actualizar este archivo solo cuando cambie algo descrito acá: un dueño de código,
un punto de entrada, un rol de contenedor o el stack. Los detalles de una feature
van en su guía de `docs/implementaciones/` o en `docs/registro/`, no acá.
