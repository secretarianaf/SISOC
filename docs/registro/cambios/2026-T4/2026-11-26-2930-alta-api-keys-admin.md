# Botón de alta de API keys en el admin (#2930)

## Alcance

El listado de API keys vuelve a mostrar el botón de alta de Unfold cuando el usuario tiene permiso para crear claves. El registro de la dependencia hereda de Django y no declara el atributo que la plantilla de Unfold consulta para mostrar ese botón.

## Comportamiento

SISOC registra una subclase del admin provisto por la dependencia que habilita el botón. El formulario de alta incluye Cancelar para volver al listado sin guardar y recuperar los filtros anteriores. Los permisos y la generación de claves siguen a cargo de las implementaciones existentes.

## Verificación

Se reprodujo la ausencia del botón en local. Las pruebas cubren el acceso del listado al formulario, el rechazo sin permiso de alta y el guardado en una base de pruebas. Se confirmó visualmente que el botón de alta abre el formulario. La revisión manual también confirmó que Cancelar vuelve al listado.
