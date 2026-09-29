# Rendiciones #2545: "Monto rendido" pasa a llamarse "Monto auditado"

El monto que se carga al finalizar la etapa `Auditoría` se muestra ahora como
`Monto auditado` en lugar de `Monto rendido`. El cambio es solo de etiqueta y
alcanza a las pantallas indicadas en el issue:

- formulario de cierre de Auditoría del detalle de la rendición (Línea
  Tradicional y Línea Secos), incluido el mensaje de validación cuando falta
  el monto;
- detalle de la rendición desde el legajo de la organización.

La columna del listado `Rendiciones Presentadas` conserva su texto anterior,
porque ese cambio no está pedido en #2545.

No cambian el campo persistido (`monto_rendido`), el nombre del input del
formulario, los servicios ni ningún contrato de API/PWA. El `verbose_name` del
modelo se mantiene para no generar una migración por un cambio cosmético; solo
se ve en el admin de Django.
