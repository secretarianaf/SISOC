# Cambio: guardar una sede VPSL vuelve al listado de sedes (#2958)

## Alcance

En Ver Para Ser Libres, al guardar una sede (alta o edición) el sistema guardaba bien pero volvía a mostrar el mismo formulario de edición. Para quien usaba la pantalla parecía que el guardado no había hecho nada.

## Comportamiento

`SedeMixin.get_success_url` en `src/backends/vpsl/ver_para_ser_libre/views.py` ahora redirige a `vpsl_sede_list`. Tras guardar se ve el listado de sedes con el aviso «Sede guardada correctamente.». Aplica al alta y a la edición porque comparten el mixin. Si el formulario tiene errores se sigue mostrando el formulario con los errores, como antes.

## Verificación

`src/backends/vpsl/ver_para_ser_libre/tests/test_workflow.py` afirma el destino del redirect en alta y edición, el aviso de éxito y que el dato editado quedó guardado.

## Limitaciones

Después de crear una sede ya no se queda en su formulario para seguir completando datos opcionales o el checklist: hay que entrar con «Editar» desde el listado. No se probó en navegador.
