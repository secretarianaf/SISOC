# Cambio: región por proyecto, edición del código de proyecto y filtros por programa

## Alcance

Pedido funcional sobre el legajo y la edición de organizaciones y los listados
de Organizaciones y Comedores:

- Región y Subzona/Aglomerado pasan de la organización a cada proyecto, en el
  alta de proyectos de Editar organización
  (`src/backends/comedores/gestion_organizaciones/forms.py`,
  `src/backends/comedores/gestion_organizaciones/templates/organizacion_form.html`).
- Opción "AMBA" en ambos catálogos.
- Etiquetas "Subzona/Aglomerado" y "Territorial/Supervisor" en lo de
  organización.
- "Editar código" de un proyecto: en el formulario si no está guardado, en una
  pantalla propia si lo está
  (`src/backends/comedores/gestion_organizaciones/services/proyectos.py`).
- Legajo: una tarjeta "Proyectos y Convenio" por línea, con una fila
  desplegable por proyecto; se quitan las tarjetas "Datos de Región" y "Datos de
  Convenio"
  (`src/backends/comedores/gestion_organizaciones/templates/organizaciones/partials/legajo/proyectos_convenio.html`).
- Filtros de Programa, Región y Subzona con opciones fijas en ambos listados
  (`src/backends/comedores/comedores/services/filter_config/impl.py`,
  `src/backends/comedores/gestion_organizaciones/filter_config.py`).

Fundamento y trade-offs: [decisión](../../decisiones/2026-11-14-region-por-proyecto-y-edicion-codigo.md).

## Comportamiento

- Migración `organizaciones.0027`: suma región/subzona a los proyectos, copia la
  de la organización a los que no tenían y crea AMBA. Sin datos perdidos ni
  pisados.
- La organización ya no edita región/subzona; su dato anterior se muestra como
  referencia y se propone al agregar un proyecto. Un cliente que envíe
  `proyectos_lineas` sin región no borra la de los proyectos.
- "Editar código" de un proyecto guardado actualiza proyecto y comedores juntos;
  si el prefijo AMBA cambia la línea de las rendiciones nuevas, pide
  confirmación. Las rendiciones existentes no se modifican.
- Territoriales/Supervisores anteriores sin proyecto se ven como aviso en la
  tarjeta de proyectos hasta asignarlos.
- Filtros: "Programa" pasa de texto a opciones en Comedores y se agrega en
  Organizaciones. Un favorito guardado como "Programa contiene…" queda obsoleto,
  como cualquier filtro que cambia de tipo.

## Verificación

Local, en Docker:

- Nuevos: `src/backends/comedores/gestion_organizaciones/tests/test_proyecto_codigo.py`,
  `src/backends/comedores/gestion_organizaciones/tests/test_proyecto_codigo_integracion.py`
  (legajo, rendiciones del comedor, notificaciones y listado PWA tras cambiar el
  código), `src/backends/comedores/tests/test_filtros_programa_region.py` y tests
  de la migración en `src/backends/comedores/tests/test_issue_2642_catalogo_excel.py`.
- Adaptados al comportamiento por proyecto: tests #2642, #2745 y #2445.
- Suite completa de `src/backends/comedores` y `src/backends/kernel/organizaciones`:
  2424 OK; 8 fallas que se repiten igual en development sin estos cambios
  (N+1 del admin y `test_issue_2641_c2_http`).
- Migración aplicada sobre la base MySQL local con datos de ejemplo.
- `black`, `pylint`, `djlint` de templates nuevos y `makemigrations --check`.
- Quien pidió el cambio lo revisó en el entorno local durante el desarrollo
  (formulario, legajo y edición de código). El resguardo de línea AMBA y los
  filtros nuevos no se verificaron en pantalla.

No cubierto por tests automáticos: el JavaScript del formulario (no hay Node en
el entorno; se validó su sintaxis con un contenedor de Node).
