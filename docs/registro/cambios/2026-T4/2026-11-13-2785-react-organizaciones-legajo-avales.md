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

- `web_api_secciones.py` suma `seccion_en_linea(variable)`: registra el
  constructor de un bloque `{% if <variable> %}` en línea. El primer pedido de la
  API envuelve ese nodo en memoria con un nodo que, sin recolector, renderiza
  exactamente igual que antes (la página nativa no cambia). Con la API
  recolectando, un bloque no vacío se reemplaza por
  `<div data-legajo-seccion="N"></div>` y el JSON del constructor se agrega a
  `sections` en orden de renderizado.
- `web_api_firmantes.py` registra `seccion_avales` (`kind: "avales"`): nombre,
  CUIT (`-` si falta), URLs de edición y baja, `can_manage` y `add_url` con el
  mismo permiso que el nativo (`puede_gestionar_organizaciones`). Sin avales
  muestra «No hay avales registrados.».
- React: `AvalesSection` en `organizacionFirmantes.tsx`, montada por
  `organizacionesLegajo.tsx`. Los marcadores ahora llevan `display: contents`
  para que un marcador vacío no sea un ítem más del contenedor flex del
  encabezado de rendiciones (en móvil sumaba 16 px del `gap`).
- Formulario de organización: se quita `noValidate`, como la página nativa, para
  que el navegador bloquee el envío con los campos requeridos vacíos («Completa
  este campo») antes de llamar a la API.

## Verificación

Pruebas nuevas de backend (sección con filas, vacía, solo «Asociación de hecho»,
técnico de dupla sin acciones, página nativa intacta) y de frontend. Ver el
informe de entrega de la ola para suites, G1 y paridad visual.

## Limitaciones

- Cabecera, selector de programa, datos de la organización, región, proyectos,
  comedores y pestañas del legajo siguen como HTML nativo.
- El envoltorio en memoria del bloque en línea depende de que el nodo siga
  probando la variable `avales` en la plantilla.
