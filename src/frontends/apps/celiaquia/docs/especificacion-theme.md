# Theme de MUI — SISOC Design System

Documento para el equipo de desarrollo. Acompaña al archivo `theme.ts`.

**Fuente de verdad**: las variables del archivo de Figma *Nuevo DS SISOC*, colección
*Sisoc Tokens*. Si un valor cambia allá, hay que cambiarlo en `theme.ts`. No escriban hex
sueltos en los componentes.

---

## 1. Cómo se usa

```tsx
import { ThemeProvider, CssBaseline } from '@mui/material';
import { getTheme } from './theme';

const theme = getTheme(modo); // 'light' | 'dark'

<ThemeProvider theme={theme}>
  <CssBaseline />
  {children}
</ThemeProvider>
```

El theme es una función del modo, no un objeto fijo. Los dos modos están completos: no hay
componentes ni pantallas duplicadas, el mismo código sirve para ambos.

Se necesita Roboto en los pesos **300, 400, 500 y 700**.

---

## 2. Lo que es MUI nativo

La mayor parte entra directo y no requiere explicación:

- Las seis familias de color (`primary`, `secondary`, `error`, `warning`, `info`, `success`)
  con sus tonos `light` / `main` / `dark` / `contrastText`.
- La escala de grises `50` a `900`.
- `background.default` y `background.paper`, `text.*`, `divider`, `action.*`.
- Las 13 variantes tipográficas estándar.
- Las 25 sombras de elevación.
- Los cinco breakpoints, con los valores por defecto de MUI.

**El espaciado también es nativo.** La escala del sistema ES `theme.spacing()` con base 8, y
los nombres de los tokens de Figma son directamente el multiplicador:

| token en Figma | en código |
|---|---|
| `spacing/0-5` = 4px | `theme.spacing(0.5)` |
| `spacing/0-75` = 6px | `theme.spacing(0.75)` |
| `spacing/1` = 8px | `theme.spacing(1)` |
| `spacing/1-5` = 12px | `theme.spacing(1.5)` |
| `spacing/2` = 16px | `theme.spacing(2)` |
| `spacing/3` = 24px | `theme.spacing(3)` |
| `spacing/12` = 96px | `theme.spacing(12)` |

---

## 3. Lo que extiende MUI

Esto sí requiere la ampliación de tipos que está al principio de `theme.ts`.

### 3.1 Seis variantes tipográficas propias

`h4Bold`, `subtitle1Medium`, `buttonSmall`, `buttonLarge`, `chip`, `captionBold`.

Las tres primeras cubren pesos que MUI no ofrece en esos tamaños. `buttonSmall` y
`buttonLarge` son los 13px y 15px que MUI usa en los botones small y large pero no expone
como variantes. `chip` es el 13px del label de un Chip.

Se usan como cualquier otra: `<Typography variant="captionBold">`.

### 3.2 Color de texto por severidad: `palette.{severidad}.text`

**El token más importante de esta extensión.** Es el color del texto de una severidad sobre
una superficie neutra (`paper` o `default`). Apunta al tono oscuro en modo claro y al claro
en oscuro, que es lo que hace MUI internamente en `Alert standard`.

```tsx
// BIEN
<Typography sx={{ color: 'success.text' }}>100%</Typography>

// MAL: no invierte con el modo. En pantallas oscuras da 2.96:1.
<Typography sx={{ color: 'success.dark' }}>100%</Typography>
```

Regla corta:

| dónde va el texto | token |
|---|---|
| sobre superficie neutra | `{severidad}.text` |
| sobre un fondo de ese color | `{severidad}.contrastText` |

`contrastText` está calculado contra `main`. No sirve sobre `dark` ni sobre `light`.

### 3.3 Un tono extra: `palette.{warning,secondary}.darker`

El naranja y el ámbar no llegan a 4.5:1 como texto sobre blanco ni en su tono `dark`. Por eso
esas dos escalas tienen un paso más oscuro, que es lo que usa su `.text` en modo claro.

