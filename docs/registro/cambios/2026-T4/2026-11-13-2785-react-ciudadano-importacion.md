# Cambio: importación masiva de ciudadanos en React (#2785, C01)

## Qué cambia

- **API.** `GET` y `POST /api/web/ciudadanos/importacion-masiva/`,
  `GET .../lotes/<pk>/?page=` y `POST .../lotes/<pk>/reanudar/`
  (`ciudadanos/web_api_importacion.py`, montadas en el core con `web_api_urls.py`) corren las
  vistas nativas con su `dispatch`: permiso `ciudadanos.add_ciudadano` (403, antes que el 404
  de un lote inexistente). El `GET` proyecta lo que imprimen los templates: formulario, los
  10 lotes recientes (fecha local `d/m/Y H:i`), y del lote los contadores, último correcto e
  intentado, error sistémico, `can_resume` y la página de 50 filas. El `POST` multipart crea el
  lote con `form_valid` (mensaje «Lote creado. El worker lo procesara de forma asincronica.»);
  un archivo ausente o que no es `.xlsx` responde 400 con el formulario ligado y no crea nada.
  «Reanudar» corre `request_resume_ciudadanos_import_job`: éxito «Lote marcado para
  reanudacion.» o el rechazo «Solo se pueden reanudar lotes fallidos.».
- **React.** `routes/ciudadanoImportacion.tsx` dibuja `/ciudadanos/importacion-masiva/`
  (formato esperado, campo de archivo, «Descargar plantilla», «Crear lote» e historial) y
  `/ciudadanos/importacion-masiva/lotes/<pk>/` (contadores, errores, filas y paginación). La
  plantilla es el `GET` nativo (`formaction`), «Exportar Excel» y «Actualizar estado» son
  enlaces nativos y las redirecciones son navegaciones de página completa. Se envía una sola
  vez; un rechazo del formulario reinicia el archivo y vuelve arriba como la recarga nativa.
- La entrada local `ciudadanos/web_preview_importacion.py` mantiene la URL nativa con sus
  guardas (login, permiso, 404 del lote) y devuelve el índice React. Se agregó la ruta a
  `_OWNED_PATTERNS` y a `url_registry.json`.
- Nunca se llama a RENAPER ni a otro servicio: la carga solo guarda el archivo y el lote; lo
  procesa el worker fuera de la web.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): proyección completa, carga válida con el efecto
  persistido (lote `pending`, usuario, archivo, ninguna fila ni ciudadano creados) y su
  mensaje, carga inválida sin lote, paginación y página fuera de rango, reanudar un lote
  fallido (estado, contador y mensaje) y uno no fallido (sin cambios), 401, 403 antes que 404,
  404, 405 y CSRF 403 sin ningún cambio, y la entrada de vista previa.
- Vitest, tsc y eslint sin avisos nuevos.
- G1 (core y runtime con gunicorn) y visual S13 contra la página nativa, escritorio y móvil.

## Limitaciones y diferencias conocidas

- Un Excel sin filas con datos levanta `ValidationError` en la vista nativa (error 500 allá);
  la API conserva ese comportamiento y no lo cambia.
- El detalle de cada ciudadano, la plantilla y el Excel de resultados siguen en Django.
