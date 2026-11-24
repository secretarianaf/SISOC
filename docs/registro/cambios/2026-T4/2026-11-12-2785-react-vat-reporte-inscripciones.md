# Cambio: reporte de inscriptos y asistencias de VAT en React sobre G1 v1 (#2785, V08.01)

## Alcance

Cierre de V08.01 del [contrato V01/V08](../../../plans/2026-T4/2026-11-12-2785-vat-v01-v08-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): la pantalla
`/vat/reportes/inscripciones-asistencias/` (filtros, métricas, resumen por grupo y detalle nominal). Lee por
`ReporteInscriptosAsistenciasView` y su servicio, sin tocar vistas, servicio, plantilla ni URLs nativas. Las cuatro
exportaciones (`?export=csv|xlsx|detalle_csv|detalle_xlsx`) siguen siendo descargas nativas. No activa React en
producción.

Archivos:

- `src/backends/vat/VAT/web_api_reportes.py` (ruta en `web_api_urls.py`), `url_registry.json` regenerado y
  `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat.py`: la entrada de vista previa sirve el índice de React salvo cuando llega un
  `export` válido, que pasa a la vista nativa (descarga).
- `src/frontends/apps/sisoc/src/routes/vatReporte.tsx` y `vatReporteStyles.ts` (el `<style>` nativo, literal),
  registrado en `routes/index.ts`.
- Pruebas: `test_web_vat_reporte_v08.py`, `test_web_preview_vat_v01_v08.py` (ampliado) y `vatReporte.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y luego una de `VAT.view_inscripcion`, `VAT.view_comisioncurso` o
  `VAT.view_centro` (403). El alcance por usuario (centros, provincias, programas) lo aplica el servicio, igual que hoy.
- La API devuelve los quince controles del formulario con sus opciones (`Nivel` y `Agrupar por` siempre visibles; los
  demás aparecen con valor o al agregarlos con «+ Agregar filtro…», y se quitan con la ×), el resumen, las filas del
  grupo (50 por página) y el detalle nominal (50 por página, con `detalle_page`). Números y fechas salen con el formato
  localizado de Django (`100,0`, `d/m/Y H:i`).
- El formulario es un `GET` nativo: Aplicar recarga con los filtros; Limpiar vuelve a la URL base. Un valor que no es
  una opción válida (o una fecha inválida) se muestra como el navegador lo haría con el HTML nativo: la primera opción
  o vacío.
- «Buscar en esta página» filtra en el cliente las filas visibles y cuenta «N filas visibles en esta página».
- El botón «Tour de ayuda» carga `driver.js` y `vat_tour.js` como la plantilla y no inicia el tour solo.
- Quirks nativos conservados: el estado del detalle se imprime como clave (`inscripta`), `None` aparece como texto si
  falta un dato, y `page` fuera de rango cae en la última página (no hay 404).
- Diferencia conocida: el menú del tour abierto se posiciona con CSS fijo y no con Popper (Bootstrap JS no está cargado
  en la pantalla de React); cerrado es idéntico.

## Verificación

- Backend (imagen fijada, sin red): pruebas nuevas, `vat` web, `test_web_gate`, `test_backend_proxy` y
  `test_servicios_backends` en verde; `black`, `pylint` y `makemigrations --check` sin cambios.
- Frontend: `vitest --project sisoc`, `tsc`, `eslint` y build en verde.
- G1 de extremo a extremo (núcleo y runtime): 401, 403, constancia falsificada, CSRF, lectura y solo lectura.
- Comparación visual nativo contra React (reporte base, con filtros agregados, otro nivel y vacío; escritorio y móvil)
  y guardas.
- No cubierto: la descarga real de los archivos desde React (la cubre la prueba de la entrada de vista previa).
