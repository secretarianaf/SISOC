# Cambio: asistente de alta de comisión de curso de VAT en React sobre G1 v1 (#2785, V04.02, U5)

## Alcance

Tercera entrega de la unidad U5 del [contrato V02 a V07](../../../plans/2026-T4/2026-11-13-2785-vat-v02-v07-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): el asistente de tres pasos de `/vat/cursos/<curso_id>/comision/nueva/`
(información básica, horarios y confirmación). Corre el `SessionWizardView` nativo (`ComisionCursoWizardView`) sin tocar vistas, formularios, servicios,
plantillas ni URLs nativas. No activa React en producción. Se conserva el alcance de la vista (paridad).

Archivos:

- `src/backends/vat/VAT/web_api_comision_wizard.py` (ruta en `web_api_urls.py`), `url_registry.json` regenerado y `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat_comision_wizard.py`: entrada de vista previa de la ruta nativa.
- `src/frontends/apps/sisoc/src/routes/vatComisionWizard.tsx` y `vatComisionWizardStyles.ts`, registrado en `routes/index.ts`.
- Pruebas: `test_web_vat_comision_wizard_v04.py` y `vatComisionWizard.test.tsx`.

## Cómo funciona

- Una subclase de la vista nativa reemplaza `render_to_response`: en lugar de la plantilla devuelve el contexto del paso actual en JSON (campos con el nombre
  y el prefijo que envía el navegador, formset de horarios con su formulario vacío, o el resumen de la confirmación). Todo lo demás es el asistente nativo: el
  almacenamiento en sesión, el `ManagementForm` (`<prefijo>-current_step`), `wizard_goto_step`, la validación de cada paso y `done`.
- `GET` reinicia el asistente (como la vista nativa). `POST` valida el paso: inválido responde 400 con los errores y se queda en el paso; válido responde 200
  con el paso siguiente; en el último paso crea la comisión, sus horarios y sus sesiones y responde `{"ok": true, "redirect": <centro>?refresh=1#cursos}`
  con el mensaje nativo «Comisión creada con N horario(s) y M sesión(es).» en cola.
- Acceso: sesión (401), compuerta G1, `VAT.add_comisioncurso` (403) y, además, el alcance del centro del curso que aplica `dispatch` (403 sin alcance, 404 si el
  curso no existe); CSRF en los POST (403).
- React conserva los comportamientos de la plantilla: el cupo de lista de espera se oculta y se vacía si la lista está apagada; los bloques de horario se agregan
  desde la plantilla, el último visible se vacía en lugar de eliminarse y el total semanal se calcula en el cliente; el botón «Volver al paso anterior» descarta
  lo editado en el paso (es el primer botón de envío, así que Enter en el paso 2 también retrocede, como en la página nativa).

## Verificación

- Backend (imagen fijada, sin red): pruebas nuevas (pasos, errores nativos, efectos persistidos, «sin cambios» ante rechazos y entrada de vista previa), `black`,
  `pylint` y `makemigrations --check`.
- Frontend: `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo y comparación visual nativo contra React (los tres pasos y un caso de error; escritorio y móvil).

## Pendiente

La alta rápida de profesor como pantalla propia (resto de U5).
