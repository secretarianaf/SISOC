# Cambio: hacer visibles los permisos heredados de tableros (#2912)

## Alcance

El formulario administrativo de `dashboard` distinguía solo grupos existentes y al guardar podía eliminar otros permisos del tablero. Esta unidad prepara la transición sin convertir permisos heredados en alcance nacional ni cambiar el evaluador de autorización.

## Comportamiento

Los valores que el selector de grupos no representa aparecen como permisos heredados seleccionados. El administrador puede conservarlos o desmarcarlos explícitamente. Los nombres con punto se interpretan como códigos, igual que en el evaluador existente; si ya están guardados se muestran una sola vez. El selector sigue permitiendo añadir otros grupos con punto como antes.

## Verificación

Prueba de regresión con base sintética: caso inicial falló antes del cambio. La suite del módulo pasó en Docker con SQLite sintético. La revisión independiente detectó riesgos de compatibilidad y normalización; se corrigieron y se reexaminó el último riesgo. Pylint aprobó el archivo administrativo. No se utilizaron datos reales.

## Limitaciones

Esta unidad no implementa las audiencias ni el alcance de datos. Los permisos existentes sin alcance confiable siguen bajo su política anterior, pendientes de revisión. El usuario confirmó la verificación visual del formulario con datos sintéticos. No se hizo publicación ni despliegue.


