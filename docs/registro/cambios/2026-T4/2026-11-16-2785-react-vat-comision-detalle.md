# Cambio: detalle de comisión de VAT en React sobre G1 v1 (#2785, V04.01, U4)

## Alcance

Unidad U4 del [contrato V02 a V07](../../../plans/2026-T4/2026-11-13-2785-vat-v02-v07-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): la pantalla de detalle de comisión,
`/vat/comisiones/<pk>/` (oferta) y `/vat/cursos/comisiones/<pk>/` (curso), que comparten la plantilla
`comision_detail.html`. U4a es la lectura y U4b suma las acciones de la propia página: lee por `ComisionDetailView` y
`ComisionCursoDetailView` sin tocar vistas, servicios, plantillas ni URLs nativas. No activa React en producción.

Archivos:

- `src/backends/vat/VAT/web_api_comision_detalle.py` (rutas `comisiones-detalle/<pk>/` y
  `comisiones-detalle/cursos/<pk>/` en `web_api_urls.py`) y `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat_comision_detalle.py`: entradas de vista previa de las dos rutas.
- `src/frontends/apps/sisoc/src/routes/vatComisionDetalle.tsx` y `vatComisionDetalleStyles.ts` (el `<style>` nativo,
  literal), registrado en `routes/index.ts`.
- U4b: `vatComisionDetalleAcciones.tsx` (modales y POST) y `vatComisionDetalleResultados.tsx`.
- Pruebas: `test_web_vat_comision_detalle_v04.py`, `vatComisionDetalle.test.tsx` y `vatComisionDetalleAcciones.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y `VAT.view_comision` (oferta) o `VAT.view_comisioncurso` (curso), como la ruta
  nativa (403). El alcance es el de la vista (`filter_comisiones_queryset_for_user` y el equivalente de curso): una
  comisión fuera de él, o inexistente, da 404.
- La API proyecta el contexto de la vista: datos generales, métricas de la variante de curso, horarios, clases, inscriptos,
  lista de espera, los permisos que la plantilla evalúa (`puede_*`) y los enlaces. Fechas, horas y números salen del
  motor de plantillas de Django.
- Las solapas (Información, Inscriptos, Lista de espera, Clases, Horarios), el hash de la URL, la ocultación de las
  tarjetas globales, el buscador de inscriptos y la paginación local de 10 filas son los del script de la página.
- Variante de oferta: no define métricas, clases dictadas ni pendientes, por lo que esos valores salen vacíos, como en la
  plantilla nativa.
- U4b: aceptar y rechazar desde la lista de espera y en lote, la alta rápida de inscripto (búsqueda por documento o alta de
  ciudadano) y la pestaña «Resultados» (acta, profesor, calificaciones, alta de profesor) corren las vistas nativas:
  `POST .../comisiones-detalle/cursos/<pk>/resultados/`, `GET .../profesores/buscar/` y `POST .../profesores/nuevo/`
  (permiso `VAT.change_inscripcion`, 404 fuera de alcance) y los endpoints de U3 y `ciudadanos/buscar/`.
  Los modales viven en su posición nativa con trampa de Tab; tras un POST con redirección la página se recarga en la solapa.
- Las acciones que todavía no migran enlazan a su pantalla nativa (eliminar la comisión, agregar, editar y borrar un
  horario, borrar una inscripción) y las descargas de nómina siguen siendo las nativas. Las descargas de nómina siguen
  siendo las nativas.

## Verificación

- Backend (imagen fijada, sin red): pruebas nuevas (incluida la comparación de los textos proyectados con los de la
  página nativa), pruebas de VAT, `test_web_gate`, `test_backend_proxy` y `test_servicios_backends`; `black`, `pylint` y
  `makemigrations --check`.
- Frontend: `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo y comparación visual nativo contra React (detalle, inscriptos, búsqueda, lista de espera,
  clases, horarios, comisión vacía y variante de oferta; escritorio y móvil).

## Limitaciones

Eliminar la comisión, alta, edición y baja de horarios y baja de inscripción son pantallas nativas (U5).
