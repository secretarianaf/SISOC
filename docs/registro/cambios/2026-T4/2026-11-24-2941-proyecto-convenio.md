# Proyecto de Convenio único para Alimentar Comunidad (#2941)

## Alcance

Legales genera el Proyecto de Convenio de incorporación y renovación a partir del Word aprobado en el issue. El servicio rellena ese archivo y lo convierte a PDF con LibreOffice. Si falla la generación de cualquiera de los dos archivos, conserva el estado de la admisión.

## Comportamiento

- El modal de Legales pide cantidad de espacios, datos de la autoridad firmante y, solo para comedores judicializados, carátula, juzgado y memo. Nombre, cargo y DNI iniciales provienen del último Informe Técnico. La autoridad se puede editar sin cambiar ese informe. La localidad debe pertenecer a la provincia seleccionada.
- El documento incluye los dos párrafos opcionales según el legajo judicial del comedor y la cantidad de espacios. La marca de agua BORRADOR se repite en diagonal detrás del texto de cada página del Word y del PDF mientras el Informe Técnico no esté validado.
- La Primera Providencia copia los datos del Proyecto de Convenio nuevo y los muestra para lectura. Para convenios anteriores sigue pidiéndolos. Si Legales debe regenerar un proyecto nuevo, el formulario conserva los datos anteriores y el IF se vuelve a cargar.
- Aplica a la pantalla Django y al backoffice React de SISOC. La migración de Admisiones agrega campos que admiten vacío para los convenios existentes.
- La migración de este cambio es `0085_proyecto_convenio` y depende de `0084_variables_if_ultimo_informe_tecnico`, incorporada por #2948. La migración se detiene antes de modificar columnas si la antigua `0084_proyecto_convenio` figura como aplicada o si alguna columna nueva ya existe sin ese registro. Esa base requiere reconciliación controlada y respaldo verificado; no se debe ejecutar `--fake` ni reaplicar las columnas a ciegas.

## Reconciliación: procedimiento propuesto para validar

El siguiente procedimiento es una propuesta para ensayar en copias sintéticas o
restauradas, no una autorización para modificar bases compartidas o reales:

1. Identificar el motor y su versión, el historial de migraciones y cualquier
   columna de la antigua `0084`. Detenerse si el estado es parcial, ambiguo o no
   coincide con el esquema esperado; la guardia no repara esos casos.
2. Detener escrituras sobre la copia y obtener un respaldo consistente. Restaurarlo
   en otra base aislada y comprobar los datos y el esquema relevantes antes de
   continuar; una copia no restaurada no demuestra capacidad de recuperación.
3. En esa copia, aplicar la `0084` de variables y comparar la definición completa
   de la tabla del proyecto de convenio con una base limpia del mismo motor y
   versión, incluidos tipos, nulabilidad, índices y claves foráneas. Normalizar
   únicamente contadores variables como `AUTO_INCREMENT`; una diferencia impide
   continuar hasta investigarla.
4. Solo cuando la equivalencia esté demostrada, evaluar el registro controlado de
   `0085` sin repetir DDL en la copia. Comparar todos los registros de la tabla y
   el historial antes y después, y verificar también la restauración del respaldo.
   La aplicación en cualquier base real requiere una autorización y un plan de
   recuperación independientes.

En MySQL 8 aislado se probó la cadena limpia y una base sintética con la antigua
`0084`: la guardia detuvo el DDL, se comparó `SHOW CREATE TABLE` completo salvo
el contador `AUTO_INCREMENT`, se restauró un volcado y se compararon todas las
filas de la tabla de convenio. Después se registró `0085` sin DDL solo en esa base
sintética y se conservó la fila de prueba; una columna adicional fue detectada
como diferencia. Esta prueba no verifica todos los datos del sistema, estados
parciales reales, otros motores o versiones, ni recuperación de datos ya perdidos.

## Verificación

Se probaron las cuatro combinaciones de judicialización y cantidad de espacios en ambos tipos de admisión, la conversión real a PDF, los campos obligatorios, la localidad fuera de provincia, los errores de generación, la precarga y la compatibilidad con convenios viejos. También se probó en React el cambio de provincia y el envío de la autoridad editada. La migración se aplicó sobre el MySQL local. La revisión manual confirmó el bloqueo con domicilio vacío, los datos de la firmante editada y la marca de agua en Word y PDF.

La guardia ante columnas previas sin registro se probó con una descripción de
esquema simulada en SQLite y con una columna parcial creada en MySQL 8 aislado.
En MySQL se verificó que la guardia detiene `0085` sin modificar el DDL ni el
valor sintético. También se verificó con una columna de nombre mixto en SQLite
y MySQL: la comparación no distingue mayúsculas y conserva el valor. Queda
pendiente la verificación independiente del candidato actualizado y la validación
del procedimiento completo sobre otros estados.
