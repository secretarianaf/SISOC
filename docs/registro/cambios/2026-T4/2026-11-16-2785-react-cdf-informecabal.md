# Cambio: Informe Cabal de Centro de Familia en React sobre G1 v1 (#2785, CDF01)

## Alcance

Pantallas nativas del Informe Cabal, cuyo contrato de acceso es D1 (sin cambios):

- `/centrodefamilia/informecabal/` (historial con los modales «Procesar nuevo archivo» y
  «Reprocesar rechazados»).
- `/centrodefamilia/informecabal/<pk>/` (detalle del archivo).
- `/centrodefamilia/informecabal/registro/<pk>/` (registro).
- `/centrodefamilia/centros/<centro_id>/informecabal/<pk>/` (registros de un centro).

Verificado antes de escribir código: ninguna de las cuatro tenía ruta React ni entrada de
`web_preview_*`. `/centrodefamilia/metricas-dashboard/` **no** es una pantalla: devuelve JSON
al dashboard del core por proxy (ver el
[contrato CDF04](../../../plans/2026-T4/2026-11-10-2785-cdf03-cdf04-contratos.md)), por lo que
no se migra. `informecabal/preview/`, `process/` y `reprocess/` son endpoints AJAX nativos y
tampoco cambian.

No cambian las vistas, las plantillas, el servicio de proceso ni la regla de acceso
(`view_centro`). No activa React en producción.

Archivos:

- `src/backends/cdf/centrodefamilia/web_api_informecabal.py` y `web_api_informecabal_urls.py`
  (API web, incluida desde `cdf_runtime/web_api_urls.py`); `web_preview_informecabal.py`
  (entradas de la vista previa local).
- `src/backends/config/middlewares/admindocs.py` (dos patrones propios).
- `src/frontends/apps/sisoc/src/routes/cdfInformeCabal.tsx`, registrada en `routes/index.ts`.
- Pruebas: `src/backends/cdf/tests/test_web_cdf_informecabal.py`,
  `test_web_cdf_preview_informecabal.py` y
  `src/frontends/apps/sisoc/src/routes/cdfInformeCabal.test.tsx`.

`url_registry.json` no cambia por sí solo: el padre lo regenera con `generar_registro_urls`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/cdf/informecabal/?page=` | Contexto de `InformeCabalListView`: 10 archivos por página, más nuevo primero, con la tolerancia de `Paginator.get_page` (página inválida es la primera, fuera de rango la última); fecha local `dd/mm/aaaa HH:MM`; los mensajes encolados se consumen y viajan con sus `tags` (la plantilla los dibuja en el contenido como `alert-<tags>`) |
| `GET /api/web/cdf/informecabal/<pk>/` | Datos del archivo y todos sus registros por id; «Pago» y «Estado» salen de las mismas reglas que la plantilla (`motivo_rechazo` vacío o `0` es aceptado; con centro es «Impactado») |
| `GET /api/web/cdf/informecabal/registro/<pk>/` | Corre la vista nativa; solo informa que existe (404 si no) |
| `GET /api/web/cdf/centros/<centro_id>/informecabal/<pk>/?page=` | Registros del centro de ese archivo, 50 por página; centro o archivo inexistente es 404; importe con `floatformat:2` |

Orden de acceso, igual que hoy: sesión y requisitos web (G1), `view_centro` (403) y
después el objeto (404). Todo es de solo lectura; cualquier otro método es 405.

Pantalla React: mismos textos, controles y orden que las plantillas.

- **Botones del historial.** «Procesar nuevo archivo» y «Reprocesar rechazados» abren los
  modales nativos, que llaman a los endpoints nativos exactamente como `informecabal.js`:
  `POST informecabal/preview/` (multipart, `file` y `page`, 25 filas), `POST
  informecabal/process/` (`file` y `force`; un 409 por nombre duplicado pregunta «Ya se subió
  un archivo con este nombre. ¿Desea proseguir?» y solo con «Aceptar» reenvía con
  `force=true`) y `POST informecabal/reprocess/` (urlencoded, `codigo`), todos con
  `X-CSRFToken`. Tras procesar, la página se recarga a los 800 ms (el mensaje de éxito
  encolado aparece en el historial). Nada se reintenta.
- **Orden por columna** local a la página, como `listSort.js` (ascendente, descendente,
  sin cambio; la fecha se ordena por `aaaa-mm-dd HH:MM` como lo hace el script).
- **Registro (actualización #2946).** En el detalle del archivo, el número de cada
  fila enlaza al registro exacto, tanto en Django como en React. La ruta
  `informecabal/registro/<archivo_pk>/` conserva su significado: `?registro=<registro_pk>`
  selecciona una fila que pertenece a ese archivo. Django y la API reutilizan la misma
  búsqueda y mantienen sus guardas. Un selector inválido, repetido o de otro archivo
  devuelve 404. Sin selector, ambas pantallas conservan los valores anteriores y no
  eligen una fila por defecto. El detalle seleccionado muestra el Centro y la marca
  «No coincidente» persistidos, y permite volver al archivo.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 14 pruebas nuevas (API y vista previa) en verde: cadena de acceso con 401/403/404/405,
  paginación de 10 y de 50 con la tolerancia nativa, formatos de fecha e importe, banderas por
  fila, mensaje encolado consumido una sola vez y entradas de la vista previa con las
  guardas nativas.
- Frontend: Vitest de la ruta (14), `tsc`, ESLint y build de Vite.
- Visual (regla S13) y G1 de punta a punta: ver el informe de la unidad.

Para #2946, las pruebas usan dos filas del mismo archivo con distintos Centro y
«No coincidente». Cubren el enlace y la apertura exacta en Django, el contrato de la
API, la vista previa local y la solicitud y el renderizado de React.

## Limitaciones

- Las celdas de la vista previa del archivo y los mensajes de error se dibujan como texto. El
  script nativo los inserta como HTML, así que un valor con marcado se vería distinto; el
  cambio es deliberado y cierra una inyección posible.
- Mismas diferencias del marco compartido que las unidades anteriores (enlace del logo y
  menú móvil).
