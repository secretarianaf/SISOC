# Cambio: foco y teclado del selector J2 iguales a Select2 nativo (#2785)

## Alcance

Seguimiento compartido de la migración React (decisión del dueño en el log
L144 del seguimiento de la migración: paridad nativa bajo «diseño
idéntico»). El selector remoto de Inspecciones
(`src/frontends/apps/sisoc/src/routes/InspSelect2.tsx`) movía el foco al campo
de búsqueda al abrir el desplegable. El Select2 4.1 nativo de `panel.js` lo deja
en la caja de selección, por lo que la pestaña Escuelas difería en el anillo de
foco (0,054 % y 0,102 % de píxeles en escritorio) y en el orden de Tab.

Archivos:

- `src/frontends/apps/sisoc/src/routes/InspSelect2.tsx`.
- Pruebas: `src/frontends/apps/sisoc/src/routes/InspSelect2.test.tsx` (nueva) y
  `src/frontends/apps/sisoc/src/routes/inspeccionesActas.test.tsx`.

## Comportamiento

Igual al nativo observado en el navegador con los mismos assets:

| Acción | Resultado |
| --- | --- |
| Clic en la caja | abre; el foco queda en la caja, sin anillo de teclado |
| Enter, Espacio o Alt+↓ en la caja cerrada | abre; ↓ y ↑ solos no abren |
| Escape, Tab o Alt+↑ con el desplegable abierto | cierra sin elegir; el foco queda en la caja |
| ↑/↓ y Enter con el desplegable abierto | mueven el resaltado y eligen, desde la caja o desde la búsqueda |
| Clic en la búsqueda | el foco pasa al campo; la caja pierde `select2-container--focus` |
| Clic afuera | cierra, vacía la búsqueda y no mueve el foco |
| Botón × | vacía la selección y abre el desplegable con foco en la caja |
| Elegir la opción ya elegida | cierra sin evento `change` (no reenvía el filtro) |

El resaltado inicial es la opción seleccionada (o la primera), y la clase
`select2-container--below` queda después de la primera apertura, como deja
Select2. Escribir con el foco en la caja no escribe en la búsqueda, igual que
el nativo.

## Verificación

- Pruebas: 8 casos nuevos o ajustados fallaron antes del cambio y pasan
  después; `vitest --project sisoc` completo, `tsc`, `eslint` y `vite build`.
- Sonda de navegador nativo contra React (22 escenarios de teclado, mouse,
  borrado y clic afuera en el filtro de localidad, el filtro de inspector y el
  modal de escuela): estado, foco, anillo y clases iguales.
- Regla visual S13 con el harness de la pestaña Escuelas (19 casos × 2) y del
  listado de actas (7 casos × 2) más el recorrido de interacción del piloto.

Límite conocido, previo al cambio: al cerrar el modal de escuela con Escape o
clic en el fondo, el nativo conserva el formulario durante la animación de
salida y React lo desmonta.
