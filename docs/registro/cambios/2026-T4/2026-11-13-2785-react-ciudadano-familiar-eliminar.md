# Cambio: desvincular un familiar en React (#2785, C03.02)

## Qué cambia

- **API.** `GET` y `POST /api/web/ciudadanos/familiares/<pk>/eliminar/`
  (`ciudadanos/web_api_familiar_eliminar.py`, montada en el core) corren
  `GrupoFamiliarDeleteView` con su `dispatch`: permiso `ciudadanos.change_ciudadano` (403, también
  para un id inexistente) y después el 404 de la relación (la ya dada de baja también). El `GET`
  proyecta la confirmación de `components/delete_confirm.html`: nombre en mayúsculas, la vista
  previa de la baja lógica en cascada (la misma proyección de la baja de ciudadano) y el enlace de
  cancelar. El `POST` corre el `post()` nativo: baja lógica de la relación con el usuario como
  actor, «Relación familiar eliminada.» en cola y redirección a `next` (ruta interna) o a la ficha
  del ciudadano 1, como `{"ok": true, "redirect": ...}`. El `next` viaja en la query de ambas
  llamadas, como en la página nativa.
- **React.** `routes/ciudadanoFamiliarEliminar.tsx` (`/ciudadanos/familiares/<pk>/eliminar`) reutiliza
  `BajaContent` de `ciudadanoBaja.tsx` (ahora con el `endpoint` del `POST` como parámetro opcional:
  la baja de ciudadano no cambia). Envía una sola vez; un rechazo o un resultado no confirmado se
  informan sin reenviar.
- La entrada local `ciudadanos/web_preview_familiar_eliminar.py` mantiene la URL nativa con sus
  guardas (login, permiso, 404) y devuelve el índice React. Se agregó la ruta a `_OWNED_PATTERNS`
  y a `url_registry.json`.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): confirmación, baja con el efecto persistido (solo la
  relación, con `deleted_at` y `deleted_by`; los dos ciudadanos siguen), `next` interno y externo,
  401, 403 antes que 404, 404, 405 y CSRF 403 sin cambios, y la entrada de vista previa.
- Vitest, tsc y eslint sin avisos nuevos.
- G1 (core y runtime con gunicorn) y visual S13 contra la página nativa, escritorio y móvil.

## Limitaciones y diferencias conocidas

- La página nativa imprime el `next` de la query tal cual en «Cancelar»; la API solo acepta rutas
  internas y, si no, vuelve a la ficha (endurecimiento deliberado; no cambia el uso normal).
- La ficha nativa no enlaza esta página: se llega por la URL, igual que hoy.
