# Cambio: exportación del listado de ciudadanos, contrato fijado (#2785, C05.04)

## Qué cambia

- No cambia código de producción. `ciudadanos/exportar` (`CiudadanosExportView`) es una descarga
  CSV nativa y por eso no tiene pantalla React ni API JSON: el listado React la enlaza con un
  enlace común y el navegador baja el archivo como hoy.
- Se agrega `ciudadanos/test_ciudadanos_exportacion_csv.py`, que fija el contrato de la descarga:
  permisos (`ciudadanos.view_ciudadano` y `auth.role_exportar_a_csv`; sin alguno de los dos es 403 y un
  anónimo va al login), tipo de contenido y nombre del archivo, encabezado, filas ordenadas por
  apellido y nombre, el filtro `q` y el orden `sort`/`direction`, y que mirar la exportación no
  escribe datos.
- El contrato M2 de C01-C03 y C05.04 (`docs/plans/2026-T4/2026-11-13-2785-ciudadanos-c01-c03-m2.md`)
  documenta los permisos, columnas y orden.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): los tres casos pasan contra el código actual, sin
  cambios de producción (la prueba fija el comportamiento existente, no hay RED posible).
- No aplican G1 ni visual: no hay endpoint web ni pantalla nuevos.

## Limitaciones y diferencias conocidas

- El listado de ciudadanos (`ciudadanos/listar`) sigue en Django; cuando pase a React deberá enlazar
  `ciudadanos/exportar` con los mismos parámetros de filtro y orden.
