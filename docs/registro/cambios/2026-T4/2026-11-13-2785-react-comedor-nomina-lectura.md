# Cambio: lectura, estado y derivación de la nómina de un comedor en React (#2785, CO01)

## Qué cambia

- **API.** `GET /api/web/comedores/comedores/<id>/admision/<admision>/nomina/` y
  `GET /api/web/comedores/comedores/<id>/nomina/` (`src/backends/comedores/comedores/web_api_nomina.py`,
  incluida desde `src/backends/comedores/comedores_runtime/web_api_urls.py`) corren
  `NominaDetailView` y `NominaDirectaDetailView` con su `setup()` y `get_context_data()`: comedor
  y admisión dentro del alcance del usuario (404 si la admisión no es del comedor o la nómina directa
  no aplica al programa), pestaña PNUD, filtro por DNI, página de 100 filas, métricas y rangos de
  edad globales y comedores de destino. Cada texto sale con la expresión de `nomina_detail.html`
  (localización, `default`, `d/m/Y`). Acceso igual que hoy: `comedores.view_nomina`. Es de solo
  lectura y consume los mensajes pendientes como la página nativa.
- **React.** `src/frontends/apps/sisoc/src/routes/comedorNomina.tsx` dibuja el encabezado, las cuatro
  tarjetas de métricas, las pestañas PNUD, la búsqueda por DNI, la tabla, la paginación nativa y el
  encabezado de página con provincia y municipio. «Agregar persona», «Historial de asistencia» y
  «Borrar» (con su confirmación) siguen siendo enlaces nativos.
- **Estado y derivación.** `POST /api/web/comedores/comedores/nomina/<id>/cambiar-estado/` y
  `POST .../nomina/<id>/derivar/` (`web_api_nomina_acciones.py`) llaman sin cambios a
  `nomina_cambiar_estado` y `nomina_derivar` (alcance, validación, servicio de dominio, códigos 200/400/404/405
  y mensajes nativos). Delante solo agregan la puerta G1, el permiso de la URL nativa
  (`change_nomina`; `change_nomina` y `add_nomina` para derivar) y CSRF. React hace un POST por acción y
  nunca reintenta: el estado recarga o avisa con los mismos `alert`, la derivación muestra el resultado en el
  aviso del modal.
- `src/backends/comedores/comedores/web_preview_nomina.py` mantiene las dos URLs nativas con sus guardas
  y devuelve el índice React. Se agregó la ruta a `_OWNED_PATTERNS` y a `url_registry.json`.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): proyección de modo directo y por admisión (métricas, filas,
  enlaces, fecha local), filtro por DNI con métricas globales, pestañas PNUD, páginas de 100, destinos de
  derivación, 401/403/404 (admisión ajena incluida), cambio de estado y derivación con efectos persistidos
  (origen en Baja, destino en Espera, historial con actor y motivo recortado) y cada rechazo sin escribir,
  permisos y CSRF, y entrada de vista previa; pruebas del core (puerta web, proxy, servicios).
- Vitest, tsc, eslint y build sin avisos. G1 y visual S13 contra la página nativa (lista por admisión
  con y sin permiso de ver ciudadano, directa, vacía, PNUD, búsqueda y página 2; escritorio y móvil).

## Limitaciones y diferencias conocidas

- La baja (pantalla de confirmación) y el alta siguen siendo páginas nativas enlazadas; no hay importación en
  esta pantalla. La ruta React solo existe en la vista previa.
- «Editar» es un enlace `#` también en la página nativa (su manejador está comentado en
  `nomina_detail.js`): se conserva.
- Las fechas de ejecución del encabezado siempre muestran «-» porque la vista nativa no las provee.
- Una página no numérica falla igual que la nativa (`int()` sin saneamiento).
- **Diferencia real con la página nativa.** En `nomina_detail.html` el botón «Confirmar derivación» no hace nada:
  `nomina_derivar.js` se ejecuta en `{% block customJS %}`, antes de que `{% block modals %}` dibuje el modal,
  así que no encuentra el botón y no registra su manejador (verificado en el navegador: el aviso sigue oculto).
  La versión React sí deriva, con el mismo servicio y mensajes; es una mejora deliberada sobre un defecto
  existente, no una copia.
