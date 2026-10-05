---
name: tema-verde-institucional
description: >
  Aplica el sistema de diseño VERDE institucional (dos modos: claro por defecto + oscuro) a un
  proyecto nuevo. Trae la paleta exacta (teal de marca #04756F, neutrales "piedra" cálidos, ámbar
  de acento, navegación verde oscuro), el mapeo a roles y un tema de Material UI (createTheme)
  listo para claro y oscuro, con tipografía Roboto y contraste AA. Usar cuando haya que theming,
  branding, paleta de colores, modo oscuro/claro o "poné el verde de SISOC" en apps React con MUI
  (o adaptarlo a Tailwind / CSS variables).
---

# Tema verde institucional (SISOC) — para reusar en otros proyectos

Sistema de diseño de **dos modos** (CLARO por defecto ⇄ OSCURO), verde. Origen: backoffice SISOC
(Tailwind + CSS variables). Este skill lo empaqueta para aplicarlo en **cualquier app React con
Material UI**. La paleta y el mapeo a roles son la fuente de verdad; el `createTheme` de abajo es la
traducción directa a MUI.

## Principios (no negociar)

1. **Un solo juego de roles, dos modos.** Los componentes usan roles (`primary`, `background`,
`text`, …), nunca hex sueltos. Cambiar de modo = cambiar el valor de los roles, no el markup.
2. **Teal de marca = `#04756F`** (primary.main en claro). Cumple AA (~5,5:1 sobre blanco) como texto.
3. **Neutrales "piedra" cálidos** (la escala grey de MUI), no grises fríos.
4. **Navegación (AppBar + Drawer/sidebar) = superficie MÁS OSCURA** en ambos modos: verde de marca
`#045F5B` (claro) / `#073B38` (oscuro), con **ámbar `#FFC000`** marcando la sección activa.
5. **Default = CLARO.** Preferencia persistida en `localStorage` (`app.theme`), best-effort try/catch.
6. **Contraste AA**: texto ≥ 4,5:1; borde de control y relleno de botón ≥ 3:1.

## Paleta exacta

### Modo CLARO (por defecto)

|Rol|Hex|Uso|
|-|-|-|
|primary.main|`#04756F`|links, activos, botón contained, acentos|
|primary.dark|`#045F5B`|títulos, hover de link|
|primary.light|`#9DCECB`|bordes/detalles sutiles de marca|
|primary.surface|`#E4F1F0`|fondo de ítem activo / hover|
|primary.chip|`#C6E3E1`|chip de marca / avatar|
|primary.contrastText|`#FFFFFF`|—|
|background.default (canvas)|`#F5F5F4`|body|
|background.paper (card)|`#FFFFFF`|superficie elevada|
|divider|`#E7E5E4`|hairline|
|border card/panel|`#D6D3D1`|—|
|border fuerte de control|`#8A837D`|inputs (≥ 3:1)|
|text.primary|`#1C1917`|tinta principal|
|text.secondary|`#57534E`|—|
|icon atenuado|`#6F6862`|(≥ 4,5:1)|
|**nav.surface**|`#045F5B`|AppBar/Drawer (chrome)|
|**nav.activeBg**|`#045049`|ítem activo del nav|
|**nav.accent (ámbar)**|`#FFC000`|sección activa, franja de banner|
|nav.text|`#FAFAF9`|texto sobre el nav|
|nav.textMuted|`#D6D3D1`|íconos/texto atenuado del nav|
|info|surf `#E3F2FB` / border `#0288D1` / text `#01466E`|estado neutral|
|attention|surf `#FBEEE1` / border `#E86A00` / text `#7A3B00`|estado neutral|
|pending|surf `#EFEFEE` / border `#78716C` / text `#44403C`|estado neutral|

### Modo OSCURO

|Rol|Hex|Uso|
|-|-|-|
|primary.main|`#379F9B`|relleno de botón / marca|
|primary.light|`#54C4C0`|íconos/links luminosos|
|primary "text"|`#6FD0CC`|links/activos sobre fondo oscuro|
|primary.surface|`#0C3B39`|fondo de ítem activo / hover|
|primary.contrastText|`#1C1917`|tinta oscura sobre teal claro|
|background.default (canvas)|`#1C1917`|body|
|background.paper (card)|`#292524`|superficie elevada|
|divider|`#44403C`|hairline|
|border card/panel|`#57534E`|—|
|border fuerte de control|`#78716C`|inputs (≥ 3:1)|
|text.primary|`#FAFAF9`|tinta principal (casi blanco)|
|text.secondary|`#D6D3D1`|—|
|icon atenuado|`#A8A29E`|(≥ 4,5:1 sobre card)|
|**nav.surface**|`#073B38`|AppBar/Drawer (chrome)|
|**nav.activeBg**|`#0A2E2B`|ítem activo del nav|
|**nav.accent (ámbar)**|`#FFCD33`|ámbar aclarado|
|nav.text|`#FAFAF9`|—|
|info|surf `#0E2F3F` / border `#3DC1FD` / text `#9FDDFB`|—|
|attention|surf `#3A2A1A` / border `#FFB74D` / text `#FFCF99`|—|
|pending|surf `#2B2725` / border `#78716C` / text `#D6D3D1`|—|

