# Cambio: ranura `appHeader` del marco React oscuro (#2785)

## Alcance

Seguimiento compartido de la migración React. `{% block app-header %}` de
`src/backends/kernel/templates/includes/main.html` reemplaza la fila vacía
(`<div class="row"></div>`) del encabezado de contenido. Las pantallas PAS y la
ficha AC01 lo imitaban con portales que buscaban ese nodo en el DOM del marco
después de montarlo. Ahora el marco recibe el bloque como prop.

Archivos:

- `src/frontends/apps/sisoc/src/routes/SisocShell.tsx`: prop `appHeader`; sin
  ella se mantiene la fila vacía del template.
- `src/frontends/apps/sisoc/src/routes/MainFrame.tsx`: `MainPage.appHeader` se
  pasa al marco.
- `src/frontends/apps/sisoc/src/routes/pasFrame.tsx`: se quita el portal
  `PasAppHeader`.
- `src/frontends/apps/sisoc/src/routes/pas.tsx`,
  `src/frontends/apps/sisoc/src/routes/pasBuscador.tsx`,
  `src/frontends/apps/sisoc/src/routes/pasPanel.tsx` (nuevo `PanelHeader`) y
  `src/frontends/apps/sisoc/src/routes/pasCambioEstado.tsx`: los botones
  `pas-top-actions` van por `appHeader`.
- `src/frontends/apps/sisoc/src/routes/acompanamientos.tsx`: el nombre del
  comedor de la ficha va por `appHeader`; se quita el portal y su nodo sonda.
- Pruebas: `src/frontends/apps/sisoc/src/routes/shellNavigation.test.tsx`,
  `src/frontends/apps/sisoc/src/routes/pas.test.tsx` y
  `src/frontends/apps/sisoc/src/routes/acompanamientos.test.tsx`.

## Comportamiento

Sin cambio visible. El bloque aparece en el mismo render que el resto de la
página (antes, un render después del portal). En PAS el contenedor ya no
conserva la fila vacía antes de `pas-top-actions`, igual que el template
nativo. Las pantallas que no pasan `appHeader` siguen con la fila vacía.

## Verificación

- Pruebas: 2 casos nuevos fallaron antes del cambio y pasan después;
  `vitest --project sisoc` completo, `tsc`, `eslint` y `vite build`.
- Capturas React del build anterior contra el build con el cambio (mismos
  servidores sintéticos de PAS y AC01, escritorio y móvil): PNG idénticos byte
  a byte, misma estructura y mismo orden de Tab.
