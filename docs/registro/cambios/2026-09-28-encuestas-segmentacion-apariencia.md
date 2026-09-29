# Restauración visual de segmentación

Por pedido del usuario se recupera la apariencia anterior al cambio de estilos
`efd1abcc7` exclusivamente en la página de segmentación: paneles oscuros,
acentos dorados, Guardar dorado, Agregar con borde discontinuo y acciones
secundarias discretas. Se recuperan las clases originales de los botones.

Los estilos se aíslan en `static/custom/css/encuestaSegmentacion.css`, usando
el layout de `encuestaForm.css`. No se cambia la apariencia del editor, listado
ni aprobación. Los grupos seleccionados siguen visibles fuera del scroll,
ahora con la misma paleta anterior. Se conservan carga manual, Excel/CSV,
plantillas, validaciones y segmentación por documentos, IDs y grupos.

No hay cambios de backend ni migraciones.

Validación: 76 tests de servicios y segmentación por documentos, IDs y grupos
pasaron en Docker. Chrome verificó plantilla XLSX, alta manual, reemplazo CSV,
rechazo de IDs inexistentes sin perder el listado y baja. También selección
visible de grupos, búsqueda, scroll, eliminación por teclado, guardado y recarga;
vista móvil sin desborde ni errores JavaScript. djlint y `git diff --check` correctos.
