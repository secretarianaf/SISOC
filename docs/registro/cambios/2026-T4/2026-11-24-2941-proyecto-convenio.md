# Proyecto de Convenio único para Alimentar Comunidad (#2941)

## Alcance

Legales genera el Proyecto de Convenio de incorporación y renovación a partir del Word aprobado en el issue. El servicio rellena ese archivo y lo convierte a PDF con LibreOffice. Si falla la generación de cualquiera de los dos archivos, conserva el estado de la admisión.

## Comportamiento

- El modal de Legales pide cantidad de espacios, datos de la autoridad firmante y, solo para comedores judicializados, carátula, juzgado y memo. Nombre, cargo y DNI iniciales provienen del último Informe Técnico. La autoridad se puede editar sin cambiar ese informe. La localidad debe pertenecer a la provincia seleccionada.
- El documento incluye los dos párrafos opcionales según el legajo judicial del comedor y la cantidad de espacios. La marca de agua BORRADOR se repite en diagonal detrás del texto de cada página del Word y del PDF mientras el Informe Técnico no esté validado.
- La Primera Providencia copia los datos del Proyecto de Convenio nuevo y los muestra para lectura. Para convenios anteriores sigue pidiéndolos. Si Legales debe regenerar un proyecto nuevo, el formulario conserva los datos anteriores y el IF se vuelve a cargar.
- Aplica a la pantalla Django y al backoffice React de SISOC. La migración de Admisiones agrega campos que admiten vacío para los convenios existentes.

## Verificación

Se probaron las cuatro combinaciones de judicialización y cantidad de espacios en ambos tipos de admisión, la conversión real a PDF, los campos obligatorios, la localidad fuera de provincia, los errores de generación, la precarga y la compatibilidad con convenios viejos. También se probó en React el cambio de provincia y el envío de la autoridad editada. La migración se aplicó sobre el MySQL local. La revisión manual confirmó el bloqueo con domicilio vacío, los datos de la firmante editada y la marca de agua en Word y PDF.
