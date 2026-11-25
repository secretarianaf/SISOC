# Cambio: segmentación e importación de encuestas en React sobre G1 v1 (#2785, E02)

## Alcance

Primera unidad del [contrato E02 a E04 y D01](../../../plans/2026-T4/2026-11-13-2785-encuestas-dashboard-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): la pantalla `/encuestas/<pk>/segmentacion/` y los
endpoints de sus acciones y de la importación de encuestas. Lee por `EncuestaSegmentacionView` y escribe por las vistas
nativas (`SegmentacionTipoUpdateView`, `SegmentacionAgregarDestinatarioView`, `SegmentacionQuitarDestinatarioView` y
`EncuestaImportarView`), sin tocar vistas, servicios, plantillas ni URLs nativas. No activa React en producción.

Archivos:

- `src/backends/sisoc_core/encuestas/web_transport_encuestas.py` (guardas y conversión de redirects),
  `web_api_segmentacion.py` y `web_api_urls.py`; montaje en `config/urls.py`, `url_registry.json` y
  `config/middlewares/admindocs.py`.
- `src/backends/sisoc_core/encuestas/web_preview_encuestas.py`: entrada de vista previa de la ruta.
- `src/frontends/apps/sisoc/src/routes/encuestasSegmentacion.tsx`, registrado en `routes/index.ts`.
- Pruebas: `test_web_segmentacion_api.py`, `test_web_preview_encuestas.py` y `encuestasSegmentacion.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y `encuestas.change_encuesta` (403; la importación exige `encuestas.add_encuesta`), igual
  que las rutas nativas; CSRF obligatorio en los POST (403) y cuerpo de formulario o multipart (415 si es otro).
- Los mensajes son los de los servicios («Segmentación actualizada correctamente.», «Destinatario agregado
  correctamente.», «Destinatario eliminado correctamente.», el texto de importación y cada `ValidationError`). Un rechazo
  del servicio responde 200 con el mensaje de error y no persiste nada; la pantalla vuelve a leer la página y lo muestra
  como toast, igual que la recarga nativa.
- El formulario envía solo lo que enviaría el nativo: el grupo de grupos y el archivo, deshabilitados según el tipo, no
  viajan; «Disponible en la PWA» viaja con `disponibilidad_pwa_presente=1`.
- Una encuesta pendiente de aprobación redirige a su revisión, en la vista previa (302 nativo) y en la API
  (`{"redirect": ...}`).
- «Importar» no tiene botón en esta unidad: es el de la lista de E04. El endpoint queda probado (alta en borrador con y sin
  segmentación, archivo inválido sin cambios, permiso `add_encuesta`).

## Verificación

- Backend (imagen fijada, sin red): 15 pruebas nuevas de la API y 3 de la vista previa (acceso, lectura, efectos persistidos y
  «sin cambios» ante rechazos), `test_web_gate`, `test_backend_proxy` y `test_servicios_backends`; `black`, `pylint` y
  `makemigrations --check`.
- Frontend: 12 pruebas nuevas, `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo (401, 403, requisito pendiente, cabecera falsificada, CSRF, lectura y cambio de tipo persistido).
- Comparación visual nativo contra React (sin segmentación, por documentos, por grupos, por usuarios y alta rechazada;
  escritorio y móvil): estructura, orden de Tab y diff perceptual 0 %, más las guardas.

## Limitaciones

El cuerpo de una importación o de un archivo de listado de más de 5 MB lo rechaza el servicio nativo (mensaje del servicio).
Un fallo de red muestra «No se pudo completar la operación.» y no reenvía.
