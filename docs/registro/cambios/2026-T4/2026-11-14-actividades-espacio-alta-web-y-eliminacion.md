# Cambio: alta web de actividades de Abordaje Comunitario y eliminación lógica

## Alcance

Pedido funcional sobre la sección de actividades de los comedores de Abordaje
Comunitario (programas PNUD), más un ajuste visual del legajo de organización:

- **Formulario de alta y edición**
  (`src/backends/comedores/comedores/templates/comedor/actividad_espacio_pwa_form.html`,
  `src/backends/comedores/comedores/forms/actividad_espacio_pwa_form.py`): mismo
  estilo que "Datos del Convenio" (secciones plegables, filas etiqueta/campo,
  barra de acciones fija), flecha en los desplegables y dos campos nuevos,
  "Nombre de fantasía" (texto) y "Número de personas" (entero, sin lógica).
- **Días y horarios**: cada horario agrupa varios días con la misma hora de
  inicio y fin; "Nuevo horario" agrega otro grupo.
- **Eliminación**: botón "Eliminar" en la tabla de actividades de la ficha del
  comedor, con confirmación y borrado lógico en cascada sobre los inscriptos
  (`ActividadEspacioPWADeleteView`, `eliminar_actividad_espacio`).
- **Legajo de organización**
  (`src/backends/comedores/gestion_organizaciones/templates/organizacion_detail.html`):
  se quita el ícono que ocupaba el lugar de la foto y los datos pasan a dos
  columnas.

## Comportamiento

- Se sigue guardando un registro por día: marcar Lunes, Miércoles y Viernes de
  11 a 12 crea tres actividades. La API de la PWA y los listados no cambian. El
  formulario sigue aceptando el POST anterior (un día por fila).
- "Nombre de fantasía" y "Número de personas" son opcionales. La tabla de la
  ficha muestra la columna "Número de personas" y el nombre de fantasía debajo
  de la actividad. La API de la PWA devuelve `nombre_fantasia` (solo lectura) en
  el listado y el detalle de actividades; mostrarlo es un cambio del repositorio
  de la PWA. "Número de personas" no se expone.
- Eliminar no es inactivar: la actividad y sus inscriptos dejan de verse en la
  web y en la PWA, quedan con `deleted_at`/`deleted_by` y se restauran desde la
  Papelera. No cambia `activo` ni la nómina. El evento queda en
  `AuditoriaOperacionPWA` con acción `delete` y los ids de inscriptos.
  Fundamento: [decisión](../../decisiones/2026-11-14-eliminacion-logica-actividades-espacio.md).
- Migraciones `pwa.0028` (campos nuevos) y `pwa.0029` (columnas de borrado
  lógico): solo agregan columnas que admiten nulos o tienen valor por defecto.

## Verificación

Local, en Docker:

- `src/backends/comedores/tests/test_actividad_espacio_web_horarios.py` (8) y
  `src/backends/comedores/tests/test_actividad_espacio_web_eliminar.py` (9):
  pasan. Cubren grupos de días, superposición, formato anterior, cascada,
  nómina sin cambios, otras actividades intactas, restauración, permisos y
  aislamiento por comedor.
- `makemigrations --check`, `black`, `pylint` y `djlint` sobre los archivos
  tocados.
- Verificación manual en el entorno local: quien pidió el cambio probó el
  formulario, el agrupado de días, los campos nuevos, la eliminación y el legajo
  de organización, y los dio por correctos.
- La suite completa de `src/backends/comedores` pasó localmente antes de sumar la
  eliminación; con la eliminación no se pudo terminar (Docker local sin
  recursos) y queda a cargo de CI.

No corrido localmente: el test JS
`src/backends/comedores/tests/js/rendicionVisualizacion.test.js` (no hay Node
en el entorno); queda para CI.
