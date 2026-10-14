# Comedores #2679: formato del Word del Informe Técnico

El Word que se descarga para validar el Informe Técnico (borrador generado desde
el Gestor de templates) toma el formato del modelo institucional
`2.-IT-Incorporación-Personería-6_-Ex-PNUD-No-vigente-1.doc`. La copia para GDE
(#2580) sigue partiendo del último DOCX disponible y conserva el formato del
cuerpo, pero sin encabezado ni pie: GDE pone su propio membrete y numeración.

## Causa

- htmldocx 0.0.6 calcula las columnas de una tabla solo con la primera fila e
  ignora `colspan` y `rowspan`. Una tabla con título combinado (como las del
  modelo) lanzaba `IndexError` y `_generate_docx_content` caía al fallback de
  texto plano: sin tablas, negritas ni alineación.
- Fuera de ese caso, la hoja base (Times New Roman, márgenes de 20 mm, tablas
  gris verdoso, títulos de Word en celeste) no seguía el modelo.

## Cambios

- El soporte de `colspan`/`rowspan` lo resuelve `_InformeHtmlToDocx`
  (#2580, en `impl.py`). Esta rama le agrega dos ajustes: traslada a los
  párrafos el `text-align` puesto sobre `<td>`/`<th>` y convierte el renglón
  vacío del editor (`<p><br></p>`) en un párrafo vacío, para que ocupe una
  línea como en el navegador y no dos.
- `admisiones/services/informes_service/formato_docx.py`:
  - `MembreteInformeTecnico` agrega el encabezado (Programa Alimentar
    Comunidad, escudo, Secretaría de Niñez Adolescencia y Familia, Ministerio
    de Capital Humano y línea azul) y el número de página al pie. El modelo arma
    el encabezado con una tabla invisible; acá se replica con párrafos y
    tabulaciones centradas para no sumar tablas al documento, porque GDE las
    rechaza. El escudo es el del modelo:
    `admisiones/templates/admisiones/docx/escudo_informe_tecnico.jpg`.
- `InformeService._configurar_documento_template`: A4, márgenes 27,8 mm arriba y
  25,4 mm al resto, Calibri 12 justificado, interlineado 1,15, 12 pt entre
  párrafos, títulos en Calibri negrita negra e ítems de lista seguidos.
- `_aplicar_estilo_tablas_templates`: borde negro de 0,5 pt, sin relleno en el
  encabezado, celdas compactas alineadas a la izquierda salvo alineación
  explícita. `w:tblBorders` se inserta en el orden del esquema de `w:tblPr`.
- `gestor_templates.css`: la hoja del editor usa la misma fuente, márgenes y
  tablas que el Word.

- `GdeDocxService.generar` quita encabezados y pies de la copia para GDE, para
  que el membrete y el número de página no se dupliquen con los de GDE ni
  sumen una imagen o un campo que GDE podría rechazar.

El membrete sí llega a la vista previa con marca de agua.

## Validación

- `src/backends/kernel/tests/test_informes_service_unit.py`: formato de hoja y
  tablas, membrete y número de página, estilos de título y tabla con celdas
  combinadas y alineación de celda; copia para GDE sin encabezado ni pie.
- Borrador, copia GDE y vista previa generados con el servicio real en el
  contenedor y revisados convertidos a PDF con Word.