No es un tono de MUI. Solo existe en esas dos familias.

### 3.4 `palette.nav` — la navegación de marca

El Header, el Drawer, el Footer y las tarjetas de navegación son superficies de marca:
**siempre oscuras, en los dos modos**.

```
nav.surface          #045F5B en claro · #073B38 en oscuro
nav.surfaceSelected  #033F3C en claro · #0A5D58 en oscuro
nav.text             #FAFAF9 en ambos
nav.textMuted        #D6D3D1 en ambos
nav.accent           el ámbar de secondary; marca la sección activa
nav.hover            blanco 8%
nav.selected         blanco 16%
nav.divider          blanco 12%
```

**`nav.surfaceSelected`** es la superficie de la sección activa: la tarjeta de navegación
seleccionada y el ítem de primer nivel del menú. Es teal saturado con valor por modo, más
oscuro que `surface` en claro y más claro en oscuro.

No es un velo. Un velo blanco desatura la superficie y la sección activa se lee apagada en vez
de activa; y oscurecerla siempre no sirve en modo oscuro, donde `surface` ya está cerca de la
página. La separación contra las no seleccionadas es de 1.6:1 en los dos modos.

Los ítems de segundo y tercer nivel del menú sí usan el velo `nav.selected`: son chicos y
están dentro de una sección ya marcada.

**Por qué existe.** Si el Drawer usara `primary.dark`, en modo oscuro ese token se aclara hasta
0.1390 de luminancia y la barra compite con el contenido. `nav.surface` tiene un valor propio en
oscuro que la baja a 0.0346, cuatro veces más oscuro.

**Con una aclaración importante.** En modo oscuro la barra **no** es la superficie más oscura:

| superficie | luminancia en oscuro |
|---|---|
| `background.default` | 0.0100 |
| `background.paper` | 0.0192 |
| `nav.surface` | 0.0346 |

Eso es inevitable. Para que la barra fuera más oscura que una página en `#1C1917` haría falta
una luminancia menor a 0.0100, y un teal así queda indistinguible de la página: 1.08:1. El
valor actual da 1.41:1, que es la mejor separación disponible.

**La barra se distingue por el tono, no por la luminancia**: teal contra gris cálido, más el
borde derecho en `nav.divider`. El texto encima da 11.89:1.

En modo claro sí es la más oscura, con 6.89:1 contra la página.

Los overrides de `MuiAppBar`, `MuiDrawer`, `MuiListItemButton` y `MuiListItemIcon` en
`theme.ts` ya aplican estos tokens. No hace falta pasarlos a mano.

### 3.5 `palette.input.outlinedBorder`

Negro al 23%, el valor que MUI define internamente en `OutlinedInput` pero no expone en la
paleta. Ya está aplicado en el override de `MuiOutlinedInput`.

### 3.6 `theme.radius`, `theme.border`, `theme.iconSize`

MUI tiene un solo `shape.borderRadius`. El sistema usa una escala:

```
radius.small   2   radius.base  4 (el shape.borderRadius del theme)
radius.medium  8   botones, chips, tarjetas
radius.large  16   paneles
radius.full 9999   avatares y píldoras
```

```
border.thin   1   bordes normales
border.focus  2   anillo de foco y borde de estado activo
border.accent 4   la franja ámbar del Header y el Footer
```

```
iconSize.small 20 · medium 24 · large 35 · buttonSmall 14 · buttonLarge 18
```

---

## 4. Jerarquía de superficies

Tres niveles, de atrás hacia adelante:

1. **Fondo de pantalla** → `background.default`
2. **Panel o tarjeta** → `background.paper`
3. **Bloque destacado dentro de un panel** → capa con `action.hover`

MUI por defecto pone `default` y `paper` en blanco puro y separa solo con la sombra de
elevación. Acá se diferencia el fondo porque varios paneles usan borde `divider` en vez de
sombra. Por eso `background.default` es `grey[100]` y no blanco.

