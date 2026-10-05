# Ola 2: VPSL, PAS, VAT y Celiaquía como backends propios

Continúa `2026-10-01-backend-dispositivos.md` (#2309, #1931, #2251). Guía:
`docs/operacion/backends_por_servicio.md`.

## Qué cambió

- **Backends nuevos:** `ver_para_ser_libre`, `pas`, `VAT` y `celiaquia`
  pasan a `backends/vpsl/`, `backends/pas/`, `backends/vat/` y
  `backends/celiaquia/`, cada uno con su runtime. El core reenvía sus
  prefijos.
- **Settings y URLs comunes de backends:** `config/backend_settings.py` y
  `config/backend_urls.py`. Dispositivos también los usa.
- **Celery** (solo PAS): el worker y el beat corren con la imagen y el
  settings del backend de PAS, y el deploy selectivo de PAS los recrea.
- **Schema y docs OpenAPI de VAT** (`/api/schema/VAT/`, `/api/docs/VAT/`,
  `/api/redoc/VAT/`): los sirve el backend de VAT.
- **Ciudadano 360:**
  - las secciones de VAT y Celiaquía pasan a ser contribuciones
    renderizadas, con el template en el vertical;
  - el core las pide al backend dueño con la sesión del usuario;
  - `ciudadanos.views` ya no importa `celiaquia.api`.
- **Filtros favoritos:** el core reenvía al backend dueño las secciones que
  no tiene registradas. **Esto corrige una regresión de la Ola 1:** los
  favoritos de Dispositivos respondían 400 en QA.
- **Menú "solo VAT":** la regla pasa al kernel (`iam.roles_vat`); `VAT`
  reexporta las funciones.
- **`NoCountPage`** pasa a ser iterable, igual que la `Page` de Django.
  Corrige un error previo en `/vat/centros/ajax/` que apareció con el test
  nuevo de rutas.
- **Tests:** `tests/test_servicios_backends.py` recorre, por cada backend y
  en su propio proceso, todas sus rutas sin argumentos como superusuario.

## Sin cambios

URLs públicas, permisos, datos y comportamiento de las pantallas.

## Riesgos

- **Detalle de ciudadano:** en deploy, las secciones de VAT y Celiaquía
  dependen de que su backend responda. El timeout es de 4 s y, si falla, la
  sección queda vacía.
- **Primer deploy:** levanta cinco backends y mueve Celery. Hay que revisar
  los logs de `celery_pas_worker` y `celery_beat`.
