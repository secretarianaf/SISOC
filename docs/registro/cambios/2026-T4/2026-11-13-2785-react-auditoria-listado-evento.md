# Cambio: listado global y detalle de evento de auditoría en React (#2785, lane A)

## Qué cambia

- **API de lista.** `GET /api/web/auditoria/listado/` (`audittrail/web_auditoria.py`) corre
  `AuditLogListView` con su `dispatch`: login y `auditlog.view_logentry` (403) y, si la página pedida
  no existe, 404. Reusa la proyección del historial de instancia (campos del filtro, filtros
  activos, errores, filas, paginación de 25) con los diez campos visibles (el modo global no oculta
  `model` ni `object_pk`) y agrega por fila el modelo (`app.modelo`) y la instancia (`#pk`). «Ver»
  lleva `?next=` con la ruta del listado y sus filtros. La exportación CSV/JSON no pasa por la API:
  `?export=` se ignora y los botones siguen siendo el `GET` nativo.
- **API de detalle.** `GET /api/web/auditoria/evento/<id>/` corre `AuditLogDetailView`: fecha con
  segundos, actor (y secundario), modelo, instancia, evento, la marca «Sin diffs», aviso de acción
  masiva o proceso con correlación, origen, batch key, IP y la tabla de cambios. Los valores de más
  de 180 caracteres sin etiquetas llevan el resumen que la plantilla pone en `<summary>`. El `next`
  lo valida la vista nativa; la API lo devuelve como ruta interna (`volver_url`).
- **React.** `routes/ciudadanoHistorial.tsx` suma `auditoriaListadoRoute` (`/auditoria/`: columnas
  Modelo e Instancia, sin columna Cambios, vacío con `colspan` 6) y `routes/auditoriaEvento.tsx`
  (`/auditoria/evento/<id>/`). Ambas se registran en `routes/index.ts`.
- La entrada local `audittrail/web_preview.py` mantiene las guardas nativas (login, permiso, 404) de
  las dos URL y devuelve el índice React; con `?export=` el listado responde la vista nativa. Se
  amplió `_OWNED_PATTERNS` y se regeneró `url_registry.json`.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): proyección de lista y detalle, filtros y errores,
  ruta de vuelta, `next` externo descartado, exportación ignorada por la API, página fuera de rango
  y evento inexistente (404), 401, 403, 405, solo lectura y la entrada de vista previa.
- Vitest completo, tsc y eslint sin errores; build de vite.
- G1 (401, 403, CSRF, cabecera falsificada, camino feliz) y visual S13 contra la página nativa en
  escritorio y móvil (listado, filtrado, error de formulario, detalle y detalle sin diffs): 0 % de
  diferencia.

## Limitaciones y diferencias conocidas

- El resumen de más de 180 caracteres casi no se alcanza: el resolutor nativo ya acorta los textos
  largos; la regla se conserva y se prueba directamente.
- El chip de filtro «Evento» muestra el código, igual que la página nativa.
- La exportación y el acceso (`auditlog.view_logentry`, `audittrail.export_auditlog`) no cambian.