---

## 5. Capas de estado

Para tintes de hover, selección y foco, usen los tokens que **ya traen la transparencia**:
`action.hover`, `action.selected`, `action.focus`, `nav.hover`, `nav.selected`.

Si necesitan un tinte de un color específico, la forma correcta es:

```tsx
backgroundColor: alpha(theme.palette.primary.main, 0.08)
```

No apliquen opacidad al contenedor: afecta también al contenido.

---

## 6. Lo que el theme NO puede expresar

Estas cuatro cosas quedan del lado de la implementación.

**El scroll del menú lateral.** Con varias secciones desplegadas el árbol supera el alto
disponible (con las tres abiertas llega a 808px contra 540 de contenedor). El bloque del menú
necesita `overflow-y: auto`, y el ítem de cerrar sesión queda **fuera** de ese scroll, fijado
al pie.

**El scroll horizontal de las tablas.** Cada tabla tiene un ancho mínimo útil documentado en
su componente de Figma. Por debajo de ese ancho corresponde `TableContainer` con
`overflow-x: auto`. Los mínimos actuales: preliquidación 798px, alertas de incompatibilidad
1068px, cursos FCH 826px.

**El color de íconos por contexto.** En Figma existe una colección auxiliar *Icon Context* con
siete modos, porque Figma no tiene herencia de color. En código eso no hace falta: el ícono
hereda con `color: 'inherit'` o se le pasa la prop `color`. La tabla de equivalencia:

| modo en Figma | en código |
|---|---|
| Default | `text.primary` |
| OnPrimary | `primary.contrastText` |
| OnSecondary | `secondary.contrastText` |
| OnSurface | `primary.main` |
| Muted | `action.active` |
| Disabled | `text.disabled` |
| OnNav | `nav.text` |

**`color="inherit"`.** Donde el diseño de Figma pinta el label de un botón o ícono por
severidad, en código va la prop `color="inherit"` y el color lo da el contenedor. Figma no
tiene herencia, así que ahí hay overrides que en código no corresponden.

---

## 7. Decisiones de accesibilidad

Si van a cambiar un color, tengan en cuenta por qué está donde está. Todo el sistema se midió:
**cero fallas de contraste** en 694 textos por modo, con el mínimo de 4.5:1 (3:1 para texto
grande).

- **`info.main` se oscureció** de `#0288D1` a `#01699F`. El valor por defecto de MUI da 3.86:1
  con texto blanco encima, que no alcanza.
- **`{severidad}.text` existe** porque usar `.dark` como color de texto daba 2.96:1 en modo
  oscuro.
- **`warning.darker` y `secondary.darker` existen** porque el naranja y el ámbar no llegan a
  4.5:1 sobre blanco ni en su tono `dark`.
- **Los íconos de `secondary` usan `dark`, no `main`**: el ámbar sobre blanco da 1.6:1 y no
  alcanza el 3:1 que se pide para elementos de interfaz.
- **`nav.textMuted` es `grey[300]`, no `grey[400]`**: sobre `nav.surface` el 400 daba 2.98:1.

El texto con `text.disabled` está por debajo del mínimo a propósito: WCAG exime los elementos
inactivos, y su bajo contraste es la señal de que están deshabilitados.

---

## 8. Verificación sugerida

Antes de dar el theme por integrado:

1. Renderizar un botón de cada variante y tamaño en los dos modos.
2. Renderizar un `Alert` de cada severidad en variante `standard` y verificar que el texto usa
   `.text` y no `.dark`.
3. Poner el Drawer y el AppBar en modo oscuro y confirmar que **se distinguen** del contenido:
   tono teal, borde visible y texto legible. NO esperen que sean más oscuros que la página: en
   modo oscuro quedan por encima y es correcto.
4. Confirmar que las seis variantes tipográficas propias resuelven y tipan.
5. Medir contraste con las herramientas del navegador en un par de pantallas por modo.
