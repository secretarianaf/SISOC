# Cambio: guardado del informe técnico (borrador y finalizar) sobre G1 v1 (#2785, AD02.01, U3a)

## Alcance

Tercera entrega del editor del informe técnico, según el
[contrato AD02](../../../plans/2026-T4/2026-10-28-2785-admisiones-informes-documentos-m2.md):
guardado por API del alta y la edición, con los efectos del gate 2. No cambia formularios,
servicios ni vistas nativos; la pantalla React del editor es la entrega siguiente (U3b). Las
brechas de acceso se conservan según la
[decisión](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md).

Archivos: `src/backends/comedores/admisiones/web_api_informe_guardar.py`,
`web_api_informe_formulario.py` (se extraen `prepare_native_view` y `fields_payload`),
`web_api_informes_urls.py`, `config/url_registry.json` (regenerado), `config/middlewares/admindocs.py`
y la prueba `test_web_api_informe_guardar_ad02.py`.

## Comportamiento

`POST /api/web/comedores/admisiones/informes/<tipo>/admision/<admision_id>/guardar/` (alta) y
`.../<tipo>/<pk>/guardar/` (edición) con `{"action": "draft"|"submit", "values": {campo: valor}}`.
Corren el circuito nativo sin reglas propias: `get_form` de la vista nativa (`require_full` sigue a
la acción, solo se leen los campos efectivos y se ignoran claves desconocidas), `form.is_valid()` e
`InformeService.guardar_informe`. Un checkbox se envía solo si está marcado (`true`).

- 200 `success`: guardado; `redirect` es la URL de éxito nativa. Borrador: Iniciado/borrador y la
  admisión pasa a `informe_tecnico_en_proceso`. Finalizar: Para revision/finalizado, DOCX generado,
  admisión `informe_tecnico_finalizado`, observaciones y campos a subsanar limpios.
- 200 `success: false` + `saved_as_draft`: falló la publicación de plantilla; el informe queda como
  borrador y la admisión en `informe_tecnico_en_proceso` (comportamiento nativo).
- 400: acción inválida o formulario inválido; no se persiste nada y `fields` devuelve el formulario
  ligado con todos sus errores, más el mensaje nativo «No se pudo guardar el informe. Revisá los
  campos: ...».
- 409: rechazo del servicio, sin datos parciales: documentos obligatorios sin cargar o sin validar,
  informe ya validado, o error al generar el DOCX. El endpoint no agrega transacción propia:
  `InformeService.guardar_informe` es `@transaction.atomic`, así que el error de generación revierte
  todo (sin informe y con la admisión sin cambios), igual que la vista nativa. Una prueba sin la
  transacción envolvente de pytest fija ese estado en ambos lados (API 409; página nativa, formulario
  re-renderizado con 200).
- Acceso igual al nativo y CSRF de sesión en todo POST.

## Verificación

Entorno sintético, sin red. Las pruebas afirman los efectos persistidos exactos (informe, actores,
estados de informe y de admisión, observaciones) y que cada rechazo deja los datos sin cambios.
Se suman `black`, `pylint`, `makemigrations --check` y las suites de `web_gate`, `backend_proxy` y
`servicios_backends`.

## Limitaciones

- Archivos adjuntos y generación real de DOCX no se ejercitan: la generación se simula en las
  pruebas; la conversión sigue siendo del backend.
- Falta la pantalla React del editor (U3b).
