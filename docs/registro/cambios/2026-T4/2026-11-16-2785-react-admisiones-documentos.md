# Cambio: documentación de la admisión (subir, adjuntar y eliminar) en React sobre G1 v1 (#2785, AD02.03)

## Alcance

Subir el archivo de un documento, adjuntar un documento adicional y eliminar un archivo desde el editor
técnico de la admisión, según el
[contrato AD02](../../../plans/2026-T4/2026-10-28-2785-admisiones-informes-documentos-m2.md). No cambia
vistas, servicios ni modelos nativos, ni activa React en producción. La generación de DOCX/PDF y la
descarga siguen en el backend. Las brechas de acceso se conservan, según la
[decisión](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md).

Archivos:

- `src/backends/comedores/admisiones/web_api_documentos.py`, rutas en `web_api_seguimiento_urls.py`
  y `url_registry.json` (regenerado) y `middlewares/admindocs.py`.
- `web_api_editor.py`: `urls.agregar_documento` apunta a la API nueva.
- `src/frontends/apps/sisoc/src/routes/admisionesEditor.tsx` (+ prueba): subir y eliminar por la API.
- Prueba: `test_web_api_documentos_ad02.py`.

## Comportamiento

- `POST .../admisiones/<id>/documentacion/<documentacion_id>/subir/`, `POST .../personalizada/agregar/`
  y `DELETE .../<id>/eliminar/?archivo_id=&preview=` ejecutan las funciones nativas
  `subir_archivo_admision`, `crear_documento_personalizado` y `eliminar_archivo_admision`: vetos del
  abogado, ventana del técnico, estados, `update_or_create`, limpieza de IF/GDE, baja lógica y mensajes
  son los nativos. La respuesta es el JSON nativo sin `html`; React arma la fila con los datos
  (`documento`, `row_id`, `estado_display`, `estado_valor`, `archivo_id`).
- `preview` mantiene la autorización y no elimina nada.
- Acceso igual al nativo (solo sesión iniciada) más el CSRF de sesión de todo POST y DELETE web.

## Verificación

Entorno sintético, sin red. Backend: pruebas de `admisiones`, `web_gate`, `backend_proxy` y
`servicios_backends`, `black`, `pylint` y `makemigrations --check`. Las pruebas nuevas cubren efectos
persistidos (archivo, limpieza de IF, reemplazo de fila, baja) y que un rechazo no cambia datos.
Frontend: Vitest de `sisoc`, `tsc`, ESLint y build. G1 de punta a punta y comparación visual del editor
(lista y modal de eliminar, escritorio y móvil).

## Limitaciones

- Los avisos de error siguen siendo los `alert` del editor (sin texto nuevo).
- Estado de documentos y número GDE siguen en sus URLs nativas (AD03.02).
