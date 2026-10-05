// ============================================================================
// SISOC Design System — theme de MUI
// Generado desde el archivo de Figma "Nuevo DS SISOC" (colección Sisoc Tokens).
//
// Fuente de verdad: las variables de Figma. Si un valor cambia allá, cambialo acá.
// No escribas hex sueltos en los componentes: usá siempre theme.palette.*
//
// Uso:
//   import { ThemeProvider, CssBaseline } from '@mui/material';
//   import { getTheme } from './theme';
//   const theme = getTheme(modo); // 'light' | 'dark'
//   <ThemeProvider theme={theme}><CssBaseline />...</ThemeProvider>
// ============================================================================

import { createTheme, type ThemeOptions } from '@mui/material/styles';
import type { PaletteMode } from '@mui/material';
import type { CSSProperties } from 'react';

// ----------------------------------------------------------------------------
// 1. Ampliación de tipos
//    Necesaria para que TypeScript acepte las variantes y los tokens propios.
// ----------------------------------------------------------------------------

declare module '@mui/material/styles' {
  interface TypographyVariants {
    h4Bold: CSSProperties;
    subtitle1Medium: CSSProperties;
    buttonSmall: CSSProperties;
    buttonLarge: CSSProperties;
    chip: CSSProperties;
    captionBold: CSSProperties;
  }
  interface TypographyVariantsOptions {
    h4Bold?: CSSProperties;
    subtitle1Medium?: CSSProperties;
    buttonSmall?: CSSProperties;
    buttonLarge?: CSSProperties;
    chip?: CSSProperties;
    captionBold?: CSSProperties;
  }

  // Color de texto por severidad, sobre superficie neutra.
  interface PaletteColor {
    text?: string;
    darker?: string;
  }
  interface SimplePaletteColorOptions {
    text?: string;
    darker?: string;
  }

  // Superficie de la navegación de marca.
  interface Palette {
    nav: {
      surface: string;
      surfaceSelected: string;
      text: string;
      textMuted: string;
      accent: string;
      hover: string;
      selected: string;
      divider: string;
    };
    input: { outlinedBorder: string };
  }
  interface PaletteOptions {
    nav?: Palette['nav'];
    input?: Palette['input'];
  }

  // Escala de radios y bordes.
  interface Theme {
    radius: { small: number; base: number; medium: number; large: number; full: number };
    border: { thin: number; focus: number; accent: number };
    iconSize: { small: number; medium: number; large: number; buttonSmall: number; buttonLarge: number };
  }
  interface ThemeOptions {
    radius?: Theme['radius'];
    border?: Theme['border'];
    iconSize?: Theme['iconSize'];
  }
}

declare module '@mui/material/Typography' {
  interface TypographyPropsVariantOverrides {
    h4Bold: true;
    subtitle1Medium: true;
    buttonSmall: true;
    buttonLarge: true;
    chip: true;
    captionBold: true;
  }
}

// ----------------------------------------------------------------------------
// 2. Primitivas
//    La escala de grises NO invierte con el modo: es una primitiva.
//    Lo que invierte son los tokens semánticos que la usan.
// ----------------------------------------------------------------------------

const grey = {
  50: '#FAFAF9',
  100: '#F5F5F4',
  200: '#E7E5E4',
  300: '#D6D3D1',
  400: '#A8A29E',
  500: '#78716C',
  600: '#57534E',
  700: '#44403C',
  800: '#292524',
  900: '#1C1917',
};

// Colores originales de la marca. No se usan en la interfaz: quedan como registro.
export const brand = {
  verdeLogo: '#058782',
  turquesa: { light: '#63D4D0', main: '#3CC9C4', dark: '#2A8D89' },
};

// ----------------------------------------------------------------------------
// 3. Paleta por modo
//
//    OJO: light / main / dark son TONOS del mismo color, para estados.
//    No tienen relación con el modo. La escala entera se corre un paso hacia
//    el claro en modo oscuro.
//
//    Para texto de severidad usá `.text` (invierte con el modo).
//    Para texto sobre un fondo de color usá `.contrastText` (calculado contra main).
//    NUNCA uses `.dark` como color de texto: no invierte y falla el contraste.
// ----------------------------------------------------------------------------

