# Cambio: alta, edición y baja de ofertas institucionales y cursos de VAT en React sobre G1 v1 (#2785, V05.02, U7)

## Alcance

Unidad U7 del [contrato V02 a V07](../../../plans/2026-T4/2026-11-13-2785-vat-v02-v07-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): alta, edición y baja de ofertas institucionales
(`/vat/ofertas-institucionales/nueva/`, `<pk>/editar/`, `<pk>/eliminar/`) y de cursos (`/vat/cursos/nuevo/?centro=<id>`, `<pk>/editar/`, `<pk>/eliminar/`). Lee y
escribe por `OfertaInstitucional{Create,Update,Delete}View` y `Curso{Create,Update,Delete}View`, sin tocar vistas, servicios, plantillas ni URLs nativas. No activa
React en producción. Se conserva el alcance de cada vista (paridad).

Archivos:

- `src/backends/vat/VAT/web_api_oferta_curso_forms.py` (rutas en `web_api_urls.py`), `url_registry.json` regenerado y `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat_oferta_curso_forms.py`: entradas de vista previa de las seis rutas.
- `src/frontends/apps/sisoc/src/routes/vatOfertaForm.tsx` y `vatCursoForm.tsx`, registrados en `routes/index.ts`; reutilizan `vatTourInline.tsx` y `vatFormShared.tsx`.
- Pruebas: `test_web_vat_oferta_curso_forms_v07.py`, `vatOfertaForm.test.tsx` y `vatCursoForm.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y `VAT.add|change|delete_ofertainstitucional` o `VAT.add|change|delete_curso` (403), 404 si el objeto no existe o queda fuera del
  alcance de la vista nativa, CSRF en los POST (403). El alta de curso conserva la guarda de `dispatch` sobre `?centro=` (403 sin centro editable); React reenvía el
  `?centro=` también en el POST.
- El POST corre `form_valid` nativo: guarda, guarda los vouchers de la oferta (varios valores `voucher_parametrias`) y encola el mensaje («Oferta institucional creada
  exitosamente.», «Oferta institucional actualizada exitosamente.», «Curso creado exitosamente.», «Curso actualizado exitosamente.»). La baja es la baja lógica nativa.
  Con el formulario inválido responde 400 con los campos y errores y no guarda.
- El script de la plantilla de la oferta se reproduce: las columnas de vouchers y costo se muestran solo con «Usa Voucher»; apagarlo (y cargar la página apagado) pone el
  costo en `0` y limpia los vouchers; encendido, descarta los vouchers de otro programa que el elegido. El desplegable abierto no lista los vouchers de otro programa (el
  nativo los deja como filas deshabilitadas).
- Los campos que el rol provincial bloquea en la edición (`centro`, `titulo_referencia`, `programa`, `ciclo_lectivo`) salen `disabled`.
- Curso: la plantilla dibuja cinco campos; «Usa voucher», las parametrías y el costo en créditos van ocultos y bloqueados, así que un valor enviado se ignora; `tipo` no se
  dibuja y guardar lo vacía. La «Guía de carga» cuenta los cuatro campos clave y su acordeón abre un ítem por vez. La variante `?modal=1` (modal del panel de centros) sigue
  siendo la página nativa, con su GET y su POST.
- Defectos nativos conservados: el alta de oferta se titula «Nueva Oferta Materia»; un curso con vouchers no admite inscripción libre (error del modelo).

## Verificación

- Backend (imagen fijada, sin red): efectos persistidos, «sin cambios» ante rechazos, guarda del centro, bloqueos por rol y entradas de vista previa (incluida la variante embebida);
  `black`, `pylint` y `makemigrations --check`.
- Frontend: `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo y comparación visual nativo contra React (formulario, formulario con voucher, formulario con error y baja de oferta y de curso; escritorio y móvil).

## Pendiente

Lista de cursos del centro (`vat_centro_cursos_panel`, equipo de centros).
