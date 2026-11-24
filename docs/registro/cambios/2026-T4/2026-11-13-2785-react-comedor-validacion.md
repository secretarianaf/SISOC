# Cambio: validación de comedor en React sobre G1 v1 (#2785, CO07.03)

## Alcance

Primera entrega de la lane K5 del contrato
[`2026-10-28-2785-comedores-validacion-convenio-tarjeta-m2.md`](../../../plans/2026-T4/2026-10-28-2785-comedores-validacion-convenio-tarjeta-m2.md):
los dos modales de validación («Validación del Comedor» y «Motivos de No
Validación») y la API que los sirve. La validación no tiene URL propia: la
dispara el botón del encabezado de la ficha, que construye otra lane. Por eso
se entrega un componente reutilizable que la ficha monta; esta entrega no
edita ningún módulo de la ficha. No activa React en producción y no cambia
ninguna vista, ruta ni permiso nativo.

Archivos:

- `src/backends/comedores/comedores/web_api_validacion.py` y
  `web_api_validacion_convenio_tarjeta_urls.py`: API web.
- `src/backends/comedores/comedores_runtime/web_api_urls.py`,
  `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/comedorValidacion.tsx` y su prueba.
- Prueba: `src/backends/comedores/comedores/tests/test_web_comedor_validacion_k5.py`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/comedores/comedores/<pk>/validacion/` | Comedor del alcance (404 si no), `puede_validar` calculado por el servidor, las opciones de `HistorialValidacion` (vacías si no puede) y el enlace a la ficha |
| `POST /api/web/comedores/comedores/<pk>/validar/` | Ejecuta la vista nativa `validar_comedor`; responde `{"redirect": ...}` |

El POST es la vista nativa tal cual: alcance del objeto, regla de
`ValidacionService` (superusuario, `role_validador_comedores` o técnico de la
dupla asignada; abogado y coordinador no alcanzan), actualización atómica de
`estado_validacion` y `fecha_validado`, fila de `HistorialValidacion` con
actor, opciones y comentario, y `safe_redirect` de `next` (un destino externo
cae en la ficha). Los rechazos (sin capacidad, sin opciones, «Otro» sin
comentario, acción inválida) son la misma redirección con el mensaje nativo en
cola y no cambian nada. Repetir la acción agrega una fila y mueve la fecha.

Acceso, en este orden: G1, el permiso de la URL nativa (`view_comedor`,
`view_admision` o `view_informacionrelevante`; el superusuario pasa siempre),
CSRF y el alcance del comedor.

React: el componente `ComedorValidacion` recibe `comedorId`, `open` y
`onClose`. Al abrirse pide `validacion/`; si el servidor no da capacidad no
muestra ningún modal. «Validar» envía `accion=validar`; «No Validar» abre el
segundo modal (selección múltiple y comentario visible solo con «Otros»), con
las mismas alertas nativas y sin enviar mientras una aplique. Cancelar no
envía nada. Tras el POST navega a la ficha, que muestra el mensaje. Un fallo
de red o 5xx avisa y no reintenta.

## Para quien monta el componente

La ficha pinta el botón con `header.validar` y mantiene el estado `open`; el
componente hace el resto. No hay control inerte: sin montar el componente no
se agrega ninguna acción.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 14 pruebas, en rojo (sin el `include`) y luego en verde: acceso,
  capacidad por rol, alcance, efectos persistidos, rechazos sin escritura,
  `next` externo, repetición, 405.
- Frontend: 9 pruebas nuevas.
- G1 de punta a punta: ver el informe de la entrega.

## Limitaciones

- La comparación visual de los modales requiere la ficha en React; queda para
  la lane que la monta.
- No se agregan códigos de opción ni se modifica el servicio: la interfaz solo
  ofrece las cinco opciones del modelo y el servicio acepta cualquier valor,
  como en el nativo.
