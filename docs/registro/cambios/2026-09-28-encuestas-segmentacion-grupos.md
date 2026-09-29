# Segmentación de encuestas por grupos

Se agrega «Grupos de usuarios» a la segmentación. Reutiliza grupos de Django
existentes y permite buscar y seleccionar varios con casillas, mostrando la
cantidad elegida. Se exige al menos uno y se valida su existencia en el servidor.
Una selección inválida conserva íntegramente la configuración anterior.

La condición es pertenecer a cualquiera de los grupos, con una sola encuesta
pendiente aunque el usuario pertenezca a varios. La pertenencia es dinámica:
entrar o salir de un grupo cambia el acceso incluso con una ronda abierta. Se
verifica tanto en la cola de pendientes como al responder; la precarga evita
una consulta de grupos por cada ronda.

La migración `0007_segmentacion_grupos` agrega la relación con `auth.Group` sin
alterar las segmentaciones anteriores. Se conservan permisos y bloqueo de
edición durante aprobación. Cambiar de tipo limpia los destinatarios anteriores;
la revisión muestra los grupos seleccionados y las nuevas versiones los copian.

Exportar con esta segmentación produce JSON v5 y nombres de grupos, evitando
depender de sus IDs entre ambientes. Al importar deben existir todos con el
mismo nombre: nunca se crean grupos ni se cambian permisos o pertenencias.
Se mantiene compatibilidad con formatos 1–4 y con los demás tipos de segmentación.

Se conserva la API explícita de `actualizar_segmentacion`, agregando el argumento
opcional `grupos_ids`; se exceptúa localmente el límite de cantidad de argumentos
de pylint para mantener compatibles las cargas existentes por archivo, documentos
e IDs de usuarios.

## Validación local

La migración se aplicó en MySQL local y no quedan cambios de modelos sin
migración. Las 12 pruebas nuevas cubren unión de grupos, pertenencia dinámica,
respuestas, rollback ante entradas inválidas, permisos, aprobación y portabilidad
por nombre con IDs distintos entre ambientes.
La suite completa de encuestas pasó en Docker: 288 tests.

Chrome verificó búsqueda, selección múltiple, persistencia, rechazo de selección
vacía sin perder la configuración anterior y revisión del aprobador. A 390 px
no hay desborde; no se registraron errores JavaScript. Se dejó la encuesta QA 11
en borrador, sin publicar ni cambiar pertenencias o permisos de los usuarios.

Black, djlint y `git diff --check` sin diferencias. Pylint: 9,99/10, con la única
advertencia de longitud de `services.py` (1124 líneas frente a 1000).

## Selección visible fuera del scroll

Los grupos marcados aparecen como etiquetas encima del buscador, fuera del
listado desplazable. Cada etiqueta permite quitar el grupo y sincroniza su
casilla; buscar no oculta la selección. Al abrir la pantalla se reconstruyen
las etiquetas de los grupos guardados. Incluye contador, estado vacío y
continuidad del foco al quitar con teclado. Los cambios se persisten al guardar.

Verificado en Chrome: seleccionar, filtrar, recorrer el listado, quitar con
teclado, sincronizar casillas, guardar y recargar. A 390 px las etiquetas se
distribuyen en varias líneas sin desbordar. No se modificó el comportamiento
del servidor ni se requieren migraciones nuevas.
