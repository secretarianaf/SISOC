# Arquitectura

Desde #2251/#2309 SISOC corre como varios servicios construidos desde el mismo
repo: el **core** (proxy de entrada y apps de Comedores), un **backend por
vertical** (PAS, CDI, CDF, Celiaquía, Dispositivos, VAT, VPSL), un **migrador**
único, workers dedicados, Celery de PAS y el **front v2** en React. El diagrama
de abajo describe un proceso Django; el core reenvía a cada backend los
prefijos que declara `src/backends/config/backends.json`. Ver
`docs/operacion/backends_por_servicio.md` y las decisiones
`docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md` y
`docs/registro/decisiones/2026-10-02-estructura-src-backends.md`.

Las referencias abreviadas de evidencia se resuelven bajo el dueño de la app
(`src/backends/kernel/`, `src/backends/sisoc_core/` o `src/backends/<vertical>/`).
Las rutas que comienzan con src/ parten de la raíz del repositorio.

## 1) Diagrama textual (ASCII)
```
           ┌───────────────┐
           │  Cliente web  │
           └───────┬───────┘
                   │ HTTP (auth Django)
            ┌──────▼───────┐
            │   Django     │
            │(views/DRF)   │
            └──────┬───────┘
   ┌────────────┬──┴──┬────────────┐
   │Middleware  │URLs │ Templates  │
   └──────┬─────┴─────┴──────┬─────┘
          │                  │
   ┌──────▼──────┐    ┌──────▼──────┐
   │  Services   │    │ Serializers │
   └──────┬──────┘    └──────┬──────┘
          │                  │
      ┌───▼───┐          ┌───▼───┐
      │ Models│          │ Auth  │
      └───┬───┘          └───┬───┘
          │                  │
   ┌──────▼──────┐     ┌─────▼─────┐
   │  MySQL      │     │  Cache    │
   └─────────────┘     │ (LocMem)  │
                        └──────────┘

      ┌────────────────────────────────────────┐
      │   Servicios externos (HTTP, async)     │
      │ - GESTIONAR (comedores, relevamientos) │
      │ - RENAPER (consulta ciudadanía)        │
      │ - Google Maps API key (opcional)       │
      └────────────────────────────────────────┘
```
Evidencia: src/backends/config/settings.py; src/backends/config/urls.py; comedores/tasks.py; relevamientos/tasks.py; core/integrations/renaper.py; core/services/renaper.py; docker-compose.yml.

## 2) Capas existentes
- Presentación: vistas Django y DRF (urls en `src/backends/config/urls.py`), plantillas en `src/backends/kernel/templates/` y apps propias. Evidencia: src/backends/config/urls.py:12-44; src/backends/config/settings.py:105-120.
- Middleware: seguridad, sesiones, CORS, CSRF, autenticación, auditlog, mensajes, XFrame, XSS custom, threadlocals; en DEBUG se agregan debug_toolbar y silk. Evidencia: src/backends/config/settings.py:85-99,359-366.
- Servicios/negocio: servicios en apps (ej. `src/backends/sisoc_core/comedores/services`, `src/backends/cdf/centrodefamilia/services`), sincronización con GESTIONAR en `tasks.py` y consulta técnica compartida de RENAPER en `src/backends/kernel/core/integrations/renaper.py` con fachada `src/backends/kernel/core/services/renaper.py`.
- Dominio/persistencia: modelos en cada app; DB configurada a MySQL. Evidencia: src/backends/config/settings.py:153-168; apps listadas en src/backends/config/settings.py:42-83.
- Serialización/API schema: DRF + drf-spectacular. Evidencia: src/backends/config/settings.py:195-234.

## 3) Flujo request → response
- Entrada HTTP → middleware chain (security, session, CORS, common, CSRF, auth, auditlog, messages, clickjacking, admindocs, XSSProtectionMiddleware, ThreadLocalMiddleware; en DEBUG: debug_toolbar, silk) → URL routing (`src/backends/config/urls.py`) → views/templates o DRF views → respuesta. Evidencia: src/backends/config/settings.py:85-99,359-366; src/backends/config/urls.py:12-44.
- Autenticación: usa `django.contrib.auth` con `LOGIN_URL`/redirects y DRF por defecto exige `IsAuthenticated`. Evidencia: src/backends/config/settings.py:130-135,195-203; src/backends/config/urls.py:15.
- Static/media: en desarrollo los sirve Django (`staticfiles_urlpatterns` y `static`); en deploy, Nginx publica `static_root/` y `media/`. Evidencia: src/backends/config/urls.py:50-51; src/backends/config/settings.py:122-128.

## 4) Asincronía
- Celery con Redis solo para PAS (`docker/compose/docker-compose.celery.yml`: `celery_pas_worker` y `celery_beat`). No hay Kafka.
- Workers dedicados con la imagen del core, elegidos por `DJANGO_SERVICE_ROLE` (`docker/django/entrypoint.py`): credenciales masivas, importación de ciudadanos y de usuarios, mailing, OCR y rondas de encuestas.
- Hilos (`threading.Thread` + `ThreadPoolExecutor`) para llamadas HTTP a GESTIONAR en comedores/relevamientos. Evidencia: comedores/tasks.py:1-249; relevamientos/tasks.py:1-144.
- Cron programados externos: purga auditlog y limpieza de logs (scripts/crontab). Evidencia: scripts/crontab:2-5; audittrail/management/commands/purge_auditlog.py:1-38; scripts/borrar_logs.py:1-43.

## 5) Almacenamiento
- Base de datos: MySQL (principal); pytest usa SQLite en memoria. Evidencia: src/backends/config/settings.py:153-174; docker-compose.yml:1-19.
- Cache: `LocMemCache` (no compartida entre instancias). Evidencia: src/backends/config/settings.py:175-189.
- Archivos estáticos/media: filesystem (`STATIC_ROOT`, `MEDIA_ROOT`). Evidencia: src/backends/config/settings.py:122-128.
- No hay search engine declarado.

## 6) Configuración por entorno
- Variable `ENVIRONMENT` (dev|qa|prd) y `DJANGO_DEBUG` controlan toggles; en homologacion y prd se activa HSTS, SSL redirect, cookies seguras y ManifestStaticFilesStorage; en dev se habilitan toolbars. Evidencia: src/backends/config/settings.py:12-15,136-140,359-388.
- Entrypoint Docker usa `.env`. En desarrollo la web prepara la DB (migraciones, fixtures, grupos) al iniciar y corre runserver. En deploy la DB la prepara el servicio `migrator` (composición completa), que además corre `collectstatic` sobre `static_root/`; la web arranca con `SISOC_PREPARAR_DB=false` y Gunicorn. Evidencia: docker/django/entrypoint.py; docker/compose/docker-compose.deploy.yml.
- Variables de entorno definidas en `.env.example` (DB, GESTIONAR, RENAPER, puertos, dominio, Gunicorn). Evidencia: .env.example:1-51.

## 7) Puntos de extensión
- Signals en varias apps (duplas, users) y auditlog middleware; management commands extensibles por app. Evidencia: users/management/commands/*.py; comedores/management/commands/*.py; relevamientos/management/commands/*.py; duplas/signals.py:1-40; auditlog middleware en src/backends/config/settings.py:92-94.
- Middleware propios: `config.middlewares.xss_protection.XSSProtectionMiddleware`, `config.middlewares.threadlocals.ThreadLocalMiddleware`. Evidencia: src/backends/config/settings.py:97-99.
- API schema vía drf-spectacular; extensible con componentes y enums. Evidencia: src/backends/config/settings.py:195-234.
