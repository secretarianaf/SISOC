# Cambio: acciones del informe técnico y informe complementario de admisión en React sobre G1 v1 (#2785, AD02.02)

## Alcance

Acciones de la página de detalle `comedores/admision/informe_tecnico/<tipo>/<pk>/ver/` (subir el DOCX
editado y revisar el informe) y la página `comedores/admision/informe_complementario/<tipo>/<pk>/ver/`,
según el [contrato AD02](../../../plans/2026-T4/2026-10-28-2785-admisiones-informes-documentos-m2.md).
No cambia vistas, formularios, servicios ni modelos nativos, ni activa React en producción. La generación
y el almacenamiento de DOCX/PDF siguen en el backend. Las brechas de acceso se conservan tal cual, según la
[decisión](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md).

Archivos:

- `src/backends/comedores/admisiones/web_api_informe_acciones.py`: `docx-editado/` y `revision/`.
- `src/backends/comedores/admisiones/web_api_informe_complementario.py`: GET y POST del complementario.
- `src/backends/comedores/admisiones/web_preview_informe_complementario.py`: entrada local del GET nativo.
- `web_api_informes_urls.py` (rutas), `src/backends/config/url_registry.json` (regenerado) y
  `middlewares/admindocs.py`.
- `src/frontends/apps/sisoc/src/routes/admisionesInformeDetalle.tsx` (acciones por la API) y
  `admisionesInformeComplementario.tsx` (página nueva), con sus pruebas y el registro en `routes/index.ts`.
- Pruebas: `test_web_api_informe_acciones_ad02.py`.

## Comportamiento

- `POST .../informes/<tipo>/<pk>/docx-editado/` (multipart `docx_editado`) ejecuta
  `_handle_subir_docx_editado_post` de `InformeTecnicoDetailView`; `POST .../revision/` (JSON `estado`,
  `observacion`, `campos_a_subsanar`) ejecuta `InformeService.procesar_revision_informe`. Los roles, el
  estado exigido («Docx generado»), los servicios y los mensajes son los nativos; un estado de revisión
  distinto de «A subsanar» o «Validado» no actúa, como hoy.
- `GET .../informes/complementario/<tipo>/<pk>/` ejecuta `InformeTecnicoComplementarioDetailView`
  (`?origen=acompanamiento` incluido) y `POST` ejecuta su `post()` con `{"values": {<campo>: <valor>}}`
  como claves `campo_<nombre>`: los valores vacíos se ignoran, un envío sin cambios se rechaza con el
  mensaje nativo y nada se guarda, y el éxito guarda los campos, pasa el complementario a
  `enviado_validacion` y actualiza el estado de legales.
- Respuesta de las acciones: 200 `{success: true, messages, redirect}`; 400 con `success: false` cuando la
  vista nativa respondió con un mensaje de error (sin cambios persistidos); 403 cuando respondió 403; 404
  para un informe inexistente. Los mensajes se devuelven y se vuelven a encolar, así que la página a la
  que React redirige los muestra una vez, como el redirect nativo.
- Acceso igual al nativo (guarda de URL con alguno de `comedores.view_comedor`, `admisiones.view_admision`
  o `acompanamientos.view_informacionrelevante`) más el CSRF de sesión de todo POST web.

## Verificación

Entorno sintético, sin red. Backend: pruebas de `admisiones`, `web_gate`, `backend_proxy` y
`servicios_backends`, `black`, `pylint` y `makemigrations --check`; las pruebas nuevas cubren efectos
persistidos y que un rechazo no cambia datos (archivo y estado, campos a subsanar y observaciones,
complementario y estado de legales). Frontend: Vitest de `sisoc` completo, `tsc`, ESLint y build.
G1 de punta a punta y tabla visual S13 de los estados clave: ver el reporte de la entrega.

## Limitaciones

- Un 403 de las acciones (usuario sin rol técnico de la dupla) muestra la pantalla de acceso compartida, como
  las demás pantallas migradas; la página nativa respondía un 403 vacío. Otro fallo del servidor muestra la
  pantalla de error existente. No se agrega texto nuevo.
- Documentación (subir, reemplazar, eliminar, filas personalizadas) y descargas de DOCX quedan para AD02.03.
