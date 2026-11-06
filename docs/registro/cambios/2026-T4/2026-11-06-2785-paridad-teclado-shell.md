# Cambio: orden de tabulación del sidebar y enlace de versión en el marco React (#2785)

## Alcance

Corrección del marco compartido de React (`SisocShell` en
`src/frontends/apps/sisoc/src/App.tsx`) detectada en el recorrido con teclado
de INS-A, INS-B, cuenta y grupos. No modifica backend, el DTO de navegación,
estilos, rutas de producción ni dependencias.

## Diagnóstico

- Orden de tabulación del sidebar. El template
  `src/backends/kernel/templates/includes/sidebar/opciones.html` escribe los
  ítems principales en el orden Inicio, Comunicados, Administración del
  sistema, Configuración de Comedores, OCR, Tableros y Legajos, y fija la
  posición visual con `order` en línea (1, 7, 4, 5, 6, 3 y 2). El navegador
  tabula en el orden del DOM. `build_web_navigation` entrega los ítems en el
  orden visual y React los escribía así, con la misma posición en pantalla
  pero otro recorrido con Tab (Inicio, Legajos, Comunicados en vez de Inicio,
  Comunicados, Legajos).
- Enlace de versión del pie. React apuntaba a `/changelog/`, que responde 404;
  el template `src/backends/kernel/templates/includes/footer.html` usa la ruta
  `changelog`, publicada como `/novedades/`.
- Altura de la página al enfocar el enlace de versión. No depende del foco: el
  script nativo `src/backends/kernel/static/custom/js/sidebar.js` escucha
  cualquier desplazamiento y fija la altura de `.sidebar-wrapper` según la
  parte visible del pie. Con el sidebar más bajo, el documento pasa de 1036 a
  906 px y el desplazamiento salta de 136 a 6 px. Una rueda de mouse sin foco
  produce el mismo efecto. React no reproduce ese ajuste.

## Comportamiento

- Si todos los ítems principales del menú son los conocidos del template, React
  los escribe en el orden del template y aplica el mismo `order` en línea, sin
  la clase `order-1`. La posición visual no cambia y Tab recorre el sidebar
  igual que la página original. Si aparece un ítem sin posición conocida, se
  conserva el orden del servidor con el comportamiento anterior.
- El enlace de versión del marco apunta a `/novedades/`.
- No se reproduce el ajuste de altura por desplazamiento: cambiaría también la
  presentación sin foco después de desplazarse y replicaría un salto de
  desplazamiento de la página original. Queda como diferencia conocida.

## Verificación

En una copia aislada sobre la unidad React del cambio voluntario de
contraseña: la prueba de orden del sidebar y la del enlace de versión
fallaron antes de implementar; la prueba de menú con un ítem desconocido
fija el comportamiento anterior. La aserción previa que exigía la clase
`order-1` en Inicio se reemplazó por el `order` en línea. Después pasan las 179
pruebas frontend, TypeScript, ESLint y el build de Vite; el CSS generado es
idéntico byte a byte.

Runtime sintético local, solo GET, 1440x900 y 390x844, en INS-A, categorías de
INS-B, cuenta y listado de grupos (con usuario editor y con superusuario):

- Recorrido de 14 Tab: el sidebar enfoca los mismos ítems que la página
  original, en el mismo orden y con capturas de foco idénticas en esos pasos.
- Capturas sin foco: las de React antes y después del cambio son idénticas
  byte a byte en los diez casos; las diferencias con la página original son
  las ya clasificadas (flecha A, glifos B, menú móvil exento C y el ícono de OCR).

Diferencias de teclado previas que siguen abiertas y no se corrigen aquí:

- La regla de `src/frontends/apps/sisoc/src/shell.css` que dibuja un contorno
  dorado de 3 px en botones y enlaces con foco difiere del contorno nativo
  (por ejemplo «Cerrar sesión», «Buscar», «Resetear» y el logo). Quitarla
  requiere cambiar la prueba de `Account.test.tsx` que la fija.
- En móvil, el logo del encabezado es enfocable en la página original y no en
  React.
- El enlace de versión de `Login.tsx` también apunta a `/changelog/`.
- «Volver» apunta a `/inicio/` en React y a `/` en la página original.

No hubo POST, errores de página ni solicitudes bloqueadas; dominio sintético
sin cambios. No constituye aceptación humana, revisión nativa, CI ni
despliegue. Riesgo técnico: marco compartido por todas las pantallas React.
