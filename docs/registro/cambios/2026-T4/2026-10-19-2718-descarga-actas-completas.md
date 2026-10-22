# Inspecciones escolares: descarga de actas completas desde el tablero

Fecha: 2026-10-19. Issue: #2718 (punto 2).

## Qué cambia

En Inspecciones → Tablero → Últimas actas hay un botón «Descargar actas
completas», a la izquierda de «Exportar CSV (filtros aplicados)». El CSV no
cambia.

| Ruta | Nombre | Qué hace |
|---|---|---|
| `tablero/descargar-actas/` | `inspecciones_tablero_descargar_actas` | PDF (una acta) o ZIP (varias) con las actas de los filtros del tablero. |

- Mismo permiso que el resto del tablero (`puede_gestionar_inspecciones`; 403
  sin permiso) y mismas actas que el CSV: `services/tablero.py::actas_validas`
  (finalizadas, no de prueba, con los filtros del querystring).
- El PDF es el original del acta (`Acta.pdf`), el que genera la app con los
  datos del reporte y las imágenes y sube al cerrar. No se genera otro formato.
- Una acta sin PDF todavía (`pdf_estado = pendiente`), o cuyo archivo falta en
  disco, no se puede incluir: se lista en `ACTAS_SIN_PDF.txt` dentro del ZIP.
  Si ninguna tiene PDF, se informa.
- Topes: 100 actas y 250 MB por descarga (el ZIP se arma dentro del pedido y lo
  sirve un worker síncrono de gunicorn); si se superan, mensaje para acotar los
  filtros.
  El ZIP se arma en un archivo temporal, copiando por bloques, sin cargar los
  PDF en memoria.
- Sin actas para los filtros: vuelve al tablero con el aviso «No hay actas para
  descargar con los filtros aplicados.»

## Archivos

`services/descarga_actas.py`, `views_tablero.py`, `urls.py`, `tablero.html`,
`tablero.js`, `config/url_registry.json` y
`tests/test_inspecciones_tablero_descarga.py`.
