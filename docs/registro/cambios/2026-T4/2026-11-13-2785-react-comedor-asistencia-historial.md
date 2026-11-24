# Cambio: historial de asistencia de la nómina de un comedor en React (#2785, CO01)

## Qué cambia

- **API.** `GET /api/web/comedores/comedores/<id>/admision/<admision>/nomina/asistencia/`
  (`src/backends/comedores/comedores/web_api_asistencia_historial.py`, incluida desde
  `src/backends/comedores/comedores_runtime/web_api_urls.py`) corre `NominaAsistenciaHistorialView` con su
  `setup()` y `get_context_data()`: comedor y admisión dentro del alcance del usuario (404 si la admisión no es
  del comedor), lista de meses con su cantidad de asistentes y el último documento generado, y, con
  `?periodo=`, los asistentes de ese mes. Cada texto sale con la expresión de
  `nomina_asistencia_historial.html` (`m/Y`, `d/m/Y H:i` en hora local, `default`). Acceso igual que hoy:
  `comedores.view_nomina`. Es de solo lectura y consume los mensajes pendientes como la página nativa.
- **React.** `src/frontends/apps/sisoc/src/routes/comedorAsistenciaHistorial.tsx` dibuja la lista de periodos
  («Descargar PDF», «Ver detalle») y el detalle con la tabla de asistentes («Ver periodos»), con el mismo
  encabezado y migas de pan que la página nativa.
- `src/backends/comedores/comedores/web_preview_asistencia.py` mantiene la URL nativa con su guarda y devuelve
  el índice React. Se agregó la ruta a `_OWNED_PATTERNS` y a `url_registry.json`.
- **Se conserva sin cambios.** La escritura de la asistencia mensual y el PDF de destinatarios siguen en los
  productores de la PWA (token, ventana de carga, documento único por período); el PDF se descarga con el
  enlace nativo al archivo (`archivo.url`), sin moverlo al cliente. La pantalla no ofrece cargar, corregir ni
  regenerar nada.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): lista de meses, detalle con formatos y orden nativos, período
  inválido que vuelve a la lista, enlace al último documento, 401/403/404 (admisión ajena incluida), `POST`
  rechazado sin escribir, filas de otra admisión y nóminas dadas de baja fuera del conteo, y entrada de vista
  previa; pruebas del core (puerta web, proxy, servicios).
- Vitest, tsc, eslint y build sin avisos. G1 y visual S13 contra la página nativa (lista, detalle, detalle
  vacío y lista vacía; escritorio y móvil).

## Limitaciones y diferencias conocidas

- La ruta React solo existe en la vista previa.
- Una fila de documento sin archivo no muestra enlace; la página nativa fallaría ahí (`archivo.url` sin
  archivo).
- Los datos de cada asistente se leen del ciudadano actual, no de una foto del período, igual que la página
  nativa.