const paletas = {
  light: {
    primary:   { light: '#379F9B', main: '#04756F', dark: '#045F5B', contrastText: '#FFFFFF', text: '#045F5B' },
    secondary: { light: '#FFCD33', main: '#FFC000', dark: '#B38600', contrastText: '#1C1917', text: '#7A5C00', darker: '#7A5C00' },
    error:     { light: '#EF5350', main: '#D32F2F', dark: '#C62828', contrastText: '#FFFFFF', text: '#C62828' },
    warning:   { light: '#FF9800', main: '#ED6C02', dark: '#E65100', contrastText: '#1C1917', text: '#8A3A00', darker: '#8A3A00' },
    info:      { light: '#03A9F4', main: '#01699F', dark: '#01579B', contrastText: '#FFFFFF', text: '#01579B' },
    success:   { light: '#4CAF50', main: '#2E7D32', dark: '#1B5E20', contrastText: '#FFFFFF', text: '#1B5E20' },
    background: { default: '#F5F5F4', paper: '#FFFFFF' },
    text: { primary: '#1C1917', secondary: '#57534E', disabled: '#A8A29E' },
    divider: '#E7E5E4',
    action: {
      active: 'rgba(0,0,0,0.54)',
      hover: 'rgba(0,0,0,0.04)',
      selected: 'rgba(0,0,0,0.08)',
      focus: 'rgba(0,0,0,0.12)',
      disabled: 'rgba(0,0,0,0.26)',
      disabledBackground: 'rgba(0,0,0,0.12)',
    },
    input: { outlinedBorder: '#78716C' },
    // La navegación de marca es SIEMPRE oscura, en los dos modos.
    nav: {
      surface: '#045F5B',
      // La sección activa: teal saturado, MÁS OSCURO que surface en claro.
      surfaceSelected: '#033F3C',
      text: '#FAFAF9',
      textMuted: '#D6D3D1',
      accent: '#FFC000',
      hover: 'rgba(255,255,255,0.08)',
      selected: 'rgba(255,255,255,0.16)',
      divider: 'rgba(255,255,255,0.12)',
    },
  },
  dark: {
    primary:   { light: '#54C4C0', main: '#379F9B', dark: '#04756F', contrastText: '#1C1917', text: '#54C4C0' },
    secondary: { light: '#FFDD75', main: '#FFCD33', dark: '#FFC000', contrastText: '#1C1917', text: '#FFDD75', darker: '#B38600' },
    error:     { light: '#F59593', main: '#F05956', dark: '#D32F2F', contrastText: '#1C1917', text: '#F59593' },
    warning:   { light: '#FFB74D', main: '#FF9800', dark: '#ED6C02', contrastText: '#1C1917', text: '#FFB74D', darker: '#E65100' },
    info:      { light: '#3DC1FD', main: '#03A9F4', dark: '#0288D1', contrastText: '#1C1917', text: '#3DC1FD' },
    success:   { light: '#79C57C', main: '#4CAF50', dark: '#2E7D32', contrastText: '#1C1917', text: '#79C57C' },
    background: { default: '#1C1917', paper: '#292524' },
    text: { primary: '#FAFAF9', secondary: '#A8A29E', disabled: '#78716C' },
    divider: '#44403C',
    action: {
      active: '#FFFFFF',
      hover: 'rgba(255,255,255,0.08)',
      selected: 'rgba(255,255,255,0.16)',
      focus: 'rgba(255,255,255,0.12)',
      disabled: 'rgba(255,255,255,0.3)',
      disabledBackground: 'rgba(255,255,255,0.12)',
    },
    input: { outlinedBorder: '#A8A29E' },
    // surface tiene un valor propio en oscuro, cuatro veces más oscuro que
    // primary/dark (0.0346 contra 0.1390 de luminancia).
    //
    // OJO: en modo oscuro la barra NO es la superficie más oscura. La página
    // está en 0.0100 y los paneles en 0.0192, así que la barra queda por
    // encima de las dos. Eso es inevitable: un teal con luminancia menor a
    // 0.0100 se vuelve indistinguible de la página (1.08:1). El valor actual
    // da 1.41:1 contra la página, que es la mejor separación posible.
    //
    // La barra se distingue por el TONO (teal contra gris cálido) más un
    // borde, no por ser más oscura. El texto encima da 11.89:1.
    nav: {
      surface: '#073B38',
      // En oscuro la activa es MÁS CLARA, no más oscura: surface ya está cerca
      // de la página. Sigue siendo teal saturado, nunca un velo blanco.
      surfaceSelected: '#0A5D58',
      text: '#FAFAF9',
      textMuted: '#D6D3D1',
      accent: '#FFCD33',
      hover: 'rgba(255,255,255,0.08)',
      selected: 'rgba(255,255,255,0.16)',
      divider: 'rgba(255,255,255,0.12)',
    },
  },
} as const;

