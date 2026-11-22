# Cambio: histórico de transacciones DW de un comedor en React (#2785, CO07.01)

## Qué cambia

- **API.** `GET /api/web/comedores/comedores/<id>/transacciones/`
  (`src/backends/comedores/comedores/web_api_transacciones.py`, incluida desde
  `src/backends/comedores/comedores_runtime/web_api_urls.py`) corre `ComedorTransaccionesDetailView` con su
  `setup()`, `get_object()` (comedor dentro del alcance del usuario, 404 si no) y `get_context_data()`, que llama
  al servicio existente `DWTransaccionesService.obtener_historico_completo` (SQL parametrizado sobre
  `DW_sisoc.vw_EC_resumen_transacciones`, 1000 por página; `?page=` inválido vuelve a 1). Cada celda sale con la
  expresión de `comedor_transacciones_detail.html`: **Transferido es `debito_total` y Gastado es
  `credito_total`**, Saldo es `cereo`, importes con `$` y punto de miles sin decimales, `Sin información` si el
  valor es nulo, período `YYYYMM` como `YYYY-MM`. Acceso igual que hoy: `comedores.view_comedor`. Es de solo
  lectura; no se agregó ningún endpoint HTTP hacia el DW ni se lee configuración del DW.
- **React.** `src/frontends/apps/sisoc/src/routes/comedorTransacciones.tsx` dibuja la tabla (Período,
  Movimientos, Transferido, Gastado, Saldo Cereado) o el aviso «Sin información», con el encabezado de la
  página nativa. No hay filtros, exportación ni controles de escritura.
- `src/backends/comedores/comedores/web_preview_transacciones.py` mantiene la URL nativa con su guarda y
  devuelve el índice React sin consultar el DW. Se agregó la ruta a `_OWNED_PATTERNS` y a `url_registry.json`.
- **Se conserva sin cambios.** Una excepción del servicio DW sigue devolviendo lista vacía y se ve igual que la
  falta de datos (sin indicador de caída ni éxito falso); la tarjeta de la ficha y su enlace «ver detalle»
  ya apuntan a esta URL nativa. No se normaliza `page` fuera de rango: sigue el comportamiento del servicio.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red, servicio DW simulado): celdas con el mapeo Transferido/Gastado,
  nulos, página reenviada e inválida, falla del DW igual a vacío, 401/403 (otro permiso incluido)/404, `POST`
  rechazado sin consultar el DW, y entrada de vista previa; pruebas del core (puerta web, proxy, servicios).
- Vitest, tsc, eslint y build sin avisos. G1 y visual S13 contra la página nativa. No se acreditó conectividad
  real con el DW.

## Limitaciones y diferencias conocidas

- La ruta React solo existe en la vista previa.
- La página nativa calcula paginador pero no lo dibuja; React tampoco.
