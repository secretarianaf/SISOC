# 2026-10-20 - Datos por programa de la Organización en gestion_organizaciones

## Estado
- propuesta (aprobada funcionalmente por el área usuaria el 20/10/2026;
  pendiente de revisión técnica antes de implementar)

## Contexto
- El legajo de Organización debe desdoblarse por programa (Alimentar
  Comunidad, Abordaje Comunitario – Línea Secos y Línea Tradicional). Las
  definiciones funcionales y el roadmap están en
  `docs/plans/2026-T4/2026-10-20-legajo-organizacion-por-programa.md`.
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
- Para reconocer cada programa se reutilizan las funciones existentes de
  `comedores/utils.py` (o variantes que reciban el programa); no se agrega un
  campo nuevo a `Programas`.
- Las acciones nuevas usan los controles existentes:
  `permissions_any_required(["organizaciones.view_organizacion"])` en las
  vistas y `_puede_ver_todas_las_organizaciones` para mostrar acciones en el
  legajo. No se crean permisos ni grupos.

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
aprobó la ubicación de los datos y el uso de permisos existentes.

## Consecuencias
- Positivas: respeta el boundary kernel/vertical, todos los cambios de
  esquema son aditivos y no requieren migraciones de estado ni mover tablas.
  El legajo puede filtrar todo por programa sin tocar el kernel.
- Costos: la línea del proyecto queda en una tabla aparte del proyecto (un
  join más). Para saber si un programa es Secos o Tradicional se sigue
  dependiendo del nombre del registro: renombrar un programa desde el admin
  rompe ese reconocimiento.
- Los datos existentes (programas de cada organización y línea de cada
  proyecto) quedan vacíos hasta la carga inicial por query; el legajo nuevo
  no debe llegar a producción antes de esa carga.

## Referencias
- Plan: `docs/plans/2026-T4/2026-10-20-legajo-organizacion-por-programa.md`.
- Guía de verticales: `docs/desarrollo/verticales_independientes.md`.
- Precedente: `Firmante` en
  `src/backends/comedores/gestion_organizaciones/models.py`.
