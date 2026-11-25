# Cambio: baja de nómina de comedores en React (#2785, CO01)

## Qué cambia

- **URLs canónicas.** Las confirmaciones «Dar de baja» de la nómina de comedores se
  sirven en React en sus mismas URLs:
  - nómina directa: `/comedores/<pk>/nomina/<pk2>/eliminar/` (`nomina_directa_borrar`);
  - nómina por admisión: `/comedores/<pk>/admision/<admision_pk>/nomina/<pk2>/eliminar/`
    (`nomina_borrar`).

  Las entradas viven en `comedores/web_preview_nomina.py` (clave `comedores` de
  `core/react_activation.py`, que ya estaba registrada). Conservan el decorador nativo
  `permissions_any_required(["comedores.delete_nomina"])` y, antes de devolver el índice
  React, resuelven el registro con la misma búsqueda de la vista nativa (comedor,
  admisión y alcance del usuario): si no corresponde, responde el 404 nativo. Solo el
  `GET` devuelve React; el `POST` llega a `NominaDeleteView` / `NominaDirectaDeleteView`.
- **API.** `GET` y `POST` en
  `/api/web/comedores/comedores/<pk>/nomina/<pk2>/eliminar/` y
  `/api/web/comedores/comedores/<pk>/admision/<admision_pk>/nomina/<pk2>/eliminar/`
  (`comedores/web_api_nomina_baja.py`). Corren las vistas nativas: el `GET` proyecta lo
  que dibuja `comedor/nomina_confirm_delete.html` (nombre en mayúsculas, desglose de la
  baja lógica en cascada, «Dar de baja», «Cancelar» con destino a la nómina
  correspondiente y el breadcrumb de la plantilla); el `POST` ejecuta el `post()` nativo
  (baja lógica con el usuario como actor, mensaje «Registro de nómina dado de baja
  correctamente.» y redirección a la nómina), que se devuelve como
  `{"ok": true, "redirect": ...}`. Mismo permiso, mismo alcance y CSRF.
- **React.** `routes/comedorNominaBaja.tsx` (ruta `comedor-nomina-baja`) reutiliza la
  confirmación compartida de `comedorIntervencionesBaja.tsx`: envía una sola vez, no
  reintenta, informa el rechazo del servidor o un resultado no confirmado y navega con
  página completa a la redirección nativa.
- `admindocs.py` suma las dos rutas de API a `_OWNED_PATTERNS` y `url_registry.json`
  suma `comedores_web_nomina_baja_admision` y `comedores_web_nomina_baja_directa`
  (generado con `generar_registro_urls`).
- El botón «Borrar» del listado de nómina ya apuntaba a esas URLs: no cambia. Con React
  apagado (`REACT_VERTICALES_ACTIVAS` sin `comedores`) las páginas siguen siendo las
  nativas.

## Cómo se verificó

- Pytest (SQLite): proyección de ambas confirmaciones, baja con efecto persistido
  (`deleted_at`, `deleted_by`) y mensaje en la nómina, rechazos sin escritura (anónimo,
  sin permiso, fuera de alcance, registro de otro comedor o admisión, CSRF), HEAD de
  staff sin metadatos de admindocs, entradas canónicas (React tras guarda y alcance,
  denegaciones nativas sin datos, `POST` nativo con 302) y páginas nativas sin React.
- Vitest: rutas, render de ambas variantes, envío único con CSRF, rechazo, resultado
  no confirmado sin reintento y error de carga. `tsc` y eslint sin errores.

## Limitaciones

- Sin prueba en navegador real en esta entrega (pedido explícito de avanzar sin ella).
- Se conserva la particularidad nativa del breadcrumb: enlaza la ficha del comedor con
  el id del registro de nómina.
