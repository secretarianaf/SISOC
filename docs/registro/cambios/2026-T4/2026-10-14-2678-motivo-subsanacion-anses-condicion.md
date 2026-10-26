# Celiaquía: motivo de subsanación por ítem y observaciones en listado

Ticket 2678. Rama `CeliaquiaTk_2678`.

## Pedido

- Cuando Nación pide una subsanación por **ANSES** o por **Condición
  diagnóstica**, la Provincia ve el motivo como «Documentación» y no sabe cuál
  de los dos ítems corregir. RENAPER ya se veía bien.
- Las observaciones de la subsanación se ven en un párrafo corrido. Se pide
  mostrarlas como listado, una por renglón.

## Causa

1. `MAPA_TIPO_DOCUMENTO_A_SUBSANACION` (`services/revision_service/impl.py`)
   traducía ANSES y CONDICION_DIAGNOSTICA a `TipoSubsanacion.DOCUMENTACION` al
   crear las `SubsanacionObservacion`. El bloque «Subsanación solicitada» pinta
   `get_tipo_display()`, de ahí el «Documentación».
2. El motivo se guarda con un salto de línea por observación y el template
   dependía de `.motivo-multilinea` (`white-space: pre-line`). Esa clase vive
   en `listModerno.css`, que `expediente_detail.html` no carga: el navegador
   colapsaba los saltos.

## Solución

- `TipoSubsanacion` suma `ANSES` y `CONDICION_DIAGNOSTICA`, y el mapa conserva
  el tipo de documento del comentario técnico. `DOCUMENTACION` sigue existiendo
  para los datos previos y para la API/POST legacy que lo envía explícito.
- `SubsanacionObservacion.tipo` pasa de `max_length=20` a `30`, porque
  `CONDICION_DIAGNOSTICA` tiene 21 caracteres. Migración
  `0009_subsanacionobservacion_tipos_anses_condicion` (ensancha un `varchar`,
  sin datos).
- `ExpedienteCiudadano.SUBSANACION_TIPO_LABELS` y los rótulos de
  `subsanacion_tipo` del detalle cubren los dos tipos nuevos.
- La vista arma `observacion_tecnica_items` (un ítem por renglón no vacío del
  motivo) y el template lo pinta con `partials/motivo_lista.html` como `<ul>`.
  Aplica a Provincia y a Nación, en los cuatro bloques que mostraban el motivo.

## Trade-offs

- **Sin corrección de históricos (definición de producto).** El cambio aplica
  a las subsanaciones que se pidan desde el fix en adelante; las observaciones
  ya creadas como DOCUMENTACION siguen mostrándose así. Era recuperable: cada
  observación copia el texto de un comentario técnico del mismo legajo, que
  conserva su `tipo_documento`, así que una migración de datos podría
  reasignarlas por coincidencia exacta de legajo y texto. Se descartó porque no
  hace falta para la operación.
- **Etiqueta «Condición diagnóstica»** (minúscula), igual que el prefijo que ya
  lleva cada renglón del motivo, para no mostrar dos grafías en la misma
  pantalla.
- El texto libre complementario también se parte por renglón: cada renglón es
  un ítem del listado.
- Se quitan las ramas del template que pintaban `subsanacion_motivo` con
  `.motivo-multilinea` cuando no había `observacion_tecnica_texto`: la vista
  copia `subsanacion_motivo` a ese campo cuando existe, así que nunca se
  mostraban con contenido. Quedan con el «-» que ya usaban.

## Tests

- `test_comentarios_tecnicos_flujo.py`: el mapeo esperado pasa a
  CONDICION_DIAGNOSTICA y se agrega el caso ANSES.
- `test_expediente_detail.py`: etiquetas nuevas y render del motivo como
  listado.
