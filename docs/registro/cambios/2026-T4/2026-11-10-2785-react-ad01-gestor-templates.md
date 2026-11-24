# Cambio: consultas del gestor de templates en React sobre G1 v1 (#2785, AD01)

## Alcance

Entregas AD01.01 (consulta) y AD01.03 (vista previa) del
[contrato AD01](../../../plans/2026-T4/2026-11-10-2785-admisiones-gestor-templates-ad01-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md):
listado y detalle de templates, variables documentales, buzón de incidencias y
detalle de incidencia. No cambia vistas, formularios, servicios, modelos,
plantillas ni URLs nativas. No activa React en producción.

Archivos:

- `src/backends/comedores/admisiones/web_api_templates.py` y
  `src/backends/comedores/admisiones/web_api_templates_urls.py`: API web de solo
  lectura, incluida desde `src/backends/comedores/comedores_runtime/web_api_urls.py`.
  `src/backends/config/url_registry.json` se regeneró con `generar_registro_urls`.
- `src/backends/config/middlewares/admindocs.py`: las rutas nuevas quedan fuera
  del atajo HEAD de admindocs.
- `src/backends/comedores/admisiones/web_preview_templates.py`: entradas React
  sin montar (`templates_preview_patterns`), solo para un URLconf local.
- `src/frontends/apps/sisoc/src/routes/admisionesTemplates.tsx` (ruta y
  pantallas) y su registro en `routes/index.ts`.
- Pruebas: `src/backends/comedores/admisiones/tests/test_web_gestor_templates_api.py`,
  `src/backends/comedores/admisiones/tests/test_web_preview_gestor_templates.py` y
  `src/frontends/apps/sisoc/src/routes/admisionesTemplates.test.tsx`.

## Comportamiento

| Ruta | Vista nativa que corre |
|---|---|
| `GET /api/web/comedores/admisiones/plantillas-informe/` | `PlantillaInformeTecnicoListView`: estado por defecto `activa`, `todas` no filtra, filtros por choice válidos, 50 por página, página inválida 404 |
| `GET .../plantillas-informe/<pk>/` | `PlantillaInformeTecnicoDetailView`: versión en preparación e historial |
| `GET .../plantillas-informe/variables/` | `VariableTemplateInformeTecnicoListView`: `activas` por defecto, 100 por página |
| `GET .../plantillas-informe/incidencias/` | `IncidenciaTemplateInformeTecnicoListView`: `pendiente` por defecto, 50 por página |
| `GET .../plantillas-informe/incidencias/<pk>/` | `IncidenciaTemplateInformeTecnicoDetailView`: casos y formulario de gestión sin ligar |

Cada endpoint ejecuta la vista nativa (`setup()`, queryset, contexto) y
proyecta su contexto a JSON; fechas `d/m/Y H:i` en la zona horaria activa,
`truncatechars:85`, `|title` y `|default:"-"` como en las plantillas. Los
mensajes pendientes de Django se consumen y se muestran con la apariencia de
Toastr. Respuestas `private, no-store`.

Acceso, en este orden: G1 (sesión 401, requisitos web 403 con `state`, firma
del core en el runtime separado) y la doble guarda nativa sin cambios
(`permissions_any_required` y `GestorTemplatesPermissionMixin` con
`admisiones.gestionar_templates_informe_tecnico`, superusuario incluido). Sin
alcance por objeto, igual que el HTML.

Acciones (AD01.02, fuera de esta entrega): la pantalla React dibuja los mismos
formularios nativos (crear versión, usar como punto de partida, publicar,
descartar con la confirmación «¿Descartar la versión en preparación? Esta
acción no se puede deshacer.», inactivar, eliminar/activar variable con `next`
y gestionar incidencia) y los envía por POST con CSRF a su URL nativa. La vista
Django decide, guarda y redirige; la página React siguiente muestra el mensaje
nativo. Un formulario de incidencia inválido vuelve a la página Django, como
hoy. El formulario de alta y el editor de versión (Summernote) siguen siendo
páginas Django y la pantalla enlaza a ellas: el editor AD01.02 opcional no se
migró en esta entrega.

Vista previa (AD01.03): sigue siendo el GET nativo
`/comedores/configuracion/templates/<p>/versiones/<v>/previsualizar/` desde el
editor Django; el URLconf de preview no la intercepta. Bugs nativos AD01-B1 a
B3 sin cambios (la API no acepta `next`; el toggle sigue siendo la vista
nativa).

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo sobre la base (19 de la API y la entrada sin
  módulo) y en verde (24). Suites de `admisiones`, `comedores/comedores`,
  `duplas`, `test_web_gate`, `test_backend_proxy`, `test_servicios_backends`,
  registro de URLs, `black`, `pylint` y `makemigrations --check`.
- Frontend: prueba de ruta en rojo (9 de 9) y en verde; `tsc`, ESLint y build.
- Visual (regla S13), nativo contra React, 15 estados (listados con filtros,
  vacíos, detalle con borrador, sin historial e inactivo, variables,
  incidencias y detalle con y sin casos) en 1440x900 y 390x844: contenido fuera
  del menú con el mismo texto, controles y estilos, desvío geométrico máximo de
  0,02 px y diferencia de píxeles 0 %. Guardas (anónimo, sin permiso, objeto y
  página inexistentes) iguales en los dos lados.
- Recorrido en React: alternar variable, gestionar incidencia, publicar (con
  el error nativo de contenido vacío), descartar con confirmación y crear
  versión llegan a la URL nativa y muestran el mensaje nativo.

## Limitaciones

- Diferencias del marco compartido (`SisocShell`): nombre accesible del logo
  (primer Tab), estructura del menú móvil y, con el menú largo del
  superusuario, la altura del menú lateral. Quedan fuera de esta unidad.
- El editor de versión y el alta quedan en Django (híbrido documentado).
