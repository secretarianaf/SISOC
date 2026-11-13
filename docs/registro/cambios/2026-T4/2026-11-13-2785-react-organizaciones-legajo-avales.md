# Cambio: tabla de avales del legajo de organización en React (#2785, O03 y O05.01)

## Alcance

La tabla «Avales» del legajo (`organizacion_detail.html`, solo «Asociación de
hecho») pasa a React. Era el último bloque de O03 que seguía como HTML nativo:
no es un `{% include %}`, sino marcado en línea dentro de `{% if avales %}`. No
cambia vistas, formularios, plantillas, servicios, modelos ni URLs nativas, y no
activa React en producción. Las páginas de alta, edición y baja de aval ya eran
React. O05.02 y O05.03 (alta y edición con programas, proyectos y territoriales
en un solo POST) ya estaban entregadas con el ABM.

## Cómo funciona

- `web_api_firmantes.py` registra `seccion_avales` (`kind: "avales"`): nombre,
  CUIT (`-` si falta), URLs de edición y baja, `can_manage` y `add_url` con el
  mismo permiso que el nativo (`puede_gestionar_organizaciones`). Sin avales
  muestra «No hay avales registrados.». La API del legajo la incluye cuando el
  contexto trae `avales` (solo «Asociación de hecho»), en el lugar de la plantilla.
- React: `AvalesSection` en `organizacionFirmantes.tsx`, dibujada por
  `organizacionLegajoPagina.tsx`.
- Formulario de organización: se quita `noValidate`, como la página nativa, para
  que el navegador bloquee el envío con los campos requeridos vacíos («Completa
  este campo») antes de llamar a la API.

## Verificación

Pruebas nuevas de backend (sección con filas, vacía, solo «Asociación de hecho»,
técnico de dupla sin acciones) y de frontend. Ver el
informe de entrega de la ola para suites, G1 y paridad visual.

## Limitaciones

- Cabecera, selector de programa, datos de la organización, región, proyectos,
  comedores y pestañas del legajo siguen como HTML nativo.
- Cabecera, selector de programa, datos de la organización, región, proyectos y
  comedores: ver el registro del legajo en datos.
