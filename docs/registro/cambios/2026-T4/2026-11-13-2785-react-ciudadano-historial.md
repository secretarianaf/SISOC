# Cambio: historial de auditoría de una instancia en React (#2785, C05)

## Qué cambia

- **API.** `GET /api/web/auditoria/<app_label>/<model_name>/<object_pk>/`
  (`audittrail/web_historial.py`, montada en el core con `audittrail/web_api_urls.py`) corre
  `AuditLogInstanceView` con su `dispatch`: login y `auditlog.view_logentry` (403) y, si
  la página pedida no existe, 404. Proyecta el contexto de `log_list.html` en modo
  instancia: los diez campos del filtro con etiqueta, ayuda, atributos y valor (los dos
  ocultos, `model` y `object_pk`, con el valor que el formulario nativo les da), los
  filtros activos, los errores del formulario, las filas ya formateadas (fecha local
  `Y-m-d H:i`, actor, evento, lote, los dos primeros cambios con «No cargado» marcado
  aparte y el contador «+ N más»), el enlace «Ver» con `?next=` hacia el listado
  nativo y la paginación. Es de solo lectura. La exportación CSV/JSON no pasa por la
  API: la API ignora `?export=` y los botones siguen siendo el `GET` nativo de la página.
- **React.** `routes/ciudadanoHistorial.tsx` (`/auditoria/<app>/<model>/<pk>/`) dibuja la
  tarjeta de filtros (formulario `GET` sin script, como en Django), el resumen de filtros
  activos, la tabla de eventos y el pie de paginación con los mismos enlaces. «Ver»
  lleva al detalle nativo del evento, que no cambia.
- La entrada local `audittrail/web_preview.py` mantiene la URL nativa con sus guardas
  (login, permiso, 404 de página) y devuelve el índice React; con `?export=csv|json`
  responde la vista nativa. Los activos los sirve la entrada de `ciudadanos`. Se agregó la
  ruta a `_OWNED_PATTERNS` y a `url_registry.json`.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): proyección completa, filtros y errores del
  formulario, exportación ignorada por la API, botones según permiso de exportar, página
  fuera de rango (404), instancia sin eventos (lista vacía), 401, 403, 405 y que mirar el
  historial no escribe nada; y la entrada de vista previa con la exportación nativa.
- Vitest, tsc y eslint sin avisos.
- G1 y visual S13 contra la página nativa, escritorio y móvil (ver el informe).

## Limitaciones y diferencias conocidas

- El detalle del evento (`/auditoria/evento/<id>/`) y el listado global (`/auditoria/`)
  siguen en Django.
- El chip de filtro activo de «Evento» muestra el código (`0`, `1`, `2`), igual que la
  página nativa (su búsqueda de la etiqueta no coincide con el valor ya convertido).
- El historial sirve a cualquier modelo auditado de la URL; solo el de ciudadanos tiene
  enlace desde una pantalla React.
