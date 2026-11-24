# Cambio: comisiones de oferta y de curso de VAT en React sobre G1 v1 (#2785, V04.02, U5)

## Alcance

Segunda entrega de la unidad U5 del [contrato V02 a V07](../../../plans/2026-T4/2026-11-13-2785-vat-v02-v07-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): alta, edición y baja de comisiones de oferta
(`/vat/comisiones/nueva/`, `<pk>/editar/`, `<pk>/eliminar/`) y de curso (`/vat/cursos/comisiones/nueva/`, `<pk>/editar/`, `<pk>/eliminar/`). Lee y escribe
por `Comision{Create,Update,Delete}View` y `ComisionCurso{Create,Update,Delete}View`, sin tocar vistas, servicios, plantillas ni URLs nativas. No activa
React en producción. Se conserva el alcance de cada vista (paridad).

Archivos:

- `src/backends/vat/VAT/web_api_comision_forms.py` (rutas en `web_api_urls.py`), `url_registry.json` regenerado y `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat_comision_forms.py`: entradas de vista previa de las seis rutas.
- `src/frontends/apps/sisoc/src/routes/vatComisionForm.tsx` y `vatComisionFormStyles.ts`, registrado en `routes/index.ts`. El detalle de comisión (U4) ya
  enlazaba a estas URLs; solo cambia su comentario.
- Pruebas: `test_web_vat_comision_forms_v04.py` y `vatComisionForm.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y `VAT.add|change|delete_comision` o `VAT.add|change|delete_comisioncurso` (403), 404 si la comisión no existe o queda
  fuera del alcance de la vista nativa, CSRF en los POST (403). El alta de curso conserva la guarda de `dispatch` sobre `?curso=` (403 si el curso no existe o
  no es editable por el usuario).
- El POST corre `form_valid` nativo: guarda y encola el mensaje («Comisión creada exitosamente.», «Comisión actualizada exitosamente.», «Comision del curso
  creada exitosamente.», «Comision del curso actualizada exitosamente.»); si cambian las fechas regenera las clases. La baja es la baja lógica nativa
  («Baja lógica realizada correctamente.»). Con el formulario inválido responde 400 con los campos y errores y no guarda.
- Defectos nativos conservados: la plantilla de la oferta no dibuja `acepta_lista_espera`, así que guardar una edición lo apaga; los widgets de fecha
  imprimen `d/m/Y`, que `<input type="date">` no puede mostrar; la baja de oferta lleva el parámetro `next` del POST (React no lo envía).
- El formulario del curso oculta el cupo de lista de espera si la lista está apagada, le exige el valor al encenderla y lo vacía al apagarla (script nativo).

## Verificación

- Backend (imagen fijada, sin red): pruebas nuevas (efectos persistidos, «sin cambios» ante rechazos, comparación con los textos de la página nativa y
  entradas de vista previa); `black`, `pylint` y `makemigrations --check`.
- Frontend: `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo y comparación visual nativo contra React (formulario, formulario con error y baja; escritorio y móvil).

## Pendiente

Asistente de alta de comisión de curso (tres pasos) y la alta rápida de profesor como pantalla propia (resto de U5).
