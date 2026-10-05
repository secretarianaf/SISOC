# Backend de Dispositivos (con Datacalle) como servicio propio

Ola 1 de #2309 (#1931, #2251). ADR:
`docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md`. Guía
operativa: `docs/operacion/backends_por_servicio.md`.

## Qué cambió

- **Código:** `dispositivos` y `datacalle` pasan a `backends/dispositivos/`,
  con sus tests. `sentry` y `healthcheck` pasan a `kernel/`.
- **Runtime propio** (`dispositivos_runtime`): settings con solo el kernel y
  las apps del backend, y sus URLs.
- **`config/backends.json`:** registro único de backends.
  `config/settings.py` separa `SHARED_APPS`, `KERNEL_APPS` y `CORE_APPS`.
  `config/settings_all.py` y `config/urls_all.py` arman la composición
  completa para tests, desarrollo y migrador.
- **Proxy del core** (`kernel/core/backend_proxy.py):
  - acepta todos los métodos y reenvía el body como stream, así los uploads
    no pasan por el límite de `DATA_UPLOAD_MAX_MEMORY_SIZE`;
  - reenvía los bytes tal como llegan, sin descomprimir;
  - conserva cada `Set-Cookie`;
  - el core calcula `Host` y los `X-Forwarded-*`, y `X-Forwarded-Host` no se
    reenvía;
  - no sigue redirects y responde 503 o 504 propios.
- **Registro de nombres de URL** (`config/url_registry.json` y
  `kernel/core/url_registry.py`): cada proceso resuelve con `reverse()` los
  nombres de otro servicio.
- **Menú lateral:** los tableros de `dashboard` se registran en
  `core.services.sidebar_items` (tag `sidebar_tags`).
- **Imágenes de deploy** (`docker/django/Dockerfile`):
  - `core`: sin `backends/`.
  - `backend`: el kernel más un backend.
  - `migrator`: todo, con `settings_all`.
  - `dev`: el stage por defecto, igual que antes.
- **Compose de deploy:** sin bind mount del checkout; solo se montan `media`,
  `static_root` y `logs`. Los workers y Celery usan la imagen `core`.
  `cache_busting` vacía `static_root` sin borrar el punto de montaje.
- **Deploy selectivo:** `scripts/operacion/deploy_targets.py` decide el plan
  (completo, selectivo o ninguno) y `deploy_refresh.sh` lo ejecuta.
  `deploy_verified.sh` le pasa la base del diff, también en el rollback, y
  verifica migraciones con el migrador y la salud de cada backend.
- **CI:** job nuevo `service_images`, requerido por `deploy_guard`. Construye
  las imágenes y verifica el aislamiento: el core no importa apps de backend y
  el backend no importa apps del core.

## Sin cambios

URLs públicas, permisos, datos y comportamiento de las pantallas de
Dispositivos y Datacalle. El desarrollo local sigue igual (`docker compose
up`, todo en un proceso).

## Evidencia

- **Ensayo local de punta a punta** con `docker-compose.deploy.yml`, MySQL y
  migrador:
  - login por el core;
  - `/dispositivos/`, `/dispositivos/crear` y `/datacalle/relevamientos/`
    llegan por el proxy desde el backend, con layout y menú;
  - POST con CSRF válido pasa y sin token da 403; un anónimo recibe 403, igual
    que antes.
- **Redeploy solo del backend:** el contenedor del core mantuvo el mismo
  `StartedAt` y la misma imagen; el backend se recreó con la imagen nueva.
- **Backend detenido:** `/dispositivos/` da 503 y `/inicio/` y
  `/comedores/listar` siguen en 200.

## Riesgos

- **Primer deploy con el nuevo modelo** (QA): cambia cómo arranca todo el
  stack. Puntos a vigilar:
  - `static_root` y `media` montados;
  - el migrador corre antes del core;
  - los logs siguen en `./logs`.
- **Latencia y workers:** cada request de Dispositivos ocupa un worker del
  core mientras espera al backend. El timeout de lectura es de 25 s, por
  debajo del de Gunicorn.
- **Menú en páginas del backend:** los predicados de sidebar de VAT y CDI no
  están registrados ahí, así que los usuarios restringidos a "solo VAT" o
  "solo CDI" ven ahí el menú general.
