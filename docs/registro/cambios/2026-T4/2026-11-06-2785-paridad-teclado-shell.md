# Cambio: paridad de teclado y foco del marco React (#2785)

## Alcance

Correcciones del marco compartido de React (`SisocShell` en
`src/frontends/apps/sisoc/src/App.tsx`), de su hoja
`src/frontends/apps/sisoc/src/shell.css` y del login
(`src/frontends/apps/sisoc/src/Login.tsx`) detectadas en el recorrido con
teclado de INS-A, INS-B, login, cuenta, grupos y cambio de contraseña. Se
hicieron en dos partes: la primera ordena el sidebar y corrige el enlace de
versión del marco; la segunda devuelve el foco a los estilos nativos, hace
enfocable el logo móvil y corrige el enlace de versión del login y el destino
de «Volver». No modifica backend, el DTO de navegación, rutas de producción ni
dependencias.

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

Las diferencias de teclado que quedaron abiertas en esta primera parte se
corrigen en la segunda, descrita a continuación.

## Segunda parte: foco nativo, logo móvil, login y «Volver»

### Diagnóstico

- Contorno de foco. `shell.css` dibujaba un contorno dorado de 3 px con
  separación de 2 px en todo botón o enlace con `:focus-visible`, salvo el
  botón de guardar de Mi cuenta (excepción del registro
  `2026-11-04-2785-react-cuenta-confirmacion.md`). La página original no
  define esa regla: el logo, «Resetear», «Agregar», «Exportar búsqueda» y el
  enlace de versión muestran el contorno automático de 1 px del navegador;
  «Cerrar sesión» y «Abrir menu» no muestran contorno; «Buscar» muestra el
  contorno sólido blanco de 2 px de sus estilos. Todos esos valores vienen de
  las hojas compartidas, que React ya carga.
- Logo móvil. El template `src/backends/kernel/templates/includes/header.html`
  escribe el logo como `brand-link d-flex align-items-center` en todos los
  tamaños. En 390 px queda con ancho 0, invisible pero enfocable entre «Abrir
  menu» y «Cerrar sesión». React le agregaba `d-none` con el menú móvil
  cerrado y lo sacaba del recorrido con Tab.
- Enlace de versión del login. `Login.tsx` apuntaba a `/changelog/` (404); la
  ruta `changelog` del pie original se publica como `/novedades/`.
- «Volver». `src/backends/kernel/templates/components/back_button.html` usa
  `volver_url` con `/` por defecto. Ninguna de las vistas originales de las
  pantallas React (insumos, categorías, mi cuenta, grupos, cambio de
  contraseña) define `volver_url`, así que el destino es `/`. React apuntaba a
  `/inicio/`.

### Comportamiento

- `shell.css` ya no define reglas de foco: botones y enlaces del marco, del
  login y de Mi cuenta usan los estilos de foco originales. El atributo
  `data-mi-cuenta-submit` sigue en el botón, pero ya no lo usa ninguna regla.
- El logo del encabezado usa siempre las clases del template original y es
  enfocable en móvil igual que en la página original.
- El enlace de versión del login apunta a `/novedades/`.
- «Volver» apunta a `/`. React no reproduce el historial de
  `src/backends/kernel/static/custom/js/volver.js`, que en la página original
  reemplaza ese destino con la pantalla anterior de la sesión; sin historial,
  ambos quedan en `/`.

### Verificación

Copia aislada sobre la primera parte. Cinco pruebas fallaron antes de
implementar: el foco nativo del botón de guardar y de otros controles del marco
(en cuenta y en confirmación), el destino de «Volver», el logo móvil enfocable
y el enlace de versión del login. La prueba previa que fijaba la excepción del
botón de Mi cuenta se reemplazó por una que exige que ninguna regla de foco de
`shell.css` alcance a ese botón ni a otros controles del marco. Después pasan
las 181 pruebas frontend, TypeScript, ESLint y el build de Vite.

Runtime sintético local, solo GET, 1440x900 y 390x844, comparando la página
original con React antes y después de esta parte, en INS-A, categorías de
INS-B, login, cuenta, listado de grupos y cambio de contraseña, con 16 Tab:

- Donde ambos enfocan el mismo control, el contorno calculado coincide en
  todos los pasos (antes difería en el logo, «Cerrar sesión», «Abrir menú»,
  «Buscar», «Resetear», «Agregar», «Exportar búsqueda» y el enlace de versión).
  Las capturas con foco del listado de grupos y de cuenta en móvil pasan a ser
  idénticas a la página original en los 17 pasos.
- En móvil, el logo es la segunda parada, con el mismo rectángulo de ancho 0
  y el mismo contorno.
- «Volver» y el enlace de versión del login tienen el mismo destino que la
  página original.
- Capturas sin foco: las de React antes y después de esta parte son idénticas
  byte a byte en los 32 pares de los ocho casos (incluido el superusuario de
  grupos y la confirmación de cambio de contraseña).

Diferencias que siguen y no se corrigen aquí:

- En móvil, el submenú activo de Insumos queda oculto en línea dentro del
  menú cerrado en la página original y visible en React, así que React tiene
  una parada de Tab invisible más dentro del menú móvil. Es la diferencia del
  menú móvil ya exenta.
- En `/password_change/`, React enfoca la contraseña anterior al cargar; en la
  página original el autofoco depende del tiempo de carga y en esta corrida no
  ocurrió, así que el recorrido queda corrido un paso.
- El ajuste de altura de `sidebar.js` al desplazarse, descrito arriba.
- Nombres accesibles: el logo de React se anuncia «Inicio de SISOC» y en la
  página original toma el texto alternativo «SISOC»; los enlaces de las
  pantallas en vista previa apuntan a `/v2/sisoc/...`. No cambian la
  presentación.
- Variaciones de render ya clasificadas: flecha A, glifos B y el logo de
  Presidencia del login, que alterna en la propia página original.

No hubo POST, errores de página ni solicitudes bloqueadas; dominio sintético
sin cambios. No constituye aceptación humana, revisión nativa, CI ni
despliegue. Riesgo técnico: marco compartido por todas las pantallas React.
