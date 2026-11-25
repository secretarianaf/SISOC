# Sedes e Itinerarios VPSL: filtros y paginación en React canónico (#2785)

El listado `/ver-para-ser-libre/sedes/` conserva la búsqueda simple,
los filtros combinables y la paginación de Django al mostrar React.
Itinerarios se agregó después con el mismo patrón (sección propia). La activación global queda fuera.

## Contrato y funcionamiento

- La navegación HTML mantiene la URL canónica y su permiso `view_sedevpsl`.
  Un build sin el marcador `sisoc-vpsl-sedes=v1` devuelve el HTML nativo.
  Desactivar `vpsl` conserva el mismo rollback. El marcador anterior de T7
  permanece en el build, pero no acredita soporte de estos controles.
- `CanonicalSedesListView` hereda el queryset, orden y paginación de
  `SedeListView`. No duplica filtros, cambia alcance provincial ni escribe datos.
- La misma URL admite la representación `Accept: application/json` para
  React. Devuelve filas, total, página, páginas, tamaño y configuración de
  controles. Ambas representaciones son privadas, `no-store`, con
  `Vary: Accept, Cookie`. La autorización ocurre antes de entregar cualquiera.
- `busqueda` conserva nombre, CUE/anexo, jurisdicción, localidad y domicilio.
  `filters` conserva el JSON y los operadores de `AdvancedFilterEngine`,
  incluido OR dentro del mismo campo y AND/OR entre campos.
- React aplica los parámetros en la URL. Cambiar filtros elimina `page`;
  paginar conserva filtros; limpiar elimina búsqueda, filtros y página.
  Recarga y navegación atrás/adelante restauran los controles. La página
  efectiva la decide Django, incluido `page=last`; las páginas inválidas
  conservan 404.
- `/v2/vpsl/` mantiene sus controles, su API con `q` y sus enlaces.
  `?sede=<id>` sigue abriendo el detalle en el router canónico.

## Verificación

- RED observado: el transporte canónico devolvía HTML al pedir JSON.
  GREEN: 16 coincidencias combinadas, una fila en página 2, mismo orden,
  total y selección que el HTML nativo.
- RED observado: el frontend ignoraba filtros y página del enlace directo.
  GREEN: carga canónica, controles restaurados, limpieza, paginación y
  navegación atrás/adelante; sin usar la API de listado V2.
- Pytest cubre permisos y denegaciones sin mutación, filtros inválidos,
  agrupación, paginación, HEAD, rollback, build incompatible y contrato V2.
- Vitest y build de VPSL ejecutados en instalación local aislada y offline.
  El primer build detectó una prop de MUI no admitida; se corrigió con `sx`.
- Prueba TCP con login sintético, build congelado y SQLite independiente:
  HTML y JSON 200, total 16, página 2, fila `Escuela 15`, `Vary` correcto.
- Evidencia del coordinador con Chrome headless, 1440×900 y 390×844:
  anónimo 403; enlace directo, fila única y total esperados; búsqueda
  restaurada, recarga, foco en página anterior + Enter, atrás a página 2
  y limpieza de query. Sin llamadas al listado V2 ni errores de página.

## Límites

El host CUA no estuvo disponible para abrir un navegador visible durante
esta unidad. El coordinador comprobó el flujo con Chrome headless; eso
no constituye una demostración visible ni aceptación humana.
Black no estaba instalado en el venv compartido ni en PATH. El coordinador
encontró Black 26.10.1 en la caché local de uv; se utilizó con `uvx --offline`
para normalizar los archivos Python del corte, sin cambios semánticos ni
churn fuera de las secciones nuevas. No se publicaron commits, PRs ni despliegues.

## Itinerarios (T9b)

- `/ver-para-ser-libre/` exige `view_itinerariovpsl`, `view_all_itinerarios_vpsl`
  o `create_itinerarios_any_province_vpsl`, como antes. React solo se sirve con
  el marcador `sisoc-vpsl-itinerarios=v1`; el marcador T7 no alcanza.
- `CanonicalItinerariosListView` hereda `ItinerarioListView`: el alcance
  territorial (`services/access.py`) se aplica antes de búsqueda, filtros
  simples y avanzados. Ni `provincia` ni un `filters` con OR amplían el alcance.
- JSON con `Accept: application/json`: total, página, páginas, tamaño 10,
  filas, `filters_config`, estados, provincias y provincia restringida.
  Privado, `no-store`, `Vary: Accept, Cookie`.
- Se conservan `busqueda`, `buscar_por`, `estado`, `provincia`, `localidad`,
  `fecha_desde`, `fecha_hasta`, `page` y `filters`. El `localidad` simple y el
  avanzado mantienen su semántica distinta. `/v2/vpsl/` sigue usando `q`.
- Pytest compara IDs, orden y total contra el HTML nativo con flag OFF para
  búsqueda por campo, solapamiento de fechas, filtro inválido y alcance por
  permiso; también marcador, flag y aislamiento del transporte.
- Pendiente: navegador real (escritorio/móvil/teclado) sobre este corte.
