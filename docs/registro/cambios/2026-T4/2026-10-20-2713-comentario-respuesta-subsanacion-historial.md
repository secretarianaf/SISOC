# Celiaquía: comentario de la Provincia visible en el historial de subsanaciones

Ticket 2713. Rama `CeliaquiaTk_2713`.

## Pedido

Al responder una subsanación, la Provincia puede cargar un comentario opcional
junto con los archivos. Una vez confirmada la subsanación el comentario deja de
verse, tanto para Provincia como para Nación.

## Causa

El comentario se guarda en `SubsanacionArchivo.descripcion`
(`SubsanacionService.responder`). El componente
`components/legajo_archivos_requeridos.html` lo pintaba solo en el bloque
«Subsanación solicitada» (subsanación activa). Ese bloque desaparece cuando el
legajo deja de estar en SUBSANAR, y el «Historial de subsanaciones», que es lo
que queda, listaba los archivos sin la descripción.

## Solución

El historial muestra la descripción de cada archivo con el mismo formato que el
bloque activo (`— <comentario>`). Sin cambios de modelo ni de datos: los
comentarios ya cargados pasan a verse. El comentario sigue siendo opcional.

## Tests

- `test_subsanacion_documentacion_complementaria.py`: el comentario de la
  respuesta aparece en el historial para Nación y para Provincia.
