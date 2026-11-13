# Cambio: editor técnico de admisión en React sobre G1 v1 (#2785, AD03.02, entrega U1a)

## Alcance

Página `comedores/admisiones/tecnicos/editar/<pk>` (`admisiones_tecnicos_form.html`), según el
[contrato AD03](../../../plans/2026-T4/2026-11-10-2785-admisiones-circuito-tecnico-legal-ad03-m2.md).
No cambia vistas, servicios ni modelos nativos, ni activa React en producción. Las brechas de acceso
se conservan tal cual, según la
[decisión](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md).

Archivos:

- `src/backends/comedores/admisiones/web_api_editor.py` (rutas en `web_api_seguimiento_urls.py`).
- `src/backends/comedores/admisiones/web_preview_seguimiento.py`: entrada local del GET nativo.
- `src/backends/config/url_registry.json` (regenerado) y `middlewares/admindocs.py`.
- `src/frontends/apps/sisoc/src/routes/admisionesEditor.tsx` (con su prueba), `admisionesSeguimiento.tsx`
  (ruta y encabezado sin cast) y `admisionesInformeEditor.tsx` (exporta `Crispy`, `ExpedienteGrid` y el editor con modo embebido).
- Pruebas: `test_web_api_editor_ad03.py` y `admisionesEditor.test.tsx`.

## Comportamiento

- `GET /api/web/comedores/admisiones/<pk>/` ejecuta `AdmisionesTecnicosUpdateView` (`setup`,
  `get_object`, `get_context_data`) y devuelve los datos que usa el template: botones, resincronización,
  selección de convenio, tarjetas de admisión y comedor, validaciones de templates, estadísticas y filas
  de documentos con el control que corresponde al usuario. La admisión se resuelve por clave global (404
  si no existe). El acceso es el nativo: sesión web y alguno de `comedores.view_comedor`,
  `admisiones.view_admision` o `acompanamientos.view_informacionrelevante`.
- `POST /api/web/comedores/admisiones/<pk>/acciones/<accion>/` (`derivar-legales`, `if-informe-tecnico`,
  `comenzar-acompanamiento`, `rectificar-documentacion`, `finalizar-carga-documentacion`, `caratular`,
  `confirmar-tipo-convenio`, `validaciones-template`, `subir-docx-final`) arma el POST con el cuerpo
  (JSON o multipart) más la clave del botón y corre el despacho nativo de la vista. Los servicios,
  validaciones y mensajes son los nativos; los mensajes se devuelven en `messages`. Respuestas: 200
  `{success, message, level, messages, redirect}`; 400 con el mismo cuerpo y `success: false` cuando la
  vista respondió con un mensaje de error (con `fields` y `non_field_errors` si re-renderizó la carátula
  inválida); 403 si la vista respondió 403; 404 para acción o admisión desconocida. La rama genérica de
  `UpdateView.post` (`AdmisionForm` con todos los campos) no se expone.
- Las ediciones en línea (número de convenio, «Vigente PWA», personas conveniadas, número de
  expediente), el estado y el número GDE de los documentos, la carga y baja de archivos y la
  resincronización siguen usando los endpoints nativos que llaman los scripts de la página; React replica
  sus toasts, alertas y modales y recarga los datos después de cada acción.
- Si el usuario puede editar el informe técnico, la página nativa dibuja el formulario embebido de
  informe y carátula. `GET` lo devuelve en `informe_embebido` (campos efectivos del formulario nativo,
  antecedentes, publicación de template y la carátula con sus cuatro partes, con los nombres con prefijo
  que el navegador enviaría). `POST .../acciones/informe-caratula/` (`{action: draft|submit, values}`)
  corre `_handle_informe_tecnico_post`: informe y carátula se guardan juntos en una transacción, con las
  mismas validaciones y mensajes. Un formulario inválido responde 400 con `fields`, `caratula_fields` y
  `messages`, y no persiste nada. La sección reutiliza el editor de informe de AD02
  (`admisionesInformeEditor.tsx`, con la carátula, el cartel de cambios sin guardar y los botones del
  template embebido); `ExpedienteGrid` comparte el bloque de número de expediente con el modal de
  «Caratular expediente».

## Verificación

Entorno sintético, sin red: pruebas de la API y del preview, `black`, `pylint`, Vitest de `sisoc`, `tsc`,
ESLint, build, visual (S13, estados clave en escritorio) y G1 sobre el árbol final.

## Limitaciones

- «Notificar a referentes del sistema» (reportar configuración faltante) sigue siendo el POST nativo del
  formulario, como en la página Django.
- La descarga de DOCX/PDF sigue siendo nativa (enlaces a las URLs de media o a la vista de descarga).
- Las brechas de acceso del contrato (resync sin permiso, personas conveniadas sin alcance por objeto,
  acciones sin revalidar rol ni estado de origen) se conservan y se fijan en las pruebas.
