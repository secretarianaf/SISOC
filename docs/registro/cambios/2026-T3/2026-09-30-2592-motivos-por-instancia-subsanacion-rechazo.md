# Celiaquía: motivos por instancia al subsanar y rechazar

Ticket 2592. Rama `CeliaquiaTk_2592`.

## Pedido

Cuando Nación pedía una segunda subsanación, la nueva instancia mostraba
también los comentarios técnicos de la primera, como si siguieran pendientes.
El ticket pide:

- que cada subsanación muestre solo los motivos de esa instancia, y que las
  anteriores queden en el historial;
- un multiselect al **Subsanar** para elegir qué motivos se piden en esa
  instancia;
- el mismo multiselect al **Rechazar**, para que el rechazo registre solo los
  motivos elegidos.

## Causa

`ComentariosTecnicosService.observaciones_publicables(legajo)` juntaba todos
los comentarios técnicos con «Sí» que tuvo el legajo, de cualquier instancia.
De esa lista salían el motivo (`leg.subsanacion_motivo` y
`HistorialValidacionTecnica.motivo`, que alimentan el campo «Observación»), las
`SubsanacionObservacion` de la nueva subsanación y la publicación a Provincia.
Cada instancia heredaba así todo lo pedido en las anteriores.

## Solución

**Del cliente llegan los ids de los comentarios técnicos elegidos**
(`observaciones_ids`) y el texto libre. El backend valida que cada id sea un
comentario técnico con «Sí» del mismo legajo y arma el motivo solo con esos.
Sin ids no entra ninguna observación: no hay fallback a «todas», porque ese era
el bug.

En `ComentariosTecnicosService`:

- `opciones_seleccionables(legajo)` alimenta el multiselect: las observaciones
  con «Sí» del legajo, sin duplicados. Cada una marca `pendiente` si todavía no
  se le comunicó a la Provincia.
- `resolver_seleccion(legajo, ids)` valida la selección.
- `componer_motivo(comentarios, texto_libre)` ya no recibe el legajo, así que no
  puede volver a leer el historial completo.
- `publicar(legajo, comentarios=...)` publica solo lo elegido. El argumento es
  obligatorio y se pasa por nombre.

`observaciones_publicables`, `lineas_concatenadas` y `texto_concatenado` se
eliminaron: eran la puerta al comportamiento anterior y solo las usaban
`RevisarLegajoView` y la previsualización.

`LegajoMotivoPreviewView` devuelve `opciones` en lugar de `lineas`/`motivo`.
Los modales Subsanar y Rechazar muestran checkboxes, y el de Rechazar suma un
contenedor de errores propio, como el de Subsanar.

**Sin migración.** El registro por instancia ya existía: `SubsanacionObservacion`
guarda una copia fija del texto de cada subsanación, y
`HistorialValidacionTecnica.motivo` la del rechazo. El historial de
subsanaciones del componente ya mostraba cada instancia por separado.

## Decisiones

Tomadas para avanzar y a validar con producto al mostrarlo:

1. **Opciones:** todas las observaciones con «Sí» del legajo, incluidas las de
   instancias anteriores. El ejemplo del rechazo del ticket elige entre
   observaciones del historial.
2. **Tildado inicial:** solo las que todavía no se comunicaron a la Provincia.
   Las de instancias anteriores se ofrecen sin tildar y con la nota «ya
   comunicada en una instancia anterior».
3. **Lo no elegido no se publica.** Un comentario nuevo que Nación no elige
   queda interno. Antes `publicar()` publicaba todo lo interno con «Sí».
4. **Validación:** hay que elegir al menos un motivo o escribir texto libre. El
   parseo legacy del POST (`motivo`, `motivos`, `tipo_subsanacion`) sigue vivo
   para cuando no se elige ninguna observación.
5. **Datos existentes:** las subsanaciones y rechazos que ya tienen texto
   acumulado quedan como están, porque son historial. El cambio aplica desde la
   próxima acción.

Si una observación se registró varias veces, la opción apunta al registro más
reciente. Al publicarla se publican también sus repetidos internos, para que no
vuelva a figurar como pendiente.

## Fuera de alcance

`SubsanacionObservacion.tipo` convierte ANSES y Condición diagnóstica al mismo
tipo, `DOCUMENTACION`. Por eso en el historial una observación de ANSES aparece
como «Documentación: …». No lo pide el ticket.

## Tests

- `celiaquia/tests/test_comentarios_tecnicos_service.py`: opciones (orden,
  duplicados, pendiente, re-registro después de publicar), validación de ids
  (comentario con «No», de otro legajo, inexistente, basura), motivo y
  publicación restringidos a lo elegido.
- `celiaquia/tests/test_comentarios_tecnicos_flujo.py`: el caso del ticket con
  dos subsanaciones seguidas (la segunda solo lleva la ANSES nueva y la primera
  queda intacta en el historial), el rechazo solo por RENAPER, lo no elegido
  queda interno, y los 400 por selección vacía o inválida.
- Se adaptaron `test_subsanacion_documentacion_complementaria.py` y
  `tests/test_celiaquia_expediente_view_helpers_unit.py`, que mandaban Subsanar
  sin selección o con `POST` como dict.

Suite de celiaquía más los unit tests de la view: 382 passed.
