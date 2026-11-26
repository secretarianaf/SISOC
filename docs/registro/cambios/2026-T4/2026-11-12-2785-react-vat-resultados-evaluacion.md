# Cambio: resultados de evaluación de VAT en React sobre G1 v1 (#2785, V08.01 y V08.02)

## Alcance

Entrega de los resultados de evaluación del [contrato V01/V08](../../../plans/2026-T4/2026-11-12-2785-vat-v01-v08-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): lista
(`/vat/resultados-evaluacion/`), detalle (`<pk>/`), alta (`nuevo/`), edición (`<pk>/editar/`) y baja
(`<pk>/eliminar/`). Lee y escribe por las vistas nativas `ResultadoEvaluacion{List,Detail,Create,Update,Delete}View`,
sin tocar vistas, formularios, modelos, plantillas ni URLs nativas. No activa React en producción.

Archivos:

- `src/backends/vat/VAT/web_api_resultados.py` (rutas en `web_api_urls.py`); `campo_formulario` de
  `web_api_common.py` acepta campos sin `choices` propias (el `NullBooleanField` con `Select`) y entrega `""` por
  la opción vacía; `url_registry.json` regenerado y `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat.py`: entradas de la vista previa local.
- `src/frontends/apps/sisoc/src/routes/vatResultados.tsx` (lista y detalle), `vatResultadosForm.tsx` (formulario y
  baja) y `vatFormShared.tsx` (campo, POST y confirmación de baja que ahora comparten también las evaluaciones),
  registrados en `routes/index.ts`.
- Pruebas: `test_web_vat_resultados_v08.py`, `test_web_preview_vat_v01_v08.py` (ampliado) y `vatResultados.test.tsx`.

## Comportamiento

- La lista filtra como la vista nativa (`evaluacion_id`, `inscripcion_id`, `calificacion`, `busqueda` o `q`), 20 por
  página y 404 con `page` inválida. Calificación y fechas salen con el formato localizado (`7,50`, `d/m/Y`); la
  calificación vacía o cero se muestra `—`, como el template. Editar y Eliminar aparecen según
  `change/delete_resultadoevaluacion`.
- El `POST` de alta y edición valida con `ResultadoEvaluacionForm` y persiste con su `form_valid`: fija
  `registrado_por` en el usuario que escribe y encola «Resultado de evaluación creado exitosamente.» o
  «Resultado de evaluación actualizado exitosamente.». Formulario inválido, incluida la pareja evaluación e
  inscripción repetida: 400 con el formulario ligado y nada se guarda.
- La baja es lógica (`SoftDeleteDeleteViewMixin`): la fila queda en `all_objects` y se encola «Baja lógica
  realizada correctamente.». Un segundo POST da 404.
- Acceso: sesión (401), compuerta G1, luego el permiso de cada ruta (403) y CSRF en el POST; no hay alcance por CFP.
- Quirk nativo conservado: el detalle imprime `{{ resultado }}`, que muestra la calificación sin localizar
  (`9.00`), y el selector de inscripción lista todas las inscripciones.

## Verificación

- Backend (imagen fijada, sin red): pruebas nuevas, `vat` web, `test_web_gate`, `test_backend_proxy` y
  `test_servicios_backends` en verde; las nuevas comparan escritor nativo y API (misma fila), permisos, CSRF y rechazo
  sin guardar. `black`, `pylint` y `makemigrations --check` sin cambios.
- Frontend: `vitest --project sisoc`, `tsc`, `eslint` y build en verde.
- G1 de extremo a extremo (núcleo y runtime): 401, 403, requisito pendiente, constancia falsificada, CSRF, lectura,
  400 del formulario inválido y edición persistida, en verde.
- Comparación visual nativo contra React (lista, vacía, solo lectura, detalle, detalle pendiente, alta, edición,
  rechazo con error y baja; escritorio y móvil) y guardas: sin diferencias.
- No cubierto: el POST real no se ejercitó en navegador; lo cubren las pruebas de API y de React.
