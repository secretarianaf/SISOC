# Cambio: «Volver» de las pantallas React usa el historial del sistema (#2957)

## Alcance

El #2971 arregló «Volver» solo en el historial de comedores. La causa era general: la cabecera React (`SisocShell`) tenía un destino fijo y, si la pantalla no declaraba uno, llevaba a Inicio. Las pantallas Django ya resolvían el destino con `src/backends/kernel/static/custom/js/volver.js`.

## Comportamiento

`src/frontends/apps/sisoc/src/volver.ts` replica esa lógica y comparte la misma pila de `sessionStorage` (`sisocNavStack`). Así el botón funciona igual al pasar entre pantallas Django y React. El orden es: destino declarado por la pantalla (con los filtros con que se visitó), pantalla anterior de la pila, referrer del mismo origen y, por último, Inicio. Nunca usa `history.back()` ni destinos externos.

Las altas, ediciones y bajas no se apilan. En Django lo marca el servidor por la clase de la vista; en React se deduce de la ruta (`crear`, `nuevo`, `editar`, `eliminar`, `borrar` y equivalentes en inglés).

## Verificación

Vitest cubre la resolución del destino, la pila compartida con Django, los pasos transitorios y el rechazo de destinos externos, más el enlace de la cabecera. Typecheck y lint sin errores.

## Limitaciones

Una pantalla React de formulario cuya ruta no use esas palabras sí se apila. No se probó en navegador ni en QA.
