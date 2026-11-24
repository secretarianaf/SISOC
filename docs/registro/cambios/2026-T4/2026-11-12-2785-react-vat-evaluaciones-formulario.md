# Cambio: alta, edición y baja de evaluaciones de VAT en React sobre G1 v1 (#2785, V08.02)

## Alcance

Segunda entrega de V08 del [contrato V01/V08](../../../plans/2026-T4/2026-11-12-2785-vat-v01-v08-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): el formulario de
`/vat/evaluaciones/nueva/` y `/vat/evaluaciones/<pk>/editar/` y la confirmación de
`/vat/evaluaciones/<pk>/eliminar/`. Escribe por las vistas nativas (`EvaluacionCreateView`,
`EvaluacionUpdateView`, `EvaluacionDeleteView`), sin tocar vistas, formularios, modelos, plantillas ni URLs
nativas. No activa React en producción.

Archivos:

- `src/backends/vat/VAT/web_api_evaluaciones_forms.py` (rutas en `web_api_urls.py`) y los helpers
  `campo_formulario` y `valor_de_campo` de `web_api_common.py`; `url_registry.json` regenerado y
  `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat.py`: entradas de alta, edición y baja.
- `src/frontends/apps/sisoc/src/routes/vatEvaluacionesForm.tsx`, registrado en `routes/index.ts`.
- Pruebas: `test_web_vat_evaluaciones_forms_v08.py`, `test_web_preview_vat_v01_v08.py` (ampliado) y
  `vatEvaluacionesForm.test.tsx`.

## Comportamiento

- `GET .../nueva/` y `.../<pk>/editar/` devuelven los ocho campos del `EvaluacionForm` con tag, atributos del
  widget, valor, opciones y errores; `POST` valida con el formulario nativo y persiste con su `form_valid`
  (mensajes «Evaluación creada exitosamente.» y «Evaluación actualizada exitosamente.», que la lista consume).
  Formulario inválido: 400 con el formulario ligado y nada se guarda.
- `GET .../<pk>/eliminar/` devuelve los datos de la confirmación; `POST` ejecuta la baja física del `DeleteView`
  nativo (sin mensaje, como hoy). Un segundo POST da 404.
- Acceso: sesión (401), compuerta G1, luego `VAT.add_evaluacion`, `VAT.change_evaluacion` o
  `VAT.delete_evaluacion` (403) y CSRF en el POST. Hoy no hay alcance por CFP ni estado que bloquee la edición.
- El campo comisión usa el selector Select2 compartido con el mismo placeholder (`data-placeholder`) y la
  cruz de borrado que el script nativo; el primer error de cada campo se muestra como en el template.
- Quirk nativo conservado: los widgets de fecha y ponderación imprimen el valor localizado de Django, que un
  `<input type="date">` o `number` puede ignorar al editar.

## Verificación

- Backend (imagen fijada, sin red): `vat/tests` completo más `test_web_gate`, `test_backend_proxy` y
  `test_servicios_backends`: 341 pruebas en verde; las nuevas comparan además el escritor nativo con la API
  (misma fila persistida) y cubren permisos, CSRF, rechazo sin guardar y baja física. `black`, `pylint` 10/10 y
  `makemigrations --check` sin cambios.
- Frontend: `vitest --project sisoc` completo (84 archivos, 879 pruebas), `tsc`, `eslint` y build en verde.
- G1 de extremo a extremo sobre el árbol final: 16 comprobaciones en verde (401, 403, requisito pendiente,
  constancia falsificada, CSRF, caminos felices y 403 del formulario sin `add_evaluacion`).
- Comparación visual (alta, edición, rechazo con errores y baja; escritorio y móvil) y guardas: sin diferencias.
  Corregidos durante la entrega: el `<select>` de tipo no es Select2, los estilos de Select2 y los espacios
  entre ícono y texto de la plantilla.
- No cubierto: el envío real (POST) no se ejercitó en navegador; lo cubren las pruebas de API y de React.
