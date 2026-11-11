# Cambio: piezas compartidas de los listados React (#2785)

## Alcance

Seguimiento compartido de la migración React. Los listados de Duplas
(`routes/duplasList.tsx`), AC01 (`routes/acompanamientosList.tsx`) y CDF
(`routes/cdfFilters.tsx` con `routes/cdfCentros.tsx`) repetían la barra de
filtros de `advanced_filters.js`, el modal de columnas de `column_config.js` y
`pagination.html`, cada copia con una parte distinta del script nativo. Se
juntan en un módulo con la unión de funciones, alineada con
`src/backends/kernel/static/custom/js/advanced_filters.js`.

Archivos:

- `src/frontends/apps/sisoc/src/routes/listControls.tsx` (nuevo): `Filters`,
  `filtersConfigValid`, `ColumnModal`, `ServerSortHeader` y `Pagination`.
- `src/frontends/apps/sisoc/src/routes/duplasList.tsx`,
  `src/frontends/apps/sisoc/src/routes/acompanamientosList.tsx` y
  `src/frontends/apps/sisoc/src/routes/cdfCentros.tsx`: usan el módulo.
- `src/frontends/apps/sisoc/src/routes/cdfFilters.tsx`: eliminado.
- Pruebas: `src/frontends/apps/sisoc/src/routes/listControls.test.tsx` (nueva) y
  `src/frontends/apps/sisoc/src/routes/acompanamientos.test.tsx`.

## Comportamiento

| Pieza | Comportamiento (igual al script o template nativo) |
| --- | --- |
| Valor de filtro | `number` usa `type="number"` con `step` 1 por defecto, `date` usa `type="date"`, el resto texto |
| Campos `choice` y `boolean` | select con `options`, `booleanOptions` o «Sí»/«No», o `choices`; arranca en la primera opción; un valor precargado desconocido se agrega como opción |
| Filas | «+ Filtro» agrega con el campo por defecto; «- Filtro» solo desde la segunda; el envío serializa `{logic: "AND", items}` |
| Modal de columnas | insignia «Obligatoria», foco atrapado con Tab, Escape cierra, recarga al guardar |
| Encabezado con orden del servidor | enlace a `sort_url` con el ícono de la dirección |
| Paginación | textos configurables («Anterior»/«Siguiente» en Duplas), saltos «...» y línea de total opcional |

Diferencias respecto de cada copia anterior, todas hacia el nativo:

- AC01: el select de un campo `choice` ya no agrega la opción «Seleccionar»
  (el script nativo vacía el select y carga solo las opciones) y arranca en la
  primera opción; el modal de columnas suma la insignia y el foco atrapado.
- CDF: el campo «Número» (`number`) usa `type="number"` con `step` 1, como
  en el nativo; antes era un input de texto.
- Duplas: sin cambio con su configuración actual (todos los campos son texto);
  un campo `choice` o `boolean` futuro mostraría su select.

## Verificación

- Pruebas: la prueba nueva del módulo y el caso `choice` de AC01 fallaron antes
  del cambio y pasan después; `vitest --project sisoc` completo, `tsc`,
  `eslint` y `vite build`.
- Capturas React del build anterior contra el build con el cambio (servidores
  sintéticos de Duplas, AC01 y CDF, escritorio y móvil; incluye modal de
  columnas, fila agregada y filtros precargados `choice` y `number`).