**Tipografía:** Roboto (300/400/500/700). Fallback: `'Segoe UI', system-ui, -apple-system, sans-serif`.
**Foco:** teal `#04756F` (claro) / `#54C4C0` (oscuro).

## Material UI — `createTheme` (pegar y usar)

`theme.ts`:

```ts
import { createTheme, type Theme } from '@mui/material/styles';

const FONT = "'Roboto','Segoe UI',system-ui,-apple-system,sans-serif";

// El nav (AppBar/Drawer) es una superficie propia; lo exponemos en theme para consumirlo con sx.
declare module '@mui/material/styles' {
  interface Palette { nav: { surface: string; activeBg: string; accent: string; text: string; textMuted: string } }
  interface PaletteOptions { nav?: Palette['nav'] }
}

export function buildTheme(mode: 'light' | 'dark'): Theme {
  const light = mode === 'light';
  return createTheme({
    palette: {
      mode,
      primary: light
        ? { main: '#04756F', light: '#9DCECB', dark: '#045F5B', contrastText: '#FFFFFF' }
        : { main: '#379F9B', light: '#54C4C0', dark: '#6FD0CC', contrastText: '#1C1917' },
      background: light
        ? { default: '#F5F5F4', paper: '#FFFFFF' }
        : { default: '#1C1917', paper: '#292524' },
      text: light
        ? { primary: '#1C1917', secondary: '#57534E' }
        : { primary: '#FAFAF9', secondary: '#D6D3D1' },
      divider: light ? '#E7E5E4' : '#44403C',
      info: { main: light ? '#0288D1' : '#3DC1FD' },
      warning: { main: light ? '#E86A00' : '#FFB74D' }, // "attention" (no semáforo)
      nav: light
        ? { surface: '#045F5B', activeBg: '#045049', accent: '#FFC000', text: '#FAFAF9', textMuted: '#D6D3D1' }
        : { surface: '#073B38', activeBg: '#0A2E2B', accent: '#FFCD33', text: '#FAFAF9', textMuted: '#D6D3D1' },
    },
    shape: { borderRadius: 8 },
    typography: {
      fontFamily: FONT,
      h1: { fontWeight: 700 }, h2: { fontWeight: 700 }, h3: { fontWeight: 500 },
      button: { textTransform: 'none', fontWeight: 500 }, // sin MAYÚSCULAS forzadas
    },
    components: {
      MuiCssBaseline: { styleOverrides: { body: { fontFamily: FONT } } },
      MuiButton: { defaultProps: { disableElevation: true } },
      // Chrome de marca: AppBar y Drawer usan la superficie de navegación (verde oscuro) en ambos modos.
      MuiAppBar: {
        styleOverrides: {
          colorPrimary: ({ theme }) => ({
            backgroundColor: theme.palette.nav.surface,
            color: theme.palette.nav.text,
            borderBottom: `3px solid ${theme.palette.nav.accent}`, // franja ámbar de marca
          }),
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: ({ theme }) => ({ backgroundColor: theme.palette.nav.surface, color: theme.palette.nav.text }),
        },
      },
    },
  });
}
```

`main.tsx` (montaje + modo persistido):

```tsx
import { ThemeProvider, CssBaseline } from '@mui/material';
import { useMemo, useState } from 'react';
import { buildTheme } from './theme';

const STORAGE_KEY = 'app.theme';
const read = (): 'light' | 'dark' => { try { return localStorage.getItem(STORAGE_KEY) === 'dark' ? 'dark' : 'light'; } catch { return 'light'; } };

export function AppRoot({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<'light' | 'dark'>(read);
  const theme = useMemo(() => buildTheme(mode), [mode]);
  const toggle = () => setMode((m) => { const n = m === 'light' ? 'dark' : 'light'; try { localStorage.setItem(STORAGE_KEY, n); } catch {} return n; });
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline /> {/* pinta background.default y aplica la tipografía */}
      {/* pasá `toggle` a tu botón Sol/Luna */}
      {children}
    </ThemeProvider>
  );
}
```

**Ítem activo del menú (ámbar):** en el `ListItemButton` seleccionado del Drawer,
`sx={{ '&.Mui-selected': { bgcolor: 'nav.activeBg', borderLeft: theme => `3px solid ${theme.palette.nav.accent}` } }}`.

## Notas de adaptación

* **Roboto**: agregá `@fontsource/roboto` (300/400/500/700) o el `<link>` de Google Fonts
`family=Roboto:wght@300;400;500;700`.
* **Tailwind / sin MUI**: en vez del `createTheme`, definí las CSS variables `--color-primary`,
`--color-bg`, `--color-paper`, etc. con los hex de las tablas y redefinilas bajo `.dark`. Misma
paleta, mismo resultado.
* **Estados** info/attention/pending son **neutrales, no un semáforo**. Si el proyecto necesita un
semáforo (rojo/amarillo/verde), usá otra escala: acá el verde es de MARCA, no de "OK".
* **Exclusión de branding** (patrón SISOC): si alguna pantalla no debe llevar la marca (p. ej. una
superficie donde el color no debe influir), no la envuelvas en el tema o dale una paleta neutra.
