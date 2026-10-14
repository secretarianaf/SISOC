# PDF de SISOC igual al de Gestionar (#2630, feedback de QA del 8 y 13/10)

## Problema

QA rebotó dos veces el punto 2 del #2630:

- jcamiloparra (8/10): el formulario inicial que descarga SISOC no es el de la
  app; "la versión en SISOC debe ser la que actualmente se encuentra en la app".
  El seguimiento no se puede descargar desde SISOC.
- FacuDrudkh (13/10): "PDFs no coinciden con lo establecido en el tk" (adjuntó
  los dos PDF del relevamiento 8419) y el seguimiento sigue sin PDF en SISOC.

El PR #2660 resolvió la descarga con un PDF propio de SISOC armado con las
tarjetas del detalle. La app arma otra cosa: una réplica del PDF oficial
("RELEVAMIENTOS COMEDORES 2026", "FORMULARIO DE PRIMER VISITA DE SEGUIMIENTO",
etc.) con la capa fija del papel y los datos en posiciones medidas, que el
territorial imprime desde el navegador. Nunca llegaba a SISOC.

## Decisión

Se eligió que **la app suba el documento que ya arma** y SISOC lo convierta,
en lugar de portar las réplicas a SISOC (unas 2.000 líneas de layout y sus
assets, duplicadas en dos repos). Así el PDF de SISOC es, por construcción, el
mismo que el de la app.

Trade-offs aceptados:

- El PDF refleja lo que envió el territorial. Una edición posterior desde
  SISOC no lo modifica. El detalle lo aclara ("Formato oficial de Gestionar,
  enviado el …").
- Un relevamiento sin documento de la app (cargado en SISOC o enviado antes de
  Gestionar 1.1.62) sigue con el PDF genérico de SISOC. Un seguimiento sin
  documento no tiene PDF y el detalle explica de dónde sale.
- Los registros enviados antes de 1.1.62 reciben su documento cuando el
  territorial abre el PDF en la app (solo se habilita validado).

## Cómo funciona

1. Gestionar (1.1.62), después de cada envío aceptado de un relevamiento o una
   instancia de seguimiento, arma la réplica oficial, pasa a `data:` todo lo
   que referencia (fuentes, capa fija, imágenes) y la sube en multipart:
   - `POST /api/relevamiento/pdf-oficial` con `sisoc_id` del relevamiento.
   - `POST /api/relevamiento/seguimiento/pdf-oficial` con los mismos
     identificadores que su PATCH (`sisoc_id` de la instancia o
     `id_relevamiento` para la nº1).
   - Campos `html` (archivo) y `version_app`.
   La subida es best-effort: si falla, el envío del formulario ya quedó hecho.
2. SISOC guarda el documento en `PdfOficialGestionar` (uno por relevamiento o
   por instancia; reenviar lo reemplaza). Mismo alcance que el PATCH: un
   territorial solo sube para lo que tiene asignado o para su provincia.
3. Al descargar, `relevamientos/pdf_oficial.py` lo convierte con weasyprint y
   guarda el PDF; las descargas siguientes salen de ese PDF hasta que la app
   suba otra versión. La primera conversión del primer seguimiento (12
   páginas) tarda unos 12 segundos; el inicial, unos 3.

## Seguridad

El HTML viene del cliente:

- Nunca se sirve como HTML: solo se entrega el PDF que sale de él.
- weasyprint resuelve únicamente `data:` y archivos propios de `STATIC_URL` y
  `MEDIA_URL` (`PdfOficialURLFetcher`, extiende `RecursosLocalesURLFetcher`):
  sin red, sin `file:`. Lo externo (por ejemplo el mapa estático) se omite.
- Tope de 20 MB, UTF-8 y `<!doctype html>` obligatorios.
- Un registro validado recibe su primer documento pero no se reemplaza (409),
  como los PATCH: lo que validó el coordinador no cambia. Las API keys de
  integración conservan el acceso.

## Verificación

- `tests/test_pdf_oficial_gestionar_2630.py`: subida, reemplazo y caché,
  alcance, validaciones del documento, validado, identificación del
  seguimiento, fetcher, descargas desde los detalles y los casos sin documento.
- Las réplicas reales de la app (inicial y primer seguimiento) se convirtieron
  con el fetcher de SISOC y salen iguales al PDF que imprime Chrome.
