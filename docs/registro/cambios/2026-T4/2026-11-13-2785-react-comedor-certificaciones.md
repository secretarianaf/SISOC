# Cambio: historial de certificaciones mensuales de un comedor en React (#2785, CO05.01)

## Qué cambia

- **API.** `GET /api/web/comedores/comedores/<id>/certificaciones-prestaciones/`
  (`src/backends/comedores/comedores/web_api_certificaciones.py`, incluida desde
  `src/backends/comedores/comedores_runtime/web_api_urls.py`) corre `CertificacionesPrestacionesHistorialView`
  con su `setup()`, `get_queryset()` y `get_context_data()`: comedor dentro del alcance del usuario (404 si no),
  filtros `periodo` (`YYYY-MM`, inválido se ignora), `usuario` (solo dígitos) y `conforme` (`true`/`false`),
  orden `-periodo, -creado`, 20 por página y página inválida 404. Cada texto sale con la expresión de
  `certificaciones_prestaciones_historial.html` (`m/Y`, `d/m/Y H:i` en hora local, nombre completo con
  alternativa al usuario). Acceso igual que hoy: `comedores.view_comedor` o `admisiones.view_admision`. Es de
  solo lectura y consume los mensajes pendientes como la página nativa.
- **React.** `src/frontends/apps/sisoc/src/routes/comedorCertificaciones.tsx` dibuja el formulario de filtros
  (GET nativo, «Filtrar» y «Limpiar»), la tabla con las insignias «Conforme» / «No conforme», «Ver PDF» o
  «No disponible», y la paginación compartida, con el mismo encabezado y migas de pan que la página nativa.
- `src/backends/comedores/comedores/web_preview_certificaciones.py` mantiene la URL nativa con su guarda y
  devuelve el índice React. Se agregó la ruta a `_OWNED_PATTERNS` y a `url_registry.json`.
- **Se conserva sin cambios.** El PDF sigue siendo la descarga binaria nativa
  (`descargar_certificacion_prestaciones_web`, con su permiso y su 404 sin archivo): el enlace «Ver PDF» apunta
  a esa ruta y no se mueve el archivo al cliente. La conformidad la genera la API de la PWA; esta pantalla no
  ofrece crear ni regenerar nada. No se extiende CDI-F2 ni se afirma aislamiento adicional en la descarga.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): filas con formato y orden nativos, filtros válidos e inválidos,
  20 por página y página inválida 404, 401/403/404, `POST` rechazado sin escribir, otros comedores fuera de la
  lista, y entrada de vista previa; pruebas del core (puerta web, proxy, servicios).
- Vitest, tsc, eslint y build sin avisos. G1 y visual S13 contra la página nativa.

## Limitaciones y diferencias conocidas

- La ruta React solo existe en la vista previa.
- La descarga del PDF resuelve la conformidad por ID y comedor sin repetir el alcance del historial; se
  conserva y documenta esa diferencia (contrato CO05).
