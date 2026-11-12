# Cambio: pantalla React del editor del informe técnico (#2785, AD02.01, U3b)

## Alcance

Alta y edición del informe técnico (`comedores/admision/informe_tecnico/<tipo>/<admision_id>/crear/` y
`.../<pk>/editar/`), según el
[contrato AD02](../../../plans/2026-T4/2026-10-28-2785-admisiones-informes-documentos-m2.md). Usa el esquema
efectivo y el guardado por API de las entregas anteriores; no cambia formularios, servicios ni vistas
nativos ni activa React en producción. Las brechas de acceso se conservan según la
[decisión](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md). Nada del editor queda nativo:
secciones colapsables, selectores geográficos y aviso de cambios sin guardar se replican en React.

Archivos: `src/frontends/apps/sisoc/src/routes/admisionesInformeEditor.tsx` (+ prueba) y su registro en
`routes/index.ts`; `src/backends/comedores/admisiones/web_preview_informes.py` (entradas locales de las
rutas `crear` y `editar`, el POST sigue nativo); `web_api_informe_formulario.py` (el esquema suma `id`,
`attrs`, `widget`, `estado_formulario` y `urls`); pruebas `test_web_preview_informe_editor_ad02.py` y
`test_web_api_informe_formulario_ad02.py`.

## Comportamiento

- Mismo marcado y orden que `partials/informe_tecnico_campos.html`: secciones `card` con `collapse`
  (chevron), campos como `as_crispy_field` (etiqueta, asterisco, `is-invalid`, `invalid-feedback`), tablas
  de solicitudes y prestaciones con el widget crudo, y las secciones de renovación y antecedentes solo
  cuando el formulario nativo expone esos campos. Un campo ausente no dibuja control.
- Secciones (`informeTecnicoSecciones.js`): abren las que traen errores o campos a subsanar; pulsar
  Guardar Borrador o Finalizar abre todas antes de validar; marcan con borde rojo los campos a subsanar.
- Geografía (`geografiaProvinciaLocalidad.js`): carga las localidades de la provincia elegida desde
  `ajax_load_localidades` y las recarga al cambiarla.
- Cambios sin guardar (`informeTecnicoCambiosSinGuardar.js`): solo cuenta un cambio hecho por el usuario;
  un enlace externo abre el modal (Seguir editando, Salir sin guardar, Guardar borrador) y cerrar o recargar
  usa el aviso del navegador.
- Guardar usa `.../guardar/`: 200 navega a la URL de éxito nativa; 400 muestra todos los errores y el
  mensaje nativo; 409 y borrador por error de publicación muestran el mensaje del servicio, sin perder lo
  escrito. «Notificar a referentes del sistema» sigue siendo el POST nativo.

## Verificación

Entorno sintético, sin red. Backend: pruebas de `admisiones`, `web_gate`, `backend_proxy` y
`servicios_backends`, `black`, `pylint`, `makemigrations --check`. Frontend: Vitest completo de `sisoc`,
`tsc`, ESLint y build. Visual (S13) contra el HTML nativo en 1440x900 y 390x844: ver el reporte del lote.

## Limitaciones

- El mensaje flash de «configuración» que la plantilla nativa dibuja dentro del formulario se muestra
  como aviso emergente como el resto de los mensajes.
- La generación real del DOCX no se ejercita en las pruebas del editor.
