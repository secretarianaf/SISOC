# Cambio: buscador, panel de control y áreas PAS en React sobre G1 v1 (#2785, PAS05.01, PAS06.01, PAS02.01)

## Alcance

Pantallas autenticadas de PAS del
[contrato PAS05-PAS06](../../../plans/2026-T4/2026-11-10-2785-pas05-pas06-contratos.md),
con la pestaña «Declaración Jurada» de PAS02.01
([contrato PAS02-PAS04](../../../plans/2026-T4/2026-11-10-2785-pas02-pas04-contratos.md)):
«Buscador PAS» (`/pas/listar`), «Panel de Control» (`/pas/panel-control`,
`/pas/panel-control/<pk>` y `/pas/<pk>`) y las áreas «Formación FCH»
(`/pas/formacion`), «Mesa de Ayuda» y «Liquidación». Solo lectura. PAS05.02
queda sin alcance, como dice el contrato.

No cambia las vistas, formularios, servicios, plantillas ni el JavaScript
nativos, ni la DDJJ pública (PAS01, `/pas/ddjj/...`). Las descargas (PDF de
DDJJ, tokens) siguen siendo rutas nativas que la pantalla enlaza. No activa
React en producción.

Archivos:

- `src/backends/pas/pas/web_api_views.py`, `src/backends/pas/pas/web_api_serializers.py`
  y `src/backends/pas/pas/web_api_urls.py`: API web, incluida desde
  `src/backends/pas/pas_runtime/web_api_urls.py`, que se monta en
  `src/backends/pas/pas_runtime/urls.py` (y por eso también en el monolito).
- `src/backends/config/backends.json`: prefijo `api/web/pas/` del backend
  `pas`. `src/backends/config/url_registry.json` se regeneró con el generador.
- `src/backends/config/middlewares/admindocs.py`: las rutas nuevas quedan fuera
  del atajo HEAD de admindocs.
- `src/backends/pas/pas/web_preview_backoffice.py`: entradas React sin montar
  (`backoffice_preview_patterns`), solo para un URLconf local; assets en
  `/pas/react/assets/`.
- `src/frontends/apps/sisoc/src/routes/`: `pas.tsx` (ruta y áreas),
  `pasBuscador.tsx`, `pasPanel.tsx` y `pasFrame.tsx` (piezas comunes de las
  plantillas PAS).
- Pruebas: `src/backends/pas/pas/tests/test_web_pas_backoffice.py`,
  `src/backends/pas/pas/tests/test_web_pas_preview.py` y
  `src/frontends/apps/sisoc/src/routes/pas.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/pas/areas/formacion/` | Contexto de `PasAreaView`: titular pedido primero, 30 por página, filtros sin fuente vacíos, resumen de formación y navegación del circuito |
| `GET /api/web/pas/formacion/personas/` | Páginas del scroll incremental, mismos parámetros que `pas/formacion/personas`, ítems en JSON en lugar del fragmento HTML |
| `GET /api/web/pas/areas/mesa-ayuda/`, `.../liquidacion/` | Área, circuito y total del padrón |
| `GET /api/web/pas/personas/` | `PasPersonaListView`: búsqueda, estado, `filters` avanzados, `NoCountPaginator` de 10 y `capabilities` de importar y exportar tokens |
| `GET /api/web/pas/panel/`, `/panel/<pk>/` | `PasPersonaDetailView`: titular (o el primero), lista lateral de hasta 100, DDJJ elegida con `?ddjj=`, historial y `can_change`; `pk` inexistente, 404 |

Cada endpoint ejecuta la vista nativa y proyecta su contexto. Las fechas salen
con los formatos de la plantilla. La DDJJ omite `firma_nombre_completo` y nunca
incluye el texto legal, la invitación, el token ni la ruta del PDF. Respuestas
JSON `private, no-store`; otros métodos, 405.

Acceso, en este orden: G1 (401 sin sesión, 403 con `state` si falta un
requisito; el runtime solo atiende lo que verificó `WebGateMiddleware`) y
después la regla nativa sin cambios, `permissions_any_required(["pas.view_paspersona"])`.
Los botones siguen los permisos de la plantilla: «Importar titulares»
(`add_paspersona`), «Exportar tokens» (`export_ddjj_tokens`), «Cambiar estado» y
editar (`change_paspersona`).

Entrada React: en las URLs nativas corre primero el decorador (anónimo y sin
permiso, 403 nativo) y el despacho nativo (titular inexistente, 404) y después
el `index.html` congelado.

Pantalla React: marco de `includes/main.html` con `pas.css`, el bloque
`app-header` propio de PAS, la navegación del circuito y el mismo marcado de
las plantillas. Los filtros siguen siendo formularios GET nativos. Las
pestañas reproducen Bootstrap 5.3 (tabindex en roving y flechas). Con
`#ddjj-panel` se abre la pestaña DDJJ y se repite la navegación al fragmento;
cambiar la versión navega a `?ddjj=<id>#ddjj-panel`. Formación carga más
titulares con `IntersectionObserver` y vuelve a pedir el GET a las 00:00:05 del
día siguiente.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo sobre la base (30 de 34 y la entrada sin
  módulo) y luego en verde. Suite de PAS, `test_web_gate`, `test_backend_proxy`
  y `test_servicios_backends` (269 pasan, 1 omitida), registro de URLs al día,
  recolección completa sin errores, `black`, `pylint` 10/10 y
  `makemigrations --check` sin cambios.
- Frontend: prueba de ruta en rojo (módulo inexistente) y luego en verde (13);
  Vitest de `sisoc` y `pas`, `tsc`, ESLint y build de Vite.
- Visual (regla S13), nativo contra React, 17 estados (buscador con, sin y con
  filtro; padrón vacío; panel sin `pk`, con `pk`, `pas/<pk>`, lector, pestañas
  DDJJ, FCH e historial; panel vacío; formación con y sin titular; mesa de
  ayuda; liquidación) en 1440x900 y 390x844: 34 de 34 pasan, desvío geométrico
  máximo de 0,23 px, diferencia de píxeles 0,000 % y el mismo orden de Tab.
  Anónimo, sin permiso y titular inexistente responden igual.
- G1 de punta a punta: core y runtime de PAS en dos contenedores gunicorn,
  corrido sobre el árbol que ya suma el cambio de estado (PAS06.03). Las cinco
  pantallas cargan por core → compuerta → runtime; anónimo 401, sin permiso
  403, requisito pendiente 403 con `state` y el header del cliente se descarta.
  Contra el runtime directo, una constancia faltante, falsa, alterada, de otro
  destino, audiencia o usuario, vencida (61 s) o futura responde 403; una de
  58 s, 200.

## Limitaciones

- `SisocShell` no tiene un espacio para el bloque `app-header`; las acciones
  superiores se montan con un portal en ese contenedor, junto a la fila vacía
  que ya dibuja el marco.
- Diferencias del marco compartido ya conocidas: nombre accesible del logo y
  menú móvil (fuera de la comparación por la excepción vigente).
- La pestaña DDJJ viaja dentro de la respuesta del panel; no se publicó una
  ruta separada `personas/<pk>/ddjj/`, que no tendría consumidor.
- Roboto quedó bloqueada sin red en los dos lados.
