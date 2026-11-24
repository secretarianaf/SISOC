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

