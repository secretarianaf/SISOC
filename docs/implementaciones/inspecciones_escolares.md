# Inspecciones escolares

Estado: vigente desde 2026-10-15. Referencia consolidada del vertical
`inspecciones`; el detalle y las mediciones de cada cambio viven en los
registros enlazados al final.

## Qué es

Backend de la PWA **Sisoc Inspecciones** (repositorio aparte,
`secretarianaf/Inspecciones`) y panel de coordinación en el backoffice. Los
inspectores registran visitas a escuelas, firman en pantalla y emiten actas
numeradas; coordinación administra el catálogo, las asignaciones y consulta
actas y tablero.

## Dónde vive

| Pieza | Ubicación |
| --- | --- |
| App | `src/backends/inspecciones/inspecciones/` |
| Runtime | `src/backends/inspecciones/inspecciones_runtime/` (servicio `backend_inspecciones`) |
| Registro del backend | `src/backends/config/backends.json` (prefijos `/inspecciones/` y `/api/inspecciones/`, el core reenvía por proxy) |
| Tests | `src/backends/inspecciones/tests/` y `src/backends/sisoc_core/tests/test_users_inspecciones_escolares.py` |
| Rol y acceso (kernel) | `users.services_inspecciones` (`puede_gestionar_inspecciones`) |

Sólo depende del kernel (`users`, `core`). Nadie importa `inspecciones`
(contratos de `.importlinter`).

## Roles y permisos

- `Profile.es_inspector_escolar` + `Profile.inspecciones_rol`
  (`inspector` | `coordinacion`). El flag sin rol no da acceso.
- El inspector es usuario sólo de la app (sin SISOC web ni `is_staff`);
  coordinación conserva el acceso web.
- Backoffice, tablero, anulación y archivos del panel exigen
  `puede_gestionar_inspecciones`: rol coordinación, permiso
  `inspecciones.gestionar_inspecciones` o superusuario. Sin eso, 403.
- API: sólo usuarios del programa (`TieneAccesoInspecciones`). El inspector ve
  y modifica lo propio; coordinación consulta todo pero no escribe sobre lo
  ajeno (404).
- Asignar el rol (ABM o importador XLSX de usuarios) requiere la sección
  `auth.role_usuarios_seccion_inspecciones_escolares`.
- El ítem del menú lateral se decide con el predicado de sidebar
  `inspecciones_gestion`, registrado en `core.apps` porque el menú se arma en
  backends donde la app no está instalada.

## API `/api/inspecciones/` (PWA)

Token DRF. Rutas (`src/backends/inspecciones/inspecciones/api_urls.py`):

| Ruta | Uso |
| --- | --- |
| `escuelas/asignadas/`, `escuelas/`, `escuelas/<codigo>/` | asignadas del día, búsqueda (mínimo 3 caracteres) y ficha |
| `borradores/`, `borradores/<uuid>/` | borrador idempotente por uuid; gana la mayor `revision` |
| `borradores/<uuid>/finalizar/` | cierre transaccional con número `ACTA-AAAA-NNNNNN` |
| `borradores/<uuid>/imagenes/<uuid>/`, `imagenes/<uuid>/` | evidencia (JPEG/PNG por firma binaria, hasta 10 MB) |
| `actas/`, `actas/<numero>/`, `actas/<numero>/pdf/` | actas propias; coordinación suma `?alcance=todas` |
| `actas/<numero>/notificaciones/`, `notificaciones/archivos/<uuid>/` | notificación en papel versionada y sus fotos |

El contrato base es `CONTRATO-API-INSPECCIONES.md` del repo de la PWA; las
diferencias implementadas están en la tabla del registro del backend.

Invariantes:

- El cierre valida, guarda la instantánea (con SHA-256), toma el número de
  `SecuenciaActa` con `select_for_update` y registra la hora oficial en una
  sola transacción: sin huecos ni duplicados. Un segundo cierre devuelve la
  misma acta.
- Un acta anulada no cuenta como visita válida: la escuela vuelve a
  `pendiente` y se puede registrar otra visita.
- Los archivos se guardan en `MEDIA_ROOT/inspecciones/` con un storage sin URL
  y se sirven sólo por API o panel, con `Cache-Control: private, no-store`.

## Backoffice `/inspecciones/`

- **Escuelas**: catálogo paginado, alta/edición, marca "a revisar" con
  motivos. El Cueanexo vive en `codigo` (inmutable, `id` de la API) y `cue`.
- **Importación del padrón** (`.xlsx` primera hoja o `.csv`, hasta 25 MB) en
  tres pasos: archivo → revisión → confirmación. Nada se escribe antes de
  confirmar; los temporales quedan en `MEDIA_ROOT/inspecciones/importaciones/`
  y lo abandonado se limpia a las 24 h. Requiere la geografía
  `core.Provincia/Municipio/Localidad` cargada.
- **Asignaciones** por jornada (alta, quitar sin acta, importación en tres
  pasos). Única por `escuela + inspector + fecha`; el inspector debe tener rol
  `inspector`.
- **Actas**: listado, detalle desde la instantánea, PDF, anulación (motivo de
  al menos 10 caracteres) y marca de prueba.
- **Tablero** `tablero/`: sólo actas válidas (`finalizada` y no de prueba);
  consulta `tablero/datos/` cada 5 s con cache de 2 s por filtros; mapa con
  teselas Argenmap del IGN limitado a Argentina; CSV `tablero/exportar.csv`.
- Usa el layout claro compartido del kernel (`includes/base_claro.html`).

## Operación y despliegue

- Nginx de cada host: `location ^~ /media/inspecciones/ { return 404; }`
  antes de habilitar (ver `docs/operacion/nginx/sisoc-produccion.conf`).
- Imagen `sisoc/backend-inspecciones`; las migraciones corren en el migrador.
  Workers: `BACKEND_INSPECCIONES_WORKERS` (por defecto 4).
- La PWA se despliega con el workflow de su repo; ver
  `docs/operacion/deploy_pwas.md` ("Primera activacion de Inspecciones").
- No hay management commands propios: la carga es por el panel.

## Registros

- Decisión: `docs/registro/decisiones/2026-10-14-inspecciones-escolares-backend.md`.
- `docs/registro/cambios/2026-T4/2026-10-14-inspecciones-escolares-backend.md`
- `docs/registro/cambios/2026-T4/2026-10-14-inspecciones-anulacion-actas.md`
- `docs/registro/cambios/2026-T4/2026-10-15-inspecciones-panel-backoffice.md`
- `docs/registro/cambios/2026-T4/2026-10-15-inspecciones-tablero-en-vivo.md`
- `docs/registro/cambios/2026-T4/2026-10-15-kernel-layout-claro-barra-lateral.md`