// ----------------------------------------------------------------------------
// 4. Tipografía — Roboto en todo el sistema
//    Las seis últimas variantes NO existen en MUI: son propias.
// ----------------------------------------------------------------------------

const typography = {
  fontFamily: 'Roboto, sans-serif',
  fontWeightLight: 300,
  fontWeightRegular: 400,
  fontWeightMedium: 500,
  fontWeightBold: 700,

  h1: { fontWeight: 300, fontSize: '6rem',      lineHeight: '112px', letterSpacing: '-1.44px' },
  h2: { fontWeight: 300, fontSize: '3.75rem',   lineHeight: '72px',  letterSpacing: '-0.6px' },
  h3: { fontWeight: 400, fontSize: '3rem',      lineHeight: '56px',  letterSpacing: '0px' },
  h4: { fontWeight: 400, fontSize: '2.125rem',  lineHeight: '42px',  letterSpacing: '0.09px' },
  h5: { fontWeight: 400, fontSize: '1.5rem',    lineHeight: '32px',  letterSpacing: '0px' },
  h6: { fontWeight: 500, fontSize: '1.25rem',   lineHeight: '32px',  letterSpacing: '0.03px' },
  subtitle1: { fontWeight: 400, fontSize: '1rem',     lineHeight: '28px', letterSpacing: '0.14px' },
  subtitle2: { fontWeight: 500, fontSize: '0.875rem', lineHeight: '22px', letterSpacing: '0.1px' },
  body1:     { fontWeight: 400, fontSize: '1rem',     lineHeight: '24px', letterSpacing: '0.14px' },
  body2:     { fontWeight: 400, fontSize: '0.875rem', lineHeight: '20px', letterSpacing: '0.24px' },
  button:    { fontWeight: 500, fontSize: '0.875rem', lineHeight: '24px', letterSpacing: '0.41px', textTransform: 'uppercase' as const },
  caption:   { fontWeight: 400, fontSize: '0.75rem',  lineHeight: '20px', letterSpacing: '0.4px' },
  overline:  { fontWeight: 400, fontSize: '0.75rem',  lineHeight: '32px', letterSpacing: '1px', textTransform: 'uppercase' as const },

  // Propias del sistema
  h4Bold:          { fontWeight: 700, fontSize: '2.125rem',  lineHeight: '42px', letterSpacing: '0.09px' },
  subtitle1Medium: { fontWeight: 500, fontSize: '1rem',      lineHeight: '28px', letterSpacing: '0.14px' },
  buttonSmall:     { fontWeight: 500, fontSize: '0.8125rem', letterSpacing: '0.41px', textTransform: 'uppercase' as const },
  buttonLarge:     { fontWeight: 500, fontSize: '0.9375rem', letterSpacing: '0.41px', textTransform: 'uppercase' as const },
  chip:            { fontWeight: 400, fontSize: '0.8125rem', letterSpacing: '0.16px' },
  captionBold:     { fontWeight: 700, fontSize: '0.75rem',   lineHeight: '20px', letterSpacing: '0.4px' },
};

// ----------------------------------------------------------------------------
// 5. Sombras — la escala de elevación de Material, con el negro de nuestro grey/900
//    El índice 0 es 'none'; los 24 restantes son shadow/01 a shadow/24.
// ----------------------------------------------------------------------------

