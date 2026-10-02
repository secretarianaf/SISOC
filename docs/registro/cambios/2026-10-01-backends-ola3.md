# Ola 3: CDI y CDF como backends, organizaciones y catálogos al kernel

Continúa `2026-10-01-backends-ola2.md` (#2309, #1931, #2251). Guía:
`docs/operacion/backends_por_servicio.md`.

## Qué cambió

- **Backends nuevos:**
  - `centrodeinfancia` y `ticketera` pasan a `backends/cdi/`
    (`/centrodeinfancia/`, `/simepi/`, `/api/ticketera/`);
  - `centrodefamilia` pasa a `backends/cdf/` (`/centrodefamilia/`,
    `/api/centrodefamilia/`).
- **Kernel:**
  - `organizaciones` pasa a `kernel/organizaciones` con sus datos maestros.
    Sus pantallas, formularios, exportaciones y el modelo `Firmante`, que se
    relaciona con comedores, quedan en el core, en la app nueva
    `gestion_organizaciones`.
  - Los catálogos de intervenciones (TipoIntervencion, SubIntervencion,
    TipoDestinatario y TipoContacto) pasan de `intervenciones` a
    `kernel/catalogo_intervenciones`.
  - Las migraciones son solo de estado: las tablas conservan su nombre y los
    content types se reasignan conservando sus ids, así que los permisos no
    cambian.
- **Prefijo de CDF.** Las pantallas de CDF pasan a `/centrodefamilia/...`.
  Las URLs viejas (`/centros/`, `/actividades/`, `/ajax/actividades/`,
  `/informecabal/` y `/beneficiarios/`) redirigen con 301 (GET) o 308 (resto)
  **solo por compatibilidad** (`core.legacy_redirects`).
- **Ciudadano 360:** la sección y el monto de CDF son contribuciones
  renderizadas, que el core pide al backend de CDF.
- **Dashboard:** el core pide las métricas de CDF a su backend
  (`/centrodefamilia/metricas-dashboard/`).
- **Menú CDI local:** la regla pasa al kernel (`iam.roles_cdi`).
- **Informe Cabal:** las vistas de preview y procesamiento aceptan solo POST.
  Antes, un GET daba 500 (ImproperlyConfigured).

## Sin cambios

Datos, permisos y comportamiento de las pantallas. Las URLs de CDF cambian,
pero las viejas siguen funcionando por redirección.

## Riesgos

- **Primer deploy:** levanta `backend_cdi` y `backend_cdf` y corre
  migraciones de estado que reasignan content types. Si existen content types
  duplicados en las dos apps, la migración se detiene a propósito y hay que
  resolverlo a mano.
- **Dashboard y detalle de ciudadano:** las métricas y la sección de CDF
  dependen de que su backend responda; si no, se muestran en cero o vacías.
- **Enlaces externos a URLs viejas de CDF:** funcionan por redirección. Un
  POST externo a una URL vieja recibe 308.
