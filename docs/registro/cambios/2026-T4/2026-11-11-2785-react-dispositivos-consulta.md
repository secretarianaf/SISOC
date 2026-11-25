# Cambio: listado, legajo y mapa de Dispositivos en React sobre G1 v1 (#2785, DS02.01 y DS01.01)

## Alcance

Primeras pantallas del backend `dispositivos` sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): listado
(`/dispositivos/`), legajo (`/dispositivos/<pk>/`) y mapa general
(`/dispositivos/mapa/`). Contrato:
[Dispositivos DS01-DS02](../../../plans/2026-T4/2026-11-10-2785-dispositivos-ds01-ds02-contratos.md).
Sigue el patrón de las pantallas CDF
([consulta de centros](2026-11-10-2805-react-cdf-centros-consulta.md)).

Fuera de esta unidad: alta, edición y baja (DS02.02) y la previsualización y el
editor de pin (DS01.02, espera a DS02.02 y a mover el editor de VPSL a
`packages/ui`). No activa React en producción.

Archivos:

- `src/backends/dispositivos/dispositivos/web_api.py` y
  `src/backends/dispositivos/dispositivos/web_api_urls.py`: API web.
- `src/backends/dispositivos/dispositivos_runtime/web_api_urls.py`: agrupa las rutas
  `/api/web/dispositivos/` del backend; lo incluye
  `src/backends/dispositivos/dispositivos_runtime/urls.py`.
- `src/backends/dispositivos/dispositivos/views.py`: refactor autorizado por el
  contrato. Las secciones del legajo pasan a `build_detalle_secciones(dispositivo)`,
  que usan la vista nativa y la API. El HTML nativo no cambia.
- `src/backends/config/backends.json`: prefijo `api/web/dispositivos/`.
  `src/backends/config/url_registry.json` se regeneró con `generar_registro_urls`.
- `src/backends/config/middlewares/admindocs.py`: las rutas nuevas quedan fuera del
  atajo HEAD de admindocs.
- `src/backends/dispositivos/dispositivos/web_preview.py`: entrada React sin montar
  (`dispositivos_preview_patterns`), solo para un URLconf local.
- `src/frontends/apps/sisoc/src/routes/`: `dispositivos.tsx` (ruta única de la
  unidad: listado, legajo y mapa), `dispositivosMapa.tsx` (mapa),
  `dispositivosShared.tsx` (barra de acciones) y `dispositivosDetalleCss.ts` (el
  `<style>` del legajo, copiado tal cual).
- Pruebas: `src/backends/dispositivos/dispositivos/tests/test_web_dispositivos_consulta.py`,
  `src/backends/dispositivos/dispositivos/tests/test_web_dispositivos_preview.py` y
  `src/frontends/apps/sisoc/src/routes/dispositivos.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/dispositivos/listado/` | Corre `DispositivoListView`: alcance, `busqueda`, filtros combinables, orden y página de 15. Sobre de Insumos más `page_range`, `query_prefix`, configuración de filtros, `add_url`, `map_url` y permisos. Página inválida: 404 «Página no válida.» |
| `GET /api/web/dispositivos/options/` | Configuración de filtros, `titulo`, `add_url`, `map_url` y permisos de acción |
| `GET /api/web/dispositivos/<pk>/` | Corre `DispositivoDetailView`: fuera de alcance o inexistente, 404. Encabezado, migas, `detalle_secciones` y `mapa_query` solo con `ver_mapa_dispositivo` |
| `GET /api/web/dispositivos/mapa/` | Corre `DispositivoMapView`: dispositivos del mapa, provincias del alcance, filtros de estado de ubicación e `initial_device` |
| `GET /api/web/dispositivos/<pk>/ubicacion/` | Mismo cuerpo que la consulta nativa (`geolocate_dispositivo`); 503 si `unavailable`. Conserva su efecto actual: puede guardar el resultado definitivo y lo cachea |

