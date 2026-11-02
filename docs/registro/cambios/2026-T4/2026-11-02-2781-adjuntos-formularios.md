# Cambio: adjuntos (imagen o PDF) en todos los formularios de relevamiento (#2781, punto 1, backend)

## Alcance

Los formularios de relevamiento de la app (relevamiento, seguimiento, seguimiento PNUD y acta
complementaria) pueden adjuntar documentos en la última pantalla. Esta parte es el backend; la app
Gestionar sube los archivos por la API nueva. Diseño aprobado por quien pidió el cambio; la
elección de modelo genérico (tipo + id) en lugar de cuatro FK la propuso el agente.

- Modelo `ArchivoAdjunto` en `src/backends/comedores/relevamientos/models.py` (migración
  `0025_archivo_adjunto.py`, solo crea la tabla). Dueño: `relevamientos`, que es donde viven los cuatro
  formularios. Apunta al formulario con `formulario_tipo` + `formulario_id` (id SISOC), sin FK: son
  cuatro modelos distintos y la API los identifica por ese par.
- Reglas compartidas en `relevamientos/services/adjuntos.py`; vistas en
  `comedores/api_views_territorial_archivos.py` (mixin de `TerritorialComedorViewSet`).
- Detalle web: bloque "Archivos adjuntos" (`relevamientos/templates/adjuntos_formulario.html`) en el
  detalle de relevamiento, seguimiento, seguimiento PNUD y acta.

## Comportamiento

- `POST /api/territorial/comedores/{id}/adjuntos/` (multipart: `archivo`, `formulario_tipo`
  = relevamiento | seguimiento | seguimiento_pnud | acta, `formulario_id`, `client_uuid` opcional).
  201 con `{"adjuntos": [...]}` (lista completa del formulario); mismo `client_uuid` -> 200 sin duplicar.
  Errores 400 `{"detail": "..."}`; formulario inexistente o de otro comedor -> 404.
- `GET` con `?formulario_tipo=&formulario_id=` -> misma lista.
- `DELETE /api/territorial/comedores/{id}/adjuntos/{adjunto_id}/` -> solo quien lo subió (403 si no),
  409 si el formulario ya está Validado, 404 si no existe; 200 con la lista.
- Se aceptan JPG, JPEG, PNG, WEBP y PDF; el contenido se verifica (cabecera `%PDF`, imágenes con
  Pillow) y el MIME guardado sale del contenido. Máximo 10 MB por archivo y 10 archivos por formulario.
- Permisos: los mismos que las fotos (`_comedor_accesible`: comedor asignado o de la zona del
  territorial). No se agregó ni cambió ningún permiso.
- Archivos en `MEDIA_ROOT/adjuntos/<comedor>/<uuid>.<ext>`, servidos como el resto de `MEDIA`
  (fotos y firmas): sin control de acceso propio, con nombre no adivinable.

## Riesgos

- Migración nueva (tabla nueva, sin datos previos). Otra rama también agrega una migración en
  `relevamientos`: si se mergean ambas hay que renumerar la que llegue segunda.
- Al borrar un formulario SISOC sus adjuntos quedan huérfanos (no hay FK); no se listan en ningún lado.

## Verificación

Tests en `src/backends/comedores/tests/test_adjuntos_formularios_2781.py`: alta por tipo, formatos,
idempotencia, contenido y extensión inválidos, tamaño, tope de 10, 404/403/401, baja y detalle web.
