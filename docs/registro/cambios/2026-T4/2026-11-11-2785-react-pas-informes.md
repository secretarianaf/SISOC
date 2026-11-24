# Cambio: consulta de informes PAS en React sobre G1 v1 (#2785, PAS04.01 y PAS04.03)

## Alcance

Listado y detalle de informes PAS del
[contrato PAS02-PAS04](../../../plans/2026-T4/2026-11-10-2785-pas02-pas04-contratos.md).
No cambia vistas, plantillas, servicios ni la descarga CSV nativa. No activa
React en producción.

Archivos:

- `src/backends/pas/pas/web_api_informes.py` y rutas en
  `src/backends/pas/pas/web_api_urls.py`.
- `src/backends/pas/pas/web_preview_informes.py` (entrada local sin montar).
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/pasInformes.tsx` y su registro en
  `routes/index.ts`.
- Pruebas: `src/backends/pas/pas/tests/test_web_pas_informes.py`,
  `src/backends/pas/pas/tests/test_web_pas_informes_preview.py` y
  `src/frontends/apps/sisoc/src/routes/pasInformes.test.tsx`.

## Comportamiento

- `GET /api/web/pas/informes/?q=&page=` ejecuta `PasInformeListView`: misma
  búsqueda, orden, 10 por página sin conteo y el mismo prefijo de paginación
  que imprime la plantilla. Devuelve `can_generate` y, por fila,
  `download_url` solo con los tres permisos de descarga.
- `GET /api/web/pas/informes/<pk>/` ejecuta `PasInformeDetailView`: filtros en
  el orden guardado y filas de `resultado` como texto, igual que la plantilla
  (clave ausente vacía, `None` como «None»), sin paginar.
- Acceso: G1 y después `permissions_all_required` con
  `pas.view_paspersona` y `pas.view_pasinforme`. Solo GET; sin escrituras.
- La descarga `pas/informes/<pk>/descargar` sigue nativa; React solo enlaza.

## Diferencia conocida (bug nativo, se corrige aparte)

Con un informe cuyo autor fue borrado (`usuario` nulo), el listado y el detalle
nativos responden 500: `default:informe.usuario.username` falla al resolver el
argumento del filtro. La API devuelve `""` y React muestra «-». Decisión del
responsable: se conserva «-»; la corrección nativa queda para otro cambio. La
prueba `test_native_pages_fail_without_author_and_the_api_does_not` fija el
estado actual.

## Verificación

Entorno sintético, sin red, imagen fijada.

- Backend: pruebas nuevas en rojo sobre la base (32 de 33) y en verde; suite de
  PAS, `test_servicios_backends`, `web_gate` y `backend_proxy`, registro de
  URLs al día, `black`, `pylint` y `makemigrations --check`.
- Frontend: Vitest de `sisoc` tres veces en verde, `tsc`, ESLint y build.
- Visual (S13) en 1440x900 y 390x844, siete casos: área principal igual,
  desvío máximo 0,05 px y hasta 0,004 % de píxeles distintos. Guardas (anónimo,
  sin permiso, inexistente) iguales al nativo.

## Limitaciones

- Diferencias del marco compartido, fuera de esta entrega: el menú lateral
  React marca abierto el grupo PAS en `/pas/informes` y el enlace de marca
  lleva `aria-label`, lo que cambia el primer tope de Tab.
- G1 de punta a punta (core y runtime de PAS con gunicorn) se ejecutó junto con
  la solicitud de generación; ver
  [el registro de PAS04.02](2026-11-12-2785-react-pas-informes-generar.md).
