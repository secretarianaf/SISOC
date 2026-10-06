# Correcciones Comedores - Octubre (#2630)

## 1. Relevamiento finalizado desde la app: "Pendiente de validación"

La app territorial cierra la visita con `PATCH /api/relevamiento` y
`estado: "Finalizado"` (o `Finalizado/Excepciones`). El mismo PATCH deja
`estado_validacion = "Pendiente validación coordinador"`. En SISOC se seguía
viendo "Finalizado" en el listado de acompañamientos del comedor, en la línea
de tiempo y en el título del detalle, aunque el coordinador todavía no lo
había validado.

Ahora, cuando el estado es `Finalizado` o `Finalizado/Excepciones` y
`estado_validacion` es exactamente `Pendiente validación coordinador`, esas
tres vistas muestran **"Pendiente de validación"**. En la línea de tiempo la
tarjeta usa el estilo de pendiente en lugar del de finalizado. La regla vive
en `RelevamientoService.estado_para_mostrar`.

Decisiones:

- **Solo cambia lo que se muestra.** `estado` sigue guardando `Finalizado`:
  de ese valor dependen el payload a GESTIONAR, el botón de PDF, la
  geolocalización por excepción, el primer seguimiento, el presupuesto y el
  resumen del comedor y la PWA.
- **Igualdad estricta con el estado pendiente.** Los relevamientos históricos
  con `estado_validacion` vacío siguen mostrando "Finalizado"; con la regla
  "distinto de Validado" habrían pasado todos a pendientes.
- **"A subsanar" y "Validado" no cambian:** muestran el estado guardado. El
  issue no los pide; el badge de validación del detalle ya los informa.

## 2. Descarga del PDF desde SISOC

El botón "Imprimir" del detalle era un link a `docPDF`, la URL que GESTIONAR
devuelve al dar de alta el relevamiento. Ese PDF lo generaba el bot de
AppSheet al finalizar *dentro de AppSheet*. Con la app nueva la visita se
cierra en SISOC, así que el archivo nunca se genera: el link quedaba vacío
(el botón reabría la misma página) o daba 404 (ver
`docs/analisis/gestionar_formularios_relevamiento.md` §9).

La app (repo `secretarianaf/Gestionar`, `pwa/src/features/pdf/`) arma su PDF
como HTML en el dispositivo e imprime con `window.print()`. No lo sube a
SISOC y nunca completa `docPDF`.

Ahora SISOC genera su propio PDF:

- Ruta `comedores/<comedor_pk>/relevamiento/<pk>/pdf`
  (`relevamiento_pdf`), con el mismo permiso que el detalle
  (`relevamientos.view_relevamiento`). Devuelve
  `relevamiento-<id>.pdf` como adjunto. El botón pasa a llamarse "Descargar
  PDF" y sigue visible solo para `Finalizado` y `Finalizado/Excepciones`.
- `RelevamientoPdfView` reutiliza el objeto y el contexto de
  `RelevamientoDetailView`. `RelevamientoPdfService` renderiza con weasyprint,
  la misma librería que usa admisiones.
- Las secciones de datos del detalle pasaron sin cambios a
  `relevamiento_detail_secciones.html`, que incluyen el detalle y el PDF. Así
  el PDF muestra exactamente los mismos campos que la pantalla. Se verificó
  que el detalle renderiza igual que antes, salvo el botón.
- **Recursos del PDF solo desde disco.** `RecursosLocalesURLFetcher` sirve
  archivos de `STATIC_URL` y `MEDIA_URL` del propio host y rechaza cualquier
  otra URL. Las URLs de imágenes llegan desde la app y GESTIONAR: dejar que
  weasyprint las descargue permitiría que el servidor pida recursos de la red
  interna (SSRF). Por eso las fotos alojadas fuera de SISOC (por ejemplo, las
  de AppSheet en relevamientos viejos) no aparecen en el PDF.

`docPDF` se sigue guardando y exponiendo por API como antes; solo dejó de
usarse en el botón.

## Pendiente

- Confirmar con el equipo funcional cómo mostrar "A subsanar" en el listado.
- El PDF de SISOC no replica el formato oficial de AppSheet que imita la app
  (5 páginas con posiciones fijas). Si hace falta ese formato, es un trabajo
  aparte.
