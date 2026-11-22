# Cambio: catálogos de VAT en React sobre G1 v1 (#2785, V07.01 y V07.02)

## Alcance

Unidades **U10** (listados y detalles) y **U11** (alta, edición y baja) del
[contrato V02 a V07](../../../plans/2026-T4/2026-11-13-2785-vat-v02-v07-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md). Cuatro catálogos bajo `/vat/catalogos/`:
sectores, subsectores, modalidades de cursado y títulos de referencia; cada uno con lista, detalle, alta, edición y baja
(20 rutas nativas). Lee y escribe por las vistas nativas `{Sector,Subsector,ModalidadCursada,TituloReferencia}
{List,Detail,Create,Update,Delete}View`, sin tocar vistas, formularios, plantillas ni URLs nativas. No activa React en
producción. Se conserva el alcance de cada vista (paridad); cualquier acotamiento, incluido #2794, queda para un ticket
aparte.

Archivos:

- `src/backends/vat/VAT/web_api_catalogos.py` (listas y detalles) y `web_api_catalogos_forms.py` (formularios y bajas),
  rutas en `web_api_urls.py`, `url_registry.json` regenerado y `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat_catalogos.py`: entradas de vista previa de las veinte rutas.
- `src/frontends/apps/sisoc/src/routes/vatCatalogos.tsx` (listas y detalles), `vatCatalogosForm.tsx` (formularios y
  bajas) y `vatCatalogosStyles.ts` (el `<style>` del formulario de modalidad), registrados en `routes/index.ts`.
- Pruebas: `test_web_vat_catalogos_v07.py` y `vatCatalogos.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y el permiso de la ruta nativa (`view`, `add`, `change` o `delete` del modelo; 403),
  404 si no existe, CSRF en los POST (403).
- Las listas conservan el queryset nativo (de a 50, orden por nombre) y los botones Editar y Eliminar según permiso. El
  listado de modalidades usa filtros combinables (`filters_config` nativo); los otros tres traen la barra simple, cuyo
  parámetro `busqueda` la vista nativa no filtra (se conserva). La descripción sale con `truncatewords:10`.
- El alta y la edición corren `form_valid` nativo y encolan su mensaje (por ejemplo «Sector creado correctamente.»); con
  el formulario inválido responden 400 sin guardar, con los errores de cada campo. La baja corre el `post` nativo de
  `DeleteView`; la de títulos pasa por `SoftDeleteDeleteViewMixin` (baja lógica).
- Quirks conservados: la lista de subsectores imprime `None` si la descripción es nula; el detalle de sector y de título
  borra con un formulario POST que pide `confirm('¿Está seguro?')`, los otros dos con un enlace a la confirmación; los
  formularios genéricos conservan la validación del navegador (`required`), el de modalidad lleva `novalidate`.
- Defecto nativo documentado: la confirmación de baja de un título (`/vat/catalogos/titulos-referencia/<pk>/eliminar/`)
  da 500 en la ruta nativa, porque la plantilla usa `titulo` y la vista expone `tituloreferencia`. La API lee el nombre
  del contexto de la vista y la página React lo muestra; la baja desde el detalle (POST directo) ya funcionaba.
- `vat_subsectores_por_sector` (`/vat/catalogos/ajax/subsectores/`) no se usa en estos formularios y queda nativo.

## Verificación

- Backend (imagen fijada, sin red): `test_web_vat_catalogos_v07.py` (acceso por ruta, proyección de listas y detalles,
  comparación con los textos de la página nativa, alta y edición por su efecto persistido, «sin cambios» ante formulario
  inválido, CSRF, permiso y sesión, y entradas de vista previa), `test_web_gate`, `test_backend_proxy` y
  `test_servicios_backends`; `black`, `pylint` y `makemigrations --check`.
- Frontend: `vitest --project sisoc` completo, `tsc`, `eslint` y build.
- G1 de extremo a extremo y comparación visual nativo contra React (listas, detalles, formularios, formulario con error y
  bajas; escritorio y móvil) y guardas.
