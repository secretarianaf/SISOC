# Compatibilidad de seguimientos y alcance de comedor (#2907)

## Alcance y comportamiento

La promoción de homologación conserva el contexto `es_primer` que la API de
seguimientos utiliza para presentar las prestaciones. La vista nativa y la API
mantienen el filtro por comedor y alcance introducido en la promoción: una URL
con un comedor inexistente o distinto no habilita la lectura ni la baja de un
registro de otro comedor.

La API web aplica el mismo alcance por comedor antes de ejecutar lecturas o
mutaciones, incluso cuando reutiliza métodos de una vista nativa sin pasar por
su `dispatch`. La tabla React de prestaciones muestra AP total, como la vista
nativa, también para seguimientos posteriores y virtuales.

## Verificación

Las pruebas de las APIs de expedientes, intervenciones y relevamientos cubren
los destinos no válidos, la preservación de registros y el flujo autorizado. La
validación local se ejecuta en Docker con datos sintéticos; CI remoto y la
aceptación humana se verifican por separado.
