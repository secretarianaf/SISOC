# Cambio: la barra lateral de `SisocShell` recorta la barra amarilla de la rama activa (#2785)

## Alcance

Corrige una diferencia visual compartida entre el shell React y las páginas nativas
de Django. No cambia el orden de Tab, los textos ni ninguna pantalla en particular.

Archivos:

- `src/frontends/apps/sisoc/src/routes/SisocShell.tsx`.
- `src/frontends/apps/sisoc/src/routes/shellNavigation.test.tsx`.

## Causa

`kernel/static/custom/css/main.css` dibuja la barra amarilla de la rama abierta con
`.nav-main-item.menu-open::before`, que es `position: absolute` y no define `top`.
Su bloque contenedor es el ancestro posicionado más cercano. En la página nativa el
script de OverlayScrollbars convierte `.sidebar-wrapper` en un host posicionado, de
modo que el wrapper lo recorta. El shell React no ejecuta ese script: el contenedor
pasaba a ser `.app-sidebar` (sticky), el recorte del wrapper no alcanzaba a la barra
y esta se dibujaba debajo del área visible, estirando la página.

El efecto aparece solo en páginas cortas a 1440x900 con una entrada de menú activa
(por ejemplo las pantallas de cursos de la app mobile), con una diferencia
perceptual de entre 13 y 15 % contra la página nativa.

## Solución

`.sidebar-wrapper` del shell lleva `position: relative`, equivalente al host
posicionado nativo. El resto del marcado y el orden de Tab no cambian.

## Verificación

- Prueba de unidad: el wrapper del shell está posicionado.
- Visual S13 de cursos (listado, alta, alta con error, edición y baja; escritorio
  y móvil) pasa con diferencia perceptual de 0,000 a 0,001 %; antes fallaban cuatro
  casos de escritorio.
- Sin regresión en pantallas cortas ya migradas (comunicados y una de comedores).

## Limitaciones

Se resuelve con un estilo en línea porque la hoja nativa no se modifica. Si el
shell cargara OverlayScrollbars, el estilo sería redundante pero inofensivo.
