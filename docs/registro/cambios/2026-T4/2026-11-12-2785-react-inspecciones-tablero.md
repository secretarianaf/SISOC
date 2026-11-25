# Cambio: Tablero de Inspecciones en React sobre G1 v1 (#2785, IN03)

## Alcance

Familia IN03 del
[contrato de Inspecciones](../../../plans/2026-T4/2026-10-28-2785-inspecciones-circuitos-m2.md)
(sección «Tablero IN03 y actas IN04»): el tablero en vivo
(`/inspecciones/tablero/`) con filtros, indicadores, mapa, barras, índices,
últimas actas, actualización cada 5 s, exportación CSV y descarga de actas
(PDF o ZIP). Sigue el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md) y el patrón de
las demás pestañas de Inspecciones ([Asignaciones](2026-11-12-2785-react-inspecciones-asignaciones.md),
[Escuelas](2026-11-10-2785-react-inspecciones-escuelas.md)).

No cambia vistas, servicios, plantillas ni el JavaScript nativos
(`tablero.js` sigue sirviendo la página nativa). No activa React en producción.
Las cifras no se recalculan en el cliente ni en la API: todos los consumidores
(página nativa, React, CSV y ZIP) leen el mismo resultado de
`inspecciones.services.tablero`.

Archivos:

- `src/backends/inspecciones/inspecciones/web_api_tablero.py`: la cáscara y las
  tres rutas que devuelven la respuesta de la vista nativa sin tocarla; rutas en
  `src/backends/inspecciones/inspecciones/web_api_urls.py`.
- `src/backends/inspecciones/inspecciones/web_preview.py`: entrada sin montar
  `TableroEntry`.
- `src/backends/config/middlewares/admindocs.py` (un patrón) y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/`: `inspeccionesTablero.tsx` (ruta),
  `inspeccionesTableroPage.tsx` (pantalla y consulta periódica),
  `inspeccionesTableroMapa.tsx` y `inspeccionesTableroLeaflet.ts` (mapa),
  `inspeccionesTableroApi.ts` (contrato y validación). `Screen` de
  `inspeccionesEscuelasPage.tsx` admite el título.
- Pruebas: `src/backends/inspecciones/tests/test_web_tablero.py` y
  `src/frontends/apps/sisoc/src/routes/inspeccionesTablero.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/inspecciones/tablero/` | Corre `TableroView`: migas, pestañas, filtros ya validados (un valor inválido se ignora; la fecha por omisión es hoy), opciones de provincia, inspector, turno y notificación, el intervalo (5000 ms), las URLs y los mensajes pendientes |
| `GET /api/web/inspecciones/tablero/datos/` | La respuesta de `TableroDatosView` sin cambios: el mismo JSON, `no-store`, solo GET |
| `GET /api/web/inspecciones/tablero/exportar.csv` | La respuesta de `TableroExportarView`: el mismo CSV con los filtros aplicados, adjunto y `no-store`, solo GET |
| `GET /api/web/inspecciones/tablero/descargar-actas/` | La respuesta de `TableroDescargarActasView`: una acta como PDF o varias como ZIP, `private, no-store` y `nosniff`. Sin nada que descargar encola el aviso nativo y redirige al tablero con los filtros (nunca un archivo vacío) |

Los otros métodos responden 405. Acceso: 401 sin sesión, 403 por requisitos web
o sin `puede_gestionar`, y las lecturas no escriben. Un POST a cualquiera de
estas rutas es 405.

Pantalla React: reproduce `tablero.js`. La primera lectura marca «Conectando…»
y deja los marcadores de la plantilla («–», «Cargando…»); luego consulta cada
`intervalo_ms`, se pausa con la pestaña oculta («En pausa (pestaña oculta)») y al
volver lee de nuevo («Actualizando…»). Si una lectura falla (red, 5xx o una
respuesta con otra forma) muestra «Sin conexión», el aviso con la hora de la
última consulta correcta y reintenta; un 401/403 avisa que la sesión venció.
Las cifras de la última lectura buena quedan a la vista. Al cambiar un filtro
vacía lo que la nativa vacía (localidad al cambiar la provincia, marcas de
«nueva», ajuste del mapa), actualiza la URL con `replaceState` y los enlaces de
CSV y de descarga, y lee otra vez. Las actas que llegan después de la primera
lectura llevan la marca «nueva» durante 8 s.

Mapa: Leaflet 1.9.4 y markercluster 1.5.3 se cargan desde los mismos archivos
del CDN y con los mismos hashes de integridad que la página nativa (no se
empaquetan), con las teselas del IGN; los grupos se colorean según cuántas
visitas fueron constatadas y el popup se arma con `textContent`. Si las
librerías no cargan, el contenedor dice «No se pudo cargar el mapa.», como la
nativa. La hoja `tablero.css` y las de Leaflet se suman después de `panel.css`,
en el orden de la nativa. El CSV y el ZIP son enlaces al backend, no un archivo
generado en el navegador.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo (21 de 22) y luego en verde (22). Incluyen que
  el JSON, el CSV y el ZIP coinciden con la ruta nativa, que cifras, filas,
  mapa, CSV y ZIP cuentan las mismas 4 actas sin la anulada ni la de prueba y
  los avisos de «sin actas», «sin PDF» y tope.
- Frontend: pruebas nuevas en rojo (12 de 13, sin la ruta registrada) y luego en
  verde (14, con reloj simulado), con un `window.L` simulado para el mapa;
  Vitest del proyecto `sisoc` completo, `tsc`, ESLint sin avisos nuevos y build.
- Visual (regla S13) en 1440x900 y 390x844: tablero, tablero filtrado por
  provincia y turno, tablero de una fecha sin actas y el estado «Sin conexión»
  (consulta de datos bloqueada). 8 de 8 casos con diferencia perceptual de
  0,000 %, desvío geométrico de 0,02 px como máximo y el mismo orden de Tab.
  Guardas iguales (anónimo y sin permiso). La fecha se congeló en el navegador
  para que «actualizado hace N s» no dependa del reloj.
- G1 de punta a punta: core y runtime en dos contenedores gunicorn. Anónimo 401,
  sin permiso 403, requisito pendiente 403 con `state`, header del cliente
  descartado, datos y CSV por core → compuerta → runtime, descarga sin PDF con
  302 al tablero y POST 405.

## Limitaciones

- Sin red no se pudo ver el mapa con las librerías cargadas: la comparación
  visual vio el estado «No se pudo cargar el mapa.» de los dos lados. La rama con
  mapa se probó con un `window.L` simulado (puntos, color, grupos, popup como
  texto, ajuste de límites) y falta mirarla con el CDN real.
- No se probó una descarga real de PDF o ZIP a través del core (sin archivos
  reales en el entorno): el contrato exige 100 actas y 250 MB como tope.
- Roboto quedó bloqueada sin red en los dos lados; el menú móvil abierto está
  fuera de la comparación.
