# Inspecciones escolares: tablero en vivo de coordinación

Fecha: 2026-10-15. Rama: `feat/inspecciones-tablero` (se integra en el PR del
panel de Inspecciones). Fuente funcional: especificación §9 (dashboard) y §15
(resultados del formulario), en el repo de la PWA.

## Qué cambia

Rutas nuevas en el backend `inspecciones` (mismo prefijo `/inspecciones/`):

| Ruta | Nombre | Qué hace |
|---|---|---|
| `tablero/` | `inspecciones_tablero` | Página: filtros, indicadores, mapa, gráficos y últimas actas. |
| `tablero/datos/` | `inspecciones_tablero_datos` | JSON con todo el tablero para los filtros del querystring. |
| `tablero/exportar.csv` | `inspecciones_tablero_exportar` | CSV de las actas válidas con los mismos filtros. |

Las tres exigen `puede_gestionar_inspecciones` (coordinación o el permiso
`inspecciones.gestionar_inspecciones`); sin permiso, 403.

- Filtros: `fecha` (jornada de la visita; por defecto hoy en Argentina),
  `provincia`, `localidad` (de SISOC, vinculadas a la escuela), `inspector`,
  `turno` y `notificacion` (`pendiente` o `cargada`). Un valor inválido se
  ignora. Los mismos filtros arman un único queryset
  (`services/tablero.py::actas_validas`) que alimenta indicadores, mapa, tabla
  y CSV, así que siempre coinciden.
- Sólo cuentan las actas válidas: `estado = finalizada` y `es_prueba = False`.
  Los borradores con datos de la jornada se informan aparte ("avance
  provisional, no suma"); el filtro de notificación no les aplica.
- Escuelas únicas: por escuela del catálogo; las de carga manual, por CUE.
- Inspectores con actividad: con acta válida o borrador en la jornada, sobre
  los usuarios activos con rol `inspector`.
- Ausentismo observado = (Σ previsto − Σ presente) / Σ previsto y aulas en
  funcionamiento = Σ funcionando / Σ previstas, sólo con actas constatadas
  (total o parcial), los dos valores como dato y el denominador mayor que cero.
  Cero es un dato. Se informan las computables y las excluidas por motivo.
- Presencia de personal y de estudiantes: Sí, No, No constatado y Sin dato por
  separado, con su denominador. El tablero muestra "El personal incluye
  docentes y no docentes; no equivale a adhesión al paro".
- Mapa: sólo puntos con `ubicacion.fuente = gps` y coordenadas válidas. Las
  actas con ubicación manual o sin ubicación no se ubican (la especificación
  prohíbe inferirlas de la dirección) y se cuentan en la leyenda.
- CSV: `;` y BOM, una fila por acta válida, columnas fijas
  (`services/tablero.py::columnas_csv`) con la etiqueta de cada pregunta F05–F16
  del formulario v1; sin imagen de firma ni links a archivos; neutraliza
  fórmulas.

## Tiempo real

La página consulta `tablero/datos/` cada 5 segundos (sin WebSockets ni SSE:
gunicorn síncrono y sin Redis), pausa con la pestaña oculta
(`visibilitychange`), muestra "En vivo · actualizado hace N s", avisa la
desconexión con la hora de la última consulta correcta y reintenta. Un acta
nueva queda marcada "nueva" unos segundos en la tabla.

La respuesta se cachea 2 segundos por combinación de filtros con el cache de
Django (hoy `LocMemCache`, por proceso). Con N workers, la base recibe a lo
sumo N cálculos cada 2 segundos por combinación de filtros, sin importar
cuántos coordinadores miren el tablero.

Con esos valores, un acta cerrada aparece en el tablero como máximo 7 segundos
después (intervalo más cache). Arrancó en 10 s y 5 s; en la prueba local de
punta a punta se midieron 10,4 s, por encima del objetivo de menos de 10 s.

Eficiencia: 7 consultas por cálculo, sin importar el volumen (agregados en la
base y una sola lectura del conjunto filtrado, que de la `instantanea` trae
sólo `ubicacion`, `respuestas`, `firma` y `escuela`, no el formulario ni las
imágenes).

## CDN, CSP y teselas

- Leaflet 1.9.4 y Leaflet.markercluster 1.5.3 desde `cdn.jsdelivr.net` (el
  mismo CDN de ApexCharts y Chart.js), con versión fija e integridad SRI
  `sha256` como el resto de los scripts de jsdelivr del backoffice.
- Teselas del mapa oficial del Instituto Geográfico Nacional (Argenmap, TMS:
  `https://wms.ign.gob.ar/geoserver/gwc/service/tms/1.0.0/capabaseargenmap@EPSG%3A3857@png/{z}/{x}/{-y}.png`),
  con su atribución y sin el prefijo de Leaflet. Rotula "Islas Malvinas (Arg.)";
  reemplazó a OpenStreetMap el 15/10/2026. El mapa no se puede alejar más allá
  de Argentina (zoom mínimo = el que la muestra entera, `maxBounds`).
- CSP (`config/middlewares/csp.py`): no hizo falta cambiarla. `script-src` y
  `style-src` ya permiten `https://cdn.jsdelivr.net`; las teselas son imágenes
  y `img-src` ya permite `https:`; el JSON del tablero es del mismo origen
  (`connect-src 'self'`). La página no usa scripts ni estilos en línea (el JS
  y el CSS son estáticos y los colores y tamaños dinámicos se fijan por CSSOM o
  clases), así que también funciona con `CSP_ALLOW_UNSAFE_INLINE_SCRIPTS=false`.
- Verificado en Chrome con la CSP en modo estricto y sin report-only: mapa,
  teselas, agrupamiento, popups, consulta periódica, pausa, desconexión y
  reconexión funcionan. Las únicas violaciones que quedan son previas a este
  cambio: atributos `style` de la plantilla base y los que agrega ApexCharts
  3.37.1 al dibujar (los gráficos se ven igual). Si se pasa la CSP a modo
  estricto en producción, eso hay que resolverlo para todo el backoffice.

## Archivos

- `inspecciones/services/tablero.py`, `inspecciones/views_tablero.py`,
  rutas al final de `inspecciones/urls.py`.
- `inspecciones/templates/inspecciones/tablero.html` (incluye
  `inspecciones/_pestanas.html` con `activa="tablero"`).
- `inspecciones/static/inspecciones/tablero/tablero.js` y `tablero.css`.
- `src/backends/config/url_registry.json` regenerado.
- Tests: `src/backends/inspecciones/tests/test_inspecciones_tablero.py`. La
  prueba de volumen (64.000 escuelas y 1.000 actas) se corre con
  `INSPECCIONES_TABLERO_VOLUMEN=1`.
