# Cambio: revisión de solicitudes de publicación de encuestas en React sobre G1 v1 (#2785, E04.B)

## Alcance

Quinta unidad del [contrato E02 a E04 y D01](../../../plans/2026-T4/2026-11-13-2785-encuestas-dashboard-m2.md): `/encuestas/<pk>/revision/` con
«Aprobar y publicar» y el modal «Rechazar solicitud». Lee por `EncuestaRevisionView` y escribe por `EncuestaAprobarView` y
`EncuestaRechazarView`, sin tocar vistas, servicios, plantillas ni URLs nativas. No activa React en producción. El formulario de alta y
edición (E04.C) sigue nativo.

Archivos: `src/backends/sisoc_core/encuestas/web_api_revision.py` (rutas en `web_api_urls.py`), `web_preview_encuestas.py`,
`url_registry.json`, `config/middlewares/admindocs.py`, `src/frontends/apps/sisoc/src/routes/encuestasRevision.tsx` y `routes/index.ts`.
Pruebas: `test_web_revision_api.py`, `test_web_preview_encuestas.py` y `encuestasRevision.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y `aprobar_encuesta` o `change_encuesta` para leer (403); aprobar y rechazar exigen `aprobar_encuesta`.
  CSRF obligatorio. Los botones solo se dibujan para quien puede aprobar y con la solicitud pendiente, como la plantilla.
- Aprobar publica y abre la primera ronda; rechazar guarda el motivo (recortado), el usuario y vuelve a borrador. Ambos dejan el mensaje
  del servicio en cola y navegan al redirect nativo. Un motivo vacío o de más de 2000 caracteres es 400 sin cambios; repetir una
  transición muestra el error nativo sin cambios.
- El modal es el de Bootstrap en su posición nativa, con foco en el motivo, Tab atrapado y Escape para cerrar.

## Verificación

Backend (imagen fijada, sin red): 11 pruebas de API (acceso, comparación de textos con la página nativa, efectos persistidos y «sin
cambios» ante rechazos) y 1 de vista previa; `black`, `pylint` y `makemigrations --check`. Frontend: 9 pruebas, `tsc`, `eslint` y build. G1 de
extremo a extremo (401, 403, requisito pendiente, cabecera falsificada, CSRF, lectura, 400 sin cambios y aprobación persistida).
Comparación visual nativo contra React (aprobador, gestor, devuelta con motivo, publicada, modal y rechazo inválido; escritorio y móvil).

## Limitaciones

La revisión de una encuesta con muchos destinatarios los lista todos dentro del `details`, como la plantilla.
