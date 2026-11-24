# Cambio: componentes de paridad compartidos del frontend React (#2785)

## Alcance

Los módulos de rutas de `src/frontends/apps/sisoc/src/routes/` reimplementaban la misma
mecánica de paridad con las pantallas nativas. Se la reúne en dos módulos compartidos y se
migran los usos mecánicos, sin cambiar lo que ve o hace el usuario. No hay cambios de
backend, de URLs ni de contratos.

Archivos:

- `routes/select2.tsx`: un único `Select2` de opciones locales.
- `routes/nativeParity.tsx`: `NativeToasts`, `useModalTabTrap`, `NativeModal` y
  `resetAfterRejectedPost`.
- `cdfSelect2.tsx`, `duplasSelect2.tsx`, `pasSelect2.tsx` y `datacalleSelect2.tsx`: ahora
  envolturas finas que conservan sus props y su exportación `Choice`.
- Usos migrados: `listControls.tsx`, `cdfDataTable.tsx`, `rendicionMensual.tsx` y
  `cdiCentros.tsx` (trampa de Tab del modal), `rendicionFinal.tsx` (`NativeModal`),
  `relevamientosApi.tsx` (toasts y reinicio) y `admisionesInformeDetalle.tsx` (toasts).
- Pruebas nuevas: `select2.test.tsx` y `nativeParity.test.tsx`.

## Diferencias entre las variantes de Select2 y su opción

| Diferencia | Opción |
| --- | --- |
| Término de búsqueda: cdf y duplas lo conservan al abrir/cerrar y Escape/Tab solo cierran; pas y datacalle lo borran, y Escape devuelve el foco | `termHandling` `keep` / `reset` |
| Enter sobre una opción ya elegida de un múltiple: solo cierra (cdf, duplas) o la quita (pas, datacalle) | `enterOnSelected` |
| La cruz de una etiqueta limpia la búsqueda y abre los resultados (cdf, duplas) | `removeOpensResults` |
| Cruz de limpiar: ninguna (duplas), al hacer clic y vaciando la búsqueda (cdf), al presionar y cerrando (pas, datacalle) | `clearTrigger` |
| Marca `select2-container--focus`: ninguna (duplas), campo de búsqueda (cdf), cualquier foco dentro (pas, datacalle) | `focusMarker` |
| Un clic cuenta como externo salvo sobre la lista (cdf, duplas) o sobre todo el desplegable (pas, datacalle) | `outsideClick` |
| Desplegable en `<body>` siguiendo el scroll (cdf, duplas, datacalle) o dentro del modal (pas); `null` = aún sin elemento | `dropdownParent` |
| Opción vacía oculta de los resultados (pas siempre; datacalle si hay placeholder) | `hideEmptyChoice` |
| Placeholder, texto sin resultados («No results found» / «Sin resultados»), clases y atributos del select nativo, deshabilitado | `placeholder`, `noResults`, `selectClassName`, `selectProps`, `disabled` |
| Foco del select simple nativo (regla corregida en `InspSelect2`) | `singleFocus="selection"` |

## Verificación

Entorno local sin red, Node 22.14.0, árbol exportado de `HEAD` `4b4ac81fd`.

- Las pruebas existentes pasan sin cambios (solo se tocó código de rutas, ningún test).
- Pruebas nuevas de los módulos compartidos (18 en total entre `select2.test.tsx` y
  `nativeParity.test.tsx`), `tsc`, ESLint (0 errores) y build de Vite en verde.
- Equivalencia con el código anterior: prueba diferencial descartable que ejecuta las
  cuatro envolturas y las implementaciones previas con las mismas 60 interacciones
  aleatorias por semilla (12 semillas, varias configuraciones y valores iniciales) y compara
  tras cada paso el DOM completo, el elemento enfocado y las llamadas a `onChange`:
  sin diferencias. No se versiona porque lee las copias del código previo.

## Limitaciones

- `InspSelect2.tsx` no se migró: su fuente de datos es remota y asíncrona. Solo comparte
  la regla de foco, disponible como `singleFocus="selection"` sin consumidor todavía.
- Quedan con su propia implementación los modales de `admisionesInformeDetalle.tsx`,
  `inspeccionesActaDetallePage.tsx`, `pasCambioEstado.tsx` y `inspeccionesModal.ts`
  (trampa por `focusin`, con otras reglas), los toasts de `inspeccionesToasts.tsx`
  (otro marcado) y los reinicios `freshPage` / `restartKeyboardFromTop` (mecanismos
  distintos de enfoque).
- La comparación visual de píxeles (S13) contra las pantallas nativas no se corrió en
  este cambio; la equivalencia se probó por marcado y comportamiento idénticos con el
  mismo CSS.
