# docs/ia/AGENT_REPO_MAP.md

Mapa practico del repositorio `SISOC` para futuros agentes de IA y desarrolladores.

## Como leer este documento

Reglas vigentes y checklists: `docs/desarrollo/verticales_independientes.md`.
- Kernel no importa core/verticales; un servicio no importa otro.
- Datos remotos por contribuciones HTML/JSON/reenvío; permisos en el dueño.
- Prefijos y reverse en registros; recursos por app; grafo completo en migrador.
- Controlar imports, runtime/imagen aislada y plan con `deploy_targets.py`.
- Comprobar referencias documentales con `src/scripts/ci/check_docs_paths.py`.
- DX del ordenamiento #2639: conservar las entradas autodetectables en la raíz
  del repo o del workspace npm. Pylint de CI enumera `src/scripts/*.py` además
  de config/apps; el debugger nativo de `.vscode/launch.json` usa
  `config.settings_all`. Evidencia y límites:
  `docs/registro/cambios/2026-T4/2026-10-05-2639-auditoria-orden-dx.md`.

- Estructura del monorepo (#1931/#2251): el codigo comun vive en `src/backends/kernel/`
  (`core`, `users`, `iam`, `ciudadanos`, `audittrail`), cada vertical migra a
  `src/backends/<vertical>/` y cada front a `src/frontends/apps/<modulo>/`. Los imports
  no cambian: `src/backends/config/__init__.py` agrega `src/backends/kernel/` al `sys.path` (tooling:
  `.pylintrc`, `pytest.ini`, `architecture.yml`). Decision y plan:
  `docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md`.
- Backends por vertical (`src/backends/`, registro en `src/backends/config/backends.json`):
  `dispositivos` (con datacalle), `vpsl`, `pas` (con Celery), `vat` y
  `celiaquia`, `cdi` y `cdf`. El core los atiende por proxy. Para tests y desarrollo todo
  corre junto con `config.settings_all`. Guia:
  `docs/operacion/backends_por_servicio.md`.
- `src/backends/kernel/users` es identidad y permisos (modelos, middleware, alcance
  territorial, delegacion, roles). La gestion de usuarios del core (pantallas,
  formularios, importacion masiva, API de login PWA) vive en `src/backends/sisoc_core/usuarios/`; los
  accesos PWA (`AccesoComedorPWA` y afines) y su logica, en `src/backends/sisoc_core/pwa/`
  (`pwa.services.accesos`), con sus tablas `users_*` de siempre.

- Sincronizacion DataCalle: los cambios de main de #2452/#2453 se incorporan a
  development conservando coordinadores PWA y su checkbox maestro. La migracion
  users/0051 une las hojas de configuracion mobile y DataCalle sin operaciones.
  Evidencia/conflictos: docs/registro/cambios/2026-09-08-sincronizacion-datacalle-main.md.

- PWA privadas: Espacios Comunitarios, DataCalle y Gestionar despliegan desde sus
  propios repositorios y ramas `main`, `homologacion` y `development`. SISOC ya
  no las activa como parte de su deploy. `src/scripts/operacion/pwas.json` y
  `deploy_pwas.py` quedan como herramientas operativas compatibles, no como el
  disparador automatico. `render_pwa_nginx.py` genera el include compartido;
  `src/scripts/infra/install_qa_pwa_nginx.sh` lo instala transaccionalmente en el
  vhost HTTP de QA con backup y rollback. Contrato, aliases y riesgos:
  `docs/operacion/deploy_pwas.md`. No mover `/sisoc/SISOC-Mobile` ni asumir
  acceso publico de Git. Verificar tambien estabilidad de workers tras desplegar:
  el healthcheck HTTP no detecta errores de lectura de codigo en otros UID de
  contenedores.

- `Hecho observado`: confirmado leyendo codigo, config, workflows o docs del repo.
- `Inferencia`: deduccion razonable por nombres, estructura o convenciones, pero no validada en profundidad.
- `No confirmado`: no encontre evidencia suficiente en esta exploracion acotada.

## Resumen ejecutivo

### Hechos observados

- Es un monorepo Django modularizado por apps de dominio, con backend renderizado por templates y APIs DRF convivientes. Corre como varios servicios desde el mismo codigo: core (proxy de entrada), un backend por vertical, migrador unico, workers y front v2 (ver `docs/operacion/backends_por_servicio.md`).
- El stack principal es Python 3.11 + Django 5.2 LTS + MySQL 8 + Docker Compose.
- La operacion local y CI estan pensadas en modo Docker-first.
- El repo mezcla backoffice web tradicional, APIs internas/server-to-server, flujos asincronos simples (hilos y workers dedicados; Celery solo para PAS), y una capa PWA/API para ciertos casos de uso.
- La logica de negocio suele vivir en `services/` cuando la app la tiene, pero coexisten apps mas legacy con mas logica en `views.py`, `models.py` o `tasks.py`.
- Hay un esfuerzo explicito de control arquitectonico incremental con `import-linter` (`.importlinter`) para evitar que el monolito siga acoplandose.
- Los modulos nuevos se ubican en el dueño correspondiente y respetan los servicios ya separados; reglas y límites actuales en `docs/ia/MODULAR_BOUNDARIES.md`.
- VPSL convive con sus pantallas Django existentes y el nuevo React en `/v2/vpsl/`. La app está en `src/frontends/apps/vpsl/`, usa `@sisoc/ui` y `@sisoc/api`, y se sirve desde `front_vpsl` por el router autenticado `src/backends/kernel/core/v2_frontend.py`. La API `/api/vpsl/` corre en el backend VPSL (o en el proceso único local con settings_all) y reutiliza la lógica del dominio, con adaptadores de ModelForms/vistas existentes y alcance compartido en `services/access.py`. Ver `docs/implementaciones/frontend_v2.md` y `docs/operacion/ver_para_ser_libre_react.md`.
- Registro nominal React: `src/frontends/apps/vpsl/src/Workflow.tsx` replica las secciones y reglas condicionales de `registro_form.html`; el schema de `api_workflow.py` incluye `renaper_estado` oculto y `graduacion_opcional` desde el ModelForm oficial para registros históricos. Crear usa Guardar y continuar y recarga el schema para el siguiente número de acta. La compatibilidad con PR #2566 se verifica en `src/backends/vpsl/ver_para_ser_libre/tests/test_api_compatibilidad.py` y `src/frontends/apps/vpsl/src/Workflow.test.tsx`; los límites de promoción están en `docs/operacion/ver_para_ser_libre_react.md`.
- El tema visual de Front v2 usa `getTheme(mode)` de `src/frontends/packages/ui/src/theme.ts`, con correcciones de contraste AA; las reglas de componentes y UX vigentes están en `docs/implementaciones/frontend_v2.md`.

### Inferencias utiles

- No parece ser un repositorio "nuevo" ni estrictamente homogenizado: conviven zonas modernas, refactors en curso y zonas legacy con patrones distintos.
- Antes de tocar cualquier feature conviene asumir side effects ocultos: signals, syncs con externos, commands bootstrap y permisos por grupos.

## Stack y herramientas detectadas

### Backend

| Item | Estado | Evidencia |
| --- | --- | --- |
| Python 3.11 | Hecho observado | `pyproject.toml`, workflows CI |
| Django 5.2.16 | Hecho observado | `requirements/base.txt` |
| Django REST Framework | Hecho observado | `requirements/base.txt`, `src/backends/config/settings.py` |
| drf-spectacular | Hecho observado | `requirements/base.txt`, `src/backends/config/urls.py` |
| Gunicorn | Hecho observado | `requirements/base.txt`, `docker/django/entrypoint.py` |
| MySQL 8.4 | Hecho observado | `docker-compose.yml` |
| PyMySQL + mysqlclient | Hecho observado | `requirements/base.txt` |
| pytest / pytest-django / pytest-xdist / pytest-cov | Hecho observado | `requirements/test.txt`, `pytest.ini` |
| black / pylint / djlint | Hecho observado | `pyproject.toml`, `requirements/dev.txt`, `requirements/lint.txt` |
| import-linter | Hecho observado | `.importlinter`, `.importlinter_celiaquia_config`, `requirements/arch.txt` |
| Sentry | Hecho observado | `.env.example`, `requirements/base.txt` |
| OCR / PDF / DOCX / Excel tooling | Hecho observado | `requirements/base.txt`, app `src/backends/sisoc_core/ocr/`, templates docx/pdf |

### Frontend

| Item | Estado | Evidencia |
| --- | --- | --- |
| Templates Django server-side | Hecho observado | `src/backends/kernel/templates/`, `*/templates/` |
| JS/CSS estaticos propios | Hecho observado | compartidos en `src/backends/kernel/static/custom/`; los de un solo vertical en `<app>/static/custom/` |
| Bootstrap/AdminLTE/Select2 | Hecho observado | `src/backends/kernel/static/dist/`, `requirements`, templates |
| PWA backend + endpoints | Hecho observado | `src/backends/sisoc_core/pwa/`, `src/backends/config/urls.py`, docs PWA |
| Toolchain Node | Hecho observado | workspace npm en `src/frontends/` (front v2); la raiz no tiene `package.json` |
| Front v2 React 19 + Vite + MUI | Hecho observado | `src/frontends/apps/vpsl/`, `src/frontends/apps/celiaquia/`, `src/frontends/packages/ui/`, `src/frontends/packages/api/` |

### Operacion y CI

| Item | Estado | Evidencia |
| --- | --- | --- |
| Docker Compose para local | Hecho observado | `docker-compose.yml` |
| Compose separado para deploy | Hecho observado | `docker/compose/docker-compose.deploy.yml`, `docker/compose/docker-compose.produccion.yml` |
| GitHub Actions para lint/tests/arquitectura/release sanity | Hecho observado | `.github/workflows/` |
| Promoción event-driven y sincronización descendente con gates | Hecho observado | `.github/workflows/release-orchestrator.yml`, `.github/workflows/deploy.yml`, `docs/operacion/deploy_automatizado.md` |
| Helpers de Codex/worktrees | Hecho observado | `src/scripts/ai/`, `.codex/environments/environment.toml` |

## Que tipo de proyecto es

### Hechos observados

- Sistema interno/backoffice multi-modulo orientado a gestion social/territorial.
- Mueve varias areas funcionales bajo un mismo monolito: comedores, relevamientos, ciudadanos, centro de familia, celiaquia, admisiones, usuarios, rendiciones, VAT, ticketera, OCR y otros modulos satelite.
- Expone UI HTML tradicional, APIs DRF y algunos endpoints server-to-server.

### Flujos principales inferibles

1. Usuarios internos autenticados operan el backoffice Django.
2. Los modulos de dominio persisten en MySQL y renderizan templates o exponen APIs.
3. Algunas acciones sincronizan datos con sistemas externos como GESTIONAR o RENAPER.
4. La PWA consume endpoints dedicados bajo `/api/pwa/`.
5. El arranque Docker ejecuta migraciones, fixtures y bootstrap de grupos/usuarios de prueba segun entorno.

## Como se corre localmente

### Flujo principal recomendado

1. Copiar `.env.example` a `.env`.
2. Ajustar variables minimas de DB, puertos y claves externas si hace falta.
3. Levantar con `docker compose up`.
4. Acceder a `http://localhost:8001` por default.

### Hechos observados

- `docker-compose.yml` levanta `mysql`, `django`, `ocr_worker`, `encuestas_worker`, `front_vpsl` y `front_celiaquia`. Los fronts solo exponen su puerto dentro de la red de Compose; Django entrega `/v2/<modulo>/` al navegador (`FRONTEND_V2_UPSTREAMS`).
- El contenedor `django` monta el repo completo en `/sisoc/`.
- `docker/django/entrypoint.py` espera MySQL, puede correr `makemigrations`, siempre corre `migrate`, `load_fixtures`, `create_test_users`, `create_groups`, y luego levanta `runserver` o `gunicorn` segun `ENVIRONMENT`.

### Helpers operativos del repo

- `src/scripts/ai/codex_task.ps1 <slug>`: crea branch `codex/<slug>`, worktree en `../worktrees/<slug>` y bootstrap.
- `src/scripts/ai/codex_run.ps1 up`: bootstrap + levantar entorno.
- `src/scripts/ai/codex_run.ps1 validate`: corre `black`, `djlint`, smoke tests y `makemigrations --check`.
- `src/scripts/operacion/deploy_refresh.sh`: refresh operativo de deploy; acepta un SHA esperado, hace fast-forward antes de validar los Compose y bloquea una revisión obsoleta antes del downtime. Así un checkout anterior puede incorporar un Compose nuevo de forma segura.
- `src/scripts/operacion/deploy_verified.sh`: wrapper de CI para QA/HML/PRD; valida migraciones y healthcheck y restaura automáticamente el checkout/stack anterior ante un fallo.

## Estructura general del proyecto

### Raiz

El mapa completo de primer nivel esta en `README.md`. Resumen:

```text
SISOC/
|-- src/
|   |-- backends/
|   |   |-- config/          # proyecto Django: settings, urls, middleware, registro de backends
|   |   |-- kernel/          # codigo comun (core, users, iam, ciudadanos, audittrail, ...)
|   |   |                    # + templates/, static/ y tests/ compartidos
|   |   |-- sisoc_core/      # cluster de Comedores y apps propias del core
|   |   `-- <vertical>/      # pas, cdi, cdf, celiaquia, dispositivos, vat, vpsl
|   |-- frontends/           # apps/, packages/, e2e/; entradas de herramientas autodetectables
|   |   `-- config/          # opciones base compartidas de TypeScript
|   `-- scripts/             # helpers IA, CI, operacion, frontend y GitHub
|-- docs/                    # fuente de verdad operativa y arquitectonica
|-- docker/                  # imagenes Django/frontend y compose/ (overrides de deploy)
|-- requirements/            # dependencias Python (all.txt = base + dev + test)
|-- .github/workflows/       # CI, lint, arquitectura, release
|-- docker-compose.yml       # stack local (los overrides viven en docker/compose/)
|-- manage.py, conftest.py   # entrada Django y fixtures globales de pytest
|-- .env.example             # catalogo de variables
|-- pytest.ini               # config de tests
`-- .importlinter            # contratos de imports
```

### Carpetas raiz importantes

| Ruta | Para que sirve | Cuando mirarla primero |
| --- | --- | --- |
| `src/backends/config/` | configuracion global de Django, URLs y middleware | cambios cross-cutting, auth, API docs, seguridad, entorno |
| `docs/` | documentacion operativa y de arquitectura | siempre antes de expandir contexto |
| `src/scripts/ai/` | flujo recomendado para worktrees/validacion desde Codex | tareas de agentes, bootstrap, validaciones |
| `src/scripts/ci/` | automatizaciones de PR docs y lint | si falla CI o hay autoformato |
| `docker/` | runtime contenedorizado real y compose de deploy | bugs de arranque/deploy |
| `src/backends/kernel/templates/components/` | primitives HTML reutilizables | cambios de UI server-side compartidos |
| `src/backends/kernel/static/custom/js/` | JS compartido entre verticales | bugs front puntuales en templates |
| `src/backends/<x>/<app>/static/custom/` | JS/CSS de un solo vertical (misma ruta publica `custom/...`) | bugs front de ese vertical |
| `src/backends/kernel/tests/` | tests transversales del proyecto | caracterizacion y regresiones |
| `src/backends/<vertical>/tests/` | tests de un vertical | cambios en ese vertical |
| `docs/api/postman/` | coleccion y entorno API | contratos API/manual testing |

## Puntos de entrada del sistema

### Backend web/API

- `manage.py`
- `src/backends/config/settings.py`
- `src/backends/config/urls.py`
- `docker/django/entrypoint.py`

### Rutas HTTP centrales

- Auth/UI base: `src/backends/config/urls.py`
- APIs:
  - `api/users/`
  - `api/comedores/`
  - `api/centrodefamilia/`
  - `api/vat/`
  - `api/comunicados/`
  - `api/renaper/`
  - `api/pwa/`
  - `api/ticketera/`
- Docs OpenAPI:
  - `/api/schema/`
  - `/api/docs/`
  - `/api/redoc/`

### Jobs / workers / asincronia

### Hechos observados

- PAS usa Celery/Redis mediante `docker/compose/docker-compose.celery.yml`; mantiene un solo
  lote activo global y paralelismo acotado dentro del lote.
- El resto de la asincronia sigue siendo "simple":
  - hilos / `ThreadPoolExecutor` en syncs (`src/backends/sisoc_core/comedores/tasks.py`, `src/backends/sisoc_core/relevamientos/tasks.py`);
  - workers dedicados por `DJANGO_SERVICE_ROLE` en `docker/django/entrypoint.py`.

### Roles de contenedor detectados

- `web`
- `bulk_credentials_worker`
- `ciudadanos_import_worker`
- `mailing_worker`
- `user_import_worker`
- `ocr_worker`
- `encuestas_worker`: abre/cierra rondas de encuestas por fecha (ver `src/backends/sisoc_core/encuestas/services.py:run_encuestas_scheduler`, sin Celery).
- Los loops persistentes llaman `close_old_connections()` por ciclo. Ciudadanos y usuarios reclaman lotes con `lease_token`; los lotes inactivos vuelven a pendiente y un worker anterior no debe confirmar filas. Con otros pendientes, ambos importadores ceden el worker por tramos configurables de treinta minutos y el reclamo prioriza al lote que lleva más tiempo esperando.

## Configuracion y variables de entorno relevantes

### Archivos

- `.env.example`: base local canonicamente documentada.
- No hay `.env` por entorno versionados: cada servidor usa su `.env` local creado desde `.env.example`.
- `docker-compose.yml`: local.
- `docker/compose/docker-compose.deploy.yml`, `docker/compose/docker-compose.produccion.yml`: deploy.

### Variables clave

| Grupo | Variables importantes |
| --- | --- |
| Entorno Django | `DJANGO_DEBUG`, `ENVIRONMENT`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` |
| DB | `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME`, `WAIT_FOR_DB`, `DB_CONN_MAX_AGE` |
| Docker/puertos | `DOCKER_MYSQL_PORT_FORWARD`, `DOCKER_DJANGO_PORT_FORWARD`, `DOCKER_DEBUGGER_PORT_FORWARD`, `RUN_UID`, `RUN_GID` |
| Runtime | `RUN_MAKEMIGRATIONS_ON_START`, `GUNICORN_WORKERS`, `GUNICORN_THREADS` |
| Seguridad/CSP | `ENABLE_CSP`, `CSP_REPORT_ONLY`, `CSP_ALLOW_UNSAFE_INLINE_SCRIPTS`, `CSP_ALLOW_UNSAFE_EVAL` |
| Async | `DISABLE_ASYNC_THREADS`, `CELERY_BROKER_URL`, `PAS_MONTHLY_ENABLED`, `PAS_BATCH_SIZE`, `PAS_BATCH_SECONDS`, `PAS_REQUESTS_PER_SECOND`, `PAS_CONCURRENCY`, `PAS_CIRCUIT_BREAKER_TIMEOUTS` |
| Testing | `USE_SQLITE_FOR_TESTS`, `PYTEST_RUNNING` |
| Integracion GESTIONAR | `GESTIONAR_INTEGRATION_ENABLED` (corte total de envíos, pulls y comandos), `GESTIONAR_API_KEY`, endpoints `GESTIONAR_API_*`, workers `GESTIONAR_*`, `DOMINIO` |
| Ticketera | `TICKETERA_ENABLED` |
| RENAPER/importaciones | `RENAPER_API_USERNAME`, `RENAPER_API_PASSWORD`, `RENAPER_REQUEST_TIMEOUT_SECONDS`, `RENAPER_MAX_CONSULTAS_POR_SEGUNDO` (30 por defecto, global mediante `src/backends/kernel/core/integrations/renaper_rate_limit.py` y `core.0009`); ciudadanos usa `CIUDADANOS_IMPORT_RENAPER_PARALLELISM` (2 hilos por réplica por defecto) y reutiliza token por hilo/lote; los tramos de cola usan `CIUDADANOS_IMPORT_JOB_SLICE_SECONDS` y `USER_IMPORT_JOB_SLICE_SECONDS` |
| Google Maps | `GOOGLE_MAPS_API_KEY` |
| Sentry | `SENTRY_ENABLED`, `SENTRY_DSN`, `SENTRY_RELEASE` |
| Email/password reset | `EMAIL_*`, `DEFAULT_FROM_EMAIL`, `PASSWORD_RESET_TIMEOUT`, `INITIAL_PASSWORD_MAX_AGE_HOURS` |
| Web push PWA | `PWA_WEB_PUSH_PUBLIC_KEY`, `PWA_WEB_PUSH_PRIVATE_KEY`, `PWA_WEB_PUSH_SUBJECT` |

### Precauciones

- No tocar `.env*` salvo pedido explicito.
- No asumir que `ENVIRONMENT=dev` representa PRD-like behavior: hay toggles importantes para QA/PRD.
- `RUN_MAKEMIGRATIONS_ON_START=true` en dev puede enmascarar drift de migraciones si nadie mira el diff.

## Mapa de carpetas y capas por responsabilidad

### Configuracion global

| Ruta | Responsabilidad |
| --- | --- |
| `src/backends/config/settings.py` | settings, apps instaladas, middleware, DB, cache, DRF, Sentry, logging, CSP, modo debug/prod |
| `src/backends/config/urls.py` | router global del monolito |
| `src/backends/config/middlewares/` | middleware propio como XSS/threadlocals |
| `src/backends/config/views.py` | views globales, errores y schema VAT |

### Capa compartida

| Ruta | Responsabilidad |
| --- | --- |
| `src/backends/kernel/core/` | utilidades transversales, fixtures, soft delete, API auxiliar, paginacion, benchmark/debug tooling |
| `src/backends/kernel/users/` | auth, login/reset, perfiles, grupos, import masivo de usuarios, permisos PWA |
| `src/backends/kernel/audittrail/` | auditoria propia del sistema |
| `src/backends/kernel/healthcheck/` | endpoint de salud |

### Presentacion/UI compartida

| Ruta | Responsabilidad |
| --- | --- |
| `src/backends/kernel/templates/includes/` | layout base, navbar, sidebar, scripts globales |
| `src/backends/kernel/templates/components/` | componentes HTML reutilizables |
| `src/backends/kernel/static/custom/js/` y `<app>/static/custom/js/` | JS por pantalla/flujo; bastante legacy y acoplado a templates |
| `src/backends/kernel/static/custom/css/` y `<app>/static/custom/css/` | estilos propios |

### Operacion

| Ruta | Responsabilidad |
| --- | --- |
| `docker/` | runtime contenedorizado |
| `src/scripts/operacion/` | refresh/deploy operativo |
| `src/scripts/ci/` | utilidades de CI |
| `src/scripts/ai/` | bootstrap/worktrees/doctor/validate/context memory |

### Tests y calidad

| Ruta | Responsabilidad |
| --- | --- |
| `src/backends/kernel/tests/` | suite transversal, smoke, contratos API, seguridad, componentes |
| `src/backends/<vertical>/tests/` | tests de cada vertical (incluye PWA y Comedores en `sisoc_core/tests/`) |
| `*/tests/` | tests cercanos al modulo |
| `.github/workflows/` | contratos CI reales |
| `.importlinter` | boundaries arquitectonicos parciales |

## Mapa de dominios / apps

La siguiente tabla mezcla hechos observados con inferencias explicitas cuando no lei el modulo a fondo.

| App | Rol practico | Piezas a mirar primero | Estado de confirmacion |
| --- | --- | --- | --- |
| `src/backends/kernel/users/` | autenticacion, perfiles, grupos, login/reset, import y credenciales masivas | `models.py`, `views.py`, `api_views.py`, `management/commands/`, `services_*` | Alto |
| `src/backends/kernel/core/` | utilidades transversales, helpers, soft delete, filtros/paginacion, comandos compartidos | `views.py`, `services/`, `management/commands/`, `utils.py` | Alto |
| `src/backends/sisoc_core/dashboard/` | tableros internos | `urls.py`, `views.py`, templates | Medio |
| `src/backends/sisoc_core/comedores/` | dominio fuerte: comedores, nomina, estados, sync GESTIONAR y API territorial PWA | `models.py`, `api_views.py`, `api_views_territorial.py`, `tasks.py`, `signals.py`, `services/`, `urls.py` | Alto |
| `src/backends/sisoc_core/relevamientos/` | relevamientos y sync externo asociado | `models.py`, `tasks.py`, `views.py`, commands | Alto |
| `src/backends/kernel/ciudadanos/` | gestion de ciudadanos/beneficiarios | `models.py`, `views.py`, `api_views.py`, forms | Medio |
| `src/backends/cdf/centrodefamilia/` | backend propio (`/centrodefamilia/`); beneficiarios/centros/familia + API | `models.py`, `views.py`, `api_views.py`, `services/` | Alto |
| `src/backends/celiaquia/celiaquia/` | modulo especializado con bastante logica en services y vistas; expone un contrato Python acotado | `api.py`, `models.py`, `views/`, `services/`, `permissions.py`, tests | Alto |
| `src/backends/sisoc_core/admisiones/` | flujo de admision, legales/tecnicos, generacion DOCX/PDF y correcciones operativas auditadas | `views/web_views.py`, `services/`, `forms/`, `management/commands/`, templates `docx/` y `pdf/` | Alto |
| `src/backends/vat/VAT/` | modulo amplio propio con views, API, services y reportes | `models.py`, `views/`, `api_views.py`, `services/`, `serializers.py`; docs `docs/vat/` | Alto |
| `src/backends/sisoc_core/pwa/` | endpoints backend para experiencia PWA | `api_urls.py`, `api_views.py`, `services/`, `models.py` | Medio |
| `src/backends/cdi/ticketera/` | corre en el backend de CDI; API server-to-server con kill-switch | `api_urls.py`, `api_views.py`, `api_serializers.py` | Medio |
| `src/backends/sisoc_core/comunicados/` | mensajes/comunicados y API asociada | `models.py`, `views.py`, `api_views.py`, forms | Medio |
| `src/backends/kernel/organizaciones/` + `src/backends/sisoc_core/gestion_organizaciones/` | datos maestros en el kernel; pantallas, forms y `Firmante` en el core (`gestion_organizaciones`). Entidades/organizaciones vinculadas; edición modal de proyectos y detalle con rendiciones por relación directa o legado | `models.py`, `forms.py`, `views.py`, templates de organización | Alto |
| `src/backends/cdi/centrodeinfancia/` | backend propio (`/centrodeinfancia/`, `/simepi/`); dominio de centros de infancia, personal, asistencia y descargables provinciales | `models.py`, `services.py`, `services_nomina_ninos_pdf.py`, `views.py`, `tests/`, urls | Alto |
| `src/backends/sisoc_core/acompanamientos/` | seguimiento/acompanamientos | `views.py`, `acompanamiento_service.py`, `services/filter_config.py`, templates | Medio |
| `src/backends/sisoc_core/expedientespagos/` | expedientes de pagos | `models.py`, `views.py`, urls | Bajo |
| `src/backends/sisoc_core/rendicioncuentasfinal/` | rendicion final | `models.py`, `views.py`, urls | Bajo |
| `src/backends/sisoc_core/rendicioncuentasmensual/` | rendición mensual, revisión Territorial/Auditoría, subsanaciones y datos expuestos en Organizaciones | `models.py`, `services.py`, `views.py`, templates, urls | Alto |
| `src/backends/sisoc_core/duplas/` | equipos tecnicos/duplas | `models.py`, `views.py` | Bajo-Medio |
| `src/backends/dispositivos/dispositivos/` | dominio de dispositivos | `models.py`, `views.py`, tests | Bajo |
| `src/backends/sisoc_core/importarexpediente/` | flujo de importacion de expedientes | `views.py`, `models.py`, urls, tests | Medio |
| `src/backends/sisoc_core/ocr/` | OCR y procesamiento asociado | `models.py`, `views.py`, urls, tests | Medio |
| `src/backends/vpsl/ver_para_ser_libre/` | dominio VPSL compartido por SISOC y el servicio HTTP React; desde PR #2566 el itinerario evalua cartas sin sedes tentativas, cada jornada posee sede/localidad/ubicacion/vehiculos y checklist con habilitacion automatica, y el registro nominal guarda graduaciones; las sedes previas permanecen para historial; la compatibilidad del PR #2566 conserva localidad historica, copia checklists y permite editar registros previos sin inventar graduacion; `api_views.py`, `api_workflow.py`, `api_inputs.py`, `api_requests.py` y `services/access.py` exponen el flujo React con permisos, contrato JSON/multipart y alcance provincial | `models.py`, `forms.py`, `views.py`, `api_urls.py`, `api_views.py`, `api_workflow.py`, `api_inputs.py`, `api_requests.py`, `services/access.py`, `services/workflow.py`, `services/map_location.py`, `migrations/0015_vpsl_ubicacion_vehiculos_graduaciones.py`, `migrations/0016_copiar_checklist_sede_a_jornadas.py`, `src/backends/vpsl/ver_para_ser_libre/tests/test_api.py`, `src/backends/vpsl/ver_para_ser_libre/tests/test_api_contract.py`, `src/backends/vpsl/ver_para_ser_libre/tests/test_jornada_location.py` | Alto |
| `src/backends/pas/pas/` | núcleo del Programa de Acompañamiento Social, circuito DDJJ —padrón, tokens, formulario público, PDF e importación CSV—, Informes PAS versionados, circuito mensual de cruces SINTyS/RENAPER, Panel de Control y Formación pendiente; el padrón lateral de Formación pagina por scroll mediante `/pas/formacion/personas` | `models.py`, `api.py`, `views.py`, `services/ddjj_service.py`, `services/titulares_import_service.py`, `services/informe_service.py`, `services/cruces_service.py`, `services/supervivencia_service.py`, `services/persona_service.py`, `services/formacion_service.py`, `src/backends/pas/pas/templates/pas/`, `src/backends/pas/pas/static/custom/js/pas_formacion.js`, `management/commands/`, `urls.py`, `migrations/` | Alto |
| `src/backends/kernel/audittrail/` | auditoria interna | `models.py`, `views.py`, `services/query_service` | Alto |
| `src/backends/sisoc_core/historial/` | historial de dominio | `models.py`, `services/` | Bajo |
| `src/backends/sisoc_core/intervenciones/` | intervenciones sobre casos | tests + archivos del modulo | Bajo; exploracion parcial |
| `src/backends/kernel/catalogo_intervenciones/` | catálogos de intervención compartidos por Comedores y CDI (tablas `intervenciones_*`) | `models.py`, `api.py`, `services_catalogo.py`, `fixtures/` | Medio |
| `src/backends/kernel/sentry/` | soporte/integracion local de sentry | codigo del modulo si toca observabilidad | Bajo |
| `src/backends/sisoc_core/encuestas/` | encuestas periodicas a usuarios logueados: preguntas con logica condicional, segmentacion, rondas recurrentes, bloqueo global si son obligatorias, resultados y export | `models.py`, `services.py`, `services_resultados.py`, `middleware.py`, `context_processors.py`, `management/commands/process_encuestas_rondas.py`, `tests/` | Alto (modulo propio, doc completa en `docs/registro/analisis/2026-08-28-modulo-encuestas.md`) |

## Patrones arquitectonicos y de codigo

### Hechos observados

- Monorepo Django por apps funcionales, desplegado como servicios por vertical.
- Coexisten:
  - views Django server-rendered;
  - DRF para APIs;
  - templates globales y por app;
  - JS por pantalla en `src/backends/kernel/static/custom/js` o `<app>/static/custom/js`;
  - servicios por modulo cuando hubo refactor/hardening.
- El repo intenta llevar la logica de negocio a `services/`, pero no es uniforme.
- Se usan management commands como extension operativa importante.
- Se usan signals para side effects de negocio.
- La arquitectura actual tiene boundaries monitoreados por `import-linter`, con baseline de excepciones a reducir por cortes. Los filtros favoritos se aportan desde cada app mediante `core.services.favorite_filters.registry`; `core` no debe volver a importar configuraciones de dominio para resolverlos.
- Los paneles de Ciudadano 360 se aportan por dominio mediante `ciudadanos.detail_contributions`; las vistas de ciudadanos no deben consultar modelos de esos dominios directamente.
- Las consultas RENAPER pasan por `core.services.renaper`, que delega el transporte compartido a `core.integrations.renaper`; ningún dominio debe tener su propio cliente ni importar otro dominio para consultarlo.
- Comedores Core es un bounded context lógico: Comedores, Admisiones, Relevamientos, Organizaciones, Dúplas, Expedientes, Rendiciones, Intervenciones y Acompañamientos conservan sus ciclos internos; Dashboard consume sus métricas mediante `comedores.api` y `relevamientos.api`.
- Los receivers de auditoría de Comedores Core se registran desde sus dominios y usan `audittrail.api`; Audittrail no debe recuperar imports de esos modelos.
- Los módulos externos sólo consumen `*.api` de Comedores Core. La FK histórica `centrodefamilia.Centro.organizacion_asociada` es la única excepción declarada hasta que se trate su migración y semántica de borrado.
- Los consumidores interdominio usan contratos Python acotados: `centrodefamilia.api` expone métricas para Dashboard, `ciudadanos.api` resuelve ciudadanos desde RENAPER y `catalogo_intervenciones.api` provee el catálogo autorizado para CDI.
- Los receivers de auditoría de Centro de Infancia viven en `centrodeinfancia.signals` y llaman `audittrail.api`; Audittrail no debe importar modelos CDI.
- Los alcances de usuarios propios de un dominio se registran mediante `iam.services.register_user_queryset_scope`; Centro de Infancia registra el suyo desde `centrodeinfancia.apps` para que `users` no importe dominios.
- Dispositivos, VAT y Ver para Ser Libre no exponen internals a otros dominios. La composición de rutas de preview de VAT se realiza desde `VAT.global_urls`.
- Los efectos de backfill de soft delete se registran desde cada dominio en `core.soft_delete.registry`; `core.soft_delete.state_sync` no debe importar handlers de dominio.
- Las restricciones de navegacion aportadas por dominios se registran en `core.services.sidebar_access`; el template tag global no debe importar reglas VAT.
- El endpoint Select2 de organizaciones vive en `gestion_organizaciones.views` y `gestion_organizaciones.urls`, aunque conserva la ruta global `ajax/load-organizaciones/`.
- Los post-procesos de dominio de `load_fixtures` se registran en `core.services.fixture_post_load`; el comando de `core` no debe importar sus servicios directamente.
- La auditoria de autenticacion se solicita desde `users.auth_audit`; PWA registra el persistidor de `AuditoriaSesionPWA` durante su arranque.
- La sincronizacion entre `Profile.duplas_asignadas` y `Dupla.coordinador` se suscribe desde `duplas.signals`; `users` no debe conocer el modelo Dupla.
- Las restricciones PWA por programa de Comedores se consultan mediante `users.pwa_comedores`; Comedores registra la capacidad concreta durante su arranque.
- Las pruebas de alcance territorial que ejercitan `Ciudadano` viven en `src/backends/kernel/ciudadanos/test_territorial_scope.py`; el módulo heredado de regresiones de Users vive en `src/backends/kernel/tests/test_users_regressions.py` para no abrir imports de dominio dentro de la app.
- Los querysets de dominio requeridos por formularios administrativos de Users se registran en `users.form_catalogs`; `users.forms` no debe importar modelos de Comedores, Duplas ni Organizaciones.
- La expansión de organizaciones y comedores del importador PWA se resuelve mediante `users.pwa_import_access`; Comedores registra el proveedor y `users.services_user_import` sólo consume IDs y especificaciones de acceso.
- `users.api` es la fachada pública de la proyección PWA por organización. `comedores.signals` y `sincronizar_accesos_pwa_organizaciones` sólo le pasan IDs; `AccesoOrganizacionPWA` es la fuente de verdad y `AccesoComedorPWA` la proyección. El save/soft-delete/restore de `Comedor` es transaccional para estos side effects y los envíos a GESTIONAR quedan en `on_commit`.

### Convenciones visibles

- Python: `snake_case`.
- Black line-length 88.
- Templates formateados con `djlint`.
- Commits sugeridos con Conventional Commits.
- En varias apps modernas los servicios usan estructura `services/<subservicio>/impl.py`.
- En otras apps legacy todavia existe `views.py` unico o `models.py` monolitico.

### Implicancia practica

- Antes de meter logica en una view, revisar si esa app ya tiene `services/`.
- Antes de crear otro helper global, revisar `src/backends/kernel/core/`.
- Antes de agregar un import cross-app, revisar `.importlinter`: quizas estas rompiendo un boundary aunque el codigo "funcione".

## Donde buscar segun el tipo de cambio

### Si necesitas cambiar autenticacion / login / reset / grupos

- `src/backends/sisoc_core/usuarios/views.py`
- `src/backends/sisoc_core/usuarios/forms.py`
- `src/backends/kernel/users/models.py`
- `src/backends/sisoc_core/usuarios/api_views.py`
- `src/backends/kernel/users/bootstrap/groups_seed.py`
- `src/backends/kernel/users/management/commands/create_groups.py`
- templates en `src/backends/kernel/users/templates/`
- En el ABM de usuarios, `es_representante_pwa` es el interruptor general de
  acceso mobile, incluido el coordinador PWA. `Profile.configuracion_mobile`
  conserva las selecciones al suspender el acceso; no otorga permisos.
  La migración es `users.0050` y la visibilidad vive en
  `src/backends/sisoc_core/usuarios/static/custom/js/user_mobile_access.js`. Validar con
  `src/backends/sisoc_core/tests/test_users_pwa_forms.py` y `node src/backends/sisoc_core/tests/js/user_mobile_access.test.js`.
- Las secciones del ABM de usuarios que no son generales (Mobile Comedores,
  Territorial comedor, Equipos técnicos, DataCalle, Administración de accesos)
  se habilitan por permiso `auth.role_usuarios_seccion_*`: catálogo en
  `src/backends/kernel/users/secciones_usuario.py`, campos en `CAMPOS_POR_SECCION` de
  `src/backends/sisoc_core/usuarios/forms.py`. Una sección nueva de un programa se agrega ahí, con su
  permiso en el seed. Decisión:
  `docs/registro/decisiones/2026-09-29-usuarios-secciones-por-permiso.md`.
- La autogestión vive en `MiCuentaForm`, `MiCuentaView` y la ruta `/mi-cuenta/`.
  La confirmación inicial usa `/mi-cuenta/confirmar/` y
  `ProfileConfirmationMiddleware`, registrado después del cambio de contraseña.
  El middleware solo bloquea web: `/api/` está exento; al tocar ese flujo, revisar
  `src/backends/kernel/users/profile_utils.py`, las migraciones `0044`/`0045` y
  `src/backends/sisoc_core/tests/test_users_mi_cuenta.py`.

### Si necesitas cambiar la importacion masiva de usuarios

- `src/backends/sisoc_core/usuarios/services_user_import.py`: parsing, alta/actualizacion, mail de
  credenciales y exportacion CSV.
- El alta canónica de `SIMEPI - EGP` es `users.UserCreationForm` en
  `/usuarios/crear/`; admite uno o más scopes provinciales completos. La URL
  histórica `/simepi/egp/generar-usuario/` sólo redirige por compatibilidad.
- `src/backends/sisoc_core/usuarios/services_user_import_jobs.py`: procesamiento y reanudacion del lote.
- Los checkpoints de usuario y progreso se confirman en una transacción por fila. `users.0053` agrega el identificador de propiedad del lote.
- `src/backends/sisoc_core/usuarios/views_user_import.py`, `src/backends/sisoc_core/usuarios/urls.py` y
  `src/backends/sisoc_core/usuarios/templates/user/user_import_job_detail.html`: detalle y descargas.
- Las credenciales se agrupan al finalizar el lote; los lotes PWA deben usar
  `/mobile/login` y las descargas sensibles se limitan al solicitante o a un
  superusuario.

### Si necesitas cambiar el import/export Excel-CSV del Django admin

- `src/backends/kernel/core/admin_import_export.py`: bases `BaseImportExportAdmin` (import +
  export) y `BaseExportAdmin` (solo export), con formatos limitados a XLSX/CSV.
- `<app>/resources.py`: resources explicitos cuando hay que acotar campos o
  resolver relaciones por nombre (`core`, `intervenciones`).
- `src/backends/config/settings.py`: bloque `IMPORT_EXPORT_*` (transacciones, preview
  obligatorio, permisos requeridos, escape de formulas).
- `src/backends/sisoc_core/tests/test_admin_import_export.py`.
- docs: `docs/registro/cambios/2026-T3/2026-07-27-import-export-admin.md` lista que
  modelo quedo habilitado y cual no, con motivo.

### Si necesitas cambiar permisos o IAM

- `src/backends/kernel/users/bootstrap/groups_seed.py`
- `src/backends/kernel/users/services_group_permissions.py`
- `src/backends/sisoc_core/usuarios/api_permissions.py`
- permisos especificos por app, por ejemplo `src/backends/celiaquia/celiaquia/permissions.py`
- docs: `docs/implementaciones/usuarios_perfil_iam.md`

### Si necesitas cambiar navegacion global, layout o sidebar

- `src/backends/kernel/templates/includes/`
- `src/backends/kernel/templates/includes/sidebar/`
- `src/backends/kernel/templates/components/`
- `src/backends/kernel/static/custom/js/sidebar.js`

### Si necesitas cambiar endpoints API

- router global: `src/backends/config/urls.py`
- por app: `api_urls.py`, `api_views.py`, `api_serializers.py`, `serializers.py`
- si es PWA: `src/backends/sisoc_core/pwa/api_urls.py`, `src/backends/sisoc_core/pwa/api_views.py`
- si es Ticketera: `src/backends/cdi/ticketera/api_*`

### Si necesitas cambiar una pantalla HTML tradicional

1. Buscar la `view`/`urls.py` de la app.
2. Abrir el template principal en `src/backends/kernel/templates/` o `app/templates/`.
3. Buscar el JS asociado en `<app>/static/custom/js/` o en `src/backends/kernel/static/custom/js/`.
4. Revisar parciales en `src/backends/kernel/templates/components/` o `app/templates/.../partials/`.

### Si necesitas cambiar negocio de Comedores

- `src/backends/sisoc_core/comedores/models.py`
- `src/backends/sisoc_core/comedores/tasks.py`
- `src/backends/sisoc_core/comedores/signals.py`
- `src/backends/sisoc_core/comedores/services/`
- `src/backends/sisoc_core/comedores/api_views.py`
- `src/backends/sisoc_core/comedores/api_views_territorial.py` (scope provincial PWA, altas idempotentes y edición)
- `src/backends/sisoc_core/comedores/api_serializers.py::TerritorialComedorWriteSerializer` (validacion de
  altas/ediciones territoriales, catalogos y jerarquia geografica)
- tests `src/backends/sisoc_core/tests/test_comedor*`, `src/backends/sisoc_core/tests/test_comedores*`
- docs de flujo: `docs/flujos/comedor_sync.md`
- certificaciones mensuales de prestaciones: regla de pendiente en
  `src/backends/sisoc_core/comedores/utils.py`, API en `src/backends/sisoc_core/comedores/api_views.py`, card e historial web en
  `src/backends/sisoc_core/comedores/views/comedor.py` y `src/backends/sisoc_core/comedores/templates/comedor/`

### Si necesitas cambiar Relevamientos

- `src/backends/sisoc_core/relevamientos/models.py`
- `src/backends/sisoc_core/relevamientos/service.py` (asignación territorial local/legacy)
- `src/backends/sisoc_core/relevamientos/tasks.py`
- `src/backends/sisoc_core/relevamientos/views/web_views.py`
- `src/backends/sisoc_core/tests/test_relevamientos*` y `src/backends/sisoc_core/tests/test_territorial_api.py`
- docs: `docs/flujos/relevamiento_sync.md`

### Si necesitas cambiar importacion de expedientes de pago

- `src/backends/sisoc_core/importarexpediente/views.py` coordina upload, validacion, importacion y acciones posteriores por lote.
- `src/backends/sisoc_core/importarexpediente/services.py` concentra parsing y reglas de negocio del Excel/CSV.
- `src/backends/sisoc_core/importarexpediente/tests/` cubre el flujo de carga, detalle, descarga, duplicados, estados y fechas de acreditacion.
- Las fechas de acreditacion masivas se actualizan por lote mediante `RegistroImportado`; no buscar `ExpedientePago` globalmente por `comedor_id`.
- El endpoint de fechas de acreditacion requiere `importarexpediente.change_archivosimportados` o `expedientespagos.change_expedientepago`.

### Si necesitas cambiar Celiaquia

- `src/backends/celiaquia/celiaquia/api.py` para el contrato Python público; consumidores externos no
  deben importar sus modelos, services, views, formularios, permisos o signals.
- `src/backends/celiaquia/celiaquia/global_urls.py` para rutas globales de propiedad del dominio.
- API REST del front v2 (`/api/celiaquia/`): `api_views.py`, `api_serializers.py`, `api_urls.py`;
  el permiso de módulo vive en `api_permissions.py` y el alcance por rol en `scope.py`. Al tocar un
  serializer, regenerar `src/frontends/packages/api/openapi.celiaquia.yaml` (`spectacular --urlconf
  config.urls_frontend_v2`) y `npm run api:types`; CI (`frontend-v2.yml`) falla si quedan viejos.
- `src/backends/celiaquia/celiaquia/views/`
- `src/backends/celiaquia/celiaquia/services/`
- `src/backends/celiaquia/celiaquia/models.py`
- `src/backends/celiaquia/celiaquia/permissions.py`
- `src/backends/celiaquia/celiaquia/tests/`
- doc especifica de DB en `docs/contexto/documentacion_base_datos_celiaquia.md`

### Si necesitas cambiar Admisiones / documentos

- `src/backends/sisoc_core/admisiones/views/web_views.py`
- `src/backends/sisoc_core/admisiones/services/`
- `src/backends/sisoc_core/admisiones/forms/`
- `src/backends/sisoc_core/admisiones/management/commands/corregir_expedientes_issue_2272.py`: preflight, aplicación transaccional y verificación de la corrección de expedientes de #2272; ejecutar --apply sólo tras un preflight correcto, en ventana sin escrituras, y confirmar con --verify.
- templates `src/backends/sisoc_core/admisiones/templates/admisiones/docx/`
- templates `src/backends/sisoc_core/admisiones/templates/admisiones/pdf/`
- `src/backends/sisoc_core/admisiones/tests/`
- El catálogo de variables de contenido se persiste como
  `VariableTemplateInformeTecnico`; guarda expresiones Django sin delimitadores
  (por ejemplo, `informe.nombre_organizacion`). Sólo las variables activas se
  pueden publicar. La migración `0073` precarga las 106 expresiones de los
  cuatro modelos DOCX vigentes y `0074` agrega los alias planos compatibles
  con el primer editor del Gestor.
- Templates dinámicos de Informe Técnico: condiciones, versiones y publicaciones
  en `src/backends/sisoc_core/admisiones/models/admisiones.py`; servicio en
  `src/backends/sisoc_core/admisiones/services/templates_informe_tecnico_service/`; UI de gestión en
  `src/backends/sisoc_core/admisiones/views/templates_informe_tecnico.py` y
  `src/backends/sisoc_core/admisiones/templates/admisiones/templates_informes_tecnicos/`. La UI se
  agrupa visualmente bajo Gestor de templates mediante el parcial
  `includes/navigation.html` y los estilos aislados
  `src/backends/sisoc_core/admisiones/static/custom/css/gestor_templates.css`; el sidebar anida Templates,
  Variables documentales e Incidencias de templates. Las incidencias se
  agrupan por combinación abierta; las vistas previas son DOCX temporales con
  marca de agua y nunca se adjuntan a la admisión. Al crear un template, el
  tipo de convenio se limita al catálogo de Personerías o Organización Base,
  presentada funcionalmente como Asociación de hecho.
- La descarga del Informe Técnico ofrece una copia transitoria "Descargar para
  GDE": prioriza el DOCX editado y, si no existe, el borrador. Se normaliza la
  geometría OOXML de sus tablas antes de responder, sin reemplazar archivos ni
  modificar estados.
- El Informe Tecnico Complementario se abre tanto desde Admision como desde el
  convenio seleccionado en `src/backends/sisoc_core/acompanamientos/views.py` y
  `src/backends/sisoc_core/acompanamientos/templates/acompañamiento_detail.html`.
- Documentación canónica: `docs/implementaciones/admisiones_informes_tecnicos.md`.

### Si necesitas cambiar PWA

- La interfaz vive en el repositorio Git anidado `mobile/`; revisar su estado y
  validaciones por separado del repositorio Django.
- `src/backends/sisoc_core/pwa/models.py`
- `src/backends/sisoc_core/pwa/api_urls.py`
- `src/backends/sisoc_core/pwa/api_views.py`
- `src/backends/sisoc_core/pwa/services/accesos.py`: alcance PWA, accesos y coordinador de equipo técnico PWA.
- `src/backends/sisoc_core/usuarios/api_permissions.py`: permisos de lectura y veto transversal de escritura
  para roles PWA de solo lectura.
- Toda mutación PWA debe incluir `IsPWAWriteAllowed`, excepto las acciones
  personales expresamente permitidas (contraseña y suscripciones push).
- `src/backends/sisoc_core/pwa/services/`
- alcance de nómina por admisión vigente o comedor directo:
  `src/backends/sisoc_core/pwa/services/nomina_queryset_service.py`
- frontend: `mobile/src/api/` y `mobile/src/features/home/`
- tests `src/backends/sisoc_core/tests/test_pwa_*`
- docs: `docs/implementaciones/pwa_backend.md`,
  `docs/implementaciones/comedores_certificaciones_prestaciones.md`,
  `docs/seguridad/security_baseline_pwa.md`

### Si necesitas cambiar documentos DOCX/PDF de prestaciones o nóminas

- plantillas versionadas: `src/backends/sisoc_core/pwa/files/varios/PROGRAMA.ALIMENTAR.COMUNIDAD.docx` y `src/backends/sisoc_core/pwa/files/varios/NOMINA.DE.DESTINATARIOS.docx`
- certificación de prestaciones: `src/backends/sisoc_core/comedores/services/certificacion_prestaciones_service.py`
- nómina de destinatarios: `src/backends/sisoc_core/pwa/services/nomina_destinatarios_pdf_service.py`
- descarga provincial de niños SIMEPI: endpoint
  `centrodeinfancia_nomina_ninos_pdf`, servicio
  `src/backends/cdi/centrodeinfancia/services_nomina_ninos_pdf.py` y pruebas
  `src/backends/cdi/centrodeinfancia/tests/test_nomina_ninos_pdf.py`; exige grupo `SIMEPI - EGP`
  y selección explícita de una provincia dentro de uno o más alcances completos,
  excluye fichas mayores de 48 meses y entrega un JPEG por página
- contrato canónico de esa descarga, privacidad y formularios CDI:
  `docs/implementaciones/centrodeinfancia_nomina_ninos_simepi.md`
- conversión e incrustación de Office en rendiciones: `src/backends/sisoc_core/rendicioncuentasmensual/service_helpers.py`
- el runtime Django requiere LibreOffice Writer/Calc para convertir DOCX/XLSX a PDF

### Si necesitas cambiar rendiciones mensuales u Organizaciones

- estados, etapas, subsanaciones y alcance por proyecto: `src/backends/sisoc_core/rendicioncuentasmensual/services.py`
- regla única de datos generales (convenio, número secuencial, período): `RendicionCuentaMensualService.validar_datos_generales`; la usan el formulario web, el alta y la edición de la PWA. No duplicarla
- el número de rendición es secuencial por proyecto + convenio y se serializa con `select_for_update()`: cualquier camino de escritura nuevo tiene que correr dentro de `transaction.atomic` o el bloqueo no protege nada
- la ventana del período depende de la línea programática: 3 meses en `secos`, 1 mes en el resto (`periodo_fin_maximo`)
- solicitudes de documentos faltantes y categorías documentales: `src/backends/sisoc_core/rendicioncuentasmensual/models.py`; el catálogo depende de la línea (`CATEGORIAS_CONFIG["lineas"]`) y web y API lo resuelven con `RendicionCuentaMensualService.obtener_categorias_visibles`; el contrato PWA se serializa en `src/backends/sisoc_core/comedores/api_serializers.py`
- confirmación de lectura de documentos: campos `visualizacion_*` en `DocumentacionAdjunta` y vista `RendicionDocumentoVerView`; los documentos se sirven por Django, no por la URL de media
- etiquetas visibles ≠ valores persistidos: la etapa `revision_auditoria` se muestra como «Revisión para Carga». No cambiar valores internos para acomodar un label
- asociación actual: `RendicionCuentaMensual.proyecto`; conservar fallback por `comedor.codigo_de_proyecto` para datos legados
- listado y detalle del legajo: `src/backends/sisoc_core/gestion_organizaciones/views.py` y templates `organizacion_*`
- proyectos editables: `OrganizacionForm.codigos_proyecto` mantiene el contrato CSV mediante un campo oculto
- tests: `src/backends/sisoc_core/tests/test_rendicioncuentasmensual_services_unit.py`, `src/backends/sisoc_core/tests/test_rendicioncuentasmensual_domain_rules.py`, `src/backends/sisoc_core/tests/test_rendicioncuentasmensual_visualizacion.py`, `src/backends/sisoc_core/tests/test_rendicioncuentasmensual_acta_auditoria.py` y `src/backends/sisoc_core/gestion_organizaciones/tests.py`
- escenarios QA de permisos por etapa: `python manage.py seed_rendicion_stage_examples --comedor-id <id>` (solicita la contraseña de forma interactiva)
- documentación canónica: `docs/flujos/rendiciones_mensuales_proyectos.md`
- contratos que consume la PWA (estados internos, health-check, edición de datos generales): `docs/implementaciones/pwa_backend.md`

### Si necesitas cambiar altas de ciudadanos en nómina

- `src/backends/sisoc_core/comedores/forms/comedor_form.py`, `src/backends/sisoc_core/comedores/views/nomina.py` y
  `src/backends/sisoc_core/comedores/services/comedor_service/impl.py`
- `src/backends/sisoc_core/tests/test_comedor_form_unit.py` y `src/backends/sisoc_core/tests/test_nomina_views_unit.py`
- documentación canónica: `docs/implementaciones/comedores_nomina_ciudadanos.md`

### Si necesitas cambiar exportaciones CSV

- Política UTF-8/BOM y helpers HTTP: `src/backends/kernel/core/services/csv_export.py`.
- Streaming reutilizable: `src/backends/kernel/core/mixins.py:CSVExportMixin`.
- Admin import/export: `src/backends/kernel/core/admin_import_export.py`.
- Guía y contrato: `docs/implementaciones/exportar_listados.md`.
- Los productores CSV nuevos deben reutilizar la política central; el guard
  vive en `src/backends/kernel/tests/test_csv_export_architecture.py`.

### Si necesitas cambiar Encuestas

- `src/backends/sisoc_core/encuestas/models.py`: `Encuesta` (versionado por edicion, ver `version`/`version_de`), `Pregunta` (condicion de visibilidad via `pregunta_condicion`/`operador_condicion`/`valor_condicion`), `OpcionPregunta`, `SegmentacionEncuesta`/`SegmentacionDestinatario`, `RondaEncuesta`, `RespuestaRonda`/`RespuestaPregunta`, `RecordatorioUsuario`.
- `src/backends/sisoc_core/encuestas/services.py`: ciclo de vida (crear/editar-nueva version/publicar/abrir-cerrar ronda), respuestas (`registrar_respuesta`, respeta anonimato), segmentacion (`actualizar_segmentacion`, `agregar_destinatario`/`quitar_destinatario`, aplican en caliente con ronda abierta), cola de pendientes (`get_rondas_pendientes_para_request`, cacheada por request) y el scheduler (`procesar_rondas_pendientes`, `run_encuestas_scheduler`).
- Segmentación por grupos: `SegmentacionEncuesta.grupos` (migración `0007`), `actualizar_segmentacion(..., grupos_ids=...)`; unión de pertenencias actuales a grupos de auth, precargada en pendientes. Selector con búsqueda y selección múltiple en segmentación; nombres visibles en revisión. Exportación JSON v5 por nombre, sin crear grupos al importar. Pruebas: `test_encuestas_segmentacion_grupos.py`.
- Apariencia de segmentación: `src/backends/sisoc_core/encuestas/static/custom/css/encuestaSegmentacion.css` restaura la paleta oscura/dorada previa a `efd1abcc7`, cargada después del layout compartido `encuestaForm.css` únicamente en `encuesta_segmentacion.html`. Conserva selección visible de grupos y cargas por documentos/IDs.
- `src/backends/sisoc_core/encuestas/services_resultados.py`: agregacion de resultados por pregunta y export CSV/Excel (nunca vincula contenido a identidad si la encuesta es anonima).
- `src/backends/sisoc_core/encuestas/validators.py`: parseo del listado de segmentacion (Excel/CSV por documentos o `usuario_id`) y del payload JSON del editor de preguntas (no usa formsets de Django a proposito). Segmentación por IDs: relación `SegmentacionEncuesta.usuarios`, migración `0006`, plantilla `?tipo=listado_usuarios`, validación de existencia y reemplazo atómico; tests en `test_encuestas_segmentacion_usuarios.py`. Exportar con estos destinatarios usa JSON v4; los IDs son locales al ambiente.
- `src/backends/sisoc_core/encuestas/middleware.py` (`EncuestaObligatoriaMiddleware`): bloquea la navegacion de cualquier usuario con una encuesta obligatoria pendiente; registrado en `src/backends/config/settings.py` despues de `ProfileConfirmationMiddleware`. Mismo patron que `src/backends/kernel/users/middleware.py`.
- `src/backends/sisoc_core/encuestas/context_processors.py`: expone la ronda pendiente al modal global (`src/backends/kernel/templates/includes/base.html` + `src/backends/sisoc_core/encuestas/templates/encuestas/partials/responder_modal.html`); comparte cache de request con el middleware para no duplicar la consulta.
- `src/backends/sisoc_core/encuestas/management/commands/process_encuestas_rondas.py` + servicio `encuestas_worker` en `docker-compose.yml`: abre/cierra rondas por fecha, sin Celery.
- `src/backends/kernel/users/bootstrap/groups_seed.py`: grupos `Gestor de Encuestas`, `Administrador de Encuestas` (permiso `aprobar_encuesta`) y `Encuestas Resultados`.
- Guía funcional canónica: `docs/implementaciones/encuestas.md`. El análisis histórico y sus decisiones de diseño quedan en `docs/registro/analisis/2026-08-28-modulo-encuestas.md`.
- Aprobación: `solicitar_publicacion` / `publicar` / `rechazar_publicacion` en `services.py`; borrador → pendiente → publicada o borrador. La ruta histórica `publicar/` ahora solicita, `aprobar/` y `rechazar/` requieren `aprobar_encuesta`. Revisión de solo lectura en `revision/`; pendientes bloquean edición y segmentación. Migración `0004` + `create_groups`. Tests en `test_encuestas_aprobacion.py`; `src/backends/sisoc_core/encuestas/tests/helpers.py` prepara rondas recorriendo el circuito.
- Portabilidad JSON: `exportar_encuesta` / `importar_encuesta` en `services.py`, endpoints `/encuestas/<pk>/exportar/` y `/encuestas/importar/`. Formato v3, admite v1/v2; importar crea borrador nuevo y vuelve al listado. Segmentacion optativa, contiene documentos personales si se incluye.
- Modalidades: obligatoria, postergable y opcional (`Encuesta.es_opcional`). `descartar_ronda` registra descarte por usuario/ronda en `RecordatorioUsuario`, sin computar respuesta. Migracion `0003_encuesta_opcional` necesaria antes de servir el cambio y reiniciar workers.
- UI: `encuestaForm.css` y `encuestaResponder.css` comparten tokens Poncho. Regresiones en `test_encuestas_portabilidad.py` y `test_encuestas_opcionales.py`.
- Listado/revisión: `src/backends/sisoc_core/encuestas/filters.py` configura `AdvancedFilterEngine` y el buscador compartido de Usuarios; título, estado, anónima y recurrente. `encuestaGestion.css` complementa los estilos de listado y las tarjetas de `user_form.css`; filtros/paginación en `test_encuestas_views.py`.
- Rechazo: modal en `encuesta_revision.html` + `RechazoEncuestaForm`, motivo obligatorio (2000 caracteres) validado también por `rechazar_publicacion`. Migración `0005_motivo_rechazo`; guarda último motivo, revisor y fecha, visibles al gestor en edición (`partials/motivo_rechazo.html`) y al revisor después del reenvío. No se exportan ni se copian a nuevas versiones.
- Segmentacion por CUIT: `_documentos_de_usuario` compara CUIT y CUIL contra el CUIL del perfil, ademas de DNI.
### Si necesitas auditar o reparar mojibake en datos

- Reparación conservadora compartida: `src/backends/kernel/core/services/text_encoding.py`.
- Prevención en RENAPER: `src/backends/kernel/core/integrations/renaper.py`; el JSON se decodifica
  desde bytes UTF-8 y el payload se normaliza antes de persistirse.
- Auditoría read-only de campos explícitos: `python manage.py
  audit_utf8_mojibake --field app.Model.campo`.
- Reparación focalizada de nombres y apellidos: `python manage.py
  repair_utf8_mojibake`; es dry-run por defecto y `--apply` requiere backup,
  ventana y autorización operativa.
- Diseño y runbook: `docs/plans/2026-T3/2026-09-01-reparacion-mojibake-datos-design.md`
  y `docs/registro/cambios/2026-T3/2026-09-01-reparacion-mojibake-datos.md`.
- La variante capitalizada (`ã` más una continuación que reconstruye una letra
  mayúscula) usa el mismo comando y requiere un nuevo dry-run después de
  desplegar el correctivo; ver
  `docs/plans/2026-T3/2026-09-01-reparacion-mojibake-capitalizado-design.md` y
  `docs/registro/cambios/2026-T3/2026-09-01-reparacion-mojibake-capitalizado.md`.
- Las variantes restantes que reconstruyen minúsculas requieren además una
  mayúscula artificial posterior y normalizan sólo el token afectado. El mismo
  flujo corrige fronteras persistidas como `ÁNabelle`; ver
  `docs/plans/2026-T3/2026-09-01-reparacion-mojibake-capitalizado-minusculas-design.md`
  y `docs/registro/cambios/2026-T3/2026-09-01-reparacion-mojibake-capitalizado-minusculas.md`.

### Si necesitas cambiar OCR / procesamiento documental

- `src/backends/sisoc_core/ocr/`
- `docker/django/entrypoint.py` para rol `ocr_worker`
- dependencias PDF/OCR en `requirements/base.txt`

### Si necesitas cambiar syncs externos

- GESTIONAR: `src/backends/config/settings.py`, `src/backends/sisoc_core/comedores/tasks.py`,
  `src/backends/sisoc_core/comedores/services/territorial_service/impl.py`, `src/backends/sisoc_core/relevamientos/tasks.py`,
  management commands relacionados, `.env.example`. El flag
  `GESTIONAR_INTEGRATION_ENABLED` corta todo el tráfico AppSheet/GESTIONAR; no
  usarlo como interruptor parcial.
- RENAPER: `src/backends/kernel/core/integrations/renaper.py`, `src/backends/kernel/core/integrations/renaper_rate_limit.py`, `src/backends/kernel/core/services/renaper.py`, docs `docs/flujos/consulta_renaper.md`. La migración `core.0009` debe existir antes de consultas.
- Validación RENAPER de nómina CDI (#2508, Fase 1): payload en
  `src/backends/kernel/ciudadanos/services_renaper_validacion.py`, indicador compartido del PDF en
  `src/backends/cdi/centrodeinfancia/services_renaper_estado.py` y comando
  `validar_renaper_nominas_cdi --dry-run --batch-size 500 --limit 100`.
  Incluso dry-run consulta RENAPER real: requiere ventana autorizada. El comando
  confirma por lote de `--batch-size`, así que una falla conserva los lotes
  anteriores y reejecutarlo retoma donde quedó.
  Contrato y límites: `docs/implementaciones/centrodeinfancia_nomina_renaper.md`.
- Reporte XLSX de CDI (#2508, Fase 2): `src/backends/cdi/centrodeinfancia/services_reportes.py` y
  `views_reportes.py`, en `/centrodeinfancia/reportes/`. Las columnas replican el
  archivo validado en el issue y el alcance sale de `aplicar_scope_centros_cdi`:
  no agregar columnas en el medio ni saltear ese scope. La descarga usa el
  permiso propio `auth.role_reportes_cdi`, no el global `role_exportar_a_csv`.
  Contrato: `docs/implementaciones/centrodeinfancia_reportes.md`.
- Ticketera: `src/backends/cdi/ticketera/`, `docs/integraciones/ticketera_api.md`

### Si necesitas cambiar preinscriptos CDF o vouchers VAT

- Preinscriptos y CSV CDF: `src/backends/cdf/centrodefamilia/views/beneficiarios_export.py`,
  `src/backends/cdf/centrodefamilia/services/beneficiarios_service/impl.py`, tests de
  exportación y `docs/implementaciones/centrodefamilia_preinscriptos.md`.
- Vouchers VAT: `src/backends/vat/VAT/services/voucher_service/`,
  `src/backends/vat/VAT/services/tipo_alumno_service.py`, tests VAT y
  `docs/vat/VOUCHER_SETUP.md`.

### Si necesitas cambiar la búsqueda de Centros VAT por CUE

- API pública: `src/backends/vat/VAT/api_views.py:CentroViewSet` y
  `src/backends/vat/VAT/serializers.py:CentroCueDetalleSerializer`.
- El parámetro `cue` busca el valor vigente e histórico en
  `InstitucionIdentificadorHist` y usa `Centro.codigo` como compatibilidad
  legacy; la respuesta detallada sólo se activa cuando el parámetro está
  presente.
- Tests de contrato: `src/backends/vat/VAT/tests.py` con prefijo
  `test_api_vat_centros_cue_`.
- Request manual: `docs/api/postman/SISOC APIs.postman_collection.json`, carpeta VAT /
  Centros e institución.

### Si necesitas cambiar el Buscador por Ciudadano de INET

- Entrada y flujo POST: `src/backends/vat/VAT/views/buscador_ciudadano.py`, `src/backends/vat/VAT/urls.py` y
  `src/backends/vat/VAT/templates/vat/buscador/ciudadano.html`.
- Scope, trayectoria y exportaciones: `src/backends/vat/VAT/services/buscador_ciudadano_service.py`
  sobre el queryset compartido `src/backends/vat/VAT/services/vat_inscripciones_base.py`.
- La búsqueda global requiere `ciudadanos.view_ciudadano`; un usuario solo VAT
  no debe poder inferir ciudadanos ni inscripciones fuera de su alcance.
- Tests de seguridad, duplicación, exports y queries:
  `src/backends/vat/VAT/test_buscador_ciudadano.py`.

### Si necesitas cambiar CI o reglas de calidad

- `.github/workflows/tests.yml`
- `.github/workflows/lint.yml`
- `.github/workflows/architecture.yml`
- `.github/workflows/release-sanity.yml`
- `.github/workflows/release-orchestrator.yml`
- `src/scripts/github/sync_main_downstream.js`: crea y actualiza ramas técnicas
  `automation/promote-<origen>-to-<destino>` después de un deploy verificado.
  Rechaza una rama origen que ya no coincida con el SHA desplegado y habilita
  auto-merge para respetar los checks del destino.
- `src/scripts/github/sync_main_downstream.test.js` cubre la promoción exacta y
  el rechazo de runs obsoletos; `deploy_guard` ejecuta las pruebas Node de
  ambos orquestadores.
- `.github/workflows/deploy.yml`
- QA, HML y producción ejecutan `deploy_verified.sh`, que sondea
  `migrate --check` y el healthcheck específico. Si no convergen, publica
  diagnóstico y reconstruye/verifica la revisión anterior; las migraciones de
  base no se revierten automáticamente.
- Después de producción verificada se promueve `main -> homologacion`; después
  de HML verificada, `homologacion -> development`. Cada tramo verifica el SHA
  desplegado y usa la GitHub App para respetar rulesets y auto-merge.
- Ante el bloqueo histórico de `centrodeinfancia.0042`, `deploy.yml` sólo
  permite inspeccionar sin PII las categorías de los ids legacy 7, 237 y 242.
  No expone una acción que nulifique filas; antes archiva el SHA aprobado en un
  directorio temporal y valida host, servidor y schema de DB esperados, sin
  tocar el checkout vivo.
- Al cambiar la fecha explícita de un PR a `main`,
  `src/scripts/ci/pr_doc_automation.py` regenera o elimina el bloque de changelog
  previo de ese PR para no dejar una release fantasma.
- La automatización de promociones usa una GitHub App privada: variable
  `RELEASE_AUTOMATION_APP_CLIENT_ID` y secret
  `RELEASE_AUTOMATION_APP_PRIVATE_KEY`; no sustituirla por un PAT.
- `.importlinter`
- `src/scripts/ci/pr_lint_tools.py`, `src/scripts/ci/pr_doc_automation.py`

## Testing, linting, build y deploy

### Lint y formato detectados

- `black --check . --config pyproject.toml`
- `pylint **/*.py --rcfile=.pylintrc`
- `djlint . --configuration=.djlintrc --check`
- CI tiene autofix para PRs internos con Black, DJLint y normalizacion de encoding.

### Tests detectados

- `pytest -m smoke`
- `pytest -n auto --cov=. --cov-fail-under=75`
- `pytest -m mysql_compat -q`
- `python manage.py makemigrations --check --dry-run`
- `lint-imports`
- `python manage.py check --deploy`
- `python manage.py spectacular --validate`

### Validacion minima sugerida por tipo de cambio

| Tipo de cambio | Validacion minima razonable |
| --- | --- |
| view/template local | test cercano del modulo + `djlint` del template |
| servicio Python | test cercano + `pylint` del archivo tocado |
| auth/permisos | tests de auth/permisos cercanos + smoke si afecta login |
| API DRF | test API del modulo + schema si cambia contrato |
| migraciones/modelos | `makemigrations --check --dry-run` + tests del flujo |
| config global | smoke + `manage.py check` |
| import boundaries | `lint-imports` si metiste imports nuevos entre apps |
| release/main | agregar `check --deploy`, `spectacular --validate`, `collectstatic`, gates del PR y baseline `AAAA.MM.DD-stable` |

### Build/deploy

- Local: `docker compose up`
- Front v2 local: `docker compose up --build front_vpsl`; hot reload con `docker/compose/docker-compose.frontends.dev.yml` como segundo archivo. Desde `src/frontends/`: `npm ci`, `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`, `npm run test:e2e` y `npm audit --audit-level=low`.
- Contrato VPSL: `FRONTEND_V2_SCHEMA_ONLY=1 python manage.py spectacular --file src/frontends/packages/api/openapi.yaml --format openapi`; luego `npm run types:generate` en `src/frontends/`.
- Deploy versionado: `docker compose --project-directory . -f docker/compose/docker-compose.deploy.yml ...`
- Produccion: override `docker/compose/docker-compose.produccion.yml`
- Sanity de release a `main` valida `check --deploy`, OpenAPI y `collectstatic`

## Comandos utiles detectados

### Seguros para inspeccion

- `Get-ChildItem`, `git ls-files`, `rg`
- `docker compose config --services`
- `python manage.py show_urls` si existiera dependencia instalada y entorno levantado
- `src/scripts/ai/codex_doctor.ps1`
- `src/scripts/ai/codex_run.ps1 smoke`
- `src/scripts/ai/codex_run.ps1 validate`

### Seguros pero potencialmente costosos

- `docker compose up -d --build`
- `docker compose exec django pytest -n auto`
- `pylint **/*.py --rcfile=.pylintrc`
- `lint-imports`

### Pedir permiso o tener especial cuidado antes de correr

- `docker compose down -v`
- comandos que destruyan volumenes/MySQL
- imports masivos desde Excel/CSV o commands operativos sobre datos
- commands que sincronicen con GESTIONAR o RENAPER reales
- cualquier deploy refresh sobre servidores
- scripts que dependan de `.env` reales del host

## Riesgos, zonas sensibles y advertencias para agentes

### Zonas sensibles

- `src/backends/config/settings.py`: cambia todo el runtime, seguridad, cache, auth, logging, docs API.
- `src/backends/config/urls.py`: cualquier ajuste impacta routing global.
- `docker/django/entrypoint.py`: side effects de arranque, migraciones, workers.
- `src/backends/kernel/users/bootstrap/groups_seed.py` y comandos de grupos: permisos globales.
- `src/backends/sisoc_core/encuestas/middleware.py`: middleware global nuevo (registrado en `src/backends/config/settings.py`), puede bloquear la navegacion de cualquier usuario autenticado en cualquier vista del sistema si tiene una encuesta obligatoria pendiente.
- `src/backends/sisoc_core/comedores/tasks.py` y `src/backends/sisoc_core/relevamientos/tasks.py`: syncs externos, threads y side effects.
- `signals.py` de varias apps: pueden disparar efectos colaterales no obvios.
- `src/backends/kernel/templates/includes/` y `src/backends/kernel/templates/components/`: impacto transversal de UI.
- `custom/js/` (en `src/backends/kernel/static/` y en cada `<app>/static/`): mucho JS parece estar acoplado a IDs/clases exactas del HTML.
- `migrations/`: tocarlas manualmente sin necesidad suele ser mala idea.
- `.env*`: no versionar secretos ni usar valores reales.

### Legacy / deuda tecnica visible

- El front legacy conserva JS y templates dispersos; la nueva base `src/frontends/` usa pipeline propio de npm, Vite y CI.
- coexistencia de apps muy refactorizadas y apps con archivos monoliticos.
- `package-lock.json` en raiz sin `package.json`: parece drift/artefacto sobrante, no contrato operativo confirmado.
- `tmp/ci-pr-*`: artefactos temporales; no usarlos como fuente de verdad.

### Precauciones practicas antes de editar

1. Revisar si la app ya tiene `services/` y tests cercanos.
2. Buscar signals, tasks y commands relacionados.
3. Si el cambio toca permisos, revisar `groups_seed.py`, permisos de view/API y docs IAM.
4. Si el cambio toca imports entre apps, pensar en `.importlinter`.
5. Si el cambio toca templates, localizar el JS asociado en `<app>/static/custom/js` o `src/backends/kernel/static/custom/js`.
6. Si el cambio toca integraciones, confirmar si existen tests con mocks o docs de flujo antes de asumir contrato.

## Que archivos NO conviene tocar salvo necesidad clara

- `.env`
- `docker/mysql/local-dump.sql`
- `migrations/` existentes solo para "ordenar"
- `src/backends/kernel/static/dist/`, `.../static/debug_toolbar/`, `.../static/silk/` salvo motivo concreto
- `tmp/`
- workflows CI completos si el problema es solo de codigo del modulo
- `src/backends/config/settings.py` para fixes locales de negocio si puede resolverse dentro del modulo

## Guias y contexto que conviene leer antes de una feature concreta

### Base minima siempre

1. `AGENTS.md`
2. `docs/indice.md`
3. este `docs/ia/AGENT_REPO_MAP.md`
4. archivo objetivo
5. tests cercanos

### Segun el tipo de tarea

| Tipo | Leer primero |
| --- | --- |
| bugfix view/template | `docs/ia/TESTING.md`, template, view, JS asociado |
| API/serializer | `docs/ia/TESTING.md`, `api_views.py`, serializer, tests API |
| permisos/auth | `docs/ia/SECURITY_AI.md`, `src/backends/kernel/users/`, docs IAM |
| nuevo modulo o preparacion de extraccion | `docs/ia/MODULAR_BOUNDARIES.md`, `.importlinter`, `src/backends/config/settings.py`, `src/backends/config/urls.py` |
| boundaries/refactor existente | `docs/ia/ARCHITECTURE.md`, `.importlinter` |
| logging/errores/fallbacks | `docs/ia/ERRORS_LOGGING.md` |
| estilo/template | `docs/ia/STYLE_GUIDE.md` |
| PWA | `docs/implementaciones/pwa_backend.md`, `docs/seguridad/security_baseline_pwa.md` |
| deploy/infra | `docs/operacion/infraestructura.md`, `docs/operacion/instalacion.md`, `docs/infra/QA_OPERATIONS.md`, `docs/infra/ENVIRONMENT_DATABASES.md` |

## Notas utiles sobre calidad y arquitectura

### Mapa web de arquitectura

- `/arquitectura/` y `/arquitectura/grafo.json` exigen sesión. El grafo vive en
  `var/arquitectura/grafo.json`, fuera de estáticos y de Git.
- `src/scripts/arquitectura/generar_mapa.py` lee el registro
  `src/backends/config/backends.json`, los dueños de las apps, los workspaces
  `src/frontends/apps/` y las claves de `FRONTEND_V2_UPSTREAMS`, sin ejecutar
  settings ni consultar la DB. La asociación frontend/backend por nombre es
  inferida; no demuestra consumo HTTP ni servicios activos.
- La etapa `source` de `docker/django/Dockerfile` ejecuta el generador con
  `--imagen` antes de quitar frontends y verticales. El arranque conserva esa
  captura completa (`var/arquitectura/grafo-imagen.json`); no reconstruye un
  mapa parcial desde el core aislado. `.dockerignore` excluye `var` para evitar
  capturas locales dentro de una nueva imagen.
- `python src/scripts/arquitectura/generar_mapa.py --docs` actualiza el grafo
  documental y `docs/arquitectura/mapa_sisoc.html`. El arranque no escribe docs.
- Pruebas focalizadas: `src/backends/kernel/tests/test_mapa_arquitectura_generador.py`.

### Import-linter

- Hay una iniciativa explicita de "monolito modular fase 0".
- El baseline actual permite imports legacy, pero CI debe fallar ante nuevas dependencias prohibidas.
- Si un import nuevo entre apps te parece inocente, igual puede ser una regresion arquitectonica.

### Modulos nuevos extraibles

- Esta regla aplica a codigo nuevo; no declara que las apps existentes ya puedan moverse a otro repositorio.
- Antes de crear una app, clasificar si es vertical extraible, parte de un bounded context o cambio de kernel.
- `api_views.py`/DRF no reemplazan el `api.py` de contrato entre dominios. Ver `docs/ia/MODULAR_BOUNDARIES.md`.

### Tests

- `pytest.ini` usa `--reuse-db`.
- Existen markers:
  - `smoke`
  - `mysql_compat`
- CI ejecuta algunos jobs contra SQLite y otros contra MySQL real.

### DRF

- `REST_FRAMEWORK` usa `IsAuthenticated` por defecto.
- Hay schema OpenAPI con drf-spectacular y variante propia para VAT.

## Mapa rapido: "si necesitas cambiar X, mira primero Y"

| Necesidad | Mirar primero |
| --- | --- |
| login / reset / perfil | `src/backends/sisoc_core/usuarios/views.py`, `src/backends/sisoc_core/usuarios/forms.py`, templates `src/backends/kernel/users/templates/` |
| grupos / permisos | `src/backends/kernel/users/bootstrap/groups_seed.py`, `src/backends/sisoc_core/usuarios/api_permissions.py`, docs IAM |
| navbar / sidebar / layout | `src/backends/kernel/templates/includes/`, `src/backends/kernel/templates/includes/sidebar/`, `src/backends/kernel/static/custom/js/sidebar.js` |
| filtro/listado generico | `src/backends/kernel/core/`, `src/backends/kernel/templates/components/data_table.html`, JS de la pantalla |
| comedores | `src/backends/sisoc_core/comedores/models.py`, `tasks.py`, `signals.py`, tests `test_comedor*` |
| relevamientos | `src/backends/sisoc_core/relevamientos/models.py`, `tasks.py`, `views.py` |
| RENAPER | `src/backends/kernel/core/integrations/renaper.py`, `src/backends/kernel/core/services/renaper.py` |
| GESTIONAR | `src/backends/sisoc_core/comedores/tasks.py`, `src/backends/sisoc_core/relevamientos/tasks.py`, commands relacionados |
| docx/pdf | `src/backends/sisoc_core/admisiones/services/`, `src/backends/sisoc_core/comedores/services/certificacion_prestaciones_service.py`, `src/backends/sisoc_core/pwa/services/nomina_destinatarios_pdf_service.py`, `src/backends/sisoc_core/pwa/files/varios/` |
| PWA | `src/backends/sisoc_core/pwa/api_views.py`, `src/backends/sisoc_core/pwa/services/`, tests `test_pwa_*` |
| OCR | `src/backends/sisoc_core/ocr/`, `docker/django/entrypoint.py` |
| encuestas | `src/backends/sisoc_core/encuestas/services.py`, `src/backends/sisoc_core/encuestas/middleware.py`, `docs/registro/analisis/2026-08-28-modulo-encuestas.md` |
| auditoria | `src/backends/kernel/audittrail/`, docs `audittrail_*` |
| release/deploy | `docs/operacion/*.md`, workflows, compose deploy |
| CI rota por estilo | `.github/workflows/lint.yml`, `src/scripts/ci/pr_lint_tools.py` |
| CI rota por imports | `.importlinter`, `requirements/arch.txt` |

## Zonas no analizadas a fondo en esta pasada

- logica interna completa de `dashboard`, `dispositivos`, `duplas`, `expedientespagos`, `historial`, `intervenciones`, `organizaciones`, `rendicioncuentasfinal`, `rendicioncuentasmensual`, `ver_para_ser_libre`
- detalle fino de `src/backends/sisoc_core/ocr/`
- contratos completos de cada API mas alla del routing y docs encontradas
- flujos exactos de algunos workers (`mailing`, `ciudadanos_import_worker`) fuera del entrypoint

Marcar esas zonas como `A inferir` hasta relevarlas cuando una tarea real las toque.

## Recomendaciones para mantener este archivo actualizado

1. Actualizarlo cuando se agregue o elimine una app relevante.
2. Reflejar nuevos entrypoints, workers o compose files.
3. Si se consolida o mueve logica de una app a `services/`, anotar el nuevo hotspot.
4. Si cambia CI, actualizar la matriz de validacion minima.
5. Si se agregan integraciones externas, sumar archivo fuente, variables y riesgos.
6. Si un area legacy se moderniza, reemplazar inferencias por hechos observados.
7. No duplicar specs detalladas de negocio aqui: enlazar a `docs/` cuando exista una fuente de verdad mas especifica.

## Archivos inspeccionados para construir este mapa

- `AGENTS.md`
- `README.md`
- `docs/indice.md`
- `docs/contexto/arquitectura.md`
- `docs/contexto/aplicaciones.md`
- `docs/contexto/panorama.md`
- `docs/contexto/dominio.md`
- `docs/operacion/instalacion.md`
- `docs/operacion/comandos_administracion.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `src/backends/config/urls.py`
- `src/backends/config/settings.py` (lectura parcial dirigida)
- `docker-compose.yml`
- `docker/django/entrypoint.py`
- `.env.example`
- `.importlinter`
- `pytest.ini`
- `pyproject.toml`
- `requirements/base.txt`
- `requirements/dev.txt`
- `requirements/test.txt`
- `requirements/lint.txt`
- `requirements/arch.txt`
- `.github/workflows/tests.yml`
- `.github/workflows/lint.yml`
- `.github/workflows/architecture.yml`
- `.github/workflows/release-sanity.yml`
- `.github/workflows/release-orchestrator.yml`
- `.github/workflows/deploy.yml`: deploy por ambiente y promoción secuencial
  posterior a producción/HML verificadas.
- `.github/workflows/pr-docs.yml`: genera los artefactos spec-as-source; usa
  `git status --porcelain --untracked-files=all` para incluir archivos nuevos.
  Solo pushea en ramas internas no protegidas; `sync_pr_artifacts` verifica
  también forks y ramas protegidas. Los PRs hacia `main` requieren además
  release note pendiente y `CHANGELOG.md` ya versionados. Las ejecuciones se
  serializan por PR y el push automático reintenta con `fetch` + `rebase` si
  otra automatización hizo avanzar la rama; los conflictos reales bloquean.
- `.github/workflows/deploy.yml`
- `src/scripts/ai/codex_run.ps1`
- `src/scripts/ai/codex_task.ps1`
- `.codex/environments/environment.toml`
- inventario de archivos con `git ls-files`
- inventario estructural de apps y scripts via shell

## PAS Celery mensual
- `src/backends/config/celery.py`, `src/backends/pas/pas/tasks.py`, `src/backends/pas/pas/services/supervivencia_jobs.py`: programación, reconciliación y un lote exclusivo por MySQL GET_LOCK; dentro del lote, ventanas transaccionales, dos clientes por hilo y límite agregado inicial de 16 solicitudes/s.
- `docker/compose/docker-compose.celery.yml` se incorpora desde deploy_refresh; Redis persistente, Beat único y worker PAS.
- Runbook funcional: `docs/implementaciones/pas_control_mensual_celery.md`; retirada cron: `src/scripts/infra/remove_pas_cron.sh`.
