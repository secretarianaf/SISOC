# Cambio: relevamientos inexistentes, dispositivos con relevamientos e imágenes externas en el PDF (#2750, puntos 5 a 7)

## Alcance

Causas sacadas de los tracebacks de PRD
(`/sisoc/SISOC/logs/2026-10-15/error.log`, 16/10 a 21/10):

- **Punto 5.** `/comedores/<id>/relevamiento/<id>` daba
  `Relevamiento.DoesNotExist` y `/comedores/<id>/relevamiento/listar` daba
  `Comedor.DoesNotExist`: eran 500 por ids que no existen. En
  `src/backends/comedores/relevamientos/views/web_views.py` se usa
  `get_object_or_404` en `RelevamientoDetailView.get_object`,
  `RelevamientoListView.get_context_data` y `_opciones_del_popup`.
- **Punto 6.** `/dispositivos/35/eliminar` daba `ProtectedError`: el
  dispositivo tenía relevamientos de datacalle
  (`datacalle.Relevamiento.dispositivo`, `on_delete=PROTECT`). En
  `src/backends/dispositivos/dispositivos/views.py`, `DispositivoDeleteView`
  muestra un mensaje con los registros asociados y vuelve al detalle. La regla de
  qué se puede borrar no cambia.
- **Punto 7.** El log `Failed to load image at 'https://www.appsheet.com/...'`
  no es una falla de AppSheet. Es `RecursosLocalesURLFetcher`
  (`src/backends/comedores/relevamientos/pdf_service.py`), que rechaza a
  propósito las URLs externas para evitar SSRF (#2630). Se mantiene esa
  protección; la decisión de mantenerla fue del usuario en el issue. Además:
  - `tipo_imagen_pdf` clasifica cada imagen como `local`, `externa` o `vacia`
    (AppSheet con `fileName=` vacío);
  - `src/backends/comedores/relevamientos/templates/relevamiento_imagen.html`:
    en el PDF (`es_pdf`), una imagen externa sale como enlace "ver imagen", una
    vacía se omite y una local se sigue embebiendo. En pantalla no cambia nada.

## Comportamiento

- Un relevamiento o comedor inexistente muestra la página 404 en vez de un error.
- Eliminar un dispositivo con relevamientos muestra "No se puede eliminar el
  dispositivo porque tiene registros asociados: …" y no lo borra.
- El PDF de relevamiento que arma SISOC lista las fotos, adjuntos y firma de
  AppSheet como enlaces. No intenta descargarlos, así que no deja errores en el
  log. Las imágenes subidas a SISOC (`MEDIA_URL`) siguen apareciendo en el PDF.
- El PDF oficial de Gestionar no cambia: trae sus imágenes en `data:`.

## Verificación

- `src/backends/comedores/tests/test_relevamiento_pdf_2630.py`:
  `test_tipo_imagen_pdf` con 7 casos; enlace para externas, omisión de vacías y
  sin `src` externo en el PDF; el detalle web sigue mostrando la imagen; 404 de
  detalle y de listado.
- `src/backends/dispositivos/dispositivos/tests/test_dispositivos_views.py`:
  `test_eliminar_dispositivo_con_relevamientos_avisa_en_vez_de_500`.
- Los 4 tests de comportamiento nuevos fallan con el código de `development`.
  El test que ya existía con fotos y firma locales sigue pasando.
- `pytest` de comedores y dispositivos (`-k "relevamiento or dispositivo or pdf"`):
  247 passed. black y djlint sin cambios. pylint 10/10.
