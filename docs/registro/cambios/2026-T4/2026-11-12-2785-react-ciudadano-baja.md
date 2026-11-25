# Cambio: baja de ciudadano en React (#2785, C05.03)

## Qué cambia

- **API.** `GET` y `POST /api/web/ciudadanos/<pk>/baja/`
  (`ciudadanos/web_baja.py`, `CiudadanoBajaWebView`, montada en el core) corren
  `CiudadanosDeleteView` con el orden nativo: permiso `ciudadanos.delete_ciudadano`
  (403, también para un id inexistente) y después el 404. El `GET` proyecta el
  contexto de `components/delete_confirm.html`: nombre en mayúsculas (`upper` de
  Django), enlace de cancelar, totales y desglose de la baja lógica en cascada
  (`cascade_preview`) y los mensajes en cola. El `POST` corre el `post()` nativo:
  baja lógica en cascada con el usuario como actor, mensaje «Ciudadano dado de baja
  correctamente.» en cola y redirección a `/ciudadanos/listar`, que pasa a
  `{"ok": true, "redirect": ...}`.
- **React.** `routes/ciudadanoBaja.tsx` (ruta `/ciudadanos/eliminar/<pk>`) dibuja la
  tarjeta de confirmación, el aviso con los totales (cero no se muestra), la tabla del
  desglose y los botones «Dar de baja» y «Cancelar». Envía una sola vez; un rechazo
  del servidor o un resultado no confirmado se informan sin reenviar y el botón queda
  deshabilitado. La redirección es una navegación de página completa.
- La entrada local `ciudadanos/web_preview.py` suma `ciudadanos/eliminar/<pk>` con
  los mismos guardas nativos (login, permiso, 404) y el índice React. Se agregó la
  ruta a `_OWNED_PATTERNS` de `admindocs.py` y a `url_registry.json`.
- El enlace «Dar de baja» de la ficha ya apuntaba a esa URL: no cambia.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): confirmación, baja con el efecto
  persistido exacto (ciudadano y relación familiar con `deleted_at`, `deleted_by`
  del actor, el resto intacto), 401, 403 sin permiso, 403 antes que 404, 404, 405 y
  CSRF 403 sin ningún cambio en los datos, y la entrada de vista previa.
- Vitest, tsc y eslint sin avisos.
- G1 (core y runtime con gunicorn) y visual S13 contra la página nativa, escritorio
  y móvil (ver el resultado en el informe de la entrega).

## Limitaciones y diferencias conocidas

- La plantilla nativa no define título: el título de página queda vacío como allá.
- «Editar», «Historial» y «Agregar familiar» siguen en Django (C05.02 y la ficha).