const sombra = (a: string, b: string, c: string) => `${a}, ${b}, ${c}`;
const S = 'rgba(28,25,23,';
const shadows = [
  'none',
  sombra(`0px 2px 1px -1px ${S}0.2)`, `0px 1px 1px 0px ${S}0.14)`, `0px 1px 3px 0px ${S}0.12)`),
  sombra(`0px 3px 1px -2px ${S}0.2)`, `0px 2px 2px 0px ${S}0.14)`, `0px 1px 5px 0px ${S}0.12)`),
  sombra(`0px 3px 3px -2px ${S}0.2)`, `0px 3px 4px 0px ${S}0.14)`, `0px 1px 8px 0px ${S}0.12)`),
  sombra(`0px 2px 4px -1px ${S}0.2)`, `0px 4px 5px 0px ${S}0.14)`, `0px 1px 10px 0px ${S}0.12)`),
  sombra(`0px 3px 5px -1px ${S}0.2)`, `0px 5px 8px 0px ${S}0.14)`, `0px 1px 14px 0px ${S}0.12)`),
  sombra(`0px 3px 5px -1px ${S}0.2)`, `0px 6px 10px 0px ${S}0.14)`, `0px 1px 18px 0px ${S}0.12)`),
  sombra(`0px 4px 5px -2px ${S}0.2)`, `0px 7px 10px 1px ${S}0.14)`, `0px 2px 16px 1px ${S}0.12)`),
  sombra(`0px 5px 5px -3px ${S}0.2)`, `0px 8px 10px 1px ${S}0.14)`, `0px 3px 14px 2px ${S}0.12)`),
  sombra(`0px 5px 6px -3px ${S}0.2)`, `0px 9px 12px 1px ${S}0.14)`, `0px 3px 16px 2px ${S}0.12)`),
  sombra(`0px 6px 6px -3px ${S}0.2)`, `0px 10px 14px 1px ${S}0.14)`, `0px 4px 18px 3px ${S}0.12)`),
  sombra(`0px 6px 7px -4px ${S}0.2)`, `0px 11px 15px 1px ${S}0.14)`, `0px 4px 20px 3px ${S}0.12)`),
  sombra(`0px 7px 8px -4px ${S}0.2)`, `0px 12px 17px 2px ${S}0.14)`, `0px 5px 22px 4px ${S}0.12)`),
  sombra(`0px 7px 8px -4px ${S}0.2)`, `0px 13px 19px 2px ${S}0.14)`, `0px 5px 24px 4px ${S}0.12)`),
  sombra(`0px 7px 9px -4px ${S}0.2)`, `0px 14px 21px 2px ${S}0.14)`, `0px 5px 26px 4px ${S}0.12)`),
  sombra(`0px 8px 9px -5px ${S}0.2)`, `0px 15px 22px 2px ${S}0.14)`, `0px 6px 28px 5px ${S}0.12)`),
  sombra(`0px 8px 10px -5px ${S}0.2)`, `0px 16px 24px 2px ${S}0.14)`, `0px 6px 30px 5px ${S}0.12)`),
  sombra(`0px 8px 11px -5px ${S}0.2)`, `0px 17px 26px 2px ${S}0.14)`, `0px 6px 32px 5px ${S}0.12)`),
  sombra(`0px 9px 11px -5px ${S}0.2)`, `0px 18px 28px 2px ${S}0.14)`, `0px 7px 34px 6px ${S}0.12)`),
  sombra(`0px 9px 12px -6px ${S}0.2)`, `0px 19px 29px 2px ${S}0.14)`, `0px 7px 36px 6px ${S}0.12)`),
  sombra(`0px 10px 13px -6px ${S}0.2)`, `0px 20px 31px 3px ${S}0.14)`, `0px 8px 38px 7px ${S}0.12)`),
  sombra(`0px 10px 13px -6px ${S}0.2)`, `0px 21px 33px 3px ${S}0.14)`, `0px 8px 40px 7px ${S}0.12)`),
  sombra(`0px 10px 14px -6px ${S}0.2)`, `0px 22px 35px 3px ${S}0.14)`, `0px 8px 42px 7px ${S}0.12)`),
  sombra(`0px 11px 14px -7px ${S}0.2)`, `0px 23px 36px 3px ${S}0.14)`, `0px 9px 44px 8px ${S}0.12)`),
  sombra(`0px 11px 15px -7px ${S}0.2)`, `0px 24px 38px 3px ${S}0.14)`, `0px 9px 46px 8px ${S}0.12)`),
] as ThemeOptions['shadows'];

// ----------------------------------------------------------------------------
// 6. Escalas propias
// ----------------------------------------------------------------------------

// radius/base (4px) es el borderRadius por defecto de MUI.
// medium (8) se usa en botones, chips y tarjetas; large (16) en paneles;
// full (9999) en avatares y píldoras.
const radius = { small: 2, base: 4, medium: 8, large: 16, full: 9999 };

const border = { thin: 1, focus: 2, accent: 4 };

const iconSize = { small: 20, medium: 24, large: 35, buttonSmall: 14, buttonLarge: 18 };

// ----------------------------------------------------------------------------
// 7. El theme
// ----------------------------------------------------------------------------

