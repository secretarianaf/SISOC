# Celiaquía: reporte provincial en su URL canónica (#2785)

El reporte React existente puede servirse en `/reporter-provincias/` sin
redirigir a `/v2/`. Esta entrega no migra expedientes, cupos, pagos ni el
tablero de seguimiento de Celiaquía.

## Activación y retorno

1. Usar un build de `front_celiaquia` con el marcador
   `sisoc-celiaquia-report=v1`. Seleccionar explícitamente `celiaquia` en
   `REACT_VERTICALES_ACTIVAS` del runtime de Celiaquía.
2. Abrir el Reporte desde el menú normal y verificar una sesión con
   `celiaquia.view_reporte_provincias` y otra sin ese permiso. El API de
   reporte sigue aplicando el alcance territorial existente.
3. Para volver a Django, retirar la clave del runtime. Ante un build
   anterior, ausente o con error, el backend también entrega Django.
   `/v2/celiaquia/reporte` sigue disponible con la navegación previa.

## Contrato

El guard de la ruta precede al proxy. Solo GET y HEAD autorizados buscan
el HTML fijo del build, sin enviar los parámetros del reporte al estático.
La respuesta es privada y no almacenable; HEAD no entrega cuerpo. Los
parámetros de provincia, fechas, expediente, documento, revisión, SINTYS,
cupo y página se conservan al aplicar filtros, paginar y recargar. La
búsqueda rápida actúa solo sobre las filas de la página cargada; no
consulta al API ni altera sus totales. El enlace de documento conserva la
URL canónica del expediente, donde Django vuelve a controlar el acceso.

Los resúmenes de revisión, SINTYS y cupo aplican el filtro nativo y
vuelven a la primera página, igual que el ranking por provincia. Las filas
sin provincia no son acciones y el ranking solo permite filtrar fuera del
alcance provincial. Se conserva el borrador de los demás controles, como
en el formulario Django, y el historial del navegador recupera la consulta
anterior. El detalle muestra la etiqueta de rol y la marca Dupla que ya
calcula Django. Los tres campos nuevos del caso en el API son opcionales;
no cambian la consulta territorial ni las reglas de clasificación.

## Verificación y límites

Pruebas aisladas del permiso, ruta exacta, fallback, HEAD, filtros y
paginación. En Chrome local (1440×900 y 390×844), con Django, API y datos
sintéticos, se verificaron la denegación sin sesión, entrada autorizada,
enlace filtrado, búsqueda rápida, aplicación con Enter y recarga. El
proxy sirvió el build real sin recibir los parámetros de negocio. No fue
una demostración visible ni aceptación humana. La comparación visual
integral contra Django queda pendiente. No se habilitó ningún entorno remoto.

## Listado de Expedientes

- `/celiaquia/expedientes/` mantiene `permissions_any_required(["celiaquia.view_expediente"])`
  y pasa por `canonical_expedientes`. Con `celiaquia` activo, GET/HEAD HTML
  sirve el build solo si trae el marcador `sisoc-celiaquia-expedientes=v1`;
  sin flag, build ausente, 404 o HTML incompatible vuelve la vista Django.
  El servidor estático no recibe la query.
- `Accept: application/json` proyecta el contexto de `ExpedienteListView`:
  mismo alcance por rol (admin/coordinador, provincial, técnico, propietario),
  `q` y `filters` aplicados después del alcance y **sin paginar**, porque
  `get_paginate_by()` devuelve `None`.
- Las acciones siguen las reglas del template nativo: alta solo provincial;
  editar/procesar en `CREADO`; confirmar envío en `EN_ESPERA`; recepcionar en
  `CONFIRMACION_DE_ENVIO`, eliminar y asignar técnicos solo para gestión.
  Las URLs apuntan a las vistas Django existentes, que vuelven a validar.
- Respuesta privada, `no-store`, `Vary: Accept, Cookie`.
- Pytest: alcance, filtros, acciones, guarda antes de JSON/estático, fallback
  y HEAD sin cuerpo. Vitest: query canónica sin usar el listado V2, sin
  acciones inventadas ni truncar filas. Build de Celiaquía correcto.
- Pendiente: navegador real; alta, detalle y edición canónicos; cupos, pagos
  y tablero. `ExpedienteUpdateView` sigue sin restricción territorial ni de
  estado (diferencia preexistente con DRF); no se modificó en este corte.

## Puente canónico genérico (resto de Celiaquía)

- `celiaquia/canonical_shell.py` generaliza el puente: `canonical_screen(vista_nativa,
  pantalla, projection=None, submit=None)`. Con `celiaquia` activo, GET/HEAD
  sirve el build solo si declara `sisoc-celiaquia-<pantalla>=v1`; `Accept:
  application/json` usa la proyección y un POST JSON usa `submit` si existe.
  Todo lo demás, y siempre sin flag, sigue en la vista Django. El decorador de
  permiso de cada URL corre antes. Se fija la cookie CSRF para las mutaciones.
- Envueltas en `urls.py`: alta, detalle y edición de expedientes; cupos y cupo
  por provincia; tablero; listado y detalle de pagos. Cada URL conserva
  exactamente la autorización que ya tenía.
