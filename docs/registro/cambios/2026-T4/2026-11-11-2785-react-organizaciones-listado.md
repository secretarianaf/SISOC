# Cambio: listado y legajo de organizaciones en React sobre G1 v1 (#2785, O05.01)

## Alcance

Primera parte de O05.01 del
[contrato O05](../../../plans/2026-T4/2026-11-10-2785-organizaciones-ficha-abm-o05-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md):
el listado `/organizaciones/listar` con búsqueda, filtros, orden por columna en
el cliente, paginación y el enlace al CSV nativo, y el legajo
`/organizaciones/detalle/<pk>`. El ABM (O05.02) y programas/proyectos (O05.03)
quedan para entregas siguientes.

No cambia vistas, formularios, servicios, modelos, plantillas, JavaScript ni
URLs nativas. No activa React en producción.

Archivos:

- `src/backends/comedores/gestion_organizaciones/web_api.py` y
  `src/backends/comedores/gestion_organizaciones/web_api_urls.py`, incluidos
  desde `src/backends/comedores/comedores_runtime/web_api_urls.py`;
  `src/backends/config/url_registry.json` regenerado con `generar_registro_urls`.
- `src/backends/config/middlewares/admindocs.py`: la ruta nueva queda fuera del
  atajo HEAD de admindocs.
- `src/backends/comedores/gestion_organizaciones/web_preview.py`: entrada React
  sin montar (`organizaciones_preview_patterns`), assets en
  `/organizaciones/react/assets/`.
- `src/frontends/apps/sisoc/src/routes/organizaciones.tsx` y
  `src/frontends/apps/sisoc/src/routes/organizacionesList.tsx`, registrados en
  `routes/index.ts`; reutilizan `Filters` y `Pagination` de `listControls.tsx`.
- Pruebas:
  `src/backends/comedores/gestion_organizaciones/test_web_organizaciones_listado_api.py`,
  `src/backends/comedores/gestion_organizaciones/test_web_preview_organizaciones.py`
  y `src/frontends/apps/sisoc/src/routes/organizaciones.test.tsx`.

## Comportamiento

`GET /api/web/comedores/organizaciones/listado/` ejecuta `OrganizacionListView`:
búsqueda simple `busqueda`, filtros `filters`, orden `-id`, 10 por página con
`NoCountPaginator` (página fuera de rango: última página con datos; sin 404 ni
total de resultados). Las filas salen del include nativo
`organizaciones/partials/organizacion_rows.html`: texto, valor `data-*` que usa
`listSort.js` y acciones «Ver», «Editar», «Eliminar».

Acceso sin cambios (ver
[brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)):
G1 primero (401 sin sesión, 403 con `state` si hay un requisito pendiente);
después uno de `ORGANIZACION_DOCUMENTACION_PERMS`, con el alcance de dupla para
técnicos y abogados. «Agregar», «Editar» y «Eliminar» solo con superusuario o
`organizaciones.view_organizacion`; «Exportar búsqueda» con superusuario o
`auth.role_exportar_a_csv`. El CSV sigue siendo `/organizaciones/exportar` con
la query vigente y el orden del cliente (`export_helper.js`). Solo GET y HEAD;
la lectura no escribe en la base.

## Legajo

`GET /api/web/comedores/organizaciones/<pk>/` ejecuta `OrganizacionDetailView`
(alcance de dupla: objeto ajeno o inexistente, 404; parámetros `programa`,
`seccion` y `proyecto` tal cual los lee `datos_legajo`) y devuelve el bloque
`content` de `organizacion_detail.html` con sus parciales como fragmento HTML
renderizado por el servidor, más el título, los mensajes pendientes y la lista
de scripts nativos (`organizacionesDocumentos.js`). React
(`organizacionesLegajo.tsx`) monta el fragmento dentro del marco compartido,
carga el script una vez y ejecuta sus inicializadores, como hace
`DOMContentLoaded` en la página nativa. Los enlaces (selector de programa,
pestañas, Editar, Eliminar, convenio, firmantes) siguen siendo los nativos.

Decisión tomada: las secciones de O01 a O04 (convenios, documentación,
firmantes y avales, rendiciones) se muestran como fragmentos nativos hasta que
esas entregas existan. Por la misma vía quedan hoy también el encabezado, el
selector de programa y los datos de la organización, que el contrato asigna a
O05.01: migrarlos a componentes React propios es trabajo pendiente.

## Alta, edición y baja (O05.02, O05.03)

`/api/web/comedores/organizaciones/` ejecuta las vistas nativas: `formulario/` y
`<pk>/formulario/` proyectan el `OrganizacionForm` real (campos, opciones,
valores, errores); `crear/` (201) y `<pk>/editar/` (200) llaman al `post` de
`OrganizacionCreateView` y `OrganizacionUpdateView` (validación, guardado,
reinicio del legajo por cambio de tipo y su aviso); errores 400 con los textos de
Django; `<pk>/baja/` (GET vista previa, POST baja, 409 con el motivo nativo);
`subtipos/` y `cuil/` sirven los JSON nativos. Programas y proyectos viajan en el
mismo POST. Acceso: `view_organizacion`, sin alcance de objeto (como hoy).
React: `organizacionesForm.tsx` y `organizacionesBaja.tsx`; los mensajes de
Django pasan a la pantalla siguiente por `sessionStorage`.

## Verificación

Entorno sintético, sin red, imagen fijada. Backend: pruebas nuevas en rojo
sobre la base (17 de 17 sin ruta; vista previa sin módulo) y en verde (21).
Frontend: prueba en rojo (módulo inexistente) y en verde; Vitest tres veces,
`tsc`, ESLint (solo la advertencia previa de `cdfFilters.tsx`) y build de Vite.

## Limitaciones

- El legajo es un fragmento nativo; no hay componentes React propios para sus
  secciones (ver "Legajo").
- Las acciones del legajo (documentación, firmantes, convenios) siguen en las
  páginas y endpoints nativos.
- El ABM y programas/proyectos no están migrados.
