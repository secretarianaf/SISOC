# Cambio: Foco en el alcance territorial (#2960)

## Alcance y comportamiento

El selector React daba foco a la búsqueda al abrir y devolvía el foco al control al cerrar, sin inhibir el desplazamiento implícito del navegador. Los selectores de alcance optan por `preventScroll` en ambas transiciones; conservan la búsqueda, el teclado y la carga dependiente. Los demás consumidores conservan su comportamiento.

## Verificación

Vitest reprodujo la llamada a foco sin la opción y verificó la corrección, la cascada y el envío de los alcances.

Chromium contra la demo local, con un usuario sintético: el desplazamiento observado con dos frames de espera provenía del centrado suave aún en curso (`scroll-behavior: smooth`). Con centrado instantáneo y coordenadas del puntero (sin autodesplazamiento del selector de Playwright), escritorio conservó `scrollY=2021` al abrir, elegir Buenos Aires, abrir municipio y cerrar con Escape. Al quitar `preventScroll` solo en la instrumentación del navegador, la misma selección desplazó la página de 2021 a 224. En edición con viewport de 390×844, el teclado conservó 2439 al abrir y elegir provincia, y 2457 al abrir y cerrar municipio.

La primera prueba aisló los recursos externos. Se repitió en Chromium sin bloquear las hojas de estilo de la aplicación: el alta de escritorio y la edición en viewport móvil conservaron la posición al abrir y elegir Buenos Aires, y al abrir y cerrar municipio. En edición, guardar con una segunda fila sin provincia devolvió HTTP 400 y mostró el error de validación.

La persona solicitante confirmó la prueba visual local. No se verificó en QA ni en producción.