- React elige la pantalla por URL en `canonical/screens.tsx` (sin basename
  `/v2`), con `canonical/transport.ts` para leer la proyección y enviar
  mutaciones a los endpoints nativos sin reintentos automáticos.
- Cada pantalla se habilita recién cuando su marcador entra en `index.html`;
  un build anterior sigue mostrando Django.
- Pruebas: `test_canonical_shell.py` (flag, marcador propio, guarda antes del
  shell, hooks solo para JSON) y suite completa de Celiaquía en verde.

## Alta y edición de Expedientes

`/celiaquia/expedientes/nuevo/` y `/celiaquia/expedientes/<pk>/editar/`: la
proyección y el guardado JSON ejecutan las propias `ExpedienteCreateView` y
`ExpedienteUpdateView` (misma búsqueda del objeto, mismo `ExpedienteForm` con
`.xlsx` y 5 MB, mismo servicio y URL de éxito). Un POST no JSON sigue llegando
a Django. Incluye vista previa con límite elegible, buscador de localidades con
CSV, plantilla, errores accesibles y sin reintentos automáticos. Diferencias:
el buscador es un panel en la página (no modal) y la vista previa muestra
texto plano (Django insertaba HTML).

## Cupos

`/celiaquia/cupos/` y `/celiaquia/cupos/provincia/<id>/`: proyección con
`CupoService.filas_dashboard` y el helper `contexto_provincia`, extraído de la
vista nativa sin cambiar su comportamiento. React replica tablero, métricas,
tablas con filtros, histórico y los modales de configurar, suspender, dar de
baja y reactivar, contra los endpoints nativos. "Generar expediente de pago"
sigue siendo un POST nativo con redirección. La columna "Expediente" queda
vacía como en Django (el template usa `expediente.codigo`, que no existe).

## Pagos y Tablero

`/celiaquia/pagos/provincia/<id>/`, `/celiaquia/pagos/expediente/<id>/` y
`/celiaquia/tablero/`: proyecciones con el queryset, el lookup y
`construir_tablero()` nativos. La respuesta de pago se sube con POST multipart
a la vista nativa. El enlace al expediente del Tablero sigue limitado a
`view_expediente`. Los gráficos son barras CSS (sin librería de gráficos).

## Detalle de Expediente

`/celiaquia/expedientes/<pk>/`: la proyección usa el contexto de
`ExpedienteDetailView`, así que alcance por rol, 404 e indicadores son los
nativos. Todas las acciones (revisión, subsanación, Renaper, archivos,
comentarios, cruce, confirmación, registros erróneos, asignación de técnico)
van a los endpoints Django sin reintentos. `preview_limit` e `historial_page`
viven en la URL; el historial ahora navega todas sus páginas (Django solo
mostraba la primera). Faltan: autoguardado de registros erróneos (hay botón
"Guardar cambios"), contador de progreso al procesar y selectores con búsqueda.

## Observaciones de seguridad preexis## Observaciones preexistentes (sin cambios)

- La migración no modifica permisos. Las observaciones de autorización
  detectadas durante la paridad se registraron por el canal interno.
- "Confirmar envío" nunca se deshabilita con registros erróneos en Django
  (`registros_erroneos.count` sobre una lista); valida el endpoint.

quía pytest 772, Vitest 123, typecheck, ESLint sin errores y build
correctos. Sin prueba en navegador real, por pedido explícito.

## Verificación independiente

Sin bloqueantes en guardas, alcance, proxy ni CSRF: 7 URLs con guarda ×
GET/HEAD/POST × JSON/HTML, anónimo y sin permiso, responden 302/403 sin datos
ni llamadas al servidor estático; el detalle fuera de alcance da 404. Encontró
un bloqueante corregido: con la vertical apagada el puente agregaba
`Cache-Control` y `Vary: Accept` (y la cookie CSRF) a la respuesta nativa.
Ahora, sin flag, la vista nativa responde sin envolver; la comparación contra
la base `26bd7cbb7` da headers y tamaño idénticos en las 9 URLs. Con flag y
build sin marcador se agregan `private, no-store` y `Vary: Accept`, correctos
porque la URL también sirve JSON. Se incorporaron `test_flag_off_keeps_native_headers`
y el barrido `test_canonical_guards_sweep.py`. Celiaquía pytest 781.

## Activación

`canonical_shell.react_enabled()` usa la misma semántica que
`core.react_activation`: Celiaquía se activa con `todas` (el valor por defecto
cuando `REACT_VERTICALES_ACTIVAS` no está definida) o con la clave `celiaquia`;
`ninguna`, una variable vacía o una lista sin `celiaquia` la apagan. El reporte
provincial usa la misma función. No se registra en `REGISTRO` porque esas
entradas montan rutas `web_preview` con assets propios, y Celiaquía sirve el
build `/v2/celiaquia/` desde sus vistas canónicas. Rollback: definir la
variable sin `celiaquia`; las pantallas vuelven a Django sin desplegar código.
