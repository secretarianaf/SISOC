# Cambio: lista y detalle de ofertas institucionales y detalle de curso de VAT en React sobre G1 v1 (#2785, V05.01, U6)

## Alcance

Unidad U6 del [contrato V02 a V07](../../../plans/2026-T4/2026-11-13-2785-vat-v02-v07-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): lista y detalle de ofertas institucionales
(`/vat/ofertas-institucionales/`, `<pk>/`) y detalle de curso (`/vat/cursos/<pk>/`). Lee por `OfertaInstitucionalListView`,
`OfertaInstitucionalDetailView` y `CursoDetailView`, sin tocar vistas, servicios, plantillas ni URLs nativas. No activa React en
producción. Se conserva el alcance de cada vista (paridad). `vat_centro_cursos_panel` queda nativo (equipo de centros).

Archivos:

- `src/backends/vat/VAT/web_api_oferta_curso.py` (rutas en `web_api_urls.py`), `url_registry.json` regenerado y `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat_oferta_curso.py`: entradas de vista previa de las tres rutas.
- `src/frontends/apps/sisoc/src/routes/vatOferta.tsx`, `vatCursoDetalle.tsx` y `vatCursoDetalleStyles.ts`, registrados en `routes/index.ts`.
- Pruebas: `test_web_vat_oferta_curso_v06.py` y `vatOferta.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y `VAT.view_ofertainstitucional` o `VAT.view_curso` (403); 404 si la oferta o el curso no existe o queda fuera del
  alcance de la vista nativa (también en la entrada de vista previa), y 404 en una página inválida de la lista.
- Los textos salen del motor de plantillas de Django (`d/m/Y`, coma decimal, `default`), como en las plantillas nativas; cada respuesta trae `messages`.
- El detalle de oferta dibuja «Editar» y «Eliminar» a todos los usuarios (la plantilla nativa no consulta permisos); la lista y el detalle de curso sí
  respetan `change/delete_ofertainstitucional` y `change_curso` más el alcance de edición del centro.
- Las ordenaciones por columna de la lista (`listSort.js`) y el tour de ayuda se reproducen en el cliente.

## Verificación

- Backend (imagen fijada, sin red): acceso, proyección, filtros, comparación con los textos de la página nativa y entradas de vista previa; `black`, `pylint`
  y `makemigrations --check`.
- Frontend: `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo y comparación visual nativo contra React (lista, detalle de oferta, detalle de curso con y sin permiso de edición; escritorio y móvil).

## Pendiente

Alta, edición y baja de ofertas y cursos (U7).
