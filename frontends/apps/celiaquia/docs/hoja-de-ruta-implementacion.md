# Hoja de ruta de implementación — SISOC Design System

Orden sugerido para construir el sistema en código. Acompaña a `theme.ts`,
`especificacion-theme.md` y `especificacion-componentes.md`.

**Antes de empezar necesitan acceso al archivo de Figma** *Nuevo DS SISOC*. Los documentos dan
el mapa conceptual; el layout exacto de cada pantalla se inspecciona en Figma. Todo el archivo
está en auto-layout con tokens, así que al inspeccionar ven `spacing/3` y no un 24 suelto.

---

## Etapa 1 — El theme

Integrar `theme.ts` con el `ThemeProvider` y verificarlo antes de escribir un componente.

Las cinco verificaciones están en la sección 8 de `especificacion-theme.md`. La más importante
es la tercera: **en modo oscuro el Drawer y el AppBar tienen que distinguirse del contenido**
por su tono teal y su borde. No por ser más oscuros: en modo oscuro quedan por encima de la
página en luminancia, y es correcto. Si la barra sale gris o el texto no se lee, algo del grupo
`nav` no se aplicó.

Salida de la etapa: una página en blanco con los dos modos funcionando y las seis variantes
tipográficas propias resolviendo.

---

## Etapa 2 — Los átomos

Los que no dependen de nada y aparecen en todo el resto.

**Primero los chips**, que son cuatro y comparten base `Chip`: State chip, Score chip,
Requirement chip y Filter chip. Empiecen por el **State chip**: es el más usado del sistema y
el que tiene la guía de color más cargada de reglas.

**Después** Button, IconButton, Link, Checkbox, Text field, Avatar.

**Y los indicadores**: Linear progress, Circular progress, Priority label.

Acá conviene implementar la **regla de severidad** como una función compartida, porque la usan
tres componentes:

```ts
const severidad = (pts: number, requerido = 100) =>
  pts === 0 ? 'error' : pts < requerido ? 'warning' : 'success';
```

Salida de la etapa: los átomos en un catálogo propio (Storybook o una página de prueba), con
todos sus estados visibles en los dos modos.

---

## Etapa 3 — La navegación

Header, Sidebar y Footer, más el List item.

Va temprano porque **es el marco de las 11 pantallas** y porque tiene la decisión más delicada
del sistema: el grupo `nav` y el scroll del menú.

Tres cosas para resolver acá:

- El bloque del menú con `overflow-y: auto` y Cerrar Sesión **fuera** de ese scroll.
- El árbol de tres niveles con `Collapse`, sabiendo que en MUI no existe un componente de menú
  con submenús: es una composición.
- La regla de armado: **Módulos se filtra por la selección del Hub; Administración y Tableros
  muestran todo siempre**.

Salida de la etapa: el marco navegable con contenido vacío.

---

## Etapa 4 — Los organismos

Los paneles que combinan átomos. En este orden, de menor a mayor dependencia:

1. **Alert message** — envuelve Alert + Circular progress
2. **Data check row** y **Stat card** — simples, sin listas
3. **Titular card, Ticket card, Scoring card, Navigation card, Program card** — las cinco
   clickeables, todas `ButtonBase`
4. **Scoring selector, Tickets panel, Ticket inbox** — contienen listas
5. **Las dos tablas** y el **Monthly circuit stepper**
6. **Tabs Panel** — el más compuesto, deja para el final

Dos cosas que aplican a todo este bloque:

**Las tarjetas clickeables son `ButtonBase`**, así que los chips de adentro son display. No
anidar botones.

**Donde la cantidad depende de los datos, mapear el array.** Aplica al sidebar, el Timeline, el
Stepper, las filas de las tablas, los mensajes del inbox y los ítems del selector.

---

## Etapa 5 — Las pantallas

Recién acá, y en este orden.

**Primero el flujo de entrada**, que es el más simple y valida la navegación:
LOGIN → Hub de programas → Bienvenida.

La de **Bienvenida** es importante: es donde el sidebar se arma con la selección del Hub. Si eso
funciona, el resto es composición.

**Después las tres del Panel de control**, que son la misma pantalla con distinta pestaña. Sirven
para validar el Tabs Panel y el patrón de lista con detalle.

**Y por último las cinco restantes**: las dos de Formación FCH, Circuito mensual, Mesa de ayuda y
Liquidación.

Para cada una: abrir la pantalla en Figma, inspeccionar la jerarquía de contenedores y
reproducirla. Los anchos mínimos de las tablas están documentados en cada componente.

---

## Qué verificar al cerrar

Cuatro cosas, medidas y no a ojo:

1. **Contraste en los dos modos.** El sistema se midió con cero fallas en 694 textos por modo.
   Si aparece una, algo se apartó de los tokens.
2. **Que ningún color esté escrito a mano.** Todo sale de `theme.palette.*`.
3. **Que las tres superficies de marca se distingan** del contenido en ambos modos. En claro
   son las más oscuras; en oscuro se distinguen por tono y borde.
4. **Que el menú lateral scrollee** con las tres secciones abiertas sin empujar Cerrar Sesión.
