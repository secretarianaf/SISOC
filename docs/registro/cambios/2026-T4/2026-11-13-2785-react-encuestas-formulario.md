# Cambio: formulario de alta y edición de encuestas en React sobre G1 v1 (#2785, E04.C)

## Alcance

Sexta unidad del [contrato E02 a E04 y D01](../../../plans/2026-T4/2026-11-13-2785-encuestas-dashboard-m2.md): `/encuestas/crear/` y
`/encuestas/<pk>/editar/` con el editor de preguntas completo (arrastre, condiciones, ponderación y «Quitar pregunta») y el menú «Exportar JSON».
Lee y escribe por `EncuestaCreateView` y `EncuestaUpdateView`, sin tocar vistas, servicios, plantillas, `encuestaPreguntasBuilder.js` ni URLs
nativas. No activa React en producción.

Archivos: `src/backends/sisoc_core/encuestas/web_api_formulario.py` (rutas en `web_api_urls.py`), `web_preview_encuestas.py`,
`url_registry.json`, `config/middlewares/admindocs.py`, `src/frontends/apps/sisoc/src/routes/encuestasFormulario.tsx` y `routes/index.ts`.
Pruebas: `test_web_formulario_api.py`, `test_web_preview_encuestas.py` y `encuestasFormulario.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y `encuestas.add_encuesta` (alta) o `encuestas.change_encuesta` (edición), como `encuestas/urls.py` (403).
  CSRF obligatorio en el POST y cuerpo de formulario (415 en otro caso). Una encuesta inexistente es 404; una pendiente de aprobación responde el
  redirect nativo a su revisión.
- Un formulario válido guarda la encuesta y reemplaza sus preguntas en la transacción de la vista nativa, deja el mensaje del servicio en cola
  y navega a `/encuestas/`. Uno inválido (campos, preguntas rechazadas por `reemplazar_preguntas`, encuesta pendiente o con ronda abierta) es 400
  con los valores y las preguntas enviados, los errores nativos y sin cambios persistidos; la pantalla vuelve al inicio.
- El editor reproduce el de `encuestaPreguntasBuilder.js`: numeración, condiciones solo hacia preguntas anteriores (con lista cerrada para
  Sí/No y opciones), puntaje por opción por texto, reordenamiento por arrastre (con marcas de destino, desplazamiento automático y animación) y con
  las flechas del teclado, aviso de orden en un toast, rechazo de movimientos que rompen una dependencia y modal de confirmación al quitar con
  el foco y el Tab de Bootstrap.

## Verificación

Backend (imagen fijada, sin red): pruebas de API (acceso, proyección contra el HTML nativo, efectos persistidos y «sin cambios» ante rechazos) y
de vista previa; `black`, `makemigrations --check`. Frontend: 15 pruebas nuevas, `tsc`, `eslint` y build. G1 de extremo a extremo y comparación
visual nativo contra React (alta, edición, borrador devuelto, error de guardado, modal y menú; escritorio y móvil).

## Limitaciones

El arrastre con el ratón y su desplazamiento automático se probaron con eventos `dragstart`/`dragover`/`drop`; la animación de reordenamiento
se omite con `prefers-reduced-motion`, como el original. Un valor de condición guardado que no esté entre las opciones de la pregunta
referenciada se muestra sin selección, igual que el `select` nativo.
