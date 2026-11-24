# Cambio: horarios de comisión de VAT en React sobre G1 v1 (#2785, V04.02, U5)

## Alcance

Primera entrega de la unidad U5 del [contrato V02 a V07](../../../plans/2026-T4/2026-11-13-2785-vat-v02-v07-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): alta, edición y baja de los horarios de comisión de oferta
(`/vat/comisiones/horarios/nuevo/`, `<pk>/editar/`, `<pk>/eliminar/`) y de curso (`/vat/cursos/comisiones/horarios/...`). Lee y escribe por
`ComisionHorario{Create,Update,Delete}View` y `ComisionCursoHorario{Create,Update,Delete}View`, sin tocar vistas, servicios, plantillas ni URLs
nativas. No activa React en producción. Se conserva el alcance de cada vista (paridad).

Archivos:

- `src/backends/vat/VAT/web_api_comision_horario_forms.py` (rutas en `web_api_urls.py`), `url_registry.json` regenerado y
  `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat_comision_horario_forms.py`: entradas de vista previa de las seis rutas.
- `src/frontends/apps/sisoc/src/routes/vatComisionHorarioForm.tsx`, registrado en `routes/index.ts`. El detalle de comisión (U4) ya enlazaba a
  estas URLs; solo cambia su comentario.
- Pruebas: `test_web_vat_comision_horario_forms_v04.py` y `vatComisionHorarioForm.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y `VAT.add|change|delete_comisionhorario` (403), 404 si el horario no existe o queda fuera del alcance de la
  vista nativa, CSRF en los POST (403).
- El POST corre `form_valid` nativo: guarda, genera o regenera las clases del horario y encola el mensaje («Horario creado. Se generaron N
  sesiones.», «Horario actualizado. N sesiones regeneradas.», «Horario eliminado exitosamente.» en el curso). Con el formulario inválido
  responde 400 con los campos y errores y no guarda.
- Defecto nativo conservado: `horario_form.html` dibuja `form.comision`, que el formulario del curso no tiene. En esa variante el primer
  grupo sale vacío y la página nativa no puede enviar `comision_curso` (el detalle usa un modal). React conserva el grupo vacío y envía
  `comision_curso` como campo oculto para que el enlace del detalle funcione; es la única diferencia de comportamiento.
- La confirmación de baja de un horario de curso imprime «None» como subtítulo (la plantilla lee `horario.comision`), igual que la nativa.

## Verificación

- Backend (imagen fijada, sin red): pruebas nuevas (efectos persistidos, «sin cambios» ante rechazos, comparación con los textos de la página
  nativa y entradas de vista previa), `test_web_gate`, `test_backend_proxy` y `test_servicios_backends`; `black`, `pylint` y `makemigrations --check`.
- Frontend: `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo y comparación visual nativo contra React (formulario, formulario con error y baja; escritorio y móvil).

## Pendiente

Alta, edición y baja de comisiones y el asistente de alta de comisión de curso (resto de U5).
