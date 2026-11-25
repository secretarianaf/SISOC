# Cambio: observaciones de comedor en React sobre G1 v1 (#2785, CO06)

## Alcance

Cuarta entrega de la lane K4 del contrato
[`2026-10-28-2785-comedores-intervenciones-observaciones-m2.md`](../../../plans/2026-T4/2026-10-28-2785-comedores-intervenciones-observaciones-m2.md):
alta, ficha, edición y baja de observaciones de un comedor (CO06), con el
mismo componente de baja que las intervenciones. A diferencia de las
intervenciones, las observaciones sí respetan el alcance del usuario. No activa
React en producción y no cambia ninguna vista, ruta ni permiso nativo.

Archivos:

- `src/backends/comedores/comedores/web_api_observaciones.py` y
  `web_api_observaciones_urls.py`: API web.
- `src/backends/comedores/comedores/web_preview_observaciones.py`: cuatro
  entradas de la vista previa local.
- `src/backends/comedores/comedores_runtime/web_api_urls.py`,
  `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/comedorObservaciones.tsx` y su prueba.
- Pruebas: `src/backends/comedores/comedores/tests/test_web_observaciones_comedor_k4.py`
  y `test_web_preview_observaciones_k4.py`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `/api/web/comedores/observaciones/comedor/<comedor_pk>/crear/` | GET: comedor del alcance (404 si no) y campo «Observación». POST: el servidor fija comedor, observador (nombre y apellido) y fecha; vuelve a `next` si es del mismo sitio o a la ficha |
| `GET /api/web/comedores/observaciones/<pk>/` | Ficha: comedor, observador, fecha y hora localizadas, texto y enlaces Editar y Eliminar |
| `/api/web/comedores/observaciones/<pk>/editar/` | GET/POST: mismo formulario; vuelve a la ficha |
| `/api/web/comedores/observaciones/<pk>/eliminar/` | GET: confirmación con la vista previa de la baja. POST: baja lógica (`deleted_at`, `deleted_by`) y vuelta a la ficha del comedor con «Observación dada de baja correctamente.» |

Cada vista de la API ejecuta la vista nativa (`comedores/views/observacion.py`),
así que el formulario, el alcance y los efectos son los mismos. Una
redirección nativa se devuelve como `{"ok": true, "redirect": ...}` y un
formulario inválido como 400 con sus errores. Solo se aceptan POST
`application/x-www-form-urlencoded` o `multipart/form-data` (otro formato
responde 415 sin escribir).

Acceso, en este orden: G1 (sesión y requisitos web, o la constancia firmada
del runtime), el permiso de la URL nativa
(`comedores.add_observacion`, `view_observacion`, `change_observacion` o
`delete_observacion`; el superusuario pasa siempre) y el alcance de la vista
nativa: un comedor u observación fuera del alcance responde 404.

Rarezas nativas conservadas, a propósito:

- Editar cambia el observador visible y la fecha a quien edita y al momento
  de editar, no solo el texto.
- La ficha nativa falla con error 500 si la observación no existe o está fuera
  del alcance; la API responde 404 (la vista nativa usa `.get` sobre un
  `values()` filtrado y el contrato pide no suponer un 404 uniforme).
- Las migajas de estas plantillas usan `div.breadcrumb-item` dentro del `ol`;
  se reproducen así.
- «Imprimir» imprime la página (`window.print()`), como el script global.

Pantallas React: marco oscuro de `routes/MainFrame.tsx`; el formulario
reproduce el campo de crispy (etiqueta con asterisco, `textarea` de 4 filas,
error en `invalid-feedback`), «Confirmar», «Imprimir» y «Cancelar»; el envío es
un solo intento (si no se confirma se avisa y se desactiva el botón); la ficha
usa el colapso de AdminLTE de `relevamientos.tsx`.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 12 pruebas de la API y 2 de la vista previa, en rojo (sin el
  `include`) y luego en verde: permisos, alcance (técnico de una dupla),
  autor y fecha fijados por el servidor, `next` local y externo, rechazos sin
  escritura (vacío, fuera de alcance, JSON, CSRF), edición y baja lógica con
  actor.
- Frontend: 7 pruebas nuevas; `tsc`, `eslint` y la compilación sin errores.
- Visual (regla S13) y G1 de punta a punta: ver el informe de la entrega.

## Limitaciones

- No se agregan restricciones ni se modifican las vistas nativas: lo que el
  contrato marca como residual sigue igual.
