# Cambio: actividades de un espacio en React sobre G1 v1 (#2785, CO03.02)

## Alcance

Segunda entrega de la lane K6 del contrato
[`2026-10-28-2785-comedores-colaboradores-actividades-catalogos.md`](../../../plans/2026-T4/2026-10-28-2785-comedores-colaboradores-actividades-catalogos.md):
alta y edición de las actividades de un espacio PNUD
(`/comedores/<id>/actividades/crear/` y
`/comedores/<id>/actividades/<actividad>/editar/`). Sigue a los
[colaboradores](2026-11-13-2785-react-comedor-colaboradores.md). No activa React
en producción y no cambia ninguna vista, formulario, servicio, modelo,
plantilla, ruta ni permiso nativo.

Varios horarios son varios registros: la pantalla manda los campos repetidos
`schedule_dia_actividad`, `schedule_hora_inicio` y `schedule_hora_fin` que lee
el formulario nativo y no convierte la entidad persistida en un arreglo. No hay
baja web en estas rutas.

Archivos:

- `src/backends/comedores/comedores/web_api_actividades_espacio.py` y
  `web_api_actividades_espacio_urls.py`: API web.
- `src/backends/comedores/comedores/web_preview_actividades_espacio.py`: dos
  entradas de la vista previa local.
- `src/backends/comedores/comedores_runtime/web_api_urls.py`,
  `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/comedorActividades.tsx` y su prueba;
  `comedorColaboradores.tsx` exporta los bloques compartidos (alertas, errores
  de `crispy`, toasts).
- Pruebas: `src/backends/comedores/comedores/tests/test_web_actividades_espacio_k6.py`
  y `test_web_preview_actividades_espacio_k6.py`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET/POST /api/web/comedores/actividades-espacio/comedor/<pk>/crear/` | Formulario con categoría, actividad, vigencia, filas de día y horario y responsable. POST: crea un registro por horario distinto, en una transacción |
| `GET/POST /api/web/comedores/actividades-espacio/comedor/<pk>/<pk2>/editar/` | Actualiza la actividad con el primer horario y crea una más por cada horario adicional; solo actividades del comedor |

Cada endpoint ejecuta el `dispatch` de la vista nativa
(`comedores/views/actividad_espacio_pwa.py`): comedor del alcance, regla «solo
comedores PNUD» (404 si no), `ActividadEspacioPWAWebForm` (catálogo activo o la
selección histórica, categorías derivadas del catálogo, día por id, vigencia
presente mayor o igual a 1, al menos un horario, `HH:MM` con fin posterior,
horarios idénticos deduplicados, cruces internos y con la misma actividad ya
existente del comedor) y el servicio PWA compartido (actor, actualizador y
auditoría). Una redirección nativa se devuelve como `{"ok": true, "redirect":
...}` (vuelve a `#legajo-actividades-pnud` de la ficha) y un rechazo como 400
con los valores, las filas con su error y los mensajes; un rechazo no escribe
nada. Solo se aceptan POST `application/x-www-form-urlencoded` o
`multipart/form-data` (otro formato responde 415) y las escrituras exigen CSRF.

Acceso, en este orden: G1, el permiso de la URL nativa (`auth.role_admin` o
`pwa.manage_colaboradores_pwa`) y el alcance y la regla PNUD de la vista nativa.
Sin cambios respecto de hoy.

Mensajes nativos conservados: «Actividad creada correctamente.», «Se crearon N
horarios de actividad correctamente.», «Actividad actualizada correctamente.» y
«Actividad actualizada y horarios adicionales creados correctamente.».

Pantalla React: mismo marcado que `actividad_espacio_pwa_form.html`. Hace lo que
el script de la plantilla: filtra las actividades por categoría (y vacía la
elección al cambiar de categoría), deshabilita la actividad sin categoría, agrega
filas de horario y quita filas dejando siempre una. Como la plantilla, el
formulario es `novalidate` y los mensajes se ven como alertas y como toast.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 12 pruebas de la API y 2 de la vista previa (acceso, regla PNUD y
  alcance, CSRF y 415, un horario y varios horarios, deduplicado, todas las
  causas de rechazo sin escritura, errores por fila, edición con horarios
  adicionales, selección histórica del catálogo, actividad de otro comedor).
- Frontend: 9 pruebas de la ruta, Vitest del workspace, `tsc`, ESLint y build.
- Visual (regla S13), nativo contra React, 5 estados (alta, alta con filas
  agregadas y quitadas, alta inválida, edición, edición con actividad de
  catálogo retirada) en 1440x900 y 390x844, y las guardas.
- G1 de punta a punta en dos contenedores gunicorn.

## Limitaciones

- El selector de actividad depende del script de la plantilla; en React se
  reproduce, no se reutiliza.
- La baja de actividades y el listado de la ficha siguen en la ficha del comedor.
