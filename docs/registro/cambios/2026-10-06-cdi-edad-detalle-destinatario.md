# CDI: el detalle del destinatario no mostraba la edad

Rama `Renaper_CDI`. Sin ticket.

## Problema

En `centrodeinfancia/<pk>/nomina/<nomina_id>/ver/` la edad del niño/a se veía
siempre como "—". El template pedía `nomina.edad_calculada`, que es un campo del
formulario de carga y no existe en el modelo. Además, la fila "Unidad de edad"
mostraba la unidad guardada en el alta, que queda desactualizada cuando el
niño/a cumple el año.

## Solución

- `calcular_edad_y_unidad(fecha_nacimiento, hoy=None)` en `models.py`: la regla
  que ya usaba el formulario (meses antes del primer año, años cumplidos
  después). El formulario la reutiliza en lugar de duplicarla.
- `NominaCentroInfancia.edad_display` devuelve la edad al día de hoy con su
  unidad ("8 meses", "1 año", "2 años").
- El detalle muestra `edad_display` y se quita la fila "Unidad de edad", que
  quedaba incluida en la edad y podía estar vieja. El campo `edad_unidad` se
  sigue guardando como antes.

## Validación

Tests en `src/backends/cdi/centrodeinfancia/tests/test_destinatario_views.py`:
cálculo en meses y años (incluido el borde del primer año) y el detalle
mostrando la edad calculada aunque la unidad guardada sea vieja.
