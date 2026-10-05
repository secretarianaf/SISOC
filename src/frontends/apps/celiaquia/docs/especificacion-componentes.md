# Especificación de componentes — SISOC Design System

Documento para el equipo de desarrollo. Acompaña a `theme.ts` y a
`especificacion-theme.md`.

**Cómo leer esto.** Este documento es el mapa: qué componente de MUI corresponde a cada pieza,
con qué props, y qué decisiones hay detrás. **El detalle completo está en la descripción de
cada componente en Figma**, que en promedio tiene 1.600 caracteres con los tokens exactos,
los arreglos hechos y las notas de uso. Seleccionen el componente en Figma y lean el panel
derecho.

Son **38 componentes**: 18 bajo `MUI/` y 20 bajo `Sisoc/`.

---

## 1. La convención de nombres

- **`MUI/X`** — es un componente de MUI configurado con el theme. El nombre siempre es un
  componente real de MUI.
- **`Sisoc/X`** — es una composición nuestra. No existe en MUI, se arma con piezas de MUI.
- **`MUI/Icon/X`** — el ícono existe en `@mui/icons-material` con ese nombre exacto.
- **`Sisoc/Icon/X`** — activo propio. Se suma como SVG envuelto en `SvgIcon`.

Esa distinción les dice de dónde sacar cada pieza sin adivinar.

---

## 2. Componentes MUI

| componente | base MUI | variantes | propiedades |
|---|---|---|---|
| Alert | `Alert` | 12 | Severity(4) × Variant(3), 4 slots opcionales |
| Avatar | `Avatar` | 9 | Size(3) × Content(3), Initials, Badge |
| Button | `Button` | 60 | Size(2) × Variant(3) × Color(2) × State(5), Start Icon |
| Checkbox | `Checkbox` | 9 | Checked(3) × State(3) |
| Circular progress | `CircularProgress` determinate | 3 | STATE(3) |
| Filter chip | `Chip` | 10 | Style(2) × State(5), Label |
| IconButton | `IconButton` | 30 | Size(2) × Color(3) × State(5), Icon source |
| Linear progress | `LinearProgress` determinate | 11 | Progress(11) |
| Link | `Link` | 4 | State(4), Label |
| List item | `ListItemButton` + `Collapse` | 27 | Level(3) × State(3) × Caret(3) |
| Requirement chip | `Chip` size small outlined | 1 | Label |
| Score chip | `Chip` | 3 | Color(3), Label |
| State chip | `Chip` | 6 | Color(6), Label, Dot |
| Step | `Step` + `StepLabel` + `StepConnector` | 3 | State(3), Number, Label, Status |
| Tab | `Tab` | 4 | State(4), Label, Icon |
| Tabs | `Tabs` | 1 | compuesta de Tab |
| Text field | `TextField` outlined + `InputAdornment` | 1 | Placeholder, Icon source |
| Timeline item | `TimelineItem` | 3 | State(3), Date, Description |

### Notas que importan

**Button** — los ejes son exactamente los de MUI. No tiene `color="inherit"` porque Figma no
tiene herencia; donde el diseño lo emula, en código va la prop.

**Filter chip** — el componente funcional real es el **grupo con selección compartida**. MUI no
tiene `ChipGroup`: se arma con un `Stack` de Chips y el estado en el padre.

**Requirement chip** — no es el `Badge` de MUI. El Badge es el contador que se pega a un ícono;
esto es un Chip pequeño que marca requisitos.

**List item** — en MUI **no existe un componente de menú con submenús**. El árbol es una
composición: `List` + `ListItemButton` + `ListItemIcon` + `Collapse`. El sidebar se arma
apilando instancias porque la cantidad depende de los datos.

**Timeline item** — el Timeline vive en **`@mui/lab`**, no en `@mui/material`.

**Linear progress y Circular progress** — están como variantes y no con una propiedad numérica
porque en Figma el ancho de la barra no se puede sobreescribir dentro de una instancia. En
código eso no aplica: pasen el valor y calculen color y ancho.

**Text field** — en MUI hay **un solo** `TextField`. Un campo de búsqueda es este mismo con el
ícono de Search. Por eso el componente es genérico con el ícono intercambiable.

---

## 3. Componentes Sisoc

### Superficies de marca

| componente | base MUI | notas |
|---|---|---|
| Header | `AppBar` position fixed + `Toolbar` | el avatar sería un `IconButton` que abre un `Menu` |
| Sidebar | `Drawer` variant permanent + `List` | el árbol se arma apilando `List item` |
| Footer | `Box` o `Paper` | MUI no tiene componente Footer |

Las tres usan `palette.nav`. Los overrides ya están en `theme.ts`.

### Tarjetas clickeables

| componente | base MUI | variantes | notas |
|---|---|---|---|
| Titular card | `ButtonBase` + Chips | 5 | |
| Ticket card | `ButtonBase` | 5 | usa State chip y Priority label |
| Scoring card | `ButtonBase` | 5 | usa Score chip |
| Navigation card | `ButtonBase` | 5 | usa `nav.surface`, no primary |
| Program card | `Card` outlined + `Checkbox` | 4 | el clic en toda la tarjeta alterna la selección |

**Todas son `ButtonBase`**, o sea que se renderizan como un elemento `button` con ripple y foco
por teclado. Por eso **los chips que contienen son siempre display, nunca interactivos**: no se
puede anidar un botón dentro de otro.

En la Program card, la superficie completa es un `FormControlLabel` del Checkbox o un
`CardActionArea`.

### Paneles y organismos

