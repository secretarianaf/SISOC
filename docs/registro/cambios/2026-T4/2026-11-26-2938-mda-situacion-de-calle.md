# Cambio: Mesa de Ayuda de Situación de Calle en SISOC (#2938)

## Alcance

Pedido (issue #2938): exponer el acceso a la Mesa de Ayuda (MDA) del programa
Situación de Calle, como el botón "Consultas" que ya tiene CDI, en el margen
superior derecho de `/datacalle/relevamientos/` y `/dispositivos/`. El enlace es
`https://consultas.capitalhumano.gob.ar/canales/equipo-situacion-de-calle`.

La parte de la aplicación de territorio (`/pwa/datacalle/`) la implementa otra
persona asignada al issue y no está en este cambio.

Implementado:

- Django: `src/backends/kernel/templates/includes/header.html` agrega el ítem
  "Consultas" en las rutas `dispositivos/...` y `datacalle/...`, junto al de CDI.
- React: `src/frontends/apps/sisoc/src/routes/cdfFrame.tsx` (`headerItemsFor`),
  el frame de las pantallas de dispositivos y datacalle, agrega el mismo ítem
  según la ruta; las pantallas de Centro de Familia que comparten el frame no
  lo muestran.

## Comportamiento

- En listado, legajo, mapa y formularios de Dispositivos, y en Relevamientos y
  Casos de datacalle, el header muestra "Consultas" antes del botón de salir.
  Abre la MDA de Situación de Calle en una pestaña nueva.
- CDI conserva su canal (`sisoc-cdi`). El resto de SISOC no muestra el botón.
- Se muestra en todas las rutas del módulo, como CDI, no solo en los dos
  listados que nombra el issue (decisión de implementación para que el acceso no
  desaparezca al entrar a un detalle).

## Verificación

- `pytest src/backends/kernel/tests/test_header_consultas.py` (10) y
  `src/backends/dispositivos`: 395 passed, 2 failed
  (`test_admin_operaciones_datacalle.py::test_listados_sin_n_mas_1`, que fallan
  igual sin este cambio).
- React: `vitest` de `cdfFrame` (nuevo), `dispositivos`, `datacalleRelevamientos`,
  `datacalleCasos`, `cdfCentros`, `dispositivoForm` y `shellNavigation`: 92 passed;
  `tsc` y `eslint`.
- Verificación visual local con React activo.
