# Celiaquía: el técnico puede descargar el Excel original de la provincia

Hasta ahora, el Excel masivo que carga la provincia en el expediente solo era
visible para administradores y coordinadores. El técnico, que es quien revisa
legajo por legajo, no tenía forma de contrastar lo cargado contra el archivo
de origen y dependía de que un coordinador se lo enviara por fuera del sistema.

El rol Técnico puede descargar el Excel desde el detalle y la columna del
listado. La metadata "Cargado por / Procesado por" sigue reservada al
Coordinador y al Administrador. La descarga usa `can_download_excel_masivo`;
la metadata usa `can_manage_excel_masivo_audit`.

## Alcance por rol

La ampliación no es simétrica. Administrador y coordinador ven todos los
expedientes; el técnico solo los que tiene asignados, y esa restricción se
mantiene para el Excel.

El listado y el detalle ya acotaban su queryset por `asignaciones_tecnicos`, de
modo que el flag en el template no amplía nada. La vista de descarga era el
punto suelto: `ExpedienteExcelMasivoDownloadView` resuelve el expediente con
`get_object_or_404(Expediente, pk=pk)` sin pasar por esos querysets, así que
con el permiso abierto un técnico habría podido bajar el Excel de cualquier
expediente tanteando el pk. Por eso la validación por asignación se aplica ahí
de forma explícita (`_puede_descargar_excel_masivo`), con el mismo criterio que
ya usan `can_review_legajo` y `can_edit_legajo_files`.

## Cambio de conducta registrada

`test_tecnico_no_descarga_excel_masivo` fijaba el 403 para el técnico como
comportamiento deseado. Este ticket lo revierte de forma deliberada: el test se
reemplaza por uno que verifica la descarga del técnico asignado y otro que
mantiene el 403 para el técnico ajeno al expediente.

Ticket 2521.