export const getTheme = (mode: PaletteMode = 'light') => {
  const p = paletas[mode];

  return createTheme({
    palette: { mode, grey, ...p },
    typography,
    shadows,
    // La escala de espaciado del sistema ES la de MUI con base 8:
    // spacing(0.5)=4, spacing(0.75)=6, spacing(1)=8, spacing(1.5)=12,
    // spacing(2)=16, spacing(3)=24, spacing(4)=32, spacing(6)=48, spacing(12)=96.
    spacing: 8,
    shape: { borderRadius: radius.base },
    breakpoints: { values: { xs: 0, sm: 600, md: 900, lg: 1200, xl: 1536 } },
    radius,
    border,
    iconSize,

    components: {
      // Botón: radius/medium y sin elevación. Los tamaños small y large usan
      // las variantes tipográficas propias.
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { borderRadius: radius.medium },
          sizeSmall: { ...typography.buttonSmall },
          sizeLarge: { ...typography.buttonLarge },
        },
      },
      // Chip: el label usa la variante propia `chip`.
      MuiChip: {
        styleOverrides: { label: { ...typography.chip } },
      },
      // Tabs: el indicador va en secondary, no en primary.
      MuiTabs: {
        defaultProps: { indicatorColor: 'secondary' },
      },
      // Paper: los paneles del sistema usan borde en vez de sombra.
      MuiPaper: {
        styleOverrides: {
          outlined: ({ theme }) => ({
            borderRadius: radius.large,
            borderColor: theme.palette.divider,
          }),
        },
      },
      MuiCard: {
        defaultProps: { variant: 'outlined' },
        styleOverrides: { root: { borderRadius: radius.large } },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: ({ theme }) => ({
            borderRadius: radius.medium,
            '& .MuiOutlinedInput-notchedOutline': { borderColor: theme.palette.input.outlinedBorder },
          }),
        },
      },
      // AppBar: superficie de marca, no primary.
      MuiAppBar: {
        defaultProps: { color: 'transparent', elevation: 2 },
        styleOverrides: {
          root: ({ theme }) => ({
            backgroundColor: theme.palette.nav.surface,
            color: theme.palette.nav.text,
            borderBottom: `${border.accent}px solid ${theme.palette.secondary.main}`,
          }),
        },
      },
      // Drawer permanente: misma superficie de marca que el AppBar.
      MuiDrawer: {
        styleOverrides: {
          paper: ({ theme }) => ({
            backgroundColor: theme.palette.nav.surface,
            color: theme.palette.nav.text,
            // En modo oscuro la barra y los paneles quedan a 1.22:1 de
            // luminancia: muy poco. El borde hace el trabajo de separación.
            borderRight: `${border.thin}px solid ${theme.palette.nav.divider}`,
          }),
        },
      },
      // Ítems de navegación: viven sobre la superficie de marca.
      //
      // El seleccionado de PRIMER nivel (las secciones: Administración, Módulos,
      // Tableros) cambia de superficie a nav.surfaceSelected. Los de segundo y
      // tercer nivel usan el velo nav.selected, que ahí sí alcanza porque son
      // ítems chicos dentro de una sección ya marcada.
      //
      // El primer nivel NO usa velo: un velo blanco desatura la superficie y la
      // sección activa se lee apagada en vez de activa.
      MuiListItemButton: {
        styleOverrides: {
          root: ({ theme }) => ({
            borderRadius: radius.medium,
            color: theme.palette.nav.text,
            '&:hover': { backgroundColor: theme.palette.nav.hover },
            '&.Mui-selected': {
              backgroundColor: theme.palette.nav.selected,
              color: theme.palette.nav.accent,
              '&:hover': { backgroundColor: theme.palette.nav.selected },
            },
            // Aplicar esta clase a los ítems de sección (primer nivel).
            '&.SisocNav-section.Mui-selected': {
              backgroundColor: theme.palette.nav.surfaceSelected,
              color: theme.palette.nav.accent,
              '&:hover': { backgroundColor: theme.palette.nav.surfaceSelected },
            },
          }),
        },
      },
      MuiListItemIcon: {
        styleOverrides: {
          root: ({ theme }) => ({ color: 'inherit', minWidth: theme.spacing(4) }),
        },
      },
      // Alert standard: el fondo tenue de la severidad y el texto con `.text`.
      MuiAlert: {
        defaultProps: { variant: 'standard' },
        styleOverrides: {
          root: ({ theme }) => ({
            borderRadius: radius.medium,
            '&.MuiAlert-standardError': { color: theme.palette.error.text },
            '&.MuiAlert-standardWarning': { color: theme.palette.warning.text },
            '&.MuiAlert-standardInfo': { color: theme.palette.info.text },
            '&.MuiAlert-standardSuccess': { color: theme.palette.success.text },
          }),
        },
      },
    },
  });
};

export default getTheme;