Acceso, en este orden: sesión y requisitos web (G1: 401/403 JSON, o la constancia
firmada en el runtime), después el mismo permiso que la ruta nativa: ANY
`view_dispositivo` en listado y legajo; ALL `view_dispositivo` +
`ver_mapa_dispositivo` en mapa y ubicación. Respuestas `private, no-store`; otros
métodos, 405.

Desvío del contrato: el listado se sirve en `listado/` y no en la raíz
`/api/web/dispositivos/`. La prueba del core
`test_vertical_names_do_not_collide_with_core_web_api_routes` exige que la raíz
`/api/web/<vertical>/` no resuelva a una vista; el resto de las rutas queda igual.

Pantalla React: misma estructura que `dispositivos_list.html` (barra de búsqueda en
modo filtros, «Mapa de dispositivos», «Resetear», «Agregar dispositivo», tabla y
paginación «Volver»/«Continuar» con «Se encontraron {n} resultados»), que
`dispositivos_detail.html` (carrusel horizontal con su JavaScript, detalle completo
e iframe de Google con `ver_mapa_dispositivo`) y que `dispositivos_map.html` con
`dispositivosMap.js` (consulta en serie con 20 s por pedido, corte tras el primer
`unavailable`, filtros de estado en el cliente, paginación de 15 y textos
literales). Quirks conservados:

- La paginación del listado no arrastra `busqueda` (el componente no recibe
  `query`).
- En el legajo, el bloque «Archivos adjuntos» del template abre con `forloop.first`
  de todos los ítems, así que el separador, la etiqueta y la grilla no se ven; solo
  quedan las tarjetas sueltas. React lo reproduce.
- `<noscript>` del mapa no aplica a una SPA (diferencia de plataforma aceptada).

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo (colección: falta `build_detalle_secciones` y el
  módulo de entrada) y luego en verde (34). Suite de `dispositivos` (incluye
  DataCalle), `test_web_gate`, `test_backend_proxy`, `test_servicios_backends`,
  registro de URLs al día, colección completa sin errores, `black`, `pylint` 10/10 y
  `makemigrations --check` sin cambios.
- Diferencial: HTML nativo del legajo (con y sin datos), del listado y del mapa
  idéntico byte a byte entre la base y el candidato (token CSRF normalizado).
- Frontend: prueba de ruta en rojo (módulo inexistente) y luego en verde (11);
  Vitest del proyecto sisoc tres veces seguidas, `tsc`, ESLint y build de Vite.
- G1 de punta a punta (core y runtime en contenedores separados): las tres pantallas
  cargan por el core; anónimo 401, sin permiso 403, requisito pendiente 403, cabecera
  falsificada ignorada; consulta directa al runtime sin constancia, alterada, de otro
  destino, usuario o audiencia, vencida (61 s) o futura: 403; dentro de 58 s: 200.
- Visual (regla S13), nativo contra React, 10 estados (listado, filtrado, vacío,
  lector sin acciones, legajo completo, legajo simple, legajo sin mapa, mapa,
  mapa filtrado con dispositivo inicial, mapa vacío) en 1440x900 y 390x844:
  diferencia perceptual 0 % y desvío geométrico máximo de 0,02 px. Anónimo, sin
  permiso, lector en el mapa, página inválida e inexistente responden igual.

## Limitaciones

- Sin red, Leaflet no carga en ninguno de los dos lados: la comparación visual del
  mapa cubre el estado «No se pudo cargar el mapa.». Los estados con marcadores, la
  consulta en serie y el corte tras `unavailable` se prueban con Vitest.
- Si el último ítem de «Observaciones y documentación» (documentación adicional 4)
  tiene archivo, el template nativo cierra un `div` de más; React no reproduce ese
  HTML mal formado.
- Diferencias del marco compartido `SisocShell`, fuera de esta unidad: el logo
  tiene `aria-label` (primer paso de Tab) y en móvil cambia el orden de clases del
  `body` y el marcado del menú (menú móvil fuera de la comparación).
- Qué proceso sirve `/media/` para este dueño en despliegue separado sigue sin
  definirse (no hay prefijo `media/` para `dispositivos`); se conserva lo actual.
