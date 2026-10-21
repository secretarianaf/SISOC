# 2026-10-20 - Datos por programa de la Organización en gestion_organizaciones (#2745)

## Estado
- propuesta (aprobada funcionalmente por el área usuaria el 20/10/2026;
  se revisa en el PR de documentación del issue #2745, antes de implementar)

## Contexto
- El legajo de Organización debe desdoblarse por programa (Alimentar
  Comunidad, Abordaje Comunitario – Línea Secos y Línea Tradicional). Las
  definiciones funcionales y el roadmap están en
  `docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md`.
- Hacen falta datos nuevos: programas de la organización, línea de cada
  proyecto, Región/Subzona y Datos de Convenio por proyecto. Todos dependen
  de `comedores.Programas` o son propios de Abordaje.
- `Organizacion` y `ProyectoOrganizacion` viven en el kernel
  (`src/backends/kernel/organizaciones/models.py`); `Programas` vive en el
  vertical Comedores (`src/backends/comedores/comedores/models.py`). El kernel
  no puede depender de verticales (contrato `kernel-no-core-ni-backends`,
  `docs/desarrollo/verticales_independientes.md`). Por la misma razón
  `Firmante` ya vive en `gestion_organizaciones`.
- Los programas se reconocen hoy comparando el nombre del registro elegido
  en el desplegable, con funciones de `src/backends/comedores/comedores/utils.py`.
- Las vistas de organización, firmante y aval exigen
  `organizaciones.view_organizacion`; el área usuaria pidió no sumar permisos
  ni grupos.

## Decision
- Los modelos nuevos van en `src/backends/comedores/gestion_organizaciones/`
  (backend `comedores`): `ProgramaOrganizacion`, `LineaProyecto` (1:1 con
  `ProyectoOrganizacion`), `RegionAbordaje`, `SubzonaAbordaje`,
  `DatosRegionOrganizacion` (1:1 con `Organizacion`) y `ConvenioProyecto`
  (1:1 con `ProyectoOrganizacion`). Nombres y campos en la sección 1.3 del
  plan.
- La línea del proyecto se guarda en la tabla nueva `LineaProyecto`. No se
  agrega una FK a `comedores.Programas` desde el kernel ni se mueve
  `ProyectoOrganizacion` de app.
- No se modifican tablas existentes del kernel. `Territorial` sigue en
  `Organizacion.territoriales_abordaje_comunitario`.
- El catálogo de Región (5) y Subzona (28) del Anexo A del plan se carga con
  una migración de datos reversible, para que sea igual en todos los
  entornos, y queda editable desde el admin.
- Para reconocer cada programa se agregan en `comedores/utils.py` variantes
  que reciben un `Programas` (patrón de `permite_codigo_de_proyecto`), porque
  `is_abordaje_comunitario_linea_secos_program` y
  `is_abordaje_comunitario_linea_tradicional_program` reciben un comedor y con
  un programa devuelven `False` sin error. Las funciones actuales las usan por
  dentro sin cambiar su resultado. No se agrega un campo nuevo a `Programas`.
- Carga inicial versionada: una migración de datos idempotente de la Etapa 1
  crea `ProgramaOrganizacion` a partir de los programas de todos los
  comedores de cada organización (incluidos los dados de baja y los
  programas distintos de los tres) y asigna a cada proyecto existente la
  línea de los comedores que lo usan: hoy la línea está en el comedor y pasa
  al proyecto (confirmado por el área usuaria el 21/10/2026). Los proyectos
  con comedores de líneas distintas o sin comedores quedan sin línea y se
  informan en el log. Reemplaza la query manual: es reproducible en QA,
  homologación y producción.
- No se pierde información (requisito del área usuaria, sección 2.1 del
  plan): migraciones de esquema solo aditivas; migraciones de datos que solo
  agregan filas en tablas nuevas, idempotentes y con reversa `noop`; FKs
  nuevas con `on_delete=PROTECT`; formularios que desactivan en lugar de
  borrar; auditoría en Historial; y un legajo donde todo registro existente
  tiene un lugar visible (bloques "Sin programa asignado" y "Rendiciones de
  otras líneas", programas distintos de los tres y Documentación aunque
  falte Alimentar).
- Mientras una organización no tenga programas cargados, las reglas nuevas
  de `ComedorForm` y `FirmanteForm` no se aplican: el alta y la edición
  funcionan como hoy. Esto evita bloquear altas si alguna etapa llega a
  producción antes que los datos (no hay feature flag).
- La línea de una rendición la define
  `RendicionCuentaMensual.linea_programatica`, no `LineaProyecto`. Las
  rendiciones sin proyecto se muestran en la pestaña de su línea; una
  rendición con línea distinta a la de su proyecto se muestra en la de su
  propia línea.
- Las acciones nuevas usan los controles existentes:
  `permissions_any_required(["organizaciones.view_organizacion"])` en las
  vistas y `_puede_ver_todas_las_organizaciones` para mostrar acciones en el
  legajo. No se crean permisos ni grupos. Para Datos de Convenio esto
  significa que un permiso de lectura habilita escribir montos: el área
  usuaria lo acepta como riesgo conocido (21/10/2026) para no sumar permisos.

Checklist 1 de `docs/desarrollo/verticales_independientes.md` (app en un
vertical existente), recorrido sobre `gestion_organizaciones`:

- Mismo servicio y dependencias permitidas: sí. `gestion_organizaciones`,
  `comedores` y `rendicioncuentasmensual` están en el backend `comedores`
  (`src/backends/config/backends.json`); las FKs al kernel
  (`organizaciones`) están permitidas.
- App existente: no se crea ni se mueve ninguna app; no cambia el label.
- `backends.json`: sin cambios; la app ya figura en `apps` del backend.
- URLs: la pantalla de convenio cae bajo el prefijo existente
  `organizaciones/` y el admin bajo `admin/gestion_organizaciones/`; no se
  agregan prefijos. Sí hay que regenerar `src/backends/config/url_registry.json`.
- Contratos de imports: sin cambios esperados; verificar con
  `import-linter` en cada PR.
- Runtime aislado, permisos, tests y `service_images`: a verificar en cada
  PR de implementación (no ejecutado en esta etapa).

Esta decisión la propuso el agente a partir del código; el área usuaria
aprobó la ubicación de los datos y el uso de permisos existentes. La carga
inicial versionada, las reglas que no bloquean sin programas, la fuente de
la línea de las rendiciones y la aceptación del riesgo de permisos del
convenio responden a la revisión del PR #2746 (21/10/2026) y las eligió el
área usuaria entre las opciones propuestas.

## Consecuencias
- Positivas: respeta el boundary kernel/vertical, todos los cambios de
  esquema son aditivos y no requieren migraciones de estado ni mover tablas.
  El legajo puede filtrar todo por programa sin tocar el kernel.
- Costos: la línea del proyecto queda en una tabla aparte del proyecto (un
  join más). Para saber si un programa es Secos o Tradicional se sigue
  dependiendo del nombre del registro: renombrar un programa desde el admin
  rompe ese reconocimiento.
- La carga inicial viaja con la Etapa 1, así que no hay un orden de
  despliegue que cuidar. Los proyectos con comedores de líneas distintas (o
  sin comedores) quedan sin línea y se completan a mano desde la edición de
  la organización.
- Mientras una organización no tenga programas, sus comedores y firmantes no
  quedan restringidos: es una ventana deliberada para no bloquear la
  operación.
- Una rendición con línea distinta a la de su proyecto aparece en una
  pestaña distinta a la del proyecto. Corregir esos datos queda fuera de
  alcance.
- Riesgo aceptado: quien puede ver organizaciones puede cargar montos de
  convenio.

## Referencias
- Issue: #2745. Revisión: PR #2746.
- Plan: `docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md`.
- Guía de verticales: `docs/desarrollo/verticales_independientes.md`.
- Precedente: `Firmante` en
  `src/backends/comedores/gestion_organizaciones/models.py`.