| componente | base MUI | variantes | usa |
|---|---|---|---|
| Alert message | `Alert` variant standard | 3 | Alert + Circular progress |
| Data check row | `Paper` outlined + `Stack` | 1 | State chip |
| Liquidation panel | `Card` + CardHeader/Content/Actions | 1 | Alert, Button |
| Tickets panel | `Card` | 1 | Filter chip, Ticket card, Button |
| Ticket inbox | `Paper` + `Stack` | 1 | Avatar, Button |
| Scoring selector | `Paper` outlined + Stack de ButtonBase | 1 | Scoring card |
| Tabs Panel | `Tabs` + `TabPanel` + Box/Stack | 3 | Tabs, State chip, Linear progress, Timeline item |
| Stat card | `Card` + `Typography` | 5 | |
| Priority label | `Typography` con color semántico | 3 | |
| Preliquidation table | `Card` + `Table` | 1 | State chip |
| Incompatibility alerts | `Card` + `Table` | 1 | State chip, Link |
| Monthly circuit stepper | `Card` + `Stepper` + Button | 7 | Step, Button |

**Paper contra Card**: en MUI, `Card` **es** un `Paper` con `overflow: hidden`. Se usa `Paper
outlined` cuando es solo superficie con borde, y `Card` cuando tiene encabezado, contenido o
acciones al pie.

**`CardContent` agrega padding propio** (16px, y 24px abajo en el último hijo). Hay que
sobreescribirlo.

---

## 4. Reglas de negocio que están en el diseño

Esto es lógica, no decoración. Si no se implementa, la interfaz miente.

### 4.1 Regla de severidad unificada

Aplica a **Score chip, Circular progress y Linear progress**, sobre un requerido de 100 puntos:

| valor | estado | color |
|---|---|---|
| 0 | No iniciado / Incumplido | `error` |
| 1 a 99 | En curso / Parcial | `warning` |
| 100 o más | Aprobado / Cumplido | `success` |

El color **se deriva del número**, no se elige. En Figma hay que elegir la variante porque no
hay lógica condicional; en código se calcula.

### 4.2 La Stat card NO sigue esa regla

Su color **refuerza el significado del dato**, no resulta de un cálculo:

- `error` → cifras que señalan un problema (bloqueados para el cobro, pagos rechazados)
- `warning` → piden atención sin ser problema cerrado (pendientes, próximos a vencer)
- `success` → cifras positivas o resueltas (habilitados, aprobados)
- `primary` → neutras, informativas, sin juicio (total de titulares, monto liquidado)
- `secondary` → destacar una cifra clave sin valorarla

### 4.3 Criterio del State chip

**Warning** es lo que requiere mirarse: alertas detectadas, revisiones pendientes, en curso.
**Error** es lo que ya bloquea o exige actuar: suspendido, bloqueado, no iniciado.

Estados de titular y cuenta: Success (Activo, OK, Aprobado, Cuenta Operativa, Resuelto) ·
Error (Suspendido, BLOQUEADO, No iniciado) · Warning (En Curso, Cuenta sin movimiento) ·
Info (En Gestión, Abierto) · Neutral (Egresado) · Primary (Reactivado).

**Notificar, Revisar y Suspender son etiquetas informativas, no acciones.** Si en algún momento
se vuelven clickeables, corresponde un `Button size="small"`, no un Chip.

### 4.4 El menú lateral se arma con la selección

En la pantalla de **Hub de programas** el usuario elige con qué programas va a trabajar. Eso
determina el sidebar:

- **Módulos** muestra SOLO los programas seleccionados.
- **Administración y Tableros** muestran siempre todo su contenido. Son secciones de sistema.

---

## 5. Pendientes de implementación

Cosas que la maqueta no puede expresar.

**Scroll del menú lateral.** Con varias secciones desplegadas el árbol supera el alto
disponible: con las tres abiertas llega a 808px contra 540 de contenedor. El bloque del menú
necesita `overflow-y: auto`, y **Cerrar Sesión queda fuera de ese scroll**, fijado al pie.

**Scroll horizontal de las tablas.** Cada tabla tiene su ancho mínimo útil documentado en
Figma. Por debajo corresponde `TableContainer` con `overflow-x: auto`. Los mínimos actuales:
preliquidación **798px**, alertas de incompatibilidad **1068px**, cursos FCH **826px**.

**Filas y listas variables.** Donde la cantidad de elementos depende de los datos, en Figma se
apilan instancias y en código se mapea el array: el sidebar, el Timeline, el Stepper, las filas
de las tres tablas, los mensajes del Ticket inbox, las tarjetas del Tickets panel y los ítems
del Scoring selector.

**`color="inherit"`.** Donde el diseño pinta el label de un botón o ícono por severidad, en
código va la prop y el color lo da el contenedor.

**Componentes sin propiedades expuestas.** Scoring selector, Tickets panel, Ticket inbox y las
dos tablas no exponen props en Figma: su contenido se edita entrando a la instancia. En código
todos reciben datos.

---

## 6. Cómo mantener esto sincronizado

**La fuente de verdad es Figma.** Las descripciones de los 38 componentes tienen el detalle
completo y se mantienen ahí.

Cuando cambien un componente, actualicen su descripción en Figma en el mismo movimiento. Una
descripción que miente es peor que no tener descripción.

**El estado del sistema al cierre de esta especificación:**

- 38 componentes, 34 íconos
- 125 variables en dos colecciones, 19 estilos de texto, 24 sombras
- 11 pantallas en modo claro y 11 en oscuro
- Cero instancias remotas, cero colores sin token, cero textos sin estilo
- Cero fallas de contraste en 694 textos por modo
