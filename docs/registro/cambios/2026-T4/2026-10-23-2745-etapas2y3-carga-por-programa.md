# Cambio: carga de datos por programa en la Organización, Etapas 2 y 3 (#2745)

## Alcance

Etapas 2 y 3 del plan
`docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md`, en un
solo PR (agrupación decidida el 23/10/2026). El legajo
(`organizaciones/detalle/<id>`) todavía no cambia: se rediseña en la Etapa 5.

- Servicios nuevos en
  `src/backends/comedores/gestion_organizaciones/services/programas.py`:
  programas de la organización en orden del legajo, si aplican las reglas
  (definición 22), proyectos por línea y sin línea, firmantes y comedores por
  programa, rendiciones por línea, datos asociados a un programa, motivo que
  impide la baja y resumen del convenio.
- `RendicionesOrganizacionService.obtener_rendiciones`
  (`src/backends/comedores/rendicioncuentasmensual/services.py`) acepta
  `linea_programatica` opcional; sin ese parámetro el resultado no cambia.
- `src/backends/comedores/comedores/utils.py`: `es_programa_alimentar_comunidad`.
- Filtro de template `monto` (`$100.000.000`) en
  `src/backends/comedores/gestion_organizaciones/templatetags/organizaciones_tags.py`.
- Edición de la organización
  (`src/backends/comedores/gestion_organizaciones/forms.py` y
  `templates/organizacion_form.html`): sección nueva "Programas" con los
  programas y una sola lista de proyectos: cada fila con código, línea y
  territoriales asignados. Reemplaza el campo `codigos_proyecto` por
  `proyectos_lineas`; `asignaciones_territoriales` (#2642) se valida contra
  los códigos de `proyectos_lineas`.
- Región y Subzona (decisión del 27/10/2026, al integrar con #2642): la
  región canónica es la de la organización
  (`Organizacion.region_abordaje`/`subzona_abordaje`, catálogo del kernel
  `RegionAbordajeComunitario`/`SubzonaAbordajeComunitario`), editable solo en
  la sección "Datos Abordaje Comunitario". Este PR no escribe
  `DatosRegionOrganizacion`. Los modelos `RegionAbordaje`, `SubzonaAbordaje`
  y `DatosRegionOrganizacion` de la Etapa 1 quedan sin uso en pantallas;
  su baja (con migración y revisión de datos cargados) es un seguimiento
  aparte.
- Pantalla nueva Datos de Convenio por proyecto
  (`organizaciones/proyectos/<id>/convenio/`, vista `ConvenioProyectoView`,
  `templates/convenio_proyecto_form.html`), con el mismo permiso que
  firmantes (`organizaciones.view_organizacion`, definición 24). Se accede
  desde cada proyecto con línea en la edición de la organización.
- Firmante: el programa se limita a los de la organización.
- Baja de organización (`OrganizacionDeleteView`): se bloquea con mensaje si
  tiene proyectos; se captura `ProtectedError`.
- `src/backends/config/url_registry.json` regenerado: agrega
  `organizacion_proyecto_convenio`.

## Comportamiento

- Organización sin programas: todo sigue como hoy. Los proyectos no exigen
  línea y el firmante ofrece todos los programas (definición 22).
- Con programas cargados: cada proyecto activo exige una línea entre los
  programas de Abordaje elegidos. Si no hay ninguno, el mensaje pide agregarlo
  o quitar el proyecto. Los proyectos que la carga inicial dejó sin línea la
  piden al volver a guardar.
- No se puede quitar un programa con proyectos, firmantes, comedores (incluidos
  los dados de baja) o rendiciones de su línea. Quitar uno sin datos borra su
  fila de `ProgramaOrganizacion`, y eso queda en Historial.
- Los programas ya cargados que no son de los tres del legajo (por ejemplo
  PNUD) siguen como opción, así que guardar no los quita.
- Quitar un proyecto lo desactiva, como hoy; su línea y su convenio se
  conservan.
- No se puede pasar a Línea Secos un proyecto cuyo convenio tiene Imprevistos.
- Región y Subzona siguen las reglas de #2642: opcionales, la subzona tiene
  que ser de la región elegida. La pantalla de convenio muestra la región de
  la organización.
- Territoriales: se asignan por proyecto en la lista de proyectos. Quitar un
  proyecto quita sus territoriales; las asignaciones anteriores sin proyecto
  se conservan hasta que se las quite, como en #2642.
- Convenio: Imprevistos solo en Línea Tradicional. Si la suma de componentes
  no coincide con el monto total, se avisa en pantalla y al guardar, pero no
  se bloquea.
- **Cambio visible: baja de organización.** Antes se borraban físicamente sus
  proyectos (sin baja lógica), o fallaba con error si algún comedor los usaba.
  Ahora no se puede dar de baja una organización que tenga proyectos: se
  muestra cuántos tiene y qué datos usan. Sin proyectos, la baja sigue igual.
- Preservación de datos (sección 2.1 del plan): sin migraciones. Los
  formularios no borran proyectos, líneas ni convenios, y
  todos los cambios en esas tablas quedan en Historial.

## Verificación

Local, en contenedor Docker de un solo uso (SQLite en memoria):

- `pytest src/backends/comedores/gestion_organizaciones/tests/test_issue_2745_organizacion_por_programa.py`:
  47 tests pasan.
  - Servicios: orden de programas, organización sin programas, rendiciones
    por línea (sin proyecto, línea cruzada, proyecto + línea) y resumen de
    convenio.
  - Formulario: alta y edición con y sin Abordaje, línea obligatoria, quitar
    programas, desactivar proyectos sin perder línea ni convenio, región y
    subzona.
  - Firmante, convenio con y sin Imprevistos, aviso de suma, sin permiso.
  - Baja con proyecto usado por comedor, con línea, con convenio y sin nada
    asociado.
- `pytest -n auto` sobre `gestion_organizaciones`, `comedores`,
  `comedores/tests`, `rendicioncuentasmensual` y `test_servicios_backends.py`:
  todos pasan, salvo `test_issue_2641_c2_http.py`, que también falla en
  `development` en el entorno local. Se ajustaron dos tests unitarios con
  mocks (`test_organizaciones_views_unit.py`) por las llamadas nuevas.
- `black`, `pylint` (10/10), `djlint --check`, `makemigrations --check` (sin
  cambios) y `lint-imports` (32 contratos): sin observaciones.
- Las pantallas de edición y de convenio responden 200 con la base local.

Integración con #2642 (27/10/2026): se ajustaron los tests de
`test_issue_2745_organizacion_por_programa.py` (región única con el catálogo
del kernel, territoriales por proyecto vía `proyectos_lineas`, convenio con
la región de la organización) y los de `test_issue_2642.py` y
`test_issue_2445_territorial_abordaje_organizacion.py`, que envían
`proyectos_lineas` en lugar de `codigos_proyecto`. Validados en CI; sin
verificación visual.
