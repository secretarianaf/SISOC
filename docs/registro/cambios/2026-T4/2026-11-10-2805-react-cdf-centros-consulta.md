# Cambio: consulta de centros CDF en React sobre G1 v1 (#2805, CDF04.01)

## Alcance

Primera pantalla del backend CDF (Centro de Familia) sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): listado
de centros (`/centrodefamilia/centros/`) y ficha
(`/centrodefamilia/centros/<pk>/`), con el panel «Usuarios del centro» (CR1)
como pedido aparte. Contrato:
[consulta de centros CDF](../../../plans/2026-T4/2026-10-27-2805-contrato-lectura-cdf.md).
Sigue el patrón de las pantallas CDI
([reportes](2026-11-10-2785-react-cdi-reportes.md)).

No cambian las vistas, formularios, servicios, plantillas ni el JavaScript
nativos, ni la API con clave (`/api/centrodefamilia/`). No activa React en
producción.

Archivos:

- `src/backends/cdf/centrodefamilia/web_api.py` y
  `src/backends/cdf/centrodefamilia/web_api_urls.py`: API web.
- `src/backends/cdf/cdf_runtime/web_api_urls.py`: agrupa las rutas
  `/api/web/cdf/` del backend; lo incluye `src/backends/cdf/cdf_runtime/urls.py`.
- `src/backends/config/backends.json`: prefijo `api/web/cdf/` del backend `cdf`.
  `src/backends/config/url_registry.json` se regeneró con `generar_registro_urls`.
- `src/backends/config/middlewares/admindocs.py`: las rutas nuevas quedan fuera
  del atajo HEAD de admindocs.
- `src/backends/cdf/centrodefamilia/web_preview.py`: entrada React sin montar
  (`cdf_preview_patterns`), solo para un URLconf local.
- `src/frontends/apps/sisoc/src/routes/`: `cdfCentros.tsx` (rutas, listado y
  ficha), `cdfFrame.tsx` (carga de sesión y datos, marco oscuro) y
  `cdfFilters.tsx` (filtros combinables con campos booleanos).
- Pruebas: `src/backends/cdf/tests/test_web_cdf_centros.py`,
  `src/backends/cdf/tests/test_web_cdf_preview.py` y
  `src/frontends/apps/sisoc/src/routes/cdfCentros.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/cdf/centros/` | Corre `CentroListView`: mismo alcance por actor, `busqueda`, filtros combinables, orden `-id` y paginación NoCount de 10. Envolvente con `count: null` y `pages: null` |
| `GET /api/web/cdf/centros/<pk>/` | Corre `CentroDetailView`: misma regla de ficha (403 fuera de regla, 404 inexistente o dado de baja), métricas, pestañas, paginaciones y archivos CABAL. Sin credenciales |
| `GET /api/web/cdf/centros/<pk>/usuarios/` | Regla de ficha y después `puede_ver_usuarios_cdf`; solo `username`, nombre, email, estado y contraseña temporal |

Respuestas JSON `private, no-store` con `Vary: Cookie`; otros métodos, 405. Solo
lectura.

Acceso, en este orden: sesión y requisitos web (G1: 401/403 JSON, o la
constancia firmada en el runtime), después `centrodefamilia.view_centro` con el
mismo predicado que `permissions_any_required`. Se conservan las reglas actuales
sin agregar alcance (ver
[brechas conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)):
«Editar» y «Agregar» se muestran como hoy y la ruta destino decide.

La API usa las vistas nativas en lugar de extraer helpers a
`services/centro_service` (variante del contrato): así no se toca la vista HTML
y el contexto no puede divergir. Los textos se proyectan como los dibuja la
plantilla (por ejemplo, una calle vacía se ve «None», como hoy).

Pantalla React: misma estructura que `centro_list.html` (buscador en modo
filtros, botones de SSE, tabla con orden local de `listSort.js`, baja con el
POST nativo y la confirmación nativa, paginación «Volver»/«Continuar» sin total)
y que `centro_detail.html` (pestañas, modal de actividad, mapa de Google solo con
URL `https://maps.google.com/maps?q=`). Los buscadores de actividades recargan
la página como `centrodefamilia.js`. El panel CR1 se pide aparte y solo vive en
memoria del componente.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo (35 de 38; la entrada sin módulo) y luego en
  verde. Suite CDF (179), `test_web_gate`, `test_backend_proxy`,
  `test_servicios_backends` (82), registro de URLs al día, colección completa sin
  errores, `black`, `pylint` 10/10 y `makemigrations --check` sin cambios.
- Frontend: prueba de ruta en rojo (módulo inexistente) y luego en verde (13);
  Vitest del proyecto sisoc, `tsc`, ESLint y build de Vite.
- Visual (regla S13), nativo contra React, 10 estados (listado, página 2, vacío,
  filtrado, ficha adherido, FARO, pestaña «Todas», búsqueda «en curso», panel de
  usuarios, listado del referente) en 1440x900 y 390x844: diferencia perceptual
  0 % y desvío geométrico máximo de 0,03 px. Anónimo, sin permiso, fuera de
  alcance e inexistente responden igual (403/404).

## Limitaciones

- Diferencias del marco compartido `SisocShell`, fuera de esta unidad: el logo
  tiene `aria-label` (primer paso de Tab) y en móvil cambia el orden de clases del
  `body` y el marcado del menú (menú móvil fuera de la comparación).
- Lora y el iframe de Google quedaron bloqueados sin red en los dos lados.
- El filtro de favoritos sigue retirado de la UI, como en la plantilla.
